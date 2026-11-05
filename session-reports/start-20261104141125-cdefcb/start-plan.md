# TailTrail Start Plan - Full Review Record

**Presentation version:** `5`
**Plan detail:** `Expert` (automatic for AIDLC Lite)

## Planning Lock

- **Run ID:** `start-20261104141125-cdefcb`
- **Status:** `approved`
- **Goal:** Implement Phase 2A.1 — Package-owned AIDLC bundle resolver from TAILTRAIL-BUNDLED-OFFLINE-AIDLC-PROVISIONING-DESIGN.md: add one typed shared resolver that discovers installed-package, managed-payload, and source-checkout bundles independently of the current working directory, applies deterministic precedence, validates outer and inner integrity offline, reports truthful trust posture and artifact-identity status, and fails closed without mutation; exclude edits to generic resources, detector, installer, qualification, project projection, current.json, frozen run bindings, Full Start routing, and host adapters.
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

**Description:** Add one package-owned official AIDLC bundle resolver that discovers installed-package, managed-payload, and source-checkout bundles by deterministic precedence; resolves independently of the process current working directory; verifies package and bundle integrity offline; emits a typed fingerprinted receipt with truthful provider, official identity, trust posture, artifact-identity status, verified root, network posture, and categorical issues; and leaves every missing, altered, incompatible, incomplete, unsafe, or conflicting source untouched.

- **Requirement type:** `change`
- **Validation state:** `required`
- **Editable owner(s):** `tailtrail/aidlc_bundle.py`
- **Read-only input(s):** `TAILTRAIL-BUNDLED-OFFLINE-AIDLC-PROVISIONING-DESIGN.md`, `aidlc-rules/PROVENANCE.json`, `aidlc-rules/manifest.json`, `package-manifest.json`, `scripts/aidlc-official-detect.py`, `scripts/aidlc-official-install.py`, `scripts/installation-qualification.py`, `tailtrail/resources.py`
- **Proof path(s):** `tests/test_aidlc_bundle_resolver.py`
- **Proof intent:** `tests/test_aidlc_bundle_resolver.py` = `new-proof` (baseline `not-run`)
- **Success criteria:** All three package resource providers resolve through one typed package-owned contract with deterministic precedence and no current-working-directory dependency.; A successful receipt binds the selected provider, official identity, verified bundle root, package and bundle integrity fingerprints, truthful trust posture, artifact-identity status, and network_used false.; The focused proof covers positive provider selection and every declared negative integrity state.; A package-owned resolver returns a typed, fingerprinted receipt containing provider identity, official source/revision/commit, bundle fingerprint, trust posture, artifact-identity status, verified pack root, network_used false, and categorical issues.; Installed-package, managed-payload, and source-checkout providers resolve independently of the process current working directory and use deterministic documented precedence.; The source-checkout provider derives its root from module location plus repository sentinels and reports development-local unless stronger authenticated identity evidence is supplied.; The managed-payload provider resolves only the versioned shared install root and reports corruption-detection-only unless an exact qualifying ownership or installation receipt is verified.; Package outer integrity and bundle inner integrity are both checked before a provider can be selected, using exact expected/declared/actual inventory equality and safe regular-file paths.; Focused proof covers each provider, precedence, current-working-directory independence, truthful trust posture, exact receipt fingerprinting, altered/missing/incompatible assets, unsafe paths, and zero network access.
- **Preservation criteria:** Local hashes, legacy schema-v1 state, self-authored manifests, or unbound receipts never become authenticated-release or new-Full authority.; Resolution never accesses the network, executes pack content, follows unsafe links, or mutates source state.; This slice does not edit inspection inputs or implement project projection, future-run selection, frozen active-run binding, Full routing, or host projection.; No provider may infer authenticated-release from local hashes, a self-authored manifest, or an unbound installation receipt.; No provider may use the current working directory, contact the network, execute bundled content, follow unsafe symlinks, or silently fall back after an explicitly selected source fails.; Legacy schema-v1 project packs cannot authorize a new Full run and must not be silently promoted to schema v2.; This Phase 2A.1 slice must not edit generic resources, detector, installer, qualification, project projection, current.json, frozen run binding, Full Start routing, or host adapters.; Missing, altered, incompatible, incomplete, unsafe, or conflicting bundle state must remain untouched and produce a typed fail-closed result.
- **Requirement behaviour scenarios:**
  - `BHV-REQ-01`: Resolve valid installed-package, managed-payload, and source-checkout fixtures from a working directory outside the repository, then attempt resolution against altered and unsafe destination state. → TailTrail deterministically selects the eligible provider, emits a stable typed receipt with a truthful trust posture and network_used false, and rejects altered or unsafe state without modifying the destination.

| Tier | Command ID | Command | Candidate | State |
|---|---|---|---|---|
| behaviour | `cmd-8960f1` | `python3 -m unittest tests.test_aidlc_bundle_resolver` | `tests/test_aidlc_bundle_resolver.py` | resolved |
| contract | `cmd-8960f1` | `python3 -m unittest tests.test_aidlc_bundle_resolver` | `tests/test_aidlc_bundle_resolver.py` | resolved |
| unit | `cmd-8960f1` | `python3 -m unittest tests.test_aidlc_bundle_resolver` | `tests/test_aidlc_bundle_resolver.py` | resolved |

## Plan

