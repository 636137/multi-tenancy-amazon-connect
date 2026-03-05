"""
Test Generator Lambda

Takes parsed flow data and generates Nova Sonic test scenarios
with AI-powered caller configurations.
"""
import json
import boto3
import logging
from typing import Dict, List, Any
from dataclasses import dataclass, asdict
import uuid

logger = logging.getLogger()
logger.setLevel(logging.INFO)

dynamodb = boto3.resource('dynamodb')


@dataclass
class CallerPersona:
    """AI caller persona configuration."""
    name: str
    voice_id: str  # Polly voice
    speaking_rate: str  # slow, normal, fast
    patience: str  # impatient, normal, patient
    behavior: str  # cooperative, confused, hostile


@dataclass  
class TestStep:
    """A single step in the test."""
    action: str  # listen, speak, dtmf, wait
    expect_prompt: str = ""
    response_text: str = ""
    dtmf_digits: str = ""
    wait_seconds: int = 0
    ai_behavior: str = ""  # Instructions for AI if dynamic


@dataclass
class TestScenario:
    """Complete test scenario."""
    id: str
    name: str
    description: str
    phone_number: str
    persona: CallerPersona
    steps: List[TestStep]
    success_criteria: List[str]
    timeout_seconds: int = 180


def handler(event, context):
    """Generate test scenarios from parsed flow."""
    
    logger.info(f"Event: {json.dumps(event)}")
    
    try:
        body = json.loads(event.get('body', '{}'))
        
        parsed_flow = body.get('parsed_flow', {})
        phone_number = body.get('phone_number', '')
        test_config = body.get('config', {})
        
        if not parsed_flow:
            return error_response(400, "Missing parsed_flow")
        if not phone_number:
            return error_response(400, "Missing phone_number")
        
        scenarios = generate_scenarios(parsed_flow, phone_number, test_config)
        
        # Save to DynamoDB
        if test_config.get('save', True):
            save_scenarios(scenarios)
        
        return success_response({
            'scenarios': [asdict(s) for s in scenarios],
            'count': len(scenarios)
        })
        
    except Exception as e:
        logger.error(f"Error generating tests: {e}", exc_info=True)
        return error_response(500, str(e))


def generate_scenarios(parsed_flow: Dict, phone_number: str, config: Dict) -> List[TestScenario]:
    """Generate test scenarios from parsed flow data."""
    
    scenarios = []
    test_paths = parsed_flow.get('test_paths', [])
    prompts = parsed_flow.get('prompts', [])
    flow_name = parsed_flow.get('name', 'Unknown')
    
    # Default persona
    persona = CallerPersona(
        name=config.get('persona_name', 'Test Caller'),
        voice_id=config.get('voice_id', 'Joanna'),
        speaking_rate=config.get('speaking_rate', 'normal'),
        patience=config.get('patience', 'patient'),
        behavior=config.get('behavior', 'cooperative')
    )
    
    for i, path in enumerate(test_paths):
        scenario_id = f"test-{uuid.uuid4().hex[:8]}"
        
        steps = convert_path_to_steps(path, prompts, persona)
        
        success_criteria = path.get('expected_prompts', [])
        if not success_criteria:
            success_criteria = ['call_connected', 'received_response']
        
        scenario = TestScenario(
            id=scenario_id,
            name=f"{flow_name}: {path.get('name', f'Test {i+1}')}",
            description=path.get('description', ''),
            phone_number=phone_number,
            persona=persona,
            steps=steps,
            success_criteria=success_criteria,
            timeout_seconds=config.get('timeout', 180)
        )
        
        scenarios.append(scenario)
    
    # Add AI-driven exploratory test
    if config.get('include_ai_test', True):
        ai_scenario = create_ai_exploratory_test(flow_name, phone_number, prompts, persona)
        scenarios.append(ai_scenario)
    
    return scenarios


