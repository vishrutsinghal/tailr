# TailTrail Design Plan

TailTrail is a compact local development helper for Codex, Claude, Cursor, GitHub Copilot, ChatGPT, and Gemini. Its purpose is to guide coding agents toward changes that are small, grounded in the existing project, easy to review, and careful with important safeguards.

## Current Design

V1.6 contains two Codex skills:

- `@tailtrail` for implementation, bug fixing, refactoring, and dependency choices.
- `@tailtrail-review` for reviewing diffs and proposed code before they land.

The main skill supports three prompt-selected modes: `steady`, `lean`, and `strict`. There is no persisted mode state. The package stays small on purpose. It has optional quiet lifecycle hooks and optional local presentation assets, but those assets are not part of the core workflow.

Phase 1 Token Slicer foundation is complete. It gives agents a small context map, named slices, project relevance notes, cache rules, compression boundaries, pruning rules, compact templates, a deterministic Python router CLI, local state files, and optional hook wrappers. Larger extensions such as graph-lite review mapping, output/cache/prune helper scripts, and visual reference compression remain deferred in `ROADMAP.md`.

Phase 1.5 adds Token Autopilot. It makes token saving automatic for hook-capable hosts and instruction-driven for adapter-only hosts. It skips tiny low-risk requests and routes only non-trivial work to Token Router.

Phase 1.6 adds Intent Expansion. It lets users say short phrases such as `use AIDLC`, `use review`, or `use AIDLC and review` while a deterministic Python resolver expands the phrase into the full TailTrail prompt, load list, avoid list, run order, and validation notes. Project and organization teams can override those internal prompts without editing TailTrail source.

Phase 1.7 adds workflow ergonomics inspired by role-based AI development systems while staying TailTrail-small: named flows, review lenses, a general updater entry point, lightweight team initialization, and project learnings. These are Markdown/Python primitives, not daemons or global services.

Phase 2 adds a portable AIDLC pack. Phase 2 V2 hardens it with stage playbooks, handoff rules, security and testing baselines, an initializer script, and a checker script that can be used in company projects without installing dependencies.

Phase 2.6 adds Guardrail Layers in `context/guardrail-layers.md`. It keeps `GUARDRAILS.md` as the canonical behavior contract, then adds compact feature-level reminders for implementation, code consistency, review, QA, dependency, AIDLC, handoff, CI/Sonar, release, and token-saving work. The point is to reduce agent off-drift without creating many overlapping guardrail files or a hidden policy engine.

Phase 3.5 adds Policy Packs. It keeps `tailtrail-policy.md` as plain readable repo policy, adds an optional structured `.tailtrail/policy-overrides.json`, and provides `scripts/policy-check.py` to initialize and validate local policy shape without interpreting every rule or creating a central policy service.

Phase 4 adds a quiet lifecycle hook in `hooks/tailtrail-lifecycle-hook.py`. It reduces repeated prompt typing by expanding short TailTrail commands and combining them with Token Autopilot. It stays opt-in and does not change core skill behavior.

Phase 5 adds a local setup assistant in `scripts/install-local.py`. It gives users one safe entry point for inspection, dry-run setup, generic guidance, Copilot managed packs, AIDLC docs, hook command hints, and full target-project setup. It avoids global writes, network calls, shell profile edits, IDE setting changes, and installer profile sprawl.

Phase 7 adds an offline benchmark harness in `scripts/benchmark-tailtrail.py`. It scores saved baseline and TailTrail artifacts across synthetic scenarios so TailTrail can make limited local claims about review quality, dependency discipline, safeguard preservation, exactness, and scope control without running live models or using private code.

Phase V3.5 adds measured efficacy evidence in `scripts/efficacy-benchmark.py`. It compares committed baseline and TailTrail-guided artifacts for governance signals such as dependency discipline, validation truth, safeguard preservation, diff size, and review finding quality. It can include measured token telemetry when supplied, but it does not call live models or make universal vendor/model claims.

Phase 7.1 adds `scripts/analyze-benchmark.py`. It interprets benchmark JSON as an evidence-driven behavior analyzer: find missed checks, map them to risk themes and likely TailTrail files, identify discrepancies, and recommend improvements without editing TailTrail automatically.

Phase 7.0a adds the light token savings reporter in `scripts/token-savings.py`. It estimates context reduction from local files and can report measured savings from user-provided telemetry, but it refuses exact claims when real model/API usage metadata is missing.

Phase 7.2 adds `scripts/review-graph.py`. It builds a compact Code Review Graph Lite from changed files using imports, file naming conventions, test proximity, text search, and manifest/config proximity. It improves review focus without a full AST engine, vector database, model call, or background service.

Phase 7.5 adds `scripts/tailtrail.py` and `TAILTRAIL-COMMANDS.md`. It gives users one local command surface while keeping existing scripts intact. The wrapper delegates to existing scripts and adds `doctor`.

Phase 8 adds `scripts/navigator.py`, `context/navigator.md`, and `templates/workflow-recommendation.md`. Navigator is the deterministic orchestration layer: it classifies the user goal, detects risk signals and changed files, selects or skips TailTrail features, includes Code Review Graph Lite output when useful, and returns an approval-first plan before implementation. It now also routes CI/Sonar Intelligence, Security And Vulnerability Intelligence, Quality Signal Scanner planning, Code Graph Mapper cache checks, graph-aware learning choices, learning refresh awareness, and post-task learning capture suggestions while keeping execution and capture approval-gated.

