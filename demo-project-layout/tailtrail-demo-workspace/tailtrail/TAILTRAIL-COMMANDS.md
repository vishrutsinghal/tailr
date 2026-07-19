# TailTrail Commands

Use this file as the daily command catalog. The commands below keep TailTrail usable through one local entry point while preserving the original scripts.

Main entry point:

```bash
python3 scripts/tailtrail.py <command> [args]
```

Installed pack entry point:

```bash
python3 tailtrail/scripts/tailtrail.py <command> [args]
```

## Discovery

```bash
python3 scripts/tailtrail.py help
python3 scripts/tailtrail.py commands
python3 scripts/tailtrail.py hello
python3 scripts/tailtrail.py version
python3 scripts/tailtrail.py start "fix Sonar issue and prepare PR"
python3 scripts/tailtrail.py governance check
```

Use these when a user is new to TailTrail, onboarding a team, or checking whether a project has a source checkout or installed pack.

## Which Command Should I Use?

| User situation | Use command | Prompt alternative | Why |
|---|---|---|---|
| I want to confirm TailTrail is installed and reachable. | `python3 scripts/tailtrail.py hello`, `tailtrail hello`, or `hello tailtrail` | `Hello TailTrail. Confirm this repo can use TailTrail and show the install location.` | Fast smoke check that prints the TailTrail location. |
| I have a real task and do not know which TailTrail feature applies. | `python3 scripts/tailtrail.py start "task"` | `Use TailTrail start for this task: <task>. Show the recommended workflow and wait for approval before implementation.` | One-command entry point with workflow selection, next actions, metrics, and full plan. |
| I only want a workflow plan. | `python3 scripts/tailtrail.py guide "task"` | `Run TailTrail Navigator for this task: <task>. Show the plan only; do not implement until I approve.` | Navigator plan without the extra Start report. |
| I know the changed or target file. | `python3 scripts/tailtrail.py graph --changed path/to/file` | `Use TailTrail Code Graph for <path/to/file>. Show likely callers, tests, helpers, and read order before changing code.` | Finds likely callers, tests, helpers, and read order. |
| I have CI, build, test, lint, or Sonar output. | `python3 scripts/tailtrail.py ci summarize --file log.txt` or `python3 scripts/tailtrail.py sonar summarize --file sonar.log` | `Use TailTrail CI/Sonar Intelligence on this pasted output. Summarize exact failures, likely impacted files, and next validation steps.` | Compacts noisy evidence without losing exact failure lines. |
| I want to know which local checks are available. | `python3 scripts/tailtrail.py quality scan --root .` | `Use TailTrail Quality Signal Scanner. Recommend local lint, test, Sonar-like, and vulnerability checks, but do not run anything without approval.` | Recommends checks without running them. |
| I need precise unit or regression test guidance. | `python3 scripts/tailtrail.py test plan --changed path/to/file` | `Use TailTrail Test Precision Planner for <path/to/file>. Give focused test cases in plain English and likely commands.` | Suggests likely test files, cases, helpers, and focused validation commands without running tests. |
| I need to run one approved local check. | `python3 scripts/tailtrail.py quality run --approved --command "..."` | `Run this one approved TailTrail quality command only: <exact command>. Do not run extra scans or builds.` | Runs only one exact allowlisted command. |
| I changed shared governance wording. | `python3 scripts/tailtrail.py governance check` | `Use TailTrail governance check. Verify shared TailTrail behavior text is synchronized and tell me what differs.` | Verifies marked governance blocks match `GOVERNANCE.md`. |
| I want to record whether TailTrail helped. | `python3 scripts/tailtrail.py outcome capture ... --approved` | `Use TailTrail outcome capture for this completed task. Record acceptance, validation result, review result, time-saved band, and learning quality only after I approve.` | Records one compact approved adoption outcome. |
| I cloned a repo that already has TailTrail files. | `python3 scripts/tailtrail.py setup-scan --root .` | `Use TailTrail setup scan for this repo. Classify shared TailTrail files, local runtime state, overrides, and safe next setup steps.` | Classifies shared project context versus local user state. |
## Governance Sync

```bash
python3 scripts/tailtrail.py governance check
python3 scripts/tailtrail.py governance sync
python3 scripts/sync-governance.py check
python3 scripts/sync-governance.py sync
```

Use this when changing repeated TailTrail behavior text in `AGENTS.md`, adapter files, or `context/guardrail-layers.md`.

`GOVERNANCE.md` owns the short repeated governance block between `<!-- tailtrail-governance:start -->` and `<!-- tailtrail-governance:end -->`. `GUARDRAILS.md` remains the full behavior contract. The sync command rewrites only marked blocks, so normal prose around those blocks stays human-edited.

Run `governance check` before committing documentation or adapter changes. Run `governance sync` after editing `GOVERNANCE.md`, then run `python3 scripts/sync-adapters.py --write` so tool-facing adapter files match their sources.

## Installation Smoke Check

```bash
python3 scripts/tailtrail.py hello
tailtrail hello
```

Use this after install, update, clone, or launcher setup. It is read-only and fast. It confirms the command resolved, prints whether TailTrail is running as a source checkout or installed pack, and points to `doctor` for full validation.

