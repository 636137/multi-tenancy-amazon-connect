---
name: testing-automation
description: Generate and execute automated tests for AWS infrastructure, Lambda functions, Lex bots, and contact flows. Use for unit tests, integration tests, E2E validation, and regression testing.
argument-hint: "[component] [test-type]"
user-invocable: true
disable-model-invocation: false
---

# Testing Automation Skill

Generate and execute comprehensive automated tests for AWS infrastructure, Lambda functions, Lex bots, and contact flows.

## When to Use This Skill

- Creating unit tests for Lambda functions
- Building integration tests for AWS resources
- E2E testing of contact center flows
- Regression testing after deployments
- Load testing and performance validation
- Validating Lex bot intent recognition

## Testing Hierarchy

```
Unit Tests (Fast, Isolated)
    │
    ├── Lambda handler logic
    ├── Utility functions
    └── Data transformations
    │
Integration Tests (AWS Services)
    │
    ├── DynamoDB operations
    ├── Lex bot configurations
    ├── Lambda invocations
    └── IAM permissions
    │
E2E Tests (Complete Flows)
    │
    ├── Contact flow execution
    ├── Bot conversations
    └── Full call simulations
```

## Lambda Unit Testing

### Test Structure
```python
# tests/test_lambda_handler.py
import pytest
import json
from unittest.mock import Mock, patch
from lambda.survey.survey_handler import handler

class TestSurveyHandler:
    """Unit tests for survey Lambda handler."""

    def test_valid_survey_response(self):
        """Test processing a valid survey response."""
        event = {
            "sessionAttributes": {},
            "inputTranscript": "yes",
            "interpretations": [
                {"intent": {"name": "ConfirmIntent", "slots": {}}}
            ]
        }
        context = Mock()

        result = handler(event, context)

        assert result["sessionState"]["dialogAction"]["type"] == "Close"
        assert "fulfillmentState" in result["sessionState"]["dialogAction"]

    def test_missing_input_transcript(self):
        """Test handling missing input."""
        event = {"sessionAttributes": {}}
        context = Mock()

        with pytest.raises(KeyError):
            handler(event, context)

    @patch('boto3.client')
    def test_dynamodb_interaction(self, mock_boto):
        """Test DynamoDB is called correctly."""
        mock_dynamo = Mock()
        mock_boto.return_value = mock_dynamo

        event = create_test_event()
        handler(event, Mock())

        mock_dynamo.put_item.assert_called_once()
```

### pytest Configuration
```ini
# pytest.ini
[pytest]
testpaths = tests
python_files = test_*.py
python_functions = test_*
addopts = -v --tb=short --strict-markers
markers =
    unit: Unit tests (fast, isolated)
    integration: Integration tests (requires AWS)
    e2e: End-to-end tests (full system)
    slow: Slow running tests
```

## Lex Bot Testing

### Intent Testing
```python
# tests/test_lex_bot.py
import boto3
import pytest

class TestLexBot:
    """Integration tests for Lex bot."""

    @pytest.fixture
    def lex_client(self):
        return boto3.client('lexv2-runtime', region_name='us-east-1')

    @pytest.fixture
    def bot_config(self):
        return {
            "botId": "YOUR_BOT_ID",
            "botAliasId": "TSTALIASID",
            "localeId": "en_US",
            "sessionId": "test-session-001"
        }

    def test_greeting_intent(self, lex_client, bot_config):
        """Test that 'hello' triggers greeting intent."""
        response = lex_client.recognize_text(
            **bot_config,
            text="Hello"
        )

        intent = response['sessionState']['intent']['name']
        assert intent == "GreetingIntent"

    def test_survey_intent_with_slots(self, lex_client, bot_config):
        """Test survey intent captures slots correctly."""
        response = lex_client.recognize_text(
            **bot_config,
            text="I'd like to take the survey"
        )

        assert response['sessionState']['intent']['name'] == "TakeSurveyIntent"

    def test_fallback_handling(self, lex_client, bot_config):
        """Test unrecognized input triggers fallback."""
        response = lex_client.recognize_text(
            **bot_config,
            text="asdfghjkl random gibberish"
        )

        intent = response['sessionState']['intent']['name']
        assert intent == "FallbackIntent"
```

## Contact Flow Testing

