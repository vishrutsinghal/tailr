# TailTrail User Guide

This guide shows how to install, use, and maintain TailTrail across Codex, Claude, Cursor, GitHub Copilot, ChatGPT, and Gemini.

For the shortest path, start with `QUICKSTART.md`. For a one-page command map, use `CHEATSHEET.md`. For copyable end-user prompts, use `USEFUL-PROMPTS.md`.

## 1. Get TailTrail

Clone the repository:

```bash
git clone <tailtrail-repository-url>
cd TailTrail
```

Validate the package:

```bash
python3 scripts/sync-adapters.py --check
python3 scripts/install-local.py --inspect
python3 scripts/tailtrail.py help
python3 scripts/tailtrail.py hello
python3 scripts/tailtrail.py doctor
python3 scripts/benchmark-tailtrail.py
python3 scripts/benchmark-tailtrail.py --format json > benchmarks/results/latest.json
python3 scripts/analyze-benchmark.py benchmarks/results/latest.json
python3 scripts/review-graph.py --changed path/to/file
```

TailTrail uses only local Markdown and Python scripts. No package install is required for the portable workflow. For Codex project guidance, run `python3 scripts/tailtrail.py install codex --target /path/to/project --dry-run`, review the plan, then rerun without `--dry-run`. This writes `AGENTS.md` only and preserves an existing file unless `--force` is supplied.

Optional local packaging is available when you want `tailtrail` on `PATH`: run `pipx install .` from the TailTrail checkout, or use `pip install --user .` as an alternative. This installs only a small console-entry shim; the canonical fallback remains `python3 scripts/tailtrail.py ...`, and the source tree still owns the Markdown, adapters, benchmarks, hooks, and scripts.

Managed project installs also support an optional surface selector. `--surface extended` is the default and installs the full TailTrail pack, matching existing behavior. `--surface core` installs a smaller first-run pack with `hello`, `start`, Navigator, guardrail checks, governance checks, adapters, and quick docs. Use Core for onboarding or lightweight repo setup; use Extended when the repo needs learning, reporting, benchmarks, meta-harness, quality/security scanning helpers, AIDLC, hooks, or token telemetry. Upgrade Core in place with `python3 scripts/tailtrail.py install upgrade-to-extended --target /path/to/project`; the upgrade is additive and does not delete files.

## Unified Command Surface

Use the unified local command when you do not want to remember every individual script:

```bash
python3 scripts/tailtrail.py help
python3 scripts/tailtrail.py commands
python3 scripts/tailtrail.py version
python3 scripts/tailtrail.py hello
python3 scripts/tailtrail.py governance check
python3 scripts/tailtrail.py registry list
python3 scripts/tailtrail.py registry validate --strict
python3 scripts/tailtrail.py setup-scan --root .
```

### Optional Global Launcher

If you want TailTrail to work from any repo without typing the absolute TailTrail path, install the launcher:

```bash
python3 scripts/tailtrail.py install launcher --dry-run
python3 scripts/tailtrail.py install launcher
```

The launcher writes a small executable, usually:

```text
~/.local/bin/tailtrail
~/.local/bin/hello
```

After that, from any repo:

```bash
hello tailtrail
tailtrail hello
tailtrail guide "tell me important features of this repo"
tailtrail start "fix Sonar issue and prepare PR" --changed path/to/file
tailtrail reference --target /path/to/service-a --reference /path/to/service-b --goal "match validation style"
```

The `hello` alias is intentionally narrow. It handles `hello tailtrail`, `hello TailTrail`, and the common typo `hello taitrail`, then delegates to `tailtrail hello`; other `hello ...` usage prints a TailTrail-specific usage message. If you already installed the launcher before this alias existed, rerun `python3 scripts/tailtrail.py install launcher --force`.

This solves the common failure where a target repo does not contain `scripts/tailtrail.py`:

```text
can't open file '/target/repo/scripts/tailtrail.py'
```

That error means the command was run relative to the target repo. The launcher points back to the TailTrail checkout and uses the current directory as the default project root. If the installer says `~/.local/bin` is not on `PATH`, add it to your shell profile or call the launcher by full path.

Daily examples:

```bash
python3 scripts/tailtrail.py hello
python3 scripts/tailtrail.py do "fix Sonar issue and prepare PR"
python3 scripts/tailtrail.py "fix Sonar issue and prepare PR"
python3 scripts/tailtrail.py start "fix Sonar issue and prepare PR"
python3 scripts/tailtrail.py next
python3 scripts/tailtrail.py do "fix Sonar issue" --changed src/service/foo.py
python3 scripts/tailtrail.py guide "fix Sonar issue and prepare PR"
python3 scripts/tailtrail.py guide "fix Sonar issue" --changed src/service/foo.py
python3 scripts/tailtrail.py bootstrap snapshot --root . --write-result
python3 scripts/tailtrail.py bootstrap status --root .
python3 scripts/tailtrail.py graph --changed src/service/foo.py
python3 scripts/tailtrail.py setup-scan --root .
python3 scripts/tailtrail.py governance check
python3 scripts/tailtrail.py registry list
python3 scripts/tailtrail.py intent "use AIDLC and review"
python3 scripts/tailtrail.py route review
python3 scripts/tailtrail.py token "review this diff for dependency risk"
python3 scripts/tailtrail.py aidlc init --root . --depth standard
python3 scripts/tailtrail.py aidlc check --root .
python3 scripts/tailtrail.py benchmark --format json
python3 scripts/tailtrail.py analyze benchmarks/results/latest.json
python3 scripts/tailtrail.py outcome summarize --month 2026-07
python3 scripts/tailtrail.py doctor
```

### Feature Registry

Use the Feature Registry when you want a read-only index of TailTrail features, commands, docs, scripts, tests, install surface, MCP exposure, approval posture, and evidence label:

```bash
python3 scripts/tailtrail.py registry list
python3 scripts/tailtrail.py registry list --surface core
python3 scripts/tailtrail.py registry show meta-harness
python3 scripts/tailtrail.py registry surfaces
python3 scripts/tailtrail.py registry workflow review
python3 scripts/tailtrail.py registry mcp --format json
python3 scripts/tailtrail.py registry validate
python3 scripts/tailtrail.py registry validate --strict
python3 scripts/tailtrail.py registry drift
```

Default `registry validate` is advisory and exits successfully with a drift report. Use `--strict` before TailTrail releases, feature additions, or command/script changes so unowned commands, orphan scripts, missing docs, missing tests, duplicate script claims, unresolved dependencies, and invalid evidence labels fail locally.

Use `registry drift` after feature changes to check command docs, roadmap wording, changelog freshness, and public claim boundaries. It is advisory by default and does not edit files.

### Resume With `next`

Use `python3 scripts/tailtrail.py next` after `start` when you paused and want a lean reminder of the single next action. It is read-only: it may inspect the latest local Start plan artifact, Git status, review markers, scan approval posture, and learning refresh markers, but it does not run scanners, edit files, mutate Git, call the network, or capture learning.

### Installation Success Check

Use `hello` immediately after installing, updating, cloning, or configuring a launcher:

```bash
python3 scripts/tailtrail.py hello
tailtrail hello
```

Expected output:

```text
Hello from TailTrail.
Installation check: passed
Mode: source checkout
Location: /path/to/tailtrail
Command: tailtrail
Next check: run `tailtrail doctor` for full validation.
```

`hello` is a fast smoke check. It does not inspect the full package, run adapters, change files, call the network, or validate a target project. Use `doctor` when you want the deeper package check.

Installed pack examples:

```bash
python3 tailtrail/scripts/tailtrail.py help
python3 tailtrail/scripts/tailtrail.py start "add payment retry handling"
python3 tailtrail/scripts/tailtrail.py start "add payment retry handling" --changed src/payment/retry.py
python3 tailtrail/scripts/tailtrail.py graph --root . --changed src/service/foo.py
python3 tailtrail/scripts/tailtrail.py guide "add payment retry handling"
python3 tailtrail/scripts/tailtrail.py guide "add payment retry handling" --changed src/payment/retry.py
```

Why use it:

- one command surface for users and future Navigator
- easier onboarding
- existing scripts still work
- no global install required
- no background service
- no automatic implementation

Use this quick choice table when you are unsure:

| Situation | First command |
|---|---|
| I have a real task and want TailTrail to choose the workflow. | `python3 scripts/tailtrail.py do "task"` or `python3 scripts/tailtrail.py "task"` |
| I only want the plan without the full Start report. | `python3 scripts/tailtrail.py guide "task"` |
| I already know the changed or target file. | `python3 scripts/tailtrail.py do "task" --changed path/to/file` |
| I want a safe repo map before broad planning. | `python3 scripts/tailtrail.py bootstrap snapshot --root . --write-result` |
| I have CI, build, lint, test, or Sonar logs. | `python3 scripts/tailtrail.py ci summarize --file log.txt` or `python3 scripts/tailtrail.py sonar summarize --file sonar.log` |
| I want to know which checks exist. | `python3 scripts/tailtrail.py quality scan --root .` |
| I need to run one approved check. | `python3 scripts/tailtrail.py quality run --approved --command "exact command"` |
| I want local guardrail enforcement. | `python3 scripts/tailtrail.py guard check` |
| I changed guardrail rules and want false-positive evidence. | `python3 scripts/tailtrail.py guardrail precision --strict` |
| I finished a TailTrail-assisted task and want adoption evidence. | `python3 scripts/tailtrail.py outcome capture ... --approved` |
| I want to know whether Meta-Harness should stay quiet or recommend product change. | `python3 scripts/tailtrail.py harness readiness --root .` |
| I accepted a Meta-Harness proposal and want Navigator to use it. | `python3 scripts/tailtrail.py harness proposal-record --root . --proposal-id MH-... --status accepted` |
| I cloned a repo that already has TailTrail files. | `python3 scripts/tailtrail.py setup-scan --root .` |
| I use an MCP-capable assistant and want direct TailTrail tools. | `python3 scripts/tailtrail.py mcp tools` |

## MCP Server

TailTrail includes an optional read-only MCP server for MCP-capable assistants:

```bash
python3 scripts/tailtrail.py mcp tools
python3 scripts/tailtrail.py mcp doctor
python3 scripts/tailtrail.py mcp serve
```

The server exposes `navigator_plan`, `start_report`, `guardrail_check`, `graph_map`, `install_status`, `eval_scenario_list`, and `eval_scenario_report`. It is local stdio only. It does not implement code, run scanners, run tests, edit files, write evaluation result files, apply fixes, upload telemetry, or run in the background by default. Use it when the assistant can call MCP tools directly; otherwise use the normal CLI and Markdown instructions.

## Guardrail Enforcement Lite

Use Guardrail Enforcement Lite when you want a local deterministic check before commit or before sending PR text for review.

Pre-commit and reusable GitHub Action support are available for teams that want opt-in enforcement. Both stay advisory unless the repo explicitly passes `--fail-on <class>[,<class>...]`; upgrading TailTrail does not make a project stricter by itself.

Guardrail precision baseline is available for maintainers changing detection rules:

```bash
python3 scripts/tailtrail.py guardrail precision
python3 scripts/tailtrail.py guardrail precision --strict --format json
python3 scripts/tailtrail.py guardrail precision --rule dependency-gate
```

It runs committed labeled fixtures and reports precision, recall, false-positive rate, fixture count, confidence, and threshold status per rule. Use it before tightening enforcement, changing `scripts/guardrail-check.py`, or claiming the rule set became less noisy. The result is evidence for TailTrail fixtures only; it is not a universal precision claim for every repo.

```bash
python3 scripts/tailtrail.py guard check
python3 scripts/tailtrail.py guard check --enforce
python3 scripts/tailtrail.py guard check --fail-on dependency-gate,local-state
python3 scripts/tailtrail.py guard check --diff changes.patch --format json
python3 scripts/tailtrail.py guard check --commit-message commit-message.txt
python3 scripts/tailtrail.py guard check --pr-body pr-body.md
```

What it checks:

- dependency manifest additions without a Dependency Gate note or approval marker
- removed lines that look like validation, auth, authorization, escaping, logging, migration safety, tests, secrets, or token safeguards
- validation claims such as "tests passed", "verified", or "deployed" without command/result evidence in the supplied commit or PR text
- staged local TailTrail runtime state such as `.tailtrail/*state*.json`, `*events*.jsonl`, run-output folders, and token telemetry

Default mode is advisory and does not block. `--enforce` returns non-zero only when high-severity findings are present. This check is intentionally conservative; it is not a full code review, SAST scanner, dependency scanner, or policy service.

`do` is the easiest preferred first command for non-trivial work. It routes to `start`, which runs Navigator, then adds a compact report with approximate token posture, guarded learning quality, and install/update posture. Free-form input such as `python3 scripts/tailtrail.py "fix validation bug"` also routes to `start`. It is still advisory: it does not edit files, run implementation, record learnings, or run scanners.

`guide` runs only TailTrail Navigator. It returns a plan-style recommendation and reminds users they can edit the plan before implementation. Use `guide` when you want the workflow plan without the extra task-start report.

## Using TailTrail In A Cloned Repo

Run setup scan before installing or updating TailTrail in a repo that already contains TailTrail files from another user or team.

```bash
python3 scripts/tailtrail.py setup-scan --root .
python3 scripts/tailtrail.py setup-scan --root . --format json
python3 scripts/tailtrail.py setup-scan --root . --tracked-only
```

Installed pack example:

```bash
python3 tailtrail/scripts/tailtrail.py setup-scan --root .
```

What it tells you:

- which files are shared project context
- which files are project overrides that should be preserved
- which assistant instruction files are team review files
- whether an installed TailTrail pack is present
- which local runtime files should not be committed
- whether generated metadata needs a team decision before sharing
- which `.gitignore` entries are missing
- which safe next commands to run

Default behavior:

- It does not write, delete, move, ignore, install, or update files.
- It preserves `tailtrail-policy.md`, `.tailtrail/policy-overrides.json`, AIDLC docs, and curated learnings by default.
- It warns when local runtime state such as event logs, quality run output, vulnerability run output, token telemetry, task starts, or local install manifests appear in the repo.
- It recommends update/install dry-run commands before changing TailTrail-managed files.

Use this flow:

1. Clone the repo.
2. Run `setup-scan`.
3. Review warnings and `.gitignore` recommendations.
4. Run `python3 scripts/tailtrail.py policy check --root .` if policy files exist.
5. Run update or install only in dry-run mode first.
6. Review the diff before committing shared TailTrail files.

## TailTrail Start

Use `start` when the user has a real task and wants TailTrail to choose the right workflow:

```bash
python3 scripts/tailtrail.py start "fix Sonar issue and prepare PR"
python3 scripts/tailtrail.py start "fix Sonar issue" --changed src/service/foo.py
python3 scripts/tailtrail.py start "triage GHSA in package.json" --changed package.json
```

The Start report contains:

- **Start Here**: the immediate next step, default action, and reminder that nothing has been changed yet.
- **Decision Menu**: short prompts for review, approve, edit, focused validation, scan approval, learning approval, or leaner workflow.
- **Navigator Summary**: selected workflow, task type, risk signals, selected feature count, skipped feature count, and impacted file count.
- **Token Posture**: approximate token estimate for focused files versus broad TailTrail docs intentionally avoided.
- **Bootstrap Snapshot**: whether safe repo/runtime facts are fresh, missing, stale, or skipped.
- **Guarded Learning Quality**: whether learning indexes/events exist, whether refresh actions exist, and whether learning approval is required.
- **Install And Update Posture**: whether the current root looks like a source checkout or installed pack and which dry-run update/check command to use.
- **Full Navigator Plan**: the same approval-first plan produced by `guide`.

The token posture is estimated from local file character counts. It helps show directionally whether TailTrail avoided loading broad context, but it is not exact model/API token usage. Exact savings require real provider usage telemetry.

Recommended user flow:

1. Run `start` with a short task goal.
2. Add `--changed` for files the user already knows.
3. Review the Start report.
4. Edit the plan if it is too heavy, too light, missing a file, or recommending the wrong command.
5. Approve implementation only after the plan looks right.
6. After implementation, run only the validation, learning capture, quality-loop, or update commands that the user explicitly approves.

Common Start examples:

