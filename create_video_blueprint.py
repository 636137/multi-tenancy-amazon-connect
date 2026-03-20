#!/usr/bin/env python3
"""
Create Amazon Bedrock Data Automation Blueprint for Video Demo Analysis.

This blueprint extracts:
1. Cut markers (timestamps to remove)
2. Content metadata (screen type classification)
3. Talk track (AI voice narration)
"""

import boto3
import json
import sys

def create_video_analysis_blueprint():
    """Create the video demo analysis blueprint."""
    
    client = boto3.client('bedrock-data-automation', region_name='us-east-1')
    
    # Define the comprehensive video analysis schema
    schema = {
        "$schema": "http://json-schema.org/draft-07/schema#",
        "description": "Video Demo Analysis Blueprint for extracting cuts, content metadata, and talk track",
        "class": "video_demo_analysis",
        "type": "object",
        "definitions": {
            "CutMarker": {
                "type": "object",
                "description": "A segment to cut from the video",
                "properties": {
                    "start_time": {"type": "string", "description": "Start timestamp in HH:MM:SS format"},
                    "end_time": {"type": "string", "description": "End timestamp in HH:MM:SS format"},
                    "reason": {"type": "string", "description": "Why this segment should be cut"}
                }
            },
            "ContentSegment": {
                "type": "object",
                "description": "A segment with metadata about displayed content",
                "properties": {
                    "start_time": {"type": "string", "description": "Start timestamp"},
                    "end_time": {"type": "string", "description": "End timestamp"},
                    "content_type": {"type": "string", "description": "Type of content: agent_desktop, mobile_mirror, browser, supervisor_dashboard, video_call, slides, terminal, other"},
                    "description": {"type": "string", "description": "What is being shown"}
                }
            },
            "TalkTrackSegment": {
                "type": "object",
                "description": "A segment of narration for AI voice overlay",
                "properties": {
                    "start_time": {"type": "string", "description": "When to start speaking"},
                    "duration_seconds": {"type": "number", "description": "Approximate duration"},
                    "narration": {"type": "string", "description": "The text to narrate"}
                }
            }
        },
        "properties": {
            "video_summary": {
                "type": "string",
                "inferenceType": "inferred",
                "instruction": "Provide a comprehensive executive summary of the video demo. Include the main product/feature being demonstrated, key workflows shown, and overall narrative flow. Keep it under 300 words.",
                "granularity": ["video"]
            },
            "total_duration": {
                "type": "string",
                "inferenceType": "inferred",
                "instruction": "Extract the total video duration in HH:MM:SS format",
                "granularity": ["video"]
            },
            "cuts": {
                "type": "array",
                "inferenceType": "inferred",
                "instruction": """Identify segments that should be CUT (removed) from the video. Look for:
                
1. Dead air or silence with no meaningful activity (>5 seconds)
2. Loading screens, spinners, or wait states
3. Repeated failed attempts at the same action
4. Off-topic tangents or digressions
5. Technical difficulties (frozen screens, error messages being debugged)
6. Excessive scrolling without narration
7. Browser/app switching that adds no value
8. Sections where the presenter appears lost or confused
9. Redundant demonstrations of the same feature
10. Transitions that take too long

For each cut, provide:
- start_time: When the cut should begin (HH:MM:SS)
- end_time: When the cut should end (HH:MM:SS)
- reason: Brief explanation of why this should be cut

Be conservative - only recommend cuts that won't disrupt the flow or lose important content.""",
                "granularity": ["video"],
                "items": {"$ref": "#/definitions/CutMarker"}
            },
            "content_segments": {
                "type": "array",
                "inferenceType": "inferred",
                "instruction": """Classify each distinct content segment by what's being displayed on screen. Categories:

- agent_desktop: Contact center agent workspace/CRM
- mobile_mirror: Phone screen mirror/emulator
- browser: Web browser showing websites/apps
- supervisor_dashboard: Analytics/monitoring dashboards
- video_call: Live video calling interface
- slides: Presentation slides
- terminal: Command line/code editor
- diagram: Architecture/flow diagrams
- other: Anything not fitting above categories

For each segment provide:
- start_time and end_time in HH:MM:SS
- content_type from the list above
- description of what specific content/feature is shown""",
                "granularity": ["video"],
                "items": {"$ref": "#/definitions/ContentSegment"}
            },
            "talk_track": {
                "type": "array",
                "inferenceType": "inferred",
                "instruction": """Generate a professional talk track for AI voice narration overlay. The talk track should:

1. Explain what's happening on screen at each moment
2. Highlight key features and benefits being demonstrated
3. Use natural, conversational language suitable for text-to-speech
4. Time segments to match the visual content closely
5. Include appropriate pauses (represented as separate segments)
6. Avoid technical jargon unless necessary for the demo
7. Build excitement and emphasize value propositions
8. Guide the viewer's attention to important UI elements

Generate the talk track assuming the original audio will be removed/muted.
Each segment should be 10-30 seconds of speaking time.
Use present tense and active voice.

Format:
- start_time: When this narration should begin
- duration_seconds: How long to speak (account for TTS timing)
- narration: The exact text to narrate""",
                "granularity": ["video"],
                "items": {"$ref": "#/definitions/TalkTrackSegment"}
            },
            "recommended_duration": {
                "type": "string",
                "inferenceType": "inferred",
                "instruction": "After applying all recommended cuts, calculate the estimated final video duration in HH:MM:SS format",
                "granularity": ["video"]
            },
            "key_moments": {
                "type": "array",
                "inferenceType": "inferred",
                "instruction": """Identify 3-5 key highlight moments that are most impressive or important to keep. These are moments that should definitely NOT be cut. Include timestamp and brief description of why it's important.""",
                "granularity": ["video"],
                "items": {
                    "type": "object",
                    "properties": {
                        "timestamp": {"type": "string"},
                        "description": {"type": "string"},
                        "importance": {"type": "string"}
                    }
                }
            }
        }
    }
    
    blueprint_name = 'video-demo-analysis-v2'
    
    print(f"Creating blueprint: {blueprint_name}")
    print(f"Schema:\n{json.dumps(schema, indent=2)[:1000]}...")
    
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
        print(f"   Created: {blueprint['creationTime']}")
        
        return blueprint['blueprintArn']
        
    except client.exceptions.ConflictException:
        print(f"\n⚠️  Blueprint '{blueprint_name}' already exists. Fetching existing...")
        # List blueprints to find the ARN
        response = client.list_blueprints()
        for bp in response.get('blueprints', []):
            if bp.get('blueprintName') == blueprint_name:
                print(f"   Found existing ARN: {bp['blueprintArn']}")
                return bp['blueprintArn']
        return None
        
    except client.exceptions.ValidationException as e:
        print(f"\n❌ Validation Error: {e}")
        print("\nTrying alternate schema format...")
        return try_alternate_schema(client, blueprint_name)
        
    except Exception as e:
        print(f"\n❌ Error: {type(e).__name__}: {e}")
        return None


