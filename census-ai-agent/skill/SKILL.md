---
name: census-ai-agent
description: Deploy an LLM-powered Census Survey AI Agent in Amazon Connect with Deepgram TTS, Claude AI, and real-time analytics dashboard.
user-invocable: true
disable-model-invocation: false
---

# Census AI Agent Skill

Deploy a fully autonomous AI agent in Amazon Connect that conducts US Census surveys using natural conversation powered by Claude 3 Haiku.

## Features

- **LLM-Powered Conversations**: Claude 3 Haiku generates dynamic survey questions
- **Deepgram TTS**: Natural voice synthesis with odysseus voice
- **Deepgram STT**: Third-party speech recognition in Lex
- **DynamoDB State**: Persistent conversation state per call
- **S3 Storage**: Completed survey results storage
- **CloudFront Dashboard**: Real-time analytics UI

## Architecture

```
Caller → Connect → Lambda (greeting) → Lex (speak+capture) ─┐
                         ↑                                   │
                         └── Lambda (with transcript) ←──────┘
                                    │
                              Claude 3 Haiku
                                    │
                              DynamoDB (state)
```

## Deployment

### Prerequisites
- Amazon Connect instance with Unlimited AI enabled
- Deepgram API key in Secrets Manager
- Bedrock access to Claude 3 Haiku
- IAM role with Lambda, DynamoDB, Bedrock permissions

### Quick Deploy

```bash
# 1. Create Lambda function
aws lambda create-function \
  --function-name CensusSurveyLLMAgent \
  --runtime python3.11 \
  --handler lambda_function.handler \
  --role arn:aws:iam::ACCOUNT:role/CensusSurveyLLMAgentRole \
  --zip-file fileb://lambda/census_llm_agent.zip

# 2. Create DynamoDB table
aws dynamodb create-table \
  --table-name CensusSurveyConversations \
  --key-schema AttributeName=contact_id,KeyType=HASH \
  --attribute-definitions AttributeName=contact_id,AttributeType=S \
  --billing-mode PAY_PER_REQUEST

# 3. Create Lex bot with FallbackIntent Lambda fulfillment
# (See lex-setup.md for detailed configuration)

# 4. Create Connect contact flow
# (See flow-template.json)

# 5. Deploy dashboard
aws s3 cp ui/index.html s3://census-dashboard-bucket/
```

### Resources Created

| Resource | Type | Purpose |
|----------|------|---------|
| CensusSurveyLLMAgent | Lambda | AI conversation logic |
| CensusSurveyConversations | DynamoDB | Call state storage |
| CensusSurveyAI | Lex V2 Bot | Speech capture |
| Census Survey AI Agent | Connect Flow | Call routing |
| census-survey-dashboard | CloudFront | Analytics UI |

## Configuration

### Lambda Environment Variables
- `BEDROCK_MODEL`: anthropic.claude-3-haiku-20240307-v1:0
- `DYNAMODB_TABLE`: CensusSurveyConversations

### Contact Flow Parameters
- TTS Engine: deepgram:aura-2
- Voice: odysseus
- Lex Bot: CensusSurveyAI

## Survey Flow

1. **Greeting**: AI greets caller and asks if they have time
2. **Household Count**: How many people live at this address?
3. **Ages**: What are the ages of household members?
4. **Housing Type**: House, apartment, condo, or other?
5. **Ownership**: Own or rent?
6. **Bedrooms**: How many bedrooms?
7. **Completion**: Thank and end survey

## Customization

### Modify Survey Questions
Edit the `SYSTEM_PROMPT` in `lambda/census_llm_agent.py`:

```python
SYSTEM_PROMPT = """You are a friendly US Census Bureau interviewer...
SURVEY QUESTIONS (ask in order):
1. Your custom question here
2. Another question
...
"""
```

### Change Voice
Update the contact flow voice block:
- `TextToSpeechVoice`: odysseus, thalia, or other Deepgram voice
- `TextToSpeechEngine`: deepgram:aura-2

### Add Languages
1. Add Lex locale (es_US, etc.)
2. Translate SYSTEM_PROMPT
3. Update voice to language-appropriate option

## Monitoring

### CloudWatch Logs
- Lambda: `/aws/lambda/CensusSurveyLLMAgent`
- Connect: Contact flow logs

### Dashboard
- URL: https://YOUR_CLOUDFRONT_DOMAIN
- Shows: Total surveys, completion rate, avg household size

## Troubleshooting

### Survey not progressing
- Check Lambda CloudWatch logs for Bedrock errors
- Verify DynamoDB table permissions
- Ensure Lex fulfillment is configured

### No audio
- Verify Deepgram API key in Secrets Manager
- Check Connect instance has third-party TTS enabled

### Lex not capturing speech
- Verify Deepgram STT is enabled in Lex locale
- Check Lex bot is built and alias is deployed

## Cost Estimation

Per 1000 surveys (avg 5 min each):
- Connect: ~$0.50
- Lambda: ~$0.10
- Bedrock (Haiku): ~$2.00
- DynamoDB: ~$0.01
- Total: ~$2.61 per 1000 surveys
