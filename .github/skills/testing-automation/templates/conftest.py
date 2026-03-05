"""
Shared pytest fixtures for AWS testing.

Place this file in your tests/ directory to make fixtures available
to all test files automatically.
"""

import os
import json
import pytest
from unittest.mock import MagicMock
import boto3
from moto import mock_aws


# =============================================================================
# AWS CREDENTIALS FIXTURES
# =============================================================================

@pytest.fixture(scope="session", autouse=True)
def aws_credentials():
    """
    Mock AWS credentials for moto.
    
    This fixture runs automatically for all tests and sets up
    fake credentials so moto can intercept AWS calls.
    """
    os.environ["AWS_ACCESS_KEY_ID"] = "testing"
    os.environ["AWS_SECRET_ACCESS_KEY"] = "testing"
    os.environ["AWS_SECURITY_TOKEN"] = "testing"
    os.environ["AWS_SESSION_TOKEN"] = "testing"
    os.environ["AWS_DEFAULT_REGION"] = "us-east-1"
    yield
    # Cleanup (optional)


# =============================================================================
# LAMBDA CONTEXT FIXTURES
# =============================================================================

@pytest.fixture
def lambda_context():
    """
    Mock AWS Lambda context object.
    
    Provides a properly structured context with common attributes
    that Lambda handlers expect.
    """
    context = MagicMock()
    context.function_name = "test-function"
    context.function_version = "$LATEST"
    context.memory_limit_in_mb = 128
    context.invoked_function_arn = (
        "arn:aws:lambda:us-east-1:123456789012:function:test-function"
    )
    context.aws_request_id = "test-request-id-12345"
    context.log_group_name = "/aws/lambda/test-function"
    context.log_stream_name = "2026/03/04/[$LATEST]abc123"
    context.get_remaining_time_in_millis.return_value = 30000  # 30 seconds
    return context


# =============================================================================
# EVENT FIXTURES
# =============================================================================

@pytest.fixture
def api_gateway_event():
    """API Gateway proxy integration event."""
    return {
        "resource": "/api/resource",
        "path": "/api/resource",
        "httpMethod": "POST",
        "headers": {
            "Content-Type": "application/json",
            "Accept": "application/json",
            "X-Amzn-Trace-Id": "Root=1-test-trace-id"
        },
        "multiValueHeaders": {},
        "queryStringParameters": None,
        "multiValueQueryStringParameters": None,
        "pathParameters": None,
        "stageVariables": None,
        "requestContext": {
            "resourceId": "abc123",
            "resourcePath": "/api/resource",
            "httpMethod": "POST",
            "requestId": "test-request-id",
            "accountId": "123456789012",
            "stage": "test",
            "identity": {
                "sourceIp": "127.0.0.1"
            }
        },
        "body": json.dumps({"key": "value"}),
        "isBase64Encoded": False
    }


@pytest.fixture
def lex_v2_event():
    """Amazon Lex V2 fulfillment event."""
    return {
        "messageVersion": "1.0",
        "invocationSource": "FulfillmentCodeHook",
        "inputMode": "Text",
        "responseContentType": "text/plain; charset=utf-8",
        "sessionId": "test-session-123",
        "inputTranscript": "test input",
        "bot": {
            "id": "TESTBOTID",
            "name": "TestBot",
            "aliasId": "TSTALIASID",
            "aliasName": "TestBotAlias",
            "localeId": "en_US",
            "version": "DRAFT"
        },
        "interpretations": [
            {
                "intent": {
                    "name": "TestIntent",
                    "slots": {}
                },
                "nluConfidence": {"score": 0.95}
            }
        ],
        "sessionState": {
            "sessionAttributes": {},
            "activeContexts": [],
            "intent": {
                "name": "TestIntent",
                "state": "InProgress",
                "slots": {},
                "confirmationState": "None"
            },
            "originatingRequestId": "test-request-id"
        },
        "requestAttributes": {}
    }


