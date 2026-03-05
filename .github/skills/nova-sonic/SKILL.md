---
name: nova-sonic
description: Deploy and customize Amazon Nova Sonic bidirectional voice streaming applications. Use for AI-to-AI conversations, voice bots, real-time audio processing, and debugging audio streaming issues with Amazon Bedrock.
argument-hint: "[action] [options]"
user-invocable: true
disable-model-invocation: false
---

# Nova Sonic Voice Application Skill

Expert guidance for deploying Nova Sonic bidirectional voice streaming. Handles AI-to-AI conversations, voice bots, and real-time audio processing using Amazon Bedrock.

## What This Skill Does

1. **Deploy** Nova Sonic voice applications from scratch
2. **Customize** AI personas and conversation scenarios
3. **Debug** audio streaming and connection issues
4. **Extend** the base implementation with new features

## Prerequisites Checklist

Before any Nova Sonic deployment, verify:

```python
# 1. Python Version (CRITICAL - must be 3.12+)
python3 --version  # Must be 3.12.0 or higher

# 2. AWS Credentials
aws sts get-caller-identity  # Must succeed

# 3. Bedrock Model Access
# User must enable amazon.nova-sonic-v1:0 in Bedrock console
```

### Why Python 3.12+?
The AWS Smithy SDK (`aws-sdk-bedrock-runtime`) requires Python 3.12+ for bidirectional streaming. boto3 does NOT support bidirectional streaming - this is a hard requirement.

### If Python < 3.12:
```bash
# macOS with pyenv (recommended)
brew install pyenv
pyenv install 3.12.8
pyenv local 3.12.8
python3.12 -m venv .venv312
source .venv312/bin/activate
```

## Core Technical Knowledge

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

### Critical: Voice Activity Detection (VAD)

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

## Required Dependencies

```txt
boto3>=1.34.0
sounddevice>=0.4.6
numpy>=1.26.0
aws-sdk-bedrock-runtime>=0.4.0  # Requires Python 3.12+
```

## Connection Pattern

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

## Message Protocol

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

See [examples/nova_session_template.py](./examples/nova_session_template.py) for complete message templates.

## AI-to-AI Conversation Pattern

```
┌─────────────────────┐         ┌─────────────────────┐
│  Customer Nova      │         │  Agent Nova         │
│  (Tiffany voice)    │ ──────► │  (Matthew voice)    │
│                     │ ◄────── │                     │
│  System: Customer   │         │  System: Agent      │
│  calling about...   │         │  helping with...    │
└─────────────────────┘         └─────────────────────┘
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

## Common Issues & Solutions

| Issue | Cause | Solution |
|-------|-------|----------|
| "Timed out waiting for input events" | Not sending enough silence | Send 2 seconds of silence (100 chunks of 640 bytes) |
| "Received invalid voiceId" | Wrong voice name | Only use `matthew`, `tiffany`, or `amy` |
| Connection hangs after setup | Missing `interactive: True` | Audio input must have `"interactive": True` |
| Audio sounds wrong | Sample rate mismatch | Play output at 24kHz, send input at 16kHz |
| ModuleNotFoundError | Wrong Python version | Must be Python 3.12+ |
| Credentials not working | Smithy SDK reads from env | Bridge credentials from boto3 to environment |

## Deployment Workflow

```bash
# 1. Setup Python 3.12 environment
python3.12 -m venv .venv312
source .venv312/bin/activate

# 2. Install dependencies
pip install boto3 sounddevice numpy aws-sdk-bedrock-runtime

# 3. Enable Nova Sonic in Bedrock console
# https://console.aws.amazon.com/bedrock/

# 4. Run demo
python voice_tester/sonic_live_playback.py
```

## Example System Prompts

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

## Success Criteria

A successful Nova Sonic deployment includes:
- [ ] Python 3.12+ environment working
- [ ] AWS credentials configured
- [ ] Nova Sonic model enabled in Bedrock
- [ ] Smithy SDK installed (`aws-sdk-bedrock-runtime`)
- [ ] Connection established without timeout
- [ ] Audio received from Nova Sonic
- [ ] Playback working through speakers
- [ ] (Optional) AI-to-AI conversation running

## References

- **Model ID**: `amazon.nova-sonic-v1:0`
- **Region**: us-east-1 (or your region with Bedrock)
- **AWS Bedrock Console**: https://console.aws.amazon.com/bedrock/
- **Smithy SDK**: https://pypi.org/project/aws-sdk-bedrock-runtime/
