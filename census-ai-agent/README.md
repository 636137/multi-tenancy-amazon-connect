# Census Survey AI Agent

A conversational AI agent for conducting Census Bureau surveys via Amazon Connect voice calls.

## Architecture

```
┌─────────────────┐     ┌──────────────────┐     ┌─────────────────┐
│  Phone Call     │────▶│  Amazon Connect  │────▶│  Lambda         │
│  +1 833-289-5330│     │  Census AI Agent │     │  CensusStrands  │
└─────────────────┘     │  Contact Flow    │     │  Agent          │
                        └──────────────────┘     └────────┬────────┘
                                                          │
                        ┌──────────────────┐     ┌────────▼────────┐
                        │  DynamoDB        │◀────│  Amazon Bedrock │
                        │  Sessions &      │     │  Nova Premier   │
                        │  Responses       │     └─────────────────┘
                        └──────────────────┘
```

## Phone Number

**📞 +1 (833) 289-5330**

## Survey Questions

Sarah (the AI agent) asks 3 questions:
1. How many people live in your household?
2. Are there any children under 18?
3. Do you own or rent your home?

## How It Works

1. **Caller dials** the toll-free number
2. **Connect Flow** invokes Lambda with `__greeting__` for initial greeting
3. **Lambda** uses Nova Premier to generate conversational responses
4. **Flow loops**: speak response → wait for input → invoke Lambda
5. **Survey complete**: Lambda marks session complete, returns goodbye
6. **Disconnect**: On next invocation, Lambda throws `SURVEY_COMPLETE` exception
7. **Flow error branch** catches exception → disconnects call

## AWS Resources

| Resource | ID/Name |
|----------|---------|
| Connect Instance | census-enumerator-9652 (`1d3555df-0f7a-4c78-9177-d42253597de2`) |
| Contact Flow | Census AI Agent (`4a2354b7-b179-400d-b175-82051ff9059d`) |
| Lambda | CensusStrandsAgent |
| DynamoDB Sessions | CensusChatSessions |
| DynamoDB Responses | CensusResponses |
| Bedrock Model | us.amazon.nova-premier-v1:0 |

## Lambda Response Format

```python
# Normal turn
{"response": "...", "sessionId": "contact-id"}

# After completion - triggers disconnect via exception
raise Exception("SURVEY_COMPLETE")
```

## Contact Flow Design

```
Start → Enable Logging → Set Voice → Invoke Greeting Lambda
                                            ↓
                                    Speak $.External.response
                                            ↓
                                    Wait for Input (30s timeout)
                                            ↓
                                    Invoke Turn Lambda ←──┐
                                            ↓             │
                                    Speak Response ───────┘
                                            
On Lambda Error (SURVEY_COMPLETE) → Disconnect
```

## Troubleshooting

### Call doesn't disconnect
- Check Lambda logs for "COMPLETE - triggering disconnect"
- Verify flow's Lambda error branch goes to Disconnect block
- Check DynamoDB session has `complete: true`

### "I didn't catch that" loops
- Ensure phone number routes to "Census AI Agent" flow (not Census Survey Flow)
- Check Lambda handler name matches deployed code

### Lambda timeout
- Current timeout: 60s
- Nova Premier can take 5-10s per turn

## Files

- `lambda/census_survey_agent.py` - Main Lambda code
- `lambda/census_llm_agent.py` - Previous Lex-based version (archived)

## Deployment

```bash
# Package and deploy Lambda
cd lambda
zip census_survey.zip census_survey_agent.py
aws lambda update-function-code --function-name CensusStrandsAgent \
    --zip-file fileb://census_survey.zip
aws lambda update-function-configuration --function-name CensusStrandsAgent \
    --handler census_survey_agent.lambda_handler
```
