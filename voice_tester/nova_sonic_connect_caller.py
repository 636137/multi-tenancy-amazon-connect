#!/usr/bin/env python3
"""
Nova Sonic AI Caller for Amazon Connect

An intelligent AI caller that uses Amazon Nova Sonic to make real phone calls
to Amazon Connect instances. The AI agent acts as a realistic human caller,
listening to IVR prompts and responding naturally based on its persona/goal.

NOT script-based or timing-driven - the AI reacts to what it actually hears.

Architecture:
    Nova Sonic (bidirectional) <---> Audio Bridge <---> Connect (PSTN/WebRTC)

Usage:
    # Define what kind of caller and what they want
    caller = NovaSonicConnectCaller(
        persona="Sarah, a 45-year-old concerned about IRS refund status",
        goal="Check on tax refund for 2023, SSN ends in 4532"
    )
    
    # Call Connect via PSTN
    result = await caller.call_pstn("+18332896602")  # Treasury line
    
    # Or via WebRTC (direct, no phone)
    result = await caller.call_webrtc(instance_id="...", flow_id="...")

Requirements:
    - Python 3.12+
    - pip install aws-sdk-bedrock-runtime boto3 sounddevice numpy websockets
    - AWS credentials with Bedrock, Connect, Chime access
    - Nova Sonic model enabled in Bedrock console
"""

import asyncio
import base64
import json
import logging
import os
import struct
import time
import uuid
import wave
from dataclasses import dataclass, field
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Callable, Dict, List, Optional, Tuple

import boto3

# Configure logging
logging.basicConfig(
    level=os.environ.get('LOG_LEVEL', 'INFO'),
    format='%(asctime)s [%(levelname)s] %(name)s: %(message)s'
)
logger = logging.getLogger(__name__)

# Import Smithy SDK (requires Python 3.12+)
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
    logger.warning("Smithy SDK not available - pip install aws-sdk-bedrock-runtime")


# Audio constants
INPUT_SAMPLE_RATE = 16000   # Nova Sonic expects 16kHz input
OUTPUT_SAMPLE_RATE = 24000  # Nova Sonic produces 24kHz output
PSTN_SAMPLE_RATE = 8000     # Standard telephony
CHUNK_SIZE_MS = 20          # 20ms chunks
INPUT_CHUNK_BYTES = int(INPUT_SAMPLE_RATE * 2 * CHUNK_SIZE_MS / 1000)  # 640 bytes
OUTPUT_CHUNK_BYTES = int(OUTPUT_SAMPLE_RATE * 2 * CHUNK_SIZE_MS / 1000)  # 960 bytes


@dataclass
class CallResult:
    """Result of a completed call"""
    call_id: str
    status: str  # 'completed', 'failed', 'timeout', 'hungup'
    started_at: datetime
    ended_at: Optional[datetime] = None
    duration_seconds: float = 0.0
    
    # Transcript of the conversation
    transcript: List[Dict[str, str]] = field(default_factory=list)  # [{"role": "ivr/caller", "text": "..."}]
    
    # Raw audio recordings
    ivr_audio: bytes = b""
    caller_audio: bytes = b""
    
    # Analysis
    goal_achieved: bool = False
    notes: str = ""
    errors: List[str] = field(default_factory=list)


