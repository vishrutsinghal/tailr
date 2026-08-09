---
description: Create a persisted TailTrail Start plan without implementing work.
---

Run the atomic TailTrail Start flow for this request:

${input:goal:Describe the task to plan}

This prompt creates a **Planning Lock** only when the **current user message**
explicitly invokes it. A prior chat mention, pasted **error output**, log, stack
trace, or follow-up debugging request must not create a **new Planning Lock**. Reuse an
awaiting-approval run ID; continue an approved in-scope run without another
Start approval.

If the local TailTrail MCP server is configured, call the single
`tailtrail_start` tool with `approved: true` and the goal above.
Otherwise run: `{{TAILTRAIL_START_COMMAND}}` and return its output.

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

If the request includes `--verbose`, return the full CLI verbose report verbatim.
Verify it includes `Planning Lock`, `Start Here`, `Navigator Decision`, `Selected
TailTrail features`, `Deferred TailTrail features`, `Guided delivery`, `Validation`,
`Evidence posture`, and `Approval`. Never replace those sections with a summary.

For `hands-free` or `end-to-end` work, the Program Delivery plan is part of
the Start Report itself — do not generate a separate one.
If the user rejects or declines this awaiting-approval plan, do **not** inspect
project files, offer inspection, run tests/scanners, edit source, run Git, or
create another Start run. Read only the saved Planning Lock and Start report,
then run `tailtrail planning feedback-template --run-id <active-run-id>` and
return its blank feedback form. Never invent a rejection decision or comment.
The user may review every requirement with an `approve` or `reject — <reason>`
decision, say `Reject all — <reason>`, or say `Use AIDLC Requirements mode`.
For AIDLC, run `tailtrail planning aidlc-cycle --run-id <active-run-id>`
and return its complete `TailTrail AIDLC Requirements` report, including the
current requirement boundary, focused questions, and next response format.
Keep the same run ID.
On the first material rejection, ask targeted questions or offer AIDLC
Requirements mode; on the second, use AIDLC Requirements mode before another
material proposal.

When the user answers an active AIDLC Requirements report, record every answer
with `tailtrail planning aidlc-cycle --run-id <active-run-id> --answers '<json>'`
and return the resulting revised boundary for approval. When the user approves
that boundary, run `tailtrail planning aidlc-cycle --run-id <active-run-id>
--approved`, return the Execution Handoff, then continue normal TailTrail
implementation under the same activated run only.

On Windows native shells, use `--answers-base64 <base64-utf8-json>` in place of
`--answers` so native argument quoting cannot corrupt the JSON.

Until the Start plan or revised AIDLC boundary is explicitly approved, do not
edit source, run project commands, scanners, tests, Terraform, or Git mutations.
