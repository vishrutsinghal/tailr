# TailTrail Start Plan - Full Review Record

**Presentation version:** `5`
**Plan detail:** `Expert` (automatic for AIDLC Lite)

## Planning Lock

- **Run ID:** `start-20261105090516-55c9cb`
- **Status:** `approved`
- **Goal:** Implement Phase 3A Full-preflight bridge adapter in scripts/aidlc-official-bridge.py using the current dirty worktree as the shared baseline: add a bridge API that invokes the existing tailtrail/aidlc_bundle.py resolver and atomic projector for explicit Full mode, preserves requested_mode full with effective_mode full when ready or unavailable when blocked, never returns Lite, carries one resolution receipt fingerprint into the project projection result, reports network_used false plus categorical actionable issues, and writes only managed project-pack state; keep existing Standard and legacy explicit-manifest preflight behavior unchanged and leave task-start, Planning Lock, Requirements-stage, MCP, host-projection, packaging, schema, registry, CLI, and documentation wiring for later Phase 3 slices; prove the bridge adapter with python3 -m unittest tests/test_aidlc_official_bridge.py -k full_without_a_compatible_pack -k bundled_full_preflight -v.
- **Request mode:** `implementation`
- **Managed writes allowed:** `true`
- **Execution status:** planning only; no source change, proof command, scanner, or Git operation has run.
- **Plan revision:** active `2`; pending `none`.

## Bound Planning Inputs

- No read-only planning inputs were bound to this plan.

## Command Reference Registry

| ID | Kind | Command |
|---|---|---|
| `cmd-ee36eb` | proof | `python3 -m unittest tests/test_aidlc_official_bridge.py -k full_without_a_compatible_pack -k bundled_full_preflight -v` |

## Validation Requirements And Focused Validation Matrix

### REQ-01

**Description:** Add a Phase 3A bridge API that resolves and atomically projects the bundled official pack for explicit Full mode, returns one consistent ready identity or typed Full-unavailable guidance, and never produces Lite.

- **Requirement type:** `change`
- **Validation state:** `required`
- **Editable owner(s):** `scripts/aidlc-official-bridge.py`
- **Read-only input(s):** `TAILTRAIL-BUNDLED-OFFLINE-AIDLC-PROVISIONING-DESIGN.md`, `scripts/official-aidlc-requirements.py`, `scripts/planning_lock.py`, `scripts/task-start.py`, `tailtrail/aidlc_bundle.py`, `tests/test_aidlc_bundle_resolver.py`
- **Proof path(s):** `tests/test_aidlc_official_bridge.py`
- **Proof intent:** `tests/test_aidlc_official_bridge.py` = `editable-proof` (baseline `not-run`)
- **Success criteria:** The bridge composes the existing explicit-Full bundle resolver and atomic projector without adding another source of pack discovery or projection logic.; Ready output retains requested_mode full, effective_mode full, network_used false, and an exact resolution-to-projection fingerprint chain.; Resolver or projection blockers return effective_mode unavailable, categorical issues, and actionable recovery guidance without a Lite result.; Only managed content-addressed project-pack state may be written by the existing projector; no Planning Lock or project source is created by this API.; The targeted command covers the existing legacy preservation case and all new bundled_full_preflight cases without selecting unrelated Full lifecycle tests.; The bridge exposes a Phase 3A Full-preflight API that accepts the target root and supported host, invokes the package-owned explicit-Full resolver, and passes only a ready sealed resolution receipt into the existing atomic project projector.; A ready result preserves requested_mode and effective_mode as full, network_used as false, and projects the same resolution receipt fingerprint into the returned project-pack identity and projection fingerprint.; A blocked resolver never calls provisioning; a blocked projection never claims Full readiness. Both retain requested_mode full, use effective_mode unavailable, preserve typed issue categories, and return an actionable recovery boundary without creating a Lite result.; Provisioning may write only TailTrail-managed content-addressed project-pack state through tailtrail/aidlc_bundle.py; the bridge itself does not write project source or create a Planning Lock.; The exact targeted proof selects the existing legacy Full-preflight preservation test plus the new bundled_full_preflight tests and excludes unrelated Full activation and Requirements-stage tests.
- **Preservation criteria:** No public task-start, Planning Lock, Requirements-stage, MCP, host-projection, packaging, schema, registry, CLI, or documentation wiring is changed in Phase 3A.; The bridge does not download or execute pack content, rewrite receipts, accept unsupported hosts, convert blocked Full state to Lite, or claim readiness after blocked projection.; Existing Standard and legacy explicit-manifest preflight behavior remain unchanged until separately approved public-route migration.; No path other than scripts/aidlc-official-bridge.py and the approved editable proof file may be modified.; Phase 3A does not wire the new adapter into task-start, Planning Lock, Requirements-stage lookup, MCP, host projection, packaging, schemas, registry, CLI dispatch, or documentation; those remain later Phase 3 slices.; The adapter never downloads rules, executes pack content, rewrites a resolver receipt, silently falls back to Lite, accepts an unsupported host, or treats blocked resolution/projection state as ready.; The shared resolver/projector, task-start, Planning Lock, Requirements adapter, MCP server, host adapters, schemas, manifests, registry, commands, and documentation are inspection-only or excluded from edits.; Existing Standard preflight and legacy explicit-manifest Full preflight behavior remain unchanged until the public route migration is approved separately.; No proof command broader than the two named unittest filters is authorized in this slice.
- **Requirement behaviour scenarios:**
  - `BHV-PHASE3A-BUNDLED-FULL-PREFLIGHT`: Supply ready and blocked sealed bundled-Full resolution receipts to the new bridge adapter, allow projection only for the ready receipt, then exercise blocked projection and the existing legacy explicit-manifest preflight. → Ready bundled preflight returns requested and effective Full mode, network_used false, and matching resolution and projection fingerprints; blocked resolution never provisions; blocked projection remains Full-unavailable with typed actionable guidance; no result becomes Lite; existing Standard and legacy explicit-manifest preflight behavior remains unchanged.