Phase 8.5 adds local CI/Sonar Intelligence summarizers in `scripts/ci-summary.py`, `scripts/sonar-summary.py`, and `scripts/validation-summary.py`. They turn provided CI/build/test/lint/Sonar output files into compact exact-safe summaries without polling CI, querying SonarQube/SonarCloud, running scanners, or claiming validation passed.

Phase 8.6 adds Quality Signal Scanner in `scripts/quality-scan.py` and `scripts/quality-run.py`. The scanner recommends repo-owned local quality commands from manifests without running them. The runner executes one exact allowlisted local quality command only with `--approved`, blocks deploy/publish/destructive/cloud commands, saves output under `.tailtrail/quality-runs/`, and returns the real exit code.

Phase 8.7 adds Security And Vulnerability Intelligence in `scripts/vulnerability-scan.py`, `scripts/vulnerability-run.py`, and `scripts/vulnerability-summary.py`. It keeps vulnerability work separate from general Sonar/quality work. The scanner recommends vulnerability tools from repo manifests without running them, the runner executes one exact allowlisted vulnerability command only with `--approved`, and the summarizer returns a structured list of findings with exact CVE/GHSA/rule IDs, severities, components, versions, paths, and evidence lines when detected. TailTrail plans remediation only when the user specifically asks to fix a finding.

Phase 8.8 adds Code Graph Mapper in `scripts/code-graph-mapper.py`. It turns Code Review Graph Lite's review-focus idea into a reusable, freshness-checked graph cache for heavy Sonar, vulnerability, review, QA, dependency, and handoff workflows. It supports Python, Java, .NET/C#, SQL, and Terraform with metadata-only extraction for symbols, references, call-chain hints, type hierarchy, endpoints, DB tables, config usage, workspace overlays, file hashes, likely callers/tests, watched manifests, and suggested read order. It stores compact metadata in `tailtrail-meta/code-graph-cache.json` by default, not source code. Navigator can reuse the cache only when target file hashes, likely caller/test hashes, scanner evidence hashes, task mode, and relevant manifests are still fresh. `.tailtrail/code-graph-cache.json` remains supported as a private legacy/local fallback.

Phase 9.5 adds Quality Loop in `scripts/quality-loop.py`. It captures approved compact TailTrail behavior events, summarizes workflow fit and outcomes, proposes reviewable improvements, and records approved quality decisions. It is a quality loop, not self-healing automation: no raw prompt logging, no automatic TailTrail edits, and no default use in routine coding context.

Phase 9.7 adds Enterprise Reporting in `scripts/tailtrail-report.py`. It generates local advisory reports from Quality Loop events, Learning Agent events, Learning Refresh actions, optional AIDLC artifact counts, and optional token telemetry. Phase V3.8 extends it with `report value`, CSV export, and JSON report comparison so teams can show evidence of governed behavior: dependency gate or avoidance signals, safeguard preservation, validation-truth signals, focused validation, diff-size discipline, adoption outcomes, learning hygiene, and measured token evidence when supplied. It is local-only: no central telemetry, no service polling, no raw prompt inclusion by default, and no exact token-saving claims without measured model/API usage metadata.

Phase 10 adds optional external assets in `assets/`. These are original SVG files for internal demos, README usage, and shareable packaging polish. They are not required by any TailTrail command, skill, hook, adapter, or runtime workflow.

Phase 6 adds multi-assistant adapters. It keeps Codex skills as the richest native integration while adding compact guidance files for Claude, Cursor, GitHub Copilot, ChatGPT, and Gemini.

The Copilot installer writes a generated TailTrail install manifest into the managed pack folder of the target project. That `.tailtrail-install.json` file is not a source file in this repo. The updater uses it to refresh unchanged core files, detect locally edited core files, and either preserve them or back them up before overwrite.

## File Purposes

### `README.md`

The README is the user-facing entry point. It explains what TailTrail is, what files the package provides, and how a developer should invoke the skills in Codex.

It is needed because a local tool should be understandable without reading plugin internals. The README solves onboarding: a teammate can open the repo and learn the basic commands, modes, local usage options, examples, current scope, and validation command in a minute.

### `QUICKSTART.md`

`QUICKSTART.md` is the task-first entry point for new users.

It is needed because users think in tasks, not TailTrail phases. The file solves first-run clarity: it points most work to `python3 scripts/tailtrail.py start "goal"` and gives short workflows for bugs, Sonar issues, vulnerabilities, and pre-commit guardrail checks.

### `CHEATSHEET.md`

`CHEATSHEET.md` is the one-page problem-to-command map.

It is needed because daily users should not search the full guide or command catalog for common workflows. The file solves recall: it maps common situations to one command and keeps advanced features discoverable without making them the first thing a user sees.

### `USEFUL-PROMPTS.md`

`USEFUL-PROMPTS.md` is the copyable end-user prompt cookbook.

It is needed because many users interact with TailTrail through assistant prompts rather than direct commands. The file solves practical prompting: it gives ready-to-use prompts for Start, Guide, AIDLC, Review, Dependency Gate, Code Graph Mapper, CI/Sonar, vulnerability work, quality checks, cross-repo reference, learning, metrics, handoff, guardrails, governance, and combined workflows, including likely output shapes for complex cases.

### `AGENTS.md`

`AGENTS.md` is portable project guidance for coding agents that read repository instructions. It gives the core TailTrail workflow without requiring a plugin install.

It is needed because not every local project will load Codex plugin skills. The file solves portability: teams can copy one small guidance file into a project and still get the main behavior of reading first, reusing existing patterns, avoiding unnecessary dependencies, and preserving safeguards.

### Adapter Files

TailTrail includes tool-facing adapter files:

- `CLAUDE.md`
- `.cursor/rules/tailtrail.mdc`
- `.github/copilot-instructions.md`
- `.openai/chatgpt-instructions.md`
- `GEMINI.md`

It is needed because teams use different coding assistants. The adapter files solve compatibility while keeping the canonical TailTrail docs unchanged.

### `assets/`

The assets folder contains optional original SVG presentation assets.

It is needed only for discoverability and internal distribution polish. The folder solves lightweight visual identity for README pages, demos, internal catalog entries, and slide decks without affecting TailTrail behavior. Assets must stay optional, small, original, and out of routine coding context.

### `adapters/`

This folder contains the source text for each tool adapter.

It is needed because tool-facing files live in different locations. The folder solves drift control: edit adapter source once, then sync target files.

### `AIDLC.md`

`AIDLC.md` defines TailTrail's portable AI Development Lifecycle. It covers phases, adaptive depth, artifact locations, question files, approval gates, resume rules, handoff rules, dependency policy, and when to keep the lifecycle lightweight.

It is needed because large company work needs continuity and approval discipline. The file solves lifecycle structure: teams can handle broad or risky work without relying on chat memory or a heavy installed workflow engine.

### `aidlc/stages/`

This folder contains concise stage playbooks for workspace detection, reverse engineering, requirements, workflow planning, design, implementation, build/test, handoff, and operations.

It is needed because a single lifecycle map is not enough for day-to-day org usage. The folder solves stage execution: agents can load only the active stage and still follow a solid process.

### `aidlc/extensions/`

This folder contains opt-in security and testing baselines.

It is needed because some work has risk that should not depend on memory or taste. The folder solves repeatable safety checks without forcing every small edit through a large checklist.

### `DEPENDENCY-GATE.md`

`DEPENDENCY-GATE.md` defines the decision process before adding, upgrading, replacing, or introducing dependencies.

It is needed because dependencies create ownership, security, licensing, supply-chain, runtime, and upgrade obligations. The file solves dependency discipline: prefer existing capabilities first and require explicit approval when a new package is truly justified.

### `GUARDRAILS.md`

`GUARDRAILS.md` defines TailTrail's agent behavior contract for evidence, uncertainty, dependencies, scope, safeguard preservation, destructive actions, validation truth, exactness, token saving, AIDLC escalation, and review.

It is needed because enterprise agent workflows can fail through unsupported confidence, false validation claims, unsafe edits, or over-aggressive context summarization. The file solves trust boundaries: agents know what they must inspect, preserve, disclose, and never claim without evidence.

### `GOVERNANCE.md`

`GOVERNANCE.md` owns the short repeated governance block that is copied into `AGENTS.md`, adapter sources, and `context/guardrail-layers.md`.

It is needed because repeated rule text drifts when each assistant surface is edited by hand. The file solves single-source alignment: `GUARDRAILS.md` stays the full behavior contract, while `GOVERNANCE.md` keeps the compact cross-surface reminder synchronized through explicit markers.

### `context/guardrail-layers.md`

`context/guardrail-layers.md` defines task-specific guardrail layers for implementation, code consistency, review, QA, dependency, AIDLC, handoff, CI/Sonar, release, and token saving.

It is needed because broad guardrails can miss ground-level checks, while separate guardrail files for every feature would make TailTrail noisy. The code consistency layer makes agents compare nearby naming, structure, validation, error handling, logging, tests, and formatting before inventing a local style. The file solves layered discipline: route-aware tools and assistants can load only the relevant layer while still treating `GUARDRAILS.md` as the source behavior contract.

### `tailtrail-policy.example.md`

`tailtrail-policy.example.md` is a copyable local policy template for project-specific commands, dependency rules, validation expectations, security requirements, ownership, restricted folders, CI/Sonar expectations, and release notes.

It is needed because each repository may have rules that TailTrail core should not hard-code. The file solves local adaptation: teams can create `tailtrail-policy.md` in a target project without editing TailTrail source or building a hidden policy engine.

### `templates/policy-overrides.json`

This template defines optional structured local policy metadata.

It is needed because some teams want simple machine-checkable values such as validation commands, restricted paths, generated paths, default reviewers, dependency approval requirements, and release expectations. The file solves structured local hints while keeping `tailtrail-policy.md` as the human-readable source of truth.

### `scripts/policy-check.py`

The policy checker initializes and validates local TailTrail policy files.

It is needed because policy files can drift or miss important sections. The script solves lightweight reviewability: it can create `tailtrail-policy.md`, optionally create `.tailtrail/policy-overrides.json`, validate required headings, validate structured override keys, and warn about starter placeholders in strict mode. It does not interpret every rule, enforce a remote policy service, or weaken TailTrail guardrails.

### `NOTICE.md`

`NOTICE.md` records the provenance boundary for the project. It states that the repository contains original internal tooling and does not vendor third-party source code, assets, or documentation.

It is needed because the project is intended for company use. The file solves policy clarity: reviewers can quickly see the stated source boundary without digging through each file.

### `PUBLIC-CLAIMS.md`

`PUBLIC-CLAIMS.md` defines allowed, cautious, and disallowed public claims for TailTrail.

It is needed because the product's credibility depends on not overstating token savings, security coverage, compliance automation, scanner behavior, learning behavior, or review quality. The file solves public positioning: release checks and reviewers have a shared standard for evidence-based wording before open-market demos, docs, or releases.

### `DESIGN.md`

`DESIGN.md` is the design plan for TailTrail itself. It explains the purpose of the tool, why the current files exist, what each Markdown file solves, and how future work should be judged.

It is needed because TailTrail will grow in small steps. The file solves continuity: future changes can be checked against the original design intent instead of adding features just because they are easy to add.