### Flow Validation
```python
# tests/test_contact_flows.py
import json
import pytest
from pathlib import Path

class TestContactFlows:
    """Validate contact flow JSON structure."""

    @pytest.fixture
    def flow_files(self):
        return list(Path("contact_flows").glob("*.json"))

    def test_all_flows_valid_json(self, flow_files):
        """All contact flows must be valid JSON."""
        for flow_file in flow_files:
            with open(flow_file) as f:
                flow = json.load(f)
            assert "Actions" in flow
            assert "StartAction" in flow

    def test_no_broken_references(self, flow_files):
        """All action references must exist."""
        for flow_file in flow_files:
            with open(flow_file) as f:
                flow = json.load(f)

            action_ids = {a["Identifier"] for a in flow["Actions"]}

            for action in flow["Actions"]:
                for transition in action.get("Transitions", {}).values():
                    if isinstance(transition, dict):
                        next_action = transition.get("NextAction")
                        if next_action:
                            assert next_action in action_ids, \
                                f"Broken reference: {next_action}"

    def test_lambda_arns_valid(self, flow_files):
        """Lambda ARNs must have correct format."""
        import re
        arn_pattern = r'arn:aws:lambda:[a-z0-9-]+:\d{12}:function:.+'

        for flow_file in flow_files:
            with open(flow_file) as f:
                content = f.read()

            arns = re.findall(r'arn:aws:lambda[^"]+', content)
            for arn in arns:
                assert re.match(arn_pattern, arn), f"Invalid ARN: {arn}"
```

## Running Tests

### Commands
```bash
# Run all tests
pytest

# Run only unit tests
pytest -m unit

# Run with coverage
pytest --cov=lambda --cov-report=html

# Run specific test file
pytest tests/test_lex_bot.py

# Run tests matching pattern
pytest -k "test_greeting"

# Run in parallel
pytest -n auto

# Verbose output
pytest -v --tb=long
```

### CI/CD Integration
```yaml
# .github/workflows/test.yml
name: Tests

on: [push, pull_request]

jobs:
  test:
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v4

      - name: Set up Python
        uses: actions/setup-python@v5
        with:
          python-version: '3.12'

      - name: Install dependencies
        run: |
          pip install -r requirements.txt
          pip install pytest pytest-cov pytest-xdist

      - name: Run unit tests
        run: pytest -m unit --cov --cov-report=xml

      - name: Run integration tests
        if: github.event_name == 'push'
        env:
          AWS_ACCESS_KEY_ID: ${{ secrets.AWS_ACCESS_KEY_ID }}
          AWS_SECRET_ACCESS_KEY: ${{ secrets.AWS_SECRET_ACCESS_KEY }}
        run: pytest -m integration
```

## Test Data Fixtures

### Creating Test Events
```python
# tests/fixtures.py
import json

def create_lex_event(intent_name: str, slots: dict = None, text: str = ""):
    """Create a mock Lex event for testing."""
    return {
        "sessionId": "test-session",
        "inputTranscript": text,
        "interpretations": [
            {
                "intent": {
                    "name": intent_name,
                    "slots": slots or {},
                    "state": "InProgress"
                },
                "nluConfidence": {"score": 0.95}
            }
        ],
        "sessionState": {
            "intent": {"name": intent_name, "slots": slots or {}},
            "sessionAttributes": {}
        }
    }

def create_connect_event(contact_id: str = "test-contact"):
    """Create a mock Connect event."""
    return {
        "Details": {
            "ContactData": {
                "ContactId": contact_id,
                "Channel": "VOICE",
                "CustomerEndpoint": {"Address": "+15551234567"}
            },
            "Parameters": {}
        }
    }
```

## Mocking AWS Services

### Using moto
```python
import pytest
import boto3
from moto import mock_aws

@pytest.fixture
def dynamodb_table():
    """Create a mock DynamoDB table."""
    with mock_aws():
        dynamodb = boto3.resource('dynamodb', region_name='us-east-1')
        table = dynamodb.create_table(
            TableName='TestTable',
            KeySchema=[{'AttributeName': 'pk', 'KeyType': 'HASH'}],
            AttributeDefinitions=[{'AttributeName': 'pk', 'AttributeType': 'S'}],
            BillingMode='PAY_PER_REQUEST'
        )
        yield table

def test_write_to_dynamodb(dynamodb_table):
    """Test writing to DynamoDB."""
    dynamodb_table.put_item(Item={'pk': 'test-1', 'data': 'value'})
    response = dynamodb_table.get_item(Key={'pk': 'test-1'})
    assert response['Item']['data'] == 'value'
```

## Test Coverage Goals

| Component | Target Coverage |
|-----------|-----------------|
| Lambda handlers | 80%+ |
| Utility functions | 90%+ |
| Lex intent recognition | All intents tested |
| Contact flows | All paths validated |
| Error handling | All exception types |

## Best Practices

1. **Isolate unit tests** - Mock all external dependencies
2. **Use fixtures** - Share test setup across tests
3. **Test edge cases** - Empty inputs, max inputs, special characters
4. **Test error paths** - Ensure graceful failure
5. **Name tests descriptively** - `test_greeting_intent_returns_welcome_message`
6. **Keep tests fast** - Unit tests should run in milliseconds
7. **Run tests before commit** - Catch issues early
8. **Review coverage gaps** - Focus on critical paths
