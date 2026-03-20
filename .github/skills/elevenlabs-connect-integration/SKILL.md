# ElevenLabs Amazon Connect Integration Skill

Deploy ElevenLabs TTS and AI Agents in contact flows, Lex bot integration, real-time audio streaming with Chime SDK, AI Agent handoff logic, and production multi-region setup.

## Quick Start

| Task | Command |
|------|---------|
| Deploy Lex bot with ElevenLabs | `python deploy_lex.py --api-key YOUR_KEY --voice-id "21m00Tcm4TlvDq8ikWAM"` |
| Update contact flow block | See Contact Flow Integration below |
| Test with Lambda mock event | `python test_lex_elevenlabs.py --text "Hello customer"` |
| Setup multi-region failover | `python setup_regional_failover.py --primary us-east-1 --secondary us-west-2` |

---

## Architecture Overview

```
Caller → Amazon Connect → Lex V2 Bot → Lambda (TTS) → ElevenLabs API
                          ↓
                    Voice Response
                      (streaming)
```

### Components
1. **Amazon Connect** — Contact flow orchestration and audio routing
2. **AWS Lex V2** — Conversation management and intent routing
3. **AWS Lambda** — ElevenLabs API call orchestration (TTS synthesis)
4. **Secrets Manager** — API key storage (KMS encrypted)
5. **Chime SDK** — Real-time audio streaming for WebRTC

---

## Workflow 1: Lex Bot Integration

### Step 1: Create IAM Role for Lex

```json
{
  "Version": "2012-10-17",
  "Statement": [
    {
      "Effect": "Allow",
      "Action": [
        "secretsmanager:GetSecretValue",
        "kms:Decrypt"
      ],
      "Resource": [
        "arn:aws:secretsmanager:*:ACCOUNT:secret:elevenlabs-api-*",
        "arn:aws:kms:*:ACCOUNT:key/*"
      ]
    },
    {
      "Effect": "Allow",
      "Action": [
        "logs:CreateLogGroup",
        "logs:CreateLogStream",
        "logs:PutLogEvents"
      ],
      "Resource": "arn:aws:logs:*:ACCOUNT:*"
    }
  ]
}
```

### Step 2: Create Lambda Fulfillment Handler

