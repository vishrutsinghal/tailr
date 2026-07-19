# TailTrail V2 Implementation Guide

This file is the execution checklist for TailTrail Version 2. It collects the remaining roadmap items into phase-by-phase implementation work so each feature can be completed end to end before moving to the next phase.

Use this file as the V2 working backlog. Keep `ROADMAP.md` as the full historical source of truth.

## V2 Rules

- Complete one phase end to end before starting the next.
- Keep implementation local, deterministic, and Python standard-library first.
- Keep every write action explicit and reviewable.
- Do not add hidden telemetry, background services, automatic prompt capture, or automatic scanner execution.
- Do not claim exact token savings without measured provider usage.
- Do not claim TailTrail replaces tests, review, CI, SAST, dependency scanners, legal review, or security review.
- Every new implementation file must be added to `scripts/check-tailtrail.py`.
- Every user-facing command must be documented in `TAILTRAIL-COMMANDS.md` and `USER-GUIDE.md`.
- Every public-release feature must pass `python3 scripts/tailtrail.py release-check`.

## Phase V2.0: Public Release Baseline

Goal: make TailTrail safe and credible for open-market evaluation.

Priority: highest.

### V2.0.1 Public CI

Status: implemented.

Implement:

- Add `.github/workflows/tailtrail-ci.yml`. Completed.
- Run on pull requests and pushes to `main`. Completed.
- Use system Python on `ubuntu-latest`. Completed.
- Run the public validation suite. Completed:
  - `python3 scripts/check-tailtrail.py`
  - `python3 scripts/tailtrail.py release-check`
  - `python3 scripts/sync-adapters.py --check`
  - `python3 -m compileall -q scripts hooks`
- Keep CI dependency-free. Completed.

Implemented files:

- `.github/workflows/tailtrail-ci.yml`
- `scripts/check-tailtrail.py` expected-file validation for the workflow.

Acceptance:

- CI requires no secrets. Completed.
- CI catches package shape failures. Completed.
- CI catches release hygiene failures. Completed.
- CI catches adapter drift. Completed.
- CI catches Python syntax errors. Completed.

Remaining:

- None for V2.0.1. Future CI expansion can add smoke tests after `scripts/smoke-test.py` exists in V2.0.2.

Validation:

```bash
python3 scripts/check-tailtrail.py
python3 scripts/tailtrail.py release-check
python3 scripts/sync-adapters.py --check
python3 -m py_compile scripts/*.py hooks/*.py
```

### V2.0.2 Fresh Clone Smoke Test

Implement:

- Add `scripts/smoke-test.py`.
- Use only Python standard library.
- Create a temporary clean test location.
- Run core commands from a clean checkout shape:
  - `python3 scripts/tailtrail.py help`
  - `python3 scripts/tailtrail.py start "fix Sonar issue" --changed missing-file.py`
  - `python3 scripts/tailtrail.py graph --changed scripts/tailtrail.py`
  - `python3 scripts/tailtrail.py quality scan --root .`
  - `python3 scripts/tailtrail.py release-check`
  - `python3 scripts/tailtrail.py doctor`
- Assert no command needs network, secrets, global install, or generated local state.

Acceptance:

- Smoke test passes from a fresh checkout.
- Missing changed files do not crash first-run flow.
- Smoke test is included in CI.

Validation:

```bash
python3 scripts/smoke-test.py
```

### V2.0.3 Changelog And Version Policy

Implement:

- Add `CHANGELOG.md`.
- Add `VERSIONING.md` or add a versioning section to `RELEASE-CHECKLIST.md`.
- Document semantic versioning:
  - patch: docs, checks, small script fixes
  - minor: compatible feature or command
  - major: breaking command behavior, install layout, or file contract
- Document version source of truth:
  - `.codex-plugin/plugin.json`
  - `CHANGELOG.md`
  - release tag
- Add release note template sections:
  - Added
  - Changed
  - Fixed
  - Security and privacy
  - Migration notes
  - Validation run

Acceptance:

- A user can tell what changed between releases.
- Maintainers know how to bump versions.
- Release checklist includes version alignment.

### V2.0.4 Issue And Pull Request Templates

