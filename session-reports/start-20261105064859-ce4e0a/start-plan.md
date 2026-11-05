# TailTrail Start Plan - Full Review Record

**Presentation version:** `5`
**Plan detail:** `Expert` (automatic for AIDLC Lite)

## Planning Lock

- **Run ID:** `start-20261105064859-ce4e0a`
- **Status:** `approved`
- **Goal:** Implement Phase 2B.1 frozen active-run AIDLC binding service in tailtrail/aidlc_bundle.py using the current dirty worktree as the shared baseline: mint and reuse an immutable sealed run binding for the exact verified Phase 2A.2 pack and projection receipt; resolve active runs without consulting current.json; keep selector changes future-run-only; support bounded read-only legacy-v1 continuation without allowing legacy state to authorize a new Full run; provide read-only status and explicit offline provision service behavior; fail closed on missing, altered, stale, incompatible, conflicting, or unsafe state; exclude the Requirements adapter, Full Start and Planning Lock wiring, MCP routing, host projection, schemas, package registration, CLI dispatcher commands, and documentation.
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

**Description:** Extend the package-owned AIDLC bundle service with immutable frozen active-run binding, selector-independent run resolution, bounded read-only legacy-v1 continuation, read-only readiness status, and explicit offline provision service behavior.

- **Requirement type:** `change`
- **Validation state:** `required`
- **Editable owner(s):** `tailtrail/aidlc_bundle.py`
- **Read-only input(s):** `TAILTRAIL-BUNDLED-OFFLINE-AIDLC-PROVISIONING-DESIGN.md`, `schemas/official-aidlc-pack.schema.json`, `scripts/aidlc-official-bridge.py`, `scripts/aidlc-official-detect.py`, `scripts/official-aidlc-requirements.py`, `scripts/official-aidlc-state.py`, `scripts/planning_lock.py`
- **Proof path(s):** `tests/test_aidlc_bundle_resolver.py`
- **Proof intent:** `tests/test_aidlc_bundle_resolver.py` = `editable-proof` (baseline `pass`)
- **Success criteria:** A Phase 2A.2 projection mints or reuses one sealed immutable active-run binding and resolves the exact bound pack independently of current.json.; Legacy-v1 continuation is explicitly bounded and read-only, status is non-mutating, and explicit provision reuses the offline projection service.; Focused proof exercises binding, selector independence, integrity failures, compatibility, status, provision, and zero-network preservation.; A ready Phase 2A.2 projection result can mint one immutable sealed active-run binding that records the exact run identity, pack path, pack fingerprint, projection fingerprint, source-resolution fingerprint, project identity, trust posture, and compatibility mode.; Resolving an active run validates the binding seal, the complete bound pack inventory, its projection receipt, and every linked fingerprint without consulting current.json.; Changing current.json after binding affects future selection only and never retargets an existing valid run.; A bounded legacy schema-v1 continuation is explicitly classified as legacy-read-only and can resolve only an already-authorized legacy run; it cannot mint a new Full binding or be promoted to schema v2.; Read-only status reports package, projection, selector, frozen-run, trust, compatibility, and provisioning-needed state without changing the filesystem.; Explicit provision service behavior reuses the Phase 2A.2 offline transaction and returns created or reused projection identity without creating run authority.; Focused proof covers binding creation and reuse, selector changes after binding, complete fingerprint validation, missing or altered packs and receipts, incompatible and unsafe state, bounded legacy continuation, read-only status, explicit provision, and zero network access.
- **Preservation criteria:** No operation contacts the network, executes pack content, mutates source bytes, rewrites an existing binding, follows unsafe links, silently upgrades legacy state, or grants new Full authority from legacy state.; Missing, altered, stale, incompatible, conflicting, or unsafe state blocks without changing source, pack, selector, or run state.; This slice does not edit the Requirements adapter or implement Full Start, Planning Lock, MCP, host, schema, registry, dispatcher, or documentation wiring.; Phase 2B.1 never contacts the network, executes pack content, mutates source bundle bytes, rewrites an existing active-run binding, follows symlinks, trusts current.json for an active run, or silently upgrades legacy state.; Missing, altered, stale, incompatible, conflicting, or unsafe bound state fails closed with categorical issues and leaves source, pack, selector, and run state unchanged.; A legacy schema-v1 pack can support only an already-authorized bounded continuation and never authorizes a new Full run.; This slice does not edit the official Requirements adapter, Full Start or Planning Lock wiring, MCP routing, host projection, schemas, package registration, CLI dispatcher commands, or documentation.
- **Requirement behaviour scenarios:**
  - `BHV-PHASE2B1-FROZEN-BINDING`: Provision one verified Phase 2A.2 pack, bind an active run to it, change the future-run selector, then resolve the active run and exercise altered bound-pack, bounded legacy-v1, read-only status, and explicit provision states. → The active run continues to resolve only its original verified pack regardless of selector changes; altered or incompatible bound state blocks without mutation; legacy continuation stays read-only and cannot mint new Full authority; status changes no files; explicit provision remains offline and returns created or reused identity.

