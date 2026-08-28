# Changelog

All notable public release changes to TailTrail are recorded here.

TailTrail follows semantic versioning as described in `VERSIONING.md`.

## Unreleased

### Added

- Shared Question Orchestrator for Navigator, Lite AIDLC, and pinned official
  Standard/Full AIDLC. It persists a versioned question context, preserves the
  active AIDLC question authority, rejects duplicate or ungrounded questions,
  maps each decision to requirement IDs and downstream impacts, preserves the
  full official host traceability block through answers and approval, exposes
  read-only CLI/MCP inspection, and ships in Core and Extended host packs.

- Enterprise Stabilization Phase E4 host adapters: one closed v3 contract for
  exact Codex, GitHub Copilot, and Claude Core files, composition, native first
  actions, diagnostics, version limitations, CI-authoritative enforcement,
  approval-required external changes, transactional adapter migration, and
  sanitized six-scenario receipt preparation. Source and checkout-free wheel
  lifecycles cover all three hosts; Claude partial installs fail closed. The
  complete 748-test suite passes on CPython 3.12 and 3.13. These adapters are
  contract-tested, not runtime-observed or release-supported; E5-E12 remain
  gated.

- Enterprise Stabilization Phase E3 transactional installer lifecycle: one
  package-owned engine for Codex, Copilot, and Claude with versioned plans,
  per-host ownership manifests, durable journals and locks, zero-write dry run,
  hash-verified staging, atomic replacement, conflict fencing, mandatory
  backups for forced changes, automatic failure restoration, unclean-stop
  recovery, repair, deterministic update, rollback, safe uninstall, retention,
  and stable text/JSON/exit contracts. Installed-artifact tests and the complete
  741-test suite pass on both supported CPython versions, closing E3; E4-E12
  remain gated.

- Enterprise Stabilization Phase E2 self-contained package: an importable
  product kernel and stable API/CLI, CPython 3.12-3.13 support contract,
  explicit wheel/sdist inventory, full packaged-resource SHA-256 verification,
  versioned migration baseline, categorical exit/JSON errors, checkout-free
  dispatch, artifact hygiene/secret-path inspection, Core installer ownership,
  CI artifact gates, and isolated hello/doctor/planning/approval/recovery/
  evidence/closure proof with missing/corrupt negative tests. The complete
  723-test suite passes on both supported CPython versions, closing E2;
  E3-E12 remain gated.

- Enterprise Stabilization Phase E1 test and release truth: all registered test
  regressions fixed, root Navigator compatibility restored, one versioned
  release manifest and schema shared across release/audit/doctor/export/smoke/CI,
  explicit public-upstream and candidate-scope policy, missing community/demo
  files added, generated state isolated from smoke preflight, negative release
  fixtures added, and the complete 716-test suite restored with no exception
  list. This closes E1 only; E2-E12 remain gated at that historical checkpoint.

- Enterprise Stabilization Phase E0 baseline and ownership: a versioned
  enterprise closure registry and schema, strict read-only validator, complete
  command/schema/adapter/state/CI/install/release/support inventory projection,
  feature maturity normalization, active E0-E12 feature freeze, exact candidate
  baseline and untracked-file dispositions, 27 owned closure requirements, 12
  known defects, top-level CLI commands, Extended-pack coverage, comprehensive
  AIDLC artifacts, and positive/negative focused tests. E0 closes classification
  and ownership only; the release candidate remains blocked by E1-E12 gates.

- Durable Workflow Runtime Deferred Phase 12 optional enterprise adapter: a
  provider-neutral state-store protocol, dependency-free local conformance
  adapter, evidence-gated activation, tenant/actor/repository isolation,
  read-only cross-repository identities, monotonic leases, fencing tokens,
  ordered idempotent receipt transport, replay, sanitized observability,
  bounded backup/restore validation, exact migration/rollback, cost controls,
  CLI, MCP, schemas, installed-pack coverage, and host guidance. Local JSON
  remains canonical and default. No provider, model API, database, queue,
  container, background worker, upload, or automatic retry was introduced.

