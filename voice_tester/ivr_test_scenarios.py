#!/usr/bin/env python3
"""
IVR Test Scenarios using Nova Sonic AI Callers

Pre-built scenarios for testing common IVR patterns with realistic AI callers.
Each scenario defines a persona, goal, and expected flow - the AI handles
the actual conversation dynamically.

Usage:
    from ivr_test_scenarios import get_scenario, run_scenario
    
    # Get a pre-built scenario
    scenario = get_scenario("irs_refund_check")
    
    # Or build a custom one
    scenario = build_scenario(
        name="My Custom Test",
        persona_type="concerned_customer",
        goal="Report a billing discrepancy",
        phone_number="+18001234567"
    )
    
    # Run it
    result = await run_scenario(scenario, method="pstn")
"""

from dataclasses import dataclass, field
from typing import Dict, List, Optional, Any
from nova_sonic_connect_caller import (
    NovaSonicConnectCaller,
    CallerPersona,
    CallResult
)


@dataclass
class IVRScenario:
    """A complete IVR test scenario"""
    name: str
    description: str
    
    # Target
    phone_number: str = ""
    instance_id: str = ""
    contact_flow_id: str = ""
    
    # Caller definition
    persona: CallerPersona = field(default_factory=CallerPersona)
    voice: str = "female"
    
    # Expected behavior (for validation)
    expected_steps: List[str] = field(default_factory=list)
    success_criteria: str = ""
    
    # Execution settings
    timeout_seconds: int = 180
    max_turns: int = 20
    
    # Metadata
    tags: List[str] = field(default_factory=list)


# ============================================================================
# PRE-BUILT PERSONAS - Common caller types
# ============================================================================

PERSONAS = {
    "patient_senior": CallerPersona(
        name="Dorothy",
        age=72,
        background="Retired teacher, not very tech-savvy but patient",
        speaking_style="Speaks slowly and clearly, asks for repetition when confused",
        patience_level="high",
        verbosity="verbose"
    ),
    
    "busy_professional": CallerPersona(
        name="Michael",
        age=38,
        background="Sales executive with limited time",
        speaking_style="Direct, efficient, slightly impatient with long menus",
        patience_level="low",
        verbosity="terse"
    ),
    
    "anxious_customer": CallerPersona(
        name="Sarah",
        age=29,
        background="First-time caller, nervous about the process",
        speaking_style="Hesitant, asks clarifying questions, apologizes often",
        patience_level="medium",
        verbosity="verbose"
    ),
    
    "confident_expert": CallerPersona(
        name="James",
        age=45,
        background="Frequent caller who knows the system",
        speaking_style="Confident, uses shortcuts, skips unnecessary prompts",
        patience_level="medium",
        verbosity="terse"
    ),
    
    "non_native_speaker": CallerPersona(
        name="Ana",
        age=35,
        background="ESL speaker, fluent but occasional hesitation",
        speaking_style="Careful pronunciation, sometimes asks for slower speech",
        patience_level="high",
        verbosity="concise"
    ),
    
    "frustrated_repeat_caller": CallerPersona(
        name="Kevin",
        age=52,
        background="Called multiple times about same issue, increasingly frustrated",
        speaking_style="Expresses frustration, mentions previous calls, wants escalation",
        patience_level="low",
        verbosity="verbose"
    ),
}


# ============================================================================
# PRE-BUILT SCENARIOS - Ready to use test cases
# ============================================================================

SCENARIOS: Dict[str, IVRScenario] = {}

# ----- IRS / Tax Related -----

SCENARIOS["irs_refund_check"] = IVRScenario(
    name="IRS Refund Status Check",
    description="Caller checking on tax refund status",
    phone_number="+18332896602",  # Treasury IVR
    persona=CallerPersona(
        name="Jennifer",
        age=42,
        background="Filed taxes in February, expecting refund",
        goal="Check on tax refund status for 2023 return",
        context="SSN ends in 4532, expecting ~$2,400 refund, filed 6 weeks ago",
        speaking_style="Polite but eager to get information",
        patience_level="medium",
        verbosity="concise"
    ),
    voice="female",
    expected_steps=[
        "Navigate main menu to refund status",
        "Provide SSN when prompted",
        "Receive refund status information",
        "End call with confirmation"
    ],
    success_criteria="Receives refund status information or estimated date",
    tags=["irs", "refund", "treasury"]
)

