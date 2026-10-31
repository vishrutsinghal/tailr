# TailTrail Start Plan - Full Review Record

**Presentation version:** `4`

## Planning Lock

- **Run ID:** `start-20261027091253-12fd05`
- **Status:** `approved`
- **Goal:** Implement generic Start Plan projection for validation-only host contracts: preserve every accepted inspection-input and proof-only path; retain the global proof command as unbound context; require explicit requirement-level proof bindings before readiness; do not grant implementation authority, auto-credit proof, or alter completion semantics.
- **Request mode:** `implementation`
- **Managed writes allowed:** `true`
- **Execution status:** planning only; no source change, proof command, scanner, or Git operation has run.
- **Plan revision:** active `2`; pending `none`.

## Command Reference Registry

| ID | Kind | Command |
|---|---|---|
| `cmd-62b3f5` | proof | `python3 -m unittest tests.test_start_plan_presentation tests.test_public_route_gate` |
| `cmd-dcb44d` | proof | `python3 -m unittest discover -s tests -p test_start_plan_presentation.py -v` |

## Validation Requirements And Focused Validation Matrix

### REQ-01

**Description:** Implement generic Start Plan projection for validation-only host contracts

- **Requirement type:** `change`
- **Validation state:** `required`
- **Editable owner(s):** `scripts/task-start.py`
- **Proof path(s):** `tests/test_start_plan_presentation.py`, `tests/test_public_route_gate.py`
- **Success criteria:** The stated requirement is observably satisfied on its approved path.
- **Preservation criteria:** Do not change behavior outside this approved requirement boundary.

| Tier | Command ID | Candidate | State |
|---|---|---|---|
| contract | `cmd-62b3f5` | `tests/test_start_plan_presentation.py` | resolved |

### REQ-02

**Description:** do not grant implementation authority, auto-credit proof, or alter completion semantics.

- **Requirement type:** `safety`
- **Validation state:** `required`
- **Editable owner(s):** `scripts/task-start.py`
- **Proof path(s):** `tests/test_start_plan_presentation.py`, `tests/test_public_route_gate.py`
- **Success criteria:** The stated requirement is observably satisfied on its approved path.
- **Preservation criteria:** Do not change behavior outside this approved requirement boundary.

| Tier | Command ID | Candidate | State |
|---|---|---|---|
| unit | `cmd-dcb44d` | `tests/test_start_plan_presentation.py` | resolved |
| unit | `cmd-62b3f5` | `tests/test_start_plan_presentation.py` | resolved |

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
| REQ-01 | The implementation must follow the existing repository boundaries discovered after approval. | Changed-scope comparison plus the repository's focused tests. |

### Scoped evidence

| Path | Role | Planned use | Confidence |
|---|---|---|---|
| `scripts/task-start.py` | implementation candidate | Primary implementation candidate, subject to post-approval source and caller confirmation. | repository-inventory hypothesis |

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
  - `cmd-62b3f5` covers 2 requirement(s): REQ-01, REQ-02.
  - `cmd-dcb44d` covers 1 requirement(s): REQ-02.

## Token Estimate

- **Planned working set:** approximately `12774` tokens (confidence: `medium`).
- **Scoped-file ceiling:** approximately `107568` tokens; estimated reduction `88.12%`.
- **Confidence basis:** at least one bounded slice lacks an exact combined behavior-and-symbol anchor.
- This is an estimate from saved scope, not measured model/provider usage.

## Implementation Boundary

- **Editable scope:** `scripts/task-start.py`.
- **Read-only / proof-only scope:** `tests/test_public_route_gate.py`, `tests/test_start_plan_presentation.py`.
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

- **Total review cycles:** 2
- **Revision cycles:** 1
- **Latest audit:** `clean`; 0 finding(s).

## Approval Decision

**READY FOR APPROVAL** — review this plan, then explicitly approve this exact run. Approval is separate from activation and permits no unlisted work.

## Canonical Machine Record

- Machine-readable state remains available at [`.tailtrail/runs/start-20261027091253-12fd05/planning/revisions/start-report-v2.json`](.tailtrail/runs/start-20261027091253-12fd05/planning/revisions/start-report-v2.json); it is not the approval view.

---

*End of Start Plan.*