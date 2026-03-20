# Multi-tenancy Amazon Connect

A comprehensive toolkit for building AI-powered contact center solutions with Amazon Connect, ElevenLabs Conversational AI, and AWS services.

## 🎯 Featured Projects

### IRS Taxpayer Assistant (ElevenLabs AI Agent)

A production-ready AI voice agent for tax support, built with ElevenLabs Conversational AI.

**Live Demo:** Run locally with `python3 -m http.server 8000` and open `http://localhost:8000/irs_agent_test.html`

**Features:**
- 🎙️ **Voice + Text Chat** - Natural voice conversations with text fallback
- 🤖 **Gemini 2.0 Flash LLM** - Fast, intelligent responses
- 🔊 **ElevenLabs TTS** - Professional Sarah voice (Eleven Turbo v2)
- 📊 **Data Collection** - Tracks inquiry types and resolution status

**Agent ID:** `agent_6201km43egt3f39tt000587m4ehp`

**Capabilities:**
- Refund status inquiries (E-file: 21 days, Paper: 6-8 weeks)
- Payment plan options (Short-term 120 days, Long-term installments)
- General tax questions and IRS information
- Intelligent escalation to human agents

### Census Survey AI Agent

Self-service census survey system using Amazon Connect with Lex V2, Lambda, and Bedrock.

**Location:** `censussurvey-ai-agent/`

**Components:**
- Amazon Q in Connect self-service agent
- Custom knowledge base with census FAQ
- DynamoDB conversation storage
- Contact flow with voice integration

---

## 📁 Repository Structure

```
├── irs_agent_test.html          # ElevenLabs IRS agent web interface
├── censussurvey-ai-agent/       # Census survey Connect implementation
│   ├── contact-flows/           # Amazon Connect flow JSON
│   ├── lambda/                  # Lambda functions (Python)
│   ├── cards-view/              # Agent guide cards
│   └── prompts/                 # AI orchestration prompts
├── backend/                     # API backend services
├── frontend/                    # Web frontend components
├── infra/                       # CDK infrastructure
├── flow-tester-ui/              # Contact flow testing interface
├── voice_tester/                # Voice testing utilities
├── multimodel_analysis/         # Video/audio analysis tools
└── docs/                        # Documentation
```

---

## 🚀 Quick Start

### IRS Agent (ElevenLabs)

```bash
# Serve the web interface
cd /path/to/repo
python3 -m http.server 8000

# Open in browser
open http://localhost:8000/irs_agent_test.html
```

**Requirements:**
- Modern browser with microphone support
- HTTPS or localhost (required for microphone access)

### Census Survey Agent (Amazon Connect)

See `censussurvey-ai-agent/README.md` for deployment instructions.

**AWS Resources Required:**
- Amazon Connect instance
- Lex V2 bot with Lambda integration
- DynamoDB table
- Lambda functions with Bedrock access

---

## 🔧 Configuration

### ElevenLabs Agent

The IRS agent is configured via the ElevenLabs dashboard:

| Setting | Value |
|---------|-------|
| LLM | Gemini 2.0 Flash |
| Voice | Sarah (EXAVITQu4vr4xnSDxMaL) |
| TTS Model | Eleven Turbo v2 |
| Text Input | Enabled |
| Max Duration | 600 seconds |

### Amazon Connect

Contact flows and configurations are in:
- `censussurvey-ai-agent/contact-flows/`
- `infra/` (CDK templates)

---

## 📚 Related Repositories

| Repository | Description |
|------------|-------------|
| [multi-tenancy-voice-tester](https://github.com/636137/multi-tenancy-voice-tester) | Voice testing automation |
| [multi-tenancy-flow-tester-ui](https://github.com/636137/multi-tenancy-flow-tester-ui) | Contact flow testing UI |
| [multi-tenancy-census-ai-agent](https://github.com/636137/multi-tenancy-census-ai-agent) | Census AI agent standalone |
| [multi-tenancy-irs-agent-views](https://github.com/636137/multi-tenancy-irs-agent-views) | IRS agent dashboard views |
| [multi-tenancy-connect-infra](https://github.com/636137/multi-tenancy-connect-infra) | CDK/Lambda/Flows infrastructure |
| [elevenlabs-connect](https://github.com/636137/elevenlabs-connect) | ElevenLabs Connect integration toolkit |

---

## 🛠️ Development Scripts

| Script | Purpose |
|--------|---------|
| `create_irs_agent_correct.py` | Create IRS agent via ElevenLabs API |
| `deploy_irs_agent_real.py` | Deploy IRS agent configuration |
| `test_irs_agent_real.py` | Test IRS agent conversation |
| `setup_elevenlabs_secure.py` | Secure ElevenLabs credential setup |
| `check_elevenlabs_account.py` | Verify ElevenLabs account status |

---

## 🔒 Security

- API keys stored in environment variables or AWS Secrets Manager
- No credentials committed to repository
- See `SECURITY.md` for security policies

---

## 📋 Troubleshooting

### Audio Not Working (ElevenLabs Widget)

1. **Use localhost or HTTPS** - Browsers require secure context for microphone
2. **Grant microphone permission** - Click lock icon in address bar
3. **Hard refresh** - Cmd+Shift+R to clear cached scripts
4. **Check browser console** - F12 → Console for errors

### Widget Script Reference

```html
<!-- Working configuration -->
<elevenlabs-convai agent-id="YOUR_AGENT_ID"></elevenlabs-convai>
<script src="https://elevenlabs.io/convai-widget/index.js" async type="text/javascript"></script>
```

---

## 📄 License

This code is proprietary to **Maximus**. **No public license is granted**. See [`NOTICE`](./NOTICE).