## Setup Scan

```bash
python3 scripts/tailtrail.py setup-scan --root .
python3 scripts/tailtrail.py setup-scan --root . --format json
python3 scripts/tailtrail.py setup-scan --root . --tracked-only
```

Use this immediately after cloning a repo that already contains TailTrail files, or before installing/updating TailTrail in a team repo.

`setup-scan` is read-only. It classifies TailTrail-related files into:

- shared project context
- project overrides
- team review files
- installed TailTrail pack
- local runtime state
- generated-but-shareable metadata
- unknown TailTrail-like files

It also reports missing `.gitignore` patterns, installed-pack status, warnings, and safe next commands such as policy check, setup JSON review, install dry-run, or update dry-run.

Default guidance:

- Preserve `tailtrail-policy.md`, `.tailtrail/policy-overrides.json`, AIDLC docs, and curated learnings.
- Do not commit runtime state, local telemetry, quality/vulnerability run output, task starts, or local install manifests.
- Update installed packs only after a dry run and explicit review.
- Review generated graph/cache metadata before sharing it.

## Start

```bash
python3 scripts/tailtrail.py start "fix Sonar issue and prepare PR"
python3 scripts/tailtrail.py start "fix Sonar issue" --changed src/service/foo.py
python3 scripts/tailtrail.py start "triage GHSA in package.json" --changed package.json --format json
```

Use `start` as the preferred first command for non-trivial work. It runs Navigator, then adds a compact task report with:

- a Start Here section with the immediate next step
- a Decision Menu with review, approve, edit, focused validation, scan approval, learning approval, and leaner-workflow prompts when relevant
- Navigator-first workflow selection
- selected and skipped TailTrail features
- likely impacted file count
- approximate token posture from focused files versus intentionally avoided broad docs
- guarded learning quality posture
- install/update posture and the recommended dry-run update check
- the full approval-first Navigator plan

The token posture is a local estimate from file character counts. It is useful for demos and planning, but it is not exact model/API token usage. Learning quality is advisory only; surfaced learnings still require `use learnings`, `ignore learnings`, or `edit plan`.

Common examples:

```bash
python3 scripts/tailtrail.py start "fix null pointer in claim mapper" --changed src/main/java/com/acme/claims/ClaimMapper.java
python3 scripts/tailtrail.py start "fix Sonar cognitive complexity issue" --changed src/main/java/com/acme/payment/PaymentValidator.java
python3 scripts/tailtrail.py start "add retry handling for payment capture"
python3 scripts/tailtrail.py start "add a CSV parsing library for import files"
python3 scripts/tailtrail.py start "triage GHSA vulnerability in package.json" --changed package.json
```

## Navigator

```bash
python3 scripts/tailtrail.py guide "fix Sonar issue and prepare PR"
python3 scripts/tailtrail.py guide "add payment retry handling" --changed src/payment/retry.py
python3 scripts/navigator.py "review auth middleware" --changed src/auth/middleware.py --format json
```

Use `guide` when the user knows the goal but not the right TailTrail sequence. Navigator recommends selected features, skipped features, likely impacted files, load/avoid guidance, suggested commands, and an implementation plan.

Navigator is advisory and approval-first. It does not edit files or run implementation. Review the plan, edit it if needed, then approve implementation.

Navigator includes a `Token Budget` section for implementation-like work. The budget is a context-planning estimate, not a hard stop and not exact model/API token telemetry. If the task needs more context than estimated, the assistant should pause, explain why, and ask for budget escalation before loading more.

For read-only discovery prompts, Navigator uses a compact `Repo Overview / Discovery` plan:

```bash
python3 scripts/tailtrail.py guide "tell me important features of this repo"
```

This mode avoids AIDLC, Review, Handoff, scanners, learning capture, tests, builds, and file edits by default. It asks approval before inspecting the target repo and answering the overview question.

For repo overview, Navigator does not create `.tailtrail/code-graph-cache.json` by itself. It shows Code Graph Mapper as optional deeper discovery. Approve and run the suggested `graph map --root /path/to/project` command when you want a reusable module, symbol, endpoint, test, config, and read-order cache.

For meaningful code-change prompts, Navigator selects Code Graph Mapper before broad reads:

- missing cache: approve `graph map --root "/path/to/project"` when graph context would help
- stale cache: approve `graph refresh --root "/path/to/project" --changed path/to/file`
- fresh cache: use the cached read order, then inspect exact source before editing

Tiny typo and docs-only prompts skip graph mapping so TailTrail does not add more process than the task needs.

When the goal asks for a full code scan, Sonar check, quality-gate precheck, vulnerability scan, dependency audit, or similar scanner work, Navigator adds a `Scan Approval` section. The default is `no`; approve only one listed command or replace it with the exact repo-approved command.

When Navigator surfaces graph-aware learnings, choose one of these before implementation:

- `use learnings`: use them as advisory repo patterns after current source and evidence are inspected
- `ignore learnings`: do not use them for this task
- `edit plan`: keep or remove specific learning IDs before implementation

Learning skip reasons are explicit: `no index`, `tiny task`, `stale graph`, or `no matching tags/files/rules`. Learnings are advisory only and never override source, CI, scanners, policy, guardrails, or explicit user instructions.

