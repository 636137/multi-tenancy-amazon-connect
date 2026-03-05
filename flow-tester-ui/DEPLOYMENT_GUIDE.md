# UK Amazon Connect Flow Tester UI - Deployment Guide

## Quick Start

Your UK Amazon Connect Flow Tester UI is now live on AWS!

### 🌐 Access Your UI

**URL:** `https://d1uil7daug1z6x.cloudfront.net`

> ⏳ **Note:** CloudFront distribution is still deploying. It typically takes 5-10 minutes. If you get a connection error, wait a few minutes and try again.

## Deployment Details

### Infrastructure

| Component | Details |
|-----------|---------|
| **S3 Bucket** | `flow-tester-uk-ui-593804350786` |
| **CloudFront Distribution** | `ETZNRX0V5QNBP` |
| **CloudFront Domain** | `d1uil7daug1z6x.cloudfront.net` |
| **Region** | `us-east-1` |
| **Status** | ✓ Deployed |

### What You Get

✓ **Global CDN**: Your UI is served from 450+ CloudFront edge locations worldwide  
✓ **HTTPS**: Automatic SSL/TLS encryption  
✓ **Fast Updates**: Upload new UI versions in seconds  
✓ **Error Handling**: 404s automatically serve index.html for SPA routing  
✓ **Caching**: Optimized cache headers for performance  

## Managing Your Deployment

### Update the UI

```bash
cd flow-tester-ui
python deploy_ui.py
```

This automatically:
- Uploads the latest `index.html` to S3
- Invalidates CloudFront cache
- New version is live within seconds

### Monitor Deployment Status

```bash
cd flow-tester-ui
python verify_deployment.py
```

Output will show:
- S3 bucket status
- CloudFront distribution status
- Cache configuration
- When it's fully deployed and ready

### Check CloudFront Status via AWS CLI

```bash
# See full distribution status
aws cloudfront get-distribution --id ETZNRX0V5QNBP

# Just check if deployed
aws cloudfront get-distribution --id ETZNRX0V5QNBP | jq '.Distribution.Status'
```

### Invalidate Cache (Force Update)

```bash
aws cloudfront create-invalidation \
  --distribution-id ETZNRX0V5QNBP \
  --paths "/*"
```

## Configuration Files

### `deployment_config.json`
Contains your deployment information for reference:
- Bucket name
- CloudFront URL
- Distribution ID
- Region

### `deploy_ui.py`
Python script to deploy/update the UI. Can be run anytime to push new changes.

### `verify_deployment.py`
Status check script. Run to verify everything is working correctly.

## Security

- ✓ S3 bucket is **private** - no direct public access
- ✓ All requests go through **CloudFront only**
- ✓ **HTTPS enforced** - no unencrypted traffic
- ✓ **Public access blocked** at bucket level
- ✓ Bucket policy restricts to CloudFront only

## Customization Options

### Add a Custom Domain

1. Get/verify a domain in Route 53 or via your registrar
2. Create an ACM certificate for your domain (free in AWS)
3. Update CloudFront distribution:
   ```bash
   aws cloudfront update-distribution \
     --id ETZNRX0V5QNBP \
     --distribution-config <config-with-custom-domain> \
     --etag <current-etag>
   ```

### Adjust Cache Settings

Edit the cache behavior in `deploy_ui.py`:
- `MinTTL`: Minimum cache time (default: 0)
- `DefaultTTL`: Default cache time (default: 3600 seconds = 1 hour)
- `MaxTTL`: Maximum cache time (default: 86400 seconds = 24 hours)

### Enable Access Logging

Add to CloudFront config to log all requests to S3:
```json
"Logging": {
  "Enabled": true,
  "IncludeCookies": false,
  "Bucket": "my-logs-bucket.s3.amazonaws.com",
  "Prefix": "cloudfront/"
}
```

## Troubleshooting

### "Cannot resolve host" error
- CloudFront is still deploying (wait 5-10 minutes)
- Try refreshing in a few minutes

### 503 Service Unavailable
- S3 bucket not fully propagated yet
- CloudFront edge location still syncing
- Wait 5-10 minutes and refresh

### 403 Forbidden
- Bucket policy may have issues
- Run `python deploy_ui.py` again
- Check AWS IAM permissions

### Cache Not Updating
- Create an invalidation to clear cache
- Or use the AWS Console: CloudFront → Select distribution → Invalidations

### Need to see real-time requests
```bash
# View CloudFront access logs (if enabled)
aws s3 ls s3://my-logs-bucket/cloudfront/ --recursive
```

## Cost Optimization

Current setup costs roughly:
- **Data Transfer**: ~$0.085 per GB (first 10TB/month)
- **HTTP Requests**: $0.0075 per 10,000 requests
- **S3 Storage**: ~$0.023 per GB/month for index.html (negligible)

**Example monthly cost for 1M visits:**
- 1M requests: ~$0.75
- ~500 MB data transfer: ~$0.04
- **Total: ~$0.79/month**

## Advanced: Rollback

To revert to a previous version:

1. **Get previous version from S3:**
   ```bash
   aws s3api list-object-versions \
     --bucket flow-tester-uk-ui-593804350786 \
     --prefix index.html
   ```

2. **Restore previous version:**
   ```bash
   aws s3api get-object \
     --bucket flow-tester-uk-ui-593804350786 \
     --key index.html \
     --version-id <VERSION_ID> | jq '.Body'
   ```

## Cleanup

To completely remove everything:

```bash
# 1. Delete CloudFront distribution (takes 15-20 mins)
ETAG=$(aws cloudfront get-distribution-config --id ETZNRX0V5QNBP | jq -r '.ETag')
aws cloudfront delete-distribution \
  --id ETZNRX0V5QNBP \
  --etag $ETAG

# 2. Wait for distribution to be deleted...

# 3. Delete S3 bucket and contents
aws s3 rm s3://flow-tester-uk-ui-593804350786 --recursive
aws s3 rb s3://flow-tester-uk-ui-593804350786
```

## Support & Updates

- **Deployment scripts:** `deploy_ui.py`, `verify_deployment.py`
- **Config reference:** `deployment_config.json`
- **Full deployment log:** `DEPLOYMENT_COMPLETE.md`

To updated deployment files, simply run `python deploy_ui.py` again - it automatically handles everything.

---

**Deployed:** March 5, 2026  
**CloudFront URL:** https://d1uil7daug1z6x.cloudfront.net  
**Distribution ID:** ETZNRX0V5QNBP
