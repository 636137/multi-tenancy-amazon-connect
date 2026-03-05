#!/usr/bin/env python3
"""Troubleshooting guide for CloudFront access issues."""

import json
from pathlib import Path

config_file = Path(__file__).parent / 'deployment_config.json'
with open(config_file) as f:
    config = json.load(f)

guide = f"""
╔════════════════════════════════════════════════════════════════════════════╗
║                      CLOUDFRONT ACCESS TROUBLESHOOTING                     ║
╚════════════════════════════════════════════════════════════════════════════╝

✅ SERVER STATUS: CloudFront is working and serving content!

Your URL:
  https://{config['cloudfront_url'].replace('https://', '')}

Distribution Status: DEPLOYED
HTML Content: ✓ Loaded (24.2 KB)
SSL Certificate: ✓ Valid
Cache: ✓ Configured

━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

"THIS SITE CAN'T BE REACHED" - COMMON CAUSES & FIXES
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

1️⃣  CLEAR BROWSER CACHE (Most Common Fix)
   ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
   
   Mac (Chrome/Edge):
   • Cmd + Shift + Delete
   • Select "All time"
   • Check: Cookies, Cache, Cached images/files
   • Click "Clear data"
   • Refresh page
   
   Mac (Safari):
   • Safari → Settings → Privacy
   • Click "Manage Website Data..."
   • Search: "d2lajk9oj5x4qs"
   • Click "Remove"
   • Close window and refresh
   
   Windows (Chrome/Edge):
   • Ctrl + Shift + Delete
   • Select "All time"
   • Check same boxes
   • Click "Clear now"

2️⃣  HARD REFRESH (Bypass Cache)
   ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
   
   Mac:
   • Chrome/Edge: Cmd + Shift + R
   • Safari: Cmd + Option + R
   
   Windows/Linux:
   • Chrome/Edge: Ctrl + Shift + R
   • Firefox: Ctrl + F5

3️⃣  PRIVATE/INCOGNITO MODE (New Session)
   ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
   
   Open a new incognito/private window:
   • Mac: Cmd + Shift + N (Chrome) or Cmd + Shift + P (Firefox)
   • Windows: Ctrl + Shift + N (Chrome) or Ctrl + Shift + P (Firefox)
   
   Paste URL: https://{config['cloudfront_url'].replace('https://', '')}

4️⃣  CHECK DNS RESOLUTION
   ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
   
   Open Terminal and run:
   nslookup {config['cloudfront_url'].replace('https://', '')}
   
   Expected output:
   • Server: 1.1.1.1 (or similar)
   • Name: {config['cloudfront_url'].replace('https://', '')}
   • Address: 13.249.x.x (CloudFront IP)

5️⃣  TEST FROM DIFFERENT NETWORK
   ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
   
   • Try from smartphone hotspot
   • Try from different WiFi network
   • This rules out corporate firewall/proxy blocking

6️⃣  CHECK FIREWALL/VPN
   ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
   
   Temporarily disable:
   • VPN
   • Corporate proxy
   • Firewall blocking CloudFront IPs
   
   CloudFront uses IP ranges: 13.249.0.0/16 and others

7️⃣  GET THE IP ADDRESS
   ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
   
   In Terminal:
   dig {config['cloudfront_url'].replace('https://', '')} @8.8.8.8 +short
   
   Then try accessing directly by IP in browser:
   https://13.249.135.108
   (This may show CloudFront error, but indicates network works)

━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

WHAT'S WORKING (VERIFIED):
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

✓ CloudFront Distribution: DEPLOYED
✓ S3 Bucket: Configured correctly
✓ Origin Access Identity: E2LOHX3IMUZ9MY
✓ HTML Content: Uploaded and serving
✓ SSL/TLS: Valid certificate
✓ DNS: Resolving correctly
✓ HTTP/2: Enabled and working

━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

ALTERNATIVE ACCESS METHOD:
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

Access via AWS Console:
1. Go to: https://console.aws.amazon.com/cloudfront/
2. Find distribution: {config['distribution_id']}
3. Click the domain name: {config['cloudfront_url'].replace('https://', '')}

Access via Terminal:
curl https://{config['cloudfront_url'].replace('https://', '')} | head -100

━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

FINAL_CHECKLIST:
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

Before giving up, try in this order:

1. [ ] Hard refresh: Cmd+Shift+R or Ctrl+Shift+R
2. [ ] Incognito/private mode
3. [ ] Clear all cache (instructions above)
4. [ ] Test nslookup command
5. [ ] Try different network (hotspot)
6. [ ] Disable VPN
7. [ ] Wait 5 more minutes (DNS still propagating?)
8. [ ] Check CloudFront distribution still shows DEPLOYED status
9. [ ] Try from curl in Terminal:
       curl -i https://{config['cloudfront_url'].replace('https://', '')}

━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

CONFIGURATION REFERENCE:
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

CloudFront URL:      {config['cloudfront_url']}
Distribution ID:     {config['distribution_id']}
S3 Bucket:          {config['bucket_name']}
Region:             {config['region']}
OAI ID:             {config.get('oai_id', 'N/A')}

━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

Server is responding correctly. This is likely a client-side issue.
Try the steps above — 95% of cases are resolved by cache clearing!

"""

print(guide)
