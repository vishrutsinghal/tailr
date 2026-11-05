# TailTrail Start Plan - Full Review Record

**Presentation version:** `5`
**Plan detail:** `Expert` (automatic for AIDLC Lite)

## Planning Lock

- **Run ID:** `start-20261104071446-c10930`
- **Status:** `approved`
- **Goal:** Implement corrected Phase 0 — Provenance decision and inventory from TAILTRAIL-BUNDLED-OFFLINE-AIDLC-PROVISIONING-DESIGN.md: extend scripts/aidlc-official-install.py to acquire one pinned official AIDLC release, resolve its full commit, verify the archive SHA-256 and MIT-0 license, compare the complete checked-in rule inventory against the authenticated upstream bytes, preserve exact matches and replace only verified mismatches within the two rule directories, generate aidlc-rules/PROVENANCE.json, aidlc-rules/LICENSE, and aidlc-rules/BUNDLE_VERSION, retain aidlc-rules/VERSION only as non-authoritative legacy inspection input, and record the compatibility, trust-posture, source-checkout, schema-v1/v2, active-run, external-pack, and host-projection decisions required by Phase 0; exclude packaging manifests, runtime resolution, Full routing, and host adapters.
- **Request mode:** `implementation`
- **Managed writes allowed:** `true`
- **Execution status:** planning only; no source change, proof command, scanner, or Git operation has run.
- **Plan revision:** active `3`; pending `none`.

## Bound Planning Inputs

| ID | Role | Path or reference | Access | Status | Integrity |
|---|---|---|---|---|---|
| `IN-02` | design-reference | `/Users/vsingha7/Desktop/tailr/TAILTRAIL-BUNDLED-OFFLINE-AIDLC-PROVISIONING-DESIGN.md` | read-only | verified-unread | `not hash-bound` |
| `IN-03` | evidence-artifact | `/Users/vsingha7/Desktop/tailr/session-reports/phase0-corrected-current-inventory.md` | read-only | verified-unread | `not hash-bound` |
- These inputs remain read-only context and never grant editable implementation scope.

## Command Reference Registry

| ID | Kind | Command |
|---|---|---|
| `cmd-0c5317` | proof | `python3 -m unittest tests.test_aidlc_bundle_provenance` |

## Validation Requirements And Focused Validation Matrix

### REQ-01

**Description:** Implement corrected Phase 0 — Provenance decision and inventory from TAILTRAIL-BUNDLED-OFFLINE-AIDLC-PROVISIONING-DESIGN.md: extend scripts/aidlc-official-install.py to acquire one pinned official AIDLC release, resolve its full commit, verify the archive SHA-256 and MIT-0 license, compare the complete checked-in rule inventory against the authenticated upstream bytes, preserve exact matches and replace only verified mismatches within the two rule directories, generate aidlc-rules/PROVENANCE.json, aidlc-rules/LICENSE, and aidlc-rules/BUNDLE_VERSION, retain aidlc-rules/VERSION only as non-authoritative legacy inspection input, and record the compatibility, trust-posture, source-checkout, schema-v1/v2, active-run, external-pack, and host-projection decisions required by Phase 0; exclude packaging manifests, runtime resolution, Full routing, and host adapters.

