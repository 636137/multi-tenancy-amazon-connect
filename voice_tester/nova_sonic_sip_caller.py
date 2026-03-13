#!/usr/bin/env python3
"""
Nova Sonic SIP Caller - Makes outbound PSTN calls to Amazon Connect

Based on the aws-samples/sample-s2s-voip-gateway architecture.
Uses SIP/RTP to make real phone calls with Nova Sonic as the AI caller.

Architecture:
    ┌─────────────────────────────────────────────────────────────┐
    │                 Nova Sonic SIP Caller                        │
    │                                                              │
    │  ┌────────────┐      ┌────────────┐      ┌──────────────┐  │
    │  │ SIP Client │ ───► │ RTP Audio  │ ───► │ Nova Sonic   │  │
    │  │ (pjsip)    │ ◄─── │ Bridge     │ ◄─── │ Agent        │  │
    │  └────────────┘      └────────────┘      └──────────────┘  │
    │         │                                                    │
    │         ▼                                                    │
    │  ┌────────────────────────────────────┐                     │
    │  │ Amazon Connect IVR (PSTN)          │                     │
    │  │ - Answers call                     │                     │
    │  │ - Plays prompts                    │                     │
    │  │ - Nova Sonic listens & responds    │                     │
    │  └────────────────────────────────────┘                     │
    └─────────────────────────────────────────────────────────────┘

Flow:
1. SIP client dials Amazon Connect phone number
2. Connect answers and plays IVR welcome prompt
3. RTP audio (8kHz μ-law) received from Connect
4. Audio decoded to 16kHz PCM, sent to Nova Sonic
5. Nova Sonic understands prompt, generates response
6. Response audio (24kHz) downsampled to 8kHz, encoded as μ-law
7. RTP sent back to Connect
8. Nova Sonic navigates the IVR based on what it hears

Requirements:
- pjsip (Python SIP library)
- SIP account (Twilio, Vonage, or your own PBX)
- AWS credentials with Bedrock access
"""

import asyncio
import base64
import json
import os
import struct
import logging
import threading
import queue
import time
from dataclasses import dataclass, field
from typing import Optional, Dict, List, Callable
from datetime import datetime

import boto3

# Configure logging
logging.basicConfig(level=logging.INFO, format='%(asctime)s [%(levelname)s] %(name)s: %(message)s')
logger = logging.getLogger(__name__)

# Bridge boto3 credentials to Smithy SDK
session = boto3.Session()
creds = session.get_credentials()
os.environ['AWS_ACCESS_KEY_ID'] = creds.access_key
os.environ['AWS_SECRET_ACCESS_KEY'] = creds.secret_key
if creds.token:
    os.environ['AWS_SESSION_TOKEN'] = creds.token

from aws_sdk_bedrock_runtime.client import BedrockRuntimeClient, InvokeModelWithBidirectionalStreamOperationInput
from aws_sdk_bedrock_runtime.models import InvokeModelWithBidirectionalStreamInputChunk, BidirectionalInputPayloadPart
from aws_sdk_bedrock_runtime.config import Config
from smithy_aws_core.identity.environment import EnvironmentCredentialsResolver


# Audio constants
NOVA_INPUT_RATE = 16000   # Nova expects 16kHz PCM input
NOVA_OUTPUT_RATE = 24000  # Nova produces 24kHz PCM output
RTP_RATE = 8000           # Standard telephony is 8kHz


@dataclass
class CallerPersona:
    """Defines how the AI caller behaves."""
    name: str = "Jennifer"
    voice_id: str = "tiffany"  # Nova voices: tiffany, matthew, amy
    goal: str = "Complete the call"
    context: str = ""
    
    # Data to provide when asked
    ssn: str = ""
    phone: str = ""
    account_number: str = ""
    
    def system_prompt(self) -> str:
        """Generate the Nova Sonic system prompt."""
        data_section = ""
        if any([self.ssn, self.phone, self.account_number]):
            items = []
            if self.ssn:
                items.append(f"- Social Security Number: {self.ssn}")
            if self.phone:
                items.append(f"- Phone Number: {self.phone}")
            if self.account_number:
                items.append(f"- Account Number: {self.account_number}")
            data_section = f"\n\nIf asked, provide this information:\n" + "\n".join(items)

        return f"""You are {self.name}, a real person calling an automated phone system.

YOUR GOAL: {self.goal}
{f"SITUATION: {self.context}" if self.context else ""}

HOW TO BEHAVE:
1. LISTEN carefully to the automated system
2. Respond NATURALLY like a real human caller
3. For menu options, say the number clearly (e.g., "One" or "Press one")  
4. Keep responses SHORT - 1-3 words for menus, 1-2 sentences for questions
5. Be patient with the automated system
6. If you don't understand, ask to repeat
{data_section}

IMPORTANT: You are a CALLER reacting to what you HEAR from the phone system.
The system will speak first - wait and listen before responding."""