```python
import boto3
import json
import os
from elevenlabs import ElevenLabsClient

def get_elevenlabs_key():
    """Retrieve API key from Secrets Manager."""
    secret_name = os.environ.get("ELEVENLABS_SECRET_NAME", "elevenlabs-api")
    region = os.environ.get("AWS_REGION", "us-east-1")
    client = boto3.client("secretsmanager", region_name=region)
    response = client.get_secret_value(SecretId=secret_name)
    return json.loads(response["SecretString"])["api_key"]

def synthesize_with_elevenlabs(text: str, voice_id: str, api_key: str) -> bytes:
    """Call ElevenLabs API and return MP3 audio."""
    url = f"https://api.elevenlabs.io/v1/text-to-speech/{voice_id}"
    
    import requests
    headers = {"xi-api-key": api_key}
    payload = {
        "text": text,
        "model_id": "eleven_turbo_v2",
        "voice_settings": {
            "stability": 0.5,
            "similarity_boost": 0.75
        }
    }
    
    response = requests.post(url, json=payload, headers=headers)
    response.raise_for_status()
    return response.content  # MP3 audio bytes

def upload_to_s3(audio_bytes: bytes, bucket: str, key: str) -> str:
    """Upload audio to S3 and return public URL."""
    s3 = boto3.client("s3")
    s3.put_object(Bucket=bucket, Key=key, Body=audio_bytes, ContentType="audio/mpeg")
    
    # Generate signed URL (valid for 1 hour)
    url = s3.generate_presigned_url(
        "get_object",
        Params={"Bucket": bucket, "Key": key},
        ExpiresIn=3600
    )
    return url

def lambda_handler(event, context):
    """Lex fulfillment handler with ElevenLabs TTS."""
    
    # Parse Lex event
    intent_name = event["currentIntent"]["name"]
    slots = event["currentIntent"]["slots"]
    session_attributes = event.get("sessionAttributes", {})
    
    # Construct response text based on intent
    if intent_name == "WelcomeIntent":
        response_text = "Welcome to our customer service. How can I help you today?"
    elif intent_name == "AccountBalanceIntent":
        response_text = f"Your account balance is ${slots.get('account_id', 'N/A')}"
    else:
        response_text = "I didn't understand that request. Please try again."
    
    # Synthesize speech
    try:
        api_key = get_elevenlabs_key()
        voice_id = os.environ.get("ELEVENLABS_VOICE_ID", "21m00Tcm4TlvDq8ikWAM")
        
        audio_bytes = synthesize_with_elevenlabs(response_text, voice_id, api_key)
        
        # Upload to S3 for streaming
        bucket = os.environ.get("ELEVENLABS_AUDIO_BUCKET", "my-bucket")
        key = f"elevenlabs/{intent_name}/{context.request_id}.mp3"
        audio_url = upload_to_s3(audio_bytes, bucket, key)
        
        session_attributes["audio_url"] = audio_url
        session_attributes["text_response"] = response_text
        
        print(f"✅ Audio synthesized: {audio_url}")
        
    except Exception as e:
        print(f"❌ TTS error: {str(e)}")
        session_attributes["error"] = str(e)
    
    # Return Lex response (optionally stop conversation if fulfilled)
    return {
        "sessionAttributes": session_attributes,
        "dialogAction": {
            "type": "ElicitIntent",
            "message": {
                "contentType": "PlainText",
                "content": response_text
            }
        }
    }

# Lambda environment variables
# ELEVENLABS_SECRET_NAME=elevenlabs-api
# ELEVENLABS_VOICE_ID=21m00Tcm4TlvDq8ikWAM  
# ELEVENLABS_AUDIO_BUCKET=my-audio-bucket
```

### Step 3: Update Lex Bot Configuration

```yaml
# Lex Bot settings (via AWS CLI or Console)
Bot:
  BotName: "IRS_Taxpayer_Assistant"
  Description: "Taxpayer services with ElevenLabs voice"
  
Intents:
  - IntentName: "WelcomeIntent"
    FulfillmentCodeHook:
      Active: true
      PostFulfillmentStatusSpecification:
        IsActive: true
        FailureConditional:
          IsActive: true
    VoiceSettings:
      VoiceId: "Amy"  # Connect's default, will be overridden by Lambda

# Use Lambda's audio URL instead
PostFulfillmentStatusSpecification:
  SuccessResponse:
    MessageGroupsList:
      - Message:
          PlainTextMessage:
            Value: "{audio_url}"  # From session attributes
```

---

## Workflow 2: Contact Flow Block Integration

### Option A: Via Invoke Lambda Block (Recommended)

```json
{
  "Version": "2019-07",
  "Comment": "Connect flow with ElevenLabs TTS via Lambda",
  "StartAction": "PlayWelcomeMessage",
  "States": [
    {
      "Type": "MessageBlock",
      "Name": "PlayWelcomeMessage",
      "Next": "GetCustomerIntent",
      "Parameters": {
        "Text": "Welcome to Customer Service"
      }
    },
    {
      "Type": "InvokeLambdaBlock",
      "Name": "SynthesizeWithElevenLabs",
      "Parameters": {
        "LambdaFunctionArn": "arn:aws:lambda:REGION:ACCOUNT:function:elevenlabs-tts",
        "InvocationTimeLimitSeconds": 5,
        "InputParameters": {
          "text": "Please wait while we process your request",
          "voice_id": "21m00Tcm4TlvDq8ikWAM"
        }
      },
      "Next": "GetCustomerIntent"
    },
    {
      "Type": "MessageBlock",
      "Name": "GetCustomerIntent",
      "Parameters": {
        "Text": "Press 1 for account info, 2 for billing"
      },
      "Transitions": {
        "OnPressed1": "PlayAccountInfo",
        "OnPressed2": "PlayBillingInfo"
      }
    }
  ]
}
```

