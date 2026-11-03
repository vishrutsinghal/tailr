# TailTrail Start Plan - Full Review Record

**Presentation version:** `5`

## Planning Lock

- **Run ID:** `start-20261103054352-bcd52d`
- **Status:** `awaiting-approval`
- **Goal:** Make pending planning revisions preserve non-conflicting approved proof and scenario changes so a later additive proposal cannot silently discard an earlier pending delta.
- **Request mode:** `implementation`
- **Managed writes allowed:** `false`
- **Execution status:** planning only; no source change, proof command, scanner, or Git operation has run.
- **Plan revision:** active `1`; pending `none`.

## Bound Planning Inputs

- No read-only planning inputs were bound to this plan.

## Command Reference Registry

| ID | Kind | Command |
|---|---|---|
| `cmd-2979fd` | proof | `python3 -m unittest tests.test_planning_revision -q` |
| `cmd-353d0e` | proof | `python3 -m unittest discover -s tests -p planning_proof_fixture.py -v` |

## Validation Requirements And Focused Validation Matrix

### REQ-01

**Description:** Make pending planning revisions preserve non-conflicting approved proof and scenario changes so a later additive proposal cannot silently discard an earlier pending delta.

- **Requirement type:** `change`
- **Validation state:** `required`
- **Editable owner(s):** `scripts/planning-revision.py`
- **Read-only input(s):** `scripts/planning-audit.py`
- **Proof path(s):** `tests/planning_proof_fixture.py`, `tests/test_canonical_statement_contract.py`, `tests/test_planning_audit.py`, `tests/test_planning_revision.py`
- **Success criteria:** A later additive pending revision retains all non-conflicting proof and behaviour-scenario changes from the earlier pending revision.; The rendered pending revision discloses the merged source revisions and the complete resulting change set.
- **Preservation criteria:** A later pending proposal cannot silently discard an earlier approved proof binding.; Conflicting revision changes cannot be merged or discarded without an explicit fail-closed decision.

| Tier | Command ID | Command | Candidate | State |
|---|---|---|---|---|
| unit | `cmd-353d0e` | `python3 -m unittest discover -s tests -p planning_proof_fixture.py -v` | `tests/planning_proof_fixture.py` | resolved |
| unit | `cmd-2979fd` | `python3 -m unittest tests.test_planning_revision -q` | `tests/test_planning_revision.py` | resolved |

## Plan

1. **REQ-01:** Implement Make pending planning revisions preserve non-conflicting approved proof and scenario changes so a later additive proposal cannot silently discard an earlier pending delta. in `scripts/planning-revision.py`; verify with `cmd-353d0e`, `cmd-2979fd`; inspect `scripts/planning-audit.py`; prove against `tests/planning_proof_fixture.py`, `tests/test_canonical_statement_contract.py`, `tests/test_planning_audit.py`, `tests/test_planning_revision.py`.
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
  - `cmd-2979fd` covers 1 requirement(s): REQ-01.
  - `cmd-353d0e` covers 1 requirement(s): REQ-01.

## Token Estimate

- **Planned working set:** approximately `5588` tokens (confidence: `medium`).
- **Scoped-file ceiling:** approximately `36418` tokens; estimated reduction `84.66%`.
- **Confidence basis:** at least one bounded slice lacks an exact combined behavior-and-symbol anchor.
- This is an estimate from saved scope, not measured model/provider usage.

## Implementation Boundary

- **Editable scope:** `scripts/planning-revision.py`.
- **Read-only / proof-only scope:** `scripts/planning-audit.py`, `tests/planning_proof_fixture.py`, `tests/test_canonical_statement_contract.py`, `tests/test_planning_audit.py`, `tests/test_planning_revision.py`.
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

- **Total review cycles:** 1
- **Revision cycles:** 0
- **Latest audit:** `clean`; 0 finding(s).

## Approval Decision

**READY FOR APPROVAL** — review this plan, then explicitly approve this exact run. Approval is separate from activation and permits no unlisted work.

## Canonical Machine Record

- Machine-readable state remains available at [`.tailtrail/runs/start-20261103054352-bcd52d/planning/start-report-v1.json`](.tailtrail/runs/start-20261103054352-bcd52d/planning/start-report-v1.json); it is not the approval view.

---

*End of Start Plan.*