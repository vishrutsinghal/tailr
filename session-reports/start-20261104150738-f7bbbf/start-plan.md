# TailTrail Start Plan - Full Review Record

**Presentation version:** `5`
**Plan detail:** `Expert` (automatic for AIDLC Lite)

## Planning Lock

- **Run ID:** `start-20261104150738-f7bbbf`
- **Status:** `approved`
- **Goal:** Implement Phase 2A.2 atomic content-addressed AIDLC project projection in tailtrail/aidlc_bundle.py: consume a ready Phase 2A.1 resolution receipt, use one bounded cross-platform lock, stage and validate exact bytes, atomically create or reuse an immutable pack, write separate projection and future-run selector receipts, preserve idempotence, fail closed on unsafe or conflicting state, and support explicit bounded stale-staging recovery; exclude public Full routing, frozen active-run binding, Requirements lookup, host adapters, schemas, package registration, and documentation.
- **Request mode:** `implementation`
- **Managed writes allowed:** `true`
- **Execution status:** planning only; no source change, proof command, scanner, or Git operation has run.
- **Plan revision:** active `2`; pending `none`.

## Bound Planning Inputs

- No read-only planning inputs were bound to this plan.

## Command Reference Registry

| ID | Kind | Command |
|---|---|---|
| `cmd-8960f1` | proof | `python3 -m unittest tests.test_aidlc_bundle_resolver` |

## Validation Requirements And Focused Validation Matrix

### REQ-01

**Description:** Extend the package-owned AIDLC bundle resolver with offline, bounded-lock, content-addressed project projection that atomically creates or reuses one immutable verified pack, writes separate projection and future-run selector receipts, preserves idempotence, fails closed without mutating unsafe or conflicting state, and supports explicit bounded stale-staging recovery.

- **Requirement type:** `change`
- **Validation state:** `required`
- **Editable owner(s):** `tailtrail/aidlc_bundle.py`
- **Read-only input(s):** `TAILTRAIL-BUNDLED-OFFLINE-AIDLC-PROVISIONING-DESIGN.md`, `package-manifest.json`, `scripts/run-ledger.py`, `tailtrail/install/engine.py`, `tailtrail/install/files.py`
- **Proof path(s):** `tests/test_aidlc_bundle_resolver.py`
- **Proof intent:** `tests/test_aidlc_bundle_resolver.py` = `editable-proof` (baseline `pass`)
- **Success criteria:** A ready Phase 2A.1 receipt projects into one immutable content-addressed pack through one bounded cross-platform lock and exact-byte atomic transaction.; Projection and future-run selector receipts remain separate, closed, fingerprinted contracts.; Repeat and concurrent calls are idempotent, while explicit bounded recovery owns only validated managed staging state.; A ready Phase 2A.1 resolution receipt can be projected into a content-addressed immutable pack under .tailtrail/official-aidlc/packs without changing the verified source bundle.; Provisioning uses one bounded cross-platform OS lock at .tailtrail/official-aidlc/locks/provision.lock, rechecks destination state after acquisition, stages on the destination filesystem, validates every copied byte, and atomically renames only into an absent destination.; A closed versioned projection receipt separately binds the source resolution fingerprint, source and project inventories, immutable pack identity, trust posture, creation result, and project projection fingerprint.; A closed versioned current.json selector is atomically created for future runs only and binds the exact immutable pack and projection receipt fingerprints.; Repeated provisioning of the same valid bundle returns reused without rewriting pack files, changing their modification times, appending duplicate projection events, or replacing an identical selector.; Concurrent provisioning produces one created result and one reused result without exposing a partial pack.; An explicit bounded recovery operation can remove only a named stale staging directory created under the managed packs root; ordinary provisioning reports pre-existing staging state and does not silently clean it.; Focused proof covers successful creation, idempotent reuse, selector stability, lock timeout and release, concurrent calls, interrupted staging recovery, deep target roots, and negative destination states.
- **Preservation criteria:** Extend the package-owned AIDLC bundle resolver with offline, bounded-lock, content-addressed project projection that atomically creates or reuses one immutable verified pack, writes separate projection and future-run selector receipts, preserves idempotence, fails closed without mutating unsafe or conflicting state, and supports explicit bounded stale-staging recovery.; Provisioning never contacts the network, executes pack content, mutates source bytes, overwrites occupied state, silently retargets a selector, or cleans pre-existing staging state during an ordinary call.; This slice does not implement active-run binding, Requirements lookup, public Full routing, host projection, schema files, package registration, or documentation.; Provisioning never contacts the network, executes bundle content, mutates the source bundle, follows symlinks, writes outside the target .tailtrail directory, or weakens the Phase 2A.1 trust posture.; A missing, altered, incomplete, incompatible, unsafe, or occupied content-addressed destination blocks without overwrite, deletion, selector replacement, or automatic repair.; An existing selector for a different pack blocks until a separately approved migration; Phase 2A.2 never retargets an active run or treats current.json as an active-run binding.; Unknown filesystem errors fail immediately; retries are bounded and limited to explicitly recognized transient rename contention.; This slice does not edit generic installer helpers, public detector or installer scripts, Requirements lookup, Full Start routing, Planning Lock attachment, MCP routing, host adapters, schemas, package registration, or documentation.
- **Requirement behaviour scenarios:**
  - `BHV-PHASE2A2-PROJECTION`: Provision one verified Phase 2A.1 resolver receipt into a temporary project twice, exercise a racing caller, then exercise unsafe destination, conflicting selector, ordinary stale-staging, and explicit recovery states. → One immutable content-addressed pack is atomically created or reused without selector or timestamp churn; unsafe or conflicting state remains unchanged; ordinary calls do not clean staging; explicit recovery removes only validated stale staging; no network access or source-byte mutation occurs.