SCENARIOS["irs_payment_question"] = IVRScenario(
    name="IRS Payment Question",
    description="Caller with question about tax payment",
    phone_number="+18332896602",
    persona=CallerPersona(
        name="Robert",
        age=58,
        background="Small business owner with quarterly payment question",
        goal="Understand estimated tax payment requirements",
        context="Recently started freelancing, needs quarterly payment info",
        speaking_style="Professional, methodical, takes notes",
        patience_level="high",
        verbosity="concise"
    ),
    voice="male",
    expected_steps=[
        "Navigate to payment information",
        "Get quarterly payment schedule",
        "Understand payment methods"
    ],
    success_criteria="Receives payment information or transfer to specialist",
    tags=["irs", "payments", "treasury"]
)


# ----- Census Survey -----

SCENARIOS["census_survey_complete"] = IVRScenario(
    name="Census Survey - Cooperative",
    description="Caller completing census survey cooperatively",
    phone_number="+18332895330",  # Census survey line
    persona=CallerPersona(
        name="Margaret",
        age=45,
        background="Homeowner, received census notification",
        goal="Complete the census survey fully and accurately",
        context="Household of 4 (self, spouse, 2 children), English speakers, employed",
        speaking_style="Cooperative, provides clear answers",
        patience_level="high",
        verbosity="concise"
    ),
    voice="female",
    expected_steps=[
        "Listen to welcome message",
        "Answer household size question",
        "Answer language question",
        "Answer employment question",
        "Complete survey"
    ],
    success_criteria="Survey completion confirmed",
    tags=["census", "survey", "full_completion"]
)

SCENARIOS["census_survey_hesitant"] = IVRScenario(
    name="Census Survey - Hesitant",
    description="Caller who is hesitant about providing information",
    phone_number="+18332895330",
    persona=CallerPersona(
        name="William",
        age=67,
        background="Privacy-conscious retiree, skeptical of government surveys",
        goal="Complete survey but ask questions about privacy first",
        context="Lives alone, but wants to know why info is needed",
        speaking_style="Asks clarifying questions, needs reassurance",
        patience_level="medium",
        verbosity="verbose"
    ),
    voice="male",
    expected_steps=[
        "Ask about privacy before answering",
        "Eventually provide answers",
        "Complete survey with hesitation"
    ],
    success_criteria="Survey completed despite hesitation",
    tags=["census", "survey", "edge_case"]
)


# ----- General Customer Service -----

SCENARIOS["balance_inquiry"] = IVRScenario(
    name="Account Balance Inquiry",
    description="Caller checking account balance",
    phone_number="",  # Set per deployment
    persona=CallerPersona(
        name="Linda",
        age=34,
        background="Regular customer checking balance",
        goal="Check current account balance",
        context="Account number: 1234567890, PIN: 1234",
        speaking_style="Efficient, knows the process",
        patience_level="medium",
        verbosity="terse"
    ),
    voice="female",
    expected_steps=[
        "Navigate to balance inquiry",
        "Enter account number",
        "Enter PIN",
        "Receive balance"
    ],
    success_criteria="Balance amount received",
    tags=["banking", "balance", "self_service"]
)

SCENARIOS["speak_to_agent"] = IVRScenario(
    name="Request Live Agent",
    description="Caller who wants to speak to a human",
    phone_number="",
    persona=CallerPersona(
        name="David",
        age=50,
        background="Has complex issue that needs human help",
        goal="Get transferred to a live agent as quickly as possible",
        context="Issue too complex for automated system",
        speaking_style="Firm but polite, repeatedly asks for agent",
        patience_level="low",
        verbosity="terse"
    ),
    voice="male",
    expected_steps=[
        "Try to navigate menu quickly",
        "Say 'agent' or 'representative'",
        "Get transferred or queued"
    ],
    success_criteria="Connected to agent queue or callback scheduled",
    tags=["escalation", "live_agent"]
)


# ----- Edge Cases / Stress Tests -----

SCENARIOS["confused_caller"] = IVRScenario(
    name="Confused Elderly Caller",
    description="Tests IVR's handling of confused or off-topic responses",
    phone_number="",
    persona=CallerPersona(
        name="Eleanor",
        age=82,
        background="Has memory issues, not sure which service she called",
        goal="Complete some kind of transaction, but confused about what",
        context="Meant to call about electricity bill, called wrong number",
        speaking_style="Confused, provides irrelevant answers, needs patience",
        patience_level="high",
        verbosity="verbose"
    ),
    voice="female",
    expected_steps=[
        "Provide confused responses",
        "Eventually get redirected or helped"
    ],
    success_criteria="IVR handles gracefully without hanging up",
    tags=["edge_case", "accessibility", "stress_test"]
)

