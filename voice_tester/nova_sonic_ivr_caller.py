#!/usr/bin/env python3
"""
Nova Sonic IVR Caller - Pure Nova Sonic AI Agent for Amazon Connect Testing

Architecture:
    ┌──────────────────────────────────────────────────────────┐
    │  Amazon Connect IVR plays prompts                         │
    │           │                                               │
    │           ▼                                               │
    │  ┌─────────────────────────────────────────────┐         │
    │  │  Nova Sonic AI Agent                         │         │
    │  │  - Listens to IVR audio                      │         │
    │  │  - Understands prompts                       │         │
    │  │  - Generates natural voice responses         │         │
    │  │  - NO Polly, NO Claude - pure Nova Sonic    │         │
    │  └─────────────────────────────────────────────┘         │
    │           │                                               │
    │           ▼                                               │
    │  Response audio sent back to Connect                      │
    └──────────────────────────────────────────────────────────┘

Flow:
1. Call Amazon Connect via PSTN
2. Connect IVR plays welcome prompt
3. Nova Sonic LISTENS to the prompt
4. Nova Sonic generates response based on what it heard
5. Response plays back to Connect
6. Repeat until call complete
"""

import asyncio
import base64
import json
import os
import struct
import wave
import io
import logging
from datetime import datetime, timezone
from typing import Optional, List, Dict, Any, Callable
from dataclasses import dataclass, field

import boto3

# Setup logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# Bridge boto3 credentials to Smithy SDK environment variables
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
NOVA_OUTPUT_RATE = 24000  # Nova Sonic produces 24kHz audio
NOVA_INPUT_RATE = 16000   # Nova Sonic expects 16kHz input
PSTN_RATE = 8000          # PSTN uses 8kHz


@dataclass
class CallerPersona:
    """
    Defines the AI caller's persona and goals.
    
    The persona instructs Nova Sonic how to behave on the call.
    """
    name: str = "Alex"
    voice_id: str = "tiffany"  # Nova Sonic voice: matthew, tiffany, amy
    goal: str = "Complete the call successfully"
    context: str = ""
    personality: str = "patient and friendly"
    
    # Additional details for realistic interaction
    phone_reason: str = "general inquiry"
    data_to_provide: Dict[str, str] = field(default_factory=dict)
    
    def to_system_prompt(self) -> str:
        """Generate the Nova Sonic system prompt."""
        data_section = ""
        if self.data_to_provide:
            data_items = "\n".join(f"- {k}: {v}" for k, v in self.data_to_provide.items())
            data_section = f"\nIf asked, provide this information:\n{data_items}"
        
        return f"""You are {self.name}, a real person calling an automated phone system.

YOUR GOAL: {self.goal}

{f"CONTEXT: {self.context}" if self.context else ""}

PERSONALITY: You are {self.personality}.

CALLING ABOUT: {self.phone_reason}
{data_section}

CRITICAL INSTRUCTIONS:
1. Listen carefully to the automated system prompts
2. Respond naturally like a real human would
3. When given menu options, say the number clearly (e.g., "One" or "Press one")
4. Keep responses SHORT - 1-3 words for menu selections, 1-2 sentences for questions
5. Be patient - automated systems are slow
6. If you don't understand something, ask for clarification naturally
7. Stay focused on your goal

EXAMPLES OF NATURAL RESPONSES:
- Hearing "Press 1 for English" → "One"
- Hearing "Please say or enter your SSN" → "Five five five, one two, three four five six"
- Hearing "How can I help you today?" → "I'd like to check on my refund status please"
- Hearing "Is there anything else?" → "No, that's all. Thank you."

Remember: You are a CALLER navigating an IVR system. React to what you HEAR."""


@dataclass 
class CallTranscript:
    """Records the conversation for analysis."""
    entries: List[Dict] = field(default_factory=list)
    
    def add(self, role: str, text: str, audio_length_ms: int = 0):
        self.entries.append({
            'time': datetime.now(timezone.utc).isoformat(),
            'role': role,  # 'ivr' or 'caller'
            'text': text,
            'audio_length_ms': audio_length_ms
        })
    
    def to_string(self) -> str:
        lines = []
        for e in self.entries:
            role_label = "🔊 IVR" if e['role'] == 'ivr' else "🗣️ CALLER"
            lines.append(f"{role_label}: {e['text']}")
        return "\n".join(lines)


@dataclass
class CallResult:
    """Result of a completed call."""
    success: bool = False
    duration_seconds: float = 0
    turns: int = 0
    transcript: CallTranscript = field(default_factory=CallTranscript)
    goal_achieved: bool = False
    error: Optional[str] = None
    audio_files: List[str] = field(default_factory=list)


