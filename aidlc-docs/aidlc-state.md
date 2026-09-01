# AIDLC State

Project: TailTrail

Lifecycle depth: comprehensive

Current phase: Product Maturity PM-7 implementation complete and protocol-ready; genuine adoption evidence and Enterprise E5 hosted evidence remain open

Current stage: PM-7 local contracts, runtime, distribution, and assurance complete; real usability trials and E5 hosted dependency evidence remain pending

Status: Enterprise Phases E0-E4 are closed; E5 and E6 implementation, contracts, workflows, local proofs, and negatives are present. E5 hosted receipts/tag attestations remain externally unobserved, so dependency-ordered E6 stays in progress and E7-E12 remain open; the enterprise release candidate remains blocked

Next step: collect genuine observer-attested PM-7 new-user and experienced-user trials and run the fail-closed adoption gate; separately run the pinned E5 workflow for one commit, ingest all six hosted receipts, and identity-attest a qualifying release tag. Do not turn protocol fixtures, local tests, configured workflows, or offline evidence into either claim.

Last updated: 2026-09-01

- Goal: Implement Product Maturity PM-7 — Adoption Validation.
- Requirements/workflow/implementation gates: approved by the user's explicit
  end-to-end PM-7 implementation request on 2026-09-01.
- Requirements: `aidlc-docs/phase-pm-7-requirements.md`.
- Design: `aidlc-docs/phase-pm-7-design.md`.
- Dependencies: none added or changed; Python standard-library JSON, hashing,
  time, paths, immutable-create semantics, Evaluation Harness, product-maturity
  freeze, registry, MCP, package, installer, release, and enterprise inventory
  controls are reused.
- Implementation: sealed two-cohort/eight-scenario usability protocol; explicit
  participant/coverage and numeric time, approval, abandonment, intervention,
  comprehension, and zero-safety-weakening gates; approval-gated sanitized
  immutable trial receipts; derived timing; fixture/real evidence separation;
  tamper/stale-catalog/path/privacy rejection; deterministic reports and nonzero
  gate; repeated independent wording/default recommendations; approval-gated
  proposal and single-decision lineage; canonical CLI and read-only MCP report;
  host-pack, wheel/sdist, release, enterprise candidate, docs, and policy-freeze
  integration.
- Evidence boundary: no real participant was fabricated or inferred. The live
  repository report is `protocol-ready` with `no-adoption-claim`; fixture-only,
  collecting, missed-threshold, safety-weakened, and invalid evidence all remain
  non-qualifying. Recommendations never edit source or weaken safeguards.
- Validation: nine focused PM-7 tests and 81 final PM-7/Evaluation/MCP/maturity
  tests pass; 37 installer/self-contained-package/release-truth tests pass; all
  176 schemas compile; strict registry, Product Maturity, enterprise candidate,
  public docs, release manifest, host adapter conformance, MCP doctor, Python
  compilation, and `git diff --check` pass. The repository-wide run executed
  1,025 tests: 1,023 passed, with only the same two pre-existing unrelated
  baselines remaining (`debug-investigation` is absent from the DWR template
  schema, and one CLI test expects a nonzero Start result for a goal that now
  resolves). The broad checker remains blocked only by the pre-existing
  `debug-intial.md contains tab indentation` finding. Registry drift separately
  reports 24 older undocumented Intent Bridge command entries and no PM-7 drift.

- Goal: Implement Product Maturity PM-L5 — Learning Calibration And Proof.
- Requirements/workflow/implementation gates: approved by the user's explicit
  PM-L5 implementation request on 2026-09-01.
- Requirements: `aidlc-docs/phase-pm-l5-requirements.md`.
- Design: `aidlc-docs/phase-pm-l5-design.md`.
- Dependencies: none added or changed; Python standard-library JSON, hashing,
  time, statistics, path, and existing Learning V3, PM-L3 receipt, Evaluation
  Harness, Meta-Harness, registry, package, and installer controls are reused.
