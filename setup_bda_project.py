#!/usr/bin/env python3
"""
Create comprehensive video analysis blueprint and project.
Build up from the minimal working schema.
"""

import boto3
import json
import time

def create_blueprint(client):
    """Create a video analysis blueprint with detailed instructions."""
    
    # Schema with detailed instructions (keeping instruction text shorter)
    schema = {
        "$schema": "http://json-schema.org/draft-07/schema#",
        "description": "default",
        "class": "default", 
        "type": "object",
        "definitions": {
            "VideoDemo": {
                "type": "object",
                "properties": {
                    "Analysis": {
                        "type": "string",
                        "inferenceType": "inferred",
                        "instruction": "Full video analysis output"
                    }
                }
            }
        },
        "properties": {
            "CutMarkers": {
                "type": "string",
                "inferenceType": "inferred",
                "instruction": "Identify segments to CUT from the video. Include dead air, loading screens, failed attempts, and redundant content. Format: JSON array with start_time, end_time, reason for each cut.",
                "granularity": ["video"]
            },
            "ContentSegments": {
                "type": "string", 
                "inferenceType": "inferred",
                "instruction": "Classify content by type: agent_desktop, mobile_mirror, browser, dashboard, video_call, slides, terminal. Format: JSON array with start_time, end_time, type, description.",
                "granularity": ["video"]
            },
            "TalkTrack": {
                "type": "string",
                "inferenceType": "inferred", 
                "instruction": "Generate AI voice narration for the video. Professional tone, explain features, highlight benefits. Format: JSON array with start_time, duration_seconds, narration.",
                "granularity": ["video"]
            },
            "Summary": {
                "type": "string",
                "inferenceType": "inferred",
                "instruction": "Executive summary: product demonstrated, key features, workflow shown, recommended final duration after cuts.",
                "granularity": ["video"]
            }
        }
    }
    
    blueprint_name = 'video-demo-analysis-v3'
    
    print(f"Creating blueprint: {blueprint_name}")
    
    try:
        response = client.create_blueprint(
            blueprintName=blueprint_name,
            type='VIDEO',
            blueprintStage='DEVELOPMENT',
            schema=json.dumps(schema)
        )
        
        arn = response['blueprint']['blueprintArn']
        print(f"✅ Blueprint created: {arn}")
        return arn
        
    except client.exceptions.ConflictException:
        print(f"⚠️ Blueprint exists, finding ARN...")
        # Search in DEVELOPMENT stage first
        for stage in ['DEVELOPMENT', 'LIVE']:
            response = client.list_blueprints(blueprintStageFilter=stage)
            for bp in response.get('blueprints', []):
                if bp.get('blueprintName') == blueprint_name:
                    print(f"   Found in {stage}: {bp['blueprintArn']}")
                    return bp['blueprintArn']
        return None
        
    except Exception as e:
        print(f"❌ Error: {e}")
        return None


def create_project(client, blueprint_arn):
    """Create a Data Automation project using the blueprint."""
    
    project_name = 'video-demo-analysis-project'
    
    print(f"\nCreating project: {project_name}")
    
    try:
        response = client.create_data_automation_project(
            projectName=project_name,
            projectDescription='Automated video demo analysis for cuts, content metadata, and talk track',
            projectStage='DEVELOPMENT',
            standardOutputConfiguration={
                'video': {
                    'extraction': {
                        'category': {
                            'state': 'ENABLED'
                        },
                        'boundingBox': {
                            'state': 'DISABLED'
                        }
                    },
                    'generativeField': {
                        'state': 'ENABLED',
                        'types': ['VIDEO_SUMMARY', 'SCENE_SUMMARY', 'IAB']
                    }
                }
            },
            customOutputConfiguration={
                'blueprints': [
                    {
                        'blueprintArn': blueprint_arn,
                        'blueprintStage': 'DEVELOPMENT'
                    }
                ]
            }
        )
        
        project_arn = response['projectArn']
        print(f"✅ Project created: {project_arn}")
        return project_arn
        
    except client.exceptions.ConflictException:
        print(f"⚠️ Project exists, finding ARN...")
        response = client.list_data_automation_projects()
        for proj in response.get('projects', []):
            if proj.get('projectName') == project_name:
                print(f"   Found: {proj['projectArn']}")
                return proj['projectArn']
        return None
        
    except client.exceptions.ValidationException as e:
        print(f"❌ Validation Error: {e}")
        print("\nTrying simpler project configuration...")
        return create_simple_project(client, blueprint_arn)
        
    except Exception as e:
        print(f"❌ Error: {type(e).__name__}: {e}")
        return None


def create_simple_project(client, blueprint_arn):
    """Try creating a minimal project."""
    
    project_name = 'video-demo-project-simple'
    
    try:
        # Most minimal project configuration
        response = client.create_data_automation_project(
            projectName=project_name,
            projectStage='DEVELOPMENT',
            customOutputConfiguration={
                'blueprints': [
                    {
                        'blueprintArn': blueprint_arn,
                        'blueprintStage': 'DEVELOPMENT'
                    }
                ]
            }
        )
        
        project_arn = response['projectArn']
        print(f"✅ Simple project created: {project_arn}")
        return project_arn
        
    except Exception as e:
        print(f"❌ Simple project also failed: {e}")
        return None


def main():
    print("=== Amazon Bedrock Data Automation Setup ===\n")
    
    client = boto3.client('bedrock-data-automation', region_name='us-east-1')
    
    # Step 1: Create blueprint
    blueprint_arn = create_blueprint(client)
    if not blueprint_arn:
        print("\n❌ Failed to create/find blueprint")
        return
    
    # Step 2: Create project
    project_arn = create_project(client, blueprint_arn)
    if not project_arn:
        print("\n❌ Failed to create/find project")
        return
    
    print("\n" + "="*50)
    print("✅ Setup Complete!")
    print(f"   Blueprint ARN: {blueprint_arn}")
    print(f"   Project ARN: {project_arn}")
    print("\nNext step: Use invoke_data_automation_async to analyze videos")


if __name__ == "__main__":
    main()
