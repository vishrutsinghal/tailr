# Workflow Planning

Purpose: choose the smallest safe path from requirements to implementation.

## Actions

- Break work into units only when it reduces risk or review size.
- Decide which conditional stages are needed.
- Identify files likely to change and files likely to be read only.
- Define validation commands and expected evidence.
- Identify approval gates.
- Record dependency decisions that need `DEPENDENCY-GATE.md`.

## Outputs

- `aidlc-docs/workflow-plan.md`
- `aidlc-docs/stage-gate-workflow.md` for standard or comprehensive depth
- updated state and audit

## Done When

- the next implementation unit is clear
- validation approach is known
- approvals are captured
- unnecessary stages are explicitly skipped
