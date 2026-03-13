"""
Nova Sonic SIP Media App Lambda - AI Caller with Real Voice

Handles Chime SIP Media Application events with Nova Sonic for intelligent
AI calling into Amazon Connect.
"""
import asyncio
import base64
import json
import logging
import os
import struct
import uuid
from datetime import datetime, timezone

import boto3

logger = logging.getLogger()
logger.setLevel(os.environ.get('LOG_LEVEL', 'INFO'))

# Import Smithy SDK for Nova Sonic
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
    NOVA_SONIC_AVAILABLE = True
    logger.info("Nova Sonic SDK loaded successfully")
except ImportError as e:
    NOVA_SONIC_AVAILABLE = False
    logger.warning(f"Nova Sonic SDK not available: {e}")

# AWS clients
dynamodb = boto3.resource('dynamodb')
polly = boto3.client('polly')
s3 = boto3.client('s3')

# Audio constants
INPUT_RATE = 16000
OUTPUT_RATE = 24000
PSTN_RATE = 8000

# S3 bucket for audio
AUDIO_BUCKET = os.environ.get('AUDIO_BUCKET', 'treasury-voice-test-audio')


def handler(event, context):
    """Main Lambda handler"""
    logger.info(f"Event: {json.dumps(event, default=str)[:500]}")
    
    event_type = event.get('InvocationEventType', '')
    call_details = event.get('CallDetails', {})
    transaction_id = call_details.get('TransactionId', '')
    
    logger.info(f"Invocation: {event_type}, Transaction: {transaction_id}")
    
    # Route events
    if event_type == 'NEW_OUTBOUND_CALL':
        return handle_new_call(event, transaction_id)
    elif event_type == 'RINGING':
        return handle_ringing(event, transaction_id)
    elif event_type == 'CALL_ANSWERED':
        return handle_call_answered(event, transaction_id)
    elif event_type == 'ACTION_SUCCESSFUL':
        return handle_action_success(event, transaction_id)
    elif event_type == 'ACTION_FAILED':
        return handle_action_failed(event, transaction_id)
    elif event_type == 'HANGUP':
        return handle_hangup(event, transaction_id)
    else:
        logger.warning(f"Unknown event: {event_type}")
        return build_response([])


def handle_new_call(event, transaction_id):
    """Handle new outbound call"""
    args = event.get('CallDetails', {}).get('Participants', [{}])[0].get('Arguments', {})
    if not args:
        args = event.get('ActionData', {}).get('Parameters', {}).get('Arguments', {})
    
    update_status(transaction_id, 'dialing', {
        'persona': args.get('persona', 'AI Caller'),
        'goal': args.get('goal', 'Complete the call'),
        'mode': args.get('mode', 'voice_test')
    })
    
    return build_response([])


def handle_ringing(event, transaction_id):
    """Handle ringing state"""
    update_status(transaction_id, 'ringing')
    return build_response([])


def handle_call_answered(event, transaction_id):
    """Handle call answered - start AI conversation"""
    update_status(transaction_id, 'connected')
    
    # Get persona info
    item = get_test_item(transaction_id)
    persona = item.get('persona', 'Caller')
    goal = item.get('goal', 'Complete the call')
    
    # Generate initial greeting with Nova Sonic
    if NOVA_SONIC_AVAILABLE:
        try:
            greeting_audio = asyncio.get_event_loop().run_until_complete(
                generate_nova_sonic_greeting(persona, goal)
            )
            if greeting_audio:
                audio_key = upload_audio_to_s3(greeting_audio, transaction_id, 'greeting')
                
                update_transcript(transaction_id, 'caller', '[AI greeting]')
                
                return build_response([
                    play_audio_action(audio_key),
                    receive_digits_action()
                ])
        except Exception as e:
            logger.error(f"Nova Sonic error: {e}")
    
    # Fallback to Polly
    greeting_text = f"Hello, this is {persona}. I'm calling to {goal[:50]}."
    audio_key = generate_polly_audio(greeting_text, transaction_id, 'greeting')
    
    update_transcript(transaction_id, 'caller', greeting_text)
    
    return build_response([
        play_audio_action(audio_key),
        receive_digits_action()
    ])


