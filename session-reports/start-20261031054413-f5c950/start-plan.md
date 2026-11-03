# TailTrail Start Plan - Full Review Record

**Presentation version:** `4`

## Planning Lock

- **Run ID:** `start-20261031054413-f5c950`
- **Status:** `approved`
- **Goal:** Phase 1A: establish a canonical append-only validation-evidence projection in scripts/closure-recorder.py. It must select the latest valid managed receipt per active approved requirement, command, and tier; retain prior attempts with explicit supersession metadata; and expose evidence-stream version metadata so downstream reports can detect stale closure snapshots. Do not wire completion-report.py or closure-finalizer.py in this phase.
- **Request mode:** `implementation`
- **Managed writes allowed:** `true`
- **Execution status:** planning only; no source change, proof command, scanner, or Git operation has run.
- **Plan revision:** active `5`; pending `none`.

## Bound Planning Inputs

- No read-only planning inputs were bound to this plan.

## Command Reference Registry

| ID | Kind | Command |
|---|---|---|
| `cmd-dfbd49` | proof | `python3 -m unittest tests.test_closure_recorder tests.test_closure_close -v` |

## Validation Requirements And Focused Validation Matrix

### REQ-01

**Description:** Phase 1A: establish a canonical append-only validation-evidence projection in scripts/closure-recorder.py. It must select the latest valid managed receipt per active approved requirement, command, and tier

- **Requirement type:** `constraint`
- **Validation state:** `required`
- **Editable owner(s):** `scripts/closure-recorder.py`
- **Read-only input(s):** `scripts/closure-finalizer.py`, `scripts/completion-report.py`
- **Proof path(s):** `tests/test_closure_recorder.py`, `tests/test_closure_close.py`
- **Success criteria:** The stated requirement is observably satisfied on its approved path.
- **Preservation criteria:** Do not change behavior outside this approved requirement boundary.
- **Requirement behaviour scenarios:**
  - `BHV-REQ-01`: Record a failed managed proof attempt and then a passing retry for the same active requirement-command-tier binding, then collect closure input. → The current projection selects only the later passing receipt for that binding.

| Tier | Command ID | Candidate | State |
|---|---|---|---|
| unit | `cmd-dfbd49` | `tests/test_closure_recorder.py` | resolved |
| contract | `cmd-dfbd49` | `tests/test_closure_recorder.py` | resolved |
| behaviour | `cmd-dfbd49` | `tests/test_closure_recorder.py` | resolved |
| unit | `cmd-dfbd49` | `tests/test_closure_recorder.py` | resolved |
| contract | `cmd-dfbd49` | `tests/test_closure_recorder.py` | resolved |
| behaviour | `cmd-dfbd49` | `tests/test_closure_recorder.py` | resolved |

### REQ-02

**Description:** retain prior attempts with explicit supersession metadata

- **Requirement type:** `change`
- **Validation state:** `required`
- **Editable owner(s):** `scripts/closure-recorder.py`
- **Read-only input(s):** `scripts/closure-finalizer.py`, `scripts/completion-report.py`
- **Proof path(s):** `tests/test_closure_recorder.py`, `tests/test_closure_close.py`
- **Success criteria:** The stated requirement is observably satisfied on its approved path.
- **Preservation criteria:** Do not change behavior outside this approved requirement boundary.
- **Requirement behaviour scenarios:**
  - `BHV-REQ-02`: Inspect the projection after a later compatible retry replaces an earlier attempt. → The earlier attempt remains available in history and is marked as superseded by the selected retry.

| Tier | Command ID | Candidate | State |
|---|---|---|---|
| unit | `cmd-dfbd49` | `tests/test_closure_recorder.py` | resolved |
| contract | `cmd-dfbd49` | `tests/test_closure_recorder.py` | resolved |
| behaviour | `cmd-dfbd49` | `tests/test_closure_recorder.py` | resolved |
| unit | `cmd-dfbd49` | `tests/test_closure_recorder.py` | resolved |
| contract | `cmd-dfbd49` | `tests/test_closure_recorder.py` | resolved |
| behaviour | `cmd-dfbd49` | `tests/test_closure_recorder.py` | resolved |

### REQ-03

**Description:** and expose evidence-stream version metadata so downstream reports can detect stale closure snapshots. Do not wire completion-report.py or closure-finalizer.py in this phase

- **Requirement type:** `change`
- **Validation state:** `required`
- **Editable owner(s):** `scripts/closure-recorder.py`
- **Read-only input(s):** `scripts/closure-finalizer.py`, `scripts/completion-report.py`
- **Proof path(s):** `tests/test_closure_recorder.py`, `tests/test_closure_close.py`
- **Success criteria:** The stated requirement is observably satisfied on its approved path.
- **Preservation criteria:** Do not change behavior outside this approved requirement boundary.
- **Requirement behaviour scenarios:**
  - `BHV-REQ-03`: Append a compatible managed retry to the evidence stream and build the projection again. → The stream version changes deterministically and the projection identifies the new selected receipt.

| Tier | Command ID | Candidate | State |
|---|---|---|---|
| unit | `cmd-dfbd49` | `tests/test_closure_recorder.py` | resolved |
| contract | `cmd-dfbd49` | `tests/test_closure_recorder.py` | resolved |
| behaviour | `cmd-dfbd49` | `tests/test_closure_recorder.py` | resolved |
| unit | `cmd-dfbd49` | `tests/test_closure_recorder.py` | resolved |
| contract | `cmd-dfbd49` | `tests/test_closure_recorder.py` | resolved |
| behaviour | `cmd-dfbd49` | `tests/test_closure_recorder.py` | resolved |

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

- **Requirements covered:** 3/3.
- **Proof command reuse:**
  - `cmd-dfbd49` covers 3 requirement(s): REQ-01, REQ-02, REQ-03.

## Token Estimate

- Unavailable: scope is `ambiguous`, so a token estimate would not be reliable.
- This is an estimate from saved scope, not measured model/provider usage.

## Implementation Boundary

- **Editable scope:** `scripts/closure-recorder.py`.
- **Read-only / proof-only scope:** `scripts/closure-finalizer.py`, `scripts/completion-report.py`, `tests/test_closure_close.py`, `tests/test_closure_recorder.py`.
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
| 4 | v4 | revision recorded | Plan changed and must be audited again |
| 5 | v5 | revision recorded | Plan changed and must be audited again |

- **Total review cycles:** 5
- **Revision cycles:** 4
- **Latest audit:** `clean`; 0 finding(s).

## Approval Decision

**READY FOR APPROVAL** — review this plan, then explicitly approve this exact run. Approval is separate from activation and permits no unlisted work.

## Canonical Machine Record

- Machine-readable state remains available at [`.tailtrail/runs/start-20261031054413-f5c950/planning/revisions/start-report-v5.json`](.tailtrail/runs/start-20261031054413-f5c950/planning/revisions/start-report-v5.json); it is not the approval view.

---

*End of Start Plan.*