```bash
python3 scripts/tailtrail.py start "fix null pointer in claim mapper" --changed src/main/java/com/acme/claims/ClaimMapper.java
python3 scripts/tailtrail.py start "fix Sonar cognitive complexity issue" --changed src/main/java/com/acme/payment/PaymentValidator.java
python3 scripts/tailtrail.py start "add retry handling for payment capture"
python3 scripts/tailtrail.py start "add a CSV parsing library for import files"
python3 scripts/tailtrail.py start "triage GHSA vulnerability in package.json" --changed package.json
```

How to use the Decision Menu:

- Choose **Review the plan first** when you want to inspect what TailTrail selected and skipped.
- Choose **Approve implementation** only when selected features, impacted files, commands, validation, scans, and learning choices look right.
- Choose **Edit the plan** when the report is too heavy, too light, missing files, or using the wrong repo command.
- Choose **Confirm focused validation** when the exact test, lint, quality, or manual check needs to be named before implementation.
- Choose **Approve exactly one scan command** only when the scan command is reviewed and repo-approved.
- Choose **Choose how to handle surfaced learnings** when the report finds advisory learning matches.
- Choose **Make the workflow leaner** for narrow fixes where broad scanners, AIDLC, or handoff would add noise.

## TailTrail Navigator

Navigator helps users choose the right TailTrail workflow without memorizing all features. It is the planning engine behind `start`; use `guide` directly when you want only the Navigator plan.

```bash
python3 scripts/tailtrail.py guide "fix Sonar issue and prepare PR"
python3 scripts/tailtrail.py guide "add payment retry handling" --changed src/payment/retry.py
python3 scripts/navigator.py "review auth middleware" --changed src/auth/middleware.py --format json
```

Use Navigator when:

- the task may touch code, tests, dependencies, CI/Sonar, security, release, or handoff
- you want a read-only repo overview such as "tell me important features of this repo"
- you are unsure whether to use AIDLC, Review, Dependency Gate, Graph, Learning, or scanner tools
- the request mentions broad work such as "prepare PR", "fix quality gate", "review this", "run scan", "handoff", "release", or "production"
- you want the agent to propose a plan before implementation

Skip Navigator for tiny tasks when the next step is obvious, such as fixing one typo, formatting one sentence, or answering a simple factual question.

### Bootstrap Snapshot

Bootstrap Snapshot is the safe pre-task map Navigator can use before broad planning.

Harness Review reports Bootstrap Fit as `missing`, `useful`, `stale`, or `noisy`. Useful snapshots can reduce repeated discovery; stale or noisy snapshots should be refreshed or paired with Code Graph Mapper before broad source reads.

```bash
python3 scripts/tailtrail.py bootstrap snapshot --root .
python3 scripts/tailtrail.py bootstrap snapshot --root . --write-result
python3 scripts/tailtrail.py bootstrap status --root .
python3 scripts/tailtrail.py bootstrap refresh --root .
```

Use it before repo overview, scanner, graph, handoff, broad review, or meaningful implementation work when you want Navigator to start from structured facts. It captures languages, manifests, package managers, test signals, CI files, scanner signals, available local commands, and TailTrail artifact presence.

It does not read source bodies, raw prompts, raw logs, secrets, environment variable values, or user identity, and it does not execute project code. `snapshot` prints without writing unless `--write-result` is used. `refresh` writes `.tailtrail/bootstrap-snapshot.json`.

Do not commit `.tailtrail/bootstrap-snapshot.json` by default. It is local runtime state. Shared reviewed metadata belongs in `tailtrail-meta/`.

### Token Harness Router

Token Harness Router is the first Token Harness phase. Use it when you want TailTrail to classify a file or pasted text before deciding whether token reduction is safe.

```bash
python3 scripts/tailtrail.py token-harness route --path src/app.py
python3 scripts/tailtrail.py token-harness route --path report.sarif --format json
python3 scripts/tailtrail.py token route --text "Traceback..." --label log
```

It reports:

- content type, such as `source`, `diff`, `scanner-output`, `log`, or `documentation`
- exactness class, such as `must-be-exact`, `structure-exact`, `summary-safe`, `reduce-safe`, or `skip-reduction`
- recommended strategy and blocked reductions
- retrieval command or pointer

TH-1 does not compress, summarize, write receipts, append ledger events, call models, call APIs, or claim token savings. It is an exactness gate and routing decision only.

### Structured Reducers

Structured Reducers are the first Token Harness feature that can reduce context. Use them for large JSON/tool output, logs, scanner reports, and source structure maps when you need a compact view before loading full evidence.

```bash
python3 scripts/tailtrail.py token-harness reduce --path report.json
python3 scripts/tailtrail.py token-harness reduce --path build.log
python3 scripts/tailtrail.py token-harness reduce --path report.sarif --format json
python3 scripts/tailtrail.py token-harness reduce --path src/app.py --mode structure
python3 scripts/tailtrail.py token-harness reduce --path report.sarif --write-receipt --approved
```

Reducers preserve retrieval commands back to the original file. They block protected exact content such as diffs, configs, dependency manifests, security policy, and source bodies. Source files require `--mode structure`, which emits symbols and line numbers but omits function bodies.

Receipt or ledger writes are off by default and require `--approved`. Reducer output is local approximate context shaping, not exact model/API token savings.

### Optional Runtime Compression Bridge

The Token Harness Bridge lets a team connect an approved local compression adapter for safe bulky artifacts. It is disabled by default and only runs when `tailtrail-policy.md` enables it and the command includes `--approved`.

Use it for:

- large build or CI logs
- long documentation files
- scanner output
- JSON or tool output that the router marks as bridge-eligible

Do not use it for source code, diffs, configs, dependency manifests, lock files, security policy, secrets, unknown content, or anything marked `must-be-exact`.

```bash
python3 scripts/tailtrail.py token-harness bridge plan --path build.log
python3 scripts/tailtrail.py token-harness bridge input --path build.log --output /tmp/bridge-input.json
python3 scripts/tailtrail.py token-harness bridge validate-output --input /tmp/bridge-input.json --output /tmp/bridge-output.json
python3 scripts/tailtrail.py token-harness bridge run --path build.log --adapter-command "local-compressor --stdin" --approved
```

Local policy example:

```yaml
## Token Harness Bridge

runtime_compression_bridge: enabled
adapter_command: "local-compressor --stdin"
allowed_content_types:
- log
- documentation
- scanner-output
- json
- tool-output
max_input_bytes: 250000
require_approval: true
```

Expected safety behavior:

- disabled repos return a disabled bridge plan
- protected exact files are blocked before adapter execution
- adapter output is rejected if it drops required preserved evidence
- rejected output falls back to exact pass-through or the internal structured reducer path
- TailTrail does not bundle a compressor, call network services, manage credentials, or act as a proxy

### Reversible Context Receipts

Context receipts are local proof records for what TailTrail loaded, avoided, preserved, and how to retrieve original evidence. TH-2 receipts add exactness and reversibility fields while keeping old receipt summaries compatible.

```bash
python3 scripts/tailtrail.py receipt capture --task "fix validation bug" --profile review --loaded src/service/foo.py --avoided ROADMAP.md --approved
python3 scripts/tailtrail.py receipt capture --task "fix Sonar issue" --loaded src/App.java --loaded-exactness must-be-exact --loaded-strategy exact-pass-through --preserve "line numbers" --route-source token-harness --reduction-strategy graph-first-plus-exact-files --approved
python3 scripts/tailtrail.py receipt summary
python3 scripts/tailtrail.py receipt retrieve --path src/App.java
```

Receipts stay in `.tailtrail/context-receipts.jsonl` and should remain local. They are approximate context accounting, not exact model/API token usage. Use measured telemetry plus `savings report` when exact token savings are required.

### Token Harness Ledger

Token Harness Ledger is the append-only local evidence log for approved Token Harness events. Use it when you want a durable record that TailTrail chose a routing strategy, captured a context receipt, imported measured usage, produced a savings report, or recorded a quality result.

```bash
python3 scripts/tailtrail.py token-harness ledger append --event-type route_decision --task-type bug-fix --content-type source --strategy exact-pass-through --exactness-class must-be-exact --tokens-before 1200 --tokens-after 1200 --evidence-label local-evidence --approved
python3 scripts/tailtrail.py token-harness ledger summary
python3 scripts/tailtrail.py token-harness ledger validate
```

Ledger writes require `--approved`. The ledger is local-only by default at `.tailtrail/token-harness-events.jsonl`, with a lock file at `.tailtrail/token-harness-events.lock`. It stores structured metadata, not raw prompts, source code, logs, secrets, repo names, user identity, pricing, or exact ROI claims.

Use `summary` for directional local evidence and `validate` before trusting the ledger in demos or reports. Exact model/API savings still require measured telemetry and later proof gates.

### Token Harness Proof

Token Harness Proof turns local ledger events and optional measured telemetry into an evidence label. Use it when you need to explain whether token savings are only directional, locally evidenced, measured, or benchmark-measured.

```bash
python3 scripts/tailtrail.py token-harness proof report
python3 scripts/tailtrail.py token-harness proof report --ledger .tailtrail/token-harness-events.jsonl --telemetry .tailtrail/token-usage.jsonl
python3 scripts/tailtrail.py token-harness proof report --telemetry .tailtrail/token-usage.jsonl --strict
python3 scripts/tailtrail.py token-harness proof holdout --task-id TASK-123 --task-class bug-fix
python3 scripts/tailtrail.py efficacy run --token-harness-ledger .tailtrail/token-harness-events.jsonl
```

Evidence labels:

- `estimated`: approximate local counts only.
- `local-evidence`: ledger or receipts exist, but measured telemetry is missing or did not pass the gate.
- `measured`: complete baseline/TailTrail token telemetry exists and the confidence gate passes.
- `benchmark-measured`: measured telemetry is tied to passing benchmark/artifact evidence.

The proof layer does not call model APIs or calculate dollars. Sensitive task classes are excluded from holdout decisions.

### Meta-Harness Token Feedback

Meta-Harness can use sanitized Token Harness signals to find repeated strategy problems. This is useful for maintainers who want to know whether token reducers, proof gates, or Navigator token routing need tuning.

```bash
python3 scripts/tailtrail.py harness review --root . --write-result
python3 scripts/tailtrail.py harness shared-summary --root . --dry-run
python3 scripts/tailtrail.py harness shared-summary --root . --write-result --approved
python3 scripts/tailtrail.py harness analyze --summary tailtrail-meta/harness-summary.jsonl
python3 scripts/tailtrail.py harness propose --root .
```

Shared summaries store categories only, such as `token_strategy`, `token_reduction_band`, and `token_proof_label`. They do not store raw prompts, source, logs, paths, repo names, users, exact token usage, or pricing/cost fields.

### Repo Overview / Discovery Mode

For read-only discovery prompts, Navigator now uses a compact plan instead of the full feature matrix:

```bash
python3 scripts/tailtrail.py guide "tell me important features of this repo"
```

Expected behavior:

- selects `Repo Overview / Discovery`
- avoids AIDLC, Review, Handoff, scanners, learning capture, tests, builds, and file edits by default
- loads README/docs, manifests, top-level structure, entry points, tests, and main modules only as needed
- shows Code Graph Mapper as an optional deeper discovery command, but does not create `tailtrail-meta/code-graph-cache.json` unless the user approves and runs that command
- asks for approval before inspecting the repo and answering the overview question

This mode is for understanding a repo. If the prompt also asks to fix, implement, review, scan, or prepare a PR, Navigator switches back to the normal workflow planner.

To create the graph cache during repo discovery, approve and run:

```bash
python3 /path/to/tailtrail/scripts/tailtrail.py graph map --root /path/to/project
```

That writes:

```text
/path/to/project/tailtrail-meta/code-graph-cache.json
```

### Recommended Daily Flow

1. Start with a short goal:

```bash
python3 scripts/tailtrail.py guide "fix failing Sonar issue in PaymentValidator"
```

2. Add changed or target files when you know them:

```bash
python3 scripts/tailtrail.py guide "fix failing Sonar issue in PaymentValidator" --changed src/main/java/com/acme/payment/PaymentValidator.java
```

3. Read the Navigator plan. It will tell you:

- which TailTrail features to use
- which features to skip
- which files are likely impacted
- what context to load
- what context to avoid
- what commands may help
- whether scans, learnings, graph cache, or handoff are relevant

4. Edit the plan if needed. Remove anything too heavy, add missing files, or replace commands with repo-approved commands.

5. Approve implementation only after the plan is acceptable.

6. After implementation, use the suggested validation, handoff, learning capture, or quality-loop commands only when they are relevant and approved.

### Navigator Output Views

Use the full view when reviewing a plan deeply:

```bash
python3 scripts/tailtrail.py guide "fix Sonar quality gate failure and check vulnerability impact before PR" --changed src/main/java/PaymentValidator.java --view full
```

Use compact view when the full plan is too noisy:

```bash
python3 scripts/tailtrail.py guide "fix Sonar quality gate failure and check vulnerability impact before PR" --changed src/main/java/PaymentValidator.java --view compact
```

Use commands-only view when you only want the suggested commands and approval/evidence warnings:

```bash
python3 scripts/tailtrail.py guide "fix Sonar quality gate failure and check vulnerability impact before PR" --changed src/main/java/PaymentValidator.java --view commands-only
```

Navigator commands now include explicit `--root "/path/to/project"` when the underlying command supports it. That makes command snippets safer when TailTrail is installed in one folder and the target repo is somewhere else.

### How To Read The Plan

Navigator output is intentionally split into sections:

- **Selected Features**: what TailTrail thinks should be used for this task.
- **Skipped Features**: what TailTrail is intentionally leaving out so the workflow does not get heavy.
- **Likely Impacted Files**: files to inspect first. This is a starting point, not a complete proof.
- **Load**: context the agent should read.
- **Avoid**: context that would add noise or token cost.
- **Suggested Commands**: optional commands to run manually or ask the agent to run.
- **Graph Cache**: whether a saved code graph is fresh, missing, stale, or invalid.
- **Cross-Repo Reference**: target/reference repo boundaries when the task mentions another repo as a pattern source.
- **Learning Approval**: whether to use, ignore, or edit surfaced learnings.
- **Scan Approval**: whether to run a Sonar, lint, test, vulnerability, audit, or broad scanner command.
- **Implementation Plan**: the proposed task sequence.
- **Approval**: how to proceed.

### How To Reply To Navigator

Approve the plan:

```text
Approve this Navigator plan. Implement the change using the selected features and validation command.
```

Edit the plan:

```text
Edit the plan: skip AIDLC, keep Review Lens and Dependency Gate, add src/test/java/com/acme/payment/PaymentValidatorTest.java as an impacted file, and use mvn test -Dtest=PaymentValidatorTest for validation.
```

Reject a heavy plan:

```text
This is too heavy. Use lean mode: read only the target file and focused test, make the smallest change, and do not run broad scanners.
```

Approve one scan command:

```text
Approve only this command: mvn test -Dtest=PaymentValidatorTest. Do not run sonar-scanner or dependency audit.
```

Use learnings:

```text
Use learnings, but only as advisory context. Current source and validation evidence should win.
```

Ignore learnings:

```text
Ignore learnings for this task. Proceed from current source, tests, and scanner evidence only.
```

Edit surfaced learnings:

```text
Edit plan: use learning 20260712-abc12345, ignore the other surfaced learnings, and inspect the current validator test before applying the pattern.
```

Navigator returns:

- task classification
- risk indicators
- selected features
- skipped features
- likely impacted files
- files/context to load
- files/context to avoid
- suggested commands
- graph cache status for heavy Sonar, vulnerability, QA, dependency, review, or handoff work
- graph-aware learning matches when they exist, with explicit learning approval choices
- learning skip reasons such as `no index`, `tiny task`, `stale graph`, or `no matching tags/files/rules`
- learning refresh awareness when surfaced learnings look stale, weak, contradictory, or the user asks why a learning was bad
- a post-task learning capture suggestion command for meaningful work
- scan approval question when the goal asks for Sonar, lint, quality-gate, vulnerability, audit, or broad local scanner work
- cross-repo reference boundaries when the goal mentions target/reference repos or sibling repo patterns
- implementation plan
- approval instructions

Navigator is approval-first. Review the plan, edit it if needed, then approve implementation. It does not edit files, run implementation, call a model, start a background service, or record learnings automatically.

### What Navigator Does Automatically

Navigator automatically classifies the request and recommends a workflow. It may check local Git changed files, local TailTrail state, graph cache status, and learning indexes. It may run lightweight local helper scripts such as Code Review Graph Lite or Graph-Aware Learning search to prepare the plan.

For meaningful code-change prompts, Navigator now treats Code Graph Mapper as a first-read helper:

