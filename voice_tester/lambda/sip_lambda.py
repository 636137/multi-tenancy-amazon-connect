"""
Nova Sonic SIP Media App Lambda - AI Caller with Real Voice
Uses Bedrock invoke_model for text-to-speech instead of bidirectional streaming.
"""
import asyncio
import base64
import json
import logging
import os
import struct
import uuid
from datetime import datetime, timezone

import boto3

logger = logging.getLogger()
logger.setLevel(os.environ.get('LOG_LEVEL', 'INFO'))

# AWS clients
dynamodb = boto3.resource('dynamodb')
polly = boto3.client('polly')
bedrock = boto3.client('bedrock-runtime', region_name='us-east-1')
s3 = boto3.client('s3')

AUDIO_BUCKET = os.environ.get('AUDIO_BUCKET', 'treasury-voice-test-audio')


def handler(event, context):
    """Main Lambda handler"""
    logger.info(f"Event: {json.dumps(event, default=str)[:500]}")
    
    event_type = event.get('InvocationEventType', '')
    call_details = event.get('CallDetails', {})
    transaction_id = call_details.get('TransactionId', '')
    
    logger.info(f"Invocation: {event_type}, Transaction: {transaction_id}")
    
    if event_type == 'NEW_OUTBOUND_CALL':
        return handle_new_call(event, transaction_id)
    elif event_type == 'RINGING':
        return handle_ringing(event, transaction_id)
    elif event_type == 'CALL_ANSWERED':
        return handle_call_answered(event, transaction_id)
    elif event_type == 'ACTION_SUCCESSFUL':
        return handle_action_success(event, transaction_id)
    elif event_type == 'ACTION_FAILED':
        return handle_action_failed(event, transaction_id)
    elif event_type == 'HANGUP':
        return handle_hangup(event, transaction_id)
    else:
        return build_response([])


def handle_new_call(event, transaction_id):
    """Handle new outbound call"""
    args = {}
    participants = event.get('CallDetails', {}).get('Participants', [])
    if participants:
        args = participants[0].get('Arguments', {})
    
    update_status(transaction_id, 'dialing', {
        'persona_name': args.get('persona', 'AI Caller'),
        'goal_text': args.get('goal', 'Complete the call'),
        'call_mode': args.get('mode', 'voice_test')
    })
    return build_response([])


def handle_ringing(event, transaction_id):
    update_status(transaction_id, 'ringing')
    return build_response([])


def handle_call_answered(event, transaction_id):
    """Handle call answered - start AI conversation"""
    update_status(transaction_id, 'connected')
    
    item = get_test_item(transaction_id)
    persona = item.get('persona_name', 'Caller')
    goal = item.get('goal_text', 'Complete the call')
    
    # Generate AI greeting using Bedrock Claude + Polly
    greeting = generate_ai_response(persona, goal, [], 'greeting')
    logger.info(f"AI Greeting: {greeting}")
    
    audio_key = generate_polly_audio(greeting, transaction_id, 'greeting')
    update_transcript(transaction_id, 'caller', greeting)
    
    return build_response([
        play_audio_action(audio_key),
        receive_digits_action()
    ])


def handle_action_success(event, transaction_id):
    """Handle action success - respond to IVR"""
    action_data = event.get('ActionData', {})
    action_type = action_data.get('Type', '')
    
    logger.info(f"Action successful: {action_type}")
    
    if action_type == 'ReceiveDigits':
        digits = action_data.get('ReceivedDigits', '')
        if digits:
            update_transcript(transaction_id, 'ivr', f'DTMF:{digits}')
        
        item = get_test_item(transaction_id)
        turn = item.get('turn_count', 0) + 1
        update_item(transaction_id, {'turn_count': turn})
        
        if turn > 8:
            goodbye = "Thank you for your time. Goodbye."
            audio_key = generate_polly_audio(goodbye, transaction_id, 'goodbye')
            return build_response([play_audio_action(audio_key), hangup_action()])
        
        # Generate AI response
        persona = item.get('persona_name', 'Caller')
        goal = item.get('goal_text', '')
        transcript = item.get('transcript', [])
        
        response = generate_ai_response(persona, goal, transcript, f'turn {turn}')
        logger.info(f"AI Response: {response}")
        
        audio_key = generate_polly_audio(response, transaction_id, f'turn{turn}')
        update_transcript(transaction_id, 'caller', response)
        
        return build_response([
            play_audio_action(audio_key),
            receive_digits_action()
        ])
    
    elif action_type in ['PlayAudio', 'Speak']:
        return build_response([receive_digits_action()])
    
    return build_response([receive_digits_action()])


def handle_action_failed(event, transaction_id):
    logger.error(f"Action failed: {event.get('ActionData', {})}")
    return build_response([hangup_action()])


def handle_hangup(event, transaction_id):
    update_status(transaction_id, 'completed')
    return build_response([])