def handle_action_success(event, transaction_id):
    """Handle successful action - process audio and respond"""
    action_data = event.get('ActionData', {})
    action_type = action_data.get('Type', '')
    
    logger.info(f"Action successful: {action_type}")
    
    if action_type == 'ReceiveDigits':
        digits = action_data.get('ReceivedDigits', '')
        if digits:
            update_transcript(transaction_id, 'ivr', f'DTMF:{digits}')
        
        # Get context
        item = get_test_item(transaction_id)
        turn = item.get('turn_count', 0) + 1
        update_item(transaction_id, {'turn_count': turn})
        
        if turn > 10:
            # Too many turns, end call
            return build_response([hangup_action()])
        
        # Generate response with Nova Sonic
        if NOVA_SONIC_AVAILABLE:
            try:
                response_audio = asyncio.get_event_loop().run_until_complete(
                    generate_nova_sonic_response(
                        item.get('persona', 'Caller'),
                        item.get('goal', ''),
                        item.get('transcript', []),
                        turn
                    )
                )
                if response_audio:
                    audio_key = upload_audio_to_s3(response_audio, transaction_id, f'turn{turn}')
                    update_transcript(transaction_id, 'caller', f'[AI response turn {turn}]')
                    
                    return build_response([
                        play_audio_action(audio_key),
                        receive_digits_action()
                    ])
            except Exception as e:
                logger.error(f"Nova response error: {e}")
        
        # Fallback
        responses = [
            "I understand.",
            "Yes, that's correct.",
            "Thank you for that information.",
            "I see."
        ]
        import random
        text = random.choice(responses)
        audio_key = generate_polly_audio(text, transaction_id, f'turn{turn}')
        update_transcript(transaction_id, 'caller', text)
        
        return build_response([
            play_audio_action(audio_key),
            receive_digits_action()
        ])
    
    elif action_type == 'PlayAudio' or action_type == 'Speak':
        # Audio finished, listen for response
        return build_response([receive_digits_action()])
    
    return build_response([receive_digits_action()])


def handle_action_failed(event, transaction_id):
    """Handle failed action"""
    action_data = event.get('ActionData', {})
    error = action_data.get('Error', 'Unknown')
    logger.error(f"Action failed: {error}")
    
    update_transcript(transaction_id, 'system', f'Error: {error}')
    
    return build_response([hangup_action()])


def handle_hangup(event, transaction_id):
    """Handle call hangup"""
    update_status(transaction_id, 'completed')
    return build_response([])


# Nova Sonic Functions

async def generate_nova_sonic_greeting(persona: str, goal: str) -> bytes:
    """Generate AI greeting using Nova Sonic"""
    system_prompt = f"""You are {persona}, a real person making a phone call.
Your goal: {goal}

Say a brief, natural phone greeting (1 sentence). Sound like a real human caller.
Example: "Hi, I'm calling to check on my tax refund status."
"""
    
    return await nova_sonic_text_to_speech(system_prompt, "Generate a greeting for this call.")


async def generate_nova_sonic_response(persona: str, goal: str, transcript: list, turn: int) -> bytes:
    """Generate AI response using Nova Sonic"""
    transcript_text = ""
    if isinstance(transcript, list):
        for t in transcript[-6:]:  # Last 6 turns
            if isinstance(t, dict):
                transcript_text += f"{t.get('role', 'unknown')}: {t.get('text', '')}\n"
            else:
                transcript_text += f"{t}\n"
    
    system_prompt = f"""You are {persona}, a real person on a phone call.
Your goal: {goal}

Recent conversation:
{transcript_text}

Respond naturally as this caller would. Keep it SHORT (1 sentence).
If you achieved your goal or the call is ending, say goodbye.
"""
    
    return await nova_sonic_text_to_speech(system_prompt, f"Respond to what you just heard (turn {turn}).")


