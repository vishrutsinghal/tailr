# TailTrail Start Plan - Full Review Record

**Presentation version:** `5`
**Plan detail:** `Expert` (automatic for AIDLC Lite)

## Planning Lock

- **Run ID:** `start-20261105073143-35fb0b`
- **Status:** `approved`
- **Goal:** Implement Phase 2B.2 official AIDLC Requirements adapter integration in scripts/official-aidlc-requirements.py using the current dirty worktree as the shared baseline: for an existing Standard or Full run, resolve governing Requirements rules only from the validated frozen active-run binding supplied by tailtrail/aidlc_bundle.py; never use current.json, the current working directory, relative rediscovery, or a caller-provided compatibility_manifest as active-run authority; allow only bounded read-only legacy-v1 continuation backed by the saved bridge and activation artifacts; preserve the separately labeled pre-run authority inspection path until Phase 3 replaces its public routing; fail closed without mutation on missing, altered, stale, incompatible, conflicting, legacy-unauthorized, or unsafe state; preserve host question validation and Requirements-stage behavior; prove the public stage_request and stage-contract paths with python3 -m unittest tests.test_aidlc_official_bridge; exclude Full Start and Planning Lock wiring, MCP routing, host projections, schemas, package registration, CLI dispatcher changes, and documentation.
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

**Description:** Bind the official AIDLC Requirements adapter for an existing Standard or Full run to the validated frozen active-run pack resolution while preserving bounded legacy continuation and the separately labeled pre-run inspection boundary.

- **Requirement type:** `change`
- **Validation state:** `required`
- **Editable owner(s):** `scripts/official-aidlc-requirements.py`
- **Read-only input(s):** `TAILTRAIL-BUNDLED-OFFLINE-AIDLC-PROVISIONING-DESIGN.md`, `scripts/aidlc-official-bridge.py`, `scripts/planning_lock.py`, `scripts/task-start.py`, `tailtrail/aidlc_bundle.py`, `tests/test_aidlc_bundle_resolver.py`
- **Proof path(s):** `tests/test_aidlc_official_bridge.py`
- **Proof intent:** `tests/test_aidlc_official_bridge.py` = `editable-proof` (baseline `not-run`)
- **Success criteria:** Existing-run stage_request and its stage-contract path resolve every governing Requirements rule from the validated frozen bundled-v2 binding for the saved bridge run ID.; Selector, cwd, and caller manifest changes cannot retarget existing-run authority; bounded legacy-v1 continuation remains saved-artifact-backed and read-only.; The separately labeled pre-run inspection behavior and host-question validation remain compatible until Phase 3 changes public routing.; Focused public-path proof covers success, preservation, categorical failure, non-mutation, and zero-network boundaries.; For an existing Standard or Full run, the official Requirements stage resolves governing rule files only through the validated frozen active-run resolution returned by tailtrail/aidlc_bundle.py for the saved bridge run ID.; The adapter derives the rule root from the validated bound resolution, checks the complete required Requirements rule set and markers, and exposes references that remain inside the resolved immutable pack.; Changing current.json or the process working directory after binding does not retarget an existing run, and a caller-provided compatibility_manifest cannot override active-run authority.; Bounded legacy schema-v1 continuation is accepted only through the saved bridge and activation authority validated by the package resolver, remains explicitly read-only, and cannot create a bundled-v2 binding or authorize a new Full run.; The existing pre-run Requirements authority inspection remains separately labeled compatibility behavior until Phase 3 replaces its public routing; it cannot be used as existing-run authority.; Focused public-path proof covers stage_request and stage-contract resolution, selector and working-directory independence, altered or missing bound state, unsafe paths, bounded legacy continuation, preservation of host-question validation, and zero network or filesystem mutation.
- **Preservation criteria:** No existing-run operation reads current.json, performs cwd rediscovery, accepts a caller manifest override, contacts the network, executes pack content, changes bundle or project files, or mints or rewrites a binding.; Missing, altered, stale, incompatible, conflicting, legacy-unauthorized, or unsafe state fails closed without selecting another pack.; This slice does not edit the package resolver, Full Start, Planning Lock, MCP, host projection, schema, registry, dispatcher, or documentation owners.; Phase 2B.2 never reads current.json for an existing run, performs current-working-directory rediscovery, trusts a caller-provided compatibility_manifest as active-run authority, contacts the network, executes pack content, changes pack bytes, creates a projection, or mints or rewrites a run binding.; Missing, altered, stale, incompatible, conflicting, legacy-unauthorized, or unsafe state fails closed with a categorical actionable error and does not fall back to another pack.; This slice does not edit tailtrail/aidlc_bundle.py, Full Start or Planning Lock wiring, MCP routing, host projections, schemas, package registration, CLI dispatch, or documentation.
- **Requirement behaviour scenarios:**
  - `BHV-PHASE2B2-FROZEN-REQUIREMENTS`: Bind an existing Standard or Full run to verified pack A, change the future-run selector and process working directory, and request its official Requirements stage through stage_request. → The adapter returns only the required rule references under the validated frozen pack A; caller manifest changes cannot retarget the run, invalid bound state fails without mutation or fallback, and bounded legacy continuation remains read-only.

| Tier | Command ID | Command | Candidate | State |
|---|---|---|---|---|
| behaviour | `cmd-c02cdb` | `python3 -m unittest tests.test_aidlc_official_bridge` | `tests/test_aidlc_official_bridge.py` | resolved |
| contract | `cmd-c02cdb` | `python3 -m unittest tests.test_aidlc_official_bridge` | `tests/test_aidlc_official_bridge.py` | resolved |
| unit | `cmd-c02cdb` | `python3 -m unittest tests.test_aidlc_official_bridge` | `tests/test_aidlc_official_bridge.py` | resolved |

## Plan

1. **REQ-01:** Implement Bind the official AIDLC Requirements adapter for an existing Standard or Full run to the validated frozen active-run pack resolution while preserving bounded legacy continuation and the separately labeled pre-run inspection boundary. in `scripts/official-aidlc-requirements.py`; verify with `cmd-c02cdb`, `cmd-c02cdb`, `cmd-c02cdb`; inspect `TAILTRAIL-BUNDLED-OFFLINE-AIDLC-PROVISIONING-DESIGN.md`, `scripts/aidlc-official-bridge.py`, `scripts/planning_lock.py`, `scripts/task-start.py`, `tailtrail/aidlc_bundle.py`, `tests/test_aidlc_bundle_resolver.py`; prove against `tests/test_aidlc_official_bridge.py`.
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

- Machine-readable state remains available at [`.tailtrail/runs/start-20261105073143-35fb0b/planning/canonical-plan-projection-v4.json`](.tailtrail/runs/start-20261105073143-35fb0b/planning/canonical-plan-projection-v4.json); it is not the approval view.

---

*End of Start Plan.*