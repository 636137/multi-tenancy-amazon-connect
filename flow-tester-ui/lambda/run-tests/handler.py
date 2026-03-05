"""
Run Tests Lambda

Triggers PSTN voice tests using Chime SDK SIP Media Application
with Nova Sonic AI caller.
"""
import json
import boto3
import logging
from typing import Dict, List, Any
from dataclasses import dataclass
import uuid
import os

logger = logging.getLogger()
logger.setLevel(logging.INFO)

chime = boto3.client('chime-sdk-voice', region_name='us-east-1')
dynamodb = boto3.resource('dynamodb')
lambda_client = boto3.client('lambda')


@dataclass
class TestResult:
    """Result of a test execution."""
    scenario_id: str
    status: str  # running, passed, failed, error
    call_id: str = ""
    transaction_id: str = ""
    duration_seconds: float = 0
    transcript: List[str] = None
    errors: List[str] = None


def handler(event, context):
    """Run voice tests against Connect."""
    
    logger.info(f"Event: {json.dumps(event)}")
    
    try:
        body = json.loads(event.get('body', '{}'))
        
        # Support single scenario or batch
        scenarios = body.get('scenarios', [])
        scenario_ids = body.get('scenario_ids', [])
        
        # Config
        config = body.get('config', {})
        sip_media_app_id = config.get('sip_media_app_id', os.environ.get('SIP_MEDIA_APP_ID'))
        from_number = config.get('from_number', os.environ.get('FROM_NUMBER'))
        
        if not sip_media_app_id:
            return error_response(400, "Missing SIP Media Application ID")
        
        # Load scenarios from DynamoDB if IDs provided
        if scenario_ids and not scenarios:
            scenarios = load_scenarios(scenario_ids)
        
        if not scenarios:
            return error_response(400, "No scenarios provided")
        
        # Execute tests
        results = execute_tests(scenarios, sip_media_app_id, from_number, config)
        
        return success_response({
            'results': [r.__dict__ for r in results],
            'summary': {
                'total': len(results),
                'running': sum(1 for r in results if r.status == 'running'),
                'errors': sum(1 for r in results if r.status == 'error')
            }
        })
        
    except Exception as e:
        logger.error(f"Error running tests: {e}", exc_info=True)
        return error_response(500, str(e))


def load_scenarios(scenario_ids: List[str]) -> List[Dict]:
    """Load scenarios from DynamoDB."""
    
    scenarios = []
    table = dynamodb.Table('flow-test-scenarios')
    
    for sid in scenario_ids:
        try:
            response = table.get_item(Key={'scenario_id': sid})
            if 'Item' in response:
                item = response['Item']
                scenario_data = json.loads(item.get('scenario_data', '{}'))
                scenarios.append(scenario_data)
        except Exception as e:
            logger.warning(f"Could not load scenario {sid}: {e}")
    
    return scenarios


def execute_tests(scenarios: List[Dict], sip_app_id: str, 
                  from_number: str, config: Dict) -> List[TestResult]:
    """Execute voice tests."""
    
    results = []
    concurrent = config.get('concurrent', False)
    
    for scenario in scenarios:
        try:
            result = start_test_call(scenario, sip_app_id, from_number)
            results.append(result)
            
            # Update DynamoDB
            update_test_status(scenario['id'], result)
            
        except Exception as e:
            logger.error(f"Error starting test {scenario.get('id')}: {e}")
            results.append(TestResult(
                scenario_id=scenario.get('id', 'unknown'),
                status='error',
                errors=[str(e)]
            ))
    
    return results


