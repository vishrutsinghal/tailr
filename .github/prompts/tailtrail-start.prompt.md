---
description: Create a persisted TailTrail Start plan without implementing work.
---

Run the atomic TailTrail Start flow for this request:

${input:goal:Describe the task to plan}

If the local TailTrail MCP server is configured, call the single
`tailtrail_start` tool with `approved: true` and the goal above.
Otherwise run: `python3 scripts/tailtrail.py start "<goal>"` and return its
output.

**Return the tool or CLI output exactly as produced. Do not add your own
implementation plan, steps, analysis, or guidance after it. The TailTrail Start
Report is the complete and only response to this prompt.**

For `hands-free` or `end-to-end` work, the Program Delivery plan is part of
the Start Report itself — do not generate a separate one.
Do not edit source, run project commands, scanners, tests, Terraform, or Git
mutations.
