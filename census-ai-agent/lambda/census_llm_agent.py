"""
Census Survey LLM Agent Lambda
Handles both Connect direct invocations and Lex V2 fulfillment requests.
Uses Claude 3 Haiku via Bedrock to generate dynamic survey questions.
"""
import json
import boto3
from datetime import datetime
import traceback

bedrock = boto3.client('bedrock-runtime', region_name='us-west-2')
dynamodb = boto3.resource('dynamodb', region_name='us-west-2')

# Get or create table
try:
    table = dynamodb.Table('CensusSurveyConversations')
    table.table_status
except:
    dynamodb.meta.client.create_table(
        TableName='CensusSurveyConversations',
        KeySchema=[{'AttributeName': 'contact_id', 'KeyType': 'HASH'}],
        AttributeDefinitions=[{'AttributeName': 'contact_id', 'AttributeType': 'S'}],
        BillingMode='PAY_PER_REQUEST'
    )
    table = dynamodb.Table('CensusSurveyConversations')

SYSTEM_PROMPT = """You are a friendly US Census Bureau interviewer conducting the 2020 Census survey by phone.

SURVEY QUESTIONS (ask in order):
1. First greet warmly and ask if they have a few minutes for the Census
2. How many people live at this address?
3. What are the ages of each person?
4. Is this a house, apartment, condo, or other type of home?
5. Do you own or rent this home?
6. How many bedrooms does the home have?
7. Thank them and say the survey is complete

RULES:
- Ask ONE question at a time
- Keep responses under 40 words
- Be conversational and natural
- If they decline, thank them politely
- When all questions answered, say "survey complete" and thank them

Current turn: {turn}
Caller's last response: {last_response}
"""

def handler(event, context):
    print(f"Event: {json.dumps(event)}")
    
    # Detect if this is a Lex fulfillment request or Connect invocation
    if 'sessionState' in event:
        return handle_lex_fulfillment(event, context)
    else:
        return handle_connect_invocation(event, context)

def handle_lex_fulfillment(event, context):
    """Handle Lex V2 fulfillment request - receives inputTranscript"""
    
    session_id = event.get('sessionId', 'unknown')
    input_transcript = event.get('inputTranscript', '')
    
    print(f"Lex Fulfillment - Session: {session_id}, Transcript: {input_transcript}")
    
    # Get conversation state
    try:
        response = table.get_item(Key={'contact_id': session_id})
        state = response.get('Item', {})
        turn = int(state.get('turn', 0))
        conv_history = json.loads(state.get('conversation_history', '[]'))
    except:
        turn = 0
        conv_history = []
    
    # Add caller's response to history
    if input_transcript:
        conv_history.append({"role": "user", "content": input_transcript})
    
    # Build messages for Claude
    messages = []
    for msg in conv_history[-8:]:
        messages.append({
            "role": msg["role"],
            "content": [{"text": msg["content"]}]
        })
    
    if not messages:
        messages.append({
            "role": "user",
            "content": [{"text": "The call has started. Greet the citizen and ask if they have time for the Census."}]
        })
    
    # Call Claude
    try:
        response = bedrock.converse(
            modelId='anthropic.claude-3-haiku-20240307-v1:0',
            messages=messages,
            system=[{"text": SYSTEM_PROMPT.format(turn=turn, last_response=input_transcript or 'N/A')}],
            inferenceConfig={"maxTokens": 150, "temperature": 0.7}
        )
        ai_response = response['output']['message']['content'][0]['text']
    except Exception as e:
        print(f"Bedrock error: {e}")
        ai_response = "How many people live in your household?"
    
    print(f"AI Response: {ai_response}")
    
    # Update history
    conv_history.append({"role": "assistant", "content": ai_response})
    
    # Save state
    table.put_item(Item={
        'contact_id': session_id,
        'turn': turn + 1,
        'conversation_history': json.dumps(conv_history[-12:]),
        'last_input': input_transcript,
        'updated': datetime.utcnow().isoformat()
    })
    
    # Check if survey complete
    is_complete = 'survey complete' in ai_response.lower() and turn > 4
    
    return {
        "sessionState": {
            "dialogAction": {
                "type": "Close" if is_complete else "ElicitIntent"
            },
            "intent": {
                "name": event['sessionState']['intent']['name'],
                "state": "Fulfilled" if is_complete else "InProgress"
            }
        },
        "messages": [
            {
                "contentType": "PlainText",
                "content": ai_response
            }
        ]
    }

def handle_connect_invocation(event, context):
    """Handle direct Connect Lambda invocation"""
    
    contact_data = event.get('Details', {}).get('ContactData', {})
    contact_id = contact_data.get('ContactId', 'unknown')
    
    try:
        response = table.get_item(Key={'contact_id': contact_id})
        state = response.get('Item', {})
        turn = int(state.get('turn', 0))
        conv_history = json.loads(state.get('conversation_history', '[]'))
    except:
        turn = 0
        conv_history = []
    
    print(f"Connect Invocation - Contact: {contact_id}, Turn: {turn}")
    
    messages = []
    for msg in conv_history[-8:]:
        messages.append({
            "role": msg["role"],
            "content": [{"text": msg["content"]}]
        })
    
    if turn == 0:
        messages.append({
            "role": "user",
            "content": [{"text": "The call has started. Greet the citizen warmly."}]
        })
    else:
        messages.append({
            "role": "user",
            "content": [{"text": "(Caller responded. Continue with the next question.)"}]
        })
    
    try:
        response = bedrock.converse(
            modelId='anthropic.claude-3-haiku-20240307-v1:0',
            messages=messages,
            system=[{"text": SYSTEM_PROMPT.format(turn=turn, last_response='N/A')}],
            inferenceConfig={"maxTokens": 150, "temperature": 0.7}
        )
        ai_response = response['output']['message']['content'][0]['text']
    except Exception as e:
        print(f"Bedrock error: {e}")
        ai_response = "Welcome to the Census Survey. How many people live in your household?"
    
    conv_history.append({"role": "assistant", "content": ai_response})
    
    table.put_item(Item={
        'contact_id': contact_id,
        'turn': turn + 1,
        'conversation_history': json.dumps(conv_history[-12:]),
        'updated': datetime.utcnow().isoformat()
    })
    
    return {"SpokenResponse": ai_response}