- **Requirement type:** `change`
- **Validation state:** `required`
- **Editable owner(s):** `scripts/aidlc-official-install.py`
- **Read-only input(s):** `TAILTRAIL-BUNDLED-OFFLINE-AIDLC-PROVISIONING-DESIGN.md`, `aidlc-rules/VERSION`, `session-reports/phase0-corrected-current-inventory.md`
- **Writable output(s):** `aidlc-rules/aws-aidlc-rules` (`configuration-output`, existing); `aidlc-rules/aws-aidlc-rule-details` (`configuration-output`, existing); `aidlc-rules/PROVENANCE.json` (`generated-output`, proposed); `aidlc-rules/LICENSE` (`generated-output`, proposed); `aidlc-rules/BUNDLE_VERSION` (`configuration-output`, proposed)
- **Proof path(s):** `tests/test_aidlc_bundle_provenance.py`, `tests/test_aidlc_official_install.py`
- **Success criteria:** The stated requirement is observably satisfied on its approved path.; One published official AIDLC tag, its full commit, release archive SHA-256, and exact MIT-0 license bytes are acquired from the official upstream and recorded together.; The complete current inventory of 30 rule files is compared by safe relative path and SHA-256 with the official archive; exact files are preserved and only verified mismatches are replaced.; PROVENANCE.json records acquisition, verification, archive, license, rule inventory, trust-posture, compatibility, migration, active-run, external-pack, and host-projection decisions without claiming to be an independent trust anchor.; BUNDLE_VERSION is separate from the official upstream revision; legacy VERSION is never treated as provenance.; The authenticated-release, development-local, corruption-detection-only, and external-explicit postures are explicit, and production Full fails closed when the required trust evidence is absent.; The focused proof exercises safe archive validation, closed inventory comparison, mismatch replacement, exact-match preservation, metadata generation, unsafe-path rejection, incomplete-acquisition failure, and deterministic output.
- **Preservation criteria:** Do not change behavior outside this approved requirement boundary.; No provenance claim may be derived only from aidlc-rules/VERSION, local filenames, or self-generated hashes.; No unverified local rule byte may be labelled as part of the pinned official release.; No rule outside aidlc-rules/aws-aidlc-rules and aidlc-rules/aws-aidlc-rule-details may be replaced, and no mismatch may be replaced before upstream archive and source identity verification succeeds.; No package manifest, source-distribution manifest, release manifest, resolver, Full-mode route, project projection, or host adapter may be changed in Phase 0.; No runtime network dependency, silent Full-to-Lite downgrade, weakened integrity check, fabricated acquisition evidence, or publisher-authentication claim from local hashes may be introduced.; Failure to acquire or verify the official tag, full commit, archive, license, or complete inventory must fail closed without writing partial Phase 0 outputs.
- **Requirement behaviour scenarios:**
  - `BHV-PHASE0-ACQUIRE-COMPARE`: Acquire a verified pinned official release fixture, compare it with a checked-in rule tree containing exact matches and a controlled mismatch, then repeat with incomplete and unsafe acquisition inputs. → Exact matches remain byte-identical, only the verified mismatch is replaced, complete provenance/license/bundle-version outputs are emitted atomically, and incomplete or unsafe inputs fail without partial writes.

| Tier | Command ID | Command | Candidate | State |
|---|---|---|---|---|
| behaviour | `cmd-0c5317` | `python3 -m unittest tests.test_aidlc_bundle_provenance` | `tests/test_aidlc_bundle_provenance.py` | resolved |
| contract | `cmd-0c5317` | `python3 -m unittest tests.test_aidlc_bundle_provenance` | `tests/test_aidlc_bundle_provenance.py` | resolved |
| integration | `cmd-0c5317` | `python3 -m unittest tests.test_aidlc_bundle_provenance` | `tests/test_aidlc_bundle_provenance.py` | resolved |
| unit | `cmd-0c5317` | `python3 -m unittest tests.test_aidlc_bundle_provenance` | `tests/test_aidlc_bundle_provenance.py` | resolved |

## Plan

