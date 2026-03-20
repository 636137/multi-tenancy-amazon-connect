# ElevenLabs API Setup Skill

Bootstrap ElevenLabs authentication, Secrets Manager integration, KMS policies, API validation, and AI Agent credential management with self-healing error recovery.

## Quick Start

| Task | Command |
|------|---------|
| Create/update Secrets Manager secret | `python elevenlabs_setup.py --action create-secret --api-key YOUR_KEY` |
| Apply KMS + Secrets policies | `python elevenlabs_setup.py --action apply-policies --secret-name elevenlabs-api` |
| Setup AI Agent credentials | `python elevenlabs_setup.py --action setup-agent-creds --agent-tier advanced` |
| List available voices + models | `python elevenlabs_setup.py --action list-voices --filter language=english` |
| Validate API access end-to-end | `python elevenlabs_setup.py --action validate --secret-name elevenlabs-api` |
| Check agent quota and limits | `python elevenlabs_setup.py --action check-agent-quota` |

---

## Workflow: Complete API Setup

### 1. Generate / Obtain API Key

```bash
# Option A: Get API key from https://elevenlabs.io/app/settings/api-keys
# Format: API_KEY=xxxx_xxxx_xxxx_xxxx (typically 32+ characters)

# Option B: Use existing API key from .env or clipboard
export ELEVENLABS_API_KEY="your_key_here"
```

### 2. Create Secrets Manager Secret

```python
import boto3
import json
from botocore.exceptions import ClientError

def create_elevenlabs_secret(api_key: str, secret_name: str = "elevenlabs-api"):
    """Create or update ElevenLabs API secret in Secrets Manager."""
    client = boto3.client("secretsmanager")
    
    secret_value = {
        "api_key": api_key,
        "api_base": "https://api.elevenlabs.io/v1",
        "created_at": datetime.now().isoformat()
    }
    
    try:
        # Try to update existing secret
        response = client.update_secret(
            SecretId=secret_name,
            SecretString=json.dumps(secret_value)
        )
        print(f"✅ Secret updated: {response['ARN']}")
    except ClientError as e:
        if e.response["Error"]["Code"] == "ResourceNotFoundException":
            # Create new secret
            response = client.create_secret(
                Name=secret_name,
                SecretString=json.dumps(secret_value),
                Description="ElevenLabs API credentials for Amazon Connect TTS"
            )
            print(f"✅ Secret created: {response['ARN']}")
        else:
            raise

# Usage
create_elevenlabs_secret(api_key="your_key")
```

### 3. Apply KMS + Secrets Manager Policies

```json
{
  "Version": "2012-10-17",
  "Statement": [
    {
      "Sid": "SecretsManagerAccess",
      "Effect": "Allow",
      "Principal": {
        "AWS": "arn:aws:iam::ACCOUNT:role/lambda-execution-role"
      },
      "Action": [
        "secretsmanager:GetSecretValue",
        "secretsmanager:DescribeSecret"
      ],
      "Resource": "arn:aws:secretsmanager:REGION:ACCOUNT:secret:elevenlabs-api-*"
    },
    {
      "Sid": "KMSDecrypt",
      "Effect": "Allow",
      "Principal": {
        "AWS": "arn:aws:iam::ACCOUNT:role/lambda-execution-role"
      },
      "Action": [
        "kms:Decrypt",
        "kms:DescribeKey"
      ],
      "Resource": "arn:aws:kms:REGION:ACCOUNT:key/KEY_ID"
    }
  ]
}
```

### 4. Retrieve Secret in Lambda

```python
import boto3
import json
import os

def get_elevenlabs_key() -> str:
    """Retrieve ElevenLabs API key from Secrets Manager."""
    secret_name = os.environ.get("ELEVENLABS_SECRET_NAME", "elevenlabs-api")
    region = os.environ.get("AWS_REGION", "us-east-1")
    
    client = boto3.client("secretsmanager", region_name=region)
    
    try:
        response = client.get_secret_value(SecretId=secret_name)
        secret = json.loads(response["SecretString"])
        return secret["api_key"]
    except client.exceptions.ResourceNotFoundException:
        raise ValueError(f"Secret '{secret_name}' not found in Secrets Manager")
    except Exception as e:
        raise RuntimeError(f"Failed to retrieve secret: {str(e)}")

# Usage in Lambda handler
def lambda_handler(event, context):
    api_key = get_elevenlabs_key()
    # Use api_key for ElevenLabs API calls
    return {"statusCode": 200, "body": "API key loaded"}
```

