# Demo Data Policy

All data in this workspace is synthetic and demo-only.

## Rules

- no real customer data
- no real employee or user names
- no real secrets
- no private URLs
- no production scanner output
- no raw prompts from real users

## Synthetic Claim Examples

Valid claim:

```json
{
  "claim_id": "CLM-1001",
  "member_id": "MBR-2001",
  "claim_type": "medical",
  "amount": 125.5
}
```

Invalid claim for the demo bug:

```json
{
  "claim_id": "CLM-1002",
  "member_id": "MBR-2002",
  "claim_type": "medical",
  "amount": 0
}
```

Policy:

- claim amount must be greater than `0`
- claim type must be one of the configured allowed types
- member id is required