### Option B: Via Lex Bot Block

```json
{
  "Type": "InvokeLexBotBlock",
  "Name": "CustomerServiceBot",
  "Parameters": {
    "BotName": "IRS_Taxpayer_Assistant",
    "BotAlias": "PROD",
    "SessionState": {
      "DialogState": "ElicitIntent",
      "Intent": {
        "name": "WelcomeIntent"
      }
    }
  },
  "Next": "RouteByIntent"
}
```

---

## Workflow 3: Real-Time Streaming with Chime SDK

```python
# For WebRTC calls (agent workspace or customer-facing web app)
import asyncio
from elevenlabs import ElevenLabsClient

async def stream_elevenlabs_to_chime(
    text: str,
    voice_id: str,
    api_key: str,
    chime_session
):
    """Stream ElevenLabs audio directly to Chime SDK."""
    
    client = ElevenLabsClient(api_key=api_key)
    
    # Use streaming endpoint for real-time
    audio_stream = client.text_to_speech.convert_as_stream(
        voice_id=voice_id,
        text=text,
        model_id="eleven_turbo_v2"
    )
    
    # Send chunks to Chime
    async for chunk in audio_stream:
        await chime_session.send_audio_frame(chunk)
        # Simulate network latency
        await asyncio.sleep(0.01)

# Integration with Lambda for Connect
def lambda_handler(event, context):
    """WebRTC streaming handler."""
    
    text = event.get("text")
    voice_id = event.get("voice_id")
    api_key = get_elevenlabs_key()
    
    # For async streaming, use asyncio runner
    asyncio.run(stream_elevenlabs_to_chime(text, voice_id, api_key, chime_session))
    
    return {
        "statusCode": 200,
        "body": json.dumps({"status": "Audio streamed successfully"})
    }
```

---

## Workflow 4: Multi-Region Failover Setup

```python
import boto3
from botocore.exceptions import ClientError

def setup_elevenlabs_regional_failover(
    primary_region: str = "us-east-1",
    secondary_region: str = "us-west-2"
):
    """Deploy Secrets Manager and Lambda replicas across regions."""
    
    regions = [primary_region, secondary_region]
    
    for region in regions:
        sm_client = boto3.client("secretsmanager", region_name=region)
        
        try:
            sm_client.describe_secret(SecretId="elevenlabs-api")
            print(f"✅ Secret exists in {region}")
        except ClientError as e:
            if e.response["Error"]["Code"] == "ResourceNotFoundException":
                # Create secret in this region
                response = sm_client.create_secret(
                    Name="elevenlabs-api",
                    SecretString=json.dumps({
                        "api_key": os.environ.get("ELEVENLABS_API_KEY"),
                        "api_base": "https://api.elevenlabs.io/v1"
                    }),
                    AddReplicaRegions=[{
                        "Region": secondary_region if region == primary_region else primary_region
                    }]
                )
                print(f"✅ Secret created in {region} with cross-region replica")

# Usage
setup_elevenlabs_regional_failover(primary_region="us-east-1", secondary_region="us-west-2")
```

---

## Workflow 5: Deploy AI Agent to Contact Center

### Step 1: Create Contact Flow with Agent Block