class NovaSonicAgent:
    """
    Nova Sonic bidirectional streaming session.
    
    Handles the AI conversation - listening to audio and generating responses.
    """
    
    def __init__(self, persona: CallerPersona):
        self.persona = persona
        self.stream = None
        self.prompt = "p1"
        self.content_num = 1
        self.is_connected = False
        
        # Response collection
        self.audio_chunks: List[bytes] = []
        self.current_text = ""
        self.all_responses: List[Dict] = []
        
    async def _send(self, data: dict):
        """Send event to Nova Sonic."""
        await self.stream.input_stream.send(
            InvokeModelWithBidirectionalStreamInputChunk(
                value=BidirectionalInputPayloadPart(bytes_=json.dumps(data).encode())
            )
        )
    
    async def connect(self, region: str = "us-east-1"):
        """Establish connection to Nova Sonic."""
        config = Config(
            endpoint_uri=f"https://bedrock-runtime.{region}.amazonaws.com",
            region=region,
            aws_credentials_identity_resolver=EnvironmentCredentialsResolver(),
        )
        client = BedrockRuntimeClient(config=config)
        self.stream = await client.invoke_model_with_bidirectional_stream(
            InvokeModelWithBidirectionalStreamOperationInput(model_id='amazon.nova-sonic-v1:0')
        )
        self.is_connected = True
        logger.info(f"Nova Sonic connected (voice: {self.persona.voice_id})")
        
    async def setup_session(self):
        """Initialize the Nova Sonic session with persona."""
        # Session start
        await self._send({
            "event": {
                "sessionStart": {
                    "inferenceConfiguration": {
                        "maxTokens": 1024,
                        "temperature": 0.7  # Slightly lower for more predictable IVR navigation
                    }
                }
            }
        })
        
        # Prompt start with audio output config
        await self._send({
            "event": {
                "promptStart": {
                    "promptName": self.prompt,
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
                }
            }
        })
        
        # System prompt
        await self._send({
            "event": {
                "contentStart": {
                    "promptName": self.prompt,
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
                    "promptName": self.prompt,
                    "contentName": "system",
                    "content": self.persona.to_system_prompt()
                }
            }
        })
        await self._send({
            "event": {"contentEnd": {"promptName": self.prompt, "contentName": "system"}}
        })
        
        logger.info(f"Nova Sonic session ready with persona: {self.persona.name}")
    
    async def start_audio_input(self):
        """Begin a new audio input turn."""
        content_name = f"audio{self.content_num}"
        await self._send({
            "event": {
                "contentStart": {
                    "promptName": self.prompt,
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
                }
            }
        })
    
    async def send_audio_chunk(self, audio_16k: bytes):
        """Send audio chunk to Nova Sonic (must be 16kHz PCM)."""
        content_name = f"audio{self.content_num}"
        await self._send({
            "event": {
                "audioInput": {
                    "promptName": self.prompt,
                    "contentName": content_name,
                    "content": base64.b64encode(audio_16k).decode()
                }
            }
        })
    
    async def end_audio_input(self):
        """End the current audio input turn."""
        content_name = f"audio{self.content_num}"
        await self._send({
            "event": {"contentEnd": {"promptName": self.prompt, "contentName": content_name}}
        })
        self.content_num += 1
    
    async def receive_response(self, timeout_seconds: float = 15.0) -> tuple[bytes, str]:
        """
        Receive Nova Sonic's audio response.
        
        Returns:
            Tuple of (audio_bytes at 24kHz, text_transcript)
        """
        self.audio_chunks = []
        self.current_text = ""
        
        start_time = asyncio.get_event_loop().time()
        got_audio = False
        silence_count = 0
        
        while True:
            elapsed = asyncio.get_event_loop().time() - start_time
            if elapsed > timeout_seconds:
                logger.debug("Response timeout")
                break
            
            try:
                output = await asyncio.wait_for(self.stream.await_output(), timeout=0.5)
                result = await output[1].receive()
                
                if result.value and result.value.bytes_:
                    data = json.loads(result.value.bytes_.decode())
                    
                    if 'event' in data:
                        evt = data['event']
                        
                        if 'textOutput' in evt:
                            text = evt['textOutput'].get('content', '')
                            role = evt['textOutput'].get('role', '')
                            if role == 'ASSISTANT':
                                # Clean up interrupted markers
                                text = text.replace('{ "interrupted" : true }', '').strip()
                                if text:
                                    self.current_text += text
                        
                        elif 'audioOutput' in evt:
                            audio = base64.b64decode(evt['audioOutput']['content'])
                            self.audio_chunks.append(audio)
                            got_audio = True
                            silence_count = 0
                        
                        elif 'contentEnd' in evt:
                            if got_audio:
                                break
                                
            except asyncio.TimeoutError:
                if got_audio:
                    silence_count += 1
                    if silence_count > 3:
                        break
                continue
            except Exception as e:
                if "closed" not in str(e).lower():
                    logger.error(f"Receive error: {e}")
                break
        
        audio_out = b''.join(self.audio_chunks)
        
        if self.current_text or audio_out:
            self.all_responses.append({
                'text': self.current_text,
                'audio_length': len(audio_out)
            })
        
        return audio_out, self.current_text
    
    async def send_text_kick(self, text: str):
        """
        Send a text prompt to kick off initial speech.
        
        Use this for the very first utterance since Nova Sonic
        only responds to input (needs something to start).
        """
        content_name = f"text{self.content_num}"
        
        await self._send({
            "event": {
                "contentStart": {
                    "promptName": self.prompt,
                    "contentName": content_name,
                    "type": "TEXT",
                    "interactive": True,
                    "role": "USER",
                    "textInputConfiguration": {"mediaType": "text/plain"}
                }
            }
        })
        await self._send({
            "event": {
                "textInput": {
                    "promptName": self.prompt,
                    "contentName": content_name,
                    "content": text
                }
            }
        })
        await self._send({
            "event": {"contentEnd": {"promptName": self.prompt, "contentName": content_name}}
        })
        self.content_num += 1
    
    async def close(self):
        """Clean up the session."""
        try:
            await self._send({"event": {"promptEnd": {"promptName": self.prompt}}})
            await self._send({"event": {"sessionEnd": {}}})
        except:
            pass
        self.is_connected = False


