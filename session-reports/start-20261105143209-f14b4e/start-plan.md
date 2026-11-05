# TailTrail Start Plan - Full Review Record

**Presentation version:** `5`
**Plan detail:** `Full` (automatic for Standard/Full, hands-free, or Intent Bridge authority)

## Planning Lock

- **Run ID:** `start-20261105143209-f14b4e`
- **Status:** `awaiting-approval`
- **Goal:** Implement Phase 5A distribution and end-to-end proof for bundled offline Full AIDLC by extending the package release proof to verify source checkout, built wheel, and sdist-to-wheel offline Full public routes, CLI and MCP identity parity, three-host identity agreement, deterministic negative integrity mutations, concurrency and interruption preservation, and built-artifact bundle integrity while preserving existing release trust and fail-closed behavior.
- **Request mode:** `implementation`
- **Managed writes allowed:** `false`
- **Execution status:** planning only; no source change, proof command, scanner, or Git operation has run.
- **Plan revision:** active `1`; pending `2`.

## Bound Planning Inputs

- No read-only planning inputs were bound to this plan.

## Command Reference Registry

| ID | Kind | Command |
|---|---|---|
| `cmd-a2a72e` | proof | `python3 -m unittest tests.test_self_contained_package -v` |

## Validation Requirements And Focused Validation Matrix

### REQ-01

**Description:** Implement a built-artifact distribution proof that verifies source checkout, direct wheel, and sdist-to-wheel offline Full public routes, matching CLI, MCP, resolver, and three-host identities, closed package and bundle inventories, deterministic negative integrity mutations, and interruption and concurrency preservation without network access or silent Full-to-Lite downgrade.

- **Requirement type:** `change`
- **Validation state:** `required`
- **Editable owner(s):** `scripts/package-release-proof.py`
- **Read-only input(s):** `MANIFEST.in`, `TAILTRAIL-BUNDLED-OFFLINE-AIDLC-PROVISIONING-DESIGN.md`, `aidlc-rules/manifest.json`, `package-manifest.json`, `scripts/aidlc-official-bridge.py`, `scripts/aidlc-official-host.py`, `scripts/mcp-server.py`, `scripts/task-start.py`, `tailtrail/aidlc_bundle.py`
- **Proof path(s):** `tests/test_self_contained_package.py`
- **Proof intent:** `tests/test_self_contained_package.py` = `editable-proof` (baseline `not-run`)
- **Success criteria:** Built wheel and source-distribution artifacts are inspected for the exact bundled AIDLC inventory, bundle manifest, license, provenance, package-integrity coverage, runtime-required modules, and deterministic hashes.; An isolated wheel install and an sdist-to-wheel install run the public explicit Full route without network access or a separately installed project pack, remain Full, and expose matching package, bundle, project, and run-resolution fingerprints.; The public CLI and MCP Full routes consume the same resolver identity, and Codex, Copilot, and Claude projections agree on that frozen official identity.; A deterministic mutation table covers missing, additional, altered, stale, incompatible, unsafe, interrupted, and conflicting state while focused integration cases cover real bundle, concurrency, and atomic recovery preservation.
- **Preservation criteria:** No proof path may download rules, silently downgrade Full to Lite, fabricate authenticated-release trust, overwrite altered state, or treat local hashes as publisher authentication.; All build, install, mutation, concurrency, and project state is isolated to temporary directories; prior valid state remains readable after injected failures.; This Phase 5A approval does not authorize runtime resolver, bridge, Start, MCP, host projection, bundle content, manifest, release workflow, or user documentation edits.; Release documentation alignment and Windows/POSIX CI-runner expansion remain explicit dependent Phase 5B work after the executable distribution proof is complete.
- **Requirement behaviour scenarios:**
  - `BHV-REQ-01-OFFLINE-FULL-DISTRIBUTION`: Build the wheel and source distribution, install each without an index into isolated environments, invoke the public explicit Full route through CLI and MCP against a new project, exercise all three host projections, then apply the approved integrity, interruption, and concurrency mutations. → Every intact source or built-artifact route remains Full without network access and reports matching immutable identities; every missing, altered, stale, incompatible, unsafe, interrupted, conflicting, or concurrent negative state blocks before authority without overwriting prior valid state or silently downgrading to Lite.

| Tier | Command ID | Command | Candidate | State |
|---|---|---|---|---|
| behaviour | `cmd-a2a72e` | `python3 -m unittest tests.test_self_contained_package -v` | `tests/test_self_contained_package.py` | resolved |
| contract | `cmd-a2a72e` | `python3 -m unittest tests.test_self_contained_package -v` | `tests/test_self_contained_package.py` | resolved |
| integration | `cmd-a2a72e` | `python3 -m unittest tests.test_self_contained_package -v` | `tests/test_self_contained_package.py` | resolved |

## Plan

