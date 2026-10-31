# TailTrail Start Plan - Full Review Record

**Presentation version:** `4`

## Planning Lock

- **Run ID:** `start-20261030123049-4edd0a`
- **Status:** `approved`
- **Goal:** Render every bound planning input in both the initial Start Plan and every pending revision view, preserve each input's path, role, access, status, and recorded SHA-256 provenance, and never promote a read-only input to editable scope or hide unavailable integrity.
- **Request mode:** `implementation`
- **Managed writes allowed:** `true`
- **Execution status:** planning only; no source change, proof command, scanner, or Git operation has run.
- **Plan revision:** active `3`; pending `none`.

## Command Reference Registry

| ID | Kind | Command |
|---|---|---|
| `cmd-39aabc` | proof | `python3 -m unittest tests.test_planning_revision tests.test_start_plan_presentation -v` |
| `cmd-dcb44d` | proof | `python3 -m unittest discover -s tests -p test_start_plan_presentation.py -v` |

## Validation Requirements And Focused Validation Matrix

### REQ-01

**Description:** Render every bound planning input in both the initial Start Plan and every pending revision view

- **Requirement type:** `change`
- **Validation state:** `required`
- **Editable owner(s):** `scripts/verbose-reporting.py`
- **Read-only input(s):** `scripts/closure-finalizer.py`, `scripts/planning_lock.py`
- **Proof path(s):** `tests/test_planning_revision.py`, `tests/test_start_plan_presentation.py`
- **Success criteria:** The stated requirement is observably satisfied on its approved path.
- **Preservation criteria:** Do not change behavior outside this approved requirement boundary.
- **Requirement behaviour scenarios:**
  - `BHV-REQ-01`: Render a Start Plan with a bound read-only planning input, propose a pending revision, and render that revision through planning revision-show. → Both human-readable plans list the input locator, its read-only role, access and status, and its recorded SHA-256 when present without adding it to editable scope.

| Tier | Command ID | Candidate | State |
|---|---|---|---|
| unit | `cmd-dcb44d` | `tests/test_start_plan_presentation.py` | resolved |
| unit | `cmd-39aabc` | `tests/test_planning_revision.py` | resolved |
| behaviour | `cmd-39aabc` | `tests/test_planning_revision.py` | resolved |
| integration | `cmd-39aabc` | `tests/test_planning_revision.py` | resolved |

### REQ-02

**Description:** preserve each input's path, role, access, status, and recorded SHA-256 provenance

- **Requirement type:** `constraint`
- **Validation state:** `required`
- **Editable owner(s):** `scripts/verbose-reporting.py`
- **Read-only input(s):** `scripts/closure-finalizer.py`, `scripts/planning_lock.py`
- **Proof path(s):** `tests/test_planning_revision.py`, `tests/test_start_plan_presentation.py`
- **Success criteria:** The stated requirement is observably satisfied on its approved path.
- **Preservation criteria:** Do not change behavior outside this approved requirement boundary.
- **Requirement behaviour scenarios:**
  - `BHV-02`: Compare the approved observable behaviour through the existing project boundary before and after the change. → The refactor changes internal structure without changing approved observable behaviour.
  - `BHV-01`: Execute the approved user-visible workflow using the existing application boundaries. → Each authoritative transition is observable in order through the customer/API surface.

| Tier | Command ID | Candidate | State |
|---|---|---|---|
| unit | `cmd-dcb44d` | `tests/test_start_plan_presentation.py` | resolved |
| unit | `cmd-39aabc` | `tests/test_planning_revision.py` | resolved |
| behaviour | `cmd-39aabc` | `tests/test_planning_revision.py` | resolved |
| integration | `cmd-39aabc` | `tests/test_planning_revision.py` | resolved |

### REQ-03

**Description:** never promote a read-only input to editable scope or hide unavailable integrity

