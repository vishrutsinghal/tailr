# TailTrail Start Plan - Full Review Record

**Presentation version:** `5`

## Planning Lock

- **Run ID:** `start-20261103072319-1120cf`
- **Status:** `awaiting-approval`
- **Goal:** Complete the Phase 3 Host Question Flow public CLI Start receipt gate in scripts/task-start.py from TAILTRAIL-HOST-TAILTRAIL-EVIDENCE-VALIDATION-DESIGN.md. Before any Planning Lock, accept only a fresh pre-Start planning-readiness receipt matching the goal, target, profile registry version, accepted answers, and requirement-specific proof bindings; reject raw host contracts, intake-recorded receipts, stale or replayed receipts with actionable missing-field guidance. Preserve legacy ordinary Start routes outside Host Question Flow. Prove with tests/test_public_route_gate.py using python3 -m unittest tests.test_public_route_gate -v.
- **Request mode:** `implementation`
- **Managed writes allowed:** `false`
- **Execution status:** planning only; no source change, proof command, scanner, or Git operation has run.
- **Plan revision:** active `1`; pending `3`.

## Bound Planning Inputs

| ID | Role | Path or reference | Access | Status | Integrity |
|---|---|---|---|---|---|
| `IN-02` | requirement-artifact | `/Users/vsingha7/Desktop/tailr/TAILTRAIL-HOST-TAILTRAIL-EVIDENCE-VALIDATION-DESIGN.md` | read-only | inspected | `2cdec26124ac3acbf3ad4c8646e8f9608e7bf9d963fb9225623b12e5aec027c6` |
- These inputs remain read-only context and never grant editable implementation scope.

## Command Reference Registry

| ID | Kind | Command |
|---|---|---|
| `cmd-c0e115` | proof | `python3 -m unittest tests.test_public_route_gate -v` |

## Validation Requirements And Focused Validation Matrix

### REQ-01

**Description:** For a Host Question Flow Build request identified by a host-contract transport or a planning-readiness receipt input, require a fresh pre-Start planning-readiness receipt before any Planning Lock. Validate its goal, target, intake run, profile registry version, accepted answers, and requirement-specific proof bindings. Reject a raw host contract alone, an intake-recorded receipt, stale evidence, or a replayed or mismatched receipt with actionable missing-field guidance. Preserve ordinary Start requests that carry neither Host Question Flow input.

- **Requirement type:** `change`
- **Validation state:** `required`
- **Editable owner(s):** `scripts/task-start.py`
- **Read-only input(s):** `TAILTRAIL-HOST-TAILTRAIL-EVIDENCE-VALIDATION-DESIGN.md`, `scripts/intake_pipeline.py`, `scripts/requirement_intake.py`
- **Proof path(s):** `tests/test_public_route_gate.py`
- **Success criteria:** A valid matching planning-readiness receipt allows Host Question Flow Start to continue to scope and Planning Lock.; Ordinary Start routes preserve their current behavior.
- **Preservation criteria:** Raw contracts, intake-recorded receipts, stale or mismatched receipts fail before Planning Lock with actionable missing-field guidance.
- **Requirement behaviour scenarios:**
  - `BHV-REQ-01`: Call the public CLI Start route with an intake-recorded receipt, a stale or mismatched planning-readiness receipt, and a fresh matching planning-readiness receipt. → The first two calls create no Planning Lock and identify the missing or mismatched field; the fresh matching receipt may proceed, while ordinary non-Host-Question-Flow Start remains unchanged.

| Tier | Command ID | Command | Candidate | State |
|---|---|---|---|---|
| behaviour | `cmd-c0e115` | `python3 -m unittest tests.test_public_route_gate -v` | `tests/test_public_route_gate.py` | resolved |
| contract | `cmd-c0e115` | `python3 -m unittest tests.test_public_route_gate -v` | `tests/test_public_route_gate.py` | resolved |
| unit | `cmd-c0e115` | `python3 -m unittest tests.test_public_route_gate -v` | `tests/test_public_route_gate.py` | resolved |

## Plan