Implement:

- Add `.github/ISSUE_TEMPLATE/bug_report.md`.
- Add `.github/ISSUE_TEMPLATE/feature_request.md`.
- Add `.github/ISSUE_TEMPLATE/docs_feedback.md`.
- Add `.github/ISSUE_TEMPLATE/security_note.md`.
- Add `.github/pull_request_template.md`.

Bug report fields:

- TailTrail version or commit
- command run
- expected behavior
- actual behavior
- operating system
- Python version
- whether generated `.tailtrail/` files are involved
- redacted output

Pull request fields:

- purpose
- changed files
- user-facing behavior
- validation commands
- skipped checks
- privacy or security impact
- release note needed yes/no

Acceptance:

- Issue templates avoid asking for secrets, raw logs, PII, PHI, customer data, or private code.
- Security issue template redirects sensitive reports to `SECURITY.md`.
- PR template requires validation evidence.

### V2.0.5 Security Reporting Finalization

Implement:

- Replace temporary security reporting language in `SECURITY.md`.
- Choose one public path:
  - private vulnerability reporting on the repository host
  - maintained security email
  - another approved private channel
- Update `RELEASE-CHECKLIST.md`.
- Update `scripts/release-check.py` to fail if placeholder security language returns.

Acceptance:

- Sensitive reports have a private path.
- Public issue templates do not collect exploit details or secrets.
- Release check blocks placeholder security contact text.

### V2.0.6 License And Provenance Finalization

Implement:

- Confirm final license and copyright owner.
- Confirm whether Apache-2.0 remains the intended license.
- Update `LICENSE` if needed.
- Update `.codex-plugin/plugin.json`.
- Update `NOTICE.md`.
- Confirm no vendored third-party source, docs, generated brand systems, or copied external material exists.

Acceptance:

- License metadata is consistent.
- Provenance is accurate.
- Release checklist includes license confirmation.

### V2.0.7 Public Claim Guardrails

Implement:

- Add `PUBLIC-CLAIMS.md`.
- Define allowed claims:
  - local-first
  - approval-first
  - assistant-agnostic guidance
  - token-aware context reduction estimates
  - measured token savings only with real telemetry
  - scanner-aware, not scanner replacement
- Define disallowed claims:
  - guaranteed token savings
  - guaranteed code quality improvement
  - replaces security review
  - replaces CI, SAST, dependency scanners, or tests
  - autonomous self-healing
  - automatic enterprise compliance
- Extend `scripts/release-check.py` to flag risky public claims.

Acceptance:

- README, demo, release notes, and reports use cautious language.
- Release check catches obvious unsupported claims.

### V2.0.8 Public Documentation Sanitizer

Implement:

- Extend `scripts/release-check.py` or add `scripts/public-doc-audit.py`.
- Scan Markdown, JSON, YAML, and Python comments for:
  - internal-only language
  - private organization names
  - private repo URLs
  - secret-like values
  - placeholder security contact text
  - unsupported exact token-saving claims
  - statements implying TailTrail replaces scanners, security review, code review, or legal review
- Add the sanitizer to CI.

Acceptance:

- Public docs can be audited before release.
- Direct public repository references are blocked.
- Unsupported public claims are blocked.

## Phase V2.1: One-Command User Experience

Goal: make `start` the obvious entry point for every non-trivial task.

Priority: highest.

Status: implemented for the V2.1 first-command polish slice.

Implement:

- Update README so `start` is the first task command. Completed.
- Update `USER-GUIDE.md` so new users run `start` before learning feature-specific commands. Completed.
- Update `TAILTRAIL-COMMANDS.md` with a command decision table. Completed:
  - "I have a task" -> `start`
  - "I only want a plan" -> `guide`
  - "I know changed files" -> `graph`
  - "I have logs" -> `ci summarize` or `sonar summarize`
  - "I want checks" -> `quality scan`
  - "I want public release validation" -> `release-check`
  - "I cloned a repo with TailTrail files" -> `setup-scan`
- Tighten `scripts/task-start.py` output. Completed:
  - show next action at top and bottom
  - separate approve/edit/scan/validate recommendations
  - mark heavy optional commands clearly
  - keep estimated token savings wording cautious
