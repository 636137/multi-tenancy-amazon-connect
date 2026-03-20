# ElevenLabs Voice Synthesis Skill

Generate production-grade speech from text, manage voice models, optimize latency and quality, configure AI Agent voice personalities, and validate audio output.

## Quick Start

| Task | Command |
|------|---------|
| Synthesize speech (simple) | `python synthesize.py --text "Hello" --voice-id "21m00Tcm4TlvDq8ikWAM"` |
| With model selection | `python synthesize.py --text "..." --voice-id "..." --model "eleven_multilingual_v2"` |
| Streaming audio | `python synthesize.py --text "..." --voice-id "..." --stream true` |
| Batch synthesis | `python synthesize.py --input-file customers.json --voice-id "..." --output-dir ./audio` |

---

## Available Voice Models

| Model | Languages | Latency | Quality | UseCase |
|-------|-----------|---------|---------|---------|
| `eleven_monolingual_v1` | English only | ~300ms | Good | Legacy, cost-effective |
| `eleven_turbo_v2` | English | ~100ms | Excellent | Real-time, low latency |
| `eleven_monolingual_v2` | English | ~150ms | Excellent | High-quality English |
| `eleven_multilingual_v1` | 28+ languages | ~400ms | Good | Multi-language support |
| `eleven_multilingual_v2` | 28+ languages | ~200ms | Excellent | Recommended for global |

**Recommendation**: Use `eleven_turbo_v2` for Amazon Connect (lowest latency for IVR), `eleven_multilingual_v2` for multi-language support.

---

## Workflow 1: Simple Text-to-Speech

```python
import requests
import os

def synthesize_speech(
    text: str,
    voice_id: str,
    api_key: str = None,
    model: str = "eleven_turbo_v2",
    output_file: str = None
) -> bytes:
    """Synthesize speech from text using ElevenLabs API.
    
    Args:
        text: Input text to synthesize
        voice_id: ElevenLabs voice ID (e.g., "21m00Tcm4TlvDq8ikWAM")
        api_key: API key (uses env var if None)
        model: Speech model (default: turbo for lowest latency)
        output_file: Optional file to save audio
    
    Returns:
        Audio bytes (MP3 by default)
    """
    api_key = api_key or os.environ.get("ELEVENLABS_API_KEY")
    
    url = f"https://api.elevenlabs.io/v1/text-to-speech/{voice_id}"
    headers = {
        "xi-api-key": api_key,
        "Content-Type": "application/json"
    }
    
    payload = {
        "text": text,
        "model_id": model,
        "voice_settings": {
            "stability": 0.5,      # 0-1, lower = more variation
            "similarity_boost": 0.75  # 0-1, higher = closer to voice sample
        }
    }
    
    response = requests.post(url, json=payload, headers=headers)
    response.raise_for_status()
    
    audio_bytes = response.content
    
    # Save to file if requested
    if output_file:
        with open(output_file, "wb") as f:
            f.write(audio_bytes)
        print(f"✅ Audio saved: {output_file}")
    
    return audio_bytes

# Usage
audio = synthesize_speech(
    text="Welcome to customer service",
    voice_id="21m00Tcm4TlvDq8ikWAM",
    output_file="greeting.mp3"
)
```

---

## Workflow 2: Streaming Audio (for Lambda/Connect)

```python
def synthesize_speech_streaming(
    text: str,
    voice_id: str,
    api_key: str,
    model: str = "eleven_turbo_v2"
):
    """Stream audio chunks for real-time playback (optimized for WebRTC/Chime SDK)."""
    url = f"https://api.elevenlabs.io/v1/text-to-speech/{voice_id}/stream"
    headers = {
        "xi-api-key": api_key,
        "Content-Type": "application/json"
    }
    
    payload = {
        "text": text,
        "model_id": model,
        "voice_settings": {
            "stability": 0.5,
            "similarity_boost": 0.75
        }
    }
    
    # Stream response (yields chunks as they're generated)
    with requests.post(url, json=payload, headers=headers, stream=True) as r:
        r.raise_for_status()
        for chunk in r.iter_content(chunk_size=1024):
            if chunk:
                yield chunk  # Send to WebRTC, Chime, or buffer

# Usage in Lambda
def lambda_handler(event, context):
    text = event.get("text", "Hello")
    voice_id = event.get("voice_id")
    api_key = get_elevenlabs_key()  # From Secrets Manager
    
    # Stream audio back to client
    audio_chunks = synthesize_speech_streaming(text, voice_id, api_key)
    return {
        "statusCode": 200,
        "body": b"".join(audio_chunks),  # Or stream directly
        "headers": {"Content-Type": "audio/mpeg"}
    }
```

---

## Workflow 3: Batch Synthesis with Cost Tracking