Navigator may also show a post-task capture suggestion:

```bash
python3 "/path/to/tailtrail/hooks/learning-capture-hook.py" "Fixed Sonar validator complexity" --root "/path/to/project" --candidate "Extract named guard methods while preserving validation order." --acceptance accepted --validation-outcome pass
```

Navigator includes this as a post-task trigger for meaningful work, but it should not be run automatically. Add `--approved` only when the user intentionally wants to record the learning after acceptance, reviewer feedback, or validation evidence.

```bash
python3 scripts/tailtrail.py guide "run a full code scan for Sonar and vulnerability issues before PR"
```

Navigator also distinguishes related heavy-work routes:

- `CI/Sonar Intelligence`: pipeline, Sonar, lint, test, static-analysis, and quality-gate evidence.
- `Security And Vulnerability Intelligence`: CVE, GHSA, SAST, secret, container, audit, and vulnerability evidence.
- `Code Graph Mapper`: graph-cache status for meaningful code changes and heavy reads, reported as fresh, stale, missing, or invalid.

The graph cache section is advisory. It can reduce repeated source discovery, but exact source files still need to be read before edits.

## Token Budget Coach

```bash
python3 scripts/tailtrail.py budget estimate "fix validation bug" --changed src/service/foo.py
python3 scripts/tailtrail.py budget record --task-type bug --initial-budget 8000 --actual-context 10500 --outcome underestimated --escalated yes --approved
python3 scripts/tailtrail.py budget profile
python3 scripts/tailtrail.py profile review
python3 scripts/tailtrail.py receipt capture --task "fix validation bug" --profile review --loaded src/service/foo.py --avoided ROADMAP.md --approved
python3 scripts/tailtrail.py receipt summary
python3 scripts/tailtrail.py savings import --source usage.jsonl --output .tailtrail/token-usage.jsonl
```

Use Token Budget Coach when you want better local context-budget estimates over time. It learns from approved budget outcome events, not from raw prompts or source code.

What it records:

- task type
- language tags
- changed file count
- graph cache status
- initial budget
- actual context used
- whether escalation was needed
- controlled reason text

What it does not record:

- raw prompts
- source snippets
- logs
- secrets
- PII, PHI, or customer data
- exact model/API usage

Budget escalation example:

```text
Initial budget: 8k
Actual need: 13k
Reason: graph cache missing and tests are outside the source package
Next similar estimate: closer to 11k-12k
```

Claim boundary: this improves planning estimates. Exact token savings still require measured usage telemetry through `savings report`.

Related token evidence features:

- `profile`: shows compact prompt compression profiles such as `lean`, `review`, `testing`, `aidlc`, `security`, and `handoff`.
- `receipt capture`: records approved loaded/avoided context with approximate local counts.
- `receipt summary`: summarizes local context receipts.
- `savings import`: normalizes measured model/API usage records before `savings report`.

Navigator uses these ideas directly: it shows the selected compression profile, recommends graph-first reads, avoids raw learning history, and asks for budget escalation when the initial budget is too low.

## Cross-Repo Reference

```bash
python3 scripts/tailtrail.py reference --target /path/to/service-a --reference /path/to/service-b --goal "match validation style"
python3 scripts/tailtrail.py reference --target /path/to/service-a --reference /path/to/service-b --format json
python3 scripts/tailtrail.py reference --target /path/to/service-a --reference /path/to/service-b --goal "reuse API error handling convention" --write-summary /path/to/service-a/.tailtrail/reference-context/service-b.md
```

Use this when you are editing one repo but want another repo used only as a pattern reference. The command validates the target/reference roles, reports whether each path looks like a repo, summarizes lightweight language and manifest signals, and prints read/write boundaries.

Navigator selects this mode when the prompt mentions target/reference repos, sibling repos, other repos, or matching another service's pattern. It should remind the user that only the target repo is editable.

Good prompt:

```text
Use TailTrail cross-repo reference.
Target: /path/to/service-a
Reference: /path/to/service-b
Goal: implement the same validation style.
Only edit service-a.
```

Reference repos are not source to copy from. Use them for conventions, validation shape, tests, architecture intent, config patterns, and naming. If repeated reference reads are likely, use the suggested `graph map --root <reference> --cache <target>/.tailtrail/reference-graphs/<name>.json` command so compact metadata stays with the target workflow.

## Guardrail Enforcement Lite

```bash
python3 scripts/tailtrail.py guard check
python3 scripts/tailtrail.py guard check --enforce
python3 scripts/tailtrail.py guard check --diff changes.patch --format json
python3 scripts/tailtrail.py guard check --commit-message commit-message.txt
python3 scripts/tailtrail.py guard check --pr-body pr-body.md
```

Use before committing or before sharing PR text when you want deterministic checks for the highest-value TailTrail guardrails. Advisory mode is the default and exits successfully. `--enforce` blocks only high-severity findings.

The first implementation checks dependency manifest additions without Dependency Gate evidence, suspicious safeguard removals, validation claims without evidence in supplied commit/PR text, and staged local TailTrail runtime state. It is not a full code review, policy service, SAST scanner, dependency scanner, or test runner.

