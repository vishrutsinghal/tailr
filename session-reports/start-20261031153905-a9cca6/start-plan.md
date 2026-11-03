# TailTrail Start Plan - Full Review Record

**Presentation version:** `4`

## Planning Lock

- **Run ID:** `start-20261031153905-a9cca6`
- **Status:** `approved`
- **Goal:** Implement Phase 3 of TAILTRAIL-HOST-TAILTRAIL-EVIDENCE-VALIDATION-DESIGN.md: bind each material requirement to proof path, exact command, tier, asserted behavior, and evidence fingerprint; keep intake-recorded separate from planning-readiness; reject stale bindings and intake-only receipts
- **Request mode:** `implementation`
- **Managed writes allowed:** `true`
- **Execution status:** planning only; no source change, proof command, scanner, or Git operation has run.
- **Plan revision:** active `6`; pending `none`.

## Bound Planning Inputs

- No read-only planning inputs were bound to this plan.

## Command Reference Registry

| ID | Kind | Command |
|---|---|---|
| `cmd-593fac` | proof | `python3 -m unittest tests.test_intake_pipeline` |

## Validation Requirements And Focused Validation Matrix

### REQ-01

**Description:** Implement Phase 3 of TAILTRAIL-HOST-TAILTRAIL-EVIDENCE-VALIDATION-DESIGN.md: bind each material requirement to proof path, exact command, tier, asserted behavior, and evidence fingerprint.

- **Requirement type:** `change`
- **Validation state:** `required`
- **Editable owner(s):** `scripts/intake_pipeline.py`
- **Read-only input(s):** `scripts/question-orchestrator.py`
- **Proof path(s):** `tests/test_intake_pipeline.py`
- **Success criteria:** The stated requirement is observably satisfied on its approved path.
- **Preservation criteria:** Do not change behavior outside this approved requirement boundary.
- **Requirement behaviour scenarios:**
  - `BHV-REQ-01`: Run the intake pipeline proof command python3 -m unittest tests.test_intake_pipeline → Intake-only receipts cannot authorize Start and stale bindings are rejected

| Tier | Command ID | Command | Candidate | State |
|---|---|---|---|---|
| behaviour | `cmd-593fac` | `python3 -m unittest tests.test_intake_pipeline` | `tests/test_intake_pipeline.py` | resolved |
| unit | `cmd-593fac` | `python3 -m unittest tests.test_intake_pipeline` | `tests/test_intake_pipeline.py` | resolved |

### REQ-02

**Description:** Keep intake-recorded separate from planning-readiness.

- **Requirement type:** `preserve`
- **Validation state:** `required`
- **Editable owner(s):** `scripts/intake_pipeline.py`
- **Read-only input(s):** `scripts/question-orchestrator.py`
- **Proof path(s):** `tests/test_intake_pipeline.py`
- **Success criteria:** The stated requirement is observably satisfied on its approved path.
- **Preservation criteria:** Keep intake-recorded separate from planning-readiness.

| Tier | Command ID | Command | Candidate | State |
|---|---|---|---|---|
| unit | `cmd-593fac` | `python3 -m unittest tests.test_intake_pipeline` | `tests/test_intake_pipeline.py` | resolved |

### REQ-03

**Description:** Reject stale bindings and intake-only receipts.

- **Requirement type:** `constraint`
- **Validation state:** `required`
- **Editable owner(s):** `scripts/intake_pipeline.py`
- **Read-only input(s):** `scripts/question-orchestrator.py`
- **Proof path(s):** `tests/test_intake_pipeline.py`
- **Success criteria:** The stated requirement is observably satisfied on its approved path.
- **Preservation criteria:** Do not change behavior outside this approved requirement boundary.

| Tier | Command ID | Command | Candidate | State |
|---|---|---|---|---|
| unit | `cmd-593fac` | `python3 -m unittest tests.test_intake_pipeline` | `tests/test_intake_pipeline.py` | resolved |

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
| `scripts/intake_pipeline.py` | implementation candidate | Primary implementation candidate, subject to post-approval source and caller confirmation. | repository-inventory hypothesis |
| `scripts/question-orchestrator.py` | orchestration boundary | Primary implementation candidate, subject to post-approval source and caller confirmation. | repository-inventory hypothesis |
| `tests/test_host_question_flow_event_schema.py` | test evidence | Run only when its tier proves an approved requirement. | repository-inventory hypothesis |
| `tests/test_intake_evidence_state.py` | test evidence | Run only when its tier proves an approved requirement. | repository-inventory hypothesis |
| `tests/test_intake_pipeline.py` | test evidence | Run only when its tier proves an approved requirement. | repository-inventory hypothesis |

