# TailTrail Git Ignore Template

Use these entries in target projects when TailTrail local runtime files should stay out of git.

```gitignore
.tailtrail/
tailtrail/
.tailtrail/*state*.json
.tailtrail/*events*.jsonl
.tailtrail/*scores*.jsonl
.tailtrail/token-usage.jsonl
.tailtrail/token-budget-profile.json
.tailtrail/context-receipts.jsonl
.tailtrail/token-harness-events.jsonl
.tailtrail/token-harness-events.lock
.tailtrail/quality-runs/
.tailtrail/vulnerability-runs/
.tailtrail/task-starts/
.tailtrail/enterprise-report.md
.tailtrail/outcome-events.jsonl
.tailtrail/outcome-summary.md
.tailtrail/harness-review.md
.tailtrail/harness-local-summary.json
.tailtrail/harness-summary.json
.tailtrail/harness-recommendations.json
.tailtrail/harness-events.jsonl
.tailtrail/meta-harness-analysis.json
.tailtrail/meta-harness-analysis.md
.tailtrail/meta-harness-proposal.md
.tailtrail/meta-harness-proposals.jsonl
tailtrail/.tailtrail-install.json
```

Default shareable TailTrail metadata:

```text
tailtrail-meta/code-graph-cache.json
tailtrail-meta/harness-summary.jsonl
tailtrail-meta/harness-summary.schema.json
tailtrail-meta/README.md
```

`.tailtrail/code-graph-cache.json` is still supported as a private legacy/local fallback, but the default team cache is `tailtrail-meta/code-graph-cache.json`.

Optional strict-local install entries:

```gitignore
.github/copilot-instructions.md
.cursor/rules/tailtrail.mdc
.openai/chatgpt-instructions.md
CLAUDE.md
GEMINI.md
AGENTS.md
AIDLC.md
DEPENDENCY-GATE.md
GUARDRAILS.md
GOVERNANCE.md
TOKEN-AUTOPILOT.md
TOKEN-SLICER.md
TAILTRAIL-COMMANDS.md
USEFUL-PROMPTS.md
USER-GUIDE.md
tailtrail-policy.md
tailtrail-policy.example.md
aidlc-docs/
```

Use the strict-local entries when your organization wants TailTrail setup files to remain local and only `tailtrail-meta/` to be shared through git.

If your team intentionally wants shared assistant instructions or lifecycle docs, remove the corresponding strict-local ignore entries after review.

Keep `tailtrail-meta/` allowed when your repo chooses to share compact metadata:

```gitignore
!tailtrail-meta/
!tailtrail-meta/README.md
!tailtrail-meta/code-graph-cache.json
!tailtrail-meta/harness-summary.schema.json
!tailtrail-meta/harness-summary.jsonl
```
