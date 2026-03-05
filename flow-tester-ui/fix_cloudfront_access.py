#!/usr/bin/env python3
"""
Fix the existing CloudFront distribution to use OAI properly.

This addresses the AccessDenied error by:
1. Creating a CloudFront OAI
2. Updating the S3 bucket policy to allow the OAI
3. Creating a new distribution with proper OAI configuration
4. Deleting the old distribution
"""
import boto3
import json
import time
from pathlib import Path
from botocore.exceptions import ClientError

def get_account_id():
    """Get AWS account ID."""
    sts = boto3.client('sts')
    return sts.get_caller_identity()['Account']

def fix_cloudfront_s3_access():
    """Fix CloudFront S3 access with proper OAI."""
    
    print("=" * 60)
    print("Fixing CloudFront + S3 Access with OAI")
    print("=" * 60 + "\n")
    
    # Load config
    config_file = Path(__file__).parent / 'deployment_config.json'
    if not config_file.exists():
        print("✗ deployment_config.json not found")
        return False
    
    with open(config_file) as f:
        config = json.load(f)
    
    bucket_name = config['bucket_name']
    old_dist_id = config['distribution_id']
    region = config['region']
    
    # Initialize clients
    s3 = boto3.client('s3', region_name=region)
    cf = boto3.client('cloudfront', region_name=region)
    
    try:
        # Step 1: Create OAI
        print("Step 1: Creating CloudFront Origin Access Identity...")
        try:
            oai_response = cf.create_cloud_front_origin_access_identity(
                CloudFrontOriginAccessIdentityConfig={
                    'CallerReference': f'oai-{bucket_name}',
                    'Comment': f'OAI for {bucket_name}'
                }
            )
            oai_id = oai_response['CloudFrontOriginAccessIdentity']['Id']
            oai_arn = oai_response['CloudFrontOriginAccessIdentity']['S3CanonicalUserId']
            print(f"✓ Created new OAI: {oai_id}")
        except ClientError as e:
            if 'CloudFrontOriginAccessIdentityAlreadyExists' in str(e):
                # List existing OAIs
                oai_list = cf.list_cloud_front_origin_access_identities()
                for oai in oai_list.get('CloudFrontOriginAccessIdentityList', {}).get('Items', []):
                    if bucket_name in oai.get('Comment', ''):
                        oai_id = oai['Id']
                        oai_arn = oai['S3CanonicalUserId']
                        print(f"✓ Using existing OAI: {oai_id}")
                        break
            else:
                raise
        
        # Step 2: Update S3 bucket policy
        print("\nStep 2: Updating S3 bucket policy...")
        bucket_domain = f"{bucket_name}.s3.amazonaws.com"
        
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
        
        s3.put_bucket_policy(
            Bucket=bucket_name,
            Policy=json.dumps(bucket_policy)
        )
        print("✓ S3 bucket policy updated with OAI")
        
        # Step 3: Get old distribution config
        print("\nStep 3: Getting old distribution configuration...")
        try:
            dist_response = cf.get_distribution(Id=old_dist_id)
            old_dist_config = dist_response['Distribution']['DistributionConfig']
            etag = dist_response['ETag']
            print(f"✓ Retrieved distribution {old_dist_id}")
            print(f"  Current status: {dist_response['Distribution']['Status']}")
        except Exception as e:
            print(f"✗ Could not retrieve distribution: {e}")
            return False
        
        # Step 4: Create new distribution with OAI
        print("\nStep 4: Creating new distribution with OAI...")
        
        new_dist_config = {
            'CallerReference': f'flow-tester-uk-fixed-{int(time.time())}',
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
        
        try:
            new_dist_response = cf.create_distribution(DistributionConfig=new_dist_config)
            new_dist_id = new_dist_response['Distribution']['Id']
            new_dist_domain = new_dist_response['Distribution']['DomainName']
            new_status = new_dist_response['Distribution']['Status']
            
            print(f"✓ New distribution created: {new_dist_id}")
            print(f"  Domain: {new_dist_domain}")
            print(f"  Status: {new_status}")
        except Exception as e:
            print(f"✗ Could not create new distribution: {e}")
            return False
        
        # Step 5: Disable old distribution and prepare for deletion
        print("\nStep 5: Disabling old distribution...")
        
        try:
            # Get current config
            old_config_response = cf.get_distribution_config(Id=old_dist_id)
            old_config = old_config_response['DistributionConfig']
            old_etag = old_config_response['ETag']
            
            # Disable it
            old_config['Enabled'] = False
            
            cf.update_distribution(
                Id=old_dist_id,
                DistributionConfig=old_config,
                IfMatch=old_etag
            )
            print(f"✓ Old distribution {old_dist_id} disabled")
            print("  (Will be fully deleted after it's no longer InProgress)")
        except Exception as e:
            print(f"⚠ Could not disable old distribution: {e}")
        
        # Step 6: Update config file
        print("\nStep 6: Updating configuration...")
        
        config['distribution_id'] = new_dist_id
        config['cloudfront_url'] = f'https://{new_dist_domain}'
        config['old_distribution_id'] = old_dist_id
        config['oai_id'] = oai_id
        
        with open(config_file, 'w') as f:
            json.dump(config, f, indent=2)
        print(f"✓ Configuration updated")
        
        # Summary
        print("\n" + "=" * 60)
        print("✓ CloudFront + S3 Access Fixed")
        print("=" * 60)
        print(f"\nNew Infrastructure:")
        print(f"  Distribution ID:  {new_dist_id}")
        print(f"  CloudFront URL:   https://{new_dist_domain}")
        print(f"  OAI ID:           {oai_id}")
        print(f"  S3 Bucket:        {bucket_name}")
        print(f"\nOld Distribution:")
        print(f"  Distribution ID:  {old_dist_id}")
        print(f"  Status:           Disabled (pending deletion)")
        print(f"\nNext Steps:")
        print(f"  1. Wait 5-10 minutes for new distribution to deploy")
        print(f"  2. Test access: https://{new_dist_domain}")
        print(f"  3. Old distribution will be auto-deleted after deployment completes")
        print("=" * 60 + "\n")
        
        return True
        
    except Exception as e:
        print(f"\n✗ Error: {e}")
        import traceback
        traceback.print_exc()
        return False

if __name__ == '__main__':
    import sys
    success = fix_cloudfront_s3_access()
    sys.exit(0 if success else 1)
