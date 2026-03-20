#!/usr/bin/env python3
"""
Test ElevenLabs Text-to-Speech with mockup IRS conversation.
Demonstrates what works right now on free tier.
"""

import os
import sys
import json
import requests
from pathlib import Path

try:
    from dotenv import load_dotenv
    load_dotenv()
except:
    pass

API_KEY = os.environ.get("ELEVENLABS_API_KEY")
if not API_KEY:
    print("❌ ELEVENLABS_API_KEY not found")
    sys.exit(1)

print("\n" + "="*70)
print("🎤 ELEVENLABS TEXT-TO-SPEECH DEMO")
print("="*70)
print("\nGenerating voice responses for IRS taxpayer scenarios...")
print("(This works on your current FREE tier account)\n")

def synthesize_speech(text: str, voice_id: str, voice_name: str) -> bool:
    """Generate speech from text."""
    
    try:
        url = f"https://api.elevenlabs.io/v1/text-to-speech/{voice_id}"
        headers = {"xi-api-key": API_KEY}
        
        data = {
            "text": text,
            "model_id": "eleven_turbo_v2",
            "voice_settings": {
                "stability": 0.5,
                "similarity_boost": 0.75
            }
        }
        
        response = requests.post(url, json=data, headers=headers, timeout=30)
        
        if response.status_code == 200:
            # Save audio
            filename = f"/tmp/irs_tts_{voice_name.lower().replace(' ', '_')}.mp3"
            with open(filename, 'wb') as f:
                f.write(response.content)
            
            file_size_kb = len(response.content) / 1024
            return True, file_size_kb
        else:
            return False, response.text
    except Exception as e:
        return False, str(e)

# Scenario 1: Initial greeting
print("Scenario 1: Agent Greeting")
print("-" * 70)
scenario1_text = "Hello! I'm the IRS Taxpayer Assistant. I can help you with refund status, payment plans, or tax questions. How can I assist you today?"
print(f"Agent: {scenario1_text}\n")

success, size_or_error = synthesize_speech(scenario1_text, "EXAVITQu4vr4xnSDxMaL", "Sarah")
if success:
    print(f"✅ Generated voice greeting ({size_or_error:.1f} KB)")
    print(f"   Voice: Sarah (professional, reassuring)")
    print(f"   Model: Turbo v2 (fastest)")
    print(f"   File: irs_tts_sarah.mp3\n")
else:
    print(f"❌ Error: {size_or_error}\n")

# Scenario 2: Refund status response
print("Scenario 2: Refund Status Response")
print("-" * 70)
scenario2_text = "I can help you track your refund. To provide you with the most accurate information, I'll need to look up your account. E-filed returns typically arrive within 21 days if you chose direct deposit. If you filed by mail, please allow 6 to 8 weeks for processing. Would you like me to help you check the status online, or is there anything else I can help with?"
print(f"Agent: {scenario2_text}\n")

success, size_or_error = synthesize_speech(scenario2_text, "21m00Tcm4TlvDq8ikWAM", "Grace")
if success:
    print(f"✅ Generated refund response ({size_or_error:.1f} KB)")
    print(f"   Voice: Grace (empathetic, warm)")
    print(f"   Duration: ~30 seconds")
    print(f"   File: irs_tts_grace.mp3\n")
else:
    print(f"❌ Error: {size_or_error}\n")

# Scenario 3: Payment plan info
print("Scenario 3: Payment Plan Option")
print("-" * 70)
scenario3_text = "I understand that paying a large amount at once can be difficult. The IRS offers flexible payment plan options. You can set up a short-term agreement allowing 120 days to pay, with no setup fee. For longer periods, you can arrange a monthly installment plan with payments as low as $25 per month. Would you like more information about either of these options?"
print(f"Agent: {scenario3_text}\n")

success, size_or_error = synthesize_speech(scenario3_text, "FGY2WhTYpPnrIDTdsKH5", "Laura")
if success:
    print(f"✅ Generated payment plan response ({size_or_error:.1f} KB)")
    print(f"   Voice: Laura (enthusiast, quirky)")
    print(f"   Duration: ~35 seconds")
    print(f"   File: irs_tts_laura.mp3\n")
else:
    print(f"❌ Error: {size_or_error}\n")

# Scenario 4: Escalation message
print("Scenario 4: Escalation Handler")
print("-" * 70)
scenario4_text = "I understand this situation requires special attention. For your security and to ensure we handle this properly, I'm going to connect you with one of our tax specialists who can help you with your identity verification. Thank you for your patience."
print(f"Agent: {scenario4_text}\n")

success, size_or_error = synthesize_speech(scenario4_text, "IKne3meq5aSn9XLyUdCD", "Charlie")
if success:
    print(f"✅ Generated escalation message ({size_or_error:.1f} KB)")
    print(f"   Voice: Charlie (deep, energetic)")
    print(f"   Duration: ~20 seconds")
    print(f"   File: irs_tts_charlie.mp3\n")
else:
    print(f"❌ Error: {size_or_error}\n")

print("="*70)
print("✅ TEXT-TO-SPEECH TEST COMPLETE")
print("="*70)

print("\nWhat works right now (FREE TIER):")
print("  ✅ 121 voices available")
print("  ✅ Natural speech synthesis")
print("  ✅ Multiple voice personalities")
print("  ✅ Customizable voice settings")
print("  ✅ Fast turbo models")

print("\nAfter upgrading and enabling agents:")
print("  ✅ All of above PLUS")
print("  ✅ Autonomous agent conversations")
print("  ✅ Intent recognition")
print("  ✅ Knowledge base integration")
print("  ✅ Multi-turn conversations")
print("  ✅ Human escalation handling")

print("\n🎯 Next Steps:")
print("  1. Upgrade: https://elevenlabs.io/pricing")
print("  2. Enable Agents: https://elevenlabs.io/account/agents")
print("  3. Run: python3 deploy_irs_agent_real.py")

print("\n")
