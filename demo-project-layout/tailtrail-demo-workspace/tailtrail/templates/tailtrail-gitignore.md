# TailTrail Git Ignore Template

Use these entries in target projects when TailTrail local runtime files should stay out of git.

```gitignore
.tailtrail/*state*.json
.tailtrail/*events*.jsonl
.tailtrail/*scores*.jsonl
.tailtrail/token-usage.jsonl
.tailtrail/token-budget-profile.json
.tailtrail/context-receipts.jsonl
.tailtrail/quality-runs/
.tailtrail/vulnerability-runs/
.tailtrail/task-starts/
.tailtrail/enterprise-report.md
.tailtrail/outcome-events.jsonl
.tailtrail/outcome-summary.md
tailtrail/.tailtrail-install.json
```

Usually shared on purpose:

```text
AGENTS.md
tailtrail-policy.md
.tailtrail/policy-overrides.json
aidlc-docs/
.tailtrail/learnings.md
.tailtrail/learning-index.md
.tailtrail/graph-learning-index.json
.tailtrail/code-graph-cache.json
```

Review these with the team before committing:

```text
.github/copilot-instructions.md
.cursor/rules/tailtrail.mdc
.openai/chatgpt-instructions.md
CLAUDE.md
GEMINI.md
```