async def nova_sonic_text_to_speech(system_prompt: str, user_prompt: str) -> bytes:
    """Use Nova Sonic to generate speech from text prompt"""
    
    config = Config(
        endpoint_uri="https://bedrock-runtime.us-east-1.amazonaws.com",
        region="us-east-1",
        aws_credentials_identity_resolver=EnvironmentCredentialsResolver(),
    )
    
    client = BedrockRuntimeClient(config=config)
    stream = await client.invoke_model_with_bidirectional_stream(
        InvokeModelWithBidirectionalStreamOperationInput(
            model_id='amazon.nova-sonic-v1:0'
        )
    )
    
    prompt_name = f"p_{uuid.uuid4().hex[:8]}"
    
    async def send(data):
        chunk = InvokeModelWithBidirectionalStreamInputChunk(
            value=BidirectionalInputPayloadPart(bytes_=json.dumps(data).encode())
        )
        await stream.input_stream.send(chunk)
    
    # Session setup
    await send({"event": {"sessionStart": {"inferenceConfiguration": {"maxTokens": 256, "temperature": 0.8}}}})
    
    await send({"event": {"promptStart": {
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
    }}})
    
    # System prompt
    await send({"event": {"contentStart": {
        "promptName": prompt_name, "contentName": "sys",
        "type": "TEXT", "interactive": False, "role": "SYSTEM",
        "textInputConfiguration": {"mediaType": "text/plain"}
    }}})
    await send({"event": {"textInput": {"promptName": prompt_name, "contentName": "sys", "content": system_prompt}}})
    await send({"event": {"contentEnd": {"promptName": prompt_name, "contentName": "sys"}}})
    
    # User prompt (text, will trigger speech output)
    await send({"event": {"contentStart": {
        "promptName": prompt_name, "contentName": "user",
        "type": "TEXT", "interactive": True, "role": "USER",
        "textInputConfiguration": {"mediaType": "text/plain"}
    }}})
    await send({"event": {"textInput": {"promptName": prompt_name, "contentName": "user", "content": user_prompt}}})
    await send({"event": {"contentEnd": {"promptName": prompt_name, "contentName": "user"}}})
    
    # Receive audio response
    audio_chunks = []
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
                        if 'audioOutput' in evt:
                            audio_chunks.append(base64.b64decode(evt['audioOutput']['content']))
                            got_audio = True
                        elif 'contentEnd' in evt and got_audio:
                            break
            except asyncio.TimeoutError:
                if got_audio:
                    break
                continue
    except Exception as e:
        logger.error(f"Nova receive error: {e}")
    
    try:
        await send({"event": {"promptEnd": {"promptName": prompt_name}}})
        await send({"event": {"sessionEnd": {}}})
    except:
        pass
    
    audio_24k = b''.join(audio_chunks)
    
    # Resample 24kHz to 8kHz for PSTN
    return resample_24k_to_8k(audio_24k) if audio_24k else b''


# Audio utilities

def resample_24k_to_8k(audio_24k: bytes) -> bytes:
    """Resample 24kHz to 8kHz"""
    if not audio_24k:
        return b''
    samples = []
    for i in range(0, len(audio_24k) - 1, 2):
        samples.append(struct.unpack('<h', audio_24k[i:i+2])[0])
    # Take every 3rd sample
    resampled = samples[::3]
    return b''.join(struct.pack('<h', s) for s in resampled)


def generate_polly_audio(text: str, transaction_id: str, name: str) -> str:
    """Generate audio with Polly and upload to S3"""
    try:
        resp = polly.synthesize_speech(
            Text=text,
            OutputFormat='pcm',
            VoiceId='Ruth',
            SampleRate='8000',
            Engine='neural'
        )
        audio = resp['AudioStream'].read()
        return upload_audio_to_s3(audio, transaction_id, name)
    except Exception as e:
        logger.error(f"Polly error: {e}")
        return ""


