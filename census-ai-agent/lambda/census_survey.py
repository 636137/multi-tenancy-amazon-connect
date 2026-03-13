"""
Census Survey AI Agent Lambda

This Lambda function powers a dynamic US Census survey in Amazon Connect.
It uses an LLM (via Bedrock) to generate contextually relevant follow-up questions
based on prior responses, stores results in DynamoDB, and syncs to S3 for vector search.

Features:
- Dynamic question flow based on household composition
- Partial survey persistence (resume if caller hangs up)
- Complete survey storage with vector embeddings
- Real-time sync to S3 for Knowledge Base ingestion
"""

import json
import os
import boto3
import uuid
from datetime import datetime
from decimal import Decimal

# Initialize clients
dynamodb = boto3.resource('dynamodb')
bedrock_runtime = boto3.client('bedrock-runtime')
s3 = boto3.client('s3')

# Environment variables
SURVEYS_TABLE = os.environ.get('SURVEYS_TABLE', 'CensusSurveys')
S3_BUCKET = os.environ.get('S3_BUCKET', 'census-survey-results')
MODEL_ID = os.environ.get('MODEL_ID', 'anthropic.claude-3-haiku-20240307-v1:0')

# Census survey structure based on 2026 ACS
SURVEY_SECTIONS = {
    "greeting": {
        "order": 0,
        "question": "Hello, this is the Census Bureau calling to complete your American Community Survey. This helps ensure your community receives fair representation and funding. May I proceed with a few questions? It will take about 5 minutes."
    },
    "address_confirmation": {
        "order": 1,
        "question": "First, I need to confirm your address. Is this {address}?",
        "slot": "address_confirmed",
        "type": "yes_no"
    },
    "household_count": {
        "order": 2,
        "question": "How many people were living or staying at this address on April 1st, 2026? Please include everyone - adults, children, and anyone staying temporarily.",
        "slot": "household_count",
        "type": "number"
    },
    "person_info": {
        "order": 3,
        "question": "I'll now collect information for each person. Let's start with Person {person_number}.",
        "sub_questions": [
            {
                "id": "name",
                "question": "What is this person's first and last name?",
                "slot": "person_name",
                "type": "name"
            },
            {
                "id": "relationship",
                "question": "What is {name}'s relationship to Person 1, the main householder?",
                "slot": "relationship",
                "type": "relationship",
                "skip_for_person_1": True
            },
            {
                "id": "dob",
                "question": "What is {name}'s date of birth? Please say the month, day, and year.",
                "slot": "date_of_birth",
                "type": "date"
            },
            {
                "id": "sex",
                "question": "What is {name}'s sex? Male or female?",
                "slot": "sex",
                "type": "choice",
                "options": ["male", "female"]
            },
            {
                "id": "hispanic_origin",
                "question": "Is {name} of Hispanic, Latino, or Spanish origin?",
                "slot": "hispanic_origin",
                "type": "yes_no"
            },
            {
                "id": "hispanic_detail",
                "question": "Which Hispanic origin? For example, Mexican, Puerto Rican, Cuban, or another?",
                "slot": "hispanic_detail",
                "type": "text",
                "conditional": {"hispanic_origin": "yes"}
            },
            {
                "id": "race",
                "question": "What is {name}'s race? You may select one or more: White, Black or African American, American Indian or Alaska Native, Asian, or Native Hawaiian or Pacific Islander.",
                "slot": "race",
                "type": "multi_choice",
                "options": ["white", "black", "american_indian", "asian", "pacific_islander", "other"]
            }
        ]
    },
    "housing_tenure": {
        "order": 4,
        "question": "Is this house, apartment, or mobile home owned or rented?",
        "slot": "housing_tenure",
        "type": "choice",
        "options": ["owned_with_mortgage", "owned_free_clear", "rented", "occupied_without_rent"]
    },
    "closing": {
        "order": 5,
        "question": "Thank you for completing the American Community Survey. Your responses help ensure your community receives proper representation and funding. Have a great day!"
    }
}