### 5. List Available Voices & Models

```python
import requests
import json

def list_elevenlabs_voices(api_key: str, filter_language: str = None) -> dict:
    """Retrieve available voices and filter by language if specified."""
    headers = {"xi-api-key": api_key}
    url = "https://api.elevenlabs.io/v1/voices"
    
    response = requests.get(url, headers=headers)
    response.raise_for_status()
    voices = response.json()["voices"]
    
    if filter_language:
        # Filter by language (requires language metadata in voice response)
        voices = [
            v for v in voices 
            if filter_language.lower() in v.get("labels", {}).get("language", "").lower()
        ]
    
    return {
        "total_voices": len(voices),
        "voices": [
            {
                "voice_id": v["voice_id"],
                "name": v["name"],
                "language": v.get("labels", {}).get("language", "unknown"),
                "accent": v.get("labels", {}).get("accent", "neutral")
            }
            for v in voices
        ]
    }

# Usage
voices = list_elevenlabs_voices(api_key, filter_language="english")
print(f"Available English voices: {len(voices['voices'])}")
```

### 6. Validate API Access End-to-End

```python
def validate_elevenlabs_api(api_key: str) -> dict:
    """Test ElevenLabs API connectivity and credentials."""
    headers = {"xi-api-key": api_key}
    url = "https://api.elevenlabs.io/v1/user"
    
    try:
        response = requests.get(url, headers=headers)
        if response.status_code == 200:
            user = response.json()
            return {
                "status": "✅ Valid",
                "subscription_tier": user.get("subscription", {}).get("tier"),
                "character_limit": user.get("subscription", {}).get("character_limit"),
                "used_characters": user.get("subscription", {}).get("used_characters")
            }
        elif response.status_code == 401:
            return {"status": "❌ Invalid API key"}
        else:
            return {"status": f"❌ HTTP {response.status_code}: {response.text}"}
    except requests.RequestException as e:
        return {"status": f"❌ Connection error: {str(e)}"}

# Usage
validation = validate_elevenlabs_api(api_key)
print(validation)
```

---

## Workflow: AI Agent Credential Setup (For Agent Deployments)

### 1. Enable AI Agents in ElevenLabs Account

```bash
# Check current account tier and agent enablement
curl -X GET "https://api.elevenlabs.io/v1/account/subscription" \
  -H "xi-api-key: YOUR_API_KEY"

# Response includes:
# - tier: "pro" | "scale" | "enterprise"
# - agents_enabled: true | false
# - concurrent_agents_limit: number
# - monthly_agent_calls_limit: number
```

### 2. Create Dedicated Agent Service Account

```python
import boto3
import json
from datetime import datetime

def setup_agent_service_account(api_key: str, secret_name: str = "elevenlabs-agent-api"):
    """Create separate Secrets Manager entry for AI Agent operations."""
    
    client = boto3.client("secretsmanager")
    
    # Store agent-specific credentials
    agent_secret = {
        "api_key": api_key,
        "service_type": "agent",
        "agent_tier": "advanced",       # or "basic", "expert"
        "api_base": "https://api.elevenlabs.io/v1",
        "agent_features": {
            "knowledge_base": True,
            "custom_intent": True,
            "escalation_rules": True,
            "sentiment_tracking": True,
            "conversation_history": True
        },
        "rate_limits": {
            "requests_per_minute": 100,
            "concurrent_agents": 5,
            "max_turns_per_conversation": 20
        },
        "created_at": datetime.now().isoformat(),
        "purpose": "AI Agent operations for Amazon Connect"
    }
    
    try:
        response = client.update_secret(
            SecretId=secret_name,
            SecretString=json.dumps(agent_secret)
        )
        print(f"✅ Agent credentials updated: {secret_name}")
    except client.exceptions.ResourceNotFoundException:
        response = client.create_secret(
            Name=secret_name,
            SecretString=json.dumps(agent_secret),
            Description="ElevenLabs AI Agent API credentials for Amazon Connect"
        )
        print(f"✅ Agent secret created: {secret_name}")
    
    return response

# Usage
setup_agent_service_account(api_key="your_key")
```

### 3. Apply Agent-Specific IAM Policies

