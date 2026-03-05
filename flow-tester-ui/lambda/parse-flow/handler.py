"""
Connect Flow Parser Lambda

Parses Amazon Connect contact flow JSON or Lex bot exports
to extract testable paths and generate test scenarios.
"""
import json
import boto3
import logging
from typing import Dict, List, Any, Optional
from dataclasses import dataclass, asdict

logger = logging.getLogger()
logger.setLevel(logging.INFO)

s3 = boto3.client('s3')


@dataclass
class FlowPrompt:
    """A prompt or message in the flow."""
    id: str
    text: str
    ssml: Optional[str] = None
    type: str = "text"  # text, ssml, dynamic


@dataclass
class FlowBranch:
    """A branch/option in the flow."""
    condition: str  # "1", "timeout", "error", "default"
    target_block: str
    description: str = ""


@dataclass
class FlowBlock:
    """A block in the contact flow."""
    id: str
    type: str
    name: str
    prompts: List[FlowPrompt]
    branches: List[FlowBranch]
    parameters: Dict[str, Any]


@dataclass
class ParsedFlow:
    """Parsed contact flow structure."""
    name: str
    description: str
    entry_point: str
    blocks: List[FlowBlock]
    prompts: List[str]  # All unique prompts
    menu_options: Dict[str, List[str]]  # Menu ID -> options
    test_paths: List[Dict[str, Any]]  # Generated test paths


def handler(event, context):
    """Parse uploaded flow and extract test paths."""
    
    logger.info(f"Event: {json.dumps(event)}")
    
    try:
        body = json.loads(event.get('body', '{}'))
        flow_type = body.get('type', 'connect')  # connect or lex
        
        if 'flow_json' in body:
            # Direct JSON upload
            flow_data = body['flow_json']
        elif 's3_key' in body:
            # S3 reference
            bucket = body.get('bucket', 'flow-tester-uploads')
            response = s3.get_object(Bucket=bucket, Key=body['s3_key'])
            flow_data = json.loads(response['Body'].read().decode('utf-8'))
        else:
            return error_response(400, "Missing flow_json or s3_key")
        
        if flow_type == 'connect':
            parsed = parse_connect_flow(flow_data)
        elif flow_type == 'lex':
            parsed = parse_lex_bot(flow_data)
        else:
            return error_response(400, f"Unknown flow type: {flow_type}")
        
        return success_response(asdict(parsed))
        
    except Exception as e:
        logger.error(f"Error parsing flow: {e}", exc_info=True)
        return error_response(500, str(e))


def parse_connect_flow(flow_data: Dict) -> ParsedFlow:
    """Parse Amazon Connect contact flow JSON."""
    
    # Handle both export formats
    if 'ContactFlow' in flow_data:
        flow = flow_data['ContactFlow']
        content = json.loads(flow.get('Content', '{}'))
    elif 'Content' in flow_data:
        flow = flow_data
        content = json.loads(flow['Content']) if isinstance(flow['Content'], str) else flow['Content']
    else:
        content = flow_data
        flow = {'Name': 'Unknown', 'Description': ''}
    
    blocks = []
    all_prompts = []
    menu_options = {}
    
    actions = content.get('Actions', [])
    
    for action in actions:
        block = parse_connect_action(action)
        blocks.append(block)
        
        # Collect prompts
        for prompt in block.prompts:
            if prompt.text and prompt.text not in all_prompts:
                all_prompts.append(prompt.text)
        
        # Collect menu options
        if block.type in ('GetUserInput', 'GetParticipantInput'):
            options = [b.condition for b in block.branches if b.condition.isdigit()]
            if options:
                menu_options[block.id] = options
    
    # Generate test paths
    test_paths = generate_test_paths(blocks, menu_options)
    
    # Find entry point
    entry_point = content.get('StartAction', '')
    if not entry_point and actions:
        entry_point = actions[0].get('Identifier', '')
    
    return ParsedFlow(
        name=flow.get('Name', 'Unknown Flow'),
        description=flow.get('Description', ''),
        entry_point=entry_point,
        blocks=blocks,
        prompts=all_prompts,
        menu_options=menu_options,
        test_paths=test_paths
    )


