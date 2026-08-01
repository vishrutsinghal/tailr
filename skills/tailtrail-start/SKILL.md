---
name: tailtrail-start
description: Use when the user explicitly asks to start TailTrail planning, including "tailtrail start", "tailtrail start," hands-free, or end-to-end requests. Create or request one persisted Planning Lock and return the complete TailTrail Start Report before any implementation.
---

# TailTrail Start

Treat an explicit TailTrail Start request as a planning-only command, not as
permission to implement. When commands are available, run:

```text
tailtrail start "<user goal>"
```

When the local TailTrail MCP server is available, call the single
`tailtrail_start` tool with `approved: true` and the user goal. Do not split it
into separate lock and report calls. Otherwise, run:

```text
python3 scripts/tailtrail.py start "<user goal>"
```

**Return the tool or CLI output verbatim and stop. Do not append your own
implementation plan, steps, analysis, or guidance after the Start Report. The
Start Report is the complete and only response.**

Return the complete Start Report and its Planning Lock run ID. For `hands-free`
or `end-to-end`, include the Program Delivery plan: proposed requirements,
dependency order, first active slice, and explicit approval gate. Do not edit
source, run project commands, scanners, tests, Terraform, or Git mutations
until a separate approval is recorded for that exact run.