## Impact Graph

```bash
python3 scripts/tailtrail.py graph --changed src/service/foo.py
python3 scripts/tailtrail.py graph --changed src/service/foo.py --format json
```

Use before implementation, review, CI/Sonar fixes, shared-helper changes, or handoff. It delegates to Code Review Graph Lite and returns likely tests, callers, shared helpers, nearby manifests, risk tags, and suggested read order.

## Scanner Graph Overlay

```bash
python3 scripts/tailtrail.py graph overlay --sonar sonar.log --changed src/service/foo.py
python3 scripts/tailtrail.py graph overlay --vulnerability audit.log --changed package.json
python3 scripts/tailtrail.py graph overlay --vulnerability codeql.sarif
python3 scripts/tailtrail.py graph overlay --vulnerability trivy.json --changed package.json
python3 scripts/tailtrail.py graph overlay --vulnerability grype.json --format json
python3 scripts/tailtrail.py graph overlay --sonar sonar.log --vulnerability audit.log --format json
python3 scripts/tailtrail.py graph overlay --sonar sonar.log --changed src/service/foo.py --no-ast
```

Use after you have local Sonar/static-analysis output or vulnerability/audit/SAST output and before remediation. The overlay auto-detects SARIF, Trivy JSON, and Grype JSON for vulnerability inputs, then connects exact scanner evidence to TailTrail graph impact metadata: affected files, scopes, severities, Sonar rule IDs, CVE/GHSA/CWE IDs, package components, likely tests, related files, AST V1 symbols for impacted source files, and useful follow-up graph commands.

This command does not run Sonar, vulnerability scanners, tests, builds, network calls, or fixes. It reads provided report files plus local metadata only. Use `--no-ast` when you want the cheapest file-level overlay without AST V1 enrichment.

## Code Graph Mapper

```bash
python3 scripts/tailtrail.py graph map --changed src/service/foo.py
python3 scripts/tailtrail.py graph status --changed src/service/foo.py
python3 scripts/tailtrail.py graph refresh --changed src/service/foo.py
python3 scripts/tailtrail.py graph map --changed src/service/foo.py --scanner-evidence sonar.log --format json
```

Use `graph map` before heavy Sonar, vulnerability, QA, dependency, review, release, or handoff work when the same source areas may be reread across a session. It writes `.tailtrail/code-graph-cache.json` with compact metadata only: file hashes, language profiles, symbols, references, call-chain hints, type hierarchy hints, endpoint hints, DB table hints, config usage hints, workspace overlays, likely tests/callers, suggested read order, monorepo partitions, service dependency hints, endpoint-to-service-to-table flows, CODEOWNERS ownership, and release path hints.

Use `graph status` when Navigator says a cache exists and you need to know whether it is fresh, stale, missing, or invalid. Use `graph refresh` when watched files changed. The mapper supports Python, Java, .NET/C#, SQL, and Terraform with explainable local heuristics and Python `ast` when available. It does not store source snippets, run scanners, query CI, run release commands, use a graph/vector database, or replace exact source inspection before edits.

## AST Maps

```bash
python3 scripts/tailtrail.py graph ast --changed src/service/foo.py --depth lite
python3 scripts/tailtrail.py graph ast --changed src/service/foo.py --depth v1
python3 scripts/tailtrail.py graph ast --changed src/service/foo.py --depth v1 --format json
python3 scripts/tailtrail.py graph ast --changed src/service/foo.py --depth v2
python3 scripts/tailtrail.py graph ast --changed src/service/foo.py --depth v2 --format json
```

Use `graph ast` when file-level impact is not precise enough and you need a dependency-free structured map before editing.

- `--depth lite`: reports structured symbols for selected files. Python uses `ast`; Java, .NET/C#, SQL, and Terraform use explainable local parsing heuristics.
- `--depth v1`: adds symbol references, call hints, type hierarchy hints, endpoint hints, DB/config hints, likely tests, and changed-symbol impact.
- `--depth v2`: adds local semantic edges, import/module edges, endpoint-to-handler links, data-flow-lite hints, test coverage hints, and provider readiness for language-server, SCIP, Roslyn, and tree-sitter paths.

Boundaries:

- AST maps are metadata, not correctness proof.
- They do not store source snippets.
- They do not run code, tests, scanners, model calls, network calls, vector search, language servers, Roslyn, SCIP ingestion, tree-sitter parsers, MCP, or background services.
- Exact current source, tests, CI, scanner evidence, policy, and guardrails still win.

## CI/Sonar Intelligence

```bash
python3 scripts/tailtrail.py ci summarize --file ci.log
python3 scripts/tailtrail.py ci summarize --file build.log --format json
python3 scripts/tailtrail.py sonar summarize --file sonar.log
python3 scripts/tailtrail.py sonar summarize --file sonar.log --format json
python3 scripts/tailtrail.py validation summarize --ci ci.log --sonar sonar.log
```

Use these when a user pastes or points to CI, build, test, lint, Sonar, static-analysis, or quality-gate output. The summarizers preserve exact failure lines, commands, paths, rule IDs, severities, and affected files when detected. They do not poll CI, query SonarQube/SonarCloud, run scanners, or claim validation passed.