@dataclass
class CallerPersona:
    """Defines who the AI caller is and what they want"""
    name: str = "Alex"
    age: int = 35
    background: str = "Professional calling about a service inquiry"
    speaking_style: str = "Polite, patient, conversational"
    
    # What this caller wants to achieve
    goal: str = "Complete the interaction successfully"
    context: str = ""  # Additional context (account info, reason for calling, etc.)
    
    # Behavior modifiers
    patience_level: str = "high"  # low, medium, high
    verbosity: str = "concise"  # terse, concise, verbose
    
    def to_system_prompt(self) -> str:
        """Generate Nova Sonic system prompt from persona"""
        return f"""You are {self.name}, a {self.age}-year-old person making a phone call.

BACKGROUND: {self.background}

GOAL FOR THIS CALL: {self.goal}

ADDITIONAL CONTEXT: {self.context}

SPEAKING STYLE:
- {self.speaking_style}
- Patience level: {self.patience_level}
- Verbosity: {self.verbosity}

CRITICAL BEHAVIOR RULES:
1. Speak like a real human on a phone call - natural, not robotic
2. Keep responses SHORT (1-2 sentences max unless asked for details)
3. Listen carefully to IVR prompts and respond appropriately
4. When asked to press a number, say the number clearly (e.g., "one" not "press 1")
5. When asked yes/no questions, respond naturally ("yes", "yeah", "no", "nope")
6. If confused, ask for clarification like a real person would
7. When the IVR says goodbye or thanks you, respond politely and prepare to hang up
8. Use natural filler words occasionally ("um", "uh", "let me think")
9. Stay in character throughout - you ARE this caller, not an AI

RESPONDING TO MENUS:
- When you hear "Press 1 for X, Press 2 for Y", say the number that matches your goal
- For DTMF prompts, speak the digits clearly and slowly
- If a menu doesn't match your goal, listen for "other options" or "speak to representative"

Remember: You're a real person calling. React naturally to what you hear."""