### Post-change checks

1. Confirm the authoritative boundary and material callers before the first edit.
2. Compare actual changed files and symbols with the approved impact map; justify or correct every unexpected path.
3. Detect missed callers, caller-specific business logic, wrong-layer placement, and public-contract drift.
4. Check dependency manifests and imports when the approved contract forbids a new dependency.
5. Run every requirement-linked validation tier and preserve unresolved evidence as a gap, not a pass.

## Behaviour Analysis

- **Status:** `planning-hypothesis`.
- **Evidence boundary:** Derived from explicit user wording and repository path inventory only. Actual states, transitions, side effects, responses, and edit necessity remain unconfirmed until after approval.

| Requirement | Scenario | Observable result | Required proof |
|---|---|---|---|
| REQ-01 | not recorded | Intake-only receipts cannot authorize Start and stale bindings are rejected | behaviour |

### Scoped evidence

| Path | Role | Planned use | Confidence |
|---|---|---|---|
| `scripts/intake_pipeline.py` | supporting candidate | Inspect after approval; edit only when the confirmed behaviour path requires it. | repository-inventory hypothesis |
| `scripts/question-orchestrator.py` | workflow orchestration | Inspect after approval; edit only when the confirmed behaviour path requires it. | repository-inventory hypothesis |
| `tests/test_host_question_flow_event_schema.py` | side-effect boundary | Inspect after approval; edit only when the confirmed behaviour path requires it. | repository-inventory hypothesis |
| `tests/test_intake_evidence_state.py` | authoritative state | Inspect after approval; edit only when the confirmed behaviour path requires it. | repository-inventory hypothesis |
| `tests/test_intake_pipeline.py` | supporting candidate | Inspect after approval; edit only when the confirmed behaviour path requires it. | repository-inventory hypothesis |

### Post-change checks

1. Confirm the actor, starting state, authoritative state owner, and observable interface before the first edit.
2. Map each actual transition and side effect to an approved behaviour scenario and requirement ID.
3. Reconcile actual changed paths with the approved behaviour roles; justify or correct unexpected scope.
4. Require matching behaviour and integration receipts; unit evidence alone cannot complete the Behaviour Harness.
5. Report unresolved scenarios as evidence-incomplete or drifted, never as a generic pass.

## Focused Validation Coverage Summary

- **Requirements covered:** 3/3.
- **Proof command reuse:**
  - `cmd-593fac` covers 3 requirement(s): REQ-01, REQ-02, REQ-03.

## Token Estimate

- **Planned working set:** approximately `1486` tokens (confidence: `medium`).
- **Scoped-file ceiling:** approximately `32153` tokens; estimated reduction `95.38%`.
- **Confidence basis:** at least one bounded slice lacks an exact combined behavior-and-symbol anchor.
- This is an estimate from saved scope, not measured model/provider usage.

## Implementation Boundary

- **Editable scope:** `scripts/intake_pipeline.py`.
- **Read-only / proof-only scope:** `scripts/question-orchestrator.py`, `tests/test_intake_pipeline.py`.
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
| 6 | v6 | revision recorded | Plan changed and must be audited again |

- **Total review cycles:** 6
- **Revision cycles:** 5
- **Latest audit:** `clean`; 0 finding(s).

## Approval Decision

**READY FOR APPROVAL** — review this plan, then explicitly approve this exact run. Approval is separate from activation and permits no unlisted work.

## Canonical Machine Record

- Machine-readable state remains available at [`.tailtrail/runs/start-20261031153905-a9cca6/planning/revisions/start-report-v6.json`](.tailtrail/runs/start-20261031153905-a9cca6/planning/revisions/start-report-v6.json); it is not the approval view.

---

*End of Start Plan.*