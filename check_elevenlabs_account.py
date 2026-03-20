#!/usr/bin/env python3
"""Check ElevenLabs account status and available features."""

import os
import sys
import json
import requests
from pathlib import Path

# Load API key
try:
    from dotenv import load_dotenv
    load_dotenv()
except:
    pass

API_KEY = os.environ.get("ELEVENLABS_API_KEY")
if not API_KEY:
    print("❌ ELEVENLABS_API_KEY not found")
    sys.exit(1)

print("🔍 Checking ElevenLabs Account...\n")

# Check user info
try:
    resp = requests.get(
        "https://api.elevenlabs.io/v1/user",
        headers={"xi-api-key": API_KEY},
        timeout=10
    )
    resp.raise_for_status()
    user = resp.json()
    
    print("✅ Account Information:")
    print(f"   Status: Active")
    print(f"   Tier: {user.get('subscription', {}).get('tier', 'unknown')}")
    print(f"   Character Limit: {user.get('character_limit', 'N/A')}")
    print(f"   Characters Used: {user.get('character_count', 'N/A')}")
    
    features = user.get('features', [])
    if features:
        print(f"\n✅ Available Features:")
        for feature in features:
            print(f"   - {feature}")
    
    # Check if agents are available
    if 'agents' in features or 'agents_v2' in features:
        print("\n✅ AI Agents are ENABLED")
    else:
        print("\n⚠️  AI Agents may not be enabled in your account")
        print("   To enable: https://elevenlabs.io/account/agents")
    
except requests.exceptions.HTTPError as e:
    print(f"❌ Account check failed: {e.response.status_code}")
    print(e.response.json())
except Exception as e:
    print(f"❌ Error: {str(e)}")

# Check available endpoints
print("\n" + "="*70)
print("🔍 Checking Available API Endpoints...\n")

endpoints = [
    ("/user", "Account"),
    ("/voices", "Voices"),
    ("/models", "TTS Models"),
    ("/projects", "Projects"),
    ("/agents", "Agents"),
    ("/agent", "Agent"),
]

for endpoint, label in endpoints:
    try:
        resp = requests.get(
            f"https://api.elevenlabs.io/v1{endpoint}",
            headers={"xi-api-key": API_KEY},
            timeout=5
        )
        status = "✅" if resp.status_code < 400 else f"❌ {resp.status_code}"
        print(f"   {status} {label:20} ({endpoint})")
    except:
        print(f"   ❌ {label:20} ({endpoint}) - Connection error")

# Check voices
print("\n" + "="*70)
print("🔍 Available Voices...\n")

try:
    resp = requests.get(
        "https://api.elevenlabs.io/v1/voices",
        headers={"xi-api-key": API_KEY},
        timeout=10
    )
    resp.raise_for_status()
    
    data = resp.json()
    voices = data.get("voices", [])
    
    if voices:
        print(f"✅ Found {len(voices)} voices:")
        for voice in voices[:5]:
            print(f"   - {voice.get('name', 'Unknown')} ({voice.get('voice_id', 'N/A')})")
        if len(voices) > 5:
            print(f"   ... and {len(voices)-5} more")
    else:
        print("❌ No voices found")
        
except Exception as e:
    print(f"❌ Failed to fetch voices: {str(e)}")

print("\n")