## Quality Signal Scanner

```bash
python3 scripts/tailtrail.py quality scan --root .
python3 scripts/tailtrail.py quality scan --changed src/service/foo.py
python3 scripts/tailtrail.py quality scan --format json
python3 scripts/tailtrail.py quality run --approved --command "npm run lint"
python3 scripts/tailtrail.py quality run --approved --command "mvn test" --timeout 180
```

Use `quality scan` before PRs, Sonar fixes, lint/test issues, or quality-gate work when the user needs to know which local checks a repo appears to support. It inspects local manifests and recommends commands without running them.

Use `quality run` only after the user approves one exact command. It blocks deploy/publish/destructive/cloud commands, uses a local quality-tool allowlist, saves output under `.tailtrail/quality-runs/`, and returns the exit code. Summarize noisy output with `ci summarize` or `sonar summarize`.

## Test Precision Planner

```bash
python3 scripts/tailtrail.py test plan --root .
python3 scripts/tailtrail.py test plan --changed src/service/foo.py
python3 scripts/tailtrail.py test plan --changed src/service/foo.py --goal "fix validation bug"
python3 scripts/tailtrail.py test plan --changed src/main/java/com/acme/PaymentValidator.java --format json
python3 scripts/tailtrail.py test summarize --changed src/service/foo.py --goal "show implemented test cases"
```

Use `test plan` after or before an implementation when the next question is "what exact test should we add or run?" It detects common Python, Java/Maven, Java/Gradle, Node, .NET, and Go test setups; infers likely test files from changed source paths; lists existing fixtures/helpers to reuse; builds a small regression/happy-path/negative-path/boundary test matrix; and recommends focused validation commands.

Use `test summarize` when the question is "what test cases appear to exist already?" It scans likely existing test files and reports recognizable test functions or blocks with line numbers and assertion hints. It is heuristic, read-only, and does not execute tests or prove coverage.

This command is read-only. It does not write test files, run test commands, start scanners, call models, or claim validation passed. Use `quality run --approved --command "..."` when the user intentionally approves one exact command.

Navigator selects this command when the task mentions unit tests, regression tests, coverage, test cases, post-change validation, validation confidence, or before-PR validation. It appears in `Selected Features` as `Test Precision Planner` with a suggested `test plan --root ... --goal ... --changed ...` command.

Navigator supports `--view full`, `--view compact`, and `--view commands-only` for plan output. Compact and commands-only views are useful for broad Sonar, vulnerability, PR, and test workflows where the full plan is too noisy.

## Quality Loop

```bash
python3 scripts/tailtrail.py quality-loop capture --workflow review,qa --fit correct --outcome accepted --validation-outcome pass --approved
python3 scripts/tailtrail.py quality-loop capture --workflow aidlc,review --fit too-heavy --outcome revised
python3 scripts/tailtrail.py quality-loop summarize --month 2026-07 --write-result
python3 scripts/tailtrail.py quality-loop review --month 2026-07
python3 scripts/tailtrail.py quality-loop propose --month 2026-07
python3 scripts/tailtrail.py quality-loop decide --area navigator --decision "Skip AIDLC for tiny docs-only tasks." --approved
```

Use Quality Loop to review TailTrail behavior, not application behavior. It captures compact approved events, summarizes workflow fit, and proposes reviewable improvements to Navigator rules, guardrails, command help, or local policy.

`capture` requires `--approved` to write `.tailtrail/quality-events.jsonl`. Without approval it prints the event shape and records nothing. Do not include raw prompts, raw logs, secrets, PII, PHI, customer data, or sensitive scanner output.

`summarize` can write `.tailtrail/quality-summary.md`. `propose` shows recommended files that may be impacted and the prompt/rule changes to review. `decide` records an approved, rejected, deferred, or proposed decision in `.tailtrail/quality-decisions.md`.

## Adoption Outcomes

```bash
python3 scripts/tailtrail.py outcome capture --task-type bug-fix --workflow start,review --acceptance accepted --validation-outcome pass --review-outcome approved --defect-escaped no --time-saved 30-60m --fit correct --learning-quality trusted --approved
python3 scripts/tailtrail.py outcome capture --task-type ci-sonar --workflow start,quality,review --acceptance partially-accepted --validation-outcome pass --review-outcome changes-requested --defect-escaped unknown --time-saved 15-30m --fit correct --scan-used --approved
python3 scripts/tailtrail.py outcome summarize --month 2026-07
python3 scripts/tailtrail.py outcome summarize --month 2026-07 --format json
python3 scripts/tailtrail.py outcome summarize --write-result
```

Use Adoption Outcomes after a task is done and the user can say whether TailTrail helped. This is different from Quality Loop:

- Outcome telemetry measures task value: acceptance, validation pass/fail, review outcome, escaped defects, time-saved band, fit, and learning quality.
- Quality Loop measures TailTrail behavior quality and tuning opportunities.

`outcome capture` requires `--approved` before writing `.tailtrail/outcome-events.jsonl`. Without approval it prints the event shape and records nothing.

Privacy boundaries:

