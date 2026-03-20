#!/usr/bin/env python3
"""Quick test of agents endpoint with more detail."""

import os
import requests
from dotenv import load_dotenv

load_dotenv()
api_key = os.environ.get("ELEVENLABS_API_KEY")

print("Testing ElevenLabs Agents API...\n")

# Try different endpoint variations
endpoints = [
    "/agents",
    "/agent",
    "/conversational_ai/agents",
    "/agents/list",
]

base_url = "https://api.elevenlabs.io/v1"

for endpoint in endpoints:
    url = f"{base_url}{endpoint}"
    try:
        resp = requests.get(
            url,
            headers={"xi-api-key": api_key},
            timeout=5
        )
        print(f"{endpoint:40} → {resp.status_code}")
        if resp.status_code < 400:
            data = resp.json()
            print(f"   Data: {str(data)[:100]}")
        elif resp.status_code == 404:
            print(f"   Not Found")
        elif resp.status_code == 403:
            print(f"   Forbidden (may need special permission)")
        else:
            try:
                print(f"   Error: {resp.json()}")
            except:
                print(f"   Error: {resp.text[:100]}")
    except Exception as e:
        print(f"{endpoint:40} → Error: {str(e)[:50]}")

print("\n" + "="*70)
print("Trying to LIST existing agents...\n")

# Try to list agents
try:
    resp = requests.get(
        f"{base_url}/agents",
        headers={"xi-api-key": api_key},
        timeout=10
    )
    print(f"GET /agents: {resp.status_code}")
    if resp.status_code < 400:
        data = resp.json()
        print(f"Response: {data}")
        if "agents" in data:
            print(f"Found {len(data['agents'])} agents")
            for agent in data["agents"][:3]:
                print(f"  - {agent.get('name', 'Unknown')} ({agent.get('agent_id')})")
except Exception as e:
    print(f"Error: {e}")

print("\n" + "="*70)
print("Getting user feature info...\n")

try:
    resp = requests.get(
        f"{base_url}/user",
        headers={"xi-api-key": api_key},
        timeout=10
    )
    if resp.status_code == 200:
        user = resp.json()
        
        print("User Details:")
        print(f"  Tier: {user.get('subscription', {}).get('tier')}")
        
        features = user.get('features', [])
        print(f"\n  Available Features ({len(features)}):")
        for feature in features:
            print(f"    - {feature}")
            
        if 'agents' in features or 'agents_v2' in features or 'conversational_ai' in features:
            print("\n  ✅ AGENTS ARE ENABLED!")
        else:
            print("\n  ⚠️  Agents not in features list")
            print("     Wait a few minutes for activation to complete")
            
except Exception as e:
    print(f"Error: {e}")
