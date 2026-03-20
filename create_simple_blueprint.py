#!/usr/bin/env python3
"""
Create video analysis blueprint using exact format from working blueprint.
"""

import boto3
import json

client = boto3.client('bedrock-data-automation', region_name='us-east-1')

# Schema that matches the existing working DemoAnalysis1 blueprint format exactly
schema = {
    "$schema": "http://json-schema.org/draft-07/schema#",
    "description": "default",
    "class": "default",
    "type": "object",
    "definitions": {
        "Video Analysis": {
            "type": "object",
            "properties": {
                "AnalysisResult": {
                    "type": "string",
                    "inferenceType": "inferred",
                    "instruction": "Analyze the video recording to identify cut points, content segments, and generate talk track"
                }
            }
        }
    },
    "properties": {
        "VideoSummary": {
            "type": "string",
            "inferenceType": "inferred",
            "instruction": """Analyze this video demo recording comprehensively. Your analysis must include:

1. CUT MARKERS: Identify segments to remove from the video:
   - Dead air or silence (>5 seconds)
   - Loading screens and wait states
   - Failed attempts or technical difficulties
   - Redundant demonstrations

   Format each cut as: [START_TIME - END_TIME]: Reason

2. CONTENT SEGMENTS: Classify each distinct section:
   - agent_desktop: Contact center agent workspace
   - mobile_mirror: Phone screen demonstrations
   - browser: Web browser content
   - supervisor_dashboard: Analytics dashboards
   - video_call: Live video interfaces
   - slides: Presentation content
   - terminal: Command line/code
   - diagram: Architecture diagrams

   Format each segment as: [START_TIME - END_TIME]: Type - Description

3. TALK TRACK: Generate professional narration for AI voice overlay:
   - Explain what's happening on screen
   - Highlight key features and benefits
   - Use natural, conversational language
   - Build excitement about the product

   Format as: [START_TIME] (duration): "Narration text"

Provide timestamps in HH:MM:SS format throughout.""",
            "granularity": [
                "video"
            ]
        }
    }
}

blueprint_name = 'video-demo-analysis-simple'

print(f"Creating blueprint: {blueprint_name}")
print(f"Schema (first 500 chars):\n{json.dumps(schema, indent=2)[:500]}...")

try:
    response = client.create_blueprint(
        blueprintName=blueprint_name,
        type='VIDEO',
        blueprintStage='DEVELOPMENT',
        schema=json.dumps(schema)
    )
    
    blueprint = response['blueprint']
    print(f"\n✅ Blueprint created successfully!")
    print(f"   Name: {blueprint['blueprintName']}")
    print(f"   ARN: {blueprint['blueprintArn']}")
    print(f"   Type: {blueprint['type']}")
    print(f"   Stage: {blueprint['blueprintStage']}")
    
except client.exceptions.ConflictException:
    print(f"\n⚠️ Blueprint '{blueprint_name}' already exists")
    response = client.list_blueprints()
    for bp in response.get('blueprints', []):
        if bp.get('blueprintName') == blueprint_name:
            print(f"   Existing ARN: {bp['blueprintArn']}")
            
except Exception as e:
    print(f"\n❌ Error: {type(e).__name__}: {e}")
    
    # Try even simpler - just a single property like the working one
    print("\n\nTrying minimal schema matching DemoAnalysis1...")
    
    minimal_schema = {
        "$schema": "http://json-schema.org/draft-07/schema#",
        "description": "default", 
        "class": "default",
        "type": "object",
        "definitions": {
            "Analysis": {
                "type": "object",
                "properties": {
                    "Result": {
                        "type": "string",
                        "inferenceType": "inferred",
                        "instruction": "Analyze video content"
                    }
                }
            }
        },
        "properties": {
            "Summary": {
                "type": "string",
                "inferenceType": "inferred",
                "instruction": "Provide video analysis including cut markers, content classification, and AI narration talk track",
                "granularity": ["video"]
            }
        }
    }
    
    try:
        response = client.create_blueprint(
            blueprintName='video-analysis-minimal',
            type='VIDEO',
            blueprintStage='DEVELOPMENT', 
            schema=json.dumps(minimal_schema)
        )
        print(f"✅ Minimal blueprint created: {response['blueprint']['blueprintArn']}")
    except Exception as e2:
        print(f"❌ Minimal also failed: {e2}")
