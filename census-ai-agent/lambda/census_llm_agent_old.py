import json
import boto3
import os
from datetime import datetime
from decimal import Decimal

# Initialize clients
bedrock = boto3.client('bedrock-runtime', region_name='us-west-2')
bedrock_agent = boto3.client('bedrock-agent-runtime', region_name='us-west-2')
dynamodb = boto3.resource('dynamodb', region_name='us-west-2')

TABLE_NAME = 'CensusSurveyConversations'
# Use Nova Micro with US inference profile for on-demand throughput
MODEL_ID = 'us.amazon.nova-micro-v1:0'

# AR Policy ARN (will be activated once policy is ready)
AR_POLICY_ARN = os.environ.get('AR_POLICY_ARN', '')
AR_GUARDRAIL_ID = os.environ.get('AR_GUARDRAIL_ID', '')
AR_GUARDRAIL_VERSION = os.environ.get('AR_GUARDRAIL_VERSION', '')

def get_table():
    return dynamodb.Table(TABLE_NAME)

def get_conversation_state(contact_id):
    """Get or create conversation state from DynamoDB"""
    table = get_table()
    try:
        response = table.get_item(Key={'contact_id': contact_id})
        if 'Item' in response:
            item = response['Item']
            if 'turn' in item:
                item['turn'] = int(item['turn'])
            if 'answers' in item and isinstance(item['answers'], str):
                item['answers'] = json.loads(item['answers'])
            return item
    except Exception as e:
        print(f"Error getting state: {e}")
    
    return {
        'contact_id': contact_id,
        'turn': 0,
        'answers': {},
        'survey_data': {},
        'complete': False,
        'created_at': datetime.utcnow().isoformat()
    }

def save_conversation_state(state):
    """Save conversation state to DynamoDB"""
    table = get_table()
    try:
        item = state.copy()
        if 'answers' in item and isinstance(item['answers'], dict):
            item['answers'] = json.dumps(item['answers'])
        item['updated_at'] = datetime.utcnow().isoformat()
        table.put_item(Item=item)
        return True
    except Exception as e:
        print(f"Error saving state: {e}")
        return False

def validate_with_ar(survey_data):
    """Validate survey data against Automated Reasoning policy"""
    if not AR_GUARDRAIL_ID or not AR_GUARDRAIL_VERSION:
        print("AR not configured, skipping validation")
        return {'valid': True, 'violations': []}
    
    try:
        bedrock_runtime = boto3.client('bedrock-runtime', region_name='us-west-2')
        
        validation_text = f"""
        Survey Data Validation Request:
        - household_size: {survey_data.get('household_size', 'not collected')}
        - has_children: {survey_data.get('has_children', 'not asked')}
        - children_count: {survey_data.get('children_count', 0)}
        - children_ages_collected: {survey_data.get('children_ages_collected', False)}
        - ownership_status: {survey_data.get('ownership_status', 'not collected')}
        - homeowner_inquiry_done: {survey_data.get('homeowner_inquiry_done', False)}
        - survey_status: {survey_data.get('survey_status', 'in_progress')}
        """
        
        response = bedrock_runtime.apply_guardrail(
            guardrailIdentifier=AR_GUARDRAIL_ID,
            guardrailVersion=AR_GUARDRAIL_VERSION,
            source='OUTPUT',
            content=[{
                'text': {
                    'text': validation_text,
                    'qualifiers': ['guard_content']
                }
            }]
        )
        
        action = response.get('action', 'NONE')
        if action == 'GUARDRAIL_INTERVENED':
            violations = []
            for assessment in response.get('assessments', []):
                ar_checks = assessment.get('automatedReasoningPolicy', {})
                for finding in ar_checks.get('findings', []):
                    violations.append(finding.get('description', 'Policy violation'))
            return {'valid': False, 'violations': violations}
        
        return {'valid': True, 'violations': []}
        
    except Exception as e:
        print(f"AR validation error: {e}")
        return {'valid': True, 'violations': []}