class NovaSonicSession:
    """
    Manages a Nova Sonic bidirectional streaming session.
    
    Handles connection, audio I/O, and conversation state.
    """
    
    VOICES = {
        "male": "matthew",
        "female": "tiffany",
        "female_uk": "amy"
    }
    
    def __init__(
        self,
        system_prompt: str,
        voice: str = "tiffany",
        region: str = "us-east-1",
        on_text_output: Optional[Callable[[str], None]] = None,
        on_audio_output: Optional[Callable[[bytes], None]] = None,
    ):
        self.system_prompt = system_prompt
        self.voice_id = self.VOICES.get(voice, voice)
        self.region = region
        
        # Callbacks
        self.on_text_output = on_text_output
        self.on_audio_output = on_audio_output
        
        # Session state
        self.stream = None
        self.client = None
        self.is_active = False
        self.prompt_name = "main"
        self.content_counter = 0
        
        # Accumulated responses
        self.current_text = ""
        self.response_audio_chunks: List[bytes] = []
        self.all_transcripts: List[str] = []
        self.all_audio: List[bytes] = []
        
        # Setup AWS credentials for Smithy SDK
        self._setup_credentials()
    
    def _setup_credentials(self):
        """Bridge boto3 credentials to environment for Smithy SDK"""
        session = boto3.Session()
        creds = session.get_credentials()
        if creds:
            frozen = creds.get_frozen_credentials()
            os.environ['AWS_ACCESS_KEY_ID'] = frozen.access_key
            os.environ['AWS_SECRET_ACCESS_KEY'] = frozen.secret_key
            if frozen.token:
                os.environ['AWS_SESSION_TOKEN'] = frozen.token
    
    async def _send(self, event_data: dict):
        """Send an event to Nova Sonic"""
        if not self.stream:
            raise RuntimeError("Session not started")
        
        chunk = InvokeModelWithBidirectionalStreamInputChunk(
            value=BidirectionalInputPayloadPart(
                bytes_=json.dumps(event_data).encode()
            )
        )
        await self.stream.input_stream.send(chunk)
    
    async def connect(self):
        """Establish connection to Nova Sonic"""
        if not SMITHY_AVAILABLE:
            raise RuntimeError("Smithy SDK not available - requires Python 3.12+")
        
        config = Config(
            endpoint_uri=f"https://bedrock-runtime.{self.region}.amazonaws.com",
            region=self.region,
            aws_credentials_identity_resolver=EnvironmentCredentialsResolver(),
        )
        
        self.client = BedrockRuntimeClient(config=config)
        self.stream = await self.client.invoke_model_with_bidirectional_stream(
            InvokeModelWithBidirectionalStreamOperationInput(
                model_id="amazon.nova-sonic-v1:0"
            )
        )
        self.is_active = True
        logger.info("Connected to Nova Sonic")
    
    async def setup_session(self):
        """Initialize session with system prompt and audio configuration"""
        # Session start
        await self._send({
            "event": {
                "sessionStart": {
                    "inferenceConfiguration": {
                        "maxTokens": 1024,
                        "temperature": 0.8,
                        "topP": 0.9
                    }
                }
            }
        })
        
        # Prompt start with output configuration
        await self._send({
            "event": {
                "promptStart": {
                    "promptName": self.prompt_name,
                    "textOutputConfiguration": {"mediaType": "text/plain"},
                    "audioOutputConfiguration": {
                        "mediaType": "audio/lpcm",
                        "sampleRateHertz": OUTPUT_SAMPLE_RATE,
                        "sampleSizeBits": 16,
                        "channelCount": 1,
                        "voiceId": self.voice_id,
                        "encoding": "base64",
                        "audioType": "SPEECH"
                    }
                }
            }
        })
        
        # System prompt
        await self._send({
            "event": {
                "contentStart": {
                    "promptName": self.prompt_name,
                    "contentName": "system",
                    "type": "TEXT",
                    "interactive": False,
                    "role": "SYSTEM",
                    "textInputConfiguration": {"mediaType": "text/plain"}
                }
            }
        })
        
        await self._send({
            "event": {
                "textInput": {
                    "promptName": self.prompt_name,
                    "contentName": "system",
                    "content": self.system_prompt
                }
            }
        })
        
        await self._send({
            "event": {
                "contentEnd": {
                    "promptName": self.prompt_name,
                    "contentName": "system"
                }
            }
        })
        
        logger.info(f"Session ready with voice: {self.voice_id}")
    
    async def send_audio_turn(self, audio_16k: bytes) -> Tuple[bytes, str]:
        """
        Send audio input and receive response.
        
        Args:
            audio_16k: PCM audio at 16kHz, 16-bit, mono
            
        Returns:
            Tuple of (response_audio_24k, response_text)
        """
        self.content_counter += 1
        content_name = f"audio_{self.content_counter}"
        
        # Start audio input
        await self._send({
            "event": {
                "contentStart": {
                    "promptName": self.prompt_name,
                    "contentName": content_name,
                    "type": "AUDIO",
                    "interactive": True,
                    "role": "USER",
                    "audioInputConfiguration": {
                        "mediaType": "audio/lpcm",
                        "sampleRateHertz": INPUT_SAMPLE_RATE,
                        "sampleSizeBits": 16,
                        "channelCount": 1,
                        "audioType": "SPEECH",
                        "encoding": "base64"
                    }
                }
            }
        })
        
        # Send audio in chunks (real-time pacing)
        chunk_size = INPUT_CHUNK_BYTES
        for i in range(0, len(audio_16k), chunk_size):
            chunk = audio_16k[i:i + chunk_size]
            await self._send({
                "event": {
                    "audioInput": {
                        "promptName": self.prompt_name,
                        "contentName": content_name,
                        "content": base64.b64encode(chunk).decode()
                    }
                }
            })
            await asyncio.sleep(CHUNK_SIZE_MS / 1000)
        
        # CRITICAL: Send silence for VAD (Voice Activity Detection)
        # Nova Sonic needs to detect end of speech
        silence = b'\x00' * chunk_size
        for _ in range(100):  # 2 seconds of silence
            await self._send({
                "event": {
                    "audioInput": {
                        "promptName": self.prompt_name,
                        "contentName": content_name,
                        "content": base64.b64encode(silence).decode()
                    }
                }
            })
            await asyncio.sleep(CHUNK_SIZE_MS / 1000)
        
        # End audio input
        await self._send({
            "event": {
                "contentEnd": {
                    "promptName": self.prompt_name,
                    "contentName": content_name
                }
            }
        })
        
        # Receive response
        return await self._receive_response()
    
    async def _receive_response(self, timeout: float = 30.0) -> Tuple[bytes, str]:
        """Receive audio and text response from Nova Sonic"""
        self.response_audio_chunks = []
        self.current_text = ""
        
        start_time = asyncio.get_event_loop().time()
        got_audio = False
        silence_count = 0
        
        while True:
            elapsed = asyncio.get_event_loop().time() - start_time
            if elapsed > timeout:
                logger.warning("Response timeout")
                break
            
            try:
                output = await asyncio.wait_for(
                    self.stream.await_output(),
                    timeout=0.5
                )
                result = await output[1].receive()
                
                if result.value and result.value.bytes_:
                    data = json.loads(result.value.bytes_.decode())
                    
                    if 'event' in data:
                        evt = data['event']
                        
                        # Text output
                        if 'textOutput' in evt:
                            text = evt['textOutput'].get('content', '')
                            role = evt['textOutput'].get('role', '')
                            if role == 'ASSISTANT':
                                # Clean up interrupted markers
                                text = text.replace('{ "interrupted" : true }', '').strip()
                                if text:
                                    self.current_text += text
                                    if self.on_text_output:
                                        self.on_text_output(text)
                        
                        # Audio output
                        elif 'audioOutput' in evt:
                            audio = base64.b64decode(evt['audioOutput']['content'])
                            self.response_audio_chunks.append(audio)
                            got_audio = True
                            silence_count = 0
                            if self.on_audio_output:
                                self.on_audio_output(audio)
                        
                        # Content end
                        elif 'contentEnd' in evt:
                            if got_audio:
                                break
                                
            except asyncio.TimeoutError:
                if got_audio:
                    silence_count += 1
                    if silence_count > 3:  # 1.5s silence after audio
                        break
                continue
            except Exception as e:
                if "closed" not in str(e).lower():
                    logger.error(f"Receive error: {e}")
                break
        
        # Accumulate results
        audio_out = b''.join(self.response_audio_chunks)
        if self.current_text:
            self.all_transcripts.append(self.current_text)
        if audio_out:
            self.all_audio.append(audio_out)
        
        return audio_out, self.current_text
    
    async def close(self):
        """Clean up session"""
        if self.stream:
            try:
                await self._send({"event": {"promptEnd": {"promptName": self.prompt_name}}})
                await self._send({"event": {"sessionEnd": {}}})
            except:
                pass
        self.is_active = False
        logger.info("Session closed")