### `ROADMAP.md`

`ROADMAP.md` is the future-scope implementation plan. It describes how to add AIDLC guidance, dependency gates, templates, local policy overrides, lifecycle hooks, installers, adapters, benchmarks, and optional assets without clustering the current package.

It is needed because TailTrail has several useful possible directions, but they should not all land at once. The file solves sequencing: each future feature has a reason, a planned shape, and an acceptance check before implementation starts.

### `HONEST-REVIEW-IMPLEMENTATION-PLAN.md`

`HONEST-REVIEW-IMPLEMENTATION-PLAN.md` turns the outside-in findings from `HONEST-REVIEW.md` into a focused V3 execution plan.

It is needed because broad roadmap notes can bury the highest-leverage product-hardening work. The file solves execution clarity: it separates public claim guardrails, enforcement, Core/Extended packaging, task-first docs, measured efficacy, Navigator maintainability, governance-text drift, reporting maturity, and packaging discipline into implementable phases with acceptance checks and explicit deferrals.

### `TOKEN-SLICER.md`

`TOKEN-SLICER.md` is the planned context-reduction design. It explains how TailTrail should avoid repeated context, full-document loading, noisy command output, and repeated rediscovery of stable project facts.

It is needed because TailTrail will add more Markdown over time. The file solves growth pressure: before adding AIDLC templates, local policies, hooks, or adapters, TailTrail needs a simple method for loading only the relevant slice.

### `TOKEN-AUTOPILOT.md`

`TOKEN-AUTOPILOT.md` defines the automatic decision layer that runs before Token Router.

It is needed because routing every prompt can waste tokens on tiny tasks. The file solves intelligent activation: skip routing when it costs more than it saves, and route only when the prompt is broad, risky, noisy, review-heavy, dependency-sensitive, or lifecycle-related.

### `context/token-router.md`

`context/token-router.md` is the decision layer for token-saving techniques. It defines how an agent chooses between text slicing, context mapping, output slicing, tool summaries, cache reuse, compressed references, and exact text pass-through.

It is needed because a large organization should not apply every optimization everywhere. The file solves routing: each task gets the cheapest safe context strategy while exact code, diffs, configs, and security material stay text.

### `context/flow-catalog.md`

`context/flow-catalog.md` defines named outcomes such as delivery, risk, review, handoff, and release.

It is needed because users should not have to remember which TailTrail features to combine. The file solves workflow ergonomics: a short phrase can choose the right combination of AIDLC, review, validation, and handoff without making TailTrail a heavy process engine.

### `context/review-lenses.md`

`context/review-lenses.md` defines focused review perspectives for architecture, security, QA, maintainability, and dependency risk.

It is needed because generic reviews can become noisy. The file solves review precision: the user can ask for the risk lens that matters and get sharper findings.

### `context/intent-aliases.md`

`context/intent-aliases.md` defines short TailTrail commands and how they map to full workflows.

It is needed because day-to-day users should not paste long prompts to use AIDLC, Review, Dependency Gate, Handoff, or Token Router. The file solves prompt ergonomics: assistants can resolve compact intent phrases consistently and fall back to readable Markdown if the Python resolver is unavailable.

### `context/TailTrail.map.md`

This is the first file to read when TailTrail context could become noisy. It points to the smallest useful slice for implementation, review, AIDLC, examples, design work, and token-saving decisions.

It is needed because the token-saving workflow should not start by loading a long design document. The file solves default routing: one compact map chooses what to read next.

### `context/slices.md`

This file defines named context bundles such as `core`, `review`, `router`, `project-map`, `output`, `cache`, `compression`, `aidlc`, and `examples`.

It is needed because repeated prompts should be able to ask for a slice rather than a folder. The file solves controlled loading: each slice says what to load and what to avoid.

### `context/project-map.md`

This is a compact relevance map for target projects. It records entry points, shared helpers, commands, likely callers, likely tests, generated areas to avoid, and refresh rules.

It is needed because broad source scans are expensive and often unfocused. The file solves source targeting: find the likely path first, then read exact files before editing.

### `context/change-impact.md`

This is a short per-change note for likely files, callers, tests, reused helpers, safeguards, validation, and residual risk.

It is needed because the visible symptom is not always the real boundary. The file solves blast-radius thinking without requiring a long design plan.

### `tailtrail-meta/code-graph-cache.json`

This target-project cache stores compact Code Graph Mapper metadata for files, hashes, likely callers, likely tests, nearby manifests, risk tags, and suggested read order.

It is needed because heavy Sonar, vulnerability, and broad review work can cause agents to reread the same source paths many times. The file solves repeat navigation: Navigator can check whether a previous graph is fresh and reuse it instead of asking the agent to scan the same repo structure again. It records scope, task tags, language profiles, symbols, references, call-chain hints, type hierarchy hints, endpoint hints, DB table hints, config usage hints, workspace overlays, file hashes, watched manifests, optional scanner evidence references, confidence, and stale reasons. It must not store full source code, raw scanner logs, secrets, or long prompts. Teams can review and commit this file when shared repo orientation is useful; `.tailtrail/code-graph-cache.json` remains a private fallback.

### `context/cache-index.md`

This file records stable summaries and their invalidation conditions.

It is needed because large teams rediscover the same project facts repeatedly. The file solves reusable memory while making refresh rules explicit.

### `context/compression-policy.md`

This file defines what may be compressed and what must stay exact text.

It is needed because token reduction can become risky if applied to code, diffs, commands, configs, IDs, or security rules. The file solves exactness boundaries.

### `context/prune-rules.md`

This file defines what context to keep, prune, or archive during long sessions.

