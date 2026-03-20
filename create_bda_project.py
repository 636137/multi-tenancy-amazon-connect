#!/usr/bin/env python3
"""
Create Bedrock Data Automation Project for video analysis.
Uses the existing video-demo-analysis-v3 blueprint.
"""

import boto3
import json
import time

def main():
    client = boto3.client('bedrock-data-automation', region_name='us-east-1')
    
    blueprint_arn = 'arn:aws:bedrock:us-east-1:593804350786:blueprint/6230b3c13506'
    project_name = 'video-analysis-proj-v1'
    
    print(f"Creating project: {project_name}")
    print(f"Using blueprint: {blueprint_arn}")
    
    # Configuration attempts - from most to least comprehensive
    configs = [
        {
            "name": "Minimal document-only standard config",
            "config": {
                'document': {
                    'extraction': {
                        'granularity': {
                            'types': ['DOCUMENT']
                        },
                        'boundingBox': {
                            'state': 'DISABLED'
                        }
                    },
                    'generativeField': {
                        'state': 'DISABLED'
                    },
                    'outputFormat': {
                        'textFormat': {
                            'types': ['PLAIN_TEXT']
                        },
                        'additionalFileFormat': {
                            'state': 'DISABLED'
                        }
                    }
                }
            }
        },
        {
            "name": "Empty standard config",
            "config": {}
        }
    ]
    
    for attempt in configs:
        print(f"\nTrying: {attempt['name']}")
        try:
            response = client.create_data_automation_project(
                projectName=project_name,
                projectDescription='Video demo analysis project',
                projectStage='DEVELOPMENT',
                standardOutputConfiguration=attempt['config'],
                customOutputConfiguration={
                    'blueprints': [
                        {
                            'blueprintArn': blueprint_arn,
                            'blueprintStage': 'DEVELOPMENT'
                        }
                    ]
                }
            )
            
            print(f"✅ Project created!")
            print(f"   ARN: {response['projectArn']}")
            print(f"   Stage: {response['projectStage']}")
            print(f"   Status: {response['status']}")
            return response['projectArn']
            
        except client.exceptions.ValidationException as e:
            print(f"   ValidationException: {str(e)[:150]}")
        except client.exceptions.ConflictException:
            print(f"   Project already exists")
            # Find existing
            resp = client.list_data_automation_projects(projectStageFilter='DEVELOPMENT')
            for proj in resp.get('projects', []):
                if proj.get('projectName') == project_name:
                    print(f"   Existing ARN: {proj['projectArn']}")
                    return proj['projectArn']
        except Exception as e:
            print(f"   Error: {type(e).__name__}: {str(e)[:150]}")
    
    return None


if __name__ == "__main__":
    arn = main()
    if arn:
        print(f"\n📋 Project ARN: {arn}")
    else:
        print("\n❌ Failed to create project")