- Add Navigator benchmark scenario for `start` workflow selection. Completed.
- Consider `tailtrail.py next` only after user testing shows continuation guidance is needed. Deferred.

Implemented files:

- `scripts/task-start.py`
- `TAILTRAIL-COMMANDS.md`
- `USER-GUIDE.md`
- `README.md`
- `benchmarks/scenarios/start-command-ux/scenario.md`
- `benchmarks/scenarios/start-command-ux/baseline-output.md`
- `benchmarks/scenarios/start-command-ux/tailtrail-output.md`
- `benchmarks/scenarios/start-command-ux/expected.json`
- `scripts/check-tailtrail.py`

Implementation design:

- `start` stays read-only and approval-first.
- `scripts/task-start.py` calls Navigator and then adds a focused Start report.
- The report begins with `Start Here`, so a new user sees the immediate next step before the full plan.
- The report includes a `Decision Menu` with copyable prompts for review, approve, edit, scan approval, learning approval, and leaner workflow.
- Scan approval appears only when the Navigator plan includes scanner-sensitive work.
- Learning approval appears only when graph-aware learnings are surfaced.
- The token posture remains a cautious character-count estimate and must not be used as exact model/API telemetry.

Example:

```bash
python3 scripts/tailtrail.py start "fix Sonar cognitive complexity issue" --changed src/main/java/com/acme/payment/PaymentValidator.java
```

Expected behavior:

- TailTrail returns a plan before implementation.
- The user sees selected features, skipped features, likely impacted files, and suggested validation.
- The user can approve the plan, edit the plan, approve exactly one scanner command, choose whether to use learnings, or make the workflow leaner.
- No code, scanners, learnings, quality events, or implementation steps run automatically.

Acceptance:

- A new user can reach a useful plan in under one minute.
- The user can tell whether to approve, edit, scan, validate, or skip heavy process.
- README does not show too many equal first-step alternatives.
- Advanced commands remain documented but secondary.

Remaining:

- `tailtrail.py next` is intentionally not implemented. Add it later only if users need continuation help after `start`.
- `setup-scan` remains in V2.2 because cloned-repo TailTrail hygiene is a separate flow.

Validation:

```bash
python3 scripts/tailtrail.py start "fix Sonar issue" --changed scripts/tailtrail.py
python3 scripts/tailtrail.py start "fix Sonar issue" --changed scripts/tailtrail.py --format json
python3 scripts/benchmark-tailtrail.py --scenario start-command-ux
```

## Phase V2.2: Clone Setup Hygiene And Shared Context Detection

Goal: let a new user safely understand TailTrail files already present in a cloned repo.

Priority: high.

Status: implemented for the first read-only setup hygiene scanner.

Implement:

- Add `scripts/setup-scan.py`. Completed.
- Add `python3 scripts/tailtrail.py setup-scan --root .`. Completed.
- Add `templates/tailtrail-gitignore.md`. Completed.
- Update `USER-GUIDE.md` with "Using TailTrail In A Cloned Repo". Completed.
- Update `TAILTRAIL-COMMANDS.md`. Completed.
- Update `scripts/check-tailtrail.py`. Completed.

Classifier categories:

- shared project context
- project overrides
- installed TailTrail pack
- local runtime state
- generated-but-shareable metadata
- unknown TailTrail-like files

Shared project files:

```text
AGENTS.md
tailtrail-policy.md
.tailtrail/policy-overrides.json
aidlc-docs/
.tailtrail/learnings.md
.tailtrail/learning-index.md
.tailtrail/graph-learning-index.json
```

Team-review files:

```text
tailtrail-meta/code-graph-cache.json
.github/copilot-instructions.md
.cursor/rules/tailtrail.mdc
.openai/chatgpt-instructions.md
CLAUDE.md
GEMINI.md
```

Local state files:

```text
.tailtrail/*state*.json
.tailtrail/*events*.jsonl
.tailtrail/*scores*.jsonl
.tailtrail/quality-runs/
.tailtrail/vulnerability-runs/
.tailtrail/token-usage.jsonl
.tailtrail/enterprise-report.md
.tailtrail/task-starts/
tailtrail/.tailtrail-install.json
```

