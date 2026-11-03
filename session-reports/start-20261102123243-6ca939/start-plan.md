# TailTrail Start Plan - Full Review Record

**Presentation version:** `5`

## Planning Lock

- **Run ID:** `start-20261102123243-6ca939`
- **Status:** `approved`
- **Goal:** Validate the host-contract routing fix without editing source: read-only and validation-only contracts must route before owner selection, preserve inspection and proof roles through audit and revision, and render no implementation authority.
- **Request mode:** `validation-only`
- **Managed writes allowed:** `true`
- **Execution status:** planning only; no source change, proof command, scanner, or Git operation has run.
- **Plan revision:** active `3`; pending `none`.

## Bound Planning Inputs

- No read-only planning inputs were bound to this plan.

## Command Reference Registry

| ID | Kind | Command |
|---|---|---|
| `cmd-c21750` | proof | `python3 -m unittest tests.test_public_route_gate tests.test_host_contract tests.test_planning_revision tests.test_start_plan_presentation tests.test_navigator_scope -q` |

## Validation Requirements And Focused Validation Matrix

### REQ-01

**Description:** Validate the host-contract routing fix without editing source: read-only and validation-only contracts must route before owner selection.

- **Requirement type:** `constraint`
- **Validation state:** `required`
- **Editable owner(s):** not applicable (`validation-only`; no implementation authority).
- **Read-only input(s):** `schemas/navigator-scope-evidence.schema.json`, `scripts/aidlc-check.py`, `scripts/change-intent-anchor.py`, `scripts/evidence-tiers.py`, `scripts/mcp-server.py`, `scripts/navigator-scope-release.py`, `scripts/navigator-scope.py`, `scripts/navigator.py`, `scripts/navigator_graph_lifecycle.py`, `scripts/navigator_scope.py`, `scripts/planning-revision.py`, `scripts/task-start.py`, `scripts/verbose-reporting.py`
- **Proof path(s):** `tests/test_host_contract.py`, `tests/test_navigator_scope.py`, `tests/test_planning_revision.py`, `tests/test_public_route_gate.py`, `tests/test_start_plan_presentation.py`
- **Success criteria:** The stated requirement is observably satisfied on its approved path.
- **Preservation criteria:** Do not change behavior outside this approved requirement boundary.

| Tier | Command ID | Command | Candidate | State |
|---|---|---|---|---|
| unit | `cmd-c21750` | `python3 -m unittest tests.test_public_route_gate tests.test_host_contract tests.test_planning_revision tests.test_start_plan_presentation tests.test_navigator_scope -q` | `tests/test_public_route_gate.py` | resolved |
| contract | `cmd-c21750` | `python3 -m unittest tests.test_public_route_gate tests.test_host_contract tests.test_planning_revision tests.test_start_plan_presentation tests.test_navigator_scope -q` | `tests/test_public_route_gate.py` | resolved |

### REQ-02

**Description:** Validate the host-contract routing preserve inspection and proof roles through audit and revision, and render no implementation authority.

- **Requirement type:** `preserve`
- **Validation state:** `required`
- **Editable owner(s):** not applicable (`validation-only`; no implementation authority).
- **Read-only input(s):** `schemas/navigator-scope-evidence.schema.json`, `scripts/aidlc-check.py`, `scripts/change-intent-anchor.py`, `scripts/evidence-tiers.py`, `scripts/mcp-server.py`, `scripts/navigator-scope-release.py`, `scripts/navigator-scope.py`, `scripts/navigator.py`, `scripts/navigator_graph_lifecycle.py`, `scripts/navigator_scope.py`, `scripts/planning-revision.py`, `scripts/task-start.py`, `scripts/verbose-reporting.py`
- **Proof path(s):** `tests/test_host_contract.py`, `tests/test_navigator_scope.py`, `tests/test_planning_revision.py`, `tests/test_public_route_gate.py`, `tests/test_start_plan_presentation.py`
- **Success criteria:** The stated requirement is observably satisfied on its approved path.
- **Preservation criteria:** Validate the host-contract routing preserve inspection and proof roles through audit and revision, and render no implementation authority.

| Tier | Command ID | Command | Candidate | State |
|---|---|---|---|---|
| unit | `cmd-c21750` | `python3 -m unittest tests.test_public_route_gate tests.test_host_contract tests.test_planning_revision tests.test_start_plan_presentation tests.test_navigator_scope -q` | `tests/test_planning_revision.py` | resolved |
| contract | `cmd-c21750` | `python3 -m unittest tests.test_public_route_gate tests.test_host_contract tests.test_planning_revision tests.test_start_plan_presentation tests.test_navigator_scope -q` | `tests/test_planning_revision.py` | resolved |

## Plan

