#!/usr/bin/env python3
"""
Nova Sonic AI Agent for Amazon Connect IVR Testing

This agent:
1. Calls Amazon Connect via PSTN
2. LISTENS to IVR prompts (Connect speaks first)
3. Responds naturally using Nova Sonic voice
4. Navigates the IVR based on what it hears

NO Polly. NO Claude. Pure Nova Sonic.
"""

import asyncio
import base64
import json
import os
import struct
import wave
import logging
from datetime import datetime, timezone
from typing import Optional, List, Dict
from dataclasses import dataclass, field

import boto3

logging.basicConfig(level=logging.INFO, format='%(asctime)s %(levelname)s %(message)s')
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


NOVA_OUTPUT_RATE = 24000  # Nova produces 24kHz
NOVA_INPUT_RATE = 16000   # Nova expects 16kHz


@dataclass
class CallerPersona:
    """Defines AI caller behavior."""
    name: str = "Jennifer"
    voice_id: str = "tiffany"  # tiffany, matthew, amy
    goal: str = "Complete the call"
    context: str = ""
    ssn: str = "555-12-3456"
    
    def system_prompt(self) -> str:
        return f"""You are {self.name}, a real person who called an automated phone system.

YOUR GOAL: {self.goal}
{f"CONTEXT: {self.context}" if self.context else ""}

INFORMATION TO PROVIDE IF ASKED:
- SSN: {self.ssn}
- Name: {self.name}

HOW TO BEHAVE:
1. LISTEN to what the automated system says
2. Respond NATURALLY like a real human caller
3. For menu options, say the number (e.g., "One" or "Press one")
4. Keep responses SHORT (1-3 words for menus, 1-2 sentences for questions)
5. Be patient - automated systems are slow
6. Stay focused on your goal

REMEMBER: You are reacting to what you HEAR from the phone system."""


class NovaSonicAgent:
    """Nova Sonic bidirectional streaming agent."""
    
    def __init__(self, persona: CallerPersona):
        self.persona = persona
        self.stream = None
        self.prompt_name = "p1"
        self.content_idx = 1
        self.connected = False
        
    async def connect(self):
        """Connect to Nova Sonic."""
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
        await self.stream.input_stream.send(
            InvokeModelWithBidirectionalStreamInputChunk(
                value=BidirectionalInputPayloadPart(bytes_=json.dumps(event).encode())
            )
        )
        
    async def setup(self):
        """Initialize session with persona."""
        # Session
        await self._send({"event": {"sessionStart": {
            "inferenceConfiguration": {"maxTokens": 1024, "temperature": 0.7}
        }}})
        
        # Prompt with audio output
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
        
        logger.info(f"Session ready - {self.persona.name}")
        
    async def send_ivr_audio(self, audio_16k: bytes):
        """
        Send IVR audio to Nova Sonic and get response.
        
        Args:
            audio_16k: PCM audio from IVR at 16kHz
            
        Returns:
            (response_audio_24k, response_text)
        """
        content_name = f"audio{self.content_idx}"
        
        # Start audio input
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
        
        # Send audio in chunks
        chunk_size = 640  # 20ms at 16kHz
        for i in range(0, len(audio_16k), chunk_size):
            chunk = audio_16k[i:i+chunk_size]
            await self._send({"event": {"audioInput": {
                "promptName": self.prompt_name,
                "contentName": content_name,
                "content": base64.b64encode(chunk).decode()
            }}})
            await asyncio.sleep(0.02)
        
        # Silence for VAD (2 seconds)
        silence = b'\x00' * chunk_size
        for _ in range(100):
            await self._send({"event": {"audioInput": {
                "promptName": self.prompt_name,
                "contentName": content_name,
                "content": base64.b64encode(silence).decode()
            }}})
            await asyncio.sleep(0.02)
        
        # End audio input
        await self._send({"event": {"contentEnd": {
            "promptName": self.prompt_name,
            "contentName": content_name
        }}})
        self.content_idx += 1
        
        # Receive response
        return await self._receive_response()
        
    async def _receive_response(self, timeout: float = 15.0) -> tuple:
        """Receive Nova Sonic audio response."""
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
                            audio_chunks.append(base64.b64decode(evt['audioOutput']['content']))
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
                
        return b''.join(audio_chunks), text
        
    async def close(self):
        try:
            await self._send({"event": {"promptEnd": {"promptName": self.prompt_name}}})
            await self._send({"event": {"sessionEnd": {}}})
        except:
            pass