- Implementation: closed and sealed paired learning-on/control catalog for all
  seven V3 classes; deterministic precision, false-intervention, Brier,
  confidence-gap, correction-cycle, review-time, and token-overhead metrics;
  real later-receipt joins; four-sample mixed-outcome gate; approval-gated,
  report-linked, repository-framed plus/minus-ten confidence projection;
  fail-closed Navigator ranking; repeated categorical sanitizer-valid
  Meta-Harness evidence and proposal integration; CLI, ownership, host pack,
  wheel/sdist, release, enterprise registry, and documentation integration.
- Evidence boundary: fixture observations are regression evidence only and
  publish no performance claim. Project calibration consumes only applied,
  chain-valid PM-L3 receipts with a later positive/adverse attribution and an
  existing completion-report reference. It does not infer causality or grant
  advice-use, source, command, Git, release, deployment, or acceptance
  authority. Shared evidence excludes raw content, paths, identity, receipt or
  scenario IDs, exact tokens, and exact timings.
- Validation: seven focused PM-L5 tests and 41 final calibration/maturity/
  retrieval/Meta-Harness tests pass; 20 Codex/Copilot/Claude installer-profile
  tests pass; isolated wheel/sdist inventory and sdist-install proofs pass; all
  167 schemas compile; strict registry, Product Maturity, release manifest,
  enterprise candidate, Python compilation, and `git diff --check` pass. The
  repository-wide run executed 1,013 tests: 1,011 passed, with only the two
  pre-existing unrelated baselines remaining (`debug-investigation` is absent
  from the DWR template schema, and one CLI test expects a nonzero Start result
  for a goal that now resolves). The broad checker remains blocked only by the
  pre-existing `debug-intial.md contains tab indentation` finding.

- Goal: Implement Product Maturity PM-L4 — Refresh, Conflict, And Negative
  Learning.
- Requirements/workflow/implementation gates: approved by the user's explicit
  PM-L4 implementation request on 2026-09-01.
- Requirements: `aidlc-docs/phase-pm-l4-requirements.md`.
- Design: `aidlc-docs/phase-pm-l4-design.md`.
- Dependencies: none added or changed; standard-library JSON, hashing, paths,
  timestamps, existing cross-platform locks, Learning V3/retrieval, PM-L3
  receipts, refresh, review, inventory, registry, and package controls are
  reused.
- Implementation: approval-gated challenge/conflict/revalidation/negative
  lifecycles; V3 revalidation; repository fingerprints for policy, graph,
  symbol, manifest, ownership, source, and validation invalidators; fail-closed
  Navigator integration; pairwise scope resolution; repeated adverse receipt
  aggregation; sanitized avoid-history promotion; source-learning revocation;
  refresh/review, CLI, ownership, registry, host pack, package, release, and
  enterprise candidate integration.
- Evidence boundary: negative candidates retain categorical counts and
  project-relative evidence references only. They never copy raw failures,
  prompts, logs, source, stack traces, identity fields, or secrets. Association
  remains non-causal, and current evidence always wins.
- Validation: 45 focused Learning V3/retrieval/receipt/governance tests pass;
  113 integrated learning/maturity/registry/install/enterprise tests pass; and
  nine isolated wheel/sdist tests pass. Strict registry, Product Maturity,
  public release, JSON-schema meta-validation, Python compilation, and `git
  diff --check` pass. The 1006-test repository run exposed six PM-L4 release
  integration gaps, all fixed and rerun in their affected modules. Its two
  remaining unrelated failures are the pre-existing CLI Start fixture
  assumption and Debug `debug-investigation` real-run schema mismatch. The
  broad checker remains blocked only by the pre-existing `debug-intial.md`
  tab-indentation finding.

- Goal: Implement Product Maturity PM-L3 — Use Receipts And Closure
  Attribution.
- Requirements/workflow/implementation gates: approved by the user's explicit
  PM-L3 implementation request on 2026-09-01.
