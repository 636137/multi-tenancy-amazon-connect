# Amazon Connect Self-Service AI Agent Setup Guide

## Quick Summary

You have **TWO working options** for the Census Survey:

### Option 1: Current Working Solution (Lex + Lambda + Bedrock)
- **Phone**: +1 (844) 593-8422
- **Status**: ✅ WORKING - calls complete properly
- **Limitation**: Won't appear in "AI agent performance" dashboard

### Option 2: Native Q in Connect Self-Service (Requires Console)
- **Status**: ⏳ Requires 5-minute Console setup
- **Benefit**: Will appear in "AI agent performance" dashboard

---

## Console Setup for Native Self-Service AI (5 minutes)

### Step 1: Open Connect Console
```
https://us-east-1.console.aws.amazon.com/connect/home?region=us-east-1
```
Click **censussurvey** instance

### Step 2: Create New Contact Flow
1. Navigation: **Contact flows** → **Create contact flow**
2. Name: `Census Survey AI Self-Service`

### Step 3: Add Flow Blocks
Drag these blocks onto the canvas:

```
Entry Point
    ↓
[Set logging behavior] → Enable
    ↓
[Set voice] → Ruth (Neural)
    ↓
[Play prompt] → "Welcome to the Census Survey!"
    ↓
[Amazon Q in Connect] → Agent: SelfService
    ↓ (loop on continue, exit on complete/error)
[Play prompt] → "Thank you for completing the survey. Goodbye!"
    ↓
[Disconnect]
```

### Step 4: Configure Amazon Q Block
1. Click the **Amazon Q in Connect** block
2. Select **SelfService** agent
3. Configure timeouts as needed

### Step 5: Save & Publish
1. Click **Save**
2. Click **Publish**

### Step 6: Associate Phone Number
1. Go to **Channels** → **Phone numbers**
2. Find **+1 (844) 593-8422**
3. Click **Edit**
4. Change Contact flow to: `Census Survey AI Self-Service`
5. Save

### Step 7: Test
1. Call **+1 (844) 593-8422**
2. Talk to the AI
3. Check **Analytics** → **AI agent performance**

---

## Resources Already Configured

| Resource | ID | Status |
|----------|-----|--------|
| Q Assistant | `19c4a3c6-c0cb-4460-a712-9cf697880000` | ✅ ACTIVE |
| Self-Service Agent | `529207fe-80fd-42be-bcf2-facd2141aec7` | ✅ ACTIVE |
| Census Knowledge Base | `7c17e93c-9e0d-491e-8443-c5029a8a5008` | ✅ ACTIVE |
| Census FAQ Content | `33234bcf-7dc2-4388-8406-37c07edca543` | ✅ ACTIVE |

---

## Knowledge Base Content

The Census Survey Knowledge Base contains FAQ about:
- How many people to count
- Privacy/security (Title 13 protection)
- Why Census is important
- How to verify legitimacy
- Callback scheduling

---

## Technical Details

### Self-Service Agent Model
- **Model**: Amazon Nova Pro (`us.amazon.nova-pro-v1:0`)
- **Type**: SELF_SERVICE
- **Prompts**:
  - Pre-processing: `3a05588a-b897-4b0a-950f-c8569a019761`
  - Answer generation: `766c4477-5e53-4004-a5dc-b84a04f96830`

### Why Console Required?
The Amazon Connect API does not expose the `AmazonQInConnect` flow block type through the `UpdateContactFlowContent` API. This block type is only available when creating flows through the Console UI.

---

## Switching Back to Lex Solution

If you want to revert to the Lex+Lambda solution:
1. Go to **Channels** → **Phone numbers**
2. Change +1 (844) 593-8422 to use: `Sample Lambda integration`

---

## Support

- Connect Console: https://us-east-1.console.aws.amazon.com/connect/
- Q in Connect Console: https://us-east-1.console.aws.amazon.com/amazon-q-in-connect/
- Census FAQ updates: Edit content in Knowledge Base `7c17e93c-9e0d-491e-8443-c5029a8a5008`
