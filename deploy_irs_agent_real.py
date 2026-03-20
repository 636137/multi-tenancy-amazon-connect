#!/usr/bin/env python3
"""
Deploy a real IRS AI Agent on ElevenLabs with voice, knowledge base, and testing.
This creates an actual agent in ElevenLabs and runs real conversation tests.
"""

import os
import sys
import json
import time
import requests
from pathlib import Path
from typing import Optional

# Load API key from .env
try:
    from dotenv import load_dotenv
    load_dotenv()
except ImportError:
    pass

API_KEY = os.environ.get("ELEVENLABS_API_KEY")
if not API_KEY:
    print("❌ ELEVENLABS_API_KEY not found in environment")
    sys.exit(1)

BASE_URL = "https://api.elevenlabs.io/v1"

def api_request(method: str, endpoint: str, json_data=None, params=None) -> dict:
    """Make authenticated request to ElevenLabs API."""
    url = f"{BASE_URL}{endpoint}"
    headers = {
        "xi-api-key": API_KEY,
        "Content-Type": "application/json"
    }
    
    try:
        if method == "GET":
            resp = requests.get(url, headers=headers, params=params, timeout=10)
        elif method == "POST":
            resp = requests.post(url, json=json_data, headers=headers, timeout=10)
        elif method == "PUT":
            resp = requests.put(url, json=json_data, headers=headers, timeout=10)
        else:
            raise ValueError(f"Unsupported method: {method}")
        
        resp.raise_for_status()
        return resp.json()
    except requests.exceptions.HTTPError as e:
        print(f"❌ API Error: {e.response.status_code}")
        try:
            error_data = e.response.json()
            print(f"   {error_data.get('error', error_data)}")
        except:
            print(f"   {e.response.text}")
        raise
    except requests.exceptions.Timeout:
        print(f"❌ API timeout")
        raise
    except Exception as e:
        print(f"❌ Request error: {str(e)}")
        raise

def create_irs_agent() -> str:
    """Create IRS AI Agent."""
    print("\n" + "="*70)
    print("STEP 1: Creating IRS AI Agent")
    print("="*70)
    
    payload = {
        "name": "IRS Taxpayer Assistant",
        "description": "Handles refund status, payment plans, and tax questions for IRS taxpayers",
        "model": "elevenlabs-agent-advanced",
        "personality": {
            "tone": "professional, patient, empathetic",
            "firstMessage": "Hello! I'm the IRS Taxpayer Assistant. I can help you with refund status, payment plans, or tax questions. How can I assist you today?",
            "responseStyle": "natural",
            "maxTurnLength": 5000
        },
        "capabilities": {
            "canTransfer": True,
            "canEscalate": True,
            "canLearnContext": True,
            "canIntegrate": True
        },
        "safety": {
            "blockOffensiveContent": True,
            "verifyUserIdentity": False,  # Handle separately
            "maxConsecutiveFails": 3
        }
    }
    
    result = api_request("POST", "/agents", json_data=payload)
    agent_id = result["agent_id"]
    
    print(f"✅ Agent created successfully")
    print(f"   Agent ID: {agent_id}")
    print(f"   Name: {result['name']}")
    print(f"   Model: {result['model']}")
    print(f"   Status: {result.get('status', 'initializing')}")
    
    return agent_id

def configure_agent_voice(agent_id: str) -> dict:
    """Configure empathetic support voice."""
    print("\n" + "="*70)
    print("STEP 2: Configuring Agent Voice")
    print("="*70)
    
    # Get available voices
    voices_result = api_request("GET", "/voices")
    voices = voices_result.get("voices", [])
    
    # Find Grace voice (empathetic female)
    grace_voice = next((v for v in voices if v.get("name") == "Grace"), None)
    if not grace_voice:
        grace_voice = voices[0]  # Fallback
    
    voice_id = grace_voice["voice_id"]
    
    payload = {
        "voice_id": voice_id,
        "tts_model": "eleven_turbo_v2",
        "voice_settings": {
            "stability": 0.5,      # More variation for natural speech
            "similarity_boost": 0.75
        }
    }
    
    result = api_request("POST", f"/agents/{agent_id}/voice", json_data=payload)
    
    print(f"✅ Voice configured")
    print(f"   Voice: {grace_voice.get('name', 'Grace')} (empathetic)")
    print(f"   TTS Model: eleven_turbo_v2 (fastest)")
    print(f"   Stability: 0.5 (natural variation)")
    
    return result

