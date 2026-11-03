# TailTrail Start Plan - Full Review Record

**Presentation version:** `4`

## Planning Lock

- **Run ID:** `start-20261031155918-3efea8`
- **Status:** `approved`
- **Goal:** Fix the Behaviour Analysis Scenario column in scripts/behaviour_planning.py so REQ-01 shows its recorded behaviour scenario (action or scenario_id) instead of not recorded. Request mode: implementation. Change authority: edit scripts/behaviour_planning.py markdown_lines only. Proof path: tests/test_behaviour_planning.py, command: python3 -m unittest discover -s tests -p test_behaviour_planning.py -v. Success: scenario text renders from action or scenario_id; the existing tests still pass.
- **Request mode:** `implementation`
- **Managed writes allowed:** `true`
- **Execution status:** planning only; no source change, proof command, scanner, or Git operation has run.
- **Plan revision:** active `3`; pending `none`.

## Bound Planning Inputs

- No read-only planning inputs were bound to this plan.

## Command Reference Registry

| ID | Kind | Command |
|---|---|---|
| `cmd-bbbac2` | proof | `python3 -m unittest discover -s tests -p test_behaviour_planning.py -v` |

## Validation Requirements And Focused Validation Matrix

### REQ-01

**Description:** Fix the Behaviour Analysis Scenario column in scripts/behaviour_planning.py so REQ-01 shows its recorded behaviour scenario (action or scenario_id) instead of not recorded.

- **Requirement type:** `change`
- **Validation state:** `required`
- **Editable owner(s):** `scripts/behaviour_planning.py`
- **Proof path(s):** `tests/test_behaviour_planning.py`
- **Success criteria:** The stated requirement is observably satisfied on its approved path.
- **Preservation criteria:** Do not change behavior outside this approved requirement boundary.

| Tier | Command ID | Command | Candidate | State |
|---|---|---|---|---|
| unit | `cmd-bbbac2` | `python3 -m unittest discover -s tests -p test_behaviour_planning.py -v` | `tests/test_behaviour_planning.py` | resolved |

### REQ-02

**Description:** Request mode: implementation.

- **Requirement type:** `change`
- **Validation state:** `required`
- **Editable owner(s):** `scripts/behaviour_planning.py`
- **Proof path(s):** `tests/test_behaviour_planning.py`
- **Success criteria:** The stated requirement is observably satisfied on its approved path.
- **Preservation criteria:** Do not change behavior outside this approved requirement boundary.

| Tier | Command ID | Command | Candidate | State |
|---|---|---|---|---|
| unit | `cmd-bbbac2` | `python3 -m unittest discover -s tests -p test_behaviour_planning.py -v` | `tests/test_behaviour_planning.py` | resolved |

### REQ-03

**Description:** Change authority: edit scripts/behaviour_planning.py markdown_lines only.

- **Requirement type:** `change`
- **Validation state:** `required`
- **Editable owner(s):** `scripts/behaviour_planning.py`
- **Proof path(s):** `tests/test_behaviour_planning.py`
- **Success criteria:** The stated requirement is observably satisfied on its approved path.
- **Preservation criteria:** Do not change behavior outside this approved requirement boundary.

| Tier | Command ID | Command | Candidate | State |
|---|---|---|---|---|
| unit | `cmd-bbbac2` | `python3 -m unittest discover -s tests -p test_behaviour_planning.py -v` | `tests/test_behaviour_planning.py` | resolved |

### REQ-04

**Description:** Proof path: tests/test_behaviour_planning.py, command: python3 -m unittest discover -s tests -p test_behaviour_planning.py -v.

- **Requirement type:** `change`
- **Validation state:** `required`
- **Editable owner(s):** `scripts/behaviour_planning.py`
- **Proof path(s):** `tests/test_behaviour_planning.py`
- **Success criteria:** The stated requirement is observably satisfied on its approved path.
- **Preservation criteria:** Do not change behavior outside this approved requirement boundary.

| Tier | Command ID | Command | Candidate | State |
|---|---|---|---|---|
| unit | `cmd-bbbac2` | `python3 -m unittest discover -s tests -p test_behaviour_planning.py -v` | `tests/test_behaviour_planning.py` | resolved |

### REQ-05

**Description:** Success: scenario text renders from action or scenario_id.