- if `tailtrail-meta/code-graph-cache.json` is missing, it recommends `graph map --root "/path/to/project"` before broad source reads
- if the cache exists and watched files changed, it recommends `graph refresh --root "/path/to/project" --changed ...`
- if the cache is fresh, it recommends using the cached read order, then reading exact source before edits

This applies to major and minor code-change work. Tiny typo or docs-only work still skips graph mapping to avoid process noise.

Navigator does not automatically:

- edit source files
- run broad scanners
- run tests or builds
- write learning events
- write quality-loop events
- create AIDLC artifacts
- change policy files
- modify TailTrail rules

Anything that writes files, runs broad commands, or records learning/quality history should be explicitly approved.

For meaningful implementation, fix, review, QA, security, dependency, or handoff work, Navigator also prepares a **Learning Capture Trigger**. This does not record a learning by itself. It adds a post-task command that should run only after user acceptance, reviewer feedback, validation results, or a clear reusable repo pattern is known.

When Navigator surfaces graph-aware learnings, it asks the user to choose:

- `use learnings`: apply the surfaced learnings as advisory repo patterns after reading current source and evidence
- `ignore learnings`: proceed from current code and evidence only
- `edit plan`: keep or remove specific learning IDs before implementation

Learnings are advisory only. Current source, tests, CI, scanner output, local policy, guardrails, and explicit user instructions always win.

For full code scans, Sonar checks, vulnerability scans, dependency audits, broad builds, or scanner-like requests, Navigator adds a **Scan Approval** section. The default answer is `no`. Reply `yes` only after reviewing the candidate command, or edit the plan with the exact repo-approved command. This prevents TailTrail from silently running slow, noisy, networked, credentialed, or organization-specific checks.

For meaningful completed work, Navigator may show a **Post-Task Learning Capture Suggestion** like:

```bash
python3 hooks/learning-capture-hook.py "Fixed Sonar validator cognitive complexity" --root "/path/to/project" --tags "bug,ci-sonar" --candidate "Extract named guard methods while preserving validation order." --acceptance accepted --validation-outcome pass
```

This is triggered in the plan, but it is still approval-first. TailTrail does not run it automatically. Add `--approved` only when the user intentionally wants to record the learning.

Example:

```bash
python3 scripts/tailtrail.py guide "run a full code scan for Sonar and vulnerability issues before PR"
```

Expected behavior:

- Navigator selects Quality Signal Scanner planning.
- Navigator distinguishes CI/Sonar Intelligence from Security And Vulnerability Intelligence when both are present.
- Navigator checks Code Graph Mapper cache status for meaningful code-change prompts and broad scanner/review work.
- Navigator lists detected project signals and candidate commands.
- Navigator asks whether to run a Sonar, lint, test, or vulnerability scan.
- Nothing runs until the user approves a specific command.

### Cross-Repo Reference Mode

Use this when your workspace has multiple repos and you are changing one repo while using another repo as a pattern reference.

Best prompt:

```text
Use TailTrail cross-repo reference.
Target: /Users/me/workspace/service-a
Reference: /Users/me/workspace/service-b
Goal: implement the same validation style.
Only edit service-a.
```

Direct command:

```bash
python3 scripts/tailtrail.py reference \
  --target /Users/me/workspace/service-a \
  --reference /Users/me/workspace/service-b \
  --goal "match validation style"
```

What it does:

- confirms which repo is editable
- confirms which repo is read-only reference context
- reports whether paths exist and look like git repos
- summarizes language and manifest signals
- warns if target/reference paths overlap
- recommends compact reference graph commands when repeated reference reads may happen

What it does not do:

- edit either repo
- copy code from the reference repo
- run scanners, tests, builds, or model calls
- make an inaccessible path readable

If your assistant cannot read the reference path, open the parent workspace that contains both repos, or run the command from a local environment that can read both paths and save a compact summary:

```bash
python3 scripts/tailtrail.py reference \
  --target /Users/me/workspace/service-a \
  --reference /Users/me/workspace/service-b \
  --goal "reuse API error handling convention" \
  --write-summary /Users/me/workspace/service-a/.tailtrail/reference-context/service-b.md
```

For repeated use, keep reference metadata near the target repo without editing the reference repo:

```bash
python3 scripts/tailtrail.py graph map \
  --root /Users/me/workspace/service-b \
  --cache /Users/me/workspace/service-a/.tailtrail/reference-graphs/service-b.json
```

Review the generated plan before implementation. The target repo's current source, tests, policy, CI, scanner evidence, and explicit user instructions always override reference summaries.

### Common Navigator Examples

Bug fix:

```bash
python3 scripts/tailtrail.py guide "fix null pointer in claim mapper" --changed src/main/java/com/acme/claims/ClaimMapper.java
```

Expected path:

- Code Review Graph Lite
- Review Lens
- likely caller/test suggestions
- focused validation recommendation

Feature work:

```bash
python3 scripts/tailtrail.py guide "add retry handling for payment capture"
```

Expected path:

- AIDLC if the task is broad or multi-step
- Review Lens
- local policy if `tailtrail-policy.md` exists
- implementation plan before edits

Dependency decision:

```bash
python3 scripts/tailtrail.py guide "add a CSV parsing package for import files"
```

Expected path:

- Dependency Gate
- standard library/platform/native alternatives first
- local dependency policy if present
- no new package unless justified

CI or Sonar failure:

```bash
python3 scripts/tailtrail.py guide "fix Sonar quality gate failure" --changed src/main/java/com/acme/payment/PaymentValidator.java
```

Expected path:

- CI/Sonar Intelligence
- QA / CI-Sonar Lens
- Code Graph Mapper status for heavy source reads
- Scan Approval if a scanner command is suggested

Security or vulnerability work:

```bash
python3 scripts/tailtrail.py guide "triage GHSA vulnerability in package.json" --changed package.json
```

Expected path:

- Security And Vulnerability Intelligence
- Dependency Gate when dependency changes are involved
- vulnerability scan recommendation, not automatic execution
- remediation only if the user asks to fix a finding

Handoff or PR preparation:

```bash
python3 scripts/tailtrail.py guide "prepare handoff for payment retry PR"
```

Expected path:

- Handoff
- Review Lens
- validation handoff template
- concise changed-files and risk summary

Policy-aware work:

```bash
python3 scripts/tailtrail.py guide "update auth middleware validation" --changed src/auth/middleware.py
```

Expected path:

- load `tailtrail-policy.md` when present
- preserve security and authorization guardrails
- recommend focused tests and handoff notes if ownership is involved

### Navigator In Installed Packs

If TailTrail is installed into a project folder such as `tailtrail/`, run Navigator from that pack:

```bash
python3 tailtrail/scripts/tailtrail.py guide "fix Sonar issue"
python3 tailtrail/scripts/tailtrail.py guide "fix Sonar issue" --changed src/service/foo.py
```

Use the same approval pattern: inspect the plan, edit it, then approve implementation.

## Code Graph Mapper

Use Code Graph Mapper when a task is broad enough that the assistant may reread the same files repeatedly, especially Sonar, vulnerability, dependency, QA, review, handoff, and before-PR work.

```bash
python3 scripts/tailtrail.py graph map --changed src/service/foo.py
python3 scripts/tailtrail.py graph status --changed src/service/foo.py
python3 scripts/tailtrail.py graph refresh --changed src/service/foo.py
python3 scripts/tailtrail.py graph map --changed src/service/foo.py --scanner-evidence sonar.log --format json
```

What it does:

- writes `tailtrail-meta/code-graph-cache.json` by default
- stores compact metadata only, not source snippets
- supports Python, Java, .NET/C#, SQL, and Terraform
- records file hashes so stale caches can be detected
- extracts symbols, references, call-chain hints, type hierarchy hints, endpoints, DB tables, config usage, workspace overlays, likely callers, likely tests, manifests, and suggested read order
- adds advanced enterprise metadata: monorepo partitions, external service hints, endpoint-to-service-to-table flows, CODEOWNERS ownership, likely tests, and release/deployment path hints

How to use it day to day:

1. Run `graph map` when starting heavy code review or scanner-remediation work.
2. Let Navigator use `graph status` during later prompts.
3. Run `graph refresh` if the cache is stale.
4. Use partitions and owner/test/release mapping to avoid reading unrelated modules.
5. Read exact source files before editing; the graph only tells you where to look first.

The mapper does not run Sonar, vulnerability scanners, tests, CI, release commands, graph databases, vector databases, or quality commands. Use Quality Signal Scanner and scan approval for that.

## Scanner Graph Overlay

Use Scanner Graph Overlay when you already have Sonar/static-analysis output, vulnerability output, dependency-audit output, SAST output, or secret/container/IaC scan output and need to know where to read before fixing it.

```bash
python3 scripts/tailtrail.py graph overlay --sonar sonar.log --changed src/service/foo.py
python3 scripts/tailtrail.py graph overlay --vulnerability audit.log --changed package.json
python3 scripts/tailtrail.py graph overlay --sonar sonar.log --vulnerability audit.log --format json
```

What it does:

- preserves exact scanner evidence lines, rule IDs, vulnerability IDs, severities, components, and paths when detected
- groups findings by impacted file
- labels each file as source, test, manifest, config, database, Terraform, or unknown
- adds AST V1 symbol and call hints for impacted source files unless `--no-ast` is used
- suggests likely tests, related files, nearby manifests, and read order
- prints per-file commands for AST V1, Code Review Graph Lite, and Code Graph Mapper refresh

When to use it:

1. Save large scanner output to a local file instead of pasting it repeatedly.
2. Run `sonar summarize` or `vulnerability summarize` if you only need a compact evidence summary.
3. Run `graph overlay` when you need scanner evidence connected to graph impact before implementation.
4. Read the suggested source and test files before editing.
5. Ask approval before running any scanner, build, test, audit, or vulnerability command.

It does not run Sonar, query SonarQube/SonarCloud, run vulnerability scanners, query vulnerability databases, prove findings are fixed, or edit code. Current scanner output, current source, local policy, and GUARDRAILS.md always win over inferred graph metadata.

## CI/Sonar Summaries

Use CI/Sonar Intelligence when you have CI, build, test, lint, Sonar, static-analysis, or quality-gate output. Save large logs to local files instead of pasting them repeatedly.

```bash
python3 scripts/tailtrail.py ci summarize --file ci.log
python3 scripts/tailtrail.py sonar summarize --file sonar.log
python3 scripts/tailtrail.py validation summarize --ci ci.log --sonar sonar.log
```

The summaries preserve exact failure lines, commands, rule IDs, severities, paths, affected files, and first relevant evidence when detected. They do not poll CI, query SonarQube/SonarCloud, run scanners, or claim validation passed.

## V2.7 Engine Helpers

Use Engine Helpers when the issue is not a missing TailTrail feature, but noisy evidence, oversized local context, or a need for a more structured local code map before editing.

```bash
python3 scripts/tailtrail.py engine summarize-output --file build.log
python3 scripts/tailtrail.py engine slice-context --file src/service/foo.py --query validate
python3 scripts/tailtrail.py engine cache-summary
python3 scripts/tailtrail.py engine prune-context --file noisy-context.md
python3 scripts/tailtrail.py graph ast --changed src/service/foo.py --depth lite
python3 scripts/tailtrail.py graph ast --changed src/service/foo.py --depth v1
python3 scripts/tailtrail.py graph ast --changed src/service/foo.py --depth v2
python3 scripts/tailtrail.py graph ast --changed src/service/foo.py --depth v3 --provider-output tailtrail-meta/providers/semantic.json --approved
```

What each helper does:

- `summarize-output`: extracts important lines, commands, affected files, and next steps from generic local output.
- `slice-context`: returns compact file windows around query terms, headings, functions, or classes.
- `cache-summary`: summarizes Code Graph Mapper cache metadata without loading the whole cache.
- `prune-context`: estimates token reduction and removes lines matching explicit noisy terms from a context file.
- `graph ast --depth lite`: reports structured symbols for selected files. Python uses `ast`; Java, .NET/C#, SQL, and Terraform use simple local parsing heuristics.
- `graph ast --depth v1`: adds symbol references, call hints, type hierarchy hints, endpoint hints, DB/config hints, likely tests, and changed-symbol impact.
- `graph ast --depth v2`: adds a local Semantic V2 layer with symbol index, import/module edges, reference edges, endpoint-to-handler links, data-flow-lite hints, test coverage hints, and provider readiness for language-server, SCIP, Roslyn, and tree-sitter paths.
- `graph ast --depth v3`: adds opt-in provider-backed semantic ingestion from approved local JSON exports. This is the path for Java JDT/language-server style symbol graphs, .NET Roslyn-derived symbol/call/type graphs, richer Python analyzer output, SQL parser output, Terraform parser output, SCIP-derived JSON, or repo-owned extractor output.

Default code-intelligence behavior:

- Default engine path is local-only: `lite`, `v1`, and `v2`.
- Normal TailTrail development stays on the local AST/Semantic path.
- `graph ast` defaults to V1.
- Use `lite`, `v1`, or `v2` first unless provider-backed metadata is explicitly needed.
- V3 is opt-in only and requires `--depth v3 --provider-output ...` plus `--approved` or local policy enablement.
- Navigator should not silently choose V3. It may recommend V3 only when the user asks for provider-backed semantic intelligence or an approved provider-output file exists and matches the task.
- TailTrail never starts JDT, Roslyn, language servers, SCIP, tree-sitter, SQL parsers, Terraform parsers, MCP providers, networked services, or repo-owned extractors automatically.
- Provider-backed facts are advisory metadata, not proof. Exact source, tests, CI, scanner evidence, policy, guardrails, and explicit user direction remain authoritative.

Use them at these stages:

- Before asking the agent to reason over a huge build, scanner, or tool output file.
- Before loading large source or docs files when only one term, class, function, rule, or config key matters.
- After creating a code graph when you need the shape of the cache without the whole metadata payload.
- Before pasting generated context when it contains known noisy folders or repeated output.
- Before editing a shared helper, endpoint, service, model, SQL object, Terraform module, or scanner-reported file where a file-level graph is too broad.

AST examples:

```bash
python3 scripts/tailtrail.py graph ast --changed src/main/java/com/acme/ClaimMapper.java --depth lite
python3 scripts/tailtrail.py graph ast --changed src/main/java/com/acme/ClaimMapper.java --depth v1
python3 scripts/tailtrail.py graph ast --changed src/main/java/com/acme/ClaimMapper.java --depth v2
python3 scripts/tailtrail.py graph ast --changed src/main/java/com/acme/ClaimMapper.java --depth v3 --provider-output tailtrail-meta/providers/jdt.json --approved
python3 scripts/tailtrail.py graph ast --changed src/main/csharp/ClaimsController.cs --depth v3 --provider-output tailtrail-meta/providers/roslyn.json --approved
python3 scripts/tailtrail.py graph ast --changed database/schema.sql --depth v3 --provider-output tailtrail-meta/providers/sql.json --approved
python3 scripts/tailtrail.py graph ast --changed infra/main.tf --depth v3 --provider-output tailtrail-meta/providers/terraform.json --approved
python3 scripts/tailtrail.py graph ast --changed scripts/tailtrail.py --depth v1 --format json
```

Use `lite` when you only need to know which symbols exist in the changed files. Use `v1` when you need local callers, reference hints, likely tests, endpoint/config/DB clues, or changed-symbol impact before deciding what to read next. Use `v2` when the task needs richer impact orientation, such as API-to-service-to-table reasoning, shared type hierarchy review, .NET/Java/Python symbol tracing, or deciding whether an approved semantic provider would help. Use `v3` only when the repo already has an approved provider/export file or a user explicitly supplies one.

Semantic V2 does not start a language server, run Roslyn, ingest SCIP, call tree-sitter, install dependencies, or prove data flow. It detects provider readiness and emits local metadata only. Semantic V3 ingests approved local provider JSON and labels those facts as `provider-backed`; it still does not execute providers or treat provider output as proof. V3 requires either `--approved` on the command or `provider_backed_semantic_ingestion: enabled` in `tailtrail-policy.md`.

Provider JSON shape:

```json
{
  "provider": "jdt",
  "language": "java",
  "symbols": [{"name": "ClaimMapper", "kind": "class", "file": "src/main/java/com/acme/ClaimMapper.java", "line": 12}],
  "calls": [{"caller": "ClaimMapper.map", "callee": "ClaimValidator.validate", "file": "src/main/java/com/acme/ClaimMapper.java", "line": 28}],
  "db_tables": [{"table": "claim", "file": "src/main/java/com/acme/ClaimMapper.java", "line": 42}]
}
```

