#!/usr/bin/env python3
"""Invalidate CloudFront cache to force new content delivery."""

import boto3
import json
from pathlib import Path

config_file = Path(__file__).parent / 'deployment_config.json'
with open(config_file) as f:
    config = json.load(f)

dist_id = config['distribution_id']
print(f"Invalidating CloudFront cache for distribution: {dist_id}")

cf = boto3.client('cloudfront', region_name=config['region'])

try:
    response = cf.create_invalidation(
        DistributionId=dist_id,
        InvalidationBatch={
            'Paths': {
                'Quantity': 1,
                'Items': ['/*']
            },
            'CallerReference': str(__import__('time').time())
        }
    )
    
    inv_id = response['Invalidation']['Id']
    status = response['Invalidation']['Status']
    
    print(f"✓ Invalidation created: {inv_id}")
    print(f"  Status: {status}")
    print(f"\nThe cache will be cleared within a few minutes.")
    print(f"Access your URL to see the updated content:")
    print(f"  {config['cloudfront_url']}")
    
except Exception as e:
    print(f"✗ Error: {e}")
