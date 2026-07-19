# Honest Review Implementation Plan

Purpose: convert the findings from `HONEST-REVIEW.md` into an execution-ready plan for TailTrail V3 hardening.

This plan focuses on the review's strongest message: TailTrail has a good enterprise governance idea, but it needs more enforcement, simpler packaging, stronger proof, and clearer public positioning before it should be treated as a polished open-market product.

## Executive Direction

TailTrail should double down on one core lane:

```text
Trustworthy AI behavior governance for coding:
multi-assistant, local-first, approval-first, deterministic, and evidence-aware.
```

Token routing, AIDLC, scanner overlays, learning, reporting, and graphing remain valuable, but they should be presented as supporting capabilities. The default user experience should feel smaller than the full internal capability set.

## Current Diagnosis

The honest review identified three primary product gaps:

1. **Advisory-only governance**: TailTrail gives good instructions, but it does not yet enforce the highest-value rules.
2. **Large default surface**: TailTrail has many files, commands, phases, and terms, which can overwhelm new users.
3. **Limited real-world proof**: Benchmarks and reports exist, but stronger measured evidence is needed before making broad impact claims.

Recent work has already improved some of this:

- `start` gives a Navigator-first command.
- `setup-scan` handles cloned-repo hygiene.
- outcome telemetry and exact token telemetry exist.
- scanner graph overlays exist.
- release checks and adapter sync exist.
- local enterprise reports exist.

The remaining V3 work should therefore focus on enforcement, packaging clarity, task-first docs, measured evidence, and maintainability.

## Priority Model

Use this priority model when deciding what to implement first:

| Priority | Meaning | Examples |
|---|---|---|
| P0 | Needed before public pitch credibility | public claim guardrails, enforcement lite, start-first docs |
| P1 | Needed for enterprise confidence | CI guardrail gate, measured efficacy, Core/Extended split |
| P2 | Needed for maintainability | Navigator refactor, deterministic tests, governance text generation |
| P3 | Useful after adoption evidence | dashboard UI, PR bot, package-manager distribution |

## Phase V3.0: Public Claim Guardrails

Goal: prevent TailTrail from overclaiming what it can do.

Status: implemented. TailTrail now includes `PUBLIC-CLAIMS.md`, release-check scanning for unsupported public claims, and public docs that describe the claim boundary.

Why this matters:

- Public/enterprise buyers will distrust a tool that claims exact token savings, security replacement, compliance automation, or guaranteed code quality without evidence.
- TailTrail's credibility comes from careful boundaries. Public docs must show the same discipline that TailTrail asks agents to follow.

Implementation:

- Add `PUBLIC-CLAIMS.md`. Implemented.
- Define allowed, cautious, and disallowed claims. Implemented.
- Extend `scripts/release-check.py` to scan public-facing docs for risky phrases. Implemented.
- Keep the scanner simple and deterministic.
- Add a release-check allowlist for quoted examples or deliberately documented anti-patterns.

Suggested files:

- `PUBLIC-CLAIMS.md`
- `scripts/release-check.py`
- `scripts/check-tailtrail.py`
- `README.md`
- `USER-GUIDE.md`
- `ROADMAP.md`
- `DESIGN.md`

Command surface:

```bash
python3 scripts/tailtrail.py release-check
```

Acceptance:

- Release check fails on unsupported phrases such as "guaranteed token savings", "replaces security review", "fully automatic compliance", and "exact savings" when no measured telemetry wording is present.
- README and guide language consistently uses cautious words such as "helps", "recommends", "estimates", "approval-first", and "local evidence".
- The check does not block legitimate documentation that says TailTrail does **not** replace scanners, tests, CI, or review.

Do not build yet:

- marketing-site claim scanner
- remote policy service
- central compliance approval workflow

## Phase V3.1: Enforcement Lite

Goal: give TailTrail's most important guardrails practical teeth without turning the project into a heavy governance platform.

Status: implemented for the first local deterministic slice. `scripts/guardrail-check.py` and `python3 scripts/tailtrail.py guard check` now provide advisory and `--enforce` modes for dependency gate evidence, safeguard removal review, validation claim evidence, and staged local TailTrail runtime state.

Why this matters:

- The honest review's lowest score was enforcement.
- Enterprise teams need at least optional local checks that can block obvious AI-assisted mistakes.
- Enforcement should stay local, deterministic, opt-in, and explainable.