- Requirements: `aidlc-docs/phase-pm-l3-requirements.md`.
- Design: `aidlc-docs/phase-pm-l3-design.md`.
- Dependencies: none added or changed; standard-library JSON, hashing, paths,
  locking, existing Planning Lock/anchor, Learning V3/retrieval, run ledger,
  and Completion Report controls are reused.
- Implementation: approval-gated append-only applied/advisory/ignored/rejected/
  stale decisions; exact saved-proposal/current-V3 checks; requirement and
  decision-type links; closure joins to requirement, drift, Harness, failure,
  validation, and report evidence; non-causal categorical associations;
  latest-attribution projection; domain/project utility caps; retrieval
  feedback; Completion Report, CLI, ownership, registry, package, installer,
  and documentation integration.
- Evidence boundary: observed association never proves causality, grants
  authority, promotes learning, or overrides current source, policy, test, CI,
  scanner, guardrail, or user evidence. Existing workflow candidate links and
  legacy learning stores remain unchanged.
- Validation: 266 integrated learning/Navigator/closure/workflow/maturity/
  registry/install/package/release tests pass on the final tree, including 14
  focused PM-L3 negative, concurrency, cap, attribution, retrieval-feedback,
  CLI, report, and tamper tests plus nine reproducible isolated wheel/sdist
  tests. Strict registry validation, Product Maturity validation, release
  manifest validation, JSON parsing, Python compilation, and `git diff
  --check` pass. The broad legacy checker and `doctor` remain blocked only by
  the pre-existing `debug-intial.md contains tab indentation` finding; PM-L3
  does not edit that unrelated file. One unrelated CLI-dispatch assertion also
  expects a pre-target error for a goal that the current repository now
  resolves successfully; it is not represented as PM-L3 evidence.

- Goal: Implement Product Maturity PM-L2 — Navigator Retrieval And Conflict Gate.
- Requirements/workflow/implementation gates: approved by the user's explicit
  PM-L2 implementation request on 2026-09-01.
- Requirements: `aidlc-docs/phase-pm-l2-requirements.md`.
- Design: `aidlc-docs/phase-pm-l2-design.md`.
- Dependencies: none added or changed; standard-library framing, matching,
  time, path, JSON, and existing Learning V3 compatibility controls are reused.
- Implementation: project/task-framed read-only retrieval, deterministic
  applicability ranking, three-result cap, match and invalidator explanations,
  default-deny use proposal, quiet Lite behavior, and fail-closed stale,
  suppressed, private, excluded, missing-source, and contradiction handling;
  Start and Next preserve the pending proposal choice.
- Evidence boundary: PM-L2 creates no use receipt or conflict ledger. PM-L3
  owns receipts/closure attribution and PM-L4 owns durable conflict and negative
  learning transitions.
- Validation: 11 focused PM-L2 tests and 169 integrated
  learning/Navigator/closure/maturity/install/registry/package/release tests
  pass on the final tree. Strict registry validation, PM maturity validation,
  JSON parsing, and `git diff --check` pass. The broad legacy check remains
  blocked only by the pre-existing `debug-intial.md contains tab indentation`
  finding; PM-L2 does not edit that unrelated file.

- Goal: Implement Product Maturity PM-L1 — Learning V3 Contract And Migration.
- Requirements/workflow/implementation gates: approved by the user's explicit
  PM-L1 implementation request on 2026-09-01.
- Requirements: `aidlc-docs/phase-pm-l1-requirements.md`.
- Design: `aidlc-docs/phase-pm-l1-design.md`.
- Dependencies: none added or changed; standard-library JSON, hashing, paths,
  and existing Learning Agent compatibility surfaces are reused.
- Implementation: closed V3 record, append-only digest chain, amendment,
  supersession, revocation, project-frame/privacy validation, canonical writer
  delegation, deterministic combined readers, and approval-gated idempotent
  legacy reference migration.
- Evidence boundary: V3 stores sanitized advice and references only; PM-L2 owns
  retrieval/conflict gating, PM-L3 owns use receipts, and PM-L4 owns first-class
  conflict and negative-learning transitions.
