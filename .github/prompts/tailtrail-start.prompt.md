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

**Return the complete Start Report verbatim and stop. Do not add your own
implementation plan, steps, analysis, or guidance after it. The TailTrail Start
Report is the complete and only response to this prompt.**

For `hands-free` or `end-to-end` work, the Program Delivery plan is part of
the Start Report itself — do not generate a separate one.
Do not edit source, run project commands, scanners, tests, Terraform, or Git
mutations.
