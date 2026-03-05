#!/usr/bin/env python3
"""Check status of both CloudFront distributions and use the working one."""

import boto3
import json
from pathlib import Path

region = "us-east-1"
cf = boto3.client('cloudfront', region_name=region)

# Check both distributions
dist_ids = ["ETZNRX0V5QNBP", "E2G8WC13R2E483"]

print("Distribution Status Check")
print("=" * 60)

for dist_id in dist_ids:
    try:
        response = cf.get_distribution(Id=dist_id)
        dist = response['Distribution']
        status = dist['Status']
        enabled = dist['DistributionConfig']['Enabled']
        domain = dist['DomainName']
        
        print(f"\n✓ {dist_id}")
        print(f"  Domain: {domain}")
        print(f"  Status: {status}")
        print(f"  Enabled: {enabled}")
        
        if dist_id == "E2G8WC13R2E483" and enabled and status == "Deployed":
            print(f"  ✅ This is the working distribution with OAI!")
    except Exception as e:
        print(f"\n✗ {dist_id}: {e}")

# Update config to use the newest one with OAI
print("\n" + "=" * 60)
print("Updating configuration to use working distribution...")

config_file = Path(__file__).parent / 'deployment_config.json'
config = {
    "bucket_name": "flow-tester-uk-ui-593804350786",
    "cloudfront_url": "https://d2lajk9oj5x4qs.cloudfront.net",
    "distribution_id": "E2G8WC13R2E483",
    "region": region,
    "oai_id": "E2LOHX3IMUZ9MY",
    "old_distribution_id": "ETZNRX0V5QNBP"
}

with open(config_file, 'w') as f:
    json.dump(config, f, indent=2)

print(f"✓ Configuration updated")
print(f"  New CloudFront URL: {config['cloudfront_url']}")
print(f"  Distribution ID: {config['distribution_id']}")

# Now invalidate the cache
print("\nInvalidating cache...")
try:
    response = cf.create_invalidation(
        DistributionId=config['distribution_id'],
        InvalidationBatch={
            'Paths': {
                'Quantity': 1,
                'Items': ['/*']
            },
            'CallerReference': str(__import__('time').time())
        }
    )
    print(f"✓ Cache invalidation created: {response['Invalidation']['Id']}")
except Exception as e:
    print(f"⚠ Could not invalidate cache: {e}")

print("\n" + "=" * 60)
print("Next Steps:")
print("1. Wait 2-3 minutes for cache invalidation to complete")
print("2. Visit your new CloudFront URL:")
print(f"   {config['cloudfront_url']}")
print("3. Hard refresh browser: Cmd+Shift+R (Mac) or Ctrl+Shift+R (Windows)")
print("=" * 60)
