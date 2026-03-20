#!/usr/bin/env python3
"""
Amazon Bedrock Data Automation - Video Demo Analysis

This script analyzes video files using Amazon Bedrock Data Automation
with a custom blueprint that extracts:
- Cut markers (timestamps to remove)
- Content segments (classified by type)
- Talk track (AI narration script)
- Summary

Usage:
    python3 analyze_video_bda.py <video_s3_uri>
    python3 analyze_video_bda.py s3://bucket/path/to/video.mp4

The video must already be uploaded to S3.
"""

import boto3
import json
import time
import sys
from datetime import datetime

# Configuration
REGION = 'us-east-1'
PROJECT_ARN = 'arn:aws:bedrock:us-east-1:593804350786:data-automation-project/a08c7ca31e7e'
BLUEPRINT_ARN = 'arn:aws:bedrock:us-east-1:593804350786:blueprint/6230b3c13506'


def invoke_analysis(s3_uri: str, output_bucket: str = None) -> str:
    """
    Invoke Bedrock Data Automation to analyze a video.
    
    Args:
        s3_uri: S3 URI of the video file (s3://bucket/key)
        output_bucket: Optional S3 bucket for output (default: same as input)
    
    Returns:
        Invocation ARN for tracking progress
    """
    client = boto3.client('bedrock-data-automation-runtime', region_name=REGION)
    
    # Parse S3 URI
    if not s3_uri.startswith('s3://'):
        raise ValueError(f"Invalid S3 URI: {s3_uri}")
    
    parts = s3_uri[5:].split('/', 1)
    bucket = parts[0]
    key = parts[1] if len(parts) > 1 else ''
    
    if not output_bucket:
        output_bucket = bucket
    
    output_prefix = f"bda-output/{datetime.now().strftime('%Y%m%d-%H%M%S')}"
    
    print(f"Invoking analysis...")
    print(f"  Input: {s3_uri}")
    print(f"  Output: s3://{output_bucket}/{output_prefix}/")
    print(f"  Project: {PROJECT_ARN}")
    
    # Data automation profile ARN - use the AWS-managed default profile
    # Format: arn:aws:bedrock:REGION:aws:data-automation-profile/us.data-automation.default
    data_automation_profile_arn = f"arn:aws:bedrock:{REGION}:aws:data-automation-profile/us.data-automation.default"
    print(f"  Profile: {data_automation_profile_arn}")
    
    try:
        response = client.invoke_data_automation_async(
            inputConfiguration={
                's3Uri': s3_uri
            },
            outputConfiguration={
                's3Uri': f"s3://{output_bucket}/{output_prefix}/"
            },
            dataAutomationConfiguration={
                'dataAutomationProjectArn': PROJECT_ARN,
                'stage': 'DEVELOPMENT'
            },
            dataAutomationProfileArn=data_automation_profile_arn
            # Note: Don't include blueprints here - they're already in the project
        )
        
        invocation_arn = response['invocationArn']
        print(f"\n✅ Analysis started!")
        print(f"   Invocation ARN: {invocation_arn}")
        
        return invocation_arn
        
    except client.exceptions.ValidationException as e:
        print(f"\n❌ Validation Error: {e}")
        raise
    except Exception as e:
        print(f"\n❌ Error: {type(e).__name__}: {e}")
        raise


def check_status(invocation_arn: str) -> dict:
    """Check the status of an analysis invocation."""
    client = boto3.client('bedrock-data-automation-runtime', region_name=REGION)
    
    try:
        response = client.get_data_automation_status(
            invocationArn=invocation_arn
        )
        return response
    except Exception as e:
        print(f"Error checking status: {e}")
        return None


