"""
Census Survey LLM Agent - Direct Bedrock Integration
Provides true LLM-orchestrated conversation for Amazon Connect
"""
import json
import boto3
from datetime import datetime

bedrock = boto3.client('bedrock-runtime', region_name='us-west-2')
dynamodb = boto3.resource('dynamodb', region_name='us-west-2')

SYSTEM_PROMPT = """You are a professional Census Bureau AI agent conducting the American Community Survey (ACS).

## YOUR MISSION
Conduct a complete census survey through natural conversation. Ask one question at a time and adapt based on responses.

## SURVEY SECTIONS (gather in this order)
1. CONSENT - Confirm they're willing to participate
2. HOUSEHOLD - How many people live there? Ages?
3. HOUSING - Rent or own? Type? Bedrooms?
4. EMPLOYMENT - Work status of adults
5. EDUCATION - Highest level for adults  
6. INCOME - Household income range

## RULES
- Ask ONE question at a time
- Be warm and conversational
- If they decline a question, say "No problem" and move on
- Data is protected by Title 13 U.S. Code

## OUTPUT FORMAT - CRITICAL
You MUST respond with valid JSON only, no other text:
{"response": "What you say to the caller", "data_collected": {}, "survey_complete": false}

Set survey_complete=true when all sections are done or they want to stop."""

def lambda_handler(event, context):
    """Handle Connect invocation for LLM conversation"""
    
    # Get contact attributes
    contact_data = event.get('Details', {}).get('ContactData', {})
    contact_attrs = contact_data.get('Attributes', {})
    
    # Get conversation state
    conversation_history = json.loads(contact_attrs.get('ConversationHistory', '[]'))
    collected_data = json.loads(contact_attrs.get('CollectedData', '{}'))
    turn_count = int(contact_attrs.get('TurnCount', '0'))
    
    # Get caller's input
    caller_input = contact_attrs.get('LastInput', '')
    
    # First turn - start the conversation
    if turn_count == 0:
        caller_input = "Hello, I'm ready to take the census survey."
    
    # Add caller's message to history (Converse API format)
    if caller_input:
        conversation_history.append({
            "role": "user",
            "content": [{"text": caller_input}]
        })
    
    # Call Bedrock Claude
    try:
        response = bedrock.converse(
            modelId='anthropic.claude-3-haiku-20240307-v1:0',
            system=[{"text": SYSTEM_PROMPT}],
            messages=conversation_history,
            inferenceConfig={
                "maxTokens": 500,
                "temperature": 0.7
            }
        )
        
        # Get response
        assistant_content = response['output']['message']['content'][0]['text']
        
        # Parse JSON response
        try:
            # Handle potential markdown code blocks
            text = assistant_content.strip()
            if text.startswith('```'):
                text = text.split('\n', 1)[1].rsplit('```', 1)[0]
            
            parsed = json.loads(text)
            spoken_response = parsed.get('response', text)
            new_data = parsed.get('data_collected', {})
            survey_complete = parsed.get('survey_complete', False)
            
            collected_data.update(new_data)
        except json.JSONDecodeError:
            spoken_response = assistant_content
            survey_complete = False
        
        # Add to history for next turn
        conversation_history.append({
            "role": "assistant",
            "content": [{"text": assistant_content}]
        })
        
        # Limit history to prevent token overflow
        if len(conversation_history) > 20:
            conversation_history = conversation_history[-20:]
        
        # Save to DynamoDB if complete
        if survey_complete or turn_count >= 15:
            try:
                table = dynamodb.Table('CensusSurveys-prod')
                contact_id = contact_data.get('ContactId', f'unknown-{datetime.utcnow().isoformat()}')
                table.put_item(Item={
                    'surveyId': contact_id,
                    'timestamp': datetime.utcnow().isoformat(),
                    'status': 'COMPLETE' if survey_complete else 'TIMEOUT',
                    'data': collected_data,
                    'turnCount': turn_count + 1
                })
            except Exception as e:
                print(f"DynamoDB error: {e}")
        
        return {
            'SpokenResponse': spoken_response,
            'ConversationHistory': json.dumps(conversation_history),
            'CollectedData': json.dumps(collected_data),
            'TurnCount': str(turn_count + 1),
            'SurveyComplete': 'true' if survey_complete else 'false'
        }
        
    except Exception as e:
        print(f"Bedrock error: {e}")
        return {
            'SpokenResponse': "I apologize for the technical difficulty. Let me try again. How many people live in your household?",
            'ConversationHistory': json.dumps(conversation_history),
            'CollectedData': json.dumps(collected_data),
            'TurnCount': str(turn_count + 1),
            'SurveyComplete': 'false'
        }
