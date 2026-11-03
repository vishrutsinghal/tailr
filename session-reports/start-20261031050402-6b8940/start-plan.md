# TailTrail Start Plan - Full Review Record

**Presentation version:** `4`

## Planning Lock

- **Run ID:** `start-20261031050402-6b8940`
- **Status:** `approved`
- **Goal:** Repair TailTrail in scripts/navigator_scope.py so an explicitly scoped existing implementation owner larger than the bounded source-body inspection limit receives a safe streaming full-content SHA-256 integrity fingerprint before host selection or host scope proposal creation, remains selectable only when hash-bound, and fails closed with actionable guidance when integrity cannot be established without weakening sensitive-path, symlink, binary, UTF-8, stale, or tamper safeguards.
- **Request mode:** `implementation`
- **Managed writes allowed:** `true`
- **Execution status:** planning only; no source change, proof command, scanner, or Git operation has run.
- **Plan revision:** active `5`; pending `none`.

## Bound Planning Inputs

| ID | Role | Path or reference | Access | Status | Integrity |
|---|---|---|---|---|---|
| `IN-02` | requirement-artifact | `/private/tmp/tailtrail-large-owner-integrity-requirements.md` | read-only | inspected | `cdef25807989089dff1a2daa9bb5b2bd7b01db946b641e18049134f1d767cd99` |
- These inputs remain read-only context and never grant editable implementation scope.

## Command Reference Registry

| ID | Kind | Command |
|---|---|---|
| `cmd-3a03e7` | proof | `python3 -m unittest tests.test_navigator_scope -v` |

## Validation Requirements And Focused Validation Matrix

### REQ-01

**Description:** Repair TailTrail in scripts/navigator_scope.py so an explicitly scoped existing implementation owner larger than the bounded source-body inspection limit receives a safe streaming full-content SHA-256 integrity fingerprint before host selection or host scope proposal creation, remains selectable only when hash-bound, and fails closed with actionable guidance when integrity cannot be established without weakening sensitive-path, symlink, binary, UTF-8, stale, or tamper safeguards.

- **Requirement type:** `change`
- **Validation state:** `required`
- **Editable owner(s):** `scripts/navigator_scope.py`
- **Proof path(s):** `tests/test_navigator_scope.py`
- **Success criteria:** The stated requirement is observably satisfied on its approved path.; An explicitly scoped valid text implementation owner above the source-body inspection limit can obtain a separately streamed full-content SHA-256 and be selected through the public Start route.; Every included implementation owner and host-offered explicit owner has a valid SHA-256 before scope proposal construction.; A path that cannot satisfy the integrity-hashing policy fails closed before proposal construction with actionable guidance.
- **Preservation criteria:** Do not change behavior outside this approved requirement boundary.; No large source body is placed in planning artifacts or model context.; Sensitive, symlinked, binary, non-UTF-8, stale, and tampered paths remain rejected.; No empty content fingerprint is serialized into a host scope proposal.
- **Requirement behaviour scenarios:**
  - `BHV-REQ-01-LARGE-OWNER-INTEGRITY`: Run the public Start route with an explicitly scoped valid UTF-8 implementation owner above the source-body inspection limit and submit its scope-owner selection. → TailTrail streams and binds a full SHA-256 without exposing the source body, accepts the supported owner selection, and fails closed before proposal creation when integrity is unavailable.

| Tier | Command ID | Candidate | State |
|---|---|---|---|
| contract | `cmd-3a03e7` | `tests/test_navigator_scope.py` | resolved |
| behaviour | `cmd-3a03e7` | `tests/test_navigator_scope.py` | resolved |
| unit | `cmd-3a03e7` | `tests/test_navigator_scope.py` | resolved |

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
  - `cmd-3a03e7` covers 1 requirement(s): REQ-01.

## Token Estimate

- **Planned working set:** approximately `902` tokens (confidence: `medium`).
- **Scoped-file ceiling:** approximately `65784` tokens; estimated reduction `98.63%`.
- **Confidence basis:** at least one bounded slice lacks an exact combined behavior-and-symbol anchor.
- This is an estimate from saved scope, not measured model/provider usage.

## Implementation Boundary

- **Editable scope:** `scripts/navigator_scope.py`.
- **Read-only / proof-only scope:** `tests/test_navigator_scope.py`.
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

- **Total review cycles:** 5
- **Revision cycles:** 4
- **Latest audit:** `clean`; 0 finding(s).

## Approval Decision

**READY FOR APPROVAL** — review this plan, then explicitly approve this exact run. Approval is separate from activation and permits no unlisted work.

## Canonical Machine Record

- Machine-readable state remains available at [`.tailtrail/runs/start-20261031050402-6b8940/planning/revisions/start-report-v5.json`](.tailtrail/runs/start-20261031050402-6b8940/planning/revisions/start-report-v5.json); it is not the approval view.

---

*End of Start Plan.*