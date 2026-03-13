"""
Census Survey AI Agent - Enhanced UX
====================================
Natural, warm, conversational survey experience.
Agent name: Sarah
Model: Amazon Nova Premier
"""

import json
import boto3
import re
from datetime import datetime

bedrock = boto3.client('bedrock-runtime', region_name='us-west-2')
dynamodb = boto3.resource('dynamodb', region_name='us-west-2')

MODEL_ID = 'us.amazon.nova-premier-v1:0'
TABLE_NAME = 'CensusSurveyConversations'


def get_table():
    return dynamodb.Table(TABLE_NAME)


def strip_markdown(text):
    text = re.sub(r'\*\*([^*]+)\*\*', r'\1', text)
    text = re.sub(r'\*([^*]+)\*', r'\1', text)
    return text.strip()


def get_conversation(contact_id):
    table = get_table()
    try:
        response = table.get_item(Key={'contact_id': contact_id})
        if 'Item' in response:
            return response['Item']
    except Exception as e:
        print(f"DynamoDB get error: {e}")
    return None


def save_conversation(contact_id, history, survey_data, complete):
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


def smart_extract(user_input, last_agent_msg, survey_data):
    """
    Smart extraction that understands natural language and context.
    Can extract multiple pieces of info from a single response.
    """
    data = survey_data.copy()
    text = user_input.lower()
    
    # Extract household size - look for numbers in context
    if 'household_size' not in data:
        # Direct numbers
        nums = re.findall(r'\b(\d+)\b', user_input)
        word_nums = {'one':1,'two':2,'three':3,'four':4,'five':5,'six':6,'seven':7,'eight':8,'nine':9,'ten':10}
        for word, num in word_nums.items():
            if word in text:
                nums.append(str(num))
        
        # Context clues
        if 'just me' in text or 'only me' in text or 'i live alone' in text:
            data['household_size'] = 1
        elif 'me and my' in text and ('husband' in text or 'wife' in text or 'partner' in text or 'spouse' in text):
            base = 2
            # Check for kids mentioned
            if 'kid' in text or 'child' in text:
                kid_nums = re.findall(r'(\d+)\s*(?:kid|child)', text)
                if kid_nums:
                    base += int(kid_nums[0])
                elif 'two' in text:
                    base += 2
                elif 'three' in text:
                    base += 3
                else:
                    base += 1  # At least one if mentioned
            data['household_size'] = base
        elif nums:
            data['household_size'] = int(nums[0])
    
    # Extract children info - be smart about it
    if 'has_children' not in data:
        # Explicit mentions
        if any(phrase in text for phrase in ['no kids', 'no children', 'dont have kids', "don't have kids", 
                                              'empty nester', 'moved out', 'no one under']):
            data['has_children'] = 'no'
        elif any(phrase in text for phrase in ['have kids', 'have children', 'our kids', 'my kids',
                                                'teenager', 'toddler', 'baby', 'year old', 'years old']):
            data['has_children'] = 'yes'
        # Ages mentioned
        elif re.search(r'\b(\d{1,2})\s*(and|,|&)\s*(\d{1,2})\b', text):
            data['has_children'] = 'yes'
        # Response to direct question
        elif last_agent_msg and 'child' in last_agent_msg.lower():
            if any(w in text for w in ['yes','yeah','yep','one','two','three']):
                data['has_children'] = 'yes'
            elif any(w in text for w in ['no','nope','none','zero']):
                data['has_children'] = 'no'
    
    # Extract ownership - comprehensive
    if 'ownership' not in data:
        if any(phrase in text for phrase in ['we own', 'i own', 'own it', 'own our', 'own my', 
                                              'own the', 'homeowner', 'our house', 'my house']):
            data['ownership'] = 'own'
        elif any(phrase in text for phrase in ['rent', 'renting', 'renter', 'lease', 'apartment']):
            data['ownership'] = 'rent'
        # Response to direct question
        elif last_agent_msg and ('own' in last_agent_msg.lower() or 'rent' in last_agent_msg.lower()):
            if 'own' in text:
                data['ownership'] = 'own'
            elif 'rent' in text:
                data['ownership'] = 'rent'
    
    return data