class AudioCodec:
    """Audio encoding/decoding utilities."""
    
    # μ-law encoding table
    ULAW_TABLE = [
        32124, 31100, 30076, 29052, 28028, 27004, 25980, 24956,
        23932, 22908, 21884, 20860, 19836, 18812, 17788, 16764,
        15996, 15484, 14972, 14460, 13948, 13436, 12924, 12412,
        11900, 11388, 10876, 10364, 9852, 9340, 8828, 8316,
        7932, 7676, 7420, 7164, 6908, 6652, 6396, 6140,
        5884, 5628, 5372, 5116, 4860, 4604, 4348, 4092,
        3900, 3772, 3644, 3516, 3388, 3260, 3132, 3004,
        2876, 2748, 2620, 2492, 2364, 2236, 2108, 1980,
        1884, 1820, 1756, 1692, 1628, 1564, 1500, 1436,
        1372, 1308, 1244, 1180, 1116, 1052, 988, 924,
        876, 844, 812, 780, 748, 716, 684, 652,
        620, 588, 556, 524, 492, 460, 428, 396,
        372, 356, 340, 324, 308, 292, 276, 260,
        244, 228, 212, 196, 180, 164, 148, 132,
        120, 112, 104, 96, 88, 80, 72, 64,
        56, 48, 40, 32, 24, 16, 8, 0
    ]
    
    @staticmethod
    def ulaw_to_pcm(ulaw_data: bytes) -> bytes:
        """Decode μ-law to 16-bit PCM."""
        pcm = []
        for byte in ulaw_data:
            byte = ~byte & 0xFF
            sign = byte & 0x80
            exponent = (byte >> 4) & 0x07
            mantissa = byte & 0x0F
            sample = AudioCodec.ULAW_TABLE[exponent * 16 + mantissa]
            if sign:
                sample = -sample
            pcm.append(struct.pack('<h', sample))
        return b''.join(pcm)
    
    @staticmethod
    def pcm_to_ulaw(pcm_data: bytes) -> bytes:
        """Encode 16-bit PCM to μ-law."""
        ulaw = []
        for i in range(0, len(pcm_data) - 1, 2):
            sample = struct.unpack('<h', pcm_data[i:i+2])[0]
            
            # Bias and clip
            sign = 0x80 if sample < 0 else 0
            if sample < 0:
                sample = -sample
            sample = min(sample + 132, 32767)
            
            # Find segment
            exponent = 7
            for exp in range(8):
                if sample < (1 << (exp + 8)):
                    exponent = exp
                    break
            
            mantissa = (sample >> (exponent + 3)) & 0x0F
            ulaw_byte = ~(sign | (exponent << 4) | mantissa) & 0xFF
            ulaw.append(ulaw_byte)
        
        return bytes(ulaw)
    
    @staticmethod
    def resample_8k_to_16k(audio_8k: bytes) -> bytes:
        """Upsample 8kHz to 16kHz (linear interpolation)."""
        samples = [struct.unpack('<h', audio_8k[i:i+2])[0] 
                   for i in range(0, len(audio_8k) - 1, 2)]
        
        resampled = []
        for i in range(len(samples)):
            resampled.append(samples[i])
            if i + 1 < len(samples):
                # Linear interpolation
                resampled.append((samples[i] + samples[i + 1]) // 2)
            else:
                resampled.append(samples[i])
        
        return b''.join(struct.pack('<h', s) for s in resampled)
    
    @staticmethod
    def resample_24k_to_8k(audio_24k: bytes) -> bytes:
        """Downsample 24kHz to 8kHz (take every 3rd sample)."""
        samples = [struct.unpack('<h', audio_24k[i:i+2])[0] 
                   for i in range(0, len(audio_24k) - 1, 2)]
        
        return b''.join(struct.pack('<h', samples[i]) 
                        for i in range(0, len(samples), 3))


class NovaSonicSession:
    """
    Bidirectional streaming session with Nova Sonic.
    
    Handles:
    - Sending audio input (from phone call)
    - Receiving audio output (to play back)
    - Managing conversation state
    """
    
    def __init__(self, persona: CallerPersona):
        self.persona = persona
        self.stream = None
        self.prompt_name = "p1"
        self.content_idx = 1
        self.connected = False
        
        # Audio queues
        self.input_queue = queue.Queue()   # Audio from phone → Nova
        self.output_queue = queue.Queue()  # Audio from Nova → phone
        
        # State
        self.is_receiving = False
        self.current_response_text = ""
        
    async def connect(self):
        """Establish connection to Nova Sonic."""
        config = Config(
            endpoint_uri="https://bedrock-runtime.us-east-1.amazonaws.com",
            region="us-east-1",
            aws_credentials_identity_resolver=EnvironmentCredentialsResolver(),
        )
        client = BedrockRuntimeClient(config=config)
        self.stream = await client.invoke_model_with_bidirectional_stream(
            InvokeModelWithBidirectionalStreamOperationInput(model_id='amazon.nova-sonic-v1:0')
        )
        self.connected = True
        logger.info(f"Nova Sonic connected (voice: {self.persona.voice_id})")
        
    async def _send(self, event: dict):
        """Send event to Nova Sonic."""
        await self.stream.input_stream.send(
            InvokeModelWithBidirectionalStreamInputChunk(
                value=BidirectionalInputPayloadPart(bytes_=json.dumps(event).encode())
            )
        )
        
    async def setup(self):
        """Initialize session with persona."""
        # Session start
        await self._send({"event": {"sessionStart": {
            "inferenceConfiguration": {
                "maxTokens": 1024,
                "topP": 0.9,
                "temperature": 0.7
            }
        }}})
        
        # Prompt start with audio output config
        await self._send({"event": {"promptStart": {
            "promptName": self.prompt_name,
            "textOutputConfiguration": {"mediaType": "text/plain"},
            "audioOutputConfiguration": {
                "mediaType": "audio/lpcm",
                "sampleRateHertz": NOVA_OUTPUT_RATE,
                "sampleSizeBits": 16,
                "channelCount": 1,
                "voiceId": self.persona.voice_id,
                "encoding": "base64",
                "audioType": "SPEECH"
            }
        }}})
        
        # System prompt
        await self._send({"event": {"contentStart": {
            "promptName": self.prompt_name,
            "contentName": "system",
            "type": "TEXT",
            "interactive": False,
            "role": "SYSTEM",
            "textInputConfiguration": {"mediaType": "text/plain"}
        }}})
        await self._send({"event": {"textInput": {
            "promptName": self.prompt_name,
            "contentName": "system",
            "content": self.persona.system_prompt()
        }}})
        await self._send({"event": {"contentEnd": {
            "promptName": self.prompt_name,
            "contentName": "system"
        }}})
        
        logger.info(f"Session ready - Persona: {self.persona.name}")
        
    async def start_audio_turn(self):
        """Start a new audio input turn."""
        content_name = f"audio{self.content_idx}"
        await self._send({"event": {"contentStart": {
            "promptName": self.prompt_name,
            "contentName": content_name,
            "type": "AUDIO",
            "interactive": True,
            "role": "USER",
            "audioInputConfiguration": {
                "mediaType": "audio/lpcm",
                "sampleRateHertz": NOVA_INPUT_RATE,
                "sampleSizeBits": 16,
                "channelCount": 1,
                "audioType": "SPEECH",
                "encoding": "base64"
            }
        }}})
        logger.debug(f"Started audio turn: {content_name}")
        
    async def send_audio_chunk(self, audio_16k: bytes):
        """Send audio chunk to Nova Sonic."""
        content_name = f"audio{self.content_idx}"
        await self._send({"event": {"audioInput": {
            "promptName": self.prompt_name,
            "contentName": content_name,
            "content": base64.b64encode(audio_16k).decode()
        }}})
        
    async def end_audio_turn(self):
        """End current audio turn and get response."""
        content_name = f"audio{self.content_idx}"
        await self._send({"event": {"contentEnd": {
            "promptName": self.prompt_name,
            "contentName": content_name
        }}})
        self.content_idx += 1
        
    async def receive_response(self, timeout: float = 15.0) -> tuple:
        """
        Receive Nova Sonic's audio response.
        
        Returns:
            (audio_24k_bytes, response_text)
        """
        audio_chunks = []
        text = ""
        start = asyncio.get_event_loop().time()
        got_audio = False
        silence_count = 0
        
        while True:
            if asyncio.get_event_loop().time() - start > timeout:
                break
                
            try:
                output = await asyncio.wait_for(self.stream.await_output(), timeout=0.5)
                result = await output[1].receive()
                
                if result.value and result.value.bytes_:
                    data = json.loads(result.value.bytes_.decode())
                    
                    if 'event' in data:
                        evt = data['event']
                        
                        if 'textOutput' in evt:
                            t = evt['textOutput'].get('content', '')
                            if evt['textOutput'].get('role') == 'ASSISTANT':
                                t = t.replace('{ "interrupted" : true }', '').strip()
                                if t:
                                    text += t
                                    
                        elif 'audioOutput' in evt:
                            chunk = base64.b64decode(evt['audioOutput']['content'])
                            audio_chunks.append(chunk)
                            got_audio = True
                            silence_count = 0
                            
                        elif 'contentEnd' in evt and got_audio:
                            break
                            
            except asyncio.TimeoutError:
                if got_audio:
                    silence_count += 1
                    if silence_count > 3:
                        break
                continue
                
        self.current_response_text = text
        return b''.join(audio_chunks), text
        
    async def close(self):
        """Clean up session."""
        try:
            await self._send({"event": {"promptEnd": {"promptName": self.prompt_name}}})
            await self._send({"event": {"sessionEnd": {}}})
        except:
            pass
        self.connected = False


class NovaSonicCaller:
    """
    Main class for making AI-powered phone calls.
    
    This simulates making a call where:
    1. We dial Amazon Connect
    2. Connect answers and plays IVR prompts
    3. Nova Sonic listens to the prompts
    4. Nova Sonic responds naturally
    """
    
    def __init__(self, persona: CallerPersona):
        self.persona = persona
        self.session: Optional[NovaSonicSession] = None
        self.codec = AudioCodec()
        
    async def process_call_audio(self, ivr_audio_8k_ulaw: bytes) -> bytes:
        """
        Process audio from phone call and get Nova's response.
        
        Args:
            ivr_audio_8k_ulaw: μ-law encoded audio from IVR at 8kHz
            
        Returns:
            μ-law encoded response audio at 8kHz
        """
        if not self.session or not self.session.connected:
            raise RuntimeError("Session not connected")
            
        # Decode μ-law to PCM
        ivr_audio_8k_pcm = self.codec.ulaw_to_pcm(ivr_audio_8k_ulaw)
        
        # Upsample 8kHz → 16kHz for Nova
        ivr_audio_16k = self.codec.resample_8k_to_16k(ivr_audio_8k_pcm)
        
        # Send to Nova Sonic
        await self.session.start_audio_turn()
        
        chunk_size = 640  # 20ms at 16kHz
        for i in range(0, len(ivr_audio_16k), chunk_size):
            await self.session.send_audio_chunk(ivr_audio_16k[i:i+chunk_size])
            await asyncio.sleep(0.02)
            
        # Send silence for VAD (2 seconds)
        silence = b'\x00' * chunk_size
        for _ in range(100):
            await self.session.send_audio_chunk(silence)
            await asyncio.sleep(0.02)
            
        await self.session.end_audio_turn()
        
        # Get response
        response_24k, response_text = await self.session.receive_response()
        
        if response_24k:
            logger.info(f"Nova response: {response_text}")
            
            # Downsample 24kHz → 8kHz
            response_8k = self.codec.resample_24k_to_8k(response_24k)
            
            # Encode to μ-law
            return self.codec.pcm_to_ulaw(response_8k)
            
        return b''
        
    async def connect(self):
        """Initialize Nova Sonic session."""
        self.session = NovaSonicSession(self.persona)
        await self.session.connect()
        await self.session.setup()
        
    async def close(self):
        """Clean up."""
        if self.session:
            await self.session.close()


async def demo_simulated_call():
    """
    Demonstrate the Nova Sonic caller with simulated IVR audio.
    
    In a real implementation, this would use pjsip or similar
    to make actual SIP/RTP calls.
    """
    print("\n" + "="*60)
    print("NOVA SONIC SIP CALLER - SIMULATION")
    print("="*60)
    
    persona = CallerPersona(
        name="Jennifer",
        voice_id="tiffany",
        goal="Check on my 2023 tax refund status",
        context="Filed return in February, been waiting 8 weeks",
        ssn="555-12-3456"
    )
    
    print(f"Persona: {persona.name}")
    print(f"Goal: {persona.goal}")
    print("="*60 + "\n")
    
    caller = NovaSonicCaller(persona)
    
    try:
        await caller.connect()
        print("✓ Nova Sonic session connected\n")
        
        # In a real call, IVR audio would come from RTP packets
        # For simulation, we'd need actual audio files
        print("To make real calls, integrate with:")
        print("  - pjsip for SIP/RTP handling")
        print("  - A SIP provider (Twilio, Vonage, your PBX)")
        print("  - Or deploy the Java sample-s2s-voip-gateway")
        print("\nThe Nova Sonic session is ready to process audio.")
        
    finally:
        await caller.close()
        print("\n✓ Session closed")


if __name__ == "__main__":
    asyncio.run(demo_simulated_call())