def upload_knowledge_base(agent_id: str) -> dict:
    """Upload IRS FAQ knowledge base."""
    print("\n" + "="*70)
    print("STEP 3: Uploading Knowledge Base")
    print("="*70)
    
    documents = [
        {
            "title": "Refund Processing Times",
            "content": """IRS Refund Processing:
- E-filed returns: Typically 21 days with direct deposit
- Paper returns: 6-8 weeks processing time
- Refunds sent by mail take 2-3 weeks additional
- Check refund status at IRS.gov with SSN and filing status
- Call 1-800-829-1040 for phone support""",
            "url": "https://irs.gov/refunds"
        },
        {
            "title": "Payment Plan Options",
            "content": """Payment Plan Arrangements:
Short-term payment plan (120 days):
- No setup fee
- Minimum $25/month payment
- Best for those who can pay within 120 days

Long-term installment plan (24-72 months):
- $225 setup fee (or $31 for online setup)
- Minimum $25/month payment
- Subject to interest and penalties
- Apply online at IRS.gov or by mail""",
            "url": "https://irs.gov/payment-plans"
        },
        {
            "title": "Identity Verification",
            "content": """Verifying Your Identity:
- We may verify identity before discussing account details
- Required information: SSN, filing status, filing year
- Verification protects your taxpayer information
- Always verify through official IRS channels
- Be cautious of phone scams claiming to be IRS""",
            "url": "https://irs.gov/identity-protection"
        },
        {
            "title": "Common IRS Terms",
            "content": """Key Terms Explained:
- AGI (Adjusted Gross Income): Income after deductions
- Refund: When you paid more tax than owed
- Amended Return (Form 1040-X): Corrects prior year return
- Withholding: Tax taken from paychecks
- Estimated Tax Payments: Quarterly payments by self-employed
- Filing Status: Single, Married, Head of Household, etc.""",
            "url": "https://irs.gov/help"
        }
    ]
    
    payload = {
        "name": "IRS_Taxpayer_FAQ",
        "documents": documents,
        "retrieval_mode": "semantic",
        "max_context_tokens": 2000,
        "confidence_threshold": 0.7
    }
    
    result = api_request("POST", f"/agents/{agent_id}/knowledge-base", json_data=payload)
    
    print(f"✅ Knowledge base uploaded")
    print(f"   KB ID: {result.get('kb_id', 'unknown')}")
    print(f"   Documents: {len(documents)}")
    print(f"   Retrieval: Semantic search with 70% confidence threshold")
    
    return result

def define_intents(agent_id: str) -> dict:
    """Define conversation intents."""
    print("\n" + "="*70)
    print("STEP 4: Defining Conversation Intents")
    print("="*70)
    
    intents = {
        "intents": [
            {
                "intent_id": "refund_status",
                "name": "Check Refund Status",
                "description": "Customer wants to know about their refund",
                "trigger_phrases": [
                    "Where is my refund?",
                    "When will I get my refund?",
                    "What's the status of my return?",
                    "How long does a refund take?",
                    "Track my refund"
                ],
                "agent_response": {
                    "type": "knowledge_lookup",
                    "knowledge_base": "IRS_Taxpayer_FAQ",
                    "fields_needed": ["refund_status", "timeline"],
                    "escalate_if": "agent_confidence < 0.6"
                },
                "can_be_handled_by": ["agent"]
            },
            {
                "intent_id": "payment_plan",
                "name": "Setup Payment Plan",
                "description": "Customer wants to arrange payments",
                "trigger_phrases": [
                    "Can I set up a payment plan?",
                    "I can't pay in full",
                    "What are my payment options?",
                    "Can I pay monthly?"
                ],
                "agent_response": {
                    "type": "knowledge_lookup",
                    "knowledge_base": "IRS_Taxpayer_FAQ",
                    "confirmation_required": True
                },
                "escalate_threshold": 0.5
            },
            {
                "intent_id": "verify_identity",
                "name": "Identity Verification",
                "description": "Verify taxpayer identity (ALWAYS ESCALATE)",
                "trigger_phrases": [
                    "verify identity",
                    "confirm information",
                    "security check"
                ],
                "agent_response": {
                    "type": "escalate_immediate",
                    "message": "For security, I'm connecting you with an agent to verify your identity."
                },
                "always_escalate": True
            },
            {
                "intent_id": "complaint",
                "name": "File Complaint",
                "description": "Customer has complaint about IRS",
                "trigger_phrases": [
                    "I have a complaint",
                    "This is unfair",
                    "I want to file a complaint"
                ],
                "agent_response": {
                    "type": "escalate_priority",
                    "message": "I understand your concern. Let me connect you with someone who can help."
                },
                "escalate_threshold": 0.8
            }
        ],
        "conversation_rules": {
            "max_turns": 10,
            "timeout_seconds": 300,
            "confirmation_required_for": [
                "payment_arrangement",
                "account_changes",
                "escalation"
            ],
            "prohibited_topics": [
                "legal_advice",
                "investment_advice",
                "personal_financial_planning"
            ]
        }
    }
    
    payload = {
        "intents": intents["intents"],
        "rules": intents["conversation_rules"]
    }
    
    result = api_request("POST", f"/agents/{agent_id}/intents", json_data=payload)
    
    print(f"✅ Intents defined")
    print(f"   Total intents: {len(intents['intents'])}")
    for intent in intents["intents"]:
        print(f"   - {intent['name']} ({intent['intent_id']})")
    
    return result

