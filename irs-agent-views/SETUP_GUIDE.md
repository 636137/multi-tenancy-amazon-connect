# IRS Agent Guide Setup - Complete Instructions

## Current Status

✅ **Working NOW:** Contact attributes appear in agent screenpop  
⚠️ **Requires Console:** ShowView block for full visual guide popup

---

## What Works Immediately

When you call **+1 833-289-6602** and press **0**, the agent will see these attributes in their Contact Control Panel:

```
IRS_GUIDE: === IRS TAXPAYER SERVICES ===
STEP_1: VERIFY: SSN + DOB + Filing Status + Address
STEP_2: DOCUMENT: Issue type + IDRS codes used
STEP_3: RESOLVE: Use IRM guidance + document resolution
USE_CASE_1: REFUND STATUS: IMFOL TC846 - Auth: SSN+Filing+Amount
USE_CASE_2: ID VERIFY 5071C: NEVER skip - Watch fraud indicators
USE_CASE_3: PAYMENT PLAN: Guaranteed <10K, Streamlined <50K
USE_CASE_4: TRANSCRIPTS: Direct to IRS.gov/transcripts first
USE_CASE_5: NOTICES: Get notice # from top right corner
FRAUD_ALERT: *** NEVER verify identity for INBOUND caller ***
POLICY_URL: https://www.irs.gov/irm/part21
```

---

## To Add Visual Card Popup (5 minutes)

The ShowView block **cannot be created via API** - Amazon Connect requires the Console UI.

### Step 1: Open Flow Editor
Direct link to the flow:
```
https://us-east-1.console.aws.amazon.com/connect/contact-flows/editor?instanceId=a88ddab9-3b29-409f-87f0-bdb614abafef&flowId=08728175-2bd5-452d-a68e-901fa36ab7eb
```

Or via Connect Admin:
1. Go to: https://treasury-connect-prod.my.connect.aws
2. Navigate to: **Routing** → **Contact flows**
3. Click on: **IRS-Inbound-Agent-Transfer**

### Step 2: Add Show View Block
1. From the block palette, drag **Show view** block
2. Place it after the **Set contact attributes** block
3. Connect the blocks:
   ```
   [Set contact attributes] → [Show view] → [Transfer to queue]
   ```

### Step 3: Configure Show View
1. Click on the **Show view** block
2. In properties, select:
   - **View**: `IRS-Taxpayer-Services`
   - **Timeout**: 400 (default)
3. Connect error branch to **Transfer to queue**

### Step 4: Save and Publish
1. Click **Save** (top right)
2. Click **Publish**

---

## Flow Diagram (After Adding ShowView)

```
┌──────────────────────────────────────────────────────────────────┐
│                    IRS-Inbound-Agent-Transfer                     │
├──────────────────────────────────────────────────────────────────┤
│                                                                   │
│  [Entry Point]                                                    │
│       ↓                                                           │
│  [Play prompt: "Thank you for calling IRS..."]                   │
│       ↓                                                           │
│  [Set working queue: TreasuryIRSQueue]                           │
│       ↓                                                           │
│  [Set contact attributes: IRS Guide info]  ← Working now!        │
│       ↓                                                           │
│  [Show view: IRS-Taxpayer-Services]  ← Add via Console           │
│       ↓                                                           │
│  [Transfer to queue]                                              │
│       ↓                                                           │
│  Agent sees both attributes AND visual cards!                     │
│                                                                   │
└──────────────────────────────────────────────────────────────────┘
```

---

## Testing

1. **Call:** +1 833-289-6602
2. **Press:** 0 for representative
3. **Login:** https://treasury-connect-prod.my.connect.aws (as agent)
4. **Accept call**
5. **Verify:** 
   - Contact attributes appear in screenpop ✓
   - Visual cards appear (after adding ShowView in Console)

---

## Why ShowView Requires Console

Amazon Connect's ShowView block:
- Works only on **chat channel** programmatically
- For **voice calls**, requires Console-generated metadata
- Creates a "side-channel" chat contact to deliver the view

This is a documented AWS limitation, not a bug in our implementation.

---

## Files Reference

| File | Description |
|------|-------------|
| `flows/irs_inbound_agent_transfer.json` | Flow with contact attributes |
| `irs_dashboard_cards.json` | View JSON definition |
| `README.md` | Complete documentation |

---

## Support

Instance: `treasury-connect-prod`  
Region: `us-east-1`  
Phone: `+1 833-289-6602`  
Admin URL: https://treasury-connect-prod.my.connect.aws
