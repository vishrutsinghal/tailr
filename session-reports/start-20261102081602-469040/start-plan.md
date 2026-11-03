# TailTrail Start Plan - Full Review Record

**Presentation version:** `4`

## Planning Lock

- **Run ID:** `start-20261102081602-469040`
- **Status:** `awaiting-approval`
- **Goal:** Add explicit host-contract proof bindings that map an approved proof command only to named requirements in multi-requirement Start Plans.
- **Request mode:** `implementation`
- **Managed writes allowed:** `false`
- **Execution status:** planning only; no source change, proof command, scanner, or Git operation has run.
- **Plan revision:** active `1`; pending `2`.

## Bound Planning Inputs

- No read-only planning inputs were bound to this plan.

## Command Reference Registry

| ID | Kind | Command |
|---|---|---|
| `cmd-4206f5` | proof | `python3 -m unittest tests.test_cli_dispatch -v` |
| `cmd-bfabe8` | proof | `python3 -m unittest tests.test_host_contract -v` |

## Validation Requirements And Focused Validation Matrix

### REQ-01

**Description:** Add explicit host-contract proof bindings

- **Requirement type:** `change`
- **Validation state:** `required`
- **Editable owner(s):** `scripts/host_contract.py`
- **Read-only input(s):** `scripts/task-start.py`, `schemas/host-input-contract.schema.json`, `schemas/proof-binding.schema.json`
- **Proof path(s):** `tests/test_host_contract.py`, `tests/test_cli_dispatch.py`
- **Success criteria:** Extend the existing versioned TailTrail host-input contract; this is an internal contract, not an external endpoint.
- **Preservation criteria:** Do not change behavior outside this approved requirement boundary.

| Tier | Command ID | Command | Candidate | State |
|---|---|---|---|---|
| unit | `cmd-bfabe8` | `python3 -m unittest tests.test_host_contract -v` | `tests/test_host_contract.py` | resolved |
| contract | `cmd-4206f5` | `python3 -m unittest tests.test_cli_dispatch -v` | `tests/test_cli_dispatch.py` | resolved |

### REQ-02

**Description:** map an approved proof command only to named requirements

- **Requirement type:** `change`
- **Validation state:** `required`
- **Editable owner(s):** `scripts/host_contract.py`
- **Read-only input(s):** `scripts/task-start.py`, `schemas/host-input-contract.schema.json`, `schemas/proof-binding.schema.json`
- **Proof path(s):** `tests/test_host_contract.py`
- **Success criteria:** Define explicit fail-closed cases for an omitted requirement mapping, duplicate/conflicting mappings, an unrelated proof path or command, and stale evidence.
- **Preservation criteria:** Do not change behavior outside this approved requirement boundary.

| Tier | Command ID | Command | Candidate | State |
|---|---|---|---|---|
| unit | `cmd-bfabe8` | `python3 -m unittest tests.test_host_contract -v` | `tests/test_host_contract.py` | resolved |

### REQ-03

**Description:** multi-requirement Start Plans

- **Requirement type:** `constraint`
- **Validation state:** `required`
- **Editable owner(s):** `scripts/host_contract.py`
- **Read-only input(s):** `scripts/task-start.py`, `schemas/host-input-contract.schema.json`, `schemas/proof-binding.schema.json`
- **Proof path(s):** `tests/test_host_contract.py`
- **Success criteria:** The stated requirement is observably satisfied on its approved path.; AIDLC answer set is reflected in the approved requirement boundary.
- **Preservation criteria:** Do not change behavior outside this approved requirement boundary.

| Tier | Command ID | Command | Candidate | State |
|---|---|---|---|---|
| unit | `cmd-bfabe8` | `python3 -m unittest tests.test_host_contract -v` | `tests/test_host_contract.py` | resolved |

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
  - `cmd-4206f5` covers 1 requirement(s): REQ-01.
  - `cmd-bfabe8` covers 3 requirement(s): REQ-01, REQ-02, REQ-03.

## Token Estimate

- **Planned working set:** approximately `327` tokens (confidence: `medium`).
- **Scoped-file ceiling:** approximately `5918` tokens; estimated reduction `94.47%`.
- **Confidence basis:** at least one bounded slice lacks an exact combined behavior-and-symbol anchor.
- This is an estimate from saved scope, not measured model/provider usage.

## Implementation Boundary

- **Editable scope:** `scripts/host_contract.py`.
- **Read-only / proof-only scope:** `schemas/host-input-contract.schema.json`, `schemas/proof-binding.schema.json`, `scripts/task-start.py`, `tests/test_cli_dispatch.py`, `tests/test_host_contract.py`.
- **Excluded:** every path, command, external system, deployment, and data change not explicitly recorded above remains outside this approval.
- **Data impact:** no data impact is authorized unless a requirement above names it explicitly.

## Approval Checklist

- [x] Requirements are present and reviewable.
- [x] Every requirement has an editable implementation owner.
- [x] Runnable proof commands are registered and mapped to requirements.
- [x] Material questions are resolved.
- [ ] Mandatory planning audit is clean for this exact plan revision.
- [ ] The host has reviewed the scope, preservation criteria, proof commands, analyses, and excluded boundary.

## AIDLC Decisions

- AIDLC authority artifacts are present: `aidlc-correction-observations-v1.json`, `aidlc-correction-projection-v1.json`, `aidlc-correction-state.json`, `aidlc-requirements-v1.json`, `aidlc-revised-requirements-v1.json`.
- **Q1:** Which existing contract must the new behavior extend or preserve?
- **Q2:** Which success, validation, conflict, and failure outcomes must clients observe?
- **Q3:** What proof is required for the caller path?
- **Q4:** How should this prior review concern change the requirement boundary: The v1 scope authorizes only host-contract validation, while the requested end-to-end verification-binding feature also requires schema and Start-plan projection work.

## Review Cycles Summary

| Cycle | Revision | Status | Action |
|---|---|---|---|
| 1 | v1 | initial review | Start Plan generated and mandatory audit required |
| 2 | v2 | revision recorded | Plan changed and must be audited again |

- **Total review cycles:** 2
- **Revision cycles:** 1
- **Latest audit:** `gaps-found`; 8 finding(s).

## Approval Decision

**NOT READY FOR APPROVAL** — resolve or revise: a clean mandatory planning audit.

## Canonical Machine Record

- Machine-readable state remains available at [`.tailtrail/runs/start-20261102081602-469040/planning/start-report-v1.json`](.tailtrail/runs/start-20261102081602-469040/planning/start-report-v1.json); it is not the approval view.

---

*End of Start Plan.*