SCENARIOS["silent_caller"] = IVRScenario(
    name="Silent/Shy Caller",
    description="Caller who takes long pauses or speaks very quietly",
    phone_number="",
    persona=CallerPersona(
        name="Quiet Tom",
        age=25,
        background="Anxious caller who speaks softly",
        goal="Complete transaction despite speaking quietly",
        context="Has social anxiety, prefers minimal interaction",
        speaking_style="Very quiet, long pauses, minimal words",
        patience_level="high",
        verbosity="terse"
    ),
    voice="male",
    expected_steps=[
        "Respond after long pauses",
        "Use single-word answers"
    ],
    success_criteria="IVR waits for responses and accepts quiet speech",
    tags=["edge_case", "accessibility"]
)

SCENARIOS["dtmf_preference"] = IVRScenario(
    name="DTMF-Preferring Caller",
    description="Caller who prefers pressing buttons over speaking",
    phone_number="",
    persona=CallerPersona(
        name="Tech Tom",
        age=30,
        background="Developer who knows DTMF is more reliable",
        goal="Navigate using numbers when possible",
        context="Prefers pressing 1, 2, 3 over speaking options",
        speaking_style="Says numbers clearly: 'one', 'two', 'three'",
        patience_level="medium",
        verbosity="terse"
    ),
    voice="male",
    expected_steps=[
        "Say numbers instead of option names",
        "Use DTMF-style navigation"
    ],
    success_criteria="Navigation works with spoken numbers",
    tags=["dtmf", "navigation"]
)


# ============================================================================
# UTILITY FUNCTIONS
# ============================================================================

def get_scenario(name: str) -> IVRScenario:
    """Get a pre-built scenario by name"""
    if name not in SCENARIOS:
        available = ", ".join(SCENARIOS.keys())
        raise ValueError(f"Unknown scenario '{name}'. Available: {available}")
    return SCENARIOS[name]


def list_scenarios(tags: List[str] = None) -> List[str]:
    """List available scenarios, optionally filtered by tags"""
    if tags:
        return [
            name for name, scenario in SCENARIOS.items()
            if any(tag in scenario.tags for tag in tags)
        ]
    return list(SCENARIOS.keys())


def get_persona(name: str) -> CallerPersona:
    """Get a pre-built persona by name"""
    if name not in PERSONAS:
        available = ", ".join(PERSONAS.keys())
        raise ValueError(f"Unknown persona '{name}'. Available: {available}")
    return PERSONAS[name]


def build_scenario(
    name: str,
    phone_number: str,
    persona_type: str = "confident_expert",
    goal: str = "Complete the call successfully",
    context: str = "",
    voice: str = "female",
    **kwargs
) -> IVRScenario:
    """
    Build a custom scenario from components.
    
    Args:
        name: Scenario name
        phone_number: Target phone number
        persona_type: Key from PERSONAS dict
        goal: What the caller wants to achieve
        context: Additional context (account numbers, etc.)
        voice: 'male' or 'female'
        **kwargs: Additional CallerPersona fields
        
    Returns:
        Configured IVRScenario
    """
    # Get base persona
    persona = get_persona(persona_type)
    
    # Customize
    persona.goal = goal
    persona.context = context
    for key, value in kwargs.items():
        if hasattr(persona, key):
            setattr(persona, key, value)
    
    return IVRScenario(
        name=name,
        description=f"Custom scenario: {goal}",
        phone_number=phone_number,
        persona=persona,
        voice=voice,
        tags=["custom"]
    )


async def run_scenario(
    scenario: IVRScenario,
    method: str = "pstn",
    sip_media_app_id: str = "3998e0ab-53e5-4f68-a2fd-1745f73e7aa1",
    from_phone: str = "+13602098836",
) -> CallResult:
    """
    Execute a test scenario.
    
    Args:
        scenario: The scenario to run
        method: 'pstn' or 'webrtc'
        sip_media_app_id: Chime SIP Media App ID (for PSTN)
        from_phone: Caller ID (for PSTN)
        
    Returns:
        CallResult with transcript and analysis
    """
    # Create caller
    caller = NovaSonicConnectCaller(
        persona=scenario.persona,
        voice=scenario.voice,
    )
    
    # Execute based on method
    if method == "pstn":
        if not scenario.phone_number:
            raise ValueError("PSTN method requires phone_number in scenario")
        
        return await caller.call_pstn(
            phone_number=scenario.phone_number,
            sip_media_app_id=sip_media_app_id,
            from_phone=from_phone,
            timeout_seconds=scenario.timeout_seconds,
        )
    
    elif method == "webrtc":
        if not scenario.instance_id or not scenario.contact_flow_id:
            raise ValueError("WebRTC method requires instance_id and contact_flow_id")
        
        return await caller.call_webrtc(
            instance_id=scenario.instance_id,
            contact_flow_id=scenario.contact_flow_id,
            timeout_seconds=scenario.timeout_seconds,
        )
    
    else:
        raise ValueError(f"Unknown method: {method}")


