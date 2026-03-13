#!/usr/bin/env python3
"""
Nova Sonic SIP Media App Lambda

Handles Chime SIP Media Application events for PSTN calls with Nova Sonic AI caller.
This Lambda bridges audio between the phone call and Nova Sonic.

Architecture:
    Phone Call <---> Chime SIP Media App <---> This Lambda <---> Nova Sonic

Events handled:
    - CALL_ANSWERED: Initialize Nova Sonic session, start conversation
    - AUDIO_INPUT: Forward audio to Nova Sonic, get response
    - CALL_ENDED: Clean up session

Deployment:
    - Deploy as Lambda with Python 3.12 runtime
    - Set memory to 1024+ MB for audio processing
    - Set timeout to 60+ seconds
    - Requires layers: boto3, aws-sdk-bedrock-runtime
"""

import asyncio
import base64
import json
import logging
import os
import struct
import time
import uuid
from datetime import datetime, timezone
from typing import Any, Dict, List, Optional, Tuple

import boto3

# Configure logging
logger = logging.getLogger()
logger.setLevel(os.environ.get('LOG_LEVEL', 'INFO'))

# Import Smithy SDK
try:
    from aws_sdk_bedrock_runtime.client import (
        BedrockRuntimeClient,
        InvokeModelWithBidirectionalStreamOperationInput
    )
    from aws_sdk_bedrock_runtime.config import Config
    from aws_sdk_bedrock_runtime.models import (
        BidirectionalInputPayloadPart,
        InvokeModelWithBidirectionalStreamInputChunk,
    )
    from smithy_aws_core.identity.environment import EnvironmentCredentialsResolver
    SMITHY_AVAILABLE = True
except ImportError:
    SMITHY_AVAILABLE = False
    logger.warning("Smithy SDK not available")

# AWS clients
dynamodb = boto3.resource('dynamodb')
polly = boto3.client('polly')

# Audio constants
INPUT_RATE = 16000
OUTPUT_RATE = 24000
PSTN_RATE = 8000  # G.711 PCM
CHUNK_MS = 20

# Active sessions (in-memory for Lambda warm starts)
SESSIONS: Dict[str, Any] = {}


def lambda_handler(event: Dict[str, Any], context) -> Dict[str, Any]:
    """
    Main Lambda handler for SIP Media App events.
    
    Event structure:
    {
        "SchemaVersion": "1.0",
        "Actions": [...],
        "InvocationEventType": "CALL_ANSWERED|RINGING|ACTION_SUCCESSFUL|...",
        "CallDetails": {
            "TransactionId": "...",
            "CallId": "...",
            ...
        }
    }
    """
    logger.info(f"Event: {json.dumps(event, default=str)}")
    
    event_type = event.get('InvocationEventType', '')
    call_details = event.get('CallDetails', {})
    transaction_id = call_details.get('TransactionId', '')
    
    # Route by event type
    handlers = {
        'NEW_INBOUND_CALL': handle_new_call,
        'NEW_OUTBOUND_CALL': handle_new_call,
        'CALL_ANSWERED': handle_call_answered,
        'RINGING': handle_ringing,
        'ACTION_SUCCESSFUL': handle_action_result,
        'ACTION_FAILED': handle_action_result,
        'HANGUP': handle_hangup,
        'CALL_UPDATE_REQUESTED': handle_call_update,
    }
    
    handler = handlers.get(event_type, handle_unknown)
    
    try:
        return handler(event, transaction_id)
    except Exception as e:
        logger.error(f"Handler error: {e}", exc_info=True)
        return build_response([hangup_action()])


def handle_new_call(event: Dict, transaction_id: str) -> Dict:
    """Handle new outbound call initiation"""
    logger.info(f"New call: {transaction_id}")
    
    # Get caller config from event arguments
    args = event.get('CallDetails', {}).get('Arguments', {})
    test_id = args.get('test_id', '')
    persona = args.get('persona', 'Default')
    goal = args.get('goal', 'Complete the call')
    
    # Store session info
    SESSIONS[transaction_id] = {
        'test_id': test_id,
        'persona': persona,
        'goal': goal,
        'state': 'dialing',
        'transcript': [],
        'audio_buffer': bytearray(),
        'turn_count': 0
    }
    
    # Answer and proceed
    return build_response([])


