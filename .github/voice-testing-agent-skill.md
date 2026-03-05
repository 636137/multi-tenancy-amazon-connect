# AI Voice Testing Agent Skill

## Purpose

A GitHub Copilot agent skill for creating and executing real voice call tests against Amazon Connect contact centers. This agent can make actual phone calls using AWS services, interact with IVR systems and Lex bots as an AI-powered caller, and validate the conversation flow.

## When to Use This Agent

- Testing Amazon Connect contact flows
- Validating Lex bot conversations
- Regression testing after IVR changes
- Load testing with multiple concurrent callers
- Testing error handling and edge cases
- Validating multi-language support

## Architecture Overview

```
User describes test → Agent creates scenario YAML → Deploy infrastructure → 
Agent makes real call → AI responds to prompts → Evaluate results → Report
```

### AWS Services Used

| Service | Purpose |
|---------|---------|
| Amazon Chime SDK PSTN | Makes outbound phone calls |
| Amazon Transcribe | Real-time speech-to-text |
| Amazon Polly | Text-to-speech for AI responses |
| Amazon Bedrock (Claude) | AI brain for intelligent responses |
| AWS Lambda | Call handling and orchestration |
| DynamoDB | Test state and results |
| S3 | Call recordings |

## Creating Test Scenarios

### Scenario Schema

```yaml
name: "Test Name"
version: "1.0.0"
description: "What this test validates"

target:
  phone_number: "+15551234567"  # The Connect number to call
  timeout_seconds: 180
  recording:
    enabled: true
    format: "wav"

persona:
  name: "Caller Type"
  attributes:
    speaking_rate: "normal"  # slow, normal, fast
    patience: "patient"      # impatient, normal, patient
    clarity: "clear"         # mumbling, clear
  background: |
    Describe who the caller is and how they should behave.
    Include any specific information they should "know" for the test.
  behaviors:
    asks_clarification: false
    interrupts: false
    makes_mistakes: false

steps:
  - id: "step_name"
    description: "What this step does"
    action: "listen"  # listen, speak, dtmf, wait, hangup
    expect:
      patterns:
        - "regex pattern to match"
        - "another pattern"
      timeout_seconds: 15
    content:  # For speak actions
      type: "literal"  # literal, ai_generated
      text: "What to say"
      # OR for AI:
      # type: "ai_generated"
      # intent: "What the AI should try to accomplish"

success_criteria:
  required:
    - step: "step_name"
      status: "completed"

assertions:
  - type: "transcript_contains"
    patterns: ["expected words"]
    all_required: true
  - type: "transcript_excludes"
    patterns: ["error", "sorry"]
  - type: "duration"
    min_seconds: 30
    max_seconds: 180
```

### Step Actions

| Action | Description |
|--------|-------------|
| `listen` | Wait for system to speak, match against patterns |
| `speak` | Say something (literal text or AI-generated) |
| `dtmf` | Send touch-tone digits |
| `wait` | Pause for specified duration |
| `hangup` | End the call |

### Content Types

| Type | Description |
|------|-------------|
| `literal` | Exact text to speak |
| `ai_generated` | AI generates response based on intent |
| `random_choice` | Pick randomly from list of options |

## Example Scenarios

### Happy Path Test

```yaml
name: "Support Line - Happy Path"
target:
  phone_number: "+15551234567"

persona:
  name: "Standard Customer"
  background: "You are a customer calling to check your account balance."

steps:
  - id: "greeting"
    action: "listen"
    expect:
      patterns: ["welcome", "thank you for calling"]
  
  - id: "respond"
    action: "speak"
    content:
      type: "literal"
      text: "Hi, I'd like to check my account balance"
  
  - id: "wait_options"
    action: "listen"
    expect:
      patterns: ["account number", "social security", "verify"]
  
  - id: "provide_id"
    action: "speak"
    content:
      type: "literal"
      text: "My account number is 12345"
  
  - id: "confirm_balance"
    action: "listen"
    expect:
      patterns: ["balance", "dollars", "$"]

success_criteria:
  required:
    - step: "confirm_balance"
      status: "completed"
```

### Error Handling Test

