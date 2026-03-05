# Nova Sonic AI-to-AI Voice Conversation Agent

## Agent Purpose
Expert AI assistant for deploying and customizing Nova Sonic bidirectional voice streaming applications. Specializes in AI-to-AI conversations, voice bots, and real-time audio processing using Amazon Bedrock.

---

## 🎯 What This Agent Does

This agent helps users:
1. **Deploy** Nova Sonic voice applications from scratch
2. **Customize** AI personas and conversation scenarios  
3. **Debug** audio streaming and connection issues
4. **Extend** the base implementation with new features

---

## 📋 Prerequisites Checklist

Before any Nova Sonic deployment, verify:

```python
# 1. Python Version (CRITICAL - must be 3.12+)
python3 --version  # Must be 3.12.0 or higher

# 2. AWS Credentials
aws sts get-caller-identity  # Must succeed

# 3. Bedrock Model Access
# User must enable amazon.nova-sonic-v1:0 in Bedrock console
```

### If Python < 3.12:
```bash
# macOS with pyenv (recommended)
brew install pyenv
pyenv install 3.12.8
pyenv local 3.12.8
python3.12 -m venv .venv312
source .venv312/bin/activate

# Or use system Python 3.12 if available
```

### Why Python 3.12+?
The AWS Smithy SDK (`aws-sdk-bedrock-runtime`) requires Python 3.12+ for bidirectional streaming. boto3 does NOT support bidirectional streaming - this is a hard requirement.

---

## 🔧 Core Technical Knowledge

### Audio Format Specifications

| Direction | Sample Rate | Bit Depth | Channels | Format |
|-----------|-------------|-----------|----------|--------|
| **Input** (to Nova) | 16,000 Hz | 16-bit | Mono | PCM, base64 |
| **Output** (from Nova) | 24,000 Hz | 16-bit | Mono | PCM, base64 |

### Available Voices

| Voice ID | Gender | Accent | Best For |
|----------|--------|--------|----------|
| `matthew` | Male | US English | Agent/Professional |
| `tiffany` | Female | US English | Customer/Caller |
| `amy` | Female | UK English | Alternative |

### Critical Discovery: VAD (Voice Activity Detection)

Nova Sonic uses VAD to detect when the user stops speaking. **YOU MUST send ~2 seconds of silence after speech** to trigger the AI response.

```python
# WRONG - Will hang forever
await send_audio(speech_audio)
await send_content_end()  # Nova never responds

# CORRECT - Add silence padding
await send_audio(speech_audio)
silence = b'\x00' * 640  # 20ms of silence
for _ in range(100):  # 2 seconds
    await send_audio(silence)
    await asyncio.sleep(0.02)
await send_content_end()  # Now Nova responds!
```

---

## 🏗️ Project Structure Template

```
nova-sonic-project/
├── .github/
│   └── copilot-instructions.md  # This file
├── .gitignore
├── README.md
├── requirements.txt
├── voice_tester/
│   ├── __init__.py
│   ├── nova_sonic_client.py     # Core client wrapper
│   ├── sonic_to_sonic.py        # AI-to-AI basic
│   ├── sonic_live_playback.py   # Full demo with recording
│   └── nova_sonic_live.py       # Live microphone mode
└── voice_output/                 # Generated audio files
    ├── customer.wav
    └── agent.wav
```

---

## 📦 Required Dependencies

```txt
# requirements.txt
boto3>=1.34.0
sounddevice>=0.4.6
numpy>=1.26.0

# Smithy SDK (requires Python 3.12+)
aws-sdk-bedrock-runtime>=0.4.0
```

### Installation Commands
```bash
# Create virtual environment with Python 3.12
python3.12 -m venv .venv312
source .venv312/bin/activate

# Install dependencies
pip install boto3 sounddevice numpy
pip install aws-sdk-bedrock-runtime
```

---

## 🔌 Connection Pattern

### AWS Credential Setup for Smithy SDK

The Smithy SDK requires credentials in environment variables (different from boto3):

```python
import os
import boto3

# Bridge boto3 credentials to Smithy SDK
session = boto3.Session()
creds = session.get_credentials()
os.environ['AWS_ACCESS_KEY_ID'] = creds.access_key
os.environ['AWS_SECRET_ACCESS_KEY'] = creds.secret_key
if creds.token:
    os.environ['AWS_SESSION_TOKEN'] = creds.token

# NOW import Smithy SDK
from aws_sdk_bedrock_runtime.client import BedrockRuntimeClient
from aws_sdk_bedrock_runtime.config import Config
from smithy_aws_core.identity.environment import EnvironmentCredentialsResolver
```

