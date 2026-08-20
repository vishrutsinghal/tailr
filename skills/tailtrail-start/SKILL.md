---
name: tailtrail-start
description: Use when the user explicitly asks to start TailTrail planning, including "tailtrail start", "tailtrail start," hands-free, or end-to-end requests. Create or request one persisted Planning Lock and return the complete TailTrail Start Report before any implementation.
---

# TailTrail Start

## AIDLC question discussion

For an awaiting-approval AIDLC run, when the user asks to explain, simplify, or
rephrase a numbered question such as `Q5`, run `tailtrail planning
aidlc-question clarify --run-id <id> --question-id Q5`. Explain only from the
saved artifact; do not change the question, plan, anchor, answers, or source.
If the user challenges the question, options, or reasoning as incorrect, create
an `aidlc-question challenge`, have the active AIDLC authority generate the
replacement, record it, show it, and require explicit `aidlc-question approve`.
For Standard and Full, replacements must use the pinned official AIDLC
Requirements rules rather than a TailTrail-generated substitute.

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
into separate lock and report calls. Otherwise, resolve the launcher in this
order: `tailtrail/scripts/tailtrail.py` (installed pack), then
`scripts/tailtrail.py` (source checkout), then run:

```text
python3 tailtrail/scripts/tailtrail.py start "<user goal>"
```

When the user includes `--verbose`, pass `verbose: true` to the MCP tool (or
append `--verbose` to the CLI invocation); do not leave the flag inside the
goal text.

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

## Approved-run closure

After implementation of an approved run and its selected review and validation
steps, run:

```text
tailtrail completion-report --root . --run-id <active-run-id>
```

Return its full stdout instead of a generic implementation summary. The report
shows requirement delivery and TailTrail controls separately. Never invent
actual token use: it is measured only when host/provider telemetry is linked to
the exact run ID.

When approval returns an `execution_handoff`, persist its exact run ID and obey
its `closure.command`. Before any final response after a source edit, execute
that command through the same resolved TailTrail CLI used for Start and return
its stdout verbatim. `Changes made`, `Validation`, and next-step narratives are
not valid replacements for the closure response.