1. **REQ-01:** Implement Implement a built-artifact distribution proof that verifies source checkout, direct wheel, and sdist-to-wheel offline Full public routes, matching CLI, MCP, resolver, and three-host identities, closed package and bundle inventories, deterministic negative integrity mutations, and interruption and concurrency preservation without network access or silent Full-to-Lite downgrade. in `scripts/package-release-proof.py`; verify with `cmd-a2a72e`, `cmd-a2a72e`, `cmd-a2a72e`; inspect `MANIFEST.in`, `TAILTRAIL-BUNDLED-OFFLINE-AIDLC-PROVISIONING-DESIGN.md`, `aidlc-rules/manifest.json`, `package-manifest.json`, `scripts/aidlc-official-bridge.py`, `scripts/aidlc-official-host.py`, `scripts/mcp-server.py`, `scripts/task-start.py`, `tailtrail/aidlc_bundle.py`; prove against `tests/test_self_contained_package.py`.
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
| `scripts/package-release-proof.py` | implementation candidate | Primary implementation candidate, subject to post-approval source and caller confirmation. | repository-inventory hypothesis |
| `tests/test_self_contained_package.py` | test evidence | Run only when its tier proves an approved requirement. | repository-inventory hypothesis |

### Post-change checks

1. Confirm the authoritative boundary and material callers before the first edit.
2. Compare actual changed files and symbols with the approved impact map; justify or correct every unexpected path.
3. Detect missed callers, caller-specific business logic, wrong-layer placement, and public-contract drift.
4. Check dependency manifests and imports when the approved contract forbids a new dependency.
5. Run every requirement-linked validation tier and preserve unresolved evidence as a gap, not a pass.

## Behaviour Analysis

- **Status:** `planning-hypothesis`.
- **Evidence boundary:** Derived from explicit user wording and repository path inventory only. Actual states, transitions, side effects, responses, and edit necessity remain unconfirmed until after approval.

| Requirement | Scenario | Observable result | Required proof |
|---|---|---|---|
| REQ-01 | Build the wheel and source distribution, install each without an index into isolated environments, invoke the public explicit Full route through CLI and MCP against a new project, exercise all three host projections, then apply the approved integrity, interruption, and concurrency mutations. | Every intact source or built-artifact route remains Full without network access and reports matching immutable identities; every missing, altered, stale, incompatible, unsafe, interrupted, conflicting, or concurrent negative state blocks before authority without overwriting prior valid state or silently downgrading to Lite. | behaviour |

### Scoped evidence

| Path | Role | Planned use | Confidence |
|---|---|---|---|
| `scripts/package-release-proof.py` | supporting candidate | Inspect after approval; edit only when the confirmed behaviour path requires it. | repository-inventory hypothesis |
| `tests/test_self_contained_package.py` | supporting candidate | Inspect after approval; edit only when the confirmed behaviour path requires it. | repository-inventory hypothesis |

### Post-change checks

1. Confirm the actor, starting state, authoritative state owner, and observable interface before the first edit.
2. Map each actual transition and side effect to an approved behaviour scenario and requirement ID.
3. Reconcile actual changed paths with the approved behaviour roles; justify or correct unexpected scope.
4. Require matching behaviour and integration receipts; unit evidence alone cannot complete the Behaviour Harness.
5. Report unresolved scenarios as evidence-incomplete or drifted, never as a generic pass.

## Focused Validation Coverage Summary

- **Requirements covered:** 1/1.
- **Proof command reuse:**
  - `cmd-a2a72e` covers 1 requirement(s): REQ-01.

## Token Estimate

- **Planned working set:** approximately `1194` tokens (confidence: `medium`).
- **Scoped-file ceiling:** approximately `6533` tokens; estimated reduction `81.72%`.
- **Confidence basis:** at least one bounded slice lacks an exact combined behavior-and-symbol anchor.
- This is an estimate from saved scope, not measured model/provider usage.

## Implementation Boundary

- **Editable scope:** `scripts/package-release-proof.py`.
- **Writable outputs:** none recorded.
- **Editable validation scope:** `tests/test_self_contained_package.py`.
- **Run-only proof scope:** none recorded.
- **Read-only / proof-only scope:** `MANIFEST.in`, `TAILTRAIL-BUNDLED-OFFLINE-AIDLC-PROVISIONING-DESIGN.md`, `aidlc-rules/manifest.json`, `package-manifest.json`, `scripts/aidlc-official-bridge.py`, `scripts/aidlc-official-host.py`, `scripts/mcp-server.py`, `scripts/task-start.py`, `tailtrail/aidlc_bundle.py`, `tests/test_self_contained_package.py`.
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

- **Total review cycles:** 2
- **Revision cycles:** 1
- **Latest audit:** `clean`; 0 finding(s).

## Approval Decision

**READY FOR APPROVAL** — review this plan, then explicitly approve this exact run. Approval is separate from activation and permits no unlisted work.

## Canonical Machine Record

- Machine-readable state remains available at [`.tailtrail/runs/start-20261105143209-f14b4e/planning/canonical-plan-projection-v3.json`](.tailtrail/runs/start-20261105143209-f14b4e/planning/canonical-plan-projection-v3.json); it is not the approval view.

---

*End of Start Plan.*