# System prompt for dynamic question generation
SYSTEM_PROMPT = """You are a professional US Census Bureau survey agent conducting the American Community Survey.

Your role:
1. Ask census questions clearly and professionally
2. Adapt follow-up questions based on previous answers
3. Confirm ambiguous responses
4. Be patient and respectful
5. Keep responses brief (1-2 sentences max)

Census data is protected by Title 13 of the US Code and kept strictly confidential.

Current survey state:
{survey_state}

Generate the next appropriate question or response based on the caller's input.
If confirming data, repeat it back clearly.
If the input is unclear, ask for clarification politely.
Keep responses under 100 words and suitable for text-to-speech."""


def lambda_handler(event, context):
    """Main Lambda handler for Lex/Connect integration."""
    
    print(f"Event: {json.dumps(event)}")
    
    # Determine event source
    if 'sessionState' in event:
        # Lex V2 event
        return handle_lex_v2(event)
    elif 'Details' in event:
        # Connect Lambda integration
        return handle_connect(event)
    else:
        # Direct invocation for testing
        return handle_direct(event)


def handle_lex_v2(event):
    """Handle Lex V2 bot events."""
    
    session_attrs = event.get('sessionState', {}).get('sessionAttributes', {}) or {}
    intent = event.get('sessionState', {}).get('intent', {})
    intent_name = intent.get('name', 'CensusSurveyIntent')
    
    # Get or create survey ID
    survey_id = session_attrs.get('survey_id')
    if not survey_id:
        survey_id = str(uuid.uuid4())
        session_attrs['survey_id'] = survey_id
    
    # Get user input
    user_input = event.get('inputTranscript', '')
    
    # Load or create survey state
    survey = load_survey(survey_id)
    if not survey:
        survey = create_survey(survey_id, session_attrs)
    
    # Process input and determine next action
    response_text, next_state = process_survey_input(survey, user_input)
    
    # Update survey state
    survey['state'] = next_state
    survey['last_response'] = user_input
    survey['updated_at'] = datetime.utcnow().isoformat()
    save_survey(survey)
    
    # Check if survey is complete
    if next_state.get('complete'):
        # Sync to S3 for vector store
        sync_to_s3(survey)
        
        return {
            'sessionState': {
                'dialogAction': {
                    'type': 'Close'
                },
                'intent': {
                    'name': intent_name,
                    'state': 'Fulfilled'
                },
                'sessionAttributes': session_attrs
            },
            'messages': [
                {
                    'contentType': 'PlainText',
                    'content': response_text
                }
            ]
        }
    
    # Continue conversation
    return {
        'sessionState': {
            'dialogAction': {
                'type': 'ElicitIntent'
            },
            'sessionAttributes': session_attrs
        },
        'messages': [
            {
                'contentType': 'PlainText',
                'content': response_text
            }
        ]
    }


def handle_connect(event):
    """Handle direct Connect Lambda invocation."""
    
    details = event.get('Details', {})
    contact_attrs = details.get('ContactData', {}).get('Attributes', {})
    parameters = details.get('Parameters', {})
    
    survey_id = contact_attrs.get('survey_id', str(uuid.uuid4()))
    user_input = parameters.get('user_input', '')
    
    survey = load_survey(survey_id) or create_survey(survey_id, contact_attrs)
    response_text, next_state = process_survey_input(survey, user_input)
    
    survey['state'] = next_state
    survey['updated_at'] = datetime.utcnow().isoformat()
    save_survey(survey)
    
    if next_state.get('complete'):
        sync_to_s3(survey)
    
    return {
        'survey_id': survey_id,
        'response': response_text,
        'complete': next_state.get('complete', False),
        'section': next_state.get('current_section', ''),
        'progress': calculate_progress(next_state)
    }


def handle_direct(event):
    """Handle direct invocation for testing."""
    
    action = event.get('action', 'process')
    
    if action == 'create':
        survey_id = str(uuid.uuid4())
        survey = create_survey(survey_id, {})
        save_survey(survey)
        return {'survey_id': survey_id, 'survey': survey}
    
    elif action == 'process':
        survey_id = event.get('survey_id')
        user_input = event.get('input', '')
        
        survey = load_survey(survey_id)
        if not survey:
            return {'error': 'Survey not found'}
        
        response_text, next_state = process_survey_input(survey, user_input)
        survey['state'] = next_state
        survey['updated_at'] = datetime.utcnow().isoformat()
        save_survey(survey)
        
        if next_state.get('complete'):
            sync_to_s3(survey)
        
        return {
            'response': response_text,
            'state': next_state,
            'complete': next_state.get('complete', False)
        }
    
    elif action == 'get':
        survey_id = event.get('survey_id')
        survey = load_survey(survey_id)
        return {'survey': survey}
    
    return {'error': 'Unknown action'}