1. **REQ-01:** Validate Validate the host-contract routing fix without editing source: read-only and validation-only contracts must route before owner selection. in no editable owner; verify with `cmd-c21750`, `cmd-c21750`; inspect `schemas/navigator-scope-evidence.schema.json`, `scripts/aidlc-check.py`, `scripts/change-intent-anchor.py`, `scripts/evidence-tiers.py`, `scripts/mcp-server.py`, `scripts/navigator-scope-release.py`, `scripts/navigator-scope.py`, `scripts/navigator.py`, `scripts/navigator_graph_lifecycle.py`, `scripts/navigator_scope.py`, `scripts/planning-revision.py`, `scripts/task-start.py`, `scripts/verbose-reporting.py`; prove against `tests/test_host_contract.py`, `tests/test_navigator_scope.py`, `tests/test_planning_revision.py`, `tests/test_public_route_gate.py`, `tests/test_start_plan_presentation.py`.
2. **REQ-02:** Validate Validate the host-contract routing preserve inspection and proof roles through audit and revision, and render no implementation authority. in no editable owner; verify with `cmd-c21750`, `cmd-c21750`; inspect `schemas/navigator-scope-evidence.schema.json`, `scripts/aidlc-check.py`, `scripts/change-intent-anchor.py`, `scripts/evidence-tiers.py`, `scripts/mcp-server.py`, `scripts/navigator-scope-release.py`, `scripts/navigator-scope.py`, `scripts/navigator.py`, `scripts/navigator_graph_lifecycle.py`, `scripts/navigator_scope.py`, `scripts/planning-revision.py`, `scripts/task-start.py`, `scripts/verbose-reporting.py`; prove against `tests/test_host_contract.py`, `tests/test_navigator_scope.py`, `tests/test_planning_revision.py`, `tests/test_public_route_gate.py`, `tests/test_start_plan_presentation.py`.
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
| Evaluation Harness | as required by the plan | selected for this task |

### Required before closure

- **Focused testing and validation:** prove the changed behavior, required preservation cases, and regression boundary with factual computational evidence
- **Canonical completion and closure:** prevent completion while required evidence is missing, unavailable, or failing

## Architecture Analysis

- **Status:** `planning-hypothesis`.
- **Evidence boundary:** Derived from explicit user wording and repository path inventory only. Source, caller relationships, and edit necessity are not confirmed until after approval.

| Requirement | Invariant | Planned proof |
|---|---|---|
| REQ-02 | Behaviour outside the approved change boundary remains compatible. | Existing preservation-path evidence plus focused regression proof. |

### Scoped evidence