def generate_llm_response(state, user_input):
    """Generate dynamic survey question using Nova Micro LLM"""
    
    turn = state.get('turn', 0)
    answers = state.get('answers', {})
    survey_data = state.get('survey_data', {})
    
    history = ""
    for i, (q, a) in enumerate(answers.items()):
        history += f"Q{i+1}: {q}\nA: {a}\n"
    
    system_prompt = """You are a friendly US Census Bureau survey agent conducting a household survey by phone.

SURVEY RULES (enforced by Automated Reasoning):
1. First confirm the respondent wants to participate
2. Ask how many people live in the household (must be 1-20)
3. If more than 1 person, ask if there are children under 18
4. If children exist, you MUST ask for EACH child's age - survey cannot complete without this
5. Ask if they own or rent their home
6. If they OWN the home, you MUST ask if you're speaking to the homeowner or another household member
7. Do NOT ask for SSN, income, or bank information

COMPLETION REQUIREMENTS:
- Household size collected
- Children question asked (if household > 1)
- All children's ages collected (if children present)
- Ownership status collected  
- Homeowner verified (if home is owned)

Current survey data collected:
""" + json.dumps(survey_data, indent=2) + """

When survey is complete, say "Thank you for completing the census survey. Your responses have been recorded. Goodbye!" and nothing else.

Keep responses brief (1-2 sentences). Be warm and conversational."""

    user_message = f"""Turn {turn + 1}
Previous conversation:
{history if history else "(This is the start of the survey)"}

User's latest response: "{user_input}"

Based on the survey rules and what data has been collected, what should you say next?
If all required data is collected, complete the survey."""

    try:
        response = bedrock.converse(
            modelId=MODEL_ID,
            messages=[
                {"role": "user", "content": [{"text": user_message}]}
            ],
            system=[{"text": system_prompt}],
            inferenceConfig={
                "maxTokens": 200,
                "temperature": 0.7,
                "topP": 0.9
            }
        )
        
        ai_response = response['output']['message']['content'][0]['text']
        
        user_lower = user_input.lower().strip()
        
        if turn == 0:
            if any(word in user_lower for word in ['yes', 'sure', 'okay', 'ok', 'yeah', 'yep']):
                survey_data['confirmed'] = True
        elif 'household_size' not in survey_data:
            import re
            numbers = re.findall(r'\b(\d+)\b', user_input)
            if numbers:
                survey_data['household_size'] = int(numbers[0])
        elif survey_data.get('household_size', 0) > 1 and 'has_children' not in survey_data:
            if any(word in user_lower for word in ['yes', 'yeah', 'yep']):
                survey_data['has_children'] = True
            elif any(word in user_lower for word in ['no', 'nope', 'none']):
                survey_data['has_children'] = False
        elif survey_data.get('has_children') and 'children_ages' not in survey_data:
            import re
            ages = re.findall(r'\b(\d+)\b', user_input)
            if ages:
                survey_data['children_ages'] = [int(a) for a in ages]
                survey_data['children_ages_collected'] = True
        elif 'ownership_status' not in survey_data:
            if 'own' in user_lower:
                survey_data['ownership_status'] = 'own'
            elif 'rent' in user_lower:
                survey_data['ownership_status'] = 'rent'
        elif survey_data.get('ownership_status') == 'own' and 'homeowner_inquiry_done' not in survey_data:
            survey_data['homeowner_inquiry_done'] = True
            if 'owner' in user_lower or 'yes' in user_lower:
                survey_data['respondent_type'] = 'homeowner'
            else:
                survey_data['respondent_type'] = 'occupant'
        
        is_complete = (
            survey_data.get('confirmed') and
            survey_data.get('household_size') and
            survey_data.get('ownership_status') and
            (survey_data.get('household_size', 0) <= 1 or 'has_children' in survey_data) and
            (not survey_data.get('has_children') or survey_data.get('children_ages_collected')) and
            (survey_data.get('ownership_status') != 'own' or survey_data.get('homeowner_inquiry_done'))
        )
        
        if is_complete:
            ar_result = validate_with_ar(survey_data)
            if not ar_result['valid']:
                print(f"AR violations: {ar_result['violations']}")
                is_complete = False
                ai_response = "I need to collect a bit more information. " + ai_response
        
        state['survey_data'] = survey_data
        state['complete'] = is_complete
        
        return ai_response, is_complete
        
    except Exception as e:
        print(f"LLM Error: {e}")
        import traceback
        traceback.print_exc()
        raise

def lambda_handler(event, context):
    """Main Lambda handler for Lex V2 fulfillment"""
    print(f"Event: {json.dumps(event)}")
    
    try:
        session_state = event.get('sessionState', {})
        session_attrs = session_state.get('sessionAttributes', {}) or {}
        intent = session_state.get('intent', {})
        intent_name = intent.get('name', 'FallbackIntent')
        
        request_attrs = event.get('requestAttributes', {}) or {}
        contact_id = request_attrs.get('x-amz-lex:connect-originating-request-id', 
                                       event.get('sessionId', 'unknown'))
        
        input_transcript = event.get('inputTranscript', '').strip()
        
        if len(input_transcript) < 2:
            return {
                "sessionState": {
                    "dialogAction": {"type": "ElicitIntent"},
                    "intent": {"name": intent_name, "state": "InProgress"},
                    "sessionAttributes": session_attrs
                },
                "messages": [{"contentType": "PlainText", "content": "I'm sorry, I didn't catch that. Could you please repeat?"}]
            }
        
        state = get_conversation_state(contact_id)
        current_turn = state.get('turn', 0)
        
        if current_turn > 0:
            state['answers'][f"turn_{current_turn}"] = input_transcript
        
        ai_response, is_complete = generate_llm_response(state, input_transcript)
        
        state['turn'] = current_turn + 1
        state['complete'] = is_complete
        
        save_conversation_state(state)
        
        print(f"Turn {current_turn + 1}: User='{input_transcript}' -> AI='{ai_response}' Complete={is_complete}")
        
        if is_complete:
            return {
                "sessionState": {
                    "dialogAction": {"type": "Close"},
                    "intent": {"name": intent_name, "state": "Fulfilled"},
                    "sessionAttributes": session_attrs
                },
                "messages": [{"contentType": "PlainText", "content": ai_response}]
            }
        else:
            return {
                "sessionState": {
                    "dialogAction": {"type": "ElicitIntent"},
                    "intent": {"name": intent_name, "state": "InProgress"},
                    "sessionAttributes": session_attrs
                },
                "messages": [{"contentType": "PlainText", "content": ai_response}]
            }
            
    except Exception as e:
        print(f"Handler error: {e}")
        import traceback
        traceback.print_exc()
        return {
            "sessionState": {
                "dialogAction": {"type": "ElicitIntent"},
                "intent": {"name": "FallbackIntent", "state": "InProgress"},
                "sessionAttributes": {}
            },
            "messages": [{"contentType": "PlainText", "content": "I apologize for the technical issue. Could you please repeat that?"}]
        }
