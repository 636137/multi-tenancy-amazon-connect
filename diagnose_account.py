#!/usr/bin/env python3
"""Check what else is available in the upgraded account."""

import os
import requests
from dotenv import load_dotenv

load_dotenv()
api_key = os.environ.get("ELEVENLABS_API_KEY")

print("="*70)
print("ELEVENLABS ACCOUNT DIAGNOSTIC")
print("="*70)

base_url = "https://api.elevenlabs.io/v1"

# Test all common endpoints
endpoints = {
    "Account": "/user",
    "Voices": "/voices",
    "Models": "/models",
    "Workspaces": "/workspaces",
    "Projects": "/projects",
    "Invites": "/invites",
    "Usage": "/usage",
    "Voice Settings": "/voice_settings",
    "Professional Voice": "/professional-voice-lab",
    "Dubbing": "/dubbing",
    "Isolation": "/voice-isolation",
    "Sound Generation": "/sound-generation",
    "Text to Speech": "/text-to-speech",
    "Agent": "/agent",
    "Agents": "/agents",
    "Agents v2": "/agents/v2",
    "Conversational AI": "/conversational-ai",
}

print("\nEndpoint Status:\n")

for name, endpoint in endpoints.items():
    try:
        resp = requests.get(
            f"{base_url}{endpoint}",
            headers={"xi-api-key": api_key},
            timeout=5
        )
        
        status_icon = "✅" if resp.status_code < 400 else "❌"
        print(f"{status_icon} {name:25} {endpoint:30} → {resp.status_code}")
        
    except Exception as e:
        print(f"❌ {name:25} {endpoint:30} → ERROR")

print("\n" + "="*70)
print("Getting User Information...")
print("="*70)

try:
    resp = requests.get(
        f"{base_url}/user",
        headers={"xi-api-key": api_key},
        timeout=10
    )
    
    if resp.status_code == 200:
        user = resp.json()
        
        print(f"\nStatus: Active")
        print(f"Tier: {user.get('subscription', {}).get('tier')}")
        print(f"Character Limit: {user.get('subscription', {}).get('character_limit')}")
        print(f"Characters Used: {user.get('subscription', {}).get('character_count')}")
        
        print(f"\nAvailable Features:")
        features = user.get('features', [])
        if features:
            for feature in features:
                print(f"  ✅ {feature}")
        else:
            print("  (No features returned - may be pending activation)")
        
        # Also show other keys that might be in the response
        print(f"\nOther Account Info:")
        for key in user.keys():
            if key not in ['subscription', 'features', 'workspace_ids']:
                value = user[key]
                if isinstance(value, str) and len(str(value)) < 50:
                    print(f"  {key}: {value}")
        
except Exception as e:
    print(f"Error: {e}")

print("\n" + "="*70)
print("RECOMMENDATION")
print("="*70)

print("""
If agents endpoints still show 404:

1. WAIT: API activation can take 15-30 mins after account upgrade
   → Try again in 10-15 minutes

2. VERIFY: Check ElevenLabs dashboard 
   → Go to https://elevenlabs.io/account/agents
   → Verify agent feature shows as ENABLED
   → Wait if activation is still in progress

3. CONTACT SUPPORT:
   → If still not working after 30 mins
   → Visit https://help.elevenlabs.io
   → Report agent API endpoint returning 404

4. ALTERNATIVE - Access via Dashboard:
   → If API not ready, agents work in web UI
   → Create/test agents at https://elevenlabs.io/apps/agents
   → Use agents in contact flows manually
""")