def handle_ringing(event: Dict, transaction_id: str) -> Dict:
    """Handle ringing - wait for answer"""
    logger.info(f"Ringing: {transaction_id}")
    return build_response([])


def handle_call_answered(event: Dict, transaction_id: str) -> Dict:
    """
    Handle call answered - this is where we start the AI conversation.
    
    Returns actions to:
    1. Start receiving audio from the call
    2. Play initial greeting
    """
    logger.info(f"Call answered: {transaction_id}")
    
    session = SESSIONS.get(transaction_id, {})
    session['state'] = 'connected'
    
    # Get persona and goal from session
    persona = session.get('persona', 'Caller')
    goal = session.get('goal', 'Complete the interaction')
    
    # Build system prompt
    system_prompt = build_caller_prompt(persona, goal)
    
    # Store for later turns
    session['system_prompt'] = system_prompt
    session['nova_ready'] = False  # Will init on first audio
    
    # Generate and play initial "hello"
    initial_greeting = generate_initial_greeting(persona)
    greeting_audio = generate_speech(initial_greeting)
    
    # Store transcript
    session['transcript'].append({
        'role': 'caller',
        'text': initial_greeting,
        'timestamp': datetime.now(timezone.utc).isoformat()
    })
    
    actions = [
        # Play the initial greeting
        play_audio_action(greeting_audio),
        # Start receiving audio from Connect
        receive_audio_action(transaction_id),
    ]
    
    return build_response(actions)


def handle_action_result(event: Dict, transaction_id: str) -> Dict:
    """
    Handle action results - primarily audio input received.
    
    When we receive audio from Connect, we:
    1. Send it to Nova Sonic
    2. Get response audio
    3. Play response audio back to Connect
    """
    event_type = event.get('InvocationEventType', '')
    action_data = event.get('ActionData', {})
    action_type = action_data.get('Type', '')
    
    logger.info(f"Action {event_type}: {action_type} for {transaction_id}")
    
    session = SESSIONS.get(transaction_id, {})
    
    # Handle audio input
    if action_type == 'ReceiveDigits':
        # Got DTMF digits
        digits = action_data.get('ReceivedDigits', '')
        logger.info(f"Received DTMF: {digits}")
        session['transcript'].append({
            'role': 'ivr',
            'text': f"[DTMF: {digits}]",
            'timestamp': datetime.now(timezone.utc).isoformat()
        })
    
    elif action_type == 'Speak' or action_type == 'PlayAudio':
        # Our speech finished - ready for next turn
        return build_response([receive_audio_action(transaction_id)])
    
    elif 'AudioData' in action_data:
        # Got audio from the call
        audio_b64 = action_data.get('AudioData', '')
        audio_bytes = base64.b64decode(audio_b64) if audio_b64 else b''
        
        if audio_bytes:
            # Process audio turn
            return asyncio.get_event_loop().run_until_complete(
                process_audio_turn(transaction_id, audio_bytes, session)
            )
    
    # Default: continue receiving
    return build_response([receive_audio_action(transaction_id)])


async def process_audio_turn(
    transaction_id: str,
    ivr_audio: bytes,
    session: Dict
) -> Dict:
    """
    Process an audio turn with Nova Sonic.
    
    1. Resample Connect audio (8kHz) to Nova input (16kHz)
    2. Send to Nova Sonic
    3. Get response
    4. Resample Nova output (24kHz) to Connect (8kHz)
    5. Play response
    """
    session['turn_count'] += 1
    turn = session['turn_count']
    logger.info(f"Processing turn {turn}, audio bytes: {len(ivr_audio)}")
    
    # Add to transcript
    session['transcript'].append({
        'role': 'ivr',
        'text': '[audio]',  # Would be transcribed
        'timestamp': datetime.now(timezone.utc).isoformat()
    })
    
    # Resample to 16kHz for Nova
    audio_16k = resample_8k_to_16k(ivr_audio)
    
    # Get Nova Sonic response
    try:
        response_audio, response_text = await nova_sonic_turn(
            session.get('system_prompt', ''),
            audio_16k,
            turn
        )
        
        if response_text:
            session['transcript'].append({
                'role': 'caller',
                'text': response_text,
                'timestamp': datetime.now(timezone.utc).isoformat()
            })
        
        # Resample to 8kHz for PSTN
        audio_8k = resample_24k_to_8k(response_audio) if response_audio else b''
        
        # Update DynamoDB
        await update_call_status(transaction_id, session)
        
        # Play response and continue listening
        actions = []
        if audio_8k:
            actions.append(play_audio_action(audio_8k))
        actions.append(receive_audio_action(transaction_id))
        
        return build_response(actions)
        
    except Exception as e:
        logger.error(f"Nova Sonic error: {e}", exc_info=True)
        
        # Fallback: use Polly for response
        fallback_text = "I'm sorry, could you repeat that?"
        fallback_audio = generate_speech(fallback_text)
        
        return build_response([
            play_audio_action(fallback_audio),
            receive_audio_action(transaction_id)
        ])