class NovaSonicConnectCaller:
    """
    AI caller that uses Nova Sonic to call Amazon Connect instances.
    
    The AI listens to what the IVR says and responds naturally based on
    its persona and goal - NOT scripted timing.
    
    Supports:
    - PSTN calls via Chime SIP Media Application
    - WebRTC calls via Connect Participant Service
    """
    
    def __init__(
        self,
        persona: CallerPersona = None,
        voice: str = "female",
        region: str = "us-east-1",
    ):
        self.persona = persona or CallerPersona()
        self.voice = voice
        self.region = region
        
        # AWS clients
        self.polly = boto3.client('polly', region_name=region)
        self.chime = None  # Lazy init
        self.connect = None  # Lazy init
        
        # Nova Sonic session
        self.session: Optional[NovaSonicSession] = None
        
        # Call state
        self.call_id = ""
        self.transcript: List[Dict[str, str]] = []
        self.ivr_audio_buffer = bytearray()
        self.caller_audio_buffer = bytearray()
    
    def _init_chime(self):
        """Initialize Chime SDK client"""
        if not self.chime:
            self.chime = boto3.client('chime-sdk-voice', region_name=self.region)
    
    def _init_connect(self):
        """Initialize Connect client"""
        if not self.connect:
            self.connect = boto3.client('connect', region_name=self.region)
    
    async def call_pstn(
        self,
        phone_number: str,
        sip_media_app_id: str,
        from_phone: str = "+13602098836",
        timeout_seconds: int = 180,
        record_audio: bool = True,
    ) -> CallResult:
        """
        Make a PSTN call to Amazon Connect using Chime SIP Media Application.
        
        Args:
            phone_number: Connect DID to call (e.g., +18332896602)
            sip_media_app_id: Chime SIP Media Application ID
            from_phone: Caller ID phone number
            timeout_seconds: Maximum call duration
            record_audio: Whether to record audio
            
        Returns:
            CallResult with transcript and audio
        """
        self._init_chime()
        
        self.call_id = f"pstn-{datetime.now().strftime('%Y%m%d-%H%M%S')}-{uuid.uuid4().hex[:8]}"
        result = CallResult(
            call_id=self.call_id,
            status="initiating",
            started_at=datetime.now(timezone.utc)
        )
        
        logger.info(f"Starting PSTN call: {self.call_id}")
        logger.info(f"  From: {from_phone}")
        logger.info(f"  To: {phone_number}")
        logger.info(f"  Persona: {self.persona.name}")
        logger.info(f"  Goal: {self.persona.goal}")
        
        try:
            # Initialize Nova Sonic session
            await self._start_nova_session()
            
            # Make the call
            response = self.chime.create_sip_media_application_call(
                FromPhoneNumber=from_phone,
                ToPhoneNumber=phone_number,
                SipMediaApplicationId=sip_media_app_id,
                ArgumentsMap={
                    'call_id': self.call_id,
                    'mode': 'nova_sonic_caller',
                    'persona': self.persona.name,
                    'goal': self.persona.goal
                }
            )
            
            transaction_id = response.get('SipMediaApplicationCall', {}).get('TransactionId', '')
            logger.info(f"Call initiated, transaction: {transaction_id}")
            
            # Run the call (audio loop would be in Lambda for PSTN)
            # For PSTN, we need a Lambda to bridge audio
            result = await self._run_pstn_call(transaction_id, timeout_seconds)
            
        except Exception as e:
            result.status = "failed"
            result.errors.append(str(e))
            logger.error(f"Call failed: {e}")
        finally:
            if self.session:
                await self.session.close()
        
        result.ended_at = datetime.now(timezone.utc)
        result.duration_seconds = (result.ended_at - result.started_at).total_seconds()
        result.transcript = self.transcript
        result.ivr_audio = bytes(self.ivr_audio_buffer)
        result.caller_audio = bytes(self.caller_audio_buffer)
        
        return result
    
    async def call_webrtc(
        self,
        instance_id: str,
        contact_flow_id: str,
        timeout_seconds: int = 180,
        record_audio: bool = True,
    ) -> CallResult:
        """
        Make a WebRTC call directly to Amazon Connect.
        
        This bypasses PSTN entirely for lower latency and no phone costs.
        Uses Connect's StartWebRTCContact API.
        
        Args:
            instance_id: Connect instance ID
            contact_flow_id: Contact flow to invoke
            timeout_seconds: Maximum call duration
            record_audio: Whether to record audio
            
        Returns:
            CallResult with transcript and audio
        """
        self._init_connect()
        
        self.call_id = f"webrtc-{datetime.now().strftime('%Y%m%d-%H%M%S')}-{uuid.uuid4().hex[:8]}"
        result = CallResult(
            call_id=self.call_id,
            status="initiating",
            started_at=datetime.now(timezone.utc)
        )
        
        logger.info(f"Starting WebRTC call: {self.call_id}")
        logger.info(f"  Instance: {instance_id}")
        logger.info(f"  Flow: {contact_flow_id}")
        logger.info(f"  Persona: {self.persona.name}")
        logger.info(f"  Goal: {self.persona.goal}")
        
        try:
            # Initialize Nova Sonic session
            await self._start_nova_session()
            
            # Start WebRTC contact
            # Note: This requires Connect's WebRTC Contact APIs
            result = await self._run_webrtc_call(
                instance_id,
                contact_flow_id,
                timeout_seconds
            )
            
        except Exception as e:
            result.status = "failed"
            result.errors.append(str(e))
            logger.error(f"Call failed: {e}")
        finally:
            if self.session:
                await self.session.close()
        
        result.ended_at = datetime.now(timezone.utc)
        result.duration_seconds = (result.ended_at - result.started_at).total_seconds()
        result.transcript = self.transcript
        result.ivr_audio = bytes(self.ivr_audio_buffer)
        result.caller_audio = bytes(self.caller_audio_buffer)
        
        return result
    
    async def call_simulated(
        self,
        ivr_audio_source: Callable[[], bytes],
        audio_sink: Callable[[bytes], None],
        timeout_seconds: int = 180,
    ) -> CallResult:
        """
        Run a simulated call with provided audio source/sink.
        
        Useful for testing with recorded IVR audio or live audio devices.
        
        Args:
            ivr_audio_source: Function that returns IVR audio (16kHz PCM)
            audio_sink: Function that receives caller audio (24kHz PCM)
            timeout_seconds: Maximum duration
            
        Returns:
            CallResult with transcript
        """
        self.call_id = f"sim-{datetime.now().strftime('%Y%m%d-%H%M%S')}"
        result = CallResult(
            call_id=self.call_id,
            status="active",
            started_at=datetime.now(timezone.utc)
        )
        
        logger.info(f"Starting simulated call: {self.call_id}")
        
        try:
            await self._start_nova_session()
            
            # Bootstrap with initial greeting
            opening_audio = self._generate_bootstrap_audio(
                "Hello? Hi, I'm calling about... let me think..."
            )
            audio_sink(opening_audio)
            
            # Main conversation loop
            start_time = time.time()
            turn = 0
            
            while time.time() - start_time < timeout_seconds:
                turn += 1
                logger.info(f"\n--- Turn {turn} ---")
                
                # Get IVR audio
                ivr_audio = ivr_audio_source()
                if not ivr_audio:
                    logger.info("No IVR audio, ending call")
                    break
                
                self.ivr_audio_buffer.extend(ivr_audio)
                self.transcript.append({"role": "ivr", "text": "[audio received]"})
                
                # Send to Nova Sonic and get response
                caller_audio, caller_text = await self.session.send_audio_turn(ivr_audio)
                
                if caller_audio:
                    self.caller_audio_buffer.extend(caller_audio)
                    audio_sink(caller_audio)
                    logger.info(f"🗣️ Caller: {caller_text}")
                    self.transcript.append({"role": "caller", "text": caller_text})
                
                # Check for call end signals
                if self._should_end_call(caller_text):
                    logger.info("Call ending naturally")
                    break
            
            result.status = "completed"
            
        except Exception as e:
            result.status = "failed"
            result.errors.append(str(e))
            logger.error(f"Simulated call error: {e}")
        finally:
            if self.session:
                await self.session.close()
        
        result.ended_at = datetime.now(timezone.utc)
        result.duration_seconds = (result.ended_at - result.started_at).total_seconds()
        result.transcript = self.transcript
        result.ivr_audio = bytes(self.ivr_audio_buffer)
        result.caller_audio = bytes(self.caller_audio_buffer)
        
        return result
    
    async def _start_nova_session(self):
        """Initialize Nova Sonic with persona prompt"""
        self.session = NovaSonicSession(
            system_prompt=self.persona.to_system_prompt(),
            voice=self.voice,
            region=self.region,
            on_text_output=lambda t: logger.debug(f"Nova text: {t}"),
        )
        await self.session.connect()
        await self.session.setup_session()
    
    async def _run_pstn_call(
        self,
        transaction_id: str,
        timeout_seconds: int
    ) -> CallResult:
        """
        Run PSTN call conversation loop.
        
        Note: For real PSTN, audio bridging happens in Lambda.
        This method monitors call status and coordinates with Lambda.
        """
        result = CallResult(
            call_id=self.call_id,
            status="in_progress",
            started_at=datetime.now(timezone.utc)
        )
        
        # For PSTN calls, the Lambda handles audio bridging
        # We poll DynamoDB for status updates
        dynamodb = boto3.resource('dynamodb', region_name=self.region)
        
        try:
            table = dynamodb.Table('voice-test-scenarios')
            
            # Store our persona and session info for Lambda
            table.put_item(Item={
                'test_id': transaction_id,
                'call_id': self.call_id,
                'persona': self.persona.name,
                'goal': self.persona.goal,
                'system_prompt': self.persona.to_system_prompt(),
                'status': 'active',
                'transcript': json.dumps([]),
                'created_at': datetime.now(timezone.utc).isoformat()
            })
            
            # Wait for call completion
            start_time = time.time()
            while time.time() - start_time < timeout_seconds:
                await asyncio.sleep(2)
                
                response = table.get_item(Key={'test_id': transaction_id})
                item = response.get('Item', {})
                status = item.get('status', 'active')
                
                if status in ('completed', 'failed', 'hangup'):
                    result.status = status
                    transcript_json = item.get('transcript', '[]')
                    if isinstance(transcript_json, str):
                        result.transcript = json.loads(transcript_json)
                    break
                
                # Log progress
                elapsed = int(time.time() - start_time)
                if elapsed % 10 == 0:
                    logger.info(f"Call in progress... {elapsed}s")
            
            if result.status == "in_progress":
                result.status = "timeout"
                
        except Exception as e:
            result.errors.append(str(e))
            logger.error(f"PSTN call error: {e}")
        
        return result
    
    async def _run_webrtc_call(
        self,
        instance_id: str,
        contact_flow_id: str,
        timeout_seconds: int
    ) -> CallResult:
        """
        Run WebRTC call with direct audio streaming.
        
        Uses Connect's StartWebRTCContact API for voice channel.
        """
        result = CallResult(
            call_id=self.call_id,
            status="connecting",
            started_at=datetime.now(timezone.utc)
        )
        
        try:
            # Start WebRTC contact (voice channel)
            # Note: This requires specific Connect instance configuration
            contact_response = self.connect.start_web_rtc_contact(
                InstanceId=instance_id,
                ContactFlowId=contact_flow_id,
                ParticipantDetails={
                    'DisplayName': self.persona.name
                },
                AllowedCapabilities={
                    'Customer': {'Video': 'SEND'},
                    'Agent': {'Video': 'SEND'}
                },
                ClientToken=str(uuid.uuid4())
            )
            
            contact_id = contact_response['ContactId']
            connection_data = contact_response.get('ConnectionData', {})
            
            logger.info(f"WebRTC contact started: {contact_id}")
            
            # For WebRTC, we'd need to:
            # 1. Parse SDP from connection_data
            # 2. Establish WebRTC peer connection
            # 3. Stream audio bidirectionally
            # This requires a WebRTC library (aiortc or similar)
            
            # Placeholder - full WebRTC implementation needed
            result.status = "webrtc_not_implemented"
            result.errors.append("Full WebRTC implementation requires aiortc library")
            
        except self.connect.exceptions.ResourceNotFoundException:
            result.errors.append("Connect instance or flow not found")
        except Exception as e:
            result.errors.append(str(e))
            logger.error(f"WebRTC call error: {e}")
        
        return result
    
    def _generate_bootstrap_audio(self, text: str) -> bytes:
        """Generate initial audio using Polly to bootstrap Nova Sonic"""
        try:
            response = self.polly.synthesize_speech(
                Text=text,
                OutputFormat='pcm',
                VoiceId='Ruth' if self.voice == 'female' else 'Matthew',
                SampleRate=str(OUTPUT_SAMPLE_RATE),  # Match Nova output
                Engine='neural'
            )
            return response['AudioStream'].read()
        except Exception as e:
            logger.error(f"Polly error: {e}")
            return b'\x00' * 48000  # 1 second silence
    
    def _should_end_call(self, text: str) -> bool:
        """Detect if the conversation is ending naturally"""
        end_phrases = [
            "goodbye", "bye", "thank you for calling",
            "have a nice day", "is there anything else"
        ]
        text_lower = text.lower()
        return any(phrase in text_lower for phrase in end_phrases)


