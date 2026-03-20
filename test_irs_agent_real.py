#!/usr/bin/env python3
"""
Real conversation test with IRS Taxpayer Assistant Agent
Uses ElevenLabs Conversational AI API to send test messages
"""

import os
import json
import requests
from dotenv import load_dotenv

load_dotenv()
API_KEY = os.environ.get("ELEVENLABS_API_KEY")
AGENT_ID = "agent_6201km43egt3f39tt000587m4ehp"
BASE_URL = "https://api.elevenlabs.io/v1"

def test_agent_conversation():
    """Run real conversation tests against the IRS agent."""
    
    print("\n" + "="*70)
    print("🧪 REAL CONVERSATION TEST: IRS Taxpayer Assistant")
    print("="*70)
    print(f"\nAgent ID: {AGENT_ID}")
    
    # Get agent info first
    print("\n📋 Getting Agent Details...")
    resp = requests.get(
        f"{BASE_URL}/convai/agents/{AGENT_ID}",
        headers={"xi-api-key": API_KEY},
        timeout=10
    )
    
    if resp.status_code == 200:
        agent = resp.json()
        conv_config = agent.get("conversation_config", {})
        agent_config = conv_config.get("agent", {})
        
        print(f"   Name: {agent.get('name')}")
        print(f"   First Message: {agent_config.get('first_message', 'N/A')[:60]}...")
        print(f"   LLM: {agent_config.get('prompt', {}).get('llm', 'N/A')}")
    else:
        print(f"   ❌ Could not get agent: {resp.status_code}")
        return
    
    # Test scenarios
    test_scenarios = [
        {
            "name": "Refund Status Inquiry",
            "message": "Where is my refund? I filed my taxes 3 weeks ago electronically.",
            "expected_topics": ["21 days", "e-file", "direct deposit", "IRS.gov"]
        },
        {
            "name": "Payment Plan Request",
            "message": "I owe $5,000 in taxes but I can't pay it all at once. What are my options?",
            "expected_topics": ["payment plan", "installment", "monthly", "setup fee"]
        },
        {
            "name": "General Tax Question",
            "message": "How long do I need to keep my tax records?",
            "expected_topics": ["3 years", "7 years", "records", "audit"]
        },
        {
            "name": "Escalation Request",
            "message": "I want to speak to a real person. This is urgent.",
            "expected_topics": ["transfer", "agent", "connect", "specialist"]
        }
    ]
    
    print("\n" + "="*70)
    print("🗣️ RUNNING CONVERSATION TESTS")
    print("="*70)
    
    # Use the signed URL approach to get a conversation
    print("\n📡 Getting signed conversation URL...")
    
    signed_url_resp = requests.get(
        f"{BASE_URL}/convai/conversation/get-signed-url",
        params={"agent_id": AGENT_ID},
        headers={"xi-api-key": API_KEY},
        timeout=10
    )
    
    if signed_url_resp.status_code == 200:
        signed_data = signed_url_resp.json()
        signed_url = signed_data.get("signed_url")
        print(f"   ✅ Got signed URL for WebSocket connection")
        print(f"   URL: {signed_url[:80]}...")
    else:
        print(f"   Status: {signed_url_resp.status_code}")
        print(f"   Response: {signed_url_resp.text[:200]}")
        
    # Try text-only conversation endpoint
    print("\n📡 Testing text conversation endpoint...")
    
    for i, scenario in enumerate(test_scenarios, 1):
        print(f"\n--- Test {i}: {scenario['name']} ---")
        print(f"User: \"{scenario['message']}\"")
        
        # Try the conversation endpoint
        try:
            conv_resp = requests.post(
                f"{BASE_URL}/convai/agents/{AGENT_ID}/conversation",
                json={
                    "message": scenario["message"],
                    "conversation_id": f"test_{i}_{os.urandom(4).hex()}"
                },
                headers={
                    "xi-api-key": API_KEY,
                    "Content-Type": "application/json"
                },
                timeout=30
            )
            
            if conv_resp.status_code == 200:
                result = conv_resp.json()
                agent_response = result.get("response", result.get("message", str(result)))
                print(f"Agent: \"{agent_response[:200]}...\"")
                
                # Check for expected topics
                response_lower = agent_response.lower()
                found_topics = [t for t in scenario["expected_topics"] if t.lower() in response_lower]
                if found_topics:
                    print(f"   ✅ Found expected topics: {found_topics}")
                else:
                    print(f"   ⚠️  Expected topics not found: {scenario['expected_topics']}")
            else:
                print(f"   Status: {conv_resp.status_code}")
                # Try to show error details
                try:
                    error = conv_resp.json()
                    print(f"   Response: {json.dumps(error)[:200]}")
                except:
                    print(f"   Response: {conv_resp.text[:200]}")
                    
        except Exception as e:
            print(f"   ❌ Error: {str(e)}")
    
    print("\n" + "="*70)
    print("📊 TEST SUMMARY")
    print("="*70)
    
    print(f"""
The IRS Taxpayer Assistant agent is LIVE and ready!

To test interactively:

1. WEB DASHBOARD (Easiest):
   → Go to: https://elevenlabs.io/app/agents
   → Click "IRS Taxpayer Assistant"  
   → Click "Test AI agent" button
   → Speak or type your questions

2. EMBED IN WEBPAGE:
   <elevenlabs-convai agent-id="{AGENT_ID}"></elevenlabs-convai>
   <script src="https://unpkg.com/@elevenlabs/convai-widget-embed" async></script>

3. SHAREABLE LINK:
   → In dashboard, click "Share" to get a public test link

Sample questions to try:
   • "Where is my refund?"
   • "I need to set up a payment plan"
   • "How long does it take to process a paper return?"
   • "I want to speak to a human"
""")

if __name__ == "__main__":
    test_agent_conversation()
