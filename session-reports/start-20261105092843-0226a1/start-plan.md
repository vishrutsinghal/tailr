# TailTrail Start Plan - Full Review Record

**Presentation version:** `5`
**Plan detail:** `Expert` (automatic for AIDLC Lite)

## Planning Lock

- **Run ID:** `start-20261105092843-0226a1`
- **Status:** `approved`
- **Goal:** Implement Phase 3B bundled Full bridge identity persistence in scripts/aidlc-official-bridge.py using the current dirty worktree as the shared baseline: add a bridge persistence API that accepts only a ready Phase 3A bundled Full preflight result, records the same sealed resolution fingerprint, project projection fingerprint, pack fingerprint, pack path, trust posture, and offline posture in immutable run-local bridge identity, rejects unavailable or mismatched preflight data before any bridge artifact is written, never grants Planning Lock authority, preserves existing Standard and legacy explicit-manifest create behavior, and leaves task-start, Planning Lock, Requirements-stage, MCP, host projection, packaging, schema, registry, CLI, and documentation wiring for later Phase 3 slices; prove it with python3 -m unittest tests/test_aidlc_official_bridge.py -k full_bridge_maps_official_identity -k bundled_full_bridge_identity -v.
- **Request mode:** `implementation`
- **Managed writes allowed:** `true`
- **Execution status:** planning only; no source change, proof command, scanner, or Git operation has run.
- **Plan revision:** active `2`; pending `none`.

## Bound Planning Inputs

- No read-only planning inputs were bound to this plan.

## Command Reference Registry

| ID | Kind | Command |
|---|---|---|
| `cmd-74a487` | proof | `python3 -m unittest tests/test_aidlc_official_bridge.py -k full_bridge_maps_official_identity -k bundled_full_bridge_identity -v` |

## Validation Requirements And Focused Validation Matrix

### REQ-01

**Description:** Add a Phase 3B bridge persistence API that records one immutable bundled Full resolution-to-project identity from a ready Phase 3A preflight result and rejects unsafe or inconsistent input before writing.

- **Requirement type:** `change`
- **Validation state:** `required`
- **Editable owner(s):** `scripts/aidlc-official-bridge.py`
- **Read-only input(s):** `TAILTRAIL-BUNDLED-OFFLINE-AIDLC-PROVISIONING-DESIGN.md`, `scripts/official-aidlc-requirements.py`, `scripts/planning_lock.py`, `scripts/task-start.py`, `tailtrail/aidlc_bundle.py`, `tests/test_aidlc_bundle_resolver.py`
- **Proof path(s):** `tests/test_aidlc_official_bridge.py`
- **Proof intent:** `tests/test_aidlc_official_bridge.py` = `editable-proof` (baseline `not-run`)
- **Success criteria:** The bridge persists exactly one ready Phase 3A bundled Full identity without repeating resolver or projector work.; The immutable artifact retains Full mode, offline posture, resolution/projection/pack fingerprints and path, trust posture, and official provenance identity.; Unsafe, unavailable, mismatched, or conflicting inputs fail before writing or granting authority.; Repeated identical persistence reuses append-only state, while a conflicting identity cannot overwrite it.; The targeted command covers legacy bridge preservation and all new bundled identity cases.; The bridge exposes a Phase 3B persistence API that accepts only a ready Phase 3A bundled Full preflight result and records one immutable run-local bridge identity without re-resolving or re-projecting the pack.; The saved bridge identity retains requested and effective Full mode, network_used false, the sealed resolution receipt fingerprint, source-resolution fingerprint, project projection fingerprint, pack fingerprint, pack path, trust posture, and official source/revision/commit identity supplied by the ready preflight chain.; Unavailable, malformed, unsealed, network-using, Lite, or resolution/projection-mismatched preflight input is rejected before any bridge artifact or authority is created.; Repeated persistence of the same identity is idempotent; a different identity for the same run fails closed instead of overwriting append-only history.; Existing Standard and legacy explicit-manifest create behavior remains unchanged and the exact targeted proof selects its existing preservation test plus the new bundled_full_bridge_identity tests.
- **Preservation criteria:** No task-start, Planning Lock, Requirements-stage, MCP, host-projection, packaging, schema, registry, CLI, or documentation wiring is changed in Phase 3B.; The persistence path does not access the network, resolve, provision, execute pack content, activate a run, or fall back to Lite.; No state outside the approved bridge owner, editable proof, and run-local managed bridge/ledger artifacts is changed.; Existing Standard and legacy explicit-manifest create behavior remains unchanged.; Phase 3B does not wire task-start, Planning Lock, Requirements-stage lookup, MCP, host projection, packaging, schemas, registry, CLI dispatch, or documentation; those remain later Phase 3 slices.; The persistence API never invokes network access, resolver discovery, project provisioning, pack code, or Planning Lock activation and never converts blocked Full input to Lite.; The bundle resolver/projector, task-start, Planning Lock, Requirements adapter, MCP server, host adapters, schemas, manifests, registry, commands, and documentation are inspection-only or excluded from edits.; No existing bridge identity is mutated or silently replaced, and no state outside the run-local managed bridge artifact and ledger event is written.; No proof command broader than the two named unittest filters is authorized in this slice.
- **Requirement behaviour scenarios:**
  - `BHV-PHASE3B-BUNDLED-FULL-BRIDGE-IDENTITY`: Persist one ready Phase 3A bundled Full preflight identity twice, then attempt persistence with unavailable, fingerprint-mismatched, network-using, and conflicting preflight inputs while exercising the existing legacy bridge creation path. → The first ready identity is recorded with the exact resolution, projection, pack, trust, offline, and official identity fields; the identical retry reuses it; unsafe or conflicting inputs create no new bridge artifact and never become Lite; existing legacy bridge creation and activation remain unchanged.