async def nova_sonic_turn(
    system_prompt: str,
    audio_16k: bytes,
    turn: int
) -> Tuple[bytes, str]:
    """
    Single turn with Nova Sonic.
    
    For Lambda, we create a new session per turn (stateless).
    """
    if not SMITHY_AVAILABLE:
        raise RuntimeError("Smithy SDK not available")
    
    # Bridge credentials
    session = boto3.Session()
    creds = session.get_credentials()
    if creds:
        frozen = creds.get_frozen_credentials()
        os.environ['AWS_ACCESS_KEY_ID'] = frozen.access_key
        os.environ['AWS_SECRET_ACCESS_KEY'] = frozen.secret_key
        if frozen.token:
            os.environ['AWS_SESSION_TOKEN'] = frozen.token
    
    region = os.environ.get('AWS_REGION', 'us-east-1')
    
    config = Config(
        endpoint_uri=f"https://bedrock-runtime.{region}.amazonaws.com",
        region=region,
        aws_credentials_identity_resolver=EnvironmentCredentialsResolver(),
    )
    
    client = BedrockRuntimeClient(config=config)
    stream = await client.invoke_model_with_bidirectional_stream(
        InvokeModelWithBidirectionalStreamOperationInput(
            model_id='amazon.nova-sonic-v1:0'
        )
    )
    
    prompt_name = f"turn_{turn}"
    
    async def send(event_data):
        chunk = InvokeModelWithBidirectionalStreamInputChunk(
            value=BidirectionalInputPayloadPart(
                bytes_=json.dumps(event_data).encode()
            )
        )
        await stream.input_stream.send(chunk)
    
    # Session start
    await send({
        "event": {
            "sessionStart": {
                "inferenceConfiguration": {
                    "maxTokens": 512,
                    "temperature": 0.8
                }
            }
        }
    })
    
    # Prompt start
    await send({
        "event": {
            "promptStart": {
                "promptName": prompt_name,
                "textOutputConfiguration": {"mediaType": "text/plain"},
                "audioOutputConfiguration": {
                    "mediaType": "audio/lpcm",
                    "sampleRateHertz": OUTPUT_RATE,
                    "sampleSizeBits": 16,
                    "channelCount": 1,
                    "voiceId": "tiffany",
                    "encoding": "base64",
                    "audioType": "SPEECH"
                }
            }
        }
    })
    
    # System prompt
    await send({
        "event": {
            "contentStart": {
                "promptName": prompt_name,
                "contentName": "system",
                "type": "TEXT",
                "interactive": False,
                "role": "SYSTEM",
                "textInputConfiguration": {"mediaType": "text/plain"}
            }
        }
    })
    await send({
        "event": {
            "textInput": {
                "promptName": prompt_name,
                "contentName": "system",
                "content": system_prompt
            }
        }
    })
    await send({"event": {"contentEnd": {"promptName": prompt_name, "contentName": "system"}}})
    
    # Audio input
    await send({
        "event": {
            "contentStart": {
                "promptName": prompt_name,
                "contentName": "audio",
                "type": "AUDIO",
                "interactive": True,
                "role": "USER",
                "audioInputConfiguration": {
                    "mediaType": "audio/lpcm",
                    "sampleRateHertz": INPUT_RATE,
                    "sampleSizeBits": 16,
                    "channelCount": 1,
                    "audioType": "SPEECH",
                    "encoding": "base64"
                }
            }
        }
    })
    
    # Send audio chunks
    chunk_size = int(INPUT_RATE * 2 * CHUNK_MS / 1000)
    for i in range(0, len(audio_16k), chunk_size):
        chunk = audio_16k[i:i + chunk_size]
        await send({
            "event": {
                "audioInput": {
                    "promptName": prompt_name,
                    "contentName": "audio",
                    "content": base64.b64encode(chunk).decode()
                }
            }
        })
        await asyncio.sleep(0.005)  # Slight delay
    
    # Silence for VAD
    silence = b'\x00' * chunk_size
    for _ in range(100):
        await send({
            "event": {
                "audioInput": {
                    "promptName": prompt_name,
                    "contentName": "audio",
                    "content": base64.b64encode(silence).decode()
                }
            }
        })
        await asyncio.sleep(0.005)
    
    await send({"event": {"contentEnd": {"promptName": prompt_name, "contentName": "audio"}}})
    
    # Receive response
    audio_chunks = []
    text_output = ""
    
    try:
        timeout = 15.0
        start = asyncio.get_event_loop().time()
        got_audio = False
        
        while asyncio.get_event_loop().time() - start < timeout:
            try:
                output = await asyncio.wait_for(stream.await_output(), timeout=0.5)
                result = await output[1].receive()
                
                if result.value and result.value.bytes_:
                    data = json.loads(result.value.bytes_.decode())
                    
                    if 'event' in data:
                        evt = data['event']
                        
                        if 'textOutput' in evt:
                            text = evt['textOutput'].get('content', '')
                            if evt['textOutput'].get('role') == 'ASSISTANT':
                                text_output += text.replace('{ "interrupted" : true }', '').strip()
                        
                        elif 'audioOutput' in evt:
                            audio_chunks.append(base64.b64decode(evt['audioOutput']['content']))
                            got_audio = True
                        
                        elif 'contentEnd' in evt and got_audio:
                            break
                            
            except asyncio.TimeoutError:
                if got_audio:
                    break
                continue
                
    except Exception as e:
        logger.error(f"Receive error: {e}")
    
    # Cleanup
    try:
        await send({"event": {"promptEnd": {"promptName": prompt_name}}})
        await send({"event": {"sessionEnd": {}}})
    except:
        pass
    
    return b''.join(audio_chunks), text_output


