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

If the user includes `--verbose`, treat it as a TailTrail flag, not part of the
goal: pass `verbose: true` to `tailtrail_start`, or append `--verbose` to the
CLI command. The returned report must then include every verbose heading.

**The complete and only normal assistant response must be the exact Start Report
stdout (starting `# TailTrail Start Plan` and including its returned run ID). Copy the
complete Start Report verbatim outside any collapsible terminal/tool-result panel.
Stop immediately after it.
Never synthesize a substitute plan or task list. Do not write `Steps`, `in-progress`,
`Next I'll`, `shall I proceed`, or implementation/testing/PR/documentation work. If
stdout is unavailable, state only that the command report could not be copied; do not
reconstruct a plan from the goal.**

**Official AIDLC exception:** if the saved Start report has
`aidlc_requirements.state = official-aidlc-host-generation-required`, do not stop
at a local substitute. Read the pinned official Requirements Analysis and
question-format rules plus the saved Question Orchestrator context referenced by
the report. Generate only material official questions and options; include
requirement IDs, decision class and impact, known context, evidence references,
and attach a TailTrail advisory recommendation and evidence-grounded reasoning to each,
record them with `tailtrail planning official-aidlc-questions`, and return the
complete `TailTrail Official AI-DLC Requirements` report for the same run. Do
not inspect project source, present inventory hypotheses as confirmed source
behavior, implement work, or claim the recommendations are
official-pack text; the user may choose any option or Other with detail.

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
--approved` and retain the internal Execution Handoff. For Lite/Off
`approved-plan-auto-grant`, continue safe implementation immediately without
returning the handoff as a stopping response. Standard/Full and Intent Bridge
retain the visible defensive handoff and material gate.

On Windows native shells, use `--answers-base64 <base64-utf8-json>` in place of
`--answers` so native argument quoting cannot corrupt the JSON.

After the user has approved this run and implementation has completed, run
`tailtrail completion-report --root . --run-id <active-run-id>` after the selected
review and validation steps. Return its complete stdout rather than a generic
implementation summary. It reports requirement delivery and TailTrail controls
separately; actual model tokens remain unavailable unless linked host/provider
telemetry identifies this exact run ID.

When plan approval returns an `execution_handoff`, retain its run ID and obey
`closure.command`. Lite/Off `approved-plan-auto-grant` consumes that handoff
internally and continues implementation; Standard/Full and Intent Bridge show
it because a material authority gate remains. Before any final response after
a source edit, execute closure and return its stdout verbatim, including the
recorded execution-authority route. A `Changes made`, `Validation`, or next-step
narrative is never a substitute for the Completion Report.

Until the Start plan or revised AIDLC boundary is explicitly approved, do not
edit source, run project commands, scanners, tests, Terraform, or Git mutations.