- Validation: 26 Learning V3/closure/completion tests, 97 integrated
  V3/maturity/install/registry/release/host tests, and nine isolated wheel/sdist
  tests pass. Strict registry and PM maturity validation pass with no freeze
  drift.

- Goal: Implement Product Maturity PM-L0 — Learning Inventory And Ownership.
- Requirements/workflow/implementation gates: approved by the user's explicit
  PM-L0 implementation request on 2026-09-01.
- Requirements: `aidlc-docs/phase-pm-l0-requirements.md`.
- Design: `aidlc-docs/phase-pm-l0-design.md`.
- Dependencies: none added or changed; the standard library and existing
  maturity, package, registry, and learning controls are reused.
- Implementation: sealed ten-system inventory, six canonical fact owners,
  physical artifact ownership, exact compatibility routes, non-destructive
  migration boundaries, CLI rendering, package inclusion, and freeze approval.
- Validation: 12 focused PM-L0/PM-0 tests, 36 maturity/registry tests, and nine
  isolated wheel/sdist tests pass. The repository-wide checker still stops on
  the pre-existing tab in `debug-intial.md`; no claim is made that it passed.

- Goal: Implement Enterprise Phase E6 — repository and CI enforcement product end to end.
- Requirements/workflow/implementation gates: approved by the user's explicit end-to-end E6 implementation request on 2026-08-24.
- Requirements: `aidlc-docs/phase-e6-requirements.md`.
- Design: `aidlc-docs/phase-e6-design.md`.
- Dependencies: no package added or changed; the standard library and existing Guard, Dependency Gate, release-manifest, registry, package, and CI contracts are reused.
- Implementation: closed versioned policy/override validation, exact approvals, provider-neutral diff modes, all configured Core controls, stable JSON/SARIF, visible exact baselines, exact owner/reason/expiry suppressions, v0 migration, exact-version action, and pinned read-only GitHub workflow are present.
- Evidence boundary: E6 local product proof can complete, but `ENT-E6-001` cannot be marked complete while its `ENT-E5-001` dependency lacks the six hosted receipts. Configured CI is not represented as a hosted run.
- Validation: 15 focused E6 tests pass on both CPython 3.12 and 3.13 after the final high-baseline and expired-approval lifecycle negatives were added. An isolated installed wheel ran policy validation and a safe diff without a checkout. The complete CPython 3.12 suite passed all 768 tests in 1567.461 seconds before those final focused hardening assertions; both implementation branches are covered by both final focused runs.

- Goal: Implement Enterprise Phase E5 — cross-platform distribution and
  release supply chain end to end.
- Requirements/workflow/implementation gates: approved by the user's explicit
  end-to-end E5 implementation request on 2026-08-22.
- Requirements: `aidlc-docs/phase-e5-requirements.md`.
- Design: `aidlc-docs/phase-e5-design.md`.
- Dependency decision: exact build-only `setuptools==84.0.0`, `wheel==0.48.0`,
  and resolved `packaging==26.3` are approved and owned; no runtime dependency
  or SBOM/provenance/platform library was added.
- Implementation: canonical deterministic build, sdist-to-wheel proof, archive
  inspection, checksum/SBOM/provenance bundle, exact hosted matrix receipts,
  aggregate gate, tag-only identity attestation, public verification guidance,
  support limitations, and tamper/missing/non-hosted negatives are present.
- Local proof: exact-pin wheel and sdist rebuild byte-for-byte; the sdist-built
  wheel matches the canonical wheel. Artifact inspection and evidence-bundle
  algorithms/negatives pass. Release provenance is intentionally unavailable
  for this dirty worktree because its bytes are not attributable to HEAD. A
  real local macOS 15/arm64 CPython 3.12 receipt passes
  both artifact routes and all three host lifecycles, path, CRLF, permission,
  and symlink checks, and truthfully records `ci: false`.
- Exit truth: E5 is not closed from local evidence. Six matching hosted
  Linux/macOS/Windows x CPython 3.12/3.13 receipts and tagged identity
  attestations have not been observed in this workspace.
