#!/usr/bin/env python3
"""
ElevenLabs Conversational AI Agent Test
Using CORRECT API endpoints: /v1/convai/agents (NOT /v1/agents)
"""

import os
import sys
import json
import requests
from dotenv import load_dotenv

load_dotenv()
API_KEY = os.environ.get("ELEVENLABS_API_KEY")
BASE_URL = "https://api.elevenlabs.io/v1"

print("="*70)
print("🔍 ELEVENLABS CONVERSATIONAL AI - CORRECT ENDPOINT TEST")
print("="*70)

# Step 1: List existing agents with CORRECT endpoint
print("\n📋 Step 1: List Existing Agents")
print("-"*70)

try:
    resp = requests.get(
        f"{BASE_URL}/convai/agents",
        headers={"xi-api-key": API_KEY},
        timeout=10
    )
    
    print(f"   Endpoint: GET /v1/convai/agents")
    print(f"   Status: {resp.status_code}")
    
    if resp.status_code == 200:
        data = resp.json()
        agents = data.get("agents", [])
        print(f"   ✅ SUCCESS! Found {len(agents)} agent(s)")
        
        for agent in agents:
            print(f"\n   Agent: {agent.get('name', 'Unnamed')}")
            print(f"   ID: {agent.get('agent_id')}")
            print(f"   Created: {agent.get('created_at_unix_secs')}")
            print(f"   Tags: {agent.get('tags', [])}")
    else:
        print(f"   ❌ Error: {resp.text[:200]}")
        
except Exception as e:
    print(f"   ❌ Exception: {str(e)}")

# Step 2: Get agent details if we have agents
print("\n" + "="*70)
print("📋 Step 2: Get Agent Details")
print("-"*70)

if resp.status_code == 200 and agents:
    agent_id = agents[0].get("agent_id")
    print(f"   Getting details for agent: {agent_id}")
    
    try:
        detail_resp = requests.get(
            f"{BASE_URL}/convai/agents/{agent_id}",
            headers={"xi-api-key": API_KEY},
            timeout=10
        )
        
        print(f"   Endpoint: GET /v1/convai/agents/{agent_id}")
        print(f"   Status: {detail_resp.status_code}")
        
        if detail_resp.status_code == 200:
            agent_detail = detail_resp.json()
            print(f"   ✅ Got agent config!")
            
            # Show key info
            conv_config = agent_detail.get("conversation_config", {})
            agent_config = conv_config.get("agent", {})
            tts_config = conv_config.get("tts", {})
            
            print(f"\n   Agent Name: {agent_detail.get('name')}")
            print(f"   First Message: {agent_config.get('first_message', 'N/A')[:60]}...")
            print(f"   Language: {agent_config.get('language', 'N/A')}")
            
            prompt_config = agent_config.get("prompt", {})
            print(f"   LLM: {prompt_config.get('llm', 'N/A')}")
            print(f"   System Prompt: {prompt_config.get('prompt', 'N/A')[:80]}...")
            
            print(f"\n   Voice ID: {tts_config.get('voice_id', 'N/A')}")
            print(f"   TTS Model: {tts_config.get('model_id', 'N/A')}")
            
            # Knowledge base
            kb = prompt_config.get("knowledge_base", [])
            print(f"\n   Knowledge Base Items: {len(kb)}")
            for item in kb[:3]:
                print(f"      - {item.get('name', 'Unnamed')} ({item.get('type')})")
                
        else:
            print(f"   ❌ Error: {detail_resp.text[:200]}")
            
    except Exception as e:
        print(f"   ❌ Exception: {str(e)}")

# Step 3: Show correct API structure
print("\n" + "="*70)
print("📋 CORRECT API ENDPOINTS")
print("="*70)

api_info = """
IMPORTANT: ElevenLabs uses /convai/ for Conversational AI agents!

Correct Endpoints:
  ✅ GET  /v1/convai/agents              - List all agents
  ✅ POST /v1/convai/agents/create       - Create new agent  
  ✅ GET  /v1/convai/agents/{agent_id}   - Get agent details
  ✅ PUT  /v1/convai/agents/{agent_id}   - Update agent

Wrong Endpoints (404):
  ❌ /v1/agents
  ❌ /v1/agent
  ❌ /v1/conversational-ai

Create Agent Payload Structure:
{
    "name": "IRS Taxpayer Assistant",
    "conversation_config": {
        "agent": {
            "first_message": "Hello! How can I help you today?",
            "language": "en",
            "prompt": {
                "prompt": "You are a helpful IRS assistant...",
                "llm": "gemini-2.0-flash-001",
                "temperature": 0,
                "knowledge_base": [...]
            }
        },
        "tts": {
            "voice_id": "EXAVITQu4vr4xnSDxMaL",
            "model_id": "eleven_turbo_v2",
            "stability": 0.5,
            "similarity_boost": 0.75
        }
    }
}
"""
print(api_info)

print("="*70)
print("✅ ANALYSIS COMPLETE")
print("="*70)