1. **REQ-01:** Implement Implement corrected Phase 0 — Provenance decision and inventory from TAILTRAIL-BUNDLED-OFFLINE-AIDLC-PROVISIONING-DESIGN.md: extend scripts/aidlc-official-install.py to acquire one pinned official AIDLC release, resolve its full commit, verify the archive SHA-256 and MIT-0 license, compare the complete checked-in rule inventory against the authenticated upstream bytes, preserve exact matches and replace only verified mismatches within the two rule directories, generate aidlc-rules/PROVENANCE.json, aidlc-rules/LICENSE, and aidlc-rules/BUNDLE_VERSION, retain aidlc-rules/VERSION only as non-authoritative legacy inspection input, and record the compatibility, trust-posture, source-checkout, schema-v1/v2, active-run, external-pack, and host-projection decisions required by Phase 0; exclude packaging manifests, runtime resolution, Full routing, and host adapters. in `scripts/aidlc-official-install.py`; verify with `cmd-0c5317`, `cmd-0c5317`, `cmd-0c5317`, `cmd-0c5317`; inspect `TAILTRAIL-BUNDLED-OFFLINE-AIDLC-PROVISIONING-DESIGN.md`, `aidlc-rules/VERSION`, `session-reports/phase0-corrected-current-inventory.md`; prove against `tests/test_aidlc_bundle_provenance.py`, `tests/test_aidlc_official_install.py`; produce `aidlc-rules/aws-aidlc-rules` as `configuration-output`, `aidlc-rules/aws-aidlc-rule-details` as `configuration-output`, `aidlc-rules/PROVENANCE.json` as `generated-output`, `aidlc-rules/LICENSE` as `generated-output`, `aidlc-rules/BUNDLE_VERSION` as `configuration-output`.
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
| Handoff | as required by the plan | selected for this task |
| Project Learnings | as required by the plan | selected for this task |
| Learning Refresh Awareness | as required by the plan | selected for this task |

### Required before closure

- **Focused testing and validation:** prove the changed behavior, required preservation cases, and regression boundary with factual computational evidence
- **Canonical completion and closure:** prevent completion while required evidence is missing, unavailable, or failing

## Architecture Analysis

- **Status:** `planning-hypothesis`.
- **Evidence boundary:** Derived from explicit user wording and repository path inventory only. Source, caller relationships, and edit necessity are not confirmed until after approval.
- No requirement-linked analysis items were saved; revise before approval if this control is required.

### Scoped evidence

| Path | Role | Planned use | Confidence |
|---|---|---|---|
| `scripts/aidlc-official-install.py` | implementation candidate | Primary implementation candidate, subject to post-approval source and caller confirmation. | repository-inventory hypothesis |
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
  - `cmd-0c5317` covers 1 requirement(s): REQ-01.

## Token Estimate

- **Planned working set:** approximately `427` tokens (confidence: `medium`).
- **Scoped-file ceiling:** approximately `2630` tokens; estimated reduction `83.76%`.
- **Confidence basis:** at least one bounded slice lacks an exact combined behavior-and-symbol anchor.
- This is an estimate from saved scope, not measured model/provider usage.

## Implementation Boundary

- **Editable scope:** `scripts/aidlc-official-install.py`.
- **Writable outputs:** `aidlc-rules/BUNDLE_VERSION` (`configuration-output`), `aidlc-rules/LICENSE` (`generated-output`), `aidlc-rules/PROVENANCE.json` (`generated-output`), `aidlc-rules/aws-aidlc-rule-details` (`configuration-output`), `aidlc-rules/aws-aidlc-rules` (`configuration-output`).
- **Read-only / proof-only scope:** `TAILTRAIL-BUNDLED-OFFLINE-AIDLC-PROVISIONING-DESIGN.md`, `aidlc-rules/VERSION`, `session-reports/phase0-corrected-current-inventory.md`, `tests/test_aidlc_bundle_provenance.py`, `tests/test_aidlc_official_install.py`.
- **Excluded:** every path, command, external system, deployment, and data change not explicitly recorded above remains outside this approval.
- **Data impact:** no data impact is authorized unless a requirement above names it explicitly.

## Approval Checklist

- [x] Requirements are present and reviewable.
- [x] Every requirement has an editable implementation owner.
- [x] Runnable proof commands are registered and mapped to requirements.
- [x] Material questions are resolved.
- [x] Mandatory planning audit is clean for this exact plan revision.
- [ ] The host has reviewed the scope, preservation criteria, proof commands, analyses, and excluded boundary.
- **Risks to review:** data shape; release

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

- Machine-readable state remains available at [`.tailtrail/runs/start-20261104071446-c10930/planning/canonical-plan-projection-v5.json`](.tailtrail/runs/start-20261104071446-c10930/planning/canonical-plan-projection-v5.json); it is not the approval view.

---

*End of Start Plan.*