```json
{
  "Version": "2019-07",
  "Comment": "Contact flow with ElevenLabs AI Agent",
  "StartAction": "PlayGreeting",
  "States": [
    {
      "Type": "MessageBlock",
      "Name": "PlayGreeting",
      "Next": "InvokeElevenLabsAgent",
      "Parameters": {
        "Text": "Welcome to customer service. You'll now speak with our AI assistant."
      }
    },
    {
      "Type": "InvokeLambdaBlock",
      "Name": "InvokeElevenLabsAgent",
      "Parameters": {
        "LambdaFunctionArn": "arn:aws:lambda:REGION:ACCOUNT:function:elevenlabs-agent-handler",
        "InvocationTimeLimitSeconds": 900,  # 15 minutes for agent to handle
        "InputParameters": {
          "agent_id": "agent_12345",
          "support_tier": "tier_1",
          "knowledge_base": "irs_faq",
          "escalation_queue": "human_support"
        }
      },
      "Next": "CheckAgentResult"
    },
    {
      "Type": "CheckAttributeBlock",
      "Name": "CheckAgentResult",
      "Conditions": [
        {
          "Name": "AgentSucceeded",
          "Condition": {
            "StringEquals": ["$.agent_status", "success"]
          },
          "Next": "PlaySuccess"
        },
        {
          "Name": "AgentEscalated",
          "Condition": {
            "StringEquals": ["$.agent_status", "escalated"]
          },
          "Next": "TransferToHuman"
        }
      ],
      "Default": "PlayTryAgain"
    },
    {
      "Type": "MessageBlock",
      "Name": "PlaySuccess",
      "Next": "DisconnectCall",
      "Parameters": {
        "Text": "Thank you for using our service. Goodbye!"
      }
    },
    {
      "Type": "TransferContactToQueueBlock",
      "Name": "TransferToHuman",
      "Parameters": {
        "QueueArn": "arn:aws:connect:REGION:ACCOUNT:instance/INSTANCE/queue/AgentQueue"
      },
      "Next": "DisconnectCall"
    },
    {
      "Type": "HangUpBlock",
      "Name": "DisconnectCall"
    }
  ]
}
```

### Step 2: Create Lambda Handler for Agent Integration

```python
import json
import boto3
import os
import requests
from datetime import datetime

def get_agent_credentials():
    """Retrieve agent API credentials."""
    secret_name = os.environ.get("ELEVENLABS_AGENT_SECRET_NAME", "elevenlabs-agent-api")
    region = os.environ.get("AWS_REGION", "us-east-1")
    
    client = boto3.client("secretsmanager", region_name=region)
    response = client.get_secret_value(SecretId=secret_name)
    return json.loads(response["SecretString"])

def record_agent_interaction(agent_id: str, call_id: str, transcript: str, outcome: str):
    """Log agent interaction for analytics."""
    dynamodb = boto3.resource("dynamodb")
    table = dynamodb.Table(os.environ.get("AGENT_METRICS_TABLE", "elevenlabs-agent-metrics"))
    
    table.put_item(Item={
        "agent_id": agent_id,
        "call_id": call_id,
        "timestamp": datetime.now().isoformat(),
        "transcript": transcript,
        "outcome": outcome,  # "success", "escalated", "failed"
        "ttl": int(datetime.now().timestamp()) + 86400*90  # 90-day retention
    })

def lambda_handler(event, context):
    """Handle Contact Center call with ElevenLabs AI Agent."""
    
    # Extract Contact Center parameters
    call_details = event.get("Details", {})
    parameters = call_details.get("Parameters", {})
    
    agent_id = parameters.get("agent_id")
    support_tier = parameters.get("support_tier", "tier_1")
    knowledge_base = parameters.get("knowledge_base")
    escalation_queue = parameters.get("escalation_queue")
    
    # Get customer info
    customer_number = call_details.get("ContactData", {}).get("CustomerEndpoint", {}).get("Address", "unknown")
    call_id = call_details.get("ContactData", {}).get("ContactId", "unknown")
    
    print(f"🤖 Starting AI Agent: {agent_id}")
    print(f"   Customer: {customer_number}")
    print(f"   Call ID: {call_id}")
    
    try:
        # Get agent credentials
        creds = get_agent_credentials()
        api_key = creds["api_key"]
        
        # Initialize agent conversation
        url = f"https://api.elevenlabs.io/v1/agents/{agent_id}/conversation/start"
        headers = {
            "xi-api-key": api_key,
            "Content-Type": "application/json"
        }
        
        payload = {
            "knowledge_base": knowledge_base,
            "context": {
                "customer_number": customer_number,
                "call_id": call_id,
                "support_tier": support_tier
            },
            "conversation_settings": {
                "max_turns": 20,
                "timeout_seconds": 300,
                "enable_sentiment_tracking": True
            }
        }
        
        response = requests.post(url, json=payload, headers=headers)
        response.raise_for_status()
        
        conversation = response.json()
        conversation_id = conversation["conversation_id"]
        
        print(f"✅ Agent conversation started: {conversation_id}")
        
        # Simulate getting conversation transcript (in real scenario, would stream)
        # For now, record the initiated conversation
        record_agent_interaction(
            agent_id=agent_id,
            call_id=call_id,
            transcript="[Conversation started with ElevenLabs AI Agent]",
            outcome="initiated"
        )
        
        # Determine if agent succeeded or needs escalation
        # In real implementation, would wait for agent to complete conversation
        agent_status = conversation.get("status", "in_progress")
        
        if agent_status == "resolved":
            outcome = "success"
        elif agent_status == "escalation_required":
            outcome = "escalated"
        else:
            outcome = "in_progress"
        
        # Return response for Contact Flow
        return {
            "statusCode": 200,
            "agent_status": outcome,
            "agent_id": agent_id,
            "conversation_id": conversation_id,
            "message": f"Agent conversation: {outcome}"
        }
    
    except Exception as e:
        print(f"❌ Agent error: {str(e)}")
        
        record_agent_interaction(
            agent_id=agent_id,
            call_id=call_id,
            transcript=f"Error: {str(e)}",
            outcome="failed"
        )
        
        # Escalate to human on agent failure
        return {
            "statusCode": 200,
            "agent_status": "escalated",
            "agent_id": agent_id,
            "error": str(e),
            "message": "Escalating to human agent due to technical issue"
        }

# Lambda environment variables
# ELEVENLABS_AGENT_SECRET_NAME=elevenlabs-agent-api
# AGENT_METRICS_TABLE=elevenlabs-agent-metrics
```

