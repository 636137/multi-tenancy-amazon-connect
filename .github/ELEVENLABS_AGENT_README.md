# ElevenLabs AI Agent & Skills System

## Overview

A complete ElevenLabs orchestration system for Amazon Connect, consisting of one primary **agent** and four specialized **skills**. This enables developers, ops teams, and integration engineers to manage voice synthesis, AI agent creation and deployment, API authentication, and contact flow integration with a single entry point.

---

## Components

### 🤖 Primary Agent: `elevenlabs-orchestrator`
**File**: `.github/agents/elevenlabs-orchestrator.agent.md`

**Role**: Orchestrate all ElevenLabs workflows (TTS + AI Agents) with Amazon Connect

**Triggers**: When user mentions:
- "Set up ElevenLabs with AI Agent"
- "Create an autonomous AI agent"
- "Deploy ElevenLabs TTS and agent"
- "Configure voice synthesis and agent behavior"
- Or request full ElevenLabs AI orchestration

**Capabilities**:
✅ API & authentication setup  
✅ TTS voice synthesis  
✅ AI Agent creation and configuration  
✅ Agent personality and behavior tuning  
✅ Amazon Connect integration (TTS + agent)  
✅ Agent performance monitoring  
✅ Escalation and handoff logic  
✅ Testing & validation  
✅ Deployment orchestration  

**Output Format**: Issues / Actions / Outcomes (as specified)

**Entry Point**: Request in chat, agent will delegate to specialized skills as needed

---

### 🎯 Skill 1: `elevenlabs-api-setup`
**File**: `.github/skills/elevenlabs-api-setup/SKILL.md`

**Role**: Handle API authentication and credential management (TTS + AI Agents)

**Workflow Covers**:
1. Generate/obtain API key from elevenlabs.io
2. Create Secrets Manager secret (with KMS encryption)
3. Apply IAM policies for Lambda access
4. Setup dedicated AI Agent service account
5. Verify account tier and agent capabilities
6. Retrieve secrets safely in Lambda functions
7. List available voices and models by language
8. Validate API access end-to-end
9. Check agent quota and concurrent limits

**Typical Use Case**: "Set up ElevenLabs authentication for TTS and AI Agents"

**Key Functions**:
```python
create_elevenlabs_secret(api_key)           # Create/update secret
setup_agent_service_account(api_key)        # Agent-specific creds
check_agent_capabilities(api_key)           # Verify agent tier
get_elevenlabs_key()                        # Retrieve in Lambda
list_elevenlabs_voices(api_key)             # List models
validate_elevenlabs_api(api_key)            # Test connectivity
```

---

### 🎤 Skill 2: `elevenlabs-voice-synthesis`
**File**: `.github/skills/elevenlabs-voice-synthesis/SKILL.md`

**Role**: Generate speech from text, configure agent voice personalities

**Workflow Covers**:
1. Simple text-to-speech synthesis
2. Streaming audio (for real-time playback)
3. Batch synthesis with cost tracking
4. Voice cloning (premium feature)
5. **AI Agent voice personality configuration** (NEW)
6. **Voice persona profiles** - customer support, empathetic, authoritative, engaging (NEW)
7. Performance tuning for IVR vs. agent guides vs. autonomous agents
8. Cost estimation and latency measurement

**Model Selection Guide**:
- **eleven_turbo_v2** → IVR/Agent TTS (< 100ms latency)
- **eleven_multilingual_v2** → Multi-language agents (< 200ms latency)
- **eleven_monolingual_v1** → Cost-effective English-only

**Typical Use Case**: "Configure voice personality for my customer support AI Agent"

**Key Functions**:
```python
synthesize_speech(text, voice_id)                      # Simple TTS
synthesize_speech_streaming(text, voice_id)           # Real-time stream
configure_agent_voice_personality(agent_id, persona)  # Agent voice (NEW)
batch_synthesize(input_file, output_dir)              # Bulk processing
test_agent_voice_personality(samples, voice_id)       # Voice validation (NEW)
add_voice(name, audio_file)                           # Voice cloning
```

---

### 🤖 Skill 3: `elevenlabs-ai-agents` (NEW!)
**File**: `.github/skills/elevenlabs-ai-agents/SKILL.md`

**Role**: Create, configure, and deploy autonomous AI agents with custom behaviors