- Do not record raw prompts, raw logs, secrets, PII, PHI, customer data, or source snippets.
- Use short task IDs, task types, workflow names, and controlled outcome values.
- Load `.tailtrail/outcome-summary.md` for retrospectives; do not load raw event files into routine coding prompts.

## Enterprise Reporting

```bash
python3 scripts/tailtrail.py report --month 2026-07
python3 scripts/tailtrail.py report value --month 2026-07
python3 scripts/tailtrail.py report value --month 2026-07 --format csv --write-result
python3 scripts/tailtrail.py report --month 2026-07 --include-aidlc --write-result
python3 scripts/tailtrail.py report --start 2026-07-01 --end 2026-07-31 --format json
python3 scripts/tailtrail.py report --token-telemetry .tailtrail/token-usage.jsonl
python3 scripts/tailtrail.py report compare --previous-report june-value.json --current-report july-value.json
python3 scripts/tailtrail.py report trend
python3 scripts/tailtrail.py report aggregate --report-file repo-a-value.json --report-file repo-b-value.json
python3 scripts/tailtrail.py report pr --only quality --only tokens
python3 scripts/tailtrail.py report --only quality
```

Use Enterprise Reporting for local retrospectives, platform improvement, and governance review. It aggregates local TailTrail artifacts such as quality events, learning events, learning refresh actions, curated learning files, optional AIDLC artifact counts, and optional token telemetry.

Use `report value` when you need the compact value surface: dependency gate or avoidance signals, safeguards preserved, validation-truth signals, focused validation signals, diff-size or scope-discipline signals, adoption outcomes, learning hygiene, and token evidence. Use `--format csv --write-result` when a team lead wants a one-row local export for a review deck or spreadsheet.

Use `report compare` only with explicitly supplied JSON reports. It compares local evidence counts and rates between two reports; it does not query a central service.

Use `report trend` for multi-month local trend tables and simple text charts. Use `report aggregate` only with local JSON report files you explicitly provide. Use `report pr` for compact PR-ready Markdown. Use `--only quality`, `--only outcomes`, `--only learning`, or `--only tokens` to keep sections focused.

The report is local and advisory. It does not upload data, poll services, read raw prompts by default, or include secrets, PII, PHI, customer data, or raw logs. Token savings are labeled as measured only when model/API usage telemetry is provided; otherwise TailTrail shows local approximation guardrails.

## Policy Packs

```bash
python3 scripts/tailtrail.py policy init --root .
python3 scripts/tailtrail.py policy init --root . --with-overrides
python3 scripts/tailtrail.py policy check --root .
python3 scripts/tailtrail.py policy check --root . --with-overrides --strict
python3 scripts/policy-check.py check --root . --format json
```

Use Policy Packs when a repo or team needs local rules without editing TailTrail core files. `init` creates `tailtrail-policy.md` from the example and can also create `.tailtrail/policy-overrides.json` from `templates/policy-overrides.json`.

`check` validates required headings and the optional structured override shape. It does not interpret every rule, weaken TailTrail guardrails, or create a hidden central policy engine.

## Security And Vulnerability Intelligence

```bash
python3 scripts/tailtrail.py vulnerability scan --root .
python3 scripts/tailtrail.py vulnerability scan --changed package.json
python3 scripts/tailtrail.py vulnerability run --approved --command "npm audit"
python3 scripts/tailtrail.py vulnerability summarize --file audit.log
python3 scripts/tailtrail.py vulnerability summarize --file codeql.sarif
python3 scripts/tailtrail.py vulnerability summarize --file trivy.json --format json
python3 scripts/tailtrail.py vulnerability summarize --file grype.json --format json
python3 scripts/tailtrail.py vulnerability summarize --file codeql.sarif --root /path/to/project --max-bytes 5000000
```

Use `vulnerability scan` when the user asks what security/vulnerability checks are available. It inspects local manifests and recommends scanner commands without running them.

Use `vulnerability run` only after the user approves one exact scanner command. It blocks destructive/deploy/cloud commands, uses a vulnerability-tool allowlist, saves output under `.tailtrail/vulnerability-runs/`, and returns the real scanner exit code.

Use `vulnerability summarize` to turn scanner output into a structured vulnerability list with exact CVE/GHSA/CWE/rule IDs, severities, components, versions, paths, and first evidence fields when detected. It auto-detects SARIF, Trivy JSON, and Grype JSON before falling back to text parsing. `--root` normalizes absolute affected paths to project-relative paths. Evidence fields are redacted for common secret patterns, and `--max-bytes` caps scanner report reads for very large files.

TailTrail should implement remediation only when the user specifically asks to fix a finding. Dependency findings go through Dependency Gate; secret findings require removal plus rotation/revocation planning.

## Prompt Expansion

```bash
python3 scripts/tailtrail.py intent "use AIDLC and review"
python3 scripts/tailtrail.py expand "use dependency gate"
```

Use when a user wants short TailTrail language but the assistant needs the fuller workflow prompt. It delegates to `expand-intent.py`.

## Token Routing