def resample_8k_to_16k(audio_8k: bytes) -> bytes:
    """Resample 8kHz (PSTN) to 16kHz (Nova input)."""
    samples = [struct.unpack('<h', audio_8k[i:i+2])[0] for i in range(0, len(audio_8k)-1, 2)]
    resampled = []
    for i in range(len(samples)):
        resampled.append(samples[i])
        if i + 1 < len(samples):
            resampled.append((samples[i] + samples[i + 1]) // 2)
        else:
            resampled.append(samples[i])
    return b''.join(struct.pack('<h', s) for s in resampled)


def resample_24k_to_8k(audio_24k: bytes) -> bytes:
    """Resample 24kHz (Nova output) to 8kHz (PSTN)."""
    samples = [struct.unpack('<h', audio_24k[i:i+2])[0] for i in range(0, len(audio_24k)-1, 2)]
    return b''.join(struct.pack('<h', samples[i]) for i in range(0, len(samples), 3))


def save_wav(audio: bytes, filename: str, rate: int):
    """Save audio to WAV file."""
    os.makedirs(os.path.dirname(filename) if os.path.dirname(filename) else '.', exist_ok=True)
    with wave.open(filename, 'wb') as w:
        w.setnchannels(1)
        w.setsampwidth(2)
        w.setframerate(rate)
        w.writeframes(audio)
    logger.info(f"Saved: {filename}")


async def test_with_simulated_ivr():
    """
    Test Nova Sonic agent with simulated IVR audio.
    
    Since we need IVR audio to test, we'll use pre-recorded prompts
    or generate simple test audio.
    """
    # Use a simple sine wave as test "IVR audio"
    import math
    
    print("\n" + "="*60)
    print("NOVA SONIC AGENT TEST")
    print("="*60)
    
    persona = CallerPersona(
        name="Jennifer",
        goal="Check on my 2023 tax refund status",
        context="Filed return in February",
        ssn="555-12-3456"
    )
    
    agent = NovaSonicAgent(persona)
    await agent.connect()
    await agent.setup()
    
    # Generate test audio: A simple tone that represents IVR speech
    # In reality, this would be actual audio from the phone call
    duration = 3  # seconds
    sample_rate = 16000
    frequency = 440  # Hz (A note)
    
    samples = []
    for i in range(duration * sample_rate):
        # Generate a simple tone (in real use, this is IVR audio)
        t = i / sample_rate
        sample = int(8000 * math.sin(2 * math.pi * frequency * t))
        samples.append(struct.pack('<h', sample))
    
    test_audio = b''.join(samples)
    
    print(f"\nSending {len(test_audio)} bytes of test audio to Nova Sonic...")
    print("(In real use, this would be IVR audio from Connect)")
    
    response_audio, response_text = await agent.send_ivr_audio(test_audio)
    
    print(f"\n{'='*60}")
    print("NOVA SONIC RESPONSE")
    print(f"{'='*60}")
    print(f"Text: {response_text}")
    print(f"Audio: {len(response_audio)} bytes ({len(response_audio)/48000:.1f}s at 24kHz)")
    
    if response_audio:
        save_wav(response_audio, "voice_output/nova_response.wav", NOVA_OUTPUT_RATE)
    
    await agent.close()
    print("\nDone!")


async def main():
    """
    Main entry point.
    
    For full PSTN integration, the Lambda handler will:
    1. Receive audio from Chime SIP Media App
    2. Send it to Nova Sonic agent
    3. Get response and play it back
    
    This test demonstrates the Nova Sonic agent working locally.
    """
    await test_with_simulated_ivr()


if __name__ == "__main__":
    asyncio.run(main())