**Workflow Covers**:
1. Create AI agents with personality and capabilities
2. Configure agent voice (TTS integration)
3. Define conversation rules and intents (150+ intent examples)
4. Upload knowledge base (semantic search, hybrid retrieval)
5. **Set escalation triggers** - automatic handoff to humans
6. **Test agent conversations** - validate against test scripts
7. **Monitor agent performance** - success rate, escalation rate, sentiment
8. **Deploy agents to production** - canary deployment with auto-rollback
9. **Safety guardrails** - PII filtering, rate limiting, timeout protection

**Agent Models**:
- `elevenlabs-agent-v1` → Basic IVR replacement
- `elevenlabs-agent-advanced` → Intelligent customer support (recommended)
- `elevenlabs-agent-multilingual` → Global 40+ languages
- `elevenlabs-agent-expert` → Healthcare, finance, compliance

**Typical Use Case**: "Create an AI agent that handles refund inquiries and escalates complex cases"

**Key Functions**:
```python
create_elevenlabs_agent(name, description, personality)  # Create agent
configure_agent_voice(agent_id, voice_id)               # Voice setup
upload_knowledge_base(agent_id, kb_name, documents)     # Add docs
set_escalation_triggers(agent_id)                       # Handoff logic
test_agent_conversation(agent_id, test_script)          # Validation
get_agent_analytics(agent_id, metrics)                  # Performance
deploy_agent_to_production(agent_id, canary_percentage) # Production
```

---

### 🔌 Skill 4: `elevenlabs-connect-integration`
**File**: `.github/skills/elevenlabs-connect-integration/SKILL.md`

**Role**: Deploy ElevenLabs TTS and AI Agents in Amazon Connect contact flows and Lex bots

**Workflow Covers**:
1. Create IAM role for Lex TTS access
2. Build Lambda fulfillment handler for TTS
3. **Create AI Agent contact flow block** (NEW)
4. **Configure Lambda handler for agent integration** (NEW)
5. Update Lex bot configuration
6. Add ElevenLabs blocks to contact flows
7. Integration via Invoke Lambda or Lex Bot blocks
8. Real-time streaming with Chime SDK
9. **AI Agent escalation and handoff logic** (NEW)
10. Multi-region failover setup
11. Troubleshooting and performance tuning

**Typical Use Case**: "Deploy an ElevenLabs AI agent to handle incoming calls in my IRS contact center"

**Key Functions**:
```python
synthesize_with_elevenlabs(text, voice_id)  # TTS in Lex
upload_to_s3(audio_bytes)                   # Persist audio
stream_to_chime(text, voice_id)             # WebRTC streaming
lambda_handler_with_agent(event, context)   # Agent integration (NEW)
record_agent_interaction(agent_id, call_id) # Track agent (NEW)
get_agent_contact_center_metrics(agent_id)  # Agent performance (NEW)
setup_regional_failover(primary, secondary) # High availability
```

---

## Usage Patterns

### Pattern 1: Ask the Main Agent (Recommended)
```
User: "Create an AI agent for customer support with ElevenLabs voice"

Agent Response:
  ISSUES: No agent created, voice not configured, escalation rules missing
  ACTIONS:
    1. Create agent with personality via elevenlabs-ai-agents skill
    2. Configure voice with personality profile via elevenlabs-voice-synthesis skill
    3. Deploy to Contact Center via elevenlabs-connect-integration skill
  OUTCOMES:
    ✅ Agent created and tested
    ✅ Voice personality configured
    ✅ Contact flow updated with agent block
    ✅ Escalation rules deployed
```

### Pattern 2: Delegate to Specialized Skill
```
User: "I have the API key set up already. Just create an AI agent."

Agent: Delegates to elevenlabs-ai-agents skill
Response: Creates agent, returns agent_id, configuration, and test results
```

### Pattern 3: Deep AI Agent Integration
```
User: "Deploy an autonomous AI agent for IRS refund inquiries with 24/7 availability"

Agent: Orchestrates full workflow
  1. Validate API setup (elevenlabs-api-setup)
  2. Create agent with advanced knowledge base (elevenlabs-ai-agents)
  3. Configure empathetic voice personality (elevenlabs-voice-synthesis)
  4. Deploy to Contact Center with failover (elevenlabs-connect-integration)
  5. Setup monitoring and escalation (elevenlabs-ai-agents + analytics)
```

---

## File Structure