| Tier | Command ID | Command | Candidate | State |
|---|---|---|---|---|
| behaviour | `cmd-8960f1` | `python3 -m unittest tests.test_aidlc_bundle_resolver` | `tests/test_aidlc_bundle_resolver.py` | resolved |
| contract | `cmd-8960f1` | `python3 -m unittest tests.test_aidlc_bundle_resolver` | `tests/test_aidlc_bundle_resolver.py` | resolved |
| unit | `cmd-8960f1` | `python3 -m unittest tests.test_aidlc_bundle_resolver` | `tests/test_aidlc_bundle_resolver.py` | resolved |

## Plan

1. **REQ-01:** Implement Extend the package-owned AIDLC bundle service with immutable frozen active-run binding, selector-independent run resolution, bounded read-only legacy-v1 continuation, read-only readiness status, and explicit offline provision service behavior. in `tailtrail/aidlc_bundle.py`; verify with `cmd-8960f1`, `cmd-8960f1`, `cmd-8960f1`; inspect `TAILTRAIL-BUNDLED-OFFLINE-AIDLC-PROVISIONING-DESIGN.md`, `schemas/official-aidlc-pack.schema.json`, `scripts/aidlc-official-bridge.py`, `scripts/aidlc-official-detect.py`, `scripts/official-aidlc-requirements.py`, `scripts/official-aidlc-state.py`, `scripts/planning_lock.py`; prove against `tests/test_aidlc_bundle_resolver.py`.
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

- **Planned working set:** approximately `4656` tokens (confidence: `medium`).
- **Scoped-file ceiling:** approximately `17712` tokens; estimated reduction `73.71%`.
- **Confidence basis:** at least one bounded slice lacks an exact combined behavior-and-symbol anchor.
- This is an estimate from saved scope, not measured model/provider usage.

## Implementation Boundary

- **Editable scope:** `tailtrail/aidlc_bundle.py`.
- **Writable outputs:** none recorded.
- **Editable validation scope:** `tests/test_aidlc_bundle_resolver.py`.
- **Run-only proof scope:** none recorded.
- **Read-only / proof-only scope:** `TAILTRAIL-BUNDLED-OFFLINE-AIDLC-PROVISIONING-DESIGN.md`, `schemas/official-aidlc-pack.schema.json`, `scripts/aidlc-official-bridge.py`, `scripts/aidlc-official-detect.py`, `scripts/official-aidlc-requirements.py`, `scripts/official-aidlc-state.py`, `scripts/planning_lock.py`, `tests/test_aidlc_bundle_resolver.py`.
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

- Machine-readable state remains available at [`.tailtrail/runs/start-20261105064859-ce4e0a/planning/canonical-plan-projection-v4.json`](.tailtrail/runs/start-20261105064859-ce4e0a/planning/canonical-plan-projection-v4.json); it is not the approval view.

---

*End of Start Plan.*