```yaml
name: "Support Line - Invalid Input"
target:
  phone_number: "+15551234567"

persona:
  name: "Confused Caller"
  background: "Give invalid inputs to test error handling"
  behaviors:
    makes_mistakes: true

steps:
  - id: "greeting"
    action: "listen"
    expect:
      patterns: ["welcome"]
  
  - id: "invalid_option"
    action: "speak"
    content:
      type: "literal"
      text: "Banana"  # Invalid response
  
  - id: "wait_retry"
    action: "listen"
    expect:
      patterns: ["sorry", "didn't understand", "repeat", "again"]
```

## Commands

```bash
# Run a test
python -m voice_tester test scenarios/my_test.yaml --target-number +15551234567

# Check status
python -m voice_tester status <test_id>

# Get results
python -m voice_tester results <test_id> --include-recording

# List tests
python -m voice_tester list --limit 10

# Validate scenario
python -m voice_tester validate scenarios/my_test.yaml

# Deploy infrastructure
python -m voice_tester deploy
```

## Persona Examples

### Cooperative Customer
```yaml
persona:
  name: "Cooperative Customer"
  attributes:
    speaking_rate: "normal"
    patience: "patient"
    clarity: "clear"
  background: |
    You are a helpful customer who provides clear, direct answers.
    You stay on topic and complete tasks efficiently.
```

### Impatient Caller
```yaml
persona:
  name: "Impatient Caller"
  attributes:
    speaking_rate: "fast"
    patience: "impatient"
    clarity: "clear"
  background: |
    You are in a hurry and can be interrupted. You may:
    - Ask to speak to a human
    - Express frustration with long menus
    - Try to interrupt prompts
  behaviors:
    interrupts: true
```

### Confused Elderly Caller
```yaml
persona:
  name: "Confused Elderly"
  attributes:
    speaking_rate: "slow"
    patience: "patient"
    clarity: "mumbling"
  background: |
    You are hard of hearing and sometimes confused. You may:
    - Ask for things to be repeated
    - Give wrong information then correct yourself
    - Take time to understand questions
  behaviors:
    asks_clarification: true
    makes_mistakes: true
    mistake_rate: 0.3
```

### Non-Native Speaker
```yaml
persona:
  name: "Non-Native Speaker"
  attributes:
    speaking_rate: "slow"
    patience: "patient"
    clarity: "accented"
  background: |
    English is your second language. You understand well but:
    - May pause to find the right words
    - Could use slightly unusual phrasing
    - Might ask for clarification on idioms
  behaviors:
    asks_clarification: true
```

## Tips for Writing Good Scenarios

1. **Be Specific with Patterns**: Use regex patterns that uniquely identify the expected prompt without being too restrictive.

2. **Handle Variations**: The system might say things slightly differently. Use alternation: `"press|say"`.

3. **Allow for Timing**: Give adequate timeouts. IVR systems can be slow.

4. **Test Error Recovery**: Include steps where wrong input is given to test how the system handles it.

5. **Use AI-Generated for Flexibility**: When exact responses aren't critical, use AI-generated content for more natural conversations.

6. **Start Simple**: Begin with happy path tests before adding edge cases.

## Infrastructure Deployment

### Prerequisites

1. AWS account with Chime SDK PSTN enabled (requires support ticket)
2. AWS credentials configured
3. CDK installed

### Deploy

```bash
cd voice_tester
pip install -r requirements.txt
cdk deploy VoiceTestStack
```

### Provision Phone Number

```bash
python -m voice_tester provision-number --area-code 202
```

### Configure Environment

After deployment, set these environment variables:

```bash
export CHIME_PHONE_NUMBER="+12025551234"
export SIP_MEDIA_APP_ID="abc123..."
export TEST_RESULTS_TABLE="VoiceTestResults"
# etc. - or add to .env file
```

## Cost Estimates

Per 2-minute test call:
- Chime PSTN: ~$0.01
- Transcribe: ~$0.07
- Polly: ~$0.01
- Bedrock: ~$0.02
- **Total: ~$0.11/test**

## Troubleshooting

### Common Issues

1. **"Chime SDK PSTN not enabled"**
   - Request enablement via AWS Support

2. **"No phone numbers available"**
   - Try different area codes
   - Some regions have limited availability

3. **"Call not connecting"**
   - Verify target number is correct
   - Check if target allows calls from unknown numbers

4. **"Transcription failing"**
   - Verify Transcribe permissions
   - Check audio format compatibility

5. **"AI responses not matching"**
   - Review persona configuration
   - Check if patterns are too restrictive

## Version History

- **1.0.0** - Initial release with Chime SDK PSTN support