It is needed because stale context can be as harmful as missing context. The file solves long-session cleanup.

## Template File Purposes

### `templates/context-brief.md`

This template captures stable project facts in a compact handoff.

It is needed because repeated project discovery should become one reusable brief, not a repeated scan.

### `templates/change-brief.md`

This template captures the request, target outcome, lifecycle depth, relevant files, smallest useful change, safeguards, dependency decision, validation, approval need, and out-of-scope work before non-trivial implementation.

It is needed because larger work should not jump straight from request to code. The file solves pre-change alignment.

### `templates/diff-handoff.md`

This template captures changed files, reused behavior, skipped work, dependency decisions, preserved guardrails, validation, risk, rollback, and approval readiness.

It is needed because reviews and handoffs need compact, consistent evidence. The file solves post-change continuity.

### `templates/validation-handoff.md`

This template captures build, test, lint, typecheck, and other validation evidence.

It is needed because validation output can be noisy. The file solves test handoff by preserving commands, result, first failure, gaps, and next action.

### `templates/operations-notes.md`

This template captures deployment, rollback, migration, monitoring, support owner, risk, and approval notes.

It is needed because production handoff needs different evidence than code review. The file solves operational continuity.

### `templates/requirements.md`, `templates/workflow-plan.md`, `templates/implementation-plan.md`

These templates capture requirements, planning, and approved construction detail.

They are needed because standard and comprehensive AIDLC work should be durable across sessions and reviewers.

### `templates/aidlc-state.md`

This template stores current project, depth, phase, stage, approvals, artifacts, source files, validation status, risks, and next action.

It is needed because long-running work must resume cheaply. The file solves lifecycle memory without loading every artifact.

### `templates/aidlc-audit.md`

This template records durable user requests, decisions, approvals, changed artifacts, reasons, and follow-ups.

It is needed because org-level development needs traceability. The file solves auditability without requiring a database or service.

### `templates/question-file.md`

This template provides file-based questions with answer slots and rules for checking missing, invalid, contradictory, or ambiguous responses.

It is needed because non-trivial ambiguity should not be buried in chat. The file solves structured clarification.

### `templates/stage-gate.md`

This template records approval before moving across lifecycle boundaries.

It is needed because standard and comprehensive work should not drift from requirements into implementation without explicit agreement. The file solves controlled progression.

### `templates/evidence-note.md`

This template captures files read, commands run, checks performed, assumptions, skipped areas, validation gaps, and residual risk.

It is needed because non-trivial work should be reviewable without relying on memory. The file solves evidence transparency for implementation, review, handoff, and later continuation.

### `templates/risk-callout.md`

This template captures risk area, evidence inspected, safeguards to preserve, dependency gate need, validation required, rollback note, recommendation, and approval need.

It is needed because risky work should not be hidden inside ordinary implementation notes. The file solves pre-change and pre-signoff risk visibility.

### `templates/router-decision.md`

This template records why Token Router chose a lane.

It is needed for broad or ambiguous work where teams need a transparent context decision without a long explanation.

### `templates/intent-overrides.json`

This template shows how a project or organization can customize intent expansion.

It is needed because companies may have local delivery checkpoints, validation commands, or wording preferences. The file solves controlled customization: teams can override prompts, load lists, avoid lists, run order, validation, and notes without changing TailTrail source files.

### `templates/learnings.md`

This template stores durable project facts that help future agents avoid rediscovery.

It is needed because repeated project context can waste time and tokens. The file solves lightweight memory without a service: project patterns, validation commands, dependency decisions, common pitfalls, and architecture constraints can be captured in `.tailtrail/learnings.md`.

Learning work remains promotion-based. Raw prompts, full assistant responses, CI logs, and every historical task should not be loaded by default. Learning Agent V2 captures compact scored events, user acceptance, CI/CD fixes, Sonar fixes, and issue history, but only curated reusable learnings should enter normal prompt context.

Future workflow guidance should include TailTrail Navigator: a small deterministic helper that recommends which TailTrail flow, review lens, handoff, token route, review graph, or learning action to use for a given user goal. Navigator should reduce feature-selection burden and should also recommend what to skip for tiny tasks. For broad, risky, or multi-file work, Navigator should return a plan with likely impacted files and ask for user approval before implementation; users should be told they can edit the generated plan before approving it.

### `templates/impact-brief.md`

This template summarizes changed files, callers, tests, reused helpers, guardrails, validation, and risk.

It is needed because code work often needs a compact review handoff after the source has been inspected.

### `templates/tool-summary.md`

This template summarizes noisy terminal, browser, MCP, API, build, test, lint, or log output.

It is needed because raw tool output is often much larger than the few fields needed for the next action.

### `skills/tailtrail/SKILL.md`

This is the primary implementation skill. It tells Codex how to approach coding tasks: inspect the real path first, reuse existing project behavior, prefer built-in capabilities, keep diffs small, and protect important validation and safety behavior.

It is needed because general coding agents can overbuild when requirements are open-ended. The file solves implementation discipline: it gives Codex a repeatable workflow for doing less work without becoming careless. Its modes solve common tradeoffs: normal delivery (`steady`), shortest maintainable path (`lean`), and scope challenge before implementation (`strict`).

### `skills/tailtrail-review/SKILL.md`

This is the focused review skill. It tells Codex how to inspect a diff for unnecessary complexity, avoidable dependencies, duplicate logic, single-use abstractions, over-broad rewrites, weakened safeguards, and missing focused checks.

It is needed because generated or rushed code often needs a second pass before it is safe to merge. The file solves review discipline: it produces concrete findings aimed at reducing ownership burden while preserving correctness.

