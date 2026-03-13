"""
Census Survey API Handler

Provides REST API for the Survey Results UI:
- List surveys with filtering
- Get survey details
- Search surveys using vector similarity
- Get aggregate statistics
"""

import json
import os
import boto3
from datetime import datetime, timedelta
from decimal import Decimal
from boto3.dynamodb.conditions import Key, Attr

# Initialize clients
dynamodb = boto3.resource('dynamodb')
bedrock_agent = boto3.client('bedrock-agent-runtime')
s3 = boto3.client('s3')

SURVEYS_TABLE = os.environ.get('SURVEYS_TABLE', 'CensusSurveys-prod')
S3_BUCKET = os.environ.get('S3_BUCKET', 'census-survey-results')
KNOWLEDGE_BASE_ID = os.environ.get('KNOWLEDGE_BASE_ID', '')


def lambda_handler(event, context):
    """Main API handler."""
    
    print(f"Event: {json.dumps(event)}")
    
    http_method = event.get('httpMethod', 'GET')
    path = event.get('path', '')
    path_params = event.get('pathParameters') or {}
    query_params = event.get('queryStringParameters') or {}
    body = event.get('body')
    
    if body and isinstance(body, str):
        try:
            body = json.loads(body)
        except:
            body = {}
    
    try:
        if path == '/surveys' and http_method == 'GET':
            return list_surveys(query_params)
        elif path.startswith('/surveys/') and http_method == 'GET':
            survey_id = path_params.get('survey_id') or path.split('/')[-1]
            return get_survey(survey_id)
        elif path == '/search' and http_method == 'POST':
            return search_surveys(body)
        elif path == '/stats' and http_method == 'GET':
            return get_stats()
        else:
            return response(404, {'error': 'Not found'})
    
    except Exception as e:
        print(f"Error: {e}")
        import traceback
        traceback.print_exc()
        return response(500, {'error': str(e)})


def list_surveys(params: dict) -> dict:
    """List surveys with optional filtering."""
    
    table = dynamodb.Table(SURVEYS_TABLE)
    
    status_filter = params.get('status')
    limit = int(params.get('limit', 50))
    
    if status_filter:
        # Use GSI
        result = table.query(
            IndexName='status-created-index',
            KeyConditionExpression=Key('status').eq(status_filter),
            ScanIndexForward=False,
            Limit=limit
        )
    else:
        # Scan all
        result = table.scan(Limit=limit)
    
    items = result.get('Items', [])
    
    # Convert to JSON-safe format
    surveys = []
    for item in items:
        surveys.append({
            'survey_id': item['survey_id'],
            'status': item.get('status', 'unknown'),
            'created_at': item.get('created_at'),
            'updated_at': item.get('updated_at'),
            'household_count': item.get('responses', {}).get('household_count'),
            'progress': calculate_progress(item.get('state', {}))
        })
    
    return response(200, {
        'surveys': surveys,
        'count': len(surveys)
    })


def get_survey(survey_id: str) -> dict:
    """Get full survey details."""
    
    table = dynamodb.Table(SURVEYS_TABLE)
    result = table.get_item(Key={'survey_id': survey_id})
    
    item = result.get('Item')
    if not item:
        return response(404, {'error': 'Survey not found'})
    
    # Convert Decimals
    survey = json.loads(json.dumps(item, default=decimal_default))
    
    return response(200, {'survey': survey})


