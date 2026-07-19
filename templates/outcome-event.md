# TailTrail Outcome Event

Use this template only for compact approved adoption evidence. Do not include raw prompts, raw logs, secrets, PII, PHI, customer data, or source snippets.

```json
{
  "task_id": "task-001",
  "task_type": "bug-fix",
  "workflow_selected": ["start", "review", "quality"],
  "user_acceptance": "accepted",
  "validation_outcome": "pass",
  "review_outcome": "approved",
  "defect_escaped": "no",
  "time_saved_band": "30-60m",
  "tailtrail_fit": "correct",
  "learning_quality": "trusted"
}
```

Allowed value reminders:

- `task_type`: `bug-fix`, `feature`, `refactor`, `review`, `ci-sonar`, `vulnerability`, `dependency`, `documentation`, `test`, `unknown`
- `user_acceptance`: `accepted`, `partially-accepted`, `revised`, `rejected`, `unknown`
- `validation_outcome`: `pass`, `fail`, `not-run`, `blocked`, `unknown`
- `review_outcome`: `approved`, `changes-requested`, `not-reviewed`, `not-needed`, `unknown`
- `defect_escaped`: `yes`, `no`, `unknown`
- `time_saved_band`: `none`, `lt15m`, `15-30m`, `30-60m`, `1-2h`, `2h-plus`, `unknown`
- `tailtrail_fit`: `too-heavy`, `too-light`, `correct`, `unknown`
- `learning_quality`: `not-used`, `weak`, `cautious`, `trusted`, `refreshed`, `unknown`
