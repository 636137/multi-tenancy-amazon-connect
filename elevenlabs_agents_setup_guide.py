#!/usr/bin/env python3
"""
ElevenLabs AI Agents Setup Guide
=================================
Your account needs to be upgraded to enable AI Agents.
This script shows you exactly what's needed and provides a template.
"""

import os
import sys
import json
import webbrowser
from pathlib import Path

print("\n" + "="*70)
print("📋 ELEVENLABS AI AGENTS - SETUP REQUIREMENTS")
print("="*70)

print("\n⚠️  Your Account Status:")
print("   • Tier: FREE")
print("   • AI Agents: NOT ENABLED")
print("   • Action Required: Yes")

print("\n" + "="*70)
print("✅ WHAT YOU NEED TO DO")
print("="*70)

steps = [
    {
        "step": 1,
        "title": "Upgrade to Paid Plan",
        "details": [
            "• Go to: https://elevenlabs.io/pricing",
            "• Select: Creator (Minimum $5/month) or higher",
            "• Reason: Agents only available on paid plans"
        ]
    },
    {
        "step": 2,
        "title": "Enable AI Agents in Settings",
        "details": [
            "• Go to: https://elevenlabs.io/account/agents",
            "• Find: AI Agents section",
            "• Click: 'Enable AI Agents'",
            "• Wait: 2-5 minutes for activation"
        ]
    },
    {
        "step": 3,
        "title": "Verify Activation",
        "details": [
            "• Run: python3 check_elevenlabs_account.py",
            "• Look for: 'agents' in Available Features",
            "• Confirm: /agents endpoint returns 200 OK"
        ]
    }
]

for item in steps:
    print(f"\nStep {item['step']}: {item['title']}")
    for detail in item['details']:
        print(f"  {detail}")

print("\n" + "="*70)
print("📊 COST COMPARISON")
print("="*70)

costs = {
    "Free Tier": {
        "monthly_cost": "$0",
        "characters": "10,000 characters",
        "agents": "❌ Not available",
        "features": ["Text-to-Speech", "Voice cloning", "Dubbing"]
    },
    "Creator ($5+/month)": {
        "monthly_cost": "$5+",
        "characters": "100,000 characters + API usage",
        "agents": "✅ Available",
        "features": ["All free features", "AI Agents", "API access", "Priority support"]
    },
    "Professional ($99/month)": {
        "monthly_cost": "$99",
        "characters": "1,000,000 characters + API",
        "agents": "✅ Advanced agents",
        "features": ["All features", "Dedicated support", "Custom models"]
    }
}

for plan, details in costs.items():
    print(f"\n{plan}")
    print(f"  Cost: {details['monthly_cost']}")
    print(f"  Characters: {details['characters']}")
    print(f"  AI Agents: {details['agents']}")
    for feature in details['features']:
        print(f"  • {feature}")

print("\n" + "="*70)
print("✨ AFTER YOU UPGRADE & ENABLE AGENTS")
print("="*70)

print("\nRun this command to deploy your IRS agent:")
print("  $ python3 deploy_irs_agent_real.py")

print("\nThe script will:")
print("  1. Create 'IRS Taxpayer Assistant' agent")
print("  2. Configure empathetic voice (Grace)")
print("  3. Upload IRS FAQ knowledge base")
print("  4. Define 4 conversation intents")
print("  5. Setup escalation rules")
print("  6. Run 5 real conversation tests")
print("  7. Save agent configuration")

print("\nExpected output:")
print("  ✅ Agent created: agent_abc123xyz")
print("  ✅ Voice configured (Grace)")
print("  ✅ Knowledge base uploaded (4 documents)")
print("  ✅ Intents defined (4 intents)")
print("  ✅ Escalation configured")
print("  ✅ Tests completed (80%+ success rate expected)")

print("\n" + "="*70)
print("📁 READY-TO-DEPLOY CONFIGURATION")
print("="*70)

# Create pre-built agent config
config = {
    "agent_id": "will-be-generated",
    "name": "IRS Taxpayer Assistant",
    "description": "Handles refund status, payment plans, and tax questions",
    "model": "elevenlabs-agent-advanced",
    "personality": {
        "tone": "professional, patient, empathetic",
        "firstMessage": "Hello! I'm the IRS Taxpayer Assistant. I can help you with refund status, payment plans, or tax questions. How can I assist you today?",
        "responseStyle": "natural",
        "maxTurnLength": 5000
    },
    "voice": {
        "name": "Grace",
        "personality": "empathetic, warm, caring",
        "settings": {
            "stability": 0.5,
            "similarity_boost": 0.75
        }
    },
    "intents": [
        {
            "id": "refund_status",
            "name": "Check Refund Status",
            "triggers": ["Where is my refund?", "When will I get my refund?", "What's the status of my return?"]
        },
        {
            "id": "payment_plan",
            "name": "Setup Payment Plan",
            "triggers": ["Can I set up a payment plan?", "I can't pay in full", "What are my payment options?"]
        },
        {
            "id": "verify_identity",
            "name": "Identity Verification",
            "triggers": ["verify identity", "confirm information"],
            "always_escalate": True
        },
        {
            "id": "complaint",
            "name": "File Complaint",
            "triggers": ["I have a complaint", "This is unfair"]
        }
    ],
    "knowledge_base": [
        {
            "title": "Refund Processing Times",
            "content": "E-filed returns: 21 days. Paper returns: 6-8 weeks..."
        },
        {
            "title": "Payment Plan Options",
            "content": "Monthly installments available from $25-$1000"
        },
        {
            "title": "Identity Verification",
            "content": "Required for security: SSN, filing status, filing year"
        },
        {
            "title": "Common IRS Terms",
            "content": "AGI, Refund, Amended Return, etc..."
        }
    ],
    "escalation_rules": [
        {
            "trigger": "max_failed_attempts",
            "threshold": 3,
            "queue": "tier_2_support"
        },
        {
            "trigger": "confidence_below",
            "threshold": 0.5,
            "queue": "tier_1_support"
        },
        {
            "trigger": "intent_requires_human",
            "intents": ["verify_identity", "complaint"],
            "queue": "priority_queue"
        }
    ]
}

config_path = Path("/Users/ChadDHendren/AmazonConnect1/.irs_agent_template.json")
config_path.write_text(json.dumps(config, indent=2))

print(f"\n✅ Pre-built configuration saved:")
print(f"   File: .irs_agent_template.json")
print(f"   Ready to deploy once agents are enabled")

print("\n" + "="*70)
print("🔗 USEFUL LINKS")
print("="*70)
print("\n  Upgrade Account:    https://elevenlabs.io/pricing")
print("  Enable Agents:      https://elevenlabs.io/account/agents")
print("  Agent Documentation: https://elevenlabs.io/docs/agents")
print("  API Reference:      https://elevenlabs.io/docs/api/reference")
print("  Support:             https://help.elevenlabs.io/")

print("\n" + "="*70)
print("💡 MEANWHILE - WHAT YOU CAN DO NOW")
print("="*70)

print("\n✅ Your current capabilities (FREE TIER):")
print("  1. Text-to-Speech with 121 voices")
print("  2. Voice cloning")
print("  3. Soundboard creation")
print("  4. Audio dubbing")

print("\n  To test these features, run:")
print("    python3 test_elevenlabs_tts.py")

print("\n")