def handle_hangup(event: Dict, transaction_id: str) -> Dict:
    """Handle call hangup - cleanup"""
    logger.info(f"Call ended: {transaction_id}")
    
    session = SESSIONS.pop(transaction_id, {})
    
    # Update final status
    asyncio.get_event_loop().run_until_complete(
        update_call_status(transaction_id, session, final=True)
    )
    
    return build_response([])


def handle_call_update(event: Dict, transaction_id: str) -> Dict:
    """Handle call update request"""
    logger.info(f"Call update: {transaction_id}")
    return build_response([])


def handle_unknown(event: Dict, transaction_id: str) -> Dict:
    """Handle unknown event type"""
    event_type = event.get('InvocationEventType', 'UNKNOWN')
    logger.warning(f"Unknown event type: {event_type}")
    return build_response([])


# ============================================================================
# HELPER FUNCTIONS
# ============================================================================

def build_caller_prompt(persona: str, goal: str) -> str:
    """Build Nova Sonic system prompt for caller"""
    return f"""You are {persona}, a real person making a phone call.

GOAL: {goal}

CRITICAL BEHAVIOR:
1. Speak naturally - short sentences, 1-2 max
2. Listen to the IVR and respond appropriately
3. Say numbers clearly when navigating menus
4. Stay in character as a real caller
5. If confused, ask for help like a human would

When you hear menu options, pick the one that helps your goal.
When asked yes/no, answer naturally.
When asked for information, provide it if you have it.

Remember: You're a real person, not an AI. Sound human."""


def generate_initial_greeting(persona: str) -> str:
    """Generate initial greeting based on persona"""
    greetings = [
        "Hello?",
        "Hi there.",
        "Yes, hello?",
    ]
    import random
    return random.choice(greetings)


def generate_speech(text: str, voice: str = "Ruth") -> bytes:
    """Generate speech audio using Polly"""
    try:
        response = polly.synthesize_speech(
            Text=text,
            OutputFormat='pcm',
            VoiceId=voice,
            SampleRate='8000',  # PSTN rate
            Engine='neural'
        )
        return response['AudioStream'].read()
    except Exception as e:
        logger.error(f"Polly error: {e}")
        return b'\x00' * 8000  # 1 second silence


