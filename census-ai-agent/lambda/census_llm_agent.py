"""
Census Survey LLM Agent
=======================
Amazon Bedrock Nova Premier-powered survey agent for Amazon Connect.

This Lambda handles all survey logic via FallbackIntent in Lex V2.
All user input goes through Nova Premier LLM for natural conversation.

Architecture:
  Connect → Lex V2 (FallbackIntent) → This Lambda → Nova Premier → Response

Resources:
  - Model: us.amazon.nova-premier-v1:0
  - DynamoDB: CensusSurveyConversations (conversation history)
  - Lex Bot: CensusSurveyAI (BSAIKYT20J) / Alias: prod (UMMWRQRQ8Q)
  - Contact Flow: 1 - Census Survey AI Agent
  - Phone: +1 (844) 593-5770

Features:
  - Full conversation history passed to LLM each turn
  - Context-aware data extraction (only extracts when relevant question was asked)
  - Explicit state tracking (KNOWN FACTS vs STILL NEED)
  - Proper Lex Close response for call termination
"""

import json
import boto3
import re
from datetime import datetime
from decimal import Decimal

bedrock = boto3.client('bedrock-runtime', region_name='us-west-2')
dynamodb = boto3.resource('dynamodb', region_name='us-west-2')

MODEL_ID = 'us.amazon.nova-premier-v1:0'
TABLE_NAME = 'CensusSurveyConversations'


def get_table():
    return dynamodb.Table(TABLE_NAME)


def strip_markdown(text):
    """Remove markdown formatting from LLM responses"""
    text = re.sub(r'\*\*([^*]+)\*\*', r'\1', text)
    text = re.sub(r'\*([^*]+)\*', r'\1', text)
    return text.strip()


def get_conversation(contact_id):
    """Get conversation history from DynamoDB"""
    table = get_table()
    try:
        response = table.get_item(Key={'contact_id': contact_id})
        if 'Item' in response:
            return response['Item']
    except Exception as e:
        print(f"DynamoDB get error: {e}")
    return None


def save_conversation(contact_id, history, survey_data, complete):
    """Save conversation history to DynamoDB"""
    table = get_table()
    try:
        table.put_item(Item={
            'contact_id': contact_id,
            'history': history,
            'survey_data': survey_data,
            'complete': complete,
            'updated_at': datetime.utcnow().isoformat()
        })
    except Exception as e:
        print(f"DynamoDB save error: {e}")


def extract_survey_data(user_input, last_agent_msg, current_data):
    """
    Context-aware extraction - only extracts data when the agent 
    actually asked the relevant question.
    """
    data = current_data.copy()
    text_lower = user_input.lower()
    agent_lower = (last_agent_msg or '').lower()
    
    # Extract household size only if we asked about it
    if 'household_size' not in data and ('how many' in agent_lower or 'people' in agent_lower or 'household' in agent_lower):
        nums = re.findall(r'\b(\d+)\b', user_input)
        words_to_num = {'one':1,'two':2,'three':3,'four':4,'five':5,'six':6,'seven':7,'eight':8,'nine':9,'ten':10}
        for word, num in words_to_num.items():
            if word in text_lower:
                nums.append(str(num))
        if nums:
            data['household_size'] = int(nums[0])
    
    # Extract ownership only if we asked about it
    if 'ownership' not in data and ('own' in agent_lower or 'rent' in agent_lower):
        if 'own' in text_lower:
            data['ownership'] = 'own'
        elif 'rent' in text_lower:
            data['ownership'] = 'rent'
    
    # Extract children info only if we asked about children
    if 'has_children' not in data and ('child' in agent_lower or 'kids' in agent_lower or 'under 18' in agent_lower):
        yes_words = ['yes','yeah','yep','sure','yea','correct']
        no_words = ['no','nope','nah','none']
        if any(w in text_lower for w in no_words):
            data['has_children'] = 'no'
        elif any(w in text_lower for w in yes_words):
            data['has_children'] = 'yes'
    
    return data