## Non-Markdown Support Files

### `.codex-plugin/plugin.json`

The plugin manifest makes TailTrail discoverable as a Codex plugin and points Codex at the bundled skills.

It is needed because the skills need metadata, display text, and a component entry point. The file solves plugin packaging.

### `scripts/check-tailtrail.py`

The self-check script validates the lightweight package shape without external dependencies. It checks JSON parsing, expected files, skill frontmatter, naming, and common unfinished placeholders.

It is needed because TailTrail is meant to stay small and policy-friendly. The script solves regression detection: future edits can quickly confirm the package still has the expected simple shape.

### `scripts/sync-governance.py`

The governance sync script checks or rewrites only the marked governance blocks derived from `GOVERNANCE.md`.

It is needed because adapter files and project guidance need the same compact behavior text without turning the whole documentation set into generated output. The script solves governance drift: `check` catches out-of-sync blocks, while `sync` updates the marked blocks and leaves surrounding human-authored prose intact.

### `scripts/efficacy-benchmark.py`

The efficacy benchmark compares committed baseline and TailTrail-guided artifacts for concrete governance outcomes.

It is needed because public and enterprise claims need reproducible evidence. The script solves proof discipline: it scores dependency avoidance, validation evidence, safeguard preservation, diff-size discipline, review quality, and measured token telemetry when supplied while refusing live model calls or universal performance claims.

### `scripts/guardrail-check.py`

The guardrail checker scans a staged diff or provided patch plus optional commit/PR text for high-value TailTrail guardrail issues.

It is needed because guidance alone has no teeth. The script solves local enforcement without a service: advisory mode reports dependency changes without Dependency Gate evidence, suspicious safeguard removals, validation claims without evidence, and staged local TailTrail runtime state; `--enforce` blocks only high-severity findings.

### `scripts/install-local.py`

The local installer is the recommended first setup command for users who are unsure which TailTrail path to choose.

It is needed because TailTrail now has multiple useful entry points: generic guidance, Copilot packs, AIDLC docs, hooks, and full team setup. The script solves setup choice without becoming a global machine installer: it validates the repo, supports a small profile set, previews changes with `--dry-run`, reuses existing scripts, and records what remains deferred.

### `scripts/benchmark-tailtrail.py`

The benchmark harness scores offline artifacts in `benchmarks/scenarios/`.

It is needed because enterprise adoption needs evidence, not vibes. The script solves proof discipline: it compares saved baseline and TailTrail outputs, produces Markdown or JSON scorecards, and keeps claims limited to local repeatable scenarios.

### `scripts/analyze-benchmark.py`

The benchmark analyzer reads JSON from `scripts/benchmark-tailtrail.py` and produces a behavior analysis report.

It is needed because scores alone do not tell a team what to fix. The script solves interpretation: it maps failed checks to themes such as validation truth, dependency discipline, safeguard preservation, exactness, and scope control, then points to likely TailTrail files or scenario gaps for human review.

### `scripts/review-graph.py`

The review graph script generates a compact impact map from changed files.

It is needed because review quality drops when an agent reads only the changed file or scans the whole repo without focus. The script solves review targeting: it suggests likely tests, callers, shared helpers, nearby manifests/config, risk tags, and a read order using simple explainable local signals.

### `scripts/code-graph-mapper.py`

This planned script will create, check, and refresh the Code Graph Mapper cache.

It is needed because Code Review Graph Lite is useful per run, but heavy enterprise workflows need a reusable freshness-aware map. The script should solve cache reuse: generate compact graph metadata, record file hashes and modified times, report whether the cache is fresh, stale, missing, or invalid, and explain what changed. It should support status before write, map creation, and refresh. It must support Python, Java, .NET/C#, SQL, and Terraform using local metadata-only extraction. It should start with language-aware heuristics and only later support optional approved semantic providers such as Roslyn/MCP, language servers, SCIP, or repo-owned indexes. It should stay Python-first and should not introduce a mandatory AST engine, vector database, graph database, background service, or hidden repo crawler.

### `scripts/ci-summary.py`, `scripts/sonar-summary.py`, `scripts/validation-summary.py`

These scripts summarize provided CI/build/test/lint/Sonar output files.

They are needed because pipeline and quality logs are noisy and expensive to paste into an assistant. The scripts solve exact-safe compression: preserve first relevant failures, commands, rule IDs, severities, paths, affected files, and validation truth while removing surrounding noise. They do not connect to CI providers, query SonarQube/SonarCloud, run scanners, or replace source inspection.

### `scripts/quality-scan.py`, `scripts/quality-run.py`

These scripts detect and run local quality checks with approval.

They are needed because users often do not know which validation command a repo owns. `quality-scan.py` solves discovery by inspecting local manifests and labeling commands as safe local, needs approval, or blocked. `quality-run.py` solves controlled execution by requiring `--approved`, blocking unsafe command families, using a quality-tool allowlist, saving output locally, and preserving validation truth through the real exit code.

### `scripts/navigator.py`

The Navigator script recommends the smallest useful TailTrail workflow for a user goal.

It is needed because users should not have to decide manually whether to use AIDLC, Review, Handoff, Dependency Gate, Token Router, Code Review Graph Lite, or project learnings. The script solves orchestration: it uses deterministic rules, changed files, local TailTrail state, and optional Review Graph output to produce selected features, skipped features, likely impacted files, load/avoid lists, commands, and a plan that requires user approval before implementation.

