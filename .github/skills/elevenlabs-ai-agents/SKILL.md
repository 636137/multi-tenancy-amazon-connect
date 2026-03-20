# ElevenLabs AI Agents Skill

Create, configure, and deploy autonomous AI agents powered by ElevenLabs with custom personalities, conversation logic, knowledge integration, and Amazon Connect orchestration.

## ⚠️ CRITICAL: Correct API Endpoints

**The correct base path is `/v1/convai/` NOT `/v1/`!**

| Endpoint | Path | Method |
|----------|------|--------|
| List agents | `/v1/convai/agents` | GET |
| Create agent | `/v1/convai/agents/create` | POST |
| Get agent | `/v1/convai/agents/{agent_id}` | GET |
| Update agent | `/v1/convai/agents/{agent_id}` | PUT |
| Delete agent | `/v1/convai/agents/{agent_id}` | DELETE |

## Quick Start

| Task | Command |
|------|---------|
| Create AI Agent | `python create_agent.py --name "Customer Support" --model "advanced"` |
| Define conversation rules | `python configure_agent.py --agent-id xxx --knowledge-base docs/ --intents intents.json` |
| Test agent conversations | `python test_agent.py --agent-id xxx --script test_calls.json` |
| Deploy to Contact Center | `python deploy_agent.py --agent-id xxx --connect-instance connect-prod` |
| Monitor agent performance | `python monitor_agent.py --agent-id xxx --metrics ctr,escalation,sentiment` |

---

## Available LLM Models

| Model | Provider | Speed | Use Case |
|-------|----------|-------|----------|
| `gemini-2.0-flash-001` | Google | Fast | General support, quick responses |
| `gemini-2.5-flash` | Google | Fast | Latest, improved reasoning |
| `gpt-4o` | OpenAI | Medium | Complex conversations |
| `claude-3-sonnet` | Anthropic | Medium | Nuanced responses |

**Recommendation**: Start with `gemini-2.0-flash-001` for speed, upgrade to `gpt-4o` for complex reasoning.

---

## Workflow 1: Create an AI Agent

### Step 1: Define Agent Profile

```python
import requests
import json
import os

def create_elevenlabs_agent(
    name: str,
    first_message: str,
    system_prompt: str,
    voice_id: str = "EXAVITQu4vr4xnSDxMaL",  # Sarah
    llm: str = "gemini-2.0-flash-001",
    api_key: str = None
) -> dict:
    """Create a new ElevenLabs Conversational AI Agent.
    
    IMPORTANT: Use /v1/convai/agents/create endpoint!
    
    Args:
        name: Agent name (e.g., "Customer Support Bot")
        first_message: What agent says when conversation starts
        system_prompt: Instructions for agent behavior
        voice_id: ElevenLabs voice ID
        llm: Language model to use
        api_key: ElevenLabs API key
    
    Returns:
        Agent configuration with agent_id
    """
    api_key = api_key or os.environ.get("ELEVENLABS_API_KEY")
    
    # CORRECT endpoint - /v1/convai/agents/create
    url = "https://api.elevenlabs.io/v1/convai/agents/create"
    headers = {
        "xi-api-key": api_key,
        "Content-Type": "application/json"
    }
    
    # CORRECT payload structure for ElevenLabs Conversational AI
    payload = {
        "name": name,
        "tags": ["support", "ai-agent"],
        "conversation_config": {
            "agent": {
                "first_message": first_message,
                "language": "en",
                "prompt": {
                    "prompt": system_prompt,
                    "llm": llm,
                    "temperature": 0.3,
                    "max_tokens": 500
                }
            },
            "tts": {
                "voice_id": voice_id,
                "model_id": "eleven_turbo_v2",
                "stability": 0.5,
                "similarity_boost": 0.75,
                "optimize_streaming_latency": 3
            },
            "turn": {
                "turn_timeout": 10,
                "silence_end_call_timeout": 30,
                "turn_eagerness": "normal"
            },
            "conversation": {
                "max_duration_seconds": 600,
                "text_only": False
            }
        }
    }
    
    response = requests.post(url, json=payload, headers=headers)
    response.raise_for_status()
    
    agent = response.json()
    print(f"✅ Agent created: {agent['agent_id']}")
    print(f"   Name: {name}")
    
    return agent

# Usage - CORRECT structure
agent = create_elevenlabs_agent(
    name="IRS Taxpayer Assistant",
    first_message="Hello! I'm the IRS Taxpayer Assistant. How can I help you today?",
    system_prompt="You are a professional, patient IRS assistant. Help with refund status, payment plans, and tax questions.",
    voice_id="EXAVITQu4vr4xnSDxMaL",  # Sarah
    llm="gemini-2.0-flash-001"
)
agent_id = agent["agent_id"]
```