def analyze_result(result: CallResult, scenario: IVRScenario) -> Dict[str, Any]:
    """
    Analyze call result against scenario expectations.
    
    Returns analysis dict with pass/fail and details.
    """
    analysis = {
        "scenario": scenario.name,
        "status": result.status,
        "duration": result.duration_seconds,
        "turn_count": len(result.transcript),
        "passed": False,
        "issues": [],
        "notes": []
    }
    
    # Check for errors
    if result.errors:
        analysis["issues"].extend(result.errors)
    
    # Check duration
    if result.duration_seconds < 5:
        analysis["issues"].append("Call too short - may have failed to connect")
    elif result.duration_seconds > scenario.timeout_seconds * 0.9:
        analysis["issues"].append("Call nearly timed out")
    
    # Check transcript for success indicators
    transcript_text = " ".join(t.get("text", "") for t in result.transcript).lower()
    
    # Look for common success phrases
    success_indicators = ["thank you", "goodbye", "completed", "confirmed"]
    found_success = any(ind in transcript_text for ind in success_indicators)
    
    # Look for common failure phrases
    failure_indicators = ["error", "sorry we couldn't", "invalid", "try again"]
    found_failure = any(ind in transcript_text for ind in failure_indicators)
    
    if found_failure:
        analysis["issues"].append("Potential failure detected in transcript")
    
    # Determine pass/fail
    analysis["passed"] = (
        result.status in ("completed", "hangup") and
        not result.errors and
        len(result.transcript) >= 2 and
        found_success and
        not found_failure
    )
    
    return analysis


# ============================================================================
# CLI / MAIN
# ============================================================================

if __name__ == "__main__":
    import argparse
    import asyncio
    import json
    
    parser = argparse.ArgumentParser(description="Run IVR test scenarios")
    parser.add_argument(
        "scenario",
        nargs="?",
        help="Scenario name to run (or 'list' to see all)"
    )
    parser.add_argument(
        "--method",
        choices=["pstn", "webrtc"],
        default="pstn",
        help="Call method"
    )
    parser.add_argument(
        "--phone",
        help="Override phone number"
    )
    parser.add_argument(
        "--tags",
        nargs="+",
        help="Filter scenarios by tags"
    )
    
    args = parser.parse_args()
    
    if not args.scenario or args.scenario == "list":
        print("\n📋 Available Scenarios:")
        print("=" * 60)
        for name in list_scenarios(args.tags):
            s = SCENARIOS[name]
            tags = ", ".join(s.tags)
            print(f"\n  {name}")
            print(f"    {s.description}")
            print(f"    Tags: {tags}")
            if s.phone_number:
                print(f"    Phone: {s.phone_number}")
        print()
    else:
        # Run scenario
        scenario = get_scenario(args.scenario)
        if args.phone:
            scenario.phone_number = args.phone
        
        print(f"\n🎯 Running: {scenario.name}")
        print(f"📞 Target: {scenario.phone_number}")
        print(f"👤 Persona: {scenario.persona.name}")
        print(f"🎯 Goal: {scenario.persona.goal}")
        print("=" * 60)
        
        async def run():
            result = await run_scenario(scenario, method=args.method)
            
            print("\n📊 Results:")
            print(f"  Status: {result.status}")
            print(f"  Duration: {result.duration_seconds:.1f}s")
            
            print("\n📜 Transcript:")
            for t in result.transcript:
                icon = "🤖" if t["role"] == "ivr" else "🗣️"
                print(f"  {icon} {t['role'].upper()}: {t['text']}")
            
            analysis = analyze_result(result, scenario)
            print(f"\n✅ Passed: {analysis['passed']}")
            if analysis["issues"]:
                print("⚠️  Issues:")
                for issue in analysis["issues"]:
                    print(f"    - {issue}")
        
        asyncio.run(run())
