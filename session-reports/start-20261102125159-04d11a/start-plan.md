# TailTrail Start Plan - Full Review Record

**Presentation version:** `5`

## Planning Lock

- **Run ID:** `start-20261102125159-04d11a`
- **Status:** `awaiting-approval`
- **Goal:** Preserve validated read-only and validation-only host-contract routing through planning revisions so a pending revision never gains implementation owners or editable implementation scope.
- **Request mode:** `implementation`
- **Managed writes allowed:** `false`
- **Execution status:** planning only; no source change, proof command, scanner, or Git operation has run.
- **Plan revision:** active `1`; pending `4`.

## Bound Planning Inputs

- No read-only planning inputs were bound to this plan.

## Command Reference Registry

| ID | Kind | Command |
|---|---|---|
| `cmd-3d4dd0` | proof | `python3 -m unittest tests.test_planning_revision tests.test_public_route_gate -q` |

## Validation Requirements And Focused Validation Matrix

### REQ-01

**Description:** Preserve validated read-only and validation-only host-contract routing through planning revisions

- **Requirement type:** `change`
- **Validation state:** `required`
- **Editable owner(s):** `scripts/planning-revision.py`
- **Read-only input(s):** `scripts/navigator.py`, `scripts/navigator_scope.py`, `scripts/task-start.py`
- **Proof path(s):** `tests/test_planning_revision.py`, `tests/test_public_route_gate.py`
- **Success criteria:** The stated requirement is observably satisfied on its approved path.
- **Preservation criteria:** Do not change behavior outside this approved requirement boundary.

| Tier | Command ID | Command | Candidate | State |
|---|---|---|---|---|
| unit | `cmd-3d4dd0` | `python3 -m unittest tests.test_planning_revision tests.test_public_route_gate -q` | `tests/test_planning_revision.py` | resolved |
| contract | `cmd-3d4dd0` | `python3 -m unittest tests.test_planning_revision tests.test_public_route_gate -q` | `tests/test_planning_revision.py` | resolved |

### REQ-02

**Description:** a pending revision never gains implementation owners or editable implementation scope.

- **Requirement type:** `safety`
- **Validation state:** `required`
- **Editable owner(s):** `scripts/planning-revision.py`
- **Read-only input(s):** `scripts/navigator.py`, `scripts/navigator_scope.py`, `scripts/task-start.py`
- **Proof path(s):** `tests/test_planning_revision.py`, `tests/test_public_route_gate.py`
- **Success criteria:** The stated requirement is observably satisfied on its approved path.
- **Preservation criteria:** Do not change behavior outside this approved requirement boundary.

| Tier | Command ID | Command | Candidate | State |
|---|---|---|---|---|
| unit | `cmd-3d4dd0` | `python3 -m unittest tests.test_planning_revision tests.test_public_route_gate -q` | `tests/test_planning_revision.py` | resolved |
| contract | `cmd-3d4dd0` | `python3 -m unittest tests.test_planning_revision tests.test_public_route_gate -q` | `tests/test_planning_revision.py` | resolved |

## Plan

1. **REQ-01:** Implement Preserve validated read-only and validation-only host-contract routing through planning revisions in `scripts/planning-revision.py`; verify with `cmd-3d4dd0`, `cmd-3d4dd0`; inspect `scripts/navigator.py`, `scripts/navigator_scope.py`, `scripts/task-start.py`; prove against `tests/test_planning_revision.py`, `tests/test_public_route_gate.py`.
2. **REQ-02:** Implement a pending revision never gains implementation owners or editable implementation scope. in `scripts/planning-revision.py`; verify with `cmd-3d4dd0`, `cmd-3d4dd0`; inspect `scripts/navigator.py`, `scripts/navigator_scope.py`, `scripts/task-start.py`; prove against `tests/test_planning_revision.py`, `tests/test_public_route_gate.py`.
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

- **Status:** `planning-hypothesis`.
- **Evidence boundary:** Derived from explicit user wording and repository path inventory only. Source, caller relationships, and edit necessity are not confirmed until after approval.

