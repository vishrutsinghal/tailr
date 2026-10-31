# TailTrail Start Plan - Full Review Record

**Presentation version:** `4`

## Planning Lock

- **Run ID:** `start-20261030165734-fb62e6`
- **Status:** `approved`
- **Goal:** Make the TESTING-to-INFRA drift gate automatically merge saved managed execution evidence with explicit handoff evidence, while preserving fail-closed behavior for missing, non-passing, stale, or unlinked receipts.
- **Request mode:** `implementation`
- **Managed writes allowed:** `true`
- **Execution status:** planning only; no source change, proof command, scanner, or Git operation has run.
- **Plan revision:** active `2`; pending `none`.

## Bound Planning Inputs

- No read-only planning inputs were bound to this plan.

## Command Reference Registry

| ID | Kind | Command |
|---|---|---|
| `cmd-817eac` | proof | `python3 -m unittest discover -s tests -p test_drift_analysis.py -v` |
| `cmd-a0b36d` | proof | `python3 -m unittest tests.test_drift_analysis -v` |

## Validation Requirements And Focused Validation Matrix

### REQ-01

**Description:** Make the TESTING-to-INFRA drift gate automatically merge saved managed execution evidence with explicit handoff evidence, while preserving fail-closed behavior for missing, non-passing, stale, or unlinked receipts.

- **Requirement type:** `change`
- **Validation state:** `required`
- **Editable owner(s):** `scripts/drift_analysis.py`
- **Proof path(s):** `tests/test_drift_analysis.py`
- **Success criteria:** The stated requirement is observably satisfied on its approved path.; The TESTING-to-INFRA gate uses requirement-linked trusted managed execution receipts saved for the same run when a handoff does not repeat them inline.; Explicit handoff evidence and saved managed evidence are combined deterministically before tier validation.
- **Preservation criteria:** Do not change behavior outside this approved requirement boundary.; Missing, failing, stale, untrusted, or unlinked saved receipts must continue to block the transition.; The change must not grant scope, approval, or write authority from evidence.
- **Requirement behaviour scenarios:**
  - `BHV-SAVED-MANAGED-EVIDENCE-01`: Request a TESTING-to-INFRA transition with an approved changed-path manifest and no inline evidence after a trusted, requirement-linked managed receipt was saved for the same run. → The drift gate accepts the transition only when the saved and inline evidence union satisfies every required tier; missing, failing, stale, untrusted, or unlinked receipts keep it blocked.

| Tier | Command ID | Candidate | State |
|---|---|---|---|
| unit | `cmd-817eac` | `tests/test_drift_analysis.py` | resolved |
| unit | `cmd-a0b36d` | `tests/test_drift_analysis.py` | resolved |
| behaviour | `cmd-a0b36d` | `tests/test_drift_analysis.py` | resolved |

## Selected TailTrail Features

| Feature | When used | Why it is selected |
|---|---|---|
| Navigator | planning | established the evidence-bound scope and approval boundary |
| Token Autopilot | as required by the plan | selected for this task |
| Code Graph Mapper | as required by the plan | selected for this task |
| Learning Capture Trigger | as required by the plan | selected for this task |
| Test Precision Planner | as required by the plan | selected for this task |
| Handoff | as required by the plan | selected for this task |
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
| REQ-01 | not recorded | The drift gate accepts the transition only when the saved and inline evidence union satisfies every required tier; missing, failing, stale, untrusted, or unlinked receipts keep it blocked. | behaviour |

### Scoped evidence

| Path | Role | Planned use | Confidence |
|---|---|---|---|
| `scripts/drift_analysis.py` | supporting candidate | Inspect after approval; edit only when the confirmed behaviour path requires it. | repository-inventory hypothesis |

### Post-change checks

1. Confirm the actor, starting state, authoritative state owner, and observable interface before the first edit.
2. Map each actual transition and side effect to an approved behaviour scenario and requirement ID.
3. Reconcile actual changed paths with the approved behaviour roles; justify or correct unexpected scope.
4. Require matching behaviour and integration receipts; unit evidence alone cannot complete the Behaviour Harness.
5. Report unresolved scenarios as evidence-incomplete or drifted, never as a generic pass.

## Focused Validation Coverage Summary

- **Requirements covered:** 1/1.
- **Proof command reuse:**
  - `cmd-817eac` covers 1 requirement(s): REQ-01.
  - `cmd-a0b36d` covers 1 requirement(s): REQ-01.

## Token Estimate

- **Planned working set:** approximately `785` tokens (confidence: `medium`).
- **Scoped-file ceiling:** approximately `5275` tokens; estimated reduction `85.12%`.
- **Confidence basis:** at least one bounded slice lacks an exact combined behavior-and-symbol anchor.
- This is an estimate from saved scope, not measured model/provider usage.

## Implementation Boundary

- **Editable scope:** `scripts/drift_analysis.py`.
- **Read-only / proof-only scope:** `tests/test_drift_analysis.py`.
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

- Machine-readable state remains available at [`.tailtrail/runs/start-20261030165734-fb62e6/planning/revisions/start-report-v2.json`](.tailtrail/runs/start-20261030165734-fb62e6/planning/revisions/start-report-v2.json); it is not the approval view.

---

*End of Start Plan.*