#!/usr/bin/env python3
"""Store ElevenLabs API key securely to .env"""
import os
import sys
from pathlib import Path

api_key = "sk_3aee547717f8fac63ffa4c8417a3b67685c7f927f65c61e9"

print("⏳ Validating ElevenLabs API key...")

try:
    import requests
    resp = requests.get(
        "https://api.elevenlabs.io/v1/user",
        headers={"xi-api-key": api_key},
        timeout=5
    )
    
    if resp.status_code == 200:
        data = resp.json()
        tier = data.get("subscription", {}).get("tier", "unknown")
        print(f"✅ Valid API key (Tier: {tier})")
        
        # Save to .env with restricted permissions
        env_path = Path("/Users/ChadDHendren/AmazonConnect1/.env")
        env_content = f"""# ElevenLabs Configuration
ELEVENLABS_API_KEY={api_key}
ELEVENLABS_API_BASE=https://api.elevenlabs.io/v1

# AWS Configuration (Optional)
# AWS_REGION=us-east-1
# AWS_PROFILE=default
"""
        env_path.write_text(env_content)
        os.chmod(env_path, 0o600)
        
        # Ensure .gitignore has .env
        gitignore_path = Path("/Users/ChadDHendren/AmazonConnect1/.gitignore")
        if gitignore_path.exists():
            content = gitignore_path.read_text()
            if ".env" not in content:
                gitignore_path.write_text(content + "\n.env\n")
        else:
            gitignore_path.write_text(".env\n")
        
        print(f"✅ Saved to .env (permissions: 0600)")
        print("\n" + "="*70)
        print("✅ Setup Complete!")
        print("="*70)
        print("\nYour ElevenLabs API key is now:")
        print("  • Stored in .env with restricted permissions (0600)")
        print("  • Protected by .gitignore (won't be committed)")
        print("  • Ready to use with orchestrator agent")
        print("\nNext: Use '/elevenlabs-orchestrator' to deploy agents")
        
    elif resp.status_code == 401:
        print("❌ Invalid API key (401 Unauthorized)")
        sys.exit(1)
    else:
        print(f"❌ API error ({resp.status_code})")
        sys.exit(1)
except Exception as e:
    print(f"❌ Error: {str(e)}")
    sys.exit(1)