def search_surveys(body: dict) -> dict:
    """Search surveys using semantic search."""
    
    query = body.get('query', '')
    limit = body.get('limit', 10)
    
    if not query:
        return response(400, {'error': 'Query required'})
    
    # If Knowledge Base is configured, use it
    if KNOWLEDGE_BASE_ID:
        try:
            kb_response = bedrock_agent.retrieve(
                knowledgeBaseId=KNOWLEDGE_BASE_ID,
                retrievalQuery={'text': query},
                retrievalConfiguration={
                    'vectorSearchConfiguration': {
                        'numberOfResults': limit
                    }
                }
            )
            
            results = []
            for result in kb_response.get('retrievalResults', []):
                content = result.get('content', {}).get('text', '')
                try:
                    survey_data = json.loads(content)
                    results.append({
                        'survey_id': survey_data.get('survey_id'),
                        'score': result.get('score', 0),
                        'summary': survey_data.get('summary', '')
                    })
                except:
                    results.append({
                        'content': content[:200],
                        'score': result.get('score', 0)
                    })
            
            return response(200, {
                'results': results,
                'query': query,
                'source': 'knowledge_base'
            })
        
        except Exception as e:
            print(f"Knowledge Base search failed: {e}")
    
    # Fallback: scan and filter locally
    table = dynamodb.Table(SURVEYS_TABLE)
    result = table.scan(Limit=100)
    items = result.get('Items', [])
    
    # Simple keyword matching
    query_lower = query.lower()
    matched = []
    
    for item in items:
        score = 0
        summary = generate_summary(item)
        
        # Check various fields
        if query_lower in summary.lower():
            score += 1
        
        responses = item.get('responses', {})
        for person in responses.get('persons', []):
            if query_lower in str(person).lower():
                score += 0.5
        
        if score > 0:
            matched.append({
                'survey_id': item['survey_id'],
                'score': score,
                'summary': summary
            })
    
    # Sort by score
    matched.sort(key=lambda x: x['score'], reverse=True)
    
    return response(200, {
        'results': matched[:limit],
        'query': query,
        'source': 'local_search'
    })


def get_stats() -> dict:
    """Get aggregate statistics."""
    
    table = dynamodb.Table(SURVEYS_TABLE)
    
    # Scan and aggregate
    result = table.scan()
    items = result.get('Items', [])
    
    total = len(items)
    complete = sum(1 for i in items if i.get('status') == 'complete')
    in_progress = sum(1 for i in items if i.get('status') == 'in_progress')
    declined = sum(1 for i in items if i.get('status') == 'declined')
    
    total_persons = 0
    housing_breakdown = {}
    
    for item in items:
        responses = item.get('responses', {})
        persons = responses.get('persons', [])
        total_persons += len(persons)
        
        tenure = responses.get('housing_tenure', 'unknown')
        housing_breakdown[tenure] = housing_breakdown.get(tenure, 0) + 1
    
    avg_household = round(total_persons / complete, 1) if complete > 0 else 0
    
    return response(200, {
        'total_surveys': total,
        'complete': complete,
        'in_progress': in_progress,
        'declined': declined,
        'completion_rate': round(complete / total * 100, 1) if total > 0 else 0,
        'total_persons_recorded': total_persons,
        'average_household_size': avg_household,
        'housing_breakdown': housing_breakdown
    })


def generate_summary(item: dict) -> str:
    """Generate text summary of a survey."""
    
    responses = item.get('responses', {})
    persons = responses.get('persons', [])
    
    parts = [
        f"Survey {item.get('survey_id', 'unknown')[:8]}...",
        f"Status: {item.get('status', 'unknown')}",
        f"Household: {responses.get('household_count', '?')} people",
        f"Housing: {responses.get('housing_tenure', 'unknown')}"
    ]
    
    for p in persons:
        parts.append(f"Person: {p.get('name', 'Unknown')}")
    
    return ". ".join(parts)


def calculate_progress(state: dict) -> int:
    """Calculate survey progress percentage."""
    
    sections = ['greeting', 'address_confirmation', 'household_count', 'person_info', 'housing_tenure', 'closing']
    current = state.get('current_section', 'greeting')
    
    if state.get('complete'):
        return 100
    
    if current not in sections:
        return 0
    
    return int((sections.index(current) / len(sections)) * 100)


def decimal_default(obj):
    """JSON serializer for Decimal."""
    if isinstance(obj, Decimal):
        return float(obj) if obj % 1 else int(obj)
    raise TypeError


def response(status_code: int, body: dict) -> dict:
    """Create API Gateway response."""
    
    return {
        'statusCode': status_code,
        'headers': {
            'Content-Type': 'application/json',
            'Access-Control-Allow-Origin': '*',
            'Access-Control-Allow-Methods': 'GET,POST,OPTIONS',
            'Access-Control-Allow-Headers': 'Content-Type,Authorization'
        },
        'body': json.dumps(body, default=decimal_default)
    }
