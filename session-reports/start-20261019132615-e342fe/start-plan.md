# TailTrail Start Plan - Full Review Record

**Presentation version:** `4`

## Planning Lock

- **Run ID:** `start-20261019132615-e342fe`
- **Status:** `awaiting-approval`
- **Goal:** Enable TailTrail to create content fingerprints for explicitly selected oversized implementation owners without reading their source bodies into scope evidence, while preserving sensitive and unsafe file rejection.
- **Managed writes allowed:** `false`
- **Execution status:** planning only; no source change, proof command, scanner, or Git operation has run.
- **Plan revision:** active `1`; pending `none`.

## Command Reference Registry

| ID | Kind | Command |
|---|---|---|
| `cmd-3bf405` | proof | `python3 -m unittest discover -s tests -p test_navigator_scope.py -v` |
| `cmd-93b907` | proof | `python3 -m unittest tests.test_navigator_scope` |

## Validation Requirements And Focused Validation Matrix

### REQ-01

**Description:** Enable TailTrail to create content fingerprints for explicitly selected oversized implementation owners without reading their source bodies into scope evidence, while preserving sensitive and unsafe file rejection.

- **Requirement type:** `change`
- **Validation state:** `required`
- **Editable owner(s):** `scripts/navigator_scope.py`
- **Read-only input(s):** `scripts/task-start.py`
- **Proof path(s):** `tests/test_navigator_scope.py`
- **Success criteria:** The stated requirement is observably satisfied on its approved path.; An explicitly selected oversized implementation owner receives a stable SHA-256 fingerprint without its source body entering scope evidence.; The public Start scope-owner path can validate that fingerprint and proceed when the owner is otherwise evidence-backed.; The focused regression covers the reported oversized-owner case through the public Start path.
- **Preservation criteria:** Do not change behavior outside this approved requirement boundary.; Sensitive, binary, non-UTF-8, traversal, and symlink paths remain rejected.; Ordinary source-body discovery remains bounded and does not admit oversized bodies into scope evidence.; An oversized file that was not explicitly selected does not gain owner authority merely because it can be hashed.

| Tier | Command ID | Candidate | State |
|---|---|---|---|
| unit | `cmd-3bf405` | `tests/test_navigator_scope.py` | resolved |
| unit | `cmd-93b907` | `tests/test_navigator_scope.py` | resolved |
| contract | `cmd-93b907` | `tests/test_navigator_scope.py` | resolved |

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

- **Status:** `planning-hypothesis`.
- **Evidence boundary:** Derived from explicit user wording and repository path inventory only. Source, caller relationships, and edit necessity are not confirmed until after approval.

| Requirement | Invariant | Planned proof |
|---|---|---|
| REQ-01 | The implementation must follow the existing repository boundaries discovered after approval. | Changed-scope comparison plus the repository's focused tests. |

### Scoped evidence

| Path | Role | Planned use | Confidence |
|---|---|---|---|
| `scripts/navigator_scope.py` | implementation candidate | Primary implementation candidate, subject to post-approval source and caller confirmation. | repository-inventory hypothesis |

### Post-change checks

1. Confirm the authoritative boundary and material callers before the first edit.
2. Compare actual changed files and symbols with the approved impact map; justify or correct every unexpected path.
3. Detect missed callers, caller-specific business logic, wrong-layer placement, and public-contract drift.
4. Check dependency manifests and imports when the approved contract forbids a new dependency.
5. Run every requirement-linked validation tier and preserve unresolved evidence as a gap, not a pass.

## Behaviour Analysis

- **Status:** `not selected`. This control is not part of the approved proof boundary for this plan.

## Focused Validation Coverage Summary

- **Requirements covered:** 1/1.
- **Proof command reuse:**
  - `cmd-3bf405` covers 1 requirement(s): REQ-01.
  - `cmd-93b907` covers 1 requirement(s): REQ-01.

## Token Estimate

- **Planned working set:** approximately `9364` tokens (confidence: `medium`).
- **Scoped-file ceiling:** approximately `65784` tokens; estimated reduction `85.77%`.
- **Confidence basis:** at least one bounded slice lacks an exact combined behavior-and-symbol anchor.
- This is an estimate from saved scope, not measured model/provider usage.

## Implementation Boundary

- **Editable scope:** `scripts/navigator_scope.py`.
- **Read-only / proof-only scope:** `scripts/task-start.py`, `tests/test_navigator_scope.py`.
- **Excluded:** every path, command, external system, deployment, and data change not explicitly recorded above remains outside this approval.
- **Data impact:** no data impact is authorized unless a requirement above names it explicitly.

## Approval Checklist

- [x] Requirements are present and reviewable.
- [x] Every requirement has an editable implementation owner.
- [x] Runnable proof commands are registered and mapped to requirements.
- [x] Material questions are resolved.
- [ ] Mandatory planning audit is clean for this exact plan revision.
- [ ] The host has reviewed the scope, preservation criteria, proof commands, analyses, and excluded boundary.

## Review Cycles Summary

| Cycle | Revision | Status | Action |
|---|---|---|---|
| 1 | v1 | initial review | Start Plan generated and mandatory audit required |

- **Total review cycles:** 1
- **Revision cycles:** 0
- **Latest audit:** not yet recorded. Run the mandatory planning audit before approval.

## Approval Decision

**NOT READY FOR APPROVAL** — resolve or revise: a clean mandatory planning audit.

## Canonical Machine Record

- Machine-readable state remains available at [`.tailtrail/runs/start-20261019132615-e342fe/planning/start-report-v1.json`](.tailtrail/runs/start-20261019132615-e342fe/planning/start-report-v1.json); it is not the approval view.

---

*End of Start Plan.*