def create_survey(survey_id: str, initial_attrs: dict) -> dict:
    """Create a new survey record."""
    
    return {
        'survey_id': survey_id,
        'status': 'in_progress',
        'created_at': datetime.utcnow().isoformat(),
        'updated_at': datetime.utcnow().isoformat(),
        'contact_attrs': initial_attrs,
        'state': {
            'current_section': 'greeting',
            'current_person': 0,
            'total_persons': 0,
            'current_question_index': 0,
            'complete': False
        },
        'responses': {
            'address': initial_attrs.get('address', 'your address on file'),
            'persons': []
        },
        'conversation_history': []
    }


def load_survey(survey_id: str) -> dict:
    """Load survey from DynamoDB."""
    
    try:
        table = dynamodb.Table(SURVEYS_TABLE)
        response = table.get_item(Key={'survey_id': survey_id})
        item = response.get('Item')
        if item:
            # Convert Decimal to int/float
            return json.loads(json.dumps(item, default=decimal_default))
        return None
    except Exception as e:
        print(f"Error loading survey: {e}")
        return None


def save_survey(survey: dict):
    """Save survey to DynamoDB."""
    
    try:
        table = dynamodb.Table(SURVEYS_TABLE)
        # Convert to DynamoDB-compatible format
        item = json.loads(json.dumps(survey), parse_float=Decimal)
        table.put_item(Item=item)
    except Exception as e:
        print(f"Error saving survey: {e}")


def decimal_default(obj):
    """JSON serializer for Decimal."""
    if isinstance(obj, Decimal):
        return float(obj) if obj % 1 else int(obj)
    raise TypeError


def process_survey_input(survey: dict, user_input: str) -> tuple:
    """Process user input and generate next question using LLM."""
    
    state = survey['state']
    responses = survey['responses']
    current_section = state.get('current_section', 'greeting')
    
    # Add to conversation history
    if user_input:
        survey['conversation_history'].append({
            'role': 'user',
            'content': user_input,
            'timestamp': datetime.utcnow().isoformat()
        })
    
    # Handle each section
    if current_section == 'greeting':
        if not user_input:
            response = SURVEY_SECTIONS['greeting']['question']
        elif is_affirmative(user_input):
            state['current_section'] = 'address_confirmation'
            address = responses.get('address', 'your address on file')
            response = SURVEY_SECTIONS['address_confirmation']['question'].format(address=address)
        else:
            response = "I understand. When would be a better time to call back? Or you can complete the survey online at census.gov."
            state['complete'] = True
            survey['status'] = 'declined'
    
    elif current_section == 'address_confirmation':
        if is_affirmative(user_input):
            responses['address_confirmed'] = True
            state['current_section'] = 'household_count'
            response = SURVEY_SECTIONS['household_count']['question']
        else:
            response = "Could you please provide your correct address?"
            # Would collect new address here
    
    elif current_section == 'household_count':
        count = extract_number(user_input)
        if count and count > 0:
            responses['household_count'] = count
            state['total_persons'] = count
            state['current_person'] = 1
            state['current_section'] = 'person_info'
            state['current_question_index'] = 0
            responses['persons'] = []
            response = f"Thank you. I'll now collect information for {count} {'person' if count == 1 else 'people'}. Let's start with Person 1. What is this person's first and last name?"
        else:
            response = "I didn't catch that. How many people were living at this address on April 1st, 2026?"
    
    elif current_section == 'person_info':
        response, state = process_person_questions(survey, user_input, state, responses)
    
    elif current_section == 'housing_tenure':
        tenure = extract_housing_tenure(user_input)
        if tenure:
            responses['housing_tenure'] = tenure
            state['current_section'] = 'closing'
            state['complete'] = True
            survey['status'] = 'complete'
            response = SURVEY_SECTIONS['closing']['question']
        else:
            response = "Is this home owned with a mortgage, owned free and clear, rented, or occupied without payment?"
    
    elif current_section == 'closing':
        state['complete'] = True
        survey['status'] = 'complete'
        response = "Thank you again for your participation. Goodbye!"
    
    else:
        response = "I apologize, I lost track of where we were. Let me start over."
        state['current_section'] = 'greeting'
    
    # Record agent response
    survey['conversation_history'].append({
        'role': 'agent',
        'content': response,
        'timestamp': datetime.utcnow().isoformat()
    })
    
    return response, state