# Convenience functions for common scenarios

def create_irs_caller() -> NovaSonicConnectCaller:
    """Create an AI caller checking on IRS refund status"""
    persona = CallerPersona(
        name="Jennifer",
        age=42,
        background="Taxpayer checking on refund status for 2023 return",
        goal="Check on tax refund status - filed in February, SSN ends in 4532",
        context="Already have my Social Security number ready. Expecting about $2,400 refund.",
        speaking_style="Polite but slightly impatient, been waiting 6 weeks",
        patience_level="medium",
        verbosity="concise"
    )
    return NovaSonicConnectCaller(persona=persona, voice="female")


def create_census_participant() -> NovaSonicConnectCaller:
    """Create an AI caller participating in census survey"""
    persona = CallerPersona(
        name="Robert",
        age=55,
        background="Homeowner responding to census survey",
        goal="Complete the census survey - household of 3, English speaker, employed",
        context="Live in suburban home, wife and one adult child at home",
        speaking_style="Cooperative, clear speaker, takes surveys seriously",
        patience_level="high",
        verbosity="concise"
    )
    return NovaSonicConnectCaller(persona=persona, voice="male")


def create_treasury_caller() -> NovaSonicConnectCaller:
    """Create an AI caller for Treasury Department inquiry"""
    persona = CallerPersona(
        name="Maria",
        age=38,
        background="Small business owner with tax question",
        goal="Get information about quarterly estimated tax payments",
        context="Recently started freelancing, need to understand estimated payments",
        speaking_style="Professional, organized, takes notes",
        patience_level="high",
        verbosity="concise"
    )
    return NovaSonicConnectCaller(persona=persona, voice="female")


