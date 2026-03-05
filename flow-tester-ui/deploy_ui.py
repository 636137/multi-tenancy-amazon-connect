#!/usr/bin/env python3
"""
Deploy UK Amazon Connect UI to S3 + CloudFront

This script handles:
1. Creating S3 bucket for the React UI
2. Uploading index.html
3. Creating/updating CloudFront distribution
4. Outputting the CloudFront URL
"""
import boto3
import json
import sys
from pathlib import Path
from botocore.exceptions import ClientError

# Configuration
PROJECT_NAME = "flow-tester-uk"
REGION = "us-east-1"
UI_FILE = Path(__file__).parent / "index.html"

def setup_s3_bucket(s3_client, bucket_name):
    """Create S3 bucket with proper website configuration."""
    try:
        # Check if bucket exists
        s3_client.head_bucket(Bucket=bucket_name)
        print(f"✓ S3 bucket '{bucket_name}' already exists")
    except ClientError as e:
        if e.response['Error']['Code'] == '404':
            # Create new bucket
            print(f"Creating S3 bucket '{bucket_name}'...")
            s3_client.create_bucket(Bucket=bucket_name)
            print(f"✓ S3 bucket created")
            
            # Wait for bucket to exist
            waiter = s3_client.get_waiter('bucket_exists')
            waiter.wait(Bucket=bucket_name)
        else:
            raise
    
    # Configure as static website
    website_config = {
        'IndexDocument': {'Suffix': 'index.html'},
        'ErrorDocument': {'Key': 'index.html'}
    }
    s3_client.put_bucket_website(Bucket=bucket_name, WebsiteConfiguration=website_config)
    print("✓ S3 website configuration applied")
    
    # Block public access but ensure proper permissions for CloudFront
    s3_client.put_public_access_block(
        Bucket=bucket_name,
        PublicAccessBlockConfiguration={
            'BlockPublicAcls': True,
            'IgnorePublicAcls': True,
            'BlockPublicPolicy': True,
            'RestrictPublicBuckets': True
        }
    )
    print("✓ Public access blocked (CloudFront will access via OAI)")
    
    return bucket_name

def upload_ui(s3_client, bucket_name, ui_file):
    """Upload index.html to S3 with caching headers."""
    if not ui_file.exists():
        raise FileNotFoundError(f"UI file not found: {ui_file}")
    
    print(f"Uploading {ui_file.name} to S3...")
    
    with open(ui_file, 'r') as f:
        content = f.read()
    
    s3_client.put_object(
        Bucket=bucket_name,
        Key='index.html',
        Body=content,
        ContentType='text/html; charset=utf-8',
        CacheControl='max-age=3600'  # 1 hour cache
    )
    print(f"✓ {ui_file.name} uploaded successfully")

