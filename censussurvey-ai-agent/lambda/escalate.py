"""
EscalateToHuman Tool Lambda

Prepares context for transfer to human agent.
"""

import json
import boto3
import os
import logging
from datetime import datetime, timezone

logger = logging.getLogger()
logger.setLevel(logging.INFO)

dynamodb = boto3.resource('dynamodb', region_name=os.environ.get('AWS_REGION', 'us-east-1'))

ESCALATIONS_TABLE = os.environ.get('ESCALATIONS_TABLE', 'CensusEscalations')


def lambda_handler(event, context):
    """
    Prepare escalation to human agent.
    
    Input:
    {
        "reason": "Complex household situation",
        "priority": "normal",
        "context_summary": "Caller has multi-generational household with questions about who to count",
        "contact_id": "abc-123"
    }
    """
    logger.info(f"EscalateToHuman invoked: {json.dumps(event)}")
    
    try:
        reason = event.get('reason', 'Caller requested agent')
        priority = event.get('priority', 'normal')
        context_summary = event.get('context_summary', '')
        contact_id = event.get('contact_id', 'unknown')
        
        # Determine queue based on priority
        queue_map = {
            'urgent': 'Census-Priority-Queue',
            'high': 'Census-Specialist-Queue',
            'normal': 'Census-General-Queue'
        }
        target_queue = queue_map.get(priority, 'Census-General-Queue')
        
        # Store escalation record
        escalation = {
            'escalationId': f"ESC-{contact_id}",
            'contactId': contact_id,
            'reason': reason,
            'priority': priority,
            'contextSummary': context_summary,
            'targetQueue': target_queue,
            'createdAt': datetime.now(timezone.utc).isoformat(),
            'status': 'Pending'
        }
        
        try:
            table = dynamodb.Table(ESCALATIONS_TABLE)
            table.put_item(Item=escalation)
        except Exception as e:
            logger.warning(f"Could not store escalation: {e}")
        
        return {
            'statusCode': 200,
            'body': json.dumps({
                'success': True,
                'action': 'transfer',
                'targetQueue': target_queue,
                'priority': priority,
                'contextSummary': context_summary,
                'message': f'Transferring to {target_queue}. Please hold while I connect you with a specialist.'
            })
        }
        
    except Exception as e:
        logger.error(f"Escalation error: {e}", exc_info=True)
        return {
            'statusCode': 500,
            'body': json.dumps({
                'success': False,
                'message': 'I apologize, let me try to connect you with someone who can help.'
            })
        }
