#!/usr/bin/env python3
"""
Create and Test IRS AI Agent on ElevenLabs
Using CORRECT API: /v1/convai/agents
"""

import os
import sys
import json
import requests
from dotenv import load_dotenv

load_dotenv()
API_KEY = os.environ.get("ELEVENLABS_API_KEY")
BASE_URL = "https://api.elevenlabs.io/v1"

def api_request(method, endpoint, data=None):
    """Make authenticated API request."""
    url = f"{BASE_URL}{endpoint}"
    headers = {"xi-api-key": API_KEY, "Content-Type": "application/json"}
    
    if method == "GET":
        resp = requests.get(url, headers=headers, timeout=15)
    elif method == "POST":
        resp = requests.post(url, json=data, headers=headers, timeout=15)
    elif method == "PUT":
        resp = requests.put(url, json=data, headers=headers, timeout=15)
    else:
        raise ValueError(f"Unsupported method: {method}")
    
    return resp

print("\n" + "="*70)
print("🚀 CREATING IRS TAXPAYER AI AGENT")
print("="*70)

# Step 1: Create IRS Agent
print("\n📋 Step 1: Creating IRS Taxpayer Assistant Agent")
print("-"*70)

irs_agent_config = {
    "name": "IRS Taxpayer Assistant",
    "tags": ["IRS", "Taxpayer Support", "Government"],
    "conversation_config": {
        "agent": {
            "first_message": "Hello! I'm the IRS Taxpayer Assistant. I can help you with refund status, payment plans, or tax questions. How can I assist you today?",
            "language": "en",
            "prompt": {
                "prompt": """You are a professional, patient, and empathetic IRS Taxpayer Assistant. Your role is to help taxpayers with their tax-related questions and concerns.

CAPABILITIES:
- Check refund status (ask for filing date, filing method)
- Explain payment plan options (short-term vs long-term)
- Answer common tax questions
- Provide general IRS information

GUIDELINES:
1. Be patient and understanding - many callers are stressed about taxes
2. Use clear, simple language - avoid jargon
3. Always verify you understood the question before answering
4. For refund status: E-filed returns take ~21 days, paper returns 6-8 weeks
5. For payment plans: Short-term (120 days, no fee) or Long-term (monthly, $31 setup fee online)
6. NEVER provide legal or investment advice
7. If you can't help, explain how to reach a human agent

ESCALATION TRIGGERS (transfer to human):
- Identity verification requests
- Fraud reports 
- Complex audit questions
- Legal disputes
- Customer requests to speak with human

TONE: Professional, helpful, patient, empathetic. Acknowledge frustration when expressed.""",
                "llm": "gemini-2.0-flash-001",
                "temperature": 0.3,
                "max_tokens": 500
            }
        },
        "tts": {
            "voice_id": "EXAVITQu4vr4xnSDxMaL",  # Sarah - professional, reassuring
            "model_id": "eleven_turbo_v2",
            "stability": 0.5,
            "similarity_boost": 0.75,
            "optimize_streaming_latency": 3
        },
        "turn": {
            "turn_timeout": 10,
            "silence_end_call_timeout": 30,
            "turn_eagerness": "normal"
        },
        "conversation": {
            "max_duration_seconds": 600,  # 10 minutes max
            "text_only": False
        }
    },
    "platform_settings": {
        "evaluation": {
            "criteria": [
                {
                    "id": "solved_inquiry",
                    "name": "Solved User Inquiry",
                    "conversation_goal_prompt": "The assistant successfully answered the taxpayer's question or directed them to appropriate resources."
                },
                {
                    "id": "professional_tone",
                    "name": "Professional Tone",
                    "conversation_goal_prompt": "The assistant maintained a professional, patient, and helpful tone throughout the conversation."
                }
            ]
        },
        "data_collection": {
            "inquiry_type": {
                "type": "string",
                "description": "The type of inquiry: refund_status, payment_plan, general_question, or escalation"
            },
            "resolution": {
                "type": "string",
                "description": "Whether the inquiry was resolved: resolved, escalated, or unresolved"
            }
        }
    }
}

print("   Sending create request to POST /v1/convai/agents/create...")
resp = api_request("POST", "/convai/agents/create", irs_agent_config)

print(f"   Status: {resp.status_code}")

if resp.status_code == 200:
    result = resp.json()
    agent_id = result.get("agent_id")
    print(f"   ✅ SUCCESS! Agent created")
    print(f"   Agent ID: {agent_id}")
else:
    print(f"   ❌ Error: {resp.text}")
    # Try to parse and show error details
    try:
        error = resp.json()
        print(f"   Details: {json.dumps(error, indent=2)[:500]}")
    except:
        pass
    sys.exit(1)

# Step 2: Get agent details to verify
print("\n📋 Step 2: Verifying Agent Creation")
print("-"*70)

resp = api_request("GET", f"/convai/agents/{agent_id}")
print(f"   Status: {resp.status_code}")

if resp.status_code == 200:
    agent = resp.json()
    print(f"   ✅ Agent verified!")
    print(f"   Name: {agent.get('name')}")
    
    conv_config = agent.get("conversation_config", {})
    agent_config = conv_config.get("agent", {})
    
    print(f"   First Message: {agent_config.get('first_message', 'N/A')[:60]}...")
    print(f"   Language: {agent_config.get('language', 'N/A')}")
    print(f"   LLM: {agent_config.get('prompt', {}).get('llm', 'N/A')}")
    
    tts = conv_config.get("tts", {})
    print(f"   Voice ID: {tts.get('voice_id', 'N/A')}")
    print(f"   TTS Model: {tts.get('model_id', 'N/A')}")
else:
    print(f"   ⚠️  Could not verify: {resp.text[:200]}")

# Step 3: Show how to test
print("\n" + "="*70)
print("✅ IRS AGENT CREATED SUCCESSFULLY!")
print("="*70)

print(f"""
Agent Details:
   Name: IRS Taxpayer Assistant
   ID: {agent_id}
   Voice: Sarah (professional, reassuring)
   LLM: Gemini 2.0 Flash

Test Your Agent:
   1. Dashboard: https://elevenlabs.io/app/agents
   2. Widget embed:
      <elevenlabs-convai agent-id="{agent_id}"></elevenlabs-convai>
      <script src="https://unpkg.com/@elevenlabs/convai-widget-embed" async></script>
   
   3. WebSocket API: wss://api.elevenlabs.io/v1/convai/conversation?agent_id={agent_id}

Sample Test Phrases:
   - "Where is my refund?"
   - "I need to set up a payment plan"
   - "How long does it take to get my refund if I filed online?"
   - "I want to speak to a human"

API Endpoints:
   GET  /v1/convai/agents/{agent_id}          - Get agent config
   PUT  /v1/convai/agents/{agent_id}          - Update agent
   GET  /v1/convai/agents/{agent_id}/widget   - Get widget HTML
""")

# Save config for reference
config_file = f"/Users/ChadDHendren/AmazonConnect1/.irs_agent_{agent_id}.json"
with open(config_file, "w") as f:
    json.dump({
        "agent_id": agent_id,
        "name": "IRS Taxpayer Assistant",
        "created_by": "deploy script",
        "config": irs_agent_config
    }, f, indent=2)
print(f"   Config saved: {config_file}")