Supported provider-style sources:

- Java: JDT or language-server style JSON exports.
- .NET: Roslyn-derived JSON exports for symbols, calls, type hierarchy, and endpoints.
- Python: richer analyzer JSON exports beyond TailTrail's built-in `ast`.
- SQL/Terraform: structured parser output or repo-owned extractor output.
- Generic: any approved repo-owned JSON extractor that uses the metadata keys above.

Evidence labels:

- `heuristic`: regex, text, proximity, or local parsing hints.
- `local-ast`: facts produced by TailTrail's local AST path, such as Python `ast`.
- `provider-backed`: facts ingested from approved local provider JSON.
- `measured/validated`: facts backed by explicit validation, scanner, CI, or measured telemetry evidence.

Every AST/Semantic map includes an `evidence_summary` so users can see how much of the output is heuristic, local AST, provider-backed, or measured/validated.

Boundaries:

- They are local, deterministic Python helpers.
- They do not edit source files.
- They do not run scanners, tests, builds, network calls, model calls, vector search, language servers, Roslyn analyzers, MCP adapters, tree-sitter parsers, or background services.
- V3 reads approved local JSON provider outputs only and requires `--approved` or local policy enablement.
- AST maps are metadata and heuristics, not correctness proof.
- AST maps do not store source snippets.
- Approximate token numbers are character-count estimates only.
- Summaries and slices are orientation aids; exact current source and evidence still need to be inspected before implementation.

## Quality Signal Scanner

Use Quality Signal Scanner when you want TailTrail to discover likely local checks before a PR, Sonar fix, lint fix, test failure, or quality-gate cleanup.

```bash
python3 scripts/tailtrail.py quality scan --root .
python3 scripts/tailtrail.py quality scan --changed src/service/foo.py
python3 scripts/tailtrail.py quality run --approved --command "npm run lint"
```

`quality scan` does not run commands. It inspects local manifests such as `package.json`, `pom.xml`, Gradle files, Python config, `.sln`, `go.mod`, CI files, and Sonar config, then labels recommendations as safe local, needs approval, or blocked.

`quality run` runs one exact command only when `--approved` is present. It blocks deploy/publish/destructive/cloud commands, uses a local quality-tool allowlist, saves output under `.tailtrail/quality-runs/`, and returns the command exit code.

## Test Precision Planner

Use Test Precision Planner when code changed or will change and you want precise test guidance without running a broad suite. It is especially useful after a bug fix, before a PR, after a Sonar/lint remediation, or when a reviewer asks for better unit coverage.

```bash
python3 scripts/tailtrail.py test plan --root .
python3 scripts/tailtrail.py test plan --changed src/service/foo.py
python3 scripts/tailtrail.py test plan --changed src/service/foo.py --goal "fix validation bug"
python3 scripts/tailtrail.py test plan --changed src/main/java/com/acme/PaymentValidator.java --format json
python3 scripts/tailtrail.py test summarize --changed src/service/foo.py --goal "show implemented test cases"
```

What it does:

- detects common Python, Java/Maven, Java/Gradle, Node, .NET, and Go test setups
- infers likely test files from changed source paths
- surfaces existing test fixtures, helpers, factories, mocks, and support files to reuse
- recommends a compact test matrix: regression, happy path, negative path, boundary path, and guard-preservation when risk signals exist
- suggests focused validation commands such as `pytest tests/service/test_foo.py`, `mvn test -Dtest=FooTest`, `dotnet test --filter ...`, or `npm test -- path`
- summarizes likely existing test functions or blocks with line numbers and assertion hints when you use `test summarize`

Navigator behavior:

- Navigator selects Test Precision Planner when the prompt mentions unit tests, regression tests, test coverage, test cases, post-change validation, validation confidence, or before-PR validation.
- Navigator shows the feature in `Selected Features` and adds a command like `tailtrail test plan --root "/path/to/repo" --goal "..." --changed src/service/foo.py`.
- It does not run automatically after development. The user or agent should run the suggested command after implementation or before final validation.
- Pair it with Review by asking: `Use TailTrail Navigator for this fix, then after implementation run review and Test Precision Planner before final validation.`

Boundaries:

- It does not create tests.
- It does not run tests, builds, scanners, or network calls.
- It does not claim validation passed.
- `test summarize` is heuristic. It helps inspect likely test coverage, but it does not prove coverage.
- Use `quality run --approved --command "..."` only when the user approves one exact command.

## Evaluation Harness

Evaluation Harness is the planned umbrella for TailTrail evidence: benchmark scenarios, measured efficacy, guardrail precision, outcome telemetry, Quality Loop, Meta-Harness, Token Harness proof, and value reporting.

Use `eval ...` when you want evidence about TailTrail behavior, quality, token claims, outcomes, or benchmarks from one command family.

```bash
python3 scripts/tailtrail.py eval audit
python3 scripts/tailtrail.py eval audit --format json
python3 scripts/tailtrail.py eval audit --strict
python3 scripts/tailtrail.py eval audit --write-report --approved
python3 scripts/tailtrail.py eval portfolio run --portfolio
python3 scripts/tailtrail.py eval guardrails precision
python3 scripts/tailtrail.py eval outcome summarize
python3 scripts/tailtrail.py eval workflow review
python3 scripts/tailtrail.py eval meta quick --root .
python3 scripts/tailtrail.py eval tokens route --path src/app.py
python3 scripts/tailtrail.py eval report value --root .
python3 scripts/tailtrail.py eval scenario list
python3 scripts/tailtrail.py eval scenario run --scenario validation-bug
python3 scripts/tailtrail.py eval scenario compare --scenario dependency-decision
python3 scripts/tailtrail.py eval scenario report --scenario security-triage
python3 scripts/tailtrail.py eval scenario report --scenario buildweek-validation
python3 scripts/tailtrail.py eval normalize --source token-proof --input token-proof.json --format json
python3 scripts/tailtrail.py eval normalize --source outcome --input outcome.json --write-event --approved
python3 scripts/tailtrail.py eval validate-events .tailtrail/evaluation/events.jsonl
```

EH-2 routes existing evidence features through `eval ...` as thin aliases. It does not add new scoring, does not run hidden telemetry, and does not weaken any approval flags from the original commands.

EH-3 adds the shared Evaluation Harness event format. Use it when you want compact evidence from existing local reports to become one normalized local event stream:

```text
.tailtrail/evaluation/events.jsonl
```

This is useful for later portfolio reporting and Meta-Harness analysis. It is not needed for normal day-to-day coding unless you are collecting evidence. Writes require `--write-event --approved`; `--dry-run` validates the shape without writing or needing approval.

EH-4 adds deterministic scenario scoring. Use it for demos, release evidence, regression proof, or product-confidence checks:

```bash
python3 scripts/tailtrail.py eval scenario list
python3 scripts/tailtrail.py eval scenario run --scenario validation-bug --format json
python3 scripts/tailtrail.py eval scenario report --scenario validation-bug --write-result --approved
python3 scripts/tailtrail.py eval scenario report --scenario buildweek-validation
```

Scenario scoring reads committed artifacts under `benchmarks/evaluation/scenarios/`. It does not run live agents, tests, CI, scanners, package managers, model/API calls, or hidden telemetry.

Use `eval audit` before adding or changing Evaluation Harness aliases. It inventories the current evidence features and decides whether each one should be exposed as `alias`, `merge`, `needs-decision`, or `retire`.

What EH-0 does:

- maps current evidence commands to future `eval ...` surfaces
- detects ambiguous aliases before EH-2
- checks local scripts, docs, tests, registry IDs, approval posture, and privacy posture
- writes `reports/evaluation-harness/eh0-audit.json` and `.md` only with `--write-report --approved`

What Evaluation Harness does not do yet:

- no live model/API calls
- no raw prompts, source, scanner logs, or secrets in audit reports
- no deletion or deprecation of old commands

See `EVALUATION-HARNESS.md` for the implementation hub and phase plan.

## TailTrail Quality Loop

Use Quality Loop when you want to review whether TailTrail itself chose the right workflow. It is for TailTrail behavior quality, not application code quality.

```bash
python3 scripts/tailtrail.py quality-loop capture --workflow review,qa --fit correct --outcome accepted --validation-outcome pass --approved
python3 scripts/tailtrail.py quality-loop capture --workflow aidlc,review --fit too-heavy --outcome revised
python3 scripts/tailtrail.py quality-loop summarize --month 2026-07 --write-result
python3 scripts/tailtrail.py quality-loop review --month 2026-07
python3 scripts/tailtrail.py quality-loop propose --month 2026-07
python3 scripts/tailtrail.py quality-loop decide --area navigator --decision "Skip AIDLC for tiny docs-only tasks." --approved
```

What it does:

- records compact approved behavior events in `.tailtrail/quality-events.jsonl`
- summarizes workflow fit, outcomes, validation, missed gates, and overlap flags
- proposes reviewable improvements to Navigator, guardrails, command help, learning guidance, or local policy
- records approved or rejected quality decisions in `.tailtrail/quality-decisions.md`

Safety rules:

- `capture` writes only with `--approved`; without it, TailTrail prints the event shape and records nothing.
- Do not include raw prompts, raw logs, secrets, PII, PHI, customer data, or sensitive scanner output.
- Do not load `.tailtrail/quality-events.jsonl` into routine coding prompts.
- Use `.tailtrail/quality-summary.md` only for quality review, Navigator tuning, or local policy review.
- Proposals are advisory. Review before editing TailTrail files, prompts, Navigator rules, or local policy.

## Adoption Outcome Telemetry

Use Adoption Outcomes after a task is complete and you can honestly say whether TailTrail helped. This is product evidence, not surveillance.

```bash
python3 scripts/tailtrail.py outcome capture --task-type bug-fix --workflow start,review --acceptance accepted --validation-outcome pass --review-outcome approved --defect-escaped no --time-saved 30-60m --fit correct --learning-quality trusted --approved
python3 scripts/tailtrail.py outcome capture --task-type ci-sonar --workflow start,quality,review --acceptance partially-accepted --validation-outcome pass --review-outcome changes-requested --defect-escaped unknown --time-saved 15-30m --fit correct --scan-used --approved
python3 scripts/tailtrail.py outcome summarize --month 2026-07
python3 scripts/tailtrail.py outcome summarize --month 2026-07 --format json
python3 scripts/tailtrail.py outcome summarize --write-result
```

What it captures:

- task type
- workflow selected
- user acceptance
- validation outcome
- review outcome
- escaped defect yes/no/unknown
- time-saved band
- TailTrail fit
- learning quality
- whether plan edits, Dependency Gate, guardrails, AIDLC, or scans were used

Safety rules:

- `capture` writes only with `--approved`; without it, TailTrail prints the event shape and records nothing.
- Store only compact controlled values and optional redacted notes.
- Do not store raw prompts, raw logs, secrets, PII, PHI, customer data, or source snippets.
- Use `.tailtrail/outcome-summary.md` for retrospectives instead of loading raw `.tailtrail/outcome-events.jsonl` into routine coding prompts.

How it differs from Quality Loop:

- Outcome telemetry answers: did TailTrail help this task?
- Quality Loop answers: does TailTrail behavior need tuning?
- Learning Agent answers: is a repo pattern safe to reuse later?

## Enterprise Reporting

Use Enterprise Reporting when leads, platform teams, or governance reviewers need a local monthly view of TailTrail adoption and outcomes.

```bash
python3 scripts/tailtrail.py report --month 2026-07
python3 scripts/tailtrail.py report value --month 2026-07
python3 scripts/tailtrail.py report value --month 2026-07 --format csv --write-result
python3 scripts/tailtrail.py report --month 2026-07 --include-aidlc --write-result
python3 scripts/tailtrail.py report --start 2026-07-01 --end 2026-07-31 --format json
python3 scripts/tailtrail.py report --token-telemetry .tailtrail/token-usage.jsonl
python3 scripts/tailtrail.py report compare --previous-report june-value.json --current-report july-value.json
python3 scripts/tailtrail.py report trend
python3 scripts/tailtrail.py report trend --format csv --write-result
python3 scripts/tailtrail.py report aggregate --report-file repo-a-value.json --report-file repo-b-value.json
python3 scripts/tailtrail.py report pr --only quality --only tokens
python3 scripts/tailtrail.py report --only quality
```

What it summarizes:

- Quality Loop workflow fit, outcomes, validation, overlap, and missed gates
- Adoption Outcome acceptance, validation, review, escaped defects, time-saved bands, fit, and learning quality
- Learning Agent acceptance, confidence bands, task types, tags, and dependency discipline
- Value Surface signals for dependency avoidance, safeguard preservation, validation truth, focused validation, diff-size discipline, learning hygiene, and measured token evidence when supplied

Use `report value` for a compact leadership or platform review view. It is intentionally not a hard ROI claim. It shows local evidence counts and labels token numbers as measured only when real model/API usage telemetry is supplied.

Use `report trend` for multi-month local trends. It groups quality, outcome, learning, and measured token records by month and renders a compact table plus a simple text chart. Use it when a team wants to show whether TailTrail evidence is growing, improving, or getting noisier.

Use `report aggregate` only with explicitly supplied local JSON reports from repos you choose. It does not discover repos, query a service, or upload telemetry. Use it when a platform team wants a local multi-repo rollup for review.

Use `report pr` for a compact Markdown block suitable for PR descriptions. Add `--only quality`, `--only outcomes`, `--only learning`, or `--only tokens` to keep the summary focused.

Use `--format csv --write-result` to create `.tailtrail/value-report.csv`. Use `--format json --write-result path.json` when you want to compare two local reports later with `report compare`.
- Learning Refresh action counts
- optional AIDLC artifact counts
- approximate context evidence when measured telemetry is missing
- measured token savings only when real model/API usage telemetry is supplied

Safety rules:

- Reports are local and advisory.
- Do not use reports for surveillance or hidden user scoring.
- Do not include raw prompts, raw logs, secrets, PII, PHI, customer data, or sensitive scanner output by default.
- Use report recommendations to decide which TailTrail rules, Navigator paths, guardrails, or policy packs should be reviewed.

## External Assets

TailTrail includes optional original SVG assets for docs, internal demos, and lightweight distribution polish.

```text
assets/tailtrail-logo.svg
assets/tailtrail-mark.svg
```

Use these only when presenting or packaging TailTrail. They are not required for any command, assistant adapter, skill, hook, or local workflow. Do not load them into routine coding prompts.

## Security And Vulnerability Intelligence

Use this when the user asks about CVEs, GHSA advisories, dependency audits, SAST findings, secret leaks, container/image findings, IaC misconfiguration, or security policy findings.

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

`vulnerability scan` does not run scanners. It inspects local manifests and recommends likely vulnerability commands.

`vulnerability run` runs one exact command only when `--approved` is present. It blocks destructive/deploy/cloud commands, uses a vulnerability-tool allowlist, saves output under `.tailtrail/vulnerability-runs/`, and returns the scanner exit code.

`vulnerability summarize` returns a structured vulnerability list from local scanner output. It auto-detects SARIF, Trivy JSON, and Grype JSON, then falls back to text parsing. It preserves exact CVE/GHSA/CWE/rule IDs, severities, packages/components, versions, and paths when present. Use `--root` to normalize absolute affected paths to project-relative paths. Evidence text is redacted for common secret patterns before output, and report reads are capped by `--max-bytes` to avoid loading oversized scanner files.

Daily rule:

1. If the user asks what to scan, return recommended commands and ask for approval.
2. If the user approves an exact scan, run only that command.
3. Return the vulnerability list from `vulnerability summarize`.
4. Implement a fix only when the user specifically asks to remediate a finding.
5. Do not claim a vulnerability is fixed until the relevant scanner or validation command passes.

For graph impact, pass structured reports to the overlay:

```bash
python3 scripts/tailtrail.py graph overlay --vulnerability codeql.sarif
python3 scripts/tailtrail.py graph overlay --vulnerability trivy.json --changed package.json
python3 scripts/tailtrail.py graph overlay --vulnerability grype.json --format json
python3 scripts/tailtrail.py graph overlay --vulnerability codeql.sarif --root /path/to/project
```

The overlay normalizes structured report paths against `--root`, filters generic related-file tokens such as `app`, and classifies Trivy package-manifest findings as dependency vulnerabilities.

## 2. Choose Your Assistant

