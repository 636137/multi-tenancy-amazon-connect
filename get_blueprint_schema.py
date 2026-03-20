#!/usr/bin/env python3
"""Get full schema from existing blueprint."""

import boto3
import json

client = boto3.client('bedrock-data-automation', region_name='us-east-1')

# Get the existing blueprint
blueprint_arn = 'arn:aws:bedrock:us-east-1:593804350786:blueprint/47daccabd3cf'
response = client.get_blueprint(blueprintArn=blueprint_arn)

schema = response.get('blueprint', {}).get('schema', '')
print("=== Full Blueprint Schema ===")
print(json.dumps(json.loads(schema), indent=2))
