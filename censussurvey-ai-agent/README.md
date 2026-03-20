# Census Survey AI Agent

AI-powered self-service voice agent for US Census Bureau surveys in Amazon Connect.

## Architecture

```
┌─────────────────────────────────────────────────────────────────┐
│                    Amazon Connect (censussurvey)                │
│                    +1 (844) 593-8443 / 8422                     │
└───────────────────────────────┬─────────────────────────────────┘
                                │
                    ┌───────────▼───────────┐
                    │   Census AI Main Flow │
                    │   (Voice Self-Service)│
                    └───────────┬───────────┘
                                │
         ┌──────────────────────┼──────────────────────┐
         │                      │                      │
         ▼                      ▼                      ▼
┌─────────────────┐  ┌─────────────────┐  ┌─────────────────┐
│ CensusSelf-     │  │ Q in Connect    │  │ Agent Workspace │
│ ServiceAgent    │  │ AI Agent        │  │ + Cards View    │
│ (Lambda)        │  │ (Assist)        │  │                 │
└────────┬────────┘  └─────────────────┘  └─────────────────┘
         │
         │  Tools (Lambda)
         ├──────────────────┐
         ▼                  ▼
┌─────────────────┐  ┌─────────────────┐
│ CreateCallback  │  │ SurveyStatus    │
│ Escalate        │  │ (+ more tools)  │
└────────┬────────┘  └────────┬────────┘
         │                    │
         └────────┬───────────┘
                  ▼
         ┌─────────────────┐
         │    DynamoDB     │
         │  - Sessions     │
         │  - Responses    │
         │  - Cases        │
         │  - Audit        │
         └─────────────────┘
```

## Phone Numbers

| Number | Purpose |
|--------|---------|
| +1 (844) 593-8443 | Census Survey Main |
| +1 (844) 593-8422 | Census Survey Toll-Free |

## Components

### Lambda Functions

| Function | Purpose |
|----------|---------|
| `CensusSelfServiceAgent` | Main AI agent with Bedrock integration |
| `CensusCreateCallback` | Schedule callback cases |
| `CensusSurveyStatus` | Check survey completion status |
| `CensusEscalate` | Transfer to human with context |

### DynamoDB Tables

| Table | Purpose |
|-------|---------|
| `CensusSurveySessions-prod` | Conversation state |
| `CensusCallbackCases-prod` | Scheduled callbacks |
| `CensusEscalations-prod` | Escalation records |
| `CensusAuditLog-prod` | Audit trail |
| `CensusResponses` | Survey responses (existing) |

### Contact Flows

| Flow | Purpose |
|------|---------|
| `Census AI Main` | Primary inbound voice flow |

### Cards View

Agent desktop guide with:
- Caller verification procedures
- Survey completion help
- Privacy & trust talking points
- Refusal handling scripts
- Language & accessibility support
- Escalation criteria

## Deployment

### Prerequisites

- AWS CLI configured
- SAM CLI installed
- Python 3.11

### Deploy Infrastructure

```bash
cd infrastructure
sam build
sam deploy --guided \
  --stack-name census-survey-ai-agent \
  --parameter-overrides ConnectInstanceId=a1f79dc3-8a46-481d-bf15-b214a7a8b05f \
  --capabilities CAPABILITY_IAM
```

### Associate Lambdas with Connect

```bash
aws connect associate-lambda-function \
  --instance-id a1f79dc3-8a46-481d-bf15-b214a7a8b05f \
  --function-arn arn:aws:lambda:us-east-1:593804350786:function:CensusSelfServiceAgent

aws connect associate-lambda-function \
  --instance-id a1f79dc3-8a46-481d-bf15-b214a7a8b05f \
  --function-arn arn:aws:lambda:us-east-1:593804350786:function:CensusCreateCallback
```

### Import Contact Flow

1. Open Amazon Connect console
2. Go to Contact Flows
3. Create new flow
4. Import `contact-flows/census_ai_main.json`
5. Update Lambda ARNs
6. Publish

### Deploy Cards View

1. Open Amazon Connect agent workspace
2. Create new Step-by-Step Guide
3. Add ShowView block with `cards-view/census_agent_guide.json`

## AI Agent Intents

| Intent | Description | Target Containment |
|--------|-------------|-------------------|
| Trust Verification | "Is this really the Census?" | 95% |
| Survey Help | "How do I complete the survey?" | 80% |
| Callback Request | "Can someone call me back?" | 95% |
| Privacy Concerns | "Why do you need this info?" | 85% |
| Refusal | "I don't want to participate" | 60% |

## Demo Scenarios

### Scenario 1: Trust & Legitimacy
```
Caller: "How do I know this is really the Census?"
Sarah: "I understand your concern. I'm Sarah with the Census Bureau. 
       By law, your responses are protected under Title 13 and cannot 
       be shared with any other agency. You can verify this call at 
       census.gov or call 1-800-923-8282. Would you like me to send 
       you verification information?"
```

### Scenario 2: Callback Scheduling
```
Caller: "I can't do this now, can you call me tomorrow?"
Sarah: "Of course! I can schedule a callback for tomorrow. 
       What time works best for you?"
Caller: "Afternoon, around 2pm"
Sarah: "I've scheduled your callback for tomorrow afternoon. 
       Your case number is CASE-A1B2C3D4. You'll receive a call 
       within 24 hours. Is there anything else I can help with?"
```

### Scenario 3: Human Escalation
```
Caller: "I have a complicated living situation with my elderly parents..."
Sarah: "I understand. Complex household situations are best handled 
       by our specialists who can make sure everyone is counted correctly. 
       Let me transfer you to someone who can help. One moment please."
[Transfer with context to specialist queue]
```

## Testing

### Voice Test
1. Call +1 (844) 593-8443
2. Wait for greeting
3. Test: "Is this really the Census?"
4. Test: "Can I schedule a callback?"
5. Test: "I need to speak to someone"

### Lambda Test
```bash
aws lambda invoke \
  --function-name CensusSelfServiceAgent \
  --payload '{"Details":{"Parameters":{"action":"greeting"},"ContactData":{"ContactId":"test-123"}}}' \
  response.json
```

## Monitoring

- CloudWatch Logs: `/aws/lambda/CensusSelfServiceAgent`
- CloudWatch Metrics: Lambda duration, errors
- DynamoDB: Session counts, callback volumes
- Connect: Contact flow metrics, abandonment rates

## Security

- All Lambda functions use least-privilege IAM
- DynamoDB encryption at rest
- No PII logged in CloudWatch
- Audit trail in DynamoDB
- Title 13 compliance by design