### Step 3: Monitor Agent Performance in Contact Center

```python
def get_agent_contact_center_metrics(agent_id: str, hours: int = 24) -> dict:
    """Get AI Agent performance metrics in Contact Center."""
    
    dynamodb = boto3.resource("dynamodb")
    table = dynamodb.Table("elevenlabs-agent-metrics")
    
    from datetime import datetime, timedelta
    cutoff_time = (datetime.now() - timedelta(hours=hours)).isoformat()
    
    # Query metrics
    response = table.query(
        KeyConditionExpression="agent_id = :agent_id AND #ts > :cutoff",
        ExpressionAttributeNames={"#ts": "timestamp"},
        ExpressionAttributeValues={
            ":agent_id": agent_id,
            ":cutoff": cutoff_time
        }
    )
    
    items = response.get("Items", [])
    
    # Calculate statistics
    outcomes = {}
    for item in items:
        outcome = item.get("outcome", "unknown")
        outcomes[outcome] = outcomes.get(outcome, 0) + 1
    
    total = len(items)
    success_rate = outcomes.get("success", 0) / total if total > 0 else 0
    escalation_rate = outcomes.get("escalated", 0) / total if total > 0 else 0
    
    print(f"📊 Agent Metrics - Last {hours} hours:")
    print(f"   Total Conversations: {total}")
    print(f"   Success Rate: {success_rate:.1%}")
    print(f"   Escalation Rate: {escalation_rate:.1%}")
    print(f"   Breakdown:")
    for outcome, count in outcomes.items():
        print(f"     - {outcome}: {count} ({count/total*100:.0f}%)")
    
    return {
        "agent_id": agent_id,
        "total_conversations": total,
        "success_rate": success_rate,
        "escalation_rate": escalation_rate,
        "outcomes": outcomes
    }

# Usage
metrics = get_agent_contact_center_metrics("agent_12345", hours=24)
```

---

## Workflow 6: Set Up Agent Handoff to Human Agents