```
.github/
├── agents/
│   └── elevenlabs-orchestrator.agent.md       # Main entry point
└── skills/
    ├── elevenlabs-api-setup/
    │   └── SKILL.md                           # API & auth (TTS + agent)
    ├── elevenlabs-voice-synthesis/
    │   └── SKILL.md                           # TTS & voice personalities
    ├── elevenlabs-ai-agents/                  # NEW!
    │   └── SKILL.md                           # Agent creation & deployment
    └── elevenlabs-connect-integration/
        └── SKILL.md                           # Deploy TTS + agents to Connect
```

---

## Quick Access (Type in Chat)

1. **Full AI Orchestration**: "Create an AI agent for customer support"
2. **API Setup Only**: `/elevenlabs-api-setup`
3. **Voice TTS**: `/elevenlabs-voice-synthesis`
4. **AI Agent Creation**: `/elevenlabs-ai-agents` (NEW!)
5. **Connect Deployment**: `/elevenlabs-connect-integration`

---

## Environment Variables (Lambda)

```bash
# TTS Credentials
ELEVENLABS_SECRET_NAME=elevenlabs-api
ELEVENLABS_API_KEY=xxxx_xxxx_xxxx_xxxx
ELEVENLABS_VOICE_ID=21m00Tcm4TlvDq8ikWAM
ELEVENLABS_MODEL=eleven_turbo_v2

# AI Agent Credentials (NEW)
ELEVENLABS_AGENT_SECRET_NAME=elevenlabs-agent-api
ELEVENLABS_AGENT_ID=agent_12345
ELEVENLABS_AGENT_MODEL=elevenlabs-agent-advanced
ELEVENLABS_AGENT_TIER=advanced

# Configuration
AWS_REGION=us-east-1
ELEVENLABS_AUDIO_BUCKET=my-audio-bucket
AGENT_METRICS_TABLE=elevenlabs-agent-metrics
ELEVENLABS_ESCALATION_ENABLED=true
```

---

## Security Checklist

✅ API keys ONLY in Secrets Manager (KMS encrypted)  
✅ Separate service account for AI Agent operations  
✅ Lambda IAM roles restricted to minimal permissions  
✅ S3 audio bucket uses signed URLs (time-limited)  
✅ Agent conversation logs encrypted and audited  
✅ PII filtering enabled in agent responses  
✅ Escalation rules and human handoff validated  
✅ Audit trail enabled via CloudTrail  
✅ Rotation policy configured  
✅ Contact flows sanitize user input (no prompt injection)  

---

## Cost Estimation (Annual)

### TTS Only
| Volume | Monthly | Annual |
|--------|---------|--------|
| 100K calls (50 chars avg) | ~$75 | ~$900 |
| 1M calls | ~$750 | ~$9,000 |
| 10M calls | ~$7,500 | ~$90,000 |

### AI Agents (Inference + TTS)
| Volume | Monthly | Annual |
|--------|---------|--------|
| 100K calls | ~$1,500 | ~$18,000 |
| 1M calls | ~$15,000 | ~$180,000 |
| 10M calls | ~$150,000+ | ~$1.8M+ |

*Costs vary by agent model tier and knowledge base size*

---

## Troubleshooting

| Problem | First Check | Escalation |
|---------|-------------|------------|
| "API key not working" | Verify key at https://elevenlabs.io/app/settings/api-keys | Contact ElevenLabs support |
| "Agent not available in account" | Check subscription tier, agents must be enabled | Upgrade to Pro/Scale tier |
| "Agent misunderstands requests" | Review knowledge base, add more trigger phrases | Test with similar inputs |
| "High escalation rate" | Lower confidence threshold, improve knowledge base | Add new intents, train agent |
| "Contact flow not calling agent" | Check Lambda permissions, verify agent_id | Test Lambda separately |

---

## What Changed (AI Agents Update)

**New Capabilities**:
- ✅ Autonomous AI Agent creation and management  
- ✅ Agent personality and behavior configuration  
- ✅ Knowledge base integration for intelligent responses  
- ✅ Escalation logic and human handoff  
- ✅ Agent performance monitoring and analytics  
- ✅ Canary deployment with auto-rollback  
- ✅ Contact flow integration with agent blocks  
- ✅ Conversation testing and validation  

**Updated Components**:
- 🔄 **elevenlabs-orchestrator**: Now orchestrates AI agents + TTS  
- 🔄 **elevenlabs-api-setup**: Added agent service account setup  
- 🔄 **elevenlabs-voice-synthesis**: Added agent voice personality profiles  
- 🔄 **elevenlabs-connect-integration**: Added agent deployment workflows  
- 🆕 **elevenlabs-ai-agents**: Entire new skill for agent management  

