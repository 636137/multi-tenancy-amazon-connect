## Proprietary Notice

This code is proprietary to **Maximus**. **No public license is granted**. See [`NOTICE`](./NOTICE).

---

# Amazon Connect Voice Testing & Agent Guides Framework

[![Python 3.12+](https://img.shields.io/badge/python-3.12+-blue.svg)](https://www.python.org/downloads/)
[![AWS](https://img.shields.io/badge/AWS-Connect%20%7C%20Chime%20%7C%20Bedrock-orange.svg)](https://aws.amazon.com/)
[![License: MIT](https://img.shields.io/badge/License-MIT-green.svg)](LICENSE)

**Automated voice testing for Amazon Connect contact centers** — Make real phone calls with AI-powered callers, test IVR flows, validate Lex bot conversations, and deploy step-by-step agent guides.

## What This Does

| Capability | Description |
|------------|-------------|
| **Real Phone Calls** | Initiates actual PSTN calls via AWS Chime SDK to test your contact centers |
| **AI Caller** | Lambda-based caller speaks via Polly, listens, and responds intelligently |
| **AI-to-AI Conversations** | Two Nova Sonic instances talking to each other (demo included) |
| **Agent Step-by-Step Guides** | Cards-based views that pop up when agents accept calls |
| **Status Tracking** | Real-time call state tracking via DynamoDB |
| **Copilot Skills** | 4 reusable agent skills for deployment, testing, and voice workflows |

## Live Demo

| Instance | Phone | Agent Login |
|----------|-------|-------------|
| **Treasury Connect** | +1 833-289-6602 | [Agent Workspace](https://treasury-connect-prod.my.connect.aws/agent-app-v2) |

```
✅ Direct-to-agent routing (no IVR menu)
✅ IRS Agent Guide Cards display on call accept
✅ 5 IRS use case cards with procedures and policies
```

---

## IRS Agent Step-by-Step Guides

This framework includes a complete **Agent Guides** implementation that displays interactive cards when agents accept voice calls.

### How It Works

```
┌─────────────────────────────────────────────────────────────────────┐
│                    AGENT GUIDE FLOW                                  │
├─────────────────────────────────────────────────────────────────────┤
│                                                                      │
│  📞 Caller dials +1 833-289-6602                                     │
│       ↓                                                              │
│  🔊 Brief greeting → Transfer to queue                               │
│       ↓                                                              │
│  ⚙️  UpdateContactEventHooks sets DefaultAgentUI                     │
│       ↓                                                              │
│  👤 Agent accepts call                                               │
│       ↓                                                              │
│  📋 Event flow triggers → ShowView → Cards appear!                   │
│                                                                      │
└─────────────────────────────────────────────────────────────────────┘
```

### IRS Use Case Cards (5 Topics)

| Card | Icon | Description |
|------|------|-------------|
| **Refund Status Inquiry** | 💰 | E-file: 21 days, Paper: 6-8 weeks, IDRS IMFOL codes |
| **Identity Verification** | 🛡️ | Letter 5071C/6331C, ID.me, phone verification |
| **Payment Plan Setup** | 💳 | Installment agreements, $50K threshold, Form 433 |
| **Transcript Request** | 📄 | Form 4506-T, online portal, 3-year availability |
| **Notice Explanation** | 📬 | CP2000, CP14, LTR notices, response deadlines |

### Technical Implementation

The guides use Amazon Connect's **AWS Managed Views** with the `Cards` template:

```json
{
  "ViewResource": {
    "Id": "arn:aws:connect:us-east-1:aws:view/cards"
  },
  "ViewData": {
    "Heading": "IRS Taxpayer Services Guide",
    "CardsPerRow": "1",
    "Cards": [...]
  }
}
```

**Key insight:** AWS managed views use `arn:aws:connect:REGION:aws:view/TEMPLATE` (with `aws` as account), NOT your account ID.

### Files

```
irs-agent-views/
├── SETUP_GUIDE.md              # Configuration instructions
├── irs_dashboard_cards.json    # Main dashboard view definition
├── flows/                      # Contact flow exports
└── *_detail.json               # Individual card detail views
```

---

## Quick Start

### 1. Clone and Setup

```bash
git clone https://github.com/636137/NovaSonicToNovaSonic.git
cd NovaSonicToNovaSonic

# Python 3.12+ required
python3.12 -m venv .venv312
source .venv312/bin/activate
pip install -r requirements.txt
```

### 2. Configure AWS

```bash
aws configure
# Needs: Connect, Chime SDK Voice, Bedrock, DynamoDB, Polly access
```

### 3. Run Voice Tests

```bash
# Test your Connect contact flows with real calls
python voice_tester/run_pstn_tests.py
```

### 4. Try AI-to-AI Demo (Optional)

```bash
# Watch two AI voices have a conversation
python voice_tester/sonic_live_playback.py
```

---

## Architecture

```
┌────────────────────────────────────────────────────────────────────┐
│                        PSTN VOICE TESTING                          │
├────────────────────────────────────────────────────────────────────┤
│                                                                     │
│   ┌─────────────┐    ┌──────────────┐    ┌─────────────────────┐   │
│   │ Test Runner │───▶│ Chime SDK    │───▶│  Amazon Connect     │   │
│   │ Python CLI  │    │ SIP Media App│    │  Contact Flow       │   │
│   └─────────────┘    └──────┬───────┘    └─────────────────────┘   │
│                             │                                       │
│                             ▼                                       │
│                      ┌──────────────┐                               │
│                      │ SIP Lambda   │                               │
│                      │ • Polly TTS  │◀──── "Hello, this is a       │
│                      │ • Bedrock AI │      test call..."           │
│                      │ • Status     │                               │
│                      └──────┬───────┘                               │
│                             │                                       │
│                             ▼                                       │
│                      ┌──────────────┐    ┌─────────────────────┐   │
│                      │  DynamoDB    │───▶│  Test Results JSON  │   │
│                      │  Status      │    │  voice_output/      │   │
│                      └──────────────┘    └─────────────────────┘   │
│                                                                     │
└────────────────────────────────────────────────────────────────────┘
```

---

## Project Structure

```
├── .github/
│   ├── copilot-instructions.md     # Copilot custom instructions
│   └── skills/                     # 4 Agent Skills (copy these!)
│       ├── aws-deployment/         # Deploy Connect, Lex, Lambda
│       ├── nova-sonic/             # Voice streaming with Bedrock
│       ├── testing-automation/     # Generate tests
│       └── voice-testing/          # PSTN call testing
│
├── irs-agent-views/                # 🆕 Agent Step-by-Step Guides
│   ├── SETUP_GUIDE.md              # Configuration documentation
│   ├── irs_dashboard_cards.json    # Main view definition
│   └── flows/                      # Contact flow exports
│
├── voice_tester/                   # Main testing framework
│   ├── run_pstn_tests.py          # ⭐ Main test runner
│   ├── sonic_live_playback.py     # ⭐ AI-to-AI demo
│   ├── nova_sonic_working.py      # Nova Sonic client
│   ├── ai_to_ai_conversation.py   # Two AIs talking
│   └── scenarios/                  # Test scenario YAML files
│
├── scripts/                        # Utilities
│   ├── fix_sip_lambda.py          # Update SIP Lambda handler
│   ├── setup_voice_testing.py     # Create DynamoDB table
│   ├── check_lambda_logs.py       # Debug Lambda
│   └── analyze_connect_flows.py   # Analyze your Connect flows
│
├── lambda/                         # Lambda handlers
│   ├── lex/                        # Lex fulfillment
│   └── survey/                     # Survey handler
│
├── contact_flows/                  # Connect flow definitions
├── lex/                            # Lex bot configuration
├── cdk/                            # CDK infrastructure
└── docs/                           # Additional documentation
```

---

## Key Commands

| Command | What It Does |
|---------|--------------|
| `python voice_tester/run_pstn_tests.py` | Run PSTN voice tests against Connect |
| `python voice_tester/sonic_live_playback.py` | AI-to-AI conversation demo |
| `python scripts/fix_sip_lambda.py` | Update the SIP Lambda handler |
| `python scripts/check_lambda_logs.py` | View recent Lambda logs |
| `python scripts/analyze_connect_flows.py` | Analyze Connect instance flows |

---

## Agent Guides Configuration

### Prerequisites

1. Amazon Connect instance with Views enabled
2. Agent Workspace access (not CCP)
3. Security profile with Views permissions

### Flow Architecture

For views to display on voice calls, you need:

1. **Main Inbound Flow** with `UpdateContactEventHooks`:
   ```json
   {
     "Type": "UpdateContactEventHooks",
     "Parameters": {
       "EventHooks": {
         "DefaultAgentUI": "arn:aws:connect:REGION:ACCOUNT:instance/ID/contact-flow/EVENT_FLOW_ID"
       }
     }
   }
   ```

2. **Event Flow** with `ShowView`:
   ```json
   {
     "Type": "ShowView",
     "Parameters": {
       "ViewResource": {
         "Id": "arn:aws:connect:us-east-1:aws:view/cards"
       },
       "ViewData": { ... }
     }
   }
   ```

### AWS Managed View Templates

| Template | ARN | Use For |
|----------|-----|---------|
| Cards | `arn:aws:connect:REGION:aws:view/cards` | Dashboard with clickable cards |
| Detail | `arn:aws:connect:REGION:aws:view/detail` | Single topic detail view |
| Form | `arn:aws:connect:REGION:aws:view/form` | Data collection forms |
| List | `arn:aws:connect:REGION:aws:view/list` | Scrollable item lists |
| Confirmation | `arn:aws:connect:REGION:aws:view/confirmation` | Action confirmations |

**Important:** Use `aws` as the account ID for managed views, not your AWS account number.

---

## Copilot Agent Skills

This project includes **4 reusable Agent Skills** for GitHub Copilot. Copy them to any project!

### Available Skills

| Skill | Invoke | Use For |
|-------|--------|---------|
| **AWS Deployment** | `/aws-deployment` | Deploy Connect, Lex, Lambda with self-healing |
| **Nova Sonic** | `/nova-sonic` | Bidirectional voice streaming with Bedrock |
| **Voice Testing** | `/voice-testing` | Create PSTN call tests |
| **Testing Automation** | `/testing-automation` | Generate unit/integration tests |

### Copy to Your Project

```bash
# Copy skills folder
cp -r .github/skills/ /your/project/.github/skills/

# Copy Copilot instructions
cp .github/copilot-instructions.md /your/project/.github/
```

See [SKILLS.md](SKILLS.md) for detailed documentation on customizing skills.

---

## Configuration

### Test Targets

Edit `voice_tester/run_pstn_tests.py` to add your phone numbers:

```python
targets = [
    {
        "name": "My IVR",
        "phone": "+15551234567",
        "scenario": {"greeting": "Test call"}
    }
]
```

### AWS Resources

| Resource | Description |
|----------|-------------|
| `treasury-synthetic-caller` | Chime SIP Media Application |
| `treasury-sip-media-app` | Lambda handler for SIP events |
| `voice-test-scenarios` | DynamoDB table (us-east-1) |
| `+13602098836` | Outbound caller ID |

---

## How It Works

### 1. Test Runner Initiates Call
```python
chime.create_sip_media_application_call(
    FromPhoneNumber="+13602098836",
    ToPhoneNumber="+18332895330",  # Your Connect number
    SipMediaApplicationId="..."
)
```

### 2. Lambda Handles SIP Events
```
NEW_OUTBOUND_CALL → RINGING → CALL_ANSWERED → ACTION_SUCCESSFUL → HANGUP
```

### 3. Lambda Speaks via Polly
```python
{
    "Type": "Speak",
    "Parameters": {
        "Text": "Hello, this is an automated test call.",
        "Engine": "neural",
        "VoiceId": "Joanna"
    }
}
```

### 4. Status Tracked in DynamoDB
```
test_id: "90ba4a34-1d94-439e-919f-eb79d0113e73"
status: "received_input" → "completed"
```

---

## Troubleshooting

### Views Not Displaying

**Symptom:** Agent accepts call but no view appears

**Checklist:**
1. Using Agent Workspace (`/agent-app-v2`) not legacy CCP
2. `UpdateContactEventHooks` with `DefaultAgentUI` is in the flow
3. Event flow has `ShowView` block
4. View ARN uses correct format:
   - AWS managed: `arn:aws:connect:REGION:aws:view/cards`
   - Custom: `arn:aws:connect:REGION:ACCOUNT:instance/ID/view/VIEW_ID:$LATEST`
5. Agent security profile has Views permissions

**"View resource is not available" error:**
- Wrong ARN format - use `aws` account for managed views
- View not published (check status in Views console)

### Call Timeouts
```bash
# Check DynamoDB table exists
python -c "import boto3; print(boto3.client('dynamodb', region_name='us-east-1').describe_table(TableName='voice-test-scenarios'))"

# Check Lambda logs
python scripts/check_lambda_logs.py
```

### PlayAudio Errors
Use `Speak` action instead (simpler, more reliable):
```python
{"Type": "Speak", "Parameters": {"Text": "Hello", "VoiceId": "Joanna"}}
```

### Wrong Region
Ensure all resources are in us-east-1:
- DynamoDB table
- Lambda function
- Chime SIP Media Application

---

## AWS Prerequisites

- **Amazon Connect** instance with phone number
- **Chime SDK Voice** SIP Media Application + Voice Connector
- **Lambda** with SIP handler code
- **DynamoDB** table for status tracking
- **Polly** access for TTS
- **Bedrock** access (optional, for AI responses)

---

## License

MIT License - see [LICENSE](LICENSE)