- Repository regression: the final CPython 3.12 run passed all 754 tests in
  778.170 seconds. E5's supported-interpreter and OS matrix remains assigned to
  the hosted workflow rather than inferred from this one local interpreter.

- Goal: Implement Enterprise Phase E4 — equal-quality Codex, GitHub Copilot,
  and Claude adapters over the E3 lifecycle.
- Requirements/workflow/implementation gates: approved by the user's explicit
  end-to-end E4 implementation request on 2026-08-22.
- Requirements: `aidlc-docs/phase-e4-requirements.md`.
- Design: `aidlc-docs/phase-e4-design.md`.
- Dependencies: no product dependency added or changed. The CPython 3.13 suite
  used an isolated temporary environment containing the already-declared build
  tools `setuptools` and `wheel` because the host interpreter lacked
  `setuptools.build_meta`.
- Phase boundary: E4 proves local contracts and checkout-free installed-wheel
  journeys. E5 owns platform support; E10 owns real named-host receipts.
- Closeout truth: 35 initial focused tests and 36 repaired integration/artifact
  tests pass. The final complete suite has 748 passing tests on CPython 3.12 in
  633.866 seconds and CPython 3.13 in 590.394 seconds.

- Goal: Implement Enterprise Phase E3 — one transactional install, verify,
  doctor, status, update, repair, recover, rollback, and uninstall lifecycle.
- Requirements/workflow/implementation gates: approved by the user's explicit
  end-to-end E3 implementation request on 2026-08-22.
- Requirements: `aidlc-docs/phase-e3-requirements.md`.
- Design: `aidlc-docs/phase-e3-design.md`.
- Dependencies: none added or changed; standard-library atomic replace,
  hashing, JSON, filesystem, process, and temporary-file primitives are reused.
- Phase boundary: E3 owns shared transactional behavior. Exact host adapter
  qualification remains E4 and OS/platform qualification remains E5.
- Closeout truth: 17 focused transaction tests and the combined 70-test E3
  installer/profile/CLI slice pass on both supported interpreters. Eight package
  tests pass on each interpreter, including checkout-free installed-wheel
  lifecycle proof. The complete 741-test suite passed on CPython 3.12 in
  619.675 seconds and CPython 3.13 in 552.139 seconds.

- Goal: Implement Enterprise Phase E2 — self-contained wheel/sdist product
  kernel, stable compatibility contracts, integrity, migrations, and isolated
  Core lifecycle proof.
- Requirements/workflow/implementation gates: approved by the user's explicit
  end-to-end E2 implementation request on 2026-08-22.
- Requirements: `aidlc-docs/phase-e2-requirements.md`.
- Design: `aidlc-docs/phase-e2-design.md`.
- Dependencies: none added or changed; the existing setuptools/wheel build
  requirements and Python standard library are reused, with no runtime
  dependencies.
- Focused E2 proof: seven tests pass across artifact inventory/hash inspection,
  wheel and sdist install, Python/exit/migration contracts, corrupt/missing
  resources, no-checkout launcher behavior, isolated Planning Lock activation,
  Mode B recovery apply, execution evidence, complete closure, and JSON error
  containment.
- Artifact boundary: user-owned proposal, backup, IDE, local-state, cache,
  test, symbolic-link, and secret-like paths are excluded or rejected.
- Closeout truth: E2 is complete. The focused proof passed on CPython 3.12 and
  3.13, and the complete 723-test suite passed on CPython 3.12 in 605.763
  seconds and CPython 3.13 in 601.523 seconds. Later installer, OS, host,
  security, operations, pilot, and GA claims remain blocked.