Navigator treats learnings as advisory only. When graph-aware learnings match, it shows dedicated approval choices: `use learnings`, `ignore learnings`, or `edit plan`. When no learning is loaded, it explains the skip reason with short operational labels such as `no index`, `tiny task`, `stale graph`, or `no matching tags/files/rules`. After meaningful work it may show a suggested `hooks/learning-capture-hook.py` command, but it never runs capture automatically. It can also suggest Learning Refresh when Phase 9.2 signals appear, such as stale graph links, low confidence, contradictory guidance, or a user report that TailTrail gave a bad suggestion.

### `scripts/tailtrail.py`

The command surface script gives users one local entry point for common TailTrail actions.

It is needed because the project now has many useful scripts. The wrapper solves discoverability: users can run `help`, `commands`, `guide`, `graph`, `intent`, `route`, `token`, `aidlc`, `benchmark`, `analyze`, `guard`, `governance`, `install`, `update`, `team-init`, `learn`, and `doctor` without memorizing every underlying script name. It delegates rather than duplicating behavior, so existing scripts remain the source of truth. The `guide` command delegates to Navigator.

### `TAILTRAIL-COMMANDS.md`

The command catalog explains the unified commands, when to use them, and what they intentionally do not do.

It is needed because enterprise users need repeatable onboarding. The file solves day-to-day usage clarity and gives future Navigator work a stable command vocabulary.

### `scripts/update-copilot.py`

The updater refreshes an existing GitHub Copilot TailTrail pack.

It is needed because teams will install TailTrail into active projects and then need new TailTrail features later. The script solves upgrade friction: it detects the pack folder, reads the install manifest, updates unchanged managed files, preserves local edits by default, and can backup-overwrite customized core files when a team chooses that path.

### `scripts/update-tailtrail.py`

The general updater is the stable user-facing update entry point.

It is needed because TailTrail will support more adapters over time. The file solves naming and future expansion: users can run one TailTrail update command while the current implementation safely updates the managed pack and Copilot instructions.

### `scripts/team-init.py`

The team initializer writes optional or required TailTrail guidance into a target project.

It is needed because organization adoption needs a repeatable repo setup. The file solves shared usage without a global daemon: optional mode recommends TailTrail, required mode adds a simple pack-exists check, and both keep custom prompts in local override files.

### `scripts/learnings.py`

The learnings script creates, appends, and shows `.tailtrail/learnings.md`.

It is needed because durable project knowledge should not depend on chat memory. The file solves small project memory with plain Markdown.

### `scripts/learning-agent.py`

Learning Agent V2 captures compact learning events, scores confidence, searches token-safe reusable learnings, and promotes only eligible patterns into `.tailtrail/learnings.md`.

It is needed because user acceptance alone can be wrong. The script solves safer memory: objective evidence, validation, review, risk, sensitivity, and stale conditions decide whether a past solution becomes reusable repo knowledge.

### `context/learning-agent.md`

This file defines Learning Agent V2 rules for capture, confidence bands, token-safe retrieval, privacy, and promotion.

It is needed because learning can become noisy or unsafe if raw history enters every prompt. The file solves boundaries: load the index first, retrieve at most three matching learnings, and never treat old memory as stronger than current source, CI, scanner, policy, or guardrail evidence.

### `scripts/graph-learning.py`

The graph-aware learning bridge links Learning Agent V2 events to Code Graph Mapper metadata such as files, symbols, scanner rules, endpoints, tables, manifests, and validation commands.

It is needed because a learning can be valid in one module but wrong elsewhere. The file solves precise retrieval: a prior learning is surfaced only when the current changed files, graph scope, tags, or linked metadata match, and stale or low-confidence links are suppressed.

### `context/graph-aware-learning.md`

This file defines Graph-Aware Learning matching rules, privacy boundaries, retrieval limits, and Navigator behavior.

It is needed because graph facts and learning facts should stay separate. The file solves the boundary: Code Graph Mapper remains a metadata graph, Learning Agent remains curated memory, and the bridge links them without storing source snippets or raw history.

### `scripts/learning-refresh.py`

The learning refresh agent inspects learning events, confidence scores, graph-learning links, policy freshness, duplicates, and approved refresh actions.

It is needed because useful learnings can become stale or harmful when code, tests, policies, scanner rules, or reviewer feedback changes. The script solves controlled cleanup: it recommends actions first and records approved actions without rewriting raw learning history.

### `context/learning-refresh.md`

This file defines refresh triggers, actions, boundaries, and safe-use rules.

It is needed because refresh should reduce noisy retrieval rather than become another memory sink. The file solves the operating contract: advisory by default, explicit approval for changes, and current evidence always wins over old learning.

### `scripts/quality-loop.py`

The quality loop script captures and reviews TailTrail behavior quality signals.

It is needed because TailTrail has many useful workflows that can overlap or drift. The script solves behavior review without self-modification: approved compact events are stored in `.tailtrail/quality-events.jsonl`, summaries can be written to `.tailtrail/quality-summary.md`, and approved decisions can be recorded in `.tailtrail/quality-decisions.md`. It can propose improvements to Navigator, guardrails, command help, learning guidance, or local policy, but it never edits those files automatically.

### `context/quality-loop.md`

This file defines when to use Quality Loop, what it may record, and what it must avoid.

It is needed because behavior monitoring can become unsafe if it captures too much. The file solves boundaries: no raw prompts by default, no secrets or sensitive data, no inference from silence, no automatic capture, and no use of raw quality history in routine coding prompts.

### `scripts/tailtrail-report.py`

The enterprise report script generates a local TailTrail usage and outcome report.

It is needed because teams need evidence before changing TailTrail rules or pitching impact. The script solves reporting without telemetry infrastructure: it aggregates local quality events, learning events, learning refresh actions, optional AIDLC artifact counts, and optional token telemetry. It labels token evidence as measured only when usage metadata exists; otherwise it reports local approximation guardrails.