def generate_response(history, survey_data, user_input):
    """Generate a warm, natural response using Nova Premier."""
    
    # Build context
    collected = []
    if 'household_size' in survey_data:
        collected.append(f"household size: {survey_data['household_size']}")
    if 'has_children' in survey_data:
        collected.append(f"children under 18: {survey_data['has_children']}")
    if 'ownership' in survey_data:
        collected.append(f"housing: {survey_data['ownership']}")
    
    missing = []
    if 'household_size' not in survey_data:
        missing.append("how many people live in the household")
    if 'has_children' not in survey_data:
        missing.append("whether there are children under 18")
    if 'ownership' not in survey_data:
        missing.append("whether they own or rent")
    
    is_complete = len(missing) == 0
    
    system_prompt = f"""You are Sarah, a friendly Census Bureau representative. You're warm, conversational, and efficient.

PERSONALITY:
- Warm and genuine - you care about people
- Natural conversational style - use contractions, casual language
- Acknowledge what people say before asking the next question
- If someone gives multiple pieces of info, acknowledge all of them
- Keep responses SHORT (under 25 words ideally)

ALREADY COLLECTED: {', '.join(collected) if collected else 'Nothing yet'}
STILL NEED: {', '.join(missing) if missing else 'SURVEY COMPLETE!'}

{"SURVEY IS COMPLETE! Thank them warmly, tell them their responses help their community, and wish them well. Be genuine, not scripted." if is_complete else f"Ask about: {missing[0]}. Make it natural, not robotic."}

RULES:
- NEVER repeat a question if you have the answer
- NEVER use asterisks or markdown
- Sound like a real person, not a bot
- If user gave multiple answers, acknowledge each briefly
- One question at a time if needed
- Match their energy - if they're brief, be brief back"""

    messages = []
    for turn in history:
        messages.append({"role": "user", "content": [{"text": turn['user']}]})
        messages.append({"role": "assistant", "content": [{"text": turn['assistant']}]})
    messages.append({"role": "user", "content": [{"text": user_input}]})
    
    response = bedrock.converse(
        modelId=MODEL_ID,
        system=[{"text": system_prompt}],
        messages=messages,
        inferenceConfig={"maxTokens": 100, "temperature": 0.6}
    )
    
    return strip_markdown(response['output']['message']['content'][0]['text']), is_complete


def lambda_handler(event, context):
    print(f"EVENT: {json.dumps(event)}")
    
    try:
        intent_name = event.get('sessionState', {}).get('intent', {}).get('name', 'FallbackIntent')
        session_attrs = event.get('sessionState', {}).get('sessionAttributes', {}) or {}
        
        request_attrs = event.get('requestAttributes', {}) or {}
        contact_id = request_attrs.get('x-amz-lex:connect-originating-request-id', event.get('sessionId', 'unknown'))
        
        user_input = event.get('inputTranscript', '').strip()
        print(f"CONTACT: {contact_id}, INPUT: '{user_input}'")
        
        if not user_input:
            return {
                "sessionState": {
                    "dialogAction": {"type": "ElicitIntent"},
                    "intent": {"name": intent_name, "state": "InProgress"},
                    "sessionAttributes": session_attrs
                },
                "messages": [{"contentType": "PlainText", "content": "Sorry, I didn't catch that. Could you say that again?"}]
            }
        
        # Get conversation state
        conv = get_conversation(contact_id)
        history = conv.get('history', []) if conv else []
        survey_data = conv.get('survey_data', {}) if conv else {}
        
        # Smart extraction
        last_agent_msg = history[-1]['assistant'] if history else ''
        survey_data = smart_extract(user_input, last_agent_msg, survey_data)
        print(f"Survey data after extraction: {survey_data}")
        
        # Generate response
        response_text, complete = generate_response(history, survey_data, user_input)
        print(f"Response: '{response_text}', Complete: {complete}")
        
        # Save state
        history.append({'user': user_input, 'assistant': response_text})
        save_conversation(contact_id, history, survey_data, complete)
        
        if complete:
            return {
                "sessionState": {
                    "dialogAction": {"type": "Close", "fulfillmentState": "Fulfilled"},
                    "intent": {"name": intent_name, "state": "Fulfilled"},
                    "sessionAttributes": session_attrs
                },
                "messages": [{"contentType": "PlainText", "content": response_text}]
            }
        
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
                "dialogAction": {"type": "Close", "fulfillmentState": "Failed"},
                "intent": {"name": "FallbackIntent", "state": "Failed"},
                "sessionAttributes": {}
            },
            "messages": [{"contentType": "PlainText", "content": "I apologize, we're having technical difficulties. Please try again later."}]
        }
