# TailTrail Start Plan - Full Review Record

**Presentation version:** `5`
**Plan detail:** `Expert` (automatic for AIDLC Lite)

## Planning Lock

- **Run ID:** `start-20261104091556-dd541c`
- **Status:** `approved`
- **Goal:** Implement Phase 1A read-only manifest validation from TAILTRAIL-BUNDLED-OFFLINE-AIDLC-PROVISIONING-DESIGN.md by extending scripts/aidlc-official-detect.py to validate restrictive v1 compatibility and schema-v2 official identity, compatibility, capabilities, provenance agreement, path safety, and exact regular-file inventory equality; prove with tests/test_aidlc_official_detect.py; exclude manifest production, packaging, resolver, Full routing, and host projection.
- **Request mode:** `implementation`
- **Managed writes allowed:** `true`
- **Execution status:** planning only; no source change, proof command, scanner, or Git operation has run.
- **Plan revision:** active `4`; pending `none`.

## Bound Planning Inputs

- No read-only planning inputs were bound to this plan.

## Command Reference Registry

| ID | Kind | Command |
|---|---|---|
| `cmd-dd7be4` | proof | `python3 -m unittest tests.test_aidlc_official_detect` |

## Validation Requirements And Focused Validation Matrix

### REQ-01

**Description:** Extend scripts/aidlc-official-detect.py as a read-only validator for restrictive v1 compatibility and schema-v2 official identity, compatibility, capabilities, provenance agreement, path safety, and exact regular-file inventory equality.

- **Requirement type:** `constraint`
- **Validation state:** `required`
- **Editable owner(s):** `scripts/aidlc-official-detect.py`
- **Read-only input(s):** `TAILTRAIL-BUNDLED-OFFLINE-AIDLC-PROVISIONING-DESIGN.md`, `schemas/official-aidlc-pack.schema.json`
- **Proof path(s):** `tests/test_aidlc_official_detect.py`, `tests/test_aidlc_official_install.py`
- **Success criteria:** The stated requirement is observably satisfied on its approved path.; The detector validates v1 compatibility and exact v2 bundle authority with actionable typed findings while remaining read-only.
- **Preservation criteria:** Do not change behavior outside this approved requirement boundary.; No manifest rewrite, provenance inference, provisioning, network access, packaging change, host selection, or Full-to-Lite downgrade.
- **Requirement behaviour scenarios:**
  - `BHV-REQ-01`: Run the read-only official AIDLC detector against valid v1, valid v2, and unsafe or inconsistent manifest fixtures → The detector reports supported compatible state only for valid bounded v1 or v2 input and rejects unsafe, incomplete, altered, unexpected, incompatible, or provenance-conflicting state without mutation

| Tier | Command ID | Command | Candidate | State |
|---|---|---|---|---|
| behaviour | `cmd-dd7be4` | `python3 -m unittest tests.test_aidlc_official_detect` | `tests/test_aidlc_official_detect.py` | resolved |
| contract | `cmd-dd7be4` | `python3 -m unittest tests.test_aidlc_official_detect` | `tests/test_aidlc_official_detect.py` | resolved |
| integration | `cmd-dd7be4` | `python3 -m unittest tests.test_aidlc_official_detect` | `tests/test_aidlc_official_detect.py` | resolved |
| unit | `cmd-dd7be4` | `python3 -m unittest tests.test_aidlc_official_detect` | `tests/test_aidlc_official_detect.py` | resolved |

## Plan

1. **REQ-01:** Implement Extend scripts/aidlc-official-detect.py as a read-only validator for restrictive v1 compatibility and schema-v2 official identity, compatibility, capabilities, provenance agreement, path safety, and exact regular-file inventory equality. in `scripts/aidlc-official-detect.py`; verify with `cmd-dd7be4`, `cmd-dd7be4`, `cmd-dd7be4`, `cmd-dd7be4`; inspect `TAILTRAIL-BUNDLED-OFFLINE-AIDLC-PROVISIONING-DESIGN.md`, `schemas/official-aidlc-pack.schema.json`; prove against `tests/test_aidlc_official_detect.py`, `tests/test_aidlc_official_install.py`.
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
| `scripts/aidlc-official-detect.py` | implementation candidate | Primary implementation candidate, subject to post-approval source and caller confirmation. | repository-inventory hypothesis |
| `tests/test_aidlc_official_install.py` | test evidence | Run only when its tier proves an approved requirement. | repository-inventory hypothesis |

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
  - `cmd-dd7be4` covers 1 requirement(s): REQ-01.

## Token Estimate

- **Planned working set:** approximately `445` tokens (confidence: `medium`).
- **Scoped-file ceiling:** approximately `3264` tokens; estimated reduction `86.37%`.
- **Confidence basis:** at least one bounded slice lacks an exact combined behavior-and-symbol anchor.
- This is an estimate from saved scope, not measured model/provider usage.

## Implementation Boundary

- **Editable scope:** `scripts/aidlc-official-detect.py`.
- **Writable outputs:** none recorded.
- **Read-only / proof-only scope:** `TAILTRAIL-BUNDLED-OFFLINE-AIDLC-PROVISIONING-DESIGN.md`, `schemas/official-aidlc-pack.schema.json`, `tests/test_aidlc_official_detect.py`, `tests/test_aidlc_official_install.py`.
- **Excluded:** every path, command, external system, deployment, and data change not explicitly recorded above remains outside this approval.
- **Data impact:** no data impact is authorized unless a requirement above names it explicitly.

## Approval Checklist

- [x] Requirements are present and reviewable.
- [x] Every requirement has an editable implementation owner.
- [x] Runnable proof commands are registered and mapped to requirements.
- [x] Material questions are resolved.
- [x] Mandatory planning audit is clean for this exact plan revision.
- [ ] The host has reviewed the scope, preservation criteria, proof commands, analyses, and excluded boundary.
- **Risks to review:** data shape; production

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

- Machine-readable state remains available at [`.tailtrail/runs/start-20261104091556-dd541c/planning/canonical-plan-projection-v6.json`](.tailtrail/runs/start-20261104091556-dd541c/planning/canonical-plan-projection-v6.json); it is not the approval view.

---

*End of Start Plan.*