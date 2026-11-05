# TailTrail Start Plan - Full Review Record

**Presentation version:** `5`
**Plan detail:** `Full` (automatic for Standard/Full, hands-free, or Intent Bridge authority)

## Planning Lock

- **Run ID:** `start-20261105114609-1219b6`
- **Status:** `awaiting-approval`
- **Goal:** Implement the complete Phase 4 Host Projections outcome from TAILTRAIL-BUNDLED-OFFLINE-AIDLC-PROVISIONING-DESIGN.md using the current dirty worktree as the shared baseline: coordinate separate requirement-scoped owners for the three-host projection engine and host-projection receipt schema, register the contract, enforce frozen bundled-v2 identity, fixed copy/reference modes, atomic safe projection, complete read-only conformance, idempotence, and Codex/Copilot/Claude agreement, while preserving Phase 5 public distribution and end-to-end proof for later.
- **Request mode:** `implementation`
- **Managed writes allowed:** `false`
- **Execution status:** planning only; no source change, proof command, scanner, or Git operation has run.
- **Plan revision:** active `1`; pending `2`.

## Bound Planning Inputs

- No read-only planning inputs were bound to this plan.

## Command Reference Registry

| ID | Kind | Command |
|---|---|---|
| `cmd-2e6ef7` | proof | `python3 -m unittest tests.test_aidlc_official_host tests.test_tailtrail_registry -v` |

## Validation Requirements And Focused Validation Matrix

### REQ-01

**Description:** Define and register the immutable Phase 4 host-projection receipt contract before the host engine emits it, including host identity, adapter and projection mode, frozen origin fingerprints, official and trust identity, complete source-to-destination mapping and hashes, instruction-block fingerprint, reload posture, qualification result, and receipt seal.

- **Requirement type:** `change`
- **Validation state:** `required`
- **Editable owner(s):** `schemas/official-aidlc-host-projection-receipt.schema.json`
- **Read-only input(s):** `TAILTRAIL-BUNDLED-OFFLINE-AIDLC-PROVISIONING-DESIGN.md`, `schemas/official-aidlc-run-state.schema.json`, `scripts/aidlc-official-bridge.py`, `scripts/install-copilot.py`, `scripts/install-local.py`, `tailtrail/aidlc_bundle.py`
- **Writable output(s):** `tailtrail-registry.json` (`configuration-output`, existing)
- **Proof path(s):** `tests/test_aidlc_official_host.py`, `tests/test_tailtrail_registry.py`
- **Proof intent:** `tests/test_aidlc_official_host.py` = `editable-proof` (baseline `pass`); `tests/test_tailtrail_registry.py` = `unchanged-proof` (baseline `pass`)
- **Success criteria:** A separate registered schema owns the complete immutable host-projection receipt contract before engine implementation depends on it.; The schema distinguishes frozen run and project-pack authority from host-specific mode, mapping, instruction, reload, qualification, and receipt identity.; Registry validation exposes the contract and truthfully distinguishes write-capable installation from read-only status.
- **Preservation criteria:** The existing run-state or bridge schema is not overloaded with host-projection state.; The receipt cannot omit complete mapping and hashes, instruction identity, reload posture, qualification, or its own fingerprint.; Schema and registry work does not claim or modify Phase 5 public distribution and end-to-end proof.

| Tier | Command ID | Command | Candidate | State |
|---|---|---|---|---|
| contract | `cmd-2e6ef7` | `python3 -m unittest tests.test_aidlc_official_host tests.test_tailtrail_registry -v` | `tests/test_aidlc_official_host.py` | resolved |
| unit | `cmd-2e6ef7` | `python3 -m unittest tests.test_aidlc_official_host tests.test_tailtrail_registry -v` | `tests/test_tailtrail_registry.py` | resolved |

### REQ-02