### `templates/enterprise-report.md`

This template defines the monthly or date-range report shape.

It is needed because enterprise reports can drift into surveillance if the boundary is unclear. The template solves review structure: workflow fit, outcomes, validation, learning signals, dependency discipline, token evidence, review questions, and decision boundaries without raw prompts or sensitive data by default.

### `scripts/expand-intent.py`

The intent expansion script turns short phrases into full TailTrail workflows.

It is needed because short commands are easier to adopt across teams than long prompt blocks. The script solves deterministic command expansion: it recognizes common phrases, prints Markdown or JSON, and applies project or organization overrides from explicit files, environment variables, `.tailtrail/intent-overrides.json`, or `tailtrail/intent-overrides.json`.

### `scripts/route-context.py`

The Token Router CLI returns the smallest safe context route for a task. It supports explicit routes such as `review` and automatic classification from prompt text.

It is needed because manual routing becomes repetitive once multiple teams use TailTrail. The script solves repeatability: the same input type returns the same load, avoid, exactness, reason, and fallback decision without calling an LLM or scanning the whole repo.

### `scripts/token-auto.py`

This script decides whether token routing is useful for a prompt. It returns `skip` for tiny low-risk work and delegates to Token Router for non-trivial work.

It is needed because automatic token saving should not become an automatic token cost. The script solves intelligent routing.

### `scripts/token-savings.py`

The token savings script estimates context reduction from local used and avoided files, or reports measured savings from normalized model/API telemetry JSONL.

It is needed because TailTrail should help teams explain token discipline without making false precision claims. The file solves the evidence boundary: estimated savings use local approximation, while measured savings require real usage metadata.

### `scripts/aidlc-init.py`

This script creates `aidlc-docs/` in a target project from the portable templates.

It is needed because org adoption should not depend on copying files by hand. The script solves consistent lifecycle setup.

### `scripts/aidlc-check.py`

This script validates the minimum shape of `aidlc-docs/` in a target project.

It is needed because lifecycle artifacts can drift or become incomplete. The script solves lightweight compliance checking.

### `scripts/sync-adapters.py`

This script syncs adapter source files into the tool-specific target locations and checks that they match.

It is needed because adapter files are intentionally duplicated into locations that tools can discover. The script solves consistency.

### `.tailtrail/token-router-state.json`

This generated local state file stores the most recent route decision. It is ignored by the package self-check.

It is needed because a long local session may need to know which route was last selected without reloading broad context. The file solves lightweight persistence without creating a background service.

### `hooks/token-router-hook.py`

This optional hook wrapper calls the router CLI and prints a compact context injection for hosts that support prompt or startup hooks.

It is needed because some teams may want the routing decision injected automatically. The hook solves convenience while staying quiet: it injects only the route decision, not full docs, logs, source, or cached state.

### `hooks/tailtrail-lifecycle-hook.py`

This optional hook prints compact lifecycle context for hook-capable hosts.

It is needed because users should not have to paste long prompts for common workflows. The hook solves prompt reduction: it expands short phrases such as `use AIDLC and review`, adds a token autopilot decision, and prints only the selected workflow, load list, avoid list, validation notes, and route.

### `hooks/token-autopilot-hook.py`

This hook calls Token Autopilot before routing.

It is needed because hook-capable hosts should skip tiny requests and route only when useful. The hook solves automatic context discipline.

### `hooks/learning-capture-hook.py`

This optional hook suggests or approved-captures Learning Agent V2 events from compact post-task summaries.

It is needed because teams may want learning capture prompts after meaningful work without logging every prompt. The hook solves convenience while preserving control: it suggests by default, writes only with `--approved`, and skips tiny or non-reusable work.

### `hooks/README.md`

This file explains how to use the optional hook and what not to inject.

It is needed because hook behavior can become noisy if misunderstood. The file solves guardrails for automation.

## Example File Purposes

### `examples/native-date-field.md`

This example shows when to choose a platform-native form control before custom UI or dependencies.

It is needed because UI tasks often invite unnecessary packages. The file solves judgment calibration: use what the platform already provides until the product clearly needs more.

### `examples/stdlib-csv.md`

This example shows when to use standard library parsing for a common data format.

It is needed because agents often rewrite familiar parsers. The file solves implementation restraint: prefer a maintained language feature over custom parsing code.

### `examples/shared-bug-fix.md`

This example shows how to fix a shared formatter or helper instead of patching one caller.

It is needed because bug reports usually describe a visible symptom, not the true source. The file solves root-cause focus: inspect callers and fix the common path when that is smaller and safer.

### `examples/preserve-guard.md`

This example shows that shortening code must not remove trust-boundary validation or safety checks.

It is needed because simplification can become careless if guards are treated as clutter. The file solves safety calibration: remove unnecessary ownership, not necessary protection.

## Growth Rules

- Add a feature only when it helps real local development.
- Prefer one focused skill over a broad command suite.
- Keep wording original and concise.
- Do not add assets, dependencies, hooks, or adapters until there is a concrete workflow that needs them.
- Plan future work in `ROADMAP.md` before adding implementation files.
- Add token-slicing support before expanding large guidance packs.
- Keep `context/TailTrail.map.md` as the default token-saving entry point.
- Keep Token Router scripts deterministic, dependency-free, and easy to remove.
- Keep hooks opt-in and limited to compact route decisions.
- Keep adapter files compact and generated from `adapters/`.
- Preserve the core promise: smaller changes, clearer ownership, and no weakened safeguards.