```python
import json
from datetime import datetime

def batch_synthesize(
    input_file: str,  # JSON: [{"text": "...", "voice_id": "..."}, ...]
    output_dir: str,
    api_key: str
) -> dict:
    """Synthesize multiple texts, track costs and latencies."""
    
    with open(input_file) as f:
        items = json.load(f)
    
    results = []
    total_characters = 0
    total_latency_ms = 0
    
    for idx, item in enumerate(items):
        text = item["text"]
        voice_id = item.get("voice_id", "default_voice_id")
        
        start_time = datetime.now()
        
        try:
            audio = synthesize_speech(
                text=text,
                voice_id=voice_id,
                api_key=api_key,
                output_file=f"{output_dir}/audio_{idx:03d}.mp3"
            )
            
            elapsed_ms = (datetime.now() - start_time).total_seconds() * 1000
            total_characters += len(text)
            total_latency_ms += elapsed_ms
            
            results.append({
                "index": idx,
                "text": text[:50],  # Preview
                "size_bytes": len(audio),
                "latency_ms": round(elapsed_ms, 2),
                "status": "✅ Success"
            })
        
        except Exception as e:
            results.append({
                "index": idx,
                "text": text[:50],
                "status": f"❌ Error: {str(e)}"
            })
    
    # Cost calculation (Pro tier: $0.30 per 10k characters)
    cost_usd = (total_characters / 10000) * 0.30
    avg_latency_ms = total_latency_ms / len(results) if results else 0
    
    summary = {
        "total_items": len(items),
        "successful": sum(1 for r in results if "✅" in r["status"]),
        "failed": sum(1 for r in results if "❌" in r["status"]),
        "total_characters": total_characters,
        "estimated_cost_usd": round(cost_usd, 4),
        "avg_latency_ms": round(avg_latency_ms, 2),
        "results": results
    }
    
    return summary

# Usage
summary = batch_synthesize(
    input_file="texts.json",
    output_dir="./audio",
    api_key="your_api_key"
)
print(f"Cost: ${summary['estimated_cost_usd']}, Latency: {summary['avg_latency_ms']}ms")
```

---

## Workflow 4: Voice Cloning (Premium Feature)

```python
def add_voice(
    name: str,
    description: str,
    audio_file: str,
    api_key: str
) -> str:
    """Create a cloned voice from sample audio (requires Pro+ tier)."""
    
    url = "https://api.elevenlabs.io/v1/voices/add"
    headers = {"xi-api-key": api_key}
    
    with open(audio_file, "rb") as f:
        files = {
            "files": f,
            "name": (None, name),
            "description": (None, description)
        }
        response = requests.post(url, headers=headers, files=files)
    
    response.raise_for_status()
    voice_id = response.json()["voice_id"]
    print(f"✅ Voice cloned: {voice_id}")
    return voice_id

# Usage (sample audio must be > 1 minute, high quality)
cloned_voice_id = add_voice(
    name="Customer Service Agent",
    description="Professional, warm tone",
    audio_file="agent_sample.wav",
    api_key=api_key
)
```

---

## Integration with Amazon Connect Lambda

```python
# Lambda handler for Lex/Connect integration
import json
import os
from elevenlabs import ElevenLabsClient

def lambda_handler(event, context):
    """Synthesize speech from Lex or Connect intent."""
    
    # Extract text from Lex event
    text = event.get("inputTranscript", "")
    voice_id = os.environ.get("ELEVENLABS_VOICE_ID", "21m00Tcm4TlvDq8ikWAM")
    api_key = get_elevenlabs_key()  # From Secrets Manager
    
    # Synthesize
    audio_bytes = synthesize_speech(
        text=text,
        voice_id=voice_id,
        api_key=api_key,
        model="eleven_turbo_v2"  # Optimized for real-time
    )
    
    # Return as audio stream or S3 URL
    return {
        "statusCode": 200,
        "body": json.dumps({
            "audio_size": len(audio_bytes),
            "text_processed": text,
            "model": "eleven_turbo_v2"
        })
    }

# Env vars for Lambda
# ELEVENLABS_SECRET_NAME=elevenlabs-api
# ELEVENLABS_VOICE_ID=21m00Tcm4TlvDq8ikWAM
```

---

## Performance Tuning

### For Real-Time IVR (Amazon Connect)

Use `eleven_turbo_v2` with streaming:
- Target latency: < 200ms
- Stability: 0.5 (balanced natural variation)
- Similarity boost: 0.75 (consistent voice)

```python
"voice_settings": {
    "stability": 0.5,
    "similarity_boost": 0.75
}
```

### For Premium Quality (Agent Guides, Callbacks)

Use `eleven_multilingual_v2` for multi-language:
- Target latency: < 500ms acceptable
- Stability: 0.75 (more consistent)
- Similarity boost: 0.85 (very close to reference)

```python
"voice_settings": {
    "stability": 0.75,
    "similarity_boost": 0.85
}
```

---

## Workflow 5: AI Agent Voice Personality Tuning

### Voice Selection for Different Agent Personas

