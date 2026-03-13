# Census AI Agent for Amazon Connect

An LLM-powered AI agent that conducts US Census surveys through Amazon Connect using natural voice conversations.

## Overview

This project deploys a fully autonomous Census Survey AI Agent that:
- Greets callers naturally using Deepgram TTS
- Asks dynamic survey questions powered by Claude 3 Haiku
- Captures responses using Deepgram STT through Lex
- Maintains conversation state in DynamoDB
- Stores completed surveys in S3
- Provides a real-time analytics dashboard

## Quick Start

**Phone Number**: +1 (844) 593-5770

Call to experience the AI agent conducting a Census survey.

## Architecture

```
┌─────────────┐     ┌─────────────┐     ┌─────────────┐
│   Caller    │────▶│   Connect   │────▶│   Lambda    │
└─────────────┘     │   Flow      │     │  (Claude)   │
                    └──────┬──────┘     └──────┬──────┘
                           │                    │
                    ┌──────▼──────┐     ┌──────▼──────┐
                    │  Lex V2 Bot │     │  DynamoDB   │
                    │ (Deepgram)  │     │   State     │
                    └─────────────┘     └─────────────┘
```

## Components

### Lambda Function
- **Name**: CensusSurveyLLMAgent
- **Runtime**: Python 3.11
- **Purpose**: Generates AI responses using Bedrock Converse API
- **Model**: Claude 3 Haiku (anthropic.claude-3-haiku-20240307-v1:0)

### Lex Bot
- **Name**: CensusSurveyAI
- **STT**: Deepgram (flux-general-en)
- **Fulfillment**: Lambda with InputTranscript

### Contact Flow
- **Name**: 1 - Census Survey AI Agent
- **TTS**: Deepgram Aura 2 (odysseus voice)
- **Pattern**: Lambda → Lex → Lambda (loop)

### Storage
- **DynamoDB**: CensusSurveyConversations (call state)
- **S3**: census-survey-results-593804350786 (completed surveys)

### Dashboard
- **URL**: https://d2z5yerl8hzju3.cloudfront.net
- **Features**: Real-time stats, survey list, analytics

## Files

```
census-ai-agent/
├── README.md                 # This file
├── lambda/
│   └── census_llm_agent.py  # Lambda source code
├── ui/
│   └── index.html           # Dashboard UI
├── skill/
│   └── SKILL.md             # Copilot skill definition
└── Q_CONNECT_SETUP_GUIDE.md # Q Connect setup docs
```

## AWS Resources

| Resource | ARN/ID |
|----------|--------|
| Lambda | arn:aws:lambda:us-west-2:593804350786:function:CensusSurveyLLMAgent |
| DynamoDB | CensusSurveyConversations |
| Lex Bot | BSAIKYT20J |
| Lex Alias | UMMWRQRQ8Q (version 9) |
| Connect Flow | d2312c30-066d-4115-a1a2-dba411c2725a |
| CloudFront | E3A2AN195NO14F |
| Dashboard | https://d2z5yerl8hzju3.cloudfront.net |

## Survey Questions

The AI asks these questions in a natural conversational flow:

1. Greeting and consent to participate
2. How many people live at this address?
3. What are the ages of household members?
4. Is this a house, apartment, condo, or other?
5. Do you own or rent?
6. How many bedrooms?
7. Thank you and completion

## Configuration

### Deepgram TTS Voice Options
- odysseus (male, warm)
- thalia (female, friendly)
- angus (male, authoritative)

### Bedrock Models
- Claude 3 Haiku (fast, cost-effective)
- Claude 3 Sonnet (higher quality)
- Claude 3.5 Sonnet (best quality)

## Monitoring

### CloudWatch Logs
- Lambda: `/aws/lambda/CensusSurveyLLMAgent`
- Connect: Flow logging enabled

### Metrics to Watch
- Lambda duration (should be < 3s)
- Bedrock throttling errors
- DynamoDB consumed capacity

## Cost

Estimated per 1000 surveys:
- Amazon Connect: $0.50
- Lambda: $0.10
- Bedrock (Haiku): $2.00
- DynamoDB: $0.01
- **Total**: ~$2.61

## Troubleshooting

### "Technical difficulty" message
- Check Lambda CloudWatch logs
- Verify Bedrock permissions
- Check DynamoDB table exists

### No speech recognition
- Verify Lex bot is built
- Check Deepgram API key in Secrets Manager
- Ensure Unlimited AI is enabled on Connect instance

### Dashboard not loading
- CloudFront can take 5-10 minutes to deploy
- Check browser console for errors
- Verify S3 bucket policy

## License

Internal use only - Maximus