# Audio utility functions

def resample_24k_to_16k(audio_24k: bytes) -> bytes:
    """Resample 24kHz audio to 16kHz for Nova Sonic input"""
    samples = []
    for i in range(0, len(audio_24k) - 1, 2):
        samples.append(struct.unpack('<h', audio_24k[i:i+2])[0])
    
    # Take 2 of every 3 samples (24 → 16)
    resampled = []
    for i in range(0, len(samples), 3):
        resampled.append(samples[i])
        if i + 1 < len(samples):
            resampled.append(samples[i + 1])
    
    return b''.join(struct.pack('<h', s) for s in resampled)


def resample_8k_to_16k(audio_8k: bytes) -> bytes:
    """Resample 8kHz audio to 16kHz for Nova Sonic input"""
    samples = []
    for i in range(0, len(audio_8k) - 1, 2):
        samples.append(struct.unpack('<h', audio_8k[i:i+2])[0])
    
    # Duplicate each sample (8 → 16)
    resampled = []
    for s in samples:
        resampled.append(s)
        resampled.append(s)
    
    return b''.join(struct.pack('<h', s) for s in resampled)


def save_audio_wav(audio: bytes, filename: str, sample_rate: int = OUTPUT_SAMPLE_RATE):
    """Save PCM audio to WAV file"""
    path = Path(filename)
    path.parent.mkdir(parents=True, exist_ok=True)
    
    with wave.open(str(path), 'wb') as wf:
        wf.setnchannels(1)
        wf.setsampwidth(2)
        wf.setframerate(sample_rate)
        wf.writeframes(audio)
    
    logger.info(f"Saved: {path}")


