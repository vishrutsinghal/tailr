# TailTrail Start Plan - Full Review Record

**Presentation version:** `5`
**Plan detail:** `Expert` (automatic for AIDLC Lite)

## Planning Lock

- **Run ID:** `start-20261105075910-50dfb3`
- **Status:** `approved`
- **Goal:** Implement corrected Phase 2B.2 frozen-resolution adapter API in scripts/official-aidlc-requirements.py using the current dirty worktree as the shared baseline: add a read-only existing-run contract resolver that takes project root and run ID, uses tailtrail/aidlc_bundle.py to resolve the frozen bundled-v2 binding or bounded legacy-v1 continuation, derives and validates all required official Requirements rule references only from that resolved immutable pack, ignores current.json, process cwd, and caller manifest paths, and fails closed without mutation or fallback on invalid authority; preserve existing pre-run stage_contract, public stage_request, and host-question behavior unchanged until Phase 3 wires provisioning and binding before the public route; prove with python3 -m unittest tests.test_aidlc_official_bridge; exclude task-start, Planning Lock, bridge, MCP, host projection, schema, package, CLI, and documentation changes.
- **Request mode:** `implementation`
- **Managed writes allowed:** `true`
- **Execution status:** planning only; no source change, proof command, scanner, or Git operation has run.
- **Plan revision:** active `2`; pending `none`.

## Bound Planning Inputs

- No read-only planning inputs were bound to this plan.

## Command Reference Registry

| ID | Kind | Command |
|---|---|---|
| `cmd-c02cdb` | proof | `python3 -m unittest tests.test_aidlc_official_bridge` |

## Validation Requirements And Focused Validation Matrix

### REQ-01

**Description:** Add a read-only official Requirements adapter API that resolves rule references from a validated frozen bundled-v2 run binding or bounded legacy-v1 continuation without changing the existing public route before Phase 3.

- **Requirement type:** `change`
- **Validation state:** `required`
- **Editable owner(s):** `scripts/official-aidlc-requirements.py`
- **Read-only input(s):** `TAILTRAIL-BUNDLED-OFFLINE-AIDLC-PROVISIONING-DESIGN.md`, `scripts/aidlc-official-bridge.py`, `scripts/planning_lock.py`, `scripts/task-start.py`, `tailtrail/aidlc_bundle.py`, `tests/test_aidlc_bundle_resolver.py`
- **Proof path(s):** `tests/test_aidlc_official_bridge.py`
- **Proof intent:** `tests/test_aidlc_official_bridge.py` = `editable-proof` (baseline `not-run`)
- **Success criteria:** A separate read-only existing-run API resolves Requirements rules through the package-owned frozen bundled-v2 binding or bounded legacy-v1 continuation.; Returned rules are regular non-symlink files inside the resolved immutable pack and retain the required official markers.; Selector, cwd, and caller manifest changes cannot affect the new API; existing pre-run stage_contract, stage_request, and host-question behavior remain unchanged.; Focused proof covers success, compatibility, preservation, categorical failure, non-mutation, and zero-network boundaries.; The official Requirements adapter exposes a read-only existing-run contract resolver that accepts a project root and run ID, calls the package-owned frozen binding resolver, and derives every required Requirements rule reference from that validated immutable pack.; The adapter accepts bundled-v2 ready resolution and bounded legacy-v1 read-only resolution as distinct compatibility modes, with legacy fallback attempted only when the bundled binding is categorically missing rather than altered or incompatible.; Every returned rule path remains inside the validated resolved pack, exists as a regular non-symlink file, and contains the required official marker.; Selector changes, process working-directory changes, and caller-provided compatibility manifest values cannot affect this new existing-run resolver.; The existing pre-run stage_contract and public stage_request behavior remain unchanged for Phase 3 to migrate after provisioning and run binding are wired.; Focused proof covers bundled-v2 resolution, selector and cwd independence, categorical failures, bounded legacy continuation, rule inventory and marker validation, non-mutation, zero network access, and preservation of the current public route.
- **Preservation criteria:** The new API does not read current.json, use process cwd or caller manifest authority, contact the network, execute rules, provision state, or mint or rewrite bindings.; Only a categorically missing bundled binding may try bounded legacy continuation; altered or incompatible bundled state never downgrades or falls back.; Public Full/Standard Start and stage_request integration remain excluded until Phase 3 creates the frozen binding before calling the adapter.; No package resolver, bridge, task-start, Planning Lock, MCP, host, schema, registry, CLI, or documentation owner is editable in this slice.; Phase 2B.2 does not wire the new resolver into stage_request, task-start, Planning Lock, MCP, or any host projection and does not change the legacy public route before Phase 3 can create a frozen binding.; The new resolver never reads current.json, resolves relative to process cwd, accepts a caller manifest path, contacts the network, executes pack content, writes project state, provisions a pack, or creates or rewrites a run binding.; Missing, altered, stale, incompatible, conflicting, legacy-unauthorized, or unsafe state fails closed without falling back to another pack; only a categorically missing bundled binding may attempt the package resolver's bounded legacy continuation.; This slice does not edit tailtrail/aidlc_bundle.py, scripts/aidlc-official-bridge.py, scripts/planning_lock.py, scripts/task-start.py, schemas, package registration, CLI dispatch, or documentation.
- **Requirement behaviour scenarios:**
  - `BHV-PHASE2B2-FROZEN-ADAPTER`: Create a verified frozen binding to pack A, change the future-run selector and process working directory, then call the new read-only existing-run Requirements adapter API for that run. → The API returns only required rule references inside frozen pack A; altered or incompatible authority fails without mutation or downgrade, bounded legacy continuation remains read-only, and the existing public stage_request route is unchanged.