- **Requirement type:** `safety`
- **Validation state:** `required`
- **Editable owner(s):** `scripts/verbose-reporting.py`
- **Read-only input(s):** `scripts/closure-finalizer.py`, `scripts/planning_lock.py`
- **Proof path(s):** `tests/test_planning_revision.py`, `tests/test_start_plan_presentation.py`
- **Success criteria:** The stated requirement is observably satisfied on its approved path.
- **Preservation criteria:** Do not change behavior outside this approved requirement boundary.

| Tier | Command ID | Candidate | State |
|---|---|---|---|
| unit | `cmd-dcb44d` | `tests/test_start_plan_presentation.py` | resolved |
| unit | `cmd-39aabc` | `tests/test_planning_revision.py` | resolved |

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

- **Status:** `planning-hypothesis`.
- **Evidence boundary:** Derived from explicit user wording and repository path inventory only. Actual states, transitions, side effects, responses, and edit necessity remain unconfirmed until after approval.

| Requirement | Scenario | Observable result | Required proof |
|---|---|---|---|
| REQ-02 | Exercise the affected existing public behaviour before and after the refactor. | The refactor changes internal structure without changing approved observable behaviour. | behaviour, integration |
| REQ-02 | Observe the approved user-visible workflow through the approved interface. | Each authoritative transition is observable in order through the customer/API surface. | behaviour, integration |
| REQ-01 | not recorded | Both human-readable plans list the input locator, its read-only role, access and status, and its recorded SHA-256 when present without adding it to editable scope. | behaviour |

### Scoped evidence

| Path | Role | Planned use | Confidence |
|---|---|---|---|
| `scripts/closure-finalizer.py` | supporting candidate | Inspect after approval; edit only when the confirmed behaviour path requires it. | repository-inventory hypothesis |
| `scripts/planning_lock.py` | supporting candidate | Inspect after approval; edit only when the confirmed behaviour path requires it. | repository-inventory hypothesis |
| `scripts/verbose-reporting.py` | supporting candidate | Inspect after approval; edit only when the confirmed behaviour path requires it. | repository-inventory hypothesis |
| `tests/test_start_plan_presentation.py` | supporting candidate | Inspect after approval; edit only when the confirmed behaviour path requires it. | repository-inventory hypothesis |

### Post-change checks

1. Confirm the actor, starting state, authoritative state owner, and observable interface before the first edit.
2. Map each actual transition and side effect to an approved behaviour scenario and requirement ID.
3. Reconcile actual changed paths with the approved behaviour roles; justify or correct unexpected scope.
4. Require matching behaviour and integration receipts; unit evidence alone cannot complete the Behaviour Harness.
5. Report unresolved scenarios as evidence-incomplete or drifted, never as a generic pass.

## Focused Validation Coverage Summary

- **Requirements covered:** 3/3.
- **Proof command reuse:**
  - `cmd-39aabc` covers 3 requirement(s): REQ-01, REQ-02, REQ-03.
  - `cmd-dcb44d` covers 3 requirement(s): REQ-01, REQ-02, REQ-03.

## Token Estimate

- **Planned working set:** approximately `4214` tokens (confidence: `medium`).
- **Scoped-file ceiling:** approximately `71647` tokens; estimated reduction `94.12%`.
- **Confidence basis:** at least one bounded slice lacks an exact combined behavior-and-symbol anchor.
- This is an estimate from saved scope, not measured model/provider usage.

## Implementation Boundary

- **Editable scope:** `scripts/verbose-reporting.py`.
- **Read-only / proof-only scope:** `scripts/closure-finalizer.py`, `scripts/planning_lock.py`, `tests/test_planning_revision.py`, `tests/test_start_plan_presentation.py`.
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

- Machine-readable state remains available at [`.tailtrail/runs/start-20261030123049-4edd0a/planning/revisions/start-report-v3.json`](.tailtrail/runs/start-20261030123049-4edd0a/planning/revisions/start-report-v3.json); it is not the approval view.

---

*End of Start Plan.*