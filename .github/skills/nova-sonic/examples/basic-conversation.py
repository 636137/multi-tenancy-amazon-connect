"""
Example: Basic Nova Sonic Bidirectional Voice Conversation

Demonstrates the minimal setup for a Nova Sonic voice conversation.
Requires Python 3.12+ and aws-sdk-bedrock-runtime package.
"""

import asyncio
import base64
import json
from pathlib import Path

# Note: This uses the AWS Smithy SDK, not boto3
# pip install aws-sdk-bedrock-runtime
try:
    from amazon_bedrock_runtime import BedrockRuntime
except ImportError:
    print("Install: pip install aws-sdk-bedrock-runtime")
    print("Requires Python 3.12+")
    exit(1)


async def create_nova_sonic_session(
    system_prompt: str = "You are a helpful assistant.",
    voice_id: str = "matthew"
):
    """Create and configure a Nova Sonic bidirectional stream."""
    
    client = BedrockRuntime(region="us-east-1")
    
    # Start bidirectional stream
    stream = await client.start_async_invoke_model_with_bidirectional_stream(
        modelId="amazon.nova-sonic-v1:0"
    )
    
    # Session configuration
    session_config = {
        "event": {
            "sessionStart": {
                "inferenceConfiguration": {
                    "maxTokens": 1024,
                    "topP": 0.9,
                    "temperature": 0.7
                },
                "audioOutputConfiguration": {
                    "sampleRateHertz": 24000,
                    "voiceId": voice_id
                },
                "audioInputConfiguration": {
                    "sampleRateHertz": 16000,
                    "encoding": "pcm"
                }
            }
        }
    }
    await stream.send(session_config)
    
    # System prompt
    system_config = {
        "event": {
            "contentStart": {
                "promptName": "system",
                "contentName": "systemPrompt",
                "type": "TEXT",
                "interactive": False,
                "role": "SYSTEM"
            }
        }
    }
    await stream.send(system_config)
    
    system_content = {
        "event": {
            "textInput": {
                "promptName": "system",
                "contentName": "systemPrompt",
                "content": system_prompt
            }
        }
    }
    await stream.send(system_content)
    
    system_end = {
        "event": {
            "contentEnd": {
                "promptName": "system",
                "contentName": "systemPrompt"
            }
        }
    }
    await stream.send(system_end)
    
    return stream


async def send_audio_with_vad_padding(stream, audio_bytes: bytes):
    """
    Send audio to Nova Sonic with proper VAD silence padding.
    
    CRITICAL: Nova uses Voice Activity Detection (VAD) to know when
    the user stops speaking. You MUST send ~2 seconds of silence
    after the speech audio, or Nova will hang waiting for more input.
    """
    
    # Start audio content
    await stream.send({
        "event": {
            "contentStart": {
                "promptName": "input",
                "contentName": "userAudio",
                "type": "AUDIO",
                "interactive": True,
                "role": "USER"
            }
        }
    })
    
    # Send actual audio in chunks
    chunk_size = 640  # 20ms at 16kHz
    for i in range(0, len(audio_bytes), chunk_size):
        chunk = audio_bytes[i:i + chunk_size]
        await stream.send({
            "event": {
                "audioInput": {
                    "promptName": "input",
                    "contentName": "userAudio",
                    "content": base64.b64encode(chunk).decode()
                }
            }
        })
        await asyncio.sleep(0.02)  # Real-time pacing
    
    # CRITICAL: Send 2 seconds of silence for VAD
    silence = b'\x00' * chunk_size
    for _ in range(100):  # 100 * 20ms = 2 seconds
        await stream.send({
            "event": {
                "audioInput": {
                    "promptName": "input",
                    "contentName": "userAudio",
                    "content": base64.b64encode(silence).decode()
                }
            }
        })
        await asyncio.sleep(0.02)
    
    # End audio content
    await stream.send({
        "event": {
            "contentEnd": {
                "promptName": "input",
                "contentName": "userAudio"
            }
        }
    })


async def collect_response(stream) -> tuple[bytes, str]:
    """Collect audio and text response from Nova Sonic."""
    
    audio_chunks = []
    text_chunks = []
    
    async for response in stream:
        event = response.get("event", {})
        
        if "audioOutput" in event:
            audio_data = base64.b64decode(event["audioOutput"]["content"])
            audio_chunks.append(audio_data)
        
        if "textOutput" in event:
            text_chunks.append(event["textOutput"].get("content", ""))
        
        if "contentEnd" in event:
            if event["contentEnd"].get("type") == "AUDIO":
                break
    
    return b"".join(audio_chunks), "".join(text_chunks)


async def main():
    """Example: Send a greeting and get response."""
    
    print("🎤 Creating Nova Sonic session...")
    stream = await create_nova_sonic_session(
        system_prompt="You are a friendly customer service agent. Keep responses brief.",
        voice_id="matthew"
    )
    
    # For this example, we'll use synthesized audio
    # In real usage, this would be actual recorded audio
    print("📢 Sending audio input...")
    
    # Create simple test audio (silence with a beep pattern)
    # In production, use actual recorded audio
    sample_audio = b'\x00' * 32000  # 1 second of silence at 16kHz
    
    await send_audio_with_vad_padding(stream, sample_audio)
    
    print("🔊 Collecting response...")
    audio_response, text_response = await collect_response(stream)
    
    print(f"\n📝 Text: {text_response}")
    print(f"🎵 Audio: {len(audio_response)} bytes")
    
    # Save audio response
    output_path = Path("nova_response.pcm")
    output_path.write_bytes(audio_response)
    print(f"💾 Saved to: {output_path}")
    
    # Convert to playable format
    print("\n▶️  To play: ffplay -f s16le -ar 24000 -ac 1 nova_response.pcm")


if __name__ == "__main__":
    asyncio.run(main())