**Description:** Implement one three-host projection engine that consumes the exact frozen bundled-v2 run binding, applies fixed Codex copy and Copilot/Claude reference modes, publishes safe atomic projections and immutable receipts, performs complete read-only conformance, preserves idempotence, fails closed on conflicting or unsafe state, and proves all hosts agree on one official and project-pack identity without network or mutable rediscovery; the engine depends on REQ-PHASE4-RECEIPT-CONTRACT being available first.

- **Requirement type:** `change`
- **Validation state:** `required`
- **Editable owner(s):** `scripts/aidlc-official-host.py`
- **Read-only input(s):** `TAILTRAIL-BUNDLED-OFFLINE-AIDLC-PROVISIONING-DESIGN.md`, `schemas/official-aidlc-run-state.schema.json`, `scripts/aidlc-official-bridge.py`, `scripts/install-copilot.py`, `scripts/install-local.py`, `tailtrail/aidlc_bundle.py`
- **Proof path(s):** `tests/test_aidlc_official_host.py`
- **Proof intent:** `tests/test_aidlc_official_host.py` = `editable-proof` (baseline `pass`)
- **Success criteria:** The engine runs only after the registered receipt contract is available and consumes exactly one frozen bundled-v2 run binding.; Codex copy mode and Copilot/Claude reference mode publish bounded atomic projections and immutable receipts while preserving unmanaged instructions.; Read-only status recomputes the complete receipt, instruction, mapping, and inventory evidence; all hosts agree on one official and project-pack identity; identical retries are idempotent.
- **Preservation criteria:** No host downloads, substitutes, rediscovers mutable selector state, accepts legacy authority, or silently changes projection mode.; Unsafe ancestors, unmanaged conflicts, altered receipts, incomplete inventories, symlinks, non-regular entries, stale identity, and different frozen authority fail closed without overwrite.; Repository AGENTS.md, Copilot and Claude instruction files, public Start/MCP wiring, Planning Lock, installers, bundle resolver, bridge, and Phase 5 distribution remain unmodified.
- **Requirement behaviour scenarios:**
  - `BHV-REQ-02-THREE-HOST-CONFORMANCE`: Install the same frozen bundled-v2 run binding into temporary Codex, Copilot, and Claude targets, rerun identical installs, then alter each copied or referenced projection using the approved negative-case fixtures before invoking read-only status. → All three receipts retain the same official and project-pack identity; Codex copy and Copilot/Claude reference modes are idempotent; status detects missing, additional, altered, symlinked, non-regular, unsafe, stale, legacy, and conflicting state without mutation or network access.

| Tier | Command ID | Command | Candidate | State |
|---|---|---|---|---|
| behaviour | `cmd-2e6ef7` | `python3 -m unittest tests.test_aidlc_official_host tests.test_tailtrail_registry -v` | `tests/test_aidlc_official_host.py` | resolved |
| contract | `cmd-2e6ef7` | `python3 -m unittest tests.test_aidlc_official_host tests.test_tailtrail_registry -v` | `tests/test_aidlc_official_host.py` | resolved |
| unit | `cmd-2e6ef7` | `python3 -m unittest tests.test_aidlc_official_host tests.test_tailtrail_registry -v` | `tests/test_aidlc_official_host.py` | resolved |

## Plan

