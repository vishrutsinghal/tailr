# TailTrail Start Plan - Full Review Record

**Presentation version:** `4`

## Planning Lock

- **Run ID:** `start-20261031071731-d2bb65`
- **Status:** `awaiting-approval`
- **Goal:** Make the host-declared scope the single contract that limits editable paths in navigator scope. Declared --changed paths are evaluated first. Discovery only proposes inspection or proof candidates and cannot add editable owners. Every proposed owner must cite an edge back to a declared path, otherwise it becomes an open question. Test-only requests narrow editable scope to declared test paths before discovery. Generic goal words must not pull production files into scope.
- **Request mode:** `implementation`
- **Managed writes allowed:** `false`
- **Execution status:** planning only; no source change, proof command, scanner, or Git operation has run.
- **Plan revision:** active `1`; pending `none`.

## Bound Planning Inputs

- No read-only planning inputs were bound to this plan.

## Command Reference Registry

| ID | Kind | Command |
|---|---|---|
| `cmd-3bf405` | proof | `python3 -m unittest discover -s tests -p test_navigator_scope.py -v` |

## Validation Requirements And Focused Validation Matrix

### REQ-01

**Description:** Make the host-declared scope the single contract that limits editable paths in navigator scope.

- **Requirement type:** `change`
- **Validation state:** `required`
- **Editable owner(s):** `scripts/navigator_scope.py`
- **Proof path(s):** `tests/test_navigator_scope.py`
- **Success criteria:** The stated requirement is observably satisfied on its approved path.
- **Preservation criteria:** Do not change behavior outside this approved requirement boundary.

| Tier | Command ID | Candidate | State |
|---|---|---|---|
| unresolved | `unresolved` | `not recorded` | unresolved |

### REQ-02

**Description:** Declared --changed paths are evaluated first.

- **Requirement type:** `change`
- **Validation state:** `required`
- **Editable owner(s):** `scripts/navigator_scope.py`
- **Proof path(s):** `tests/test_navigator_scope.py`
- **Success criteria:** The stated requirement is observably satisfied on its approved path.
- **Preservation criteria:** Do not change behavior outside this approved requirement boundary.

| Tier | Command ID | Candidate | State |
|---|---|---|---|
| unit | `cmd-3bf405` | `tests/test_navigator_scope.py` | resolved |

### REQ-03

**Description:** Discovery only proposes inspection or proof candidates and cannot add editable owners.

- **Requirement type:** `constraint`
- **Validation state:** `required`
- **Editable owner(s):** `scripts/navigator_scope.py`
- **Proof path(s):** `tests/test_navigator_scope.py`
- **Success criteria:** The stated requirement is observably satisfied on its approved path.
- **Preservation criteria:** Do not change behavior outside this approved requirement boundary.

| Tier | Command ID | Candidate | State |
|---|---|---|---|
| unit | `cmd-3bf405` | `tests/test_navigator_scope.py` | resolved |

### REQ-04

**Description:** Every proposed owner must cite an edge back to a declared path, otherwise it becomes an open question.

- **Requirement type:** `change`
- **Validation state:** `required`
- **Editable owner(s):** `scripts/navigator_scope.py`
- **Proof path(s):** `tests/test_navigator_scope.py`
- **Success criteria:** The stated requirement is observably satisfied on its approved path.
- **Preservation criteria:** Do not change behavior outside this approved requirement boundary.

| Tier | Command ID | Candidate | State |
|---|---|---|---|
| unit | `cmd-3bf405` | `tests/test_navigator_scope.py` | resolved |

### REQ-05

**Description:** Test-only requests narrow editable scope to declared test paths before discovery.

- **Requirement type:** `constraint`
- **Validation state:** `required`
- **Editable owner(s):** `scripts/navigator_scope.py`
- **Proof path(s):** `tests/test_navigator_scope.py`
- **Success criteria:** The stated requirement is observably satisfied on its approved path.
- **Preservation criteria:** Do not change behavior outside this approved requirement boundary.

| Tier | Command ID | Candidate | State |
|---|---|---|---|
| unit | `cmd-3bf405` | `tests/test_navigator_scope.py` | resolved |

### REQ-06

**Description:** Generic goal words must not pull production files into scope.

- **Requirement type:** `constraint`
- **Validation state:** `required`
- **Editable owner(s):** `scripts/navigator_scope.py`
- **Proof path(s):** `tests/test_navigator_scope.py`
- **Success criteria:** The stated requirement is observably satisfied on its approved path.
- **Preservation criteria:** Do not change behavior outside this approved requirement boundary.

| Tier | Command ID | Candidate | State |
|---|---|---|---|
| unit | `cmd-3bf405` | `tests/test_navigator_scope.py` | resolved |

## Selected TailTrail Features

| Feature | When used | Why it is selected |
|---|---|---|
| Navigator | planning | established the evidence-bound scope and approval boundary |
| Token Autopilot | as required by the plan | selected for this task |
| Bootstrap Snapshot | as required by the plan | selected for this task |
| Code Review Graph Lite | as required by the plan | selected for this task |
| Code Graph Mapper | as required by the plan | selected for this task |
| Learning Capture Trigger | as required by the plan | selected for this task |
| AIDLC | as required by the plan | selected for this task |
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

- **Requirements covered:** 5/6.
- **Proof command reuse:**
  - `cmd-3bf405` covers 5 requirement(s): REQ-02, REQ-03, REQ-04, REQ-05, REQ-06.

## Token Estimate

- **Planned working set:** approximately `17169` tokens (confidence: `medium`).
- **Scoped-file ceiling:** approximately `66745` tokens; estimated reduction `74.28%`.
- **Confidence basis:** at least one bounded slice lacks an exact combined behavior-and-symbol anchor.
- This is an estimate from saved scope, not measured model/provider usage.

## Implementation Boundary

- **Editable scope:** `scripts/navigator_scope.py`.
- **Read-only / proof-only scope:** `tests/test_navigator_scope.py`.
- **Excluded:** every path, command, external system, deployment, and data change not explicitly recorded above remains outside this approval.
- **Data impact:** no data impact is authorized unless a requirement above names it explicitly.

## Approval Checklist

- [x] Requirements are present and reviewable.
- [x] Every requirement has an editable implementation owner.
- [x] Runnable proof commands are registered and mapped to requirements.
- [x] Material questions are resolved.
- [ ] Mandatory planning audit is clean for this exact plan revision.
- [ ] The host has reviewed the scope, preservation criteria, proof commands, analyses, and excluded boundary.
- **Risks to review:** production

## Review Cycles Summary

| Cycle | Revision | Status | Action |
|---|---|---|---|
| 1 | v1 | initial review | Start Plan generated and mandatory audit required |

- **Total review cycles:** 1
- **Revision cycles:** 0
- **Latest audit:** not yet recorded. Run the mandatory planning audit before approval.

## Approval Decision

**NOT READY FOR APPROVAL** — resolve or revise: a clean mandatory planning audit.

## Canonical Machine Record

- Machine-readable state remains available at [`.tailtrail/runs/start-20261031071731-d2bb65/planning/start-report-v1.json`](.tailtrail/runs/start-20261031071731-d2bb65/planning/start-report-v1.json); it is not the approval view.

---

*End of Start Plan.*