def start_test_call(scenario: Dict, sip_app_id: str, from_number: str) -> TestResult:
    """Start a single test call using Chime SDK."""
    
    scenario_id = scenario.get('id', str(uuid.uuid4()))
    phone_number = scenario.get('phone_number')
    
    if not phone_number:
        raise ValueError("Scenario missing phone_number")
    
    # Ensure phone number format
    if not phone_number.startswith('+'):
        phone_number = f"+1{phone_number}"
    
    # Build SIP headers with test context
    sip_headers = {
        'X-Test-Scenario-Id': scenario_id,
        'X-Test-Name': scenario.get('name', 'Unknown Test')[:100],
    }
    
    # Add persona info
    persona = scenario.get('persona', {})
    if persona:
        sip_headers['X-Persona-Voice'] = persona.get('voice_id', 'Joanna')
        sip_headers['X-Persona-Behavior'] = persona.get('behavior', 'cooperative')
    
    # Add steps as compressed JSON
    steps = scenario.get('steps', [])
    if steps:
        steps_json = json.dumps(steps[:10])  # Limit for header size
        if len(steps_json) < 1000:
            sip_headers['X-Test-Steps'] = steps_json
    
    try:
        # Create outbound call via Chime SDK
        response = chime.create_sip_media_application_call(
            SipMediaApplicationId=sip_app_id,
            FromPhoneNumber=from_number,
            ToPhoneNumber=phone_number,
            SipHeaders=sip_headers,
            ArgumentsMap={
                'scenario_id': scenario_id,
                'scenario_data': json.dumps(scenario),
                'test_mode': 'true'
            }
        )
        
        call_id = response.get('SipMediaApplicationCall', {}).get('CallId', '')
        transaction_id = response.get('SipMediaApplicationCall', {}).get('TransactionId', '')
        
        logger.info(f"Started call {call_id} for scenario {scenario_id}")
        
        return TestResult(
            scenario_id=scenario_id,
            status='running',
            call_id=call_id,
            transaction_id=transaction_id
        )
        
    except Exception as e:
        logger.error(f"Chime call failed: {e}")
        raise


def update_test_status(scenario_id: str, result: TestResult):
    """Update test status in DynamoDB."""
    
    try:
        table = dynamodb.Table('flow-test-scenarios')
        
        table.update_item(
            Key={'scenario_id': scenario_id},
            UpdateExpression='SET #status = :status, call_id = :call_id, transaction_id = :tid',
            ExpressionAttributeNames={'#status': 'status'},
            ExpressionAttributeValues={
                ':status': result.status,
                ':call_id': result.call_id,
                ':tid': result.transaction_id
            }
        )
        
    except Exception as e:
        logger.warning(f"Could not update status for {scenario_id}: {e}")


def get_test_results(event, context):
    """Get results for running/completed tests."""
    
    try:
        body = json.loads(event.get('body', '{}'))
        scenario_ids = body.get('scenario_ids', [])
        
        results = []
        table = dynamodb.Table('flow-test-scenarios')
        
        for sid in scenario_ids:
            response = table.get_item(Key={'scenario_id': sid})
            if 'Item' in response:
                results.append(response['Item'])
        
        return success_response({'results': results})
        
    except Exception as e:
        return error_response(500, str(e))


def cancel_test(event, context):
    """Cancel a running test."""
    
    try:
        body = json.loads(event.get('body', '{}'))
        call_id = body.get('call_id')
        sip_app_id = body.get('sip_media_app_id', os.environ.get('SIP_MEDIA_APP_ID'))
        
        if call_id and sip_app_id:
            # End the call
            chime.update_sip_media_application_call(
                SipMediaApplicationId=sip_app_id,
                TransactionId=call_id,
                Arguments={'action': 'hangup'}
            )
        
        return success_response({'cancelled': True})
        
    except Exception as e:
        return error_response(500, str(e))


def success_response(data: Any) -> Dict:
    """Return success response."""
    return {
        'statusCode': 200,
        'headers': {
            'Content-Type': 'application/json',
            'Access-Control-Allow-Origin': '*',
            'Access-Control-Allow-Headers': 'Content-Type,Authorization',
            'Access-Control-Allow-Methods': 'POST, GET, OPTIONS'
        },
        'body': json.dumps(data, default=str)
    }


def error_response(status: int, message: str) -> Dict:
    """Return error response."""
    return {
        'statusCode': status,
        'headers': {
            'Content-Type': 'application/json',
            'Access-Control-Allow-Origin': '*'
        },
        'body': json.dumps({'error': message})
    }