def setup_escalation(agent_id: str) -> dict:
    """Configure escalation rules."""
    print("\n" + "="*70)
    print("STEP 5: Configuring Escalation Rules")
    print("="*70)
    
    payload = {
        "escalation_rules": [
            {
                "trigger": "max_failed_attempts",
                "threshold": 3,
                "queue": "tier_2_support",
                "message": "Let me connect you with a specialist who can help..."
            },
            {
                "trigger": "confidence_below",
                "threshold": 0.5,
                "queue": "tier_1_support",
                "message": "I'm not confidently sure about that. Let me get someone to help..."
            },
            {
                "trigger": "intent_requires_human",
                "intents": ["verify_identity", "legal_question", "complaint"],
                "queue": "priority_queue",
                "message": "For this, I'm connecting you with a tax professional..."
            },
            {
                "trigger": "sentiment_negative",
                "threshold": -0.7,
                "queue": "retention_team",
                "message": "I understand this is frustrating. Let me get my supervisor..."
            }
        ],
        "timeout_seconds": 300,
        "fallback_queue": "general_support"
    }
    
    result = api_request("POST", f"/agents/{agent_id}/escalation", json_data=payload)
    
    print(f"✅ Escalation rules configured")
    print(f"   Rules: 4 triggers defined")
    print(f"   - Failed attempts → Tier 2")
    print(f"   - Low confidence → Tier 1")
    print(f"   - Critical intents → Priority queue")
    print(f"   - Negative sentiment → Retention team")
    
    return result

def run_conversation_tests(agent_id: str) -> dict:
    """Run real conversation tests against the agent."""
    print("\n" + "="*70)
    print("STEP 6: Running Conversation Tests")
    print("="*70)
    
    test_cases = [
        {
            "user_input": "Where is my refund?",
            "expected_intent": "refund_status",
            "description": "Check refund status"
        },
        {
            "user_input": "I need a payment plan. I can pay $100 a month.",
            "expected_intent": "payment_plan",
            "description": "Setup payment arrangement"
        },
        {
            "user_input": "Can I verify my identity?",
            "expected_intent": "verify_identity",
            "description": "Should escalate to human (identity verification)"
        },
        {
            "user_input": "I'm really frustrated with how long this is taking!",
            "expected_intent": "complaint",
            "description": "Customer complaint with negative sentiment"
        },
        {
            "user_input": "What's the fastest way to get my refund?",
            "expected_intent": "refund_status",
            "description": "Refund inquiry with follow up"
        }
    ]
    
    print(f"\nRunning {len(test_cases)} test conversations...\n")
    
    results = {
        "total_tests": len(test_cases),
        "passed": 0,
        "failed": 0,
        "test_results": []
    }
    
    for idx, test_case in enumerate(test_cases, 1):
        print(f"Test {idx}/{len(test_cases)}: {test_case['description']}")
        print(f"  Input: '{test_case['user_input']}'")
        print(f"  Expected Intent: {test_case['expected_intent']}")
        
        try:
            # Call agent with test input
            payload = {
                "user_input": test_case["user_input"],
                "validate_intent": True,
                "measure_latency": True,
                "capture_sentiment": True
            }
            
            test_result = api_request(
                "POST",
                f"/agents/{agent_id}/test-conversation",
                json_data=payload
            )
            
            detected_intent = test_result.get("intent", {}).get("intent_id", "unknown")
            confidence = test_result.get("confidence", 0)
            latency = test_result.get("latency_ms", 0)
            response = test_result.get("response", "")
            
            # Check if test passed
            intent_match = detected_intent == test_case["expected_intent"]
            status = "✅ PASS" if intent_match and confidence > 0.7 else "⚠️  PARTIAL"
            
            print(f"  Result: {status}")
            print(f"    Detected Intent: {detected_intent}")
            print(f"    Confidence: {confidence:.0%}")
            print(f"    Latency: {latency}ms")
            print(f"    Response: {response[:60]}...")
            
            if intent_match and confidence > 0.7:
                results["passed"] += 1
            else:
                results["failed"] += 1
            
            results["test_results"].append({
                "test": test_case["description"],
                "intent_match": intent_match,
                "confidence": confidence,
                "latency_ms": latency,
                "status": "pass" if intent_match else "fail"
            })
            
        except Exception as e:
            print(f"  Result: ❌ ERROR")
            print(f"    Error: {str(e)}")
            results["failed"] += 1
            results["test_results"].append({
                "test": test_case["description"],
                "status": "error",
                "error": str(e)
            })
        
        print()
    
    # Summary
    success_rate = results["passed"] / results["total_tests"] if results["total_tests"] > 0 else 0
    print("="*70)
    print(f"Test Summary")
    print("="*70)
    print(f"  Total Tests: {results['total_tests']}")
    print(f"  Passed: {results['passed']}")
    print(f"  Failed: {results['failed']}")
    print(f"  Success Rate: {success_rate:.0%}")
    
    return results