### Connection Establishment

```python
async def connect_to_nova_sonic(region: str = "us-east-1"):
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
    return stream
```

---

## 📨 Message Protocol

### Session Lifecycle

```
1. sessionStart
2. promptStart (with audio config)
3. contentStart (SYSTEM prompt, TEXT type)
4. textInput (system prompt content)
5. contentEnd
6. contentStart (USER audio, AUDIO type, interactive=True)
7. audioInput (chunks)... 
8. [silence padding]
9. contentEnd
10. [receive response]
11. promptEnd
12. sessionEnd
```

### Message Templates

#### Session Start
```python
{"event": {"sessionStart": {
    "inferenceConfiguration": {
        "maxTokens": 1024,
        "temperature": 0.8
    }
}}}
```

#### Prompt Start with Audio Config
```python
{"event": {"promptStart": {
    "promptName": "p1",
    "textOutputConfiguration": {"mediaType": "text/plain"},
    "audioOutputConfiguration": {
        "mediaType": "audio/lpcm",
        "sampleRateHertz": 24000,
        "sampleSizeBits": 16,
        "channelCount": 1,
        "voiceId": "matthew",  # or tiffany, amy
        "encoding": "base64",
        "audioType": "SPEECH"
    }
}}}
```

#### System Prompt
```python
# Start
{"event": {"contentStart": {
    "promptName": "p1",
    "contentName": "system",
    "type": "TEXT",
    "interactive": False,
    "role": "SYSTEM",
    "textInputConfiguration": {"mediaType": "text/plain"}
}}}

# Content
{"event": {"textInput": {
    "promptName": "p1",
    "contentName": "system",
    "content": "You are a helpful assistant..."
}}}

# End
{"event": {"contentEnd": {
    "promptName": "p1",
    "contentName": "system"
}}}
```

#### Audio Input
```python
# Start audio turn
{"event": {"contentStart": {
    "promptName": "p1",
    "contentName": "audio1",
    "type": "AUDIO",
    "interactive": True,
    "role": "USER",
    "audioInputConfiguration": {
        "mediaType": "audio/lpcm",
        "sampleRateHertz": 16000,
        "sampleSizeBits": 16,
        "channelCount": 1,
        "audioType": "SPEECH",
        "encoding": "base64"
    }
}}}

# Send audio chunks (20ms each = 640 bytes at 16kHz)
{"event": {"audioInput": {
    "promptName": "p1",
    "contentName": "audio1",
    "content": "<base64-encoded-pcm>"
}}}

# End audio turn
{"event": {"contentEnd": {
    "promptName": "p1",
    "contentName": "audio1"
}}}
```

---

## 🎭 AI-to-AI Conversation Pattern

### Architecture
```
┌─────────────────────┐         ┌─────────────────────┐
│  Customer Nova      │         │  Agent Nova         │
│  (Tiffany voice)    │ ──────► │  (Matthew voice)    │
│                     │ ◄────── │                     │
│  System: Customer   │         │  System: Agent      │
│  calling about...   │         │  helping with...    │
└─────────────────────┘         └─────────────────────┘
         │                               │
         │    Audio routed between       │
         │    (24kHz → 16kHz resample)   │
         └───────────────────────────────┘
```

### Resampling Function
```python
def resample_24k_to_16k(audio_24k: bytes) -> bytes:
    """Resample Nova's 24kHz output to 16kHz for input."""
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
```

### Bootstrap Requirement
Nova Sonic only responds to audio input - it won't start speaking from just a system prompt. Use Polly to generate the first line:

```python
import boto3

polly = boto3.client('polly', region_name='us-east-1')

def bootstrap_audio(text: str, voice: str = "Ruth") -> bytes:
    """Generate 16kHz PCM to bootstrap conversation."""
    resp = polly.synthesize_speech(
        Text=text,
        OutputFormat='pcm',
        VoiceId=voice,
        SampleRate='16000',
        Engine='neural'
    )
    return resp['AudioStream'].read()
```

---

## 🐛 Common Issues & Solutions

### Issue: "Timed out waiting for input events"
**Cause**: Not sending enough silence after speech
**Solution**: Send 2 seconds of silence (100 chunks of 640 bytes)

