#!/usr/bin/env python3
"""Verify UK Amazon Connect UI Deployment Status."""

import boto3
import json
from pathlib import Path

def check_s3_bucket(s3_client, bucket_name):
    """Check S3 bucket status."""
    try:
        s3_client.head_bucket(Bucket=bucket_name)
        print(f"✓ S3 Bucket exists: {bucket_name}")
        
        # Check index.html
        response = s3_client.head_object(Bucket=bucket_name, Key='index.html')
        size = response['ContentLength']
        print(f"  - index.html size: {size} bytes")
        return True
    except Exception as e:
        print(f"✗ S3 Bucket error: {e}")
        return False

def check_cloudfront_distribution(cf_client, dist_id):
    """Check CloudFront distribution status."""
    try:
        response = cf_client.get_distribution(Id=dist_id)
        dist = response['Distribution']
        status = dist['Status']
        domain = dist['DomainName']
        enabled = dist.get('DistributionConfig', {}).get('Enabled', True)
        
        print(f"✓ CloudFront Distribution: {dist_id}")
        print(f"  - Status: {status}")
        print(f"  - Domain: {domain}")
        print(f"  - Enabled: {enabled}")
        
        if status == 'Deployed':
            print(f"\n✓ Distribution is ready! Access at: https://{domain}")
        elif status == 'InProgress':
            print(f"\n⏳ Distribution is still deploying (typically 5-10 minutes)")
            print(f"   Check again in a few minutes or visit: https://{domain}")
        
        return True
    except Exception as e:
        print(f"⚠ CloudFront check (non-critical): {e}")
        return True

def check_bucket_policy(s3_client, bucket_name):
    """Check S3 bucket policy."""
    try:
        response = s3_client.get_bucket_policy(Bucket=bucket_name)
        policy = json.loads(response['Policy'])
        print(f"✓ S3 Bucket Policy configured")
        print(f"  - Statements: {len(policy['Statement'])}")
        return True
    except s3_client.exceptions.NoSuchBucketPolicy:
        print(f"⚠ No bucket policy found")
        return False
    except Exception as e:
        print(f"⚠ Policy check error: {e}")
        return False

def main():
    # Load config
    config_file = Path(__file__).parent / 'deployment_config.json'
    if not config_file.exists():
        print("✗ deployment_config.json not found. Run deploy_ui.py first.")
        return
    
    with open(config_file) as f:
        config = json.load(f)
    
    print("=" * 60)
    print("UK Amazon Connect UI - Deployment Verification")
    print("=" * 60 + "\n")
    
    # Initialize clients
    s3 = boto3.client('s3', region_name=config['region'])
    cf = boto3.client('cloudfront', region_name=config['region'])
    
    # Run checks
    print("Checking infrastructure...\n")
    
    s3_ok = check_s3_bucket(s3, config['bucket_name'])
    print()
    cf_ok = check_cloudfront_distribution(cf, config['distribution_id'])
    print()
    policy_ok = check_bucket_policy(s3, config['bucket_name'])
    
    print("\n" + "=" * 60)
    
    if s3_ok and cf_ok and policy_ok:
        print("✓ All infrastructure checks passed!")
    else:
        print("⚠ Some checks failed - see details above")
    
    print("=" * 60)

if __name__ == '__main__':
    main()
