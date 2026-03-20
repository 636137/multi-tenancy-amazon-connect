"""
CreateCallbackCase Tool Lambda

Schedules callbacks for Census callers and creates tracking cases.
"""

import json
import boto3
import os
import logging
from datetime import datetime, timezone
import uuid

logger = logging.getLogger()
logger.setLevel(logging.INFO)

dynamodb = boto3.resource('dynamodb', region_name=os.environ.get('AWS_REGION', 'us-east-1'))
connect = boto3.client('connect', region_name=os.environ.get('AWS_REGION', 'us-east-1'))

CASES_TABLE = os.environ.get('CASES_TABLE', 'CensusCallbackCases')
INSTANCE_ID = os.environ.get('CONNECT_INSTANCE_ID', 'a1f79dc3-8a46-481d-bf15-b214a7a8b05f')


def lambda_handler(event, context):
    """
    Create a callback case.
    
    Input:
    {
        "preferred_time": "tomorrow afternoon",
        "language": "English",
        "reason": "Survey assistance",
        "contact_id": "abc-123",
        "caller_phone": "+15551234567"
    }
    """
    logger.info(f"CreateCallbackCase invoked: {json.dumps(event)}")
    
    try:
        # Extract parameters
        preferred_time = event.get('preferred_time', 'next business day')
        language = event.get('language', 'English')
        reason = event.get('reason', 'General inquiry')
        contact_id = event.get('contact_id', 'unknown')
        caller_phone = event.get('caller_phone', 'unknown')
        
        # Generate case ID
        case_id = f"CASE-{uuid.uuid4().hex[:8].upper()}"
        
        # Create case record
        case = {
            'caseId': case_id,
            'contactId': contact_id,
            'callerPhone': caller_phone,
            'preferredTime': preferred_time,
            'language': language,
            'reason': reason,
            'status': 'Scheduled',
            'createdAt': datetime.now(timezone.utc).isoformat(),
            'sla': '24 hours'
        }
        
        # Store in DynamoDB
        table = dynamodb.Table(CASES_TABLE)
        table.put_item(Item=case)
        
        logger.info(f"Callback case created: {case_id}")
        
        return {
            'statusCode': 200,
            'body': json.dumps({
                'success': True,
                'caseId': case_id,
                'status': 'Scheduled',
                'sla': '24 hours',
                'message': f'Callback scheduled for {preferred_time}. Your case number is {case_id}.'
            })
        }
        
    except Exception as e:
        logger.error(f"Error creating callback case: {e}", exc_info=True)
        return {
            'statusCode': 500,
            'body': json.dumps({
                'success': False,
                'error': str(e),
                'message': 'Sorry, I was unable to schedule the callback. Let me connect you with a specialist.'
            })
        }