### Step 2: List and Get Agents

```python
def list_agents(api_key: str = None) -> list:
    """List all conversational AI agents."""
    api_key = api_key or os.environ.get("ELEVENLABS_API_KEY")
    
    url = "https://api.elevenlabs.io/v1/convai/agents"
    headers = {"xi-api-key": api_key}
    
    response = requests.get(url, headers=headers)
    response.raise_for_status()
    
    data = response.json()
    return data.get("agents", [])

def get_agent(agent_id: str, api_key: str = None) -> dict:
    """Get agent configuration by ID."""
    api_key = api_key or os.environ.get("ELEVENLABS_API_KEY")
    
    url = f"https://api.elevenlabs.io/v1/convai/agents/{agent_id}"
    headers = {"xi-api-key": api_key}
    
    response = requests.get(url, headers=headers)
    response.raise_for_status()
    
    return response.json()
```

### Step 3: Configure Agent Voice

```python
def configure_agent_voice(
    agent_id: str,
    voice_id: str,
    api_key: str,
    model: str = "eleven_turbo_v2",
    stability: float = 0.5,
    similarity_boost: float = 0.75
) -> dict:
    """Configure voice settings for the AI Agent."""
    
    url = f"https://api.elevenlabs.io/v1/agents/{agent_id}/voice"
    headers = {
        "xi-api-key": api_key,
        "Content-Type": "application/json"
    }
    
    payload = {
        "voice_id": voice_id,
        "tts_model": model,
        "voice_settings": {
            "stability": stability,
            "similarity_boost": similarity_boost
        }
    }
    
    response = requests.post(url, json=payload, headers=headers)
    response.raise_for_status()
    
    print(f"✅ Voice configured for agent {agent_id}")
    return response.json()

# Usage
configure_agent_voice(
    agent_id=agent_id,
    voice_id="21m00Tcm4TlvDq8ikWAM",  # Professional female voice
    api_key=api_key
)
```

---

## Workflow 2: Define Conversation Rules & Intents

### Step 1: Create Intent Definitions

```json
{
  "intents": [
    {
      "intent_id": "refund_status",
      "name": "Check Refund Status",
      "description": "Customer wants to know refund status",
      "trigger_phrases": [
        "Where is my refund?",
        "When will I get my refund?",
        "What's the status of my return?",
        "How long does a refund take?"
      ],
      "agent_response": {
        "type": "knowledge_lookup",
        "knowledge_base": "irs_refund_faq",
        "fields_needed": ["refund_status", "timeline", "next_steps"],
        "escalate_if": "agent_confidence < 0.6"
      },
      "followup_intents": ["account_verification", "payment_method"],
      "can_be_handled_by": ["agent_level_1", "agent_level_2"]
    },
    {
      "intent_id": "payment_plan",
      "name": "Setup Payment Plan",
      "description": "Customer wants to set up a payment arrangement",
      "trigger_phrases": [
        "Can I set up a payment plan?",
        "I can't pay in full",
        "What are my payment options?"
      ],
      "agent_response": {
        "type": "api_call",
        "api_endpoint": "https://irs-api.internal/payment-plans",
        "required_fields": ["amount_owed", "monthly_income"],
        "confirmation_required": True
      },
      "escalate_threshold": 0.5,  # Escalate if confidence < 50%
      "human_handoff_message": "I'm connecting you with a tax specialist..."
    },
    {
      "intent_id": "identity_verification_failure",
      "name": "Failed Identity Verification",
      "description": "Customer failed identity verification (critical: escalate to human)",
      "trigger_phrases": ["identity_check_failed"],
      "agent_response": {
        "type": "escalate_immediate",
        "queue": "human_verification_queue",
        "message": "For security, I'm connecting you with an agent to verify your identity."
      },
      "always_escalate": True
    }
  ],
  "conversation_rules": {
    "max_turns": 10,                      # Max back-and-forth exchanges
    "timeout_seconds": 300,               # Escalate if no response in 5 min
    "confirmation_required_for": [        # Always confirm these actions
      "collecting_payment",
      "modifying_account",
      "escalation_decision"
    ],
    "prohibited_topics": [
      "legal_advice",
      "medical_advice",
      "investment_advice"
    ]
  }
}
```

