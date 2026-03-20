"""
Census Survey Self-Service AI Agent Lambda
"""

import json
import boto3
import os
import logging
from datetime import datetime, timezone

logger = logging.getLogger()
logger.setLevel(logging.INFO)

bedrock = boto3.client('bedrock-runtime', region_name=os.environ.get('AWS_REGION', 'us-east-1'))
dynamodb = boto3.resource('dynamodb', region_name=os.environ.get('AWS_REGION', 'us-east-1'))

SESSIONS_TABLE = os.environ.get('SESSIONS_TABLE', 'CensusChatSessions')
MODEL_ID = os.environ.get('MODEL_ID', 'anthropic.claude-3-sonnet-20240229-v1:0')

SYSTEM_PROMPT = """You are Sarah, a friendly AI assistant for the US Census Bureau.
Your job is to help callers with Census inquiries, answer questions about privacy 
and legitimacy, assist with survey completion, and route complex cases to specialists.

Key rules:
- Never ask for SSN, bank info, or payment
- Protect caller privacy under Title 13 of the US Code
- Be warm, patient, and reassuring
- Keep responses concise (2-3 sentences for voice)

When callers ask if this is legitimate, explain:
- The Census is constitutionally mandated and required by law
- Your responses are protected and cannot be shared with other agencies
- Census workers take a lifetime oath to protect your information
- You can verify at census.gov or call 1-800-923-8282

When asked about what the Census collects, mention it asks about:
- Number of people in household
- Ages and relationships
- Whether you own or rent
- Race and ethnicity (for representation purposes only)"""


def lambda_handler(event, context):
    logger.info(f"Event received: {json.dumps(event)}")
    
    try:
        details = event.get('Details', {})
        contact_data = details.get('ContactData', {})
        parameters = details.get('Parameters', {})
        
        contact_id = contact_data.get('ContactId', 'unknown')
        user_input = parameters.get('userInput', '')
        action = parameters.get('action', 'turn')
        attributes = contact_data.get('Attributes', {})
        
        session = get_or_create_session(contact_id, attributes)
        
        if action == 'greeting' or action == '__greeting__':
            response = generate_greeting(session)
        else:
            response = process_turn(session, user_input)
        
        if session.get('complete'):
            return {
                'response': response.get('message', 'Thank you for calling. Goodbye!'),
                'action': 'complete',
                'sessionId': contact_id
            }
        
        return {
            'response': response.get('message', 'Could you please repeat that?'),
            'action': 'continue',
            'sessionId': contact_id
        }
        
    except Exception as e:
        logger.error(f"Error: {str(e)}", exc_info=True)
        return {
            'response': "I apologize, I'm having technical difficulties. Let me connect you with a specialist.",
            'action': 'escalate',
            'error': str(e)
        }


def get_or_create_session(contact_id: str, attributes: dict) -> dict:
    table = dynamodb.Table(SESSIONS_TABLE)
    
    try:
        response = table.get_item(Key={'contactId': contact_id})
        if 'Item' in response:
            session = response['Item']
            session['conversation_history'] = json.loads(session.get('conversationHistory', '[]'))
            return session
    except Exception as e:
        logger.warning(f"Error getting session: {e}")
    
    session = {
        'contactId': contact_id,
        'createdAt': datetime.now(timezone.utc).isoformat(),
        'callerPhone': attributes.get('CustomerPhoneNumber', 'unknown'),
        'conversation_history': [],
        'complete': False
    }
    save_session(session)
    return session


def save_session(session: dict):
    table = dynamodb.Table(SESSIONS_TABLE)
    session_copy = {
        'contactId': session['contactId'],
        'createdAt': session.get('createdAt', datetime.now(timezone.utc).isoformat()),
        'updatedAt': datetime.now(timezone.utc).isoformat(),
        'callerPhone': session.get('callerPhone', 'unknown'),
        'conversationHistory': json.dumps(session.get('conversation_history', [])),
        'complete': session.get('complete', False)
    }
    table.put_item(Item=session_copy)


def generate_greeting(session: dict) -> dict:
    greeting = (
        "Hello, thank you for calling the United States Census Bureau. "
        "My name is Sarah, and I'm here to help you with any Census-related questions. "
        "How may I assist you today?"
    )
    session['conversation_history'].append({
        'role': 'assistant',
        'content': [{"text": greeting}]
    })
    save_session(session)
    return {'message': greeting}


def process_turn(session: dict, user_input: str) -> dict:
    if not user_input or user_input.strip() == '':
        return {'message': "I'm sorry, I didn't catch that. Could you please repeat what you said?"}
    
    # Add user input in correct format for Bedrock Converse API
    session['conversation_history'].append({
        'role': 'user',
        'content': [{"text": user_input}]
    })
    
    messages = session['conversation_history']
    
    try:
        response = bedrock.converse(
            modelId=MODEL_ID,
            system=[{"text": SYSTEM_PROMPT}],
            messages=messages,
            inferenceConfig={
                "maxTokens": 500,
                "temperature": 0.7
            }
        )
        
        output = response.get('output', {})
        message = output.get('message', {})
        content = message.get('content', [])
        
        text_response = ""
        for block in content:
            if 'text' in block:
                text_response = block['text']
                break
        
        if not text_response:
            text_response = "I apologize, could you please rephrase that?"
        
        # Add assistant response
        session['conversation_history'].append({
            'role': 'assistant',
            'content': [{"text": text_response}]
        })
        
        # Check for goodbye indicators
        lower_input = user_input.lower()
        if any(word in lower_input for word in ['goodbye', 'bye', 'thank you', 'thanks', "that's all"]):
            session['complete'] = True
        
        save_session(session)
        return {'message': text_response}
        
    except Exception as e:
        logger.error(f"Bedrock error: {e}", exc_info=True)
        return {
            'message': "I apologize, I'm having trouble processing that. Could you please rephrase your question?"
        }
