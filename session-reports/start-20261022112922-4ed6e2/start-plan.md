# TailTrail Start Plan - Full Review Record

**Presentation version:** `4`

## Planning Lock

- **Run ID:** `start-20261022112922-4ed6e2`
- **Status:** `awaiting-approval`
- **Goal:** Make planning revision-show render the pending v2 Start Plan instead of raw JSON.
- **Managed writes allowed:** `false`
- **Execution status:** planning only; no source change, proof command, scanner, or Git operation has run.
- **Plan revision:** active `1`; pending `none`.

## Command Reference Registry

| ID | Kind | Command |
|---|---|---|
| `cmd-1c705e` | proof | `python3 -m unittest discover -s tests -p test_canonical_statement_contract.py -v` |
| `cmd-4aec0d` | proof | `python3 -m unittest tests.test_planning_revision.PlanningRevisionTests.test_revision_show_renders_pending_start_plan` |

## Validation Requirements And Focused Validation Matrix

### REQ-01

**Description:** Make planning revision-show render the pending v2 Start Plan instead of raw JSON

- **Requirement type:** `change`
- **Validation state:** `required`
- **Editable owner(s):** `scripts/planning-revision.py`
- **Read-only input(s):** `scripts/tailtrail.py`, `scripts/task-start.py`
- **Proof path(s):** `tests/test_canonical_statement_contract.py`, `tests/test_planning_audit.py`, `tests/test_planning_lock.py`, `tests/test_planning_revision.py`
- **Success criteria:** The stated requirement is observably satisfied on its approved path.; The public tailtrail planning revision-show route renders the selected pending revision as a readable Start Plan.; The rendered pending plan includes command-registry-backed proof commands.; A public CLI regression invokes the production revision-show route and proves the behavior.
- **Preservation criteria:** Do not change behavior outside this approved requirement boundary.; Revision proposal content, fingerprints, approval state, and persistence remain unchanged.; Normal planning show retains its active-report behavior and raw machine data remains available through its existing artifact.

| Tier | Command ID | Candidate | State |
|---|---|---|---|
| unit | `cmd-1c705e` | `tests/test_canonical_statement_contract.py` | resolved |
| unit | `cmd-4aec0d` | `tests/test_planning_revision.py` | resolved |

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
  - `cmd-1c705e` covers 1 requirement(s): REQ-01.
  - `cmd-4aec0d` covers 1 requirement(s): REQ-01.

## Token Estimate

- **Planned working set:** approximately `8170` tokens (confidence: `medium`).
- **Scoped-file ceiling:** approximately `56790` tokens; estimated reduction `85.61%`.
- **Confidence basis:** at least one bounded slice lacks an exact combined behavior-and-symbol anchor.
- This is an estimate from saved scope, not measured model/provider usage.

## Implementation Boundary

- **Editable scope:** `scripts/planning-revision.py`.
- **Read-only / proof-only scope:** `scripts/tailtrail.py`, `scripts/task-start.py`, `tests/test_canonical_statement_contract.py`, `tests/test_planning_audit.py`, `tests/test_planning_lock.py`, `tests/test_planning_revision.py`.
- **Excluded:** every path, command, external system, deployment, and data change not explicitly recorded above remains outside this approval.
- **Data impact:** no data impact is authorized unless a requirement above names it explicitly.

## Approval Checklist

- [x] Requirements are present and reviewable.
- [x] Every requirement has an editable implementation owner.
- [x] Runnable proof commands are registered and mapped to requirements.
- [x] Material questions are resolved.
- [ ] Mandatory planning audit is clean for this exact plan revision.
- [ ] The host has reviewed the scope, preservation criteria, proof commands, analyses, and excluded boundary.

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

- Machine-readable state remains available at [`.tailtrail/runs/start-20261022112922-4ed6e2/planning/start-report-v1.json`](.tailtrail/runs/start-20261022112922-4ed6e2/planning/start-report-v1.json); it is not the approval view.

---

*End of Start Plan.*