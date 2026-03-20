#!/usr/bin/env python3
"""Quick check for account upgrade and agents enablement."""
import os
import sys
import requests

try:
    from dotenv import load_dotenv
    load_dotenv()
except:
    pass

API_KEY = os.environ.get("ELEVENLABS_API_KEY")

print("\n🔍 Checking Account After Upgrade...\n")

try:
    # Check user
    resp = requests.get(
        "https://api.elevenlabs.io/v1/user",
        headers={"xi-api-key": API_KEY},
        timeout=10
    )
    resp.raise_for_status()
    user = resp.json()
    
    tier = user.get("subscription", {}).get("tier", "unknown")
    print(f"✅ Account Status: Active")
    print(f"   Tier: {tier.upper()}")
    
    # Check agents endpoint
    print("\n🔍 Checking AI Agents...")
    agents_resp = requests.get(
        "https://api.elevenlabs.io/v1/agents",
        headers={"xi-api-key": API_KEY},
        timeout=10
    )
    
    if agents_resp.status_code == 200:
        print(f"✅ AI AGENTS: ENABLED ✓\n")
        agents = agents_resp.json()
        agent_list = agents.get("agents", [])
        print(f"   Active Agents: {len(agent_list)}")
        if agent_list:
            for agent in agent_list[:3]:
                print(f"   - {agent.get('name', 'Unknown')}")
        print(f"\n🚀 Ready to deploy IRS agent!")
        sys.exit(0)
    elif agents_resp.status_code == 404:
        print(f"❌ AI Agents: NOT ENABLED")
        print(f"   • Go to: https://elevenlabs.io/account/agents")
        print(f"   • Click: 'Enable AI Agents'")
        print(f"   • Wait: 2-5 minutes for activation")
        print(f"   • Then run deployment again")
        sys.exit(1)
    else:
        print(f"⚠️  Unexpected status: {agents_resp.status_code}")
        sys.exit(1)
        
except Exception as e:
    print(f"❌ Error: {str(e)}")
    sys.exit(1)
