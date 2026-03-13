# IRS Agent Guide Setup - Complete Instructions

## Current Status

✅ **Views created and published** (6 views)  
✅ **Event flow created:** `IRS-Agent-Guide-Event` (shows view when agent connects)  
⚠️ **ONE STEP REMAINING:** Add "Set event flow" block in Console

---

## Final Step: Add "Set event flow" Block (2 minutes)

**Why Event Flow?** For voice calls, ShowView must run in a separate "event flow" that triggers when the agent accepts the call - not during IVR routing.

### Step 1: Open Flow Editor

Direct link:
```
https://us-east-1.console.aws.amazon.com/connect/contact-flows/editor?instanceId=a88ddab9-3b29-409f-87f0-bdb614abafef&flowId=08728175-2bd5-452d-a68e-901fa36ab7eb
```

Or via Connect Admin:
1. Go to: https://treasury-connect-prod.my.connect.aws
2. Navigate to: **Routing** → **Contact flows**
3. Click on: **IRS-Inbound-Agent-Transfer**

### Step 2: Replace ShowView with Set Event Flow

1. **DELETE** the current "Show view" block (it's in the wrong place)
2. From the block palette, drag **Set event flow** block
3. Place it where ShowView was (after Set contact attributes)
4. Connect the blocks:
   ```
   [Set contact attributes] → [Set event flow] → [Transfer to queue]
   ```

### Step 3: Configure Set Event Flow

1. Click on the **Set event flow** block
2. In properties, select:
   - **Event**: `Default flow for agent UI`
   - **Flow**: `IRS-Agent-Guide-Event`

### Step 4: Save and Publish

1. Click **Save** (top right)
2. Click **Publish**

---

## Architecture (Event Flow Pattern)

```
┌─────────────────────────────────────────────────────────────────────┐
│              MAIN FLOW: IRS-Inbound-Agent-Transfer                   │
├─────────────────────────────────────────────────────────────────────┤
│                                                                      │
│  [Entry Point]                                                       │
│       ↓                                                              │
│  [Play prompt: "Thank you for calling IRS..."]                       │
│       ↓                                                              │
│  [Set working queue: TreasuryIRSQueue]                               │
│       ↓                                                              │
│  [Set contact attributes: IRS Guide info]                            │
│       ↓                                                              │
│  [Set event flow: IRS-Agent-Guide-Event] ← ADD THIS                  │
│       ↓                                                              │
│  [Transfer to queue]                                                 │
│                                                                      │
└─────────────────────────────────────────────────────────────────────┘
                                 │
                    When agent accepts call...
                                 ↓
┌─────────────────────────────────────────────────────────────────────┐
│              EVENT FLOW: IRS-Agent-Guide-Event (CREATED)             │
├─────────────────────────────────────────────────────────────────────┤
│                                                                      │
│  [Show view: IRS-Taxpayer-Services] ← 5 IRS use case cards           │
│       ↓                                                              │
│  [End flow]                                                          │
│                                                                      │
└─────────────────────────────────────────────────────────────────────┘
```

---

## What's Already Done

| Resource | Status | ID |
|----------|--------|-----|
| IRS-Taxpayer-Services view | ✅ Published | `4b281dc3-bf4f-4e48-b27a-e17ea1fdb954` |
| IRS-Refund-Status-Detail | ✅ Published | `01c39969-8c8a-4bcb-bfa4-69e83939b810` |
| IRS-Identity-Verification-Detail | ✅ Published | `a6be4da3-891d-4f38-a180-fd384a361af2` |
| IRS-Payment-Plan-Detail | ✅ Published | `8c96d2ce-ae3c-468a-a06d-d68ddd42c9a9` |
| IRS-Transcript-Request-Detail | ✅ Published | `adb87dfd-329a-4646-8db5-b0fb84c06f0c` |
| IRS-Notice-Explanation-Detail | ✅ Published | `3028976b-94cf-4547-b4b9-ee77351149a0` |
| IRS-Agent-Guide-Event flow | ✅ Created | `4f9dbdf9-f62b-4558-97ca-198a00e9832a` |
| IRS-Inbound-Agent-Transfer | ⚠️ Needs Set event flow | `08728175-2bd5-452d-a68e-901fa36ab7eb` |
| Contact attributes | ✅ Working | 12 attributes set |

---

## Testing

1. **Call:** +1 833-289-6602
2. **Press:** 0 for representative
3. **Login:** https://treasury-connect-prod.my.connect.aws (as agent)
4. **Accept call**
5. **Verify:** IRS Agent Guide card dashboard appears automatically

---

## Why "Set event flow" Requires Console

Amazon Connect's "Set event flow" block:
- Cannot be created via CLI/API (requires Console-generated metadata)
- Is the ONLY way to display ShowView for voice calls
- Triggers a "side-channel" UI when the agent accepts

This is a documented AWS limitation.

---

## IRS Agent Guide Cards (5 Use Cases)

When the view appears, agents see:

1. **Refund Status** - IMFOL TC846, auth requirements, wheres-my-refund
2. **Identity Verification (5071C)** - Fraud detection, identity theft procedures
3. **Payment Plans** - Guaranteed (<$10K), Streamlined (<$50K), criteria
4. **Transcript Requests** - Form 4506-T, self-service portal, timing
5. **Notice Explanations** - CP/LTR notice handling, taxpayer rights

Each card includes:
- Step-by-step instructions
- Required documentation
- Policy references (IRM chapters)
- Fraud alerts and warnings

---

## Support

Instance: `treasury-connect-prod`  
Region: `us-east-1`  
Phone: `+1 833-289-6602`  
Admin URL: https://treasury-connect-prod.my.connect.aws
