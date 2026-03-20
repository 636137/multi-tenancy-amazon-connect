"""
CheckSurveyStatus Tool Lambda

Checks if a household has completed the Census survey.
"""

import json
import boto3
import os
import logging

logger = logging.getLogger()
logger.setLevel(logging.INFO)

dynamodb = boto3.resource('dynamodb', region_name=os.environ.get('AWS_REGION', 'us-east-1'))

RESPONSES_TABLE = os.environ.get('RESPONSES_TABLE', 'CensusResponses')
ADDRESSES_TABLE = os.environ.get('ADDRESSES_TABLE', 'CensusAddresses')


def lambda_handler(event, context):
    """
    Check survey completion status.
    
    Input:
    {
        "census_id": "ABC123",
        "address": "123 Main St"
    }
    """
    logger.info(f"CheckSurveyStatus invoked: {json.dumps(event)}")
    
    try:
        census_id = event.get('census_id', '')
        address = event.get('address', '')
        
        # Demo response - in production would query actual Census records
        if census_id:
            # Look up by Census ID
            status = lookup_by_census_id(census_id)
        elif address:
            # Look up by address
            status = lookup_by_address(address)
        else:
            return {
                'statusCode': 400,
                'body': json.dumps({
                    'success': False,
                    'message': 'Please provide either a Census ID or address to check status.'
                })
            }
        
        return {
            'statusCode': 200,
            'body': json.dumps(status)
        }
        
    except Exception as e:
        logger.error(f"Error checking status: {e}", exc_info=True)
        return {
            'statusCode': 500,
            'body': json.dumps({
                'success': False,
                'message': 'Unable to check status at this time.'
            })
        }


def lookup_by_census_id(census_id: str) -> dict:
    """Look up status by Census ID."""
    table = dynamodb.Table(RESPONSES_TABLE)
    
    try:
        response = table.get_item(Key={'censusId': census_id})
        if 'Item' in response:
            item = response['Item']
            return {
                'success': True,
                'found': True,
                'status': item.get('status', 'Unknown'),
                'completedAt': item.get('completedAt'),
                'message': f"Survey status: {item.get('status', 'In Progress')}"
            }
    except Exception as e:
        logger.warning(f"Lookup error: {e}")
    
    return {
        'success': True,
        'found': False,
        'message': 'No record found for that Census ID. You may need to start a new survey.'
    }


def lookup_by_address(address: str) -> dict:
    """Look up status by address - simplified for demo."""
    # In production, would do address matching against Census database
    return {
        'success': True,
        'found': False,
        'message': 'To check your status, please provide the Census ID from your mailing, or I can help you start a new survey.'
    }
