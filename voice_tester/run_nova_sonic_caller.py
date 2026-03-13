#!/usr/bin/env python3
"""
Nova Sonic Connect Caller - CLI Test Runner

Command-line interface for running AI caller tests against Amazon Connect.
The AI caller uses Amazon Nova Sonic to act as a realistic human caller.

Usage:
    # List available scenarios
    python run_nova_sonic_caller.py --list
    
    # Run a specific scenario
    python run_nova_sonic_caller.py --scenario census_survey_complete
    
    # Run with custom persona
    python run_nova_sonic_caller.py --phone +18332895330 --persona "Maria, 35, checking census survey status"
    
    # Run simulated test (no real call)
    python run_nova_sonic_caller.py --scenario irs_refund_check --mode simulated
    
    # Run PSTN call
    python run_nova_sonic_caller.py --scenario irs_refund_check --mode pstn
    
    # Run with live audio I/O (mic/speakers)
    python run_nova_sonic_caller.py --live

Requirements:
    - Python 3.12+
    - pip install aws-sdk-bedrock-runtime boto3 sounddevice numpy
    - AWS credentials with Bedrock access
    - Nova Sonic model enabled in Bedrock console
"""

import argparse
import asyncio
import json
import os
import sys
import wave
from datetime import datetime
from pathlib import Path

# Add parent to path for imports
sys.path.insert(0, str(Path(__file__).parent))

try:
    import boto3
    import sounddevice as sd
    import numpy as np
    AUDIO_AVAILABLE = True
except ImportError:
    AUDIO_AVAILABLE = False


def print_banner():
    """Print CLI banner"""
    print("""
╔═══════════════════════════════════════════════════════════════╗
║     Nova Sonic Connect Caller - AI Voice Testing              ║
║     Realistic AI callers for Amazon Connect IVR testing       ║
╚═══════════════════════════════════════════════════════════════╝
""")


def list_scenarios():
    """List available test scenarios"""
    from ivr_test_scenarios import SCENARIOS, PERSONAS
    
    print("\n📋 AVAILABLE SCENARIOS:")
    print("=" * 60)
    
    for name, scenario in SCENARIOS.items():
        print(f"\n  🎯 {name}")
        print(f"     {scenario.description}")
        if scenario.phone_number:
            print(f"     📞 Phone: {scenario.phone_number}")
        print(f"     👤 Persona: {scenario.persona.name}")
        print(f"     🎯 Goal: {scenario.persona.goal[:50]}...")
    
    print("\n\n👥 AVAILABLE PERSONAS:")
    print("=" * 60)
    
    for name, persona in PERSONAS.items():
        print(f"\n  {name}")
        print(f"     {persona.name}, {persona.age} - {persona.background[:40]}...")


def parse_custom_persona(persona_str: str):
    """Parse a custom persona string"""
    from nova_sonic_connect_caller import CallerPersona
    
    # Simple format: "Name, age, description"
    parts = [p.strip() for p in persona_str.split(',')]
    
    name = parts[0] if len(parts) > 0 else "Caller"
    age = int(parts[1]) if len(parts) > 1 and parts[1].isdigit() else 35
    background = parts[2] if len(parts) > 2 else "Customer calling for assistance"
    
    return CallerPersona(
        name=name,
        age=age,
        background=background,
        goal="Complete the call based on prompts",
        speaking_style="Natural and conversational"
    )


async def run_simulated_test(scenario):
    """Run a simulated test with Polly-generated IVR audio"""
    from nova_sonic_connect_caller import NovaSonicConnectCaller, save_audio_wav
    
    print("\n🎭 SIMULATED MODE - Using Polly for IVR simulation")
    print("=" * 60)
    
    polly = boto3.client('polly', region_name='us-east-1')
    
    # Simulated IVR prompts based on scenario
    ivr_prompts = get_ivr_prompts_for_scenario(scenario.name)
    prompt_index = [0]
    
    def get_ivr_audio():
        if prompt_index[0] >= len(ivr_prompts):
            return b""
        
        text = ivr_prompts[prompt_index[0]]
        prompt_index[0] += 1
        print(f"\n🤖 IVR says: {text}")
        
        response = polly.synthesize_speech(
            Text=text,
            OutputFormat='pcm',
            VoiceId='Joanna',
            SampleRate='16000',
            Engine='neural'
        )
        return response['AudioStream'].read()
    
    caller_audio_buffer = []
    
    def handle_audio(audio):
        caller_audio_buffer.append(audio)
    
    # Create and run caller
    from nova_sonic_connect_caller import NovaSonicConnectCaller
    caller = NovaSonicConnectCaller(persona=scenario.persona, voice=scenario.voice)
    
    result = await caller.call_simulated(
        ivr_audio_source=get_ivr_audio,
        audio_sink=handle_audio,
        timeout_seconds=scenario.timeout_seconds
    )
    
    # Save audio
    if caller_audio_buffer:
        combined = b''.join(caller_audio_buffer)
        output_dir = Path(__file__).parent.parent / "voice_output"
        output_dir.mkdir(exist_ok=True)
        save_audio_wav(combined, str(output_dir / f"caller_{scenario.name}.wav"))
    
    return result