| Tier | Command ID | Command | Candidate | State |
|---|---|---|---|---|
| behaviour | `cmd-ee36eb` | `python3 -m unittest tests/test_aidlc_official_bridge.py -k full_without_a_compatible_pack -k bundled_full_preflight -v` | `tests/test_aidlc_official_bridge.py` | resolved |
| contract | `cmd-ee36eb` | `python3 -m unittest tests/test_aidlc_official_bridge.py -k full_without_a_compatible_pack -k bundled_full_preflight -v` | `tests/test_aidlc_official_bridge.py` | resolved |
| unit | `cmd-ee36eb` | `python3 -m unittest tests/test_aidlc_official_bridge.py -k full_without_a_compatible_pack -k bundled_full_preflight -v` | `tests/test_aidlc_official_bridge.py` | resolved |

## Plan

1. **REQ-01:** Implement Add a Phase 3A bridge API that resolves and atomically projects the bundled official pack for explicit Full mode, returns one consistent ready identity or typed Full-unavailable guidance, and never produces Lite. in `scripts/aidlc-official-bridge.py`; verify with `cmd-ee36eb`, `cmd-ee36eb`, `cmd-ee36eb`; inspect `TAILTRAIL-BUNDLED-OFFLINE-AIDLC-PROVISIONING-DESIGN.md`, `scripts/official-aidlc-requirements.py`, `scripts/planning_lock.py`, `scripts/task-start.py`, `tailtrail/aidlc_bundle.py`, `tests/test_aidlc_bundle_resolver.py`; prove against `tests/test_aidlc_official_bridge.py`.
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
| `tests/test_official_aidlc_checkpoint.py` | test evidence | Run only when its tier proves an approved requirement. | repository-inventory hypothesis |
| `tests/test_official_aidlc_runtime.py` | test evidence | Run only when its tier proves an approved requirement. | repository-inventory hypothesis |
| `tests/test_official_aidlc_sanitize.py` | test evidence | Run only when its tier proves an approved requirement. | repository-inventory hypothesis |

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
  - `cmd-ee36eb` covers 1 requirement(s): REQ-01.

## Token Estimate

- **Planned working set:** approximately `2785` tokens (confidence: `medium`).
- **Scoped-file ceiling:** approximately `16525` tokens; estimated reduction `83.15%`.
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

- Machine-readable state remains available at [`.tailtrail/runs/start-20261105090516-55c9cb/planning/canonical-plan-projection-v4.json`](.tailtrail/runs/start-20261105090516-55c9cb/planning/canonical-plan-projection-v4.json); it is not the approval view.

---

*End of Start Plan.*