TailTrail is Codex-first. Other assistants are supported through portable instruction adapters, and behavior depends on how each assistant loads and follows project instructions. See `ASSISTANT-COMPATIBILITY.md` for support levels, limitations, and the validated adapter contract.

TailTrail includes native Codex skills plus adapter files for other assistants.

| Assistant | How To Use |
|---|---|
| Codex | Use the repo as a local Codex plugin source. Invoke `@tailtrail` and `@tailtrail-review`. |
| Claude | Keep `CLAUDE.md` at the project root. |
| Cursor | Keep `.cursor/rules/tailtrail.mdc` in the project. |
| GitHub Copilot | Keep `.github/copilot-instructions.md` in the project. |
| ChatGPT | Use `.openai/chatgpt-instructions.md` as project instructions or upload/reference it in the ChatGPT project. |
| Gemini | Keep `GEMINI.md` at the project root. |
| Generic agents | Keep `AGENTS.md` at the project root. |

Short assistant-specific prompt packs live in `adapters/prompts/`.

If you update adapter source files in `adapters/`, sync tool-facing files and validate the required behavior contract:

```bash
python3 scripts/tailtrail.py adapters sync
python3 scripts/tailtrail.py adapters check
python3 scripts/sync-adapters.py --write
python3 scripts/sync-adapters.py --check
```

## 3. Set Up GitHub Copilot

TailTrail's Copilot adapter is:

```text
.github/copilot-instructions.md
```

This file is repository-wide guidance. When Copilot works in the context of the repository, it can use these instructions for chat, code generation, and code review surfaces that support repository custom instructions.

### What Goes Inside The File

The file should contain TailTrail's Copilot-specific adapter content:

- core coding rules
- dependency decision rules
- when to use TailTrail support files
- token/context discipline
- AIDLC and handoff summary rules

Use this source file as the canonical content:

```text
adapters/copilot-instructions.md
```

The actual Copilot file is generated from that source:

```text
.github/copilot-instructions.md
```

Keep them synced with:

```bash
python3 scripts/sync-adapters.py --write
python3 scripts/sync-adapters.py --check
```

### Step 1: Install Into The Target Repo

Recommended setup for a project that should use TailTrail with Copilot:

```bash
python3 scripts/install-copilot.py --root /path/to/project --with-tailtrail-pack
```

This keeps the project root clean by creating:

- `.github/copilot-instructions.md`
- `tailtrail/`

The `tailtrail/` folder contains:

- `tailtrail/AGENTS.md`
- `tailtrail/AIDLC.md`
- `tailtrail/DEPENDENCY-GATE.md`
- `tailtrail/GUARDRAILS.md`
- `tailtrail/TOKEN-AUTOPILOT.md`
- `tailtrail/TOKEN-SLICER.md`
- `tailtrail/tailtrail-policy.example.md`
- `tailtrail/USER-GUIDE.md`
- `tailtrail/adapters/`
- `tailtrail/aidlc/`
- `tailtrail/context/`
- `tailtrail/templates/`
- selected TailTrail scripts:
  - `tailtrail/scripts/aidlc-check.py`
  - `tailtrail/scripts/aidlc-init.py`
  - `tailtrail/scripts/analyze-benchmark.py`
  - `tailtrail/scripts/benchmark-tailtrail.py`
  - `tailtrail/scripts/ci-summary.py`
  - `tailtrail/scripts/code-graph-mapper.py`
  - `tailtrail/scripts/expand-intent.py`
  - `tailtrail/scripts/graph-learning.py`
  - `tailtrail/scripts/install-copilot.py`
  - `tailtrail/scripts/install-local.py`
  - `tailtrail/scripts/learning-agent.py`
  - `tailtrail/scripts/learning-refresh.py`
  - `tailtrail/scripts/learnings.py`
  - `tailtrail/scripts/navigator.py`
  - `tailtrail/scripts/policy-check.py`
  - `tailtrail/scripts/quality-loop.py`
  - `tailtrail/scripts/quality-run.py`
  - `tailtrail/scripts/quality-scan.py`
  - `tailtrail/scripts/review-graph.py`
  - `tailtrail/scripts/route-context.py`
  - `tailtrail/scripts/sonar-summary.py`
  - `tailtrail/scripts/tailtrail.py`
  - `tailtrail/scripts/tailtrail-report.py`
  - `tailtrail/scripts/team-init.py`
  - `tailtrail/scripts/token-auto.py`
  - `tailtrail/scripts/token-savings.py`
  - `tailtrail/scripts/update-copilot.py`
  - `tailtrail/scripts/update-tailtrail.py`
  - `tailtrail/scripts/validation-summary.py`
  - `tailtrail/scripts/vulnerability-run.py`
  - `tailtrail/scripts/vulnerability-scan.py`
  - `tailtrail/scripts/vulnerability-summary.py`
- `tailtrail/hooks/`

TailTrail also writes a manifest:

```text
tailtrail/.tailtrail-install.json
```

The manifest records TailTrail-managed file hashes so future updates can tell unchanged core files from local edits.
It is generated inside the installed pack in the target project. Do not edit it by hand; customize TailTrail with `.tailtrail/intent-overrides.json`, `tailtrail/intent-overrides.json`, or local project notes instead.

The generated `.github/copilot-instructions.md` tells Copilot that the TailTrail pack lives in `tailtrail/`.

The installed pack includes `tailtrail/context/guardrail-layers.md`. It gives compact task-specific checks for implementation, code consistency, review, QA, dependency, AIDLC, handoff, CI/Sonar, release, and token-saving work. Users do not need to paste this file manually; short TailTrail prompts and router decisions point the assistant to the relevant layer.

### Policy Packs

Use Policy Packs when a repo or team needs local commands, reviewers, dependency approvals, restricted folders, generated-code boundaries, privacy notes, CI/Sonar expectations, or release rules without editing TailTrail core files.

```bash
python3 tailtrail/scripts/tailtrail.py policy init --root /path/to/project --with-overrides
python3 tailtrail/scripts/tailtrail.py policy check --root /path/to/project --with-overrides --strict
```

This creates:

- `tailtrail-policy.md`
- `.tailtrail/policy-overrides.json` when `--with-overrides` is used

`tailtrail-policy.md` stays the human-readable source of truth. `.tailtrail/policy-overrides.json` is optional local metadata for simple structured values. The checker validates shape and required headings only; it does not create a hidden policy engine.

Use a custom folder name when your team wants a different location:

```bash
python3 scripts/install-copilot.py --root /path/to/project --with-tailtrail-pack --pack-dir tools/tailtrail
```

Use root layout only when you intentionally want TailTrail files spread at the project root:

```bash
python3 scripts/install-copilot.py --root /path/to/project --with-tailtrail-pack --pack-dir .
```

Minimal setup if you only want Copilot guidance and do not want the full TailTrail pack:

```bash
python3 scripts/install-copilot.py --root /path/to/project
```

This creates only:

```text
/path/to/project/.github/copilot-instructions.md
```

Use `--force` only when you intentionally want to overwrite existing target files:

```bash
python3 scripts/install-copilot.py --root /path/to/project --with-tailtrail-pack --force
```

### Step 1.0: Use The Local Installer Assistant

If you are unsure which setup path to use, start with:

```bash
python3 scripts/install-local.py --inspect
```

Preview a setup before writing files:

```bash
python3 scripts/install-local.py --target /path/to/project --profile full --dry-run
```

Apply a setup:

```bash
python3 scripts/install-local.py --target /path/to/project --profile generic
python3 scripts/install-local.py --target /path/to/project --profile copilot
python3 scripts/install-local.py --target /path/to/project --profile aidlc --depth standard
python3 scripts/install-local.py --target /path/to/project --profile hooks
python3 scripts/install-local.py --target /path/to/project --profile full
```

The installer does not perform network calls, shell profile edits, IDE setting changes, or global machine writes. It keeps the profile list intentionally small: `inspect`, `generic`, `copilot`, `aidlc`, `hooks`, and `full`.

### Git Hygiene For Installed TailTrail Files

TailTrail setup and runtime files are local-only by default in work projects. The installer writes `.gitignore` entries so these files do not get pushed accidentally:

- `.tailtrail/`
- `tailtrail/`
- assistant setup files such as `.github/copilot-instructions.md`, `CLAUDE.md`, `GEMINI.md`, and local TailTrail guidance files
- generated local lifecycle/runtime state

The default TailTrail folder intended for reviewed team sharing is:

```text
tailtrail-meta/
```

Use `tailtrail-meta/` for reviewed compact metadata such as Code Graph Mapper cache and sanitized Meta-Harness summaries. Do not commit the managed `tailtrail/` pack or `.tailtrail/` runtime state unless your repository explicitly opts into sharing TailTrail setup files.

If TailTrail files were already staged:

```bash
git restore --staged tailtrail .tailtrail .github/copilot-instructions.md AGENTS.md AIDLC.md
python3 scripts/tailtrail.py setup-scan --root .
python3 scripts/tailtrail.py guard check --enforce
```

If your repo intentionally wants shared TailTrail setup files, remove the corresponding strict-local `.gitignore` entries after team review.

### Step 1.1: Update An Existing TailTrail Pack

When TailTrail has a new version and the target project already has TailTrail installed, use the updater instead of deleting files or reinstalling the project.

Preview first:

```bash
python3 scripts/update-copilot.py --root /path/to/project --dry-run
```

Apply a safe update:

```bash
python3 scripts/update-copilot.py --root /path/to/project
```

Default behavior is `--strategy preserve`:

- updates missing files
- updates files that match the previous TailTrail manifest
- skips files that appear locally modified
- prints the skipped files as `Local edits preserved`

If your team intentionally edited TailTrail core files but still wants the new TailTrail version, use backup-overwrite:

```bash
python3 scripts/update-copilot.py --root /path/to/project --strategy backup-overwrite
```

This refreshes TailTrail-managed files and saves previous copies under:

```text
.tailtrail/backups/
```

For custom pack folders:

```bash
python3 scripts/update-copilot.py --root /path/to/project --pack-dir tools/tailtrail --dry-run
python3 scripts/update-copilot.py --root /path/to/project --pack-dir tools/tailtrail
```

Best practice: do not customize TailTrail core files directly. Put project or organization prompt changes in:

```text
.tailtrail/intent-overrides.json
tailtrail/intent-overrides.json
```

Those override files are not TailTrail core files and are not overwritten by the updater.

### Step 2: Review And Commit The Files

Review what was copied:

```bash
cd /path/to/project
git status --short
```

Commit the setup so GitHub.com, pull request reviews, and teammates can use the same instructions:

```bash
git add .github/copilot-instructions.md tailtrail
git commit -m "Add TailTrail Copilot setup"
```

If you used a custom folder, stage that folder instead:

```bash
git add .github/copilot-instructions.md tools/tailtrail
```

If you used minimal setup, commit only:

```bash
git add .github/copilot-instructions.md
git commit -m "Add TailTrail Copilot instructions"
```

### Step 3: Open The Repo With Copilot Enabled

Open the target repository in a Copilot-supported editor or on GitHub.com.

Common options:

- VS Code with GitHub Copilot Chat enabled
- Visual Studio with GitHub Copilot enabled
- JetBrains IDE with the GitHub Copilot extension enabled
- GitHub.com Copilot Chat or Copilot code review

### Step 4: Confirm Copilot Is Using The File

In Copilot Chat, ask a repository-context question:

```text
Using this repository's custom instructions, summarize how you should approach a small bug fix.
```

Then expand the response references. If repository instructions were used, Copilot should show:

```text
.github/copilot-instructions.md
```

If you do not see the file in references:

- make sure the file is committed or saved in the opened workspace
- make sure the repository root you opened contains `.github/copilot-instructions.md`
- make sure custom instructions are enabled in your editor
- restart Copilot Chat or reload the editor window

### Step 5: Use TailTrail Prompts With Copilot

For implementation:

```text
Use TailTrail from .github/copilot-instructions.md. Read the relevant files first, reuse existing project patterns, avoid new dependencies, and make the smallest maintainable change.
```

For review:

```text
Use TailTrail Review. Check this diff for unnecessary dependencies, duplicate logic, over-broad rewrites, weakened safeguards, and missing focused validation.
```

For dependency decisions:

```text
Apply TailTrail's dependency gate before recommending any new package. Prefer standard library, platform-native features, framework capabilities, and already-installed dependencies.
```

For AIDLC work:

```text
Use TailTrail AIDLC standard depth. Create or update aidlc-docs/ state, requirements, workflow plan, implementation plan, validation handoff, and audit notes as needed.
```

For CI/Sonar work:

```text
Use TailTrail CI/Sonar. Preserve the exact job, stage, rule ID, severity, file, line, command, and first relevant failure. Fix the smallest root cause and name the exact validation needed.
```

### Step 6: Use Copilot Code Review

When using Copilot code review on GitHub.com, repository custom instructions are enabled by default for code review. Repository admins can toggle this in repository settings under Copilot code review.

For best results:

- keep `.github/copilot-instructions.md` in the base branch of the pull request
- ask Copilot to review after the file is merged into the base branch
- include TailTrail handoff notes in the pull request description for larger changes

### Step 7: Know Manual vs Automated Token Features

The Copilot instructions file does not install a plugin or run TailTrail scripts automatically. It gives Copilot guidance.

Token Router and Token Autopilot are implemented as Python CLIs. They become automatic only when the host environment calls `hooks/token-autopilot-hook.py` or `hooks/token-router-hook.py`, or when your team wires those scripts into a local workflow. In assistants that only read instruction files, TailTrail applies token saving through guidance: load smaller slices, avoid broad docs, summarize noisy output, and preserve exact source/diff/config text when needed.

Use scripts manually when needed:

```bash
python3 tailtrail/scripts/expand-intent.py "use AIDLC and review"
python3 tailtrail/scripts/tailtrail.py guide "fix Sonar issue"
python3 tailtrail/scripts/tailtrail.py guide "fix Sonar issue" --changed src/service/foo.py
python3 tailtrail/scripts/expand-intent.py "use delivery flow"
python3 tailtrail/scripts/expand-intent.py "use CI Sonar"
python3 tailtrail/scripts/route-context.py review
python3 tailtrail/scripts/route-context.py qa
python3 tailtrail/scripts/route-context.py ci-sonar
python3 tailtrail/scripts/route-context.py release
python3 tailtrail/scripts/learnings.py init --root /path/to/project
python3 tailtrail/scripts/review-graph.py --root /path/to/project --changed path/to/file
python3 tailtrail/scripts/team-init.py --root /path/to/project --mode optional
python3 tailtrail/scripts/token-auto.py "review this diff"
python3 tailtrail/scripts/update-tailtrail.py --root /path/to/project --dry-run
python3 tailtrail/scripts/aidlc-init.py --root /path/to/project --depth standard
python3 tailtrail/scripts/aidlc-check.py --root /path/to/project
```

For hook-capable hosts, reduce repeated prompt typing with:

```bash
python3 tailtrail/hooks/tailtrail-lifecycle-hook.py --startup
python3 tailtrail/hooks/tailtrail-lifecycle-hook.py "use AIDLC and review"
python3 tailtrail/hooks/tailtrail-lifecycle-hook.py "use CI Sonar"
```

The lifecycle hook expands short commands and adds the token autopilot decision. It prints compact guidance only; it does not inject full docs.

If Copilot ignores a rule, mention the file explicitly in your prompt:

```text
Follow .github/copilot-instructions.md and TailTrail's dependency gate.
```

## 4. Use TailTrail For Normal Coding

For implementation work, ask the assistant to use TailTrail.

Codex examples:

```text
@tailtrail implement this with the smallest clear change
@tailtrail lean add this endpoint
@tailtrail strict challenge this design before coding
```

Other assistants:

```text
Use TailTrail. Read the relevant files first, reuse existing patterns, avoid new dependencies, and keep the smallest maintainable diff.
```

Expected behavior:

- inspect relevant files before editing
- trace callers, tests, and data flow
- reuse existing helpers and conventions
- prefer standard library and platform-native features
- avoid unnecessary dependencies
- preserve validation, security, accessibility, data integrity, and explicit requirements

## 5. Use TailTrail Modes

TailTrail modes are prompt-selected. There is no global persisted mode.

| Mode | Use When | Prompt Example |
|---|---|---|
| `steady` | normal implementation | `@tailtrail implement this` |
| `lean` | smallest maintainable path | `@tailtrail lean simplify this` |
| `strict` | scope may be unclear or overbuilt | `@tailtrail strict review this approach before coding` |