Default behavior:

- Preserve shared files.
- Preserve overrides.
- Warn on local state.
- Recommend `.gitignore` entries.
- Recommend policy check.
- Recommend update dry-run for installed packs.
- Do not write unless the user explicitly asks.

Acceptance:

- `setup-scan` produces Markdown and JSON.
- New user can tell what is shared versus local.
- Existing overrides are not overwritten.
- Runtime state is flagged.
- Recommended next commands are shown.
- `.gitignore` recommendations are shown without editing `.gitignore`.
- Installed packs are pointed to dry-run update commands.

Boundaries:

- No files are installed, updated, moved, deleted, ignored, or rewritten.
- No automatic cleanup is performed.
- No remote policy or central registry is consulted.
- Unknown TailTrail-like files are surfaced for manual review.

Validation:

```bash
python3 scripts/tailtrail.py setup-scan --root .
python3 scripts/tailtrail.py setup-scan --root . --format json
python3 scripts/tailtrail.py setup-scan --root . --tracked-only
```

## Phase V2.3: Adoption Evidence And Outcome Telemetry

Goal: provide real local adoption evidence without surveillance.

Priority: high.

Status: implemented for the first opt-in local outcome telemetry layer.

Implement:

- Add outcome capture to existing Quality Loop or add `scripts/outcome-capture.py` if a separate tool is clearer. Completed as separate `scripts/outcome-telemetry.py`.
- Capture only compact approved events. Completed with `--approved`.
- Suggested event fields:
  - task id
  - task type
  - workflow selected
  - user acceptance
  - validation outcome
  - review outcome
  - defect escaped yes/no
  - estimated time-saved band
  - TailTrail fit: too heavy, too light, correct
  - notes, redacted and optional
- Update `scripts/tailtrail-report.py` to include outcome metrics. Completed.
- Add privacy and retention guidance. Completed in docs and command output.
- Add templates for task outcome events if needed. Completed with `templates/outcome-event.md`.

Acceptance:

- Capture is opt-in.
- No raw prompts are captured by default.
- Reports include outcomes, not just usage.
- Teams can show adoption evidence locally.
- Setup scan flags outcome event files as local runtime state.

Validation:

```bash
python3 scripts/tailtrail.py outcome capture --task-type bug-fix --workflow start,review --acceptance accepted --validation-outcome pass --review-outcome approved --defect-escaped no --time-saved 30-60m --fit correct --learning-quality trusted --approved
python3 scripts/tailtrail.py outcome summarize --month 2026-07
python3 scripts/tailtrail.py outcome summarize --month 2026-07 --format json
python3 scripts/tailtrail.py report --month 2026-07
```

## Phase V2.4: Exact Token Usage Path

Goal: allow exact measured token reports when users supply real usage telemetry.

Priority: high.

Status: implemented for the first measured token telemetry path.

Implement:

- Add `templates/token-usage-example.jsonl` with fake measured values. Completed.
- Document `.tailtrail/token-usage.jsonl` schema:
  - task id
  - provider
  - model
  - baseline input/output tokens
  - TailTrail input/output tokens
  - source of measurement
  - date
  - confidence/evidence level
- Update `TOKEN-SLICER.md`, `USER-GUIDE.md`, and `TAILTRAIL-COMMANDS.md`. Completed.
- Improve `scripts/token-savings.py` error messages for missing or malformed telemetry. Completed with ignored-record reasons.
- Add measured telemetry sample test path. Completed.
- Keep provider adapters deferred until privacy review. Deferred.

Acceptance:

- Estimated reports and measured reports are visually distinct.
- Exact savings are impossible to claim without measured telemetry.
- A user can create a valid telemetry JSONL from docs.

Validation:

```bash
python3 scripts/tailtrail.py savings estimate --used README.md --avoided ROADMAP.md
python3 scripts/tailtrail.py savings report --telemetry templates/token-usage-example.jsonl
python3 scripts/tailtrail.py savings report --telemetry templates/token-usage-example.jsonl --format json
python3 scripts/tailtrail.py report --token-telemetry templates/token-usage-example.jsonl
```