1. **REQ-01:** Implement Define and register the immutable Phase 4 host-projection receipt contract before the host engine emits it, including host identity, adapter and projection mode, frozen origin fingerprints, official and trust identity, complete source-to-destination mapping and hashes, instruction-block fingerprint, reload posture, qualification result, and receipt seal. in `schemas/official-aidlc-host-projection-receipt.schema.json`; verify with `cmd-2e6ef7`, `cmd-2e6ef7`; inspect `TAILTRAIL-BUNDLED-OFFLINE-AIDLC-PROVISIONING-DESIGN.md`, `schemas/official-aidlc-run-state.schema.json`, `scripts/aidlc-official-bridge.py`, `scripts/install-copilot.py`, `scripts/install-local.py`, `tailtrail/aidlc_bundle.py`; prove against `tests/test_aidlc_official_host.py`, `tests/test_tailtrail_registry.py`; produce `tailtrail-registry.json` as `configuration-output`.
2. **REQ-02:** Implement Implement one three-host projection engine that consumes the exact frozen bundled-v2 run binding, applies fixed Codex copy and Copilot/Claude reference modes, publishes safe atomic projections and immutable receipts, performs complete read-only conformance, preserves idempotence, fails closed on conflicting or unsafe state, and proves all hosts agree on one official and project-pack identity without network or mutable rediscovery; the engine depends on REQ-PHASE4-RECEIPT-CONTRACT being available first. in `scripts/aidlc-official-host.py`; verify with `cmd-2e6ef7`, `cmd-2e6ef7`, `cmd-2e6ef7`; inspect `TAILTRAIL-BUNDLED-OFFLINE-AIDLC-PROVISIONING-DESIGN.md`, `schemas/official-aidlc-run-state.schema.json`, `scripts/aidlc-official-bridge.py`, `scripts/install-copilot.py`, `scripts/install-local.py`, `tailtrail/aidlc_bundle.py`; prove against `tests/test_aidlc_official_host.py`.
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
| REQ-01 | Behaviour outside the approved change boundary remains compatible. | Existing preservation-path evidence plus focused regression proof. |

### Scoped evidence

| Path | Role | Planned use | Confidence |
|---|---|---|---|
| `scripts/aidlc-official-host.py` | implementation candidate | Primary implementation candidate, subject to post-approval source and caller confirmation. | repository-inventory hypothesis |
| `tests/test_aidlc_official_host.py` | test evidence | Run only when its tier proves an approved requirement. | repository-inventory hypothesis |

### Post-change checks

1. Confirm the authoritative boundary and material callers before the first edit.
2. Compare actual changed files and symbols with the approved impact map; justify or correct every unexpected path.
3. Detect missed callers, caller-specific business logic, wrong-layer placement, and public-contract drift.
4. Check dependency manifests and imports when the approved contract forbids a new dependency.
5. Run every requirement-linked validation tier and preserve unresolved evidence as a gap, not a pass.

## Behaviour Analysis

- **Status:** `not selected`. This control is not part of the approved proof boundary for this plan.

## Focused Validation Coverage Summary

- **Requirements covered:** 2/2.
- **Proof command reuse:**
  - `cmd-2e6ef7` covers 2 requirement(s): REQ-01, REQ-02.

## Token Estimate

- **Planned working set:** approximately `470` tokens (confidence: `medium`).
- **Scoped-file ceiling:** approximately `2900` tokens; estimated reduction `83.79%`.
- **Confidence basis:** at least one bounded slice lacks an exact combined behavior-and-symbol anchor.
- This is an estimate from saved scope, not measured model/provider usage.

## Implementation Boundary

- **Editable scope:** `schemas/official-aidlc-host-projection-receipt.schema.json`, `scripts/aidlc-official-host.py`.
- **Writable outputs:** `tailtrail-registry.json` (`configuration-output`).
- **Editable validation scope:** `tests/test_aidlc_official_host.py`.
- **Run-only proof scope:** `tests/test_tailtrail_registry.py`.
- **Read-only / proof-only scope:** `TAILTRAIL-BUNDLED-OFFLINE-AIDLC-PROVISIONING-DESIGN.md`, `schemas/official-aidlc-run-state.schema.json`, `scripts/aidlc-official-bridge.py`, `scripts/install-copilot.py`, `scripts/install-local.py`, `tailtrail/aidlc_bundle.py`, `tests/test_aidlc_official_host.py`, `tests/test_tailtrail_registry.py`.
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

- Machine-readable state remains available at [`.tailtrail/runs/start-20261105114609-1219b6/planning/canonical-plan-projection-v3.json`](.tailtrail/runs/start-20261105114609-1219b6/planning/canonical-plan-projection-v3.json); it is not the approval view.

---

*End of Start Plan.*