```json
{
  "Version": "2012-10-17",
  "Statement": [
    {
      "Sid": "ElevenLabsAgentAPICalls",
      "Effect": "Allow",
      "Principal": {
        "AWS": "arn:aws:iam::ACCOUNT:role/lambda-agent-execution-role"
      },
      "Action": [
        "secretsmanager:GetSecretValue"
      ],
      "Resource": [
        "arn:aws:secretsmanager:REGION:ACCOUNT:secret:elevenlabs-agent-api-*",
        "arn:aws:secretsmanager:REGION:ACCOUNT:secret:elevenlabs-api-*"
      ]
    },
    {
      "Sid": "KMSDecryptForAgents",
      "Effect": "Allow",
      "Principal": {
        "AWS": "arn:aws:iam::ACCOUNT:role/lambda-agent-execution-role"
      },
      "Action": [
        "kms:Decrypt",
        "kms:DescribeKey",
        "kms:GenerateDataKey"
      ],
      "Resource": "arn:aws:kms:REGION:ACCOUNT:key/KEY_ID",
      "Condition": {
        "StringEquals": {
          "kms:ViaService": "secretsmanager.REGION.amazonaws.com"
        }
      }
    }
  ]
}
```

### 4. Validate Agent Tier and Limits

```python
def check_agent_capabilities(api_key: str) -> dict:
    """Verify account supports AI Agents and check limits."""
    
    import requests
    
    # Check subscription
    headers = {"xi-api-key": api_key}
    response = requests.get(
        "https://api.elevenlabs.io/v1/account/subscription",
        headers=headers
    )
    response.raise_for_status()
    
    subscription = response.json()
    
    print("✅ Account Capabilities:")
    print(f"  Tier: {subscription.get('tier', 'unknown')}")
    print(f"  Agents Enabled: {subscription.get('agents_enabled', False)}")
    
    if subscription.get('agents_enabled'):
        print(f"  Concurrent Agents: {subscription.get('concurrent_agents_limit', 'unlimited')}")
        print(f"  Monthly Agent Calls: {subscription.get('agent_calls_limit', 'unlimited')}")
        print(f"  Knowledge Base: {'Included' if 'knowledge_base' in subscription else 'Not included'}")
    else:
        print("  ❌ AI Agents NOT enabled. Upgrade account at https://elevenlabs.io/app/billing/overview")
    
    return subscription

# Usage
capabilities = check_agent_capabilities(api_key="your_key")
if not capabilities.get('agents_enabled'):
    print("\nTo enable AI Agents:")
    print("1. Visit https://elevenlabs.io/app/settings/agents")
    print("2. Upgrade to Pro or Scale tier")
    print("3. Enable 'AI Agents' feature")
```

---

## Environment Variables (Lambda) for Agents

```bash
# TTS credentials (existing)
ELEVENLABS_SECRET_NAME=elevenlabs-api
ELEVENLABS_API_KEY=xxxx_xxxx_xxxx_xxxx

# AI Agent credentials (new)
ELEVENLABS_AGENT_SECRET_NAME=elevenlabs-agent-api
ELEVENLABS_AGENT_TIER=advanced
ELEVENLABS_AGENT_MODEL=elevenlabs-agent-advanced

# Agent limits
ELEVENLABS_MAX_AGENT_TURNS=20
ELEVENLABS_AGENT_TIMEOUT_SECONDS=300
ELEVENLABS_ESCALATION_ENABLED=true
```

---



```bash
# .env or Lambda environment
ELEVENLABS_SECRET_NAME=elevenlabs-api
ELEVENLABS_API_BASE=https://api.elevenlabs.io/v1
AWS_REGION=us-east-1
```

---

## Troubleshooting

| Issue | Solution |
|-------|----------|
| "Secret not found" | Create secret via `create_elevenlabs_secret()` or AWS console |
| "Invalid API key" | Verify key format at https://elevenlabs.io/app/settings/api-keys |
| "KMS decrypt denied" | Check Lambda IAM role has `kms:Decrypt` permission |
| "API rate limited" | Check subscription tier at elevenlabs.io/app/billing/overview |

---

## Cost Estimation

- **Free tier**: 10,000 characters/month
- **Pro tier**: $5/month for 100k characters + $0.30/10k additional
- **Scale tier**: Custom pricing, contact sales

---

## Security Checklist

✅ API key stored in Secrets Manager (not in code or .env)  
✅ KMS encryption enabled for secret  
✅ Lambda IAM role restricted to minimal permissions  
✅ Rotation policy configured (optional but recommended)  
✅ Audit trail enabled via CloudTrail  