def call_llm_with_history(history, survey_data, user_input):
    """
    Call Nova Premier with full conversation context.
    Returns (response_text, is_complete)
    """
    # Build context of what we know
    known = []
    if 'household_size' in survey_data:
        known.append(f"Household has {survey_data['household_size']} people")
    if 'has_children' in survey_data:
        known.append(f"Children under 18: {survey_data['has_children']}")
    if 'ownership' in survey_data:
        known.append(f"Housing: {survey_data['ownership']}")
    
    # Determine what we still need
    needed = []
    if 'household_size' not in survey_data:
        needed.append("household size")
    if 'has_children' not in survey_data:
        needed.append("whether there are children under 18")
    if 'ownership' not in survey_data:
        needed.append("whether they own or rent")
    
    complete = len(needed) == 0
    
    system_prompt = f"""You are a Census Bureau survey agent. Be conversational and natural.

KNOWN FACTS: {', '.join(known) if known else 'None yet'}
STILL NEED: {', '.join(needed) if needed else 'Survey complete!'}

{'SURVEY COMPLETE: Thank them warmly and say goodbye.' if complete else 'Ask the FIRST item in STILL NEED naturally.'}

RULES:
- NEVER re-ask something already known
- Keep responses under 30 words
- No asterisks or markdown
- Sound friendly and human"""

    # Build messages with full history
    messages = []
    for turn in history:
        messages.append({"role": "user", "content": [{"text": turn['user']}]})
        messages.append({"role": "assistant", "content": [{"text": turn['assistant']}]})
    messages.append({"role": "user", "content": [{"text": user_input}]})
    
    response = bedrock.converse(
        modelId=MODEL_ID,
        system=[{"text": system_prompt}],
        messages=messages,
        inferenceConfig={"maxTokens": 80, "temperature": 0.4}
    )
    
    return strip_markdown(response['output']['message']['content'][0]['text']), complete


def lambda_handler(event, context):
    """
    Main Lambda handler for Lex V2 fulfillment.
    
    All user input comes through FallbackIntent and is processed by Nova Premier.
    Returns Close action with fulfillmentState when survey is complete.
    """
    print(f"EVENT: {json.dumps(event)}")
    
    try:
        intent_name = event.get('sessionState', {}).get('intent', {}).get('name', 'FallbackIntent')
        session_attrs = event.get('sessionState', {}).get('sessionAttributes', {}) or {}
        
        request_attrs = event.get('requestAttributes', {}) or {}
        contact_id = request_attrs.get('x-amz-lex:connect-originating-request-id', event.get('sessionId', 'unknown'))
        
        user_input = event.get('inputTranscript', '').strip()
        print(f"CONTACT: {contact_id}, INPUT: '{user_input}'")
        
        # Handle empty input
        if not user_input:
            return {
                "sessionState": {
                    "dialogAction": {"type": "ElicitIntent"},
                    "intent": {"name": intent_name, "state": "InProgress"},
                    "sessionAttributes": session_attrs
                },
                "messages": [{"contentType": "PlainText", "content": "I didn't catch that. Could you repeat?"}]
            }
        
        # Get existing conversation
        conv = get_conversation(contact_id)
        if conv:
            history = conv.get('history', [])
            survey_data = conv.get('survey_data', {})
        else:
            history = []
            survey_data = {}
        
        # Get last agent message for context-aware extraction
        last_agent_msg = history[-1]['assistant'] if history else ''
        
        # Extract data based on context
        survey_data = extract_survey_data(user_input, last_agent_msg, survey_data)
        print(f"Survey data: {survey_data}")
        
        # Call LLM with full history
        response_text, complete = call_llm_with_history(history, survey_data, user_input)
        print(f"LLM response: {response_text}, Complete: {complete}")
        
        # Save updated conversation
        history.append({'user': user_input, 'assistant': response_text})
        save_conversation(contact_id, history, survey_data, complete)
        
        # Return Close action when complete
        if complete:
            print("SURVEY COMPLETE - returning Close with fulfillmentState")
            return {
                "sessionState": {
                    "dialogAction": {
                        "type": "Close",
                        "fulfillmentState": "Fulfilled"
                    },
                    "intent": {
                        "name": intent_name,
                        "state": "Fulfilled"
                    },
                    "sessionAttributes": session_attrs
                },
                "messages": [{"contentType": "PlainText", "content": response_text}]
            }
        
        # Continue conversation
        return {
            "sessionState": {
                "dialogAction": {"type": "ElicitIntent"},
                "intent": {"name": intent_name, "state": "InProgress"},
                "sessionAttributes": session_attrs
            },
            "messages": [{"contentType": "PlainText", "content": response_text}]
        }
        
    except Exception as e:
        print(f"ERROR: {e}")
        import traceback
        traceback.print_exc()
        return {
            "sessionState": {
                "dialogAction": {
                    "type": "Close",
                    "fulfillmentState": "Failed"
                },
                "intent": {"name": "FallbackIntent", "state": "Failed"},
                "sessionAttributes": {}
            },
            "messages": [{"contentType": "PlainText", "content": "Sorry, there was an issue. Goodbye."}]
        }