async def run_pstn_test(scenario, sip_app_id: str, from_phone: str):
    """Run a real PSTN call test"""
    from nova_sonic_connect_caller import NovaSonicConnectCaller
    
    print("\n📞 PSTN MODE - Making real phone call")
    print("=" * 60)
    print(f"   To: {scenario.phone_number}")
    print(f"   From: {from_phone}")
    print(f"   SIP App: {sip_app_id}")
    
    caller = NovaSonicConnectCaller(persona=scenario.persona, voice=scenario.voice)
    
    result = await caller.call_pstn(
        phone_number=scenario.phone_number,
        sip_media_app_id=sip_app_id,
        from_phone=from_phone,
        timeout_seconds=scenario.timeout_seconds
    )
    
    return result


async def run_live_test():
    """Run a live test with microphone and speakers"""
    if not AUDIO_AVAILABLE:
        print("❌ Audio libraries not available (sounddevice, numpy)")
        print("   Install with: pip install sounddevice numpy")
        return None
    
    from nova_sonic_connect_caller import (
        NovaSonicConnectCaller,
        CallerPersona,
        NovaSonicSession,
        save_audio_wav
    )
    
    print("\n🎤 LIVE MODE - Using microphone and speakers")
    print("=" * 60)
    print("This will use your microphone to simulate the IVR")
    print("and play the AI caller's responses through speakers.")
    print()
    print("Press Ctrl+C to stop.")
    print()
    
    # Use default persona
    persona = CallerPersona(
        name="Test Caller",
        age=35,
        background="Testing the system",
        goal="Respond naturally to whatever you say",
        speaking_style="Conversational"
    )
    
    # Create session
    session = NovaSonicSession(
        system_prompt=persona.to_system_prompt(),
        voice="tiffany",
    )
    
    await session.connect()
    await session.setup_session()
    
    # Audio parameters
    input_rate = 16000
    output_rate = 24000
    
    try:
        turn = 0
        while True:
            turn += 1
            print(f"\n--- Turn {turn} ---")
            print("🎤 Recording (speak then wait 2 seconds)...")
            
            # Record from mic
            duration = 5  # seconds
            recording = sd.rec(
                int(duration * input_rate),
                samplerate=input_rate,
                channels=1,
                dtype='int16'
            )
            sd.wait()
            
            # Convert to bytes
            audio_bytes = recording.tobytes()
            
            # Send to Nova Sonic
            print("🔄 Processing...")
            response_audio, response_text = await session.send_audio_turn(audio_bytes)
            
            if response_audio:
                print(f"🗣️ AI says: {response_text}")
                
                # Play through speakers
                samples = np.frombuffer(response_audio, dtype=np.int16).astype(np.float32) / 32768.0
                sd.play(samples, samplerate=output_rate, blocking=True)
            else:
                print("(No response)")
            
    except KeyboardInterrupt:
        print("\n\n👋 Stopping...")
    finally:
        await session.close()
    
    return None


def get_ivr_prompts_for_scenario(scenario_name: str):
    """Get simulated IVR prompts for a scenario"""
    prompts = {
        "irs_refund_check": [
            "Thank you for calling the Treasury Department. For information about tax refunds, press 1. For payment options, press 2. For general inquiries, press 3.",
            "You've selected refund information. Please say or enter your Social Security number.",
            "I found your account. Your refund is being processed and you should receive it within 7 to 10 business days.",
            "Is there anything else I can help you with?",
            "Thank you for calling. Goodbye."
        ],
        "irs_payment_question": [
            "Thank you for calling the Treasury Department. For information about tax refunds, press 1. For payment options, press 2. For general inquiries, press 3.",
            "You've selected payment options. For quarterly estimated payments, press 1. For payment plans, press 2.",
            "Quarterly estimated payments are due four times per year: April 15th, June 15th, September 15th, and January 15th of the following year.",
            "Would you like more information about how to calculate your estimated payments?",
            "You can calculate your estimated payments using Form 1040-ES. Is there anything else I can help you with?",
            "Thank you for calling. Goodbye."
        ],
        "census_survey_complete": [
            "Hello! Welcome to the Census Survey. I will ask you a few questions to help us understand our community better. This will only take a few minutes. Let's get started!",
            "Please tell me, how many people live in your household?",
            "Great, thank you. What is the primary language spoken in your home?",
            "And what is your current employment status? Are you employed, unemployed, retired, or a student?",
            "What is your age range? Under 18, 18 to 34, 35 to 54, 55 to 64, or 65 and older?",
            "Thank you for completing the census survey. Your responses have been recorded and will help us serve our community better. Have a great day!"
        ],
        "census_survey_hesitant": [
            "Hello! Welcome to the Census Survey. I will ask you a few questions.",
            "This survey helps us understand community needs. All responses are confidential and protected by law.",
            "Please tell me, how many people live in your household?",
            "Thank you. What is the primary language spoken in your home?",
            "Thank you for completing the survey. Goodbye."
        ],
        "default": [
            "Thank you for calling. How can I help you today?",
            "I understand. Let me help you with that.",
            "Is there anything else I can assist you with?",
            "Thank you for calling. Goodbye."
        ]
    }
    return prompts.get(scenario_name, prompts["default"])


