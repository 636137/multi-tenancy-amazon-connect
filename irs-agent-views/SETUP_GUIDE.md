# IRS Agent Guide Setup - Complete Instructions

## Current Status

✅ **All components configured and working!**

| Component | Status | Details |
|-----------|--------|---------|
| IRS-Taxpayer-Services view | ✅ Ready | Uses AWS managed Cards template |
| IRS-Agent-Guide-Event flow | ✅ Active | ShowView with ViewData |
| IRS-Inbound-Agent-Transfer | ✅ Configured | UpdateContactEventHooks set |
| TreasuryConversationalFlow | ✅ Simplified | Direct to agent (no IVR menu) |
| Phone routing | ✅ Working | +1 833-289-6602 |

---

## Quick Test

1. **Agent Login:** https://treasury-connect-prod.my.connect.aws/agent-app-v2
2. **Set Status:** Available
3. **Call:** +1 833-289-6602
4. **Result:** Cards view appears when you accept the call!

---

## Architecture (Working Configuration)

```
┌─────────────────────────────────────────────────────────────────────┐
│                    CALL FLOW                                         │
├─────────────────────────────────────────────────────────────────────┤
│                                                                      │
│  📞 Caller dials +1 833-289-6602                                     │
│       ↓                                                              │
│  TreasuryConversationalFlow                                          │
│       ↓ (greeting → immediate transfer)                              │
│  TransferToFlow: IRS-Inbound-Agent-Transfer                          │
│       ↓                                                              │
│  UpdateContactTargetQueue: TreasuryIRSQueue                          │
│       ↓                                                              │
│  UpdateContactEventHooks:                                            │
│    DefaultAgentUI → IRS-Agent-Guide-Event                            │
│       ↓                                                              │
│  TransferContactToQueue                                              │
│       ↓                                                              │
│  👤 Agent accepts call                                               │
│       ↓                                                              │
│  EVENT FLOW TRIGGERS:                                                │
│    ShowView → Cards template with IRS ViewData                       │
│       ↓                                                              │
│  📋 IRS Agent Guide Cards appear in Agent Workspace!                 │
│                                                                      │
└─────────────────────────────────────────────────────────────────────┘
```

---

## Key Technical Details

### AWS Managed View ARN Format

```
arn:aws:connect:us-east-1:aws:view/cards
                          ^^^
                    Use "aws" as account ID!
```

**NOT:** `arn:aws:connect:us-east-1:593804350786:instance/.../view/...`

### ShowView Configuration

```json
{
  "Type": "ShowView",
  "Parameters": {
    "ViewResource": {
      "Id": "arn:aws:connect:us-east-1:aws:view/cards"
    },
    "InvocationTimeLimitSeconds": "400",
    "ViewData": {
      "Heading": "IRS Taxpayer Services Guide",
      "CardsPerRow": "1",
      "Cards": [
        {
          "Summary": {
            "Id": "refund-status",
            "Icon": "document",
            "Heading": "💰 Refund Status Inquiry",
            "Status": "HIGH VOLUME",
            "Description": "E-file: 21 days | Paper: 6-8 weeks"
          }
        },
        ...
      ]
    }
  }
}
```

### UpdateContactEventHooks Configuration

```json
{
  "Type": "UpdateContactEventHooks",
  "Parameters": {
    "EventHooks": {
      "DefaultAgentUI": "arn:aws:connect:us-east-1:593804350786:instance/a88ddab9-3b29-409f-87f0-bdb614abafef/contact-flow/4f9dbdf9-f62b-4558-97ca-198a00e9832a"
    }
  }
}
```

---

## IRS Agent Guide Cards (5 Topics)

| # | Card | Icon | Status | Key Info |
|---|------|------|--------|----------|
| 1 | Refund Status Inquiry | 💰 | HIGH VOLUME | E-file 21 days, Paper 6-8 wks, IMFOL TC846 |
| 2 | Identity Verification | 🛡️ | REQUIRED | Letter 5071C/6331C, ID.me, phone verify |
| 3 | Payment Plan Setup | 💳 | - | <$10K guaranteed, <$50K streamlined |
| 4 | Transcript Request | 📄 | - | Form 4506-T, online portal, 3 years |
| 5 | Notice Explanation | 📬 | - | CP2000, CP14, LTR notices |

---

## Resource IDs

| Resource | ID |
|----------|-----|
| Instance | `a88ddab9-3b29-409f-87f0-bdb614abafef` |
| TreasuryConversationalFlow | `8dfd7f4a-e383-4889-a941-d516d4919a50` |
| IRS-Inbound-Agent-Transfer | `08728175-2bd5-452d-a68e-901fa36ab7eb` |
| IRS-Agent-Guide-Event | `4f9dbdf9-f62b-4558-97ca-198a00e9832a` |
| TreasuryIRSQueue | `7e2fbca2-82c2-4fd8-addd-444b0dbdb2fd` |
| Phone Number | `c3f388bc-0eeb-489a-b7d5-916758416f4a` |

---

## Troubleshooting

### View Not Displaying

1. **Check Agent Workspace URL** - Must use `/agent-app-v2`, not legacy CCP
2. **Check View ARN format** - Use `aws` account for managed templates
3. **Check flow order** - UpdateContactEventHooks must be BEFORE TransferContactToQueue
4. **Check browser console** - Look for JavaScript errors

### "View resource is not available"

This means ShowView triggered but ARN is wrong. Fix:
```
Wrong: arn:aws:connect:us-east-1:593804350786:instance/.../view/cards:$LATEST
Right: arn:aws:connect:us-east-1:aws:view/cards
```

---

## Support

| Resource | Value |
|----------|-------|
| Instance | `treasury-connect-prod` |
| Region | `us-east-1` |
| Phone | `+1 833-289-6602` |
| Admin URL | https://treasury-connect-prod.my.connect.aws |
| Agent Workspace | https://treasury-connect-prod.my.connect.aws/agent-app-v2 |