def wait_for_completion(invocation_arn: str, timeout_minutes: int = 30) -> dict:
    """Wait for analysis to complete."""
    print(f"\nWaiting for analysis to complete (timeout: {timeout_minutes} min)...")
    
    start_time = time.time()
    timeout_seconds = timeout_minutes * 60
    check_interval = 30  # Check every 30 seconds
    
    while True:
        elapsed = time.time() - start_time
        if elapsed > timeout_seconds:
            print(f"\n⏰ Timeout after {timeout_minutes} minutes")
            return None
        
        status = check_status(invocation_arn)
        if status:
            current_status = status.get('status', 'UNKNOWN')
            print(f"  [{int(elapsed)}s] Status: {current_status}")
            
            if current_status == 'SUCCESS':
                print(f"\n✅ Analysis completed!")
                return status
            elif current_status in ['FAILED', 'CANCELLED']:
                print(f"\n❌ Analysis {current_status}")
                if 'errorMessage' in status:
                    print(f"   Error: {status['errorMessage']}")
                return status
        
        time.sleep(check_interval)


def download_results(output_uri: str, local_path: str = './bda_output') -> None:
    """Download analysis results from S3."""
    import os
    
    s3 = boto3.client('s3', region_name=REGION)
    
    # Parse URI
    parts = output_uri[5:].split('/', 1)
    bucket = parts[0]
    prefix = parts[1] if len(parts) > 1 else ''
    
    os.makedirs(local_path, exist_ok=True)
    
    print(f"\nDownloading results from {output_uri}...")
    
    # List and download objects
    paginator = s3.get_paginator('list_objects_v2')
    for page in paginator.paginate(Bucket=bucket, Prefix=prefix):
        for obj in page.get('Contents', []):
            key = obj['Key']
            local_file = os.path.join(local_path, key.replace(prefix, '').lstrip('/'))
            os.makedirs(os.path.dirname(local_file), exist_ok=True)
            
            print(f"  Downloading: {key}")
            s3.download_file(bucket, key, local_file)
    
    print(f"\n✅ Results saved to: {local_path}")


def parse_results(local_path: str = './bda_output') -> dict:
    """Parse and display the analysis results."""
    import os
    
    results = {}
    
    # Look for output JSON files
    for root, dirs, files in os.walk(local_path):
        for file in files:
            if file.endswith('.json'):
                filepath = os.path.join(root, file)
                print(f"\nReading: {filepath}")
                with open(filepath, 'r') as f:
                    data = json.load(f)
                    results[file] = data
                    
                    # Pretty print the results
                    print(json.dumps(data, indent=2)[:2000])
                    if len(json.dumps(data)) > 2000:
                        print("...")
    
    return results


def main():
    """Main entry point."""
    if len(sys.argv) < 2:
        # Use the video we already uploaded
        s3_uri = 's3://video-analysis-593804350786-us-east-1/videos/DHS - GSA Demo Recording-20260319_182431-Meeting Recording.mp4'
        print(f"Using default video: {s3_uri}")
    else:
        s3_uri = sys.argv[1]
    
    print("=" * 60)
    print("Amazon Bedrock Data Automation - Video Demo Analysis")
    print("=" * 60)
    
    # Step 1: Invoke analysis
    try:
        invocation_arn = invoke_analysis(s3_uri)
    except Exception as e:
        print(f"\nFailed to start analysis: {e}")
        return 1
    
    # Step 2: Wait for completion
    final_status = wait_for_completion(invocation_arn, timeout_minutes=60)
    
    if not final_status or final_status.get('status') != 'SUCCESS':
        print("\nAnalysis did not complete successfully")
        return 1
    
    # Step 3: Download and parse results
    output_uri = final_status.get('outputConfiguration', {}).get('s3Uri')
    if output_uri:
        download_results(output_uri)
        results = parse_results()
        
        # Generate summary
        print("\n" + "=" * 60)
        print("ANALYSIS SUMMARY")
        print("=" * 60)
        for filename, data in results.items():
            print(f"\n📄 {filename}:")
            if isinstance(data, dict):
                for key in ['CutMarkers', 'ContentSegments', 'TalkTrack', 'Summary']:
                    if key in data:
                        print(f"   - {key}: Found")
    
    return 0


if __name__ == "__main__":
    sys.exit(main())