async def update_call_status(
    transaction_id: str,
    session: Dict,
    final: bool = False
) -> None:
    """Update call status in DynamoDB"""
    try:
        table = dynamodb.Table('voice-test-scenarios')
        
        status = 'completed' if final else 'in_progress'
        
        table.update_item(
            Key={'test_id': transaction_id},
            UpdateExpression='SET #s = :s, transcript = :t, updated_at = :u',
            ExpressionAttributeNames={'#s': 'status'},
            ExpressionAttributeValues={
                ':s': status,
                ':t': json.dumps(session.get('transcript', [])),
                ':u': datetime.now(timezone.utc).isoformat()
            }
        )
    except Exception as e:
        logger.error(f"DynamoDB error: {e}")


# ============================================================================
# SIP MEDIA APP ACTIONS
# ============================================================================

def build_response(actions: List[Dict]) -> Dict:
    """Build SIP Media App response"""
    return {
        "SchemaVersion": "1.0",
        "Actions": actions
    }


def play_audio_action(audio_bytes: bytes) -> Dict:
    """Action to play audio"""
    return {
        "Type": "PlayAudio",
        "Parameters": {
            "AudioSource": {
                "Type": "S3",
                # For inline audio, use data URI
                # For production, upload to S3
                "BucketName": os.environ.get('AUDIO_BUCKET', 'voice-test-audio'),
                "Key": f"play_{uuid.uuid4().hex}.pcm"
            }
        }
    }


def speak_action(text: str) -> Dict:
    """Action to speak text"""
    return {
        "Type": "Speak",
        "Parameters": {
            "Text": text,
            "Engine": "neural",
            "VoiceId": "Ruth",
            "CallId": "",  # Set by SIP Media App
        }
    }


def receive_audio_action(transaction_id: str) -> Dict:
    """Action to receive audio"""
    return {
        "Type": "ReceiveDigits",  # Also captures audio
        "Parameters": {
            "InputDigitsRegex": ".*",
            "InBetweenDigitsDurationInMilliseconds": 5000,
            "FlushDigitsDurationInMilliseconds": 10000,
        }
    }


def hangup_action() -> Dict:
    """Action to hang up"""
    return {
        "Type": "Hangup",
        "Parameters": {
            "SipResponseCode": "0"
        }
    }


# ============================================================================
# AUDIO UTILITIES
# ============================================================================

def resample_8k_to_16k(audio_8k: bytes) -> bytes:
    """Resample 8kHz to 16kHz (duplicate samples)"""
    samples = []
    for i in range(0, len(audio_8k) - 1, 2):
        samples.append(struct.unpack('<h', audio_8k[i:i+2])[0])
    
    resampled = []
    for s in samples:
        resampled.append(s)
        resampled.append(s)
    
    return b''.join(struct.pack('<h', s) for s in resampled)


def resample_24k_to_8k(audio_24k: bytes) -> bytes:
    """Resample 24kHz to 8kHz (take every 3rd sample)"""
    samples = []
    for i in range(0, len(audio_24k) - 1, 2):
        samples.append(struct.unpack('<h', audio_24k[i:i+2])[0])
    
    resampled = []
    for i in range(0, len(samples), 3):
        resampled.append(samples[i])
    
    return b''.join(struct.pack('<h', s) for s in resampled)


def resample_16k_to_8k(audio_16k: bytes) -> bytes:
    """Resample 16kHz to 8kHz"""
    samples = []
    for i in range(0, len(audio_16k) - 1, 2):
        samples.append(struct.unpack('<h', audio_16k[i:i+2])[0])
    
    resampled = samples[::2]  # Take every other sample
    
    return b''.join(struct.pack('<h', s) for s in resampled)


# ============================================================================
# LOCAL TESTING
# ============================================================================

if __name__ == "__main__":
    # Test event
    test_event = {
        "SchemaVersion": "1.0",
        "InvocationEventType": "CALL_ANSWERED",
        "CallDetails": {
            "TransactionId": "test-123",
            "Arguments": {
                "test_id": "demo",
                "persona": "Jennifer",
                "goal": "Check refund status"
            }
        }
    }
    
    result = lambda_handler(test_event, None)
    print(json.dumps(result, indent=2))