- Goal: Implement Enterprise Phase E0 — baseline, ownership, inventory, feature freeze, known defects, and complete E0-E12 closure traceability.
- Lifecycle depth: comprehensive because E0 governs packaging, security, privacy, release, host support, enterprise operations, and GA boundaries.
- Requirements/workflow/implementation gates: approved by the user's explicit end-to-end E0 implementation request on 2026-08-22.
- Authority: `ENTERPRISE-READINESS-ASSESSMENT.md` Sections 13–19; its E0-E12 sequence supersedes the historical plan.
- Requirements: `aidlc-docs/phase-e0-requirements.md`.
- Design: `aidlc-docs/phase-e0-design.md`.
- Dependencies: none added or changed; implementation uses Python standard library and existing TailTrail registries.
- Ownership boundary: preserve all unrelated and user-owned untracked files; classify them without staging, deleting, or silently including them.
- Release truth: E0 declares the current baseline blocked and does not claim the E1 release, package, smoke, full-suite, or real-host gates pass.
- E0 focused validation: 17 tests passed, including closed-field, baseline commit/branch/worktree drift, ownership, dependency, maturity, evidence, release blocking, inventory-category uniqueness, untracked-path, inventory, status, and CLI negatives.
- E0 integration validation: 98 tests passed across enterprise readiness, feature registry, registry drift, CLI dispatch, installer profiles, and workflow documentation.
- Repository-wide baseline: 704 tests ran with exactly the five registered E1 defects (four failures and one error). No E0 test failed.
- E0 governance: enterprise closure validation, strict feature registry, Extended pack ownership, authority-document traceability, and read-only inventory passed.
- E0 exit gate: passed for six E0 requirements, 27 total E0-E12 requirements, and 12 known defects. Passing E0 means complete ownership/classification only, not release readiness.

- Goal: Implement Enterprise Phase E1 — restore complete test, release, repository, Navigator, smoke, CI, documentation, and negative-fixture truth.
- Requirements/workflow/implementation gates: approved by the user's explicit end-to-end E1 implementation request on 2026-08-22.
- Requirements: `aidlc-docs/phase-e1-requirements.md`.
- Design: `aidlc-docs/phase-e1-design.md`.
- Dependencies: none added or changed; implementation uses the Python standard library and existing TailTrail contracts.
- Complete suite: 716 tests passed with no baseline exception list after two newly exposed Extended-pack/smoke compatibility expectations were corrected.
- E1 negative assurance: missing file, wrong version, private reference, stale workflow, and local-state fixtures failed as intended; the approved official-upstream fixture passed.
- Release gates: enterprise registry, strict feature registry, repository check, public audit, release check, doctor, manifest-isolated smoke, root Navigator import, compile, and diff hygiene passed.
- E1 exit gate: passed for three E1 requirements and eight E1 defects. E2-E12 and four later-phase known defects remain open, so enterprise release remains blocked.

- Goal: Implement Deferred Phase 11 — evaluation, real-run proof, migration, and release gate end to end.
- Requirements gate: approved by the user's explicit implementation request on 2026-08-21.
- Workflow gate: approved by the same explicit end-to-end request.
- Implementation gate: approved by the same explicit end-to-end request.
- Dependencies: none added or changed.
- Phase 12 requirements and implementation design are approved by the user's explicit end-to-end request on 2026-08-21.
- Phase 12 preserves local mode as default and cannot activate while the Phase 11 live release gate is blocked.
- Focused Phase 12: 17 tests passed.
- Integrated Phase 7–12/MCP/host/package/documentation regression: 168 tests passed.
- Repository-wide: 691 tests ran with the same five pre-existing unrelated failures: unsupported legacy `evaluation_calibrated`, extra `dwr-small-change-vertical` scenario inventory, two Navigator expectation mismatches, and one UI wording mismatch. No Phase 12 test failed.
- Governance: strict registry, adapter sync, MCP doctor, generated host conformance, Phase 12 drift check, AIDLC, guardrails, Python compilation, module-size boundary, and diff check passed.
- Enterprise truth: no adapter was activated in this repository, no provider was contacted, and no production/provider conformance, availability, encryption, external backup, or cost claim was inferred from the local reference adapter.
- Dependencies: none added or changed.
- Completed slice: closed release-proof contracts, 15-scenario evidence, six-template real-run receipts, host convergence, compatibility/migration assessment, and separately approved `--no-workflow` retirement.
- Focused Phase 10: 16 tests passed.
- Integrated Phase 7–10/MCP/host/package/docs regression: 162 tests run; only two MCP ordering failures were found, fixed, and revalidated in a 61-test passing run plus a passing MCP doctor.
- Repository-wide: 665 tests run with the same five pre-existing unrelated failures documented before Phase 10 (one missing `evaluation_calibrated` ledger event, one scenario-inventory mismatch, two Navigator expectation mismatches, and one UI wording mismatch).
- Governance: strict registry, adapter sync, generated host conformance, AIDLC, guardrails, Python compilation, and diff check passed. The legacy all-file `check-tailtrail.py` inventory remains broadly stale and reports pre-existing missing/unexpected files; its Phase 10 drift assertions were added without concealing that baseline.
- Dependencies: none added or changed.
- Closeout gate: complete for Phase 10; external real-host receipt status remains truthfully `not-validated`.

