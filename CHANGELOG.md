# Changelog

All notable public release changes to TailTrail are recorded here.

TailTrail follows semantic versioning as described in `VERSIONING.md`.

## Unreleased

### Added

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

- First public release is source-only.
- Exact token savings require user-provided measured model/API telemetry.
- TailTrail is scanner-aware but does not replace security scanners, CI, tests, review, or approval.