| Tier | Command ID | Command | Candidate | State |
|---|---|---|---|---|
| behaviour | `cmd-8960f1` | `python3 -m unittest tests.test_aidlc_bundle_resolver` | `tests/test_aidlc_bundle_resolver.py` | resolved |
| contract | `cmd-8960f1` | `python3 -m unittest tests.test_aidlc_bundle_resolver` | `tests/test_aidlc_bundle_resolver.py` | resolved |
| unit | `cmd-8960f1` | `python3 -m unittest tests.test_aidlc_bundle_resolver` | `tests/test_aidlc_bundle_resolver.py` | resolved |

## Plan

1. **REQ-01:** Implement Extend the package-owned AIDLC bundle resolver with offline, bounded-lock, content-addressed project projection that atomically creates or reuses one immutable verified pack, writes separate projection and future-run selector receipts, preserves idempotence, fails closed without mutating unsafe or conflicting state, and supports explicit bounded stale-staging recovery. in `tailtrail/aidlc_bundle.py`; verify with `cmd-8960f1`, `cmd-8960f1`, `cmd-8960f1`; inspect `TAILTRAIL-BUNDLED-OFFLINE-AIDLC-PROVISIONING-DESIGN.md`, `package-manifest.json`, `scripts/run-ledger.py`, `tailtrail/install/engine.py`, `tailtrail/install/files.py`; prove against `tests/test_aidlc_bundle_resolver.py`.
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
| Dependency Gate | as required by the plan | selected for this task |
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
| unassigned | Behaviour outside the approved change boundary remains compatible. | Existing preservation-path evidence plus focused regression proof. |

### Scoped evidence

| Path | Role | Planned use | Confidence |
|---|---|---|---|
| `tailtrail/aidlc_bundle.py` | implementation candidate | Primary implementation candidate, subject to post-approval source and caller confirmation. | repository-inventory hypothesis |
| `tests/test_aidlc_bundle_resolver.py` | test evidence | Run only when its tier proves an approved requirement. | repository-inventory hypothesis |

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
  - `cmd-8960f1` covers 1 requirement(s): REQ-01.

## Token Estimate

- **Planned working set:** approximately `1980` tokens (confidence: `medium`).
- **Scoped-file ceiling:** approximately `8887` tokens; estimated reduction `77.72%`.
- **Confidence basis:** at least one bounded slice lacks an exact combined behavior-and-symbol anchor.
- This is an estimate from saved scope, not measured model/provider usage.

## Implementation Boundary

- **Editable scope:** `tailtrail/aidlc_bundle.py`.
- **Writable outputs:** none recorded.
- **Editable validation scope:** `tests/test_aidlc_bundle_resolver.py`.
- **Run-only proof scope:** none recorded.
- **Read-only / proof-only scope:** `TAILTRAIL-BUNDLED-OFFLINE-AIDLC-PROVISIONING-DESIGN.md`, `package-manifest.json`, `scripts/run-ledger.py`, `tailtrail/install/engine.py`, `tailtrail/install/files.py`, `tests/test_aidlc_bundle_resolver.py`.
- **Excluded:** every path, command, external system, deployment, and data change not explicitly recorded above remains outside this approval.
- **Data impact:** no data impact is authorized unless a requirement above names it explicitly.

## Approval Checklist

- [x] Requirements are present and reviewable.
- [x] Every requirement has an editable implementation owner.
- [x] Runnable proof commands are registered and mapped to requirements.
- [x] Material questions are resolved.
- [x] Mandatory planning audit is clean for this exact plan revision.
- [ ] The host has reviewed the scope, preservation criteria, proof commands, analyses, and excluded boundary.
- **Risks to review:** dependency

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

- Machine-readable state remains available at [`.tailtrail/runs/start-20261104150738-f7bbbf/planning/canonical-plan-projection-v4.json`](.tailtrail/runs/start-20261104150738-f7bbbf/planning/canonical-plan-projection-v4.json); it is not the approval view.

---

*End of Start Plan.*