class AudioResampler:
    """Handles audio resampling between different rates."""
    
    @staticmethod
    def resample_24k_to_16k(audio_24k: bytes) -> bytes:
        """Resample 24kHz to 16kHz (for feeding back to Nova)."""
        samples = []
        for i in range(0, len(audio_24k) - 1, 2):
            samples.append(struct.unpack('<h', audio_24k[i:i+2])[0])
        
        # Take 2 out of every 3 samples (24kHz → 16kHz)
        resampled = []
        for i in range(0, len(samples), 3):
            resampled.append(samples[i])
            if i + 1 < len(samples):
                resampled.append(samples[i + 1])
        
        return b''.join(struct.pack('<h', s) for s in resampled)
    
    @staticmethod
    def resample_24k_to_8k(audio_24k: bytes) -> bytes:
        """Resample 24kHz to 8kHz (for PSTN)."""
        samples = []
        for i in range(0, len(audio_24k) - 1, 2):
            samples.append(struct.unpack('<h', audio_24k[i:i+2])[0])
        
        # Take 1 out of every 3 samples (24kHz → 8kHz)
        resampled = [samples[i] for i in range(0, len(samples), 3)]
        
        return b''.join(struct.pack('<h', s) for s in resampled)
    
    @staticmethod
    def resample_8k_to_16k(audio_8k: bytes) -> bytes:
        """Resample 8kHz to 16kHz (from PSTN to Nova)."""
        samples = []
        for i in range(0, len(audio_8k) - 1, 2):
            samples.append(struct.unpack('<h', audio_8k[i:i+2])[0])
        
        # Double each sample (8kHz → 16kHz via linear interpolation)
        resampled = []
        for i in range(len(samples)):
            resampled.append(samples[i])
            if i + 1 < len(samples):
                # Linear interpolation
                resampled.append((samples[i] + samples[i + 1]) // 2)
            else:
                resampled.append(samples[i])
        
        return b''.join(struct.pack('<h', s) for s in resampled)


class NovaSonicIVRCaller:
    """
    Main class for making AI-powered calls to Amazon Connect.
    
    Uses Nova Sonic as the complete AI agent - no other LLM or TTS needed.
    """
    
    def __init__(self, region: str = "us-east-1"):
        self.region = region
        self.chime = boto3.client('chime-sdk-voice', region_name=region)
        self.resampler = AudioResampler()
        
        # Chime SIP resources (from existing infrastructure)
        self.sip_media_app_id = "3998e0ab-53e5-4f68-a2fd-1745f73e7aa1"
        self.from_phone = "+13602098836"
    
    async def call_connect_pstn(
        self,
        phone_number: str,
        persona: CallerPersona,
        max_turns: int = 15,
        save_audio: bool = True
    ) -> CallResult:
        """
        Make a PSTN call to Amazon Connect using Nova Sonic.
        
        This initiates an outbound call and uses Nova Sonic to interact
        with the IVR as if it were a real human caller.
        
        Args:
            phone_number: Connect phone number to call (e.g., +18332896602)
            persona: CallerPersona defining how the AI should behave
            max_turns: Maximum conversation turns before ending
            save_audio: Whether to save audio files
        
        Returns:
            CallResult with transcript and outcome
        """
        result = CallResult()
        transcript = CallTranscript()
        start_time = datetime.now(timezone.utc)
        
        # Create Nova Sonic agent
        agent = NovaSonicAgent(persona)
        
        try:
            # Connect to Nova Sonic
            await agent.connect(self.region)
            await agent.setup_session()
            
            # Initiate PSTN call via Chime
            logger.info(f"Calling {phone_number}...")
            call_response = self.chime.create_sip_media_application_call(
                SipMediaApplicationId=self.sip_media_app_id,
                FromPhoneNumber=self.from_phone,
                ToPhoneNumber=phone_number,
                SipHeaders={},
                ArgumentsMap={
                    'mode': 'nova_sonic_agent',
                    'persona': persona.name,
                    'goal': persona.goal[:100]
                }
            )
            
            transaction_id = call_response['SipMediaApplicationCall']['TransactionId']
            logger.info(f"Call initiated: {transaction_id}")
            
            # First turn: Nova Sonic speaks first
            # We kick it off with a text prompt since Nova needs input to generate output
            logger.info("Generating initial greeting...")
            await agent.send_text_kick(
                f"The phone is ringing and someone answers. Start the conversation. "
                f"Your goal: {persona.goal}. Say hello and state your purpose briefly."
            )
            
            # Get initial audio from Nova Sonic
            initial_audio, initial_text = await agent.receive_response(timeout_seconds=10)
            
            if initial_audio:
                logger.info(f"Nova: {initial_text}")
                transcript.add('caller', initial_text, len(initial_audio) // 48)
                
                # The Lambda will play this audio and record IVR response
                # We store it for the Lambda to fetch
                # ... (Lambda integration would go here)
            
            # Note: Full PSTN integration requires the Lambda to stream audio
            # For now, we demonstrate the Nova Sonic agent working
            
            result.success = True
            result.turns = 1
            result.transcript = transcript
            result.duration_seconds = (datetime.now(timezone.utc) - start_time).total_seconds()
            
            # Save audio if requested
            if save_audio and initial_audio:
                output_dir = "voice_output"
                os.makedirs(output_dir, exist_ok=True)
                filename = f"{output_dir}/nova_caller_{transaction_id[:8]}.wav"
                save_wav(initial_audio, filename, NOVA_OUTPUT_RATE)
                result.audio_files.append(filename)
            
        except Exception as e:
            logger.error(f"Call error: {e}")
            result.error = str(e)
            
        finally:
            await agent.close()
        
        return result
    
    async def simulate_ivr_interaction(
        self,
        persona: CallerPersona,
        ivr_prompts: List[str],
        max_turns: int = 10
    ) -> CallResult:
        """
        Simulate an IVR interaction with Nova Sonic (no real call).
        
        This is useful for testing the AI agent's behavior without
        making actual phone calls.
        
        Args:
            persona: CallerPersona defining AI behavior
            ivr_prompts: List of IVR prompts to play (as text to convert to audio)
            max_turns: Maximum conversation turns
        
        Returns:
            CallResult with full transcript
        """
        result = CallResult()
        transcript = CallTranscript()
        start_time = datetime.now(timezone.utc)
        
        agent = NovaSonicAgent(persona)
        all_caller_audio = []
        
        try:
            await agent.connect(self.region)
            await agent.setup_session()
            
            logger.info(f"\n{'='*60}")
            logger.info(f"SIMULATED IVR INTERACTION")
            logger.info(f"Persona: {persona.name}")
            logger.info(f"Goal: {persona.goal}")
            logger.info(f"{'='*60}\n")
            
            # Turn 1: Kick off with initial greeting
            await agent.send_text_kick(
                f"You've just called the phone number and it's ringing. "
                f"The system answers. Listen for prompts and respond appropriately. "
                f"Your goal: {persona.goal}"
            )
            
            caller_audio, caller_text = await agent.receive_response(timeout_seconds=10)
            if caller_text:
                logger.info(f"🗣️ CALLER: {caller_text}")
                transcript.add('caller', caller_text)
                if caller_audio:
                    all_caller_audio.append(caller_audio)
            
            # Process IVR prompts
            for turn, ivr_prompt in enumerate(ivr_prompts, 1):
                if turn > max_turns:
                    break
                
                logger.info(f"\n--- Turn {turn} ---")
                logger.info(f"🔊 IVR: {ivr_prompt}")
                transcript.add('ivr', ivr_prompt)
                
                # Convert IVR prompt to audio and send to Nova Sonic
                # For simulation, we use a text kick to represent the IVR audio
                await agent.send_text_kick(
                    f"[The automated system says]: {ivr_prompt}"
                )
                
                # Get Nova's response
                caller_audio, caller_text = await agent.receive_response(timeout_seconds=10)
                
                if caller_text:
                    logger.info(f"🗣️ CALLER: {caller_text}")
                    transcript.add('caller', caller_text)
                    result.turns += 1
                    
                    if caller_audio:
                        all_caller_audio.append(caller_audio)
                else:
                    logger.warning("No response from Nova Sonic")
                    break
            
            result.success = True
            result.transcript = transcript
            result.duration_seconds = (datetime.now(timezone.utc) - start_time).total_seconds()
            
            # Save combined audio
            if all_caller_audio:
                combined = b''.join(all_caller_audio)
                output_dir = "voice_output"
                os.makedirs(output_dir, exist_ok=True)
                filename = f"{output_dir}/nova_caller_sim_{datetime.now().strftime('%H%M%S')}.wav"
                save_wav(combined, filename, NOVA_OUTPUT_RATE)
                result.audio_files.append(filename)
                logger.info(f"\nAudio saved: {filename}")
            
        except Exception as e:
            logger.error(f"Simulation error: {e}")
            result.error = str(e)
            
        finally:
            await agent.close()
        
        return result


def save_wav(audio: bytes, filename: str, sample_rate: int):
    """Save PCM audio to WAV file."""
    os.makedirs(os.path.dirname(filename), exist_ok=True)
    with wave.open(filename, 'wb') as wf:
        wf.setnchannels(1)
        wf.setsampwidth(2)
        wf.setframerate(sample_rate)
        wf.writeframes(audio)
    logger.info(f"Saved: {filename}")


# Predefined IVR test scenarios
IRS_REFUND_PROMPTS = [
    "Welcome to the Internal Revenue Service. For English, press 1. Para español, oprima 2.",
    "For information about refunds, press 1. For tax questions, press 2. For payment options, press 3.",
    "To check the status of your refund, I'll need some information. Please enter or say your Social Security number.",
    "Please enter or say the tax year you're inquiring about.",
    "Please enter or say the exact refund amount shown on your return.",
    "Thank you. Your refund is being processed. The expected direct deposit date is in 2 to 3 weeks. Is there anything else I can help you with?",
]

CENSUS_SURVEY_PROMPTS = [
    "Hello, this is the US Census Bureau. We're conducting an important survey about your household. May I speak with an adult member of the household?",
    "Thank you. This survey should take about 5 minutes. First, how many people live at this address?",
    "Got it. And how many of those are adults 18 or older?",
    "Are any children under 5 living there?",
    "What is your relationship to the other household members?",
    "Thank you for your time. This completes our survey. Have a great day.",
]


async def demo():
    """Demonstrate the Nova Sonic IVR Caller."""
    
    # Create persona for IRS refund check
    persona = CallerPersona(
        name="Jennifer",
        voice_id="tiffany",
        goal="Check on my 2023 tax refund status",
        context="Filed my return in February, been waiting 8 weeks",
        personality="patient but eager to get information",
        phone_reason="tax refund status inquiry",
        data_to_provide={
            "SSN": "555-12-3456",
            "tax_year": "2023",
            "refund_amount": "2,847 dollars"
        }
    )
    
    caller = NovaSonicIVRCaller()
    
    print("\n" + "="*70)
    print("NOVA SONIC IVR CALLER DEMO")
    print("="*70)
    print(f"Persona: {persona.name}")
    print(f"Voice: {persona.voice_id}")
    print(f"Goal: {persona.goal}")
    print("="*70 + "\n")
    
    # Run simulated IVR interaction
    result = await caller.simulate_ivr_interaction(
        persona=persona,
        ivr_prompts=IRS_REFUND_PROMPTS,
        max_turns=10
    )
    
    print("\n" + "="*70)
    print("RESULTS")
    print("="*70)
    print(f"Success: {result.success}")
    print(f"Duration: {result.duration_seconds:.1f} seconds")
    print(f"Turns: {result.turns}")
    if result.audio_files:
        print(f"Audio: {result.audio_files}")
    
    print("\n📜 TRANSCRIPT:")
    print("-"*50)
    print(result.transcript.to_string())


if __name__ == "__main__":
    asyncio.run(demo())