## 6. Review Code

Use review mode before merging, accepting generated code, or approving large diffs.

Codex:

```text
@tailtrail-review review this diff for unnecessary code
@tailtrail-review check this change for dependency, validation, and security risk
```

Other assistants:

```text
Use TailTrail Review. Find unnecessary dependencies, duplicate logic, over-broad rewrites, weakened safeguards, and missing focused checks.
```

Review output should focus on concrete findings, not style churn.

## 7. Use The Dependency Gate

Before adding or changing a package, service, framework, build tool, runtime dependency, or UI dependency, use:

```text
DEPENDENCY-GATE.md
```

Ask:

```text
Apply TailTrail's dependency gate before adding this package.
```

A dependency should be approved only when it clearly reduces risk, complexity, or maintenance burden compared with existing project capabilities.

## 8. Use AIDLC For Larger Work

Use AIDLC for broad, risky, ambiguous, multi-team, regulated, production-sensitive, or long-running work.

Initialize lifecycle artifacts in a target project:

```bash
python3 scripts/aidlc-init.py --root /path/to/project --depth standard
```

Available depths:

| Depth | Use When |
|---|---|
| `minimal` | clear, low-risk, small-scope work |
| `standard` | normal feature, bug, or refactor work |
| `comprehensive` | high-risk, multi-team, regulated, production-sensitive, or system-wide work |

Check lifecycle artifacts:

```bash
python3 scripts/aidlc-check.py --root /path/to/project
```

Use strict answer validation after `questions.md` should be complete:

```bash
python3 scripts/aidlc-check.py --root /path/to/project --strict-answers
```

Resume lifecycle work:

```text
Use TailTrail AIDLC. Resume from aidlc-docs/aidlc-state.md and load only the active stage playbook.
```

When AIDLC asks questions, each question should include:

- meaningful choices
- one recommended option
- concise reasoning for that recommendation
- `[Answer]:` for the user to approve, change, or choose another option

## 8.1. Use Short TailTrail Commands

TailTrail includes an intent expansion agent so users do not need to paste long prompts every time.

Examples:

```bash
python3 scripts/expand-intent.py "use AIDLC"
python3 scripts/expand-intent.py "use review"
python3 scripts/expand-intent.py "use AIDLC and review"
python3 scripts/expand-intent.py "use AIDLC review and handoff"
python3 scripts/expand-intent.py "use delivery flow"
python3 scripts/expand-intent.py "use risk flow"
python3 scripts/expand-intent.py "use architecture review"
python3 scripts/expand-intent.py "use dependency gate"
```

In a project installed with the Copilot pack folder, run:

```bash
python3 tailtrail/scripts/expand-intent.py "use AIDLC and review"
```

The assistant-facing instruction is simple:

```text
Use AIDLC and review.
```

When the assistant has access to TailTrail support files, it should resolve that short command through `context/intent-aliases.md` and `scripts/expand-intent.py`, then follow the expanded prompt.

Supported short commands include:

- `use TailTrail`
- `use delivery flow`
- `use risk flow`
- `use release flow`
- `use review`
- `use architecture review`
- `use security review`
- `use QA review`
- `use maintainability review`
- `use dependency review`
- `use dependency gate`
- `use AIDLC`
- `use AIDLC and review`
- `review then AIDLC`
- `use AIDLC and handoff`
- `use review and handoff`
- `use AIDLC review and handoff`
- `use handoff`
- `project learnings`
- `save tokens`

### Named Flow Catalog

Named flows bundle common TailTrail actions behind short commands.

| Flow | Short Prompt | Use When |
|---|---|---|
| Delivery | `Use delivery flow.` | A meaningful feature or bug needs planning, implementation, validation, review, and possible handoff. |
| Risk | `Use risk flow.` | The change touches security, dependencies, data integrity, rollout, production behavior, or unclear ownership. |
| Review | `Use review flow.` | You want final diff review without lifecycle overhead. |
| Handoff | `Use handoff flow.` | Work needs to move to reviewer, QA, operations, another assistant, or later continuation. |
| Release | `Use release flow.` | You need final approval notes: validation, risk, rollback/recovery, docs impact, and owner. |

Examples:

```text
Use delivery flow for this notifications feature.
```

```text
Use risk flow before changing the auth middleware.
```

```text
Use release flow to prepare this branch for approval.
```

The source guide is `context/flow-catalog.md`.

### Review Lenses

Review lenses focus TailTrail Review on one type of risk.

| Lens | Short Prompt | Focus |
|---|---|---|
| Architecture | `Use architecture review.` | Boundaries, data flow, coupling, shared abstractions, migrations, blast radius. |
| Security | `Use security review.` | Auth, authorization, secrets, input handling, escaping, dependency risk, privacy. |
| QA | `Use QA review.` | User flows, regression paths, fixtures, manual checks, automated validation. |
| Maintainability | `Use maintainability review.` | Simplicity, duplication, naming, unnecessary abstractions, ownership burden. |
| Dependency | `Use dependency review.` | Package additions, upgrades, license/security/supply-chain risk, standard-library alternatives. |

Examples:

```text
Use architecture review on this diff before I merge it.
```

```text
Use security review for this login and token change.
```

```text
Use QA review and create a validation handoff.
```

The source guide is `context/review-lenses.md`.

### AIDLC, Review, And Handoff Prompt Catalog

Use these examples when you want lifecycle planning, review, and handoff separately or together.

To see the exact current expansion in your project, run:

```bash
python3 scripts/expand-intent.py "use AIDLC and review"
```

In an installed Copilot pack:

```bash
python3 tailtrail/scripts/expand-intent.py "use AIDLC and review"
```

If your project has `.tailtrail/intent-overrides.json` or `tailtrail/intent-overrides.json`, the expansion may be customized for your team.

#### Single Feature Prompts

| Need | Short Prompt | What It Expands To |
|---|---|---|
| AIDLC only | `Use AIDLC.` | Use TailTrail AIDLC standard depth unless the task clearly calls for minimal or comprehensive depth. Create or update `aidlc-docs/` with useful task state, requirements, workflow plan, implementation plan, validation handoff, and audit notes as needed. Load only the active stage playbook. |
| Review only | `Use review.` | Use TailTrail Review. Check the diff for unnecessary dependencies, duplicate logic, over-broad rewrites, weakened safeguards, missing focused validation, and behavior risk. Lead with concrete findings. |
| Handoff only | `Use handoff.` | Create a TailTrail handoff for this work. Summarize task intent, changed files, reused code, intentionally skipped work, validation run, validation not run, remaining risk, and next owner or approval. |

Examples:

```text
Use AIDLC for this feature. Keep the lifecycle docs compact and load only the active stage.
```

```text
Use review on this diff. Focus on dependency risk, duplicated logic, weakened safeguards, and missing validation.
```

```text
Use handoff for this change. Capture changed files, validation, skipped work, remaining risk, and next approval.
```

#### Two Feature Combinations

| Need | Short Prompt | What It Expands To |
|---|---|---|
| AIDLC then Review | `Use AIDLC and review.` | Use TailTrail AIDLC first, then TailTrail Review. Update lifecycle docs only with useful task state, implement the smallest maintainable change, then review the final diff for dependency risk, duplicate logic, over-broad rewrites, weakened safeguards, and missing focused validation. |
| Review then AIDLC | `Review then AIDLC.` | Use TailTrail Review first, then TailTrail AIDLC. Review the current diff, decide what should be kept, changed, or removed, then update `aidlc-docs/` to reflect the final intended implementation path. |
| AIDLC then Handoff | `Use AIDLC and handoff.` | Use TailTrail AIDLC first, then create a TailTrail handoff. Update lifecycle docs only with useful task state, requirements, workflow plan, implementation plan, validation handoff, and audit notes as needed. Then summarize task intent, changed files, reused code, intentionally skipped work, validation run, validation not run, remaining risk, and next owner or approval. |
| Review then Handoff | `Use review and handoff.` | Use TailTrail Review first, then create a TailTrail handoff. Review the final diff for unnecessary dependencies, duplicate logic, over-broad rewrites, weakened safeguards, missing focused validation, and behavior risk. Then summarize findings, changed files, validation evidence, remaining risk, and the next owner or approval. |

Examples:

```text
Use AIDLC and review for this change. Plan the work, implement the smallest maintainable diff, then review the final diff before closeout.
```

```text
Review then AIDLC. Stabilize the current diff first, then update aidlc-docs/ to match the final implementation path.
```

```text
Use AIDLC and handoff. Keep lifecycle docs compact, then create a transfer package for the reviewer.
```

```text
Use review and handoff. Review the final diff, then prepare a compact handoff for approval.
```

#### Three Feature Combination

| Need | Short Prompt | What It Expands To |
|---|---|---|
| AIDLC, Review, then Handoff | `Use AIDLC review and handoff.` | Use TailTrail AIDLC first, TailTrail Review second, and TailTrail Handoff last. Update lifecycle docs only with useful task state, implement the smallest maintainable change, review the final diff for dependency risk, duplicate logic, over-broad rewrites, weakened safeguards, and missing focused validation, then create a compact handoff with changed files, validation evidence, skipped work, remaining risk, and next owner or approval. |

Example:

```text
Use AIDLC review and handoff for this feature. Plan and track the work, implement the smallest maintainable change, review the final diff, then create handoff notes for the reviewer.
```

#### Choosing The Right Combination

| Situation | Use |
|---|---|
| Starting a larger or risky task | `Use AIDLC.` |
| Reviewing an existing diff | `Use review.` |
| Passing work to another person, reviewer, or assistant | `Use handoff.` |
| Normal meaningful feature work | `Use AIDLC and review.` |
| Messy or inherited changes | `Review then AIDLC.` |
| Work is planned and must be transferred | `Use AIDLC and handoff.` |
| Review output must be transferred | `Use review and handoff.` |
| Feature needs lifecycle, review, and transfer | `Use AIDLC review and handoff.` |

### Customize Internal Prompts

Projects can override TailTrail's built-in expanded prompts without editing TailTrail source.

Create one of these files in the target project:

```text
.tailtrail/intent-overrides.json
tailtrail/intent-overrides.json
```

Or pass a file explicitly:

```bash
python3 scripts/expand-intent.py "use AIDLC" --overrides /path/to/intent-overrides.json
```

Use this template as the starting shape:

```text
templates/intent-overrides.json
```

Overrides can replace the prompt, files to load, files to avoid, run order, validation, and notes for a flow. Fields that are not listed keep the TailTrail default.

## 9. Use AIDLC Stage Playbooks

Stage playbooks live in:

```text
aidlc/stages/
```

Use only the active stage:

- `workspace-detection.md`: understand project shape
- `reverse-engineering.md`: understand existing brownfield behavior
- `requirements.md`: clarify requirements
- `workflow-planning.md`: plan stages and validation
- `design.md`: add design detail only when needed
- `implementation.md`: implement approved work
- `build-test.md`: validate without noisy logs
- `handoff.md`: transfer work to reviewer, ops, or another agent
- `operations.md`: deployment, rollback, monitoring, support

## 10. Use Handoff

Handoff is the compact transfer package for review, validation, operations, or another assistant.

Use handoff when:

- code is ready for review
- validation needs another owner
- work is paused or resumed later
- production or operations handoff is needed
- another assistant will continue the task

Useful files:

- `aidlc/stages/handoff.md`
- `templates/diff-handoff.md`
- `templates/validation-handoff.md`
- `templates/operations-notes.md`

Prompt example:

```text
Create a TailTrail handoff for this change: changed files, reused code, skipped work, validation, risk, and next approval.
```

## 10.1. Use Project Learnings

Project learnings are short durable facts stored outside chat.

Initialize:

```bash
python3 scripts/learnings.py init --root /path/to/project
```

Add a learning:

```bash
python3 scripts/learnings.py add --root /path/to/project --section validation "Run npm test -- auth before merging auth middleware changes."
```

Show learnings:

```bash
python3 scripts/learnings.py show --root /path/to/project
```

Default location:

```text
.tailtrail/learnings.md
```

Store only reusable facts: approved project patterns, validation commands, dependency decisions, common pitfalls, and architecture constraints. Delete stale entries.

For richer learning, use Learning Agent V2. It captures compact events, scores confidence, and promotes only reusable high-confidence patterns.

Use `LEARNING-GOVERNANCE.md` when a team needs the operating rules for capture, promotion, refresh, privacy, and review cadence.

Initialize V2:

```bash
python3 scripts/tailtrail.py learn agent init --root /path/to/project
```

Capture a scored learning event:

```bash
python3 scripts/tailtrail.py learn capture --root /path/to/project --type sonar --tags sonar,java --summary "Fixed validator cognitive complexity" --candidate "Extract named guard methods while preserving validation order." --validation-command "mvn test -Dtest=PaymentValidatorTest" --validation-outcome pass --acceptance accepted --small-focused-change --no-new-dependency --scanner-resolved
```

Search reusable learnings:

```bash
python3 scripts/tailtrail.py learn search --root /path/to/project --tags sonar,java --limit 3
```

Link a learning to current graph scope:

```bash
python3 scripts/tailtrail.py learn graph link --root /path/to/project --learning-id 20260712-abc12345 --file src/main/java/PaymentValidator.java --symbols PaymentValidator.validate --rules Sonar:S3776
```

Search graph-aware learnings:

```bash
python3 scripts/tailtrail.py learn graph search --root /path/to/project --changed src/main/java/PaymentValidator.java --tags sonar,java
```

Validate graph-aware links:

```bash
python3 scripts/tailtrail.py learn graph validate --root /path/to/project
```

Inspect and refresh learning quality:

```bash
python3 scripts/tailtrail.py learn review --root /path/to/project
python3 scripts/tailtrail.py learn review --root /path/to/project --write-result
python3 scripts/tailtrail.py learn govern --root /path/to/project
python3 scripts/tailtrail.py learn refresh recommend --root /path/to/project
python3 scripts/tailtrail.py learn refresh recommend --root /path/to/project --tags sonar,java --write-result
python3 scripts/tailtrail.py learn refresh stale --root /path/to/project --days 90
python3 scripts/tailtrail.py learn refresh apply --root /path/to/project --learning-id 20260712-abc12345 --action mark-stale --approved
```

`learn review` is the safest first governance command. It reads compact learning metadata and reports:

- weak or do-not-use events
- repeated rejected patterns
- missing validation evidence
- guardrail weakening signals
- low-confidence user overrides
- duplicate or conflicting learning candidates
- stale-pattern conflicts where a learning still looks reusable but has suppress, stale, archive, or delete refresh history
- blocking refresh actions

`learn govern` is an alias for `learn review`. It exists for users who think of this as learning governance rather than a review. It does not edit, suppress, promote, delete, or load raw prompt history.

Promote an eligible event:

```bash
python3 scripts/tailtrail.py learn promote --root /path/to/project --event-id 20260712-abc12345
```

Summarize learning history:

```bash
python3 scripts/tailtrail.py learn summarize --root /path/to/project --month 2026-07
```

Use the optional learning capture hook after meaningful work:

```bash
python3 hooks/learning-capture-hook.py "Fixed Sonar validator cognitive complexity" --root /path/to/project --candidate "Extract named guard methods while preserving validation order." --validation-command "mvn test -Dtest=PaymentValidatorTest" --validation-outcome pass --acceptance accepted
```

The hook suggests a capture command by default. It writes a learning event only with `--approved`:

```bash
python3 hooks/learning-capture-hook.py "Fixed Sonar validator cognitive complexity" --root /path/to/project --candidate "Extract named guard methods while preserving validation order." --validation-outcome pass --acceptance accepted --approved
```

Learning Agent V2 stores generated local files under `.tailtrail/`: `learning-events.jsonl`, `learning-index.md`, `learning-scores.jsonl`, `learning-policy.json`, and curated `learnings.md`. Normal tasks should load `learning-index.md` first and at most three matching curated learnings. Do not load raw event history unless the user asks for learning history or debugging.

Graph-Aware Learning adds `.tailtrail/graph-learning-index.json`. It links approved learnings to metadata such as files, symbols, scanner rule IDs, validation commands, endpoints, tables, and manifests. Navigator can surface up to three matches in the plan when the current changed files or graph scope match. These matches are advisory only: current source, scanner, CI, policy, and guardrail evidence always wins.