def convert_path_to_steps(path: Dict, prompts: List[str], persona: CallerPersona) -> List[TestStep]:
    """Convert a test path to executable steps."""
    
    steps = []
    
    # Initial listen for greeting
    steps.append(TestStep(
        action='listen',
        expect_prompt=prompts[0] if prompts else 'greeting',
        ai_behavior='Wait for the system greeting'
    ))
    
    for path_step in path.get('steps', []):
        action = path_step.get('action', '')
        
        if action == 'dtmf':
            # Listen for prompt, then press digits
            steps.append(TestStep(
                action='listen',
                expect_prompt=path_step.get('after_prompt', 'menu'),
                ai_behavior='Listen for menu options'
            ))
            steps.append(TestStep(
                action='dtmf',
                dtmf_digits=str(path_step.get('value', '1')),
                ai_behavior=f"Press {path_step.get('value', '1')}"
            ))
        
        elif action == 'speak':
            steps.append(TestStep(
                action='speak',
                response_text=path_step.get('text', ''),
                ai_behavior=f"Say: {path_step.get('text', '')}"
            ))
            steps.append(TestStep(
                action='listen',
                expect_prompt=path_step.get('wait_for', 'response'),
                ai_behavior='Listen for response'
            ))
        
        elif action == 'wait':
            steps.append(TestStep(
                action='wait',
                wait_seconds=path_step.get('seconds', 10),
                ai_behavior='Stay silent to test timeout'
            ))
    
    # Final step - listen for completion
    steps.append(TestStep(
        action='listen',
        expect_prompt='goodbye|thank you|end',
        ai_behavior='Listen for call completion'
    ))
    
    return steps


def create_ai_exploratory_test(flow_name: str, phone_number: str, 
                               prompts: List[str], persona: CallerPersona) -> TestScenario:
    """Create an AI-driven exploratory test."""
    
    # Generate AI instructions based on prompts
    prompt_context = "\n".join([f"- {p}" for p in prompts[:10]])
    
    ai_instructions = f"""
You are testing an IVR system. Expected prompts include:
{prompt_context}

Your goal:
1. Listen to each prompt carefully
2. Respond appropriately (speak or press digits)
3. Try to complete a successful interaction
4. Note any errors or unexpected behavior

Be {persona.patience} and {persona.behavior}.
"""
    
    steps = [
        TestStep(
            action='ai_driven',
            ai_behavior=ai_instructions,
            expect_prompt='any'
        )
    ]
    
    return TestScenario(
        id=f"ai-explore-{uuid.uuid4().hex[:8]}",
        name=f"{flow_name}: AI Exploratory Test",
        description="AI-driven test that dynamically responds to the flow",
        phone_number=phone_number,
        persona=persona,
        steps=steps,
        success_criteria=['call_completed', 'no_errors'],
        timeout_seconds=300
    )


def save_scenarios(scenarios: List[TestScenario]):
    """Save scenarios to DynamoDB."""
    
    try:
        table = dynamodb.Table('flow-test-scenarios')
        
        with table.batch_writer() as batch:
            for scenario in scenarios:
                batch.put_item(Item={
                    'scenario_id': scenario.id,
                    'name': scenario.name,
                    'phone_number': scenario.phone_number,
                    'scenario_data': json.dumps(asdict(scenario)),
                    'status': 'pending',
                    'created_at': str(uuid.uuid1())
                })
        
        logger.info(f"Saved {len(scenarios)} scenarios to DynamoDB")
        
    except Exception as e:
        logger.warning(f"Could not save to DynamoDB: {e}")


def success_response(data: Any) -> Dict:
    """Return success response."""
    return {
        'statusCode': 200,
        'headers': {
            'Content-Type': 'application/json',
            'Access-Control-Allow-Origin': '*',
            'Access-Control-Allow-Headers': 'Content-Type',
            'Access-Control-Allow-Methods': 'POST, OPTIONS'
        },
        'body': json.dumps(data, default=str)
    }


def error_response(status: int, message: str) -> Dict:
    """Return error response."""
    return {
        'statusCode': status,
        'headers': {
            'Content-Type': 'application/json',
            'Access-Control-Allow-Origin': '*'
        },
        'body': json.dumps({'error': message})
    }
