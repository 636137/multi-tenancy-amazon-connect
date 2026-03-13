"""
Census Survey AI Agent - Amazon Connect Lambda
Uses Amazon Nova Premier via Bedrock Converse API
Designed to disconnect after survey completion via exception trigger
"""
import json
import boto3
import os
from datetime import datetime
import random

dynamodb = boto3.resource('dynamodb', region_name='us-east-1')
responses_table = dynamodb.Table(os.environ.get('CENSUS_TABLE', 'CensusResponses'))
sessions_table = dynamodb.Table('CensusChatSessions')
bedrock = boto3.client('bedrock-runtime', region_name='us-east-1')

SYSTEM_PROMPT = """You are Sarah, a friendly Census Bureau representative conducting a brief phone survey.

YOUR THREE QUESTIONS (ask in order, one at a time):
1. How many people live in your household?  
2. Are there any children under 18?
3. Do you own or rent your home?

RULES:
- Be warm, natural, and brief (max 25 words per response)
- Extract answers from natural speech:
  - "just me" = 1, "me and my wife" = 2, "family of 4" = 4
  - "no kids", "empty nester" = no children
  - "we own", "mortgage" = own; "lease", "renting" = rent
- Track which questions have been answered in this conversation
- Once ALL THREE are answered, include [SURVEY_COMPLETE] at the start and say goodbye
- Do NOT repeat questions already answered

OUTPUT: Just respond naturally. When all 3 questions answered, start with [SURVEY_COMPLETE]"""

sessions = {}

def load_session(contact_id):
    if contact_id in sessions:
        return sessions[contact_id]
    try:
        item = sessions_table.get_item(Key={'contactId': contact_id}).get('Item')
        if item:
            return json.loads(item.get('data', '{}'))
    except:
        pass
    return {'history': [], 'complete': False, 'turn': 0}

def save_session(contact_id, data):
    sessions[contact_id] = data
    try:
        sessions_table.put_item(Item={
            'contactId': contact_id,
            'data': json.dumps(data),
            'ttl': int(datetime.now().timestamp()) + 3600
        })
    except:
        pass

def call_nova(history):
    messages = []
    for h in history:
        messages.append({"role": h['role'], "content": [{"text": h['text']}]})
    
    # Ensure conversation starts with user message
    if not messages or messages[0]['role'] != 'user':
        messages.insert(0, {"role": "user", "content": [{"text": "Hello, I'm ready for the census survey."}]})
    
    response = bedrock.converse(
        modelId='us.amazon.nova-premier-v1:0',
        system=[{"text": SYSTEM_PROMPT}],
        messages=messages,
        inferenceConfig={"maxTokens": 200, "temperature": 0.7}
    )
    return response['output']['message']['content'][0]['text']

def save_survey(contact_id):
    case_id = f"CENSUS-{datetime.now().strftime('%Y%m%d')}-{random.randint(1000, 9999)}"
    try:
        responses_table.put_item(Item={
            'caseId': case_id,
            'contactId': contact_id,
            'timestamp': datetime.now().isoformat(),
            'status': 'completed'
        })
        print(f"SAVED: {case_id}")
    except Exception as e:
        print(f"SAVE ERROR: {e}")
    return case_id

def lambda_handler(event, context):
    """
    Amazon Connect Lambda handler.
    
    Flow integration:
    - Returns response dict on normal turns
    - Raises SURVEY_COMPLETE exception after completion to trigger disconnect
    """
    if 'Details' not in event:
        return {'statusCode': 400, 'body': 'Use via Amazon Connect'}

    params = event['Details'].get('Parameters', {})
    contact_id = event['Details']['ContactData'].get('ContactId', 'session')
    input_text = (params.get('inputText') or '').strip()

    print(f"INPUT: contact={contact_id} text={input_text}")

    session = load_session(contact_id)
    
    # Already complete - trigger disconnect via exception
    if session.get('complete'):
        print("COMPLETE - triggering disconnect")
        raise Exception("SURVEY_COMPLETE")

    # Greeting - first turn
    if not input_text or input_text == '__greeting__':
        greeting = "Hi! This is Sarah from the Census Bureau. I just have three quick questions. How many people live in your household?"
        session['history'] = [
            {"role": "user", "text": "Hello"},
            {"role": "assistant", "text": greeting}
        ]
        session['turn'] = 1
        save_session(contact_id, session)
        return {'response': greeting, 'sessionId': contact_id}

    # Add user input to history
    session['history'].append({"role": "user", "text": input_text})
    session['turn'] = session.get('turn', 0) + 1
    
    # Call Nova Premier
    response_text = call_nova(session['history'])
    
    # Check if complete
    if '[SURVEY_COMPLETE]' in response_text:
        response_text = response_text.replace('[SURVEY_COMPLETE]', '').strip()
        session['complete'] = True
        save_survey(contact_id)
        print("MARKED COMPLETE - next call will disconnect")
    
    session['history'].append({"role": "assistant", "text": response_text})
    save_session(contact_id, session)
    
    print(f"TURN {session['turn']} RESPONSE: {response_text[:80]}")
    return {'response': response_text, 'sessionId': contact_id}
