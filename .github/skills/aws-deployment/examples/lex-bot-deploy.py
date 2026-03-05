"""
Example: Deploy a Lex V2 Bot with Proper State Management

This script demonstrates the idempotent deployment pattern for Lex V2 bots,
including waiting for resources to reach ready state before proceeding.
"""

import boto3
import time
from botocore.exceptions import ClientError

def wait_for_bot_available(lex_client, bot_id: str, max_wait: int = 300) -> bool:
    """Wait for bot to reach Available state with exponential backoff."""
    wait_time = 5
    total_waited = 0
    
    while total_waited < max_wait:
        response = lex_client.describe_bot(botId=bot_id)
        status = response["botStatus"]
        
        if status == "Available":
            print(f"✅ Bot {bot_id} is Available")
            return True
        elif status in ["Failed", "Deleting"]:
            raise Exception(f"Bot entered failed state: {status}")
        
        print(f"⏳ Bot status: {status}, waiting {wait_time}s...")
        time.sleep(wait_time)
        total_waited += wait_time
        wait_time = min(wait_time * 1.5, 30)
    
    raise TimeoutError(f"Bot did not become Available after {max_wait}s")


def create_or_get_bot(lex_client, bot_name: str, role_arn: str) -> str:
    """Create bot if it doesn't exist, return bot ID."""
    # Check if bot exists
    try:
        bots = lex_client.list_bots()
        for bot in bots.get("botSummaries", []):
            if bot["botName"] == bot_name:
                print(f"📌 Found existing bot: {bot['botId']}")
                return bot["botId"]
    except ClientError as e:
        print(f"Error listing bots: {e}")
    
    # Create new bot
    print(f"🔨 Creating bot: {bot_name}")
    response = lex_client.create_bot(
        botName=bot_name,
        roleArn=role_arn,
        dataPrivacy={"childDirected": False},
        idleSessionTTLInSeconds=300
    )
    
    bot_id = response["botId"]
    print(f"✅ Created bot: {bot_id}")
    return bot_id


def create_locale_if_needed(lex_client, bot_id: str, locale_id: str = "en_US") -> None:
    """Create locale if it doesn't exist."""
    try:
        lex_client.describe_bot_locale(
            botId=bot_id,
            botVersion="DRAFT",
            localeId=locale_id
        )
        print(f"📌 Locale {locale_id} already exists")
        return
    except lex_client.exceptions.ResourceNotFoundException:
        pass
    
    print(f"🔨 Creating locale: {locale_id}")
    lex_client.create_bot_locale(
        botId=bot_id,
        botVersion="DRAFT",
        localeId=locale_id,
        nluIntentConfidenceThreshold=0.4
    )
    
    # Wait for locale to be ready
    wait_for_locale_available(lex_client, bot_id, locale_id)


def wait_for_locale_available(lex_client, bot_id: str, locale_id: str, max_wait: int = 120) -> None:
    """Wait for locale to reach ready state."""
    wait_time = 5
    total_waited = 0
    
    while total_waited < max_wait:
        response = lex_client.describe_bot_locale(
            botId=bot_id,
            botVersion="DRAFT",
            localeId=locale_id
        )
        status = response["botLocaleStatus"]
        
        if status in ["NotBuilt", "Built"]:
            print(f"✅ Locale {locale_id} is ready")
            return
        elif status == "Failed":
            raise Exception(f"Locale creation failed: {response.get('failureReasons')}")
        
        print(f"⏳ Locale status: {status}")
        time.sleep(wait_time)
        total_waited += wait_time
    
    raise TimeoutError(f"Locale did not become ready after {max_wait}s")


def build_bot(lex_client, bot_id: str, locale_id: str = "en_US") -> None:
    """Build the bot and wait for completion."""
    print(f"🔨 Building bot {bot_id}...")
    lex_client.build_bot_locale(
        botId=bot_id,
        botVersion="DRAFT",
        localeId=locale_id
    )
    
    # Wait for build
    wait_time = 10
    max_wait = 300
    total_waited = 0
    
    while total_waited < max_wait:
        response = lex_client.describe_bot_locale(
            botId=bot_id,
            botVersion="DRAFT",
            localeId=locale_id
        )
        status = response["botLocaleStatus"]
        
        if status == "Built":
            print(f"✅ Bot built successfully!")
            return
        elif status == "Failed":
            raise Exception(f"Build failed: {response.get('failureReasons')}")
        
        print(f"⏳ Build status: {status}")
        time.sleep(wait_time)
        total_waited += wait_time


if __name__ == "__main__":
    # Example usage
    lex = boto3.client("lexv2-models", region_name="us-east-1")
    
    # Replace with your IAM role ARN
    ROLE_ARN = "arn:aws:iam::123456789012:role/LexBotRole"
    BOT_NAME = "SurveyBot"
    
    # Deploy
    bot_id = create_or_get_bot(lex, BOT_NAME, ROLE_ARN)
    wait_for_bot_available(lex, bot_id)
    create_locale_if_needed(lex, bot_id)
    
    # Add intents/slots here...
    
    build_bot(lex, bot_id)
    print(f"\n🎉 Bot deployed: {bot_id}")