def upload_audio_to_s3(audio: bytes, transaction_id: str, name: str) -> str:
    """Upload audio to S3 and return key"""
    key = f"calls/{transaction_id}/{name}.pcm"
    try:
        s3.put_object(Bucket=AUDIO_BUCKET, Key=key, Body=audio, ContentType='audio/pcm')
        logger.info(f"Uploaded audio: s3://{AUDIO_BUCKET}/{key}")
        return key
    except Exception as e:
        logger.error(f"S3 upload error: {e}")
        return ""


# DynamoDB helpers

def get_test_item(transaction_id: str) -> dict:
    try:
        table = dynamodb.Table('voice-test-scenarios')
        resp = table.get_item(Key={'test_id': transaction_id})
        return resp.get('Item', {})
    except:
        return {}


def update_status(transaction_id: str, status: str, extra: dict = None):
    try:
        table = dynamodb.Table('voice-test-scenarios')
        update_expr = 'SET #s = :s, updated_at = :u'
        expr_values = {':s': status, ':u': datetime.now(timezone.utc).isoformat()}
        expr_names = {'#s': 'status'}
        
        if extra:
            for k, v in extra.items():
                update_expr += f', {k} = :{k}'
                expr_values[f':{k}'] = v
        
        table.update_item(
            Key={'test_id': transaction_id},
            UpdateExpression=update_expr,
            ExpressionAttributeNames=expr_names,
            ExpressionAttributeValues=expr_values
        )
        logger.info(f"Updated {transaction_id} to {status}")
    except Exception as e:
        logger.error(f"DynamoDB update error: {e}")


def update_item(transaction_id: str, updates: dict):
    try:
        table = dynamodb.Table('voice-test-scenarios')
        update_expr = 'SET ' + ', '.join(f'{k} = :{k}' for k in updates.keys())
        expr_values = {f':{k}': v for k, v in updates.items()}
        table.update_item(
            Key={'test_id': transaction_id},
            UpdateExpression=update_expr,
            ExpressionAttributeValues=expr_values
        )
    except Exception as e:
        logger.error(f"Update error: {e}")


def update_transcript(transaction_id: str, role: str, text: str):
    try:
        item = get_test_item(transaction_id)
        transcript = item.get('transcript', [])
        if isinstance(transcript, str):
            transcript = [transcript] if transcript else []
        transcript.append({'role': role, 'text': text, 'time': datetime.now(timezone.utc).isoformat()})
        update_item(transaction_id, {'transcript': transcript})
    except Exception as e:
        logger.error(f"Transcript error: {e}")


# SIP Media App actions

def build_response(actions):
    return {"SchemaVersion": "1.0", "Actions": actions}


def play_audio_action(s3_key: str) -> dict:
    if not s3_key:
        return speak_action("I'm sorry, there was an error.")
    return {
        "Type": "PlayAudio",
        "Parameters": {
            "AudioSource": {
                "Type": "S3",
                "BucketName": AUDIO_BUCKET,
                "Key": s3_key
            }
        }
    }


def speak_action(text: str) -> dict:
    return {
        "Type": "Speak",
        "Parameters": {
            "Text": text,
            "Engine": "neural",
            "VoiceId": "Ruth"
        }
    }


def receive_digits_action() -> dict:
    return {
        "Type": "ReceiveDigits",
        "Parameters": {
            "InputDigitsRegex": ".*",
            "InBetweenDigitsDurationInMilliseconds": 3000,
            "FlushDigitsDurationInMilliseconds": 5000
        }
    }


def hangup_action() -> dict:
    return {"Type": "Hangup", "Parameters": {"SipResponseCode": "0"}}