```bash
python3 scripts/tailtrail.py route review
python3 scripts/tailtrail.py route ci-sonar
python3 scripts/tailtrail.py token "review this diff for dependency risk"
python3 scripts/tailtrail.py savings estimate --used context/slices.md --avoided ROADMAP.md USER-GUIDE.md
python3 scripts/tailtrail.py telemetry manual --task-id demo-001 --provider openai --model gpt-5 --baseline-input 42000 --baseline-output 3000 --tailtrail-input 18000 --tailtrail-output 2500
python3 scripts/tailtrail.py telemetry import-openai --source openai-usage.jsonl --output .tailtrail/token-usage.jsonl
python3 scripts/tailtrail.py telemetry import-claude --source claude-usage.jsonl --output .tailtrail/token-usage.jsonl
python3 scripts/tailtrail.py telemetry import-gemini --source gemini-usage.jsonl --output .tailtrail/token-usage.jsonl
python3 scripts/tailtrail.py savings report --telemetry .tailtrail/token-usage.jsonl
python3 scripts/tailtrail.py savings report --telemetry templates/token-usage-example.jsonl
```

Use `route` when the task type is known. Use `token` when TailTrail should decide whether token routing is worth the cost. These commands help avoid loading broad docs when one slice is enough.

Use `savings estimate` after a task or demo to calculate approximate context reduction from files that were used versus files intentionally avoided. It uses a local character-count approximation and must be described as estimated savings only.

Use `telemetry manual` when you already have before/after usage numbers from your provider UI, logs, gateway, or benchmark notes. It writes one normalized `.tailtrail/token-usage.jsonl` record and does not call any API.

Use `telemetry import-openai`, `telemetry import-claude`, `telemetry import-gemini`, or `telemetry import-generic` when you have a local JSON/JSONL export. The importers are conservative: each row must include both a baseline/before usage block and a TailTrail/after usage block. A single raw API response is not enough to calculate token savings.

Use `savings report` only when you have normalized model/API usage telemetry. TailTrail can call savings measured only for records that include real baseline and TailTrail token totals.

Measured telemetry schema:

```json
{
  "mode": "measured",
  "schema_version": "1",
  "timestamp": "2026-07-13T00:00:00+00:00",
  "task_id": "sonar-fix-123",
  "provider": "your-provider",
  "model": "your-model",
  "source": "usage_metadata",
  "baseline": {"input_tokens": 64000, "output_tokens": 11000, "total_tokens": 75000},
  "tailtrail": {"input_tokens": 15000, "output_tokens": 3500, "total_tokens": 18500}
}
```

How telemetry improves token results:

- Estimated mode uses local character counts, so it can only approximate context size.
- Measured mode uses provider/model usage metadata, so it reflects the actual billed or reported token counts for the recorded task.
- The report shows `Before TailTrail`, `With TailTrail`, `Difference`, and `% Reduction`.
- Example-only sample: `75,000` before versus `18,500` with TailTrail means `56,500` fewer tokens, a `75.33%` reduction for that sample record. Real results vary by task, model, prompt style, and whether telemetry was captured consistently.

Never claim exact ROI from `savings estimate`. Exact token savings require `savings report` with real telemetry from the user's model/API usage metadata.

No API runner is implemented yet. TailTrail does not collect tokens from model providers automatically, does not store API keys, and does not make network calls for token telemetry.

## AIDLC

```bash
python3 scripts/tailtrail.py aidlc init --root . --depth standard
python3 scripts/tailtrail.py aidlc check --root .
python3 scripts/tailtrail.py aidlc check --root . --strict-answers
```

Use AIDLC for broad, risky, ambiguous, regulated, multi-team, or long-running work. Do not use it for tiny clear edits unless the user asks.

## Benchmark And Analyzer

```bash
python3 scripts/tailtrail.py benchmark
python3 scripts/tailtrail.py benchmark --format json
python3 scripts/tailtrail.py benchmark efficacy
python3 scripts/tailtrail.py benchmark efficacy --format json
python3 scripts/tailtrail.py analyze benchmarks/results/latest.json
```

Use benchmark commands to gather local evidence. Use `benchmark efficacy` for committed baseline-vs-TailTrail artifact comparisons with measured/estimated evidence labels. Use analyzer commands to interpret misses, discrepancies, proposed file changes, and recommended prompt improvements.

## Engine Helpers

```bash
python3 scripts/tailtrail.py engine summarize-output --file build.log
python3 scripts/tailtrail.py engine summarize-output --file scanner.log --format json
python3 scripts/tailtrail.py engine slice-context --file src/service/foo.py --query validate
python3 scripts/tailtrail.py engine slice-context --file README.md
python3 scripts/tailtrail.py engine cache-summary
python3 scripts/tailtrail.py engine cache-summary --cache .tailtrail/code-graph-cache.json --format json
python3 scripts/tailtrail.py engine prune-context --file noisy-context.md
python3 scripts/tailtrail.py engine prune-context --file noisy-context.md --drop generated --include-text
```

Use these when the user has evidence that is too noisy for normal prompting:

- `summarize-output`: compact generic logs or command output when the output type is unknown.
- `slice-context`: extract small file windows around matching terms, headings, functions, or classes.
- `cache-summary`: summarize `.tailtrail/code-graph-cache.json` without loading the whole cache.
- `prune-context`: estimate and remove lines matching explicit noisy terms from a local context file.

