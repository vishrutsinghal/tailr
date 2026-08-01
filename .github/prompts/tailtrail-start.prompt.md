---
description: Create a persisted TailTrail Start plan without implementing work.
---

Run the atomic TailTrail Start flow for this request:

${input:goal:Describe the task to plan}

Create or invoke exactly one persisted Start run. Return the complete TailTrail
Start Report, including the Planning Lock run ID, selected controls, and the
separate approval action. For `hands-free` or `end-to-end` work, return the
Hands-Free Program Plan before any implementation. Do not edit source, run
project commands, scanners, tests, Terraform, or Git mutations.