def save_agent_config(agent_id: str, test_results: dict):
    """Save agent configuration for later reference."""
    print("\n" + "="*70)
    print("STEP 7: Saving Configuration")
    print("="*70)
    
    config = {
        "agent_id": agent_id,
        "name": "IRS Taxpayer Assistant",
        "model": "elevenlabs-agent-advanced",
        "voice": "Grace (empathetic)",
        "created_at": time.strftime("%Y-%m-%d %H:%M:%S"),
        "test_results": test_results,
        "api_endpoints": {
            "conversations": f"https://api.elevenlabs.io/v1/agents/{agent_id}/conversations",
            "test": f"https://api.elevenlabs.io/v1/agents/{agent_id}/test-conversation",
            "analytics": f"https://api.elevenlabs.io/v1/agents/{agent_id}/analytics"
        },
        "next_steps": [
            f"1. View analytics: Check dashboard for agent performance",
            f"2. Deploy to Amazon Connect: Use '/elevenlabs-orchestrator' agent",
            f"3. Monitor: Watch escalation %s and conversation success rates",
            f"4. Refine: Adjust intents based on real traffic patterns"
        ]
    }
    
    config_path = Path("/Users/ChadDHendren/AmazonConnect1/.elevenlabs_agent_config.json")
    config_path.write_text(json.dumps(config, indent=2))
    
    print(f"✅ Configuration saved")
    print(f"   File: {config_path}")
    print(f"   Agent ID: {agent_id}")
    
    return config

def main():
    print("\n" + "="*70)
    print("🚀 DEPLOYING REAL IRS AI AGENT ON ELEVENLABS")
    print("="*70)
    print("\nThis will create an actual functioning agent that can handle")
    print("live conversations about IRS refunds, payments, and tax issues.\n")
    
    try:
        # Create agent
        agent_id = create_irs_agent()
        
        # Wait for agent to initialize
        print("\n⏳ Waiting for agent to initialize...")
        time.sleep(2)
        
        # Configure voice
        configure_agent_voice(agent_id)
        
        # Upload knowledge base
        upload_knowledge_base(agent_id)
        
        # Define intents
        define_intents(agent_id)
        
        # Setup escalation
        setup_escalation(agent_id)
        
        # Run tests
        test_results = run_conversation_tests(agent_id)
        
        # Save config
        config = save_agent_config(agent_id, test_results)
        
        # Final summary
        print("\n" + "="*70)
        print("✅ DEPLOYMENT COMPLETE")
        print("="*70)
        print(f"\nYour IRS AI Agent is now live!")
        print(f"\nAgent Details:")
        print(f"  Agent ID: {agent_id}")
        print(f"  Name: IRS Taxpayer Assistant")
        print(f"  Model: Advanced (complex reasoning)")
        print(f"  Voice: Grace (empathetic, natural)")
        print(f"  Knowledge Base: IRS FAQs (semantic search)")
        print(f"  Intents: 4 (refund, payment, verify, complaint)")
        print(f"  Escalation: Configured for 4 scenarios")
        print(f"\nTest Results:")
        print(f"  Success Rate: {test_results['passed']}/{test_results['total_tests']}")
        print(f"\nNext Steps:")
        for step in config["next_steps"]:
            print(f"  {step}")
        print()
        
    except Exception as e:
        print(f"\n❌ Deployment failed: {str(e)}")
        sys.exit(1)

if __name__ == "__main__":
    main()
