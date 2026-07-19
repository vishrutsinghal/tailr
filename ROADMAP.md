# TailTrail Roadmap

This roadmap keeps future work simple and staged. Each phase should be useful on its own, easy to remove if it does not help, and consistent with TailTrail's core promise: small changes, clear ownership, and no weakened safeguards.

## Direction

TailTrail should grow from portable guidance first, automation second. Plain Markdown features are preferred because they work across repositories and do not require runtime setup. Hooks, installers, adapters, and benchmark tooling should appear only after the manual workflow proves valuable.

## TailTrail V2 Roadmap

Purpose: collect all remaining planned work into a single TailTrail Version 2 track so new development can start from one clear backlog.

Status: planned. V1/V1.x established the core local-first toolkit: Navigator, `start`, AIDLC, guardrails, policy packs, token routing, graph mapping, quality scanning, vulnerability intelligence, learning, reporting, release checks, and multi-assistant guidance. V2 should focus on public-release readiness, one-command polish, adoption evidence, safer setup in cloned repos, and carefully deepening the MVP-grade engines.

V2 principle:

- Make `tailtrail.py start` the obvious first command.
- Keep automation local, deterministic, and approval-first.
- Do not oversell MVP-grade helpers as deep engines.
- Use real evidence before making enterprise productivity or ROI claims.
- Preserve user privacy and avoid raw prompt/log capture by default.
- Treat cloned-repo TailTrail files as shared project context only when they are safe to share.
- Add public-release polish before advanced infrastructure.

### Current Improvement Opportunities

These improvements emerged from recent project work and should be added to the active V2 backlog:

- Add a dedicated Codex installer/plugin command and profile so Codex installation becomes a first-class supported path.
- Provide a Codex plugin manifest and packaging path for reproducible host setup and plugin registration.
- Improve the demo onboarding experience with clear, step-by-step Codex installation documentation.
- Expand CLI and installer coverage with targeted tests for new install routes and profile-based deployment behavior.
- Strengthen install-time validation and diagnostics for local plugin packaging and adapter setup.
- Keep public docs, command catalog, and demo materials aligned with the actual supported Codex install workflow.

### V2.0: Public Release Baseline

Goal: make TailTrail safe and credible for open-market evaluation.

Priority: highest.

Scope:

- Public CI. Implemented in V2.0.1 with `.github/workflows/tailtrail-ci.yml`.
- Fresh-clone smoke test.
- `CHANGELOG.md`.
- Versioning policy and release tag rules.
- GitHub issue templates.
- Pull request template.
- Public security reporting finalization.
- License and provenance finalization.
- Public claim guardrails.
- Public documentation sanitizer.

Implementation references:

- See `Public Release Features`.
- See `Shortcoming Remediation Plan`, Priority 0.

Acceptance check:

- A public PR has automated checks. Implemented for package validation, release hygiene, adapter sync, and Python compilation.
- A fresh clone can run the core commands.
- Public docs avoid unsupported claims.
- Release checks catch local state, placeholders, and public hygiene issues.
- Security reporting and license language are final.

### V2.1: One-Command User Experience

Goal: make TailTrail approachable for a new user who does not know the feature map.

Priority: highest.

Status: implemented for the first V2.1 slice. `start` is now the primary documented first command, the command catalog includes a decision table, and the Start report includes a Start Here section plus a Decision Menu.

Scope:

- Make Navigator-first task entry the primary first step in README, user guide, demo, and command catalog. Implemented through `start`, daily `do`, and free-form task fallback.
- Add a command decision table. Implemented in `TAILTRAIL-COMMANDS.md` and summarized in `USER-GUIDE.md`.
- Tighten `start` output so the next action is obvious. Implemented with Start Here, Decision Menu, and approval/edit/scan/learning/leaner prompts.
- Add a benchmark scenario for the Start command user experience. Implemented with `benchmarks/scenarios/start-command-ux/`.
- `tailtrail.py next` is now implemented as read-only continuation guidance after `start`.
- Keep advanced commands visible but secondary. Implemented in docs.

Implementation design:

- `scripts/task-start.py` remains a report generator, not an implementation agent.
- It calls Navigator, then adds a small `next_actions` list to make the user decision explicit.
- The Markdown output starts with `Start Here`, followed by a `Decision Menu`.
- Scan and learning actions only appear when Navigator reports `scan_approval` or `learning_approval`.
- Token posture remains a cautious local estimate and is not presented as exact model/API usage.

Example:

```bash
python3 scripts/tailtrail.py start "fix Sonar cognitive complexity issue" --changed src/main/java/com/acme/payment/PaymentValidator.java
```

Expected result:

- TailTrail recommends a workflow before implementation.
- The report shows selected and skipped features.
- The user sees likely impacted files and suggested validation.
- If scanner work is involved, TailTrail asks for explicit scan approval.
- The user can approve, edit, or make the workflow leaner before any code changes happen.

Implemented V2.1 follow-up:

- `tailtrail.py next` is implemented as deterministic continuation guidance after the Start report.
- V2.2 `setup-scan` remains a separate command because cloned-repo setup hygiene is bigger than first-command UX.

Implementation references:

- See `Shortcoming Remediation Plan` -> `One Obvious Command Polish`.
- See `Phase 11: Enterprise Polish To 8.5`.

Acceptance check:

- New user reaches a useful Navigator plan in under one minute.
- `start` tells the user whether to approve, edit, scan, validate, or skip heavy process.
- README does not overwhelm the user with many equal first-step choices.

### V2.2: Clone Setup Hygiene And Shared Context Detection

Goal: support repos where TailTrail files already exist because another user or team committed shared project context.

Priority: high.

Status: completed end to end for the first read-only setup scanner. TailTrail now includes `scripts/setup-scan.py`, `python3 scripts/tailtrail.py setup-scan --root .`, JSON/Markdown output, a gitignore template, installed-pack detection, local-state warnings, shared-context classification, and documentation.

Scope:

- Add `scripts/setup-scan.py`. Implemented.
- Add `python3 scripts/tailtrail.py setup-scan --root .`. Implemented.
- Classify existing TailTrail files into:
  - shared project context
  - project overrides
  - team review files
  - installed TailTrail pack
  - local runtime state
  - generated-but-shareable metadata
  - unknown TailTrail-like files
- Preserve shared policy, overrides, AIDLC docs, and curated learnings by default. Implemented as recommendations.
- Warn on committed local state such as router state, events, scores, telemetry, and run outputs. Implemented.
- Recommend `.gitignore` patterns. Implemented through scan output and `templates/tailtrail-gitignore.md`.
- Recommend safe next commands: policy check, update dry-run, install dry-run, setup review. Implemented.

Implemented commands:

```bash
python3 scripts/tailtrail.py setup-scan --root .
python3 scripts/tailtrail.py setup-scan --root . --format json
python3 scripts/tailtrail.py setup-scan --root . --tracked-only
```

Implementation boundaries:

- Read-only: no install, update, delete, move, gitignore edit, or file rewrite.
- Conservative: existing overrides are preserved and surfaced for review.
- Local state is flagged, not removed.
- Installed packs are only pointed to dry-run update commands.

Implementation references:

- See `Shortcoming Remediation Plan` -> `Clone Setup Hygiene And Shared Context Detection`.

Acceptance check:

- A new developer can clone a repo and understand which TailTrail files are shared versus local.
- Existing overrides are not overwritten silently.
- Runtime state is flagged.
- Installed packs are only updated through dry-run or explicit approval.

### V2.3: Real Adoption Evidence And Outcome Telemetry

Goal: collect useful local evidence without surveillance.

Priority: high.

Status: completed end to end for the first opt-in local outcome telemetry layer. TailTrail now includes `scripts/outcome-telemetry.py`, `python3 scripts/tailtrail.py outcome capture|summarize`, `.tailtrail/outcome-events.jsonl`, `.tailtrail/outcome-summary.md`, enterprise-report integration, setup-scan local-state detection, and documentation.

Scope:

- Add an explicit outcome capture path for:
  - task type
  - workflow selected
  - user acceptance
  - validation outcome
  - review outcome
  - defect escaped yes/no
  - time-saved band
  - TailTrail fit: too heavy, too light, correct
- Keep capture opt-in and local. Implemented with `--approved`.
- Avoid raw prompt capture by default. Implemented through compact controlled values and privacy notes.
- Extend Enterprise Reporting to include adoption evidence. Implemented.
- Add privacy and retention guidance. Implemented.

Implemented commands:

```bash
python3 scripts/tailtrail.py outcome capture --task-type bug-fix --workflow start,review --acceptance accepted --validation-outcome pass --review-outcome approved --defect-escaped no --time-saved 30-60m --fit correct --learning-quality trusted --approved
python3 scripts/tailtrail.py outcome summarize --month 2026-07
python3 scripts/tailtrail.py outcome summarize --month 2026-07 --format json
python3 scripts/tailtrail.py outcome summarize --write-result
python3 scripts/tailtrail.py report --month 2026-07
```

Implementation boundaries:

- No background observer.
- No automatic prompt logging.
- No raw logs, secrets, PII, PHI, customer data, or source snippets.
- No upload or central telemetry service.
- Raw event files are local state; use summaries for retrospectives.

Implementation references:

- See `Shortcoming Remediation Plan` -> `Real Usage Telemetry, Privacy-First`.
- See `Phase 9.7: Enterprise Reporting` future candidates.

Acceptance check:

- Teams can show evidence of value without uploading data.
- Reports include outcomes, not just command usage.
- No raw prompts, secrets, PII, PHI, customer data, or raw logs are captured by default.

### V2.4: Exact Token Usage Path

Goal: separate directional token estimates from exact measured usage.

Priority: high.

Status: completed end to end for the first measured telemetry path and the non-network adapter layer. TailTrail now defines the `.tailtrail/token-usage.jsonl` schema, includes `templates/token-usage-example.jsonl`, supports friendly manual measured entries, supports provider-file imports for OpenAI, Claude/Anthropic, Gemini, and generic usage exports, improves measured savings reports with record-level before/after stats, and documents exact-claim boundaries.

Scope:

- Define `.tailtrail/token-usage.jsonl` schema. Implemented.
- Add sample measured telemetry file with fake values. Implemented as `templates/token-usage-example.jsonl`.
- Document manual provider usage export. Implemented as a manual usage-metadata normalization flow.
- Add Manual Telemetry Adapter. Implemented with `python3 scripts/tailtrail.py telemetry manual ...`; it writes normalized measured records without network calls.
- Add Import Adapters. Implemented with `telemetry import-openai`, `telemetry import-claude`/`import-anthropic`, `telemetry import-gemini`, and `telemetry import-generic`; they parse user-provided JSON/JSONL files containing both baseline/before and TailTrail/after usage blocks.
- Improve measured token reports. Implemented with before TailTrail, with TailTrail, difference, reduction, ignored-record reasons, and JSON output.
- Add provider adapters later only after privacy review. Implemented for local file imports only; direct provider API collection remains deferred.
- Keep pricing/cost analysis optional and user-supplied until pricing update rules are clear. Deferred.
- Optional API runner. Deferred. TailTrail does not call model APIs, store API keys, or run networked telemetry benchmarks in normal local development.

Implemented commands:

```bash
python3 scripts/tailtrail.py telemetry manual --task-id demo-001 --provider openai --model gpt-5 --baseline-input 42000 --baseline-output 3000 --tailtrail-input 18000 --tailtrail-output 2500
python3 scripts/tailtrail.py telemetry import-openai --source openai-usage.jsonl --output .tailtrail/token-usage.jsonl
python3 scripts/tailtrail.py telemetry import-claude --source claude-usage.jsonl --output .tailtrail/token-usage.jsonl
python3 scripts/tailtrail.py telemetry import-gemini --source gemini-usage.jsonl --output .tailtrail/token-usage.jsonl
python3 scripts/tailtrail.py savings estimate --used README.md --avoided ROADMAP.md
python3 scripts/tailtrail.py savings report --telemetry templates/token-usage-example.jsonl
python3 scripts/tailtrail.py savings report --telemetry .tailtrail/token-usage.jsonl --format json
python3 scripts/tailtrail.py report --token-telemetry .tailtrail/token-usage.jsonl
```

Adapter import shape:

```json
{
  "task_id": "demo-001",
  "model": "gpt-5",
  "baseline": {"usage": {"input_tokens": 42000, "output_tokens": 3000}},
  "tailtrail": {"usage": {"input_tokens": 18000, "output_tokens": 2500}}
}
```

Provider importers are conservative: they import only records that include both `baseline`/`before` and `tailtrail`/`after` usage. A single API response is not enough to calculate before/after savings.

Example-only sample stats:

| Task | Before TailTrail | With TailTrail | Difference | Reduction |
|---|---:|---:|---:|---:|
| example-sonar-fix | 75,000 | 18,500 | 56,500 | 75.33% |
| example-review | 42,000 | 14,000 | 28,000 | 66.67% |

These are fake values for schema validation and demos. Real teams must use their own model/API usage metadata before making exact token-savings claims.

Deferred:

- Provider-specific automatic usage collectors that call external APIs.
- Pricing/cost conversion.
- Cross-repo token analytics.
- Any shared telemetry service.
- Controlled benchmark API runner.

Implementation references:

- See `Shortcoming Remediation Plan` -> `Exact Token Usage Path`.
- See `Phase 7.0a: Token Savings Telemetry Guardrail`.

Acceptance check:

- Estimated and measured token reports are clearly different.
- TailTrail never claims exact savings without measured telemetry.
- Teams with real usage metadata can generate measured savings reports through manual entry or local provider-file imports.
- TailTrail rejects or ignores telemetry rows that do not contain both baseline and TailTrail usage evidence.

### V2.4.1: Token Budget Coach

Goal: improve Navigator's initial context-token budget estimates over time without turning budget guidance into a hard stop or an exact-savings claim.

Priority: high.

Status: implemented for the first local learning slice. TailTrail now includes a deterministic Token Budget Coach that estimates a context budget from task type, changed files, graph cache status, risk signals, language hints, and approved local budget outcome events. Navigator includes the budget, confidence, evidence level, and escalation rule in its plan.

Scope:

- Add `scripts/token_budget_coach.py` as the importable deterministic estimator. Implemented.
- Add `scripts/token-budget-coach.py` as the CLI wrapper. Implemented.
- Add `python3 scripts/tailtrail.py budget estimate|record|profile`. Implemented.
- Add Context Budget Planner output to Navigator. Implemented through the Token Budget section with budget, confidence, evidence level, and escalation rule.
- Add Graph-First Reads to Navigator. Implemented through the Context Strategy section, which recommends graph/read-order and summary context before exact source reads.
- Add Context Receipts. Implemented with `scripts/context_receipt.py`, `scripts/context-receipt.py`, and `python3 scripts/tailtrail.py receipt capture|summary`.
- Add Prompt Compression Profiles. Implemented with `scripts/prompt_profile.py`, `scripts/prompt-profile.py`, and `python3 scripts/tailtrail.py profile lean|review|testing|aidlc|security|handoff`.
- Add Learning/Graph Summaries Instead Of Raw History. Implemented in Navigator's Context Strategy with top matching graph-aware learnings only, graph/cache summaries before exact reads, and explicit raw-history avoidance.
- Add Measured Telemetry Import. Implemented with `python3 scripts/tailtrail.py savings import --source usage.jsonl --output .tailtrail/token-usage.jsonl` and the friendlier adapter commands under `python3 scripts/tailtrail.py telemetry ...`.
- Store approved budget events in `.tailtrail/token-budget-events.jsonl`. Implemented.
- Store local budget profile summaries in `.tailtrail/token-budget-profile.json`. Implemented.
- Include Token Budget in Navigator full and compact plans. Implemented.
- Keep budget events privacy-safe by storing hashes, task type, language tags, graph status, budget numbers, escalation outcome, and reason only. Implemented.
- Avoid raw prompts, source snippets, logs, secrets, PII, PHI, customer data, model calls, background services, and cross-repo aggregation. Implemented.

Implemented commands:

```bash
python3 scripts/tailtrail.py budget estimate "fix validation bug" --changed src/service/foo.py
python3 scripts/tailtrail.py budget record --task-type bug --initial-budget 8000 --actual-context 10500 --outcome underestimated --escalated yes --approved
python3 scripts/tailtrail.py budget profile
python3 scripts/tailtrail.py profile review
python3 scripts/tailtrail.py receipt capture --task "fix validation bug" --profile review --loaded src/service/foo.py --avoided ROADMAP.md --approved
python3 scripts/tailtrail.py receipt summary
python3 scripts/tailtrail.py telemetry manual --task-id demo-001 --provider openai --model gpt-5 --baseline-total 45000 --tailtrail-total 20500
python3 scripts/tailtrail.py telemetry import-gemini --source gemini-usage.jsonl --output .tailtrail/token-usage.jsonl
python3 scripts/tailtrail.py savings import --source usage.jsonl --output .tailtrail/token-usage.jsonl
```

Budget escalation example:

```text
Initial budget: 8,000
Needed context: 13,000
Reason: graph cache missing and validation tests live outside the source package
Next estimate: similar Python bug tasks start closer to 11,000-12,000
Rule: if needed context exceeds the escalation threshold, pause and ask before loading more
```

Implementation boundaries:

- Budget is guidance, not a hard stop.
- Token Budget Coach improves local estimates only; it does not create exact model/API telemetry.
- Exact savings still require V2.4 measured usage records.
- The Coach should ask for budget escalation instead of starving the assistant of necessary context.
- Context receipts use approximate local counts unless paired with measured telemetry.
- Prompt profiles are compact guidance slices; they are not a substitute for exact source, policy, scanner, or validation evidence.

Acceptance check:

- Navigator shows a token budget and escalation rule for implementation-like tasks.
- Navigator shows graph-first context strategy and raw-history avoidance.
- Approved budget outcomes improve later estimates for similar task/language patterns.
- Context receipts can be captured only with explicit approval.
- Measured telemetry can be imported before running exact token reports.
- Budget events do not store raw prompts or source content.
- Public docs still distinguish estimates, local learned budgets, and exact measured telemetry.

### V2.5: Guarded Learning UX

Goal: keep learning useful without letting noisy or user-biased history degrade future work.

Priority: high.

Status: implemented for the guarded UX slice plus richer learning conflict detection. TailTrail now has a learning governance guide, `learn review`, `learn govern`, Start-report hygiene warnings, enterprise learning hygiene signals, contradiction detection across acceptance/confidence/validation/override history, and stale-pattern conflict detection against refresh actions.

Scope:

- Add learning governance guide. Implemented in `LEARNING-GOVERNANCE.md`.
- Add a friendly `tailtrail.py learn review` wrapper. Implemented through `scripts/learning-review.py`.
- Add `tailtrail.py learn govern` alias for users who think of this as learning governance. Implemented.
- Add noise thresholds for weak notes, rejected patterns, stale graph links, no-validation learnings, conflicting learnings, guardrail weakening, and low-confidence overrides. Implemented in the review report.
- Add monthly learning hygiene into Enterprise Reporting. Implemented in `scripts/tailtrail-report.py`.
- Add stronger `start` warnings when learning refresh actions are stale or unresolved. Implemented in `scripts/task-start.py`.

Implementation design:

- `learn review` is read-only by default and does not edit learning files.
- It reads compact local learning metadata: `.tailtrail/learning-events.jsonl`, `.tailtrail/learning-index.md`, `.tailtrail/learnings.md`, and `.tailtrail/learning-refresh-actions.json`.
- It reports weak/do-not-use events, rejected patterns, missing validation evidence, guardrail risk, user overrides, duplicates, conflicts, and blocking refresh actions.
- It detects richer contradictions: accepted vs rejected history, trusted vs weak/do-not-use confidence, passed vs failed/missing validation history, trusted history with low-confidence override history, and reusable learnings that conflict with stale/suppress/archive/delete refresh actions.
- `--write-result` writes `.tailtrail/learning-governance-review.md` for local review.
- `start` now shows whether learning review is recommended and gives the exact command.
- Enterprise Reporting now includes a Learning Hygiene section so teams can review memory quality during retrospectives.
- Current source, tests, CI, scanners, policy, and guardrails continue to override old learnings.

Example:

```bash
python3 scripts/tailtrail.py learn review --root .
python3 scripts/tailtrail.py learn review --root . --write-result
python3 scripts/tailtrail.py learn govern --root .
python3 scripts/tailtrail.py report --month 2026-07
```

Expected result:

- TailTrail shows whether learning memory is clean, noisy, stale, or weakly validated.
- The user gets recommended next steps, such as running refresh or suppressing a stale learning.
- No learning is promoted, suppressed, archived, or deleted without explicit approval.

Remaining V2.5 follow-up:

- Add approved remediation commands for conflict groups only after users review governance output in real projects.

Implementation references:

- See `Shortcoming Remediation Plan` -> `Guarded Learning UX`.
- See `Phase 9`, `Phase 9.1`, and `Phase 9.2`.

Acceptance check:

- Learning remains advisory.
- Low-confidence accepted changes are not promoted automatically.
- Teams can clean stale or noisy learnings without loading raw history.

### V2.6: Public Docs And Product Surface

Goal: make TailTrail easy to understand, evaluate, and trust.

Priority: medium.

Scope:

- Public demo walkthrough.
- `ARCHITECTURE.md`.
- `PUBLIC-ROADMAP.md`.
- `SUPPORT.md`.
- Public claim guardrails.
- Public docs sanitizer.
- Adapter capability matrix for Codex, Claude, Cursor, Copilot, ChatGPT, and Gemini.

Implementation references:

- See `Public Release Features`.
- See `Shortcoming Remediation Plan` -> `Multi-Agent Integration Beyond Instruction Files`.

Acceptance check:

- A user can understand the architecture without reading every file.
- Public readers see a concise roadmap instead of only the detailed internal roadmap.
- Multi-agent limitations are clear and not oversold.

### V2.7: Engine Deepening Based On Evidence

Goal: improve MVP-grade engines only where real usage shows gaps.

Priority: medium after V2.0-V2.6.

Status: implemented for the first evidence-helper slice plus dependency-free AST Lite, AST V1 maps, Semantic V2 maps, Semantic V3 approved-provider ingestion, and scanner graph overlays. TailTrail now includes local helpers for generic output summarization, context slicing, cache summarization, context pruning, structured metadata maps for selected source files, local semantic graph metadata for selected files, optional provider readiness detection, approved local provider-output ingestion, and scanner-to-graph impact overlays for local Sonar/static-analysis and vulnerability evidence. Direct provider execution remains deferred until usage evidence and local policy justify it.

Scope:

- Code Graph Mapper enrichment. Partially implemented through `cache-summary`, which helps inspect cache shape without loading full metadata.
- AST Lite maps. Implemented through `graph ast --depth lite`; reports selected-file symbols with Python `ast` and explainable local heuristics for Java, .NET/C#, SQL, and Terraform.
- AST V1 maps. Implemented through `graph ast --depth v1`; adds symbol references, call hints, type hierarchy hints, endpoint hints, DB/config hints, likely tests, and changed-symbol impact.
- Semantic V2 maps. Implemented through `graph ast --depth v2`; adds a local symbol index, import/module edges, reference edges, endpoint-to-handler links, data-flow-lite hints, test coverage hints, and provider readiness for language-server, SCIP, Roslyn, and tree-sitter paths.
- Semantic V3 provider ingestion. Implemented through `graph ast --depth v3 --provider-output ...`; ingests approved local JSON exports from Java JDT/language-server style tools, .NET Roslyn-derived analyzers, richer Python analyzers, SQL parsers, Terraform parsers, SCIP-derived JSON, or repo-owned extractors. TailTrail labels ingested facts as `provider-backed`.
- Sonar graph overlay. Implemented through `graph overlay --sonar`; connects provided local Sonar/static-analysis findings to impacted files, likely tests, related files, AST V1 hints, and follow-up graph commands.
- Vulnerability graph overlay. Implemented through `graph overlay --vulnerability`; connects provided local vulnerability/audit/SAST findings to impacted manifests/source files, components, likely tests, related files, AST V1 hints, and follow-up graph commands.
- Optional language-server, SCIP, Roslyn, or tree-sitter execution. Deferred; V2/V3 detect readiness or ingest approved JSON exports only and do not start those providers.
- Optional MCP graph provider adapter. Deferred.
- Optional monorepo graph partitioning. Deferred.
- Output summarization, cache-summary, prune-context, and slice-context helper scripts. Implemented.

Default semantic policy:

- Default engine path is local-only: AST Lite, AST V1, and Semantic V2.
- TailTrail's default code-intelligence path remains local and dependency-free.
- `graph ast` defaults to AST V1.
- Use AST Lite, AST V1, and Semantic V2 for normal local development.
- Semantic V3 is never the default route.
- Semantic V3 requires explicit `--depth v3`, at least one explicit `--provider-output` path, and either `--approved` or local policy enablement.
- Navigator may recommend V3 only when the user asks for provider-backed semantic intelligence or an approved provider-output file already exists and is relevant.
- TailTrail must not auto-run JDT, Roslyn, language servers, SCIP, tree-sitter, SQL parsers, Terraform parsers, MCP providers, networked services, or repo-owned extractors.
- Provider output is advisory metadata. Exact current source, tests, CI, scanner output, policy, guardrails, and explicit user direction still win.

Implementation design:

- Add a single `tailtrail.py engine ...` command group for engine helper scripts.
- Add `tailtrail.py graph ast ...` for dependency-free structured source maps.
- Add Semantic V2 as an extension of `graph ast`, not a separate background service.
- Add Semantic V3 as an approved-provider ingestion extension of `graph ast`, not a provider runner.
- Keep every helper local, deterministic, Python standard-library only, and read-only against source files.
- Use helpers to reduce noisy evidence before prompting, not to replace exact source/log inspection.
- Preserve cautious token language: approximate context counts are not model/API token telemetry.
- Avoid vector DB, graph DB, background service, MCP adapter, parser-package dependency, Roslyn execution, direct binary SCIP ingestion, tree-sitter parser execution, or language-server startup in this slice.

Implemented commands:

```bash
python3 scripts/tailtrail.py engine summarize-output --file build.log
python3 scripts/tailtrail.py engine slice-context --file src/service/foo.py --query validate
python3 scripts/tailtrail.py engine cache-summary
python3 scripts/tailtrail.py engine prune-context --file noisy-context.md
python3 scripts/tailtrail.py graph ast --changed src/service/foo.py --depth lite
python3 scripts/tailtrail.py graph ast --changed src/service/foo.py --depth v1
python3 scripts/tailtrail.py graph ast --changed src/service/foo.py --depth v1 --format json
python3 scripts/tailtrail.py graph ast --changed src/service/foo.py --depth v2
python3 scripts/tailtrail.py graph ast --changed src/service/foo.py --depth v2 --format json
python3 scripts/tailtrail.py graph ast --changed src/service/foo.py --depth v3 --provider-output tailtrail-meta/providers/semantic.json --approved
python3 scripts/tailtrail.py graph ast --changed src/service/foo.py --depth v3 --provider-output tailtrail-meta/providers/roslyn.json --approved --format json
python3 scripts/tailtrail.py graph overlay --sonar sonar.log --changed src/service/foo.py
python3 scripts/tailtrail.py graph overlay --vulnerability audit.log --changed package.json
python3 scripts/tailtrail.py graph overlay --sonar sonar.log --vulnerability audit.log --format json
```

Expected result:

- Generic logs can be compacted before the agent reads them.
- Large files can be sliced around relevant terms.
- Code graph cache metadata can be summarized without loading the full cache.
- Noisy context files can be estimated and pruned with explicit drop terms.
- Selected files can be mapped at symbol level before editing.
- Selected files can be mapped with local semantic edges before editing when V1 is not enough.
- Selected files can be enriched with approved provider-backed metadata before editing when V2 is not enough.
- Shared helper, endpoint, DB/config, and scanner-remediation work gets a better read order without loading the whole repo.
- Sonar and vulnerability findings can be overlaid onto graph impact metadata before remediation.

Scanner overlay example:

```bash
python3 scripts/tailtrail.py graph overlay --sonar sonar.log --changed src/main/java/com/acme/payment/PaymentValidator.java
```

Expected overlay result:

- Preserves the exact Sonar rule ID, severity, affected path, and evidence line from `sonar.log`.
- Labels `PaymentValidator.java` as source and runs AST V1 enrichment for that file.
- Shows symbols, call hints, likely tests, related files, and nearby manifests when detected.
- Suggests a read order before implementation.
- Prints follow-up commands such as `graph ast --depth v1`, Code Review Graph Lite, and Code Graph Mapper refresh.

Vulnerability overlay example:

```bash
python3 scripts/tailtrail.py graph overlay --vulnerability audit.log --changed package.json
```

Expected overlay result:

- Preserves CVE/GHSA/CWE IDs, severity, component names, and affected manifest paths when detected.
- Labels dependency manifests separately from source files.
- Recommends Dependency Gate before package, BOM, lockfile, or base image changes.
- Keeps scanner execution separate; the overlay does not run audits or prove the issue is fixed.

Semantic V2 example:

```bash
python3 scripts/tailtrail.py graph ast --changed src/main/java/com/acme/payment/PaymentController.java --depth v2
```

Expected semantic result:

- Shows symbol definitions and local references from the selected file.
- Shows import/module edges so the agent knows which nearby packages or framework APIs matter.
- Links endpoint annotations or route decorators to likely handler symbols.
- Emits data-flow-lite hints such as endpoint -> handler -> service call names -> DB/config clues when detected.
- Reports provider readiness for language-server, SCIP, Roslyn, and tree-sitter paths without starting those tools.
- Keeps the output as metadata only; exact source inspection, tests, CI, scanners, policy, and guardrails still win.

Semantic V3 example:

```bash
python3 scripts/tailtrail.py graph ast \
  --changed src/main/java/com/acme/payment/PaymentController.java \
  --depth v3 \
  --provider-output tailtrail-meta/providers/jdt.json \
  --approved
```

Expected provider-backed result:

- Reads the exact selected source file with TailTrail's local AST/heuristic layer.
- Reads the approved local provider JSON file without starting the provider.
- Runs only when the command includes `--approved` or `tailtrail-policy.md` enables `provider_backed_semantic_ingestion: enabled`.
- Normalizes provider symbols, references, calls, type hierarchy, endpoints, DB tables, config usage, and import edges.
- Labels provider facts as `provider-backed`.
- Adds normalized `evidence_label` values and an `evidence_summary` for `heuristic`, `local-ast`, `provider-backed`, and `measured/validated`.
- Supports Java JDT/language-server style exports, .NET Roslyn-derived exports, richer Python analyzer exports, SQL parser exports, Terraform parser exports, SCIP-derived JSON, or repo-owned extractor output.
- Rejects missing or outside-root provider output as an error entry instead of reading arbitrary filesystem paths.
- Keeps source snippets out of the report.
- Requires exact source, tests, scanner evidence, policy, and guardrail review before implementation.

Remaining V2.7 follow-up:

- Add provider execution for language-server, SCIP, Roslyn, tree-sitter/parser-package support, MCP, or monorepo partitioning only after approved JSON ingestion proves useful and local policy approves execution.
- Add deeper data-flow and type-resolution engines only if dependency-free Semantic V2 cannot answer recurring impact questions.
- Add cross-repo service graph, graph DB, or vector DB only after local metadata maps show clear limits.
- Add visual reference compression manifest only if visual references become a practical token issue.
- Add provider-specific report parsers for Sonar JSON, dependency-check XML, CycloneDX, SPDX, and other structured formats if current SARIF, Trivy JSON, Grype JSON, and text parsing miss recurring enterprise evidence.
- Add data-flow-lite overlays from endpoint to service to database table only after repeated scanner remediation misses show this is needed.

Implementation references:

- See Phase 1 deferred helpers.
- See `Phase 7.2: Code Review Graph Lite` future candidates.
- See `Phase 8.8: Code Graph Mapper` future candidates.
- See `Shortcoming Remediation Plan` -> `Deepen MVP-Grade Engines Carefully`.

Acceptance check:

- Improvements are driven by documented misses.
- Output remains explainable.
- No vector DB, background service, or MCP adapter is added before a clear need exists.

### V2.8: Enterprise Reporting Maturity

Goal: improve reporting enough for enterprise evaluation without building a surveillance platform.

Priority: medium.

Status: implemented for the local maturity slice. TailTrail now supports `report trend`, `report aggregate`, `report pr`, section filters with `--only`, and measured token trend integration when local measured telemetry exists.

Scope:

- Month-over-month trend comparison. Implemented through `report trend`.
- CSV export. Implemented for value, trend, aggregate, compare, and enterprise key-value outputs.
- Multi-report aggregation from explicitly supplied local report files. Implemented through `report aggregate --report-file ...`.
- Pull request summary mode. Implemented through `report pr`.
- Optional report section filters. Implemented through repeated `--only quality|outcomes|learning|tokens`.
- Measured token trend integration. Implemented in `report trend` when `.tailtrail/token-usage.jsonl` or `--token-telemetry` has measured records.
- Enterprise dashboard only after privacy review and local reports prove value.

Implemented commands:

```bash
python3 scripts/tailtrail.py report trend
python3 scripts/tailtrail.py report trend --format csv --write-result
python3 scripts/tailtrail.py report aggregate --report-file repo-a-value.json --report-file repo-b-value.json
python3 scripts/tailtrail.py report pr --only quality --only tokens
python3 scripts/tailtrail.py report --only quality
```

Decision boundary:

- Trend and aggregate reports are local and advisory.
- Aggregate does not discover repos or upload telemetry; it only reads JSON files explicitly supplied by the user.
- PR summary is compact Markdown and should not include raw prompts, secrets, PII, PHI, customer data, or raw logs.
- Token trend numbers are exact only for measured model/API telemetry records.

Implementation references:

- See `Phase 9.7: Enterprise Reporting` future candidates.
- See `Shortcoming Remediation Plan` -> `Enterprise Reporting Maturity`.

Acceptance check:

- Teams can show trend evidence.
- Reports remain local and privacy-preserving.
- No central telemetry is introduced by default.

### V2.9: Packaging And Distribution Decision

Goal: decide whether TailTrail should remain source-only or add package distribution.

Priority: later, after public basics.

Scope:

- First public release should remain source-only unless user demand says otherwise.
- Later candidates:
  - Python package with console script
  - `pipx` install
  - GitHub release archive
  - Codex plugin package
  - package-manager distribution only after demand

Implementation references:

- See `Public Release Features` -> `Distribution Decision`.
- See `Shortcoming Remediation Plan` -> `Packaging And Distribution`.

Acceptance check:

- Installation remains understandable.
- Updating does not break installed packs.
- TailTrail does not adopt package-manager complexity too early.

### V2 Implementation Order

1. Public CI.
2. Fresh-clone smoke test.
3. Changelog and version policy.
4. Issue and PR templates.
5. Public claim guardrails and docs sanitizer.
6. Security reporting finalization.
7. License and provenance finalization.
8. One-command UX tightening around `start`.
9. Clone setup hygiene with `setup-scan`.
10. Learning governance UX.
11. Real outcome telemetry schema.
12. Exact token telemetry docs and examples.
13. Public demo walkthrough.
14. Architecture and public roadmap docs.
15. Multi-agent capability matrix.
16. Enterprise reporting trends and CSV.
17. Evidence-driven graph/scanner overlays.
18. Packaging only after source-only release feedback.

### V2 Non-Goals For Now

- No hidden telemetry.
- No automatic raw prompt capture.
- No background service.
- No automatic scanner execution.
- No central enterprise dashboard before privacy review.
- No vector DB by default.
- No package-manager distribution before source-only feedback.
- No claim of exact token savings without measured provider usage.
- No claim that TailTrail replaces review, tests, CI, SAST, dependency scanners, legal review, or security review.

## Phase 1: Token Slicer Foundation

Purpose: reduce repeated context and noisy Markdown loading before adding more process files.

Status: completed for the foundation. The implemented foundation is stable enough to move into Phase 2 review. Later Phase 1 extensions remain intentionally deferred and are kept here for pitch, demo, and future planning context.

Implemented foundation files:

- `TOKEN-SLICER.md`: plan for context slicing, output style, project mapping, output slicing, tool sandboxing, project memory, reuse cache, pruning, and optional compression.
- `TOKEN-AUTOPILOT.md`: automatic token-saving activation rules.
- `context/TailTrail.map.md`: short file map for choosing what to load.
- `context/token-router.md`: tiny decision table for choosing the best token-saving lane.
- `context/slices.md`: named slices such as `core`, `review`, `aidlc`, and `examples`.
- `context/project-map.md`: compact project relevance map.
- `context/change-impact.md`: per-change impact note.
- `context/cache-index.md`: reusable summary index.
- `context/compression-policy.md`: exact-safe compression rules.
- `context/prune-rules.md`: stale-context cleanup rules.
- `templates/context-brief.md`: compact reusable project-context handoff.
- `templates/router-decision.md`: optional trace for why a token-saving lane was selected.
- `templates/impact-brief.md`: compact code relevance handoff.
- `templates/tool-summary.md`: compact MCP/browser/API response summary.
- `scripts/route-context.py`: deterministic Token Router CLI.
- `scripts/token-auto.py`: intelligent Token Autopilot CLI that skips tiny requests and routes non-trivial work.
- `context/intent-aliases.md`: short command map for TailTrail intent phrases.
- `context/flow-catalog.md`: named delivery, risk, review, handoff, and release flows.
- `context/review-lenses.md`: architecture, security, QA, maintainability, and dependency review lenses.
- `templates/intent-overrides.json`: override template for project or organization prompt customization.
- `templates/learnings.md`: lightweight project learnings template.
- `scripts/expand-intent.py`: deterministic intent expansion agent for phrases such as `use AIDLC` and `use AIDLC and review`.
- `scripts/update-copilot.py`: safe updater for existing Copilot TailTrail packs.
- `scripts/update-tailtrail.py`: general updater entry point.
- `scripts/team-init.py`: optional or required team guidance initializer.
- `scripts/learnings.py`: create, add, and show project learnings.
- target-project `tailtrail/.tailtrail-install.json`: generated in installed TailTrail packs, not stored in this source repo; tracks managed file hashes so updates can distinguish unchanged core files from local edits.
- `.tailtrail/token-router-state.json`: generated local state for the latest route decision.
- `.tailtrail/token-autopilot-state.json`: generated local state for the latest autopilot decision.
- `hooks/token-autopilot-hook.py`: optional automatic token-saving hook.
- `hooks/token-router-hook.py`: optional compact context-injection hook.
- `hooks/README.md`: hook usage and guardrails.

Automation boundary:

- Token Router and Token Autopilot are implemented as local Python CLIs.
- Hook-capable hosts can call the optional wrappers for automatic compact context guidance.
- Adapter-only assistants follow the same token-saving rules through instructions; they do not run automation unless the user or host invokes the scripts.
- Tiny, low-risk prompts are intentionally allowed to skip routing so TailTrail does not spend work to save less than it costs.
- Output slicing, cache reuse, pruning, graph-lite review mapping, and visual reference compression remain guided/manual patterns until the deferred helper scripts are implemented.

Deferred helpers still planned after Phase 1 foundation closure:

- Later: `scripts/slice-context.py` to print full content for only a requested slice.
- Later: `scripts/summarize-output.py` to reduce logs and terminal output.
- Later: `scripts/cache-summary.py` to reuse stable summaries.
- Later: `scripts/prune-context.py` to identify stale context.

To Be Implemented Later:

- **Code Review Graph Lite**: build a small Python-assisted impact map for reviews. It should identify changed files, likely callers, likely tests, shared helpers, and dependency boundaries using simple file/path/import signals before reading broad source areas. It should not become a full AST graph engine in Phase 1.
- **Review Impact Output**: add a compact graph-style summary that can be pasted into `context/change-impact.md` or `templates/impact-brief.md`. It should show `changed -> callers -> tests -> risks` in text first, with optional Mermaid later if useful.
- **Visual PNG Reference Compression**: explore converting bulky, stable, non-exact reference material into PNG snapshots only when text exactness is not required. This is for old process docs, historical reports, large diagrams, or visual summaries, not for code, diffs, configs, logs, commands, IDs, hashes, dependency versions, or security rules.
- **Compression Manifest**: if PNG reference compression is added, create a small manifest that records source path, generated image path, refresh date, invalidation rule, and exact-text fallback.
- **Router Integration**: extend `scripts/route-context.py` only after the above is proven manually. New routes should remain explicit, such as `review-graph` and `visual-reference`, and should keep exact text pass-through for risky material.

Implementation idea:

- Start with documentation, manual slicing, and a deterministic Python router.
- Use `context/TailTrail.map.md` as the default entry point instead of loading `TOKEN-SLICER.md` for routine work.
- Add Token Router before adding more token-saving mechanisms.
- Tighten routine response verbosity before adding machinery.
- Add graph-lite project mapping before broad source scanning.
- Add output summarization before any visual compression.
- Add tool sandboxing and cache rules before considering MCP integrations.
- Add pruning rules before long-session memory grows.
- Keep the active skills short and link to Token Slicer only for large or repeated work.
- Keep `scripts/route-context.py` as the only deterministic route-decision source; Token Autopilot and hooks should delegate to it instead of inventing separate routing rules.
- Add full slice-printing, output summarization, cache, and prune scripts only after the route decisions prove useful.
- Keep optional visual compression exact-safe and off by default.
- Defer full AST graphing, semantic search, visual compression runtime, auto hooks everywhere, global install, background services, and complex MCP proxy until reviewed with usage data.
- Keep the Phase 1 hook optional and quiet; do not enable broad automatic injection in plugin metadata.

Acceptance check:

- A user can choose one relevant context slice, identify likely source files, and summarize noisy output instead of loading every TailTrail Markdown file, broad source area, and raw terminal log.
- The self-check validates the manual Token Slicer files before any automation is added.
- `python3 scripts/route-context.py review` prints an automatic decision and writes local route state.
- `python3 scripts/token-auto.py "rename this variable"` skips routing.
- `python3 scripts/token-auto.py "review this diff for dependency risk"` routes to the review/dependency-aware path.
- `python3 hooks/token-autopilot-hook.py review this diff` prints compact automatic context guidance.
- `python3 hooks/token-router-hook.py review` prints a compact injection without loading full docs.
- `python3 scripts/expand-intent.py "use AIDLC and review"` expands a short user phrase into the full run order and prompt.
- A project can customize an expanded prompt with `.tailtrail/intent-overrides.json` or `tailtrail/intent-overrides.json`.
- `python3 scripts/update-copilot.py --root /path/to/project --dry-run` previews a TailTrail pack update.
- `python3 scripts/update-copilot.py --root /path/to/project` refreshes unchanged managed files and preserves local edits.
- `python3 scripts/update-copilot.py --root /path/to/project --strategy backup-overwrite` refreshes locally edited managed files after backing them up.
- `python3 scripts/update-tailtrail.py --root /path/to/project --dry-run` provides the general update command.
- `python3 scripts/team-init.py --root /path/to/project --mode optional` adds team guidance.
- `python3 scripts/learnings.py init --root /path/to/project` creates a durable learnings file.

## Phase 2: Portable AIDLC Pack

Purpose: add a lightweight AI Development Lifecycle that any repo can adopt without installing tools.

Status: completed end to end. The portable lifecycle, templates, stage playbooks, dependency gate, handoff rules, security/testing baselines, initializer, checker, token-router integration, and documentation are implemented. The final cleanup fixed comprehensive-depth validation so freshly initialized question files pass structural checks, while `--strict-answers` can enforce completed answers later.

Implemented files:

- `AIDLC.md`: define the lifecycle from request to handoff.
- `DEPENDENCY-GATE.md`: define the rule for adding or rejecting dependencies.
- `templates/change-brief.md`: short pre-change template for goal, context, smallest change, risks, and validation.
- `templates/diff-handoff.md`: short post-change template for changed, reused, skipped, validation, and risk.
- `templates/aidlc-state.md`: lightweight state tracker for phase, stage, approvals, and next step.
- `templates/aidlc-audit.md`: lightweight audit log for user requests, decisions, approvals, and generated artifacts.
- `templates/question-file.md`: standard question file format with choices, recommended option, reasoning, and answer slots.
- `templates/stage-gate.md`: standard approval gate format for phase completion.
- `templates/requirements.md`: portable requirements artifact.
- `templates/workflow-plan.md`: portable workflow planning artifact.
- `templates/implementation-plan.md`: portable construction planning artifact.
- `templates/validation-handoff.md`: portable build/test handoff artifact.
- `templates/operations-notes.md`: portable operations handoff artifact.
- `aidlc/stages/`: stage playbooks for day-to-day lifecycle execution.
- `aidlc/extensions/`: security and testing baselines.
- `scripts/aidlc-init.py`: create `aidlc-docs/` in target projects.
- `scripts/aidlc-check.py`: validate minimum AIDLC artifact shape, with optional `--strict-answers` enforcement for completed question files.

Implementation idea:

- Used `aidlc-rules/` only as reference; TailTrail files use original wording and a smaller workflow.
- Keep `AIDLC.md` as the portable lifecycle map, not a giant rulebook.
- Define three phases:
  - **Inception**: understand request, workspace, requirements, user impact, and plan.
  - **Construction**: design only as needed, implement in approved units, build, and test.
  - **Operations**: capture deployment, monitoring, rollback, and support notes when relevant.
- Define always-run stages:
  - workspace detection
  - intent and requirements analysis
  - workflow planning
  - implementation planning for non-trivial work
  - build/test or validation handoff
- Define conditional stages:
  - reverse engineering for brownfield systems
  - user stories for user-facing or stakeholder-heavy work
  - application/design notes for new components or changed boundaries
  - NFR/security/performance notes when risk or scope requires them
  - operations notes when deployment or production support is in scope
- Use adaptive depth:
  - **minimal** for clear, low-risk changes
  - **standard** for normal feature/bug work
  - **comprehensive** for broad, high-risk, regulated, or multi-team work
- Store lifecycle artifacts under `aidlc-docs/` in target projects; never put application code there.
- Use `aidlc-docs/aidlc-state.md` to resume work and avoid rediscovering the phase/stage on every run.
- Use `aidlc-docs/audit.md` to record raw user requests, important decisions, approval gates, and completed artifacts.
- Ask clarifying questions in a question file for non-trivial ambiguity instead of long chat threads.
- Include a recommended option and reasoning after each question so users can review the default path before answering.
- Require explicit approval gates before moving from requirements to planning, planning to implementation, and implementation to build/test for standard or comprehensive depth.
- Integrate Token Router:
  - AIDLC requests load the `aidlc` slice.
  - resume requests load `aidlc-state.md`, not every artifact.
  - construction work loads only the current unit plan plus exact source files.
  - build/test work uses Output Slicer for logs.
- Keep each portable file concise; detailed future stage rules should live in optional references loaded by slice.

Implemented integration:

- `@tailtrail` uses AIDLC only when lifecycle structure adds value.
- `@tailtrail-review` applies the dependency gate and diff handoff shape when relevant.
- `context/slices.md` routes AIDLC work to only the active lifecycle files.
- `scripts/route-context.py` routes `aidlc`, `lifecycle`, `audit`, and `handoff` requests.
- `scripts/check-tailtrail.py` validates the new files exist.

Implementation sequence completed:

1. Add `AIDLC.md` with the phase/stage map, adaptive depth rules, artifact locations, and approval gates.
2. Add templates for state, audit, questions, stage gates, change brief, and diff handoff.
3. Add `DEPENDENCY-GATE.md`.
4. Update `context/slices.md` so `aidlc` points to `AIDLC.md` and only the needed templates.
5. Update skills with one short instruction: use AIDLC for non-trivial lifecycle work, not every tiny edit.
6. Update `DESIGN.md`, `README.md`, and `scripts/check-tailtrail.py`.
7. Add V2 stage playbooks, handoff guidance, security/testing baselines, and AIDLC scripts.

Acceptance check:

- A developer can copy `AGENTS.md`, `AIDLC.md`, `DEPENDENCY-GATE.md`, and `templates/` into another repo and get a useful AI-assisted workflow without installing anything.
- A simple bug fix can run at minimal depth without creating heavy artifacts.
- A larger feature can create state, audit, questions, requirements, plan, implementation handoff, and validation handoff in `aidlc-docs/`.
- A resumed session can read `aidlc-docs/aidlc-state.md` and continue without loading every prior artifact.
- A target project can be initialized with `python3 scripts/aidlc-init.py --root /path/to/project --depth standard`.
- A target project can be checked with `python3 scripts/aidlc-check.py --root /path/to/project`.
- A comprehensive target project can be initialized and structurally checked before question answers are filled in.
- Completed question files can be enforced with `python3 scripts/aidlc-check.py --root /path/to/project --strict-answers`.
- Handoff work can route through `python3 scripts/route-context.py handoff`.

## Phase 2.5: Agent Guardrails

Purpose: reduce hallucination, unsupported confidence, unsafe edits, and absurd automation decisions before TailTrail is adopted by more teams.

Status: completed end to end. The guardrail contract, evidence and risk templates, core guidance links, assistant adapter links, token-slice guidance, router reminders, managed pack inclusion, and validation checks are implemented. Guardrails remain documentation-first in this phase; no automated policy engine or silent behavior mutation was added.

Why it is needed:

- TailTrail is meant to guide coding agents across company repositories, where a wrong confident answer can create security, compliance, production, or review risk.
- More TailTrail features mean more choices for the agent: AIDLC depth, review lenses, dependency gates, handoff, token routing, updates, and future learning. Guardrails make those choices explainable and bounded.
- Enterprise users need a clear behavior contract: what the agent must inspect, what it may not claim, what it must preserve, and when it must ask or stop.
- Guardrails should be lightweight and portable, not a heavy policy engine.

Planned files:

- `GUARDRAILS.md`: canonical guardrail contract for evidence, action limits, uncertainty, risky changes, validation claims, and escalation points.
- `templates/evidence-note.md`: short reusable summary of files read, commands run, checks performed, assumptions, skipped areas, and residual risk.
- `templates/risk-callout.md`: compact format for calling out risky decisions before implementation or review signoff.
- Optional `tailtrail-policy.example.md` update: show how a team can add local guardrails without editing TailTrail core files.

Guardrail categories:

- **Read-before-change guardrail**: no code change before inspecting relevant files, callers, tests, and existing project conventions.
- **Evidence guardrail**: non-trivial answers must identify the evidence used, including files read, commands run, tests/checks run, assumptions, and skipped areas.
- **Uncertainty guardrail**: unknown facts must be labeled as unknown; the agent should inspect or ask instead of inventing details.
- **Dependency guardrail**: no new, upgraded, replaced, or removed dependency without applying `DEPENDENCY-GATE.md`.
- **Scope guardrail**: no broad rewrite, formatting churn, architectural move, or unrelated cleanup unless explicitly requested or approved through AIDLC.
- **Safeguard preservation guardrail**: do not remove or weaken authentication, authorization, validation, escaping, logging, auditability, rate limiting, accessibility, data integrity, privacy, or error handling to make code shorter.
- **Destructive action guardrail**: do not delete files, reset git state, rewrite history, remove tests, drop migrations, or overwrite local edits unless the user explicitly approves.
- **Validation truth guardrail**: do not claim tests passed, code was pushed, a deployment happened, or a check succeeded unless the command actually ran and succeeded.
- **Exactness guardrail**: preserve exact text for code, diffs, configs, commands, IDs, paths, hashes, dependency versions, security rules, logs being debugged, and policy text.
- **Token-saving guardrail**: token optimization must not hide material facts. Use exact pass-through for high-risk content and summarize only when exactness is not required.
- **AIDLC escalation guardrail**: broad, risky, ambiguous, regulated, multi-team, or long-running work should use AIDLC state, questions, and approval gates before implementation.
- **Review guardrail**: review output should lead with concrete findings and file references; if there are no findings, say that clearly and mention residual risk.

Implementation idea:

- Start with documentation only: add `GUARDRAILS.md` and two small templates.
- Link `GUARDRAILS.md` from `AGENTS.md`, `AIDLC.md`, `DEPENDENCY-GATE.md`, `TOKEN-SLICER.md`, and both Codex skills.
- Update adapter files so Claude, Cursor, Copilot, ChatGPT, and Gemini know where the guardrail contract lives.
- Add the guardrails file to `context/slices.md` only where needed:
  - `core` loads a short guardrail pointer, not the full file every time.
  - `review` loads review and evidence guardrails.
  - `aidlc` loads escalation, approval, and evidence guardrails.
  - `dependency` loads dependency and validation truth guardrails.
- Add `scripts/check-tailtrail.py` checks for `GUARDRAILS.md`, the templates, and required links.
- Update `scripts/route-context.py` so risky routes include a guardrail reminder without loading every guardrail section.
- Keep guardrails human-readable and explicit. Do not build an automated policy engine in this phase.

Acceptance check:

- A developer can read `GUARDRAILS.md` and understand what TailTrail agents must never claim or do without evidence.
- A normal implementation prompt reminds the agent to inspect relevant files before editing.
- A dependency prompt routes through `DEPENDENCY-GATE.md` and does not recommend packages casually.
- A review prompt requires findings to be evidence-backed and grounded in changed files or callers.
- A token-saving prompt preserves exact risky text and does not over-summarize code, diffs, configs, logs, or policies.
- A broad or risky prompt escalates to AIDLC instead of jumping straight into implementation.
- The self-check fails if the guardrail file or required links are missing.

## Phase 2.6: Guardrail Layers

Purpose: add compact feature-level guardrail sections so TailTrail can apply the right checks for implementation, code consistency, review, QA, dependency, AIDLC, handoff, CI/Sonar, release, and token-saving work without duplicating every rule.

Status: completed end to end. The layered guardrail context, code consistency layer, router routes, intent-expansion load hints, install-pack pointer, package validation, and user/design docs are implemented. The implementation stayed documentation-first and deterministic; no hidden policy engine or automatic enforcement layer was added.

Feature rating:

```text
Usefulness: 8 / 10
Enterprise value: 8.5 / 10
Risk if overbuilt: 7 / 10
Recommended timing: next, before or with Navigator
```

Problem to solve:

- Broad guardrails can miss ground-level checks for QA, Sonar, release, dependency, and handoff work.
- Code can drift across a repo when agents invent new naming, structure, validation, error handling, logging, test, or formatting patterns without inspecting nearby files.
- Review, QA, handoff, dependency, and policy features can overlap and cause off-drift if the agent loads everything or applies the wrong workflow.
- Enterprise users need exact feature-specific "do not miss" checks without forcing every prompt to load a large rulebook.
- Token-saving should still work: the agent should load only the layer relevant to the current task.

Design principle:

- Use one compact layered file instead of many scattered guardrail files.
- Feature layers must extend `GUARDRAILS.md`, not replace or weaken it.
- Load only the relevant layer for the task.
- Keep each section short enough for token-safe routing.
- Do not add a hidden policy engine, broad automatic enforcement, or silent behavior mutation in this phase.

Implemented file:

- `context/guardrail-layers.md`: recommended location because this is route/slice support context, not a new top-level rulebook.

Planned layers:

- **Global pointer**: always apply `GUARDRAILS.md`, local policy if present, and validation-truth rules.
- **Implementation**: read relevant code first, preserve safeguards, make the smallest maintainable change, and avoid unrelated rewrites.
- **Code Consistency**: inspect nearby naming, structure, imports, validation style, error handling, logging, tests, and formatting before adding a new local pattern.
- **Review**: lead with evidence-backed findings, avoid style-only churn, and check changed files, callers, tests, dependencies, and safeguards.
- **QA / validation**: keep validation claims exact, preserve reproducible commands, and separate passed, failed, skipped, and not-run checks.
- **Dependency**: apply `DEPENDENCY-GATE.md`, prefer standard/platform/current dependencies, and preserve approval notes.
- **AIDLC**: use lifecycle depth, state, questions, stage gates, and audit notes for broad or risky work.
- **Handoff**: capture changed files, validation, skipped work, risks, next owner, approvals, and rollback where relevant.
- **CI/Sonar**: preserve exact rule IDs, job names, stages, failing lines, logs, and remediation evidence.
- **Release**: capture deployment scope, environment, approval, rollback, monitoring, and post-release checks.
- **Token Saving**: summarize only safe context, preserve exact risky text, and prefer slices over full-document loading.

Implemented integration:

- `context/guardrail-layers.md` has compact sections and direct pointers to source files.
- `context/slices.md` points implementation, code consistency, review, dependency, AIDLC, handoff, output, release, and token-saving work to the relevant layer.
- `scripts/route-context.py` includes layer-aware routes for implementation, review, dependency, AIDLC, handoff, output, QA, CI/Sonar, release, exact pass-through, compression, and router work.
- `scripts/expand-intent.py` includes layer hints for short commands such as `use review`, `use QA`, `use handoff`, `use dependency gate`, `use CI Sonar`, `use release flow`, and `use AIDLC and review`.
- `scripts/check-tailtrail.py` validates the layered file and required references.
- `scripts/install-copilot.py` points installed Copilot packs to `context/guardrail-layers.md`.
- `README.md`, `USER-GUIDE.md`, and `DESIGN.md` describe the feature.
- Keep local policy in `tailtrail-policy.md` as the team override layer; do not duplicate local policy rules inside the layer file.
- Do not create separate `qa-guardrails.md`, `review-guardrails.md`, `sonar-guardrails.md`, or similar files unless real usage proves a layer has grown too large.

Acceptance check:

- A QA task can load the QA/validation layer without loading every guardrail layer.
- A Sonar or CI task preserves exact rule ID, job, stage, failing line, log excerpt, and evidence.
- A dependency task uses `DEPENDENCY-GATE.md` plus the dependency layer before suggesting a package.
- An implementation or review task checks nearby code consistency before inventing naming, structure, validation, error handling, logging, test, or formatting patterns.
- A review task produces evidence-backed findings without style-only churn or broad rewrite advice.
- A handoff or release task captures changed files, validation, skipped work, risks, next owner or approval, and rollback when relevant.
- Token-saving routes never summarize exact-risk material such as code, diffs, configs, logs being debugged, IDs, dependency versions, or policy text.
- The self-check fails if `context/guardrail-layers.md` or required links are missing.

## Phase 3: Local Policy Override

Purpose: let each repository adapt TailTrail without editing the base skill.

Status: completed end to end. The prompt override foundation was already implemented, and this phase now adds `tailtrail-policy.example.md`, active-policy guidance for `tailtrail-policy.md`, core skill/adapter references, context/router references, managed pack inclusion, and validation checks. No config parser, runtime hook, or hidden policy engine was added.

Implemented prompt override foundation:

- `templates/intent-overrides.json`: optional local prompt override template for intent expansion.
- `scripts/expand-intent.py`: reads overrides from `--overrides`, `TAILTRAIL_INTENT_OVERRIDES`, `.tailtrail/intent-overrides.json`, or `tailtrail/intent-overrides.json`.

Implemented broader policy file:

- `tailtrail-policy.example.md`: optional local policy template for team-specific commands, dependency approval rules, test commands, API conventions, and security checks.

Implementation idea:

- Document that agents should read `tailtrail-policy.md` if present in the target repo.
- Keep the example generic and original.
- Do not require a config parser or runtime hook.
- Keep prompt overrides narrow and explicit; do not turn them into a hidden policy engine.

Acceptance check:

- A team can create `tailtrail-policy.md` in a project and TailTrail can follow it as plain text guidance.
- A team can create `tailtrail/intent-overrides.json` in an installed pack and change the internal prompt for one flow without changing core TailTrail files.

## Phase 3.5: Policy Packs

Purpose: support organization and repository policy without editing TailTrail core files or creating a hidden central service.

Status: completed end to end. TailTrail now supports a Markdown local policy file, an optional structured policy override template, a local policy initializer/checker, command-surface wiring, managed-pack inclusion, and documentation. The implementation stays local and reviewable: no remote policy service, no hidden policy engine, and no automatic weakening of TailTrail guardrails.

Problem to solve:

- Enterprise teams need consistent policy around dependencies, testing, security, CI/Sonar expectations, ownership, restricted folders, generated code, and review gates.
- Teams should not fork TailTrail core files to encode local rules.
- Policy must be readable, reviewable, and easy to remove.

Planned files:

- `tailtrail-policy.example.md`: source example for repo/team policy. Implemented.
- `templates/policy-overrides.json`: optional structured policy override template. Implemented.
- `scripts/policy-check.py`: local validator for policy shape and required sections. Implemented.

Target-project files:

- `tailtrail-policy.md`: human-readable local project policy.
- `.tailtrail/policy-overrides.json`: optional local structured overrides.

Policy areas:

- dependency approval expectations
- required validation commands
- security baseline additions
- CI/Sonar expectations
- code ownership and reviewer expectations
- restricted folders or generated-code boundaries
- data/privacy handling notes
- release and rollback expectations

Implementation idea:

- Start with Markdown policy only. Completed in Phase 3.
- Add `scripts/policy-check.py` only after teams use the policy file enough to know what should be validated. Completed in Phase 3.5 with shape checks only.
- Keep policy local and explicit. Completed.
- Let `scripts/route-context.py dependency`, `review`, `aidlc`, and future `navigator` mention local policy when present. Completed; routing and Navigator already recognize local policy.
- Do not create a remote policy service in this phase. Completed.

Implemented commands:

```bash
python3 scripts/tailtrail.py policy init --root .
python3 scripts/tailtrail.py policy init --root . --with-overrides
python3 scripts/tailtrail.py policy check --root .
python3 scripts/tailtrail.py policy check --root . --with-overrides --strict
```

Implemented behavior:

- `init` copies `tailtrail-policy.example.md` to `tailtrail-policy.md`.
- `init --with-overrides` also creates `.tailtrail/policy-overrides.json` from `templates/policy-overrides.json`.
- `check` validates required Markdown headings.
- `check --with-overrides` validates the optional structured override keys and basic value shapes.
- `check --strict` warns about starter placeholders and empty command sections.
- Output supports Markdown or JSON.

Acceptance check:

- A project can add `tailtrail-policy.md` and use it without changing TailTrail core files. Completed.
- A policy check can confirm required headings without interpreting every rule. Completed.
- TailTrail agents can mention local policy in dependency, review, AIDLC, and release work. Completed through router/Navigator guidance and docs.
- Local policy can extend TailTrail guardrails without weakening them silently. Completed through policy wording and checker warnings.

## Phase 4: Lifecycle Hooks

Purpose: reduce repeated prompt typing only after the Markdown workflow is stable.

Status: completed end to end for the first quiet hook. TailTrail now has an optional lifecycle hook that expands short commands, runs Token Autopilot, prints compact context guidance, and writes local hook state. Hooks remain opt-in and are not enabled by plugin metadata.

Implemented behavior:

- Optional startup reminder that TailTrail is available.
- Optional prompt/context injection for Codex-compatible hosts.
- Optional compact lifecycle state at `.tailtrail/lifecycle-hook-state.json`.
- No persistent skill mode state.

Implemented files:

- `hooks/tailtrail-lifecycle-hook.py`: combines `scripts/expand-intent.py` and `scripts/token-auto.py`.
- `hooks/README.md`: explains lifecycle, token autopilot, and token router hooks.

Implementation notes:

- Keep hooks off by default.
- Put hook code under `hooks/`; host-specific wiring remains external and opt-in.
- Keep hook output quiet: no repeated banners, no noisy reminders.
- Do not inject full TailTrail docs, raw logs, source files, or cached state.
- Include hooks in installed packs so teams can wire them locally.
- Keep plugin metadata unchanged until a specific host integration proves useful.

Acceptance check:

- `python3 hooks/tailtrail-lifecycle-hook.py --startup --no-state` prints a compact command reminder.
- `python3 hooks/tailtrail-lifecycle-hook.py "use AIDLC and review" --no-state` expands the lifecycle/review flow and token decision.
- `python3 hooks/tailtrail-lifecycle-hook.py "rename this variable" --no-state` can skip token routing for tiny work.
- Hooks improve daily usage without changing the core skill behavior or creating noisy sessions.

## Phase 5: Global Installer

Purpose: make local installation repeatable for internal users.

Status: completed for the first local installer and optional launcher. The implementation is a safe local setup assistant plus an explicit `tailtrail` launcher installer. It validates the TailTrail repo, supports a small profile set, dry-runs target changes, reuses existing installers, creates a user-approved command launcher when requested, and tracks deferred global behavior.

Implemented behavior:

- A tiny script that checks the repo shape, prints install instructions, and optionally prepares a local plugin path.
- No network calls.
- No silent global writes.
- Optional launcher write through `python3 scripts/tailtrail.py install launcher`, usually to `~/.local/bin/tailtrail`.
- Dry-run support before target writes.
- Limited profiles only: `inspect`, `generic`, `copilot`, `aidlc`, `hooks`, and `full`.
- Target-project writes reuse existing scripts where possible.

Implemented file:

- `scripts/install-local.py`: local setup assistant for inspecting TailTrail and preparing a target project.
- `scripts/install-launcher.py`: explicit installer for a small `tailtrail` executable that points back to this checkout and can be used from any repo.

Implemented profiles:

- `inspect`: validate TailTrail and print capabilities, recommended start commands, and deferred work.
- `generic`: copy `AGENTS.md` to a target project.
- `copilot`: run the existing managed Copilot pack installer.
- `aidlc`: run the existing AIDLC initializer.
- `hooks`: print lifecycle hook commands without enabling hooks globally.
- `full`: Copilot pack, AIDLC docs, team guidance, and hook command hints.

Not implemented yet:

- Global Codex config writes.
- Shell profile edits.
- IDE setting changes.
- Network install or dependency download.
- Auto-enabling hooks everywhere.
- Assistant-specific installers beyond the existing Copilot managed pack.
- Additional install profiles beyond the small initial set.
- OS/package-manager installers.

Acceptance check:

- A teammate can set up TailTrail locally from this repo without guessing which files matter.
- `python3 scripts/install-local.py --inspect` validates the repo and prints supported profiles.
- `python3 scripts/tailtrail.py install launcher --dry-run` previews the launcher path.
- `python3 scripts/tailtrail.py install launcher` creates a `tailtrail` command when the user approves the write.
- `python3 scripts/install-local.py --target /path/to/project --profile full --dry-run` previews a full target-project setup.
- `python3 scripts/install-local.py --target /path/to/project --profile generic` can add portable guidance only.
- `python3 scripts/install-local.py --target /path/to/project --profile hooks` prints hook commands without enabling anything globally.

## Phase 6: Multi-Agent Adapters

Purpose: support other local coding tools without changing TailTrail's core guidance.

Status: completed end to end for validated instruction-adapter support. Codex remains the strongest and deepest path. Claude, Cursor, GitHub Copilot, ChatGPT, and Gemini are supported through portable instruction adapters with a validated behavior contract, assistant-specific prompt packs, and an explicit compatibility matrix.

Implemented adapters:

- Claude adapter: `CLAUDE.md`.
- Cursor adapter: `.cursor/rules/tailtrail.mdc`.
- GitHub Copilot adapter: `.github/copilot-instructions.md`.
- ChatGPT adapter: `.openai/chatgpt-instructions.md`.
- Gemini adapter: `GEMINI.md`.
- Generic `AGENTS.md` copy path remains the default.

Implemented hardening:

- Compatibility matrix: `ASSISTANT-COMPATIBILITY.md`.
- Prompt packs:
  - `adapters/prompts/codex.md`
  - `adapters/prompts/claude.md`
  - `adapters/prompts/cursor.md`
  - `adapters/prompts/copilot.md`
  - `adapters/prompts/chatgpt.md`
  - `adapters/prompts/gemini.md`
- Adapter behavior contract validation in `scripts/sync-adapters.py`.
- Unified commands:
  - `python3 scripts/tailtrail.py adapters check`
  - `python3 scripts/tailtrail.py adapters sync`
- Tests:
  - adapter source/target sync
  - required adapter contract phrases
  - `tailtrail adapters check` CLI dispatch

Validated adapter contract:

- Navigator-first workflow for non-trivial tasks.
- Approval before implementation.
- Post-change review after code changes.
- Scanner approval before Sonar, vulnerability, audit, build, broad test, or heavy local commands.
- Learnings are advisory and never override current source, CI, scanners, policy, guardrails, or explicit user direction.
- Token-saving claims stay estimated unless measured telemetry is provided.
- Evidence labels are explicit: heuristic, local-ast, provider-backed, measured/validated.
- `tailtrail-policy.md` is respected when present without weakening safety rules.

Implementation idea:

- Generate adapters from TailTrail-owned wording only.
- Keep each adapter short.
- Keep source adapter files under `adapters/`.
- Use `scripts/sync-adapters.py` to check or write tool-facing files.
- Do not duplicate long AIDLC, roadmap, or token-slicer content into adapters.

Acceptance check:

- Each adapter can be removed without affecting the Codex plugin.
- `python3 scripts/sync-adapters.py --check` passes.
- `python3 scripts/tailtrail.py adapters check` passes.
- `python3 scripts/check-tailtrail.py` validates adapter files are present and synced.

Remaining boundary:

- TailTrail should claim validated adapter coverage, not identical assistant behavior. Real behavior still depends on each assistant's instruction loading, local tool access, and user approval flow.

## Phase 7: Benchmark Harness

Purpose: measure whether TailTrail improves code review outcomes before claiming broad impact.

Status: completed end to end for the first offline artifact harness. The benchmark uses saved scenario outputs, deterministic scoring, Markdown/JSON reports, and no model calls or network calls.

Implemented behavior:

- Small local scenarios only.
- Compare baseline and TailTrail artifact outputs.
- Score dependency discipline, safeguard preservation, root-cause focus, CI/Sonar exactness, validation clarity, and review specificity.
- Produce Markdown or JSON reports.
- Avoid model/vendor-specific claims.

Implemented files:

- `benchmarks/README.md`: benchmark scope, usage, and claim boundaries.
- `benchmarks/scenarios/native-date-field/`: native capability and dependency discipline.
- `benchmarks/scenarios/preserve-validation/`: safeguard preservation and false validation claims.
- `benchmarks/scenarios/shared-bug-fix/`: shared root-cause fix behavior.
- `benchmarks/scenarios/ci-sonar-review/`: CI/Sonar exactness and remediation evidence.
- `benchmarks/results/.gitkeep`: result output folder.
- `templates/benchmark-result.md`: manual result note shape.
- `scripts/benchmark-tailtrail.py`: deterministic offline scorer.

Implemented metrics:

- pattern-based pass/miss checks per scenario
- baseline score
- TailTrail score
- score delta
- per-check explanation
- JSON result for automation-friendly review
- Markdown result for human review

How to explain the benchmark score:

The benchmark compares two saved artifacts for each scenario:

- **Baseline output**: a normal answer without TailTrail guidance.
- **TailTrail output**: an answer written with TailTrail guidance.

Each scenario has a small `expected.json` file with checks worth points. A check can reward good behavior, such as mentioning native/platform capability, or penalize bad behavior, such as suggesting a needless dependency or making a false test claim.

Current sample result:

```text
Baseline: 4 / 32
TailTrail: 32 / 32
Delta: +28
```

Plain-English explanation:

- The four sample scenarios are worth 32 total points.
- The baseline artifacts earned 4 points because they showed some useful behavior but missed most TailTrail expectations.
- The TailTrail artifacts earned 32 points because they matched every expected behavior in the current sample suite.
- The `+28` delta means TailTrail-guided artifacts scored 28 points higher than the baseline artifacts on these local scenarios.

Concrete example:

```text
Scenario: Native Date Field

Task:
Add a date field to a form.

Baseline behavior:
Suggests adding a date picker package and replacing part of the form.

TailTrail behavior:
Suggests using a native date input first, preserving validation, avoiding a new dependency, and keeping the change focused.

Why TailTrail scores higher:
- prefers platform/native capability
- avoids unnecessary dependency ownership
- preserves validation
- keeps scope small
```

How to present this safely:

- Say: "On these local benchmark artifacts, TailTrail scored higher on dependency discipline, safeguard preservation, root-cause focus, and exact CI/Sonar evidence."
- Do not say: "TailTrail always improves every model by this amount."
- Do not say: "TailTrail guarantees safe code."
- Do not use the sample score as a vendor/model-wide claim.

Why this matters:

- It gives a repeatable way to decide whether TailTrail guidance is useful or noisy.
- It makes improvement visible before making enterprise claims.
- It shows where TailTrail needs more benchmark scenarios before broader rollout.

Not implemented yet:

- live model execution
- multi-model comparison
- exact token API accounting and measured token-savings telemetry
- larger benchmark suite
- statistical reporting
- CI dashboard
- human reviewer calibration workflow
- benchmark UI
- company-specific benchmark packs
- private-code benchmarks

Acceptance check:

- The benchmark helps decide whether a TailTrail rule should stay, change, or be removed.
- TailTrail can show local score deltas without making vendor-specific claims.
- Benchmark results distinguish useful guardrails from process noise.
- `python3 scripts/benchmark-tailtrail.py` prints a Markdown scorecard.
- `python3 scripts/benchmark-tailtrail.py --format json` prints machine-readable results.
- `python3 scripts/benchmark-tailtrail.py --scenario native-date-field` runs one scenario.

## Phase 7.0a: Token Savings Telemetry Guardrail

Purpose: prevent TailTrail from claiming exact token savings unless it has real model/API usage metadata, while still allowing clearly labeled local estimates for demos and planning.

Status: light version implemented. TailTrail can estimate local context reduction and can report measured savings from user-provided telemetry JSONL. Deeper provider adapters, pricing analysis, and automatic usage capture remain backlog.

Problem to solve:

- Token savings are useful for product demos, leadership updates, and adoption confidence.
- TailTrail can estimate avoided context by comparing selected slices against skipped files or raw logs.
- Estimates are not the same as real model/API billing or token usage.
- Exact claims such as "TailTrail saved 82.95%" should require measured provider/model usage data.

Design principle:

- Use two separate modes: **estimated** and **measured**.
- Estimated mode can use local approximations such as file size, character count, selected slices, summarized logs, and skipped guidance files.
- Measured mode must use real usage metadata from a model/provider run, such as input tokens, output tokens, total tokens, model name, request or run id, timestamp, and task id.
- Every report must label token savings as `estimated`, `measured`, `mixed`, or `unknown`.
- Never present estimated savings as exact savings.
- Never infer billing impact unless usage metadata and pricing inputs are explicitly provided.

Implemented behavior:

- Add an estimate command for local dry runs and demos.
- Add a measured report command when users provide normalized API/model usage metadata.
- Add report wording that refuses exact claims when measured telemetry is missing.
- Keep all usage records local by default.

Implemented files:

- `scripts/token-savings.py`: estimate and report token savings.
- `templates/token-savings-report.md`: human-readable savings report with clear labels.
- optional generated `.tailtrail/token-usage.jsonl`: local normalized usage records, ignored by default unless a repo chooses to keep it.

Example normalized record:

```json
{
  "task_id": "2026-07-12-auth-fix",
  "mode": "measured",
  "provider": "openai",
  "model": "gpt-5-codex",
  "baseline": {
    "input_tokens": 48000,
    "output_tokens": 4200,
    "total_tokens": 52200
  },
  "tailtrail": {
    "input_tokens": 7600,
    "output_tokens": 1300,
    "total_tokens": 8900
  },
  "saved_tokens": 43300,
  "reduction_percent": 82.95,
  "source": "api_usage_metadata"
}
```

Example commands:

```bash
python3 scripts/token-savings.py estimate --used context/slices.md --avoided ROADMAP.md USER-GUIDE.md
python3 scripts/token-savings.py report --telemetry .tailtrail/token-usage.jsonl
```

Safe wording examples:

- Estimated mode: "Estimated context reduction: about 80%, based on local file-size/token approximation."
- Measured mode: "Measured token reduction: 82.95%, based on provider usage metadata for this run."
- Missing telemetry: "Exact token savings are unavailable because no model/API usage metadata was provided."

Acceptance check:

- TailTrail can show estimated token savings without overstating precision.
- TailTrail can show measured token savings only when real usage metadata exists.
- Reports clearly label the evidence level.
- The feature supports enterprise demos without creating misleading ROI claims.

Remaining backlog:

- provider-specific telemetry adapters
- automatic usage capture from supported hosts
- pricing inputs and cost reporting
- benchmark-integrated savings trend reports
- enterprise reporting rollups

## Phase 7.1: Benchmark Behavior Analyzer

Purpose: use benchmark results as a small evidence-driven "brain" that analyzes TailTrail behavior, detects discrepancies, and recommends improvement areas without changing TailTrail automatically.

Status: completed end to end for the first deterministic analyzer. It reads benchmark JSON, maps misses to risk themes, identifies discrepancies, and recommends improvement areas without editing TailTrail automatically.

Naming:

- Preferred feature name: **TailTrail Behavior Analyzer**.
- Avoid calling it "self-healing" in early versions because it should not modify TailTrail automatically.
- It can become part of the later TailTrail Quality Loop, but it should start as a small benchmark analyzer.

Problem to solve:

- Benchmark scores show pass/fail results, but users still need help interpreting what the misses mean.
- A low score should point to a likely TailTrail weakness, such as weak validation wording, noisy review behavior, missing dependency guidance, or overuse of lifecycle process.
- Repeated misses across scenarios should become visible before TailTrail is pitched broadly.
- Improvement ideas should be evidence-backed, not based on vague impressions.

Design principle:

- Keep the benchmark scorer and analyzer separate.
- Use benchmark JSON as the input.
- Produce recommendations, not automatic edits.
- Keep output reviewable and concise.
- Do not log raw user prompts or private repo content.
- Do not claim benchmark analysis proves universal model behavior.

Implemented files:

- `scripts/analyze-benchmark.py`: read benchmark JSON and produce behavior analysis.
- `templates/behavior-analysis.md`: human-readable output shape.
- optional generated `benchmarks/results/latest-analysis.md`: local report ignored by default.

Implemented command flow:

```bash
python3 scripts/benchmark-tailtrail.py --format json > benchmarks/results/latest.json
python3 scripts/analyze-benchmark.py benchmarks/results/latest.json
python3 scripts/analyze-benchmark.py benchmarks/results/latest.json --format json
python3 scripts/analyze-benchmark.py benchmarks/results/latest.json --write-result
```

Implemented analysis categories:

- **Strong areas**: scenario checks where TailTrail consistently passes.
- **Weak areas**: checks TailTrail misses.
- **Baseline gaps**: places where TailTrail improves sharply over baseline.
- **Discrepancies**: unexpected results, such as baseline passing while TailTrail fails.
- **Risk themes**: validation truth, dependency discipline, safeguard preservation, exactness, scope control, code consistency, and handoff clarity.
- **Recommended improvements**: doc wording, guardrail layer changes, intent expansion changes, new scenarios, or stricter benchmark checks.
- **Proposed file changes**: likely impacted files, suggested line anchors, and prompt wording to review before editing.

Recommendation safety note:

- Analyzer recommendations are advisory only.
- The output must tell users to review the impacted files, line numbers, and proposed prompt wording before adding anything.
- Suggested line numbers are anchors found from current file content, not guaranteed edit locations.
- The analyzer should make the next human review easier; it should not silently change TailTrail behavior.

Detailed example:

This example shows how the analyzer turns a plain score into an actionable engineering discussion.

Step 1: run the benchmark and save JSON:

```bash
python3 scripts/benchmark-tailtrail.py --format json > benchmarks/results/latest.json
```

Step 2: run the analyzer:

```bash
python3 scripts/analyze-benchmark.py benchmarks/results/latest.json
```

Example benchmark signal:

```text
Scenario: preserve-validation
Baseline: 2 / 8
TailTrail: 6 / 8
TailTrail missed:
- avoids_false_test_claim
```

What this means:

- TailTrail is still better than the baseline in this scenario because it scored `6 / 8` while baseline scored `2 / 8`.
- The result is not perfect because TailTrail missed `avoids_false_test_claim`.
- The missed check maps to the **validation truth** risk theme.
- The analyzer treats this as high priority because false claims about tests, CI, or validation reduce trust quickly in enterprise use.
- The analyzer should recommend a human-reviewed improvement, not silently change TailTrail files.

Example analyzer output:

```text
# TailTrail Behavior Analysis

## Benchmark Summary

- Baseline: `2 / 8`
- TailTrail: `6 / 8`
- Delta: `+4`

## Weak Areas

- HIGH: validation truth in `preserve-validation`
  - Check: `avoids_false_test_claim`
  - Evidence: TailTrail implied validation was complete without exact command evidence.

## Recommended Improvements

- HIGH: Strengthen validation-truth wording and add another false-validation benchmark scenario.
  - Theme: validation truth
  - Likely files: `GUARDRAILS.md`, `context/guardrail-layers.md`, `skills/tailtrail-review/SKILL.md`
  - Evidence: preserve-validation missed avoids_false_test_claim
  - Proposed file changes:
    - `GUARDRAILS.md` near line `12`: review and add or strengthen nearby guidance.
      Prompt change: Do not claim validation, tests, CI, or scanner checks passed unless exact commands, jobs, or evidence were actually run or provided. If validation was not run, say so plainly and name the smallest next check.
      Note: Line is a suggested anchor from the current file content; review surrounding wording before editing.
    - `context/guardrail-layers.md` near line `44`: review and add or strengthen nearby guidance.
      Prompt change: Do not claim validation, tests, CI, or scanner checks passed unless exact commands, jobs, or evidence were actually run or provided. If validation was not run, say so plainly and name the smallest next check.
      Note: Line is a suggested anchor from the current file content; review surrounding wording before editing.
    - `skills/tailtrail-review/SKILL.md` near line `31`: review and add or strengthen nearby guidance.
      Prompt change: Do not claim validation, tests, CI, or scanner checks passed unless exact commands, jobs, or evidence were actually run or provided. If validation was not run, say so plainly and name the smallest next check.
      Note: Line is a suggested anchor from the current file content; review surrounding wording before editing.
```

How a team should use this result:

- Review the listed files and decide whether the TailTrail wording is too weak.
- Treat the line numbers as starting points for review, not instructions to paste blindly at that exact line.
- Compare the proposed prompt wording with the existing guidance so TailTrail stays consistent and does not duplicate rules.
- If the wording is weak, update the guardrail or review guidance and add a benchmark scenario that would catch the same behavior later.
- If the wording is already strong, inspect the benchmark scenario because the benchmark expectation may be unclear or too narrow.
- Rerun the benchmark and analyzer after the change.
- Use the result as local product evidence, not as a universal claim about every model, repo, or company workflow.

What this example does not mean:

- It does not mean TailTrail should edit itself automatically.
- It does not mean user prompts or private repo content should be logged.
- It does not mean TailTrail is broadly better in all enterprise scenarios.
- It only means this saved benchmark artifact found one actionable validation-truth weakness.

Second example: discrepancy detection.

Example benchmark signal:

```text
Scenario: dependency-choice
Baseline: 5 / 8
TailTrail: 5 / 8
TailTrail missed:
- avoids_dependency
```

What this means:

- TailTrail did not outperform baseline in this scenario.
- The miss maps to **dependency discipline**.
- Because dependency discipline is one of TailTrail's core value propositions, this should be investigated before making claims about dependency reduction.

Expected analyzer recommendation:

```text
Discrepancy:
dependency-choice: baseline 5 vs TailTrail 5

Recommended improvement:
Strengthen dependency-gate wording and add examples for native/platform alternatives.

Likely files:
DEPENDENCY-GATE.md, context/guardrail-layers.md, skills/tailtrail/SKILL.md

Proposed file changes:
- DEPENDENCY-GATE.md near the first dependency guidance anchor:
  Prompt change: Before recommending a package, check standard library, platform-native capability, framework features, and already-installed dependencies. Add a dependency only when the native path is clearly insufficient and the tradeoff is documented.
- context/guardrail-layers.md near the dependency layer:
  Prompt change: Before recommending a package, check standard library, platform-native capability, framework features, and already-installed dependencies. Add a dependency only when the native path is clearly insufficient and the tradeoff is documented.
- skills/tailtrail/SKILL.md near the dependency rule:
  Prompt change: Before recommending a package, check standard library, platform-native capability, framework features, and already-installed dependencies. Add a dependency only when the native path is clearly insufficient and the tradeoff is documented.

Note:
These are recommended changes. Review before adding.
```

Implemented behavior:

- Parse the JSON output from `scripts/benchmark-tailtrail.py`.
- Aggregate passed and missed checks by check name and scenario.
- Detect discrepancies where baseline score is equal to or higher than TailTrail score.
- Map check names to risk themes with a small deterministic table.
- Generate Markdown and JSON reports.
- Add a review-before-adding note to every report.
- Add proposed file changes to each recommendation:
  - likely impacted file
  - suggested line anchor when the file exists locally
  - fallback manual anchor when the file is missing
  - proposed prompt wording
  - note that the anchor is a review starting point
- Include priority rules:
  - high when TailTrail misses validation truth, safeguard preservation, dependency discipline, or exactness.
  - medium when TailTrail misses scope control, review clarity, code consistency, or handoff quality.
  - low when the miss suggests benchmark wording may need calibration.
- Validate the analyzer and template in `scripts/check-tailtrail.py`.

Still not implemented yet:

- no automatic TailTrail file edits
- no background observer
- no raw prompt/user-history logging
- no model calls
- no vector search
- no CI dashboard
- no cross-repo aggregate analytics
- no hidden scoring of user behavior
- no automatic creation of pull requests from recommendations
- no company-wide benchmark trend store

Acceptance check:

- Analyzer can read benchmark JSON and produce Markdown recommendations.
- Analyzer can identify weak scenarios and repeated missed checks.
- Analyzer can detect discrepancies where TailTrail does not outperform baseline.
- Analyzer recommendations map to concrete TailTrail files or scenario gaps.
- Analyzer output keeps claims local to benchmark artifacts.
- Analyzer does not modify TailTrail behavior automatically.
- `python3 scripts/analyze-benchmark.py benchmarks/results/latest.json --format json` prints machine-readable analysis.
- `python3 scripts/analyze-benchmark.py benchmarks/results/latest.json --write-result` writes a local ignored Markdown report.

## Phase 7.2: Code Review Graph Lite

Purpose: improve review focus by mapping changed files to likely callers, tests, shared helpers, and risk boundaries before broad source reading.

Status: completed end to end for the first Lite implementation. It generates a compact review impact map from changed files using simple explainable local signals.

Problem to solve:

- Review can drift into broad repo scanning.
- Agents may miss shared callers or tests affected by a small change.
- Enterprise reviews need impact clarity without a full AST graph engine.
- Token usage can increase when an agent reads large folders instead of a targeted impact slice.

Design principle:

- Python-only.
- Simple file/path/import/test-name signals first.
- Text output first.
- Deterministic and explainable.
- No model calls.
- No semantic vector search in the Lite version.
- No full AST graph in the Lite version.
- No background indexing service in the Lite version.

Implemented files:

- `scripts/review-graph.py`: generate a compact impact map from changed files.
- `templates/review-graph.md`: reusable review graph output shape.

Implemented behavior:

- Accept changed file paths with repeated `--changed`.
- If no file is passed, read changed paths from `git diff --name-only HEAD` when available.
- Identify likely callers through direct text/import references to changed file tokens.
- Identify likely tests through naming, path proximity, and references.
- Identify shared helpers, config, dependency manifests, and generated/vendor boundaries.
- Produce compact Markdown and optional JSON.
- Produce a suggested read order.
- Tag risks such as auth, validation, dependency/config, CI/Sonar, shared helper, and test paths.
- Preserve exact source/diff paths; do not replace source reading before edits.

Example command:

```bash
python3 scripts/review-graph.py --changed src/service/foo.py --format markdown
python3 scripts/review-graph.py --changed src/service/foo.py --format json
python3 scripts/review-graph.py --root /path/to/project --changed src/service/foo.py
```

Example output:

```text
# TailTrail Code Review Graph Lite

This is an explainable impact map, not a complete call graph. Review suggested files before relying on it.

## Changed Files

- src/service/foo.py

## Suggested Read Order

- src/service/foo.py
- tests/service/test_foo.py
- src/api/foo_controller.py
- src/shared/validation.py
- pyproject.toml

## Per-File Impact

### src/service/foo.py

Risks: validation path, shared helper path

Likely tests:
- tests/service/test_foo.py: test name/path matches changed file

Likely callers:
- src/api/foo_controller.py: text/import reference to changed file token

Related shared helpers:
- src/shared/validation.py: shared helper references changed path token

Import signals:
- src.shared.validation

## Nearby Manifests / Config

- pyproject.toml: near changed file

## Signals Used

- imports
- file naming conventions
- test proximity
- local text search
- manifest/config proximity
```

How this helps day to day:

- It gives the agent and reviewer a small list of files to inspect first.
- It reduces missed callers/tests without loading the whole repository.
- It supports token saving because the graph becomes a targeted review slice.
- It gives explainable reasons for each suggestion, which is easier to defend in enterprise review.
- It complements, but does not replace, reading the relevant source before editing.

Why Lite first:

- It is portable across languages and repo styles.
- It has no dependency, service, index, or company infrastructure requirement.
- It avoids policy concerns around persistent code indexing.
- It can be benchmarked before investing in deeper graph intelligence.

Known limitations:

- It may miss framework magic, dependency injection paths, reflection, generated route bindings, runtime config loading, and indirect call chains.
- Text references can produce false positives.
- It does not understand symbol scope, inheritance, overloads, or dynamic dispatch.
- It is a review-focus helper, not a correctness proof.

Future candidates to review later:

- **Full AST engine**: build language-aware import/symbol/call edges for selected high-value stacks after Lite proves useful.
- **Semantic vector database**: support similarity search across large repos only if text/import signals miss too much and governance approves indexing.
- **Background indexing service**: cache graph data for very large monorepos only if on-demand scanning becomes too slow.
- **Cross-repo graph hints**: map service-to-service ownership and pipeline boundaries after local repo behavior is stable.
- **CI/Sonar graph integration**: connect scanner findings to likely tests, owners, generated boundaries, and rule-specific remediation paths.

Acceptance check:

- A reviewer can see likely callers and tests before reading broad directories.
- The output is compact enough to paste into `context/change-impact.md`.
- The script avoids generated/vendor folders.
- It improves review focus without becoming a full graph engine.
- `python3 scripts/review-graph.py --changed scripts/review-graph.py` prints Markdown.
- `python3 scripts/review-graph.py --changed scripts/review-graph.py --format json` prints machine-readable output.

## Phase 7.5: Easy Command Surface

Purpose: make TailTrail feel like one usable tool instead of a folder of scripts and Markdown files.

Status: completed end to end for the first local wrapper. `scripts/tailtrail.py` delegates to existing scripts, `TAILTRAIL-COMMANDS.md` documents the command surface, and Navigator can reuse these command names later.

Problem to solve:

- TailTrail has useful pieces, but users should not need to remember many script names.
- Named commands are easier to discover than long prompts or scattered script entry points.
- Enterprise users need predictable commands that work across repos, assistants, and onboarding docs.
- A simple command surface should improve usability without adding a daemon, service, or assistant lock-in.

Design principle:

- Keep Python-only.
- Keep existing scripts working.
- Add one friendly entry point over current capabilities.
- Prefer clear command names over clever automation.
- Make every command explain what it will do and what it will not do.
- Do not hide policy or guardrail decisions behind magic.

Implemented behavior:

- `scripts/tailtrail.py` is the main local command entry point.
- `scripts/tailtrail.py help` prints common commands and examples.
- `scripts/tailtrail.py commands` prints `TAILTRAIL-COMMANDS.md`.
- `scripts/tailtrail.py version` shows source or installed-pack location.
- `scripts/tailtrail.py hello` confirms TailTrail is installed and reachable with a friendly smoke check.
- `scripts/tailtrail.py guide "<goal>"` delegates to Navigator and returns a plan-first recommendation without editing files.
- `scripts/tailtrail.py intent "use AIDLC and review"` wraps `expand-intent.py`.
- `scripts/tailtrail.py route review` wraps `route-context.py`.
- `scripts/tailtrail.py token "review this diff"` wraps `token-auto.py`.
- `scripts/tailtrail.py graph --changed src/service/foo.py` wraps `review-graph.py`.
- `scripts/tailtrail.py aidlc init --root . --depth standard` wraps `aidlc-init.py`.
- `scripts/tailtrail.py aidlc check --root .` wraps `aidlc-check.py`.
- `scripts/tailtrail.py benchmark` wraps `benchmark-tailtrail.py`.
- `scripts/tailtrail.py analyze benchmarks/results/latest.json` wraps `analyze-benchmark.py`.
- `scripts/tailtrail.py install copilot --root . --with-tailtrail-pack` wraps `install-copilot.py`.
- `scripts/tailtrail.py install local --inspect` wraps `install-local.py`.
- `scripts/tailtrail.py update --root . --dry-run` wraps `update-tailtrail.py`.
- `scripts/tailtrail.py team-init --root . --mode optional` wraps `team-init.py`.
- `scripts/tailtrail.py learn init --root .` wraps `learnings.py`.
- `scripts/tailtrail.py doctor` runs `check-tailtrail.py` and `sync-adapters.py --check`.
- Delegated scripts run from the user's current working directory so installed packs can operate on the user's project.

Command names to review:

```bash
python3 scripts/tailtrail.py help
python3 scripts/tailtrail.py commands
python3 scripts/tailtrail.py hello
python3 scripts/tailtrail.py guide "fix Sonar issue and prepare PR"
python3 scripts/tailtrail.py intent "use AIDLC and review"
python3 scripts/tailtrail.py route review
python3 scripts/tailtrail.py token "review this diff for dependency risk"
python3 scripts/tailtrail.py graph --changed src/service/foo.py
python3 scripts/tailtrail.py aidlc init --root . --depth standard
python3 scripts/tailtrail.py aidlc check --root .
python3 scripts/tailtrail.py benchmark --format json
python3 scripts/tailtrail.py analyze benchmarks/results/latest.json
python3 scripts/tailtrail.py install local --inspect
python3 scripts/tailtrail.py install copilot --root /path/to/project --with-tailtrail-pack
python3 scripts/tailtrail.py update --root . --dry-run
python3 scripts/tailtrail.py team-init --root . --mode optional
python3 scripts/tailtrail.py learn init --root .
python3 scripts/tailtrail.py doctor
```

Implemented files:

- `scripts/tailtrail.py`: unified command wrapper around existing scripts.
- `TAILTRAIL-COMMANDS.md`: user-facing command catalog.
- `templates/command-result.md`: consistent shape for future command outputs if repeated patterns emerge.

Detailed end-user examples:

New user discovery:

```bash
python3 scripts/tailtrail.py help
python3 scripts/tailtrail.py commands
```

Why it helps: the user learns one command surface instead of memorizing many script names.

Bug fix with possible caller/test impact:

```bash
python3 scripts/tailtrail.py graph --changed src/checkout/dateValidation.ts
```

Expected use: paste or reference the graph before implementation so the assistant reads likely tests and callers first.

Broad or unclear task:

```bash
python3 scripts/tailtrail.py guide "add payment retry handling and prepare PR"
```

Expected output: Navigator plan with selected features, skipped features, impacted files, suggested next commands, and a reminder that the user can edit the plan before implementation.

AIDLC setup:

```bash
python3 scripts/tailtrail.py aidlc init --root . --depth standard
python3 scripts/tailtrail.py aidlc check --root .
```

Benchmark evidence:

```bash
python3 scripts/tailtrail.py benchmark --format json
python3 scripts/tailtrail.py analyze benchmarks/results/latest.json
```

Repo health:

```bash
python3 scripts/tailtrail.py doctor
```

Navigator relationship:

- Phase 8 Navigator should use these same command names when it recommends or later invokes TailTrail features.
- Example: Navigator should recommend `python3 scripts/tailtrail.py graph --changed src/service/foo.py`, not a separate graph command.
- This keeps human usage, assistant usage, and future automation aligned.

Integration points:

- `USER-GUIDE.md` makes `tailtrail.py help`, `tailtrail.py guide`, and `TAILTRAIL-COMMANDS.md` the first discovery path.
- `README.md` shows the main command surface.
- `scripts/check-tailtrail.py` validates the unified CLI and command catalog.
- Installers include `scripts/tailtrail.py` and `TAILTRAIL-COMMANDS.md` in managed packs.

Non-goals:

- No graphical dashboard in this phase.
- No background service.
- No global command install by default.
- No automatic execution of workflows.
- No replacement of existing scripts until adoption proves the wrapper is enough.
- No full Navigator implementation in Phase 7.5; `guide` is a preview/advisory command.

Acceptance check:

- A new user can run one help command and discover the major TailTrail workflows.
- Existing scripts still work.
- Common workflows have short commands and do not require long prompt memorization.
- The command catalog explains when to use AIDLC, review, handoff, dependency gate, token routing, team init, update, and learning.
- The unified CLI delegates to existing scripts rather than duplicating logic.
- `python3 scripts/tailtrail.py help` prints the command surface.
- `python3 scripts/tailtrail.py commands` prints the command catalog.
- `python3 scripts/tailtrail.py hello` prints `Installation check: passed`, TailTrail mode, and location.
- `python3 scripts/tailtrail.py graph --changed scripts/tailtrail.py` delegates to Code Review Graph Lite.
- `python3 scripts/tailtrail.py doctor` runs package validation checks.

## Phase 8: TailTrail Navigator

Purpose: help users choose the right TailTrail feature, sequence, and token strategy for their current goal without memorizing every command.

Status: completed end to end for the first deterministic Navigator. It is advisory, approval-first, and integrated into `scripts/tailtrail.py guide`.

Problem to solve:

- TailTrail now has many useful features: AIDLC, Review, Handoff, Dependency Gate, Token Router, Review Lenses, Delivery/Risk/Release flows, Team mode, Learnings, and future Learning Agent V2.
- End users should not need to remember which feature to use, when to combine features, or which files to load.
- Users should not need to manually decide whether Code Review Graph Lite, Token Autopilot, AIDLC, Review, Handoff, or Dependency Gate should run for every prompt.
- Using too much TailTrail process on a tiny task wastes time and tokens.
- Using too little process on risky work can miss validation, review, or handoff needs.
- Implementation should not start silently when the prompt is broad, risky, multi-file, or unclear. Navigator should propose a plan first and ask for approval.

Design principle:

- Recommend the smallest useful workflow.
- Tell users what to use and what to skip.
- Navigator is the single orchestration layer for automatic feature selection; individual features should not all auto-trigger independently.
- Prefer deterministic rules before any LLM-dependent behavior.
- Keep recommendations token-safe and explainable.
- Use a plan-first approval gate before implementation.
- Tell users they can edit the generated plan before approving implementation.

Implemented behavior:

- Accept a user goal or task description.
- Classify task type: small edit, feature, bug, review, dependency, CI/CD, Sonar, release, handoff, security, architecture, QA, learning.
- Detect risk indicators: auth, secrets, dependency change, production, data migration, CI failure, Sonar issue, broad refactor, multiple repos, unclear ownership.
- Detect existing TailTrail state when available: `aidlc-docs/`, `.tailtrail/learnings.md`, `.tailtrail/learning-index.md`, installed pack manifest, changed files, and validation artifacts.
- Recommend an ordered workflow such as `aidlc -> review -> qa_review -> handoff`.
- Recommend exact local commands the user can run through `scripts/tailtrail.py`.
- Recommend files to load and files to avoid.
- Recommend when to run Token Autopilot, AIDLC, review lenses, handoff, learnings, or release flow.
- Explicitly state when to skip AIDLC, handoff, review lenses, or learning capture.
- Auto-select Code Review Graph Lite for non-trivial implementation, review, refactor, bug, CI/Sonar, validation, auth, dependency, or shared-helper prompts when changed files are known or can be inferred.
- Skip Code Review Graph Lite for tiny typo/comment/docs-only prompts, conceptual questions, or prompts with no useful repo/file context.
- Return an implementation plan before code changes for broad/risky/multi-file work.
- Include affected or likely impacted files from Code Review Graph Lite when available.
- Include exact TailTrail features selected, features skipped, and reasons.
- Ask the user to approve before implementation.
- Notify the user that the plan is editable and can be customized before approval.
- Support explicit overrides such as `use AIDLC only`, `skip review graph`, `review only`, or `implement without AIDLC`.

Implemented files:

- `context/navigator.md`: rule table and recommendation logic.
- `templates/workflow-recommendation.md`: output shape for recommendations.
- `scripts/navigator.py`: deterministic recommendation helper.
- `scripts/tailtrail.py guide "fix Sonar issue and prepare PR"` delegates to Navigator.

Example command:

```bash
python3 scripts/navigator.py "fix Sonar issue and prepare PR"
python3 scripts/navigator.py "fix Sonar issue" --changed src/service/foo.py --format json
python3 scripts/tailtrail.py guide "fix Sonar issue" --changed src/service/foo.py
```

Example output:

```text
Recommended workflow: risk -> qa_review -> release

Use:
- Use risk flow.
- Use QA review.
- Use release flow.

Skip:
- AIDLC comprehensive unless multiple modules are affected.
- Dependency review unless package files changed.
- Learning capture unless the Sonar pattern is reusable.

Load:
- exact Sonar issue
- exact changed files
- context/review-lenses.md
- templates/validation-handoff.md
```

Plan-first approval output shape:

```text
TailTrail Navigator Plan

Goal:
- Fix Sonar issue and prepare PR.

Selected features:
- Token Autopilot: route context because the task touches CI/Sonar.
- Code Review Graph Lite: map likely callers/tests from changed files.
- Review Lens: QA / maintainability.
- Handoff: prepare validation and review notes.

Skipped features:
- AIDLC comprehensive: scope appears limited to one scanner issue.
- Dependency Gate: no package or manifest files are affected.
- Learning capture: optional unless this Sonar pattern is repeated.

Likely impacted files:
- src/service/foo.py: scanner finding source.
- tests/service/test_foo.py: likely validation path.
- .github/workflows/build.yml: nearby CI context if failure came from workflow.

Implementation plan:
1. Read the scanner finding and exact affected source lines.
2. Run Code Review Graph Lite and inspect suggested tests/callers.
3. Fix the smallest root cause.
4. Run or name the focused validation command.
5. Produce review/handoff notes.

Approval:
- Review this plan before implementation.
- You can edit the plan, remove steps, add files, change validation, or skip selected TailTrail features.
- Reply `approve` to proceed, or send an edited plan.
```

Recommendation examples:

- Small typo: recommend `TailTrail lean`; skip AIDLC, review lenses, handoff, and learning capture.
- New API endpoint: recommend `delivery -> architecture_review -> qa_review`; add handoff if another owner reviews.
- Dependency addition: recommend `risk -> dependency_review`; load `DEPENDENCY-GATE.md`.
- CI failure: recommend `risk -> qa_review`; later integrate with `ci-summary.py`.
- Sonar issue: recommend `risk -> maintainability_review or qa_review`; capture learning if repeated.
- Release prep: recommend `release`; load validation and diff handoff.
- Security-sensitive change: recommend `risk -> security_review -> qa_review -> release`.

Learning Agent V2 integration:

- Navigator should search learnings only after Learning Agent V2 exists.
- It should read `.tailtrail/learning-index.md` first.
- It should suggest at most three matching learnings.
- It must not load raw learning history by default.

Token-saving behavior:

- Run Token Autopilot before recommending large TailTrail context.
- Load `context/navigator.md` and one selected flow/lens, not every TailTrail guide.
- Keep exact text for source, diffs, configs, CI/Sonar failures, commands, versions, paths, IDs, and security rules.
- Prefer summary outputs for recommendation only; do not dump long docs into the prompt.

Implementation idea:

- Start with keyword/risk rules in Python. Completed.
- Accept optional inputs: `--changed`, `--root`, `--format json`, and `--command-prefix`.
- Return Markdown by default and JSON for tooling.
- Add TailTrail command names to the recommendation output.
- Make plan-only behavior the default for every Navigator response.
- Add `--approve-plan path/to/plan.md` later only after the plan format is stable.
- Include Code Review Graph Lite output when it is selected and changed files are known.
- Keep automatic feature selection advisory until a host environment can enforce approval safely.
- Wire into `scripts/tailtrail.py guide`. Completed.

Additional future candidates:

- Save Navigator plans to `aidlc-docs/navigator-plan.md` or `.tailtrail/navigator-plan.md` with explicit user request.
- Add `--approve-plan path/to/plan.md` only after the plan schema is stable.
- Add policy-tunable Navigator rules through `tailtrail-policy.md`.
- Add benchmark scenarios for Navigator decisions so workflow selection can be scored.
- Add CI/Sonar summary integration after Phase 8.5.
- Add Learning Agent V2 retrieval after curated learning indexes exist.
- Add an interactive edit/approve loop only in hosts that can enforce approval boundaries safely.

Non-goals for V1:

- No autonomous execution.
- No background service.
- No cross-repo scanning.
- No mandatory hooks.
- No LLM dependency.
- No full learning-history ingestion.
- No hidden implementation after generating a plan.
- No auto-editing files without explicit user approval.
- No per-feature independent auto-triggering that bypasses Navigator.

Acceptance check:

- A user can describe a goal and get a concise recommended TailTrail workflow.
- The recommendation includes use, skip, load, avoid, and next command.
- Small tasks receive small workflows.
- Risky tasks receive review/validation/handoff suggestions.
- Recommendations are deterministic and testable.
- Non-trivial implementation prompts receive a plan-first response before edits.
- The plan includes likely impacted files when Code Review Graph Lite is selected.
- The response asks for approval and tells the user the plan can be edited before implementation.
- Explicit user overrides can disable selected features.
- `python3 scripts/navigator.py "fix Sonar issue" --changed src/service/foo.py` prints Markdown.
- `python3 scripts/navigator.py "fix Sonar issue" --changed src/service/foo.py --format json` prints machine-readable output.
- `python3 scripts/tailtrail.py guide "fix Sonar issue" --changed src/service/foo.py` delegates to Navigator.

## Phase 8.5: CI/Sonar Intelligence

Purpose: make TailTrail useful for pipeline-heavy enterprise repositories by turning noisy CI, test, lint, and Sonar output into compact, exact-safe validation guidance.

Status: completed end to end for local file summaries. `scripts/ci-summary.py`, `scripts/sonar-summary.py`, and `scripts/validation-summary.py` summarize provided CI/build/test/lint/Sonar output files. Navigator routing is implemented. Provider API integrations, scanner execution, and automatic polling remain out of scope.

Naming clarification:

- `ci-sonar` is a TailTrail route/category name, not a product name.
- It means CI, pipeline, build, test, lint, static-analysis, scanner, and quality-gate work.
- SonarQube, SonarCloud, and sonar-scanner output are subcases inside this category.
- To reduce confusion later, consider renaming the user-facing command/category to **pipeline-quality** while keeping `ci-sonar` as a backward-compatible alias.
- Example future aliases:
  - `python3 scripts/tailtrail.py route pipeline-quality`
  - `python3 scripts/tailtrail.py route ci-sonar`
  - `python3 scripts/tailtrail.py sonar summarize --file sonar.log`
  - `python3 scripts/tailtrail.py ci summarize --file ci.log`

Problem to solve:

- Enterprise teams spend significant time on CI failures, pipeline failures, Sonar/static-analysis issues, and quality gates.
- Raw logs are expensive and noisy.
- Summaries can become unsafe if exact failing lines, rule IDs, paths, or commands are lost.
- Users may paste large logs without knowing whether the issue is CI, SonarQube, test, lint, or another pipeline-quality failure.

Design principle:

- Preserve exact failure lines, rule IDs, file paths, command names, and versions.
- Summarize only surrounding noise.
- Python-only local scripts.
- No direct CI provider API integration in the first version.
- Accept pasted logs or local files first.
- Navigator should detect CI/Sonar-like prompt or log signatures and recommend the right summarizer.
- Navigator should not silently process huge pasted logs in prompt context when a local file summarizer would save tokens.
- TailTrail should not poll CI systems, call SonarQube/SonarCloud APIs, or scan repositories automatically in this phase.

Planned files:

- `scripts/ci-summary.py`: summarize build/test/pipeline output. Implemented.
- `scripts/sonar-summary.py`: summarize Sonar/static-analysis findings. Implemented.
- `scripts/validation-summary.py`: create a combined validation handoff. Implemented.
- `templates/ci-summary.md`: compact CI/pipeline summary shape. Implemented.
- `templates/sonar-summary.md`: compact Sonar/static-analysis summary shape. Implemented.

Planned behavior:

- Capture command or pipeline stage when available.
- Capture first relevant failure.
- Capture failing test name.
- Capture Sonar rule ID and severity when available.
- Capture affected files and line hints.
- Produce `templates/validation-handoff.md` compatible output.
- Feed Learning Agent V2 later with compact event summaries only.
- Let Navigator classify pasted or referenced logs as `pipeline-quality` / `ci-sonar` when it sees signals such as `SonarQube`, `sonar-scanner`, `Quality Gate failed`, rule IDs like `java:S2259`, `BUILD FAILED`, stack traces, failing test names, lint errors, or `file:line` patterns.
- If the log is small, preserve exact relevant lines and recommend CI/Sonar Intelligence.
- If the log is large, tell the user to save it to a local file and run the summarizer instead of pasting the full log again.
- Navigator should recommend Code Review Graph Lite after an affected source file is known.

Navigator behavior after implementation:

- Navigator owns detection and routing.
- The user should not need to know the feature name.
- User can say `fix this pipeline failure` or paste a small excerpt; Navigator should classify it and recommend the summarizer.
- Navigator does **not** automatically check CI/Sonar issues by itself.
- Navigator does **not** query CI providers, poll pipelines, or connect to SonarQube/SonarCloud.
- Navigator only reacts to the prompt, supplied changed files, pasted excerpts, or local files the user asks TailTrail to summarize.
- Automatic CI/Sonar checking would require later provider integrations, credentials, polling rules, and organization approval.

Implemented Navigator behavior:

- Selects `CI/Sonar Intelligence` when it sees pipeline, Sonar, lint, test, static-analysis, or quality-gate signals.
- Adds exact evidence to the load list: rule IDs, paths, line numbers, commands, and first relevant failures.
- Adds an avoid note for large logs: do not paste or reload huge CI/Sonar logs when a local file summary would be cheaper.
- Keeps scan execution approval-gated through the Scan Approval section.

Possible commands:

```bash
python3 scripts/ci-summary.py --file build.log
python3 scripts/sonar-summary.py --file sonar.txt
python3 scripts/validation-summary.py --ci build.log --sonar sonar.txt
python3 scripts/tailtrail.py ci summarize --file build.log
python3 scripts/tailtrail.py sonar summarize --file sonar.txt
python3 scripts/tailtrail.py validation summarize --ci build.log --sonar sonar.txt
python3 scripts/tailtrail.py route pipeline-quality
python3 scripts/tailtrail.py route ci-sonar
python3 scripts/tailtrail.py guide "fix this pipeline failure" --changed src/service/UserService.java
```

Example Navigator response to a large pasted log:

```text
This looks like pipeline-quality / CI-Sonar output.

Selected:
- CI/Sonar Intelligence
- Token Autopilot
- QA review
- Code Review Graph Lite after the affected file is known

Because the log is large, save it locally and run:

python3 scripts/tailtrail.py ci summarize --file ci.log

If the failure is from SonarQube or SonarCloud, run:

python3 scripts/tailtrail.py sonar summarize --file sonar.log

Preserve exact rule IDs, file paths, line numbers, commands, and first relevant failures.
```

Non-goals:

- No raw log ingestion into normal prompt context.
- No automatic polling of CI providers.
- No automatic SonarQube/SonarCloud API calls.
- No hidden scanner execution.
- No credential handling.
- No background service.
- No provider-specific CI API calls in V1.
- No automatic upload or telemetry.
- No guessing fixes without reading exact source.

Acceptance check:

- A user can paste or point to CI/Sonar output and get a compact useful summary.
- Exact failure lines, Sonar rule IDs, paths, and commands are preserved.
- Long logs are reduced to relevant failure, affected files, and next action.
- Validation handoff can use the output directly.
- The command surface exposes `ci summarize`, `sonar summarize`, and `validation summarize`.
- Installed TailTrail packs include the summarizer scripts and templates.

## Phase 8.6: Quality Signal Scanner

Purpose: help users find likely local lint, test, build, scanner, and quality-gate issues by detecting project quality tools and recommending or running safe local checks with explicit approval.

Status: completed end to end for the first local scanner/runner. `scripts/quality-scan.py` recommends repo-owned local quality commands from manifests without running them. `scripts/quality-run.py` runs one exact allowlisted local quality command only with `--approved`, blocks unsafe command families, saves output under `.tailtrail/quality-runs/`, and returns the real exit code.

Positioning:

- Phase 8.5 summarizes known CI/Sonar/lint/test output.
- Phase 8.6 discovers available local quality checks and helps run them safely.
- It is not a SonarQube replacement and should not try to reimplement Sonar rules.
- It should use the tools the repo already owns: linters, test runners, build tools, quality plugins, and optional local `sonar-scanner` commands.

Problem to solve:

- Users may ask, "Can TailTrail find possible SonarQube, lint, or quality-gate issues before CI?"
- Developers often do not know the right local command for a repo.
- Large enterprise repos may have many possible checks, and running all of them can be slow or risky.
- Agents should not guess quality-gate failures from source alone when project tools can provide exact evidence.

Design principle:

- Detect first, recommend second, run only with approval.
- Prefer project-defined scripts and build commands over invented checks.
- Keep all command execution local and explicit.
- Preserve exact command, exit code, first relevant failure, affected file, line, rule ID, and tool name.
- Pipe output into Phase 8.5 summarizers instead of dumping raw logs into prompts.
- Do not claim a repo is clean unless the relevant command actually ran and passed.
- Do not execute networked, deploy, publish, destructive, or credentialed commands automatically.

Planned files:

- `scripts/quality-scan.py`: inspect repo files and recommend quality commands. Implemented.
- `scripts/quality-run.py`: run an approved local quality command and save output for summarization. Implemented.
- `templates/quality-scan.md`: command recommendation output. Implemented.
- `templates/quality-run.md`: executed command result summary. Implemented.
- Optional `context/quality-tools.md`: documented detection rules and command safety boundaries.

Detection signals:

- Java / Maven:
  - `pom.xml`
  - `mvn test`
  - `mvn verify`
  - `mvn -DskipTests=false test`
  - local `mvn sonar:sonar` only when configured and explicitly approved
- Java / Gradle:
  - `build.gradle`, `build.gradle.kts`
  - `./gradlew test`
  - `./gradlew check`
  - `./gradlew sonarqube` only when configured and explicitly approved
- JavaScript / TypeScript:
  - `package.json`
  - scripts such as `lint`, `test`, `typecheck`, `build`
  - `npm run lint`, `npm test`, `npm run typecheck`
- Python:
  - `pyproject.toml`, `requirements.txt`, `pytest.ini`, `tox.ini`
  - `pytest`
  - `ruff check`
  - `mypy`
- .NET:
  - `.sln`, `.csproj`
  - `dotnet test`
  - `dotnet build`
- Go:
  - `go.mod`
  - `go test ./...`
  - `go vet ./...`
- Generic:
  - `.github/workflows/`
  - `.gitlab-ci.yml`
  - `sonar-project.properties`
  - `Makefile`
  - `Jenkinsfile`

Planned behavior:

- Inspect the repo for known manifests, build files, CI config, and package scripts.
- Recommend a small ordered set of checks, not every possible command.
- Mark each command as:
  - **safe local**: test, lint, typecheck, build without publish/deploy.
  - **needs approval**: slow, broad, networked, scanner, integration, or credentialed.
  - **blocked**: deploy, publish, destructive, or missing required setup.
- Prefer changed-file focused checks when possible.
- Ask for explicit user approval before running commands.
- Save raw command output to an ignored local file when needed.
- Feed output into `ci-summary.py`, `sonar-summary.py`, or `validation-summary.py`.
- Return a compact report with exact command, exit code, first relevant failure, affected files, and next suggested action.
- Let Navigator recommend Quality Signal Scanner when the user asks whether TailTrail can find local quality issues or when the prompt mentions lint, quality gate, Sonar, CI precheck, scanner, test failure, or "before PR".

Possible commands:

```bash
python3 scripts/quality-scan.py --root .
python3 scripts/quality-scan.py --root . --changed src/service/UserService.java
python3 scripts/quality-run.py --root . --command "npm run lint"
python3 scripts/tailtrail.py quality scan --changed src/service/UserService.java
python3 scripts/tailtrail.py quality run --approved --command "mvn test"
```

Example output:

```text
# TailTrail Quality Signal Scanner

Detected project signals:
- package.json
- tsconfig.json
- .github/workflows/build.yml

Recommended checks:
- safe local: npm run lint
- safe local: npm test -- --runInBand
- needs approval: npm run build

Skipped:
- sonar-scanner: not configured locally
- deploy/publish commands: blocked

Approval:
- Reply approve to run `npm run lint`, or edit the command list.
```

Navigator integration:

- Navigator should not say TailTrail can detect all SonarQube issues from source.
- Navigator should say TailTrail can recommend and optionally run local quality tools with approval.
- Navigator should add a dedicated Scan Approval section when it suggests full Sonar, lint, test, audit, vulnerability, broad build, or scanner work.
- The default approval answer should be `no`; users must reply `yes` for one listed command or edit the plan with the exact repo-approved command.
- Navigator should explain why approval is required: scanner commands can be slow, noisy, networked, credentialed, or organization-specific.
- If the user asks "find possible quality gate issues", Navigator should select:
  - Quality Signal Scanner
  - Token Autopilot
  - Code Review Graph Lite when changed files are known
  - CI/Sonar Intelligence for summarizing output
- Navigator should ask for approval before running any command.

Implemented Navigator example:

```bash
python3 scripts/tailtrail.py guide "run a full code scan for Sonar and vulnerability issues before PR"
```

Expected Navigator behavior:

- Selects Quality Signal Scanner planning.
- Keeps CI/Sonar and security context exact-safe.
- Lists detected project signals such as `pom.xml`, `package.json`, `sonar-project.properties`, `pyproject.toml`, `go.mod`, Gradle files, or .NET project files.
- Lists candidate commands with safety labels such as `safe local`, `needs explicit approval`, or `manual review required`.
- Shows a Scan Approval question:
  - yes: approve one listed command or provide the exact command to run
  - no: keep this as planning only
  - edit: replace the command list with the repo-approved quality command
- Does not run any command silently.

Non-goals:

- No custom SonarQube rule engine.
- No full static analyzer.
- No automatic background scanning.
- No CI provider polling.
- No SonarQube/SonarCloud API calls.
- No credential handling.
- No networked scanner execution without explicit user approval.
- No deploy, publish, migration, or destructive commands.
- No claim that quality gates will pass unless the relevant local or CI command actually passed.

Acceptance check:

- Scanner recommends commands from local repo manifests without running them.
- Scanner labels command safety clearly.
- Running commands requires explicit approval path.
- Output can be summarized by Phase 8.5 tooling.
- Navigator can recommend Quality Signal Scanner but does not execute it automatically.
- The command surface exposes `quality scan` and `quality run`.
- Installed TailTrail packs include the scanner, runner, and templates.

## Phase 8.6a: Test Precision Planner

Purpose: make post-development validation sharper by planning exactly which unit, regression, and focused validation tests should be added or run for a change.

Status: implemented end to end as a read-only local planner with Navigator routing. `scripts/test-precision.py` detects common test stacks, infers likely test files from changed source paths, surfaces existing test helpers to reuse, creates a compact test-case matrix, and suggests focused validation commands. The command is available through `python3 scripts/tailtrail.py test plan ...`, Navigator selects it for unit/regression/coverage/post-change validation prompts, and it is included in both internal and public exports.

Why this exists:

- Developers often finish code changes and then ask, "what should I test?"
- Broad test suites can be slow, noisy, and token-expensive when the immediate need is a focused regression check.
- Agents can over-create tests or invent scaffolding when they do not first inspect existing conventions.
- Reviewers and enterprise teams need evidence that the changed behavior has a precise check without weakening guards.

Design principles:

- Plan before running. The feature recommends tests and commands but does not execute anything.
- Reuse before creating. Existing fixtures, factories, helpers, mocks, and support files should be considered first.
- Test behavior, not internals. Prefer public outputs, persisted state, status codes, errors, and guard behavior over private implementation details.
- Keep the smallest useful validation slice. Add one regression test that would fail before the fix, then only the extra cases justified by risk.
- Preserve safeguards. Validation, authorization, escaping, data integrity, accessibility, and security guards must not be weakened just to make tests pass.

Implemented files:

- `scripts/test-precision.py`: deterministic planner.
- `scripts/tailtrail.py`: `test plan` command surface.
- `scripts/navigator_core.py` and `scripts/navigator.py`: testing-intent detection plus Navigator selected feature and command recommendation.
- `TAILTRAIL-COMMANDS.md`, `USER-GUIDE.md`, `CHEATSHEET.md`, `README.md`: usage documentation.
- `tests/test_deterministic_tools.py`: Python and Java/Maven planning tests plus public/internal export assertions.
- `scripts/check-tailtrail.py` and `scripts/smoke-test.py`: package validation and public smoke coverage.

Supported first-pass signals:

- Python: `pyproject.toml`, `pytest.ini`, `tox.ini`, `requirements.txt`, `setup.cfg`, `tests/`; source `src/service/foo.py` maps to candidates such as `tests/service/test_foo.py`; focused command example: `pytest tests/service/test_foo.py`.
- Java / Maven: `pom.xml`; source `src/main/java/com/acme/Foo.java` maps to `src/test/java/com/acme/FooTest.java`; focused command example: `mvn test -Dtest=FooTest`.
- Java / Gradle: `build.gradle`, `build.gradle.kts`, `gradlew`, Gradle settings files; focused command example: `./gradlew test --tests '*FooTest'`.
- Node: `package.json`; candidates such as `foo.test.ts`, `foo.spec.ts`, and `__tests__/...`; focused command example: `npm test -- src/foo.test.ts`.
- .NET: `.sln`, `.csproj`; candidates such as `tests/FooTests.cs`; focused command example: `dotnet test --filter FullyQualifiedName~Foo`.
- Go: `go.mod`; candidate `foo_test.go`; focused command example: `go test ./pkg/service`.

Example usage:

```bash
python3 scripts/tailtrail.py test plan --changed src/service/claims.py --goal "fix validation bug"
```

Example output shape:

```text
# Test Precision Planner

## Changed Files
- src/service/claims.py

## Detected Frameworks
- python: evidence pyproject.toml

## Likely Test Files
- src/service/claims.py
  - tests/service/test_claims.py (exists)

## Test Case Matrix
- regression: Capture the exact behavior that was broken or requested.
- happy path: Confirm normal valid input.
- negative path: Confirm invalid input is handled safely.
- boundary path: Cover empty/null/missing values when relevant.
- guard preservation: Protect validation or security safeguards.

## Focused Validation Commands
- `pytest tests/service/test_claims.py`: focused Python test path
```

Navigator relationship:

- Navigator may recommend this feature when the user asks for tests, unit coverage, regression coverage, post-change validation, PR readiness, review response, Sonar/lint remediation validation, or precise test creation.
- Navigator should still ask before running any command.
- Quality Signal Scanner remains the tool for discovering repo quality commands.
- Test Precision Planner is the tool for deciding what tests should exist and which focused command is a good next step.
- When selected, Navigator adds a suggested command such as `tailtrail test plan --root "/path/to/repo" --goal "..." --changed src/service/foo.py`.
- After implementation, the ideal TailTrail flow is to run review plus Test Precision Planner, then run one approved focused validation command if the user approves it.

Future candidates:

- Deeper framework-specific test filters for JUnit 5 nested tests, pytest node IDs, Jest/Vitest config, and NUnit/xUnit traits.
- Optional integration with Code Graph Mapper so likely impacted tests can include graph-derived callers and endpoint/service/table flows.
- Optional generated test skeleton proposals, still requiring user approval before file writes.
- Optional coverage report parsing when the user supplies local coverage output.

## Phase 8.7: Security And Vulnerability Intelligence

Purpose: give TailTrail a separate enterprise-grade path for vulnerability findings, dependency CVEs, secret leaks, SAST findings, container/image scan issues, IaC misconfiguration, and security policy violations without blurring them into Sonar/quality work.

Status: completed end to end for local vulnerability planning, approved execution, exact-safe summarization, first structured scanner parsers, and scanner-output hardening. Navigator routing is implemented; `scripts/vulnerability-scan.py` recommends scanner commands without running them; `scripts/vulnerability-run.py` runs one exact allowlisted command only with `--approved`; `scripts/vulnerability-summary.py` turns local scanner output into a structured vulnerability list; SARIF, Trivy JSON, and Grype JSON are parsed before text fallback. Evidence is redacted for common secret patterns, report reads are size-capped, Trivy package-manifest findings are classified as dependency vulnerabilities, and summary/overlay paths can be normalized against the target `--root`. Remediation is still implementation work and should happen only when the user specifically asks TailTrail to fix a finding.

Positioning:

- Phase 8.5 handles CI, pipeline, build, test, lint, Sonar/static-analysis, and quality-gate output.
- Phase 8.6 discovers and recommends local quality commands such as tests, lint, build, typecheck, and optional Sonar scanner commands.
- Phase 8.7 handles security and vulnerability-specific evidence such as CVEs, vulnerable packages, secret findings, SAST rules, container scan findings, IaC misconfiguration, license/security policy violations, and supply-chain risk.
- SonarQube security hotspots may route through this phase when the finding is security-specific, but general Sonar code smells and quality gate failures should stay in Phase 8.5 / Phase 8.6.

Problem to solve:

- Enterprise teams often receive vulnerability findings from many tools, not only SonarQube.
- Raw vulnerability reports can be large, repetitive, and expensive to paste into an assistant.
- Fixes can be risky because a package upgrade may be breaking, a transitive dependency may need a parent upgrade, or a secret finding may require rotation outside code.
- Agents must preserve exact identifiers such as CVE IDs, package names, versions, image tags, rule IDs, file paths, line numbers, and scanner names.
- Security remediation should not become "just upgrade everything"; it needs dependency discipline, explicit risk, and validation.

Design principle:

- Keep vulnerability intelligence separate from Sonar/quality intelligence.
- Preserve exact security identifiers and affected versions.
- Summarize report noise but never rewrite CVE IDs, package names, versions, severities, file paths, or rule IDs.
- Prefer project-owned remediation paths and already-approved dependency versions.
- Apply `DEPENDENCY-GATE.md` before recommending dependency upgrades.
- Distinguish direct dependencies from transitive dependencies.
- Distinguish code fix, dependency upgrade, configuration change, secret rotation, image rebuild, and infrastructure change.
- Ask for explicit approval before running any vulnerability, audit, SAST, secret, container, or IaC scanner.
- Do not claim a vulnerability is fixed unless the relevant scanner, test, build, or security validation actually passed.

Planned files:

- `scripts/vulnerability-summary.py`: summarize vulnerability, audit, SAST, secret, container, and IaC scan output from a local file. Implemented.
- `scripts/vulnerability-scan.py`: inspect repo manifests and recommend security scanner commands without running them. Implemented.
- `scripts/vulnerability-run.py`: run one explicitly approved local vulnerability command and save output for summarization. Implemented.
- `templates/vulnerability-summary.md`: compact security finding summary shape. Implemented.
- `templates/vulnerability-remediation.md`: remediation handoff with exact identifiers, risk, chosen fix, and validation. Implemented.
- Optional `context/vulnerability-tools.md`: documented detection rules, scanner categories, and safety boundaries.
- Structured parser support:
  - SARIF for CodeQL, Semgrep, GitHub code scanning, and other SAST/code-scanning tools. Implemented.
  - Trivy JSON for container, dependency, OS package, secret, and IaC findings. Implemented.
  - Grype JSON for container, dependency, and OS package findings. Implemented.
  - Sonar JSON, dependency-check XML, CycloneDX, SPDX, and additional scanner schemas remain future candidates.
- Hardening support:
  - Common secret-like evidence redaction before markdown or JSON output. Implemented.
  - `--max-bytes` input guard for oversized scanner reports. Implemented.
  - Target-root path normalization for structured scanner summary and overlay paths. Implemented.
  - Generic-token filtering to avoid noisy related-file matches. Implemented.
  - Trivy dependency vs container finding classification. Implemented.

Detection signals:

- Dependency vulnerability:
  - `CVE-`
  - `GHSA-`
  - `npm audit`
  - `pip-audit`
  - `osv-scanner`
  - `mvn org.owasp:dependency-check`
  - `gradle dependencyCheckAnalyze`
  - `dotnet list package --vulnerable`
  - `go list -m -u -json all`
- SAST/security rule:
  - `semgrep`
  - `CodeQL`
  - `Fortify`
  - `Checkmarx`
  - `Veracode`
  - `Bandit`
  - `SpotBugs`
  - scanner rule IDs and severity labels
- Secret scanning:
  - `gitleaks`
  - `trufflehog`
  - `secret`
  - `private key`
  - token-like findings
- Container/image:
  - `trivy`
  - `grype`
  - image name and tag
  - OS package vulnerability
- IaC/cloud configuration:
  - `checkov`
  - `tfsec`
  - Terraform, Kubernetes, Helm, CloudFormation, or policy-as-code paths
- License/security policy:
  - license denylist
  - security policy violation
  - organization exception request

Planned behavior:

- Accept pasted vulnerability snippets or local report files first.
- If the report is large, tell the user to save it locally and run the summarizer instead of pasting the whole report again.
- If the user asks what can be scanned, return recommended scanner commands and ask for approval. Do not run scanners from a general request.
- If the user approves one exact scan command, run only that command and save the output locally.
- After scanner output exists, return a structured vulnerability list before proposing implementation.
- Implement remediation only when the user specifically asks to fix a finding.
- Extract exact:
  - scanner/tool name
  - CVE/GHSA/rule ID
  - package/component/image/resource
  - current version
  - fixed version when present
  - severity
  - direct vs transitive hint when present
  - affected file and line when present
  - first relevant evidence line
- Classify finding type:
  - dependency CVE
  - SAST/code vulnerability
  - secret leak
  - container/image vulnerability
  - IaC/cloud misconfiguration
  - license/security policy violation
- Recommend the smallest remediation path:
  - upgrade direct dependency
  - upgrade parent dependency or BOM
  - pin or override transitive dependency only when policy allows
  - code-level fix
  - remove/rotate secret
  - rebuild base image
  - update IaC configuration
  - request exception only when remediation is blocked and policy permits
- Feed remediation into:
  - Dependency Gate for package changes
  - Security Review for trust-boundary/code changes
  - Handoff for risk, owner, validation, and remaining exceptions
  - Learning Agent V2 later for reusable vulnerability patterns

Possible commands:

```bash
python3 scripts/vulnerability-summary.py --file audit.log
python3 scripts/vulnerability-summary.py --file codeql.sarif
python3 scripts/vulnerability-summary.py --file trivy.json
python3 scripts/vulnerability-summary.py --file grype.json
python3 scripts/vulnerability-scan.py --root .
python3 scripts/vulnerability-scan.py --root . --changed package.json
python3 scripts/vulnerability-run.py --root . --approved --command "npm audit"
python3 scripts/tailtrail.py vulnerability summarize --file audit.log
python3 scripts/tailtrail.py vulnerability summarize --file codeql.sarif
python3 scripts/tailtrail.py vulnerability summarize --file trivy.json --format json
python3 scripts/tailtrail.py vulnerability summarize --file grype.json --format json
python3 scripts/tailtrail.py vulnerability scan --changed pom.xml
python3 scripts/tailtrail.py vulnerability run --approved --command "npm audit"
python3 scripts/tailtrail.py guide "fix CVE-2025-1234 from the dependency scan"
```

Example output:

```text
# TailTrail Vulnerability Summary

Finding:
- Tool: npm audit
- ID: CVE-2025-1234
- Severity: high
- Component: example-lib
- Current version: 1.2.0
- Fixed version: 1.2.7
- Dependency path: app -> parent-lib -> example-lib
- Type: transitive dependency CVE

Recommended remediation:
- Apply Dependency Gate before changing versions.
- Check whether parent-lib has an approved upgrade that brings example-lib to 1.2.7 or later.
- Avoid force-overriding the transitive dependency unless the repo policy allows it and tests pass.

Validation:
- Run the repo-owned dependency audit command again.
- Run focused tests that cover the affected package path.
```

Navigator integration:

- Navigator should route prompts containing `CVE`, `GHSA`, `vulnerability`, `vuln`, `SAST`, `secret leak`, `container scan`, `image scan`, `Trivy`, `npm audit`, `pip-audit`, `dependency-check`, `gitleaks`, `CodeQL`, `Fortify`, `Checkmarx`, `Veracode`, `Semgrep`, `Bandit`, `Checkov`, or `tfsec` to Security And Vulnerability Intelligence.
- Navigator should not treat every security prompt as a Sonar/quality prompt.
- Navigator should select:
  - Security And Vulnerability Intelligence
  - Security Review
  - Dependency Gate when packages, versions, manifests, or dependency paths are involved
  - Quality Signal Scanner only when local scan command discovery is needed
  - Handoff when an exception, owner approval, secret rotation, release risk, or security sign-off is involved
- Navigator should show Scan Approval before running any vulnerability command.
- Navigator should default scan approval to `no`.
- Navigator should ask the user to choose or edit the exact scanner command if multiple security tools could apply.

Implemented Navigator behavior:

- Routes CVE, GHSA, vulnerability, SAST, secret, container, image, audit, and named scanner prompts to Security And Vulnerability Intelligence.
- Adds exact vulnerability evidence to the load list: IDs, packages, versions, severities, scanner names, and affected paths.
- Selects Dependency Gate when vulnerability work appears to involve dependency/package remediation.
- Avoids treating vulnerability findings as generic Sonar code smells.
- Avoids claiming a vulnerability is fixed without scanner or validation evidence.
- Suggests `python3 scripts/tailtrail.py vulnerability scan --root .` when vulnerability work is detected.

Implemented vulnerability behavior:

- `vulnerability scan` detects common project signals such as `package.json`, Python dependency files, Maven/Gradle, .NET, Go, Cargo, Dockerfile, Terraform, and CI config.
- `vulnerability scan` recommends scanner commands such as `npm audit`, `pip-audit`, OWASP dependency-check, `dotnet list package --vulnerable`, `govulncheck`, `cargo audit`, `trivy`, `grype`, `checkov`, `tfsec`, `gitleaks`, and `semgrep` when relevant.
- `vulnerability run` requires `--approved`, blocks destructive/deploy/cloud command families, uses a vulnerability-tool allowlist, saves output under `.tailtrail/vulnerability-runs/`, and returns the scanner exit code.
- `vulnerability summarize` reads a local scanner output file and returns a structured vulnerability list with exact IDs, severity, component, versions, affected path, finding type, tool name, and first evidence line when detected.
- TailTrail command surface exposes `tailtrail.py vulnerability summarize|scan|run`.
- Installed TailTrail packs include the vulnerability scripts and templates.

Non-goals:

- No custom vulnerability database.
- No CVE lookup service in V1.
- No networked vulnerability scanner execution without explicit approval.
- No automatic secret scanning in the background.
- No credential handling.
- No automated security exception filing.
- No automatic dependency upgrade PRs.
- No claiming a CVE is fixed from source inspection alone.
- No uploading reports or telemetry.

Acceptance check:

- A pasted or file-based vulnerability report becomes a compact exact-safe summary.
- CVE/GHSA/rule IDs, packages, versions, paths, and severities remain exact.
- A general scan request returns scanner recommendations and approval guidance instead of running a scanner.
- An approved exact command can be run with `vulnerability run --approved --command "..."`.
- Scanner output becomes a structured list of vulnerabilities.
- Remediation is not implemented unless the user specifically asks TailTrail to fix a finding.
- Dependency findings invoke Dependency Gate.
- Secret findings recommend removal and rotation instead of only deleting code.
- Navigator routes vulnerability prompts separately from general Sonar/quality prompts.
- Scanner commands require explicit approval and default to no.

## Phase 8.8: Code Graph Mapper

Purpose: reduce repeated source reading during heavy Sonar, vulnerability, review, QA, dependency, and handoff workflows by creating a compact, explainable, freshness-checked graph cache that Navigator can reuse.

Status: completed end to end for the first local metadata mapper plus the first advanced enterprise metadata layer. `scripts/code-graph-mapper.py` implements `map`, `status`, and `refresh`; `scripts/tailtrail.py graph map/status/refresh` exposes the command surface; Navigator cache checking and mapper recommendations are wired for heavy Sonar, vulnerability, dependency, QA, review, release, and handoff prompts. The mapper now also emits monorepo partitions, service dependency hints, endpoint-to-service-to-table flows, owner/test/release-path mapping, and explicit graph/vector DB boundaries.

Naming:

- User-facing feature name: **Code Graph Mapper**.
- Cache file: `tailtrail-meta/code-graph-cache.json` by default. Legacy/private fallback: `.tailtrail/code-graph-cache.json`.
- Command group: `graph map`, `graph status`, and `graph refresh`.
- Relationship to Phase 7.2: Code Review Graph Lite creates an on-demand impact map. Code Graph Mapper adds persistent cache, freshness checks, and Navigator reuse.

Problem to solve:

- Heavy Sonar and vulnerability work often makes agents reread the same source files, tests, manifests, configs, and scanner evidence.
- Repeated broad repo reads waste tokens and can create inconsistent review paths.
- Existing graph tools on the market are powerful but often too heavy for TailTrail's small, local, policy-friendly shape.
- Enterprise users need explainable graph reuse, not a hidden background index or a source-code cache.
- Users should be able to ask for a heavy read, and Navigator should decide whether to reuse an existing graph, create a missing graph, or refresh a stale graph before asking the agent to read broad code again.

Design principle:

- Store compact metadata only; never store full source code, secrets, raw prompts, full assistant responses, or raw scanner logs.
- Use simple, explainable signals first: imports, filename conventions, test proximity, local text search, manifest/config proximity, package/module paths, and scanner evidence paths.
- Must support TailTrail's primary enterprise languages: Python, Java, .NET/C#, SQL, and Terraform.
- Add deeper semantic understanding in layers. Start with explainable heuristics, then add language-specific symbol extraction, then optional approved external/MCP enrichers.
- Treat static graph output as likely guidance, not perfect truth.
- Recompute or mark stale when relevant files change.
- Prefer file hashes over timestamps for correctness; keep modified time and file size as helpful diagnostics.
- Make every stale/fresh decision explainable.
- Navigator can recommend graph creation or reuse, but it should not silently run heavy scanner commands.
- Build the graph around the user's actual task scope. A graph for `payment-service` should not be reused for an unrelated `auth-service` task unless the scope overlaps and the hashes match.
- Separate graph refresh from scanner execution. Refreshing the graph reads repo structure and file metadata; running Sonar or vulnerability tools remains a separate approval-gated action.

Core user flow:

1. User asks for heavy work, for example:

```text
Run a full Sonar and vulnerability review before PR.
```

2. Navigator classifies the prompt as heavy quality/security work.
3. Navigator checks `tailtrail-meta/code-graph-cache.json` first, then falls back to `.tailtrail/code-graph-cache.json` for older/private local installs.
4. Navigator compares requested scope against cached scope.
5. Navigator compares cached hashes against current files.
6. Navigator returns one of three plan paths:
   - **fresh graph found**: reuse cached suggested read order and avoid broad rediscovery.
   - **missing graph**: recommend creating a graph before heavy read.
   - **stale graph**: recommend refreshing the graph and show exactly why.
7. User approves graph creation/refresh.
8. Agent reads only the graph-suggested files first.
9. Sonar/vulnerability scanner execution still requires separate scan approval.

Must-have features:

- **Graph status check**: detect `fresh`, `stale`, `missing`, and `invalid` cache states.
- **Scope matching**: confirm the graph covers the requested changed files, affected files, or scanner-reported files.
- **Hash-based freshness**: compare current SHA-256 hashes for source files, likely tests, likely callers, and watched manifests.
- **Changed-file explanation**: list the exact files that made the graph stale.
- **Manifest watch list**: track dependency/build/config files such as `pom.xml`, `package.json`, lockfiles, Gradle files, `requirements.txt`, `pyproject.toml`, `go.mod`, `.csproj`, `sonar-project.properties`, CI workflow files, and scanner config files.
- **Language coverage**: map Python, Java, .NET/C#, SQL, and Terraform files at minimum.
- **Symbol index lite**: extract classes, functions, methods, modules, endpoints, table names, Terraform resources, and config keys using language-aware heuristics.
- **Reference index lite**: find local references to extracted symbols through bounded text search and import/package path matching.
- **Call-chain hints**: create likely caller/callee hints for Python functions, Java methods/classes, and .NET methods/classes without claiming a complete call graph.
- **Type hierarchy hints**: detect obvious inheritance/implements/extends patterns in Java and .NET/C#, plus Python class inheritance where text patterns are clear.
- **Endpoint hints**: detect common framework endpoint declarations in Java, Python, and .NET.
- **DB/table hints**: detect SQL table names, migration files, ORM entity/table annotations, and query references.
- **Config usage hints**: connect config keys from YAML/properties/JSON/env-style files to source references.
- **Workspace overlays**: include uncommitted changed files, scanner-reported files, and user-provided target files as an overlay on top of the cached baseline graph.
- **Monorepo partitions**: group files by nearby service/module markers so one huge repo can be read as smaller slices.
- **Service dependency hints**: detect obvious HTTP URLs, service/base-url/endpoint/host config keys, and .NET project references.
- **Endpoint-to-service-to-table flow**: connect detected endpoints to same-file service calls, external service hints, DB table hints, and config hints.
- **Owner/test/release-path mapping**: connect changed files to CODEOWNERS, likely tests, and release/deployment paths when detectable.
- **Suggested read order**: provide a compact file-first path for the agent to inspect.
- **Token-safe cache**: store metadata only, never source code or raw scanner logs.
- **Navigator integration**: check the graph automatically for heavy Sonar, vulnerability, dependency, QA, review, and handoff prompts.
- **Approval prompt**: ask before creating or refreshing the graph, and ask separately before running scanners.
- **Stale fallback**: if the cache is stale or invalid, do not rely on it for final decisions.

Good-to-have features:

- **Graph confidence score**: label graph usefulness as `high`, `medium`, or `low` based on matched files, tests, callers, and manifests.
- **TTL policy**: optionally mark old graphs as `review recommended` even when hashes match, useful for fast-moving repos.
- **Task tags**: store whether the graph was created for Sonar, vulnerability, review, dependency, or QA work.
- **Scanner evidence links**: record scanner report file paths and hashes when the graph was created from Sonar/vulnerability output.
- **Diff-aware refresh**: use changed files from Git to refresh only the impacted graph scope.
- **Policy-aware cache location**: allow `tailtrail-policy.md` to choose whether graph cache is local-only, ignored, or shareable.
- **Cache summary export**: produce a short Markdown summary that can be pasted into reviews without exposing source.
- **Monorepo partitions**: support multiple graph entries by module/service so one huge cache does not become noisy. Implemented as first local partition summary.
- **Graph aging report**: show cache age, last checked time, and number of stale files.
- **Semantic provider hook**: allow approved MCP or language-server providers to enrich graph data when locally configured.
- **Language profile report**: show which languages were detected and which extraction level was used for each.
- **Endpoint-to-handler map**: connect route declarations to handler classes/functions when detectable. Partially implemented through endpoint and flow hints.
- **Data-flow-lite notes**: connect API handlers to repository/DAO/query/table references without claiming full data flow. Implemented as first endpoint/service/table hint layer.

Must-not-have in first implementation:

- No whole-repo background scan.
- No persistent daemon.
- No graph database.
- No vector database.
- No full AST/code-property graph in the first implementation.
- No secret or source-code storage.
- No automatic scanner execution after graph refresh.
- No cross-repo aggregation across multiple repos in this implementation; only local service dependency hints are emitted.
- No hidden learning from user prompts.
- No mandatory MCP dependency.
- No claim of complete semantic accuracy for dynamic dispatch, reflection, generated code, runtime dependency injection, or framework magic.

Language support requirements:

- Python:
  - detect modules, imports, classes, functions, decorators, FastAPI/Flask/Django-style route hints, pytest files, and likely callers via symbol/text references.
  - watch `pyproject.toml`, `requirements.txt`, `setup.py`, `tox.ini`, `pytest.ini`, and related config.
- Java:
  - detect packages, imports, classes, interfaces, enums, methods, `extends`, `implements`, Spring/JAX-RS endpoint annotations, JPA table/entity annotations, Maven/Gradle modules, and likely tests.
  - watch `pom.xml`, `build.gradle`, `build.gradle.kts`, Gradle wrapper files, `application.yml`, `application.properties`, and scanner config.
- .NET/C#:
  - detect namespaces, using statements, classes, interfaces, records, methods, inheritance, controller/Minimal API endpoints, EF-style DbSet/table hints, `.sln`, `.csproj`, and likely tests.
  - first implementation should use text/regex heuristics. A later optional semantic provider can use Roslyn/MCP when approved.
- SQL:
  - detect `CREATE TABLE`, `ALTER TABLE`, `INSERT INTO`, `UPDATE`, `DELETE FROM`, `SELECT ... FROM`, migration naming, stored procedure/function names, and source references to tables.
  - connect SQL files to Java/Python/.NET data-access code when table names or migration paths match.
- Terraform:
  - detect `resource`, `data`, `module`, `variable`, `output`, provider blocks, backend configuration, and references such as `module.x`, `var.x`, and resource addresses.
  - connect Terraform files to CI/deployment/config ownership but do not execute `terraform` commands.

Semantic understanding requirements:

- **Symbols**:
  - Store symbol kind, name, file, approximate line, language, and confidence.
  - Keep snippets out of the cache; store only names and coordinates.
- **References**:
  - Store reference target, referring file, approximate line, reference type, and confidence.
  - References may be heuristic unless produced by an approved semantic provider.
- **Call chains**:
  - Build bounded likely call chains from callers/callees.
  - Label them as `heuristic` unless sourced from a semantic provider.
  - Keep depth small by default to avoid token and runtime explosion.
- **Type hierarchy**:
  - Store direct extends/implements/inherits relationships when explicit in source text.
  - Do not infer runtime DI, reflection, proxies, or generated inheritance unless evidence exists.
- **Endpoints**:
  - Detect common route annotations/decorators and map endpoint path/method to handler symbol when possible.
  - Store route, method, handler, file, line, framework hint, and confidence.
- **DB tables**:
  - Detect SQL tables and ORM mappings.
  - Connect table names to migrations, queries, repositories/DAOs, services, and tests when text evidence exists.
- **Config usage**:
  - Detect config keys in common config files and source references.
  - Connect changed config keys to likely consumers.
- **Workspace overlays**:
  - Maintain a baseline graph plus overlay entries for changed files, scanner findings, and user-provided target files.
  - Overlays should expire or become stale independently from the baseline.

Semantic enrichment levels:

- Level 0: file/path/import/test/manifests only. This is equivalent to current Code Review Graph Lite.
- Level 1: language-aware regex extraction for Python, Java, .NET/C#, SQL, and Terraform.
- Level 2: optional standard-library parsers where safe, such as Python `ast`, while still storing metadata only.
- Level 3: optional approved external providers such as MCP, Roslyn, language servers, SCIP, or repo-owned generated indexes.

MCP / external provider position:

- TailTrail should not require MCP to work.
- TailTrail can optionally consume approved MCP or semantic-provider output when a project policy enables it.
- Provider output must be normalized into TailTrail's metadata-only cache shape.
- Provider output must be marked with source and confidence, for example `heuristic`, `python_ast`, `roslyn_mcp`, or `language_server`.
- If provider setup is unavailable, TailTrail should gracefully fall back to local heuristics.
- This keeps TailTrail portable while allowing .NET-heavy teams to use deeper Roslyn-style graph intelligence later.

Planned files:

- `scripts/code-graph-mapper.py`: create, status-check, and refresh graph cache. Implemented.
- `templates/code-graph-map.md`: human-readable graph cache report. Implemented.
- `context/code-graph-mapper.md`: feature behavior, cache boundaries, freshness rules, and Navigator usage. Implemented.
- `tailtrail-meta/code-graph-cache.json`: generated target-project cache, metadata-only, intended to be team-reviewable and commit-friendly when a repo wants shared orientation. Implemented as generated output.
- `.tailtrail/code-graph-cache.json`: legacy/private local fallback for teams that deliberately do not want to share the cache.

Cache schema sketch:

```json
{
  "schema_version": "1",
  "created_at": "2026-07-11T12:00:00Z",
  "updated_at": "2026-07-11T12:15:00Z",
  "tailtrail_version": "local",
  "root": "/path/to/repo",
  "cache_key": "sha256(root + scope + graph_mode)",
  "graph_mode": "sonar-vulnerability-review",
  "scope": ["src/service/UserService.java"],
  "task_tags": ["sonar", "vulnerability", "review"],
  "language_profiles": {
    "python": {"level": 1, "files": 8},
    "java": {"level": 1, "files": 34},
    "dotnet": {"level": 1, "files": 21},
    "sql": {"level": 1, "files": 12},
    "terraform": {"level": 1, "files": 6}
  },
  "source_files": {
    "src/service/UserService.java": {
      "sha256": "abc123",
      "mtime": 1783771200,
      "size": 4210
    }
  },
  "watch_files": {
    "pom.xml": {
      "sha256": "def456",
      "reason": "nearby dependency manifest"
    }
  },
  "scanner_evidence": {
    "sonar.log": {
      "sha256": "ghi789",
      "reason": "Sonar report used to identify affected files"
    }
  },
  "graph": {
    "changed_files": ["src/service/UserService.java"],
    "symbols": [
      {
        "kind": "class",
        "name": "UserService",
        "language": "java",
        "file": "src/service/UserService.java",
        "line": 12,
        "confidence": "heuristic"
      }
    ],
    "references": [],
    "call_chains": [],
    "type_hierarchy": [],
    "endpoints": [],
    "db_tables": [],
    "config_usage": [],
    "service_edges": [],
    "partitions": [],
    "endpoint_service_table_flows": [],
    "owner_test_release_map": {},
    "workspace_overlays": [],
    "likely_callers": [],
    "likely_tests": ["src/test/service/UserServiceTest.java"],
    "nearby_manifests": ["pom.xml"],
    "risk_tags": ["dependency", "quality"],
    "confidence": "medium",
    "suggested_read_order": [
      "src/service/UserService.java",
      "src/test/service/UserServiceTest.java",
      "pom.xml"
    ]
  },
  "freshness": {
    "status": "fresh",
    "checked_at": "2026-07-11T12:20:00Z",
    "reasons": []
  }
}
```

Freshness logic:

- Fresh when:
  - cache exists
  - requested target files are covered by cache scope
  - cached file hashes match current file hashes
  - watched manifests/configs still match
  - scanner evidence files referenced by the graph have not changed
  - graph mode matches the current task class, or the current task is safely narrower than the cached task
- Stale when:
  - a target file hash changed
  - a likely caller/test hash changed
  - a nearby manifest/config changed
  - a scanner evidence file changed
  - the graph was created for a different scope
  - the graph was created for a meaningfully different task class
  - the cache schema version is unsupported
  - required files disappeared or moved
- Missing when:
  - `tailtrail-meta/code-graph-cache.json` does not exist and no `.tailtrail/code-graph-cache.json` fallback exists
  - the cache cannot be parsed
  - the cache has no graph for the requested files
- Invalid when:
  - the JSON parses but required schema fields are missing
  - a hash field has an unsupported format
  - the cache root does not match the current project root
  - the cache looks manually edited in a way that prevents trustworthy freshness checks

Cache key and matching:

- Compute a cache key from:
  - normalized project root
  - normalized scope paths
  - graph mode
  - schema version
- A graph can be reused when:
  - the requested files are the same as cached scope, or are a subset of cached scope
  - the task class is compatible
  - source/watch/evidence hashes match
- A graph should not be reused when:
  - the request is for unrelated files
  - the cache was created for a different module/service
  - the user asks for vulnerability review but only a tiny docs graph exists
  - important manifests changed after graph creation

Planned commands:

```bash
python3 scripts/code-graph-mapper.py map --root . --changed src/service/UserService.java
python3 scripts/code-graph-mapper.py status --root . --changed src/service/UserService.java
python3 scripts/code-graph-mapper.py refresh --root . --changed src/service/UserService.java
python3 scripts/tailtrail.py graph map --changed src/service/UserService.java
python3 scripts/tailtrail.py graph status --changed src/service/UserService.java
python3 scripts/tailtrail.py graph refresh --changed src/service/UserService.java
```

Navigator behavior:

- For small typo/comment/docs-only work, skip Code Graph Mapper.
- For non-trivial implementation, review, Sonar, vulnerability, dependency, QA, release, or handoff work, check whether graph cache exists.
- For heavy Sonar and vulnerability prompts, check Code Graph Mapper before recommending broad code reads.
- If fresh:
  - select Code Graph Mapper
  - use cached suggested read order
  - avoid broad repo scanning
  - report the cache as fresh with the checked scope
  - still instruct the agent to inspect exact source files before editing
- If stale:
  - explain stale reasons
  - recommend `graph refresh`
  - ask user to approve refresh before relying on the old map
- If missing:
  - recommend `graph map`
  - explain that a fresh map can reduce repeated code reads
- Never treat cached graph output as proof that code is unchanged unless the file hashes match.
- Never use graph freshness as proof that Sonar or vulnerability findings are resolved.

Implemented Navigator behavior:

- Checks `tailtrail-meta/code-graph-cache.json` first for heavy prompts, then falls back to `.tailtrail/code-graph-cache.json`.
- Reports graph cache status in Markdown and JSON output.
- Handles `missing`, `fresh`, `stale`, and `invalid` states.
- Compares cached SHA-256 values for source files, watched files, and scanner evidence when a cache exists.
- Recommends graph reuse only when hashes still match.
- Recommends graph recreation or refresh when the cache is missing, invalid, or stale.
- Recommends `python3 scripts/tailtrail.py graph map ...` for missing or invalid cache scope.
- Recommends `python3 scripts/tailtrail.py graph refresh ...` for stale cache scope.

Implemented mapper behavior:

- Creates `tailtrail-meta/code-graph-cache.json` with compact metadata only by default.
- Checks cache status as `fresh`, `stale`, `missing`, or `invalid`.
- Refreshes the cache and records previous status in the generated cache.
- Hashes source files, likely callers, likely tests, watched manifests/configs, and optional scanner evidence.
- Produces Markdown and JSON reports.
- Supports Python, Java, .NET/C#, SQL, and Terraform language profiles.
- Extracts metadata-only symbols, references, call-chain hints, type-hierarchy hints, endpoint hints, DB table hints, config usage hints, workspace overlays, likely callers/tests, nearby manifests, risk tags, confidence, and suggested read order.
- Extracts advanced metadata-only partitions, external service hints, endpoint-to-service-to-table flows, CODEOWNERS owner hints, release/deployment path hints, and test mappings.
- Uses Python `ast` for Python when parsable and regex heuristics for Java, .NET/C#, SQL, Terraform, and config files.
- Stays local and Python-only with no model call, no vector database, no graph database, no daemon, no scanner execution, and no source snippet storage.

Navigator decision example:

```text
Goal: run full Sonar and vulnerability review before PR

Graph check:
- Cache status: stale
- Reason: package.json and src/payment/PaymentService.ts changed after graph creation.
- Last graph update: 2026-07-11T12:15:00Z
- Latest file change: 2026-07-11T13:02:00Z

Recommendation:
- Refresh Code Graph Mapper before broad source read.
- After graph refresh, read suggested files first.
- Ask separately before running Sonar or vulnerability scanners.
```

Example Navigator output:

```text
Selected:
- Code Graph Mapper: existing graph is stale because src/service/UserService.java changed after the cache was created.
- Quality Signal Scanner: Sonar/quality-gate work detected.
- Security And Vulnerability Intelligence: vulnerability review detected.

Recommended next step:
- Run `python3 scripts/tailtrail.py graph refresh --changed src/service/UserService.java`.

Approval:
- Review before refreshing. The graph refresh reads local file metadata and code references, but it does not run Sonar or vulnerability scanners.
```

Implementation sequence:

1. Add cache schema and template. Completed.
2. Implement `status` first so Navigator can safely detect missing/fresh/stale without writing files. Completed.
3. Implement `map` with hashes, language metadata, and suggested read order. Completed.
4. Add Level 1 language-aware extraction for Python, Java, .NET/C#, SQL, and Terraform. Completed.
5. Implement `refresh` as map overwrite with previous stale reason included in the report/cache. Completed.
6. Add `tailtrail.py graph map/status/refresh` wrappers. Completed.
7. Add Navigator integration for heavy Sonar/vulnerability/review prompts. Completed.
8. Add smoke checks for fresh, stale/missing command behavior, CLI wrapper, JSON output, and package validation. Completed.
9. Add optional semantic provider interface only after Level 1 behavior is stable. Future candidate.

Non-goals:

- No full AST graph engine in the first version.
- No code property graph.
- No graph database.
- No vector database.
- No background indexing service.
- No cross-repo service graph across multiple checked-out repos or remote systems.
- No hidden repo crawler.
- No source-code storage in cache.
- No automatic scanner execution.
- No claim that cached graph output is complete or perfect.

Future candidates:

- Optional SCIP or language-server based enrichment when a project already produces an index.
- Optional AST-based enrichment for high-value languages after usage proves the simple signals are insufficient.
- Optional MCP graph provider adapter for approved tools, especially Roslyn-based .NET graphing.
- Optional provider-backed cross-repo service graph when teams approve multi-repo indexing.
- Optional graph DB or vector DB only if JSON metadata becomes too slow or too weak for real enterprise workloads.
- Deeper data-flow beyond the current endpoint/service/table hints.

Acceptance check:

- A user can create a graph cache for changed files.
- A user can check whether the graph is fresh, stale, or missing.
- Python, Java, .NET/C#, SQL, and Terraform files produce language profile metadata.
- Symbols, references, call-chain hints, type-hierarchy hints, endpoint hints, DB table hints, config usage hints, and workspace overlays are present when detectable.
- Stale reasons identify exact files or manifests that changed.
- Navigator recommends graph reuse or refresh for heavy Sonar/vulnerability work.
- The cache contains compact metadata only and does not store source code or raw scanner logs.
- The feature reduces repeated read guidance without replacing exact source inspection before edits.

## Phase 9: Learning Agent V2

Purpose: turn repeated repo work into compact, reusable project intelligence without creating a noisy token sink.

Status: completed end to end for the first explicit local Learning Agent V2. TailTrail now supports compact event capture, confidence scoring, token-safe search, curated promotion, summaries, low-confidence pruning review, and index rebuilds. Capture remains explicit; there is no background observer or automatic prompt logging.

Problem to solve:

- Teams work across many repos and pipelines.
- Agents repeatedly rediscover the same repo conventions, validation commands, CI/CD failure patterns, Sonar/static-analysis rules, ownership constraints, and user preferences.
- Chat history is unreliable as durable memory.
- A single ever-growing learning file would increase token cost and eventually become noisy.

Design principle:

- Capture many compact events.
- Promote only a few reusable learnings.
- Retrieve only a small relevant slice.
- Keep raw history out of normal prompts.
- Treat user acceptance as one signal, not proof that a solution is correct.
- Score learning confidence before retrieval or promotion.
- Let users override task execution, but do not let low-confidence choices silently become reusable learnings.

Implemented behavior:

- Capture compact learning events for feature work, bug fixes, CI/CD fixes, Sonar/static-analysis fixes, validation outcomes, prompt intent, and user acceptance.
- Track whether the user accepted, rejected, revised, or partially accepted the solution.
- Record why the user liked or rejected a solution when that reason is explicit.
- Compute a Learning Confidence score for meaningful accepted or completed work.
- Show a compact Learning Confidence section when a learning event is captured.
- Block automatic promotion when confidence is below the configured threshold.
- Allow the user to proceed with a low-confidence implementation by explicit override, while clearly saying it will not be promoted into curated learnings.
- Promote only reusable facts into curated learnings.
- Keep raw event history out of normal prompt context.
- Search only matching learnings for the current repo, module, issue type, pipeline, tags, or file area.

Implemented file shape:

- `.tailtrail/learning-events.jsonl`: compact raw events, one JSON object per task.
- `.tailtrail/learning-index.md`: small searchable index by tags, modules, pipelines, and issue types.
- `.tailtrail/learnings.md`: curated durable patterns that agents may read during future work.
- `.tailtrail/learning-scores.jsonl`: compact scoring log for learning candidates.
- `.tailtrail/learning-policy.json`: local capture flags, prompt-capture setting, search limits, and promotion defaults.
- `scripts/learning-agent.py`: local Python CLI for `init`, `capture`, `score`, `search`, `promote`, `summarize`, `prune`, and `rebuild-index`.
- `context/learning-agent.md`: rules for confidence, token-safe retrieval, capture, privacy, and promotion.
- `templates/learning-signal.md`: compact final-response shape for captured events.
- `.tailtrail/history/`: future optional archived monthly event files if event volume grows.

Detailed event schema to consider:

- timestamp
- repo identifier or slug
- branch name when useful
- task summary
- original prompt summary, not full prompt by default
- optional prompt hash for dedupe
- task type: feature, bug, CI/CD, Sonar, dependency, refactor, review, release, docs, test
- source area: package, module, service, UI area, pipeline, folder, or owning domain
- files or modules touched
- issue tags: `ci`, `sonar`, `auth`, `pipeline`, `dependency`, `validation`, `frontend`, `backend`, `data`, `release`, `security`
- issue identifiers when available: ticket, PR, Sonar rule ID, pipeline job, test name
- validation commands run
- validation outcome: pass, fail, skipped, not-run, partial
- validation evidence summary, not raw logs
- first relevant CI/test/Sonar failure line when exact text matters
- solution summary
- reused project pattern
- new dependency decision, if any
- user acceptance: accepted, rejected, revised, partially accepted, unknown
- acceptance reason when explicit
- learning confidence score: 0-100
- learning confidence band: do-not-use, weak-note, candidate, trusted
- confidence factors: evidence, validation, review, repeatability, freshness, risk penalties
- user override: none, proceed-anyway, record-low-confidence-event
- promotion decision: not-promoted, event-only, candidate, promoted, trusted, stale
- follow-up requested by user
- reusable learning candidate
- sensitivity marker: normal, internal, sensitive
- stale condition or refresh trigger

Example compact event:

```json
{
  "timestamp": "2026-07-11T10:30:00Z",
  "repo": "payments-service",
  "task_type": "sonar",
  "tags": ["sonar", "java", "validation"],
  "prompt_summary": "Fix Sonar cognitive complexity in payment validator.",
  "files": ["src/main/java/.../PaymentValidator.java"],
  "issue_ids": ["Sonar:S3776"],
  "validation": [{"command": "mvn test -Dtest=PaymentValidatorTest", "outcome": "pass"}],
  "solution_summary": "Extracted named guard methods without changing validation behavior.",
  "acceptance": "accepted",
  "acceptance_reason": "User preferred behavior-preserving small refactor.",
  "learning_confidence": {
    "score": 86,
    "band": "trusted",
    "positive_factors": ["user accepted", "focused test passed", "no dependency added", "validation order preserved"],
    "negative_factors": [],
    "promotion_decision": "promoted"
  },
  "learning_candidate": "For validator cognitive complexity, extract named guard methods and preserve validation ordering.",
  "stale_when": "Validator framework or Sonar rules change."
}
```

Learning Confidence Gate:

The Learning Confidence Gate is the safety layer that prevents bad user-approved choices from becoming reusable TailTrail memory.

Core rule:

```text
TailTrail can learn from user acceptance, but it should trust evidence more than acceptance.
```

User acceptance should increase confidence, but it must not automatically create a trusted learning. A user can still approve execution of a low-confidence change, but TailTrail should not promote that choice into curated learnings unless objective evidence improves the score.

Score bands:

```text
0-39: do not use
40-59: weak historical note only
60-79: candidate learning, suggest with caution
80-100: trusted reusable repo pattern
```

Band behavior:

- **0-39 do not use**:
  - Do not retrieve in future prompts.
  - Do not promote to `.tailtrail/learnings.md`.
  - Show warning in final response for meaningful work.
  - User may proceed with explicit task override.
  - If user explicitly asks to record it, store only a low-confidence event, not a curated learning.
- **40-59 weak historical note**:
  - Do not auto-surface in normal Navigator plans.
  - May be shown only when the user asks for learning history or debugging.
  - Not eligible for trusted promotion.
  - Can become candidate only after validation or reviewer evidence is added.
- **60-79 candidate learning**:
  - Eligible as a candidate learning.
  - Navigator may surface it with caution language.
  - Needs validation, review, repeated success, or stronger evidence before trusted use.
- **80-100 trusted reusable repo pattern**:
  - Eligible for curated learning.
  - Navigator may retrieve it when task tags, files, graph scope, or issue type match.
  - Still must yield to current source, policy, scanner, and validation evidence.

Suggested scoring model:

```text
score = evidence + validation + review + repeatability + freshness + user_acceptance - risk_penalty
```

Positive factors:

- user explicitly accepted the solution
- focused tests, build, lint, scanner, or CI checks passed
- Sonar/static-analysis/vulnerability issue was rerun and resolved
- reviewer or owner approved the fix
- change reused an existing project pattern
- change was small, root-cause focused, and easy to review
- Dependency Gate was applied when packages changed
- no new dependency was introduced
- no guardrail was weakened
- same pattern succeeded more than once
- learning includes clear stale conditions

Negative factors:

- no validation was run
- validation failed, was skipped, or is unknown
- user accepted but evidence is thin
- broad refactor for a narrow issue
- auth, authorization, validation, escaping, privacy, data integrity, payment, release, or security logic changed
- dependency upgrade was made without approval or Dependency Gate evidence
- scanner issue was not rerun
- reviewer later rejected or revised the fix
- learning conflicts with current source, policy, graph, scanner, or CI evidence
- learning is old or attached to files/configs that changed
- solution hides a symptom instead of addressing a shared root cause

Risk-sensitive thresholds:

```text
normal bug fix: 60+
shared helper or multi-file refactor: 70+
dependency, auth, security, payment, data, migration, production, release: 80+
regulated or multi-team work: 85+
```

User override behavior:

When the user accepts or requests a change with a low confidence score, TailTrail should not block execution. It should make the boundary explicit:

```text
Proceeding with user override.

Learning Confidence: 34 / 100
Status: do not promote
Reason: validation was not run, safeguard impact is unknown, and the change touches authentication logic.
Learning action: not added to curated learnings.
```

If the user says:

```text
Record this anyway.
```

TailTrail may record only a low-confidence historical event:

```text
Recorded as low-confidence event only.
It will not be surfaced as a reusable recommendation unless later validation or review evidence raises the score.
```

Final response shape for meaningful work:

```text
TailTrail Learning Signal
Score: 76 / 100
Status: candidate learning
Why:
- focused change
- existing project pattern reused
- tests passed
- no new dependency
Missing:
- no reviewer approval yet
Learning action:
- captured as candidate
- not trusted until PR review or repeated successful use
```

Low-score final response example:

```text
TailTrail Learning Signal
Score: 42 / 100
Status: weak historical note, not promoted
Why:
- user accepted the approach
- no validation command was run
- dependency impact is unknown
- current evidence is limited
Learning action:
- not added to curated learnings
- user can explicitly record a low-confidence event for history
```

Trusted-score final response example:

```text
TailTrail Learning Signal
Score: 88 / 100
Status: trusted reusable repo pattern
Why:
- user accepted the solution
- focused test passed
- scanner issue was rerun and resolved
- no new dependency
- reviewer approved the PR
Learning action:
- eligible for curated learning
- stale if validator framework or Sonar profile changes
```

Learning states:

```text
candidate
validated
promoted
trusted
weak-note
stale
rejected
blocked
```

Promotion rules with confidence:

- User acceptance alone can create at most a candidate event.
- User acceptance plus no validation usually cannot exceed weak-note or candidate status.
- Validation evidence can raise a candidate.
- Reviewer/owner approval can raise confidence.
- Repeated success in the same repo area can promote to trusted.
- Negative reviewer feedback, failed validation, stale files, or policy conflicts lower confidence.
- Low-confidence choices must not enter `.tailtrail/learnings.md` as reusable guidance.
- Current source, scanner, CI, policy, and guardrail evidence always wins over old learning.

Planned Learning Confidence commands:

```bash
python3 scripts/learning-agent.py score --event-id 20260711-001
python3 scripts/learning-agent.py score --summary "Fixed Sonar validator complexity" --validation passed --risk validation
python3 scripts/learning-agent.py promote --event-id 20260711-001 --min-score 80
python3 scripts/learning-agent.py record-override --event-id 20260711-001 --reason "User chose to proceed despite low confidence"
```

Acceptance check for Learning Confidence Gate:

- A user-accepted but unvalidated risky fix receives a low score and is not promoted.
- A user can proceed with a low-confidence change by explicit override.
- A low-confidence override does not silently enter curated learnings.
- Final responses for meaningful work include a compact Learning Signal.
- Tiny low-risk tasks can skip Learning Signal to avoid noise.
- Trusted retrieval requires score threshold plus current scope match.
- Risky domains require higher thresholds than normal bug fixes.
- A stale or contradictory learning is suppressed even if it was previously trusted.

Learning promotion rules:

- Promote a learning only when it is likely reusable.
- Promote a learning only when the Learning Confidence score meets the relevant risk threshold.
- Prefer concrete project behavior over generic advice.
- Include evidence: file path, command, issue type, or accepted/rejected outcome.
- Include a refresh rule or stale condition.
- Do not promote private, sensitive, or one-off conversation details.

Promotion examples:

Bad learning:

```text
Fixed Sonar issue.
```

Good learning:

```text
Tag: sonar, java, cognitive-complexity
When Sonar flags validator cognitive complexity, prefer extracting named guard methods over changing validation behavior. Preserve rule order. Accepted by user on 2026-07-11 after `PaymentValidatorTest` passed. Refresh if validation framework or Sonar rule profile changes.
```

Bad learning:

```text
User did not like the first answer.
```

Good learning:

```text
Tag: user-preference, refactor
For this repo, user rejected broad refactors when the request is a narrow bug fix. Prefer one focused change plus a short note about deferred cleanup.
```

Token-saving rules:

- Load `.tailtrail/learning-index.md` first, not raw history.
- Load at most three matching curated learnings by default.
- Never load raw `learning-events.jsonl` unless the user explicitly asks for history/debugging.
- Summarize or archive old events when a threshold is reached.
- Keep source code, diffs, configs, CI failures, Sonar rule IDs, paths, and security rules exact when referenced.
- Prune stale learnings when commands, ownership, architecture, pipeline behavior, or policies change.

Suggested thresholds:

- If `.tailtrail/learning-events.jsonl` exceeds 200 events, summarize by month or tag.
- If `.tailtrail/learnings.md` exceeds 150 lines, split curated learnings by topic.
- If a search returns more than 5 matches, show only index summaries and ask the agent to pick at most 3.
- If a learning has not matched a task in 90 days and has no owner, mark it stale instead of loading it.

Retrieval strategy:

- Classify the current prompt by task type and tags.
- Check changed files or mentioned modules.
- Read `.tailtrail/learning-index.md`.
- Select at most three matching curated learnings.
- Read exact source/diff/config only after selecting relevant learnings.
- Do not read raw monthly history unless explicitly requested.

Privacy and compliance rules:

- Do not record secrets, tokens, credentials, PII, PHI, or customer data.
- Do not store full raw prompts by default; store summaries.
- Redact sensitive values from CI logs and error messages.
- Mark sensitive learning candidates as `sensitive` and keep them out of automatic retrieval.
- Allow teams to disable capture with a local setting before any hook integration is considered.

Implemented commands:

```bash
python3 scripts/learning-agent.py init --root .
python3 scripts/learning-agent.py capture --type bug --tags ci,pipeline --summary "Fixed failing deploy job" --candidate "Check generated deploy artifact before editing provider versions." --validation-outcome pass --acceptance accepted
python3 scripts/learning-agent.py score --event-id 20260711-001
python3 scripts/learning-agent.py search --tags sonar,java --limit 3
python3 scripts/learning-agent.py promote --event-id 20260711-001
python3 scripts/learning-agent.py summarize --month 2026-07
python3 scripts/learning-agent.py prune --max-score 39
python3 scripts/learning-agent.py rebuild-index
python3 scripts/tailtrail.py learn capture --type sonar --tags sonar,java --summary "Fixed validator complexity" --candidate "Extract named guard methods while preserving validation order."
```

Possible prompt aliases:

```text
Capture learning for this fix.
Search learnings for this CI issue.
Promote this as a repo learning.
Record user acceptance as accepted.
Summarize learning history for this module.
```

Agent behavior:

- At the end of meaningful work, suggest capturing a learning only when something reusable was discovered.
- Do not interrupt tiny low-risk tasks with learning prompts.
- Do not capture rejected solutions as positive patterns.
- Capture rejection reasons as user preference or anti-pattern only when the reason is explicit.
- Prefer updating an existing learning over adding duplicates.

Review questions before implementation:

- What events should be captured manually versus automatically?
- Should raw event history be committed, ignored, or configurable per repo?
- What redaction rules are mandatory for company data?
- Should user acceptance be recorded only with explicit user wording?
- Should the first implementation use Markdown only, JSONL only, or both?
- What default token limit should retrieval enforce?
- How should stale or contradictory learnings be resolved?
- Should CI/Sonar integrations remain manual text capture in V2, or should they parse known report formats?

Implemented sequence:

1. Added `scripts/learning-agent.py` with explicit local commands. Completed.
2. Added confidence scoring and score bands. Completed.
3. Added event capture into `.tailtrail/learning-events.jsonl`. Completed.
4. Added `.tailtrail/learning-index.md` rebuild for token-safe retrieval. Completed.
5. Added promotion into curated `.tailtrail/learnings.md` only when confidence and risk thresholds pass. Completed.
6. Added `scripts/tailtrail.py learn ...` wrappers while preserving simple `learnings.py` commands. Completed.
7. Added docs, context, template, installer inclusion, and validation checks. Completed.
8. Add opt-in learning capture hook for post-task summaries. Completed.
9. Integrate with Token Router/Navigator retrieval after Graph-Aware Learning Bridge. Future candidate.

Non-goals for V2:

- No vector database.
- No background service.
- No automatic capture of every prompt.
- No raw CI log ingestion by default.
- No cross-repo global memory until per-repo learning quality is proven.
- No user sentiment guessing; record acceptance only from explicit signals.
- No hidden automatic capture.
- No raw prompt or full assistant-response capture by default.

Automatic capture hook:

- Implemented as `hooks/learning-capture-hook.py`.
- The hook reads a compact post-task summary, infers task type/tags/risk, and decides whether capture is useful.
- By default it prints a reviewable `learning-agent.py capture` command and writes hook state only.
- With `--approved`, it writes a Learning Agent V2 event through `scripts/learning-agent.py capture`.
- It skips tiny, vague, typo-only, formatting-only, or non-reusable work unless `--force` is used.
- It must be wired only to post-task or post-approval flows, not every raw user prompt.
- It must not capture raw prompts, full assistant responses, source snippets, raw logs, secrets, credentials, PII, PHI, or customer data.

Acceptance check:

- A user can capture a feature/bug/CI/Sonar fix as a compact event.
- A user can record user acceptance or rejection with a short reason.
- A future similar task can retrieve a small matching set of learnings.
- Raw history does not enter normal prompt context.
- The learning workflow reduces repeated discovery without increasing routine token usage.
- Sensitive data is not captured in normal workflows.
- Stale learnings can be summarized, pruned, or marked inactive.
- Low-confidence accepted work is not promoted into curated learnings.
- User override can approve execution but does not silently approve learning promotion.
- Meaningful work can return a compact Learning Signal score and promotion decision.

## Phase 9.1: Graph-Aware Learning Bridge

Purpose: connect Code Graph Mapper facts with curated Learning Agent V2 knowledge so TailTrail can use past accepted repo patterns only when they match the current code scope.

Status: completed end to end for the first metadata-only bridge. TailTrail now supports linking Learning Agent V2 events to graph scope, searching graph-aware learnings, inspecting links, validating stale links, and surfacing matches in Navigator plans. Navigator now shows explicit learning approval choices, clear skip reasons, advisory-only wording, and post-task capture suggestions without recording anything automatically. The bridge stays separate from Code Graph Mapper and does not store source snippets or raw history.

Feature rating:

```text
Usefulness if kept curated: 8.5 / 10
Enterprise value: 9 / 10
Token-saving value: 8 / 10
Risk if overbuilt: 8 / 10
Recommended timing: after Phase 8.8 and Phase 9 baseline
```

Why this should be separate:

- **Code Graph Mapper** should answer "what code, symbols, configs, tests, tables, endpoints, and manifests are relevant right now?"
- **Learning Agent V2** should answer "what reusable repo/team pattern was accepted before?"
- **Navigator** should combine both answers and decide whether a learning is worth showing for the current task.
- Mixing learning into the graph cache would make the graph harder to trust, harder to invalidate, and more likely to become a behavior log.
- Mixing graph facts into learnings would make curated learnings too large and stale when code moves.

Problem to solve:

- Agents repeatedly rediscover accepted repo patterns for similar bugs, Sonar fixes, CI failures, dependency decisions, and validation paths.
- Graph data alone can show relevant files but cannot explain what solution was accepted by the team last time.
- Learning data alone can remember useful patterns but may apply them to the wrong module, symbol, endpoint, table, pipeline, or repo area.
- Large learning files can increase token cost if the agent loads everything for every task.
- Enterprise teams need precise reuse without raw prompt logging, hidden profiling, or broad memory ingestion.

Design principle:

- Keep graph facts and learning facts physically separate.
- Link them with compact metadata, not duplicated source code.
- Retrieve only a tiny number of relevant learnings.
- Current source evidence always wins over old learnings.
- User or team approval is required before capturing or promoting a learning.
- Do not store raw prompts, full assistant responses, secrets, source snippets, full logs, or personal behavior profiles.
- Every surfaced learning must show why it matched the current graph scope.
- If a learning conflicts with current code, policy, or scanner evidence, mark it stale or ignore it.

Implemented files:

- `scripts/graph-learning.py`: link, search, inspect, and validate graph-aware learnings.
- `context/graph-aware-learning.md`: rules for matching curated learnings to graph scope.
- `templates/graph-learning.md`: human-readable recommendation shape.
- `.tailtrail/graph-learning-index.json`: generated local metadata index linking learning IDs to graph entities.

Implemented commands:

```bash
python3 scripts/graph-learning.py link --learning-id sonar-java-001 --file src/main/java/.../PaymentValidator.java --symbols PaymentValidator.validate
python3 scripts/graph-learning.py search --changed src/main/java/.../PaymentValidator.java --tags sonar,java --limit 3
python3 scripts/graph-learning.py inspect --learning-id sonar-java-001
python3 scripts/graph-learning.py validate --root .
python3 scripts/tailtrail.py learn graph search --changed src/main/java/.../PaymentValidator.java --tags sonar,java
```

Index schema sketch:

```json
{
  "schema_version": "1",
  "updated_at": "2026-07-12T12:00:00Z",
  "learning_links": [
    {
      "learning_id": "sonar-java-001",
      "learning_file": ".tailtrail/learnings.md",
      "repo_scope": "payments-service",
      "graph_scope": ["src/main/java/.../PaymentValidator.java"],
      "linked_symbols": ["PaymentValidator.validate"],
      "linked_files": ["src/test/java/.../PaymentValidatorTest.java"],
      "linked_rules": ["Sonar:S3776"],
      "linked_tables": [],
      "linked_endpoints": [],
      "problem_type": "sonar-cognitive-complexity",
      "accepted_resolution": "Extract named guard methods while preserving validation order.",
      "validation_commands": ["mvn test -Dtest=PaymentValidatorTest"],
      "approval_status": "curated",
      "sensitivity": "normal",
      "stale_when": [
        "PaymentValidator.java changes",
        "PaymentValidatorTest.java changes",
        "Sonar rule profile changes"
      ]
    }
  ]
}
```

Matching strategy:

- Start from Navigator's task classification and changed files.
- Check Code Graph Mapper status first.
- If the graph is fresh, use its file, symbol, endpoint, table, config, manifest, scanner-rule, and test hints as the search scope.
- If the graph is stale or missing, fall back to changed files and prompt tags only, and label learning matches as lower confidence.
- Search `.tailtrail/learning-index.md` or the planned graph-learning index before reading curated learning details.
- Select at most three matching curated learnings.
- Rank matches by exact file, exact symbol, exact rule ID, nearby test, matching module, matching task type, and recent acceptance.
- Exclude stale, sensitive, rejected, unapproved, or contradictory learnings from automatic retrieval.

Navigator integration:

- Navigator should own when this bridge runs.
- Skip for tiny typo/comment/docs-only tasks.
- Use for repeated Sonar, CI, vulnerability, dependency, review, QA, handoff, and module-specific implementation tasks when graph scope or changed files are known.
- Show selected learnings in the plan, not as hidden instructions.
- Explain the match reason for each learning.
- Ask the user to choose `use learnings`, `ignore learnings`, or `edit plan` before implementation when matches are surfaced.
- Explain skip reasons with short labels:
  - `no index`: no `.tailtrail/learning-index.md` or `.tailtrail/graph-learning-index.json` exists.
  - `tiny task`: the task is too small to justify learning retrieval.
  - `stale graph`: graph-aware learning scope is stale or invalid.
  - `no matching tags/files/rules`: an index exists, but no match fits the current tags, files, graph scope, or scanner rules.
- Ask before capturing a new learning after implementation.
- Show a suggested `python3 hooks/learning-capture-hook.py ...` command after meaningful work, but do not run it automatically.
- For rejected or revised work, show capture suggestions only with explicit `--acceptance rejected` or `--acceptance revised` placeholders and a required reason. Full rejection/revision capture automation should wait for the refresh and quality loop UX.
- Do not block implementation if no learning is found.
- Do not apply a learning blindly; require exact source inspection before editing.
- Make advisory wording explicit: learnings never override current source, tests, CI, scanners, local policy, guardrails, or explicit user direction.

Example 1: Sonar cognitive complexity:

```text
User goal:
Fix Sonar cognitive complexity in PaymentValidator.

Graph match:
- File: src/main/java/.../PaymentValidator.java
- Symbol: PaymentValidator.validate
- Rule: Sonar:S3776
- Likely test: src/test/java/.../PaymentValidatorTest.java

Learning match:
- sonar-java-001: For validator cognitive complexity, extract named guard methods and preserve validation order.
- Validation previously accepted with: mvn test -Dtest=PaymentValidatorTest

Navigator plan impact:
- Read current PaymentValidator and PaymentValidatorTest first.
- Use the prior pattern only if validation ordering is still the same.
- Do not introduce a broad validator rewrite.
```

Example 2: dependency vulnerability:

```text
User goal:
Fix GHSA vulnerability in a transitive Java dependency.

Graph match:
- Manifest: pom.xml
- Parent/BOM: platform-bom
- Affected package: org.example:example-lib

Learning match:
- dependency-java-004: This repo prefers upgrading the parent BOM over direct transitive overrides unless the security team approves an exception.

Navigator plan impact:
- Apply Dependency Gate.
- Check current BOM and dependency tree evidence.
- Prefer the accepted repo path before suggesting an override.
```

Example 3: CI failure:

```text
User goal:
Fix failing deploy pipeline.

Graph match:
- Workflow: .github/workflows/deploy.yml
- Job: deploy-prod
- Terraform path: infra/prod

Learning match:
- ci-terraform-002: Deploy failures in this repo often require updating the generated plan artifact and rerunning the policy check, not editing provider versions first.

Navigator plan impact:
- Summarize CI log first.
- Inspect workflow and infra/prod plan path.
- Avoid dependency/provider changes until the policy-check evidence is reviewed.
```

Token-saving behavior:

- Load only the index first.
- Load at most three curated learning summaries by default.
- Never load raw `learning-events.jsonl` during normal implementation.
- Prefer graph-linked search over broad keyword search.
- Store long historical details in local artifacts but keep Navigator output compact.
- Mark stale learnings when linked file hashes, graph scope, validation commands, scanner rules, or policy files change.
- If the matching result is weak, show no learning rather than adding noisy context.

Privacy and compliance rules:

- Do not capture raw prompts by default.
- Do not infer user sentiment; record acceptance only from explicit user feedback.
- Do not store personal performance judgments.
- Do not store secrets, credentials, PII, PHI, customer data, or raw vulnerability details beyond exact IDs and safe summaries.
- Teams must be able to disable capture and retrieval with local policy.
- Sensitive learnings should be searchable only with explicit request and should never load automatically.

What not to implement initially:

- No model training.
- No vector database.
- No background observer.
- No automatic capture of every prompt.
- No hidden user behavior scoring.
- No cross-repo analytics.
- No remote memory service.
- No automatic edits based on learnings.
- No storing full source snippets or raw scanner logs inside the graph-learning index.
- No applying stale learnings without current source evidence.

Implemented sequence:

1. Add `context/graph-aware-learning.md` with matching rules, privacy boundaries, and Navigator behavior. Completed.
2. Add `templates/graph-learning.md` for surfaced learning recommendations. Completed.
3. Add `scripts/graph-learning.py search` using graph-learning links and Learning Agent V2 events. Completed.
4. Add `link`, `inspect`, and `validate` commands. Completed.
5. Add generated `.tailtrail/graph-learning-index.json` support with metadata-only links. Completed.
6. Add `scripts/tailtrail.py learn graph ...` wrappers. Completed.
7. Add Navigator integration that surfaces up to three graph-aware learnings in approval-first plans. Completed.
8. Add token-safety checks to ensure raw event history is not loaded by default during Navigator flow. Completed.
9. Add dedicated Navigator learning approval choices, skip reasons, advisory wording, and capture suggestions. Completed.
10. Add benchmark scenarios for repeated Sonar, dependency, CI, and vulnerability tasks. Future candidate.

Acceptance check:

- A curated learning can be linked to a file, symbol, scanner rule, validation command, endpoint, table, or manifest.
- Navigator can surface one to three matching learnings for a task with known graph scope.
- Each surfaced learning explains why it matched.
- Stale, sensitive, rejected, or unapproved learnings are not loaded automatically.
- Raw prompts and raw history are not stored or loaded by default.
- The bridge improves precision for repeated work without making Code Graph Mapper a learning database.
- The bridge still requires exact current source inspection before implementation.

## Phase 9.2: Learning Refresh And Improvement Agent

Purpose: periodically review TailTrail learnings for stale, low-confidence, contradictory, or harmful guidance and recommend refresh actions before bad patterns influence future work.

Status: completed end to end for the first advisory local refresh agent. TailTrail now inspects learning events, graph-learning links, confidence scores, duplicate candidates, policy freshness, and approved refresh actions; it recommends refresh actions and can record approved `mark-stale`, `suppress`, `archive`, and related decisions without rewriting raw learning history.

Feature rating:

```text
Usefulness if advisory: 8.5 / 10
Enterprise safety value: 9 / 10
Risk if overbuilt: 7.5 / 10
Recommended timing: after Phase 9 baseline confidence scoring
```

Problem to solve:

- Even good learnings can become stale when code, dependencies, CI, Sonar profiles, vulnerability rules, architecture, ownership, or local policy changes.
- Low-confidence user overrides may accumulate as historical events and create noise.
- A previously accepted repo pattern may later be rejected by reviewers, fail CI, become insecure, or drift away from enterprise standards.
- Teams need a way to refresh learning memory deliberately instead of letting old learnings age silently.
- If TailTrail starts giving weak or bad suggestions, users need an explainable way to diagnose which learning caused it and how to improve or suppress it.

Design principle:

- Learning Refresh is an agent/workflow, not a trained model.
- Review learnings with evidence, not vibes.
- Recommend refresh actions; do not auto-edit curated learnings in the first version.
- Current source, tests, scanner output, CI evidence, local policy, and guardrails always override old learnings.
- Keep raw prompt history out of refresh by default.
- Refresh should reduce future token load by pruning stale/noisy learnings, not create another large context file.
- User approval is required before marking a curated learning stale, demoting it, deleting it, or rewriting it.

Refresh triggers:

- User explicitly runs a refresh:

```text
Refresh TailTrail learnings for this repo.
```

- Navigator sees repeated bad suggestions, low confidence, or contradictions:

```text
TailTrail used this learning twice, but validation failed both times.
```

- A linked file, module, test, manifest, pipeline, scanner profile, or policy file changed.
- A learning has not matched any task for a configured period, for example 90 days.
- A learning has a low confidence score or repeated user override.
- A reviewer, CI, Sonar, vulnerability scanner, or benchmark analyzer contradicts a learning.
- A team updates `tailtrail-policy.md`, dependency policy, guardrails, or coding standards.
- Code Graph Mapper marks linked graph scope stale.
- Graph-Aware Learning sees a learning whose linked symbol/file/rule no longer exists.

Implemented files:

- `scripts/learning-refresh.py`: inspect learning files, scores, linked graph metadata, and policy freshness.
- `templates/learning-refresh-report.md`: human-readable refresh recommendation report.
- `context/learning-refresh.md`: refresh rules, stale conditions, and safe-use boundaries.
- `.tailtrail/learning-refresh-report.md`: generated local report, ignored or local-only by default.
- `.tailtrail/learning-refresh-actions.json`: generated local approved refresh actions.

Implemented commands:

```bash
python3 scripts/learning-refresh.py inspect --root .
python3 scripts/learning-refresh.py inspect --root . --tags sonar,java
python3 scripts/learning-refresh.py stale --root . --days 90
python3 scripts/learning-refresh.py recommend --root . --format markdown
python3 scripts/learning-refresh.py apply --root . --action mark-stale --learning-id sonar-java-001 --approved
python3 scripts/tailtrail.py learn refresh --root .
```

Refresh report shape:

```text
# TailTrail Learning Refresh Report

Summary:
- Curated learnings checked: 42
- Trusted learnings: 18
- Candidate learnings: 9
- Weak notes: 7
- Stale candidates: 5
- Contradictions: 3

Recommended actions:
- Mark stale: sonar-java-001
  Reason: linked Sonar rule profile changed and validation command no longer exists.
- Demote: dependency-java-004
  Reason: reviewer rejected direct transitive overrides twice after this learning was created.
- Improve: ci-terraform-002
  Reason: missing validation command and linked workflow path moved.
- Keep: validation-auth-003
  Reason: high confidence, recent successful match, tests still present.

Approval:
- Review before applying.
- No learning files were changed.
```

Learning refresh actions:

- **keep**: learning is still fresh and useful.
- **improve**: learning needs better evidence, stale condition, tags, validation command, or scope.
- **demote**: learning should move from trusted to candidate or weak-note.
- **mark-stale**: learning should not auto-surface until refreshed.
- **suppress**: learning should not be used because it conflicts with policy or current evidence.
- **archive**: learning is old/noisy and should move out of normal retrieval.
- **merge**: duplicate learnings should become one clearer learning.
- **delete**: only with explicit user approval and only when policy allows deletion.

Refresh scoring inputs:

- current Learning Confidence score
- last matched date
- number of successful matches
- number of failed matches
- user acceptance/rejection/revision history
- validation outcomes after the learning was used
- reviewer or owner feedback when captured
- linked file/hash freshness
- Code Graph Mapper scope freshness
- scanner rule/profile changes
- dependency manifest changes
- local policy or guardrail changes
- benchmark analyzer findings
- quality loop findings

Examples:

Example 1: stale Sonar learning:

```text
Learning:
For validator cognitive complexity, extract named guard methods and preserve validation order.

Refresh finding:
- Linked rule: Sonar:S3776
- Linked file: PaymentValidator.java
- Validation command: mvn test -Dtest=PaymentValidatorTest
- Problem: PaymentValidatorTest was renamed and Sonar profile changed.

Recommendation:
- Mark stale until validation command and rule profile are refreshed.
```

Example 2: user-accepted but bad practice:

```text
Learning event:
User accepted broad dependency override to fix transitive CVE.

Refresh finding:
- Score: 38 / 100
- Validation: not run
- Reviewer later rejected this pattern
- Dependency Gate says parent BOM upgrade is preferred

Recommendation:
- Do not promote.
- Keep as low-confidence historical event only.
- Add anti-pattern note: avoid direct transitive overrides unless policy approves.
```

Example 3: useful learning improvement:

```text
Learning:
Run npm test for auth middleware changes.

Refresh finding:
- Recently matched 6 times
- Tests passed 5 times
- One failure showed missing lint check

Recommendation:
- Improve learning to say: run npm test and npm run lint for auth middleware changes.
```

Navigator integration:

- Navigator should not run refresh on every prompt.
- Navigator can suggest refresh when:
  - a surfaced learning has low confidence
  - a trusted learning conflicts with current evidence
  - the same learning caused repeated failed validation
  - graph-linked files or scanner rules changed
  - user asks why TailTrail keeps giving a bad suggestion
- Navigator now includes Learning Refresh Awareness when those signals appear:
  - It lists the refresh reasons in the plan.
  - It suggests `python3 scripts/tailtrail.py learn refresh recommend --root .`.
  - It states that refresh is advisory and must not demote, suppress, archive, delete, or rewrite learnings without explicit approval.
- Navigator should show refresh as an optional next command:

```bash
python3 scripts/tailtrail.py learn refresh --root .
```

- Navigator should not automatically demote, delete, or rewrite learnings.

Token-saving behavior:

- Inspect `.tailtrail/learning-index.md` first.
- Load only matching learning records, not full raw history.
- Use score summaries instead of raw event history.
- For large repos, refresh by tag/module/date rather than all learnings.
- Archive old events before loading them.
- Keep refresh reports compact and generated locally.

Privacy and compliance rules:

- Do not use raw prompts by default.
- Do not score user competence or user behavior.
- Score learning quality and evidence only.
- Do not upload learning data.
- Do not store secrets, PII, PHI, customer data, or raw scanner logs.
- Sensitive learnings require explicit refresh request.
- User approval is required before changing learning files.

What not to implement initially:

- No background learning monitor.
- No automatic learning edits.
- No model training.
- No vector database.
- No cross-repo aggregate learning refresh.
- No hidden user scoring.
- No remote dashboard.
- No raw prompt replay.

Acceptance check:

- A user can ask TailTrail to inspect learning freshness and receive a report.
- The report identifies stale, weak, contradictory, duplicate, or high-quality learnings.
- Low-confidence user overrides remain historical events unless evidence improves.
- Refresh suggestions explain the evidence behind each recommendation.
- No learning files are changed without explicit approval.
- Navigator can suggest refresh when a learning appears harmful, stale, or contradictory.
- Refresh reduces noisy learning retrieval instead of increasing routine token usage.

## Phase 9.5: TailTrail Quality Loop

Purpose: track whether TailTrail chose the right features, avoided overlap, preserved guardrails, and produced useful outcomes so the tool can improve over time with explicit user approval.

Status: completed end to end for the first local reviewable loop. TailTrail now supports approved compact behavior capture, monthly or scoped summaries, reviewable improvement proposals, and approved quality decisions. It remains advisory: no raw prompt logging, no background observer, no automatic TailTrail edits, and no default loading of raw quality history.

Feature rating:

```text
Usefulness if kept small: 8.5 / 10
Enterprise maturity value: 9 / 10
Risk if overbuilt: 7 / 10
Recommended timing: later, after guardrails + navigator + learning
```

Honest assessment:

- This is a strong enterprise feature because TailTrail will eventually have overlapping choices: AIDLC, review, QA, handoff, dependency gate, token routing, learning capture, release flow, and future policy checks.
- It should not be called "self-healing" in V1 because automatic self-modification is risky and hard to govern.
- It is valuable if it behaves like a reviewable quality loop: observe behavior, evaluate fit, and propose improvements.
- It becomes a clog if it logs too much, runs on every tiny task, stores raw prompts, judges everything, or changes TailTrail behavior without approval.

Problem to solve:

- TailTrail features can overlap and create process drift.
- Agents may choose a heavy workflow for a small task.
- Agents may skip a necessary gate for risky work.
- Review, QA, maintainability, and handoff can duplicate each other if the workflow is not selected carefully.
- Token-saving can conflict with exactness if risky material is summarized.
- Learning capture can become noisy if every task writes history.
- Teams need evidence about whether TailTrail usage is improving outcomes or adding friction.

Design principle:

- Observe lightly.
- Evaluate later.
- Recommend improvements.
- Require explicit user or maintainer approval before changing TailTrail behavior.
- Store summaries, not raw sensitive content.
- Prefer local, per-repo data before any org-level aggregation.
- Keep the loop explainable and auditable.

Planned behavior:

- Capture compact behavior events only when the user approves or a command explicitly records one.
- Track what TailTrail recommended or used:
  - user goal summary
  - selected features such as AIDLC, review, QA, handoff, token route, dependency gate, learning, release, or team init
  - skipped features
  - files or docs loaded
  - checks run
  - validation outcome
  - user acceptance: accepted, rejected, revised, partially accepted, or unknown
  - workflow fit: too heavy, too light, correct, unknown
  - overlap signals: duplicated review, redundant handoff, unnecessary AIDLC, missing gate, missed validation
- Evaluate behavior against guardrails, navigator recommendations, dependency gate rules, and learning outcomes.
- Produce suggestions, not automatic rule changes.
- Summarize recurring behavior patterns monthly or per repo.

Example questions it should answer:

- Did TailTrail use AIDLC for tiny low-risk tasks too often?
- Did dependency changes always trigger `DEPENDENCY-GATE.md`?
- Did review and QA duplicate the same checks?
- Did handoff appear only when another person/team needed transfer context?
- Did token routing preserve exact risky text?
- Did users reject answers because the workflow was too broad?
- Did TailTrail skip learning capture for reusable CI/Sonar fixes?
- Which TailTrail features led to accepted outcomes most often?

Proposed files:

- `.tailtrail/quality-events.jsonl`: compact local behavior events. Implemented as generated local output.
- `.tailtrail/quality-summary.md`: curated patterns and improvement suggestions. Implemented as optional generated output.
- `.tailtrail/quality-decisions.md`: approved changes to TailTrail usage rules or local policy. Implemented as optional generated output.
- `templates/quality-event.md`: manual event capture shape. Implemented.
- `templates/quality-review.md`: monthly or milestone review shape. Implemented.
- `context/quality-loop.md`: safe-use rules, boundaries, and Navigator/quality-loop guidance. Implemented.
- `scripts/quality-loop.py`: local Python helper for capture, summarize, review, propose, and decide. Implemented.

Potential commands:

```bash
python3 scripts/quality-loop.py capture --workflow review,qa --fit too-heavy --outcome revised --approved
python3 scripts/quality-loop.py capture --workflow dependency-review --fit correct --outcome accepted --approved
python3 scripts/quality-loop.py summarize --month 2026-07
python3 scripts/quality-loop.py review --root .
python3 scripts/quality-loop.py propose --area navigator
python3 scripts/quality-loop.py decide --area navigator --decision "Skip AIDLC for tiny docs-only tasks." --approved
python3 scripts/tailtrail.py quality-loop review --month 2026-07
```

Implemented command behavior:

- `capture`: builds a compact behavior event. Without `--approved`, it prints the event and records nothing. With `--approved`, it appends to `.tailtrail/quality-events.jsonl`.
- `summarize`: summarizes workflow fit, outcomes, validation, overlap flags, missed gates, sources, and recent suggestions. `--write-result` writes `.tailtrail/quality-summary.md`.
- `review`: prints the summary plus improvement proposals.
- `propose`: prints recommended improvements only.
- `decide`: records an approved/rejected/deferred/proposed quality-loop decision in `.tailtrail/quality-decisions.md`; requires `--approved`.

Implemented proposal output:

- issue
- evidence
- proposed files that may be impacted
- prompt or rule change
- review note: recommended change only; review before editing

Suggested event schema:

- timestamp
- repo slug or local project name
- task type
- goal summary
- workflow selected
- workflow skipped
- source of recommendation: user, navigator, intent expansion, manual, hook, unknown
- guardrails applied
- docs loaded
- exact materials preserved
- validation commands and outcome summary
- user acceptance status
- workflow fit: too-heavy, too-light, correct, unknown
- overlap flags
- missed gate flags
- improvement suggestion
- sensitivity marker
- approval status: proposed, approved, rejected, deferred

Quality rules:

- Do not store full raw prompts by default.
- Do not record secrets, tokens, credentials, PII, PHI, customer data, or raw logs.
- Do not capture every task automatically.
- Do not infer user satisfaction from silence.
- Do not promote a suggestion into TailTrail rules without explicit approval.
- Do not use quality logs as default prompt context.
- Keep exact risky details out of summaries unless the user explicitly includes them.

Integration with existing backlog:

- Agent Guardrails define what valid behavior means.
- TailTrail Navigator defines what workflow should have been recommended.
- Learning Agent V2 captures reusable repo/project knowledge.
- Quality Loop evaluates TailTrail behavior and proposes improvements to Navigator rules, guardrail reminders, command help, and local policy.
- Enterprise Reporting can include aggregate quality patterns later.

Token-saving rules:

- Load `.tailtrail/quality-summary.md` only during quality review or Navigator tuning.
- Never load `.tailtrail/quality-events.jsonl` into routine coding prompts.
- Summarize quality events by month, feature, and workflow fit.
- Keep at most three relevant quality insights when tuning Navigator or local policy.
- Archive or prune old events after thresholds are reached.

Suggested thresholds:

- If `quality-events.jsonl` exceeds 100 events, summarize by month.
- If more than 20 percent of small tasks are marked `too-heavy`, tune Navigator to skip AIDLC/review/handoff more aggressively.
- If dependency changes are missing dependency gate more than once, add a stronger guardrail reminder.
- If a workflow is rejected three times for the same reason, propose a local policy or prompt override update.
- If a quality summary has not been reviewed in 90 days, mark suggestions stale instead of applying them.

Non-goals:

- No autonomous self-modification.
- No hidden prompt rewriting.
- No automatic capture of all prompts.
- No central telemetry service.
- No cross-repo aggregation until local quality proves useful.
- No sentiment guessing.
- No default use of quality logs as agent context.

What remains later:

- Navigator-triggered optional quality-loop capture suggestions after repeated plan rejections.
- Benchmark Harness integration that can attach benchmark analyzer findings to quality proposals.
- Learning Refresh integration that can cite stale learning actions inside quality summaries.
- Enterprise Reporting aggregation after local per-repo quality events prove useful.
- Optional pruning/archive command once repos collect more than 100 quality events.

Acceptance check:

- A user can manually record whether a TailTrail workflow was too heavy, too light, or correct.
- A monthly summary can show repeated overlap, missed gates, and accepted workflow patterns.
- Suggestions are reviewable and require approval before changing docs, prompts, Navigator rules, or local policy.
- Routine coding prompts do not load raw quality history.
- Sensitive information is not captured by default.
- The feature helps reduce process drift instead of adding another mandatory process.

Implemented acceptance status:

- Manual approved capture is implemented.
- Summary and review reports are implemented.
- Reviewable proposals with impacted files and prompt/rule changes are implemented.
- Approved quality decisions are implemented.
- Raw quality history is not loaded by Navigator or normal coding flows.
- Sensitive data capture remains user-controlled and excluded from summaries unless `--include-sensitive` is used.

## Phase 9.7: Enterprise Reporting

Purpose: help leads, platform teams, and governance reviewers understand TailTrail adoption, quality patterns, dependency decisions, validation gaps, and approximate token-saving impact using local artifacts.

Status: completed end to end for the first local advisory report. TailTrail now generates Markdown or JSON enterprise reports from local Quality Loop events, Learning Agent events, Learning Refresh actions, optional AIDLC artifact counts, and optional measured token telemetry. Reports are local-only and do not include raw prompts, raw logs, secrets, PII, PHI, customer data, or sensitive scanner output by default.

Problem to solve:

- Teams need to know whether TailTrail improves outcomes or only adds process.
- Leads need visibility into repeated CI/Sonar issues, validation gaps, dependency decisions, and accepted/rejected solution patterns.
- Token-saving needs measurement before it becomes a strong enterprise claim.

Design principle:

- Local reports only.
- No central telemetry service.
- No raw prompts or sensitive data by default.
- Summarize counts and trends, not private content.
- Make reports useful for retrospectives and platform improvement, not surveillance.

Planned file:

- `scripts/tailtrail-report.py`: generate a local report for a month or date range. Implemented.
- `templates/enterprise-report.md`: report output shape. Implemented.
- `.tailtrail/enterprise-report.md`: optional generated local report when `--write-result` is used. Implemented as generated output.

Potential inputs:

- `.tailtrail/learnings.md`
- `.tailtrail/learning-index.md`
- `.tailtrail/learning-events.jsonl`
- `.tailtrail/quality-summary.md`
- `.tailtrail/quality-events.jsonl`
- AIDLC handoff and validation summaries when explicitly included

Report sections:

- tasks captured
- accepted/rejected/revised/partial solution counts
- repeated CI/Sonar issues
- dependency decisions avoided, approved, deferred, or rejected
- validation commands run and skipped
- validation gaps
- common reusable learnings
- stale learnings
- workflow fit: too heavy, too light, correct, unknown
- guardrail misses or risk callouts
- approximate token/context savings when measured telemetry is unavailable
- measured token savings only when real model/API usage metadata is provided

Possible command:

```bash
python3 scripts/tailtrail-report.py --month 2026-07 --root .
python3 scripts/tailtrail.py report --month 2026-07
python3 scripts/tailtrail.py report --month 2026-07 --include-aidlc --write-result
python3 scripts/tailtrail.py report --start 2026-07-01 --end 2026-07-31 --format json
python3 scripts/tailtrail.py report --token-telemetry .tailtrail/token-usage.jsonl
```

Implemented behavior:

- Reads `.tailtrail/quality-events.jsonl` for workflow fit, user outcome, validation, workflow usage, overlap flags, and missed gates.
- Reads `.tailtrail/learning-events.jsonl` for acceptance, validation, task types, tags, confidence bands, dependency gate usage, and no-new-dependency evidence.
- Reads `.tailtrail/learning-refresh-actions.json` for stale/suppress/archive/improve/demote action counts.
- Counts AIDLC artifacts only when `--include-aidlc` is provided.
- Reads measured token telemetry from `.tailtrail/token-usage.jsonl` or `--token-telemetry` when present.
- Falls back to approximate curated-context size when measured telemetry is missing.
- Writes `.tailtrail/enterprise-report.md` only when `--write-result` is provided.
- Supports `--month`, `--start`, `--end`, `--format json`, and `--include-sensitive`.

Token evidence rule:

- If measured model/API usage metadata is available, report measured baseline, TailTrail, saved tokens, and reduction percentage for those records only.
- If measured telemetry is unavailable, report only local approximate context size and clearly say exact token savings are unavailable.

Privacy and compliance rules:

- Do not include raw prompts by default.
- Do not include secrets, credentials, PII, PHI, customer data, or raw logs.
- Redact sensitive values.
- Allow local teams to exclude files or sections.
- Keep the report commit/ignore choice configurable by repo.

Acceptance check:

- A project can generate a useful monthly TailTrail report locally.
- The report uses local artifacts only.
- Sensitive data is excluded or summarized.
- The report helps decide which TailTrail rules, Navigator paths, guardrails, or policy packs should change.

Implemented acceptance status:

- Monthly and date-range reports are implemented.
- Markdown and JSON output are implemented.
- Optional local write to `.tailtrail/enterprise-report.md` is implemented.
- Quality, learning, refresh, optional AIDLC, and token evidence sections are implemented.
- Token claims are evidence-labeled and guarded.
- No data is uploaded or polled.

Future candidates:

- Multi-repo aggregation from explicitly provided local report files.
- Trend comparison across months.
- Optional CSV export for governance decks.
- Optional section filters such as `--exclude learning` or `--only quality`.
- Pull request summary mode that compares current month against previous month.
- Enterprise dashboard only after local reports prove useful and privacy review approves it.

## Phase 9.8: Harness Review And Metric Confidence Engine

Purpose: use a Meta-Harness-style feedback loop to improve TailTrail's own operating wrapper over time: Navigator choices, context routing, validation recommendations, learning quality, token budgeting, and evidence labels.

Status: implemented through Layer 3.5 plus the Environment Bootstrap Snapshot pre-layer. Layer 1 Local Harness Review is implemented through `scripts/harness-review.py` and `python3 scripts/tailtrail.py harness quick|review|confidence|recommendations`. Layer 2 Shareable Harness Summary is implemented through `python3 scripts/tailtrail.py harness export-summary`. It rebuilds an allowlisted sanitized summary from local compact artifacts and writes `.tailtrail/harness-summary.json` only with `--write-result`. Layer 2.5 Commit-Friendly Shared Harness Metadata is implemented through `python3 scripts/tailtrail.py harness shared-summary|shared-status|shared-sanitize`. Layer 3 Product Improvement Pipeline is implemented through `python3 scripts/tailtrail.py harness aggregate-shared|analyze`. Layer 3.5 Evidence-Gated TailTrail Improvement Loop is implemented through `python3 scripts/tailtrail.py harness propose|proposal-status|proposal-record`. Environment Bootstrap Snapshot is implemented through `python3 scripts/tailtrail.py bootstrap snapshot|status|refresh`.

Dedicated implementation spec:

- `META-HARNESS-IMPLEMENTATION.md`

The roadmap below keeps the product direction visible. The dedicated spec keeps the exact implementation plan, schemas, commands, examples, privacy rules, and deferred work in one reviewable place.

Research inspiration:

- The Meta-Harness idea is to optimize the harness around a model: prompts, tools, context, examples, scoring, retries, validation, and failure review.
- TailTrail should apply that idea locally and safely. Instead of claiming "the model improved," TailTrail will ask whether the TailTrail workflow around the model was fit for the task.
- Public and enterprise pitch wording should say "inspired by Meta-Harness-style end-to-end harness optimization," not "guaranteed accuracy" or "automatic self-improvement."
- A public Meta-Harness Terminal-Bench artifact shows a practical harness pattern TailTrail should learn from without copying code: capture a compact environment snapshot before the agent starts so the first plan has useful facts about the workspace, available tools, languages, and package managers. For TailTrail, the equivalent should be an original Python bootstrap snapshot that feeds Navigator and later Harness Review.

Problem to solve:

- TailTrail has many orchestration features, but the product needs evidence that the right features were selected for each task.
- Token and value metrics need confidence labels so teams do not overclaim ROI.
- Code suggestions improve when the assistant works inside a precise task harness: exact files, graph scope, local policy, validation expectations, risk boundaries, and explicit skipped context.
- Learning can help over time only when it is confidence-gated, stale-aware, and advisory.
- Local-only learning improves one repo or one developer, but product-level improvement needs a safe way to learn from patterns without uploading raw prompts, source code, repo names, logs, or user identity.
- Users should not pay extra token or time cost during normal work just so TailTrail can analyze itself. Harness review must be cheap, post-task, optional, and mostly deterministic at first.

Difference from Learning Agent V2:

| Area | Learning Agent V2 | Harness Review / Meta-Harness Layer |
| --- | --- | --- |
| Main question | "What repo pattern should future tasks reuse?" | "Did TailTrail choose the right workflow, context, validation, metrics, and learning behavior?" |
| Scope | Project and repo behavior | TailTrail behavior around the task |
| Example | "This repo validates DTOs in service tests." | "Navigator should have selected Test Precision and skipped AIDLC for this small bug fix." |
| Output | Advisory learnings, confidence scores, refresh suggestions | Harness findings, metric confidence, workflow tuning recommendations |
| Risk | Biased or stale repo memory | Overclaiming product improvement or collecting too much telemetry |
| Safety control | Confidence gate and refresh | Read-only review, sanitized summaries, explicit sharing approval |

Planned command:

```bash
python3 scripts/tailtrail.py harness quick --root .
python3 scripts/tailtrail.py harness review --root .
python3 scripts/tailtrail.py harness confidence --root .
python3 scripts/tailtrail.py harness recommendations --root . --format markdown
python3 scripts/tailtrail.py harness review --root . --write-result
python3 scripts/tailtrail.py harness export-summary --root .
python3 scripts/tailtrail.py harness export-summary --root . --write-result
python3 scripts/tailtrail.py bootstrap snapshot --root .
python3 scripts/tailtrail.py bootstrap status --root .
```

Planned files:

- `scripts/harness-review.py`: deterministic local harness review and recommendation engine. Implemented.
- `scripts/bootstrap-snapshot.py`: deterministic local repo/runtime snapshot used before Navigator planning. Implemented.
- `templates/harness-review.md`: human-readable report template.
- `.tailtrail/harness-review.md`: optional generated local report when `--write-result` is provided. Implemented.
- `.tailtrail/harness-events.jsonl`: optional approved compact harness review events only if later needed.
- `.tailtrail/harness-local-summary.json`: optional Layer 1 local summary when the user explicitly asks for it with `--write-result`. Implemented.
- `.tailtrail/harness-summary.json`: optional Layer 2 sanitized shareable summary when the user explicitly runs `harness export-summary --write-result`. Implemented as local output only; not auto-committed.
- `.tailtrail/harness-recommendations.json`: optional machine-readable recommendations with proposed files, rationale, and confidence. Implemented.
- `.tailtrail/bootstrap-snapshot.json`: optional generated local snapshot with safe repo/runtime facts.

Planned inputs:

- `.tailtrail/bootstrap-snapshot.json`
- `.tailtrail/task-starts/*.json`
- Navigator or Start report JSON when available.
- `.tailtrail/quality-events.jsonl`
- `.tailtrail/outcome-events.jsonl`
- `.tailtrail/learning-events.jsonl`
- `.tailtrail/learning-refresh-actions.json`
- `.tailtrail/token-budget-events.jsonl`
- `.tailtrail/context-receipts.jsonl`
- `.tailtrail/token-usage.jsonl`
- `tailtrail-meta/code-graph-cache.json`
- Benchmark result JSON or Markdown when explicitly supplied.

Performance model:

| Mode | When used | Expected cost | Behavior |
| --- | --- | --- | --- |
| Skip | Tiny prompt, no TailTrail artifacts, or user did not ask | 0 seconds | Do nothing. Do not create noise. |
| Quick | After a normal task or when user asks for lightweight review | About 1-3 seconds | Read compact local JSON/JSONL only, produce short findings. |
| Standard | When user asks for harness review, value report, or tuning recommendations | About 3-10 seconds | Read task, outcome, context receipt, learning, token, graph, and scanner summaries. |
| Deep local | Before demos, pilot reviews, or release readiness | About 15-60 seconds | Compare multiple local tasks and detect repeated workflow or metric issues. |
| Batch summary | Later enterprise/public opt-in aggregation | About 10-90 seconds depending on files supplied | Aggregate sanitized summaries only. No raw source or prompts. |

V1 should not call a model or external API. It should be deterministic and local so the end user does not feel extra delay while doing normal development.

Planned review dimensions:

- **Workflow fit**: Did Navigator select the right features, or was the plan too heavy, too light, or missing a useful route?
- **Bootstrap fit**: Did TailTrail create or reuse a compact safe repo/runtime snapshot before planning, and did it reduce repeated first-turn discovery?
- **Context fit**: Did TailTrail use graph/cache/slices before broad reads, and did it avoid unrelated docs?
- **Validation fit**: Did TailTrail suggest or run the smallest meaningful check for the changed behavior?
- **Metric confidence**: Are token/value claims estimated, local-evidence-backed, measured, or unsupported?
- **Learning fit**: Were surfaced learnings high-confidence, fresh, graph-relevant, and explicitly approved?
- **Scanner/security fit**: Did TailTrail preserve exact evidence and ask before scans?
- **Code precision fit**: Did the harness identify exact files, callers, tests, policy, and safeguards before code writing?

Metric confidence bands:

```text
low:
  local estimate only, no accepted outcome, no validation evidence

medium:
  Navigator/start plan + context receipt + approved outcome or validation status

high:
  measured token telemetry or concrete validation evidence + accepted outcome + no unresolved guardrail finding

very high:
  repeated similar tasks with high-confidence outcomes, fresh graph links, and no stale-learning warnings
```

Layered implementation design:

### Pre-Layer: Environment Bootstrap Snapshot

This is the pre-task half of the Meta-Harness idea. Harness Review checks behavior after the task; Bootstrap Snapshot improves the starting point before Navigator plans.

Status: implemented. TailTrail now supports `python3 scripts/tailtrail.py bootstrap snapshot|status|refresh --root .`, writes `.tailtrail/bootstrap-snapshot.json` only when `--write-result` or `refresh` is used, feeds Navigator with missing/stale/fresh status, and improves Harness Review `bootstrap_fit` scoring.

Purpose:

- Give Navigator a compact, safe view of the workspace before it chooses a path.
- Reduce repetitive first-turn discovery such as repeatedly asking the assistant to inspect top-level files, identify languages, find dependency manifests, or determine test tooling.
- Improve token budgeting before broad context is loaded.
- Improve repo overview, scanner, quality, test, graph, and handoff prompts by starting from structured workspace facts.

What it should capture:

- repo root and TailTrail install state
- top-level project shape without reading full source content
- detected languages by extension and manifest
- package managers and dependency manifests
- test frameworks and likely test commands when inferable
- CI files and pipeline config presence
- scanner-related files such as Sonar, SARIF, Trivy, Grype, dependency manifests, and lockfiles
- Docker, Terraform, SQL, Java, Python, .NET, and frontend signals
- existing `.tailtrail/` artifacts and whether they are fresh
- code graph cache presence, timestamp, and stale/fresh status
- local policy, guardrails, AIDLC docs, and learning files presence
- available local commands only when cheap and safe to check

What it must not capture:

- source code bodies
- raw prompts
- raw logs
- secrets or environment variable values
- private URLs
- user identity
- absolute paths in shareable summaries
- large file contents

Planned snapshot shape:

```json
{
  "schema_version": "1",
  "root_kind": "git",
  "tailtrail_installed": true,
  "languages": ["java", "python", "terraform"],
  "manifests": ["pom.xml", "requirements.txt"],
  "test_signals": ["junit", "pytest"],
  "ci_signals": ["github_actions"],
  "scanner_signals": ["sonar", "trivy"],
  "tailtrail_artifacts": {
    "code_graph": "fresh",
    "learnings": "present",
    "policy": "present"
  },
  "recommended_first_reads": [
    "README.md",
    "pom.xml",
    "tailtrail-meta/code-graph-cache.json"
  ],
  "avoid_first_reads": [
    "full source tree",
    "large generated folders"
  ]
}
```

Implemented Navigator integration:

- `tailtrail start` and `tailtrail guide` should check whether `.tailtrail/bootstrap-snapshot.json` exists and is fresh.
- If it is fresh, Navigator should use it to choose workflow, context, graph, test, scanner, and token budget behavior.
- If it is missing or stale, Navigator suggests creating or refreshing it with an explicit command.
- For read-only prompt planning, Navigator shows the snapshot status and command but does not write `.tailtrail/bootstrap-snapshot.json` by itself.
- For simple tiny prompts, Navigator skips snapshot creation to avoid overhead.

Implemented Harness Review integration:

- Harness Review should score **Bootstrap fit**:
  - `missing`: no usable snapshot exists, or the snapshot exists but carries too little useful signal
  - `useful`: snapshot is fresh and contains safe language, manifest, test, CI, scanner, or first-read signals
  - `stale`: snapshot is invalid or workspace shape changed since it was created
  - `noisy`: snapshot is fresh but hit scan limits, saturated first reads, or detected too many manifests/top-level directories
- Current implementation reports the explicit label in Harness Review JSON and Markdown. Future tuning can connect context receipts and value reports to explicit snapshot influence.

Example finding:

```text
Finding: Navigator performed broad repo discovery even though no bootstrap snapshot existed.
Recommendation: Create `.tailtrail/bootstrap-snapshot.json` before repo overview, scanner, graph, or handoff prompts.
Confidence: medium
Expected benefit: fewer repeated first-turn reads and better token budget estimation.
```

Why this fits TailTrail:

- It is deterministic and local.
- It improves planning before tokens are spent on broad reads.
- It does not require model calls.
- It complements Code Graph Mapper rather than replacing it.
- It gives TailTrail a stronger "first useful plan" story for demos and real usage.

### Layer 1: Local Harness Review

Layer 1 is the default and safest implementation.

What it does:

- Runs after a task, value report, benchmark, learning refresh, or user-requested harness review.
- Reads only local TailTrail artifacts.
- Produces a local report about TailTrail behavior.
- Recommends improvements but does not edit TailTrail rules automatically.
- Helps one developer or one repo get better results over time.

What it reviews:

- Did Navigator classify the task correctly?
- Did the selected workflow match the task size and risk?
- Did TailTrail skip unnecessary heavy features for a small task?
- Did TailTrail include Code Graph, Test Precision, scanner parsing, or handoff when the prompt required them?
- Did context receipts show focused reads rather than broad noisy reads?
- Did value reporting use the correct evidence label: estimated, local evidence, measured telemetry, or unavailable?
- Did learning usage stay advisory, fresh, high-confidence, and graph-relevant?

Example finding:

```text
Finding: Navigator selected AIDLC for a small bug fix because the prompt included "add unit test".
Recommendation: Suppress AIDLC when the only feature-like signal is test addition, changed-file count is small, and no regulated/risky keyword appears.
Confidence: medium
Proposed file: scripts/navigator.py
Review note: user must approve before TailTrail routing rules are changed.
```

Why it helps:

- It improves TailTrail behavior without needing shared telemetry.
- It gives the user an explainable reason for workflow changes.
- It protects against feature sprawl by showing when a feature was too heavy, too light, or not useful.

### Layer 2: Shareable Harness Summary

Layer 2 is optional and explicit. It exists because local-only improvement helps the current repo, but not the broader product.

What it does:

- Converts local harness findings into a sanitized summary.
- Removes raw prompts, raw logs, source code, file paths, repo names, user names, branch names, secrets, private package names, private URLs, and customer-specific identifiers.
- Keeps only categorical evidence that can improve TailTrail rules.
- Writes a local file the user can inspect before sharing.
- Never uploads automatically in the initial implementation.
- Optionally writes a commit-friendly shared metadata event to `tailtrail-meta/harness-summary.jsonl` so product improvement signals can ride with normal repo commits instead of requiring a separate manual upload.

Example sanitized summary:

```json
{
  "schema_version": "1",
  "tailtrail_version": "1.4.0",
  "task_type": "bug_fix_with_tests",
  "language_family": "java",
  "workflow_selected": ["navigator", "code_graph", "test_precision"],
  "bootstrap_snapshot_used": true,
  "bootstrap_snapshot_fit": "useful",
  "workflow_fit": "correct",
  "context_fit": "focused",
  "validation_fit": "strong",
  "token_budget_fit": "underestimated",
  "metric_confidence": "medium",
  "learning_used": false,
  "scanner_type": "sonar",
  "issue_type": "validation_gap",
  "recommendation_codes": ["increase-budget-java-sonar-test"]
}
```

Why it helps:

- Teams can send product-useful evidence without exposing code or private context.
- Internal admins can compare patterns across teams without collecting raw development history.
- Public users can optionally contribute generic product signals later if the project adds a contribution process.
- Developers do not need to push metadata separately when the repo opts into tracking `tailtrail-meta/harness-summary.jsonl`; it becomes part of normal repo changes.

### Layer 2.5: Commit-Friendly Shared Harness Metadata

Status: implemented. TailTrail can dry-run, append, status-check, and sanitize shared harness metadata through:

```bash
python3 scripts/tailtrail.py harness shared-summary --root . --dry-run
python3 scripts/tailtrail.py harness shared-summary --root . --write-result --approved
python3 scripts/tailtrail.py harness shared-status --root .
python3 scripts/tailtrail.py harness shared-sanitize --root .
```

Implemented files:

- `scripts/harness-review.py`: builds the sanitized shared event, rejects private-looking values, appends JSONL only with explicit approval, and validates the shared file.
- `tailtrail-meta/README.md`: explains the shared/private metadata boundary.
- `tailtrail-meta/harness-summary.schema.json`: documents the allowed shared event shape.
- `scripts/setup-scan.py`: classifies shared harness metadata as generated-but-shareable metadata.
- `templates/tailtrail-gitignore.md`: documents that `tailtrail-meta/harness-summary.jsonl` is usually shared only when the team opts in.

What remains later:

- `aggregate-shared` across multiple repos.
- monthly rotation if the JSONL file grows too large.
- admin/product proposal generation from repeated shared patterns.
- automatic task-completion prompt integration through Navigator once the UX is proven.

Purpose:

- Solve the local-only metadata problem without adding hidden telemetry.
- Keep raw TailTrail runtime files private in `.tailtrail/`.
- Create a sanitized tracked file that can be committed and pushed with normal code changes.
- Let future TailTrail maintainers or enterprise admins aggregate evidence from checked-out repos.

Recommended tracked path:

```text
tailtrail-meta/harness-summary.jsonl
```

Why not `.tailtrail/`:

- `.tailtrail/` is ignored by default and may contain private runtime state.
- Shared metadata should have a clear boundary from local task starts, token events, scanner output, raw learning events, and install state.
- `tailtrail-meta/` makes the intent visible: sanitized process metadata that a repo may choose to share.

Allowed fields:

- schema version
- TailTrail version
- month or coarse timestamp
- task type
- language family
- selected workflow categories
- review scope category
- requirement fulfillment band
- validation fit band
- token budget fit band
- metric confidence band
- learning signal band
- scanner category
- issue category
- recommendation codes

Forbidden fields:

- raw prompts
- raw assistant responses
- source code or diffs
- file paths
- function names
- repo names
- branch names
- user names or emails
- ticket IDs unless normalized
- customer identifiers
- private URLs or package names
- scanner raw output
- secrets
- absolute local paths

Example event:

```json
{
  "schema_version": "1",
  "event_type": "harness_summary",
  "tailtrail_version": "1.4.0",
  "created_month": "2026-07",
  "task_type": "bug_fix_with_tests",
  "language_family": "java",
  "workflow_selected": ["navigator", "code_graph", "test_precision", "review"],
  "review_scope": "uncommitted",
  "requirement_fulfillment": "partially-aligned",
  "clarification_needed": true,
  "validation_fit": "partial",
  "token_budget_fit": "underestimated",
  "metric_confidence": "medium",
  "learning_signal": "candidate",
  "scanner_type": "sonar",
  "issue_type": "validation_gap",
  "recommendation_codes": ["ask-clarification-on-partial-fulfillment"]
}
```

Implemented commands:

```bash
python3 scripts/tailtrail.py harness shared-summary --root . --dry-run
python3 scripts/tailtrail.py harness shared-summary --root . --write-result --approved
python3 scripts/tailtrail.py harness shared-status --root .
python3 scripts/tailtrail.py harness shared-sanitize --root .
```

Design rules:

- `shared-summary --dry-run` shows exactly what would be written.
- `--write-result --approved` appends one sanitized JSONL event.
- No auto-stage and no auto-commit in V1.
- If the file is already tracked, normal repo commits can include it.
- If the file is untracked, TailTrail should ask the repo owner to review before adding it.
- Sanitizer tests must reject unknown fields and private-looking values.
- JSONL should be append-only to reduce merge conflicts.
- Monthly rotation can be added later if files grow too large.
- `aggregate-shared` is implemented in Layer 3; Phase 2.5 intentionally stops at repo-local shared metadata creation and validation.

### Layer 3: Product Improvement Pipeline

Status: implemented as an explicit, deterministic admin/product workflow. It is not a default local feature and does not run automatically.

What it does:

- Aggregates user-approved sanitized summaries.
- Finds repeated TailTrail behavior issues across repos or teams.
- Converts repeated findings into candidate product changes.
- Recommends Navigator rules, token budget heuristics, prompt compression profiles, scanner parsers, test triggers, benchmark scenarios, docs, or onboarding guidance after review.
- Writes local analysis outputs only when `--write-result` is used.

Implemented commands:

```bash
python3 scripts/tailtrail.py harness aggregate-shared --root . --format markdown
python3 scripts/tailtrail.py harness aggregate-shared --roots ../repo-a --roots ../repo-b
python3 scripts/tailtrail.py harness analyze --summary tailtrail-meta/harness-summary.jsonl
python3 scripts/tailtrail.py harness analyze --root . --write-result
```

Implemented outputs:

- `.tailtrail/meta-harness-analysis.json`: local private machine-readable analysis.
- `.tailtrail/meta-harness-analysis.md`: local private human-readable analysis.

Implemented detection categories:

- repeated recommendation codes
- weak or missing validation fit
- token budget underestimation
- weak or missing metric confidence
- partial or unclear requirement fulfillment
- missing, stale, invalid, or unknown graph cache
- AIDLC over-routing for small bug-fix tasks
- scanner tasks missing healthy graph context

Examples:

- If shared `tailtrail-meta/harness-summary.jsonl` files repeatedly show partial requirement fulfillment, improve Navigator clarification prompts.
- If many Java + Sonar + test tasks underestimate context by 30-40%, increase the budget profile for that task family.
- If many small bug fixes trigger AIDLC only because the prompt says "add tests," tune Navigator to keep those tasks lightweight.
- If many vulnerability tasks miss graph overlays, add a stronger Security Intelligence route.
- If many value reports remain "estimated only," improve telemetry import examples and prompts.
- If many repo overview tasks start with repeated broad discovery, make Bootstrap Snapshot more visible in Navigator.
- If many snapshots are stale or too noisy, tune snapshot freshness rules and summary fields.

Why it helps:

- Product improvement becomes evidence-led instead of opinion-led.
- TailTrail can improve for many users without reading their source code.
- The pitch stays honest: TailTrail improves its workflow logic as approved evidence accumulates, but it does not secretly train on private code.

Recommended hybrid model:

- Local-first by default.
- Deterministic quick review after meaningful TailTrail work only when explicitly requested or included in a value/report command.
- Optional sanitized summary export for teams that want product-level improvement.
- Optional commit-friendly shared metadata in `tailtrail-meta/harness-summary.jsonl`.
- Optional internal aggregation for enterprise admins from checked-out repos.
- Optional public contribution flow only after legal, privacy, and governance review.
- No automatic upload, hidden telemetry, or background service in V1.

### Layer 3.5: Evidence-Gated TailTrail Improvement Loop

Status: implemented as a proposal and decision-record loop. It does not edit TailTrail source files automatically.

Purpose:

- Decide when Meta-Harness understanding is strong enough to change TailTrail itself.
- Prevent one-off user preferences or low-quality accepted shortcuts from becoming product behavior.
- Make every product improvement proposal testable, reviewable, and reversible.

When Meta-Harness learning is strong enough:

- the same issue appears across multiple meaningful tasks
- the issue has measurable product impact, such as wrong Navigator route, weak validation, stale graph reuse, noisy context loading, or token budget underestimation
- the same recommendation appears in more than one local or shared harness summary
- the proposed change can be implemented as deterministic TailTrail behavior
- unit tests, golden plans, benchmark scenarios, or value reports can verify the change
- the change does not weaken guardrails, local policy, security, validation, dependency controls, scanner approval, or explicit user instructions

Do not apply learning when:

- the signal is from one task only
- the evidence is subjective
- the user accepted a low-confidence or unsafe shortcut
- the pattern belongs in repo-local Learning Agent V2 instead of TailTrail product rules
- the recommendation would make TailTrail more aggressive by default without proof
- the recommendation conflicts with source, tests, CI, scanners, policy, guardrails, or user direction

Implementation model:

1. **Collect** approved sanitized categorical metadata.
2. **Analyze** repeated behavior patterns.
3. **Propose** a reviewable TailTrail improvement with evidence, risk, impacted files, tests, and rollback.
4. **Validate and apply** only after explicit human approval.

Implemented commands:

```bash
python3 scripts/tailtrail.py harness analyze --root . --format markdown
python3 scripts/tailtrail.py harness propose --root . --proposal-id MH-2026-07-001
python3 scripts/tailtrail.py harness propose --root . --finding-id MH-F-001 --write-result
python3 scripts/tailtrail.py harness proposal-status --root .
python3 scripts/tailtrail.py harness proposal-record --root . --proposal-id MH-2026-07-001 --status accepted
python3 scripts/tailtrail.py harness proposal-record --root . --proposal-id MH-2026-07-001 --status rolled_back
```

Implemented files:

- `scripts/meta-harness-analyze.py`: group sanitized local/shared evidence into repeated TailTrail behavior findings.
- `scripts/meta-harness-propose.py`: turn a finding into a reviewable product-change proposal.
- `templates/meta-harness-proposal.md`: proposal report with evidence threshold, impacted files, tests, expected improvement, degradation risk, and rollback.
- `.tailtrail/meta-harness-proposals.jsonl`: local private proposal history.
- `.tailtrail/meta-harness-proposal.md`: latest local private proposal report when `--write-result` is used.
- `.tailtrail/meta-harness-analysis.json`: latest local private analysis when `--write-result` is used.
- `.tailtrail/meta-harness-analysis.md`: latest local private analysis report when `--write-result` is used.
- `tailtrail-meta/harness-summary.jsonl`: optional shared sanitized evidence input.
- `tests/test_meta_harness.py`: sanitizer, threshold, proposal, and rollback-record tests.

Likely impacted files by recommendation type:

| Recommendation type | Likely files |
|---|---|
| Navigator routing | `scripts/navigator.py`, `scripts/navigator_core.py`, `scripts/navigator_render.py`, `tests/test_navigator_core.py`, `tests/golden/*` |
| Token budgeting | `scripts/token_budget_coach.py`, `scripts/token-auto.py`, `TOKEN-AUTOPILOT.md`, `tests/test_deterministic_tools.py` |
| Code graph usage | `scripts/code-graph-mapper.py`, `scripts/cache-summary.py`, `context/code-graph-mapper.md`, `tailtrail-meta/code-graph-cache.json`, `tests/test_deterministic_tools.py` |
| Review behavior | `scripts/review-run.py`, `scripts/review-output.py`, `context/review-lenses.md`, `tests/test_review_output.py`, `tests/test_review_scope.py` |
| Learning governance | `scripts/learning-agent.py`, `scripts/learning-refresh.py`, `LEARNING-GOVERNANCE.md` |
| Meta-Harness engine | `scripts/meta-harness-analyze.py`, `scripts/meta-harness-propose.py`, `templates/meta-harness-proposal.md`, `META-HARNESS-IMPLEMENTATION.md`, `ROADMAP.md`, `TAILTRAIL-PITCH.md`, `tests/test_meta_harness.py` |

Verification plan:

- Run existing unit tests.
- Run `python3 scripts/tailtrail.py doctor`.
- Add targeted regression tests for the behavior change.
- Update golden Navigator or report outputs only when intentionally changed.
- Run benchmark harness or scenario replay before/after.
- Compare route selection, validation strength, token budget fit, graph usage, review specificity, and plan noise.
- Accept the proposal only if scores improve or stay equal and no guardrail regression appears.

Example verification:

```text
Before:
Navigator selected: review only
Missed: Code Graph Mapper
Token budget: underestimated
Benchmark score: 21 / 32

After:
Navigator selected: graph -> review -> test planner
Token budget: closer estimate
Benchmark score: 29 / 32
```

Rollback model:

- Every accepted Meta-Harness product change should be a normal git commit.
- Commit messages should include a proposal ID.
- If degradation appears, revert the commit.
- Record a sanitized proposal outcome such as `rolled_back`, with categorical reason and future action.

Example rollback record:

```json
{
  "proposal_id": "MH-2026-07-001",
  "status": "rolled_back",
  "reason": "graph_mapper_triggered_too_often_for_small_lint_tasks",
  "future_action": "add_stricter_changed_file_and_scanner_signal_threshold"
}
```

Operating modes:

| Mode | Purpose | Behavior edits |
|---|---|---|
| `observe` | collect and summarize evidence | none |
| `recommend` | generate reviewable proposals | none |
| `apply` | implement approved proposal through normal code work | explicit approval only |

Deferred:

- no self-editing TailTrail agent
- no automatic rollout
- no hidden developer scoring
- no model-call optimizer loop
- no central aggregation until privacy/legal/admin controls exist
- no raw prompt, source, diff, file path, repo name, branch name, user identity, private URL, scanner output, or secret in shared evidence

Example output:

```text
TailTrail Harness Review

Workflow fit: good
Context fit: medium
Validation fit: weak
Metric confidence: medium
Learning fit: good

Findings:
- Test Precision was skipped even though the prompt asked for unit tests.
- Token budget underestimated Java/Sonar work by 35%.
- Value report should not claim exact token savings because measured telemetry is missing.

Recommended improvements:
- Add a Navigator trigger for "unit test coverage" prompts.
- Increase token budget for Java + Sonar + graph-stale tasks.
- Require validation evidence before publishing high-confidence value reports.
```

What this improves:

- Better workflow selection over time.
- Faster first useful Navigator plans because the workspace starts with a safe bootstrap snapshot.
- More precise code suggestions because the assistant receives a tighter task harness.
- Better metric publishing because every metric receives an evidence confidence label.
- Better learning use because weak, stale, or mismatched learnings stay advisory or suppressed.
- Better product demos because TailTrail can show not only "what happened," but "why the workflow was trustworthy."
- Better org-level improvement because optional sanitized summaries can show repeated TailTrail behavior issues without sharing source code.
- Better cost control because token budget estimates can be compared with context receipts and measured telemetry imports.

What to defer:

- No automatic TailTrail prompt/rule edits.
- No background observer.
- No hidden user-behavior scoring.
- No raw prompt or raw log capture by default.
- No central telemetry service.
- No cross-repo analytics unless users explicitly provide local reports.
- No model/API optimizer loop.
- No automatic benchmark API runner.
- No vector database or graph database requirement.
- No claim that TailTrail guarantees correctness or exact ROI.
- No automatic upload of harness summaries.
- No raw prompt, source, log, file path, repo name, user identity, private URL, or secret in shareable summaries.
- No hidden scoring of a developer's behavior.
- No central product telemetry service until privacy/legal/admin controls exist.
- No shell-heavy environment probing in the first snapshot version.
- No capturing command output that may include secrets or private machine details.
- No automatic snapshot generation for every prompt.

### Meta-Harness Readiness Tiers

Status: implemented. TailTrail now supports `python3 scripts/tailtrail.py harness readiness --root .` and `--roots/--summary` variants. The command decides when Meta-Harness should stay quiet, when it should advise a repo maintainer, and when it should tell central TailTrail maintainers that evidence is strong enough to review a product-improvement proposal.

Purpose:

- Prevent Meta-Harness from interrupting normal development work.
- Make "now is a good time to implement this learning" an evidence-gated decision, not a subjective feeling.
- Separate three audiences:
  - developers doing normal repo work
  - repo maintainers improving a team's local TailTrail usage
  - central TailTrail maintainers deciding whether to change TailTrail itself
- Keep the final improvement loop clear:

```text
Navigator uses approved TailTrail behavior.
Meta-Harness discovers future improvements.
Maintainers approve, validate, and ship those improvements.
Users benefit after update.
```

#### Level 1: Developer Task Mode

Audience: normal developers using TailTrail for feature work, bug fixes, reviews, scans, tests, and handoff.

Behavior:

- Navigator should not run heavy Meta-Harness aggregation during every task.
- Navigator should not ask users to implement TailTrail product improvements during normal repo work.
- Navigator may show a compact Meta-Harness-backed explanation only when the rule is already approved/productized and directly relevant to the task.
- Example:

```text
Why this path:
Meta-Harness-backed evidence shows graph-first reads help similar Sonar tasks.
Recommended path includes Code Graph Mapper.
```

Implemented behavior:

1. Developer task mode returns `stay_quiet` by default.
2. It explicitly blocks aggregation, proposal generation, metadata sharing, automatic TailTrail edits, and developer interruption.
3. Normal `start` and `guide` do not load `.tailtrail/meta-harness-*` local analysis files unless the user explicitly asks for harness analysis.
4. Navigator reads only `.tailtrail/meta-harness-proposals.jsonl` proposal/status records and surfaces at most three short hints when a proposal is already `accepted` or `implemented` and intersects the current registry workflow feature IDs.
5. Navigator does not run `harness aggregate-shared`, `harness analyze`, `harness readiness`, or `harness propose` during normal task planning.

Acceptance check:

- Normal `start` and `guide` commands stay compact.
- Meta-Harness notes appear only when a productized rule is relevant.
- No aggregation, proposal generation, or local metadata capture happens automatically.

#### Level 2: Repo Maintainer Mode

Audience: team leads, repo owners, platform maintainers, or senior engineers reviewing how TailTrail is working in one repo or one team.

Behavior:

- Runs on demand after meaningful work or during a periodic repo review.
- Reviews local TailTrail evidence such as quality events, outcome telemetry, token receipts, graph freshness, learning confidence, scanner routing, and validation fit.
- Produces repo-level improvement recommendations.
- Does not change TailTrail product behavior directly.
- Does not upload data.

Example commands:

```bash
python3 scripts/tailtrail.py harness review --root .
python3 scripts/tailtrail.py harness shared-summary --root . --dry-run
python3 scripts/tailtrail.py harness shared-summary --root . --write-result --approved
```

Implementation plan:

1. Implemented `harness readiness --root .`.
2. Reports repo-maintainer decisions:
   - `stay_quiet`: no valid evidence or no actionable repeated signal.
   - `advise_repo_maintainer`: sanitizer/input issues, repeated local findings, weak validation, or weak metric confidence should be reviewed locally.
3. Includes evidence counts, finding counts, sanitizer/input issue counts, registry status, allowed actions, blocked actions, and next actions.
4. Keeps all repo-local details in `.tailtrail/`; only `tailtrail-meta/harness-summary.jsonl` remains the optional commit-friendly shared artifact.
5. Adds tests for quiet, repo advisory, and central product-improvement decisions.

Acceptance check:

- Repo maintainers can tell whether sharing a summary is useful.
- Weak or stale evidence does not become a central recommendation.
- Sharing remains explicit and approved.

#### Level 3: Central TailTrail Maintainer Mode

Audience: TailTrail maintainers, platform owners, or admins responsible for improving the central TailTrail repo.

Behavior:

- Aggregates approved sanitized summaries from multiple repos or teams.
- Decides whether a repeated pattern is strong enough to create a product-improvement proposal.
- Generates proposals with evidence count, impacted TailTrail files, implementation prompts, verification plan, degradation checks, and rollback guidance.
- Product changes remain normal reviewed code changes.
- No automatic rollout.

Example commands:

```bash
python3 scripts/tailtrail.py harness aggregate-shared --roots repo-a --roots repo-b --roots repo-c
python3 scripts/tailtrail.py harness propose --root . --proposal-id MH-2026-07-001
python3 scripts/tailtrail.py harness proposal-record --root . --proposal-id MH-2026-07-001 --status accepted
```

Implementation plan:

1. Extended `meta-harness-analyze.py` with central readiness scoring.
2. Scores valid event count, invalid sanitizer issues, missing inputs, repeated findings, high-severity findings, registry health, weak metric confidence, and weak validation fit.
3. Reports central-maintainer decisions:
   - `stay_quiet`: evidence is too small or no repeated product finding crossed threshold.
   - `advise_repo_maintainer`: sanitizer/input evidence is not clean or registry maturity is not healthy.
   - `recommend_central_tailtrail_improvement`: sanitized evidence is clean, repeated findings crossed threshold, and the Feature Registry is healthy.
4. Added `harness readiness --root .`, `harness readiness --roots repo-a --roots repo-b`, and `harness readiness --summary summary-a.jsonl`.
5. Gates `harness propose`: if central readiness is not `recommend_central_tailtrail_improvement`, proposal output returns `no_proposal`.
6. Added synthetic tests covering all implemented readiness outcomes.

Acceptance check:

- Central maintainers know when a finding is ready to implement.
- One repo or one user preference cannot change TailTrail product behavior.
- Proposal readiness is deterministic and test-backed.
- Product changes are still human-approved, committed, validated, and reversible.

Non-goals:

- No per-task central aggregation.
- No hidden upload.
- No raw prompt, source, diff, path, repo name, branch name, user identity, private URL, scanner raw output, secret, or exact token usage in shared evidence.
- No automatic TailTrail self-editing.
- No automatic rollout to users.
- No hidden scoring of developers or teams.

Safety rules:

- Harness Review is read-only by default.
- Bootstrap Snapshot must be compact, local, deterministic, and source-content-free.
- Recommendations must show proposed files and rationale before any TailTrail rule changes.
- Any harness event capture must be explicit and approved.
- Current source, tests, CI, scanners, local policy, guardrails, and user instructions always win over harness history.
- Metrics must keep evidence labels: estimated, local evidence, measured telemetry, or unavailable.
- Shareable summaries must be inspectable before sharing.
- Local reports can include more context, but summary exports must be sanitized.
- If sanitization cannot prove a value is safe, omit it.
- Product claims must say "inspired by Meta-Harness-style harness optimization" rather than implying guaranteed correctness or model training.

Implementation recommendations:

- Add Bootstrap Snapshot before or alongside the first Harness Review implementation because it improves Navigator input quality and creates a clean pre-task signal for Harness Review.
- Start with `harness quick` and `harness review` as local deterministic commands.
- Reuse existing JSON/JSONL artifacts instead of adding another logging system.
- Keep recommendation codes stable so future aggregation can compare patterns without raw text.
- Add a sanitizer before adding any summary export command.
- Use allowlists for summary fields. Do not try to redact arbitrary raw content and then upload it.
- Make all generated recommendations review-first. TailTrail can propose file and prompt-rule changes, but a user must approve before edits.
- Add tests that prove private-looking fields are not included in summary exports.
- Keep the first version boring: no model calls, no API calls, no background service.
- Implement snapshot generation with filesystem and manifest inspection first. Add command availability checks only when they are cheap, safe, and do not execute project code.
- Treat Code Graph Mapper as the deeper code understanding layer. Treat Bootstrap Snapshot as the small map on the first page.

Acceptance check:

- A user can generate a compact bootstrap snapshot without reading source bodies or executing project code.
- Navigator can use a fresh bootstrap snapshot to improve route selection and suggested first reads.
- A user can run Harness Review locally and get actionable findings.
- The report explains workflow, context, validation, metric, and learning fit.
- The report improves product behavior without self-editing TailTrail automatically.
- Pitch material can truthfully say TailTrail uses a Meta-Harness-inspired review loop to improve workflow quality over time as approved local evidence accumulates.
- A sanitized export contains only categorical fields and recommendation codes.
- Tests prove summary export does not include raw prompt text, source snippets, absolute paths, repo names, branch names, private URLs, or user identifiers.
- Normal implementation tasks do not become slower because Harness Review runs only when requested or as part of reporting.
- Harness Review can report whether Bootstrap Snapshot was used, missing, stale, or noisy.

## Phase 10: External Assets

Purpose: add visual or packaged assets only if the tool needs a shareable identity or internal distribution polish.

Status: completed for a minimal optional asset set. TailTrail now includes original SVG presentation assets in `assets/` and validation tracks them, but no command, skill, hook, adapter, or runtime workflow depends on them.

Planned behavior:

- No assets by default. Superseded by a minimal optional asset set once internal presentation polish became useful.
- If added, use original simple assets created for this project. Completed.
- Keep assets out of the core workflow. Completed.

Implemented files:

- `assets/README.md`: usage rules and provenance.
- `assets/tailtrail-logo.svg`: optional horizontal logo for README, demos, and internal listings.
- `assets/tailtrail-mark.svg`: optional compact mark for cards, slide corners, or catalog thumbnails.

Rules:

- Assets are optional.
- Assets are original TailTrail project files.
- Assets must not be loaded into routine coding prompts.
- TailTrail commands must not depend on assets.
- Do not add third-party logos, stock imagery, icon packs, or generated brand systems without explicit review.

Acceptance check:

- Assets improve discoverability without becoming required for using the tool. Completed.

## Phase 11: Enterprise Polish To 8.5

Purpose: turn TailTrail from a feature-rich toolkit into a practical daily enterprise tool by improving the first command, Navigator-first flow, metrics visibility, installer/update clarity, and guarded learning quality.

Status: completed for the first polish layer. TailTrail now has a `start` command that combines Navigator, approximate token posture, learning quality posture, install/update posture, and the full approval-first Navigator plan. TailTrail also supports `do`, `run`, and free-form task input as Navigator-default aliases, so users can start with `python3 scripts/tailtrail.py do "task"` or `python3 scripts/tailtrail.py "task"` without memorizing the full feature catalog. This is intentionally local, deterministic, and advisory.

Problem to solve:

- TailTrail has many useful features, but users should not need to remember the best sequence.
- Navigator should be the default orchestration path for non-trivial work.
- Product demos need visible metrics, but TailTrail must not claim exact savings without measured usage telemetry.
- Teams need clearer install/update checks before adopting TailTrail across repos.
- Learnings must remain guarded so weak or stale history does not steer the agent into bad decisions.

Implemented files:

- `scripts/task-start.py`: one-command task start report.
- `scripts/tailtrail.py`: adds `start` as the preferred non-trivial task entry point, plus `do`, `run`, and free-form task fallback routing into `start`.
- `TAILTRAIL-COMMANDS.md`: documents `start` and the task-start report.
- `README.md`: points daily users to `start` before lower-level commands.
- `USER-GUIDE.md`: explains when and how to use `start`.
- `scripts/check-tailtrail.py`: validates `scripts/task-start.py` is part of the package.

Command:

```bash
python3 scripts/tailtrail.py start "fix Sonar issue and prepare PR"
python3 scripts/tailtrail.py do "fix Sonar issue and prepare PR"
python3 scripts/tailtrail.py "fix Sonar issue and prepare PR"
python3 scripts/tailtrail.py start "fix Sonar issue" --changed src/service/foo.py
python3 scripts/tailtrail.py start "triage GHSA in package.json" --changed package.json --format json
```

What `start` does:

- Runs the same deterministic Navigator decision engine as `guide`.
- Shows workflow, task types, risk signals, selected feature count, skipped feature count, and likely impacted file count.
- Shows top selected features so users know why TailTrail chose the path.
- Adds Scan Approval reminders when the goal asks for broad Sonar, quality, vulnerability, audit, test, or build work.
- Estimates token posture by counting local characters in focused impacted files and broad TailTrail docs intentionally avoided.
- Labels token posture as approximate local evidence only.
- Shows learning quality posture: learning index exists, events exist, refresh actions exist, surfaced matches, and whether learning approval is required.
- Shows install/update posture: source checkout, installed pack detection, recommended doctor command, and recommended dry-run update check.
- Embeds the full Navigator plan so users can approve, edit, or reject before implementation.

Token evidence rule:

- `start` may show approximate token posture.
- `start` must not claim exact token savings.
- Exact token-savings claims still require `scripts/token-savings.py report --telemetry .tailtrail/token-usage.jsonl` with real model/API usage metadata.

Learning quality rule:

- `start` does not load raw learning history.
- `start` does not promote, suppress, refresh, or write learnings.
- Surfaced learnings remain advisory and require `use learnings`, `ignore learnings`, or `edit plan`.
- Current source, validation, scanner output, local policy, guardrails, and explicit user direction always win over historical learnings.

Installer/update rule:

- `start` only recommends checks.
- Update checks should be dry-run first.
- Locally edited managed files must be preserved unless the user explicitly chooses a backup/overwrite strategy.
- No global shell profile, IDE setting, or background service changes are added by this phase.

Example output shape:

```text
TailTrail Start Report

Navigator Summary
- Workflow: review -> ci_sonar_intelligence -> qa_review
- Selected features: 6
- Skipped features: 8

Token Posture
- Approx baseline tokens: 28000
- Approx TailTrail focused tokens: 900
- Approx saved tokens: 27100
- Evidence: local estimate only

Guarded Learning Quality
- Learning index exists: true
- Surfaced matches: 2
- Learning approval required: true

Install And Update Posture
- Recommended check: python3 scripts/tailtrail.py doctor
- Recommended update check: python3 scripts/tailtrail.py update --root "." --dry-run

Next Step
- Review the Navigator plan. Edit it if needed, then approve implementation.
```

Acceptance check:

- A user can run one command to start non-trivial work.
- The command makes Navigator the obvious first path.
- The command exposes useful metrics without overclaiming exact savings.
- The command makes learning quality visible without trusting weak history blindly.
- The command gives a safe update/install check without changing files.
- The command embeds the full plan so implementation still requires user approval.

Implemented acceptance status:

- `python3 scripts/tailtrail.py start "goal"` works.
- `--changed` is passed into Navigator and metrics.
- `--format json` works for machine-readable usage.
- Token posture is approximate and labeled.
- Learning quality is advisory and non-writing.
- Install/update posture is advisory and non-writing.
- Package validation tracks the new script.

Future candidates:

- Persist approved task-start reports to `.tailtrail/task-starts/` only when explicitly requested.
- Add a `--save-report` flag for demos and retrospectives.
- Add measured token telemetry linkage when users provide real model/API usage metadata.
- Add an update-health command that compares installed pack manifest versions across local repos.
- Add Navigator benchmark scenarios that score whether `start` selects the right workflow.
- Add richer learning-quality warnings from Learning Refresh summaries.
- Add shell-specific PATH helpers only if teams need guided profile edits. The launcher itself is implemented.

## Phase 12: Open-Market Release Readiness

Purpose: prepare TailTrail for public evaluation and open-market release by adding governance files, provenance clarity, release checks, and public-safe metadata.

Status: implemented for the release hygiene and license/provenance finalization layer. TailTrail now includes public governance documents, a release checklist, Apache-2.0 license metadata, explicit public release metadata, NOTICE provenance, and a deterministic release readiness script. This records the project-level public release decision; external legal/security approval still remains a release-owner responsibility.

Problem to solve:

- Internal tools can rely on team context; public tools need explicit license, security, contribution, conduct, provenance, and release expectations.
- Public users need to know what TailTrail does locally, what it does not collect, and what remains approval-first.
- Maintainers need a repeatable pre-release check that catches common accidental publishing mistakes.

Implemented files:

- `LICENSE`: Apache-2.0 public license text for the public distribution.
- `PUBLIC-RELEASE-METADATA.md`: public release license, ownership, and provenance source of truth.
- `SECURITY.md`: security reporting expectations and local/privacy boundaries.
- `CONTRIBUTING.md`: contribution principles and validation expectations.
- `CODE_OF_CONDUCT.md`: basic community behavior standard.
- `RELEASE-CHECKLIST.md`: first public release checklist.
- `scripts/release-check.py`: deterministic public release hygiene check, including license/provenance alignment.
- `.codex-plugin/plugin.json`: license changed from `UNLICENSED` to `Apache-2.0`.
- `NOTICE.md`: updated from internal-only wording to public provenance wording.
- `scripts/tailtrail.py`: adds `release-check`.
- `scripts/check-tailtrail.py`: validates release files and script presence.

Command:

```bash
python3 scripts/tailtrail.py release-check
python3 scripts/release-check.py
```

What the release check validates:

- required public governance files exist
- plugin manifest uses `Apache-2.0`
- `LICENSE`, `PUBLIC-RELEASE-METADATA.md`, `.codex-plugin/plugin.json`, and `NOTICE.md` agree on public license/provenance basics
- tracked files do not include `.DS_Store`, `__pycache__`, or `.tailtrail` local state
- known public-release blocker markers are absent

What this phase does not replace:

- legal approval
- security review
- trademark review
- fresh-clone smoke test
- public package publishing
- GitHub Actions CI
- issue templates
- changelog
- version tagging policy

Open-market items still left after this phase:

- Replace temporary security reporting language with the final public GitHub private vulnerability reporting path or security email.
- Add `CHANGELOG.md`.
- Add `.github/ISSUE_TEMPLATE/` and `.github/pull_request_template.md`.
- Add GitHub Actions CI for package check, release check, adapter sync, and Python compile.
- Add a fresh-clone smoke test script.
- Decide whether distribution stays source-only or adds a package/installer.
- Add semantic versioning and release tag rules.
- Add a short public demo walkthrough.
- Review every doc for internal-only names, private repo references, proprietary wording, and unsupported claims.

Acceptance check:

- A maintainer can run one command before publishing.
- The repo has public governance documents.
- The plugin manifest has public license metadata.
- Provenance wording no longer describes TailTrail as internal-only.
- Public license/provenance metadata is explicit and checked.
- Public release blockers are visible and tracked for later completion.

## Public Release Features

Purpose: track all feature and productization work needed to make TailTrail credible for open-market release, not just internal or enterprise-local use.

Status: planned. The first release hygiene layer is implemented in Phase 12, but the public-release feature set below remains the main release backlog.

Release principle:

- Keep TailTrail local-first and documentation-first.
- Make the first user experience obvious.
- Avoid hidden telemetry, background services, automatic prompt capture, or silent scanner execution.
- Make public claims evidence-based.
- Keep install, update, validation, and rollback paths simple enough for a new user.
- Prefer source-only distribution until real usage proves a package manager is worth owning.

### 1. Public CI

Priority: highest.

Purpose: prove every public commit can pass the basic TailTrail contract without relying on the maintainer's machine.

Implementation plan:

- Add `.github/workflows/tailtrail-ci.yml`.
- Run on pull requests and pushes to `main`.
- Use the default system Python.
- Run:
  - `python3 scripts/check-tailtrail.py`
  - `python3 scripts/tailtrail.py release-check`
  - `python3 scripts/sync-adapters.py --check`
  - `python3 -m py_compile scripts/*.py hooks/*.py`
- Keep CI dependency-free.
- Do not add package installs unless absolutely required.

Acceptance check:

- A public pull request shows pass/fail status.
- CI catches missing expected files, adapter drift, release hygiene failures, and Python syntax errors.
- CI does not need secrets, network services, or paid integrations.

### 2. Changelog And Version Policy

Priority: highest.

Purpose: public users need to know what changed, whether an update is safe, and how TailTrail versions should be interpreted.

Status: implemented. `CHANGELOG.md` records the current public release candidate changes, and `VERSIONING.md` defines semantic versioning, version source-of-truth, tag format, release note sections, and measured-claim boundaries.

Implementation plan:

- Add `CHANGELOG.md`.
- Add version policy to `RELEASE-CHECKLIST.md` or a small `VERSIONING.md`.
- Use semantic versioning:
  - patch: docs, checks, small script fixes
  - minor: new compatible feature or command
  - major: breaking command behavior, install layout, or file contract
- Sync `.codex-plugin/plugin.json` version with release notes.
- Add release note template:
  - added
  - changed
  - fixed
  - security/privacy
  - migration notes
  - validation run

Acceptance check:

- A new user can read what changed between releases.
- Maintainers know when to bump patch/minor/major.
- Release notes include validation and known limitations.

### 3. GitHub Issue And PR Templates

Priority: high.

Purpose: reduce noisy public issues and make useful reports easier.

Status: implemented. Public issue templates now cover bug reports, feature requests, docs feedback, and security-note redirection; `.github/pull_request_template.md` captures purpose, changed files, validation, skipped checks, privacy/security impact, and release-note need.

Implementation plan:

- Add `.github/ISSUE_TEMPLATE/bug_report.md`.
- Add `.github/ISSUE_TEMPLATE/feature_request.md`.
- Add `.github/ISSUE_TEMPLATE/docs_feedback.md`.
- Add `.github/ISSUE_TEMPLATE/security_note.md` that redirects sensitive reports to `SECURITY.md` instead of collecting secrets publicly.
- Add `.github/pull_request_template.md`.

Issue template fields:

- TailTrail version or commit
- command run
- expected behavior
- actual behavior
- operating system
- Python version
- whether generated `.tailtrail/` files are involved
- redacted output

PR template fields:

- purpose
- changed files
- user-facing behavior
- validation commands
- skipped checks
- privacy/security impact
- release note needed yes/no

Acceptance check:

- Public issues collect actionable detail without asking for secrets.
- PRs clearly list validation and user-facing changes.
- Security-sensitive reports are redirected away from public issue content.

### 4. Fresh-Clone Smoke Test

Priority: high.

Purpose: prove TailTrail works for a new public user from a clean checkout.

Status: implemented. `scripts/smoke-test.py` creates a temporary fresh-clone copy, runs core TailTrail commands, avoids network/secrets/global install requirements, and is wired into public CI.

Implementation plan:

- Add `scripts/smoke-test.py`.
- Use only Python standard library.
- Create a temporary directory.
- Copy or reference the current checkout.
- Run core commands from a fresh working state:
  - `python3 scripts/tailtrail.py help`
  - `python3 scripts/tailtrail.py start "fix Sonar issue" --changed missing-file.py`
  - `python3 scripts/tailtrail.py graph --changed scripts/tailtrail.py`
  - `python3 scripts/tailtrail.py quality scan --root .`
  - `python3 scripts/tailtrail.py release-check`
  - `python3 scripts/tailtrail.py doctor`
- Assert commands return expected safe statuses.
- Confirm no command requires network access, secrets, or global install.

Acceptance check:

- A maintainer can run one smoke test before release.
- The smoke test catches broken command wiring.
- Missing changed files are handled safely without crashing the first-run experience.

### 5. Public Demo Walkthrough

Priority: high.

Purpose: show the product value quickly without requiring a user to read the whole guide.

Status: implemented. `DEMO.md` provides a short public walkthrough around `start`, Navigator, graph/quality/vulnerability evidence, local reports, and approval-first boundaries.

Implementation plan:

- Add `DEMO.md` or `docs/public-demo.md`.
- Keep it under 10 minutes.
- Include one realistic workflow:
  1. Run `tailtrail.py start`.
  2. Read Navigator selected/skipped features.
  3. Run graph or quality scan.
  4. Review scan approval behavior.
  5. Show learning capture as suggested-only.
  6. Generate a report.
- Include expected output snippets.
- Explain what TailTrail will not do automatically.

Acceptance check:

- A new user can understand TailTrail's value in one read.
- Demo avoids unsupported claims.
- Demo reinforces approval-first and local-first behavior.

### 6. Public Documentation Sanitizer

Priority: high.

Purpose: prevent accidental publication of internal-only wording, private names, placeholders, unsupported claims, or sensitive content.

Status: implemented. `scripts/public-doc-audit.py` audits public text artifacts for private residue, secret-like values, placeholder markers, direct private repository references, and unsupported claims; `scripts/release-check.py` and CI run it.

Implementation plan:

- Extend `scripts/release-check.py` or add `scripts/public-doc-audit.py`.
- Scan Markdown, JSON, YAML, and Python comments for:
  - internal-only language
  - private organization names
  - private repo URLs
  - secret-like values
  - placeholder security contact text
  - unsupported exact token-saving claims
  - statements implying TailTrail replaces scanners, security review, code review, or legal review
- Keep allowlist comments simple and explicit if needed.
- Add the check to CI.

Acceptance check:

- Public docs can be audited before release.
- Release check catches obvious internal/private residue.
- Exact token savings are only allowed when tied to measured telemetry wording.

### 7. Distribution Decision

Priority: medium.

Purpose: decide how open-market users install and update TailTrail.

Recommended first release:

- Source-only GitHub repository.
- Users clone the repo and run `python3 scripts/tailtrail.py`.
- No PyPI package yet.
- No global shell command yet.
- No background service.

Future package options:

- Python package with console script.
- `pipx` install path.
- GitHub release archive.
- Codex plugin package.
- Homebrew or package-manager distribution only if demand appears.

Acceptance check:

- The first release has one clear install path.
- Update instructions are clear.
- The project does not own unnecessary packaging complexity too early.

### 8. Semantic Versioning And Release Tags

Priority: medium.

Purpose: make upgrades predictable.

Status: implemented for policy documentation. `VERSIONING.md` defines version source of truth and tag rules. Tag creation remains a release action, not a repository file change.

Implementation plan:

- Document version source of truth:
  - `.codex-plugin/plugin.json`
  - `CHANGELOG.md`
  - Git tag
- Add release tag format: `vMAJOR.MINOR.PATCH`.
- Add release checklist step to verify version alignment.
- Add release-check validation for plugin version format.

Acceptance check:

- Maintainers can cut a release without guessing version rules.
- Users can compare installed version with public release notes.

### 9. Public Support And Triage Model

Priority: medium.

Purpose: define what maintainers will and will not support after open release.

Status: implemented. `SUPPORT.md` defines supported public surfaces, unsupported-by-default areas, safe help requests, and maintainer expectations.

Implementation plan:

- Add `SUPPORT.md`.
- Define supported surfaces:
  - source checkout
  - local Python scripts
  - documented assistant adapters
  - current `main` or latest tagged release
- Define unsupported surfaces:
  - private company CI systems
  - proprietary scanners
  - user-specific assistant behavior bugs that ignore instructions
  - unreviewed forks
- Define expected response language without promising SLA unless desired.

Acceptance check:

- Public users know where to ask questions.
- Maintainers are not implicitly committing to enterprise support.

### 10. Security Reporting Finalization

Priority: highest before launch.

Purpose: replace temporary security reporting language with a real public path.

Status: implemented. `SECURITY.md` now directs sensitive reports to GitHub private vulnerability reporting through the repository Security tab, with a non-public maintainer channel fallback for forks or mirrors.

Implementation plan:

- Enable GitHub private vulnerability reporting, or add a maintained security email.
- Update `SECURITY.md`.
- Update `RELEASE-CHECKLIST.md`.
- Add release-check marker so placeholder security text cannot ship.

Acceptance check:

- Sensitive reports have a private path.
- Public issue templates redirect users away from posting secrets or exploit details.

### 11. License And Provenance Finalization

Priority: highest before launch.

Purpose: ensure public users and contributors understand rights, ownership, and attribution.

Status: implemented. `PUBLIC-RELEASE-METADATA.md` records Apache-2.0 as the public license, identifies TailTrail project maintainers as the public release owner, and points to `LICENSE`, `.codex-plugin/plugin.json`, and `NOTICE.md`. `scripts/release-check.py` now validates the license/provenance alignment, and internal exports exclude the public metadata.

Implementation plan:

- Confirm final license with owner/legal reviewer. Implemented as a project-level public release metadata decision; external legal approval remains outside TailTrail automation.
- Confirm copyright owner. Implemented as TailTrail project maintainers in public metadata and `NOTICE.md`.
- Confirm whether Apache-2.0 remains the intended license. Implemented.
- Update `LICENSE` if needed. Implemented; Apache-2.0 is present.
- Update `.codex-plugin/plugin.json`. Implemented; license is `Apache-2.0`.
- Update `NOTICE.md`. Implemented.
- Confirm no vendored third-party code, docs, generated brand assets, or copied external material exists. Implemented in `NOTICE.md` and checked through release hygiene review.

Acceptance check:

- Public license is final and consistent across files. Implemented.
- Provenance statement is accurate. Implemented.
- Release checklist includes license confirmation. Implemented.

### 12. Public Claim Guardrails

Priority: high.

Purpose: prevent overclaiming in public marketing, README, demo, and reports.

Implementation plan:

- Add a short `PUBLIC-CLAIMS.md` or section in `RELEASE-CHECKLIST.md`.
- Allowed claims:
  - local-first
  - approval-first
  - assistant-agnostic guidance
  - token-aware context reduction estimates
  - measured token savings only with real telemetry
  - scanner-aware, not scanner replacement
- Disallowed claims:
  - guaranteed token savings
  - guaranteed code quality improvement
  - replaces security review
  - replaces CI/Sonar/SAST/dependency scanners
  - autonomous self-healing
  - automatic enterprise compliance

Acceptance check:

- Marketing/demo language stays accurate.
- Release check or doc audit can catch obvious unsupported claims.

### 13. Public Architecture Overview

Priority: medium.

Purpose: help users understand TailTrail's moving parts without reading every file.

Status: implemented. `ARCHITECTURE.md` explains the command surface, Navigator, AIDLC, guardrails, graph/evidence helpers, learning/reporting, release modes, and local-only boundaries with a Mermaid diagram.

Implementation plan:

- Add `ARCHITECTURE.md`.
- Include:
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
- Include a Mermaid diagram.
- Call out local-only boundaries.

Acceptance check:

- New contributors can understand the architecture in one file. Implemented.
- The architecture doc does not become a second roadmap. Implemented.

### 14. Public Roadmap Compression

Priority: low.

Purpose: the current roadmap is very detailed and useful internally, but public readers may need a shorter roadmap.

Status: implemented. `PUBLIC-ROADMAP.md` provides a compact now/next/later/not-planned view while keeping `ROADMAP.md` as the detailed source of truth.

Implementation plan:

- Keep `ROADMAP.md` as detailed source of truth.
- Add `PUBLIC-ROADMAP.md` or a README section with:
  - now
  - next
  - later
  - not planned yet
- Avoid exposing every internal experiment as a public commitment.

Acceptance check:

- Public users can understand direction without being overwhelmed. Implemented.
- Detailed roadmap remains available for serious contributors. Implemented.

### 15. Open-Market Enterprise Enhancements After Launch

Priority: later.

Purpose: identify features that could make TailTrail stronger after public feedback.

Candidates:

- Multi-repo report aggregation from explicitly supplied local reports.
- Trend comparison across months.
- CSV export for governance decks.
- Pull request summary mode.
- Optional enterprise dashboard after privacy review.
- Optional SCIP/language-server/Roslyn graph enrichment.
- Optional MCP graph provider adapter.
- Optional Sonar/vulnerability graph overlays.
- Optional monorepo graph partitioning.
- Real token telemetry provider adapters.
- Pricing and cost analysis from measured usage.
- Package distribution through `pipx` or release archive.

Do not implement these before the public basics unless there is clear demand.

### Recommended Open-Market Implementation Order

1. Public CI.
2. `CHANGELOG.md` and version policy.
3. Issue and pull request templates.
4. Fresh-clone smoke test.
5. Public demo walkthrough.
6. Public documentation sanitizer.
7. Security reporting finalization.
8. License/provenance finalization.
9. Public architecture overview.
10. Distribution decision.
11. Public roadmap compression.
12. Post-launch enterprise enhancements.

## Shortcoming Remediation Plan

Purpose: turn the current honest shortcomings into a prioritized product-hardening plan for enterprise and open-market release.

Status: planned. Some foundations already exist, such as `start`, Navigator, release checks, Learning Agent V2, benchmark harness, token savings guardrails, and enterprise reports. This section focuses on closing the remaining product gaps.

### Priority 0: Must Fix Before Public Pitch

These items protect credibility. They should be completed before broad open-market promotion.

#### 1. One Obvious Command Polish

Shortcoming:

- TailTrail has many commands and features.
- A new user can still wonder whether to use `start`, `guide`, `graph`, `quality`, `learn`, `aidlc`, or `report`.

Current foundation:

- `python3 scripts/tailtrail.py start "goal"` exists.
- `start` wraps Navigator plus token posture, learning quality, and update posture.

Fix plan:

- Make `start` the default first command everywhere:
  - README quick start
  - USER-GUIDE first workflow
  - TAILTRAIL-COMMANDS discovery section
  - public demo
  - issue templates
- Add a `first-run` or `quickstart` command only if user testing shows `start` is still unclear.
- `scripts/tailtrail.py next` is implemented; future work should tune its recommendations only if usage shows gaps.
- Keep lower-level commands documented as advanced commands.
- Add a command decision table:
  - "I have a task" -> `start`
  - "I only want a plan" -> `guide`
  - "I know changed files" -> `graph`
  - "I have logs" -> `ci summarize` / `sonar summarize`
  - "I want checks" -> `quality scan`
  - "I want public release validation" -> `release-check`

Acceptance check:

- A new user can start with one command in under one minute.
- README does not present too many first-step alternatives.
- `start` output clearly tells the user what to do next.

#### 2. Public Claim Guardrails

Status: implemented. `PUBLIC-CLAIMS.md` now defines allowed, cautious, and disallowed claims, and `scripts/release-check.py` scans public-facing docs for unsupported public claims while allowing explicit negative/cautious wording.

Shortcoming:

- Some features are MVP-grade scripts/docs, not deep engines.
- Public pitch could oversell graphing, learning, token savings, security, or review quality.

Current foundation:

- `RELEASE-CHECKLIST.md` exists.
- `scripts/release-check.py` exists.
- Token savings already distinguish estimated versus measured.

Fix plan:

- Add `PUBLIC-CLAIMS.md`. Implemented.
- Define allowed, cautious, and disallowed claims. Implemented.
- Add release-check scanning for risky phrases. Implemented:
  - "guaranteed token savings"
  - "replaces security review"
  - "replaces CI"
  - "fully automatic compliance"
  - "self-healing"
  - "exact savings" without telemetry wording
- Update README and demo language to use accurate phrases:
  - "helps"
  - "recommends"
  - "estimates"
  - "approval-first"
  - "local evidence"
  - "not a scanner replacement"

Acceptance check:

- Public-facing docs avoid unsupported claims.
- Release check fails on obvious overclaiming.
- Demo language is credible to enterprise reviewers.

#### 3. Public CI And Fresh Clone Proof

Shortcoming:

- Open users need confidence that the repo works from a clean checkout.

Current foundation:

- Local checks exist.
- Release check exists.

Fix plan:

- Add GitHub Actions CI.
- Add `scripts/smoke-test.py`.
- CI should run:
  - package check
  - release check
  - adapter sync
  - Python compile
  - smoke test
- Keep CI dependency-free.

Acceptance check:

- Every PR shows basic health.
- A fresh clone can run core commands safely.

### Priority 1: Needed For Enterprise Confidence

These items are not required to make TailTrail usable, but they matter for serious enterprise evaluation.

#### 4. Real Usage Telemetry, Privacy-First

Shortcoming:

- Benchmark harness helps, but true product confidence needs real adoption data: task outcomes, acceptance, defect reduction, time saved, and validation evidence.

Current foundation:

- Benchmark harness exists.
- Learning Agent V2 captures explicit events.
- Quality Loop captures approved workflow quality events.
- Enterprise Reporting aggregates local artifacts.

Fix plan:

- Add explicit, opt-in `task outcome` capture:
  - task type
  - workflow selected
  - user acceptance
  - validation outcome
  - review outcome
  - defect escaped yes/no
  - estimated time saved band
  - whether TailTrail was too heavy/too light/correct
- Do not capture raw prompts by default.
- Do not upload anything.
- Add `scripts/outcome-capture.py` only if Quality Loop feels too generic.
- Update Enterprise Reporting to include:
  - accepted/rejected/revised counts
  - validation pass/fail/skipped
  - repeated issue types
  - workflow fit
  - time-saved bands
  - escaped defect reports, if explicitly recorded
- Add clear privacy and retention guidance.

Acceptance check:

- Teams can measure adoption without surveillance.
- Reports show outcome evidence, not just feature usage.
- Users must explicitly approve capture.

#### 5. Exact Token Usage Path

Shortcoming:

- Token savings are estimated, not exact.
- Estimated savings are useful directionally but not strong ROI proof.

Current foundation:

- `scripts/token-savings.py estimate` exists.
- `scripts/token-savings.py report --telemetry` supports measured telemetry JSONL.
- `start` shows approximate token posture.

Fix plan:

- Define a normalized `.tailtrail/token-usage.jsonl` schema:
  - task id
  - provider
  - model
  - baseline input/output tokens
  - TailTrail input/output tokens
  - source of measurement
  - date
  - confidence/evidence level
- Add sample telemetry file with fake values.
- Add docs for how users can export provider usage metadata manually.
- Add provider adapters later only if privacy review approves:
  - OpenAI API usage metadata
  - Anthropic usage metadata
  - local assistant logs if user supplies them
- Add pricing calculation later as optional, because price changes over time.

Acceptance check:

- TailTrail never claims exact savings without measured telemetry.
- Teams that have telemetry can produce exact measured reports.
- Estimated and measured reports are visually distinct.

#### 6. Guarded Learning UX

Shortcoming:

- Learning can become noisy if governance is weak.
- Scoring and refresh exist, but users need disciplined UX.

Current foundation:

- Learning Agent V2 confidence scoring exists.
- Learning Refresh exists.
- Graph-Aware Learning exists.
- Navigator asks `use learnings`, `ignore learnings`, or `edit plan`.

Fix plan:

- Add a learning governance guide:
  - what to capture
  - what not to capture
  - when to promote
  - when to suppress
  - when to refresh
  - when to delete/archive
- Add `tailtrail.py learn review` as a friendly wrapper around refresh and prune commands.
- Add learning noise thresholds:
  - too many weak notes
  - repeated rejected patterns
  - stale graph links
  - no validation evidence
- Add monthly learning hygiene report into Enterprise Reporting.
- Add warning in `start` when learning index exists but refresh actions are stale or unresolved.

Acceptance check:

- Learning stays advisory.
- Low-confidence user-accepted changes do not become trusted patterns automatically.
- Teams can clean up stale/noisy learnings without reading raw history.

#### 6.5. Clone Setup Hygiene And Shared Context Detection

Shortcoming:

- A user may clone a repo that already contains TailTrail files from another user or a previous team setup.
- Some TailTrail files are legitimate shared project context and should stay in Git.
- Other TailTrail files are local runtime state and should not be inherited by a new developer.
- Overrides can be project policy, team convention, or accidental personal customization.
- Current setup commands do not yet give a clear "what did I inherit?" report.

Purpose:

- Help a new user safely set up TailTrail in a repo that already contains TailTrail-related files.
- Prevent accidental overwrite of project policy, AIDLC docs, curated learnings, or assistant instructions.
- Warn when local state appears to be committed.
- Make the distinction between shared project knowledge and local user state obvious.

Proposed command:

```bash
python3 scripts/tailtrail.py setup-scan --root .
python3 scripts/setup-scan.py --root .
python3 scripts/setup-scan.py --root . --format json
```

Setup-scan should not write files by default. It should inspect, classify, and recommend next actions.

Classification model:

- **Shared project context**: intended to be read by every developer or assistant in the repo.
- **Project overrides**: shared customizations that modify TailTrail behavior for this repo.
- **Installed TailTrail pack**: copied TailTrail tooling, usually in `tailtrail/` or another configured pack folder.
- **Local runtime state**: per-user generated state, event logs, command outputs, cache, or telemetry.
- **Generated-but-shareable metadata**: generated files that may be useful if the team intentionally commits them.
- **Unknown TailTrail-like files**: files matching TailTrail names but not recognized by the current version.

Files that usually make sense to commit:

```text
AGENTS.md
tailtrail-policy.md
.tailtrail/policy-overrides.json
aidlc-docs/
aidlc-docs/aidlc-state.md
aidlc-docs/requirements.md
aidlc-docs/workflow-plan.md
aidlc-docs/implementation-plan.md
aidlc-docs/validation-handoff.md
aidlc-docs/audit-notes.md
.tailtrail/learnings.md
.tailtrail/learning-index.md
.tailtrail/graph-learning-index.json
```

Files that can be committed only by explicit team choice:

```text
tailtrail-meta/code-graph-cache.json
.github/copilot-instructions.md
.cursor/rules/tailtrail.mdc
.openai/chatgpt-instructions.md
CLAUDE.md
GEMINI.md
```

Rationale:

- `tailtrail-meta/code-graph-cache.json` can save discovery in large repos, but it may become stale and should contain metadata only.
- Assistant instruction files can be shared when the team wants consistent assistant behavior, but they should be reviewed before commit.

Files that usually should not be committed:

```text
.tailtrail/token-router-state.json
.tailtrail/token-autopilot-state.json
.tailtrail/quality-events.jsonl
.tailtrail/quality-summary.md
.tailtrail/quality-decisions.md
.tailtrail/learning-events.jsonl
.tailtrail/learning-scores.jsonl
.tailtrail/learning-refresh-actions.json
.tailtrail/enterprise-report.md
.tailtrail/token-usage.jsonl
.tailtrail/quality-runs/
.tailtrail/vulnerability-runs/
.tailtrail/task-starts/
tailtrail/.tailtrail-install.json
```

Default setup behavior:

- Preserve existing shared project context.
- Preserve existing overrides.
- Validate overrides when validators exist.
- Never overwrite `tailtrail-policy.md` silently.
- Never overwrite `AGENTS.md` silently.
- Never overwrite `aidlc-docs/` silently.
- Treat committed `.tailtrail/*state*.json`, `*events*.jsonl`, `*scores*.jsonl`, and run-output folders as suspicious.
- Mark `tailtrail-meta/code-graph-cache.json` as shareable only if it contains metadata only and the team has opted in.
- Recommend update dry-run for installed packs.
- Recommend `.gitignore` additions for local runtime files.

Conflict rules:

| Detected file | Default action | Reason |
|---|---|---|
| `tailtrail-policy.md` | preserve and validate | project policy belongs to the repo |
| `.tailtrail/policy-overrides.json` | preserve and validate | structured project policy override |
| `.tailtrail/intent-overrides.json` | preserve and validate shape | project-specific prompt expansion |
| `tailtrail/intent-overrides.json` | preserve and validate shape | installed-pack override |
| `AGENTS.md` | preserve; suggest manual merge | may contain non-TailTrail repo instructions |
| `aidlc-docs/` | preserve | lifecycle state belongs to current repo work |
| `.tailtrail/learnings.md` | preserve | curated team learning |
| `.tailtrail/learning-index.md` | preserve | token-safe shared learning index |
| `tailtrail-meta/code-graph-cache.json` | preserve but check freshness | useful metadata if team-approved |
| `.tailtrail/*state*.json` | warn and recommend ignore | per-user runtime state |
| `.tailtrail/*events*.jsonl` | warn and recommend ignore | local event history |
| `.tailtrail/token-usage.jsonl` | warn and recommend ignore | local usage telemetry |
| `tailtrail/` installed pack | update only through dry-run | avoid overwriting local edits |
| `.github/copilot-instructions.md` | preserve; suggest review | may be team-shared assistant behavior |

Recommended setup report:

```text
TailTrail setup scan

Shared project context:
- AGENTS.md
- tailtrail-policy.md
- aidlc-docs/
- .tailtrail/learnings.md

Overrides:
- .tailtrail/policy-overrides.json
- .tailtrail/intent-overrides.json

Local/runtime state:
- .tailtrail/token-router-state.json
- .tailtrail/quality-events.jsonl

Installed pack:
- tailtrail/ found
- manifest present
- recommended action: run update dry-run

Recommended next commands:
- python3 tailtrail/scripts/tailtrail.py policy check --root .
- python3 tailtrail/scripts/tailtrail.py update --root . --dry-run
- review .gitignore for local TailTrail state patterns
```

Suggested implementation files:

- `scripts/setup-scan.py`: deterministic classifier and report generator.
- `templates/tailtrail-gitignore.md`: recommended ignore patterns for product repos.
- `scripts/tailtrail.py`: add `setup-scan` command.
- `USER-GUIDE.md`: add "Using TailTrail In A Cloned Repo" section.
- `TAILTRAIL-COMMANDS.md`: document setup-scan.
- `scripts/check-tailtrail.py`: validate new script/template/docs.

JSON output shape:

```json
{
  "root": "/path/to/repo",
  "shared_project_context": [],
  "project_overrides": [],
  "installed_pack": [],
  "local_runtime_state": [],
  "generated_shareable_metadata": [],
  "unknown_tailtrail_files": [],
  "warnings": [],
  "recommended_commands": []
}
```

Gitignore recommendation:

```gitignore
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

Open questions before implementation:

- Should `tailtrail-meta/code-graph-cache.json` be ignored by default or allowed by default?
- Should setup-scan fail on committed local runtime state or only warn?
- Should installed `tailtrail/` packs be discouraged for public repos but allowed for internal repos?
- Should assistant instruction files be treated as shared by default or prompt for review?

Recommended defaults:

- Warn, do not fail, on local runtime state.
- Preserve all overrides.
- Do not overwrite shared files.
- Treat `tailtrail-meta/code-graph-cache.json` as "team-review required".
- Treat assistant instruction files as "shared but review recommended".
- Prefer each developer installing/updating their own TailTrail tooling instead of inheriting another user's full pack.

Acceptance check:

- A new user can clone a repo and run one command to understand existing TailTrail files.
- The report distinguishes project-shared files from local user state.
- The report recommends safe next commands without writing files.
- Existing overrides are preserved.
- Setup does not silently overwrite project policy.
- Local runtime state is flagged for gitignore review.
- Installed packs are updated only through dry-run or explicit user approval.

### Priority 2: Platform Depth After Public Basics

These items improve quality, but should not block first public release.

#### 7. Deepen MVP-Grade Engines Carefully

Shortcoming:

- Some features are deliberately MVP-grade scripts/docs.
- This is okay, but the product should show a path to deeper engines.

Current foundation:

- Code Review Graph Lite exists.
- Code Graph Mapper exists.
- Quality Scanner and Vulnerability Intelligence exist.
- CI/Sonar summarizers exist.

Fix plan:

- Improve one engine at a time based on usage evidence.
- Recommended order:
  1. Code Graph Mapper enrichment.
  2. Sonar/vulnerability graph overlays.
  3. Fresh-clone smoke test and CI coverage.
  4. Report trend analysis.
  5. Optional language-server/SCIP/Roslyn adapter.
- Avoid vector DB, background services, and MCP adapters until simple local signals prove insufficient.

Acceptance check:

- Deepening is driven by real misses, not feature excitement.
- Existing local deterministic behavior remains stable.
- Users can understand how results were produced.

#### 8. Multi-Agent Integration Beyond Instruction Files

Shortcoming:

- Multi-agent/platform integration is mostly guidance-driven.
- Codex works best; other tools depend on whether they honor instruction files.

Current foundation:

- Adapter files exist for Claude, Cursor, Copilot, ChatGPT, and Gemini.
- Sync validation exists.
- Installers can place Copilot packs.

Fix plan:

- Add per-agent smoke scenarios:
  - prompt to use `start`
  - prompt to use AIDLC
  - prompt to use review
  - prompt to preserve guardrails
- Add adapter capability matrix:
  - reads repo instructions
  - supports custom commands
  - supports tool execution
  - supports persistent memory
  - supports file edits
  - known limitations
- Add manual test checklist for each assistant.
- Keep automation limited because external assistant behavior changes often.

Acceptance check:

- Public users know what each adapter can and cannot do.
- TailTrail does not imply all assistants behave equally.
- Adapter drift is tracked.

#### 9. Enterprise Reporting Maturity

Shortcoming:

- Enterprise reports are local and useful, but not yet enough for broad ROI claims.

Current foundation:

- Local report generation exists.
- Quality, learning, refresh, optional AIDLC, and token evidence are included.

Fix plan:

- Add trend comparison across months.
- Add CSV export.
- Add multi-report aggregation from explicitly supplied local report files.
- Add PR summary mode.
- Keep dashboard deferred until privacy review.

Acceptance check:

- Teams can show month-over-month improvement.
- Reports remain local and privacy-preserving.
- No central telemetry is introduced by default.

### Priority 3: Post-Launch Enhancements

These should wait until public users show demand.

#### 10. Packaging And Distribution

Shortcoming:

- Source-only install is simple but less polished than package-manager installation.

Fix plan:

- First release: source-only.
- Later:
  - Python package with console script
  - `pipx` install
  - GitHub release archive
  - optional Codex plugin packaging
- Do not add Homebrew or OS installers until demand is clear.

Acceptance check:

- Installation remains understandable.
- Updating does not break existing managed packs.

#### 11. Advanced Token And Cost Analytics

Shortcoming:

- Token savings are not yet tied to dollar impact.

Fix plan:

- Add optional pricing config.
- Keep model prices user-provided or fetched only with explicit update.
- Separate token reduction from cost reduction.
- Show confidence levels.

Acceptance check:

- No stale pricing claims.
- Users can produce ROI estimates when they supply real usage and pricing.

### Recommended Remediation Order

1. Public CI and smoke test.
2. Public claim guardrails and doc sanitizer.
3. One-command UX tightening around `start`.
4. Changelog and version policy.
5. Issue/PR templates.
6. Learning governance UX.
7. Real usage telemetry schema and outcome capture.
8. Exact token telemetry docs and examples.
9. Multi-agent capability matrix.
10. Enterprise reporting trends and CSV.
11. Deeper graph/scanner overlays.
12. Packaging only after source-only release feedback.

### Success Metrics

- New user reaches useful Navigator plan in under one minute.
- Public CI passes on every PR.
- Release check catches public hygiene problems.
- No public docs claim exact token savings without telemetry.
- At least three real tasks have outcome evidence before claiming enterprise productivity impact.
- Learning promotions are mostly high-confidence and validation-backed.
- Adapter docs clearly explain differences between Codex, Claude, Cursor, Copilot, ChatGPT, and Gemini.

## Keep It Simple Rules

- Prefer Markdown over code.
- Prefer one skill update over a new command.
- Prefer optional files over required runtime behavior.
- Add one phase at a time.
- Add token controls before adding large new guidance packs.
- Every new file must have a clear purpose in `DESIGN.md`.
- Every new implementation file must be covered by `scripts/check-tailtrail.py`.

## V3 Roadmap: Honest-Review Remediation Track

Purpose: turn the findings in `HONEST-REVIEW.md` into a single staged, implementable V3 backlog. The review scored TailTrail 6.5/10 with three headline gaps: advisory-only governance (no enforcement teeth), oversized default surface, and unproven real-world efficacy. This track fixes those in dependency-order while preserving TailTrail's core promise: local-first, deterministic, approval-first, no weakened safeguards.

Detailed execution plan: see `HONEST-REVIEW-IMPLEMENTATION-PLAN.md`.

Guiding principles for V3:

- Add enforcement without breaking the advisory nature of the core docs. Enforcement is opt-in, local, and deterministic.
- Shrink perceived surface area without deleting capability. Prefer a small Core plus opt-in Extended pack.
- Prove value with measured evidence before making stronger claims.
- Keep every new script Python standard-library only, read-only unless explicitly approved, and covered by `scripts/check-tailtrail.py`.

Mapping of review findings to phases:

| Review finding (HONEST-REVIEW.md) | V3 phase |
|---|---|
| Advisory, not enforced (Enforcement 4/10) | V3.0, V3.1 |
| Oversized default surface (Simplicity 4/10) | V3.2 |
| Docs are phase-history framed (Docs 6/10) | V3.3 |
| Unproven efficacy (Proof of value 5/10) | V3.4 |
| navigator.py monolith, no tests (Maintainability 5/10) | V3.5 / V3.6 |
| Governance-text drift/overlap | V3.7 |
| Value is invisible / no ROI surface | V3.8 |
| Strategic focus / pick a lane | V3.9 |
| Review UX requires too much command knowledge | V3.10 |

Recommended implementation order: V3.0 -> V3.1 -> V3.2 -> V3.3 -> V3.4 -> V3.5/V3.6 -> V3.7 -> V3.8 -> V3.9. The Navigator refactor and deterministic tests may run in parallel with any phase because they are internal hardening.

### V3.0: Guardrail Enforcement Engine (Local Pre-Commit)

Goal: give the highest-value guardrails real teeth through a local, deterministic, opt-in check that can block a commit.

Status: implemented for Enforcement Lite. `scripts/guardrail-check.py` and `python3 scripts/tailtrail.py guard check` now scan staged diffs or provided patches in advisory mode by default, with `--enforce` blocking high-severity findings. Sample hook installation remains deferred until teams review false-positive behavior.

Priority: highest. This directly addresses the review's biggest gap (Enforcement 4/10).

Scope:

- Add `scripts/guardrail-check.py` that scans a staged diff (or a provided diff/patch file) and reports guardrail violations with exact file/line evidence. Implemented.
- Detect the three highest-value, low-false-positive violation classes first:
  - New or changed dependency manifest entry without a matching `DEPENDENCY-GATE` note or approval marker.
  - Removed safeguard signal (auth, authz, validation, escaping, logging, rate limit, migration/test deletion) in the diff.
  - Unverified validation claim in the commit message or PR body (for example "tests pass", "deployed", "verified") without an evidence marker.
- Return a non-zero exit code only in `--enforce` mode; default mode is advisory report. Implemented.
- Add `python3 scripts/tailtrail.py guard check` wrapper. Implemented.
- Provide a sample pre-commit hook and a documented opt-in install path. Do not auto-install git hooks.

Implementation design:

- Read staged files via `git diff --cached` when no input file is given; never write to the working tree.
- Keep detection rule-based and explainable; every finding cites the exact matched line and the guardrail section it maps to.
- Allow project override of severity and allowlist through `.tailtrail/policy-overrides.json` (reuse existing policy shape from `scripts/policy-check.py`).
- Ship conservative defaults tuned for low false positives; prefer a missed finding over blocking a correct commit.

Implemented commands (target):

```bash
python3 scripts/tailtrail.py guard check
python3 scripts/tailtrail.py guard check --diff changes.patch --format json
python3 scripts/tailtrail.py guard check --enforce
```

Acceptance check:

- A commit that adds a dependency with no gate note is flagged (and blocked under `--enforce`).
- A commit message claiming "tests pass" with no evidence marker is flagged.
- Advisory mode never blocks; enforce mode returns a clear non-zero exit with actionable findings.
- False-positive rate on TailTrail's own history is low enough to enable in this repo's CI.

### V3.1: CI Guardrail Gate And PR Evidence Check

Goal: extend V3.0 enforcement to shared workflows so governance holds across a team, not just one machine.

Priority: highest, after V3.0.

Scope:

- Add a reusable GitHub Actions workflow `.github/workflows/tailtrail-guard.yml` that runs `guardrail-check.py` against the PR diff.
- Add a PR body evidence check: verify a filled `templates/evidence-note.md`-style block exists for non-trivial PRs (files read, checks run, skipped areas, residual risk).
- Post findings as a compact PR summary; fail the check only for the high-severity classes from V3.0.
- Keep the gate opt-in per repo and configurable through policy overrides.

Implementation design:

- Reuse V3.0 detection; the CI layer only changes the input source (PR diff) and the reporting surface.
- Keep the workflow dependency-free (Python standard library, checkout action only).
- Respect `.tailtrail/policy-overrides.json` for severity, allowlist, and required-evidence thresholds.

Acceptance check:

- A PR that removes a safeguard or makes an unverified validation claim fails the guard gate.
- A trivial PR is not forced through heavy evidence requirements.
- The gate can be enabled or disabled per repository without editing TailTrail source.

### V3.2: Core And Extended Pack Split

Goal: cut the intimidating default surface (Simplicity 4/10) without removing capability.

Priority: high.

Scope:

- Define TailTrail Core: `GUARDRAILS.md`, `AGENTS.md`, one adapter, `scripts/tailtrail.py`, `scripts/navigator.py`, `scripts/guardrail-check.py`, and the policy/check helpers.
- Move the remaining engines (graph mapper, overlays, learning, quality/vuln scanners, reporting, benchmarks) into an opt-in Extended pack, surfaced only when the user asks or the task needs them.
- Update `scripts/install-local.py` and `scripts/install-copilot.py` to install Core by default and Extended on request (`--extended`).
- Add a `manifest` that lists Core vs Extended so `check-tailtrail.py` and the updater treat them consistently.

Implementation design:

- No files are deleted; classification is metadata plus installer behavior.
- Navigator continues to reference Extended features but marks them as opt-in when not installed.
- Preserve backward compatibility: existing full installs keep working.

Acceptance check:

- A default install writes a small, understandable Core footprint.
- Extended features remain one flag away and are clearly documented.
- Existing installed packs continue to update cleanly.

### V3.3: Task-First Documentation And Cheat Sheet

Goal: replace phase-history framing with outcome-first guidance (Docs 6/10).

Status: implemented. `QUICKSTART.md` and `CHEATSHEET.md` now provide task-first command paths, and `README.md` leads with `start` and `guard check` before the package inventory.

Priority: high.

Scope:

- Add `QUICKSTART.md`: a task-first entry (for example "stop my AI from claiming fake test passes", "keep diffs small", "block casual dependencies") each mapped to the one command or file to use. Implemented.
- Add a one-page `CHEATSHEET.md` mapping problem -> single file/command. Implemented.
- Restructure `README.md` to lead with outcomes and the `start`/`guard check` commands, keeping internal phase history in `ROADMAP.md` and `DESIGN.md` only. Implemented.
- Keep the detailed roadmap intact; the public surface points to it rather than leading with it. Implemented.

Acceptance check:

- A new reader can find the right command for a concrete problem in under a minute.
- README leads with outcomes, not phase numbers.
- Phase history is still available but not the first thing users see.

### V3.4: Measured Efficacy Benchmark

Goal: replace synthetic self-scored benchmarks with reproducible, measured evidence (Proof of value 5/10).

Status: implemented for artifact-based local evidence. `scripts/efficacy-benchmark.py` and `python3 scripts/tailtrail.py benchmark efficacy` compare committed baseline and TailTrail-guided artifacts under `benchmarks/efficacy/`, including measured token telemetry only when supplied by scenario or user JSONL.

Priority: high.

Scope:

- Add a reproducible benchmark harness that runs a fixed task set with and without TailTrail guidance, capturing token counts from provided model/API usage metadata and objective quality signals such as dependency added yes/no, safeguard preserved yes/no, unverified claim yes/no, and diff size. Implemented with committed artifacts rather than live model runs.
- Publish results under `benchmarks/results/` with the exact inputs, method, and disclaimers. Implemented through `--write-result`.
- Keep exact token claims gated behind real usage metadata (reuse the V2.4 telemetry schema). Implemented.
- Add a `benchmark efficacy` subcommand that produces the comparison report deterministically from captured artifacts. Implemented.

Implementation design:

- Do not call live models in the harness; consume captured artifacts and provided usage metadata.
- Separate directional estimates from measured results in the output, matching existing token-savings guardrails.

Acceptance check:

- A skeptical evaluator can reproduce the benchmark from committed inputs.
- Results clearly separate measured from estimated numbers.
- No efficacy or token claim is made without the supporting artifact.

### V3.4.1: Cross-Repo Reference Mode

Goal: make multi-repo local development safe and practical when the user edits one repo but asks TailTrail to use a sibling or external repo as reference.

Status: implemented. `scripts/cross-repo-reference.py`, `python3 scripts/tailtrail.py reference`, `context/cross-repo-reference.md`, and Navigator integration now provide target/reference repo boundary planning.

Problem it solves:

- Enterprise workspaces often contain many related repos under one parent folder.
- Users commonly say "use this other repo as reference" while working in a single repo.
- Assistants may not read the other repo if it is outside the active workspace or sandbox.
- If the other repo is readable, the agent still needs clear boundaries so it does not edit the reference repo or copy code.
- Broad sibling repo reads can waste tokens when a compact summary or graph is enough.

Implementation design:

- Add `scripts/cross-repo-reference.py` as a deterministic, local-only planner.
- Inputs:
  - `--target`: repo that may be edited.
  - `--reference`: read-only reference repo; repeatable for multiple references.
  - `--goal`: task goal.
  - `--format markdown|json`.
  - `--write-summary`: optional durable summary under the target repo.
- Output:
  - target repo existence and git-root signal
  - reference repo existence, git-root signal, and relationship to target
  - lightweight language and manifest signals
  - read/write boundaries
  - context to load and avoid
  - optional reference graph command that stores metadata in the target repo
  - approval reminders before implementation
- Integrate with `scripts/tailtrail.py reference`.
- Integrate with Navigator so prompts mentioning target/reference repos, sibling repos, other repos, or "as reference" select Cross-Repo Reference Mode.
- Keep reference summaries and graph caches near the target repo, such as:

```bash
python3 scripts/tailtrail.py reference \
  --target /path/to/service-a \
  --reference /path/to/service-b \
  --goal "match validation style"

python3 scripts/tailtrail.py graph map \
  --root /path/to/service-b \
  --cache /path/to/service-a/.tailtrail/reference-graphs/service-b.json
```

Usage example:

```text
Use TailTrail cross-repo reference.
Target: /Users/me/workspace/service-a
Reference: /Users/me/workspace/service-b
Goal: implement the same validation style.
Only edit service-a.
```

Expected Navigator behavior:

- Select Cross-Repo Reference Mode.
- Confirm that the target repo is editable and the reference repo is read-only.
- Recommend `tailtrail reference` with parsed paths when available.
- Warn if the reference path is missing, inaccessible, or overlaps the target.
- Load target exact source plus compact reference summary/graph only.
- Avoid broad sibling repo reads, accidental reference edits, and source-copying from the reference repo.

Boundaries:

- No code edits.
- No scanner/test/build execution.
- No model calls.
- No automatic graph creation.
- No claim that an inaccessible reference path can be read.
- No source snippets are stored in reference graph caches.

Future candidates:

- Multi-reference ranking when several sibling repos are available.
- Reference freshness checks against stored `.tailtrail/reference-context/` summaries.
- Navigator prompt extraction for more path shapes, such as quoted shell paths and IDE workspace aliases.
- Optional policy rule for allowed reference roots.
- Cross-repo service dependency hints after Code Graph Mapper supports cross-repo service graphs.

Acceptance check:

- User can identify target and reference repos without writing a long prompt.
- Navigator recommends the feature when a prompt mentions a sibling/reference repo.
- The command makes read/write boundaries explicit.
- Reference metadata can be stored under the target repo without modifying the reference repo.

### V3.5 / V3.6: Navigator Refactor And Deterministic Tests

Goal: fix internal maintainability (5/10) and prove the deterministic tools are correct.

Status: completed end to end for the V3.6 scope. `scripts/navigator_core.py` owns deterministic Navigator classification/routing helpers, `scripts/navigator_render.py` owns Markdown rendering, and `scripts/navigator.py` keeps the stable CLI plus decision orchestration. `tests/` covers Navigator core decisions, golden Markdown rendering, task-start wrapping, guardrail-check, intent expansion, and policy-check behavior. Manual TailTrail CI runs `python3 -m unittest discover -s tests`. The post-refactor cleanup is implemented: read-only repo overview prompts use compact `Repo Overview / Discovery` output, generated learning capture commands point to the TailTrail install path instead of assuming hooks exist inside the target repo, and repo overview plans show Code Graph Mapper as an optional deeper discovery command instead of silently creating graph files.

Priority: medium, can run in parallel.

Scope:

- Split `scripts/navigator.py` (~1100 lines) into focused modules: goal classification, risk detection, feature selection, and report rendering, behind a stable CLI. Implemented for deterministic classification/routing helpers in `scripts/navigator_core.py` and Markdown rendering in `scripts/navigator_render.py`.
- Remove stale duplicate Navigator keyword tables and classifier helpers from `scripts/navigator.py` so classification has one source of truth. Implemented.
- Add explicit read-only repo overview classification for prompts such as "tell me important features of this repo" so "features" does not accidentally trigger implementation planning. Implemented.
- Add compact Navigator Markdown for repo overview/discovery prompts. Implemented.
- Add an Optional Deeper Discovery section for repo overview that explains `tailtrail-meta/code-graph-cache.json` is created only after an approved `graph map --root ...` command. Implemented.
- Make generated post-task learning capture commands portable when TailTrail is run against another repo through `--root`. Implemented.
- Add a `tests/` suite (Python `unittest`, standard library only) covering navigator classification, golden Markdown rendering, task-start wrapping, guardrail-check detection, intent expansion, and policy checks with fixture inputs and expected outputs. Implemented.
- Wire the tests into `.github/workflows/tailtrail-ci.yml`. Implemented while preserving manual-only `workflow_dispatch`.
- Extend `scripts/check-tailtrail.py` to require test coverage references for new implementation files. Implemented by registering `scripts/navigator_core.py` and `tests/`.

Acceptance check:

- Navigator behavior is unchanged externally but split into testable units. Implemented.
- CI runs deterministic tests on every manual validation run. Implemented; push-triggered CI remains intentionally disabled.
- New implementation files are tracked by the checker. Implemented.

Implemented test examples:

- Navigator classifies Sonar plus vulnerability plus handoff prompts into the expected workflow features.
- Navigator detects cross-repo target/reference prompts and preserves parsed paths.
- Navigator classifies repo-overview prompts as read-only discovery and renders a compact plan without skipped-feature noise.
- Navigator repo-overview output shows the exact Code Graph Mapper command and generated cache path without running it automatically.
- Navigator repo-overview Markdown matches a golden fixture.
- Navigator learning-capture suggestions use the TailTrail install hook path, not a target-repo relative hook path.
- Task Start wraps Navigator decisions with next actions, setup posture, token posture, and learning posture.
- Guardrail checks detect dependency manifest additions without Dependency Gate evidence.
- Guardrail checks detect validation claims without evidence.
- Intent expansion maps short prompts such as `use AIDLC and review`.
- Policy checks validate the example policy shape in a temporary repo.

Future candidates:

- Split graph/cache/learning integrations into smaller adapter modules if `scripts/navigator.py` grows again.
- Add broader golden-file coverage for high-risk workflows such as Sonar plus vulnerability plus handoff.
- Add mutation-style fixtures for edge-case prompt routing if teams report drift.

### V3.7: Single-Source Governance Text

Goal: remove drift and overlap across GUARDRAILS, AGENTS, adapters, and guardrail-layers.

Priority: medium.

Status: implemented.

Scope:

- Designate one canonical repeated governance source and sync the marked blocks in project guidance, adapter sources, and guardrail layers.
- Add local and CI-covered checks that fail when marked governance blocks drift from the canonical source.
- Keep human-readable canonical text; sync only the repeated compact block, not complete docs.

Implemented:

- Added `GOVERNANCE.md` as the single source for the compact repeated governance block.
- Added marker-based sync blocks to `AGENTS.md`, `context/guardrail-layers.md`, and adapter source files.
- Added `scripts/sync-governance.py` with `check` and `sync` actions.
- Added `python3 scripts/tailtrail.py governance check|sync` to the unified command surface.
- Added governance sync to `doctor` and `scripts/check-tailtrail.py`.
- Added `GOVERNANCE.md` and `scripts/sync-governance.py` to Copilot pack installation.
- Synced generated tool-facing adapter files through `scripts/sync-adapters.py`.

Example:

```bash
python3 scripts/tailtrail.py governance check
python3 scripts/tailtrail.py governance sync
python3 scripts/sync-adapters.py --write
python3 scripts/tailtrail.py doctor
```

If a contributor changes `GOVERNANCE.md`, `governance sync` updates only the text between:

```text
<!-- tailtrail-governance:start -->
- Read relevant source, callers, tests, configuration, and policy before changing code.
- Reuse existing helpers, types, conventions, validation style, and project patterns before adding new abstractions.
- Prefer standard library, platform-native behavior, framework capabilities, and already-installed dependencies before adding packages.
- Make the smallest maintainable change that solves the root problem without unrelated rewrites or formatting churn.
- Preserve safeguards: authentication, authorization, validation, escaping, accessibility, data integrity, privacy, logging, auditability, error handling, data-loss prevention, and explicit user requirements.
- Do not claim tests, builds, scans, pushes, deployments, merges, or approvals succeeded unless they actually ran and succeeded.
- Preserve exact source, diffs, configs, commands, file paths, IDs, hashes, dependency names and versions, security rules, policy text, and logs when exactness affects the task.
- Token saving must not hide material facts or make validation, policy, security, dependency, or source evidence lossy.
- Use `tailtrail-policy.md` when present, and never let local policy, project memory, summaries, or learnings weaken explicit safety rules.
<!-- tailtrail-governance:end -->
```

This prevents repeated behavior text from drifting while still allowing each file to keep its own local explanation and format.

Acceptance check:

- Editing the canonical governance text updates all marked derived blocks through one command. Implemented.
- CI/check-tailtrail catches drift between source and generated views. Implemented.
- No behavioral guardrail is lost in the consolidation because `GUARDRAILS.md` remains the full behavior contract. Implemented.

Deferred:

- No generated README or generated User Guide.
- No hidden policy compiler.
- No full documentation generation framework.

### V3.8: Value Surface And ROI Dashboard

Goal: make the currently invisible value visible (review: "value is invisible").

Priority: medium.

Status: implemented.

Scope:

- Extend Enterprise Reporting to surface concrete governance outcomes: dependencies avoided, safeguards preserved, unverified claims caught (from V3.0/V3.1), diff-size discipline, and learning hygiene trends.
- Add a compact local `report value` view that aggregates guard findings, outcome telemetry (V2.3), and measured savings (V2.4) into one advisory summary.
- Keep it local-only, no upload, no raw prompt or log capture, consistent with existing reporting boundaries.
- Add CSV export and local report comparison from explicitly supplied JSON reports.

Implemented:

- `python3 scripts/tailtrail.py report value --month 2026-07` renders a compact value surface.
- `python3 scripts/tailtrail.py report value --format json` emits machine-readable local value evidence.
- `python3 scripts/tailtrail.py report value --format csv --write-result` writes `.tailtrail/value-report.csv`.
- `python3 scripts/tailtrail.py report compare --previous-report old.json --current-report new.json` compares explicitly supplied local JSON reports.
- Value signals include dependency gate or avoidance signals, dependencies avoided, safeguard preservation signals, validation-truth signals, focused validation signals, diff-size or scope-discipline signals, workflow overlap signals, adoption outcomes, learning hygiene, and token evidence.
- Token evidence remains claim-safe: exact token savings appear only when measured model/API telemetry is supplied.

Acceptance check:

- A team can see, from local evidence, what governance actually prevented over a period. Implemented.
- No exact productivity or ROI claim is made without supporting measured data. Implemented.
- The value view reuses existing local artifacts and adds no new telemetry service. Implemented.

Deferred:

- No web dashboard.
- No central telemetry service.
- No hidden user behavior scoring.
- No automatic upload or organization-wide analytics.

### V3.8.5: Release Mode Separation

Goal: keep internal/private TailTrail usage separate from public/open-market release packaging.

Priority: high for maintainers, invisible to normal internal users.

Status: implemented.

Why this exists:

- Internal users should not see public-release commands, public licensing workflow, contribution workflow, public claim docs, or any suggestion that they can switch TailTrail to public mode.
- Admins still need one source tree that can produce both an internal distribution and a public distribution without maintaining two unrelated codebases.
- Public release work needs license, security, contribution, conduct, claims, and release hygiene files, while internal usage should stay focused on day-to-day development workflows.

Implemented:

- Added `ADMIN-RELEASE-MODES.md` as an admin-only guide for release mode rules and validation.
- Added `scripts/export-release.py` as an admin-only exporter.
- Added two distribution markers:
  - `.tailtrail-internal-release`
  - `.tailtrail-public-release`
- Internal export excludes public/legal/admin files:
  - `LICENSE`
  - `SECURITY.md`
  - `CONTRIBUTING.md`
  - `CODE_OF_CONDUCT.md`
  - `PUBLIC-CLAIMS.md`
  - `RELEASE-CHECKLIST.md`
  - `.github/workflows/tailtrail-ci.yml`
  - `scripts/release-check.py`
  - roadmap/honest-review/admin planning files
  - `ADMIN-RELEASE-MODES.md`
  - `scripts/export-release.py`
- Public export includes public release files and writes `.tailtrail-public-release`.
- Normal `tailtrail.py help` hides `release-check`.
- `tailtrail.py release-check` is blocked unless:
  - `TAILTRAIL_ADMIN=1`, or
  - `.tailtrail-public-release` is present.
- Added admin-only wrapper:

```bash
TAILTRAIL_ADMIN=1 python3 scripts/tailtrail.py admin export --mode internal --target /tmp/tailtrail-internal --force
TAILTRAIL_ADMIN=1 python3 scripts/tailtrail.py admin export --mode public --target /tmp/tailtrail-public --force
```

- Source CI runs release-check through admin mode:

```bash
TAILTRAIL_ADMIN=1 python3 scripts/tailtrail.py release-check
```

- `scripts/release-check.py` now supports exported public folders that are not Git checkouts by falling back to filesystem file discovery.
- Normal user-facing docs no longer advertise public-release workflow or `release-check`.
- Added deterministic unit tests for:
  - internal/public include-exclude behavior
  - internal/public marker creation
  - public files excluded from internal export
  - public release files included in public export

Admin usage:

```bash
python3 scripts/export-release.py --mode internal --target /tmp/tailtrail-internal --force
python3 scripts/export-release.py --mode public --target /tmp/tailtrail-public --force
```

Validation completed during implementation:

- Internal export hides public/legal/admin files.
- Internal `tailtrail.py help` does not show `release-check`.
- Internal `tailtrail.py release-check` is blocked.
- Internal `tailtrail.py doctor` passes.
- Public export enables `tailtrail.py release-check`.
- Public export `tailtrail.py release-check` passes.
- Admin source tree `TAILTRAIL_ADMIN=1 python3 scripts/tailtrail.py release-check` passes.
- `TAILTRAIL_ADMIN=1 python3 scripts/tailtrail.py admin export ...` works for both internal and public modes.

Acceptance check:

- Internal users cannot discover or run public release mode from the normal command surface. Implemented.
- Admins can generate an internal distribution and a public distribution from the same source tree. Implemented.
- Public release checks remain available for public distributions and admin source validation. Implemented.
- Public-only release files do not ship in internal export. Implemented.
- Deterministic tests cover internal/public export behavior. Implemented.
- Admin-only wrapper command exists and remains hidden unless `TAILTRAIL_ADMIN=1`. Implemented.

Deferred:

- Add version stamping into internal/public export manifests after V3.9 changelog/versioning is implemented.
- Add a public distribution README rewrite only if the public release needs a different landing page than the admin source README.

### V3.9: Strategic Focus - Trustworthy AI Behavior Governance

Goal: sharpen positioning around the strongest, most defensible core identified in the review.

Priority: medium, ongoing.

Scope:

- Lead all public docs and the product surface with one lane: trustworthy, multi-assistant, local-first AI behavior governance for coding.
- Frame token routing, lifecycle, scanners, learning, and reporting as optional supporting add-ons, not co-equal headline products.
- Align `README.md`, `DESIGN.md`, and any public roadmap with this single message.

Acceptance check:

- A new evaluator can state TailTrail's core purpose in one sentence after reading the top of the README.
- Secondary features are clearly positioned as optional.
- The USP guardrails (Validation Truth, Exactness, Dependency Gate) are front and center.

### V3.10: Navigator-Led Review And Guarded Fix Loop

Goal: make TailTrail Review powerful without asking users to memorize review commands, flags, or scopes.

Priority: high for daily developer experience.

Status: implemented.

Why this exists:

- TailTrail has many features, so users should not need to remember separate review commands such as `review uncommitted`, `review --base main`, or `review --dir <path>`.
- Code review should be part of the normal Navigator flow after implementation.
- Standalone review requests should be guided by a small scope question instead of requiring command syntax.
- Review findings should be concrete enough to act on: one-line issue description, file, function, line, impact, suggested fix, validation, confidence, and fix safety.
- Review should check not only code health, but also whether implementation appears aligned with the user request, Navigator plan, clarified requirements, or AIDLC requirements. This is an implementation verification layer, not a guarantee of correctness.
- When requirement fulfillment is unclear, TailTrail should ask clarification questions instead of assuming the implementation is complete.
- Approved implementation details, requested changes, clarifications, and fulfillment status should be captured in the learning layer only after user approval, so future tasks improve from review outcomes without storing raw prompts.

Design principle:

```text
User asks naturally -> Navigator chooses or asks review scope -> TailTrail reviews the right diff -> TailTrail reports actionable findings -> user approves fixes -> TailTrail validates and re-reviews
```

Primary user experience:

- Users can say:

```text
Use TailTrail to implement claim validation and review it after.
```

- Navigator should plan:

```text
Implementation -> focused validation -> review uncommitted changes -> ask approval before fixes
```

- After implementation, Navigator should ask:

```text
I can review the uncommitted changes for bugs, validation gaps, security issues, duplicated logic, dependency risk, weakened safeguards, and missing focused tests.

Approve review?
```

Default post-implementation review scope:

- **Uncommitted changes**.

Reason:

- The assistant just changed those files.
- The scope is small, fast, and reviewable.
- It avoids broad repo review unless the user asks.

Standalone review flow:

When the user says:

```text
Use TailTrail to review my code.
Review my changes.
Check this PR before I raise it.
Review this branch against main.
Run security review on this module.
```

Navigator should ask for scope only when the scope is not obvious:

```text
What should TailTrail review?

Recommended: uncommitted local changes

Options:
1. Uncommitted local changes
2. Current branch against main
3. Specific folder or files
4. Full repo review
```

Scope selection rules:

- If uncommitted changes exist and the user says "review my changes", recommend uncommitted changes.
- If no uncommitted changes exist but the branch differs from the base branch, recommend branch-vs-base.
- If the prompt names a folder or file, recommend that path scope.
- If the prompt says full repo, architecture, security, quality gate, or broad review, ask explicit approval before full repo review.
- If the user says PR, branch, merge, or before raising PR, recommend branch-vs-base and ask for the base branch when not obvious.
- If the prompt is post-implementation, default to uncommitted changes and ask for review approval.

Review dimensions:

- requirement fulfillment against user goal and clarified requirements
- bugs and behavior regressions
- validation gaps
- weakened safeguards
- security and trust-boundary concerns
- duplicated logic and missed reuse
- dependency risk
- missing focused tests
- risky broad rewrites
- code consistency with nearby patterns
- unverified claims in comments, docs, or handoff notes

Detailed review output format:

```text
Review Scope
Reviewed uncommitted changes.

Requirement Fulfillment
Status: partially-aligned
Requested: Add blank, null, and non-numeric claim amount validation.
Verified:
- Blank amount handled: appears-addressed
- Null amount handled: unclear
- Non-numeric amount handled: appears-addressed
Clarification needed:
- Where should TailTrail verify null amount behavior?

Summary
Critical: 0
Warning: 2
Info: 1

Findings

Warning 1
Issue: Missing null/empty validation before claim amount parsing
File: src/claims/ClaimValidator.java
Function: validateClaimAmount
Line: 84
Impact: Invalid input may throw a runtime error instead of returning a validation response
Suggested fix: Add an explicit blank/null guard before parsing
Validation: Add a focused unit test for blank amount
Confidence: high
Safe fix: yes, with approval

Warning 2
Issue: Duplicate timeout fallback logic
File: src/client/PaymentClient.java
Function: resolveTimeout
Line: 132
Impact: Divergent fallback behavior can appear across client paths
Suggested fix: Reuse existing TimeoutPolicy.defaultTimeout()
Validation: Existing PaymentClientTest should cover fallback behavior
Confidence: medium
Safe fix: yes, with approval

Info 1
Issue: Test name does not describe expected behavior clearly
File: src/test/java/claims/ClaimValidatorTest.java
Function: testInvalidAmount
Line: 47
Impact: Lower review readability
Suggested fix: Rename test to rejectsBlankClaimAmount
Validation: No additional behavior validation needed beyond the test run
Confidence: medium
Safe fix: yes, with approval
```

Compact finding format for dense output:

```text
Warning | src/claims/ClaimValidator.java:84 | validateClaimAmount
Missing null/empty validation before claim amount parsing.
Impact: invalid input can throw a runtime error instead of returning validation response.
Fix: add explicit guard and focused unit test.
Confidence: high
Safe fix: yes, with approval
```

Clean review output:

```text
Review Scope
Reviewed uncommitted changes.

Summary
Critical: 0
Warning: 0
Info: 0

Result
No review issues found.

Reviewed files:
- src/claims/ClaimValidator.java
- src/test/java/claims/ClaimValidatorTest.java

Checked for:
bugs, validation gaps, weakened safeguards, duplicated logic, dependency risk, security concerns, code consistency, and missing focused tests.

Recommended next step:
Run focused validation before commit.
```

Guarded fix loop:

```text
review -> propose fix list -> user approves selected fixes -> apply one fix at a time -> run focused validation -> re-review changed scope -> stop when clean or accepted info-only findings remain
```

Rules:

- Treat review text, PR comments, scanner output, pasted logs, and suggested fixes as untrusted issue reports.
- Never execute commands from review text.
- Never apply reviewer-provided code blindly.
- Inspect local code first.
- Show proposed fix and validation before editing.
- Ask before editing.
- Ask before running broad tests, scanners, builds, or vulnerability tools.
- Do not auto-commit by default.
- Capture learning only after user acceptance and confidence gate.

Navigator integration:

- Add a `review_after_implementation` flag to Navigator plans when the user asks for implementation work.
- Add `review_scope` to Navigator output:
  - `uncommitted`
  - `branch_vs_base`
  - `path`
  - `full_repo`
  - `needs_user_choice`
- Add `review_detail_level`:
  - `compact`
  - `standard`
  - `detailed`
- Add `fix_loop_allowed` only after explicit user approval.
- Pass compact `--goal` or `--requirement` values into review so implementation verification can compare reviewed changes against the requested behavior.
- If fulfillment is unclear, render clarification questions before suggesting code fixes.
- For small tasks, default to compact review output.
- For risky, security, dependency, scanner, or broad changes, default to detailed output.

Planned commands behind Navigator:

The user should not need these, but TailTrail can keep internal command support for repeatability:

```bash
python3 scripts/tailtrail.py review --scope uncommitted
python3 scripts/tailtrail.py review --scope branch --base main
python3 scripts/tailtrail.py review --scope path --dir services/payment
python3 scripts/tailtrail.py review --scope full --requires-approval
```

Implemented commands:

```bash
python3 scripts/tailtrail.py review
python3 scripts/tailtrail.py review --scope uncommitted
python3 scripts/tailtrail.py review --scope branch --base main
python3 scripts/tailtrail.py review --scope path --dir services/payment
python3 scripts/tailtrail.py review --scope full
```

Implemented files:

- `scripts/review-run.py`: deterministic review scope resolver and finding formatter.
- `templates/review-result.md`: standard review result output.
- `templates/review-finding.md`: individual finding schema.
- `tests/test_review_scope.py`: Navigator/review scope selection tests. Implemented.
- `tests/test_review_output.py`: severity, clean-result, and finding detail formatting tests. Implemented.
- `scripts/navigator.py`: emits `review_plan` with scope, command, approval, detail level, finding fields, and guarded fix-loop rules. Implemented.
- `scripts/navigator_core.py`: detects review intent, post-implementation review, branch review, path review, and full review signals. Implemented.
- `scripts/navigator_render.py`: renders the Navigator-led review plan in full, compact, and commands-only views. Implemented.
- `scripts/task-start.py`: adds a post-implementation review approval action when Navigator selects review. Implemented.
- `TAILTRAIL-COMMANDS.md`: documents Navigator-led review as primary and direct review commands as repeatable backend commands. Implemented.
- `hooks/learning-capture-hook.py`: accepts compact approved changes, requested changes, clarifications, and fulfillment status for approved learning capture. Implemented.
- `scripts/learning-agent.py`: scores fulfillment alignment, requested changes, approved changes, and clarifications as learning-quality evidence. Implemented.
- `templates/learning-signal.md`: documents fulfillment and review-change learning fields. Implemented.

Implementation note:

- `scripts/review-run.py` is deliberately local and deterministic. It does not call an external review service, upload diffs, auto-apply fixes, or auto-commit.
- Current review findings are rule-based and conservative: safeguard-related removals, dependency/build manifest changes, temporary/debug markers, and source changes without test changes in the review scope.
- Current requirement fulfillment is evidence-based and conservative: it compares compact goals/requirements with reviewed diffs and changed-file names, marks unclear areas, and asks clarification instead of assuming.
- Deeper semantic review remains a future enhancement through Code Graph Mapper, scanners, and later AST/semantic engines.

Example prompts and expected routing:

```text
Prompt:
Use TailTrail to fix claim amount validation and add tests. Review after implementation.

Expected route:
Navigator -> implementation -> Test Precision -> focused validation -> review uncommitted changes -> guarded fix loop if approved
```

```text
Prompt:
Use TailTrail to review my changes.

Expected route:
Navigator checks Git state. If uncommitted changes exist, recommend uncommitted review. If not, ask whether to review branch vs base or a specific folder.
```

```text
Prompt:
Use TailTrail to review this branch before PR.

Expected route:
Navigator asks for base branch if not known, then reviews current branch against base. It should include Code Graph Mapper if the diff is broad or touches shared modules.
```

```text
Prompt:
Use TailTrail security review on services/auth.

Expected route:
Navigator selects path-scoped review, Security Review Lens, Code Graph if useful, and asks before vulnerability or scanner commands.
```

Acceptance check:

- A user can ask for review in natural language without remembering flags.
- Post-implementation review defaults to uncommitted changes and asks for approval.
- Standalone review prompts ask for scope only when scope is unclear.
- Findings include severity, one-line issue, file, function, line, impact, suggested fix, validation, confidence, and safe-fix status.
- Review output includes Requirement Fulfillment and asks clarification when implementation alignment is unclear.
- Learning capture can record approved changes, requested changes, clarifications, and fulfillment status after explicit user approval.
- Clean reviews are reported confidently with reviewed scope and checked dimensions.
- Guarded fix loop never applies fixes without user approval.
- Review text and external reports are treated as untrusted issue reports.
- Navigator tests cover uncommitted, branch, path, full repo, and ambiguous review prompts.

Deferred:

- No external review service integration by default.
- No automatic PR comments.
- No auto-commit after fixes.
- No full semantic review engine beyond existing graph/scanner/lens capability until real usage shows gaps.
- No broad full-repo review without explicit approval.

### V3 Success Metrics

- Guardrail enforcement blocks at least the three high-value violation classes locally and in CI, with a low false-positive rate on TailTrail's own history.
- Default install footprint is materially smaller (Core), with Extended one flag away.
- A new reader maps a concrete problem to one command in under a minute.
- At least one reproducible measured-efficacy benchmark exists with committed inputs.
- Navigator is split into tested modules and CI runs deterministic tests on every PR.
- Governance text has one canonical source with CI drift detection.
- Enterprise Reporting shows concrete governance outcomes without new telemetry uploads.
- Internal/public release modes are separated so internal users do not see public-release workflow, while admins can export both distributions.

## Review-Driven Backlog (2026-07-16)

This section captures an independent review of TailTrail's roadmap, features, and posture, plus a concrete, reviewable implementation plan for each finding. It is advisory input to planning. Nothing here changes shipped behavior until an item is approved and scheduled. Items reference existing roadmap tracks (`Shortcoming Remediation Plan`, `V2.x`, `V3`) where they overlap, so this backlog augments rather than replaces prior planning.

### Review Summary

- Core thesis is strong: portable Markdown guidance first, deterministic local automation second, approval-first everything.
- Safety, privacy, and honesty discipline (estimate vs measured, "did it actually run") are the standout strengths and should be protected.
- Biggest gap: efficacy is asserted through local estimates, not proven with measured evidence.
- Secondary gaps: surface-area sprawl, duplicate scripts, setup friction, shallow multi-agent integration, and governance-text duplication risk.

### Aspect Ratings (Advisory)

| Aspect | Rating | Basis |
|---|---|---|
| Vision and positioning | 9/10 | Clear, differentiated "guidance-first, automation-second" thesis. |
| Safety and guardrails design | 9/10 | Approval-first, read-only defaults, explicit non-goals. |
| Privacy posture | 9/10 | Local-only, opt-in telemetry, no raw prompt/secret capture. |
| Roadmap discipline | 8/10 | Phased, acceptance checks, deferrals stated. |
| Honesty of claims | 9/10 | Estimate vs measured separation; MVP-grade labeling. |
| Measured efficacy evidence | 4/10 | Token/quality value still mostly local estimates. |
| Discoverability and UX | 6/10 | `start` helps; overall command surface is large. |
| Maintainability | 5/10 | Large roadmap; duplicate/overlapping scripts. |
| Multi-agent depth | 5/10 | Instruction-file injection, not runtime enforcement. |
| Distribution readiness | 5/10 | Source-only; `python3 scripts/...` friction. |
| Overall | ~7/10 | Principled and safe; held back by evidence, sprawl, friction. |

### Backlog Priority Order

1. BL-1 Measured Efficacy Proof (highest).
2. BL-6 Governance Single-Source And Drift Check (highest, low cost).
3. BL-11 TailTrail Feature Registry (highest, low cost; retroactively raises the value of every prior BL by giving them a shared home).
4. BL-2 Surface-Area Consolidation And Duplicate Script Cleanup (high).
5. BL-3 Packaging And Zero-Friction Entry Point (high).
6. BL-4 `tailtrail next` Continuation Guidance (medium, high UX payoff).
7. BL-7 Guardrail False-Positive Baseline (medium).
8. BL-5 Enforced Guardrails Via Pre-Commit And CI Action (medium).
9. BL-10 Token Harness Track (medium, staged TH-1 through TH-7; extends BL-1; consumes BL-11 registry entries).
10. BL-8 Core Vs Extended Install Profiles (medium; `surface` field is authored in BL-11 registry).
11. BL-9 MCP Guardrail Server, Opt-In (later; tool list projected from BL-11 registry).

Each item below is independently useful, independently removable, and consistent with existing non-goals (no hidden telemetry, no background service, no exact-savings claims without measured usage).

### BL-1: Measured Efficacy Proof

- Problem: The primary value claim (token and quality savings) is shown as `local_estimate`. Adoption evidence needs at least one reproducible, committed measured benchmark.
- Related: `V2.4 Exact Token Usage Path`, `Phase 7 Benchmark Harness`, `V3 Success Metrics`.
- Goal: One command produces a measured before/after report from committed fixtures, clearly labeled measured, not estimated.

Status: implemented end to end. TailTrail ships a dedicated measured-efficacy runner that consumes committed artifacts plus paired token telemetry and enforces strict `measured` vs `estimate` labeling. The runner rejects half-populated measured records under `--strict` and never presents estimate numbers as tokens.

Implemented files:

- `scripts/efficacy-run.py`: deterministic BL-1 runner. Stdlib-only. Produces artifact evidence and token evidence separately, labels token evidence `measured` only when complete baseline + TailTrail token blocks are supplied, and exits non-zero under `--strict` when a record advertises `mode=measured` but is missing token totals.
- `benchmarks/efficacy/README.md`: measured efficacy protocol, evidence labels, half-populated-record rules, reproduction commands, and honesty rules.
- `tests/test_efficacy_run.py`: 8 unit tests covering measured labeling, estimate fallback, half-populated ignore-vs-strict-fail behavior, non-measured record fallback, claim-guard markdown wording, and the committed governance scenario.
- `scripts/tailtrail.py`: adds `tailtrail efficacy run` and `tailtrail efficacy report` verbs, help catalog entry, and installed-pack doctor coverage.
- `scripts/check-tailtrail.py`: registers `scripts/efficacy-run.py`, `benchmarks/efficacy/README.md`, and `tests/test_efficacy_run.py` for package validation and Python syntax checks.
- `scripts/install-copilot.py`: includes `scripts/efficacy-run.py` in installed Copilot packs.
- `.github/workflows/tailtrail-ci.yml`: runs `tailtrail efficacy run --strict --format json` on every manual validation run so schema and labeling regressions fail visibly.

Implemented commands:

```bash
python3 scripts/tailtrail.py efficacy run
python3 scripts/tailtrail.py efficacy run --scenario governance-remediation
python3 scripts/tailtrail.py efficacy run --format json
python3 scripts/tailtrail.py efficacy run --strict --format json
python3 scripts/tailtrail.py efficacy run --write-result
python3 scripts/tailtrail.py efficacy report
```

Verified behavior:

- On the committed `governance-remediation` scenario, the runner returns artifact score `17 / 17`, token evidence label `measured`, measured records `1`, and `--strict` succeeds.
- With no telemetry file present, token evidence label is `estimate` with an explicit reason; estimate details are reported in a separate block and clearly labeled as character-count approximation, not tokens.
- A half-populated `mode=measured` record is added to the ignored list by default and causes `SystemExit` under `--strict`.
- The full test suite runs 73 tests including the 8 new BL-1 tests; all pass.

Acceptance check:

- A fresh clone runs one command and gets a measured report from committed inputs. Implemented via `python3 scripts/tailtrail.py efficacy run`.
- Reports never label estimated numbers as measured. Implemented via strict `label` semantics and dedicated `estimate_details` block.
- CI proves the efficacy path stays green. Implemented via the new CI step running strict JSON mode.

Boundaries:

- No network calls, no provider API keys, no cost conversion in this item.
- The runner is intentionally separate from `scripts/efficacy-benchmark.py` (V3.4). V3.4 produces artifact scores; BL-1 adds strict token-evidence labeling and CI-friendly acceptance.

### BL-1.5: Measured Evidence Portfolio

- Problem: BL-1 proves the measured-efficacy runner works, but one measured scenario is a baseline, not a portfolio. Public and enterprise claims need repeated evidence across task types before TailTrail can credibly say it improves outcomes beyond one curated case.
- Related: `BL-1 Measured Efficacy Proof`, `Phase 7 Benchmark Harness`, `V3.4 Measured Efficacy Benchmark`, `BL-10 Token Harness Track`, `Measured Efficacy Evidence` scoring.
- Goal: Build a committed 5-10 scenario measured evidence portfolio that covers common enterprise task types and keeps claims evidence-labeled.

Status: implemented end to end.

Implemented summary:

- Added explicit portfolio mode to `scripts/efficacy-run.py`.
- Added scenario-class metadata and portfolio coverage summary.
- Added committed scenarios across bug fix, review, security, CI/Sonar, dependency, feature, token-heavy artifact, and learning-governance task classes.
- Added measured sample telemetry for 6 scenarios and estimate-only labeling for 3 scenarios.
- Added tests for committed portfolio coverage and CLI output.
- Updated user guide, command catalog, pitch plan, detailed pitch, and efficacy protocol docs.
- Registered all new fixture files in `scripts/check-tailtrail.py`.

Implemented portfolio result:

```text
Scenarios: 9
Artifact score: 111 / 111
Measured records: 6
Estimated-only scenarios: 3
Target classes missing: none
Public claim ready: true
Final evidence label: mixed
```

The final evidence label is `mixed` because not every scenario has measured token telemetry. Measured claims apply only to scenarios with complete telemetry records; estimate-only scenarios remain labeled as estimates.

Why this matters:

- One scenario proves the harness, fixtures, token telemetry format, and strict labels.
- It does not prove broad task coverage, robustness, or general product impact.
- A portfolio lets TailTrail report where it helps, where it is neutral, and where it still needs improvement.
- Public claims should only describe the scenario classes actually represented by committed evidence.

Evidence maturity ladder:

| Scenario count | Meaning | Claim posture |
|---|---|---|
| 1 | Runner smoke proof | "Measured runner works for one committed scenario." |
| 3 | Internal demo set | "Early evidence across a few workflows." |
| 5-10 | Credible early portfolio | "Measured/local evidence across representative task types." |
| 10+ with repeated runs | Stronger product evidence | "Trend-backed evidence with failures, neutral results, and improvements visible." |

Target portfolio scenarios:

1. **Bug Fix With Focused Tests**
   - Task: fix a small validation or parsing bug.
   - Expected TailTrail behavior: Navigator keeps scope lean, Code Graph or exact callers identify impact, Test Precision recommends one focused check, Review verifies requirement fulfillment.
   - Evidence: baseline output, TailTrail output, expected checks, token telemetry, validation note.

2. **Code Review Only**
   - Task: review an uncommitted diff without implementing.
   - Expected TailTrail behavior: Review reports actionable findings with severity, file, symbol/function when available, line, issue, fix direction, and requirement link when supplied.
   - Evidence: diff fixture, baseline review, TailTrail review, expected finding checks.

3. **Security Or Vulnerability Triage**
   - Task: summarize a SARIF, Trivy, Grype, or audit-style vulnerability artifact and identify likely impacted files.
   - Expected TailTrail behavior: routes through vulnerability/security intelligence, preserves IDs/severities/versions/paths, asks approval before remediation or heavy scans.
   - Evidence: sanitized scanner artifact, summary output, expected retained evidence fields.

4. **CI Or Sonar Failure**
   - Task: triage a failing build/test/Sonar log and suggest a precise fix path.
   - Expected TailTrail behavior: uses CI/Sonar intelligence, Quality Signal Scanner only when requested or approved, keeps first failure and exit evidence, avoids broad repo reads.
   - Evidence: CI/Sonar log fixture, TailTrail summary, expected first-failure/quality-gate checks.

5. **Dependency Decision Or Dependency Change**
   - Task: decide whether to add, upgrade, remove, or avoid a dependency.
   - Expected TailTrail behavior: applies Dependency Gate, checks standard library/platform/framework/installed options first, records reason and validation if dependency change is justified.
   - Evidence: manifest fixture, baseline recommendation, TailTrail recommendation, expected dependency-discipline checks.

6. **Cross-File Feature Change**
   - Task: implement a small feature that touches endpoint/service/test or UI/state/test.
   - Expected TailTrail behavior: Navigator plans before edits, Code Graph Mapper identifies likely impacted files, AIDLC appears only if the change is broad/risky, review verifies requirement fulfillment.
   - Evidence: source fixture, expected touched files, validation command, review output.

7. **Token-Heavy Log Or Scanner Analysis**
   - Task: analyze a large safe artifact without loading unrelated docs/source.
   - Expected TailTrail behavior: Token Harness routes exactness, Structured Reducer compacts safe content, Proof labels evidence correctly, Runtime Compression Bridge remains disabled unless policy enables it.
   - Evidence: large log/scanner fixture, reducer output, optional bridge plan, ledger/proof output.

8. **Learning And Meta-Harness Governance**
   - Task: evaluate whether previous learning or harness evidence should influence a similar task.
   - Expected TailTrail behavior: learning stays advisory, low-confidence/stale learning is not promoted, Meta-Harness recommendations remain proposal-first and registry-aware.
   - Evidence: synthetic learning/harness summaries, review output, expected advisory/approval checks.

Recommended optional scenarios after the first 8:

- **Handoff / Release Readiness**: verify validation, risk, ownership, rollback, and approval notes.
- **Cross-Repo Reference**: read a reference repo safely without copying code and without broad loading.
- **Quality Scanner With Approval Gate**: prove broad scanner/test/build commands are suggested but not run without approval.

Implementation plan:

1. Create one scenario folder per task type under `benchmarks/efficacy/` or `benchmarks/scenarios/`, using a consistent naming convention:
   - `bug-fix-focused-tests`
   - `review-only`
   - `security-vulnerability-triage`
   - `ci-sonar-failure`
   - `dependency-decision`
   - `cross-file-feature`
   - `token-heavy-artifact`
   - `learning-meta-harness-governance`
2. For each scenario, commit:
   - `scenario.md`: user task and constraints.
   - `baseline-artifact.md`: baseline assistant output or baseline workflow artifact.
   - `tailtrail-artifact.md`: TailTrail-guided output.
   - `expected.json`: deterministic checks.
   - `token-usage.jsonl`: measured telemetry when available; otherwise include no measured record and let the runner label it estimated/local evidence.
   - optional `fixtures/`: sanitized logs, diffs, scanner reports, manifests, or source snippets.
3. Extend `scripts/efficacy-run.py` if needed so it can run all scenarios and group results by scenario class.
4. Add `--portfolio` or equivalent scenario selection:

```bash
python3 scripts/tailtrail.py efficacy run --portfolio
python3 scripts/tailtrail.py efficacy run --portfolio --strict --format json
python3 scripts/tailtrail.py efficacy run --scenario bug-fix-focused-tests
```

5. Add a portfolio summary report:

```text
Measured Evidence Portfolio

- Scenarios: 8
- Measured scenarios: 5
- Local-evidence scenarios: 2
- Estimated-only scenarios: 1
- Artifact checks passed: 124 / 136
- Token evidence labels: measured=5, local-evidence=2, estimate=1
- Scenario classes covered: bug-fix, review, security, CI/Sonar, dependency, feature, token-heavy artifact, learning governance
```

6. Add tests for:
   - scenario discovery
   - portfolio aggregation
   - mixed measured/local/estimated labels
   - strict failure on malformed measured telemetry
   - public claim wording
   - scenario-class coverage thresholds
7. Update docs:
   - `benchmarks/efficacy/README.md`
   - `TAILTRAIL-PITCH.md`
   - `PITCH-PLAN.md`
   - `PUBLIC-CLAIMS.md`
   - `USER-GUIDE.md`
8. Add pitch evidence examples under `pitch/evidence/` only if sanitized and useful for demos.

Claim boundaries:

- Do not claim broad TailTrail impact from one scenario.
- Do not claim exact token savings for scenarios without measured model/API usage metadata.
- Do not hide failed or neutral scenarios from the portfolio report.
- Do not compare TailTrail against unnamed or unrealistic baselines.
- Do not turn scenario scores into developer/team performance scores.

Acceptance criteria:

- At least 8 committed scenarios exist across the target task types.
- At least 5 scenarios include measured token telemetry or clearly explain why the label is local/estimated.
- Portfolio command summarizes scenario coverage, artifact checks, and evidence labels.
- Public pitch language can say "measured/local evidence across representative scenarios" only when the portfolio passes coverage thresholds.
- Failing, neutral, and improvement-needed outcomes remain visible.
- Full tests, `doctor`, registry validation, and efficacy portfolio validation pass.

Expected score impact:

- Current measured efficacy evidence score remains around **7/10** because BL-1 proves the runner and one committed measured scenario.
- Completing this portfolio should move measured efficacy evidence toward **8.5-9/10**, assuming scenario quality is realistic, labels are strict, and failures are reported honestly.

### BL-2: Surface-Area Consolidation And Duplicate Script Cleanup

- Problem: `scripts/` contains hyphen/underscore twins (for example `context-receipt.py` and `context_receipt.py`, `prompt-profile.py` and `prompt_profile.py`, `token-budget-coach.py` and `token_budget_coach.py`). This raises maintenance and onboarding cost and contradicts the lean promise.
- Related: `V3 Success Metrics` (smaller footprint), `Direction`.
- Goal: One canonical importable module per capability with thin CLI wrappers, no behavior change.

Status: implemented. TailTrail now treats underscore files as importable canonical modules and hyphenated files as compatibility CLI wrappers. User-facing docs route through `python3 scripts/tailtrail.py ...`, while direct wrapper paths remain available for compatibility.

Wrapper retention note: keep the four hyphenated wrapper files through at least the next minor release after BL-3 packaging lands. Revisit removal only after docs, installer output, demo material, and command telemetry show users are using the unified `tailtrail`/`python3 scripts/tailtrail.py` surface. If uncertain, keep wrappers permanently as stable compatibility shims.

Implemented duplicate-pair inventory:

| Capability | Public TailTrail command | Thin CLI wrapper | Canonical importable module |
|---|---|---|---|
| Context Receipts | `python3 scripts/tailtrail.py receipt ...` | `scripts/context-receipt.py` | `scripts/context_receipt.py` |
| Prompt Compression Profiles | `python3 scripts/tailtrail.py profile ...` | `scripts/prompt-profile.py` | `scripts/prompt_profile.py` |
| Token Budget Coach | `python3 scripts/tailtrail.py budget ...` | `scripts/token-budget-coach.py` | `scripts/token_budget_coach.py` |
| Token Telemetry | `python3 scripts/tailtrail.py telemetry ...` | `scripts/token-telemetry.py` | `scripts/token_telemetry.py` |

Implemented files:

- `tests/test_cli_dispatch.py`: verifies each hyphen wrapper imports only `main` from its underscore module, defines no independent functions/classes, TailTrail dispatches through the public wrappers, and docs do not advertise underscore module paths.
- `USER-GUIDE.md`: feature inventory now lists public `tailtrail.py` commands instead of both wrapper and module paths.
- `demo-project-layout/tailtrail-demo-workspace/tailtrail/USER-GUIDE.md`: demo copy re-synced with the public command surface.
- `scripts/public-doc-audit.py`: user-facing doc audit now fails when public docs advertise internal underscore module paths.
- `scripts/check-tailtrail.py`: package validation includes the new CLI dispatch tests.

Implementation plan:

1. Inventory duplicate pairs and classify each as importable-module vs CLI-wrapper. Implemented.
2. Keep the underscore module as the importable core and the hyphen file as a thin `tailtrail.py`-dispatched wrapper. Implemented.
3. Ensure `tailtrail.py` subcommands call the public wrapper path while wrapper logic delegates to canonical modules. Implemented.
4. Keep direct wrapper paths as compatibility shims until after BL-3 packaging stabilizes; revisit later and keep permanently if usage is uncertain. Implemented.
5. Add `tests/test_cli_dispatch.py` asserting wrappers are thin and docs avoid importable module paths. Implemented.
6. Update docs to list public `tailtrail.py` commands only. Implemented.

Acceptance check:

- No capability has two independent logic copies.
- All documented commands still run.
- Duplicate-logic count drops to zero in a follow-up audit.

Boundaries:

- No user-facing command removal without a deprecation release.

### BL-3: Packaging And Zero-Friction Entry Point

- Problem: Every command is `python3 scripts/tailtrail.py ...`. This adds friction against the "useful plan in under a minute" goal.
- Related: `V2.9 Packaging And Distribution Decision`.
- Goal: Provide a `tailtrail` console entry point without adopting heavy packaging or new runtime dependencies.

Status: implemented. TailTrail now ships local packaging metadata and a zero-dependency console-entry shim while keeping `python3 scripts/tailtrail.py ...` as the canonical fallback.

Shipped files and commands:

- `pyproject.toml`: defines the stdlib-only local package, `setuptools` build backend, empty runtime dependency list, and `tailtrail = "tailtrail_cli:main"` console script.
- `tailtrail_cli.py`: source-tree resolver and console-entry shim. It honors `TAILTRAIL_ROOT`, falls back to the current checkout when `scripts/tailtrail.py` is present, sets `TAILTRAIL_COMMAND_NAME=tailtrail`, and exec-loads the existing dispatcher without changing `scripts/tailtrail.py`.
- `tests/test_packaging_entry_point.py`: validates package metadata, zero runtime dependencies, importability, and source-tree root resolution.
- `scripts/smoke-test.py`: now checks `python3 tailtrail_cli.py hello` and also checks `tailtrail hello` when a prior install places `tailtrail` on `PATH`.
- `.github/workflows/tailtrail-ci.yml`: installs the checkout with `python3 -m pip install --user .` and runs `tailtrail hello`.
- Docs: `README.md`, `QUICKSTART.md`, `USER-GUIDE.md`, and `CHANGELOG.md` document optional `pipx install .` / `pip install --user .` usage while preserving the fallback command path.

Supported local install commands:

```bash
pipx install .
pip install --user .
tailtrail hello
tailtrail start "fix Sonar issue"
```

Acceptance check:

- `tailtrail start "goal"` works after install.
- `python3 scripts/tailtrail.py start "goal"` still works without install.
- No new runtime dependency is introduced.

Boundaries:

- No package-manager publication in this item; local install only until demand is shown (consistent with V2.9).

### BL-4: `tailtrail next` Continuation Guidance

- Problem: After the Start report, users lack a lightweight "what now" continuation. The roadmap deferred `tailtrail.py next`; review suggests it is needed sooner.
- Related: `V2.1 One-Command User Experience` (deferred follow-up).
- Goal: A compact, deterministic next-step recommender that reads current state and suggests one action.

Status: implemented end to end. TailTrail now ships a read-only continuation recommender through `python3 scripts/tailtrail.py next`.

Shipped files and behavior:

- `scripts/task-next.py`: deterministic stdlib-only report generator. Reads the latest `.tailtrail/task-starts/*.json` when present, read-only Git state, review/scan/learning markers, learning refresh actions, and graph-cache presence. It writes nothing and never runs scanners, tests, Git mutations, learning capture, or network calls.
- `python3 scripts/tailtrail.py next`: command dispatcher and help entry.
- `tests/test_task_next.py`: covers clean state, post-plan uncommitted review recommendation, clean post-implementation value recommendation, pending scan approval, and stale learning refresh action handling without calling Git on the real repo.
- `scripts/task-start.py`: verbose Decision Menu now points users to `next` for a lean resume reminder.
- `scripts/install-copilot.py` and `doctor`: installed packs include and validate `scripts/task-next.py`.
- `TAILTRAIL-COMMANDS.md`, `USER-GUIDE.md`, and `README.md`: document `next` as a secondary resume command after `start`.

Commands:

```bash
python3 scripts/tailtrail.py next
python3 scripts/tailtrail.py next --root .
python3 scripts/tailtrail.py next --format json
```

Acceptance check:

- `next` gives exactly one obvious recommended action.
- It never runs scanners, edits files, or captures learning by itself.

Boundaries:

- Advisory only; no automatic execution.

### BL-5: Enforced Guardrails Via Pre-Commit And CI Action

- Problem: Guardrails are advisory (instruction files) rather than optionally enforced.
- Related: `V3 Success Metrics` (block three high-value violation classes), `Phase 2.5 Agent Guardrails`.
- Goal: Optional, opt-in blocking enforcement for a small set of high-value violation classes, with low false positives.

Status: implemented end to end. TailTrail now supports optional class-scoped guardrail enforcement while preserving advisory default behavior.

Shipped files and behavior:

- `scripts/guardrail-check.py`: adds canonical enforceable classes, `--fail-on <class>[,<class>...]`, `rule_class` in findings, JSON fields for `mode`, `enforce`, `fail_on_classes`, and blocking count. `--enforce` still blocks high-severity findings; `--fail-on` blocks only named classes; both can be combined.
- `.pre-commit-hooks.yaml`: registers `tailtrail-guard` as a system-language hook. It is advisory by default; downstream repos opt into enforcement through hook args.
- `.github/actions/tailtrail-guard/action.yml`: reusable composite action for downstream repositories. It checks out TailTrail and runs `guard check`, with optional `fail-on` input.
- `tests/test_guardrail_check.py` and `tests/fixtures/guardrail/*`: positive fixtures for dependency gate, safeguard removal, local state, and validation-claim findings; negative fixtures for Dependency Gate-approved additions, formatting-only diffs, TODO deletion, and skipped validation wording.
- `.github/workflows/tailtrail-ci.yml`: validates class-scoped enforcement against committed guardrail fixtures.
- `GUARDRAILS.md`, `QUICKSTART.md`, `USER-GUIDE.md`, and `TAILTRAIL-COMMANDS.md`: document optional `--fail-on` usage, pre-commit setup, and the advisory default.

Commands:

```bash
python3 scripts/tailtrail.py guard check
python3 scripts/tailtrail.py guard check --enforce
python3 scripts/tailtrail.py guard check --fail-on dependency-gate,local-state
```

Acceptance check:

- The check blocks the defined classes only when enforcement is explicitly enabled.
- Findings include exact rule, file, line, and reason.
- Warn-only remains the default.

Boundaries:

- No auto-fix, no auto-commit, no network calls.

### BL-6: Governance Single-Source And Drift Check

- Problem: Governance text is duplicated across many `.md` files and adapters, creating near-term drift risk. The roadmap only lists a canonical source as a V3 metric.
- Related: `V3 Success Metrics`, `GOVERNANCE.md`, `adapters/*`.
- Goal: One canonical governance block; generated copies; CI fails on drift.

Status: implemented end to end. Governance sync now has complete target coverage, snapshot policy, strict checking, and an inventory report.

Shipped files and behavior:

- `scripts/sync-governance.py`: expands `TARGETS` to root assistant files, generated adapter files, `ROADMAP.md`, and compact guardrail layers; adds `SNAPSHOT_TARGETS` for demo workspace copies; adds `inventory`, `--strict`, `--include-snapshots`, `--root`, and `--format markdown|json`.
- `python3 scripts/tailtrail.py governance check --strict`: fails on drift, missing markers in targets, and unregistered real marker blocks.
- `python3 scripts/tailtrail.py governance inventory --format markdown|json`: reports canonical, target, snapshot, and unregistered files with status.
- `.github/workflows/tailtrail-ci.yml`: adds dedicated `Check governance drift` and advisory `Governance inventory` steps.
- `tests/test_governance_sync.py`: covers canonical extraction, sync/check, idempotency, drift detection, missing marker failure, snapshot policy, inventory shape, strict unregistered handling, and CI-visible error wording.
- `GOVERNANCE.md`, `CONTRIBUTING.md`, and `TAILTRAIL-COMMANDS.md`: document the single-source editing rule and inventory/check commands.

Expanded target policy:

- Sync targets are live generated governance blocks and must match `GOVERNANCE.md` byte for byte.
- Demo files under `demo-project-layout/` are snapshots. Normal sync does not mutate them; `--include-snapshots` is the explicit opt-in path.

Acceptance check:

- One edit to the canonical block updates all copies via the sync script.
- CI fails when a generated copy is edited directly or left stale.

Boundaries:

- No change to governance meaning; mechanical single-sourcing only.

### BL-7: Guardrail False-Positive Baseline

- Problem: V3 targets a "low false-positive rate" but there is no measurement harness proving rule-based findings are not noisy.
- Related: `BL-5`, `Phase 8.6 Quality Signal Scanner`, `Phase 7.2 Code Review Graph Lite`.
- Goal: A committed precision baseline for rule-based review/scanner findings against labeled outcomes.

Status: implemented end to end. TailTrail now has a committed precision baseline for the first Enforcement Lite guardrail classes.

Shipped files and behavior:

- `benchmarks/guardrail-precision/README.md`: explains fixture layout, expected labels, metrics, thresholds, strict mode, and claim limits.
- `benchmarks/guardrail-precision/thresholds.json`: stores minimum precision and minimum fixture counts per rule class.
- `benchmarks/guardrail-precision/fixtures/`: contains 64 committed labeled fixtures, 8 expected-finding and 8 expected-clean fixtures for each rule class: `dependency-gate`, `safeguard-removal`, `local-state`, and `validation-claim`.
- `scripts/guardrail-precision.py`: runs the existing guardrail detector over labeled fixtures and computes TP, FP, TN, FN, precision, recall, false-positive rate, fixture count, confidence, threshold, and status.
- `python3 scripts/tailtrail.py guardrail precision`: user-facing command for the precision baseline.
- `python3 scripts/tailtrail.py guard precision`: compatibility alias through the existing guard command surface.
- `tests/test_guardrail_precision.py`: covers metric math, insufficient fixtures, cross-rule leakage, undefined precision, committed fixture baseline, selected-rule scoping, no fixture mutation, and threshold regression behavior.
- `.github/workflows/tailtrail-ci.yml`: runs `python3 scripts/tailtrail.py guardrail precision --strict --format json` so precision regressions fail CI.
- `scripts/check-tailtrail.py`, `scripts/install-copilot.py`, `GUARDRAILS.md`, `TAILTRAIL-COMMANDS.md`, and `USER-GUIDE.md`: include the runner in package validation, installed packs, and user docs.

Current baseline example:

```text
Rule                 Precision  Recall  FP rate  Fixtures  Status
dependency-gate      1.00       0.62    0.00     16        ok
safeguard-removal    1.00       0.88    0.00     16        ok
local-state          1.00       1.00    0.00     16        ok
validation-claim     0.89       1.00    0.12     16        ok
```

How to use:

```bash
python3 scripts/tailtrail.py guardrail precision
python3 scripts/tailtrail.py guardrail precision --strict --format json
python3 scripts/tailtrail.py guardrail precision --rule dependency-gate
```

Strict status rules:

- `ok`: fixture count is sufficient and precision meets the committed floor.
- `below-threshold`: precision is defined but below the rule floor.
- `insufficient-fixtures`: the rule does not have enough labeled fixtures.
- `undefined`: the rule produced no positive predictions, so precision cannot be calculated.

Acceptance check:

- A committed precision number exists and is enforced in CI. Implemented.
- New enforced rule classes should add labeled fixtures and pass the precision threshold before shipping. Implemented as the expected maintainer workflow.

Boundaries:

- Measures TailTrail's own fixtures; no external repo scraping.
- Does not add new guardrail detection rules.
- Does not rename existing enforcement classes.
- Does not claim universal precision across every repo or language.

### BL-8: Core Vs Extended Install Profiles

- Problem: The full surface (many scripts, docs, adapters) overwhelms new users and inflates footprint.
- Related: `V3 Success Metrics` (smaller Core), `Direction`.
- Goal: A minimal Core profile (start, Navigator, guardrails) with Extended one flag away.

Status: implemented end to end. TailTrail now supports an install-time surface-area split: `core` for first-run workflows and `extended` for the full pack. Extended remains the default, so existing installs keep the full behavior unless a user explicitly chooses Core.

Shipped files and behavior:

- `scripts/install_surfaces.py`: single source of truth for `CORE_FILES`, `CORE_DIRS`, `CORE_SCRIPTS`, `CORE_CONTEXT`, `CORE_TEMPLATES`, `SURFACES`, `DEFAULT_SURFACE`, and `resolve()`.
- `scripts/install-copilot.py`: accepts `--surface core|extended`, writes `surface` into `.tailtrail-install.json`, supports `--target` root-layout installs, supports `--status`, and supports additive `--upgrade` from Core to Extended.
- `scripts/install-local.py`: accepts `--surface core|extended` without changing the existing `--profile` flag. `--profile` remains the assistant/install context selector; `--surface` is file breadth.
- `scripts/tailtrail.py`: adds `install status` and `install upgrade-to-extended`, shows surface examples in help, and makes installed-pack doctor respect Core manifests instead of requiring Extended files.
- `tests/test_install_profiles.py`: covers Core subset invariants, Core size, default Extended behavior, Extended-only omissions, Core first-run capability, additive upgrade planning, manifest surface recording, unknown-surface rejection, and deterministic Core manifest ordering.
- `.github/workflows/tailtrail-ci.yml`: adds dedicated `Core install smoke` and `Core upgrade smoke` steps.
- `QUICKSTART.md`, `USER-GUIDE.md`, and `TAILTRAIL-COMMANDS.md`: document when to choose Core vs Extended and how to upgrade.

Core manifest summary:

- Files: root guidance and quick docs, root assistant adapters needed by governance sync, `ROADMAP.md` because governance drift check targets it, `pyproject.toml`, `tailtrail_cli.py`, and `tailtrail-policy.example.md`.
- Directories: `adapters/` only.
- Context: `context/TailTrail.map.md`, `context/slices.md`, `context/intent-aliases.md`, `context/guardrail-layers.md`, and `context/token-router.md`.
- Templates: `templates/intent-overrides.json`.
- Scripts: `tailtrail.py`, `task-start.py`, Navigator core/render files, guardrail check, governance sync, adapter sync, policy check, installer helpers, intent/router helpers, and the small import-time modules needed by `start`.

Commands:

```bash
python3 scripts/tailtrail.py install copilot --target /path/to/project --surface core
python3 scripts/tailtrail.py install local --target /path/to/project --profile copilot --surface core
python3 scripts/tailtrail.py install status --target /path/to/project
python3 scripts/tailtrail.py install upgrade-to-extended --target /path/to/project
```

Upgrade behavior:

- Core -> Extended is additive.
- It writes missing Extended files and rewrites byte-identical TailTrail-managed files only.
- It records `upgraded_at` in `.tailtrail-install.json`.
- It does not delete files or implement a downgrade path.

Acceptance check:

- Core install footprint is materially smaller than full. Implemented and tested.
- Extended is one flag away and additive. Implemented through `install upgrade-to-extended`.
- Core alone can produce a Start report and run guardrails/governance. Implemented and smoke-tested.

Boundaries:

- No feature removal; only install-time selection.
- No third surface.
- No rename or semantic change to `install-local.py --profile`.
- No downgrade path.

### BL-9: MCP Guardrail Server, Opt-In

- Problem: Multi-agent integration is instruction-file injection, not runtime enforcement.
- Related: `V2.7` deferred MCP adapter, `Phase 6 Multi-Agent Adapters`.
- Goal: An opt-in local MCP server that exposes Navigator, guardrail-check, and read-only context helpers to MCP-capable agents, with the Markdown path as fallback.

Status: implemented end to end for the read-only BL-9 V1 scope. TailTrail now has an opt-in stdio MCP server, a CLI surface, tests, docs, CI validation, and Extended-pack inclusion. The implementation deliberately does not add autonomous development chaining, write tools, scanner execution, background service behavior, telemetry upload, or MCP-only behavior.

Shipped files and behavior:

- `scripts/mcp-server.py`: stdio JSON-RPC MCP server with allowlisted read-only tools: `navigator_plan`, `start_report`, `guardrail_check`, `graph_map`, `install_status`, `eval_scenario_list`, and `eval_scenario_report`.
- `python3 scripts/tailtrail.py mcp serve`: starts the local stdio MCP server for MCP-capable hosts.
- `python3 scripts/tailtrail.py mcp tools`: lists the read-only MCP tool contract.
- `python3 scripts/tailtrail.py mcp doctor`: validates tool schemas, handler coverage, and read-only posture.
- `tests/test_mcp_server.py`: covers tool list, JSON schemas, unknown-tool rejection, stdio `tools/list`, doctor, command construction, guardrail diff handling, and install-status read-only behavior.
- `MCP-SERVER.md`: documents setup, tools, safety boundaries, MCP host config shape, recommended user flow, and non-MCP fallback.
- `scripts/check-tailtrail.py`, `scripts/install-copilot.py`, and `.github/workflows/tailtrail-ci.yml`: include MCP in package validation, Extended managed packs, syntax checks, and CI doctor validation.
- `QUICKSTART.md`, `TAILTRAIL-COMMANDS.md`, and `USER-GUIDE.md`: document MCP commands and boundaries.

Commands:

```bash
python3 scripts/tailtrail.py mcp tools
python3 scripts/tailtrail.py mcp doctor
python3 scripts/tailtrail.py mcp serve
```

Design clarification:

- BL-9 V1 makes TailTrail capabilities callable through MCP. It does **not** make Navigator an autonomous development engine.
- MCP Navigator should not call every TailTrail tool automatically for a complete development task.
- The assistant remains responsible for reading the MCP result, showing the plan, asking for user approval, implementing code, and deciding which approved follow-up tools are appropriate.
- The user approval boundary remains unchanged: implementation, scanner execution, broad reads, fixes, and learning capture still require explicit approval through the normal TailTrail workflow.
- MCP improves tool access and consistency, not autonomy.

Current design without MCP:

```text
User prompt
  -> assistant reads TailTrail docs or runs tailtrail guide/start
  -> Navigator returns recommended path
  -> assistant/user manually follows commands
```

Weaknesses in the current design:

- The assistant may skip TailTrail unless prompted.
- The assistant may not know which TailTrail script to call.
- Different assistants interpret Markdown guidance differently.
- Agents may over-read TailTrail docs instead of calling the compact command.
- Guardrail/review/graph follow-up can be inconsistent after planning.

BL-9 design with MCP:

```text
User prompt
  -> assistant calls navigator_plan
  -> assistant receives structured plan
  -> assistant may call read-only graph_map or guardrail_check when the plan says they are useful
  -> assistant asks user before implementation, scanner execution, fixes, or learning capture
```

Initial MCP tools:

- `navigator_plan`: returns the Navigator plan only. It does not implement, scan, or edit files.
- `start_report`: returns the compact TailTrail Start report. It does not edit files or capture learning.
- `guardrail_check`: runs the deterministic guardrail checker on a provided diff or safe staged diff input and returns structured findings.
- `graph_map`: returns graph/read-order guidance from existing review graph tooling. It does not create or refresh heavy graph caches in V1.
- `install_status`: reads install manifest state and reports Core/Extended/unknown plus safe next command.

Implementation plan:

1. Add `scripts/mcp-server.py` as an stdio JSON-RPC MCP server with a hardcoded allowlist of read-only TailTrail tools.
2. Add `python3 scripts/tailtrail.py mcp serve`, `python3 scripts/tailtrail.py mcp tools`, and `python3 scripts/tailtrail.py mcp doctor`.
3. Keep all handlers as thin wrappers around existing TailTrail scripts. Do not duplicate Navigator, guardrail, graph, or Start logic.
4. Implement tool schemas inside the server registry. Each tool gets a name, description, input schema, and handler.
5. Enforce read-only posture at the server level:
   - no arbitrary shell command tool
   - no write/apply/fix tool
   - no scanner/test/build runner tool
   - no network listener
   - no upload or telemetry export
   - no background service
6. Add `tests/test_mcp_server.py` covering tool list, schemas, unknown-tool rejection, read-only allowlist, stdio request handling, and representative handler command construction.
7. Add `MCP-SERVER.md` documenting purpose, setup, tool list, safety boundaries, assistant config example, and fallback path.
8. Update `scripts/check-tailtrail.py`, `scripts/install-copilot.py`, `TAILTRAIL-COMMANDS.md`, `USER-GUIDE.md`, `QUICKSTART.md`, and CI.

Recommended user flow:

```text
1. MCP assistant calls navigator_plan.
2. Assistant shows the TailTrail plan.
3. User approves or edits the plan.
4. Assistant calls read-only support tools only when useful.
5. Assistant implements code after approval.
6. Assistant runs guardrail/review checks only when appropriate and approved by workflow.
7. User reviews final output.
```

What BL-9 improves:

- Less prompt dependence: MCP-capable assistants can discover TailTrail tools instead of waiting for a long user prompt.
- More reliable planning: `navigator_plan` and `start_report` return structured, deterministic TailTrail output.
- Lower context use: agents can call compact tools instead of loading large TailTrail docs.
- Better multi-assistant consistency: Codex, Claude, Cursor, Copilot, ChatGPT, Gemini, and future MCP-capable hosts can share the same local TailTrail tool contract.
- Safer boundary: V1 exposes read-only tools only and keeps implementation/scanners/fixes behind user approval.
- Future automation path: a later Navigator Orchestrator can chain approved tools, but only after precision, UX, and safety evidence justify it.

Future candidate: Navigator Orchestrator:

- Purpose: after BL-9 proves the MCP contract, add an optional orchestrator that can propose a machine-readable sequence such as `navigator_plan -> graph_map -> approval -> implementation -> guardrail_check -> review`.
- It should still ask before implementation, scanner execution, fixes, or learning capture.
- It should not ship until guardrail precision, review quality, and user-approval UX have enough evidence.
- It should remain opt-in and auditable, not a hidden background automation layer.

Acceptance check:

- MCP-capable agents can call Navigator and guardrail-check locally.
- No background service, no upload, no auto-scan.
- Non-MCP agents still work via instruction files.
- `mcp tools` lists only read-only allowlisted tools.
- `mcp doctor` validates schemas and safety boundaries.
- Tests prove unknown or write-like tools are rejected.

Boundaries:

- Read-only first; enforcement tools only after guardrail precision is proven.
- No automatic complete-development chain in V1.
- No auto-fix, auto-commit, auto-scan, model call, telemetry upload, or long-running daemon.
- No MCP-only behavior; Markdown instructions and CLI commands remain the fallback.

### BL-10: Token Harness Track

- Problem: Token savings today come from ad-hoc slicing, an approximate Start-report posture, and manual telemetry import. There is no single track that unifies content-aware routing, exactness protection, reversible receipts, an append-only ledger, holdout-based measured proof, output-side discipline, cache-friendly assembly, and one-command assistant wrapping. Without this track, savings claims stay directional and TailTrail cannot answer "did the token-saving strategy hurt correctness?" honestly.
- Related: `TOKEN-HARNESS.md` (design source of truth, 15 features + Idea Bank A-AF), `BL-1 Measured Efficacy Proof`, `V2.4 Exact Token Usage Path`, `V2.4.1 Token Budget Coach`, `Phase 7.0a Token Savings Telemetry Guardrail`, `Phase 8.5 CI/Sonar Intelligence`, `Phase 9.8 Harness Review And Metric Confidence Engine`.
- Goal: Deliver Token Harness in seven staged phases (TH-1 through TH-7) so each phase is independently useful, independently removable, and consistent with TailTrail's local-first, approval-first, exactness-first thesis.

Design source of truth:

- `TOKEN-HARNESS.md` holds the full design: Core Thesis, 8 Relevant Headroom Ideas, Idea Bank A-AF, 15 Features, Implementation Phases TH-1 through TH-7, and explicit non-goals.
- This backlog entry intentionally does not duplicate that content. It records the staging, dependencies, cross-links, and acceptance signals that belong in the roadmap.

Staged implementation plan:

1. **TH-1 Router and Design** — implement `scripts/token-harness.py route` with content detection and exactness classification per Feature 1 and Feature 2. Deterministic, stdlib-only. Tests cover source/diff/config/JSON/log/scanner/doc paths. Implemented.
2. **TH-2 Reversible Receipts v2** — extend `scripts/context_receipt.py` per Feature 3 with exactness, preservation list, and retrieval commands. Keep v1 compatibility. Update `setup-scan.py` and gitignore templates so v2 receipts remain local-only. Implemented.
3. **TH-3 Append-Only Ledger** — add `.tailtrail/token-harness-events.jsonl` per Feature 4 with the concurrency safety rules from Idea G (POSIX `fcntl.flock` required, Windows best-effort with warning, monotonic sequence number). Concurrency safety is a release blocker for this phase. Implemented.
4. **TH-4 Structured Reducers** — implement Feature 6 (JSON/tool-output reducer), Feature 7 (log/scanner reducer), and Feature 13 (AST-preserving `structure-exact` view). Each reducer must emit a receipt and pass the exactness gate. Implemented.
5. **TH-5 Proof and Benchmark Integration** — implement Feature 5 (proof levels: estimated / local-evidence / measured / benchmark-measured), Feature 12 (holdout measurement protocol with 10% control group, deterministic salt, sensitive-class exclusion, CI-width confidence gate). Extend `scripts/efficacy-run.py` from BL-1 to consume Token Harness ledger events. `measured` label requires the confidence gate to pass. Implemented.
6. **TH-6 Meta-Harness Feedback** — extend `tailtrail-meta/harness-summary.jsonl` per Feature 11 with sanitized token-strategy fields; extend `meta-harness-analyze.py` to detect strategy-hurts-quality patterns; add central proposal types for router/gate/Navigator tuning. Implemented.
7. **TH-7 Optional Runtime Compression Bridge** — implement Feature 10 as an adapter contract only. **Explicit non-goal: TailTrail is not becoming an HTTP proxy.** Adapter output must pass the exactness gate; failure falls back to exact pass-through, never to silent degradation.

#### TH-1 Implementation Design: Router And Exactness Gate

Status: implemented.

Goal:

- Build the first usable Token Harness layer without reducers, ledger, proxy, adapter, or measured-claim logic.
- Answer one question deterministically: **what kind of content is this, how exact must it remain, and what token strategy is safe?**
- Keep TH-1 read-only, local-only, stdlib-only, and independently reversible.

Implemented files:

- `scripts/token-harness.py`: new Token Harness CLI with `route`.
- `scripts/tailtrail.py`: route wrapper under `tailtrail token-harness route`; short alias `tailtrail token route` delegates to the same router.
- `tests/test_token_harness.py`: deterministic coverage for content routing and exactness.
- `TOKEN-HARNESS.md`: TH-1 status and command examples.
- `TAILTRAIL-COMMANDS.md`: add user-facing command examples.
- `USER-GUIDE.md`: explain when users should run the router.
- `tailtrail-registry.json`: ensure `token-harness` owns the script, command, docs, and tests.

Content types:

| Content type | Typical signals |
|---|---|
| `source` | `.py`, `.java`, `.cs`, `.ts`, `.js`, `.sql`, `.tf`, function/class/import syntax |
| `diff` | unified diff markers such as `diff --git`, `+++`, `---`, `@@` |
| `config` | `.yml`, `.yaml`, `.toml`, `.ini`, `.properties`, `.env.example`, tool config files |
| `security-policy` | security rules, policy docs, guardrail docs, auth/permission config |
| `dependency-manifest` | `package.json`, lock files, `pom.xml`, `requirements.txt`, `.csproj`, `go.mod`, `Cargo.toml` |
| `json` | valid JSON object/array without scanner-specific fields |
| `tool-output` | structured command output, status summaries, non-scanner machine output |
| `log` | stack traces, timestamps, repeated failure lines, build/test logs |
| `scanner-output` | SARIF, Sonar, Trivy, Grype, SAST, dependency audit, rule/severity/file/line evidence |
| `documentation` | Markdown/text docs, README, design notes, handoff docs |
| `learning-history` | `.tailtrail` learning summaries or learning index artifacts |
| `unknown` | ambiguous or unsupported content |

Exactness classes:

| Exactness class | Rule |
|---|---|
| `must-be-exact` | Do not summarize, compress, drop lines, reorder, or paraphrase. Used for source, diffs, configs, security rules, dependency versions, commands, IDs, hashes, and policy text. |
| `structure-exact` | Preserve keys, IDs, paths, counts, severities, relationships, and hierarchy. Used for JSON, scanner output, and structured tool output. |
| `summary-safe` | Summarize only when named facts, decisions, constraints, and section headings remain retrievable. Used for docs and handoff notes. |
| `reduce-safe` | Later reducers may collapse repetitive bulk while preserving failures and retrieval pointers. Used for logs and repeated tool output. |
| `skip-reduction` | Content is tiny, ambiguous, or safer to leave alone; token routing would add more overhead than value. |

Recommended strategies:

| Strategy | Used when |
|---|---|
| `exact-pass-through` | Content must stay exact or is too small to reduce. |
| `graph-first` | Source understanding should start from Code Graph Mapper before broad source reads. |
| `slice-first` | Only relevant sections/files should be loaded. |
| `structure-summary` | Structured JSON/tool output can later be summarized while preserving schema and key facts. |
| `failure-focused-summary` | Logs can later be reduced around first failures, repeated errors, and command boundaries. |
| `scanner-focused-summary` | Scanner output can later preserve rule ID, severity, file, line, package, version, and remediation evidence. |
| `doc-section-slice` | Documentation can be sliced by headings or relevant sections. |
| `learning-summary` | Learning history should load curated high-confidence summaries, not raw history. |
| `skip-reduction` | No reduction is useful or safe. |

CLI design:

```bash
python3 scripts/token-harness.py route --path file.log
python3 scripts/token-harness.py route --path report.sarif --format json
python3 scripts/token-harness.py route --text "..." --label scanner-output
python3 scripts/token-harness.py route --path src/app.py --task "review security fix"
python3 scripts/tailtrail.py token-harness route --path file.log
```

Expected JSON shape:

```json
{
  "schema_version": "1",
  "type": "tailtrail-token-harness-route",
  "input": {
    "path": "src/app.py",
    "label": "",
    "size_bytes": 8421
  },
  "classification": {
    "content_type": "source",
    "exactness_class": "must-be-exact",
    "confidence": "high"
  },
  "strategy": {
    "name": "exact-pass-through",
    "reason": "Source code must remain exact for implementation and review.",
    "allowed_reductions": [],
    "blocked_reductions": ["summarize", "compress", "drop-lines"]
  },
  "preserve": [
    "file path",
    "line numbers",
    "function names",
    "imports",
    "exact source text"
  ],
  "retrieval": {
    "required": false,
    "command": "cat src/app.py"
  },
  "notes": [
    "TH-1 does not transform content.",
    "No token savings claim is produced."
  ]
}
```

Detection and routing examples:

| Input | Content type | Exactness | Strategy |
|---|---|---|---|
| `src/app.py` | `source` | `must-be-exact` | `exact-pass-through` or `graph-first` when task is broad |
| unified diff text | `diff` | `must-be-exact` | `exact-pass-through` |
| `package-lock.json` | `dependency-manifest` | `must-be-exact` | `exact-pass-through` |
| `sonar-project.properties` | `config` | `must-be-exact` | `exact-pass-through` |
| generic JSON | `json` | `structure-exact` | `structure-summary` |
| SARIF/Trivy/Grype/Sonar JSON | `scanner-output` | `structure-exact` | `scanner-focused-summary` |
| build log with stacktrace | `log` | `reduce-safe` | `failure-focused-summary` |
| README/design doc | `documentation` | `summary-safe` | `doc-section-slice` |

Navigator integration for TH-1:

- Keep integration minimal and advisory.
- Navigator may suggest the route command for:
  - large log/scanner prompts
  - explicit token-saving prompts
  - broad review, quality, CI/Sonar, scanner, or vulnerability tasks
  - user-provided file-like targets
- Navigator should not run reducers, write ledgers, or claim savings in TH-1.
- Tiny tasks should skip Token Harness routing unless the user explicitly asks for token saving.

Testing plan:

- Source file route returns `source`, `must-be-exact`, and blocks summarization/compression.
- Unified diff route returns `diff`, `must-be-exact`.
- Dependency manifest route returns `dependency-manifest`, `must-be-exact`.
- Config/security policy route returns an exact class.
- Generic JSON route returns `json`, `structure-exact`.
- SARIF/Trivy/Grype/Sonar-like JSON route returns `scanner-output`, `structure-exact`.
- Log/stacktrace route returns `log`, `reduce-safe`.
- Markdown documentation route returns `documentation`, `summary-safe`.
- Tiny/ambiguous text returns `skip-reduction`.
- CLI JSON output is parseable.
- CLI Markdown includes content type, exactness class, strategy, preserve list, and blocked reductions.

TH-1 acceptance criteria:

- `python3 scripts/tailtrail.py token-harness route --path <file>` works.
- The router never rewrites, compresses, uploads, calls a model, records telemetry, or appends ledger events.
- The router explicitly protects `must-be-exact` content.
- The router can return `skip-reduction` when routing would add overhead or risk.
- Tests cover all required content classes.
- `doctor`, full unit tests, and registry validation pass.
- Public docs do not claim measured savings from TH-1.

#### TH-2 Implementation Design: Reversible Receipts V2

Status: implemented.

Goal:

- Upgrade current context receipts from approximate loaded-versus-avoided accounting into reversible Token Harness evidence.
- Preserve backward compatibility with existing v1 receipts.
- Make every reduced or avoided context decision explain what changed, what must remain exact, and how to retrieve the original evidence.
- Keep TH-2 local-only, approval-first, and free of reducers, ledgers, model calls, API calls, and measured-savings claims.

Current receipt state:

- Existing implementation lives in `scripts/context_receipt.py` with the public wrapper `scripts/context-receipt.py`.
- Existing command surface is `python3 scripts/tailtrail.py receipt capture|summary`.
- Existing storage is `.tailtrail/context-receipts.jsonl`.
- Current receipts record task, profile, budget, loaded paths, avoided paths, approximate token counts, graph-first flag, budget escalation, reason, and local-only guardrails.
- Missing TH-2 fields are exactness class, preservation list, reduction strategy, route provenance, and retrieval pointer.

Implemented files:

- `scripts/context_receipt.py`: extended capture, summary, validation, and retrieval behavior.
- `scripts/context-receipt.py`: keep as a thin wrapper only.
- `scripts/navigator.py`: updated suggested receipt command placeholders to include exactness and strategy when meaningful.
- `scripts/setup-scan.py`: already classifies `.tailtrail/context-receipts.jsonl` as local runtime state.
- `templates/tailtrail-gitignore.md`: already keeps `.tailtrail/context-receipts.jsonl` ignored/local.
- `tests/test_context_receipt.py`: v1/v2 compatibility, validation, summary, and retrieval coverage.
- `TOKEN-HARNESS.md`: TH-2 status and v2 examples.
- `TAILTRAIL-COMMANDS.md`: v2 capture, summary, and retrieval examples.
- `USER-GUIDE.md`: reversible receipts, local-only behavior, and exactness boundaries.
- `tailtrail-registry.json`: receipt scripts/docs/tests are owned by `token-harness`.

Receipt schema v2:

```json
{
  "schema_version": "2",
  "type": "tailtrail-context-receipt",
  "created_at": "2026-07-18T12:00:00+00:00",
  "root": "/repo",
  "task": "fix Sonar issue",
  "profile": "review",
  "budget_tokens": 8000,
  "loaded": [
    {
      "path": "src/App.java",
      "approx_tokens": 1200,
      "exactness_class": "must-be-exact",
      "strategy": "exact-pass-through",
      "preserve": ["exact source text", "line numbers", "imports"],
      "retrieval": {
        "type": "path",
        "command": "cat src/App.java"
      }
    }
  ],
  "avoided": [
    {
      "path": "ROADMAP.md",
      "approx_tokens": 50000,
      "exactness_class": "summary-safe",
      "strategy": "skip-unrelated",
      "preserve": ["not applicable"],
      "retrieval": {
        "type": "path",
        "command": "cat ROADMAP.md"
      }
    }
  ],
  "preserved_evidence": [
    "source file path",
    "line numbers",
    "rule ID",
    "scanner severity"
  ],
  "reduction_strategy": "graph-first-plus-exact-files",
  "route_source": "token-harness",
  "loaded_tokens": 1200,
  "avoided_tokens": 50000,
  "baseline_tokens": 51200,
  "estimated_reduction_percent": 97.66,
  "claim_guardrail": "Local approximate context accounting only. Exact savings require measured telemetry.",
  "privacy": "No raw prompts, source snippets, logs, secrets, PII, PHI, or customer data."
}
```

CLI design:

Existing v1-compatible command remains valid:

```bash
python3 scripts/tailtrail.py receipt capture \
  --task "fix validation bug" \
  --profile review \
  --loaded src/service/foo.py \
  --avoided ROADMAP.md \
  --approved
```

New v2 capture options:

```bash
python3 scripts/tailtrail.py receipt capture \
  --task "fix Sonar issue" \
  --profile review \
  --loaded src/App.java \
  --loaded-exactness must-be-exact \
  --loaded-strategy exact-pass-through \
  --preserve "exact source text" \
  --preserve "line numbers" \
  --retrieval "cat src/App.java" \
  --avoided ROADMAP.md \
  --avoided-exactness summary-safe \
  --avoided-strategy skip-unrelated \
  --route-source token-harness \
  --reduction-strategy graph-first-plus-exact-files \
  --approved
```

Optional TH-2 retrieval command:

```bash
python3 scripts/tailtrail.py receipt retrieve --path src/App.java
```

`retrieve --path` is enough for TH-2. Stable receipt IDs and `retrieve --id` can wait until TH-3 or a later receipt index if needed.

Implementation details:

1. Extend path summaries.

Current item shape:

```json
{"path": "src/foo.py", "approx_tokens": 1200}
```

TH-2 item shape:

```json
{
  "path": "src/foo.py",
  "approx_tokens": 1200,
  "exactness_class": "must-be-exact",
  "strategy": "exact-pass-through",
  "preserve": ["exact text", "line numbers"],
  "retrieval": {"type": "path", "command": "cat src/foo.py"}
}
```

2. Preserve v1 compatibility.

- `capture` without v2 flags should still work.
- `summary` must read mixed v1/v2 JSONL files.
- v1 receipts can remain `schema_version: "1"` and `type: "context-receipt"`.
- v2 receipts should use `schema_version: "2"` and `type: "tailtrail-context-receipt"`.

3. Add exactness validation.

- `must-be-exact` cannot use unsafe strategies such as `summary`, `compress`, `drop-lines`, or `paraphrase`.
- v2 loaded and avoided items should include a retrieval pointer.
- receipt fields must not store raw source bodies, raw logs, secrets, PII, PHI, or customer data.
- receipts remain approximate local context accounting unless paired with measured telemetry elsewhere.

4. Keep receipts local-only.

- `.tailtrail/context-receipts.jsonl` stays private local runtime state.
- `setup-scan.py` should continue warning if local runtime receipt files are about to be committed.
- Gitignore templates and install hygiene should not encourage committing `.tailtrail/context-receipts.jsonl`.

5. Update Navigator suggestion.

Current Navigator receipt suggestion can remain compact, but non-tiny task guidance should include placeholders for:

```bash
--loaded-exactness REPLACE_WITH_exactness
--loaded-strategy REPLACE_WITH_strategy
--route-source token-harness
--reduction-strategy REPLACE_WITH_strategy
--preserve "REPLACE_WITH_preserved_evidence"
```

Navigator should not auto-run capture. It should suggest capture only after meaningful work and explicit approval.

Testing plan:

- Existing v1 receipt capture still works.
- New v2 receipt capture writes `schema_version: "2"` and `type: "tailtrail-context-receipt"`.
- Loaded and avoided entries include exactness, strategy, preserve list, and retrieval pointer.
- Summary reads mixed v1 and v2 receipts.
- `must-be-exact` rejects unsafe reduction strategies.
- Capture refuses writes without `--approved`.
- `receipt retrieve --path ...` shows the retrieval command or path status.
- `.tailtrail/context-receipts.jsonl` remains classified as local-only by setup/install hygiene.
- Docs do not claim exact savings from receipts alone.

TH-2 acceptance criteria:

- Existing `python3 scripts/tailtrail.py receipt capture ... --approved` usage remains compatible.
- New v2 receipt fields can be captured from CLI.
- Summary output remains stable with mixed v1/v2 receipts.
- Unsafe reductions for `must-be-exact` are blocked.
- No raw content is stored in receipts.
- Receipts remain local-only and approval-first.
- Full unit tests, `doctor`, and registry validation pass.
- Public docs say receipts provide local approximate evidence only, not measured model/API savings.

#### TH-3 Implementation Design: Append-Only Token Evidence Ledger

Status: implemented.

Goal:

- Add a durable local JSONL ledger that records Token Harness evidence events safely over time.
- Make token evidence auditable without loading raw context.
- Support future proof, benchmark, Meta-Harness, and reporting phases.
- Keep the ledger local-only, append-only, concurrency-safe, sanitized, and approval-first.
- Exclude pricing/cost fields from the ledger schema through TH-5.

Core rule:

```text
route decisions + receipts + usage evidence + quality result -> append-only local ledger
```

Ledger path:

```text
.tailtrail/token-harness-events.jsonl
.tailtrail/token-harness-events.lock
```

Implemented files planned:

- `scripts/token-harness-ledger.py`: append, summary, and validate commands for the local ledger.
- `scripts/token-harness.py`: routes `ledger ...` to the ledger script.
- `scripts/tailtrail.py`: exposes `tailtrail token-harness ledger ...`.
- `scripts/setup-scan.py`: classifies `.tailtrail/token-harness-events.jsonl` and `.tailtrail/token-harness-events.lock` as local runtime state.
- `templates/tailtrail-gitignore.md`: keeps ledger and lock files ignored/local.
- `tests/test_token_harness_ledger.py`: append, locking, sequence, validation, summary, local-only checks.
- `TOKEN-HARNESS.md`: TH-3 status and ledger examples.
- `TAILTRAIL-COMMANDS.md`: ledger append, summary, and validate examples.
- `USER-GUIDE.md`: local-only ledger usage and claim boundaries.
- `tailtrail-registry.json`: ledger script/test ownership under `token-harness`.

Event types:

| Event type | Purpose |
|---|---|
| `route_decision` | Record selected Token Harness strategy without raw content. |
| `context_receipt` | Record loaded/avoided/preserved context evidence from v2 receipts. |
| `measured_usage` | Record user-provided model/API usage evidence. Deeper integration comes in TH-5. |
| `savings_report` | Record a generated savings report summary. Deeper integration comes in TH-5. |
| `quality_result` | Record whether reduced/shaped context still passed validation. Deeper integration comes in TH-6. |

TH-3 should structurally accept all event types, but only require first-class flows for:

- `route_decision`
- `context_receipt`

Ledger event shape:

```json
{
  "schema_version": "1",
  "type": "tailtrail-token-harness-event",
  "sequence": 1,
  "event_id": "th-20260718-000001",
  "created_at": "2026-07-18T12:00:00+00:00",
  "event_type": "context_receipt",
  "task_type": "bug-fix",
  "content_type": "source",
  "strategy": "exact-pass-through",
  "exactness_class": "must-be-exact",
  "tokens_before": 52000,
  "tokens_after": 1200,
  "tokens_saved": 50800,
  "evidence_label": "local-evidence",
  "validation_outcome": "not-run",
  "receipt_ref": ".tailtrail/context-receipts.jsonl",
  "lock_mode": "posix-flock",
  "privacy": "No raw prompt, source, log, path, secret, repo name, or user identity."
}
```

Required fields:

- `schema_version`
- `type`
- `sequence`
- `event_id`
- `created_at`
- `event_type`
- `task_type`
- `content_type`
- `strategy`
- `exactness_class`
- `tokens_before`
- `tokens_after`
- `tokens_saved`
- `evidence_label`
- `validation_outcome`
- `privacy`

Allowed evidence labels:

- `estimated`
- `local-evidence`
- `measured`
- `benchmark-measured`

Allowed exactness classes:

- `must-be-exact`
- `structure-exact`
- `summary-safe`
- `reduce-safe`
- `skip-reduction`

Privacy and sanitization:

Do not store:

- raw prompt
- raw assistant response
- source snippets
- raw logs
- private repo names
- branch names
- usernames or emails
- private URLs
- customer identifiers
- secrets
- exact file contents

Allowed references:

- `.tailtrail/context-receipts.jsonl`
- `.tailtrail/token-usage.jsonl`
- categorical task/content/strategy labels
- sanitized IDs generated by TailTrail
- hashed references later if a future phase needs them

Concurrency design:

- POSIX/macOS/Linux:
  - use `fcntl.flock(fd, LOCK_EX)` before reading the latest sequence and appending the event
  - flush and release the lock after append
  - record `lock_mode: "posix-flock"`
- Windows or platforms without `fcntl`:
  - use best-effort append
  - record `lock_mode: "best-effort"`
  - validation should still detect torn or malformed lines
- Use a separate lock file:

```text
.tailtrail/token-harness-events.lock
```

Sequence and event ID rules:

- The first event gets `sequence: 1`.
- Each append computes `sequence = current max sequence + 1` while holding the lock.
- `event_id` uses deterministic local format:

```text
th-YYYYMMDD-000001
```

- `sequence` must be monotonic.
- `event_id` must be unique.
- Append must not rewrite or repair old lines.
- Append should fail if validation of the new event fails.
- `validate` reports malformed existing lines instead of silently fixing them.

CLI design:

Append route decision:

```bash
python3 scripts/tailtrail.py token-harness ledger append \
  --event-type route_decision \
  --task-type bug-fix \
  --content-type source \
  --strategy exact-pass-through \
  --exactness-class must-be-exact \
  --tokens-before 1200 \
  --tokens-after 1200 \
  --evidence-label local-evidence \
  --validation-outcome not-run \
  --approved
```

Append context receipt evidence:

```bash
python3 scripts/tailtrail.py token-harness ledger append \
  --event-type context_receipt \
  --task-type sonar-fix \
  --content-type scanner-output \
  --strategy scanner-focused-summary \
  --exactness-class structure-exact \
  --tokens-before 50000 \
  --tokens-after 4000 \
  --evidence-label local-evidence \
  --receipt-ref .tailtrail/context-receipts.jsonl \
  --approved
```

Summary:

```bash
python3 scripts/tailtrail.py token-harness ledger summary
```

Validate:

```bash
python3 scripts/tailtrail.py token-harness ledger validate
```

Expected summary output:

```text
# Token Harness Ledger Summary

- Events: 12
- Tokens before: 240000
- Tokens after: 84000
- Estimated saved: 156000
- Evidence labels:
  - local-evidence: 10
  - estimated: 2
- Strategies:
  - exact-pass-through: 5
  - graph-first: 4
  - scanner-focused-summary: 3

Claim guardrail:
Ledger totals are local evidence only. Exact model/API savings require measured telemetry and TH-5 proof gates.
```

Validation rules:

- every non-empty line is valid JSON
- required fields exist
- `sequence` is monotonic
- `event_id` is unique
- `event_type` is allowed
- `evidence_label` is allowed
- `exactness_class` is allowed
- `tokens_saved = tokens_before - tokens_after`
- `tokens_after <= tokens_before` when both are provided
- pricing/cost fields are rejected:
  - `cost`
  - `price`
  - `dollars`
  - `usd`
- unsafe text markers are rejected:
  - private key markers
  - common token prefixes
  - `password=`
  - `secret=`
  - private URLs
  - email-like user identifiers

Integration rules:

- `token-harness route` should not auto-write ledger events in TH-3.
- `receipt capture` should not auto-write ledger events by default.
- If `receipt capture --ledger` is considered, it must still require `--approved`; first implementation can keep ledger append as a separate explicit command.
- Reports can read ledger summaries in later phases, but TH-3 summary is enough for first value.
- Meta-Harness should not consume ledger until TH-6.

Testing plan:

- append requires `--approved`
- append writes valid JSONL
- sequence increments from 1
- event IDs are unique
- POSIX lock path is exercised where `fcntl` is available
- summary aggregates token counts and category counts
- validate passes a good ledger
- validate fails malformed JSON
- validate fails duplicate event ID
- validate fails non-monotonic sequence
- validate rejects pricing/cost fields
- validate rejects unsafe text markers
- validate rejects `tokens_after > tokens_before`
- setup-scan classifies ledger files as local-only
- gitignore template includes ledger and lock files

TH-3 acceptance criteria:

- `.tailtrail/token-harness-events.jsonl` is append-only.
- Appends are locked with `fcntl.flock` on POSIX.
- Windows or unsupported platforms use explicit best-effort lock mode.
- Every event has monotonic `sequence` and unique `event_id`.
- Write commands require `--approved`.
- Summary works without loading raw context.
- Validate detects corruption, duplicate IDs, non-monotonic sequence, unsafe fields, and pricing fields.
- Setup/gitignore keep the ledger local-only.
- No pricing/cost fields are allowed.
- No exact savings claims are made from the ledger alone.
- Full unit tests, `doctor`, and registry validation pass.

#### TH-4 Implementation Design: Structured Reducers

Status: implemented.

Goal:

- Add the first Token Harness phase that actually transforms context.
- Keep reductions deterministic, local-only, stdlib-only, auditable, and reversible.
- Reduce only content classes that are safe to shape after passing the TH-1 exactness gate.
- Emit receipts only with approval and preserve retrieval paths back to the original evidence.
- Avoid exact savings claims; TH-4 reductions are local structured summaries until TH-5 proof gates exist.

Core flow:

```text
route content -> confirm exactness class -> reduce only safe classes -> emit receipt when approved -> optionally append ledger event
```

Implemented files:

- `scripts/token-harness-reduce.py`: reducer CLI and deterministic reducer implementations.
- `scripts/token-harness.py`: route `reduce ...` commands to the reducer script.
- `scripts/tailtrail.py`: exposes `tailtrail token-harness reduce ...`.
- `scripts/check-tailtrail.py`: include reducer script and tests in TailTrail self-check.
- `scripts/install-copilot.py`: include reducer script in installed packs.
- `tests/test_token_harness_reduce.py`: reducer behavior, exactness boundaries, receipt/ledger approval checks.
- `TOKEN-HARNESS.md`: TH-4 status, examples, exactness boundaries, and claim boundaries.
- `TAILTRAIL-COMMANDS.md`: reducer command examples.
- `USER-GUIDE.md`: user workflow for reducers and when to avoid them.
- `tailtrail-registry.json`: reducer command/script/test ownership under `token-harness`.

CLI design:

```bash
python3 scripts/tailtrail.py token-harness reduce --path report.json
python3 scripts/tailtrail.py token-harness reduce --path build.log
python3 scripts/tailtrail.py token-harness reduce --path report.sarif
python3 scripts/tailtrail.py token-harness reduce --path src/app.py --mode structure
python3 scripts/tailtrail.py token-harness reduce --path report.sarif --write-receipt --approved
```

Optional later CLI:

```bash
python3 scripts/tailtrail.py token-harness reduce --text "..." --label log
```

Output modes:

```bash
--format markdown
--format json
```

JSON output must be deterministic so Navigator, MCP, tests, and later benchmark/proof phases can consume it without parsing prose.

Reducer 1: JSON / tool-output reducer:

- Purpose: reduce large structured output without losing schema shape.
- Preserve:
  - top-level keys
  - nested object paths
  - array counts
  - status fields
  - error fields
  - IDs when safe
  - file/rule/severity references
  - representative array item shape
- Avoid:
  - raw large arrays
  - raw payload bodies
  - secrets, private URLs, emails, or identity fields
  - pretending a structure summary is exact source evidence

Expected JSON-style output:

```json
{
  "content_type": "json",
  "exactness_class": "structure-exact",
  "strategy": "json-structure-summary",
  "summary": {
    "top_level_keys": ["status", "results", "errors"],
    "array_counts": {"results": 842},
    "important_paths": ["errors[0].message", "results[].file", "results[].severity"]
  },
  "retrieval": {
    "command": "cat report.json"
  }
}
```

Reducer 2: log / scanner reducer:

- Purpose: collapse noisy logs and scanner output while preserving actionable failures and evidence.
- For logs, preserve:
  - command boundaries
  - first failure
  - last failure
  - likely root-cause stack trace lines
  - repeated error count
  - file/line references
  - exit code when present
- For scanner output, preserve:
  - rule ID
  - severity
  - file
  - line
  - package/version
  - remediation text
  - quality gate status
  - CVE/GHSA or equivalent vulnerability IDs when present

Expected Markdown-style output:

```text
Reducer: scanner-focused-summary
Findings: 18
Critical: 1
Warning: 7
Info: 10

Top Findings:
- WARNING java:S2259 src/main/java/App.java:42 possible null dereference
- CRITICAL CVE-2025-0001 package example-lib@1.2.0 fixed in 1.2.4

Retrieval:
cat sonar-report.json
```

Reducer 3: AST-preserving `structure-exact` source view:

- Purpose: provide a compact source map without implying that full source bodies were loaded.
- Python should use the standard-library `ast` module.
- Java, C#, TypeScript, and JavaScript should start with conservative stdlib regex extraction only.
- Preserve:
  - imports
  - classes
  - functions and methods
  - decorators or annotations when detectable
  - route/controller-like endpoints when detectable
  - line numbers
  - parent/child structure
  - retrieval command for full source
- Avoid:
  - full function bodies
  - expression-level rewriting
  - semantic call graph claims
  - type hierarchy claims unless explicitly detected by current lightweight parser

Expected source-structure output:

```text
File: src/service/payment.py
Imports:
- decimal.Decimal
- app.validation.validate_amount

Classes:
- PaymentService line 12
  - authorize(self, request) line 18
  - capture(self, payment_id) line 44

Structure exactness:
- bodies omitted
- line numbers preserved
- retrieve full source with: cat src/service/payment.py
```

Exactness rules:

- Reducers must call or reuse TH-1 routing logic before transforming content.
- Allowed reductions:
  - `json` + `structure-exact`
  - `tool-output` + `structure-exact`
  - `scanner-output` + `structure-exact`
  - `log` + `reduce-safe`
  - `documentation` + `summary-safe`
  - `source` only with `--mode structure`, never body compression
- Blocked reductions:
  - source body compression
  - diffs
  - dependency manifests
  - security policy
  - config files
  - lock files
  - secrets or private URLs
  - unknown content unless the reducer returns `skip-reduction`

Receipt integration:

- `--write-receipt` must require `--approved`.
- Reducer receipts use TH-2 schema v2.
- Receipt fields should include:
  - exactness class
  - strategy
  - preserve list
  - retrieval command
  - approximate before/after token counts
  - claim guardrail
- No receipt should store raw source bodies, raw logs, raw scanner payloads, secrets, private URLs, PII, PHI, or customer data.
- No automatic receipt by default.

Ledger integration:

- Ledger append remains optional in TH-4.
- If `--write-ledger` is added, it must require `--approved`.
- Ledger events should be `context_receipt` or `route_decision` with `evidence_label: local-evidence`.
- Default behavior should avoid hidden state changes.

Testing plan:

- JSON reducer preserves keys, paths, counts, and representative shape without dumping large arrays.
- Tool-output reducer handles valid JSON-like command output.
- Scanner reducer preserves severity, rule, file, line, package/version, and remediation evidence.
- Log reducer preserves first failure, repeated failure count, command boundary, and exit status when present.
- Python structure view preserves imports, classes, functions, methods, and line numbers.
- Source structure view does not include full function bodies.
- Protected `must-be-exact` files are rejected unless the source reducer is explicitly in structure mode.
- Diff, dependency manifest, config, and security-policy inputs return a blocked or skip-reduction result.
- Receipt writes require `--approved`.
- Optional ledger writes require `--approved`.
- CLI JSON output is parseable and deterministic.
- `check-tailtrail.py`, registry validation, and install profile checks include the reducer.

TH-4 acceptance criteria:

- `python3 scripts/tailtrail.py token-harness reduce --path <file>` works.
- Reducers never reduce protected exact content.
- Structure views never imply full source was loaded.
- Receipts are emitted only with explicit approval.
- Ledger events are optional and approval-gated.
- Reducer outputs include retrieval commands.
- Full unit tests, `doctor`, and registry validation pass.
- Docs clearly state reductions are local structured summaries, not exact model/API token savings.

Deferred from TH-4:

- tree-sitter
- language server integration
- SCIP
- Roslyn
- vector DB
- graph DB
- external compressor runtime
- model/API calls
- automatic assistant wrapping
- exact ROI claims

#### TH-5 Implementation Design: Proof And Benchmark Integration

Status: implemented.

Goal:

- Add the Token Harness proof layer that distinguishes directional estimates, local evidence, measured evidence, and benchmark-measured evidence.
- Connect Token Harness ledger events with existing telemetry and efficacy benchmark tooling.
- Prevent overstated savings claims by requiring complete measured telemetry and confidence-gate checks before any report can use the `measured` label.
- Answer whether context reduction helped without hiding whether quality changed.

Core questions:

```text
Did Token Harness reduce context?
Was the evidence estimated, local, measured, or benchmark-measured?
Did reduction hurt quality?
Can TailTrail safely claim measured savings?
```

Core flow:

```text
Token Harness route/reduce/receipt/ledger
        |
        v
Token Harness proof report
        |
        v
Efficacy benchmark integration
        |
        v
Evidence label gate:
estimated -> local-evidence -> measured -> benchmark-measured
```

Implemented files:

- `scripts/token-harness-proof.py`: proof report, holdout decision, evidence-label gate, confidence gate.
- `scripts/token-harness.py`: route `proof ...` commands to the proof script.
- `scripts/tailtrail.py`: exposes `tailtrail token-harness proof ...`.
- `scripts/efficacy-run.py`: accepts Token Harness ledger evidence and includes it in efficacy output.
- `scripts/check-tailtrail.py`: includes proof script and tests in TailTrail self-check.
- `scripts/install-copilot.py`: includes proof script in installed packs.
- `tests/test_token_harness_proof.py`: proof labels, holdout, confidence gate, strict telemetry behavior.
- `tests/test_efficacy_run.py`: coverage for ledger integration without breaking existing BL-1 evidence labels.
- `TOKEN-HARNESS.md`: TH-5 status, examples, evidence labels, holdout rules, and claim boundaries.
- `TAILTRAIL-COMMANDS.md`: proof report and holdout command examples.
- `USER-GUIDE.md`: how users interpret proof labels and when claims are allowed.
- `tailtrail-registry.json`: proof command/script/test ownership under `token-harness`.

CLI design:

```bash
python3 scripts/tailtrail.py token-harness proof report
python3 scripts/tailtrail.py token-harness proof report --ledger .tailtrail/token-harness-events.jsonl
python3 scripts/tailtrail.py token-harness proof report --telemetry .tailtrail/token-usage.jsonl
python3 scripts/tailtrail.py token-harness proof report --strict
python3 scripts/tailtrail.py token-harness proof holdout --task-id TASK-123 --task-class bug-fix
python3 scripts/tailtrail.py efficacy run --token-harness-ledger .tailtrail/token-harness-events.jsonl
```

Evidence labels:

| Label | Meaning | Claim allowed |
|---|---|---|
| `estimated` | Approximate counts only, usually from local text size, reducer output, or no ledger. | Directional only. |
| `local-evidence` | Token Harness ledger and/or receipts exist, but no complete provider/model token telemetry is present. | Local context-reduction evidence only. |
| `measured` | Complete user-provided model/API token telemetry exists and passes the confidence gate. | Measured token savings may be stated with boundaries. |
| `benchmark-measured` | Measured telemetry is tied to committed benchmark scenarios and benchmark quality checks pass. | Strongest local proof label; still no cost/ROI claim unless a later pricing module exists. |

Estimated example:

```text
Estimated saved: 5,200 tokens
Evidence: estimated
Claim: directional only
```

Local-evidence example:

```text
Ledger events: 18
Receipts: 11
Evidence: local-evidence
Claim: local context reduction evidence only
```

Measured requirements:

- baseline token count is present
- TailTrail token count is present
- both totals use the same task/scenario ID
- telemetry schema is valid
- no half-populated measured records are counted
- confidence gate passes
- quality result is not worse than baseline

Benchmark-measured requirements:

- measured telemetry exists
- committed benchmark scenario artifact exists
- benchmark artifact/quality score passes
- confidence gate passes
- final output keeps artifact evidence and token evidence separate

Proof report output:

```text
# Token Harness Proof Report

Evidence label: local-evidence
Measured claim allowed: false

Ledger:
- Events: 24
- Route decisions: 8
- Context receipts: 10
- Measured usage events: 0
- Quality results: 6

Token Evidence:
- Local before: 240000
- Local after: 92000
- Local estimated saved: 148000
- Local estimated reduction: 61.67%

Claim Boundary:
This is local Token Harness evidence only. Exact model/API savings require measured telemetry and confidence gate pass.
```

Measured proof output:

```text
# Token Harness Proof Report

Evidence label: measured
Measured claim allowed: true

Measured Telemetry:
- Records: 7
- Baseline tokens: 210000
- TailTrail tokens: 98000
- Saved tokens: 112000
- Reduction: 53.33%

Quality:
- Passed: 7
- Failed: 0

Confidence:
- Gate: passed
- Reason: measured telemetry complete and quality did not degrade
```

Holdout protocol:

- Purpose: avoid proving savings only from shaped TailTrail runs.
- Default: 10% control/holdout group, 90% shaped group.
- Selection is deterministic:

```text
hash(repo_id + task_id + holdout_salt) <= holdout_rate
```

- Holdout means Token Harness does not apply reducers/context shaping for that task.
- Holdout selection should be visible and auditable.
- Users may force a single run with `--holdout` or `--no-holdout` later if reproducibility requires it.

Sensitive task classes excluded from holdout:

- security
- vulnerability
- release
- regulated
- production incident
- auth/permission work

Sensitive classes always keep the shaped/protected workflow because withholding governance or safety context is unacceptable.

Holdout command examples:

```bash
python3 scripts/tailtrail.py token-harness proof holdout --task-id TASK-123 --task-class bug-fix
python3 scripts/tailtrail.py token-harness proof holdout --task-id TASK-999 --task-class security
```

Expected non-sensitive output:

```json
{
  "task_id": "TASK-123",
  "task_class": "bug-fix",
  "holdout": false,
  "reason": "deterministic hash selected shaped run",
  "holdout_rate": 10
}
```

Expected sensitive output:

```json
{
  "task_id": "TASK-999",
  "task_class": "security",
  "holdout": false,
  "reason": "sensitive task class excluded from holdout"
}
```

Confidence gate:

- V1 should stay simple and explainable.
- Measured claims require:
  - at least the configured minimum measured records, default `3`
  - no malformed measured telemetry
  - no half-populated measured records counted as measured
  - shaped token total lower than baseline token total
  - quality pass rate does not degrade
  - confidence-width estimate is within threshold when sample size supports it
  - sensitive classes are not counted as holdout/control evidence
  - no pricing/cost fields exist inside ledger proof inputs

Report simple statistics:

- measured record count
- mean reduction percent
- min and max reduction percent
- baseline token total
- TailTrail token total
- saved token total
- quality pass/fail counts
- confidence gate pass/fail
- confidence gate reason

Ledger extensions:

- Keep TH-3 ledger rows backward compatible.
- Do not add pricing/cost fields.
- Optional TH-5-compatible fields:

```json
{
  "holdout": false,
  "holdout_reason": "deterministic shaped run",
  "task_class": "bug-fix",
  "quality_passed": true,
  "proof_group": "2026-07"
}
```

Efficacy integration:

- Extend `scripts/efficacy-run.py` with:

```bash
python3 scripts/tailtrail.py efficacy run --token-harness-ledger .tailtrail/token-harness-events.jsonl
```

- Combine:
  - existing scenario artifact score
  - existing token telemetry records
  - Token Harness ledger evidence
  - proof label decision
- Output sections should remain separate:

```text
Artifact Evidence
Token Telemetry Evidence
Token Harness Ledger Evidence
Final Evidence Label
Claim Boundary
```

Testing plan:

- proof report reads missing/empty ledger and returns `estimated`
- ledger-only evidence returns `local-evidence`
- complete telemetry returns `measured` only when the confidence gate passes
- benchmark scenario plus measured telemetry returns `benchmark-measured`
- half-populated telemetry never returns `measured`
- strict mode fails malformed measured records
- deterministic holdout returns the same result for same task ID, repo ID, salt, and rate
- sensitive classes are excluded from holdout
- confidence gate blocks `measured` when sample count is too low
- confidence gate blocks `measured` when quality result fails
- confidence gate blocks `measured` when shaped token total is not lower than baseline
- proof input rejects pricing/cost fields
- `efficacy-run.py` consumes Token Harness ledger evidence without breaking existing BL-1 tests
- CLI JSON output is parseable and deterministic
- docs do not claim exact savings from `estimated` or `local-evidence`

TH-5 acceptance criteria:

- `python3 scripts/tailtrail.py token-harness proof report` works.
- Proof report emits exactly one final evidence label.
- Measured claims require complete measured telemetry and confidence-gate pass.
- Benchmark-measured claims require benchmark artifact evidence, measured telemetry, and quality pass.
- Deterministic holdout works.
- Sensitive task classes are excluded from holdout.
- `efficacy-run.py` can consume Token Harness ledger evidence.
- No pricing/cost fields are added to the ledger schema.
- Docs clearly explain claim boundaries.
- Full unit tests, `doctor`, and registry validation pass.

Deferred from TH-5:

- provider API calls
- pricing / dollar ROI conversion
- background telemetry collection
- central upload
- dashboard
- complex statistical model
- model-based quality scoring
- hidden holdouts without user visibility

#### TH-6 Implementation Design: Meta-Harness Feedback

Status: implemented.

Goal:

- Make Meta-Harness aware of Token Harness behavior without making TailTrail self-modifying.
- Use sanitized Token Harness evidence to detect strategy quality risks, proof gaps, and reducer/router tuning opportunities.
- Convert repeated local evidence into reviewable proposals for TailTrail maintainers.
- Keep all shared metadata categorical and privacy-preserving.

Core flow:

```text
Token strategy used -> quality outcome -> proof label -> repeated pattern -> proposal for improvement
```

Core questions:

- Which token strategies are working?
- Which strategies correlate with weak validation or quality failures?
- Are reducers saving context without hurting correctness?
- Should Navigator, router, reducer, or proof gates be tuned?
- Is there enough evidence to propose a TailTrail product improvement?

Implemented files:

- `scripts/harness-review.py`: read local Token Harness evidence and include sanitized token fields in local/shared summaries.
- `scripts/meta-harness-analyze.py`: detect token-strategy findings from shared summaries.
- `scripts/meta-harness-propose.py`: map token findings to router, reducer, proof-gate, Navigator, or docs changes.
- `scripts/token-harness-proof.py`: expose proof labels in a shape Meta-Harness can consume.
- `tests/test_meta_harness_token_feedback.py`: shared summary, analysis, proposal, and privacy tests.
- `META-HARNESS-IMPLEMENTATION.md`: explain token feedback loop and proposal boundary.
- `TOKEN-HARNESS.md`: TH-6 status and examples.
- `TAILTRAIL-COMMANDS.md`: Meta-Harness token-feedback usage examples.
- `USER-GUIDE.md`: how users/maintainers should interpret token-strategy findings.
- `tailtrail-registry.json`: ensure Meta-Harness and Token Harness ownership is clear.

Data flow:

```text
Token Harness Ledger
.tailtrail/token-harness-events.jsonl
        |
        v
Harness Review / Shared Summary
tailtrail-meta/harness-summary.jsonl
        |
        v
Meta-Harness Analyze
.tailtrail/meta-harness-analysis.json
        |
        v
Meta-Harness Proposal
.tailtrail/meta-harness-proposals.jsonl
```

Shared summary token fields:

```json
{
  "token_strategy": "json-structure-summary",
  "token_exactness_class": "structure-exact",
  "token_evidence_label": "local-evidence",
  "token_reduction_band": "medium",
  "token_proof_label": "measured",
  "token_quality_outcome": "pass",
  "token_holdout": false,
  "token_confidence_gate": "passed"
}
```

Shared metadata privacy rules:

- Keep fields categorical only.
- Do not store:
  - raw prompt
  - raw source
  - raw logs
  - raw scanner payload
  - file paths
  - repo names
  - branch names
  - user identity
  - private URLs
  - secrets
  - pricing/cost fields

Reduction bands:

| Band | Meaning |
|---|---|
| `none` | 0% reduction |
| `low` | 1-20% reduction |
| `medium` | 21-60% reduction |
| `high` | 61%+ reduction |
| `unknown` | no safe reduction evidence |

Harness Review integration:

- `harness-review.py` should read:
  - `.tailtrail/token-harness-events.jsonl`
  - `.tailtrail/token-usage.jsonl`
  - optional proof report when present
- Shared summaries should include only categorical token fields.
- Exact token counts can stay in local reports, but shared summaries should use reduction bands.

Example shared event:

```json
{
  "schema_version": "1",
  "event_type": "tailtrail-harness-summary",
  "task_type": "bug-fix",
  "workflow_selected": ["navigator", "token-harness", "review"],
  "validation_fit": "strong",
  "token_strategy": "scanner-focused-summary",
  "token_exactness_class": "structure-exact",
  "token_evidence_label": "local-evidence",
  "token_reduction_band": "high",
  "token_quality_outcome": "pass",
  "token_confidence_gate": "not-measured",
  "privacy": "sanitized categorical metadata only"
}
```

Meta-Harness analysis findings:

1. `token-strategy-quality-risk`

- Trigger: one token strategy repeatedly appears with weak validation or failed quality.
- Example:

```text
scanner-focused-summary appeared 8 times.
4 events had weak validation or quality failure.
Recommendation: tighten scanner reducer preservation rules or require exact scanner excerpts for high-severity findings.
```

2. `token-proof-gap`

- Trigger: many events stay `local-evidence` and never reach `measured`.
- Example:

```text
18 local-evidence events, 0 measured records.
Recommendation: improve telemetry import docs or add a clearer post-task proof command.
```

3. `token-reduction-too-low`

- Trigger: reducers run but reduction band is repeatedly `none` or `low`.
- Example:

```text
json-structure-summary produced low/no reduction in 6 events.
Recommendation: tune reducer thresholds or skip reducer for small JSON.
```

4. `token-holdout-gap`

- Trigger: no holdout/control data exists for eligible non-sensitive task classes.
- Example:

```text
No holdout records found for eligible bug-fix tasks.
Recommendation: enable deterministic holdout in proof workflow for measured evidence.
```

5. `token-exactness-mismatch`

- Trigger: risky reduction strategy appears with exact content.
- Example:

```text
must-be-exact content paired with reduction strategy.
Recommendation: strengthen exactness gate tests and Navigator guidance.
```

Proposal change types:

```text
token-router
token-reducer
token-proof-gate
navigator-token-routing
token-docs
```

Proposal file mapping:

```json
{
  "token-router": [
    "scripts/token-harness.py",
    "tests/test_token_harness.py"
  ],
  "token-reducer": [
    "scripts/token-harness-reduce.py",
    "tests/test_token_harness_reduce.py"
  ],
  "token-proof-gate": [
    "scripts/token-harness-proof.py",
    "tests/test_token_harness_proof.py"
  ],
  "navigator-token-routing": [
    "scripts/navigator.py",
    "scripts/navigator_core.py",
    "tests/test_navigator_core.py"
  ],
  "token-docs": [
    "TOKEN-HARNESS.md",
    "USER-GUIDE.md",
    "TAILTRAIL-COMMANDS.md"
  ]
}
```

Proposal requirements:

- finding ID
- affected feature IDs
- evidence label
- likely files
- recommended prompt changes
- test commands
- rollback instruction
- explicit warning: review before editing; do not apply automatically

Command usage:

```bash
python3 scripts/tailtrail.py harness review --root . --write-result
python3 scripts/tailtrail.py harness shared-summary --root . --write-result --approved
python3 scripts/tailtrail.py harness analyze --summary tailtrail-meta/harness-summary.jsonl
python3 scripts/tailtrail.py harness propose --root .
python3 scripts/tailtrail.py harness proposal-status --root .
```

No new end-user command is required. TH-6 improves existing Meta-Harness behavior.

Example analysis output:

```text
Finding: token-strategy-quality-risk
Severity: high
Evidence: scanner-focused-summary appeared in 9 events; 4 had weak validation.
Recommended change type: token-reducer
Likely files:
- scripts/token-harness-reduce.py
- tests/test_token_harness_reduce.py

Recommendation:
Preserve high-severity scanner excerpts exactly and add a regression test for rule ID, file, line, severity, and remediation.
```

Testing plan:

- shared summary allows sanitized token fields
- shared summary rejects unsafe token fields or raw-looking values
- token strategy counts appear in Meta-Harness analysis
- repeated weak validation for one strategy creates `token-strategy-quality-risk`
- many local-evidence records with no measured records creates `token-proof-gap`
- low reduction band creates `token-reduction-too-low`
- sensitive holdout exclusions do not create false holdout gaps
- proposal maps token findings to correct files
- registry validation still passes

TH-6 acceptance criteria:

- Harness shared summaries include sanitized token strategy fields.
- Meta-Harness analysis detects token strategy quality risks.
- Meta-Harness proposals can target router, reducer, proof gate, Navigator token routing, or token docs.
- No raw prompt/source/log/path/user data is stored in shared summaries.
- No automatic TailTrail edits happen.
- Full unit tests, `doctor`, and registry validation pass.

Deferred from TH-6:

- background analyzer
- central upload automation
- automatic product edits
- model-based diagnosis
- vector search
- raw prompt logging
- exact file/path sharing
- pricing/cost analytics
- dashboard

#### TH-7 Implementation Design: Optional Runtime Compression Bridge

Status: implemented.

Goal:

- Add a strict adapter contract for optional external compression.
- Keep TailTrail as the exactness and policy gatekeeper.
- Let teams plug in local external compressors only when policy enables them.
- Reject invalid adapter output and fall back safely.
- Avoid proxy/runtime ownership.

Core flow:

```text
TailTrail selects safe reducible context
        ->
Optional external adapter compresses only that safe portion
        ->
TailTrail validates returned output against exactness rules
        ->
Accept compressed output or fall back to exact original
```

Planned files:

- `scripts/token-harness-bridge.py`: bridge planner, input builder, output validator, and guarded runner.
- `tests/test_token_harness_bridge.py`: deterministic bridge policy, contract, fallback, and failure tests.
- `schemas/token-harness-bridge-input.schema.json`: public input contract for optional adapters.
- `schemas/token-harness-bridge-output.schema.json`: public output contract for optional adapters.
- `scripts/token-harness.py`: add bridge subcommands.
- `scripts/tailtrail.py`: expose bridge commands under the main command surface.
- `scripts/check-tailtrail.py`: validate bridge schemas and disabled-by-default behavior.
- `scripts/install-copilot.py`: install bridge docs/policy examples without enabling the feature.
- `tailtrail-registry.json`: add the Token Harness Bridge feature ID and evidence label.
- `TOKEN-HARNESS.md`: document bridge purpose, safety model, contracts, and examples.
- `TAILTRAIL-COMMANDS.md`: add user-facing command examples.
- `USER-GUIDE.md`: explain when to use the bridge and when not to use it.
- `tailtrail-policy.example.md`: add disabled-by-default policy settings.

CLI design:

```bash
python3 scripts/tailtrail.py token-harness bridge plan --path build.log
python3 scripts/tailtrail.py token-harness bridge input --path build.log --output /tmp/bridge-input.json
python3 scripts/tailtrail.py token-harness bridge validate-output --input /tmp/bridge-input.json --output /tmp/bridge-output.json
python3 scripts/tailtrail.py token-harness bridge run --path build.log --adapter-command "local-compressor --stdin" --approved
```

Policy configuration:

```yaml
## Token Harness Bridge

runtime_compression_bridge: disabled
adapter_command: ""
allowed_content_types:
  - log
  - documentation
  - scanner-output
  - json
max_input_bytes: 250000
require_approval: true
```

Default behavior when disabled:

```text
Bridge status: disabled
Reason: no local policy enabled runtime compression bridge
Fallback: exact pass-through or internal structured reducer
```

Bridge input contract:

```json
{
  "schema_version": "1",
  "type": "tailtrail-token-harness-bridge-input",
  "content_type": "log",
  "exactness_class": "reduce-safe",
  "strategy": "failure-focused-summary",
  "allowed_reductions": ["deduplicate repeated lines", "keep first and last relevant failures"],
  "blocked_reductions": ["drop exit codes", "drop command names", "drop first failure"],
  "preserve": [
    "command boundaries",
    "exit codes",
    "first failure",
    "stack traces",
    "retrieval pointer"
  ],
  "retrieval": {
    "command": "cat build.log"
  },
  "input": {
    "kind": "path",
    "path": "build.log",
    "text": "..."
  }
}
```

V1 bridge scope:

- Include text only for safe content classes and only under policy limits.
- Never send protected source, diffs, manifests, security policy, lock files, secrets, or unknown content to an adapter.
- Keep retrieval pointers so exact evidence can be reloaded when needed.

Bridge output contract:

```json
{
  "schema_version": "1",
  "type": "tailtrail-token-harness-bridge-output",
  "status": "compressed",
  "content_type": "log",
  "exactness_class": "reduce-safe",
  "strategy": "external-compressor",
  "preserved": [
    "command boundaries",
    "exit codes",
    "first failure"
  ],
  "blocked_reductions_honored": true,
  "text": "compressed safe summary",
  "retrieval": {
    "command": "cat build.log"
  },
  "adapter": {
    "name": "local-compressor",
    "version": "local"
  }
}
```

Validation rules:

- Input and output schemas must be valid.
- Output `content_type` must match input `content_type`.
- Output `exactness_class` must match input `exactness_class`.
- Output must list every required preserved field.
- `blocked_reductions_honored` must be `true`.
- Retrieval command must be preserved.
- Unsafe markers must not appear in adapter output.
- Output must not be larger than the original safe context.
- Source, diff, config, security policy, dependency manifest, lock file, secret, unknown, and must-be-exact content must be rejected before adapter invocation.

Failure output:

```text
Bridge output rejected.
Reason: missing required preserved evidence: exit codes
Fallback: exact original or internal structured reducer
```

Allowed bridge content:

- `log`
- `documentation`
- `scanner-output`
- `json`
- `tool-output`

Always blocked bridge content:

- source body
- diff
- config
- security policy
- dependency manifest
- lock files
- secrets
- unknown content
- must-be-exact context

Run behavior:

1. Require `--approved`.
2. Check local policy and confirm bridge is enabled.
3. Route input through TH-1.
4. Reject protected exact content.
5. Build bridge input JSON.
6. Run adapter command with JSON on stdin.
7. Parse adapter JSON output.
8. Validate exactness and preservation.
9. Print accepted output or fallback result.
10. Optionally write receipt/ledger entries only with separate approved flags.

Accepted output example:

```text
# Token Harness Bridge

- Status: accepted
- Adapter: local-compressor
- Content type: log
- Exactness: reduce-safe
- Fallback used: false
- Retrieval: cat build.log

Compressed Output:
...
```

Rejected output example:

```text
# Token Harness Bridge

- Status: rejected
- Reason: adapter output violated exactness contract
- Fallback used: true
- Fallback: exact-pass-through
```

Testing plan:

- Bridge is disabled by default.
- Policy opt-in enables planning.
- Must-be-exact content is blocked.
- Logs produce valid bridge input.
- JSON/tool output preserves structure-exact requirements.
- Adapter output is accepted when the contract is valid.
- Adapter output is rejected when content type changes.
- Adapter output is rejected when preserve fields are missing.
- Adapter output is rejected when blocked reductions are not honored.
- Adapter output is rejected when unsafe markers appear.
- Adapter output is rejected when larger than the original.
- Failed adapter command falls back safely.
- Run requires `--approved`.
- Receipt or ledger writes require explicit approved flags.
- Doctor and registry validation pass.

TH-7 acceptance criteria:

- `token-harness bridge plan` explains whether a path is bridge-eligible.
- `token-harness bridge input` emits deterministic JSON.
- `token-harness bridge validate-output` accepts and rejects correctly.
- `token-harness bridge run` is policy-gated and approval-gated.
- Protected exact content never reaches an adapter.
- Invalid adapter output falls back safely.
- Docs clearly state this is not a proxy and TailTrail does not bundle a compressor.
- Full unit tests, `doctor`, and registry validation pass.

Deferred from TH-7:

- HTTP proxy
- model/API interception
- bundled compressor engine
- background service
- automatic assistant wrapping
- network calls
- credential handling
- central telemetry upload
- pricing/cost analytics

TH-7 principle:

TH-7 should make TailTrail compatible with external compression tools without depending on them or trusting them blindly. TailTrail owns exactness. The adapter only proposes a compressed representation.

Cross-cutting features that ride the staged phases:

- **Feature 8 Output Token Discipline** and **Feature 14 Response Shape Profiles** ship alongside TH-2 because they change Navigator rendering, not ledger schema. They add `compact | standard | detailed | audit` profiles with `audit` sticky per session.
- **Feature 9 Cache-Friendly Context** ships alongside TH-1 as a rendering invariant (stable prefix / shared middle / task-varying tail). `sync-governance.py` and `sync-adapters.py` gain a drift check for byte-identical stable prefixes.
- **Feature 15 Assistant Wrap Adapters** ships alongside TH-2 as a marker-safe preamble injection (`<!-- tailtrail-wrap:start -->` / `<!-- tailtrail-wrap:end -->`). Reuses the marker pattern already validated in `sync-governance.py`. Not a proxy, not a runtime interceptor.

Acceptance check:

- Each TH phase is independently valuable and independently reversible.
- The exactness gate blocks compression of source, diffs, configs, security rules, dependency versions, commands, IDs, and hashes by default.
- Every reduced context block carries a receipt with a retrieval pointer.
- The ledger survives parallel Navigator, benchmark, and harness runs without torn writes.
- No public report labels a value `measured` unless the holdout confidence gate passes.
- Value reports quantify TailTrail-side token discipline (assistant output shaping) separately from assistant-side reductions.
- One command wraps a supported assistant preamble; wrap and unwrap are idempotent and preserve user content outside the markers.
- TH-7 adapter output that violates its declared exactness class is rejected and TailTrail falls back to the exact original.

Boundaries:

- No default proxy, no automatic agent wrapping through the adapter, no background service, no central upload, no hidden telemetry.
- No compression of `must-be-exact` content classes.
- No pricing or cost conversion inside the ledger schema for TH-1 through TH-5 (may be added later as a separate module that consumes the ledger, never as a field within it).
- No dependency-heavy ML compression in the core package.
- No public claim of exact savings without measured telemetry passing the Feature 12 confidence gate.

### BL-11: TailTrail Feature Registry

- Problem: TailTrail has grown into a platform with roughly 15 tracked features (Navigator, AIDLC, Guardrails, Review, Testing, Quality/Sonar, Vulnerability, Code Graph, Learning, Meta-Harness, Token Harness, Reporting, Install Surfaces, MCP, Governance). Each feature is described in multiple places: scripts, docs, adapters, tests, CI steps, install manifests, ROADMAP status. There is no single index that answers "what features exist, which commands belong to each, which are Core vs Extended, which are implemented vs planned, which docs describe them, which tests validate them, which MCP tools expose them, which are read-only vs write-capable, which require approval." Without such an index, every new feature multiplies drift risk in 5-7 places and future work (BL-9 MCP, BL-10 Token Harness, BL-8 Core/Extended split) will each invent its own parallel taxonomy.
- Related: `BL-6 Governance Single-Source` (solves the same drift problem for one specific string; BL-11 generalizes it), `BL-8 Core Vs Extended Install Profiles` (registry authors the `surface` field consumed by installers), `BL-9 MCP Guardrail Server` (MCP tool list is a projection of the registry), `BL-10 Token Harness Track` (Token Harness features register themselves and inherit the evidence-label vocabulary from BL-1 and Feature 5).
- Goal: One committed, schema-validated **registry** (not agent) that describes every TailTrail feature, plus a validator that catches drift between what the registry claims and what actually exists on disk. Read-only in V1. Advisory locally, strict in CI. Docs are validated, not generated.
- Implementation priority: BL-11 is the missing **feature inventory and drift-control layer**. Implement it before adding more feature expansion so new features have one required place to declare commands, docs, tests, install surface, MCP exposure, approval rules, and evidence level.

Design source of truth:

- The registry is the runtime-index. `ROADMAP.md` remains the design-time source. Entries in the registry point back at their owning ROADMAP phase or BL number.
- Naming discipline: this is a **registry**, not a control-plane agent. It makes assertions about metadata. It does not make runtime decisions, does not have autonomy, and does not write to the repo except when a maintainer explicitly regenerates it.

Registry entry shape (schema v1):

```json
{
  "id": "guardrails",
  "title": "Guardrail Enforcement",
  "status": "implemented",
  "surface": "core",
  "roadmap_ref": "V3.0 + BL-5 + BL-7",
  "owner": "tailtrail-core",
  "governance_class": "governance",
  "commands": [
    "tailtrail guard check",
    "tailtrail guard check --enforce",
    "tailtrail guard check --fail-on <class>",
    "tailtrail guardrail precision"
  ],
  "docs": [
    "GUARDRAILS.md",
    "TAILTRAIL-COMMANDS.md"
  ],
  "scripts": [
    "scripts/guardrail-check.py",
    "scripts/guardrail-precision.py"
  ],
  "tests": [
    "tests/test_guardrail_check.py",
    "tests/test_guardrail_precision.py"
  ],
  "mcp_tools": ["guardrail_check"],
  "requires_approval": false,
  "read_only": true,
  "evidence_label": "local-evidence",
  "depends_on": ["governance"],
  "since_version": "v0.8",
  "deprecated_in_version": null
}
```

Required fields per entry (enforced by `tailtrail-registry.schema.json`):

- `id` — kebab-case, unique, matches folder/script naming.
- `title` — human-readable.
- `status` — enum: `planned | implemented | deprecated`.
- `surface` — enum: `core | extended` (matches BL-8).
- `roadmap_ref` — the ROADMAP.md phase or `BL-N` that owns this feature.
- `commands` — every user-facing command; each must be dispatched in `scripts/tailtrail.py`.
- `docs` — every doc that describes it; each must exist on disk.
- `scripts` — every script that implements it; each must exist on disk.
- `tests` — every test file that validates it; empty list forbidden for `status: implemented`.
- `mcp_tools` — MCP tool names or `[]`.
- `requires_approval` — bool.
- `read_only` — bool.
- `evidence_label` — enum: `none | estimated | local-evidence | measured | benchmark-measured` (matches Feature 5 in `TOKEN-HARNESS.md`).
- `depends_on` — list of other feature IDs; each must resolve.
- `owner` — free-form string; defaults to `tailtrail-core`.
- `governance_class` — enum: `governance | product | dev-experience | benchmark | telemetry`.
- `since_version` — string; TailTrail version where the feature landed.
- `deprecated_in_version` — string or null.

Flow of implementation:

```text
[ 1 committed source ]     tailtrail-registry.json  +  tailtrail-registry.schema.json

[ CLI, read-only V1 ]      scripts/tailtrail-registry.py
                            list      -> print all features (compact)
                            show <id> -> print one feature (full JSON or markdown)
                            validate  -> return drift report
                            validate --strict -> non-zero on any drift
                            workflow <task> -> print features relevant to a task class
                            mcp        -> print MCP-safe tool projection
                            surfaces   -> print core/extended breakdown

[ dispatcher ]             scripts/tailtrail.py  registry <verb>

[ tests ]                  tests/test_tailtrail_registry.py

[ CI enforcement ]         .github/workflows/tailtrail-ci.yml
                            step: `tailtrail registry validate --strict`

[ later consumers ]        BL-8 installer reads `surface` field
                            BL-9 MCP server reads `mcp_tools` + `read_only`
                            BL-10 Token Harness features register themselves
                            Navigator (V2 later) reads workflow projections
```

What `validate` must catch (the drift the registry earns its keep by finding):

- Every listed `scripts/*.py` exists on disk.
- Every listed `docs/*.md` exists.
- Every listed `tests/test_*.py` exists.
- Every listed command is dispatched in `scripts/tailtrail.py`.
- Every command in `scripts/tailtrail.py` `COMMANDS` dict is claimed by at least one registry entry (catches orphan commands).
- Every script under `scripts/` appears in exactly one registry entry (catches orphan scripts).
- Every `depends_on` reference resolves to a known feature ID.
- `surface: core` features only reference other `surface: core` scripts and docs (Core stays self-contained).
- Every `status: implemented` feature has non-empty `tests`.
- No `status: implemented` feature has `evidence_label: none` when its `governance_class` is `benchmark` or `telemetry`.
- No two features share an `id`.
- No two features claim the same script.

Files involved:

- **Add**:
  - `tailtrail-registry.json` — the committed registry (single source of truth).
  - `tailtrail-registry.schema.json` — JSON Schema draft 2020-12; stdlib validation via custom minimal checker (no `jsonschema` dependency).
  - `scripts/tailtrail-registry.py` — read-only CLI with the six verbs above. Stdlib only. Under ~500 lines.
  - `tests/test_tailtrail_registry.py` — schema conformance, drift detection, orphan script detection, orphan command detection, Core self-containment, `depends_on` resolution, ID uniqueness, script uniqueness.

- **Modify**:
  - `scripts/tailtrail.py` — add `registry` command in the `COMMANDS` dict, add `registry` dispatcher routing to `tailtrail-registry.py`, add help examples.
  - `scripts/check-tailtrail.py` — register the three new files and the schema in `EXPECTED_FILES` and the Python syntax-check list.
  - `scripts/install-copilot.py` — add `scripts/tailtrail-registry.py`, `tailtrail-registry.json`, and `tailtrail-registry.schema.json` to `PACK_SCRIPTS` / `PACK_FILES`.
  - `scripts/tailtrail.py` `doctor()` — add the three new files to the installed-pack required list.
  - `.github/workflows/tailtrail-ci.yml` — add a dedicated step `Registry drift check (strict)` running `python3 scripts/tailtrail.py registry validate --strict`. Place it after the existing governance-drift step so registry drift surfaces as its own failure line.
  - `GOVERNANCE.md` — add one paragraph noting that the feature registry is a governance artifact; changes to feature status, surface, or evidence label must be reflected in the registry in the same PR.
  - `CONTRIBUTING.md` — add one paragraph pointing at `tailtrail registry validate` as a mandatory local check before opening a PR.
  - `TAILTRAIL-COMMANDS.md` — add rows for the six new `registry` verbs.
  - `USER-GUIDE.md` — add one paragraph describing the registry as the read-only feature index; not a runtime dependency in V1.
  - `README.md` — add one line under the daily-workflow examples: `python3 scripts/tailtrail.py registry list`.

- **Do NOT modify** (V1 boundaries):
  - Navigator (`scripts/navigator.py`, `scripts/navigator_core.py`, `scripts/navigator_render.py`) — Navigator does NOT depend on the registry in V1. This is the single most important design decision; it ensures the registry can be wrong for a release without breaking Start reports.
  - Meta-Harness scripts.
  - Learning Agent scripts.
  - MCP scripts (BL-9 will consume the registry when it lands; BL-11 does not touch MCP).
  - Efficacy runner (BL-1), Governance sync (BL-6), guardrail-check (BL-5), guardrail-precision (BL-7) — these register themselves in the registry, but their code does not change.

Command surface (V1, read-only only):

```bash
python3 scripts/tailtrail.py registry list
python3 scripts/tailtrail.py registry list --surface core
python3 scripts/tailtrail.py registry list --status implemented
python3 scripts/tailtrail.py registry show guardrails
python3 scripts/tailtrail.py registry show guardrails --format json
python3 scripts/tailtrail.py registry validate
python3 scripts/tailtrail.py registry validate --strict
python3 scripts/tailtrail.py registry workflow review
python3 scripts/tailtrail.py registry mcp
python3 scripts/tailtrail.py registry mcp --format json
python3 scripts/tailtrail.py registry surfaces
```

Staged implementation plan (single phase, small):

1. **Draft the schema** (`tailtrail-registry.schema.json`) with the required fields and enums above. Ship a minimal stdlib validator (~150 lines) — do not add a `jsonschema` dependency.
2. **Populate the initial registry** (`tailtrail-registry.json`) with entries for the ~15 existing features. For each entry: derive `commands` from `scripts/tailtrail.py` COMMANDS dict, derive `scripts` from `EXPECTED_FILES` groupings, derive `docs` from the file list, set `status: implemented` for shipped features and `planned` for BL-3, BL-4, BL-5, BL-7, BL-8, BL-9, BL-10 pieces not yet landed.
3. **Ship the CLI** (`scripts/tailtrail-registry.py`) with the six read-only verbs. Deterministic; stdlib only; no writes.
4. **Wire the dispatcher** in `scripts/tailtrail.py` and add help examples.
5. **Add tests** (`tests/test_tailtrail_registry.py`) covering schema conformance, drift detection, orphan detection (both directions), Core self-containment, `depends_on` resolution, ID uniqueness, script uniqueness.
6. **Wire CI** with a dedicated strict-validate step.
7. **Update docs** (GOVERNANCE, CONTRIBUTING, TAILTRAIL-COMMANDS, USER-GUIDE, README) — narrow, cross-referencing edits only. Do not rewrite any existing content.
8. **Update ROADMAP.md** with `Status: implemented end to end` matching the BL-1 pattern.

Phased implementation plan:

**Phase 11.1: Registry Foundation**

Status: implemented end to end.

- Add `tailtrail-registry.json` as the committed feature inventory.
- Add `tailtrail-registry.schema.json` as the schema contract.
- Add `scripts/tailtrail-registry.py` with read-only commands:
  - `list`
  - `show <id>`
  - `surfaces`
- Add basic tests for:
  - required fields
  - valid enums
  - unique feature IDs
  - duplicate script claims
  - missing listed files
- Purpose: create the source of truth first without wiring every TailTrail surface to it immediately.

**Phase 11.2: Drift Validation**

Status: implemented end to end.

- Add `registry validate`.
- Add `registry validate --strict`.
- Validate:
  - listed scripts exist
  - listed docs exist
  - listed tests exist
  - `depends_on` references resolve
  - implemented features have tests
  - scripts are not claimed by multiple features
  - commands are claimed by at least one feature where practical
  - orphan scripts are reported where practical
- Purpose: make the registry useful as a drift detector, not just a static catalog.

**Phase 11.3: TailTrail Integration**

Status: implemented end to end.

- Add `tailtrail registry ...` dispatcher support in `scripts/tailtrail.py`.
- Add registry files to `scripts/check-tailtrail.py`.
- Add registry files to installer pack manifests.
- Add registry awareness to `tailtrail doctor`.
- Update:
  - `README.md`
  - `USER-GUIDE.md`
  - `TAILTRAIL-COMMANDS.md`
  - `CONTRIBUTING.md`
  - `GOVERNANCE.md`
- Purpose: make the registry a normal TailTrail maintenance and user-facing command surface.

**Phase 11.4: CI Enforcement**

Status: implemented end to end.

- Add a dedicated CI step:
  - `python3 scripts/tailtrail.py registry validate --strict`
- Keep local `validate` advisory by default.
- Make strict mode fail only for actionable drift.
- Purpose: prevent future feature sprawl from silently drifting across commands, docs, tests, installer surfaces, and governance.

**Phase 11.5: Later Consumers**

Status: implemented end to end.

- Defer runtime consumers until the registry proves stable.
- Later candidates in recommended order:
  - Navigator reads workflow projections.
  - MCP server reads `mcp_tools`, `read_only`, and approval metadata.
  - Core/Extended installer derives surfaces directly from registry fields.
  - Token Harness reads evidence labels.
  - Meta-Harness aggregates registry maturity and drift history.
- Purpose: avoid making runtime systems dependent on the registry before the registry has proven reliable.

Meta-Harness and Feature Registry integration:

- Relationship:
  - Feature Registry answers: "What TailTrail features exist, which files/commands/docs/tests own them, and are they drifting?"
  - Meta-Harness answers: "Did TailTrail choose and use the right workflow for real tasks, and what should improve based on evidence?"
  - Registry is declared truth. Meta-Harness is observed truth.
  - Registry is the map. Navigator chooses the route. Meta-Harness reviews whether the route worked.
- Overlap is intentional but bounded:
  - both use feature IDs
  - both use evidence labels
  - both care about command surfaces
  - both care about validation and tests
  - both can point to impacted TailTrail files
  - neither should silently edit TailTrail behavior
- Phase 11.1 through 11.4 boundary:
  - Implement the registry standalone first.
  - Register Meta-Harness itself as a feature entry.
  - Do not make Meta-Harness depend on the registry yet.
  - Do not make Navigator depend on the registry yet.
- Later integration candidates:
  - Meta-Harness proposals reference registry feature IDs in `affected_features`.
  - Meta-Harness proposals use registry ownership to list impacted commands, docs, scripts, tests, and install surface.
  - Registry-aware proposal validation detects when a Meta-Harness proposal names an unknown feature ID.
  - Registry evidence labels become the shared vocabulary for Meta-Harness confidence and Token Harness reporting.
  - Central Meta-Harness aggregation can include registry maturity signals such as missing tests, stale docs, unowned commands, or repeated drift.
- Validation policy:
  - Unknown feature IDs in Meta-Harness proposals are blocking in central maintainer proposal mode.
  - A proposal with an unknown affected feature returns `no_proposal` with registry validation issues.
  - Meta-Harness must not claim `measured` or `benchmark-measured` confidence for an affected feature whose registry entry only supports `estimated` or `local-evidence`.
  - Proposal impact should include direct `affected_features` only by default.
  - Transitive impact through registry `depends_on` should be opt-in through a future `--include-dependents` option to avoid noisy over-reporting.
- Readiness tie-in:
  - Registry-aware proposal validation is implemented in Meta-Harness Readiness Tier 3, central maintainer mode.
  - Developer task mode must not run registry-aware product-improvement validation unless the user explicitly asks for harness or registry analysis.
- Implemented proposal shape:

```json
{
  "finding": "Navigator under-routes Code Graph Mapper for Java Sonar tasks",
  "affected_features": ["navigator", "code-graph-mapper", "quality-signal-scanner"],
  "proposal_evidence_label": "local-evidence",
  "registry_validation": {
    "valid": true,
    "proposal_evidence_label": "local-evidence"
  },
  "recommended_change": "Route Java Sonar prompts to Code Graph Mapper earlier and increase the token budget band."
}
```

- Implemented proposal impact text:

```text
Impacted feature: Code Graph Mapper
Surface: extended
Commands affected:
- tailtrail graph
- tailtrail start
Docs affected:
- USER-GUIDE.md
- TAILTRAIL-COMMANDS.md
Tests affected:
- tests/test_code_graph_mapper.py
```

- Recommended integration sequence:
  1. Implement BL-11 standalone.
  2. Add a registry entry for Meta-Harness with its scripts, commands, docs, tests, surface, and evidence label.
  3. Extend Meta-Harness proposals to reference registry IDs. Implemented.
  4. Add registry-aware proposal validation after BL-11 strict validation is stable. Implemented.
  5. Let Navigator and MCP consume registry projections only after registry drift checks are reliable in CI. Implemented for existing projections.
- Non-goals for the first integration:
  - no god-agent that manages every TailTrail feature
  - no automatic source edits from Meta-Harness
  - no runtime dependency from Navigator to registry in BL-11 V1
  - no generated docs from registry metadata
  - no central aggregation of raw prompts, source, paths, repo names, scanner raw output, or user identity

Acceptance check:

- `python3 scripts/tailtrail.py registry list` prints every known feature with `id`, `status`, `surface`, and `commands`.
- `python3 scripts/tailtrail.py registry show <id>` prints one feature (markdown or JSON).
- `python3 scripts/tailtrail.py registry validate --strict` exits non-zero when someone adds a new script to `scripts/` without registering it, without touching `scripts/check-tailtrail.py`. This is the golden acceptance test — if this does not hold, the registry is decorative and should not be built.
- `python3 scripts/tailtrail.py registry validate --strict` exits non-zero when a listed script/doc/test does not exist, when a `depends_on` reference is unresolved, when a Core feature references an Extended script, when a `status: implemented` feature has empty `tests`, or when two features claim the same script.
- Advisory default (no `--strict`) always exits 0 with a drift report.
- Every registry entry validates against `tailtrail-registry.schema.json`.
- CI runs the strict validate step and reports drift as its own named failure line.
- Registry-aware Meta-Harness validation is implemented: a proposal with `affected_features: ["unknown-feature"]` returns `no_proposal` with registry validation issues.
- Later proposal impact validation has a placeholder acceptance check: direct affected features are listed by default, while dependents are listed only with a future `--include-dependents` option.
- `check-tailtrail.py`, `sync-adapters.py --check`, `governance check --strict`, `efficacy run --strict`, and `smoke-test.py` all still pass.

Boundaries and non-goals:

- **Registry, not agent.** No runtime autonomy, no auto-classification, no auto-generation of docs.
- **Read-only in V1.** No `registry add`, `registry update`, or `registry remove` verbs. Maintainers edit the JSON directly.
- **Docs are validated, not generated.** The registry validates that TAILTRAIL-COMMANDS.md mentions the commands it should; it does not rewrite the doc. Generated docs lose editorial voice and any regeneration bug silently rewrites human-authored content.
- **Navigator does NOT depend on the registry in V1.** Navigator integration is a later phase (V2), gated on registry stability. In V1, the registry can be wrong without breaking Start reports.
- **No per-entry `priority` or `importance` field.** Prioritization belongs in ROADMAP.md where it is contextual. Two sources drift; ROADMAP wins.
- **No new runtime dependency.** Stdlib JSON validation only; no `jsonschema` or `pydantic`.
- **No projection to external systems.** The registry lives in this repo. Central Meta-Harness aggregation of registry data is a separate future phase and requires the sanitization pattern already used for `harness-summary.jsonl`.
- **Governance wording is unchanged by BL-11.** BL-6 owns the governance block; BL-11 references it.

### BL-11.6: Registry Drift And Release Hygiene Gate

- Problem: TailTrail now has a broad feature surface. The Feature Registry helps, but drift risk remains unless registry, command docs, roadmap status, tests, install manifests, and changelog updates are enforced as part of the normal release gate.
- Related: `BL-11 TailTrail Feature Registry`, `BL-6 Governance Single-Source`, `BL-5 Guardrail Enforcement`, `BL-10 Token Harness Track`, `CHANGELOG.md`, `VERSIONING.md`, `scripts/check-tailtrail.py`.
- Goal: make feature drift visible and actionable before merge or release, so TailTrail does not rely on maintainers remembering every file to update.

Status: planned.

Design principle:

- Registry remains the declared feature inventory.
- Drift checks compare declared truth against implemented truth.
- Reports recommend fixes but do not rewrite files automatically.
- Changelog and roadmap stay human-authored; the tool validates freshness and obvious contradictions.
- All checks stay deterministic and stdlib-only.

Command design:

```bash
python3 scripts/tailtrail.py registry drift
python3 scripts/tailtrail.py registry drift --strict
python3 scripts/tailtrail.py registry drift --since HEAD~1
python3 scripts/tailtrail.py registry drift --format json
```

Planned files:

- `scripts/registry-drift.py`: deterministic drift report and strict gate.
- `tests/test_registry_drift.py`: focused tests for missing docs, missing changelog, command drift, and stale roadmap wording.
- `tailtrail-registry.json`: add any needed metadata only if the current schema cannot express ownership clearly.
- `tailtrail-registry.schema.json`: update only if new required fields are introduced.
- `scripts/tailtrail.py`: expose `registry drift`.
- `scripts/check-tailtrail.py`: run strict drift checks or a safe subset.
- `CONTRIBUTING.md`: add Feature Change Checklist.
- `CHANGELOG.md`: add or maintain `Unreleased` section.
- `TAILTRAIL-COMMANDS.md`: document the drift command.
- `USER-GUIDE.md`: explain when maintainers should run drift checks.

Drift checks:

1. **Registry completeness**
   - every registered script exists
   - every registered doc exists
   - every registered test exists
   - every registered dependency reference resolves
   - every implemented feature has docs and validation surface

2. **Command surface drift**
   - commands in `scripts/tailtrail.py` are represented in `tailtrail-registry.json`
   - registry commands are mentioned in `TAILTRAIL-COMMANDS.md` or intentionally marked internal/admin
   - user-facing docs do not advertise removed or internal-only command paths

3. **Roadmap status drift**
   - registry `implemented` features should not have nearby roadmap wording saying "not implemented yet"
   - roadmap `implemented` sections should not conflict with registry `planned`
   - remaining/deferred sections should be explicitly marked as future candidates when the base feature is implemented

4. **Changelog freshness**
   - feature-impacting file changes require a `CHANGELOG.md` update in the same change set
   - feature-impacting paths include:
     - `scripts/`
     - `skills/`
     - `benchmarks/`
     - `tailtrail-registry.json`
     - `tailtrail-registry.schema.json`
     - `ROADMAP.md`
     - public user docs
     - adapter docs
   - docs-only typo fixes may be allowed through an explicit `--allow-doc-only` flag or a lightweight ignore marker later if needed

5. **Install and package drift**
   - scripts and docs added to the registry must be included in install-pack surfaces when appropriate
   - installed-pack manifests should not include tests unless intentionally configured
   - source-only files should not leak into internal/public export modes incorrectly

6. **Claim boundary drift**
   - public docs must not introduce unsupported claims such as guaranteed savings, exact ROI without measured telemetry, scanner replacement, or automatic policy enforcement
   - public claims should use evidence labels: estimated, local-evidence, mixed, measured, benchmark-measured, observed, advisory

Example output:

```text
# TailTrail Registry Drift Report

Status: failed

Issues:
- Feature `token-harness` lists command `tailtrail token-harness bridge run`, but `TAILTRAIL-COMMANDS.md` does not mention it.
- `scripts/token-harness-bridge.py` changed, but `CHANGELOG.md` has no `Unreleased` entry.
- `ROADMAP.md` says a registered command is not implemented, but the registry lists it as implemented.

Recommended fixes:
- Add bridge command examples to `TAILTRAIL-COMMANDS.md`.
- Add an `Unreleased` changelog entry.
- Update the stale V2.1 roadmap wording.
```

Strict behavior:

- Default mode prints a report and exits 0 for local maintenance visibility.
- `--strict` exits non-zero for actionable drift.
- `check-tailtrail.py` should run the strict subset once false positives are low.
- CI should run `registry drift --strict` after the feature has passed a false-positive baseline period.

Feature Change Checklist:

Add to `CONTRIBUTING.md`:

```text
For every feature change, check:
- registry entry updated
- command help updated
- TAILTRAIL-COMMANDS.md updated
- USER-GUIDE.md or feature doc updated
- ROADMAP status updated
- CHANGELOG.md Unreleased entry added
- tests added or updated
- install/check-tailtrail inventory updated
- public claim boundaries preserved
```

Implementation plan:

1. Implement `scripts/registry-drift.py` with pure stdlib parsing and conservative checks.
2. Add `tailtrail.py registry drift` dispatcher.
3. Add JSON and Markdown output.
4. Add tests for:
   - missing command documentation
   - missing changelog update for changed feature files
   - stale roadmap "not implemented yet" wording for implemented registry feature
   - missing registered doc/script/test
   - public claim boundary issue
5. Add `CHANGELOG.md` `Unreleased` discipline if it is missing or stale.
6. Add Feature Change Checklist to `CONTRIBUTING.md`.
7. Add docs to `TAILTRAIL-COMMANDS.md` and `USER-GUIDE.md`.
8. Add advisory drift command to `check-tailtrail.py`.
9. After at least one release cycle with low false positives, promote the strict subset into CI.

Acceptance criteria:

- `python3 scripts/tailtrail.py registry drift` prints a useful drift report.
- `python3 scripts/tailtrail.py registry drift --strict` fails on known test fixtures for command/doc/changelog/roadmap drift.
- A feature script change without a changelog entry is flagged.
- A command added to `tailtrail.py` but missing from registry or command docs is flagged.
- Stale roadmap wording is detected for implemented registry features.
- Public claim drift is detected using the existing public-claim guardrail vocabulary.
- `python3 scripts/check-tailtrail.py`, `python3 scripts/tailtrail.py registry validate`, and full tests still pass.

Boundaries:

- No automatic changelog generation in the first version.
- No automatic ROADMAP edits.
- No model calls.
- No network calls.
- No background watcher.
- No hidden telemetry.
- No generated docs replacing human-authored docs.

Expected impact:

- Raises TailTrail maintainability from roughly `7.7/10` toward `8.5/10`.
- Makes the broad feature surface safer to maintain.
- Reduces release mistakes after rapid BL/TH feature work.
- Gives contributors one obvious maintenance path for every feature change.

## Evaluation Harness Consolidation Track

Status: design only. Detailed plan is in `EVALUATION-HARNESS.md`.

Purpose: consolidate TailTrail's evidence-related systems under one umbrella instead of letting benchmark, efficacy, outcome telemetry, quality loop, Meta-Harness, Token Harness proof, guardrail precision, value reporting, and demo evidence feel like separate products.

Product thesis:

```text
TailTrail guides AI coding work. Evaluation Harness proves whether that guidance helped.
```

Planned consolidation:

- Benchmark Harness -> `eval scenario ...`
- Measured Efficacy Evidence -> `eval portfolio ...`
- Guardrail Precision -> `eval guardrails ...`
- Outcome Telemetry -> `eval outcome ...`
- Quality Loop -> `eval workflow ...`
- Meta-Harness -> `eval meta ...`
- Token Harness proof/telemetry/savings -> `eval tokens ...`
- Enterprise/value reports -> `eval report ...`
- Build Week demo evidence -> `eval scenario report --scenario buildweek-validation`

Design rules:

- Existing commands stay as compatibility aliases.
- First implementation is a thin router, not a rewrite.
- Shared schema comes after command alias stability.
- Scenario Harness starts deterministic and local; no live model/API calls.
- Optional live-agent evaluation is deferred until deterministic scenario scoring is stable.
- No exact token claims without measured telemetry.
- No automatic TailTrail file edits from Meta-Harness or Evaluation Harness.
- No hidden telemetry, raw prompt logging, background observer, or automatic upload.

Implementation phases:

1. **EH-0 Usage And Overlap Audit**: inventory evidence scripts, mark alias/merge/retire/needs-decision, and block ambiguous aliases before routing. Detailed implementation design lives in `EVALUATION-HARNESS.md` and includes `scripts/evaluation-audit.py`, `tailtrail eval audit`, JSON/Markdown reports, strict-mode blockers, canonical mapping rules, and tests.
2. **EH-1 Umbrella Documentation - Implemented**: documentation/governance phase that makes `EVALUATION-HARNESS.md` the major implementation hub. The hub owns the detailed design, phase order, command migration model, privacy boundaries, claim rules, and acceptance criteria. `ROADMAP.md` stays as the brief executive tracker; `USER-GUIDE.md` explains day-to-day evidence usage; `TAILTRAIL-COMMANDS.md` documents only currently working `eval` commands and marks future commands as pending. No scoring, scenario runner, event schema, telemetry capture, deprecation warning, or behavior migration should be added in EH-1.
3. **EH-2 Command Aliases - Implemented**: added `scripts/evaluation-harness.py` as the thin Evaluation Harness router and delegated `python3 scripts/tailtrail.py eval ...` to existing evidence scripts without rewriting scoring. Supported aliases include portfolio, guardrails, outcome, workflow, meta, tokens, report, and artifact routes; scenario commands stay pending until EH-4. Detailed alias matrix, pending-message rules, compatibility constraints, tests, and validation commands live in `EVALUATION-HARNESS.md`.
4. **EH-3 Shared Evaluation Event Schema - Implemented**: added the common Evaluation Harness event contract, `schemas/evaluation-harness-event.schema.json`, `templates/evaluation-result.md`, and approval-gated local JSONL output at `.tailtrail/evaluation/events.jsonl`. `eval normalize` and `eval validate-events` are available without scenario scoring, hidden telemetry, raw prompt/source/log storage, uploads, or report migration. Detailed schema, privacy rules, source adapters, write modes, tests, and acceptance criteria live in `EVALUATION-HARNESS.md`.
5. **EH-4 Scenario Harness V1 - Implemented**: deterministic saved-artifact scenario scoring is available through `eval scenario list|run|compare|report`, with committed fixtures under `benchmarks/evaluation/scenarios/`, rubric-backed per-dimension scores, winner/delta comparison, Markdown/JSON reports, claim boundaries, and approval-gated report writes. No live agents, model/API calls, repo modification, scanners, package managers, hidden telemetry, or exact token claims. Detailed scenario layout, scoring rubric, initial scenario set, files, tests, and acceptance criteria live in `EVALUATION-HARNESS.md`.
6. **EH-8 Build Week Demo As Scenario - Implemented**: add a formal `buildweek-validation` scenario under `benchmarks/evaluation/scenarios/` so the Build Week demo has repeatable fixture-backed proof through `eval scenario report --scenario buildweek-validation`. The live `buildweek-demo-project/` remains human-readable and independent; the scenario reads only committed sanitized artifacts and uses the existing EH-4 deterministic scorer. Planned files include `scenario.json`, `baseline-artifact.md`, `tailtrail-artifact.md`, `expected.json`, and a scenario README. Navigator should route Build Week/demo/proof prompts to this scenario, and MCP can use existing read-only `eval_scenario_list` and `eval_scenario_report` tools. No live agents, model/API calls, scanner/test/build execution, raw prompt/source/log capture, automatic report writes, or exact token-saving claims are included. Detailed implementation design, scoring dimensions, tests, acceptance criteria, and non-goals live in `EVALUATION-HARNESS.md`.
7. **EH-5 Portfolio Consolidation**: migrate efficacy portfolio into the umbrella report model.
8. **EH-7 Token Evidence Integration**: consume Token Harness proof, receipts, ledger, and measured telemetry.
9. **EH-6 Meta-Harness Integration**: Meta-Harness consumes normalized Evaluation Harness evidence and produces registry-aware proposals.
10. **EH-9 Optional Live-Agent Mode**: deferred to a separate RFC/design doc; explicit-approval isolated Codex/Claude runs only after deterministic scoring is stable.

Success criteria:

- users see one evidence umbrella instead of many disconnected reporting tools
- old commands still work
- `eval ...` provides a coherent command family
- scenario reports compare baseline vs TailTrail variants
- portfolio reports summarize outcome quality across task classes
- Meta-Harness proposals use Evaluation Harness evidence
- token claims remain evidence-labeled
- Build Week and enterprise demos can show one clean proof story

### Backlog Non-Goals

- No hidden telemetry, background service, or automatic scanner execution introduced by any backlog item.
- No exact token-savings claims without measured provider usage (BL-1 preserves estimate-vs-measured labeling; BL-10 Feature 12 adds the holdout confidence gate).
- No package-manager publication before source-only and local-install feedback (BL-3).
- No enforced guardrail blocking by default; enforcement is opt-in (BL-5).
- No governance meaning changes during single-sourcing (BL-6).
- No HTTP proxy or runtime API interception introduced by BL-10 (TH-7 is an adapter contract only; Feature 15 is preamble injection only).
- No pricing / cost fields inside the Token Harness ledger schema for TH-1 through TH-5 (BL-10).
- No runtime autonomy, no doc auto-generation, and no Navigator dependency introduced by BL-11 (registry is read-only V1; consumers integrate in later phases).

### Suggested Sequencing Rationale

- BL-1 and BL-6 come first because they are high-trust, comparatively low-cost, and directly raise credibility (evidence and consistency).
- BL-11 slots at position 3 because it is cheap (static JSON + validator, roughly one day of implementation) and retroactively raises the value of every prior and subsequent BL by giving them a shared home. BL-2 (surface consolidation) becomes trivial to keep clean if the registry enforces the invariant. BL-3 (packaging) benefits because `pyproject.toml` metadata can be validated against the registry. BL-8 (core/extended) becomes purely mechanical: `resolve()` reads the registry's `surface` field. BL-9 (MCP) becomes a projection of the registry, not a parallel taxonomy. BL-10 (Token Harness) features register themselves and inherit the evidence-label vocabulary.
- BL-2 and BL-3 reduce friction and maintenance drag before adding new surface.
- BL-4 and BL-7 are cheap UX and quality wins that de-risk BL-5.
- BL-10 slots after BL-5/BL-7 because Token Harness proof (Feature 12 holdout gate, Feature 5 evidence labels) reuses the guardrail enforcement and precision baseline from BL-5/BL-7 to keep `measured` claims honest.
- BL-5, BL-8, BL-9, and BL-10 are larger and should follow the precision baseline and consolidation work.