def try_alternate_schema(client, blueprint_name):
    """Try a simpler schema format matching the existing working blueprint."""
    
    # Use format matching the existing DemoAnalysis1 blueprint
    schema = {
        "$schema": "http://json-schema.org/draft-07/schema#",
        "description": "default",
        "class": "default",
        "type": "object",
        "definitions": {
            "Video Demo Analysis": {
                "type": "object",
                "properties": {
                    "cuts": {
                        "type": "string",
                        "inferenceType": "inferred",
                        "instruction": "Identify all segments to cut from the video. For each cut provide start_time (HH:MM:SS), end_time (HH:MM:SS), and reason. Format as JSON array."
                    },
                    "content_segments": {
                        "type": "string",
                        "inferenceType": "inferred",
                        "instruction": "Classify each content segment by type (agent_desktop, mobile_mirror, browser, supervisor_dashboard, video_call, slides, terminal, other). Provide start_time, end_time, content_type, and description for each. Format as JSON array."
                    },
                    "talk_track": {
                        "type": "string",
                        "inferenceType": "inferred",
                        "instruction": "Generate AI voice narration for the video. Provide start_time, duration_seconds, and narration text for each segment. Format as JSON array."
                    }
                }
            }
        },
        "properties": {
            "video_summary": {
                "type": "string",
                "inferenceType": "inferred",
                "instruction": "Summarize this video demo in 2-3 paragraphs. Include: main product demonstrated, key features shown, workflow demonstrated, and overall quality assessment.",
                "granularity": ["video"]
            },
            "analysis_json": {
                "type": "string",
                "inferenceType": "inferred",
                "instruction": """Analyze the video and output a JSON object with three arrays:

1. "cuts": Array of segments to remove, each with:
   - "start_time": HH:MM:SS format
   - "end_time": HH:MM:SS format  
   - "reason": Why to cut this segment

2. "content_segments": Array of content classifications, each with:
   - "start_time": HH:MM:SS
   - "end_time": HH:MM:SS
   - "content_type": One of [agent_desktop, mobile_mirror, browser, supervisor_dashboard, video_call, slides, terminal, other]
   - "description": What's shown

3. "talk_track": Array of narration segments, each with:
   - "start_time": HH:MM:SS
   - "duration_seconds": Number
   - "narration": Text to speak

Return only valid JSON.""",
                "granularity": ["video"]
            }
        }
    }
    
    blueprint_name_alt = f"{blueprint_name}-alt"
    print(f"\nTrying alternate schema for: {blueprint_name_alt}")
    
    try:
        response = client.create_blueprint(
            blueprintName=blueprint_name_alt,
            type='VIDEO',
            blueprintStage='DEVELOPMENT',
            schema=json.dumps(schema)
        )
        
        blueprint = response['blueprint']
        print(f"\n✅ Blueprint created with alternate schema!")
        print(f"   ARN: {blueprint['blueprintArn']}")
        return blueprint['blueprintArn']
        
    except Exception as e:
        print(f"\n❌ Alternate schema also failed: {e}")
        return None


if __name__ == "__main__":
    arn = create_video_analysis_blueprint()
    if arn:
        print(f"\n📋 Blueprint ARN for use in projects: {arn}")
    else:
        print("\n❌ Failed to create blueprint")
        sys.exit(1)