- **Requirement type:** `change`
- **Validation state:** `required`
- **Editable owner(s):** `scripts/behaviour_planning.py`
- **Proof path(s):** `tests/test_behaviour_planning.py`
- **Success criteria:** The stated requirement is observably satisfied on its approved path.
- **Preservation criteria:** Do not change behavior outside this approved requirement boundary.

| Tier | Command ID | Command | Candidate | State |
|---|---|---|---|---|
| unit | `cmd-bbbac2` | `python3 -m unittest discover -s tests -p test_behaviour_planning.py -v` | `tests/test_behaviour_planning.py` | resolved |

### REQ-06

**Description:** The existing tests still pass.

- **Requirement type:** `change`
- **Validation state:** `required`
- **Editable owner(s):** `scripts/behaviour_planning.py`
- **Proof path(s):** `tests/test_behaviour_planning.py`
- **Success criteria:** The stated requirement is observably satisfied on its approved path.
- **Preservation criteria:** Do not change behavior outside this approved requirement boundary.

| Tier | Command ID | Command | Candidate | State |
|---|---|---|---|---|
| unit | `cmd-bbbac2` | `python3 -m unittest discover -s tests -p test_behaviour_planning.py -v` | `tests/test_behaviour_planning.py` | resolved |

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
| `scripts/behaviour_planning.py` | implementation candidate | Primary implementation candidate, subject to post-approval source and caller confirmation. | repository-inventory hypothesis |
| `tests/test_behaviour_planning.py` | test evidence | Run only when its tier proves an approved requirement. | repository-inventory hypothesis |

### Post-change checks

1. Confirm the authoritative boundary and material callers before the first edit.
2. Compare actual changed files and symbols with the approved impact map; justify or correct every unexpected path.
3. Detect missed callers, caller-specific business logic, wrong-layer placement, and public-contract drift.
4. Check dependency manifests and imports when the approved contract forbids a new dependency.
5. Run every requirement-linked validation tier and preserve unresolved evidence as a gap, not a pass.

## Behaviour Analysis

- **Status:** `planning-hypothesis`.
- **Evidence boundary:** Derived from explicit user wording and repository path inventory only. Actual states, transitions, side effects, responses, and edit necessity remain unconfirmed until after approval.
- No requirement-linked analysis items were saved; revise before approval if this control is required.

### Scoped evidence

| Path | Role | Planned use | Confidence |
|---|---|---|---|
| `scripts/behaviour_planning.py` | supporting candidate | Inspect after approval; edit only when the confirmed behaviour path requires it. | repository-inventory hypothesis |
| `tests/test_behaviour_planning.py` | supporting candidate | Inspect after approval; edit only when the confirmed behaviour path requires it. | repository-inventory hypothesis |

### Post-change checks

1. Confirm the actor, starting state, authoritative state owner, and observable interface before the first edit.
2. Map each actual transition and side effect to an approved behaviour scenario and requirement ID.
3. Reconcile actual changed paths with the approved behaviour roles; justify or correct unexpected scope.
4. Require matching behaviour and integration receipts; unit evidence alone cannot complete the Behaviour Harness.
5. Report unresolved scenarios as evidence-incomplete or drifted, never as a generic pass.

## Focused Validation Coverage Summary

- **Requirements covered:** 6/6.
- **Proof command reuse:**
  - `cmd-bbbac2` covers 6 requirement(s): REQ-01, REQ-02, REQ-03, REQ-04, REQ-05, REQ-06.

## Token Estimate

- **Planned working set:** approximately `1287` tokens (confidence: `medium`).
- **Scoped-file ceiling:** approximately `12799` tokens; estimated reduction `89.94%`.
- **Confidence basis:** at least one bounded slice lacks an exact combined behavior-and-symbol anchor.
- This is an estimate from saved scope, not measured model/provider usage.

## Implementation Boundary

- **Editable scope:** `scripts/behaviour_planning.py`.
- **Read-only / proof-only scope:** `tests/test_behaviour_planning.py`.
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

- Machine-readable state remains available at [`.tailtrail/runs/start-20261031155918-3efea8/planning/revisions/start-report-v3.json`](.tailtrail/runs/start-20261031155918-3efea8/planning/revisions/start-report-v3.json); it is not the approval view.

---

*End of Start Plan.*