### Issue: "Received invalid voiceId"
**Cause**: Using wrong voice name
**Solution**: Only use `matthew`, `tiffany`, or `amy`

### Issue: Connection hangs after setup
**Cause**: Not setting `interactive: True` on audio content
**Solution**: Audio input must have `"interactive": True`

### Issue: Audio plays but sounds wrong
**Cause**: Sample rate mismatch
**Solution**: 
- Play Nova output at 24kHz
- Send input to Nova at 16kHz
- Resample when routing between instances

### Issue: ModuleNotFoundError for aws_sdk_bedrock_runtime
**Cause**: Wrong Python version or not installed
**Solution**:
```bash
python3 --version  # Must be 3.12+
pip install aws-sdk-bedrock-runtime
```

### Issue: Credentials not working with Smithy SDK
**Cause**: Smithy SDK reads from environment, not boto3
**Solution**: Bridge credentials as shown in Connection Pattern section

---

## 🚀 Deployment Workflow

### For New Users
```bash
# 1. Clone repository
git clone https://github.com/USER/nova-sonic-project.git
cd nova-sonic-project

# 2. Setup Python 3.12 environment
python3.12 -m venv .venv312
source .venv312/bin/activate

# 3. Install dependencies
pip install -r requirements.txt

# 4. Configure AWS (if not already)
aws configure

# 5. Enable Nova Sonic in Bedrock console
# https://console.aws.amazon.com/bedrock/

# 6. Run demo
python voice_tester/sonic_live_playback.py
```

### For Customization
1. Edit system prompts in the script
2. Change voices (matthew/tiffany/amy)
3. Modify conversation scenarios
4. Adjust turn count and flow

---

## 📝 Example System Prompts

### Customer Persona
```python
customer_prompt = """You are Sarah, a customer calling about a suspicious charge.

SITUATION: You noticed $47.99 from "STREAMTECH SERVICES" and don't recognize it.

BEHAVIOR:
- Speak naturally like a real phone caller
- Express mild concern about the charge
- Your name is Sarah Miller if asked
- Keep responses SHORT - 1-2 sentences maximum
- End call politely when resolved"""
```

### Agent Persona
```python
agent_prompt = """You are Alex, a customer service rep at ABC Bank.

ROLE:
- Greet warmly
- The $47.99 is their StreamTech Plus subscription (set up 3 months ago)
- Verify identity if needed (ask for name)
- Explain the charge clearly
- Offer to block merchant if they want to cancel
- Keep responses SHORT - 1-2 sentences
- Be warm and helpful"""
```

---

## 🔊 Audio Playback

```python
import sounddevice as sd
import numpy as np

def play_audio(audio_bytes: bytes, sample_rate: int = 24000):
    """Play PCM audio through speakers."""
    if not audio_bytes:
        return
    samples = np.frombuffer(audio_bytes, dtype=np.int16)
    samples = samples.astype(np.float32) / 32768.0
    sd.play(samples, samplerate=sample_rate, blocking=True)
```

---

## 💾 Save Audio to File

```python
import wave
import os

def save_wav(audio: bytes, filename: str, sample_rate: int = 24000):
    """Save PCM audio to WAV file."""
    os.makedirs(os.path.dirname(filename), exist_ok=True)
    with wave.open(filename, 'wb') as wf:
        wf.setnchannels(1)
        wf.setsampwidth(2)
        wf.setframerate(sample_rate)
        wf.writeframes(audio)
```

---

## ✅ Success Criteria

A successful Nova Sonic deployment includes:
- [ ] Python 3.12+ environment working
- [ ] AWS credentials configured
- [ ] Nova Sonic model enabled in Bedrock
- [ ] Smithy SDK installed (`aws-sdk-bedrock-runtime`)
- [ ] Connection established without timeout
- [ ] Audio received from Nova Sonic
- [ ] Playback working through speakers
- [ ] (Optional) AI-to-AI conversation running

---

## 🔗 References

- **Model ID**: `amazon.nova-sonic-v1:0`
- **Region**: us-east-1 (or your region with Bedrock)
- **AWS Bedrock Console**: https://console.aws.amazon.com/bedrock/
- **Smithy SDK**: https://pypi.org/project/aws-sdk-bedrock-runtime/

---

*This agent skill was created based on real implementation experience with Nova Sonic bidirectional streaming.*