| Tier | Command ID | Command | Candidate | State |
|---|---|---|---|---|
| behaviour | `cmd-c02cdb` | `python3 -m unittest tests.test_aidlc_official_bridge` | `tests/test_aidlc_official_bridge.py` | resolved |
| contract | `cmd-c02cdb` | `python3 -m unittest tests.test_aidlc_official_bridge` | `tests/test_aidlc_official_bridge.py` | resolved |
| unit | `cmd-c02cdb` | `python3 -m unittest tests.test_aidlc_official_bridge` | `tests/test_aidlc_official_bridge.py` | resolved |

## Plan

1. **REQ-01:** Implement Add a read-only official Requirements adapter API that resolves rule references from a validated frozen bundled-v2 run binding or bounded legacy-v1 continuation without changing the existing public route before Phase 3. in `scripts/official-aidlc-requirements.py`; verify with `cmd-c02cdb`, `cmd-c02cdb`, `cmd-c02cdb`; inspect `TAILTRAIL-BUNDLED-OFFLINE-AIDLC-PROVISIONING-DESIGN.md`, `scripts/aidlc-official-bridge.py`, `scripts/planning_lock.py`, `scripts/task-start.py`, `tailtrail/aidlc_bundle.py`, `tests/test_aidlc_bundle_resolver.py`; prove against `tests/test_aidlc_official_bridge.py`.
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
| REQ-01 | The existing adapter remains the authoritative boundary. | Changed-symbol/import review and caller-path integration evidence. |

### Scoped evidence

| Path | Role | Planned use | Confidence |
|---|---|---|---|
| `scripts/official-aidlc-requirements.py` | implementation candidate | Primary implementation candidate, subject to post-approval source and caller confirmation. | repository-inventory hypothesis |
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
  - `cmd-c02cdb` covers 1 requirement(s): REQ-01.

## Token Estimate

- **Planned working set:** approximately `1555` tokens (confidence: `medium`).
- **Scoped-file ceiling:** approximately `10438` tokens; estimated reduction `85.1%`.
- **Confidence basis:** at least one bounded slice lacks an exact combined behavior-and-symbol anchor.
- This is an estimate from saved scope, not measured model/provider usage.

## Implementation Boundary

- **Editable scope:** `scripts/official-aidlc-requirements.py`.
- **Writable outputs:** none recorded.
- **Editable validation scope:** `tests/test_aidlc_official_bridge.py`.
- **Run-only proof scope:** none recorded.
- **Read-only / proof-only scope:** `TAILTRAIL-BUNDLED-OFFLINE-AIDLC-PROVISIONING-DESIGN.md`, `scripts/aidlc-official-bridge.py`, `scripts/planning_lock.py`, `scripts/task-start.py`, `tailtrail/aidlc_bundle.py`, `tests/test_aidlc_bundle_resolver.py`, `tests/test_aidlc_official_bridge.py`.
- **Excluded:** every path, command, external system, deployment, and data change not explicitly recorded above remains outside this approval.
- **Data impact:** no data impact is authorized unless a requirement above names it explicitly.

## Approval Checklist

- [x] Requirements are present and reviewable.
- [x] Every requirement has an editable implementation owner.
- [x] Runnable proof commands are registered and mapped to requirements.
- [x] Material questions are resolved.
- [x] Mandatory planning audit is clean for this exact plan revision.
- [ ] The host has reviewed the scope, preservation criteria, proof commands, analyses, and excluded boundary.
- **Risks to review:** data shape; dependency

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

- Machine-readable state remains available at [`.tailtrail/runs/start-20261105075910-50dfb3/planning/canonical-plan-projection-v4.json`](.tailtrail/runs/start-20261105075910-50dfb3/planning/canonical-plan-projection-v4.json); it is not the approval view.

---

*End of Start Plan.*