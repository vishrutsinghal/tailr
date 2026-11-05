# TailTrail Start Plan - Full Review Record

**Presentation version:** `5`
**Plan detail:** `Expert` (automatic for AIDLC Lite)

## Planning Lock

- **Run ID:** `start-20261105133305-08d3b7`
- **Status:** `approved`
- **Goal:** Implement Phase 4A of the bundled offline AIDLC Host Projections design using the current dirty worktree as the shared baseline: define and register the immutable host-projection receipt contract before the host engine depends on it, while preserving the Phase 4 engine and Phase 5 public distribution work for separate later owners.
- **Request mode:** `implementation`
- **Managed writes allowed:** `true`
- **Execution status:** planning only; no source change, proof command, scanner, or Git operation has run.
- **Plan revision:** active `3`; pending `none`.

## Bound Planning Inputs

- No read-only planning inputs were bound to this plan.

## Command Reference Registry

| ID | Kind | Command |
|---|---|---|
| `cmd-ba7aa2` | proof | `python3 -m unittest tests.test_tailtrail_registry -v` |

## Validation Requirements And Focused Validation Matrix

### REQ-01

**Description:** Define and register the immutable Phase 4 host-projection receipt contract before the host engine depends on it, including host identity, adapter and projection mode, frozen origin fingerprints, official and trust identity, complete source-to-destination mapping and hashes, instruction-block fingerprint, reload posture, qualification result, and receipt seal.

- **Requirement type:** `change`
- **Validation state:** `required`
- **Editable owner(s):** `schemas/official-aidlc-host-projection-receipt.schema.json`
- **Read-only input(s):** `TAILTRAIL-BUNDLED-OFFLINE-AIDLC-PROVISIONING-DESIGN.md`, `schemas/official-aidlc-run-state.schema.json`
- **Writable output(s):** `tailtrail-registry.json` (`configuration-output`, existing)
- **Proof path(s):** `tests/test_tailtrail_registry.py`
- **Proof intent:** `tests/test_tailtrail_registry.py` = `editable-proof` (baseline `pass`)
- **Success criteria:** A separate registered schema owns the complete immutable host-projection receipt contract before the host engine depends on it.; The receipt records host and adapter identity, fixed projection mode, frozen origin run-resolution and project-pack fingerprints, official and trust identity, complete source-to-destination mapping and hashes, instruction-block fingerprint, reload posture, qualification result, and receipt seal.; tailtrail-registry.json registers the new contract and focused registry proof validates both schema ownership and strict discoverability.
- **Preservation criteria:** Do not overload the existing run-state or bridge schema with host-projection state.; Do not implement the host projection engine, alter host instruction files, wire public Start or MCP routes, or claim Phase 5 distribution and end-to-end proof.; Do not permit the receipt to omit complete mapping and hashes, instruction identity, reload posture, qualification, or its own fingerprint.

| Tier | Command ID | Command | Candidate | State |
|---|---|---|---|---|
| contract | `cmd-ba7aa2` | `python3 -m unittest tests.test_tailtrail_registry -v` | `tests/test_tailtrail_registry.py` | resolved |
| unit | `cmd-ba7aa2` | `python3 -m unittest tests.test_tailtrail_registry -v` | `tests/test_tailtrail_registry.py` | resolved |

## Plan