| Tier | Command ID | Command | Candidate | State |
|---|---|---|---|---|
| behaviour | `cmd-74a487` | `python3 -m unittest tests/test_aidlc_official_bridge.py -k full_bridge_maps_official_identity -k bundled_full_bridge_identity -v` | `tests/test_aidlc_official_bridge.py` | resolved |
| contract | `cmd-74a487` | `python3 -m unittest tests/test_aidlc_official_bridge.py -k full_bridge_maps_official_identity -k bundled_full_bridge_identity -v` | `tests/test_aidlc_official_bridge.py` | resolved |
| unit | `cmd-74a487` | `python3 -m unittest tests/test_aidlc_official_bridge.py -k full_bridge_maps_official_identity -k bundled_full_bridge_identity -v` | `tests/test_aidlc_official_bridge.py` | resolved |

## Plan

1. **REQ-01:** Implement Add a Phase 3B bridge persistence API that records one immutable bundled Full resolution-to-project identity from a ready Phase 3A preflight result and rejects unsafe or inconsistent input before writing. in `scripts/aidlc-official-bridge.py`; verify with `cmd-74a487`, `cmd-74a487`, `cmd-74a487`; inspect `TAILTRAIL-BUNDLED-OFFLINE-AIDLC-PROVISIONING-DESIGN.md`, `scripts/official-aidlc-requirements.py`, `scripts/planning_lock.py`, `scripts/task-start.py`, `tailtrail/aidlc_bundle.py`, `tests/test_aidlc_bundle_resolver.py`; prove against `tests/test_aidlc_official_bridge.py`.
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
| `scripts/aidlc-official-bridge.py` | implementation candidate | Primary implementation candidate, subject to post-approval source and caller confirmation. | repository-inventory hypothesis |
| `tests/test_aidlc_official_bridge.py` | test evidence | Run only when its tier proves an approved requirement. | repository-inventory hypothesis |

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
  - `cmd-74a487` covers 1 requirement(s): REQ-01.

## Token Estimate

- **Planned working set:** approximately `779` tokens (confidence: `medium`).
- **Scoped-file ceiling:** approximately `12915` tokens; estimated reduction `93.97%`.
- **Confidence basis:** at least one bounded slice lacks an exact combined behavior-and-symbol anchor.
- This is an estimate from saved scope, not measured model/provider usage.

## Implementation Boundary

- **Editable scope:** `scripts/aidlc-official-bridge.py`.
- **Writable outputs:** none recorded.
- **Editable validation scope:** `tests/test_aidlc_official_bridge.py`.
- **Run-only proof scope:** none recorded.
- **Read-only / proof-only scope:** `TAILTRAIL-BUNDLED-OFFLINE-AIDLC-PROVISIONING-DESIGN.md`, `scripts/official-aidlc-requirements.py`, `scripts/planning_lock.py`, `scripts/task-start.py`, `tailtrail/aidlc_bundle.py`, `tests/test_aidlc_bundle_resolver.py`, `tests/test_aidlc_official_bridge.py`.
- **Excluded:** every path, command, external system, deployment, and data change not explicitly recorded above remains outside this approval.
- **Data impact:** no data impact is authorized unless a requirement above names it explicitly.

## Approval Checklist

- [x] Requirements are present and reviewable.
- [x] Every requirement has an editable implementation owner.
- [x] Runnable proof commands are registered and mapped to requirements.
- [x] Material questions are resolved.
- [x] Mandatory planning audit is clean for this exact plan revision.
- [ ] The host has reviewed the scope, preservation criteria, proof commands, analyses, and excluded boundary.
- **Risks to review:** data shape

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

- Machine-readable state remains available at [`.tailtrail/runs/start-20261105092843-0226a1/planning/canonical-plan-projection-v4.json`](.tailtrail/runs/start-20261105092843-0226a1/planning/canonical-plan-projection-v4.json); it is not the approval view.

---

*End of Start Plan.*