1. **REQ-01:** Implement Add one package-owned official AIDLC bundle resolver that discovers installed-package, managed-payload, and source-checkout bundles by deterministic precedence; resolves independently of the process current working directory; verifies package and bundle integrity offline; emits a typed fingerprinted receipt with truthful provider, official identity, trust posture, artifact-identity status, verified root, network posture, and categorical issues; and leaves every missing, altered, incompatible, incomplete, unsafe, or conflicting source untouched. in `tailtrail/aidlc_bundle.py`; verify with `cmd-8960f1`, `cmd-8960f1`, `cmd-8960f1`; inspect `TAILTRAIL-BUNDLED-OFFLINE-AIDLC-PROVISIONING-DESIGN.md`, `aidlc-rules/PROVENANCE.json`, `aidlc-rules/manifest.json`, `package-manifest.json`, `scripts/aidlc-official-detect.py`, `scripts/aidlc-official-install.py`, `scripts/installation-qualification.py`, `tailtrail/resources.py`; prove against `tests/test_aidlc_bundle_resolver.py`.
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
| `pyproject.toml` | dependency boundary | Supporting/boundary-check path; inspect for impact, not an implementation candidate. | repository-inventory hypothesis |
| `scripts/aidlc-official-bridge.py` | implementation candidate | Primary implementation candidate, subject to post-approval source and caller confirmation. | repository-inventory hypothesis |
| `scripts/aidlc-official-detect.py` | implementation candidate | Primary implementation candidate, subject to post-approval source and caller confirmation. | repository-inventory hypothesis |
| `scripts/aidlc-official-host.py` | implementation candidate | Primary implementation candidate, subject to post-approval source and caller confirmation. | repository-inventory hypothesis |
| `scripts/aidlc-official-install.py` | implementation candidate | Primary implementation candidate, subject to post-approval source and caller confirmation. | repository-inventory hypothesis |
| `scripts/benchmark-tailtrail.py` | implementation candidate | Primary implementation candidate, subject to post-approval source and caller confirmation. | repository-inventory hypothesis |
| `scripts/install-copilot.py` | implementation candidate | Primary implementation candidate, subject to post-approval source and caller confirmation. | repository-inventory hypothesis |
| `scripts/official-aidlc-checkpoint.py` | implementation candidate | Primary implementation candidate, subject to post-approval source and caller confirmation. | repository-inventory hypothesis |
| `scripts/official-aidlc-requirements.py` | implementation candidate | Primary implementation candidate, subject to post-approval source and caller confirmation. | repository-inventory hypothesis |
| `scripts/official-aidlc-runtime.py` | implementation candidate | Primary implementation candidate, subject to post-approval source and caller confirmation. | repository-inventory hypothesis |
| `scripts/official-aidlc-sanitize.py` | implementation candidate | Primary implementation candidate, subject to post-approval source and caller confirmation. | repository-inventory hypothesis |
| `scripts/official-aidlc-state.py` | implementation candidate | Primary implementation candidate, subject to post-approval source and caller confirmation. | repository-inventory hypothesis |
| `scripts/tailtrail-report.py` | implementation candidate | Primary implementation candidate, subject to post-approval source and caller confirmation. | repository-inventory hypothesis |
| `scripts/tailtrail.py` | implementation candidate | Inspect after approval; edit only if the confirmed architecture contract requires it. | repository-inventory hypothesis |
| `scripts/update-tailtrail.py` | implementation candidate | Primary implementation candidate, subject to post-approval source and caller confirmation. | repository-inventory hypothesis |
| `tests/test_aidlc_bundle_provenance.py` | test evidence | Run only when its tier proves an approved requirement. | repository-inventory hypothesis |
| `tests/test_aidlc_official_bridge.py` | test evidence | Run only when its tier proves an approved requirement. | repository-inventory hypothesis |
| `tests/test_aidlc_official_detect.py` | test evidence | Run only when its tier proves an approved requirement. | repository-inventory hypothesis |
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

- **Requirements covered:** 1/1.
- **Proof command reuse:**
  - `cmd-8960f1` covers 1 requirement(s): REQ-01.

## Token Estimate

- Unavailable: scope is `ambiguous`, so a token estimate would not be reliable.
- This is an estimate from saved scope, not measured model/provider usage.

## Implementation Boundary

- **Editable scope:** `tailtrail/aidlc_bundle.py`.
- **Writable outputs:** none recorded.
- **Editable validation scope:** `tests/test_aidlc_bundle_resolver.py`.
- **Run-only proof scope:** none recorded.
- **Read-only / proof-only scope:** `TAILTRAIL-BUNDLED-OFFLINE-AIDLC-PROVISIONING-DESIGN.md`, `aidlc-rules/PROVENANCE.json`, `aidlc-rules/manifest.json`, `package-manifest.json`, `scripts/aidlc-official-detect.py`, `scripts/aidlc-official-install.py`, `scripts/installation-qualification.py`, `tailtrail/resources.py`, `tests/test_aidlc_bundle_resolver.py`.
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

- Machine-readable state remains available at [`.tailtrail/runs/start-20261104141125-cdefcb/planning/canonical-plan-projection-v4.json`](.tailtrail/runs/start-20261104141125-cdefcb/planning/canonical-plan-projection-v4.json); it is not the approval view.

---

*End of Start Plan.*