def print_results(result, scenario_name: str):
    """Print test results"""
    print("\n" + "=" * 60)
    print("📊 TEST RESULTS")
    print("=" * 60)
    
    print(f"\n  Scenario: {scenario_name}")
    print(f"  Status: {result.status}")
    print(f"  Duration: {result.duration_seconds:.1f} seconds")
    print(f"  Turns: {len(result.transcript)}")
    
    if result.errors:
        print("\n  ⚠️  Errors:")
        for e in result.errors:
            print(f"      - {e}")
    
    print("\n📜 TRANSCRIPT:")
    print("-" * 60)
    for entry in result.transcript:
        role = entry.get('role', 'unknown')
        text = entry.get('text', '')
        icon = "🤖" if role == 'ivr' else "🗣️"
        print(f"  {icon} {role.upper()}: {text}")
    
    print("\n" + "=" * 60)
    
    if result.status == 'completed':
        print("✅ TEST PASSED")
    else:
        print(f"⚠️  TEST STATUS: {result.status}")


def main():
    """Main CLI entry point"""
    parser = argparse.ArgumentParser(
        description="Nova Sonic Connect Caller - AI Voice Testing CLI",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  # List scenarios
  python run_nova_sonic_caller.py --list
  
  # Run simulated test
  python run_nova_sonic_caller.py --scenario census_survey_complete --mode simulated
  
  # Run real PSTN call
  python run_nova_sonic_caller.py --scenario irs_refund_check --mode pstn
  
  # Live mic/speaker test
  python run_nova_sonic_caller.py --live
"""
    )
    
    parser.add_argument('--list', action='store_true', help='List available scenarios')
    parser.add_argument('--scenario', '-s', help='Scenario name to run')
    parser.add_argument('--mode', '-m', choices=['simulated', 'pstn', 'webrtc'], 
                       default='simulated', help='Test mode')
    parser.add_argument('--live', action='store_true', 
                       help='Live mode with microphone/speakers')
    parser.add_argument('--phone', '-p', help='Override phone number')
    parser.add_argument('--persona', help='Custom persona: "Name, age, description"')
    parser.add_argument('--sip-app-id', 
                       default='3998e0ab-53e5-4f68-a2fd-1745f73e7aa1',
                       help='Chime SIP Media App ID')
    parser.add_argument('--from-phone', 
                       default='+13602098836',
                       help='Caller ID phone number')
    parser.add_argument('--verbose', '-v', action='store_true', help='Verbose output')
    
    args = parser.parse_args()
    
    # Setup logging
    if args.verbose:
        import logging
        logging.basicConfig(level=logging.DEBUG)
    
    print_banner()
    
    # Handle commands
    if args.list:
        list_scenarios()
        return 0
    
    if args.live:
        asyncio.run(run_live_test())
        return 0
    
    if not args.scenario and not args.phone:
        print("❌ Please specify --scenario or --phone")
        print("   Use --list to see available scenarios")
        return 1
    
    # Get or build scenario
    from ivr_test_scenarios import get_scenario, IVRScenario
    
    if args.scenario:
        try:
            scenario = get_scenario(args.scenario)
        except ValueError as e:
            print(f"❌ {e}")
            return 1
    else:
        # Build from args
        from nova_sonic_connect_caller import CallerPersona
        
        if args.persona:
            persona = parse_custom_persona(args.persona)
        else:
            persona = CallerPersona(
                name="Test Caller",
                goal="Complete the interaction",
                background="Customer calling for assistance"
            )
        
        scenario = IVRScenario(
            name="custom",
            description="Custom test scenario",
            phone_number=args.phone or "",
            persona=persona,
        )
    
    # Override phone if specified
    if args.phone:
        scenario.phone_number = args.phone
    
    # Print scenario info
    print(f"🎯 Scenario: {scenario.name}")
    print(f"📞 Target: {scenario.phone_number or '(simulated)'}")
    print(f"👤 Persona: {scenario.persona.name}")
    print(f"🎯 Goal: {scenario.persona.goal}")
    print(f"🔧 Mode: {args.mode}")
    print()
    
    # Run test
    async def run():
        if args.mode == 'simulated':
            return await run_simulated_test(scenario)
        elif args.mode == 'pstn':
            if not scenario.phone_number:
                print("❌ PSTN mode requires a phone number")
                return None
            return await run_pstn_test(
                scenario, 
                args.sip_app_id, 
                args.from_phone
            )
        elif args.mode == 'webrtc':
            print("⚠️  WebRTC mode not fully implemented")
            return await run_simulated_test(scenario)
    
    result = asyncio.run(run())
    
    if result:
        print_results(result, scenario.name)
        return 0 if result.status == 'completed' else 1
    
    return 1


if __name__ == "__main__":
    sys.exit(main())
