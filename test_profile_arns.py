#!/usr/bin/env python3
"""Test different data automation profile ARN formats."""

import boto3

REGION = 'us-east-1'
ACCOUNT = '593804350786'
PROJECT_ARN = 'arn:aws:bedrock:us-east-1:593804350786:data-automation-project/a08c7ca31e7e'

client = boto3.client('bedrock-data-automation-runtime', region_name=REGION)

# Try various profile ARN formats
profile_formats = [
    f"arn:aws:bedrock:{REGION}:aws:data-automation-profile/default",
    f"arn:aws:bedrock:{REGION}:aws:data-automation-profile/us-data-automation-default",
    f"arn:aws:bedrock:{REGION}:{ACCOUNT}:data-automation-profile/default",
    f"arn:aws:bedrock:{REGION}:{ACCOUNT}:data-automation-profile/us-data-automation",
    f"arn:aws:bedrock:us-east-1:aws:application-inference-profile/bedrock-data-automation",
    f"arn:aws:bedrock:{REGION}:aws:data-automation-profile/bedrock-data-automation",
]

s3_uri = 's3://video-analysis-593804350786-us-east-1/videos/DHS - GSA Demo Recording-20260319_182431-Meeting Recording.mp4'
output_uri = 's3://video-analysis-593804350786-us-east-1/bda-output/test/'

for profile_arn in profile_formats:
    print(f"\nTrying profile: {profile_arn}")
    try:
        response = client.invoke_data_automation_async(
            inputConfiguration={'s3Uri': s3_uri},
            outputConfiguration={'s3Uri': output_uri},
            dataAutomationConfiguration={
                'dataAutomationProjectArn': PROJECT_ARN,
                'stage': 'DEVELOPMENT'
            },
            dataAutomationProfileArn=profile_arn
        )
        print(f"✅ SUCCESS! Invocation ARN: {response['invocationArn']}")
        break
    except Exception as e:
        error_msg = str(e)[:150]
        print(f"❌ {error_msg}")