---

## Next Steps

1. **Try the agent**: "Create an AI agent for my contact center"
2. **Review the AI Agents skill**: Read `.github/skills/elevenlabs-ai-agents/SKILL.md`
3. **Set up credentials**: Use elevenlabs-api-setup for agent service account
4. **Configure personality**: Use elevenlabs-voice-synthesis for voice tuning
5. **Deploy to production**: Follow Contact Flow Integration skill checklist
6. **Monitor**: Enable agent analytics dashboard

---

**Updated**: March 19, 2026  
**Agent**: ElevenLabs Orchestrator (with AI Agents)  
**Status**: Ready for production (TTS + autonomous AI agents)


---

## Components

### 🤖 Primary Agent: `elevenlabs-orchestrator`
**File**: `.github/agents/elevenlabs-orchestrator.agent.md`

**Role**: Orchestrate all ElevenLabs workflows with Amazon Connect

**Triggers**: When user mentions:
- "Set up ElevenLabs TTS"
- "Integrate ElevenLabs with Connect"
- "Configure voice synthesis"
- "Deploy ElevenLabs API"
- Or request full ElevenLabs orchestration

**Capabilities**:
✅ API & authentication setup  
✅ Voice synthesis orchestration  
✅ Amazon Connect integration  
✅ Configuration management  
✅ Testing & validation  
✅ Deployment orchestration  

**Output Format**: Issues / Actions / Outcomes (as requested)

**Entry Point**: Request in chat, agent will delegate to specialized skills as needed

---

### 🎯 Skill 1: `elevenlabs-api-setup`
**File**: `.github/skills/elevenlabs-api-setup/SKILL.md`

**Role**: Handle API authentication and credential management

**Workflow Covers**:
1. Generate/obtain API key from elevenlabs.io
2. Create Secrets Manager secret (with KMS encryption)
3. Apply IAM policies for Lambda access
4. Retrieve secrets safely in Lambda functions
5. List available voices and models by language
6. Validate API access end-to-end

**Typical Use Case**: "Set up ElevenLabs authentication for my Lambda functions"

**Key Functions**:
```python
create_elevenlabs_secret(api_key)      # Create/update secret
get_elevenlabs_key()                   # Retrieve in Lambda
list_elevenlabs_voices(api_key)        # List models
validate_elevenlabs_api(api_key)       # Test connectivity
```

---

### 🎤 Skill 2: `elevenlabs-voice-synthesis`
**File**: `.github/skills/elevenlabs-voice-synthesis/SKILL.md`

**Role**: Generate speech from text with model selection and optimization

**Workflow Covers**:
1. Simple text-to-speech synthesis
2. Streaming audio (for real-time playback)
3. Batch synthesis with cost tracking
4. Voice cloning (premium feature)
5. Performance tuning for IVR vs. agent guides
6. Cost estimation and latency measurement

**Model Selection Guide**:
- **eleven_turbo_v2** → IVR/Connect (< 100ms latency)
- **eleven_multilingual_v2** → Multi-language (< 200ms latency)
- **eleven_monolingual_v1** → Cost-effective English only

**Typical Use Case**: "Synthesize a greeting message with ElevenLabs and save to file"

**Key Functions**:
```python
synthesize_speech(text, voice_id)              # Simple TTS
synthesize_speech_streaming(text, voice_id)   # Real-time stream
batch_synthesize(input_file, output_dir)      # Bulk processing
add_voice(name, audio_file)                   # Voice cloning
```

---

### 🔌 Skill 3: `elevenlabs-connect-integration`
**File**: `.github/skills/elevenlabs-connect-integration/SKILL.md`

**Role**: Deploy ElevenLabs TTS in Amazon Connect contact flows and Lex bots

**Workflow Covers**:
1. Create IAM role for Lex TTS access
2. Build Lambda fulfillment handler
3. Update Lex bot configuration
4. Add ElevenLabs blocks to contact flows
5. Integration via Invoke Lambda or Lex Bot blocks
6. Real-time streaming with Chime SDK
7. Multi-region failover setup
8. Troubleshooting and performance tuning

**Typical Use Case**: "Add ElevenLabs voice to my IRS contact flow"

**Key Functions**:
```python
synthesize_with_elevenlabs(text, voice_id)    # TTS in Lex
upload_to_s3(audio_bytes)                     # Persist audio
stream_to_chime(text, voice_id)               # WebRTC streaming
setup_regional_failover(primary, secondary)   # High availability
```