1. **REQ-01:** Implement Define and register the immutable Phase 4 host-projection receipt contract before the host engine depends on it, including host identity, adapter and projection mode, frozen origin fingerprints, official and trust identity, complete source-to-destination mapping and hashes, instruction-block fingerprint, reload posture, qualification result, and receipt seal. in `schemas/official-aidlc-host-projection-receipt.schema.json`; verify with `cmd-ba7aa2`, `cmd-ba7aa2`; inspect `TAILTRAIL-BUNDLED-OFFLINE-AIDLC-PROVISIONING-DESIGN.md`, `schemas/official-aidlc-run-state.schema.json`; prove against `tests/test_tailtrail_registry.py`; produce `tailtrail-registry.json` as `configuration-output`.
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
| `scripts/adoption-validation.py` | validation boundary | Primary implementation candidate, subject to post-approval source and caller confirmation. | repository-inventory hypothesis |
| `scripts/advanced-runtime.py` | implementation candidate | Primary implementation candidate, subject to post-approval source and caller confirmation. | repository-inventory hypothesis |
| `scripts/aidlc-official-bridge.py` | implementation candidate | Primary implementation candidate, subject to post-approval source and caller confirmation. | repository-inventory hypothesis |
| `scripts/aidlc-official-detect.py` | implementation candidate | Primary implementation candidate, subject to post-approval source and caller confirmation. | repository-inventory hypothesis |
| `scripts/aidlc-official-host.py` | implementation candidate | Primary implementation candidate, subject to post-approval source and caller confirmation. | repository-inventory hypothesis |
| `scripts/change-intent-anchor.py` | implementation candidate | Primary implementation candidate, subject to post-approval source and caller confirmation. | repository-inventory hypothesis |
| `scripts/check-tailtrail.py` | implementation candidate | Inspect after approval; edit only if the confirmed architecture contract requires it. | repository-inventory hypothesis |
| `scripts/closure-contract.py` | implementation candidate | Primary implementation candidate, subject to post-approval source and caller confirmation. | repository-inventory hypothesis |
| `scripts/context-receipt.py` | implementation candidate | Primary implementation candidate, subject to post-approval source and caller confirmation. | repository-inventory hypothesis |
| `scripts/context_receipt.py` | implementation candidate | Primary implementation candidate, subject to post-approval source and caller confirmation. | repository-inventory hypothesis |
| `scripts/debug-host-diagnosis.py` | implementation candidate | Primary implementation candidate, subject to post-approval source and caller confirmation. | repository-inventory hypothesis |
| `scripts/evidence-tiers.py` | implementation candidate | Primary implementation candidate, subject to post-approval source and caller confirmation. | repository-inventory hypothesis |
| `scripts/host-adapter-conformance.py` | domain/integration boundary | Primary implementation candidate, subject to post-approval source and caller confirmation. | repository-inventory hypothesis |
| `scripts/host-decision.py` | implementation candidate | Primary implementation candidate, subject to post-approval source and caller confirmation. | repository-inventory hypothesis |
| `scripts/host-interpretation-builder.py` | implementation candidate | Primary implementation candidate, subject to post-approval source and caller confirmation. | repository-inventory hypothesis |
| `scripts/host-reply-validate.py` | implementation candidate | Primary implementation candidate, subject to post-approval source and caller confirmation. | repository-inventory hypothesis |
| `scripts/host-runtime-conformance.py` | implementation candidate | Inspect after approval; edit only if the confirmed architecture contract requires it. | repository-inventory hypothesis |
| `scripts/host-workspace-adapter.py` | domain/integration boundary | Primary implementation candidate, subject to post-approval source and caller confirmation. | repository-inventory hypothesis |
| `scripts/host_contract.py` | implementation candidate | Inspect after approval; edit only if the confirmed architecture contract requires it. | repository-inventory hypothesis |
| `scripts/install-copilot.py` | implementation candidate | Inspect after approval; edit only if the confirmed architecture contract requires it. | repository-inventory hypothesis |
| `scripts/learning-use-receipt.py` | implementation candidate | Primary implementation candidate, subject to post-approval source and caller confirmation. | repository-inventory hypothesis |
| `scripts/learning-v3.py` | implementation candidate | Primary implementation candidate, subject to post-approval source and caller confirmation. | repository-inventory hypothesis |
| `scripts/phase8-advanced.py` | implementation candidate | Primary implementation candidate, subject to post-approval source and caller confirmation. | repository-inventory hypothesis |
| `scripts/planning_lock.py` | implementation candidate | Primary implementation candidate, subject to post-approval source and caller confirmation. | repository-inventory hypothesis |
| `scripts/run-ledger.py` | implementation candidate | Primary implementation candidate, subject to post-approval source and caller confirmation. | repository-inventory hypothesis |
| `scripts/validation-receipt.py` | validation boundary | Primary implementation candidate, subject to post-approval source and caller confirmation. | repository-inventory hypothesis |
| `tests/test_aidlc_official_host.py` | test evidence | Run only when its tier proves an approved requirement. | repository-inventory hypothesis |
| `tests/test_closure_contract.py` | test evidence | Run only when its tier proves an approved requirement. | repository-inventory hypothesis |
| `tests/test_host_adapter_conformance.py` | test evidence | Run only when its tier proves an approved requirement. | repository-inventory hypothesis |
| `tests/test_host_contract.py` | test evidence | Run only when its tier proves an approved requirement. | repository-inventory hypothesis |
| `tests/test_self_contained_package.py` | test evidence | Run only when its tier proves an approved requirement. | repository-inventory hypothesis |

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
  - `cmd-ba7aa2` covers 1 requirement(s): REQ-01.

## Token Estimate

- Unavailable: scope is `ambiguous`, so a token estimate would not be reliable.
- This is an estimate from saved scope, not measured model/provider usage.

## Implementation Boundary

- **Editable scope:** `schemas/official-aidlc-host-projection-receipt.schema.json`.
- **Writable outputs:** `tailtrail-registry.json` (`configuration-output`).
- **Editable validation scope:** `tests/test_tailtrail_registry.py`.
- **Run-only proof scope:** none recorded.
- **Read-only / proof-only scope:** `TAILTRAIL-BUNDLED-OFFLINE-AIDLC-PROVISIONING-DESIGN.md`, `schemas/official-aidlc-run-state.schema.json`, `tests/test_tailtrail_registry.py`.
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

- **Total review cycles:** 3
- **Revision cycles:** 2
- **Latest audit:** `clean`; 0 finding(s).

## Approval Decision

**READY FOR APPROVAL** — review this plan, then explicitly approve this exact run. Approval is separate from activation and permits no unlisted work.

## Canonical Machine Record

- Machine-readable state remains available at [`.tailtrail/runs/start-20261105133305-08d3b7/planning/canonical-plan-projection-v7.json`](.tailtrail/runs/start-20261105133305-08d3b7/planning/canonical-plan-projection-v7.json); it is not the approval view.

---

*End of Start Plan.*