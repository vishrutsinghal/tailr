# TailTrail Start Plan - Full Review Record

**Presentation version:** `5`

## Planning Lock

- **Run ID:** `start-20261102152103-bf5a8c`
- **Status:** `approved`
- **Goal:** Fix the pipeline evidence-selection defect so the TESTING-to-INFRA gate evaluates the current compatible proof result per approved binding while retaining superseded attempts as history.
- **Request mode:** `implementation`
- **Managed writes allowed:** `true`
- **Execution status:** planning only; no source change, proof command, scanner, or Git operation has run.
- **Plan revision:** active `1`; pending `none`.

## Bound Planning Inputs

- No read-only planning inputs were bound to this plan.

## Command Reference Registry

| ID | Kind | Command |
|---|---|---|
| `cmd-817eac` | proof | `python3 -m unittest discover -s tests -p test_drift_analysis.py -v` |
| `cmd-d36598` | proof | `python3 -m unittest tests.test_drift_analysis -q` |

## Validation Requirements And Focused Validation Matrix

### REQ-01

**Description:** Fix the pipeline evidence-selection defect so the TESTING-to-INFRA gate evaluates the current compatible proof result per approved binding while retaining superseded attempts as history.

- **Requirement type:** `change`
- **Validation state:** `required`
- **Editable owner(s):** `scripts/drift_analysis.py`
- **Read-only input(s):** `scripts/pipeline_judge.py`
- **Proof path(s):** `tests/test_drift_analysis.py`
- **Success criteria:** A later compatible passing proof result permits the TESTING-to-INFRA gate for its approved binding.; The selected current result is derived per approved proof binding while earlier attempts remain visible as history.
- **Preservation criteria:** A result with a different approved plan, source state, command, tier, or scenario must not replace the selected current result.; A later compatible failing proof result must block the gate.

| Tier | Command ID | Command | Candidate | State |
|---|---|---|---|---|
| unit | `cmd-817eac` | `python3 -m unittest discover -s tests -p test_drift_analysis.py -v` | `tests/test_drift_analysis.py` | resolved |
| unit | `cmd-d36598` | `python3 -m unittest tests.test_drift_analysis -q` | `tests/test_drift_analysis.py` | resolved |

## Plan

1. **REQ-01:** Implement Fix the pipeline evidence-selection defect so the TESTING-to-INFRA gate evaluates the current compatible proof result per approved binding while retaining superseded attempts as history. in `scripts/drift_analysis.py`; verify with `cmd-817eac`, `cmd-d36598`; inspect `scripts/pipeline_judge.py`; prove against `tests/test_drift_analysis.py`.
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
| CI/Sonar Intelligence | as required by the plan | selected for this task |
| QA / CI-Sonar Lens | as required by the plan | selected for this task |
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
  - `cmd-817eac` covers 1 requirement(s): REQ-01.
  - `cmd-d36598` covers 1 requirement(s): REQ-01.

## Token Estimate

- **Planned working set:** approximately `2550` tokens (confidence: `medium`).
- **Scoped-file ceiling:** approximately `11902` tokens; estimated reduction `78.58%`.
- **Confidence basis:** at least one bounded slice lacks an exact combined behavior-and-symbol anchor.
- This is an estimate from saved scope, not measured model/provider usage.

## Implementation Boundary

- **Editable scope:** `scripts/drift_analysis.py`.
- **Read-only / proof-only scope:** `scripts/pipeline_judge.py`, `tests/test_drift_analysis.py`.
- **Excluded:** every path, command, external system, deployment, and data change not explicitly recorded above remains outside this approval.
- **Data impact:** no data impact is authorized unless a requirement above names it explicitly.

## Approval Checklist

- [x] Requirements are present and reviewable.
- [x] Every requirement has an editable implementation owner.
- [x] Runnable proof commands are registered and mapped to requirements.
- [x] Material questions are resolved.
- [x] Mandatory planning audit is clean for this exact plan revision.
- [ ] The host has reviewed the scope, preservation criteria, proof commands, analyses, and excluded boundary.
- **Risks to review:** ci/sonar

## Review Cycles Summary

| Cycle | Revision | Status | Action |
|---|---|---|---|
| 1 | v1 | initial review | Start Plan generated and mandatory audit required |

- **Total review cycles:** 1
- **Revision cycles:** 0
- **Latest audit:** `clean`; 0 finding(s).

## Approval Decision

**READY FOR APPROVAL** — review this plan, then explicitly approve this exact run. Approval is separate from activation and permits no unlisted work.

## Canonical Machine Record

- Machine-readable state remains available at [`.tailtrail/runs/start-20261102152103-bf5a8c/planning/start-report-v1.json`](.tailtrail/runs/start-20261102152103-bf5a8c/planning/start-report-v1.json); it is not the approval view.

---

*End of Start Plan.*