### Step 2: Upload Knowledge Base

```python
def upload_knowledge_base(
    agent_id: str,
    knowledge_base_name: str,
    documents: list,  # List of {"title": "...", "content": "...", "url": "..."}
    api_key: str
) -> dict:
    """Upload knowledge base documents for agent to reference."""
    
    url = f"https://api.elevenlabs.io/v1/agents/{agent_id}/knowledge-base"
    headers = {
        "xi-api-key": api_key,
        "Content-Type": "application/json"
    }
    
    payload = {
        "name": knowledge_base_name,
        "documents": documents,
        "retrieval_mode": "semantic",  # or "keyword", "hybrid"
        "max_context_tokens": 2000,    # How much context to provide agent
        "confidence_threshold": 0.7    # Only use if confident
    }
    
    response = requests.post(url, json=payload, headers=headers)
    response.raise_for_status()
    
    kb = response.json()
    print(f"✅ Knowledge base uploaded: {kb['kb_id']}")
    print(f"   Documents: {len(documents)}")
    print(f"   Indexed: {kb.get('indexed_documents', 0)}")
    
    return kb

# Usage
kb_docs = [
    {
        "title": "Refund Processing Times",
        "content": "E-filed returns: 21 days. Paper returns: 6-8 weeks...",
        "url": "https://irs.gov/refunds"
    },
    {
        "title": "Payment Plan Options",
        "content": "Monthly installments, minimum $25/month...",
        "url": "https://irs.gov/payment-plans"
    }
]

upload_knowledge_base(
    agent_id=agent_id,
    knowledge_base_name="IRS FAQs",
    documents=kb_docs,
    api_key=api_key
)
```

### Step 3: Configure Escalation Logic

```python
def set_escalation_triggers(
    agent_id: str,
    api_key: str
) -> dict:
    """Define when and how agent escalates to humans."""
    
    url = f"https://api.elevenlabs.io/v1/agents/{agent_id}/escalation"
    headers = {
        "xi-api-key": api_key,
        "Content-Type": "application/json"
    }
    
    payload = {
        "escalation_rules": [
            {
                "trigger": "max_failed_attempts",
                "threshold": 3,
                "queue": "tier_2_support",
                "message": "Let me connect you with a specialist..."
            },
            {
                "trigger": "confidence_below",
                "threshold": 0.5,
                "queue": "tier_1_support",
                "message": "I'm not sure about that. Let me get someone to help..."
            },
            {
                "trigger": "intent_requires_human",
                "intents": ["identity_verification_failed", "legal_question", "fraud_report"],
                "queue": "priority_queue",
                "message": "For security, please hold while I get someone..."
            },
            {
                "trigger": "sentiment_negative",
                "threshold": -0.7,  # Very negative sentiment
                "queue": "retention_team",
                "message": "I understand this is frustrating. Let me get my manager..."
            }
        ],
        "timeout_seconds": 300,
        "fallback_queue": "level_2_support"
    }
    
    response = requests.post(url, json=payload, headers=headers)
    response.raise_for_status()
    
    print(f"✅ Escalation rules configured")
    return response.json()

# Usage
set_escalation_triggers(agent_id=agent_id, api_key=api_key)
```

---

## Workflow 3: Test Agent Conversations