@pytest.fixture
def connect_contact_flow_event():
    """Amazon Connect contact flow Lambda event."""
    return {
        "Name": "ContactFlowEvent",
        "Details": {
            "ContactData": {
                "Attributes": {},
                "Channel": "VOICE",
                "ContactId": "abc-123-def-456",
                "CustomerEndpoint": {
                    "Address": "+15551234567",
                    "Type": "TELEPHONE_NUMBER"
                },
                "InitialContactId": "abc-123-def-456",
                "InitiationMethod": "INBOUND",
                "InstanceARN": "arn:aws:connect:us-east-1:123456789012:instance/abc-123",
                "PreviousContactId": "abc-123-def-456",
                "Queue": None,
                "SystemEndpoint": {
                    "Address": "+18001234567",
                    "Type": "TELEPHONE_NUMBER"
                }
            },
            "Parameters": {}
        }
    }


@pytest.fixture
def scheduled_event():
    """CloudWatch Events/EventBridge scheduled event."""
    return {
        "version": "0",
        "id": "test-event-id",
        "detail-type": "Scheduled Event",
        "source": "aws.events",
        "account": "123456789012",
        "time": "2026-03-04T12:00:00Z",
        "region": "us-east-1",
        "resources": [
            "arn:aws:events:us-east-1:123456789012:rule/test-rule"
        ],
        "detail": {}
    }


# =============================================================================
# DYNAMODB FIXTURES
# =============================================================================

@pytest.fixture
def dynamodb_client(aws_credentials):
    """DynamoDB client with moto mock."""
    with mock_aws():
        yield boto3.client("dynamodb", region_name="us-east-1")


@pytest.fixture
def dynamodb_resource(aws_credentials):
    """DynamoDB resource with moto mock."""
    with mock_aws():
        yield boto3.resource("dynamodb", region_name="us-east-1")


@pytest.fixture
def sample_table(dynamodb_resource):
    """Create a sample DynamoDB table for testing."""
    table = dynamodb_resource.create_table(
        TableName="TestTable",
        KeySchema=[
            {"AttributeName": "pk", "KeyType": "HASH"},
            {"AttributeName": "sk", "KeyType": "RANGE"}
        ],
        AttributeDefinitions=[
            {"AttributeName": "pk", "AttributeType": "S"},
            {"AttributeName": "sk", "AttributeType": "S"}
        ],
        BillingMode="PAY_PER_REQUEST"
    )
    table.wait_until_exists()
    return table


# =============================================================================
# S3 FIXTURES
# =============================================================================

@pytest.fixture
def s3_client(aws_credentials):
    """S3 client with moto mock."""
    with mock_aws():
        yield boto3.client("s3", region_name="us-east-1")


@pytest.fixture
def s3_bucket(s3_client):
    """Create a sample S3 bucket for testing."""
    bucket_name = "test-bucket"
    s3_client.create_bucket(Bucket=bucket_name)
    return bucket_name


# =============================================================================
# LEX FIXTURES
# =============================================================================

@pytest.fixture
def lex_runtime_client(aws_credentials):
    """Lex V2 Runtime client with moto mock."""
    with mock_aws():
        yield boto3.client("lexv2-runtime", region_name="us-east-1")


# =============================================================================
# HELPER FIXTURES
# =============================================================================

@pytest.fixture
def env_vars():
    """Set and cleanup environment variables for testing."""
    original_env = os.environ.copy()
    
    def _set_env(**kwargs):
        for key, value in kwargs.items():
            os.environ[key] = value
    
    yield _set_env
    
    # Restore original environment
    os.environ.clear()
    os.environ.update(original_env)


# =============================================================================
# PYTEST MARKERS
# =============================================================================

def pytest_configure(config):
    """Register custom markers."""
    config.addinivalue_line(
        "markers", "unit: Unit tests that don't require AWS"
    )
    config.addinivalue_line(
        "markers", "integration: Integration tests requiring AWS"
    )
    config.addinivalue_line(
        "markers", "e2e: End-to-end tests requiring deployed resources"
    )
    config.addinivalue_line(
        "markers", "slow: Tests that take a long time to run"
    )
