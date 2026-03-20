#!/usr/bin/env python3
"""Explore Bedrock Data Automation Blueprints and test schema formats."""

import boto3
import json

def main():
    # Initialize client
    client = boto3.client('bedrock-data-automation', region_name='us-east-1')

    # List existing blueprints
    print("=== Listing Existing Blueprints ===")
    try:
        response = client.list_blueprints()
        blueprints = response.get('blueprints', [])
        print(f"Found {len(blueprints)} blueprints:")
        for bp in blueprints:
            print(f"  - {bp.get('blueprintName')} (ARN: {bp.get('blueprintArn')}, Type: {bp.get('type')})")
            # Try to get blueprint details
            try:
                detail = client.get_blueprint(blueprintArn=bp.get('blueprintArn'))
                schema = detail.get('blueprint', {}).get('schema', 'N/A')
                print(f"    Schema: {schema[:500]}..." if len(schema) > 500 else f"    Schema: {schema}")
            except Exception as e:
                print(f"    Could not get details: {e}")
    except Exception as e:
        print(f"Error listing blueprints: {e}")

    # List data automation projects
    print("\n=== Listing Data Automation Projects ===")
    try:
        response = client.list_data_automation_projects()
        projects = response.get('projects', [])
        print(f"Found {len(projects)} projects:")
        for proj in projects:
            print(f"  - {proj.get('projectName')} (ARN: {proj.get('projectArn')}, Stage: {proj.get('projectStage')})")
    except Exception as e:
        print(f"Error listing projects: {e}")

    # Test different schema formats
    print("\n=== Testing Schema Formats ===")
    
    # Test 1: Simple JSON schema
    test_schemas = [
        {
            "name": "Minimal Object Schema",
            "schema": json.dumps({
                "type": "object",
                "properties": {
                    "summary": {"type": "string", "description": "Video summary"}
                }
            })
        },
        {
            "name": "JSON Schema with $schema",
            "schema": json.dumps({
                "$schema": "http://json-schema.org/draft-07/schema#",
                "type": "object",
                "properties": {
                    "summary": {"type": "string"}
                }
            })
        },
        {
            "name": "Plain text schema description",
            "schema": "Extract video summary and scene descriptions"
        },
        {
            "name": "Array of fields format",
            "schema": json.dumps([
                {"name": "summary", "type": "string", "description": "Video summary"},
                {"name": "scenes", "type": "array", "description": "List of scenes"}
            ])
        }
    ]
    
    for i, test in enumerate(test_schemas):
        print(f"\nTest {i+1}: {test['name']}")
        print(f"  Schema: {test['schema'][:100]}...")
        try:
            response = client.create_blueprint(
                blueprintName=f'test-schema-format-{i+1}',
                type='VIDEO',
                blueprintStage='DEVELOPMENT',
                schema=test['schema']
            )
            print(f"  SUCCESS! Blueprint ARN: {response['blueprint']['blueprintArn']}")
            # Clean up
            client.delete_blueprint(blueprintArn=response['blueprint']['blueprintArn'])
            print(f"  (Cleaned up test blueprint)")
            break  # Stop on first success
        except client.exceptions.ValidationException as e:
            print(f"  ValidationException: {str(e)[:200]}")
        except client.exceptions.ConflictException as e:
            print(f"  ConflictException: Blueprint already exists")
        except Exception as e:
            print(f"  Error: {type(e).__name__}: {str(e)[:200]}")


if __name__ == "__main__":
    main()