```python
def test_agent_conversation(
    agent_id: str,
    api_key: str,
    test_script: list  # [{"user_input": "...", "expected_intent": "..."}, ...]
) -> dict:
    """Run conversation tests against agent."""
    
    url = f"https://api.elevenlabs.io/v1/agents/{agent_id}/test"
    headers = {
        "xi-api-key": api_key,
        "Content-Type": "application/json"
    }
    
    payload = {
        "test_cases": test_script,
        "validate_intents": True,
        "measure_latency": True,
        "capture_sentiment": True
    }
    
    response = requests.post(url, json=payload, headers=headers)
    response.raise_for_status()
    
    results = response.json()
    
    # Print results
    print(f"Test Results for Agent {agent_id}:")
    print(f"  Success Rate: {results['success_rate']:.1%}")
    print(f"  Avg Latency: {results['avg_latency_ms']:.0f}ms")
    print(f"  Intent Accuracy: {results['intent_accuracy']:.1%}")
    print(f"  Failed Tests: {len(results['failures'])}")
    
    if results['failures']:
        print("\n  Failures:")
        for failure in results['failures'][:3]:
            print(f"    - {failure['input']}: {failure['reason']}")
    
    return results

# Usage
test_cases = [
    {"user_input": "Where is my refund?", "expected_intent": "refund_status"},
    {"user_input": "I need a payment plan", "expected_intent": "payment_plan"},
    {"user_input": "Verify my identity", "expected_intent": "identity_verification"},
    {"user_input": "This is unfair!", "expected_intent": "complaint"}
]

test_results = test_agent_conversation(
    agent_id=agent_id,
    api_key=api_key,
    test_script=test_cases
)
```

---

## Workflow 4: Monitor Agent Performance

```python
def get_agent_analytics(
    agent_id: str,
    api_key: str,
    start_date: str = None,
    end_date: str = None,
    metrics: list = None
) -> dict:
    """Retrieve agent performance metrics."""
    
    if not metrics:
        metrics = ["conversation_count", "avg_duration", "escalation_rate", 
                   "success_rate", "sentiment", "intent_distribution"]
    
    url = f"https://api.elevenlabs.io/v1/agents/{agent_id}/analytics"
    headers = {"xi-api-key": api_key}
    
    params = {
        "metrics": ",".join(metrics),
        "start_date": start_date or "2024-01-01",
        "end_date": end_date or "2024-03-31"
    }
    
    response = requests.get(url, headers=headers, params=params)
    response.raise_for_status()
    
    analytics = response.json()
    
    # Print summary
    print(f"Analytics for Agent {agent_id}:")
    print(f"\n  Conversations: {analytics['conversation_count']}")
    print(f"  Avg Duration: {analytics['avg_duration_minutes']:.1f} minutes")
    print(f"  Success Rate: {analytics['success_rate']:.1%}")
    print(f"  Escalation Rate: {analytics['escalation_rate']:.1%}")
    print(f"  Avg Sentiment: {analytics['avg_sentiment']:.2f} (-1 to +1)")
    
    print(f"\n  Top Intents:")
    for intent, count in sorted(
        analytics['intent_distribution'].items(),
        key=lambda x: x[1],
        reverse=True
    )[:5]:
        print(f"    - {intent}: {count} ({count/analytics['conversation_count']*100:.0f}%)")
    
    return analytics

# Usage
analytics = get_agent_analytics(
    agent_id=agent_id,
    api_key=api_key,
    metrics=["conversation_count", "success_rate", "escalation_rate", "intent_distribution"]
)
```

---

## Workflow 5: Deploy Agent to Production