# Main entry point for testing

async def main():
    """Example: Test call to Census survey"""
    
    print("=" * 60)
    print("Nova Sonic Connect Caller - Demo")
    print("=" * 60)
    
    # Create a census survey participant
    caller = create_census_participant()
    
    print(f"\n📞 Caller: {caller.persona.name}")
    print(f"🎯 Goal: {caller.persona.goal}")
    print(f"🎭 Background: {caller.persona.background}")
    
    # For demo, use simulated audio (you'd replace with real audio source)
    print("\n⚠️  Demo mode - using simulated audio source")
    print("For real calls, use call_pstn() or call_webrtc()")
    
    # Simulate IVR audio from a file or Polly
    polly = boto3.client('polly', region_name='us-east-1')
    
    ivr_prompts = [
        "Hello! Welcome to the Census Survey. I will ask you a few questions. Let's get started!",
        "Please tell me, how many people live in your household?",
        "What is the primary language spoken in your home?",
        "Thank you for completing the survey. Have a great day!"
    ]
    
    prompt_index = [0]  # Mutable for closure
    
    def get_ivr_audio() -> bytes:
        """Generate next IVR prompt"""
        if prompt_index[0] >= len(ivr_prompts):
            return b""
        
        text = ivr_prompts[prompt_index[0]]
        prompt_index[0] += 1
        print(f"\n🤖 IVR: {text}")
        
        response = polly.synthesize_speech(
            Text=text,
            OutputFormat='pcm',
            VoiceId='Joanna',
            SampleRate='16000',
            Engine='neural'
        )
        return response['AudioStream'].read()
    
    def handle_caller_audio(audio: bytes):
        """Handle caller's response audio"""
        # In real call, this would be sent to Connect
        pass
    
    # Run simulated call
    result = await caller.call_simulated(
        ivr_audio_source=get_ivr_audio,
        audio_sink=handle_caller_audio,
        timeout_seconds=60
    )
    
    # Print results
    print("\n" + "=" * 60)
    print("CALL RESULTS")
    print("=" * 60)
    print(f"Status: {result.status}")
    print(f"Duration: {result.duration_seconds:.1f}s")
    
    print("\n📜 TRANSCRIPT:")
    for entry in result.transcript:
        icon = "🤖" if entry["role"] == "ivr" else "🗣️"
        print(f"  {icon} {entry['role'].upper()}: {entry['text']}")
    
    # Save audio if any
    if result.caller_audio:
        save_audio_wav(result.caller_audio, "voice_output/demo_caller.wav")
    
    print("\n✅ Demo complete!")


if __name__ == "__main__":
    asyncio.run(main())
