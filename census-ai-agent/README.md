# Census Survey AI Agent

An LLM-powered Census Survey system using Amazon Connect, Lex V2, Amazon Bedrock Nova Premier, and Deepgram voices.

## Quick Start

**Call the survey:** +1 (844) 593-5770

**View results:** https://d2z5yerl8hzju3.cloudfront.net

## Architecture

```
Phone Call → Amazon Connect → Lex V2 (FallbackIntent) → Lambda → Nova Premier
                  ↓                                               ↓
            Deepgram Aura 2                              Full conversation
            (Thalia - young female)                      history context
```

**Key Design:**
- ALL input goes through Lex FallbackIntent → Lambda
- No Lex intent matching - the LLM handles all conversation logic
- Full conversation history passed to Nova Premier each turn
- Context-aware data extraction (only extracts when agent asked relevant question)

## Features

- **Nova Premier LLM**: Amazon's most capable model for natural conversation
- **Full Context**: Complete conversation history passed to LLM each turn
- **Smart Extraction**: Only extracts data when relevant question was asked
- **Deepgram Voice**: Natural-sounding Aura 2 voice (Thalia - young female)
- **Proper Call Termination**: Returns Close with fulfillmentState when complete
- **Real-time Dashboard**: View survey results via CloudFront

## AWS Resources

| Resource | ID/Name |
|----------|---------|
| Lambda (Survey) | CensusSurveyLLMAgent |
| Lambda (API) | CensusSurveyApiHandler |
| Lex Bot | CensusSurveyAI (BSAIKYT20J) |
| Lex Alias | prod (UMMWRQRQ8Q) - Version 19 |
| DynamoDB | CensusSurveyConversations |
| API Gateway | eaae6ys28g |
| CloudFront | d2z5yerl8hzju3 |
| S3 | census-survey-dashboard-593804350786 |
| Connect Instance | 3b3a1349-4cff-40f4-aed7-b19e2e1644b2 |
| Connect Flow | 1 - Census Survey AI Agent (d2312c30-066d-4115-a1a2-dba411c2725a) |
| Bedrock Model | us.amazon.nova-premier-v1:0 |
| Voice Engine | deepgram:aura-2 / thalia |

## Survey Data Collected

1. **Household size** - How many people live in the household
2. **Children** - Whether there are children under 18
3. **Ownership** - Whether they own or rent their home

## Files

- `lambda/census_llm_agent.py` - Main LLM survey Lambda (Nova Premier)
- `lambda/census_llm_agent_old.py` - Previous version (archived)
- `ui/index.html` - Dashboard frontend
- `skill/` - Copilot skill for redeployment

## How It Works

1. **Call comes in** → Connect plays greeting via Deepgram TTS
2. **User speaks** → Lex transcribes via STT, triggers FallbackIntent
3. **Lambda invoked** → Retrieves conversation history from DynamoDB
4. **Nova Premier** → Receives full history + system prompt with KNOWN FACTS / STILL NEED
5. **Response** → Lambda returns response via Lex TTS (Deepgram)
6. **Survey complete** → Lambda returns `Close` with `fulfillmentState: Fulfilled`
7. **Call ends** → Connect disconnects

## Troubleshooting

### Call doesn't connect
```bash
# Verify phone-to-flow association
aws connect list-phone-numbers-v2 --target-arn arn:aws:connect:us-west-2:593804350786:instance/3b3a1349-4cff-40f4-aed7-b19e2e1644b2
```

### Check Lambda logs
```bash
aws logs tail /aws/lambda/CensusSurveyLLMAgent --follow --region us-west-2
```

### Test Lambda directly
```bash
aws lambda invoke --function-name CensusSurveyLLMAgent \
  --payload '{"sessionId":"test","inputTranscript":"yes","sessionState":{"intent":{"name":"FallbackIntent"}}}' \
  --region us-west-2 /dev/stdout
```

### Call ends immediately
Check that Lambda is associated with Lex alias:
```bash
aws lexv2-models describe-bot-alias --bot-id BSAIKYT20J --bot-alias-id UMMWRQRQ8Q --region us-west-2
```

### Survey doesn't end
Lambda must return `dialogAction.type: Close` with `fulfillmentState: Fulfilled`.

### Test API
```bash
curl https://eaae6ys28g.execute-api.us-west-2.amazonaws.com/prod/surveys
```

## Copilot Skill

Use the `census-survey-agent` skill to redeploy or modify the system.

## Lambda Response Format

**Continue conversation:**
```json
{
  "sessionState": {
    "dialogAction": {"type": "ElicitIntent"},
    "intent": {"name": "FallbackIntent", "state": "InProgress"}
  },
  "messages": [{"contentType": "PlainText", "content": "..."}]
}
```

**End survey:**
```json
{
  "sessionState": {
    "dialogAction": {"type": "Close", "fulfillmentState": "Fulfilled"},
    "intent": {"name": "FallbackIntent", "state": "Fulfilled"}
  },
  "messages": [{"contentType": "PlainText", "content": "Thank you..."}]
}
```