1. **REQ-01:** Implement For a Host Question Flow Build request identified by a host-contract transport or a planning-readiness receipt input, require a fresh pre-Start planning-readiness receipt before any Planning Lock. Validate its goal, target, intake run, profile registry version, accepted answers, and requirement-specific proof bindings. Reject a raw host contract alone, an intake-recorded receipt, stale evidence, or a replayed or mismatched receipt with actionable missing-field guidance. Preserve ordinary Start requests that carry neither Host Question Flow input. in `scripts/task-start.py`; verify with `cmd-c0e115`, `cmd-c0e115`, `cmd-c0e115`; inspect `TAILTRAIL-HOST-TAILTRAIL-EVIDENCE-VALIDATION-DESIGN.md`, `scripts/intake_pipeline.py`, `scripts/requirement_intake.py`; prove against `tests/test_public_route_gate.py`.
## Selected TailTrail Features

| Feature | When used | Why it is selected |
|---|---|---|
| Navigator | planning | established the evidence-bound scope and approval boundary |
| Token Autopilot | as required by the plan | selected for this task |
| Bootstrap Snapshot | as required by the plan | selected for this task |
| Code Review Graph Lite | as required by the plan | selected for this task |
| Code Graph Mapper | as required by the plan | selected for this task |
| Learning Capture Trigger | as required by the plan | selected for this task |
| Review Lens | as required by the plan | selected for this task |
| Focused QA Lens | as required by the plan | selected for this task |
| Test Precision Planner | as required by the plan | selected for this task |
| Project Learnings | as required by the plan | selected for this task |
| Learning Refresh Awareness | as required by the plan | selected for this task |

### Required before closure

- **Focused testing and validation:** prove the changed behavior, required preservation cases, and regression boundary with factual computational evidence
- **Canonical completion and closure:** prevent completion while required evidence is missing, unavailable, or failing

## Architecture Analysis

- **Status:** `not selected`. This control is not part of the approved proof boundary for this plan.

## Behaviour Analysis

- **Status:** `not selected`. This control is not part of the approved proof boundary for this plan.

## Focused Validation Coverage Summary

- **Requirements covered:** 1/1.
- **Proof command reuse:**
  - `cmd-c0e115` covers 1 requirement(s): REQ-01.

## Token Estimate

- Unavailable: scope is `ambiguous`, so a token estimate would not be reliable.
- This is an estimate from saved scope, not measured model/provider usage.

## Implementation Boundary

- **Editable scope:** `scripts/task-start.py`.
- **Read-only / proof-only scope:** `TAILTRAIL-HOST-TAILTRAIL-EVIDENCE-VALIDATION-DESIGN.md`, `scripts/intake_pipeline.py`, `scripts/requirement_intake.py`, `tests/test_public_route_gate.py`.
- **Excluded:** every path, command, external system, deployment, and data change not explicitly recorded above remains outside this approval.
- **Data impact:** no data impact is authorized unless a requirement above names it explicitly.

## Approval Checklist

- [x] Requirements are present and reviewable.
- [x] Every requirement has an editable implementation owner.
- [x] Runnable proof commands are registered and mapped to requirements.
- [x] Material questions are resolved.
- [x] Mandatory planning audit is clean for this exact plan revision.
- [ ] The host has reviewed the scope, preservation criteria, proof commands, analyses, and excluded boundary.

## Review Cycles Summary

| Cycle | Revision | Status | Action |
|---|---|---|---|
| 1 | v1 | initial review | Start Plan generated and mandatory audit required |
| 2 | v2 | revision recorded | Plan changed and must be audited again |
| 3 | v3 | revision recorded | Plan changed and must be audited again |

- **Total review cycles:** 3
- **Revision cycles:** 2
- **Latest audit:** `clean`; 0 finding(s).

## Approval Decision

**READY FOR APPROVAL** — review this plan, then explicitly approve this exact run. Approval is separate from activation and permits no unlisted work.

## Canonical Machine Record

- Machine-readable state remains available at [`.tailtrail/runs/start-20261103072319-1120cf/planning/start-report-v1.json`](.tailtrail/runs/start-20261103072319-1120cf/planning/start-report-v1.json); it is not the approval view.

---

*End of Start Plan.*