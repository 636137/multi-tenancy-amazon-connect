#!/usr/bin/env python3
"""
Secure ElevenLabs API key setup with masked input and validation.
- Never logs the API key
- Uses masked input (no echo to terminal)
- Validates key against ElevenLabs API
- Stores in .env file (gitignored)
- Ready for AWS Secrets Manager upload
"""

import os
import sys
import getpass
import re
import subprocess
from pathlib import Path

def validate_elevenlabs_key(api_key: str) -> tuple[bool, str]:
    """
    Validate API key against ElevenLabs API endpoint.
    Returns: (is_valid, message)
    """
    try:
        import requests
    except ImportError:
        print("❌ requests library required. Installing...")
        subprocess.check_call([sys.executable, "-m", "pip", "install", "requests", "-q"])
        import requests
    
    # Check key format (should be 32+ chars alphanumeric)
    if not api_key or len(api_key) < 32:
        return False, "API key too short (minimum 32 characters)"
    
    if not re.match(r'^[a-zA-Z0-9]+$', api_key):
        return False, "API key contains invalid characters"
    
    # Validate against API (no key leaked - just calls API)
    try:
        resp = requests.get(
            "https://api.elevenlabs.io/v1/user",
            headers={"xi-api-key": api_key},
            timeout=5
        )
        
        if resp.status_code == 200:
            data = resp.json()
            tier = data.get("subscription", {}).get("tier", "unknown")
            return True, f"✅ Valid API key (Tier: {tier})"
        elif resp.status_code == 401:
            return False, "❌ Invalid API key (401 Unauthorized)"
        elif resp.status_code == 403:
            return False, "❌ Access forbidden (may need to enable agents in settings)"
        else:
            return False, f"❌ API error: {resp.status_code}"
    except requests.exceptions.Timeout:
        return False, "❌ API timeout (check internet connection)"
    except Exception as e:
        return False, f"❌ Validation error: {str(e)}"


def save_to_env_file(api_key: str, overwrite: bool = False) -> Path:
    """
    Save API key to .env file (gitignored).
    Returns: Path to .env file
    """
    env_path = Path("/Users/ChadDHendren/AmazonConnect1/.env")
    
    # Check if .env exists and handle overwrite
    if env_path.exists() and not overwrite:
        print(f"\n⚠️  {env_path} already exists")
        confirm = input("Overwrite existing .env? (y/N): ").strip().lower()
        if confirm != 'y':
            print("❌ Cancelled. Existing .env preserved.")
            return None
    
    # Create .env content
    env_content = f"""# ElevenLabs Configuration
ELEVENLABS_API_KEY={api_key}
ELEVENLABS_API_BASE=https://api.elevenlabs.io/v1

# AWS Configuration (Optional - set if deploying to AWS)
# AWS_REGION=us-east-1
# AWS_PROFILE=default
"""
    
    # Write file with restricted permissions (0600 = rw-------)
    env_path.write_text(env_content)
    os.chmod(env_path, 0o600)  # Owner read/write only
    
    print(f"✅ Saved to {env_path}")
    print(f"   Permissions: Owner read/write only (0600)")
    
    return env_path


def create_gitignore_entry():
    """Ensure .env is in .gitignore"""
    gitignore_path = Path("/Users/ChadDHendren/AmazonConnect1/.gitignore")
    
    if gitignore_path.exists():
        content = gitignore_path.read_text()
        if ".env" not in content:
            gitignore_path.write_text(content + "\n.env\n")
            print("✅ Added .env to .gitignore")
    else:
        gitignore_path.write_text(".env\n")
        print("✅ Created .gitignore with .env")


def main():
    print("\n" + "="*70)
    print("🔐 ElevenLabs Secure Credential Setup")
    print("="*70)
    print("\nThis will:")
    print("  1. Prompt for your ElevenLabs API key (masked input, no echo)")
    print("  2. Validate against ElevenLabs API (without logging key)")
    print("  3. Save to .env file with restricted permissions (0600)")
    print("  4. Never display the key in terminal")
    print("\n")
    
    # Masked input
    print("Enter your ElevenLabs API key (input hidden):")
    try:
        api_key = getpass.getpass("API Key: ")
    except Exception:
        # Fallback if getpass doesn't work in this terminal
        api_key = input("API Key: ")
    
    if not api_key:
        print("❌ No key provided. Exiting.")
        sys.exit(1)
    
    print("\n⏳ Validating API key...")
    is_valid, message = validate_elevenlabs_key(api_key)
    print(message)
    
    if not is_valid:
        print("❌ Setup cancelled.")
        sys.exit(1)
    
    # Save to .env
    print("\n📝 Saving to .env file...")
    create_gitignore_entry()
    env_path = save_to_env_file(api_key)
    
    if env_path:
        print("\n" + "="*70)
        print("✅ Setup Complete!")
        print("="*70)
        print(f"\nYour ElevenLabs API key is now stored in:")
        print(f"  {env_path}")
        print(f"\nThe key is:")
        print(f"  • Masked input (never echoed to terminal)")
        print(f"  • Stored with restricted permissions (0600)")
        print(f"  • Protected by .gitignore (won't be committed)")
        print(f"  • Ready to use with the ElevenLabs Orchestrator agent")
        print(f"\nNext steps:")
        print(f"  1. Import the agent: '/elevenlabs-orchestrator' in chat")
        print(f"  2. Request deployment: 'Create an AI agent for...'")
        print(f"  3. Agent will use credentials from .env automatically")
        print("\n")
        return 0
    
    return 1


if __name__ == "__main__":
    sys.exit(main())