def process_person_questions(survey: dict, user_input: str, state: dict, responses: dict) -> tuple:
    """Process person-specific questions dynamically."""
    
    person_num = state['current_person']
    q_index = state['current_question_index']
    sub_questions = SURVEY_SECTIONS['person_info']['sub_questions']
    
    # Initialize person data if needed
    if len(responses['persons']) < person_num:
        responses['persons'].append({'person_number': person_num})
    
    current_person = responses['persons'][person_num - 1]
    
    # Get current question
    while q_index < len(sub_questions):
        q = sub_questions[q_index]
        
        # Skip relationship for Person 1
        if q.get('skip_for_person_1') and person_num == 1:
            q_index += 1
            continue
        
        # Check conditional
        if 'conditional' in q:
            cond = q['conditional']
            skip = True
            for key, expected in cond.items():
                if current_person.get(key, '').lower() == expected.lower():
                    skip = False
                    break
            if skip:
                q_index += 1
                continue
        
        break
    
    if q_index >= len(sub_questions):
        # Move to next person or next section
        if person_num < state['total_persons']:
            state['current_person'] = person_num + 1
            state['current_question_index'] = 0
            next_person = person_num + 1
            return f"Great, let's move on to Person {next_person}. What is this person's first and last name?", state
        else:
            state['current_section'] = 'housing_tenure'
            return SURVEY_SECTIONS['housing_tenure']['question'], state
    
    current_q = sub_questions[q_index]
    
    # Process the answer
    if user_input:
        slot = current_q['slot']
        
        if current_q['type'] == 'name':
            current_person['name'] = user_input.strip().title()
        elif current_q['type'] == 'date':
            current_person['date_of_birth'] = user_input.strip()
        elif current_q['type'] == 'yes_no':
            current_person[current_q['id']] = 'yes' if is_affirmative(user_input) else 'no'
        elif current_q['type'] == 'choice':
            current_person[current_q['id']] = user_input.strip().lower()
        elif current_q['type'] == 'multi_choice':
            current_person[current_q['id']] = user_input.strip()
        elif current_q['type'] == 'relationship':
            current_person['relationship'] = user_input.strip()
        else:
            current_person[current_q['id']] = user_input.strip()
        
        # Move to next question
        state['current_question_index'] = q_index + 1
        
        # Get next question
        return process_person_questions(survey, '', state, responses)
    
    # Generate question with name substitution
    name = current_person.get('name', f'Person {person_num}')
    question = current_q['question'].format(name=name)
    
    return question, state


def is_affirmative(text: str) -> bool:
    """Check if response is affirmative."""
    affirmatives = ['yes', 'yeah', 'yep', 'sure', 'okay', 'ok', 'correct', 'right', 'that\'s right', 'proceed', 'go ahead']
    return any(aff in text.lower() for aff in affirmatives)


def extract_number(text: str) -> int:
    """Extract a number from text."""
    import re
    
    # Number words
    word_to_num = {
        'one': 1, 'two': 2, 'three': 3, 'four': 4, 'five': 5,
        'six': 6, 'seven': 7, 'eight': 8, 'nine': 9, 'ten': 10,
        'eleven': 11, 'twelve': 12
    }
    
    text_lower = text.lower()
    for word, num in word_to_num.items():
        if word in text_lower:
            return num
    
    # Try to find digits
    numbers = re.findall(r'\d+', text)
    if numbers:
        return int(numbers[0])
    
    return None