- Durable Workflow Runtime Deferred Phase 11 release proof: a closed 15-scenario
  portfolio, sanitized six-template local-run receipts, Codex/Copilot/Claude
  convergence, calibrated safety and token-coverage observations, read-only
  migration compatibility assessment, and a fail-closed release gate.

  `--no-workflow` remains available as the compatibility escape hatch. Even a
  passing release gate requires a separate exact-fingerprint retirement approval
  and later reviewed release change; Phase 11 does not migrate old history or
  remove compatibility automatically.

- Durable Workflow Runtime Deferred Phase 5 full template execution: six exact
  deterministic graphs; shortest-continuation status; typed start, finish, and
  skip controls; scoped stage, risk, saved-CI/scanner, and release boundaries;
  stable replay and terminal receipts; and six end-to-end fixtures covering
  completion, rejected-fix containment, read-only discovery, blocked provider
  input, failure, and explicit skip.

- Durable Workflow Runtime Deferred Phase 4 capability adapters: a closed
  eleven-adapter Feature Registry catalog; compiler-bound canonical action
  classes; approval-, scope-, and freshness-bound idempotent inputs; typed
  factual outputs; official AIDLC and graph-proof boundaries; public adapter
  CLI commands; installed schemas/modules; and negative contract tests for
  duplicate dispatch, missing evidence, raw output, arbitrary command
  construction, and authority mismatch.

- Durable Workflow Runtime Deferred Phase 3 approval enforcement: immutable
  run/target/graph/scope-bound decision records, guarded stage and explicit
  skip approval IDs, low-risk session/policy limits, pause/session/revision and
  policy/target invalidation, separate Dependency Gate authority, public CLI
  controls, installed-pack coverage, and adversarial approval tests.

- Hands-free Start requirement extraction now recognizes order-amendment work
  before preservation references. Prompts that say to preserve cancellation no
  longer drift into cancellation requirements; amendment eligibility, revision,
  concurrency, inventory/payment delta, audit, notification, contract,
  migration, and rollout evidence are represented explicitly. Full AIDLC
  escalation now states that a verified pack and a new Full-mode Planning Lock
  are required rather than implying an in-place Standard-to-Full upgrade.

- Real-host runtime conformance Phase J: portable six-scenario bundles for
  Codex, Copilot, and Claude; sanitized integrity-checked receipt intake;
  canonical-state probes; immutable ledger-linked evaluations; separate
  instruction/runtime status reporting; public CLI commands; read-only MCP
  inspection; installation packaging; registry metadata; and deterministic
  pass/fail/not-validated/stale/incompatible coverage.

- Official AI-DLC Phase I runtime attachment for Full mode: immutable session
  binding, sanitized ordered transition receipts, restart-safe stage
  projection, explicit resume/redo/jump/recovery actions, canonical-state and
  checkpoint gates, CLI commands, and read-only MCP session inspection. The
  adapter never executes arbitrary official-pack scripts.
- Evaluation Harness EH-2 command aliases through `python3 scripts/tailtrail.py eval ...`, backed by a thin router that delegates to existing evidence scripts while keeping scenario commands pending until EH-4.
- Evaluation Harness EH-3 shared event schema, `eval normalize`, and `eval validate-events` for approval-gated local evidence JSONL.
- Evaluation Harness EH-4 Scenario Harness V1 through `eval scenario list|run|compare|report`, with deterministic committed fixtures, rubric-backed scoring, and approval-gated report writes.
- Evaluation Harness EH-8 Build Week demo scenario through `eval scenario report --scenario buildweek-validation`, with deterministic fixture evidence linked to the live demo story and no live execution.
- Navigator-default task routing through `python3 scripts/tailtrail.py do "task"`, `python3 scripts/tailtrail.py run "task"`, and free-form `python3 scripts/tailtrail.py "task"` input.
- Semantic V3 code intelligence through `graph ast --depth v3 --provider-output ...`, ingesting approved local provider JSON for Java/JDT or language-server style exports, .NET/Roslyn-derived exports, richer Python analyzer output, SQL/Terraform parser output, SCIP-derived JSON, or repo-owned extractors.
- Start reports now include a compact Code Intelligence section explaining `lite`, `v1`, `v2`, V3 opt-in provider metadata, Navigator recommendation rules, and provider auto-run boundaries.
- Semantic V3 provider ingestion now requires explicit `--approved` or local `tailtrail-policy.md` enablement, and AST/Semantic maps emit normalized evidence labels plus an `evidence_summary`.
- Assistant compatibility hardening through `ASSISTANT-COMPATIBILITY.md`, assistant-specific prompt packs under `adapters/prompts/`, `tailtrail adapters check|sync`, and required adapter behavior contract validation.
- Registry drift checker through `python3 scripts/tailtrail.py registry drift`, covering registry validation, command documentation drift, stale roadmap wording, changelog freshness, and public-claim wording.
- Feature change checklist guidance for registry, docs, roadmap, changelog, tests, and install/check inventory updates.
- Measured evidence portfolio for efficacy scenarios across bug fix, review, security, CI/Sonar, dependency, feature, token-heavy artifact, and learning-governance task classes.
- Evaluation Harness EH-0 audit through `python3 scripts/tailtrail.py eval audit`, with canonical evidence-surface mapping, strict-mode validation, and approved report writing under `reports/evaluation-harness/`.

