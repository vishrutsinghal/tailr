# TailTrail Start Plan - Full Review Record

**Presentation version:** `5`

## Planning Lock

- **Run ID:** `start-20261103055428-bf2e84`
- **Status:** `approved`
- **Goal:** Make closure finalization explain stale managed evidence and the required recovery order instead of reporting only a generic missing receipt error.
- **Request mode:** `implementation`
- **Managed writes allowed:** `true`
- **Execution status:** planning only; no source change, proof command, scanner, or Git operation has run.
- **Plan revision:** active `3`; pending `none`.

## Bound Planning Inputs

- No read-only planning inputs were bound to this plan.

## Command Reference Registry

| ID | Kind | Command |
|---|---|---|
| `cmd-2f4137` | proof | `python3 -m unittest tests.test_closure_finalizer -q` |

## Validation Requirements And Focused Validation Matrix

### REQ-01

**Description:** Make closure finalization explain stale managed evidence and the required recovery order instead of reporting only a generic missing receipt error.

- **Requirement type:** `change`
- **Validation state:** `required`
- **Editable owner(s):** `scripts/closure-finalizer.py`
- **Read-only input(s):** `scripts/closure-close.py`, `scripts/closure-contract.py`, `scripts/closure-recorder.py`, `scripts/tailtrail.py`
- **Proof path(s):** `tests/test_closure_finalizer.py`
- **Success criteria:** Closure finalization identifies saved stale managed evidence by receipt identity and rejection reason.; The public failure guidance gives the exact recovery order: record source edits, rerun the approved managed command, record closure, then finalize.
- **Preservation criteria:** Stale evidence cannot be selected as current proof or permit successful closure.; A missing current receipt is not reduced to an opaque generic missing-receipt error when stale managed evidence explains the condition.
- **Requirement behaviour scenarios:**
  - `BHV-ISSUE-45-STALE-CLOSURE`: Run the public closure-finalize route after a source edit makes every managed proof receipt stale → The route identifies stale evidence, gives the exact recovery order and approved rerun command, and does not finalize successfully

| Tier | Command ID | Command | Candidate | State |
|---|---|---|---|---|
| behaviour | `cmd-2f4137` | `python3 -m unittest tests.test_closure_finalizer -q` | `tests/test_closure_finalizer.py` | resolved |
| unit | `cmd-2f4137` | `python3 -m unittest tests.test_closure_finalizer -q` | `tests/test_closure_finalizer.py` | resolved |

## Plan

1. **REQ-01:** Implement Make closure finalization explain stale managed evidence and the required recovery order instead of reporting only a generic missing receipt error. in `scripts/closure-finalizer.py`; verify with `cmd-2f4137`, `cmd-2f4137`; inspect `scripts/closure-close.py`, `scripts/closure-contract.py`, `scripts/closure-recorder.py`, `scripts/tailtrail.py`; prove against `tests/test_closure_finalizer.py`.
## Selected TailTrail Features

| Feature | When used | Why it is selected |
|---|---|---|
| Navigator | planning | established the evidence-bound scope and approval boundary |
| Token Autopilot | as required by the plan | selected for this task |
| Bootstrap Snapshot | as required by the plan | selected for this task |
| Code Review Graph Lite | as required by the plan | selected for this task |
| Code Graph Mapper | as required by the plan | selected for this task |
| Learning Capture Trigger | as required by the plan | selected for this task |
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
  - `cmd-2f4137` covers 1 requirement(s): REQ-01.

## Token Estimate

- **Planned working set:** approximately `1535` tokens (confidence: `medium`).
- **Scoped-file ceiling:** approximately `10168` tokens; estimated reduction `84.9%`.
- **Confidence basis:** at least one bounded slice lacks an exact combined behavior-and-symbol anchor.
- This is an estimate from saved scope, not measured model/provider usage.

## Implementation Boundary

- **Editable scope:** `scripts/closure-finalizer.py`.
- **Read-only / proof-only scope:** `scripts/closure-close.py`, `scripts/closure-contract.py`, `scripts/closure-recorder.py`, `scripts/tailtrail.py`, `tests/test_closure_finalizer.py`.
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

- Machine-readable state remains available at [`.tailtrail/runs/start-20261103055428-bf2e84/planning/revisions/start-report-v3.json`](.tailtrail/runs/start-20261103055428-bf2e84/planning/revisions/start-report-v3.json); it is not the approval view.

---

*End of Start Plan.*