| Path | Role | Planned use | Confidence |
|---|---|---|---|
| `schemas/navigator-scope-evidence.schema.json` | configuration boundary | Supporting/boundary-check path; inspect for impact, not an implementation candidate. | repository-inventory hypothesis |
| `scripts/adoption-validation.py` | validation boundary | Primary implementation candidate, subject to post-approval source and caller confirmation. | repository-inventory hypothesis |
| `scripts/advanced-runtime.py` | implementation candidate | Primary implementation candidate, subject to post-approval source and caller confirmation. | repository-inventory hypothesis |
| `scripts/aidlc-check.py` | implementation candidate | Primary implementation candidate, subject to post-approval source and caller confirmation. | repository-inventory hypothesis |
| `scripts/aidlc-official-bridge.py` | implementation candidate | Primary implementation candidate, subject to post-approval source and caller confirmation. | repository-inventory hypothesis |
| `scripts/aidlc-official-detect.py` | implementation candidate | Primary implementation candidate, subject to post-approval source and caller confirmation. | repository-inventory hypothesis |
| `scripts/aidlc-official-host.py` | implementation candidate | Primary implementation candidate, subject to post-approval source and caller confirmation. | repository-inventory hypothesis |
| `scripts/aidlc-official-install.py` | implementation candidate | Primary implementation candidate, subject to post-approval source and caller confirmation. | repository-inventory hypothesis |
| `scripts/change-intent-anchor.py` | implementation candidate | Primary implementation candidate, subject to post-approval source and caller confirmation. | repository-inventory hypothesis |
| `scripts/closure-contract.py` | implementation candidate | Primary implementation candidate, subject to post-approval source and caller confirmation. | repository-inventory hypothesis |
| `scripts/evidence-tiers.py` | implementation candidate | Primary implementation candidate, subject to post-approval source and caller confirmation. | repository-inventory hypothesis |
| `scripts/host-reply-validate.py` | implementation candidate | Primary implementation candidate, subject to post-approval source and caller confirmation. | repository-inventory hypothesis |
| `scripts/host_contract.py` | implementation candidate | Primary implementation candidate, subject to post-approval source and caller confirmation. | repository-inventory hypothesis |
| `scripts/mcp-server.py` | implementation candidate | Primary implementation candidate, subject to post-approval source and caller confirmation. | repository-inventory hypothesis |
| `scripts/navigator-scope-calibration.py` | implementation candidate | Primary implementation candidate, subject to post-approval source and caller confirmation. | repository-inventory hypothesis |
| `scripts/navigator-scope-release.py` | implementation candidate | Primary implementation candidate, subject to post-approval source and caller confirmation. | repository-inventory hypothesis |
| `scripts/navigator-scope.py` | implementation candidate | Primary implementation candidate, subject to post-approval source and caller confirmation. | repository-inventory hypothesis |
| `scripts/navigator.py` | implementation candidate | Primary implementation candidate, subject to post-approval source and caller confirmation. | repository-inventory hypothesis |
| `scripts/navigator_graph_lifecycle.py` | implementation candidate | Primary implementation candidate, subject to post-approval source and caller confirmation. | repository-inventory hypothesis |
| `scripts/navigator_scope.py` | implementation candidate | Primary implementation candidate, subject to post-approval source and caller confirmation. | repository-inventory hypothesis |
| `scripts/planning-revision.py` | implementation candidate | Primary implementation candidate, subject to post-approval source and caller confirmation. | repository-inventory hypothesis |
| `scripts/task-start.py` | implementation candidate | Primary implementation candidate, subject to post-approval source and caller confirmation. | repository-inventory hypothesis |
| `scripts/test_scope.py` | test evidence | Run only when its tier proves an approved requirement. | repository-inventory hypothesis |
| `scripts/verbose-reporting.py` | implementation candidate | Primary implementation candidate, subject to post-approval source and caller confirmation. | repository-inventory hypothesis |
| `tests/golden/host-replies/hello_narrated.md` | test evidence | Run only when its tier proves an approved requirement. | repository-inventory hypothesis |
| `tests/planning_proof_fixture.py` | test evidence | Run only when its tier proves an approved requirement. | repository-inventory hypothesis |
| `tests/test_host_contract.py` | test evidence | Run only when its tier proves an approved requirement. | repository-inventory hypothesis |
| `tests/test_host_reply_validate.py` | test evidence | Run only when its tier proves an approved requirement. | repository-inventory hypothesis |
| `tests/test_navigator_graph_lifecycle.py` | test evidence | Run only when its tier proves an approved requirement. | repository-inventory hypothesis |
| `tests/test_navigator_scope.py` | test evidence | Run only when its tier proves an approved requirement. | repository-inventory hypothesis |
| `tests/test_navigator_scope_calibration.py` | test evidence | Run only when its tier proves an approved requirement. | repository-inventory hypothesis |
| `tests/test_navigator_scope_release.py` | test evidence | Run only when its tier proves an approved requirement. | repository-inventory hypothesis |
| `tests/test_planning_revision.py` | test evidence | Run only when its tier proves an approved requirement. | repository-inventory hypothesis |
| `tests/test_public_route_gate.py` | test evidence | Run only when its tier proves an approved requirement. | repository-inventory hypothesis |
| `tests/test_review_scope.py` | test evidence | Run only when its tier proves an approved requirement. | repository-inventory hypothesis |
| `tests/test_revision_proof_overlay.py` | test evidence | Run only when its tier proves an approved requirement. | repository-inventory hypothesis |
| `tests/test_start_plan_presentation.py` | test evidence | Run only when its tier proves an approved requirement. | repository-inventory hypothesis |

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
  - `cmd-c21750` covers 2 requirement(s): REQ-01, REQ-02.

## Token Estimate

- Not applicable: this is a `validation-only` plan with no editable implementation scope; a source-edit working-set estimate would be misleading.
- This is an estimate from saved scope, not measured model/provider usage.

## Implementation Boundary

- **Editable scope:** not applicable (`validation-only`; no implementation authority).
- **Read-only / proof-only scope:** `schemas/navigator-scope-evidence.schema.json`, `scripts/aidlc-check.py`, `scripts/change-intent-anchor.py`, `scripts/evidence-tiers.py`, `scripts/mcp-server.py`, `scripts/navigator-scope-release.py`, `scripts/navigator-scope.py`, `scripts/navigator.py`, `scripts/navigator_graph_lifecycle.py`, `scripts/navigator_scope.py`, `scripts/planning-revision.py`, `scripts/task-start.py`, `scripts/verbose-reporting.py`, `tests/test_host_contract.py`, `tests/test_navigator_scope.py`, `tests/test_planning_revision.py`, `tests/test_public_route_gate.py`, `tests/test_start_plan_presentation.py`.
- **Excluded:** every path, command, external system, deployment, and data change not explicitly recorded above remains outside this approval.
- **Data impact:** no data impact is authorized unless a requirement above names it explicitly.

## Approval Checklist

- [x] Requirements are present and reviewable.
- [x] No implementation owner is declared for this `validation-only` plan.
- [x] Read-only or proof-only scope is recorded.
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

- Machine-readable state remains available at [`.tailtrail/runs/start-20261102123243-6ca939/planning/revisions/start-report-v3.json`](.tailtrail/runs/start-20261102123243-6ca939/planning/revisions/start-report-v3.json); it is not the approval view.

---

*End of Start Plan.*