Phase 11 must implement the complete proof and gate surface while remaining
fail-closed: implementation completion is not release eligibility. Real host or
project evidence may not be fabricated, compatibility history is never migrated
automatically, and `--no-workflow` retirement requires a separate explicit
approval after every evidence threshold passes.

- Focused Phase 11: 9 tests passed.
- Integrated Phase 7–11/MCP/host/package/documentation regression: 171 tests passed.
- Repository-wide: 674 tests ran with the same five pre-existing unrelated failures: unsupported legacy `evaluation_calibrated`, extra `dwr-small-change-vertical` scenario inventory, two Navigator expectation mismatches, and one UI wording mismatch. No Phase 11 test failed.
- Governance: strict registry, adapter sync, MCP doctor, generated host conformance, AIDLC, guardrails, Python compilation, compatibility assessment, and diff check passed.
- Release truth: the live gate is correctly `BLOCKED` because no genuine persisted 15-scenario, six-template, three-host, and measured-token receipt set exists. No receipt was fabricated and no retirement decision was written.
- Compatibility: old commands and artifacts remain authoritative, automatic migration and aliases remain disabled, retention remains manual, rollback guidance is present, and `--no-workflow` remains available.
- Dependencies: none added or changed.

Phase 10 must prove hostile or malformed runtime input cannot mutate project
files, contact providers, weaken authority, falsify evidence/completion, leak
private material, break Planning Lock stop rules, or delete/upload retained data
without an explicit manual cleanup contract.

- Goal: Audit every Product Maturity phase PM-0 through PM-7 and PM-L0 through
  PM-L5 against its implementation, owning tests, CLI/MCP projection,
  packaging, release controls, and honest evidence boundary; repair every
  locally reproducible gap.
- Authority: the user's explicit phase-by-phase validation and fix request on
  2026-09-01 and `PRODUCT-MATURITY-IMPROVEMENT-PLAN.md`.
- Dependencies: none added or changed.
- Corrected gaps: added `debug-investigation` to the canonical workflow
  instance and real-run proof template sets; made the pre-target banner test
  deterministic in an empty workspace; documented all 24 canonical
  `intent-bridge` commands; replaced tab-separated Markdown with valid tables.
- Focused proof: 169 phase-owned maturity/runtime/facade/presentation/
  maintainability/evaluation/enterprise/adoption/learning/CLI tests passed in
  175.599 seconds. A separate 63-test package, installer, supply-chain, release,
  and continuous-governance slice passed in 74.844 seconds.
- Repository-wide proof: all 1,025 tests passed in 756.746 seconds with no
  failures, errors, skips promoted as passes, or exception list.
- Static gates: Product Maturity validation, strict Feature Registry,
  repository check, registry drift, public documentation audit, release check,
  enterprise closure validation, host adapter conformance, MCP doctor, all 171
  JSON Schema meta-validations, and Git diff hygiene passed.
- Evidence truth: PM-5 remains protocol-ready with 0/54 genuine observations;
  PM-6 has local/offline conformance but no hosted six-cell platform report;
  PM-7 has no genuine usability observations; PM-L5 is fixture-only. Those
  evidence exits cannot be closed by local implementation or synthetic data.
