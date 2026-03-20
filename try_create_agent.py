#!/usr/bin/env python3
"""Test creating an agent directly."""

import os
import requests
import json
from dotenv import load_dotenv

load_dotenv()
api_key = os.environ.get("ELEVENLABS_API_KEY")

print("Attempting to create IRS Agent...\n")

# Try creating agent
payload = {
    "name": "IRS Taxpayer Assistant",
    "description": "Handles refund status, payment plans, and tax questions",
    "model": "elevenlabs-agent-advanced",
    "personality": {
        "tone": "professional, patient, empathetic",
        "firstMessage": "Hello! I'm the IRS Taxpayer Assistant. How can I help you today?"
    }
}

# Try different endpoints
endpoints = [
    "https://api.elevenlabs.io/v1/agents",
    "https://api.elevenlabs.io/v1/agent",
    "https://api.elevenlabs.io/v2/agents",
]

for url in endpoints:
    print(f"Trying: {url}")
    try:
        resp = requests.post(
            url,
            json=payload,
            headers={"xi-api-key": api_key},
            timeout=10
        )
        
        print(f"  Status: {resp.status_code}")
        
        try:
            data = resp.json()
            if resp.status_code < 400:
                print(f"  ✅ SUCCESS!")
                print(f"     Agent ID: {data.get('agent_id')}")
                print(f"     Full Response: {json.dumps(data, indent=2)}")
            else:
                print(f"  Error: {data}")
        except:
            print(f"  Response: {resp.text[:200]}")
            
    except Exception as e:
        print(f"  Exception: {str(e)[:100]}")
    
    print()
