---
name: tailtrail-start
description: Use when the user explicitly asks to start TailTrail planning, including "tailtrail start", "tailtrail start," hands-free, or end-to-end requests. Create or request one persisted Planning Lock and return the complete TailTrail Start Report before any implementation.
---

# TailTrail Start

Treat an explicit TailTrail Start request as a planning-only command, not as
permission to implement. When commands are available, run:

Evaluate that explicit request only from the **current user message**. A prior
chat mention, pasted **error output**, log, stack trace, or follow-up debugging
request is not a new Start invocation and must not create a **new Planning Lock**.
If a persisted run is awaiting approval, reuse its exact run ID and ask
for approval of that plan. If it is approved, continue the in-scope debugging
work under the same run without another Start approval. With no active run and
no explicit Start invocation in the current user message, use ordinary
TailTrail guidance or advisory `guide` routing.

```text
tailtrail start "<user goal>"
```

When the local TailTrail MCP server is available, call the single
`tailtrail_start` tool with `approved: true` and the user goal. Do not split it
into separate lock and report calls. Otherwise, run:

```text
python3 scripts/tailtrail.py start "<user goal>"
```

**The complete and only normal assistant response must be the exact Start Report
stdout (starting `# TailTrail Start Plan` and including its returned run ID). Copy the
complete Start Report verbatim outside any collapsible terminal/tool-result panel.
Stop immediately after it.
Never synthesize a substitute plan or task list. Do not write `Steps`, `in-progress`,
`Next I'll`, `shall I proceed`, or implementation/testing/PR/documentation work. If
stdout is unavailable, state only that the command report could not be copied; do not
reconstruct a plan from the goal.**

Before sending the report, verify it includes every required heading: `Planning Lock`,
`Scope`, `Requirements`, `Selected TailTrail features`, `Plan`, `Focused validation`,
and `Approval`. The selected-features table is mandatory. Do not shorten, rename, or
replace it with `Next step`; paste the CLI stdout again if any section is missing.

Return the complete Start Report and its Planning Lock run ID. For `hands-free`
or `end-to-end`, include the Program Delivery plan: proposed requirements,
dependency order, first active slice, and explicit approval gate. Do not edit
source, run project commands, scanners, tests, Terraform, or Git mutations
until a separate approval is recorded for that exact run.

## Rejected Start plans

If the user rejects or declines an awaiting-approval Start plan, preserve its
run ID and do **not** inspect source, offer inspection, run tests/scanners,
edit files, mutate Git, or create a new Start run. Read only the saved Planning
Lock and Start report, then run:

```text
tailtrail planning feedback-template --run-id <active-run-id>
```

Return that blank requirement-by-requirement form; never invent a decision or
comment. The user may review every row with `approve` or `reject — <reason>`,
say `Reject all — <reason>`, or say `Use AIDLC Requirements mode`. Record
individual feedback through `tailtrail planning feedback`, reject-all feedback
through `tailtrail planning reject-all`, or the AIDLC choice through `tailtrail
planning aidlc-cycle`. For that last path, return the complete `TailTrail
AIDLC Requirements` report with the current boundary, focused questions, and
next response format. The first material rejection offers AIDLC; the second
requires it before a revised material proposal.

When the user answers an active AIDLC Requirements report, record all answers
with `tailtrail planning aidlc-cycle --run-id <active-run-id> --answers '<json>'`
and return the resulting revised boundary for approval. When the user approves
that boundary, run `tailtrail planning aidlc-cycle --run-id <active-run-id>
--approved`, return the Execution Handoff, and continue implementation only
under that same activated run and approved AIDLC anchor.

On Windows native shells, use `--answers-base64 <base64-utf8-json>` in place of
`--answers` so native argument quoting cannot corrupt the JSON.