Implementation:

- Add `scripts/guardrail-check.py`. Implemented.
- Add `python3 scripts/tailtrail.py guard check`. Implemented.
- Support advisory mode by default. Implemented.
- Support blocking mode with `--enforce`. Implemented.
- Read staged diff through `git diff --cached` when no diff file is supplied. Implemented.
- Support `--diff path/to.patch` for CI and testing. Implemented.
- Support `--commit-message path/to/message.txt` and `--pr-body path/to/body.md` for validation-claim checks. Implemented.

First checks:

- **Dependency gate check**: flag new or changed dependency manifest entries without a Dependency Gate note or approval marker.
- **Safeguard removal check**: flag removed lines that look like validation, auth, authorization, escaping, rate limit, logging, migration safety, or test coverage.
- **Validation truth check**: flag claims such as "tests passed", "verified", "deployed", or "validated" without command/result evidence.
- **Local TailTrail state check**: flag staged `.tailtrail/*state*.json`, `*events*.jsonl`, `*scores*.jsonl`, run-output folders, or local telemetry files.

Suggested files:

- `scripts/guardrail-check.py`
- `scripts/tailtrail.py`
- `templates/guardrail-finding.md`
- `hooks/guardrail-pre-commit-hook.py`
- `USER-GUIDE.md`
- `TAILTRAIL-COMMANDS.md`
- `ROADMAP.md`
- `DESIGN.md`
- `scripts/check-tailtrail.py`

Command surface:

```bash
python3 scripts/tailtrail.py guard check
python3 scripts/tailtrail.py guard check --diff changes.patch
python3 scripts/tailtrail.py guard check --diff changes.patch --format json
python3 scripts/tailtrail.py guard check --enforce
```

Acceptance:

- Advisory mode prints findings but exits successfully.
- Enforce mode exits non-zero for high-severity findings.
- Every finding includes file/path, evidence line, rule name, severity, and recommended fix.
- A dependency added without a gate note is flagged.
- A validation claim without evidence is flagged.
- Local TailTrail runtime state staged for commit is flagged.
- False positives are conservative enough that TailTrail can use the check in its own CI after review.

Do not build yet:

- PR bot
- hosted policy service
- AI-based diff judgment
- automatic code modification
- pre-commit hook installation; a sample hook can be added in a later slice after teams review false-positive behavior

## Phase V3.2: CI Guardrail Gate

Goal: make the local enforcement engine usable by teams in shared pull request workflows.

Why this matters:

- Local hooks are useful but optional.
- CI gives teams a shared minimum standard without relying on each developer's local setup.

Implementation:

- Reuse `scripts/guardrail-check.py`.
- Add `.github/workflows/tailtrail-guard.yml`.
- Run against PR diff or staged-equivalent input.
- Fail only on high-severity checks in `--enforce` mode.
- Keep the workflow dependency-free.
- Let repos configure severity/allowlist through `.tailtrail/policy-overrides.json`.

Suggested files:

- `.github/workflows/tailtrail-guard.yml`
- `scripts/guardrail-check.py`
- `templates/evidence-note.md`
- `USER-GUIDE.md`
- `TAILTRAIL-COMMANDS.md`
- `README.md`

Acceptance:

- CI can fail a PR that adds a dependency without a gate note.
- CI can fail a PR that includes unverified validation claims.
- Trivial docs-only changes are not forced through heavy evidence requirements.
- The workflow remains opt-in for target repos.

Do not build yet:

- GitHub App
- PR comment bot
- required-status automation across organizations

## Phase V3.3: Core And Extended Pack Split

Goal: reduce the perceived default surface without deleting useful capabilities.

Why this matters:

- TailTrail is powerful, but a new user should not need to understand every feature on day one.
- Core should solve the first 80 percent of daily governance needs.
- Extended should remain available for teams that need AIDLC, graphing, learning, reporting, scanners, and benchmarks.

Core should include:

- `README.md`
- `USER-GUIDE.md`
- `AGENTS.md`
- `GUARDRAILS.md`
- `DEPENDENCY-GATE.md`
- `tailtrail-policy.example.md`
- `scripts/tailtrail.py`
- `scripts/navigator.py`
- `scripts/policy-check.py`
- `scripts/guardrail-check.py`
- one selected adapter for the target assistant

Extended should include:

- AIDLC pack
- Token Router and Token Autopilot
- Code Review Graph Lite
- Code Graph Mapper
- AST maps
- scanner summaries and overlays
- Learning Agent V2
- Quality Loop
- Enterprise Reporting
- Benchmark Harness
- multi-assistant adapter set

Implementation:

- Add a pack manifest that classifies files as `core`, `extended`, or `dev`.
- Update installers to default to Core.
- Add `--extended` for full feature install.
- Keep existing full installs backward compatible.
- Navigator should gracefully say when an Extended feature is unavailable.

Suggested files:

- `tailtrail-pack.json`
- `scripts/install-local.py`
- `scripts/install-copilot.py`
- `scripts/update-tailtrail.py`
- `scripts/check-tailtrail.py`
- `README.md`
- `USER-GUIDE.md`
- `DESIGN.md`

Acceptance:

- A default install produces a small understandable footprint.
- Extended install remains one flag away.
- Existing installed packs keep updating safely.
- Docs clearly explain Core vs Extended.

Do not build yet:

- package-manager distribution
- binary installer
- separate repository split

## Phase V3.4: Task-First Documentation

Goal: make TailTrail understandable by user goal, not by internal phase history.

Status: implemented. TailTrail now includes `QUICKSTART.md`, `CHEATSHEET.md`, a task-first README opening, and user-guide links that make `start` the dominant first command.

Why this matters:

- Users do not think in TailTrail phases.
- They think in tasks: fix a bug, review a diff, handle Sonar, handle vulnerability, avoid hallucinated tests, keep changes small.

Implementation:

- Add `QUICKSTART.md`. Implemented.
- Add `CHEATSHEET.md`. Implemented.
- Rewrite the top of `README.md` around outcomes. Implemented.
- Keep phase history in `ROADMAP.md` and `DESIGN.md`, not as the first public path. Implemented.
- Make `start` the dominant first command. Implemented.

Task map:

| User problem | First command |
|---|---|
| I have a task | `python3 scripts/tailtrail.py start "goal"` |
| I only want a plan | `python3 scripts/tailtrail.py guide "goal"` |
| I have a diff to review | `python3 scripts/tailtrail.py graph --changed path` |
| I have CI logs | `python3 scripts/tailtrail.py ci summarize --file ci.log` |
| I have Sonar output | `python3 scripts/tailtrail.py sonar summarize --file sonar.log` |
| I have vulnerability output | `python3 scripts/tailtrail.py vulnerability summarize --file audit.log` |
| I want scanner impact | `python3 scripts/tailtrail.py graph overlay --sonar sonar.log --changed path` |
| I want enforcement | `python3 scripts/tailtrail.py guard check` |

Suggested files:

- `QUICKSTART.md`
- `CHEATSHEET.md`
- `README.md`
- `USER-GUIDE.md`
- `TAILTRAIL-COMMANDS.md`
- `DESIGN.md`
- `scripts/check-tailtrail.py`

Acceptance:

- A new reader can find the right command for a concrete task in under one minute.
- README no longer feels like an inventory of everything TailTrail can do.
- Advanced commands remain discoverable but not front-loaded.

Do not build yet:

- interactive terminal wizard
- GUI onboarding

## Phase V3.5: Measured Efficacy Evidence

Goal: prove TailTrail helps using reproducible evidence, not just synthetic benchmark scores or product intuition.

Status: implemented for artifact-based local evidence. TailTrail now includes `scripts/efficacy-benchmark.py`, a committed `benchmarks/efficacy/governance-remediation/` scenario, `templates/efficacy-result.md`, and `python3 scripts/tailtrail.py benchmark efficacy`.

Why this matters:

- Enterprise pitch needs proof.
- Token savings and review quality claims must be measured or clearly marked as estimates.

Implementation:

- Add a reproducible efficacy benchmark that consumes captured artifacts. Implemented.
- Do not call live models from the benchmark. Implemented.
- Compare baseline artifact vs TailTrail-guided artifact. Implemented.
- Record:
  - dependency added or avoided
  - validation claim with evidence or without evidence
  - safeguard preserved or weakened
  - diff size
  - review finding quality
  - measured token telemetry when supplied
- Generate a report with measured vs estimated labels. Implemented for measured telemetry and no-telemetry claim boundaries.

Suggested files:

- `scripts/efficacy-benchmark.py`
- `benchmarks/efficacy/`
- `templates/efficacy-result.md`
- `scripts/token-savings.py`
- `scripts/tailtrail-report.py`
- `README.md`
- `ROADMAP.md`

Acceptance:

- A skeptical reviewer can reproduce the benchmark from committed inputs.
- Reports never claim exact token savings without measured telemetry.
- Results include enough detail to explain what improved and what did not.

Do not build yet:

- live model runner
- public leaderboard
- dollar ROI calculator without user-supplied pricing

## Phase V3.6: Navigator Refactor And Deterministic Tests

Goal: reduce maintenance risk and make deterministic behavior testable.

Status: implemented. Navigator now has a separated deterministic core and renderer, golden Markdown coverage for repo overview output, task-start wrapping tests, and package validation for the new files.

Why this matters:

- `navigator.py` is a critical orchestration layer.
- As more features route through Navigator, a monolith becomes harder to reason about.
- Deterministic Python helpers deserve deterministic tests.

Implementation:

- Split Navigator behavior into internal modules while preserving the CLI:
  - goal classification. Implemented in `scripts/navigator_core.py`.
  - risk detection. Implemented in `scripts/navigator_core.py`.
  - feature selection. Partly implemented through tested core helpers while final orchestration remains in `scripts/navigator.py`.
  - learning integration. Kept in `scripts/navigator.py`; future candidate for a small adapter if the file grows again.
  - graph integration. Kept in `scripts/navigator.py`; future candidate for a small adapter if the file grows again.
  - rendering. Implemented in `scripts/navigator_render.py`.
- Remove stale duplicate Navigator keyword tables/helpers from `scripts/navigator.py`. Implemented.
- Add Python `unittest` tests with fixtures. Implemented.
- Cover:
  - Navigator task classification. Implemented.
  - repo overview golden Markdown rendering. Implemented.
  - task-start wrapping of Navigator decisions. Implemented.
  - intent expansion. Implemented.
  - policy check. Implemented.
  - guardrail check. Implemented.
  - scanner overlay parsing. Future candidate for broader fixture coverage.
  - setup scan classification. Future candidate for broader fixture coverage.
  - token savings measured vs estimated boundaries. Future candidate for broader fixture coverage.
- Wire tests into public CI. Implemented through the manual TailTrail CI workflow.

Suggested files:

- `scripts/navigator_core.py`
- `scripts/navigator_render.py`
- `scripts/navigator.py`
- `tests/`
- `tests/golden/navigator_repo_overview.md`
- `.github/workflows/tailtrail-ci.yml`
- `scripts/check-tailtrail.py`
- `V2-IMPLEMENTATION-GUIDE.md`

Acceptance:

- External Navigator command behavior remains stable.
- Tests run without third-party dependencies.
- CI runs the deterministic test suite.
- New implementation files require either tests or an explicit documented reason.

Do not build yet:

- external test framework dependency
- snapshot tests that are too brittle to maintain
- deep adapter split for graph/cache/learning integrations until Navigator growth justifies it

## Phase V3.7: Single-Source Governance Text

Goal: reduce drift across `GUARDRAILS.md`, `AGENTS.md`, adapters, and guardrail layers.

Status: implemented.

Why this matters:

- Duplicated governance language can drift.
- Tool-specific files need different formats, but the core behavioral contract should remain consistent.

Implementation:

- Treat `GUARDRAILS.md` as the full behavior contract.
- Treat `GOVERNANCE.md` as the single source for the compact repeated governance block.
- Use explicit marker comments to sync only repeated governance text in `AGENTS.md`, adapter sources, and `context/guardrail-layers.md`.
- Keep generated outputs human-readable.
- Avoid making every doc generated; only generate or validate repeated governance blocks.

Implemented:

- Added `GOVERNANCE.md`.
- Added `scripts/sync-governance.py check|sync`.
- Added `python3 scripts/tailtrail.py governance check|sync`.
- Added governance drift validation to `scripts/check-tailtrail.py` and `doctor`.
- Added governance files to the Copilot pack installer.
- Synced adapter sources and generated adapter targets.

Suggested files:

- `scripts/sync-governance.py`
- `scripts/sync-adapters.py`
- `GUARDRAILS.md`
- `AGENTS.md`
- `context/guardrail-layers.md`
- `adapters/`
- `scripts/check-tailtrail.py`

Acceptance:

- CI/check-tailtrail catches adapter or guardrail-layer drift.
- Updating a canonical repeated rule has a predictable sync path.
- Human-readable docs remain pleasant to edit.

Do not build yet:

- full docs generation framework
- generated README
- hidden policy compiler

## Phase V3.8: Value Surface And Reporting Maturity

Goal: make TailTrail's value visible from local evidence.

Status: implemented.

Why this matters:

- A good governance tool should show what it prevented or improved.
- Enterprises need evidence, but TailTrail must avoid surveillance.

Implementation:

- Extend Enterprise Reporting with:
  - guardrail findings caught
  - dependencies avoided or gated
  - safeguards preserved
  - validation truth issues caught
  - acceptance/revision rates
  - measured token savings when supplied
  - learning hygiene trend
- Add CSV export.
- Add month-over-month comparison from explicitly supplied local reports.
- Keep all data local and opt-in.

Implemented:

- Added `report value` to `scripts/tailtrail-report.py`.
- Added CSV output for value and enterprise reports.
- Added local comparison through `report compare --previous-report ... --current-report ...`.
- Added `templates/value-report.csv`.
- Added deterministic tests for value-surface and comparison calculations.
- Updated `TAILTRAIL-COMMANDS.md`, `USER-GUIDE.md`, `README.md`, `DESIGN.md`, and `ROADMAP.md`.

Suggested files:

- `scripts/tailtrail-report.py`
- `templates/enterprise-report.md`
- `templates/value-report.csv`
- `USER-GUIDE.md`
- `TAILTRAIL-COMMANDS.md`

Acceptance:

- Teams can show governance outcomes without uploading data. Implemented.
- Reports distinguish measured, estimated, and advisory numbers. Implemented.
- No raw prompt history is required. Implemented.

Do not build yet:

- web dashboard
- central telemetry service
- hidden user behavior scoring

## Phase V3.9: Public Packaging Discipline

Goal: make release and update behavior boring, predictable, and understandable.

Why this matters:

- Public users need version clarity.
- Enterprise users need safe updates and changelog discipline.

Implementation:

- Add `CHANGELOG.md`.
- Define versioning rules.
- Tag releases only after release-check passes.
- Keep source install as the first public release path.
- Add package-manager options later only after real demand.

Suggested files:

- `CHANGELOG.md`
- `RELEASE-CHECKLIST.md`
- `scripts/release-check.py`
- `README.md`
- `USER-GUIDE.md`

Acceptance:

- A user can tell what changed between versions.
- Update guidance is clear.
- Public release claims are tied to release checks.

Do not build yet:

- Homebrew formula
- OS installer
- hosted update service

## Implementation Order

Recommended sequence:

1. V3.0 Public Claim Guardrails.
2. V3.1 Enforcement Lite.
3. V3.4 Task-First Documentation.
4. V3.2 CI Guardrail Gate.
5. V3.3 Core And Extended Pack Split.
6. V3.5 Measured Efficacy Evidence.
7. V3.6 Navigator Refactor And Deterministic Tests. Implemented.
8. V3.7 Single-Source Governance Text. Implemented.
9. V3.8 Value Surface And Reporting Maturity. Implemented.
10. V3.9 Public Packaging Discipline.

Reasoning:

- Claim guardrails and enforcement improve trust immediately.
- Task-first docs make the existing product easier to use before deeper packaging changes.
- CI gate turns local enforcement into team governance.
- Core/Extended split becomes easier once docs and enforcement clarify the core lane.
- Measured evidence and reporting maturity make the product pitch stronger.
- Refactor and single-source governance reduce long-term maintenance burden.

## Success Metrics

- A new user can start with `python3 scripts/tailtrail.py start "goal"` in under one minute.
- Public docs do not make unsupported claims.
- Guardrail checks catch high-value violations in advisory and enforce modes.
- Default install footprint is smaller and easier to explain.
- At least one reproducible measured-efficacy benchmark exists.
- Navigator behavior has deterministic tests.
- Governance text drift is caught by CI.
- Enterprise reports show local evidence without uploading data.

## Decision Boundaries

TailTrail should continue to avoid these until user demand and privacy/security review justify them:

- hosted telemetry
- background observer service
- PR bot as the first enforcement layer
- vector database
- hidden model calls
- automatic code modification from quality reports
- package-manager distribution before source release is stable
- exact ROI claims without measured usage and user-supplied pricing