### Changed

- Efficacy reporting now includes portfolio coverage, scenario-class counts, evidence-label counts, and public-claim readiness.
- TailTrail pitch and public claims docs now distinguish single-scenario proof from portfolio evidence.
- Evaluation Harness documentation now treats `EVALUATION-HARNESS.md` as the implementation hub, with roadmap, user guide, and command catalog kept as shorter entry points.

### Validation

- `python3 scripts/check-tailtrail.py`
- `python3 scripts/tailtrail.py registry validate`
- `python3 scripts/tailtrail.py registry drift`
- `python3 scripts/tailtrail.py efficacy run --portfolio --strict`
- `python3 -m unittest discover tests`

## 0.6.0 - Public Release Candidate

### Added

- Local packaging metadata through `pyproject.toml` and a zero-dependency `tailtrail` console entry shim for `pipx install .` and `pip install --user .`.
- Measured efficacy proof runner through `python3 scripts/tailtrail.py efficacy run|report`, with committed benchmark fixtures, strict measured-vs-estimated token labeling, and CI coverage.
- CLI dispatch consolidation tests that enforce thin wrapper behavior for compatibility CLI files.
- Public release governance files: license, notice, security policy, contribution guide, code of conduct, public claims, and public release metadata.
- Public/private release mode separation with admin export commands.
- Public release readiness checks through `scripts/release-check.py`.
- TailTrail command surface centered on `python3 scripts/tailtrail.py start`.
- Navigator-first planning, AIDLC, guardrails, policy checks, graph mapping, quality scanning, vulnerability summarization, learning governance, value reporting, and measured-token boundaries.

### Changed

- User-facing docs now prefer the unified `python3 scripts/tailtrail.py ...` command surface for token budget, prompt profile, context receipt, and token telemetry workflows.
- Demo workspace user guide was re-synced with the unified command surface.
- Public document audit now flags user-facing documentation that advertises internal underscore module paths.
- Hyphenated wrapper files remain compatibility shims around canonical underscore importable modules and will be revisited only after packaging stabilizes.
- Public license metadata is now Apache-2.0 in `.codex-plugin/plugin.json`.
- Public scanner summaries redact common secret-like evidence and cap scanner report reads.
- Internal exports exclude public release, license, security, contribution, conduct, roadmap, and admin files.

### Security And Privacy

- TailTrail remains local-first and approval-first.
- TailTrail does not upload project code, prompts, logs, scanner output, token telemetry, learning history, or reports by default.
- Security reports should use the private reporting path described in `SECURITY.md`.

### Validation

- `python3 -m unittest tests.test_cli_dispatch tests.test_efficacy_run`
- `python3 scripts/public-doc-audit.py`
- `python3 -m unittest discover -s tests`
- `python3 scripts/tailtrail.py doctor`
- `TAILTRAIL_ADMIN=1 python3 scripts/tailtrail.py release-check`

### Known Limitations

- Host-profile transactional lifecycle and cross-platform qualification remain
  governed by Enterprise Phases E3-E5; the E2 wheel/sdist is available but does
  not claim those later host/platform gates.
- Exact token savings require user-provided measured model/API telemetry.
- TailTrail is scanner-aware but does not replace security scanners, CI, tests, review, or approval.
