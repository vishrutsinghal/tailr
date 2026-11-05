# TailTrail Start Plan - Full Review Record

**Presentation version:** `5`
**Plan detail:** `Expert` (automatic for AIDLC Lite)

## Planning Lock

- **Run ID:** `start-20261104113216-770659`
- **Status:** `approved`
- **Goal:** Implement Phase 1B package inventory inclusion from TAILTRAIL-BUNDLED-OFFLINE-AIDLC-PROVISIONING-DESIGN.md by updating package-manifest.json to require the complete aidlc-rules bundle and current official-pack runtime assurance assets so setup.py packages them and includes every bundled byte in package-integrity.json; prove with tests/test_self_contained_package.py; exclude MANIFEST.in, release-manifest.json, .gitattributes, package-release-proof logic, resolver, Full routing, and host projection.
- **Request mode:** `implementation`
- **Managed writes allowed:** `true`
- **Execution status:** planning only; no source change, proof command, scanner, or Git operation has run.
- **Plan revision:** active `9`; pending `none`.

## Bound Planning Inputs

| ID | Role | Path or reference | Access | Status | Integrity |
|---|---|---|---|---|---|
| `IN-02` | requirement-artifact | `/Users/vsingha7/Desktop/tailr/TAILTRAIL-BUNDLED-OFFLINE-AIDLC-PROVISIONING-DESIGN.md` | read-only | inspected | `d4f7415dd001cb13521cd42de6d44260df89ef6313ec66178cbf1dcf2fda9426` |
- These inputs remain read-only context and never grant editable implementation scope.

## Command Reference Registry

| ID | Kind | Command |
|---|---|---|
| `cmd-2ce7f0` | proof | `python3 -m unittest tests/test_self_contained_package.py` |

## Validation Requirements And Focused Validation Matrix

### REQ-01

**Description:** Require the complete official AIDLC bundle and current runtime assurance assets in package-manifest.json by adding aidlc-rules to required_directories so built packages and outer package integrity include every bundled byte, while preserving setup.py behavior and keeping source-distribution, release-candidate, resolver, Full-routing, and host-projection changes outside this plan.

- **Requirement type:** `change`
- **Validation state:** `required`
- **Editable owner(s):** `package-manifest.json`
- **Read-only input(s):** `TAILTRAIL-BUNDLED-OFFLINE-AIDLC-PROVISIONING-DESIGN.md`, `aidlc-rules/manifest.json`, `setup.py`
- **Proof path(s):** `tests/test_self_contained_package.py`
- **Proof intent:** `tests/test_self_contained_package.py` = `editable-proof` (baseline `not-run`)
- **Success criteria:** package-manifest.json requires the complete aidlc-rules directory and current official-pack runtime assurance assets so setup.py includes them in the package payload and outer package-integrity inventory.; The built wheel contains the complete bundle and package-integrity covers every packaged AIDLC byte.
- **Preservation criteria:** Do not change setup.py selection behavior, source-distribution selection, release-candidate policy, resolver behavior, Full routing, or host projection.; Do not add nonexistent future resolver modules to runtime_required or weaken required-resource failure behavior.
- **Requirement behaviour scenarios:**
  - `BHV-PHASE1B-PACKAGE-INVENTORY`: Build the TailTrail wheel and source distribution, then inspect the aidlc-rules inventory and package-integrity coverage in both artifacts. → Both artifacts contain the complete official AIDLC bundle and every packaged bundle byte is covered by the outer package-integrity inventory.

| Tier | Command ID | Command | Candidate | State |
|---|---|---|---|---|
| behaviour | `cmd-2ce7f0` | `python3 -m unittest tests/test_self_contained_package.py` | `tests/test_self_contained_package.py` | resolved |
| contract | `cmd-2ce7f0` | `python3 -m unittest tests/test_self_contained_package.py` | `tests/test_self_contained_package.py` | resolved |
| integration | `cmd-2ce7f0` | `python3 -m unittest tests/test_self_contained_package.py` | `tests/test_self_contained_package.py` | resolved |

## Plan