def setup_cloudfront_distribution(cf_client, s3_client, bucket_name, bucket_domain):
    """Create or update CloudFront distribution with OAI."""
    
    # Create OAI (Origin Access Identity) for secure S3 access
    try:
        oai_response = cf_client.create_cloud_front_origin_access_identity(
            CloudFrontOriginAccessIdentityConfig={
                'CallerReference': f'oai-{bucket_name}',
                'Comment': f'OAI for {bucket_name}'
            }
        )
        oai_id = oai_response['CloudFrontOriginAccessIdentity']['Id']
        oai_arn = oai_response['CloudFrontOriginAccessIdentity']['S3CanonicalUserId']
        print(f"✓ Created CloudFront OAI: {oai_id}")
    except ClientError as e:
        if 'CloudFrontOriginAccessIdentityAlreadyExists' in str(e):
            # List existing OAIs and find ours
            oai_list = cf_client.list_cloud_front_origin_access_identities()
            for oai in oai_list.get('CloudFrontOriginAccessIdentityList', {}).get('Items', []):
                if bucket_name in oai.get('Comment', ''):
                    oai_id = oai['Id']
                    oai_arn = oai['S3CanonicalUserId']
                    print(f"✓ Using existing OAI: {oai_id}")
                    break
        else:
            raise
    
    # Distribution config with OAI
    dist_config = {
        'CallerReference': f'{PROJECT_NAME}-{bucket_name}',
        'DefaultRootObject': 'index.html',
        'Origins': {
            'Quantity': 1,
            'Items': [
                {
                    'Id': 'S3Origin',
                    'DomainName': bucket_domain,
                    'S3OriginConfig': {
                        'OriginAccessIdentity': f'origin-access-identity/cloudfront/{oai_id}'
                    }
                }
            ]
        },
        'DefaultCacheBehavior': {
            'TargetOriginId': 'S3Origin',
            'ViewerProtocolPolicy': 'redirect-to-https',
            'AllowedMethods': {
                'Quantity': 2,
                'Items': ['GET', 'HEAD'],
                'CachedMethods': {
                    'Quantity': 2,
                    'Items': ['GET', 'HEAD']
                }
            },
            'ForwardedValues': {
                'QueryString': False,
                'Cookies': {'Forward': 'none'},
                'Headers': {
                    'Quantity': 0
                }
            },
            'TrustedSigners': {
                'Enabled': False,
                'Quantity': 0
            },
            'Compress': True,
            'MinTTL': 0,
            'DefaultTTL': 3600,
            'MaxTTL': 86400
        },
        'CacheBehaviors': {
            'Quantity': 0,
            'Items': []
        },
        'CustomErrorResponses': {
            'Quantity': 2,
            'Items': [
                {
                    'ErrorCode': 404,
                    'ResponseCode': '200',
                    'ResponsePagePath': '/index.html',
                    'ErrorCachingMinTTL': 0
                },
                {
                    'ErrorCode': 403,
                    'ResponseCode': '200',
                    'ResponsePagePath': '/index.html',
                    'ErrorCachingMinTTL': 0
                }
            ]
        },
        'Comment': 'UK Amazon Connect Flow Tester UI',
        'Enabled': True,
        'ViewerCertificate': {
            'CloudFrontDefaultCertificate': True
        },
        'Restrictions': {
            'GeoRestriction': {
                'RestrictionType': 'none',
                'Quantity': 0
            }
        }
    }
    
    # Set up bucket policy to allow OAI
    bucket_policy = {
        "Version": "2012-10-17",
        "Statement": [
            {
                "Sid": "AllowCloudFrontOAI",
                "Effect": "Allow",
                "Principal": {
                    "CanonicalUser": oai_arn
                },
                "Action": "s3:GetObject",
                "Resource": f"arn:aws:s3:::{bucket_name}/*"
            },
            {
                "Sid": "AllowListBucket",
                "Effect": "Allow",
                "Principal": {
                    "CanonicalUser": oai_arn
                },
                "Action": "s3:ListBucket",
                "Resource": f"arn:aws:s3:::{bucket_name}"
            }
        ]
    }
    
    try:
        s3_client.put_bucket_policy(
            Bucket=bucket_name,
            Policy=json.dumps(bucket_policy)
        )
        print("✓ S3 bucket policy configured for CloudFront OAI")
    except Exception as e:
        print(f"⚠ Could not set bucket policy: {e}")
    
    # Create or update distribution
    try:
        print("Creating CloudFront distribution...")
        response = cf_client.create_distribution(DistributionConfig=dist_config)
        dist_id = response['Distribution']['Id']
        dist_domain = response['Distribution']['DomainName']
        status = response['Distribution']['Status']
        
        print(f"✓ CloudFront distribution created")
        print(f"  Distribution ID: {dist_id}")
        print(f"  Domain: {dist_domain}")
        print(f"  Status: {status}")
        
        return dist_id, dist_domain
    except ClientError as e:
        if 'DistributionAlreadyExists' in str(e):
            print("⚠ Distribution already exists, retrieving details...")
            # List distributions to find ours
            response = cf_client.list_distributions()
            for dist in response.get('DistributionList', {}).get('Items', []):
                if dist['Comment'] == 'UK Amazon Connect Flow Tester UI':
                    dist_id = dist['Id']
                    dist_domain = dist['DomainName']
                    return dist_id, dist_domain
        raise

def get_account_id():
    """Get AWS account ID."""
    sts = boto3.client('sts')
    return sts.get_caller_identity()['Account']

def main():
    """Main deployment function."""
    print("=" * 60)
    print("UK Amazon Connect UI Deployment")
    print("=" * 60)
    
    # Get AWS account ID for bucket naming
    try:
        account_id = get_account_id()
        print(f"✓ AWS Account ID: {account_id}")
    except Exception as e:
        print(f"✗ Failed to get AWS account ID: {e}")
        print("  Make sure AWS credentials are configured")
        return False
    
    bucket_name = f"{PROJECT_NAME}-ui-{account_id}"
    bucket_domain = f"{bucket_name}.s3.amazonaws.com"
    
    try:
        # Initialize clients
        s3 = boto3.client('s3', region_name=REGION)
        cf = boto3.client('cloudfront', region_name=REGION)
        
        # Create S3 bucket
        setup_s3_bucket(s3, bucket_name)
        
        # Upload UI
        upload_ui(s3, bucket_name, UI_FILE)
        
        # Set up CloudFront
        dist_id, dist_domain = setup_cloudfront_distribution(cf, s3, bucket_name, bucket_domain)
        
        # Output results
        print("\n" + "=" * 60)
        print("Deployment Summary")
        print("=" * 60)
        print(f"S3 Bucket:       {bucket_name}")
        print(f"CloudFront URL:  https://{dist_domain}")
        print(f"Distribution ID: {dist_id}")
        print("\nNote: CloudFront may take 5-10 minutes to fully deploy")
        print("=" * 60 + "\n")
        
        # Save configuration
        config = {
            'bucket_name': bucket_name,
            'cloudfront_url': f'https://{dist_domain}',
            'distribution_id': dist_id,
            'region': REGION
        }
        
        config_file = Path(__file__).parent / 'deployment_config.json'
        with open(config_file, 'w') as f:
            json.dump(config, f, indent=2)
        print(f"✓ Configuration saved to {config_file}")
        
        return True
        
    except Exception as e:
        print(f"\n✗ Deployment failed: {e}")
        import traceback
        traceback.print_exc()
        return False

if __name__ == '__main__':
    success = main()
    sys.exit(0 if success else 1)
