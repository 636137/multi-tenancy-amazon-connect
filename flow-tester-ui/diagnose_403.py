#!/usr/bin/env python3
"""Detailed troubleshooting for CloudFront 403 errors."""

import boto3
import json
from pathlib import Path
from botocore.exceptions import ClientError

def diagnose_403_error():
    """Diagnose 403 error issues."""
    
    print("=" * 60)
    print("CloudFront 403 Error Diagnostics")
    print("=" * 60 + "\n")
    
    # Load config
    config_file = Path(__file__).parent / 'deployment_config.json'
    if not config_file.exists():
        print("✗ deployment_config.json not found")
        return
    
    with open(config_file) as f:
        config = json.load(f)
    
    bucket_name = config['bucket_name']
    dist_id = config['distribution_id']
    region = config['region']
    
    # Initialize clients
    s3 = boto3.client('s3', region_name=region)
    cf = boto3.client('cloudfront', region_name=region)
    
    print("Step 1: Checking Distribution Configuration")
    print("-" * 60)
    try:
        dist_response = cf.get_distribution(Id=dist_id)
        dist = dist_response['Distribution']
        status = dist['Status']
        enabled = dist['DistributionConfig']['Enabled']
        
        print(f"✓ Distribution: {dist_id}")
        print(f"  Status: {status}")
        print(f"  Enabled: {enabled}")
        
        if status != 'Deployed':
            print(f"\n⚠️  Distribution is not fully deployed yet")
            print(f"   Status: {status} (typically takes 5-15 minutes)")
            print(f"   This is a common cause of 403 errors during deployment")
        
        # Check origins
        origins = dist['DistributionConfig']['Origins']['Items']
        print(f"\n  Origins ({len(origins)}):")
        for origin in origins:
            print(f"    - ID: {origin['Id']}")
            print(f"      Domain: {origin['DomainName']}")
            if 'S3OriginConfig' in origin:
                oai = origin['S3OriginConfig'].get('OriginAccessIdentity', 'None')
                print(f"      S3 OAI: {oai if oai else '❌ NOT CONFIGURED'}")
            if 'OriginAccessIdentity' in origin:
                print(f"      OAI: {origin['OriginAccessIdentity']}")
        
        # Check cache behaviors
        print(f"\n  Cache Behaviors: {dist['DistributionConfig']['CacheBehaviors']['Quantity']}")
        
        # Check custom error responses
        error_responses = dist['DistributionConfig'].get('CustomErrorResponses', {})
        print(f"  Custom Error Responses: {error_responses.get('Quantity', 0)}")
        for resp in error_responses.get('Items', []):
            print(f"    - {resp['ErrorCode']} → {resp.get('ResponseCode', 'N/A')} ({resp.get('ResponsePagePath', 'N/A')})")
        
    except Exception as e:
        print(f"✗ Error checking distribution: {e}")
    
    print("\n\nStep 2: Checking S3 Bucket Access")
    print("-" * 60)
    try:
        # Check bucket exists
        s3.head_bucket(Bucket=bucket_name)
        print(f"✓ S3 bucket exists: {bucket_name}")
        
        # Check index.html exists
        response = s3.head_object(Bucket=bucket_name, Key='index.html')
        print(f"✓ index.html exists: {response['ContentLength']} bytes")
        print(f"  Content-Type: {response.get('ContentType', 'N/A')}")
        
        # Try to get the object
        obj = s3.get_object(Bucket=bucket_name, Key='index.html')
        print(f"✓ S3 object is readable")
        
    except ClientError as e:
        if e.response['Error']['Code'] == '404':
            print(f"✗ Object not found in S3")
        elif e.response['Error']['Code'] == 'NoSuchBucket':
            print(f"✗ Bucket does not exist")
        else:
            print(f"✗ S3 error: {e}")
    except Exception as e:
        print(f"✗ Error checking S3: {e}")
    
    print("\n\nStep 3: Checking Bucket Policy")
    print("-" * 60)
    try:
        policy_response = s3.get_bucket_policy(Bucket=bucket_name)
        policy = json.loads(policy_response['Policy'])
        
        print(f"✓ Bucket policy exists")
        print(f"  Statements: {len(policy['Statement'])}")
        
        for i, stmt in enumerate(policy['Statement']):
            print(f"\n  Statement {i+1}:")
            print(f"    Sid: {stmt.get('Sid', 'N/A')}")
            print(f"    Effect: {stmt.get('Effect', 'N/A')}")
            print(f"    Principal: {stmt.get('Principal', {})}")
            print(f"    Action: {stmt.get('Action', [])}")
            print(f"    Resource: {stmt.get('Resource', 'N/A')}")
        
    except s3.exceptions.NoSuchBucketPolicy:
        print(f"✗ No bucket policy found")
    except Exception as e:
        print(f"✗ Error checking policy: {e}")
    
    print("\n\nStep 4: Checking CloudFront Cache")
    print("-" * 60)
    try:
        invalidations = cf.list_invalidations(DistributionId=dist_id)
        print(f"✓ Invalidations: {invalidations['InvalidationList']['Quantity']}")
        
        for inv in invalidations['InvalidationList'].get('Items', []):
            print(f"  - {inv['Id']}: {inv['Status']} ({inv['CreateTime']})")
    except Exception as e:
        print(f"⚠ Could not check invalidations: {e}")
    
    print("\n\nTroubleshooting Recommendations")
    print("-" * 60)
    print("""
1. ✓ WAIT: Distribution is still deploying
   - Status shows: InProgress
   - This typically takes 5-15 minutes for global deployment
   - Retry in 5-10 minutes
   
2. Clear CloudFront cache (if deployed):
   aws cloudfront create-invalidation \\
     --distribution-id E2G8WC13R2E483 \\
     --paths "/*"
   
3. Clear browser cache:
   - Hard refresh: Cmd+Shift+R (Mac) or Ctrl+Shift+R (Windows)
   - Or use incognito/private mode
   
4. Test direct S3 access (if bucket is public):
   aws s3 cp s3://""" + bucket_name + """/index.html - | head -c 200
   
5. Check CloudFront logs (if enabled):
   aws s3 ls s3://YOUR_LOGS_BUCKET/cloudfront/ --recursive
   
6. Check AWS Console:
   - Go to CloudFront → Distributions
   - Select E2G8WC13R2E483
   - Check "Status" and "Last Modified"
   - Review "Origins" tab for OAI configuration
    """)
    
    print("\n" + "=" * 60)

if __name__ == '__main__':
    diagnose_403_error()