```python
def deploy_agent_to_production(
    agent_id: str,
    environment: str = "production",
    api_key: str = None,
    canary_percentage: int = 10  # Start with 10% of traffic
) -> dict:
    """Deploy agent with traffic gradual rollout (canary deployment)."""
    
    api_key = api_key or os.environ.get("ELEVENLABS_API_KEY")
    
    url = f"https://api.elevenlabs.io/v1/agents/{agent_id}/deploy"
    headers = {
        "xi-api-key": api_key,
        "Content-Type": "application/json"
    }
    
    payload = {
        "environment": environment,
        "canary": {
            "enabled": True,
            "percentage": canary_percentage,
            "duration_minutes": 60,
            "metrics_to_monitor": ["error_rate", "latency_p99", "escalation_rate"],
            "auto_rollback_threshold": {
                "error_rate": 0.05,      # Rollback if > 5% errors
                "escalation_rate": 0.30  # Rollback if > 30% escalations
            }
        },
        "pre_deployment_checks": [
            "knowledge_base_health",
            "intent_coverage",
            "escalation_rules_validity"
        ]
    }
    
    response = requests.post(url, json=payload, headers=headers)
    response.raise_for_status()
    
    deployment = response.json()
    print(f"✅ Agent deployment started")
    print(f"   Deployment ID: {deployment['deployment_id']}")
    print(f"   Canary: {canary_percentage}% of traffic")
    print(f"   Status: {deployment['status']}")
    print(f"   ETA: {deployment.get('estimated_completion', 'N/A')}")
    
    return deployment

# Usage
deploy_agent_to_production(
    agent_id=agent_id,
    environment="production",
    api_key=api_key,
    canary_percentage=20
)
```

---

## Agent Configuration Best Practices

### Voice Selection for Agents

| Use Case | Recommended Voice | Stability | Similarity Boost |
|----------|-------------------|-----------|------------------|
| Customer Support | Amy (professional) | 0.6 | 0.75 |
| Friendly Greeting | Jake (warm) | 0.5 | 0.70 |
| Legal/Finance | Onyx (authoritative) | 0.8 | 0.85 |
| Empathetic Support | Grace (caring) | 0.5 | 0.75 |

### Conversation Tuning Parameters

```python
agent_config = {
    "response_length": {
        "min_chars": 50,
        "max_chars": 500,
        "target": 200
    },
    "confidence_threshold": {
        "proceed_if_confidence_above": 0.65,
        "escalate_if_below": 0.50,
        "retry_if_below": 0.55
    },
    "context_window": {
        "max_turns_to_remember": 10,
        "max_context_tokens": 2000,
        "include_sentiment_history": True
    },
    "error_handling": {
        "max_retries": 2,
        "fallback_response": "Let me connect you with someone who can help...",
        "error_escalation": True
    }
}
```

---

## Agent Safety Guardrails

✅ **Input Validation**: Filter offensive/harmful content before processing  
✅ **Output Filtering**: Prevent PII leakage, verify completeness  
✅ **Rate Limiting**: Max 100 requests/minute per agent  
✅ **Escalation**: Critical issues → immediate human handoff  
✅ **Audit Trail**: Log all conversations for compliance  
✅ **Sentiment Monitoring**: Track conversation tone, escalate if negative  
✅ **Timeout Protection**: Auto-escalate if no response > 5 minutes  

---

## Cost Estimation (Monthly)

| Metric | Cost |
|--------|------|
| Agent creation/update | Free |
| Conversation inference (per call) | ~$0.10–0.20 |
| TTS synthesis (included in inference) | Included |
| Knowledge base retrieval | ~$0.01–0.05 per query |
| Escalation tracking | Free |
| Analytics & monitoring | Free |

**Example**: 10K calls/month = ~$1,500 (agent) + variable TTS costs

---

## Troubleshooting

| Issue | Solution |
|-------|----------|
| "Agent misunderstands intent" | Review knowledge base, add trigger phrases, test with similar inputs |
| "High escalation rate" | Lower confidence threshold, improve knowledge base, add new intents |
| "Latency > 2s" | Use streaming TTS, reduce context window, optimize knowledge base queries |
| "Agent loops" | Set max_turns limit, improve escalation triggers, test conversation paths |
| "PII leakage" | Enable output filtering, audit logs, add redaction rules |

---

## Integration with Amazon Connect

See **elevenlabs-connect-integration** skill for:
- Deploying agents to Contact Flows
- Handling real-time transcription
- Managing handoffs to human agents
- Monitoring conversation metrics