Boundaries:

- These helpers do not edit source files.
- They do not run scanners, tests, builds, model calls, vector search, MCP adapters, or background services.
- Token counts are approximate character-count estimates, not exact model/API token usage.
- Exact source, logs, CI, scanner evidence, and validation still win over summaries.

## Setup And Updates

```bash
python3 scripts/tailtrail.py install local --inspect
python3 scripts/tailtrail.py install launcher --dry-run
python3 scripts/tailtrail.py install launcher
python3 scripts/tailtrail.py install copilot --root /path/to/project --with-tailtrail-pack
python3 scripts/tailtrail.py update --root /path/to/project --dry-run
python3 scripts/tailtrail.py team-init --root /path/to/project --mode optional
```

Use these for onboarding a repo, installing a managed TailTrail pack, refreshing an existing pack, adding team guidance, or creating a `tailtrail` command that works from any repo.

The launcher writes small executables, usually under `~/.local/bin/tailtrail` and `~/.local/bin/hello`, that point back to this TailTrail checkout. After installation, run from any project:

```bash
hello tailtrail
tailtrail hello
tailtrail guide "tell me important features of this repo"
tailtrail start "fix Sonar issue and prepare PR" --changed path/to/file
tailtrail reference --target /path/to/service-a --reference /path/to/service-b --goal "match validation style"
```

The `hello` alias handles `hello tailtrail`, `hello TailTrail`, and the common typo `hello taitrail`, then delegates to `tailtrail hello`. If the launcher was installed before the alias existed, rerun `python3 scripts/tailtrail.py install launcher --force`.

If the installer says the bin directory is not on `PATH`, add that directory to your shell profile or run the launcher by full path.

## Learnings

```bash
python3 scripts/tailtrail.py learn init --root .
python3 scripts/tailtrail.py learn add --root . --section validation "Run focused test before merge."
python3 scripts/tailtrail.py learn show --root .
python3 scripts/tailtrail.py learn agent init --root .
python3 scripts/tailtrail.py learn capture --root . --type sonar --tags sonar,java --summary "Fixed validator complexity" --candidate "Extract named guard methods while preserving validation order." --validation-outcome pass --acceptance accepted --small-focused-change --no-new-dependency
python3 scripts/tailtrail.py learn search --root . --tags sonar,java --limit 3
python3 scripts/tailtrail.py learn promote --root . --event-id 20260712-abc12345
python3 scripts/tailtrail.py learn summarize --root . --month 2026-07
python3 scripts/tailtrail.py learn review --root .
python3 scripts/tailtrail.py learn review --root . --write-result
python3 scripts/tailtrail.py learn govern --root .
python3 scripts/tailtrail.py learn graph link --root . --learning-id 20260712-abc12345 --file src/main/java/PaymentValidator.java --symbols PaymentValidator.validate --rules Sonar:S3776
python3 scripts/tailtrail.py learn graph search --root . --changed src/main/java/PaymentValidator.java --tags sonar,java
python3 scripts/tailtrail.py learn graph validate --root .
python3 scripts/tailtrail.py learn refresh recommend --root .
python3 scripts/tailtrail.py learn refresh stale --root . --days 90
python3 scripts/tailtrail.py learn refresh apply --root . --learning-id 20260712-abc12345 --action mark-stale --approved
python3 hooks/learning-capture-hook.py "Fixed Sonar validator complexity" --candidate "Extract named guard methods while preserving validation order."
python3 hooks/learning-capture-hook.py "Fixed Sonar validator complexity" --candidate "Extract named guard methods while preserving validation order." --approved
```

Use simple `init/add/show` for manual durable project facts. Use Learning Agent V2 commands for scored events, confidence-gated promotion, and token-safe retrieval. Do not load raw history by default.

Use `learn review` or `learn govern` before broad reuse, monthly hygiene checks, or after TailTrail gives weak learning suggestions. It reports weak notes, rejected patterns, missing validation, guardrail risks, low-confidence overrides, duplicates, richer contradictions, stale-pattern conflicts, and blocking refresh actions. It does not edit learning files.

Use `learn graph ...` when a prior learning should apply only to a specific file, symbol, rule, endpoint, table, manifest, or graph scope.

Use `learn refresh ...` to inspect stale, weak, duplicate, sensitive, or harmful learnings. Refresh reports are advisory; `apply --approved` records an explicit refresh action without rewriting raw learning history.

Use `learning-capture-hook.py` only in post-task or post-approval flows. Without `--approved`, it suggests the exact capture command but does not write a learning event.

For rejected or revised solutions, capture only explicit feedback. Prefer using Navigator's suggested hook command with `--acceptance rejected` or `--acceptance revised` and a clear `--reason`; do not automate rejection/revision learning capture until the refresh and quality loop have reviewed the UX.

## Doctor

```bash
python3 scripts/tailtrail.py doctor
```

Use doctor before releases, after edits, or after installing TailTrail into a project. It runs the package self-check and adapter sync check.

## Design Boundaries

- Existing scripts still work.
- No global install is required.
- No background service runs.
- No workflow executes automatically.
- No files are edited by `guide`.
- Navigator uses this command surface for suggested commands.