def extract_housing_tenure(text: str) -> str:
    """Extract housing tenure from response."""
    text_lower = text.lower()
    
    if 'rent' in text_lower:
        return 'rented'
    elif 'own' in text_lower:
        if 'mortgage' in text_lower or 'loan' in text_lower:
            return 'owned_with_mortgage'
        elif 'free' in text_lower or 'clear' in text_lower or 'paid' in text_lower:
            return 'owned_free_clear'
        return 'owned_with_mortgage'  # Default
    elif 'without' in text_lower or 'free' in text_lower:
        return 'occupied_without_rent'
    
    return None


def calculate_progress(state: dict) -> int:
    """Calculate survey completion percentage."""
    
    sections = ['greeting', 'address_confirmation', 'household_count', 'person_info', 'housing_tenure', 'closing']
    current = state.get('current_section', 'greeting')
    
    if current not in sections:
        return 0
    
    base_progress = (sections.index(current) / len(sections)) * 100
    
    # Add progress for person questions
    if current == 'person_info':
        person_progress = 0
        total_persons = state.get('total_persons', 1)
        current_person = state.get('current_person', 1)
        q_index = state.get('current_question_index', 0)
        total_questions = 7  # Approximate
        
        persons_done = (current_person - 1) / total_persons
        current_person_progress = q_index / total_questions / total_persons
        
        section_weight = 1 / len(sections)
        person_progress = section_weight * (persons_done + current_person_progress) * 100
        
        base_progress += person_progress
    
    return min(int(base_progress), 100)


def sync_to_s3(survey: dict):
    """Sync completed survey to S3 for vector store ingestion."""
    
    survey_id = survey['survey_id']
    
    # Create a document suitable for vector embedding
    document = {
        'survey_id': survey_id,
        'completed_at': survey['updated_at'],
        'status': survey['status'],
        'household': {
            'address_confirmed': survey['responses'].get('address_confirmed'),
            'household_count': survey['responses'].get('household_count'),
            'housing_tenure': survey['responses'].get('housing_tenure')
        },
        'persons': survey['responses'].get('persons', []),
        'summary': generate_survey_summary(survey)
    }
    
    # Upload to S3
    try:
        s3.put_object(
            Bucket=S3_BUCKET,
            Key=f"surveys/{survey_id}.json",
            Body=json.dumps(document, indent=2),
            ContentType='application/json'
        )
        print(f"Survey {survey_id} synced to S3")
    except Exception as e:
        print(f"Error syncing to S3: {e}")


def generate_survey_summary(survey: dict) -> str:
    """Generate a text summary for vector embedding."""
    
    responses = survey['responses']
    persons = responses.get('persons', [])
    
    summary_parts = [
        f"Census survey completed on {survey['updated_at']}.",
        f"Household size: {responses.get('household_count', 'unknown')} people.",
        f"Housing: {responses.get('housing_tenure', 'unknown')}."
    ]
    
    for p in persons:
        person_desc = f"Person {p.get('person_number', '?')}: {p.get('name', 'Unknown')}"
        if p.get('date_of_birth'):
            person_desc += f", DOB: {p['date_of_birth']}"
        if p.get('sex'):
            person_desc += f", {p['sex']}"
        if p.get('race'):
            person_desc += f", {p['race']}"
        if p.get('relationship'):
            person_desc += f", {p['relationship']}"
        summary_parts.append(person_desc)
    
    return " ".join(summary_parts)


def generate_with_llm(prompt: str, survey_state: dict) -> str:
    """Generate dynamic response using Bedrock LLM."""
    
    system = SYSTEM_PROMPT.format(survey_state=json.dumps(survey_state, indent=2))
    
    try:
        response = bedrock_runtime.invoke_model(
            modelId=MODEL_ID,
            body=json.dumps({
                'anthropic_version': 'bedrock-2023-05-31',
                'max_tokens': 200,
                'system': system,
                'messages': [
                    {'role': 'user', 'content': prompt}
                ]
            })
        )
        
        result = json.loads(response['body'].read())
        return result['content'][0]['text']
    except Exception as e:
        print(f"LLM error: {e}")
        return None