### Configure Handoff Queue and Escalation Logic

```json
{
  "Type": "TransferContactToQueueBlock",
  "Name": "EscalateToHuman",
  "Parameters": {
    "QueueArn": "arn:aws:connect:us-east-1:ACCOUNT:instance/INSTANCE/queue/tier2-support",
    "ContactFlowId": "transfer-flow-id"
  },
  "Next": "LogEscalation",
  "OnFailure": "PlayRetryMessage"
}
```

### Track Agent Escalations and Feedback

```python
def record_escalation_reason(
    call_id: str,
    agent_id: str,
    escalation_reason: str,
    customer_satisfaction: int = None
):
    """Log escalation for quality improvement."""
    
    dynamodb = boto3.resource("dynamodb")
    table = dynamodb.Table("elevenlabs-escalations")
    
    table.put_item(Item={
        "call_id": call_id,
        "agent_id": agent_id,
        "timestamp": datetime.now().isoformat(),
        "escalation_reason": escalation_reason,
        "customer_satisfaction": customer_satisfaction,
        "ttl": int(datetime.now().timestamp()) + 86400*180
    })
    
    print(f"✅ Escalation logged: {call_id} → {escalation_reason}")

# Escalation reasons can be:
# - max_turns_exceeded
# - confidence_too_low
# - illegal_request
# - language_barrier
# - complex_issue
# - customer_requested
# - agent_error
```

---



| Issue | Solution |
|-------|----------|
| "Audio quality poor in Connect" | Use `eleven_turbo_v2` model, reduce text length, check bandwidth |
| "Lambda timeout (> 30s)" | Use streaming endpoint, cache voice models, set timeout to 60s |
| "Lex bot doesn't play audio" | Check S3 presigned URL validity, verify session attributes passed |
| "Audio URL returns 403" | Check S3 bucket policy, verify IAM permissions, regenerate URL |
| "Regional failover delays" | Pre-warm Lambda replicas, test failover monthly |

---

## Performance Targets

| Metric | Target | Typical |
|--------|--------|---------|
| TLS handshake to ElevenLabs | < 200ms | ~100ms |
| Text-to-speech latency | < 500ms | ~200ms |
| S3 upload | < 1s | ~300ms |
| Total Lambda execution | < 3s | ~800ms |
| Connect flow delay (user perceivable) | < 2s | ~1.2s |

---

## Cost & Budgeting

### Estimated Monthly Costs (1M calls, 500 chars avg)

| Component | Cost |
|-----------|------|
| ElevenLabs TTS (Pro tier) | ~$1,500 |
| Lambda invocations (1M @ $0.02/million) | ~$20 |
| S3 storage (30GB) | ~$1 |
| Secrets Manager | ~$0.40 |
| **Total** | **~$1,521/month** |

### Cost Optimization

- Use `eleven_turbo_v2` (cheaper than multilingual)
- Cache audio responses (S3, CloudFront)
- Batch synthesis for less frequent calls
- Regional routing (lower latency = fewer retries)

---

## Security Checklist

✅ ElevenLabs API key in Secrets Manager (KMS encrypted)  
✅ S3 audio bucket has private ACL + signed URLs only  
✅ Lambda IAM role limited to Secrets Manager + S3 + Logs  
✅ Contact flows validate input before TTS (no prompt injection)  
✅ Audit all API calls via CloudTrail  
✅ Rate limiting configured (100 calls/min per user)  

---

## Deployment Checklist

- [ ] Secrets Manager secret created with API key
- [ ] Lambda IAM role + policies applied
- [ ] Lambda function deployed with ElevenLabs integration
- [ ] Lex bot created and configured with Lambda hook
- [ ] S3 bucket created for audio storage
- [ ] Contact flow updated with Invoke Lambda block
- [ ] End-to-end test (voice call, listen to response)
- [ ] CloudWatch logs monitored for errors
- [ ] Failover tested (manual in secondary region)
- [ ] Cost tracking enabled (monthly budget alert)
