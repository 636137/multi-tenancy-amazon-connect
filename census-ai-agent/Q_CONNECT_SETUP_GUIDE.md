# Amazon Q in Connect - Census Survey AI Agent Setup Guide

## Overview

This guide completes the setup of Amazon Q in Connect Self-Service AI Agent for conducting dynamic Census surveys. The API-based setup is complete; these final steps must be done via the AWS Console.

## Already Configured (via API)

✅ **Q Connect Assistant**: `chaddhendren-ai-domain1`  
✅ **Q Connect AI Agent**: `Census-Survey-Agent` (SELF_SERVICE type)  
✅ **AI Prompt**: `Census-Survey-Orchestration` with Census survey instructions  
✅ **Bedrock Agent**: `CensusSurveyAgent` with comprehensive Census instructions  
✅ **Lex Bot**: `CensusSurveyAI` with Generative AI and 8 survey slots  
✅ **Contact Flow**: `1 - Census Survey AI Agent` with Deepgram TTS  

## Console Steps Required

### Step 1: Add Amazon Q in Connect Block to Contact Flow

1. Open **Amazon Connect Console** → Your instance → **Contact flows**
2. Edit **"1 - Census Survey AI Agent"** flow
3. After the "Set voice" block, add:
   - **Amazon Q in Connect** block (under "Integrate" section)
   - Configure: Select `chaddhendren-ai-domain1` assistant
4. Connect the block:
   - Success → Get customer input (Lex bot)
   - Error → Disconnect
5. **Publish** the flow

### Step 2: Verify Lex Bot Integration with Q Connect

1. Open **Amazon Lex Console** → `CensusSurveyAI` bot
2. Edit **en_US** locale
3. Add or verify **AMAZON.QInConnectIntent** with:
   - Assistant ARN: `arn:aws:wisdom:us-west-2:593804350786:assistant/1a4e1a15-0b63-4c96-90b7-3a0207d44879`
4. Build the bot
5. Update alias to new version

### Step 3: Test the Integration

Call: **+1 (844) 593-5770**

Expected experience:
1. Deepgram TTS greeting
2. Q Connect creates AI session
3. Lex bot routes to QInConnect intent
4. AI Agent conducts dynamic Census survey
5. 8 survey questions asked conversationally
6. Data captured in session attributes
7. Thank you and disconnect

## Architecture

```
┌────────────────────────────────────────────────────────────────┐
│                     Contact Flow                                │
├────────────────────────────────────────────────────────────────┤
│  1. Set Voice (Deepgram Aura-2 Odysseus)                       │
│  2. Welcome Message                                             │
│  3. Amazon Q in Connect (creates AI session)   ← Console step  │
│  4. Get Customer Input → Lex Bot                               │
│  5. Thank You / Disconnect                                      │
└────────────────────────────────────────────────────────────────┘
                              │
                              ▼
┌────────────────────────────────────────────────────────────────┐
│                     Lex Bot (CensusSurveyAI)                   │
├────────────────────────────────────────────────────────────────┤
│  • AMAZON.QInConnectIntent → Q Connect AI Agent                │
│  • FallbackIntent                                              │
│  • Generative AI enabled (Claude 3 Haiku)                      │
└────────────────────────────────────────────────────────────────┘
                              │
                              ▼
┌────────────────────────────────────────────────────────────────┐
│              Q Connect Self-Service AI Agent                    │
├────────────────────────────────────────────────────────────────┤
│  Name: Census-Survey-Agent                                      │
│  Prompt: Census-Survey-Orchestration                           │
│  Model: Claude 3 Sonnet                                        │
│                                                                 │
│  Dynamic Survey Flow:                                          │
│  1. Consent                                                    │
│  2. Household composition                                      │
│  3. Housing details                                            │
│  4. Employment status                                          │
│  5. Education levels                                           │
│  6. Income range                                               │
└────────────────────────────────────────────────────────────────┘
```

## Resource IDs

| Resource | ID | ARN |
|----------|----|----|
| Connect Instance | `3b3a1349-4cff-40f4-aed7-b19e2e1644b2` | - |
| Contact Flow | `d2312c30-066d-4115-a1a2-dba411c2725a` | - |
| Q Connect Assistant | `1a4e1a15-0b63-4c96-90b7-3a0207d44879` | `arn:aws:wisdom:us-west-2:593804350786:assistant/1a4e1a15-0b63-4c96-90b7-3a0207d44879` |
| Q Connect AI Agent | `11c03b42-2f50-4342-ab32-f74fe6606a12` | - |
| AI Prompt | `58737ff8-4e37-427d-b00d-bfcea42b1223` | - |
| Lex Bot | `BSAIKYT20J` | `arn:aws:lex:us-west-2:593804350786:bot-alias/BSAIKYT20J/UMMWRQRQ8Q` |
| Bedrock Agent | `HEO2C3GL5P` | `arn:aws:bedrock:us-west-2:593804350786:agent-alias/HEO2C3GL5P/EYQRIC6K98` |

## Session Attributes (from Q Connect)

After the AI conversation, these attributes contain the session data:
- `x-amz-lex:q-in-connect-response` - AI response text
- `x-amz-lex:q-in-connect:session-arn` - Session identifier
- `x-amz-lex:q-in-connect:conversation-status` - READY/PROCESSING/CLOSED
- `x-amz-lex:q-in-connect:conversation-status-reason` - SUCCESS/FAILED/REJECTED

## Alternative: Current Working Configuration

If Q Connect console setup is not completed, the current Lex bot configuration provides a working Census survey experience:
- **Generative AI enabled** (Claude 3 Haiku via Bedrock)
- **8 survey slots** with dynamic elicitation
- **Deepgram TTS** for high-quality voice

Test: Call **+1 (844) 593-5770**