def generate_ai_response(persona: str, goal: str, transcript: list, context: str) -> str:
    """Generate AI response using Bedrock Claude"""
    
    transcript_text = ""
    if isinstance(transcript, list):
        for t in transcript[-4:]:
            if isinstance(t, dict):
                transcript_text += f"- {t.get('role', 'unknown')}: {t.get('text', '')}\n"
    
    prompt = f"""You are {persona}, a real person on a phone call.
Your goal: {goal}

{f"Recent conversation:{chr(10)}{transcript_text}" if transcript_text else ""}

Context: {context}

Generate a SHORT, natural phone response (1-2 sentences max).
Sound like a real human caller. Use natural language.
If answering questions, be helpful and stay on topic.
Do not use quotation marks or say "I would say" - just say it directly."""

    try:
        response = bedrock.invoke_model(
            modelId='anthropic.claude-3-haiku-20240307-v1:0',
            contentType='application/json',
            accept='application/json',
            body=json.dumps({
                'anthropic_version': 'bedrock-2023-05-31',
                'max_tokens': 100,
                'temperature': 0.8,
                'messages': [{'role': 'user', 'content': prompt}]
            })
        )
        result = json.loads(response['body'].read())
        text = result.get('content', [{}])[0].get('text', '').strip()
        # Clean up
        text = text.strip('"\'')
        return text if text else "I'm here to help."
    except Exception as e:
        logger.error(f"Bedrock error: {e}")
        return "Yes, I understand."


def generate_polly_audio(text: str, transaction_id: str, name: str) -> str:
    """Generate audio with Polly and upload to S3"""
    try:
        resp = polly.synthesize_speech(
            Text=text,
            OutputFormat='pcm',
            VoiceId='Ruth',
            SampleRate='8000',
            Engine='neural'
        )
        audio = resp['AudioStream'].read()
        return upload_audio_to_s3(audio, transaction_id, name)
    except Exception as e:
        logger.error(f"Polly error: {e}")
        return ""


def upload_audio_to_s3(audio: bytes, transaction_id: str, name: str) -> str:
    key = f"calls/{transaction_id}/{name}.pcm"
    try:
        s3.put_object(Bucket=AUDIO_BUCKET, Key=key, Body=audio, ContentType='audio/pcm')
        logger.info(f"Uploaded: s3://{AUDIO_BUCKET}/{key}")
        return key
    except Exception as e:
        logger.error(f"S3 error: {e}")
        return ""


def get_test_item(transaction_id: str) -> dict:
    try:
        table = dynamodb.Table('voice-test-scenarios')
        resp = table.get_item(Key={'test_id': transaction_id})
        return resp.get('Item', {})
    except:
        return {}


def update_status(transaction_id: str, status: str, extra: dict = None):
    try:
        table = dynamodb.Table('voice-test-scenarios')
        update_expr = 'SET #s = :s, updated_at = :u'
        expr_values = {':s': status, ':u': datetime.now(timezone.utc).isoformat()}
        expr_names = {'#s': 'status'}
        
        if extra:
            for k, v in extra.items():
                update_expr += f', #{k} = :{k}'
                expr_names[f'#{k}'] = k
                expr_values[f':{k}'] = v
        
        table.update_item(
            Key={'test_id': transaction_id},
            UpdateExpression=update_expr,
            ExpressionAttributeNames=expr_names,
            ExpressionAttributeValues=expr_values
        )
        logger.info(f"Updated {transaction_id} to {status}")
    except Exception as e:
        logger.error(f"DynamoDB error: {e}")


def update_item(transaction_id: str, updates: dict):
    try:
        table = dynamodb.Table('voice-test-scenarios')
        update_expr = 'SET ' + ', '.join(f'#{k} = :{k}' for k in updates.keys())
        expr_names = {f'#{k}': k for k in updates.keys()}
        expr_values = {f':{k}': v for k, v in updates.items()}
        table.update_item(
            Key={'test_id': transaction_id},
            UpdateExpression=update_expr,
            ExpressionAttributeNames=expr_names,
            ExpressionAttributeValues=expr_values
        )
    except Exception as e:
        logger.error(f"Update error: {e}")


def update_transcript(transaction_id: str, role: str, text: str):
    try:
        item = get_test_item(transaction_id)
        transcript = item.get('transcript', [])
        if isinstance(transcript, str):
            transcript = [transcript] if transcript else []
        transcript.append({'role': role, 'text': text, 'time': datetime.now(timezone.utc).isoformat()})
        update_item(transaction_id, {'transcript': transcript})
    except Exception as e:
        logger.error(f"Transcript error: {e}")


def build_response(actions):
    return {"SchemaVersion": "1.0", "Actions": actions}


def play_audio_action(s3_key: str) -> dict:
    if not s3_key:
        return speak_action("I'm here to help.")
    return {
        "Type": "PlayAudio",
        "Parameters": {
            "AudioSource": {
                "Type": "S3",
                "BucketName": AUDIO_BUCKET,
                "Key": s3_key
            }
        }
    }


def speak_action(text: str) -> dict:
    return {"Type": "Speak", "Parameters": {"Text": text, "Engine": "neural", "VoiceId": "Ruth"}}


def receive_digits_action() -> dict:
    return {
        "Type": "ReceiveDigits",
        "Parameters": {
            "InputDigitsRegex": ".*",
            "InBetweenDigitsDurationInMilliseconds": 4000,
            "FlushDigitsDurationInMilliseconds": 8000
        }
    }


def hangup_action() -> dict:
    return {"Type": "Hangup", "Parameters": {"SipResponseCode": "0"}}