---

## Usage Patterns

### Pattern 1: Ask the Main Agent
```
User: "Set up ElevenLabs for my Connect instance"

Agent Response:
  ISSUES: API key missing, Secrets Manager empty, Lex bot not configured
  ACTIONS:
    1. Create Secrets Manager secret with elevenlabs-api-setup skill
    2. Deploy Lex Lambda handler with elevenlabs-voice-synthesis skill
    3. Update contact flow with elevenlabs-connect-integration skill
  OUTCOMES:
    ✅ API authenticated
    ✅ Voices available (50+ models)
    ✅ Contact flow testing passed
```

### Pattern 2: Delegate to Specialized Skill
```
User: "I already have the API key set up. Just synthesize a greeting message."

Agent: Delegates to elevenlabs-voice-synthesis skill
Response: Generates audio file with cost breakdown and latency metrics
```

### Pattern 3: Deep Integration
```
User: "Integrate ElevenLabs with my IRS contact flow, handle multi-language"

Agent: Orchestrates full workflow
  1. Validates existing API setup (elevenlabs-api-setup)
  2. Configures multilingual models (elevenlabs-voice-synthesis)
  3. Deploys Lambda + Lex + contact flow updates (elevenlabs-connect-integration)
```

---

## File Structure

```
.github/
├── agents/
│   └── elevenlabs-orchestrator.agent.md       # Main entry point
└── skills/
    ├── elevenlabs-api-setup/
    │   └── SKILL.md                           # API & auth
    ├── elevenlabs-voice-synthesis/
    │   └── SKILL.md                           # TTS & synthesis
    └── elevenlabs-connect-integration/
        └── SKILL.md                           # Connect integration
```

---

## Quick Access (Type in Chat)

1. **Full Orchestration**: "Set up ElevenLabs for Amazon Connect"
2. **API Setup Only**: `/elevenlabs-api-setup`
3. **Voice Synthesis**: `/elevenlabs-voice-synthesis`
4. **Connect Integration**: `/elevenlabs-connect-integration`

---

## Environment Variables (Lambda)

```bash
# Required for all operations
ELEVENLABS_API_KEY=xxxx_xxxx_xxxx_xxxx
ELEVENLABS_SECRET_NAME=elevenlabs-api
AWS_REGION=us-east-1

# For voice synthesis
ELEVENLABS_VOICE_ID=21m00Tcm4TlvDq8ikWAM
ELEVENLABS_MODEL=eleven_turbo_v2

# For Connect integration
ELEVENLABS_AUDIO_BUCKET=my-audio-bucket
ELEVENLABS_LOGLEVEL=INFO
```

---

## Security Checklist

✅ API keys ONLY in Secrets Manager (KMS encrypted)  
✅ Lambda IAM roles restricted to minimal permissions  
✅ S3 audio bucket uses signed URLs (time-limited)  
✅ Audit trail enabled via CloudTrail  
✅ Rotation policy configured  
✅ Contact flows sanitize user input (no prompt injection)  

---

## Cost Estimation (Annual)

| Volume | Monthly Cost | Annual Cost |
|--------|--------------|-------------|
| 100K calls (small) | ~$150 | ~$1,800 |
| 1M calls (medium) | ~$1,500 | ~$18,000 |
| 10M calls (large) | ~$15,000 | ~$180,000 |

---

## Troubleshooting

| Problem | First Check | Escalation |
|---------|-------------|------------|
| "API key not working" | Verify key at https://elevenlabs.io/app/settings/api-keys | Contact ElevenLabs support |
| "Audio quality poor" | Switch to `eleven_turbo_v2` or `eleven_multilingual_v2` | Review voice ID, test sample |
| "Lambda timeout" | Use streaming instead of full synthesis | Increase timeout, enable caching |
| "Contact flow not playing audio" | Check S3 URL validity and IAM permissions | Validate flow syntax, test manually |

---

## Next Steps

1. **Try the agent**: "Set up ElevenLabs for my Amazon Connect instance"
2. **Review one skill**: Start with API setup, then voice synthesis, then integration
3. **Deploy to production**: Follow the Contact Flow Integration skill checklist
4. **Monitor costs**: Set budget alerts in AWS Cost Explorer

---

**Created**: March 19, 2026  
**Agent**: ElevenLabs Orchestrator  
**Status**: Ready for production use