1. **REQ-01:** Implement Require the complete official AIDLC bundle and current runtime assurance assets in package-manifest.json by adding aidlc-rules to required_directories so built packages and outer package integrity include every bundled byte, while preserving setup.py behavior and keeping source-distribution, release-candidate, resolver, Full-routing, and host-projection changes outside this plan. in `package-manifest.json`; verify with `cmd-2ce7f0`, `cmd-2ce7f0`, `cmd-2ce7f0`; inspect `TAILTRAIL-BUNDLED-OFFLINE-AIDLC-PROVISIONING-DESIGN.md`, `aidlc-rules/manifest.json`, `setup.py`; prove against `tests/test_self_contained_package.py`.
## Selected TailTrail Features

| Feature | When used | Why it is selected |
|---|---|---|
| Navigator | planning | established the evidence-bound scope and approval boundary |
| Token Autopilot | as required by the plan | selected for this task |
| Bootstrap Snapshot | as required by the plan | selected for this task |
| Code Review Graph Lite | as required by the plan | selected for this task |
| Code Graph Mapper | as required by the plan | selected for this task |
| Learning Capture Trigger | as required by the plan | selected for this task |
| AIDLC | as required by the plan | selected for this task |
| Review Lens | as required by the plan | selected for this task |
| Dependency Gate | as required by the plan | selected for this task |
| Focused QA Lens | as required by the plan | selected for this task |
| Test Precision Planner | as required by the plan | selected for this task |
| Handoff | as required by the plan | selected for this task |
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
| `package-manifest.json` | configuration boundary | Primary implementation candidate, subject to post-approval source and caller confirmation. | repository-inventory hypothesis |

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
  - `cmd-2ce7f0` covers 1 requirement(s): REQ-01.

## Token Estimate

- **Planned working set:** approximately `not calculable` tokens (confidence: `low`).
- **Scoped-file ceiling:** approximately `2906` tokens; estimated reduction `not recorded%`.
- **Confidence basis:** at least one scoped path has no reliable bounded range.
- This is an estimate from saved scope, not measured model/provider usage.

## Implementation Boundary

- **Editable scope:** `package-manifest.json`.
- **Writable outputs:** none recorded.
- **Editable validation scope:** `tests/test_self_contained_package.py`.
- **Run-only proof scope:** none recorded.
- **Read-only / proof-only scope:** `TAILTRAIL-BUNDLED-OFFLINE-AIDLC-PROVISIONING-DESIGN.md`, `aidlc-rules/manifest.json`, `setup.py`, `tests/test_self_contained_package.py`.
- **Excluded:** every path, command, external system, deployment, and data change not explicitly recorded above remains outside this approval.
- **Data impact:** no data impact is authorized unless a requirement above names it explicitly.

## Approval Checklist

- [x] Requirements are present and reviewable.
- [x] Every requirement has an editable implementation owner.
- [x] Runnable proof commands are registered and mapped to requirements.
- [x] Material questions are resolved.
- [x] Mandatory planning audit is clean for this exact plan revision.
- [ ] The host has reviewed the scope, preservation criteria, proof commands, analyses, and excluded boundary.
- **Risks to review:** dependency; release

## Review Cycles Summary

| Cycle | Revision | Status | Action |
|---|---|---|---|
| 1 | v1 | initial review | Start Plan generated and mandatory audit required |
| 2 | v2 | revision recorded | Plan changed and must be audited again |
| 3 | v3 | revision recorded | Plan changed and must be audited again |
| 4 | v4 | revision recorded | Plan changed and must be audited again |
| 5 | v5 | revision recorded | Plan changed and must be audited again |
| 6 | v6 | revision recorded | Plan changed and must be audited again |
| 7 | v7 | revision recorded | Plan changed and must be audited again |
| 8 | v8 | revision recorded | Plan changed and must be audited again |
| 9 | v9 | revision recorded | Plan changed and must be audited again |

- **Total review cycles:** 9
- **Revision cycles:** 8
- **Latest audit:** `clean`; 0 finding(s).

## Approval Decision

**READY FOR APPROVAL** — review this plan, then explicitly approve this exact run. Approval is separate from activation and permits no unlisted work.

## Canonical Machine Record

- Machine-readable state remains available at [`.tailtrail/runs/start-20261104113216-770659/planning/canonical-plan-projection-v17.json`](.tailtrail/runs/start-20261104113216-770659/planning/canonical-plan-projection-v17.json); it is not the approval view.

---

*End of Start Plan.*