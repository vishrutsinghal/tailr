# TailTrail Start Plan - Full Review Record

**Presentation version:** `4`

## Planning Lock

- **Run ID:** `start-20261102110113-15a708`
- **Status:** `awaiting-approval`
- **Goal:** Make planning revisions compose from the active validated AIDLC revision rather than the original Start report, preserving requirement rows, scope roles, proof bindings, behavior scenarios, and fingerprints through an audit-suggested revision.
- **Request mode:** `implementation`
- **Managed writes allowed:** `false`
- **Execution status:** planning only; no source change, proof command, scanner, or Git operation has run.
- **Plan revision:** active `1`; pending `3`.

## Bound Planning Inputs

- No read-only planning inputs were bound to this plan.

## Command Reference Registry

| ID | Kind | Command |
|---|---|---|
| `cmd-38cc3b` | proof | `python3 -m unittest tests.test_planning_revision -v` |

## Validation Requirements And Focused Validation Matrix

### REQ-01

**Description:** Make planning revisions compose from the active validated AIDLC revision rather than the original Start report, preserving requirement rows, scope roles, proof bindings, behavior scenarios, and fingerprints through an audit-suggested revision.

- **Requirement type:** `change`
- **Validation state:** `required`
- **Editable owner(s):** `scripts/planning-revision.py`
- **Proof path(s):** `tests/test_planning_revision.py`, `tests/planning_proof_fixture.py`, `tests/test_canonical_statement_contract.py`
- **Success criteria:** An audit-suggested planning revision begins from the active validated AIDLC revision and preserves every requirement row, scope role, proof binding, behavior scenario, and fingerprint that the revision does not intentionally change.
- **Preservation criteria:** A normal revision must not silently fall back to the original Start report or drop prior validated AIDLC projections; non-AIDLC revision behavior remains compatible.
- **Requirement behaviour scenarios:**
  - `BHV-REQ-01-AIDLC-REVISION-PRESERVATION`: Create an active validated AIDLC revision, apply an audit-suggested proof-tier revision, and render the pending plan. → The pending plan preserves every unmodified requirement row, scope role, proof binding, behavior scenario, and canonical fingerprint from the active AIDLC revision while adding only the requested proof-tier delta.

| Tier | Command ID | Command | Candidate | State |
|---|---|---|---|---|
| behaviour | `cmd-38cc3b` | `python3 -m unittest tests.test_planning_revision -v` | `tests/test_planning_revision.py` | resolved |
| unit | `cmd-38cc3b` | `python3 -m unittest tests.test_planning_revision -v` | `tests/test_planning_revision.py` | resolved |

## Selected TailTrail Features

| Feature | When used | Why it is selected |
|---|---|---|
| Navigator | planning | established the evidence-bound scope and approval boundary |
| Token Autopilot | as required by the plan | selected for this task |
| Bootstrap Snapshot | as required by the plan | selected for this task |
| Code Review Graph Lite | as required by the plan | selected for this task |
| Code Graph Mapper | as required by the plan | selected for this task |
| Learning Capture Trigger | as required by the plan | selected for this task |
| Test Precision Planner | as required by the plan | selected for this task |
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
| REQ-01 | Create an active validated AIDLC revision, apply an audit-suggested proof-tier revision, and render the pending plan. | The pending plan preserves every unmodified requirement row, scope role, proof binding, behavior scenario, and canonical fingerprint from the active AIDLC revision while adding only the requested proof-tier delta. | behaviour |

### Scoped evidence

| Path | Role | Planned use | Confidence |
|---|---|---|---|
| `scripts/planning-revision.py` | supporting candidate | Inspect after approval; edit only when the confirmed behaviour path requires it. | repository-inventory hypothesis |
| `tests/planning_proof_fixture.py` | supporting candidate | Inspect after approval; edit only when the confirmed behaviour path requires it. | repository-inventory hypothesis |
| `tests/test_canonical_statement_contract.py` | authoritative state | Inspect after approval; edit only when the confirmed behaviour path requires it. | repository-inventory hypothesis |
| `tests/test_planning_revision.py` | supporting candidate | Inspect after approval; edit only when the confirmed behaviour path requires it. | repository-inventory hypothesis |

### Post-change checks

1. Confirm the actor, starting state, authoritative state owner, and observable interface before the first edit.
2. Map each actual transition and side effect to an approved behaviour scenario and requirement ID.
3. Reconcile actual changed paths with the approved behaviour roles; justify or correct unexpected scope.
4. Require matching behaviour and integration receipts; unit evidence alone cannot complete the Behaviour Harness.
5. Report unresolved scenarios as evidence-incomplete or drifted, never as a generic pass.

## Focused Validation Coverage Summary

- **Requirements covered:** 1/1.
- **Proof command reuse:**
  - `cmd-38cc3b` covers 1 requirement(s): REQ-01.

## Token Estimate

- **Planned working set:** approximately `5555` tokens (confidence: `medium`).
- **Scoped-file ceiling:** approximately `34520` tokens; estimated reduction `83.91%`.
- **Confidence basis:** at least one bounded slice lacks an exact combined behavior-and-symbol anchor.
- This is an estimate from saved scope, not measured model/provider usage.

## Implementation Boundary

- **Editable scope:** `scripts/planning-revision.py`.
- **Read-only / proof-only scope:** `tests/planning_proof_fixture.py`, `tests/test_canonical_statement_contract.py`, `tests/test_planning_revision.py`.
- **Excluded:** every path, command, external system, deployment, and data change not explicitly recorded above remains outside this approval.
- **Data impact:** no data impact is authorized unless a requirement above names it explicitly.

## Approval Checklist

- [x] Requirements are present and reviewable.
- [x] Every requirement has an editable implementation owner.
- [x] Runnable proof commands are registered and mapped to requirements.
- [x] Material questions are resolved.
- [x] Mandatory planning audit is clean for this exact plan revision.
- [ ] The host has reviewed the scope, preservation criteria, proof commands, analyses, and excluded boundary.

## AIDLC Decisions

- AIDLC authority artifacts are present: `aidlc-correction-observations-v2.json`, `aidlc-correction-state.json`, `aidlc-requirements-v1.json`.
- **Q1:** Which user-visible or caller-visible result remains unspecified in this request?
- **Q2:** Which named integration, data boundary, or side effect needs an explicit compatibility decision?
- **Q3:** What focused evidence proves the stated acceptance criteria at the affected boundary?
- **Q4:** How should this prior review concern change the requirement boundary: The pending Start Plan omits the mandatory Plan section and does not visibly preserve the supplied inspection input, so it cannot be reviewed safely.

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

- Machine-readable state remains available at [`.tailtrail/runs/start-20261102110113-15a708/planning/start-report-v1.json`](.tailtrail/runs/start-20261102110113-15a708/planning/start-report-v1.json); it is not the approval view.

---

*End of Start Plan.*