Learning Refresh adds `.tailtrail/learning-refresh-actions.json` and optional `.tailtrail/learning-refresh-report.md`. It recommends `keep`, `improve`, `demote`, `mark-stale`, `suppress`, `archive`, `merge`, or `delete` actions. It does not rewrite raw learning events. Approved blocking actions such as `mark-stale`, `suppress`, and `archive` prevent future automatic retrieval.

Guarded Learning UX adds `.tailtrail/learning-governance-review.md` only when `learn review --write-result` is used. Start reports and enterprise reports can recommend `learn review` when learning events exist without refresh history, blocking refresh actions exist, or learning hygiene looks noisy. This keeps learning useful without silently trusting every accepted solution.

Navigator learning behavior:

- It shows dedicated choices when learnings match: `use learnings`, `ignore learnings`, or `edit plan`.
- It explains why learning retrieval was skipped: `no index`, `tiny task`, `stale graph`, or `no matching tags/files/rules`.
- It can suggest `python3 scripts/tailtrail.py learn refresh recommend --root /path/to/project` when Phase 9.2 refresh signals appear.
- It can show a suggested `python3 hooks/learning-capture-hook.py ...` command after meaningful work.
- It never runs learning capture or refresh automatically.
- Rejection and revision capture should remain explicit: use the suggested hook command only after the user confirms what was rejected or revised and why.

Confidence bands:

- `0-39`: do not use
- `40-59`: weak historical note only
- `60-79`: candidate learning, suggest with caution
- `80-100`: trusted reusable repo pattern

User acceptance is useful but not enough. Low-confidence accepted work can be recorded as an event, but it is not promoted into curated learnings unless validation, review, repeated success, or stronger evidence raises the score.

## 10.2. Set Up Team Mode

Team mode adds lightweight repo guidance for shared projects.

Optional mode:

```bash
python3 scripts/team-init.py --root /path/to/project --mode optional
```

Required mode:

```bash
python3 scripts/team-init.py --root /path/to/project --mode required
```

Optional mode writes `.tailtrail/team-policy.md` and appends a TailTrail section to `AGENTS.md`.

Required mode also writes:

```text
.tailtrail/check-tailtrail.py
```

Run it in the target project when you want a simple pack-exists check:

```bash
python3 .tailtrail/check-tailtrail.py
```

This is intentionally lighter than global enforcement. It gives org repos a consistent adoption point without requiring a daemon or global install.

## 11. Use Token Router

Token Router chooses the smallest safe context slice.

For day-to-day usage, prefer Token Autopilot first. It decides whether routing should happen at all:

```bash
python3 scripts/token-auto.py "rename this variable"
python3 scripts/token-auto.py "review this diff for dependency risk"
python3 scripts/token-auto.py --format json "fix failing tests from this log"
```

If the request is tiny and low-risk, Token Autopilot returns `skip`. If the request is non-trivial, it routes to Token Router automatically.

Examples:

```bash
python3 scripts/route-context.py review
python3 scripts/route-context.py aidlc
python3 scripts/route-context.py handoff
python3 scripts/route-context.py auto review this diff for extra dependencies
python3 scripts/route-context.py output --format json
```

By default it writes local state to:

```text
.tailtrail/token-router-state.json
```

Use `--no-state` for a dry run:

```bash
python3 scripts/route-context.py review --no-state
```

## 12. Use Token Slicer

For broad or repeated work, start with:

```text
context/TailTrail.map.md
```

Then load one slice from:

```text
context/slices.md
```

Common slices:

- `core`: normal implementation
- `review`: code or diff review
- `aidlc`: lifecycle work
- `output`: noisy logs, test output, build output
- `cache`: stable repeated facts
- `compression`: stable non-exact bulky references

Keep exact text for source code, diffs, configs, commands, dependency versions, paths, IDs, hashes, stack traces, and security rules.

## 13. Run Benchmarks

TailTrail includes offline benchmark scenarios for local evidence.

```bash
python3 scripts/benchmark-tailtrail.py
python3 scripts/benchmark-tailtrail.py --scenario native-date-field
python3 scripts/benchmark-tailtrail.py --format json
python3 scripts/benchmark-tailtrail.py --write-result
python3 scripts/benchmark-tailtrail.py --format json > benchmarks/results/latest.json
python3 scripts/analyze-benchmark.py benchmarks/results/latest.json
python3 scripts/analyze-benchmark.py benchmarks/results/latest.json --write-result
python3 scripts/tailtrail.py benchmark efficacy
python3 scripts/tailtrail.py benchmark efficacy --format json
python3 scripts/tailtrail.py benchmark efficacy --write-result
python3 scripts/tailtrail.py efficacy run --portfolio
python3 scripts/tailtrail.py efficacy run --portfolio --strict --format json
python3 scripts/tailtrail.py efficacy run --scenario bug-fix-focused-tests
python3 scripts/tailtrail.py savings estimate --used context/slices.md --avoided ROADMAP.md USER-GUIDE.md
python3 scripts/tailtrail.py savings report --telemetry templates/token-usage-example.jsonl
```

Benchmarks compare saved baseline and TailTrail artifacts. The efficacy benchmark adds reproducible governance signals: dependency avoided, validation evidence, safeguard preservation, diff size discipline, review finding quality, and measured token telemetry when supplied. The BL-1.5 portfolio runs representative scenarios across bug fix, review, security, CI/Sonar, dependency, feature, token-heavy artifact, and learning-governance work. It reports scenario coverage, artifact checks, evidence labels, and public-claim readiness.

The behavior analyzer reads benchmark JSON, identifies missed checks or discrepancies, and recommends improvement areas. These commands do not call live models, use the network, include private project code, edit TailTrail automatically, or prove universal model/vendor performance.

Use benchmark results to decide whether a TailTrail rule is useful, noisy, or missing.

Use token savings reports only with the right evidence label:

- `savings estimate` uses local file character counts and reports estimated context reduction.
- `savings report` reads normalized telemetry from `.tailtrail/token-usage.jsonl` and reports measured savings only when records include real model/API token usage.
- If telemetry is missing, TailTrail must say exact token savings are unavailable.

## Exact Token Usage Telemetry

Use exact token telemetry when you need real before/after token results instead of approximate context estimates.

```bash
python3 scripts/tailtrail.py telemetry manual --task-id demo-001 --provider openai --model gpt-5 --baseline-input 42000 --baseline-output 3000 --tailtrail-input 18000 --tailtrail-output 2500
python3 scripts/tailtrail.py telemetry import-openai --source openai-usage.jsonl --output .tailtrail/token-usage.jsonl
python3 scripts/tailtrail.py telemetry import-claude --source claude-usage.jsonl --output .tailtrail/token-usage.jsonl
python3 scripts/tailtrail.py telemetry import-gemini --source gemini-usage.jsonl --output .tailtrail/token-usage.jsonl
python3 scripts/tailtrail.py savings report --telemetry .tailtrail/token-usage.jsonl
python3 scripts/tailtrail.py savings report --telemetry .tailtrail/token-usage.jsonl --format json
python3 scripts/tailtrail.py savings report --telemetry templates/token-usage-example.jsonl
python3 scripts/tailtrail.py report --token-telemetry .tailtrail/token-usage.jsonl
```

Use `telemetry manual` when the provider UI, logs, gateway, or benchmark notes already show token numbers. Use `telemetry import-*` when those numbers are in a local JSON or JSONL file. These commands create normalized measured records; `savings report` is still the command that calculates the before/after totals.

Provider-file import example:

```json
{
  "task_id": "demo-001",
  "model": "gpt-5",
  "baseline": {"usage": {"input_tokens": 42000, "output_tokens": 3000}},
  "tailtrail": {"usage": {"input_tokens": 18000, "output_tokens": 2500}}
}
```

The importers accept common usage names such as `usage`, `usage_metadata`, `usageMetadata`, `input_tokens`, `output_tokens`, `prompt_tokens`, `completion_tokens`, `promptTokenCount`, `candidatesTokenCount`, and `total_tokens`. They import only records that include both baseline/before and TailTrail/after usage evidence.

Telemetry record schema:

```json
{
  "mode": "measured",
  "schema_version": "1",
  "timestamp": "2026-07-13T00:00:00+00:00",
  "task_id": "sonar-fix-123",
  "provider": "your-provider",
  "model": "your-model",
  "source": "usage_metadata",
  "baseline": {
    "input_tokens": 64000,
    "output_tokens": 11000,
    "total_tokens": 75000
  },
  "tailtrail": {
    "input_tokens": 15000,
    "output_tokens": 3500,
    "total_tokens": 18500
  }
}
```

How to collect it:

1. Run or record a comparable baseline task without TailTrail's focused routing.
2. Capture the provider/model usage metadata for that run.
3. Run the TailTrail-guided version of the task with focused context, slicing, graphing, summaries, or Navigator guidance.
4. Capture the provider/model usage metadata for the TailTrail run.
5. Add one JSONL record with `baseline` and `tailtrail` token totals.
6. Or run `python3 scripts/tailtrail.py telemetry manual ...` / `telemetry import-* ...` to create that JSONL record.
7. Run `python3 scripts/tailtrail.py savings report --telemetry .tailtrail/token-usage.jsonl`.

How telemetry improves the result:

- Estimated mode asks, "How much local context did we avoid loading?"
- Measured mode asks, "How many tokens did the provider/model actually report for comparable before and after runs?"
- Measured reports include before TailTrail, with TailTrail, token difference, and percentage reduction.
- Enterprise reports can include measured totals when you pass `--token-telemetry`.
- The telemetry commands improve accuracy only when the supplied numbers came from real provider/model usage metadata.
- TailTrail does not call provider APIs, store API keys, or collect telemetry automatically.

Example-only stats from `templates/token-usage-example.jsonl`:

| Task | Before TailTrail | With TailTrail | Difference | Reduction |
|---|---:|---:|---:|---:|
| example-sonar-fix | 75,000 | 18,500 | 56,500 | 75.33% |
| example-review | 42,000 | 14,000 | 28,000 | 66.67% |

These numbers are fake sample values for schema validation and demos. Users should expect real reduction to vary by task size, model, assistant surface, prompt style, available graph/cache context, and how consistently baseline and TailTrail runs are measured. TailTrail should never promise a fixed percentage reduction.

Safety rules:

- Keep `.tailtrail/token-usage.jsonl` local unless the team explicitly agrees to share it.
- Do not include raw prompts, raw logs, secrets, PII, PHI, customer data, or source snippets.
- Use task IDs and aggregate reports for demos.
- Exact token-savings claims require measured telemetry. Estimates are useful for planning, not ROI claims.

## Code Review Graph Lite

Use Code Review Graph Lite before review or implementation when you want a compact impact map instead of broad repo scanning.

```bash
python3 scripts/review-graph.py --changed src/service/foo.py
python3 scripts/review-graph.py --changed src/service/foo.py --changed src/service/bar.py
python3 scripts/review-graph.py --changed src/service/foo.py --format json
python3 scripts/review-graph.py --root /path/to/project --changed src/service/foo.py
```

The output shows changed files, suggested read order, likely tests, likely callers, related shared helpers, nearby manifests/config, and risk tags. It is not a complete call graph. It uses simple explainable signals only: imports, file naming conventions, test proximity, local text search, and manifest/config proximity.

The Lite review graph intentionally does not use the AST/Semantic engine, vector database, model call, or background indexing service. Use `graph ast --depth v2` when you need deeper selected-file semantic metadata before implementation.

## 14. Use Examples

Examples live in:

```text
examples/
```

Use one matching example at a time:

- `native-date-field.md`: prefer native UI first
- `stdlib-csv.md`: prefer standard library parsing
- `shared-bug-fix.md`: fix shared root cause
- `preserve-guard.md`: do not remove safeguards to simplify code

## 15. Validate TailTrail Itself

After changing TailTrail files, run:

```bash
python3 scripts/check-tailtrail.py
python3 scripts/sync-adapters.py --check
python3 scripts/benchmark-tailtrail.py
python3 -m compileall -q scripts hooks
python3 -m unittest discover -s tests
```

For Codex plugin validation:

```bash
python3 /Users/vsingha7/.codex/skills/.system/plugin-creator/scripts/validate_plugin.py /path/to/TailTrail
python3 /Users/vsingha7/.codex/skills/.system/skill-creator/scripts/quick_validate.py /path/to/TailTrail/skills/tailtrail
python3 /Users/vsingha7/.codex/skills/.system/skill-creator/scripts/quick_validate.py /path/to/TailTrail/skills/tailtrail-review
```

## 16. What Not To Commit

These are local/generated and should stay ignored:

- `.tailtrail/`
- `__pycache__/`
- `.DS_Store`
- `aidlc-rules/`

## 17. Recommended Daily Workflow

1. Start with the assistant adapter for your tool.
2. For small work, use TailTrail `steady` or `lean`.
3. For risky or broad work, initialize AIDLC.
4. Use Token Router when context feels large.
5. Apply the Dependency Gate before packages.
6. Use Review before merge.
7. Create Handoff before pausing, transferring, or closing larger work.
8. Run the relevant validation commands.

## 18. Complete Feature And File Reference

Use this section when you want to know which TailTrail file matters for a daily task.

### Start Here

| File | Purpose | Use It When | How To Use |
|---|---|---|---|
| `README.md` | Short project overview. | You need a quick explanation of what TailTrail provides. | Read first, then jump to `USER-GUIDE.md` for operating steps. |
| `USER-GUIDE.md` | Complete end-user usage guide. | You are installing, configuring, or using TailTrail day to day. | Follow the setup section for your assistant, then use the feature sections as needed. |
| `AGENTS.md` | Portable default agent guidance. | Your assistant reads repository instruction files, or you want one generic file for a project. | Copy to the target project root. |
| `NOTICE.md` | Provenance and policy boundary. | Reviewers need to know whether TailTrail vendors third-party source/docs. | Keep in the repo; read during policy review. |
| `scripts/install-local.py` | Safe local setup assistant. | You are unsure which TailTrail setup path to use. | Run `python3 scripts/install-local.py --inspect`, then dry-run the chosen profile. |
| `scripts/setup-scan.py` | Read-only cloned-repo TailTrail file classifier. | A repo already contains TailTrail files from another user or team. | Run `python3 scripts/tailtrail.py setup-scan --root .` before install/update. |
| `scripts/outcome-telemetry.py` | Opt-in adoption outcome capture and summary. | You need evidence that TailTrail helped after a completed task. | Run `python3 scripts/tailtrail.py outcome capture ... --approved`, then summarize. |
| `templates/outcome-event.md` | Outcome event schema and allowed values. | You need to explain or review what outcome telemetry records. | Use as a schema reference; do not paste raw task details into it. |
| `templates/token-usage-example.jsonl` | Fake measured token telemetry sample. | You need to validate token-savings reporting or show the telemetry schema. | Run `python3 scripts/tailtrail.py savings report --telemetry templates/token-usage-example.jsonl`; do not treat sample values as expected savings. |
| `templates/tailtrail-gitignore.md` | Suggested ignore patterns for local TailTrail runtime state. | Setup scan reports missing ignore patterns. | Review entries, then add only the patterns your repo agrees to ignore. |

### Assistant Setup Files

| File | Purpose | Use It When | How To Use |
|---|---|---|---|
| `.codex-plugin/plugin.json` | Codex plugin manifest. | Using TailTrail as a Codex plugin. | Keep with `skills/`; validate with the plugin validator. |
| `skills/tailtrail/SKILL.md` | Codex implementation skill. | Coding, fixing, refactoring, dependency decisions. | Invoke `@tailtrail ...`. |
| `skills/tailtrail-review/SKILL.md` | Codex review skill. | Reviewing diffs, generated code, PRs, or risky changes. | Invoke `@tailtrail-review ...`. |
| `CLAUDE.md` | Claude project instructions. | Using Claude in a TailTrail-enabled project. | Copy or keep at target project root. |
| `.cursor/rules/tailtrail.mdc` | Cursor always-on rule. | Using Cursor. | Keep under `.cursor/rules/` in target project. |
| `.github/copilot-instructions.md` | GitHub Copilot repository instructions. | Using Copilot Chat, completions, or Copilot code review. | Install with `python3 scripts/install-copilot.py --root /path/to/project --with-tailtrail-pack`. |
| `.openai/chatgpt-instructions.md` | ChatGPT project instruction file. | Using ChatGPT with project context. | Upload/reference it in a ChatGPT project or copy into project docs. |
| `GEMINI.md` | Gemini project instructions. | Using Gemini CLI or Gemini-enabled local coding. | Copy or keep at target project root. |
| `adapters/` | Source files for assistant adapters. | Updating adapter wording. | Edit files here, then run `python3 scripts/sync-adapters.py --write`. |