## Phase V2.5: Guarded Learning UX

Goal: keep learning useful, curated, and safe.

Priority: high.

Status: implemented for the first guarded learning UX slice.

Implement:

- Add `LEARNING-GOVERNANCE.md`. Completed.
- Add `python3 scripts/tailtrail.py learn review`. Completed.
- Wrap existing refresh and prune commands into a friendly review flow. Completed through `learn review` recommendations and existing `learn refresh ...` actions.
- Add learning noise thresholds. Completed:
  - too many weak notes
  - repeated rejected patterns
  - stale graph links
  - missing validation evidence
  - conflicting learnings
- Add monthly learning hygiene into Enterprise Reporting. Completed.
- Add stronger `start` warnings when learning index exists but refresh actions are stale or unresolved. Completed.
- Document when not to capture a learning. Completed in `LEARNING-GOVERNANCE.md` and `USER-GUIDE.md`.

Implemented files:

- `LEARNING-GOVERNANCE.md`
- `scripts/learning-review.py`
- `scripts/tailtrail.py`
- `scripts/task-start.py`
- `scripts/tailtrail-report.py`
- `scripts/check-tailtrail.py`
- `README.md`
- `TAILTRAIL-COMMANDS.md`
- `USER-GUIDE.md`
- `ROADMAP.md`
- `V2-IMPLEMENTATION-GUIDE.md`

Implementation design:

- `learn review` is local, read-only, deterministic, and Python standard-library only.
- It reads compact learning metadata, not raw prompt history.
- It reports weak/do-not-use events, rejected events, missing validation evidence, guardrail weakening, user overrides, duplicate candidates, conflicting candidates, and blocking refresh actions.
- `--write-result` writes `.tailtrail/learning-governance-review.md`; otherwise nothing is written.
- Start reports show `Learning review recommended`, a reason, and the exact review command.
- Enterprise reports include a Learning Hygiene section for monthly review.

Acceptance:

- Learnings remain advisory.
- Low-confidence accepted work is not promoted automatically.
- Teams can review stale or noisy learnings without loading raw history.
- Enterprise report shows learning hygiene signals.

Remaining:

- Richer conflict detection can be added after real teams generate more learning events.
- Trend charts are deferred until adoption telemetry exists.
- No automatic learning suppression, promotion, deletion, or background review service is implemented.

Validation:

```bash
python3 scripts/tailtrail.py learn review --root .
python3 scripts/tailtrail.py learn refresh recommend --root .
python3 scripts/tailtrail.py report --month 2026-07
```

## Phase V2.6: Public Docs And Product Surface

Goal: make TailTrail easy to evaluate publicly.

Priority: medium.

Implement:

- Add `DEMO.md`.
- Add `ARCHITECTURE.md`.
- Add `PUBLIC-ROADMAP.md`.
- Add `SUPPORT.md`.
- Add adapter capability matrix.
- Update README to link these files without overwhelming first-time users.

Demo should show:

- `tailtrail.py start`
- selected and skipped Navigator features
- graph or quality scan
- scan approval behavior
- learning capture as suggestion only
- enterprise report

Architecture should show:

- command surface
- Navigator
- AIDLC
- guardrails
- token routing
- graph mapper
- learning agent
- quality loop
- reporting
- release checks

Acceptance:

- New user can understand TailTrail value in one short demo.
- Contributor can understand architecture in one file.
- Public roadmap is concise and does not expose every experiment as a commitment.

## Phase V2.7: Engine Deepening Based On Evidence

Goal: improve MVP-grade engines after basic public trust is in place.

Priority: medium after V2.0 through V2.6.

Status: implemented for the first evidence-helper slice, AST Lite, AST V1 maps, and scanner graph overlays.

Implement only when usage evidence shows need:

- Code Graph Mapper enrichment. Partially completed with cache summary and dependency-free AST maps.
- AST Lite maps. Completed with selected-file symbol extraction.
- AST V1 maps. Completed with references, call hints, type hierarchy hints, endpoint hints, DB/config hints, likely tests, and changed-symbol impact.
- Sonar graph overlay. Completed for local report text files through `graph overlay --sonar`.
- Vulnerability graph overlay. Completed for local report text files through `graph overlay --vulnerability`.
- Optional language-server, SCIP, or Roslyn enrichment. Deferred.
- Optional MCP graph provider adapter. Deferred.
- Optional monorepo graph partitioning. Deferred.
- `scripts/slice-context.py`. Completed.
- `scripts/summarize-output.py`. Completed.
- `scripts/cache-summary.py`. Completed.
- `scripts/prune-context.py`. Completed.
- `scripts/ast-map.py`. Completed.
- Optional visual reference compression manifest.

Implemented files:

- `scripts/summarize-output.py`
- `scripts/slice-context.py`
- `scripts/cache-summary.py`
- `scripts/prune-context.py`
- `scripts/ast-map.py`
- `scripts/scanner-graph-overlay.py`
- `scripts/tailtrail.py`
- `scripts/check-tailtrail.py`
- `README.md`
- `TAILTRAIL-COMMANDS.md`
- `USER-GUIDE.md`
- `ROADMAP.md`
- `V2-IMPLEMENTATION-GUIDE.md`

Implemented commands:

```bash
python3 scripts/tailtrail.py engine summarize-output --file build.log
python3 scripts/tailtrail.py engine slice-context --file src/service/foo.py --query validate
python3 scripts/tailtrail.py engine cache-summary
python3 scripts/tailtrail.py engine prune-context --file noisy-context.md
python3 scripts/tailtrail.py graph ast --changed src/service/foo.py --depth lite
python3 scripts/tailtrail.py graph ast --changed src/service/foo.py --depth v1
python3 scripts/tailtrail.py graph ast --changed src/service/foo.py --depth v1 --format json
python3 scripts/tailtrail.py graph overlay --sonar sonar.log --changed src/service/foo.py
python3 scripts/tailtrail.py graph overlay --vulnerability audit.log --changed package.json
python3 scripts/tailtrail.py graph overlay --sonar sonar.log --vulnerability audit.log --format json
```

AST Lite purpose:

- Give the agent a compact list of symbols before it edits a selected file.
- Use Python `ast` for Python source and local heuristics for Java, .NET/C#, SQL, and Terraform.
- Avoid loading broad source context when the user only needs symbol-level orientation.

AST V1 purpose:

- Add local references and call hints around changed symbols.
- Surface likely test files and changed-symbol impact.
- Surface endpoint, DB table, and config hints where simple local parsing can detect them.
- Help Sonar, vulnerability, QA, review, and shared-helper tasks choose a better read order.

Scanner Graph Overlay purpose:

- Connect provided Sonar/static-analysis and vulnerability/audit/SAST evidence to graph impact.
- Preserve exact scanner evidence while adding file scopes, likely tests, related files, nearby manifests, AST V1 symbols, and next graph commands.
- Help users move from "scanner says this failed" to "read these files in this order before remediation."
- Keep scanner execution separate and approval-gated.

Deferred from AST V1:

- full language-server integration
- SCIP indexes
- Roslyn-backed .NET semantic graph
- tree-sitter or other parser-package dependencies
- MCP graph provider adapters
- graph DB or vector DB
- cross-repo service graph
- background indexing service
- semantic correctness claims without reading exact source and validation evidence

Implementation design:

- Add `python3 scripts/tailtrail.py engine ...` as the command group.
- Add `python3 scripts/tailtrail.py graph ast ...` as the structured map command.
- Keep helpers local, deterministic, and read-only against source files.
- Use helpers to reduce noisy evidence and oversized context before prompting.
- Keep outputs explainable and include decision boundaries.
- Do not add vector DB, background service, language server, Roslyn, SCIP, parser-package dependency, MCP adapter, or model calls in this slice.

Examples:

```bash
python3 scripts/tailtrail.py engine summarize-output --file build.log
python3 scripts/tailtrail.py engine slice-context --file src/service/foo.py --query validate
python3 scripts/tailtrail.py engine cache-summary
python3 scripts/tailtrail.py engine prune-context --file noisy-context.md
python3 scripts/tailtrail.py graph ast --changed src/service/foo.py --depth v1
python3 scripts/tailtrail.py graph overlay --sonar sonar.log --changed src/service/foo.py
python3 scripts/tailtrail.py graph overlay --vulnerability audit.log --changed package.json
```