| Requirement | Invariant | Planned proof |
|---|---|---|
| REQ-01 | Behaviour outside the approved change boundary remains compatible. | Existing preservation-path evidence plus focused regression proof. |

### Scoped evidence

| Path | Role | Planned use | Confidence |
|---|---|---|---|
| `scripts/planning-revision.py` | implementation candidate | Primary implementation candidate, subject to post-approval source and caller confirmation. | repository-inventory hypothesis |
| `tests/planning_proof_fixture.py` | test evidence | Primary implementation candidate, subject to post-approval source and caller confirmation. | repository-inventory hypothesis |
| `tests/test_architecture_planning.py` | test evidence | Primary implementation candidate, subject to post-approval source and caller confirmation. | repository-inventory hypothesis |
| `tests/test_behaviour_planning.py` | test evidence | Primary implementation candidate, subject to post-approval source and caller confirmation. | repository-inventory hypothesis |
| `tests/test_canonical_statement_contract.py` | test evidence | Primary implementation candidate, subject to post-approval source and caller confirmation. | repository-inventory hypothesis |
| `tests/test_maintainability_planning.py` | test evidence | Primary implementation candidate, subject to post-approval source and caller confirmation. | repository-inventory hypothesis |
| `tests/test_navigator_scope.py` | test evidence | Primary implementation candidate, subject to post-approval source and caller confirmation. | repository-inventory hypothesis |
| `tests/test_navigator_scope_calibration.py` | test evidence | Primary implementation candidate, subject to post-approval source and caller confirmation. | repository-inventory hypothesis |
| `tests/test_navigator_scope_release.py` | test evidence | Primary implementation candidate, subject to post-approval source and caller confirmation. | repository-inventory hypothesis |
| `tests/test_planning_aidlc_question.py` | test evidence | Primary implementation candidate, subject to post-approval source and caller confirmation. | repository-inventory hypothesis |
| `tests/test_planning_audit.py` | test evidence | Primary implementation candidate, subject to post-approval source and caller confirmation. | repository-inventory hypothesis |
| `tests/test_planning_revision.py` | test evidence | Primary implementation candidate, subject to post-approval source and caller confirmation. | repository-inventory hypothesis |

### Post-change checks

1. Confirm the authoritative boundary and material callers before the first edit.
2. Compare actual changed files and symbols with the approved impact map; justify or correct every unexpected path.
3. Detect missed callers, caller-specific business logic, wrong-layer placement, and public-contract drift.
4. Check dependency manifests and imports when the approved contract forbids a new dependency.
5. Run every requirement-linked validation tier and preserve unresolved evidence as a gap, not a pass.

## Behaviour Analysis

- **Status:** `not selected`. This control is not part of the approved proof boundary for this plan.

## Focused Validation Coverage Summary

- **Requirements covered:** 2/2.
- **Proof command reuse:**
  - `cmd-3d4dd0` covers 2 requirement(s): REQ-01, REQ-02.

## Token Estimate

- Unavailable: scope is `ambiguous`, so a token estimate would not be reliable.
- This is an estimate from saved scope, not measured model/provider usage.

## Implementation Boundary

- **Editable scope:** `scripts/planning-revision.py`.
- **Read-only / proof-only scope:** `scripts/navigator.py`, `scripts/navigator_scope.py`, `scripts/task-start.py`, `tests/test_planning_revision.py`, `tests/test_public_route_gate.py`.
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

- **Total review cycles:** 4
- **Revision cycles:** 3
- **Latest audit:** `clean`; 0 finding(s).

## Approval Decision

**READY FOR APPROVAL** — review this plan, then explicitly approve this exact run. Approval is separate from activation and permits no unlisted work.

## Canonical Machine Record

- Machine-readable state remains available at [`.tailtrail/runs/start-20261102125159-04d11a/planning/start-report-v1.json`](.tailtrail/runs/start-20261102125159-04d11a/planning/start-report-v1.json); it is not the approval view.

---

*End of Start Plan.*