def parse_connect_action(action: Dict) -> FlowBlock:
    """Parse a single Connect flow action into a FlowBlock."""
    
    action_type = action.get('Type', 'Unknown')
    identifier = action.get('Identifier', '')
    parameters = action.get('Parameters', {})
    
    prompts = []
    branches = []
    
    # Extract prompts based on action type
    if action_type == 'MessageParticipant':
        text = parameters.get('Text', '')
        if text:
            prompts.append(FlowPrompt(id=identifier, text=text, type='text'))
        
        ssml = parameters.get('SSML', '')
        if ssml:
            prompts.append(FlowPrompt(id=identifier, text='', ssml=ssml, type='ssml'))
    
    elif action_type in ('GetUserInput', 'GetParticipantInput'):
        # Menu prompt
        text = parameters.get('Text', parameters.get('Prompt', {}).get('Text', ''))
        if text:
            prompts.append(FlowPrompt(id=identifier, text=text, type='menu'))
    
    elif action_type == 'InvokeLambdaFunction':
        # Lambda integration - note for testing
        prompts.append(FlowPrompt(
            id=identifier, 
            text=f"[Lambda: {parameters.get('LambdaFunctionARN', 'unknown')}]",
            type='lambda'
        ))
    
    elif action_type == 'TransferToQueue':
        prompts.append(FlowPrompt(id=identifier, text="[Transfer to Queue]", type='transfer'))
    
    # Extract branches/transitions
    transitions = action.get('Transitions', {})
    
    # NextAction (default transition)
    if 'NextAction' in transitions:
        branches.append(FlowBranch(
            condition='default',
            target_block=transitions['NextAction'],
            description='Default next step'
        ))
    
    # Conditions (menu options, errors, etc.)
    for condition in transitions.get('Conditions', []):
        cond_type = condition.get('ConditionType', '')
        
        if cond_type == 'Equals':
            value = condition.get('ConditionValue', '')
            branches.append(FlowBranch(
                condition=str(value),
                target_block=condition.get('NextAction', ''),
                description=f"Option {value}"
            ))
    
    # Error handling
    if 'Errors' in transitions:
        for error in transitions['Errors']:
            branches.append(FlowBranch(
                condition=f"error:{error.get('ErrorType', 'unknown')}",
                target_block=error.get('NextAction', ''),
                description=f"Error: {error.get('ErrorType', '')}"
            ))
    
    return FlowBlock(
        id=identifier,
        type=action_type,
        name=action.get('Name', action_type),
        prompts=prompts,
        branches=branches,
        parameters=parameters
    )


def parse_lex_bot(bot_data: Dict) -> ParsedFlow:
    """Parse Lex bot export to extract intents and slots."""
    
    bot_name = bot_data.get('name', bot_data.get('botName', 'Unknown Bot'))
    
    blocks = []
    all_prompts = []
    menu_options = {}
    
    # Handle Lex V2 format
    if 'botLocales' in bot_data:
        for locale in bot_data.get('botLocales', []):
            for intent in locale.get('intents', []):
                block, intent_prompts = parse_lex_intent(intent)
                blocks.append(block)
                all_prompts.extend(intent_prompts)
    
    # Handle Lex V1 format
    elif 'intents' in bot_data:
        for intent in bot_data.get('intents', []):
            block, intent_prompts = parse_lex_intent(intent)
            blocks.append(block)
            all_prompts.extend(intent_prompts)
    
    # Generate test paths from intents
    test_paths = generate_lex_test_paths(blocks)
    
    return ParsedFlow(
        name=bot_name,
        description=bot_data.get('description', ''),
        entry_point='greeting',
        blocks=blocks,
        prompts=list(set(all_prompts)),
        menu_options=menu_options,
        test_paths=test_paths
    )