Acceptance:

- Each engine improvement has a documented miss or user need.
- Output remains explainable.
- No vector DB, background service, or MCP adapter is added by default.

Remaining:

- Optional language-server, SCIP, Roslyn, MCP provider, and monorepo graph partitioning.
- Visual reference compression manifest.
- Provider-specific report formats such as SARIF, Sonar JSON, dependency-check XML, CycloneDX, and SPDX.
- Deeper data-flow-lite mapping from endpoints through services to tables for recurring high-risk stacks.

Validation:

```bash
python3 scripts/tailtrail.py engine summarize-output --file README.md
python3 scripts/tailtrail.py engine slice-context --file README.md --query TailTrail
python3 scripts/tailtrail.py engine prune-context --file README.md
python3 scripts/tailtrail.py engine cache-summary
python3 scripts/tailtrail.py graph overlay --sonar sonar.log --changed src/service/foo.py
```
- Exact source inspection is still required before edits.

## Phase V2.8: Enterprise Reporting Maturity

Goal: improve reporting for enterprise evaluation while staying local and privacy-preserving.

Priority: medium.

Implement:

- Month-over-month trend comparison.
- CSV export.
- Multi-report aggregation from explicitly supplied local report files.
- Pull request summary mode.
- Optional report section filters:
  - `--exclude learning`
  - `--only quality`
  - `--only token`
- Keep dashboard deferred until privacy review.

Acceptance:

- Teams can show trends.
- Reports remain local.
- No central telemetry exists by default.
- CSV export is safe and redacted.

Validation:

```bash
python3 scripts/tailtrail.py report --month 2026-07 --format json
python3 scripts/tailtrail.py report --start 2026-07-01 --end 2026-07-31
```

## Phase V2.9: Packaging And Distribution Decision

Goal: decide whether source-only release remains enough.

Priority: later.

First public release recommendation:

- Source-only repository.
- Users clone or download and run `python3 scripts/tailtrail.py`.
- No package-manager install.
- No global command.
- No background service.

Future options:

- Python package with console script.
- `pipx` install.
- Release archive.
- Codex plugin package.
- Package-manager distribution only after demand.

Acceptance:

- Installation remains simple.
- Updating does not break installed packs.
- Packaging complexity is justified by real users.

## V2 Tracking Table

| Phase | Status | Blocker For Public Pitch | Primary Output |
|---|---|---|---|
| V2.0 Public Release Baseline | Not started | Yes | CI, smoke test, changelog, templates, claim guardrails |
| V2.1 One-Command UX | Implemented first-command slice | Yes | clearer `start` path |
| V2.2 Clone Setup Hygiene | Implemented read-only scanner | No, but high value | `setup-scan` |
| V2.3 Adoption Evidence | Implemented opt-in outcome telemetry | Enterprise pitch | outcome metrics |
| V2.4 Exact Token Usage | Implemented measured telemetry path | ROI claims | measured token schema |
| V2.5 Guarded Learning UX | Implemented first guarded UX slice | Enterprise pitch | learning governance |
| V2.6 Public Docs Surface | Not started | Public launch polish | demo, architecture, support |
| V2.7 Engine Deepening | Implemented evidence helpers plus AST Lite/V1 maps | No | graph/scanner/output helpers |
| V2.8 Reporting Maturity | Later | Enterprise expansion | trends, CSV, aggregation |
| V2.9 Packaging Decision | Later | No | distribution plan |

## V2 Release Discipline

For every phase:

1. Update implementation docs first if the scope changes.
2. Implement one command or artifact at a time.
3. Add validation to `scripts/check-tailtrail.py`.
4. Update `TAILTRAIL-COMMANDS.md` for new commands.
5. Update `USER-GUIDE.md` for user-facing behavior.
6. Run:

```bash
python3 scripts/check-tailtrail.py
python3 scripts/tailtrail.py release-check
python3 scripts/tailtrail.py doctor
git diff --check
```

7. Commit only after the phase is end-to-end complete.