```python
AGENT_VOICE_PROFILES = {
    "customer_support": {
        "voice_id": "21m00Tcm4TlvDq8ikWAM",      # Amy (professional, friendly)
        "model": "eleven_turbo_v2",
        "settings": {
            "stability": 0.6,           # Balanced natural variation
            "similarity_boost": 0.75,   # Stay close to voice sample
            "response_style": "conversational"
        },
        "best_for": "IVR, customer support, general inquiries"
    },
    "empathetic_support": {
        "voice_id": "EXAVITQu4vr4xnSDxMaL",      # Grace (warm, caring)
        "model": "eleven_multilingual_v2",
        "settings": {
            "stability": 0.5,           # More variation, natural flow
            "similarity_boost": 0.70,   # Flexible, adaptive tone
            "response_style": "empathetic"
        },
        "best_for": "Healthcare, grievance handling, sensitive topics"
    },
    "authoritative_expert": {
        "voice_id": "onyx",                      # Onyx (formal, authoritative)
        "model": "eleven_turbo_v2",
        "settings": {
            "stability": 0.8,           # Consistent, professional
            "similarity_boost": 0.85,   # Strict adherence to voice
            "response_style": "formal"
        },
        "best_for": "Finance, legal, compliance, official communications"
    },
    "engaging_friendly": {
        "voice_id": "nPczCjzI2devNBz1zQrb",      # Sarah (bright, energetic)
        "model": "eleven_monolingual_v2",
        "settings": {
            "stability": 0.4,           # High variation, expressive
            "similarity_boost": 0.65,   # Allow interpretation
            "response_style": "enthusiastic"
        },
        "best_for": "Onboarding, promotions, friendly interactions"
    }
}

def configure_agent_voice_personality(
    agent_id: str,
    persona: str,  # "customer_support", "empathetic_support", etc.
    api_key: str
) -> dict:
    """Configure voice personality for AI Agent."""
    
    import requests
    
    profile = AGENT_VOICE_PROFILES.get(persona)
    if not profile:
        raise ValueError(f"Unknown persona: {persona}")
    
    url = f"https://api.elevenlabs.io/v1/agents/{agent_id}/voice"
    headers = {
        "xi-api-key": api_key,
        "Content-Type": "application/json"
    }
    
    payload = {
        "voice_id": profile["voice_id"],
        "tts_model": profile["model"],
        "voice_settings": profile["settings"],
        "personality": {
            "persona": persona,
            "speaking_style": profile["settings"]["response_style"],
            "speech_rate": 0.95,       # Slightly slower for clarity
            "pause_duration_ms": 500   # Natural pauses between phrases
        }
    }
    
    response = requests.post(url, json=payload, headers=headers)
    response.raise_for_status()
    
    print(f"✅ Agent voice personality configured")
    print(f"   Persona: {persona}")
    print(f"   Voice: {profile['voice_id']}")
    print(f"   Model: {profile['model']}")
    print(f"   Best for: {profile['best_for']}")
    
    return response.json()

# Usage
configure_agent_voice_personality(
    agent_id="agent_12345",
    persona="customer_support",
    api_key="your_key"
)
```

### Test Voice Personality with Sample Prompts

```python
def test_agent_voice_personality(
    text_samples: list,
    voice_id: str,
    api_key: str,
    save_dir: str = "./voice_samples"
) -> list:
    """Generate voice samples to validate personality fit."""
    
    import os
    os.makedirs(save_dir, exist_ok=True)
    
    samples = []
    
    for idx, text in enumerate(text_samples):
        # Synthesize each sample
        audio = synthesize_speech(
            text=text,
            voice_id=voice_id,
            api_key=api_key,
            output_file=f"{save_dir}/sample_{idx:02d}.mp3"
        )
        
        samples.append({
            "index": idx,
            "text": text,
            "file": f"sample_{idx:02d}.mp3",
            "size_bytes": len(audio)
        })
    
    print(f"✅ Generated {len(samples)} voice samples")
    print(f"   Location: {save_dir}")
    print("\n   Review samples to validate:")
    print("   - Tone matches agent persona")
    print("   - Pronunciation is clear")
    print("   - Pacing feels natural")
    print("   - No unexpected inflections")
    
    return samples

# Usage
sample_texts = [
    "Hello! I'm here to help with your refund status inquiry.",
    "I understand this is frustrating, and I'm committed to finding a solution.",
    "Let me connect you with a specialist who can assist further.",
    "Your account shows the refund processed on March 15th."
]

test_agent_voice_personality(
    text_samples=sample_texts,
    voice_id="21m00Tcm4TlvDq8ikWAM",
    api_key="your_key"
)
```

---



| Model | Cost/1M chars | Connect Call (500 chars) | Annual (1M calls) |
|-------|---------------|--------------------------|-------------------|
| Turbo v2 | $1.50 | $0.0008 | $770/month |
| Multilingual v2 | $3.00 | $0.0015 | $1,500/month |
| Monolingual v1 | $1.00 | $0.0005 | $500/month |

---

## QA Checklist

✅ Audio files generated without errors  
✅ Latency measured and acceptable (< 300ms for Connect)  
✅ Voice quality validated (play samples)  
✅ Cost per call calculated and budgeted  
✅ Error handling for API rate limits  
✅ Fallback voice configured if primary unavailable  