### Normal Coding Features

| Feature | Files | Purpose | Day-To-Day Use |
|---|---|---|---|
| Trail Check | `AGENTS.md`, `skills/tailtrail/SKILL.md`, adapter files | Read first, reuse existing code, keep small diffs. | Ask: `Use TailTrail and make the smallest maintainable change.` |
| Modes | `skills/tailtrail/SKILL.md` | Adjust how aggressively TailTrail challenges scope. | Use `steady`, `lean`, or `strict` in the prompt. |
| Review | `skills/tailtrail-review/SKILL.md`, `context/change-impact.md` | Find unnecessary dependencies, duplicate logic, broad rewrites, weakened safeguards. | Ask: `Use TailTrail Review on this diff.` |
| Dependency Gate | `DEPENDENCY-GATE.md` | Prevent unnecessary package/service ownership. | Ask: `Apply the dependency gate before adding this package.` |
| Guardrails | `GUARDRAILS.md` | Prevent unsupported claims, unsafe edits, false validation claims, and bad token-saving choices. | Use for non-trivial, risky, review-heavy, dependency-sensitive, lifecycle-driven, or unclear work. |
| Governance Sync | `GOVERNANCE.md`, `scripts/sync-governance.py` | Keep repeated behavior text aligned across `AGENTS.md`, adapters, and guardrail layers. | Run `python3 scripts/tailtrail.py governance check`; after editing `GOVERNANCE.md`, run `governance sync` and adapter sync. |
| Local Policy | `tailtrail-policy.md`, `.tailtrail/policy-overrides.json`, `scripts/policy-check.py` | Add repo-specific commands, validation expectations, ownership, dependency approval, restricted folders, and security notes. | Run `python3 scripts/tailtrail.py policy init --root . --with-overrides`, then edit and check it. |
| Examples | `examples/` | Calibrate judgment with small patterns. | Read one matching example, not the whole folder. |

### AIDLC Features

| File Or Folder | Purpose | Use It When | How To Use |
|---|---|---|---|
| `AIDLC.md` | Main lifecycle map. | Work is broad, risky, ambiguous, regulated, multi-team, or long-running. | Initialize `aidlc-docs/`, then follow the active phase. |
| `aidlc/stages/README.md` | Stage order and loading rule. | Starting or resuming lifecycle work. | Read after `aidlc-docs/aidlc-state.md`. |
| `aidlc/stages/workspace-detection.md` | Identify project shape and commands. | Starting AIDLC in a new repo. | Use before requirements/planning. |
| `aidlc/stages/reverse-engineering.md` | Understand existing brownfield behavior. | Existing code is unfamiliar or behavior is unclear. | Trace current flow before requirements/design. |
| `aidlc/stages/requirements.md` | Clarify functional, non-functional, and explicit constraints. | Scope or acceptance criteria are unclear. | Create/update `aidlc-docs/requirements.md`. |
| `aidlc/stages/workflow-planning.md` | Plan stages, units, files, validation, approvals. | Before standard/comprehensive implementation. | Create/update `aidlc-docs/workflow-plan.md`. |
| `aidlc/stages/design.md` | Add design detail only when needed. | New boundaries, APIs, data, infra, or NFRs are involved. | Create/update `aidlc-docs/design.md` or `nfr-notes.md`. |
| `aidlc/stages/implementation.md` | Implement approved work. | Requirements and plan are ready. | Read exact source, keep focused diff, update handoff. |
| `aidlc/stages/build-test.md` | Capture validation evidence. | Running build/test/lint/typecheck. | Use `templates/validation-handoff.md`. |
| `aidlc/stages/handoff.md` | Transfer work to reviewer, ops, another assistant, or future you. | Work pauses, moves to review, or changes owner. | Fill `diff-handoff`, `validation-handoff`, or `operations-notes`. |
| `aidlc/stages/operations.md` | Deployment, rollback, monitoring, support. | Production handoff is in scope. | Fill `templates/operations-notes.md`. |
| `aidlc/extensions/security-baseline.md` | Security-sensitive checklist. | Auth, secrets, input, user data, config, dependencies. | Use with AIDLC or review. |
| `aidlc/extensions/testing-baseline.md` | Focused validation checklist. | Behavior changes or risk is non-trivial. | Use before closeout. |

### AIDLC Templates

| Template | Purpose | Output Location In Target Project |
|---|---|---|
| `templates/aidlc-state.md` | Current phase, stage, next step, risks. | `aidlc-docs/aidlc-state.md` |
| `templates/aidlc-audit.md` | Durable decisions, approvals, generated artifacts. | `aidlc-docs/audit.md` |
| `templates/requirements.md` | Requirements, assumptions, non-goals, acceptance criteria. | `aidlc-docs/requirements.md` |
| `templates/question-file.md` | File-based questions with choices, recommendation, reasoning, and answer slots. | `aidlc-docs/questions.md` |
| `templates/stage-gate.md` | Approval checkpoint. | `aidlc-docs/stage-gate.md` or named gate file |
| `templates/workflow-plan.md` | Stage and implementation-unit plan. | `aidlc-docs/workflow-plan.md` |
| `templates/implementation-plan.md` | Approved construction plan. | `aidlc-docs/implementation-plan.md` |
| `templates/change-brief.md` | Pre-change alignment. | `aidlc-docs/change-brief.md` |
| `templates/diff-handoff.md` | Review handoff after code changes. | `aidlc-docs/diff-handoff.md` |
| `templates/validation-handoff.md` | Build/test/lint/typecheck evidence. | `aidlc-docs/validation-handoff.md` |
| `templates/vulnerability-summary.md` | Exact-safe vulnerability finding summary. | `aidlc-docs/vulnerability-summary.md` or review notes |
| `templates/vulnerability-remediation.md` | Remediation handoff after user asks for a fix. | `aidlc-docs/vulnerability-remediation.md` or security handoff |
| `templates/operations-notes.md` | Deployment, rollback, monitoring, support notes. | `aidlc-docs/operations-notes.md` |
| `templates/evidence-note.md` | Files read, commands run, checks, assumptions, skipped areas, residual risk. | `aidlc-docs/evidence-note.md` or handoff notes |
| `templates/risk-callout.md` | Risk area, evidence, safeguards, validation, rollback, approval. | `aidlc-docs/risk-callout.md` or review notes |

### Token Saving Features

| Feature | Files | Purpose | Day-To-Day Use |
|---|---|---|---|
| Token Autopilot | `TOKEN-AUTOPILOT.md`, `scripts/token-auto.py`, `hooks/token-autopilot-hook.py` | Decide whether token routing is worth using. | `python3 scripts/token-auto.py "review this diff"` |
| Token Router | `context/token-router.md`, `scripts/route-context.py` | Choose one route and one slice. | `python3 scripts/route-context.py review` |
| Intent Expander | `context/intent-aliases.md`, `scripts/expand-intent.py`, `templates/intent-overrides.json` | Turn short user phrases into full TailTrail workflow prompts. | `python3 scripts/expand-intent.py "use AIDLC and review"` |
| Token Slicer | `TOKEN-SLICER.md`, `context/TailTrail.map.md`, `context/slices.md` | Load only the relevant TailTrail context. | Start with the map, then one slice. |
| Prompt Compression Profiles | `python3 scripts/tailtrail.py profile ...` | Pick compact guidance bundles such as lean, review, testing, AIDLC, security, or handoff. | `python3 scripts/tailtrail.py profile review` |
| Token Budget Coach | `python3 scripts/tailtrail.py budget ...` | Estimate context budgets, learn from approved local budget outcomes, and tell Navigator when to ask for budget escalation. | `python3 scripts/tailtrail.py budget estimate "fix validation bug" --changed src/service/foo.py` |
| Context Receipts | `python3 scripts/tailtrail.py receipt ...` | Capture approved loaded/avoided context after work for local token evidence. | `python3 scripts/tailtrail.py receipt capture --task "fix bug" --loaded src/foo.py --avoided ROADMAP.md --approved` |
| Token Savings | `scripts/token-savings.py`, `templates/token-savings-report.md` | Estimate local context reduction or report measured savings from provided telemetry without overstating precision. | `python3 scripts/tailtrail.py savings estimate --used context/slices.md --avoided ROADMAP.md USER-GUIDE.md` |
| Output Slicer | `templates/tool-summary.md` | Summarize noisy command/tool output. | Use for build logs, test failures, MCP/API/browser output. |
| Context Map | `context/project-map.md`, `context/change-impact.md` | Avoid broad source scans. | Fill when project area or blast radius is unclear. |
| Code Graph Mapper | `context/code-graph-mapper.md`, `scripts/code-graph-mapper.py`, `templates/code-graph-map.md` | Reuse freshness-checked metadata for heavy source reads. | `python3 scripts/tailtrail.py graph map --changed src/service/foo.py` |
| Cache/Prune | `context/cache-index.md`, `context/prune-rules.md` | Avoid rediscovering stable facts and carrying stale context. | Use for long-running or repeated work. |
| Compression Policy | `context/compression-policy.md` | Define what can be compressed and what must stay exact. | Use before any future visual/image compression. |

### Scripts

| Script | Purpose | Example |
|---|---|---|
| `scripts/check-tailtrail.py` | Validate package shape, expected files, skill metadata, adapter sync, placeholders. | `python3 scripts/check-tailtrail.py` |
| `scripts/sync-adapters.py` | Sync adapter sources to tool-facing files. | `python3 scripts/sync-adapters.py --write` |
| `scripts/sync-governance.py` | Check or rewrite only the marked governance blocks copied from `GOVERNANCE.md`. | `python3 scripts/tailtrail.py governance check` |
| `scripts/install-local.py` | Inspect TailTrail and choose a small safe setup profile for a target project. | `python3 scripts/install-local.py --target /path/to/project --profile full --dry-run` |
| `scripts/install-copilot.py` | Install Copilot instructions and optional TailTrail pack into target project. | `python3 scripts/install-copilot.py --root /path/to/project --with-tailtrail-pack` |
| `scripts/update-copilot.py` | Safely refresh an existing Copilot TailTrail pack while preserving or backing up local edits. | `python3 scripts/update-copilot.py --root /path/to/project --dry-run` |
| `scripts/update-tailtrail.py` | General updater entry point for installed TailTrail packs. | `python3 scripts/update-tailtrail.py --root /path/to/project --dry-run` |
| `scripts/team-init.py` | Add optional or required TailTrail team guidance to a target project. | `python3 scripts/team-init.py --root /path/to/project --mode optional` |
| `scripts/learning-agent.py` | Capture compact scored events, search token-safe learnings, and promote only confidence-gated patterns. | `python3 scripts/learning-agent.py search --tags sonar,java --limit 3` |
| `scripts/graph-learning.py` | Link curated learnings to graph metadata and search by current graph scope. | `python3 scripts/graph-learning.py search --changed src/service/Foo.java --tags sonar,java` |
| `scripts/learning-refresh.py` | Recommend learning refresh actions and record approved stale/suppress/archive decisions. | `python3 scripts/learning-refresh.py recommend --root .` |
| `scripts/quality-loop.py` | Capture approved TailTrail behavior events, summarize workflow fit, and propose reviewable improvements. | `python3 scripts/quality-loop.py review --month 2026-07` |
| `scripts/tailtrail-report.py` | Generate a local enterprise report from TailTrail quality, learning, refresh, AIDLC, and token evidence. | `python3 scripts/tailtrail-report.py --month 2026-07` |
| `scripts/learnings.py` | Create, append, or show `.tailtrail/learnings.md`. | `python3 scripts/learnings.py add --section validation "Run focused test before merge"` |
| `scripts/navigator.py` | Recommend the smallest useful TailTrail workflow for a goal. | `python3 scripts/navigator.py "fix Sonar issue" --changed src/service/foo.py` |
| `scripts/policy-check.py` | Initialize and validate local TailTrail policy files. | `python3 scripts/policy-check.py check --root . --with-overrides` |
| `scripts/aidlc-init.py` | Create `aidlc-docs/` artifacts in a target project. | `python3 scripts/aidlc-init.py --root /path/to/project --depth standard` |
| `scripts/aidlc-check.py` | Check target project AIDLC artifact shape. Add `--strict-answers` when question files must be complete. | `python3 scripts/aidlc-check.py --root /path/to/project` |
| `scripts/analyze-benchmark.py` | Analyze benchmark JSON and recommend TailTrail improvement areas. | `python3 scripts/analyze-benchmark.py benchmarks/results/latest.json` |
| `scripts/benchmark-tailtrail.py` | Score offline baseline and TailTrail artifacts in benchmark scenarios. | `python3 scripts/benchmark-tailtrail.py --format json` |
| `scripts/code-graph-mapper.py` | Create, check, and refresh metadata-only graph cache for heavy source-read work. | `python3 scripts/code-graph-mapper.py map --changed src/service/foo.py` |
| `scripts/review-graph.py` | Generate a compact review impact graph from changed files. | `python3 scripts/review-graph.py --changed src/service/foo.py` |
| `scripts/vulnerability-scan.py` | Recommend vulnerability scanner commands without running them. | `python3 scripts/vulnerability-scan.py --changed package.json` |
| `scripts/vulnerability-run.py` | Run one exact approved vulnerability command and save output. | `python3 scripts/vulnerability-run.py --approved --command "npm audit"` |
| `scripts/vulnerability-summary.py` | Summarize local vulnerability scanner output into a finding list. | `python3 scripts/vulnerability-summary.py --file audit.log` |
| `scripts/tailtrail.py` | Unified local command surface for common TailTrail actions. | `python3 scripts/tailtrail.py help` |
| `scripts/expand-intent.py` | Expand short TailTrail phrases into full workflow prompts with optional overrides. | `python3 scripts/expand-intent.py "use AIDLC and review"` |
| `scripts/token-auto.py` | Automatically skip or route token-saving strategy. | `python3 scripts/token-auto.py "rename variable"` |
| `scripts/prompt-profile.py` | Show prompt compression profiles. | `python3 scripts/tailtrail.py profile testing` |
| `scripts/token-budget-coach.py` | Estimate and learn local context budgets from approved events. | `python3 scripts/tailtrail.py budget profile` |
| `scripts/context-receipt.py` | Capture or summarize context receipts. | `python3 scripts/tailtrail.py receipt summary` |
| `scripts/token-savings.py` | Estimate context reduction and report measured savings only from real usage telemetry. | `python3 scripts/token-savings.py estimate --used context/slices.md --avoided ROADMAP.md` |
| `scripts/route-context.py` | Route explicit task type to load/avoid guidance. | `python3 scripts/route-context.py handoff` |

### Hooks

| Hook | Purpose | Use When |
|---|---|---|
| `hooks/tailtrail-lifecycle-hook.py` | Expand short commands and combine them with token autopilot. | Your assistant/host can inject compact lifecycle context. |
| `hooks/learning-capture-hook.py` | Suggest or approved-capture Learning Agent V2 events from compact post-task summaries. | Run after meaningful work, not on every raw prompt. |
| `hooks/token-autopilot-hook.py` | Hook-capable automatic token decision. | Your assistant/host can call a script before injecting context. |
| `hooks/token-router-hook.py` | Direct compact router injection. | You already know routing is needed. |
| `hooks/README.md` | Hook usage and boundaries. | Setting up host-level automation. |

### Project Maintenance Files

| File | Purpose | Use It When |
|---|---|---|
| `DESIGN.md` | Current architecture and purpose of files. | Changing TailTrail itself. |
| `ROADMAP.md` | Implemented phases and future scope. | Planning next TailTrail features. |
| `.gitignore` | Excludes local/generated files. | Keep `.tailtrail/`, caches, `.DS_Store`, and `aidlc-rules/` out of commits. |

## 19. Which Feature Should I Use?

| Situation | Use |
|---|---|
| Small bug fix | TailTrail `steady` or `lean` |
| Unclear or possibly overbuilt request | TailTrail `strict` |
| New dependency requested | `DEPENDENCY-GATE.md` |
| Generated code needs review | TailTrail Review |
| Large feature | AIDLC `standard` |
| Regulated/high-risk/multi-team work | AIDLC `comprehensive` |
| Work paused or moved to review | Handoff |
| Prompt may load too much context | Token Autopilot |
| Large logs or tool output | `templates/tool-summary.md` |
| Another assistant will continue | Handoff plus adapter file |