def parse_lex_intent(intent: Dict) -> tuple:
    """Parse a Lex intent into a FlowBlock."""
    
    intent_name = intent.get('name', intent.get('intentName', 'Unknown'))
    prompts = []
    
    # Sample utterances become expected inputs
    utterances = intent.get('sampleUtterances', [])
    if isinstance(utterances, list):
        for utt in utterances[:5]:  # Top 5
            if isinstance(utt, dict):
                text = utt.get('utterance', '')
            else:
                text = str(utt)
            if text:
                prompts.append(text)
    
    # Slot prompts
    slots = intent.get('slots', intent.get('slotTypes', []))
    slot_prompts = []
    for slot in slots:
        prompt = slot.get('valueElicitationPrompt', {})
        messages = prompt.get('messages', [])
        for msg in messages:
            if msg.get('content'):
                slot_prompts.append(msg['content'])
    
    # Fulfillment/conclusion message
    conclusion = intent.get('conclusionStatement', {})
    for msg in conclusion.get('messages', []):
        if msg.get('content'):
            slot_prompts.append(msg['content'])
    
    branches = [
        FlowBranch(condition='fulfilled', target_block='end', description='Intent fulfilled'),
        FlowBranch(condition='failed', target_block='fallback', description='Intent failed')
    ]
    
    block = FlowBlock(
        id=intent_name,
        type='LexIntent',
        name=intent_name,
        prompts=[FlowPrompt(id=f"{intent_name}_p{i}", text=p, type='utterance') 
                 for i, p in enumerate(prompts)],
        branches=branches,
        parameters={
            'utterances': prompts,
            'slot_prompts': slot_prompts,
            'slots': [s.get('name', s.get('slotName', '')) for s in slots]
        }
    )
    
    return block, prompts + slot_prompts


def generate_test_paths(blocks: List[FlowBlock], menu_options: Dict) -> List[Dict]:
    """Generate test paths from parsed flow blocks."""
    
    test_paths = []
    
    # Path 1: Happy path (follow default transitions)
    happy_path = {
        'name': 'Happy Path',
        'description': 'Follow default/first options through the flow',
        'steps': [],
        'expected_prompts': []
    }
    
    for block in blocks:
        if block.prompts:
            for prompt in block.prompts:
                if prompt.text and not prompt.text.startswith('['):
                    happy_path['expected_prompts'].append(prompt.text)
        
        # Add DTMF steps for menus
        if block.id in menu_options:
            options = menu_options[block.id]
            if options:
                happy_path['steps'].append({
                    'action': 'dtmf',
                    'value': options[0],  # First option
                    'after_prompt': block.prompts[0].text if block.prompts else ''
                })
    
    test_paths.append(happy_path)
    
    # Path 2: Explore all menu options
    for menu_id, options in menu_options.items():
        menu_block = next((b for b in blocks if b.id == menu_id), None)
        
        for option in options:
            path = {
                'name': f'Menu Option {option}',
                'description': f'Select option {option} at menu',
                'steps': [{
                    'action': 'dtmf',
                    'value': option,
                    'after_prompt': menu_block.prompts[0].text if menu_block and menu_block.prompts else ''
                }],
                'expected_prompts': []
            }
            test_paths.append(path)
    
    # Path 3: Timeout path
    timeout_path = {
        'name': 'Timeout Test',
        'description': 'Test timeout handling by not responding',
        'steps': [{'action': 'wait', 'seconds': 15}],
        'expected_prompts': []
    }
    test_paths.append(timeout_path)
    
    return test_paths


def generate_lex_test_paths(blocks: List[FlowBlock]) -> List[Dict]:
    """Generate test paths for Lex bot."""
    
    test_paths = []
    
    for block in blocks:
        if block.type == 'LexIntent':
            utterances = block.parameters.get('utterances', [])
            slot_prompts = block.parameters.get('slot_prompts', [])
            
            if utterances:
                path = {
                    'name': f'Test {block.name}',
                    'description': f'Test the {block.name} intent',
                    'steps': [
                        {
                            'action': 'speak',
                            'text': utterances[0],
                            'wait_for': slot_prompts[0] if slot_prompts else 'response'
                        }
                    ],
                    'expected_prompts': slot_prompts,
                    'intent': block.name,
                    'sample_utterances': utterances
                }
                test_paths.append(path)
    
    return test_paths


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
