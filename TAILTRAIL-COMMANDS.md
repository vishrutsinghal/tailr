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
python3 scripts/tailtrail.py do "fix Sonar issue and prepare PR"
python3 scripts/tailtrail.py run "fix Sonar issue and prepare PR"
python3 scripts/tailtrail.py "fix Sonar issue and prepare PR"
python3 scripts/tailtrail.py start "fix Sonar issue and prepare PR"
python3 scripts/tailtrail.py start "fix Sonar issue and prepare PR" --verbose
python3 scripts/tailtrail.py planning show --root . --run-id <run-id>
python3 scripts/tailtrail.py planning activate --root . --run-id <run-id> --approved
python3 scripts/tailtrail.py planning discuss --root . --run-id <run-id> --question "Why was service.py selected?"
python3 scripts/tailtrail.py planning explain --root . --run-id <run-id> --question "Why was service.py selected?"
python3 scripts/tailtrail.py planning discussion-show --root . --run-id <run-id>
python3 scripts/tailtrail.py planning decision-show --root . --run-id <run-id>
python3 scripts/tailtrail.py planning investigate --root . --run-id <run-id> --path src/service.py --approved-read-only
python3 scripts/tailtrail.py planning investigation-show --root . --run-id <run-id>
python3 scripts/tailtrail.py planning revise --root . --run-id <run-id> --changes '[{"kind":"scope-remove","requirement_uid":"REQ-03","path":"src/api.py","reason":"Internal service support only."}]' --approved-proposal
python3 scripts/tailtrail.py planning revision-show --root . --run-id <run-id> --revision 2
python3 scripts/tailtrail.py planning revision-approve --root . --run-id <run-id> --revision 2 --approved
python3 scripts/tailtrail.py planning aidlc-standard --root . --run-id <run-id> --approved-proposal
python3 scripts/tailtrail.py planning aidlc-standard-approve --root . --run-id <run-id> --revision 2 --approved
python3 scripts/tailtrail.py planning feature-controls-show --root . --run-id <run-id>
python3 scripts/tailtrail.py planning feature-controls-propose --root . --run-id <run-id> --changes '[{"feature":"Behaviour Harness","value":"selected","reason":"Customer journey proof is needed."}]' --approved-proposal
python3 scripts/tailtrail.py planning feature-controls-approve --root . --run-id <run-id> --revision 2 --approved
python3 scripts/tailtrail.py planning authority-show --root . --run-id <run-id>
python3 scripts/tailtrail.py governance check
python3 scripts/tailtrail.py spec-kit policy check --root .
python3 scripts/tailtrail.py spec-kit detect --root .
```

Use these when a user is new to TailTrail, onboarding a team, or checking whether a project has a source checkout or installed pack.

## Interactive Plan Mode (IP-0)

While a Start run is awaiting approval, `planning discuss` and `planning
explain` answer from the saved Planning Lock and immutable Start Report, then
record a compact sanitized receipt under the existing run. Answers contain a
direct response, evidence label, alternative, risk, plan impact, and next
choice. They do not inspect project source, rerun a graph, run tests/scanners,
change the plan, or persist raw chat. `discussion-show` returns saved metadata.
`planning explain` renders Markdown by default; use `--format json` for a host
adapter or a saved-artifact integration.

An awaiting Lite AIDLC run may move to **Standard AIDLC** without discarding
its run ID or original plan. Ask the host to “switch to Standard AIDLC”, then
review the versioned mode-switch proposal. Approving it begins the Standard
AIDLC Requirements stage only; answering and approving those requirements is a
separate gate before implementation. The switch refuses active, non-Lite, and
Intent Bridge source-owned runs.

IP-1 can explain saved file/requirement decisions, selected controls, AIDLC
mode, validation, drift posture, token estimate, risk, and approval boundaries.
It returns `unknown` rather than inventing a fresh code fact. A rejection routes
to the existing feedback flow; an AIDLC request routes to AIDLC Requirements;
pasted errors and unrelated chat stay outside Interactive Plan Mode. Approved
runs are rejected because the approved anchor and normal execution controls
apply.

`planning investigate` is the deeper, explicitly approved path. Every `--path`
must already be a saved planned impact path; it refuses absolute, parent, binary,
credential-like, missing, and unplanned paths. It reads at most 12 UTF-8 files
of 512 KiB each, records hashes/line counts/symbol names only, and checks an
existing Code Graph Mapper cache for freshness without refreshing or rebuilding
it. The resulting receipt records no raw source, raw question, commands, test
result, source mutation, or plan change.

## Interactive Plan Revision (IP-3)

`planning revise` is the only pre-approval path that changes a saved plan. It
accepts a bounded JSON list of material changes (`scope-add`, `scope-remove`,
`requirement-add`, `requirement-remove`, `requirement-update`, or
`proof-update`) and requires a stable requirement ID/display ID plus a short
reason. It creates `revision-vN.json` and a pending revision pointer under the
same run; the original `start-report-v1.json` is never overwritten.

While a revision is pending, ordinary `planning approve` and `planning activate`
refuse to run. Review the delta, then use `revision-approve` for that exact
version. This writes a versioned report snapshot, freezes its requirements into
the existing immutable anchor workflow, and activates the same run. A stale v1
approval cannot activate v2.

## AIDLC and Intent Bridge authority routing (IP-4)

`planning revise` deliberately does **not** create a competing TailTrail plan
revision when the approved requirement authority is AIDLC or Intent Bridge.
Instead it records a sanitized authority-route receipt under the same run:

- TailTrail Lite/Standard AIDLC-bound work starts or resumes the existing AIDLC
  Requirements stage, carrying only the bounded material-change reasons.
- Full AIDLC work routes requirement refinement to the verified official
  Requirements stage. A material architecture/design request is explicitly
  labelled `official-aidlc-design`, to be completed by the configured official
  host stage before another requirement boundary can be approved.
- Intent Bridge wording stays source-owned. TailTrail records an amendment
  request and requires an updated, explicitly imported source snapshot rather
  than rewriting imported requirements or the immutable Start report.

Use `planning authority-show` (or the read-only MCP
`planning_authority_show`) to inspect the authority, route, request context,
next action, and no-source-change boundary. The normal AIDLC or Intent Bridge
approval/amendment flow then remains the only path back to an approved anchor.

## Interactive Plan hosts and evaluation (IP-5)

The Codex, Copilot, and Claude instruction surfaces now share the same
Interactive Plan boundary: a question or plan-update request keeps the current
run ID and never implies source inspection, implementation, or approval.
`planning decision-show` (and read-only MCP `planning_decision_show`) gives a
compact view of the lock, saved discussion count, active/pending revision, and
AIDLC/Intent Bridge authority routes.

```bash
python3 scripts/tailtrail.py adapters conformance
python3 scripts/tailtrail.py adapters runtime prepare --root . --host codex
python3 scripts/tailtrail.py adapters runtime report --root . --host codex
python3 scripts/tailtrail.py eval scenario report --scenario interactive-plan-mode
```

Instruction conformance and real-host runtime conformance remain distinct.
Generated host instructions are checked locally; a host becomes runtime-passed
only after fresh sanitized receipts cover every portable runtime scenario.

## Optional Spec Kit bridge policy (SK-0)

SK-0 establishes the local security and ownership contract. SK-1 adds safe,
read-only workspace discovery. SK-2 adds an explicit, versioned import into
TailTrail state. None of these phases executes or modifies a Spec Kit project.

```bash
python3 scripts/tailtrail.py spec-kit policy check --root .
python3 scripts/tailtrail.py spec-kit policy init --root .
python3 scripts/tailtrail.py spec-kit policy contracts
python3 scripts/tailtrail.py spec-kit detect --root .
python3 scripts/tailtrail.py spec-kit status --root .
python3 scripts/tailtrail.py spec-kit inspect --root . --feature 014-order-amendment
python3 scripts/tailtrail.py spec-kit import --root . --feature 014-order-amendment --mode review
python3 scripts/tailtrail.py start "Use Intent Bridge feature 014-order-amendment to plan order amendments" --intent-feature 014-order-amendment
python3 scripts/tailtrail.py spec-kit bridge --root . --feature 014-order-amendment
python3 scripts/tailtrail.py spec-kit slices show --root . --run-id <run-id>
python3 scripts/tailtrail.py spec-kit slices assert-active --root . --run-id <run-id> --requirement-uid <uid>
python3 scripts/tailtrail.py spec-kit evidence plan --root . --run-id <run-id>
python3 scripts/tailtrail.py spec-kit evidence record --root . --run-id <run-id> --checkpoint .tailtrail/runs/<run-id>/checkpoints/checkpoint-1.json --architecture <assessment.json>
python3 scripts/tailtrail.py spec-kit amendment check --root . --run-id <run-id>
python3 scripts/tailtrail.py spec-kit amendment propose --root . --run-id <run-id>
python3 scripts/tailtrail.py spec-kit amendment approve --root . --run-id <run-id> --approved
python3 scripts/tailtrail.py spec-kit amendment recovery --root . --run-id <run-id>
python3 scripts/tailtrail.py spec-kit converge --root . --run-id <run-id>
python3 scripts/tailtrail.py spec-kit ci-ingest --root . --run-id <run-id> --input ci-receipts.json --approved
python3 scripts/tailtrail.py spec-kit ci-gate --root . --run-id <run-id> --format json
python3 scripts/tailtrail.py spec-kit observe --root . --run-id <run-id>
python3 scripts/tailtrail.py spec-kit release --root . --run-id <run-id>
python3 scripts/tailtrail.py spec-kit governance --root . --run-id <run-id>
python3 scripts/tailtrail.py spec-kit evaluate --root . --run-id <run-id> --baseline baseline.json
```

`policy check` uses the committed safe template when a project policy is absent.
`policy init` copies that template to `.tailtrail/spec-kit-policy.json` without
overwriting an existing file. The policy requires source locks, versioned
snapshots, material-amendment approval, read-only artifact handling, and no raw
prompt, log, or artifact retention.

`detect`, `status`, and `inspect` examine only the approved `.specify/` and
`specs/` artifact paths. They do not run `specify`, create `.tailtrail/`, create
a Planning Lock, import source, or write any workspace file. An absent Spec Kit
workspace returns `not-detected`; an unsafe or incomplete selected feature is
reported as `incompatible` with paths and fingerprints only.

`import` is explicit and writes only normalized, immutable TailTrail evidence
under `.tailtrail/spec-kit/sources/<feature>/`. It never copies source Markdown
or runs `specify`. An identical fingerprint returns `already-imported`; a source
change creates the next `vN` snapshot without replacing earlier evidence.

For SK-3, name a previously imported feature in `tailtrail start` with
`--intent-feature <feature>` (or the exact phrase `Intent Bridge feature <feature>`
in the goal). Navigator uses its imported requirement IDs and wording as the
planning boundary, carries source references into the approved anchor, and does
not create a parallel TailTrail or AIDLC requirement questionnaire. If the source
changed since the import, planning/activation stop for a future amendment review.

After approval, SK-4 automatically writes the source lock, requirement mapping,
task-slice mapping, and amendment-state records beneath the active run. Only the
first bounded slice is active; use `slices assert-active` before executing a
requirement and `slices advance --approved` after its verified completion.

## Which Command Should I Use?

| User situation | Use command | Prompt alternative | Why |
|---|---|---|---|
| I want to confirm TailTrail is installed and reachable. | `python3 scripts/tailtrail.py hello`, `tailtrail hello`, or `hello tailtrail` | `Hello TailTrail. Confirm this repo can use TailTrail and show the install location.` | Fast smoke check that prints the TailTrail location. |
| I have a real task and do not know which TailTrail feature applies. | `python3 scripts/tailtrail.py do "task"`, `python3 scripts/tailtrail.py start "task"`, or `python3 scripts/tailtrail.py "task"` | `Use TailTrail for this task: <task>. Start with Navigator, show the recommended workflow, and wait for approval before implementation.` | Compact one-command entry point with workflow selection, review/Meta-Harness next steps, key commands, and metrics. It creates a Planning Lock and saved Start Report; it does not implement—even if the task wording also says “implement” or “set up.” Activate the returned run with `planning activate` after approval. `do` is the easiest daily form; `start` is the explicit backend command; free-form input routes to `start`. Use `--verbose` for the full plan. |
| I paused after `start` and need one lean reminder. | `python3 scripts/tailtrail.py next` | `Use TailTrail next. Read current local state and recommend exactly one next action without running scanners, editing files, or capturing learnings.` | Secondary resume command. Use after `start` when you paused and want a lean reminder of the single next action. |
| I only want a workflow plan. | `python3 scripts/tailtrail.py guide "task"` | `Run TailTrail Navigator for this task: <task>. Show the plan only; do not implement until I approve.` | Navigator plan without the extra Start report. |
| I know the changed or target file. | `python3 scripts/tailtrail.py graph --changed path/to/file` | `Use TailTrail Code Graph for <path/to/file>. Show likely callers, tests, helpers, and read order before changing code.` | Finds likely callers, tests, helpers, and read order. |
| I have CI, build, test, lint, or Sonar output. | `python3 scripts/tailtrail.py ci summarize --file log.txt` or `python3 scripts/tailtrail.py sonar summarize --file sonar.log` | `Use TailTrail CI/Sonar Intelligence on this pasted output. Summarize exact failures, likely impacted files, and next validation steps.` | Compacts noisy evidence without losing exact failure lines. |
| I want to know which local checks are available. | `python3 scripts/tailtrail.py quality scan --root .` | `Use TailTrail Quality Signal Scanner. Recommend local lint, test, Sonar-like, and vulnerability checks, but do not run anything without approval.` | Recommends checks without running them. |
| I need precise unit or regression test guidance. | `python3 scripts/tailtrail.py test plan --changed path/to/file` | `Use TailTrail Test Precision Planner for <path/to/file>. Give focused test cases in plain English and likely commands.` | Suggests likely test files, cases, helpers, and focused validation commands without running tests. |
| I want TailTrail to review code. | `python3 scripts/tailtrail.py start "review my changes"` or `python3 scripts/tailtrail.py review` | `Use TailTrail to review my changes. If scope is unclear, ask whether to review uncommitted changes, branch vs main, a path, or the full repo.` | Navigator chooses the safest review scope; the direct command exists for repeatable local review. |
| I changed guardrail detection and want false-positive evidence. | `python3 scripts/tailtrail.py guardrail precision --strict` | `Use TailTrail guardrail precision. Run the committed false-positive baseline and report precision, recall, false-positive rate, and any below-threshold rule.` | Checks labeled guardrail fixtures before enforcement gets stricter. |
| I need to run one approved local check. | `python3 scripts/tailtrail.py quality run --approved --command "..."` | `Run this one approved TailTrail quality command only: <exact command>. Do not run extra scans or builds.` | Runs only one exact allowlisted command. |
| I changed shared governance wording. | `python3 scripts/tailtrail.py governance check` | `Use TailTrail governance check. Verify shared TailTrail behavior text is synchronized and tell me what differs.` | Verifies marked governance blocks match `GOVERNANCE.md`. |
| I want a smaller first-run installed pack. | `python3 scripts/tailtrail.py install copilot --target /path/to/project --surface core` | `Install TailTrail Core for this project: minimal Navigator, start, guardrails, governance, adapters, and quick docs only.` | Installs the Core surface instead of the full Extended pack. |
| I want to upgrade a Core pack later. | `python3 scripts/tailtrail.py install upgrade-to-extended --target /path/to/project` | `Upgrade this TailTrail Core install to Extended. Add missing files only and do not delete user content.` | Adds Extended-only TailTrail files in place. |
| I want to know which surface is installed. | `python3 scripts/tailtrail.py install status --target /path/to/project` | `Show TailTrail install status for this project, including installed surface and what Extended upgrade would add.` | Reads the install manifest and reports Core vs Extended. |
| I want to record whether TailTrail helped. | `python3 scripts/tailtrail.py outcome capture ... --approved` | `Use TailTrail outcome capture for this completed task. Record acceptance, validation result, review result, time-saved band, and learning quality only after I approve.` | Records one compact approved adoption outcome. |
| I want Navigator to start from safe repo facts. | `python3 scripts/tailtrail.py bootstrap snapshot --root . --write-result` | `Use TailTrail Bootstrap Snapshot for this repo. Capture safe repo/runtime facts before Navigator planning, without reading source bodies or executing project code.` | Creates `.tailtrail/bootstrap-snapshot.json` for local pre-task planning. |
| My task names another repository and I need to verify the editable target first. | `python3 scripts/tailtrail.py target resolve "task" --root /path/to/project` | `Use TailTrail Target Workspace Resolver. Verify the one editable target before planning; do not fall back to the current workspace.` | Read-only target resolution. Explicit `--root` wins; it reports verified, inaccessible, unmapped, or ambiguous without creating a Planning Lock. |
| I need to declare a target plus references, design, specs, or CI evidence. | `python3 scripts/tailtrail.py target roles --root /path/to/project --reference-root /path/to/reference --design-reference https://figma.example/design --summary` | `Use TailTrail Input Roles. Keep the target editable only after approval and treat every supplied reference, design, requirement, and evidence input as read-only.` | Creates a deterministic role registry and bounded metadata-only summaries; it does not fetch external references. |
| My Codex, Copilot, or Claude workspace differs from the prompt path. | `python3 scripts/tailtrail.py target host-workspace --host copilot --workspace /path/to/project` | `Use TailTrail Host Workspace Adapter. Verify the host-selected workspace before planning; do not fall back to the current directory if it is unavailable.` | Local-only path classification and mapping receipt. Start also accepts `--host`, `--host-workspace`, and `--host-platform`; explicit `--root` still wins. |
| My team restricts which repositories may be edited. | `python3 scripts/tailtrail.py target policy --root /path/to/project --policy .tailtrail/enterprise-target-policy.json` | `Use TailTrail Enterprise Target Policy. Check the selected root against the approved local roots, aliases, and restrictions before planning.` | Read-only deterministic inspection. Start accepts `--enterprise-policy`, `--target-alias`, and `--actor`; it writes a sanitized run-local receipt only after a Planning Lock is created. |
| I am changing a UI screen and must preserve the current product look. | `python3 scripts/tailtrail.py ui discover --root . --changed src/pages/Example.tsx` | `Use TailTrail for this UI change. Preserve existing repository UI conventions and plan first.` | Read-only discovery of reusable components, comparable screens, styles/tokens, frontend packages, and any existing visual-test setup. UI wording or frontend/style paths automatically select the UI Consistency Guardrail in Start. |
| I want to know whether TailTrail itself behaved well. | `python3 scripts/tailtrail.py harness review --root .` | `Use TailTrail Harness Review locally. Check workflow fit, context fit, validation fit, metric confidence, learning fit, scanner/security fit, and code precision fit. Do not share or commit metadata.` | Reviews local TailTrail harness behavior without model calls or git sharing. |
| I want an MCP-capable assistant to call TailTrail directly. | `python3 scripts/tailtrail.py mcp tools` then `python3 scripts/tailtrail.py mcp serve` | `Use TailTrail MCP. Inspect local TailTrail artifacts first; use a controlled check only with explicit approval.` | Exposes Navigator, run/evidence/recovery inspection, and one approval-gated repository-control runner. |
| I cloned a repo that already has TailTrail files. | `python3 scripts/tailtrail.py setup-scan --root .` | `Use TailTrail setup scan for this repo. Classify shared TailTrail files, local runtime state, overrides, and safe next setup steps.` | Classifies shared project context versus local user state. |
## Governance Sync

```bash
python3 scripts/tailtrail.py governance check
python3 scripts/tailtrail.py governance check --strict
python3 scripts/tailtrail.py governance inventory
python3 scripts/tailtrail.py governance sync
python3 scripts/sync-governance.py check
python3 scripts/sync-governance.py inventory
python3 scripts/sync-governance.py sync
```

Use this when changing repeated TailTrail behavior text in `AGENTS.md`, adapter files, root assistant files, `ROADMAP.md`, or `context/guardrail-layers.md`.

`GOVERNANCE.md` owns the short repeated governance block between `<!-- tailtrail-governance:start -->` and `<!-- tailtrail-governance:end -->`. `GUARDRAILS.md` remains the full behavior contract. The sync command rewrites only marked blocks, so normal prose around those blocks stays human-edited.

Run `governance check --strict` before committing documentation or adapter changes. Run `governance inventory` when you need a file-by-file drift table. Run `governance sync` after editing `GOVERNANCE.md`, then run `python3 scripts/sync-adapters.py --write` so tool-facing adapter files match their sources. Demo snapshots under `demo-project-layout/` are intentionally excluded from normal sync.

## Feature Registry

```bash
python3 scripts/tailtrail.py registry list
python3 scripts/tailtrail.py registry list --surface core
python3 scripts/tailtrail.py registry list --status implemented
python3 scripts/tailtrail.py registry show meta-harness
python3 scripts/tailtrail.py registry show meta-harness --format json
python3 scripts/tailtrail.py registry surfaces
python3 scripts/tailtrail.py registry workflow review
python3 scripts/tailtrail.py registry workflow sonar --format json
python3 scripts/tailtrail.py registry mcp
python3 scripts/tailtrail.py registry mcp --format json
python3 scripts/tailtrail.py registry validate
python3 scripts/tailtrail.py registry validate --strict
python3 scripts/tailtrail.py registry drift
python3 scripts/tailtrail.py registry drift --strict
```

Use this when adding or changing TailTrail features, commands, scripts, docs, tests, install surfaces, MCP exposure, approval posture, or evidence labels. The registry is read-only in V1: maintainers edit `tailtrail-registry.json` directly, then run `registry validate --strict`.

Default `registry validate` is advisory and exits `0` with a drift report. `registry validate --strict` exits non-zero when the registry drifts from the source tree, such as an unowned command, orphan script, missing file, duplicate script claim, unresolved dependency, implemented feature without tests, or invalid evidence label.

Use `registry drift` after feature changes to catch release hygiene drift that pure registry validation cannot see: missing command docs, stale roadmap wording, missing changelog updates, and unsupported public-claim wording. Default mode is advisory. Use `--strict` after the false-positive rate is acceptable for release gating.

`registry workflow ...` projects the features, commands, docs, scripts, and evidence labels for a workflow such as `review`, `qa`, `sonar`, `security`, or `harness`. Navigator can use this projection for registry-backed route explanations without making the registry a runtime decision engine.

`registry mcp` projects the MCP-safe read-only tool surface from registry metadata. A feature may be write-capable overall while its MCP tool remains read-only, such as `code-graph-mapper` exposing only the read-only `graph_map` tool.

## Installation Smoke Check

```bash
python3 scripts/tailtrail.py hello
tailtrail hello
```

Use this after install, update, clone, or launcher setup. It is read-only and fast. It confirms the command resolved, prints whether TailTrail is running as a source checkout or installed pack, and points to `doctor` for full validation. In an assistant chat, the ASCII banner and installation result must be returned verbatim as the entire response—no narration, todo update, or added doctor suggestion.

## MCP Server

```bash
python3 scripts/tailtrail.py mcp tools
python3 scripts/tailtrail.py mcp doctor
python3 scripts/tailtrail.py mcp serve
```

Use this only for MCP-capable assistants. `mcp tools` lists the inspection-first tool contract, `mcp doctor` validates schemas and safety boundaries, and `mcp serve` starts the stdio server for an MCP client. The server exposes existing Navigator/review/evaluation tools plus `ledger_state`, `anchor_show`, `harness_checkpoint_show`, `completion_feedback_show`, `profile_view`, `validation_receipt_show`, `git_readiness`, and `recovery_boundary_show`. `harness_control_check` is the sole controlled tool and requires explicit `approved: true`.

MCP support improves tool access and consistency. It does not automatically complete development, edit source, commit, push, apply recovery, upload telemetry, or bypass user approval. Non-MCP assistants should keep using `start`, `guide`, `guard check`, `eval scenario`, and the Markdown instruction files.

### Run-local execution evidence through MCP

MCP hosts can record one factual, requirement-linked event at a time with the
approval-gated `execution_evidence_record` tool and inspect the saved stream
with `execution_evidence_show`. The record tool requires the exact approved run
ID, `approved: true`, and an event accepted by the same schema as
`tailtrail execution-evidence record`. It records host-visible facts only; it
does not run the named command or turn a conversational claim into evidence.
After evidence is saved, use `tailtrail closure finalize --root . --run-id
<run-id>` to feed selected Harnesses through the normal fail-closed closure
path.

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
- local TailTrail install files
- local runtime state
- generated-but-shareable metadata
- unknown TailTrail-like files

It also reports missing `.gitignore` patterns, installed-pack status, warnings, and safe next commands such as policy check, setup JSON review, install dry-run, or update dry-run.

Default guidance:

- Keep `.tailtrail/`, managed `tailtrail/`, assistant setup files, AIDLC setup docs, local telemetry, quality/vulnerability run output, task starts, and local install manifests out of normal commits.
- Commit only reviewed `tailtrail-meta/` metadata by default.
- If a repo intentionally wants shared TailTrail setup files, remove the matching strict-local `.gitignore` entries only after team review.
- Update installed packs only after a dry run and explicit review.
- Review generated graph/cache metadata before sharing it.
- Run `python3 scripts/tailtrail.py guard check --enforce` before pushing after installing or updating TailTrail files.

## Start

```bash
python3 scripts/tailtrail.py do "fix Sonar issue and prepare PR"
python3 scripts/tailtrail.py run "fix Sonar issue and prepare PR"
python3 scripts/tailtrail.py "fix Sonar issue and prepare PR"
python3 scripts/tailtrail.py start "fix Sonar issue and prepare PR"
python3 scripts/tailtrail.py start "fix Sonar issue" --changed src/service/foo.py
python3 scripts/tailtrail.py start "triage GHSA in package.json" --changed package.json --format json
python3 scripts/tailtrail.py start "fix validation bug and add tests" --changed src/service/foo.py --verbose
```

Use `do`, `start`, or free-form task input as the preferred first command for non-trivial work. They run Navigator, then add a compact task report with:

- a Start Here section with the immediate next step
- a compact approval menu with review, approve, edit, and focused validation prompts
- Navigator-first workflow selection
- selected TailTrail features and hidden counts for extra details
- likely impacted files to inspect first
- key suggested commands
- post-change Review guidance
- Meta-Harness quick/confidence/shared-metadata dry-run guidance
- approximate token posture from focused files versus intentionally avoided broad docs
- guarded learning and setup posture summary

Default output is intentionally compact. Use `--verbose` when you need the full decision menu, detailed learning/setup posture, and the full approval-first Navigator plan.

The token posture is a local estimate from file character counts. It is useful for demos and planning, but it is not exact model/API token usage. Learning quality is advisory only; surfaced learnings still require `use learnings`, `ignore learnings`, or `edit plan`.

## Next

```bash
python3 scripts/tailtrail.py next
python3 scripts/tailtrail.py next --root .
python3 scripts/tailtrail.py next --format json
```

Use `next` after `start` when work paused and you want one deterministic continuation. It reads the latest local Start plan artifact when present, read-only Git state, and local posture markers, then returns exactly one primary action plus at most three alternatives. It does not run scanners, edit files, mutate Git, call the network, or capture learning.

Common examples:

```bash
python3 scripts/tailtrail.py start "fix null pointer in claim mapper" --changed src/main/java/com/acme/claims/ClaimMapper.java
python3 scripts/tailtrail.py start "fix Sonar cognitive complexity issue" --changed src/main/java/com/acme/payment/PaymentValidator.java
python3 scripts/tailtrail.py start "add retry handling for payment capture"
python3 scripts/tailtrail.py start "add a CSV parsing library for import files"
python3 scripts/tailtrail.py start "triage GHSA vulnerability in package.json" --changed package.json
```

## Navigator

Short explicit Navigator modes keep discovery, planning, and edit authorization separate:

```bash
python3 scripts/tailtrail.py navigator "Phase 1"
python3 scripts/tailtrail.py navigator plan "tailtrail-implementation-backlog.md Phase 1"
python3 scripts/tailtrail.py navigator implement "tailtrail-implementation-backlog.md Phase 1"
```

`plan` approval authorizes only a detailed proposal. `implement` still needs an explicit implementation approval before files may change. When a phase name appears in multiple planning documents, Navigator asks which document is intended rather than guessing.

## Canonical Local State (Phase 1)

```bash
python3 scripts/tailtrail.py ledger init --run-id claim-validation --goal "reject zero claim amounts"
python3 scripts/tailtrail.py anchor draft --run-id claim-validation --input proposal.json
python3 scripts/tailtrail.py anchor approve --run-id claim-validation
python3 scripts/tailtrail.py ledger state --run-id claim-validation
```

These commands write only `.tailtrail/runs/<run-id>/`: an append-only event ledger, immutable approved anchor, requirement matrix, and selected graph-evidence receipts. They do not edit project source. A rejected matrix must include feedback for every requirement; after the second material rejection, the returned state requires AIDLC Requirements mode.

## Sanitized Failure Artifacts (Foundation)

```bash
python3 scripts/tailtrail.py failure record --root . --run-id claim-validation --source agent-command --error-code TEST_FAILURE --command-label "focused pytest" --project-frame "claim validation" --exit-code 1
python3 scripts/tailtrail.py failure show --root . --run-id claim-validation
python3 scripts/tailtrail.py failure intake --root . --run-id claim-validation --source user-pasted --error-code ACCESS_DENIED --command-label "terraform plan" --project-frame "backend setup" --exit-code 1
python3 scripts/tailtrail.py failure diagnose --root . --run-id claim-validation --failure-id failure-0001 --classification permission --confidence supported-hypothesis --hypothesis "The active identity lacks the required permission." --proposed-action bounded-correction
python3 scripts/tailtrail.py failure map --root . --run-id claim-validation --failure-id failure-0001 --requirement-uid req-... --evidence-kind approved-path --checkpoint-delta unchanged --reason "The approved validation path still fails." --suspected-path src/claims.py
python3 scripts/tailtrail.py failure correction-route --root . --run-id claim-validation --failure-id failure-0001 --max-cycles 2
python3 scripts/tailtrail.py failure readiness --root . --run-id claim-validation
```

`failure record` requires an approved Planning Lock and writes one local artifact
under `.tailtrail/runs/<run-id>/execution-failures/`. It accepts structured,
bounded metadata only: a stable error code, safe command label, project frame,
optional exit code, and an optional project-relative evidence file with its
SHA-256. Raw logs, pasted error bodies, full commands, prompts, secrets, and
environment values are neither accepted nor stored. `failure show` is read-only.

`failure intake` creates an immediate receipt. Without an explicit approved run,
it returns `not-attached` and writes nothing; it never guesses or creates a run.
With an approved run, it stores a sanitized intake receipt and ledger event.
`failure diagnose` records a provisional classification and authority decision
only. Infrastructure, dependency, permission, and data corrections are blocked
for explicit authority; other corrections remain a proposal until later scope
and drift evidence exists. No command here edits source, retries a command, or
changes infrastructure.

`failure map` requires an approved anchor and an approved requirement UID. It
creates a SHA-256 fingerprint from only five sanitized fields: requirement UID,
classification, stable error code, project frame, and command label. A drift
link is created only with an explicit approved-path, architecture, behaviour,
preservation, or scope evidence basis. `failure correction-route` delegates the
cycle limit to Harness Convergence and returns one of bounded correction,
recovery, or replan. It records the route only—no source patch or retry is run.

Resolution and automatic correction remain intentionally deferred to later
failure-flow phases.

`failure readiness` combines the existing read-only setup scan with the saved
failure lifecycle. It reports `ready`, `needs-correction`, or `blocked`; it
cannot approve implementation or change setup. Completion reports and the
workflow dashboard now show sanitized unresolved-failure status and will not
report a run complete while an execution failure remains unresolved.

## Requirement Completion Harness (Phase 2 V1-V4)

```bash
python3 scripts/tailtrail.py harness plan --run-id example-change --controls controls.json --changed src/service.py
python3 scripts/tailtrail.py harness check --run-id example-change --controls controls.json --changed src/service.py --approved --output results.json
python3 scripts/tailtrail.py harness checkpoint --run-id example-change --changed src/service.py --results results.json
python3 scripts/tailtrail.py harness completion-review --run-id example-change --output review.json
python3 scripts/tailtrail.py harness completion-report --root . --run-id example-change
python3 scripts/tailtrail.py harness feedback --root . --run-id example-change --review review.json --output feedback.json
python3 scripts/tailtrail.py harness impact-map --root . --run-id example-change --changed src/service.py
python3 scripts/tailtrail.py harness converge --root . --run-id example-change --requirement-uid req-... --state unchanged --max-cycles 2
python3 scripts/tailtrail.py harness template --root . --run-id example-change --requirement-uid req-... --template harness-templates.json
```

`impact-map` is local AST evidence only; its candidate callers/tests are not a
completion claim. `converge` records one bounded correction cycle and routes to
an existing recovery mode or an approval-required replan. `template` only adds
controls and proof tiers to the approved requirement contract.

Controls are repository-native command arrays and require `--approved` to run.
The harness stores actual state per checkpoint, classifies requirement-level
evidence drift, and creates only one correction packet at a time. It does not
edit code, run an unbounded retry loop, or treat a single passing test as proof
of every approved requirement.

Add `--run-id <run-id>` to `harness plan`, `harness check`, and `harness
validation-receipt` to retain complete normalized artifacts under the Phase 1
run directory. Checkpoints and completion gates always write there. The
append-only ledger records event type, requirement UID, result summary, and an
artifact pointer; it does not copy raw source into the ledger.

`completion-report` writes one compact, end-of-task artifact under
`.tailtrail/runs/<run-id>/completion-reports/`. It aggregates—not replaces—the
approved anchor, checkpoint, completion review/gate, Architecture Fitness,
Behaviour Harness, validation receipts, drift state, recovery boundary, the
Start token estimate, and run-linked measured token telemetry. Its Markdown
output has two tables: requirement delivery (`REQ` status, saved proof, and
requirement-linked drift) and TailTrail control status (selected harnesses,
recovery, continuity/learning, and token posture). Missing evidence or telemetry
is shown as `unavailable`; it is never shown as a pass or measured cost. Add
`--show` to read the most recent saved report without writing.

### Closure input contract and recorder (Phases 0–1)

Validate a proposed requirement-linked closure input without writing artifacts
or executing any command:

```bash
tailtrail closure validate --root . --input closure-input.json
```

The input must name the approved run, repository-relative changed paths, one or
more approved requirement UIDs per receipt, evidence tier, exact one-line
command, outcome, environment, and asserted behaviour. Validation rejects raw
command output, unknown requirement IDs, unsafe paths, and token telemetry that
is not linked to the same run ID.

When closure has an incomplete requirement, unresolved drift, missing/failed
evidence, or an unresolved execution failure, the command also writes a
sanitized run-local `learning-observations/completion-learning-v1.json` and one
deduplicated candidate in `.tailtrail/learning-events.jsonl`. It records only
requirement IDs, classifications, statuses, artifact references, and changed
paths—never source, raw prompts, or logs. The candidate is **not** auto-promoted
or allowed to override current evidence, policy, or user instructions.

After the Planning Lock is approved, persist the same validated evidence with:

```bash
tailtrail closure record --root . --input closure-input.json
tailtrail closure record --root . --run-id <run-id>
```

The recorder is deliberately not an executor. It never runs the commands named
in the input, edits source, commits, pushes, deploys, or creates a final
completion claim. It fans each multi-requirement receipt into requirement-linked
local receipt artifacts, creates a fingerprinted checkpoint, runs the existing
Completion Review and Requirement Completion Gate, and returns the saved
artifact pointers plus the next required action. Replaying identical input for
the same run safely reuses the prior closure record.

Finalize an approved recorded run with its selected deterministic controls:

```bash
tailtrail closure finalize --root . --run-id <run-id>
```

You can pass `--input closure-input.json` to record that input idempotently
before finalization. The finalizer runs only selected local Architecture Fitness,
Behaviour, and Maintainability assessments, reads saved higher-tier receipts,
and writes the Completion Report. It never runs the command text in a receipt,
provisions an environment, deploys, or performs recovery. When Behaviour
Harness is selected but no declared scenario evidence exists, it writes a
fail-closed assessment and the Completion Report remains `evidence-incomplete`.

For an incomplete finalized run, TailTrail automatically creates one bounded
same-run correction packet. You can read or recreate that idempotent handoff:

```bash
tailtrail closure correct --root . --run-id <run-id>
```

It identifies the first requirement-scoped gap, records a sanitized fingerprint,
uses the existing convergence guard, and renders a Context Continuity packet.
The same fingerprint is reused rather than consuming another correction cycle.
It does not edit code, retry a command, recover Git state, or amend the anchor.

### Guarded positive learning and calibrated closure evaluation (Phase 4)

```bash
tailtrail closure learn --root . --run-id <run-id> --accepted-by user
tailtrail closure learn --root . --run-id <run-id> --accepted-by trusted-ci
tailtrail closure evaluate --root . --run-id <run-id> --baseline baseline.json
```

For the normal user flow, use the single close-out command first:

```bash
tailtrail closure close --root .
tailtrail closure close --root . --decision accept-user
tailtrail closure close --root . --decision wait-ci
tailtrail closure close --root . --decision accept-ci --ci-receipt .tailtrail/runs/<run-id>/ci-ingestion/ingestion-1.json
```

The first call resolves the one approved run with recorded closure evidence,
finalizes it, shows the Completion Report, and returns an acceptance menu. It
does not create learning or evaluation yet. After the user selects
`accept-user`, the second call derives a transparent delivery-start baseline
from the approved anchor, creates candidate-only learning, and writes paired
evaluation automatically. `wait-ci` and `reopen` retain evidence without
creating positive learning. `accept-ci` is available only after a linked saved
CI-ingestion artifact for the same run provides provenance and receipts; it then
creates candidate-only learning and paired evaluation with `trusted-ci` as the
acceptance source.

`closure learn` never infers acceptance. It creates one sanitized, run-local
success-pattern **candidate** only when the saved Completion Report is complete,
all requirements and receipts pass, and no unresolved drift or execution failure
remains. It does not promote the candidate into reusable instructions.

`closure evaluate` reads saved artifacts only. With `--baseline`, it records
requirement-completion, drift, and test-status deltas. Without one, it writes a
clearly labelled run observation—not a baseline comparison or a quality claim.

### First-run guidance and workflow dashboard

Every successful `install-local.py` profile installation now finishes with a
read-only smoke check and one short first action. Run it again at any time:

```bash
python3 scripts/first-run.py --target /path/to/project --profile codex-plugin
```

The check verifies the expected installed guidance/skill files and TailTrail's
local `hello` command. It does not edit the target, run its tests, or invoke an
agent. Codex users should start with `Using TailTrail Navigator, plan "<task>"
before implementation.`

The workflow dashboard is a local, read-only view of an existing run:

```bash
python3 scripts/tailtrail.py harness dashboard --root . --run-id example-change
python3 scripts/tailtrail.py harness dashboard --root . --run-id example-change --format html --output tailtrail-dashboard.html
```

It reads the approved anchor, latest checkpoint, requirement states, drift,
review/gate posture, recovery availability, and any Completion Report. HTML is
rendered only when an explicit `--output` path is supplied; it never starts a
server, runs checks, edits source, or applies recovery.

## Real evaluation dataset

```bash
python3 scripts/tailtrail.py eval dataset validate
python3 scripts/tailtrail.py eval dataset report
```

The delivery dataset contains 12 paired, realistic multi-file task fixtures. It
reports requirement completion, missed caller/test cases, correction cycles,
scope drift, false interventions, and developer review time for baseline versus
TailTrail outcomes. The current V1 values are curated local fixtures that prove
the evaluation contract and aggregation pipeline—not live model performance.

## Safe Git checkpoints and recovery (Phase 4)

```bash
# Read-only; requires a named branch, current HEAD, committer identity, and a clean worktree.
python3 scripts/tailtrail.py harness git-readiness --root .

# Changes branch only with explicit approval and creates tailtrail/<run-id>.
python3 scripts/tailtrail.py harness boundary init --root . --run-id example-change --expected-path src/service.py --approved
python3 scripts/tailtrail.py harness boundary activate --root . --run-id example-change --requirement-uid req-...
python3 scripts/tailtrail.py harness boundary checkpoint --root . --run-id example-change --requirement-uid req-... --approved

# Recovery never resets the repository. It plans first, then restores verified
# active tracked paths only when explicitly approved.
python3 scripts/tailtrail.py harness recovery plan --root . --run-id example-change
python3 scripts/tailtrail.py harness recovery apply --root . --run-id example-change --approved
```

Mode A refuses dirty starting worktrees, detached HEAD, missing commit identity,
untracked/renamed active files, and paths outside the approved requirement
boundary. Validated requirement commits are retained under local immutable refs
at `refs/tailtrail/<run-id>/<requirement-uid>`; no remote push occurs.

### Conflict classification and reconciliation (Phase 6 V1)

```bash
python3 scripts/tailtrail.py harness reconcile plan --root . --run-id example-change --task-patch .tailtrail/task.patch
python3 scripts/tailtrail.py harness reconcile apply --root . --run-id example-change --task-patch .tailtrail/task.patch --approved
```

Reconciliation only applies an exact supplied task-owned patch when Git proves
its reverse applies cleanly. It preserves unrelated changed paths, records their
fingerprints, and classifies same-hunk overlap as a no-write bounded
reconciliation plan. It never restores a whole file or resets the repository.

## Program Delivery Harness (Phase 7 V1)

```bash
python3 scripts/tailtrail.py harness program init --root . --run-id claims-program --plan program-plan.json --hands-free --approved
python3 scripts/tailtrail.py harness orchestrate next --root . --run-id claims-program
python3 scripts/tailtrail.py harness program-checkpoint --root . --run-id claims-program --feature F-01 --state validated --evidence receipt.json
python3 scripts/tailtrail.py harness program amend --root . --run-id claims-program --plan amended-program-plan.json --reason "approved refactor discovery" --approved
```

Program Delivery is available only through explicit `--hands-free` activation.
It coordinates approved feature order, dependencies, correction budget, pause and
resume state; it does not edit code, execute tests, or bypass feature/material
approval gates.

## Mode B Recovery And Diagnosis (Phase 6 V1)

```bash
python3 scripts/tailtrail.py harness mode-b capture --root . --run-id example-change --requirement-uid req-... --approved
python3 scripts/tailtrail.py harness mode-b seal --root . --run-id example-change --requirement-uid req-... --approved
python3 scripts/tailtrail.py harness mode-b plan --root . --run-id example-change --requirement-uid req-...
python3 scripts/tailtrail.py harness mode-b apply --root . --run-id example-change --requirement-uid req-... --approved
python3 scripts/tailtrail.py harness diagnose --root . --run-id example-change --failure-artifact assessment-1.json --failure-artifact assessment-2.json
```

Mode B is an explicit dirty-worktree fallback. It captures only the active
requirement's approved path baselines, seals its exact task delta, and restores
only paths that still match the sealed post-change fingerprint. Later overlap is
always a no-write recovery plan. The diagnoser starts only after repeated local
failure evidence and returns hypotheses/replan guidance—not source edits.

## Architecture Fitness Harness (Phase 6 V1)

```bash
python3 scripts/tailtrail.py harness architecture --root . --run-id example-change --changed src/service.py --profile architecture-profile.json
```

This deterministic local assessment compares changed paths with the approved
requirement matrix and checks approved/profile rules for required caller paths,
protected paths, and forbidden Python imports. It records requirement-linked
scope or architecture drift; it does not edit source or claim an inference is
architectural proof.

## Behaviour Harness (Phase 6 V1)

```bash
python3 scripts/tailtrail.py harness behavior --root . --run-id example-change --scenarios behavior-scenarios.json --evidence behavior-evidence.json
```

Behaviour Harness verifies requirement-linked user-flow scenarios against exact
local receipts. A scenario needs matching requirement UID, tier, asserted
behavior, and passing outcome; missing integration/E2E proof remains incomplete.

## Maintainability Harness (Phase 6 V1)

```bash
python3 scripts/tailtrail.py harness maintainability --root . --run-id example-change --changed src/service.py --changed tests/test_service.py
```

Maintainability Harness records deterministic approved-scope and test-only
change findings, then labels duplicate definitions and possible specialised
single-use abstractions as advisory local-AST signals. It does not edit source,
run tests, or claim that an advisory signal is a defect. The latest local
assessment is also available to an MCP host through
`maintainability_assessment_show`.

## Evidence-Aware Testing (Phase 3 V1-V5)

```bash
python3 scripts/tailtrail.py harness testing-profile validate --profile testing-profile.json
python3 scripts/tailtrail.py harness validation-receipt --requirement-uid req-... --tier unit --command "python -m unittest" --outcome pass --environment local --asserted-behavior "behavior" --output receipt.json
python3 scripts/tailtrail.py harness requirement-completion --run-id example-change --receipts receipts.json
python3 scripts/tailtrail.py harness tier-select --root . --run-id example-change --profile testing-profile.json --changed src/service.py
python3 scripts/tailtrail.py harness ci-ingest --root . --run-id example-change --input saved-ci-results.json
python3 scripts/tailtrail.py harness flaky --root . --run-id example-change --test-id tests/test_service.py::test_submit --outcome fail
python3 scripts/tailtrail.py harness evidence-metrics --root . --run-id example-change --receipts receipts.json
```

Tier selection only uses the approved contract and repository-declared profile.
CI ingestion reads a supplied local artifact; it never calls CI. Flaky tracking
preserves failures, while evidence metrics report receipt completeness—not a
probability of correctness or deployment authorization.

Testing profiles contain repository-owned tier commands, prerequisites, approval
requirements, environments, and cleanup. The completion gate reports missing,
blocked, unavailable, or insufficient evidence; it never upgrades unit proof to
integration, E2E, infrastructure, or release proof.

## Higher-Tier Testing And Release Confidence (Phase 8 V1)

```bash
python3 scripts/tailtrail.py harness higher-tier plan --profile testing-profile.json --tier contract
python3 scripts/tailtrail.py harness higher-tier run --root . --run-id example-change --profile testing-profile.json --tier contract --requirement-uid req-... --asserted-behavior "API contract remains compatible" --approved
python3 scripts/tailtrail.py harness release-confidence --root . --run-id example-change --receipts receipts.json
python3 scripts/tailtrail.py harness phase8 journey --root . --run-id example-change --input journeys.json
python3 scripts/tailtrail.py harness phase8 contracts --root . --run-id example-change --input openapi.json
python3 scripts/tailtrail.py harness phase8 lifecycle --root . --run-id example-change --input lifecycle.json --approved
python3 scripts/tailtrail.py harness phase8 deployment --root . --run-id example-change --input deployment-plan.json
python3 scripts/tailtrail.py harness phase8 release-policy --root . --run-id example-change --policy release-policy.json --receipts receipts.json
python3 scripts/tailtrail.py harness phase8 calibration --root . --run-id example-change --input real-run-metrics.json
```

## Advanced Runtime Boundaries

```bash
python3 scripts/tailtrail.py harness advanced graph --root . --run-id example-change --input agent-graph.json
python3 scripts/tailtrail.py harness advanced cloud --root . --run-id example-change --input declared-cloud-commands.json --approved --remote-approved
python3 scripts/tailtrail.py harness advanced live-eval --root . --run-id example-change --input model-result.json --approved
python3 scripts/tailtrail.py harness advanced claims --root . --run-id example-change --input claims.json
```

The graph command records bounded roles but does not spawn agents. Cloud commands
must be repository-owned and require two approvals. Live model evaluation is
never default. Claim auditing rejects unmeasured quality, time, and token claims.

## Context Continuity Harness (V1-V3)

```bash
python3 scripts/tailtrail.py harness continuity render --root . --run-id example-change --requirement-uid req-...
python3 scripts/tailtrail.py harness continuity render --root . --run-id example-change --requirement-uid req-... --policy templates/context-continuity-policy.example.json
python3 scripts/tailtrail.py harness continuity show --root . --run-id example-change --sequence 1
python3 scripts/tailtrail.py harness continuity calibrate --root . --run-id example-change --input saved-interventions.json
python3 scripts/tailtrail.py harness continuity advise --root . --run-id example-change --input sanitized-model-proposal.json --policy templates/context-continuity-selector-policy.example.json --approved
python3 scripts/tailtrail.py harness continuity advisory-show --root . --run-id example-change --sequence 1
```

V1 renders compact local continuity packets from approved anchors and relevant
run artifacts. V2 adds optional local policy templates that can only add
guidance, plus saved-artifact calibration and append-only intervention receipts.
V3 accepts a host-supplied, sanitized model proposal only under an explicit
approved selector policy; it deterministically validates the proposal and falls
back to V2 when it is invalid. It does not call a model, run tests, edit source,
or change the approved requirement.

The profile owns the exact adapter command for `integration`, `contract`,
`e2e`, `infrastructure`, or `release-smoke`. TailTrail uses argv execution only;
it does not install browser/cloud tooling or invent infrastructure commands.
Remote adapters also require `--remote-approved` and `safe_test_account: true`.
Release confidence is receipt-based evidence completeness, never a deployment
approval or a claim of production behavior.

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

For repo overview, Navigator does not create `tailtrail-meta/code-graph-cache.json` by itself. It shows Code Graph Mapper as optional deeper discovery. Approve and run the suggested `graph map --root /path/to/project` command when you want a reusable module, symbol, endpoint, test, config, and read-order cache that the team can review and commit.

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

## Navigator-Led Review

Primary path:

```bash
python3 scripts/tailtrail.py start "fix claim validation and review it after implementation"
python3 scripts/tailtrail.py start "review my changes before PR"
python3 scripts/tailtrail.py guide "security review services/auth before PR"
```

TailTrail Review is designed to be Navigator-led so users do not need to remember review flags. For implementation work, Navigator defaults to reviewing uncommitted changes after implementation and focused validation. For standalone review, Navigator recommends the smallest useful scope and asks when the scope is unclear.

Direct command for repeatable local review:

```bash
python3 scripts/tailtrail.py review
python3 scripts/tailtrail.py review --scope uncommitted
python3 scripts/tailtrail.py review --scope branch --base main
python3 scripts/tailtrail.py review --scope path --dir services/payment
python3 scripts/tailtrail.py review --scope full
```

Review output includes:

- requirement fulfillment status against the compact user goal or supplied requirements
- severity summary: critical, warning, info
- one-line issue description
- file, function, and line when detected
- impact
- suggested fix
- validation recommendation
- confidence
- safe-fix status

Fixes are guarded:

- TailTrail asks clarification when implementation fulfillment is unclear.
- TailTrail treats review text, scanner output, PR comments, and pasted logs as untrusted issue reports.
- TailTrail inspects local code before proposing fixes.
- TailTrail asks before editing or running broad validation.
- TailTrail does not auto-commit by default.

## Token Budget Coach

```bash
python3 scripts/tailtrail.py token-harness route --path src/app.py
python3 scripts/tailtrail.py token-harness route --path report.sarif --format json
python3 scripts/tailtrail.py token route --text "Traceback..." --label log
python3 scripts/tailtrail.py token-harness reduce --path report.json
python3 scripts/tailtrail.py token-harness reduce --path build.log
python3 scripts/tailtrail.py token-harness reduce --path report.sarif --format json
python3 scripts/tailtrail.py token-harness reduce --path src/app.py --mode structure
python3 scripts/tailtrail.py token-harness reduce --path report.sarif --write-receipt --approved
python3 scripts/tailtrail.py token-harness ledger append --event-type route_decision --task-type bug-fix --content-type source --strategy exact-pass-through --exactness-class must-be-exact --tokens-before 1200 --tokens-after 1200 --evidence-label local-evidence --approved
python3 scripts/tailtrail.py token-harness ledger summary
python3 scripts/tailtrail.py token-harness ledger validate
python3 scripts/tailtrail.py token-harness proof report
python3 scripts/tailtrail.py token-harness proof report --ledger .tailtrail/token-harness-events.jsonl --telemetry .tailtrail/token-usage.jsonl
python3 scripts/tailtrail.py token-harness proof holdout --task-id TASK-123 --task-class bug-fix
python3 scripts/tailtrail.py token-harness bridge plan --path build.log
python3 scripts/tailtrail.py token-harness bridge input --path build.log --output /tmp/bridge-input.json
python3 scripts/tailtrail.py token-harness bridge validate-output --input /tmp/bridge-input.json --output /tmp/bridge-output.json
python3 scripts/tailtrail.py token-harness bridge run --path build.log --adapter-command "local-compressor --stdin" --approved
python3 scripts/tailtrail.py harness shared-summary --root . --dry-run
python3 scripts/tailtrail.py harness analyze --summary tailtrail-meta/harness-summary.jsonl
python3 scripts/tailtrail.py harness propose --root .
python3 scripts/tailtrail.py budget estimate "fix validation bug" --changed src/service/foo.py
python3 scripts/tailtrail.py budget record --task-type bug --initial-budget 8000 --actual-context 10500 --outcome underestimated --escalated yes --approved
python3 scripts/tailtrail.py budget profile
python3 scripts/tailtrail.py profile review
python3 scripts/tailtrail.py receipt capture --task "fix validation bug" --profile review --loaded src/service/foo.py --avoided ROADMAP.md --approved
python3 scripts/tailtrail.py receipt capture --task "fix Sonar issue" --loaded src/App.java --loaded-exactness must-be-exact --loaded-strategy exact-pass-through --preserve "line numbers" --route-source token-harness --reduction-strategy graph-first-plus-exact-files --approved
python3 scripts/tailtrail.py receipt summary
python3 scripts/tailtrail.py receipt retrieve --path src/App.java
python3 scripts/tailtrail.py savings import --source usage.jsonl --output .tailtrail/token-usage.jsonl
```

Use Token Harness Router when you have a file, pasted text, log, JSON, scanner output, source file, diff, dependency manifest, or document and want TailTrail to decide how exact it must remain before any token-saving step. TH-1 is read-only: it classifies content and recommends a safe strategy, but it does not compress, summarize, write receipts, append a ledger, call models, call APIs, or claim token savings.

Use Token Harness Reducers when you want a compact structured view of large JSON/tool output, logs, scanner reports, or source symbols. Reducers keep retrieval commands, block protected exact content, and require `--approved` before writing receipts or ledger events.

Use Token Harness Ledger when you want durable local evidence that a token strategy was chosen or context receipt evidence exists. Ledger writes require `--approved`, use local JSONL, and do not store raw prompts, source, logs, secrets, pricing, or exact model/API savings claims.

Use Token Harness Proof when you need a defensible evidence label. It reports `estimated`, `local-evidence`, `measured`, or `benchmark-measured` and blocks measured claims unless complete token telemetry and confidence checks pass.

Use Token Harness Bridge only when a repo policy explicitly enables an approved local compression adapter. The bridge can reduce safe bulky artifacts such as logs, documentation, scanner output, JSON, and tool output. It blocks source, diffs, config, dependency manifests, lock files, security policy, secrets, unknown content, and must-be-exact material before the adapter runs.

Bridge flow:

1. `bridge plan` checks eligibility.
2. `bridge input` emits deterministic adapter JSON.
3. `bridge validate-output` checks an adapter response.
4. `bridge run --approved` runs a local adapter and falls back safely if validation fails.

TailTrail does not bundle a compressor, call a network service, manage credentials, or act as an HTTP proxy.

Use Meta-Harness Token Feedback when maintainers want to see whether repeated token strategies correlate with weak validation, proof gaps, low reductions, holdout gaps, or exactness mismatches. It uses sanitized categorical shared metadata and creates reviewable proposals only.

Key outputs:

- content type, such as `source`, `diff`, `scanner-output`, `log`, or `documentation`
- exactness class, such as `must-be-exact`, `structure-exact`, `summary-safe`, `reduce-safe`, or `skip-reduction`
- recommended strategy, such as `exact-pass-through`, `graph-first`, `scanner-focused-summary`, or `failure-focused-summary`
- preserve list and blocked reductions

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
- `receipt capture`: records approved loaded/avoided context with approximate local counts plus v2 exactness, strategy, preservation, and retrieval fields when supplied.
- `receipt summary`: summarizes local context receipts, including mixed v1/v2 files.
- `receipt retrieve --path`: shows the retrieval command for original evidence when a v2 receipt recorded it.
- `token-harness reduce`: creates exactness-preserving structured summaries for JSON/tool output, logs, scanner reports, and source symbol maps.
- `token-harness ledger`: records approved local Token Harness evidence events and summarizes or validates the append-only JSONL ledger.
- `token-harness proof`: reports proof labels and deterministic holdout decisions for token-saving evidence.
- `harness analyze/propose`: consumes sanitized token feedback through shared Meta-Harness summaries and proposes reviewable improvements.
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
python3 scripts/tailtrail.py guard check --fail-on dependency-gate,local-state
python3 scripts/tailtrail.py guard check --diff changes.patch --format json
python3 scripts/tailtrail.py guard check --commit-message commit-message.txt
python3 scripts/tailtrail.py guard check --pr-body pr-body.md
```

Use before committing or before sharing PR text when you want deterministic checks for the highest-value TailTrail guardrails. Advisory mode is the default and exits successfully. `--enforce` blocks high-severity findings. `--fail-on dependency-gate,local-state` blocks only the named classes a repo has chosen to enforce.

The first implementation checks dependency manifest additions without Dependency Gate evidence, suspicious safeguard removals, validation claims without evidence in supplied commit/PR text, and staged local TailTrail runtime state. It is not a full code review, policy service, SAST scanner, dependency scanner, or test runner.

### Guardrail Precision Baseline

```bash
python3 scripts/tailtrail.py guardrail precision
python3 scripts/tailtrail.py guardrail precision --strict --format json
python3 scripts/tailtrail.py guardrail precision --rule dependency-gate
python3 scripts/tailtrail.py guard precision --strict
```

Use this after changing `scripts/guardrail-check.py`, enforcement classes, or fixture thresholds. It runs labeled committed fixtures under `benchmarks/guardrail-precision/` and reports precision, recall, false-positive rate, fixture count, confidence, and status per rule. `--strict` exits non-zero if a rule falls below threshold, has too few fixtures, or has undefined precision.

The output is a TailTrail-internal baseline. It proves the current rules behave on committed fixtures; it does not prove universal repo-wide precision.

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

Use `graph map` before heavy Sonar, vulnerability, QA, dependency, review, release, or handoff work when the same source areas may be reread across a session. It writes `tailtrail-meta/code-graph-cache.json` by default with compact metadata only: file hashes, language profiles, symbols, references, call-chain hints, type hierarchy hints, endpoint hints, DB table hints, config usage hints, workspace overlays, likely tests/callers, suggested read order, monorepo partitions, service dependency hints, endpoint-to-service-to-table flows, CODEOWNERS ownership, and release path hints.

`tailtrail-meta/code-graph-cache.json` is the shareable team cache. Review it before committing because it can reveal architecture shape, symbols, endpoints, DB table names, config keys, owners, tests, and release paths. Use `--cache .tailtrail/code-graph-cache.json` only for a deliberately private local cache.

Use `graph status` when Navigator says a cache exists and you need to know whether it is fresh, stale, missing, or invalid. Use `graph refresh` when watched files changed. The mapper supports Python, Java, .NET/C#, SQL, and Terraform with explainable local heuristics and Python `ast` when available. It does not store source snippets, run scanners, query CI, run release commands, use a graph/vector database, or replace exact source inspection before edits.

## AST Maps

```bash
python3 scripts/tailtrail.py graph ast --changed src/service/foo.py --depth lite
python3 scripts/tailtrail.py graph ast --changed src/service/foo.py --depth v1
python3 scripts/tailtrail.py graph ast --changed src/service/foo.py --depth v1 --format json
python3 scripts/tailtrail.py graph ast --changed src/service/foo.py --depth v2
python3 scripts/tailtrail.py graph ast --changed src/service/foo.py --depth v2 --format json
python3 scripts/tailtrail.py graph ast --changed src/service/foo.py --depth v3 --provider-output tailtrail-meta/providers/semantic.json --approved
python3 scripts/tailtrail.py graph ast --changed src/service/foo.py --depth v3 --provider-output tailtrail-meta/providers/roslyn.json --approved --format json
```

Use `graph ast` when file-level impact is not precise enough and you need a dependency-free structured map before editing.

- `--depth lite`: reports structured symbols for selected files. Python uses `ast`; Java, .NET/C#, SQL, and Terraform use explainable local parsing heuristics.
- `--depth v1`: adds symbol references, call hints, type hierarchy hints, endpoint hints, DB/config hints, likely tests, and changed-symbol impact.
- `--depth v2`: adds local semantic edges, import/module edges, endpoint-to-handler links, data-flow-lite hints, test coverage hints, and provider readiness for language-server, SCIP, Roslyn, and tree-sitter paths.
- `--depth v3`: adds opt-in provider-backed semantic ingestion from approved local JSON files. Use `--provider-output` for JDT/language-server exports, Roslyn-derived .NET exports, richer Python analyzer exports, SQL/Terraform structured parser output, SCIP-derived JSON, or repo-owned extractor output.

Default policy:

- Default engine path is local-only: `lite`, `v1`, and `v2`.
- `graph ast` defaults to local AST V1.
- Normal work should use `lite`, `v1`, or `v2` first.
- V3 is never automatic and requires explicit `--depth v3 --provider-output ...` plus `--approved` or local policy enablement.
- Navigator may recommend V3 only when provider-backed metadata is explicitly requested or an approved provider-output file already exists for the task.
- TailTrail must not auto-run JDT, Roslyn, LSP/language servers, SCIP, tree-sitter, SQL parsers, Terraform parsers, MCP providers, networked services, or repo-owned extractors.

Provider output shape is intentionally simple and source-free. A provider JSON file may contain `provider`, `language`, and arrays named `symbols`, `references`, `calls`, `hierarchy`, `endpoints`, `db_tables`, `config_usage`, or `imports`. TailTrail keeps only metadata fields such as name, kind, file, line, caller, callee, table, key, route, method, and handler. It labels ingested facts as `provider-backed`.

Evidence labels are normalized in JSON and Markdown output:

- `heuristic`: regex, text, proximity, or local parsing hints.
- `local-ast`: local AST-derived facts.
- `provider-backed`: approved provider JSON facts.
- `measured/validated`: explicit validation, scanner, CI, or measured telemetry evidence.

Outputs include `evidence_summary` counts for those labels.

Boundaries:

- AST maps are metadata, not correctness proof.
- They do not store source snippets.
- They do not run code, tests, scanners, model calls, network calls, vector search, language servers, Roslyn analyzers, tree-sitter parsers, MCP, or background services.
- V3 ingests approved local JSON exports only; it requires `--approved` or local policy enablement and does not start JDT, Roslyn, LSP/language servers, SCIP, tree-sitter, SQL parsers, Terraform parsers, MCP providers, networked services, or repo-owned extractors.
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

## Harness Review

```bash
python3 scripts/tailtrail.py bootstrap snapshot --root .
python3 scripts/tailtrail.py bootstrap snapshot --root . --write-result
python3 scripts/tailtrail.py bootstrap status --root .
python3 scripts/tailtrail.py bootstrap refresh --root .
python3 scripts/tailtrail.py harness quick --root .
python3 scripts/tailtrail.py harness review --root .
python3 scripts/tailtrail.py harness confidence --root .
python3 scripts/tailtrail.py harness recommendations --root .
python3 scripts/tailtrail.py harness review --root . --month 2026-07 --write-result
python3 scripts/tailtrail.py harness review --root . --format json
python3 scripts/tailtrail.py harness export-summary --root .
python3 scripts/tailtrail.py harness export-summary --root . --write-result
python3 scripts/tailtrail.py harness shared-summary --root . --dry-run
python3 scripts/tailtrail.py harness shared-summary --root . --write-result --approved
python3 scripts/tailtrail.py harness shared-status --root .
python3 scripts/tailtrail.py harness shared-sanitize --root .
python3 scripts/tailtrail.py harness aggregate-shared --root . --format markdown
python3 scripts/tailtrail.py harness aggregate-shared --roots ../repo-a --roots ../repo-b
python3 scripts/tailtrail.py harness analyze --summary tailtrail-meta/harness-summary.jsonl
python3 scripts/tailtrail.py harness readiness --root .
python3 scripts/tailtrail.py harness readiness --roots ../repo-a --roots ../repo-b
python3 scripts/tailtrail.py harness propose --root . --proposal-id MH-2026-07-001
python3 scripts/tailtrail.py harness proposal-status --root .
python3 scripts/tailtrail.py harness proposal-record --root . --proposal-id MH-2026-07-001 --status accepted
```

Use Bootstrap Snapshot before broad Navigator tasks when you want TailTrail to start from safe workspace facts instead of repeated first-turn discovery. It captures filenames, language signals, manifests, test/CI/scanner signals, package managers, command availability, and TailTrail artifact presence. It does not read source bodies, raw prompts, logs, secrets, environment variable values, or user identity, and it does not execute project code.

Bootstrap commands:

- `bootstrap snapshot --root .`: print a snapshot without writing.
- `bootstrap snapshot --root . --write-result`: write `.tailtrail/bootstrap-snapshot.json`.
- `bootstrap status --root .`: report whether the local snapshot is missing, fresh, stale, or invalid.
- `bootstrap refresh --root .`: recreate `.tailtrail/bootstrap-snapshot.json`.

Navigator uses a fresh snapshot when present and recommends creation or refresh for repo overview, scanner, graph, handoff, review, and meaningful implementation prompts. Tiny or low-signal prompts can skip it to avoid overhead. `.tailtrail/bootstrap-snapshot.json` is local runtime state; do not commit it by default.

Use Harness Review when you want to know whether TailTrail itself behaved well: workflow fit, bootstrap fit, context fit, validation fit, metric confidence, learning fit, scanner/security fit, and code precision fit.

Layer 1 is local-only. It reads compact local artifacts such as quality events, outcome events, context receipts, token telemetry, learning events, learning refresh actions, and Code Graph Mapper cache metadata. It does not call models, query a service, run scanners, edit TailTrail rules, or push metadata to git.

`--write-result` writes only local runtime files:

```text
.tailtrail/harness-review.md
.tailtrail/harness-local-summary.json
.tailtrail/harness-recommendations.json
```

Layer 2 shareable summary export is explicit and writes only when `--write-result` is used:

```text
.tailtrail/harness-summary.json
```

`export-summary` rebuilds a sanitized allowlisted summary from local compact artifacts. It removes paths, repo names, raw prompts, logs, source, branch names, user identity, private URLs, private package names, and secrets. Do not commit `.tailtrail/harness-summary.json` by default; review it first and use Layer 2.5 later when a team explicitly opts into git-friendly shared metadata.

Layer 2.5 writes commit-friendly shared metadata only after explicit approval:

```text
tailtrail-meta/harness-summary.jsonl
```

`shared-summary --dry-run` shows the event without writing. `shared-summary --write-result --approved` appends one sanitized JSONL event and creates `tailtrail-meta/README.md` plus `tailtrail-meta/harness-summary.schema.json` when missing. `shared-status` reports whether the file exists, is tracked, ignored, and valid. `shared-sanitize` validates the file and exits non-zero if any event is unsafe.

Example shared event dry run:

```bash
python3 scripts/tailtrail.py harness shared-summary --root . --dry-run \
  --task-type bug-fix-with-tests \
  --language-family python \
  --workflow navigator,code-graph,review \
  --review-scope uncommitted \
  --requirement-fulfillment aligned \
  --token-budget-fit within-budget
```

The shared JSONL file contains categorical fields only. It must not contain prompts, source, diffs, file paths, repo names, users, tickets, private URLs, scanner raw output, secrets, or exact token usage.

Layer 3 aggregates approved sanitized shared metadata and finds repeated TailTrail behavior patterns:

```bash
python3 scripts/tailtrail.py harness aggregate-shared --root .
python3 scripts/tailtrail.py harness aggregate-shared --roots ../repo-a --roots ../repo-b --format json
python3 scripts/tailtrail.py harness analyze --summary tailtrail-meta/harness-summary.jsonl --write-result
python3 scripts/tailtrail.py harness readiness --root .
```

It can detect repeated validation gaps, token budget underestimation, weak metric confidence, partial requirement fulfillment, stale or missing graph context, AIDLC over-routing for small bug fixes, and scanner tasks missing graph context. `readiness` decides whether Meta-Harness should stay quiet, advise a repo maintainer, or recommend a central TailTrail product-improvement proposal. `--write-result` writes local private analysis/readiness files only:

```text
.tailtrail/meta-harness-analysis.json
.tailtrail/meta-harness-analysis.md
.tailtrail/meta-harness-readiness.json
.tailtrail/meta-harness-readiness.md
```

Layer 3.5 turns one repeated finding into a reviewable product-improvement proposal:

```bash
python3 scripts/tailtrail.py harness propose --root . --proposal-id MH-2026-07-001
python3 scripts/tailtrail.py harness propose --root . --finding-id MH-F-001 --write-result
python3 scripts/tailtrail.py harness proposal-status --root .
python3 scripts/tailtrail.py harness proposal-record --root . --proposal-id MH-2026-07-001 --status accepted
python3 scripts/tailtrail.py harness proposal-record --root . --proposal-id MH-2026-07-001 --status rolled_back --reason noisy-small-task-routing
```

Proposal commands show likely impacted files, line hints when available, implementation prompts, verification checks, degradation checks, and rollback guidance. They do not edit TailTrail source files automatically.

`harness propose` is registry-aware. A proposal must name valid `affected_features` from `tailtrail-registry.json`; unknown feature IDs return `no_proposal`. Proposal confidence is capped by the weakest affected feature evidence label, and proposal output includes registry-owned commands, docs, scripts, and tests for direct affected features. This prevents Meta-Harness from making product-change claims stronger than the registered evidence supports.

Navigator uses approved Meta-Harness hints only after a proposal decision is recorded:

```bash
python3 scripts/tailtrail.py harness proposal-record --root . --proposal-id MH-2026-07-001 --status accepted
python3 scripts/tailtrail.py guide "fix Sonar issue in validator" --root .
```

During `guide` or `start`, Navigator reads only the local proposal/status JSONL file, filters to `accepted` or `implemented` proposals, intersects them with the current registry workflow feature IDs, and shows at most three short hints. It does not run aggregation, readiness, proposal generation, scans, or product tuning during normal tasks.

`--write-result` writes local private proposal files only:

```text
.tailtrail/meta-harness-proposal.md
.tailtrail/meta-harness-proposals.jsonl
```

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

Never claim exact ROI from `savings estimate`. Exact token savings require `savings report` with real telemetry.

No API runner is implemented yet. TailTrail does not collect tokens from model providers automatically, does not store API keys, and does not make network calls for token telemetry.

## AIDLC

```bash
python3 scripts/tailtrail.py aidlc init --root . --depth standard
python3 scripts/tailtrail.py aidlc check --root .
python3 scripts/tailtrail.py aidlc check --root . --strict-answers
```

Use AIDLC for broad, risky, ambiguous, regulated, multi-team, or long-running work. Do not use it for tiny clear edits unless the user asks.

### Official AWS AI-DLC pack installation and compatibility

Install the pinned official AWS AI-DLC release into the current project before
using `--aidlc full`. This is separate from TailTrail's local Lite and Standard
modes. The installer downloads the published AWS release, preserves its MIT-0
license, records SHA-256 hashes for every installed rule, and does not execute
any pack script.

```powershell
py -3 scripts\tailtrail.py aidlc official install --root "D:\path\to\your-project" --host copilot
py -3 scripts\tailtrail.py aidlc official status --root "D:\path\to\your-project"

# Codex only: project the verified pack into the official rule locations and
# add a conditional Full-mode bridge to the existing AGENTS.md.
py -3 scripts\tailtrail.py aidlc official host install --root "D:\path\to\your-project" --host codex
py -3 scripts\tailtrail.py aidlc official host status --root "D:\path\to\your-project" --host codex
```

On macOS/Linux, use `python3 scripts/tailtrail.py` in the same commands. The
pack is saved locally at `.tailtrail/official-aidlc/`; it is project-local and
should not be manually edited after installation.

```bash
python3 scripts/tailtrail.py aidlc official status --root .
python3 scripts/tailtrail.py aidlc official status --root . --format json
```

This validates a locally supplied, pinned official-pack manifest at
`.tailtrail/official-aidlc/manifest.json`. It checks official source, a pinned
version/commit, MIT-0 license record, host adapter, and SHA-256 file hashes.
It reports `not-installed`, `compatible`, `altered`, or `incompatible` and
does not download, execute, attach, or edit an official pack. Start from
`templates/official-aidlc-pack.manifest.example.json`; placeholders must be
replaced with real local file hashes.

### AIDLC mode selection and official bridge identity

```bash
# Default local Lifecycle Lite mode
python3 scripts/tailtrail.py start "add a feature" --aidlc lite

# Strong local AIDLC planning (medium is an alias)
python3 scripts/tailtrail.py start "using AIDLC: add a feature" --aidlc standard

# Disable AIDLC lifecycle routing for this one planning run
python3 scripts/tailtrail.py start "small local fix" --aidlc off

# Explicit Full mode: requires Phase A compatibility first
python3 scripts/tailtrail.py start "regulated delivery" --aidlc full \
  --official-intent-id intent-42 --official-session-id session-7 \
  --official-stage requirements

# Read one saved mapping after Start
python3 scripts/tailtrail.py aidlc official bridge show --root . --run-id <run-id>

# Read the canonical owner/projection state for one run
python3 scripts/tailtrail.py aidlc official state show --root . --run-id <run-id>

# Validate canonical state; exits 1 when ownership conflicts are present
python3 scripts/tailtrail.py aidlc official state validate --root . --run-id <run-id>

# Validate one local official AI-DLC artifact without returning its contents
python3 scripts/tailtrail.py aidlc official sanitize validate --root . --input path/to/artifact.json --context checkpoint

# Full-mode requirements lifecycle: official stage -> TailTrail anchor
python3 scripts/tailtrail.py planning aidlc-requirements --root . --run-id <run-id>
python3 scripts/tailtrail.py planning aidlc-answer --root . --run-id <run-id> --answers '<answers-json>'
python3 scripts/tailtrail.py planning aidlc-approve --root . --run-id <run-id> --approved
```

Full mode uses the verified official-pack Requirements Analysis rules to create
the requirements questions and imports only sanitized requirement references
and explicit decisions. `aidlc-approve` is the single linked approval: it
writes the official stage decision, freezes the immutable TailTrail anchor, and
activates the same Planning Lock. A rejected Full-mode boundary routes back to
official requirements, or to the official design route when the feedback names
a design/architecture boundary. It does not download or execute a remote
official workflow engine. After approval, Phase I can attach the declared host
session through validated receipts as shown below.

### Official AI-DLC runtime attachment (Full mode)

```bash
python3 scripts/tailtrail.py aidlc official runtime attach --root . --run-id <run-id>
python3 scripts/tailtrail.py aidlc official runtime status --root . --run-id <run-id>
python3 scripts/tailtrail.py aidlc official runtime import-transition --root . --run-id <run-id> --receipt path/to/official-transition.json
python3 scripts/tailtrail.py aidlc official runtime resume --root . --run-id <run-id> --receipt path/to/resume-receipt.json
python3 scripts/tailtrail.py aidlc official runtime redo --root . --run-id <run-id> --receipt path/to/redo-receipt.json
python3 scripts/tailtrail.py aidlc official runtime jump --root . --run-id <run-id> --receipt path/to/jump-receipt.json
python3 scripts/tailtrail.py aidlc official runtime recovery --root . --run-id <run-id> --receipt path/to/recovery-receipt.json
```

Full-mode Start must include a real host-issued `--official-session-id`; the
placeholder `pending-host-session` cannot attach. Attachment requires the
compatible pinned pack, approved Planning Lock/anchor, and conflict-free
canonical state. TailTrail never executes arbitrary pack scripts. The declared
host adapter executes the official lifecycle and supplies sanitized receipts.
Each receipt must match the run, session, revision, approved-anchor fingerprint,
current stage, and next sequence, and must include a valid canonical SHA-256
integrity digest. Accepted receipts form an append-only restart-safe journal.

### Official AI-DLC evidence checkpoints (Full mode)

```bash
python3 scripts/tailtrail.py aidlc official checkpoint design-plan --root . --run-id <run-id>
python3 scripts/tailtrail.py aidlc official checkpoint design-approve --root . --run-id <run-id> --approved
python3 scripts/tailtrail.py aidlc official checkpoint construction --root . --run-id <run-id> --checkpoint saved-harness-checkpoint.json
python3 scripts/tailtrail.py aidlc official checkpoint test-plan --root . --run-id <run-id> --strategy standard
python3 scripts/tailtrail.py aidlc official checkpoint evidence --root . --run-id <run-id> --receipt saved-receipt.json
python3 scripts/tailtrail.py aidlc official checkpoint handoff --root . --run-id <run-id>
```

These commands use only the approved anchor and supplied saved receipts. They
do not run test commands, CI, deployments, or a remote official workflow. A
missing requirement-linked tier produces a bounded correction packet routed to
the official Build & Test stage. Phase I requires the Full runtime attachment
before these commands can claim an official lifecycle checkpoint.

Without an explicit flag, Start selects Lite normally, Standard for `using
AIDLC`, and Standard for hands-free/end-to-end delivery. Hands-free reports a
Full-escalation assessment and moves to Full only when Navigator sees
programme-scale signals *and* the pinned pack is compatible.

## Benchmark And Analyzer

```bash
python3 scripts/tailtrail.py benchmark
python3 scripts/tailtrail.py benchmark --format json
python3 scripts/tailtrail.py benchmark efficacy
python3 scripts/tailtrail.py benchmark efficacy --format json
python3 scripts/tailtrail.py efficacy run --portfolio
python3 scripts/tailtrail.py efficacy run --portfolio --strict --format json
python3 scripts/tailtrail.py efficacy run --scenario bug-fix-focused-tests
python3 scripts/tailtrail.py analyze benchmarks/results/latest.json
```

Use benchmark commands to gather local evidence. Use `benchmark efficacy` for committed baseline-vs-TailTrail artifact comparisons. Use `efficacy run --portfolio` for the BL-1.5 measured evidence portfolio across bug fix, review, security, CI/Sonar, dependency, feature, token-heavy artifact, and learning-governance scenarios. Portfolio output reports scenario-class coverage, artifact score, token evidence labels, and whether public claim thresholds are met. Use analyzer commands to interpret misses, discrepancies, proposed file changes, and recommended prompt improvements.

## Engine Helpers

```bash
python3 scripts/tailtrail.py engine summarize-output --file build.log
python3 scripts/tailtrail.py engine summarize-output --file scanner.log --format json
python3 scripts/tailtrail.py engine slice-context --file src/service/foo.py --query validate
python3 scripts/tailtrail.py engine slice-context --file README.md
python3 scripts/tailtrail.py engine cache-summary
python3 scripts/tailtrail.py engine cache-summary --cache tailtrail-meta/code-graph-cache.json --format json
python3 scripts/tailtrail.py engine prune-context --file noisy-context.md
python3 scripts/tailtrail.py engine prune-context --file noisy-context.md --drop generated --include-text
```

Use these when the user has evidence that is too noisy for normal prompting:

- `summarize-output`: compact generic logs or command output when the output type is unknown.
- `slice-context`: extract small file windows around matching terms, headings, functions, or classes.
- `cache-summary`: summarize `tailtrail-meta/code-graph-cache.json` without loading the whole cache. If the shared cache is missing, it falls back to `.tailtrail/code-graph-cache.json`.
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
python3 scripts/tailtrail.py install codex --target /path/to/project --dry-run
python3 scripts/tailtrail.py install codex --target /path/to/project
python3 scripts/tailtrail.py install codex-plugin --target /path/to/project --dry-run
python3 scripts/tailtrail.py install codex-plugin --target /path/to/project
python3 scripts/tailtrail.py install copilot --root /path/to/project --with-tailtrail-pack
python3 scripts/tailtrail.py install claude --target /path/to/project
python3 scripts/tailtrail.py install copilot --target /path/to/project --surface core
python3 scripts/tailtrail.py install local --target /path/to/project --profile copilot --surface core
python3 scripts/tailtrail.py install status --target /path/to/project
python3 scripts/tailtrail.py install upgrade-to-extended --target /path/to/project
python3 scripts/tailtrail.py update --root /path/to/project --dry-run
python3 scripts/tailtrail.py team-init --root /path/to/project --mode optional
```

Use these for onboarding a repo, installing a managed TailTrail pack, refreshing an existing pack, adding team guidance, or creating a `tailtrail` command that works from any repo.

`install codex` installs TailTrail's portable `AGENTS.md` guidance for Codex and preserves an existing `AGENTS.md` unless `--force` is supplied. Use `install codex-plugin` to install TailTrail's `.codex-plugin/plugin.json` and skills, including `$tailtrail-start`. Use `install claude` to install `CLAUDE.md` plus Claude Code's `/tailtrail-start` command. Copilot installation writes `.github/copilot-instructions.md` plus `.github/prompts/tailtrail-start.prompt.md`. `--profile` and `--surface` are independent on `install-local.py`: `--profile` selects the installation context or assistant host (`codex`, `codex-plugin`, `copilot`, `claude`, `aidlc`, `hooks`, `full`), while `--surface` selects file breadth (`core` or `extended`). Extended is the default and matches the full pack behavior; Core is the smaller first-run pack.

The launcher writes small executables, usually under `~/.local/bin/tailtrail` and `~/.local/bin/hello`, that point back to this TailTrail checkout. After installation, run from any project:

```bash
hello tailtrail
tailtrail hello
tailtrail guide "tell me important features of this repo"
tailtrail start "fix Sonar issue and prepare PR" --changed path/to/file
tailtrail start "continue payment retry correction" --changed src/worker.py --run-id payment-retry
tailtrail planning show --root . --run-id <run-id>
tailtrail planning activate --root . --run-id <run-id> --approved
tailtrail reference --target /path/to/service-a --reference /path/to/service-b --goal "match validation style"
```

The `hello` alias handles `hello tailtrail`, `hello TailTrail`, and the common typo `hello taitrail`, then delegates to `tailtrail hello`. If the launcher was installed before the alias existed, rerun `python3 scripts/tailtrail.py install launcher --force`.

`tailtrail start` is the default guided-delivery entry point: it selects the smallest applicable TailTrail controls, creates a local Planning Lock, and saves the exact Start Report at `.tailtrail/runs/<run-id>/planning/start-report-v1.json`. It remains planning-only even if the same prompt says implement, set up, or replicate. After the user approves, use `tailtrail planning activate --root . --run-id <run-id> --approved`: guided-delivery and hands-free plans receive an immutable approved anchor at `anchors/approved-v1.json`; lean tasks keep only the lock. It does not edit source, run tests, or invoke an implementation agent by itself; managed source changes require that separately approved Planning Lock run.

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

## Release Hygiene

```bash
python3 scripts/tailtrail.py release-check
python3 scripts/release-check.py
```

Use `release-check` before public packaging or release review. It validates public governance files, license/provenance alignment, public-release blockers, and tracked local-state mistakes. It does not replace legal, security, trademark, or maintainer approval.

## Doctor

```bash
python3 scripts/tailtrail.py doctor
```

Use doctor before releases, after edits, or after installing TailTrail into a project. It runs the package self-check and adapter sync check.

## Assistant Adapters

```bash
python3 scripts/tailtrail.py adapters check
python3 scripts/tailtrail.py adapters conformance
python3 scripts/tailtrail.py adapters sync
python3 scripts/sync-adapters.py --check
python3 scripts/sync-adapters.py --write
```

Use `adapters check` after changing assistant guidance. It verifies source adapters match tool-facing files and that every adapter includes the required TailTrail behavior contract: Navigator-first workflow, approval before implementation, post-change review, scanner approval, advisory learnings, measured-token claim boundaries, evidence labels, and local policy behavior.

`adapters conformance` verifies the Phase F versioned composed surfaces for
Codex, Copilot, and Claude. It checks the fixed precedence order and six local
control-flow scenarios; it does not claim identical runtime behavior by hosts.

### Real-host runtime conformance

```bash
python3 scripts/tailtrail.py adapters runtime prepare --root . --host codex
python3 scripts/tailtrail.py adapters runtime record --root . --host codex --receipt path/to/receipt.json
python3 scripts/tailtrail.py adapters runtime report --root .
python3 scripts/tailtrail.py adapters runtime report --root . --host codex
```

`prepare` writes a portable, source-free scenario bundle under
`.tailtrail/host-runtime/bundles/`. After running a scenario in Codex, Copilot,
or Claude, `record` validates a sanitized receipt against its digest, current
adapter/scenario versions, and canonical TailTrail run artifacts. `report`
keeps deterministic instruction conformance separate from observed runtime
conformance. Runtime status is `passed` only with all six current passing
scenario evaluations; otherwise it is `failed`, `not-validated`, `stale`, or
`incompatible` as the evidence requires.

Use `adapters sync` after editing files in `adapters/`; it writes the generated files such as `CLAUDE.md`, `.cursor/rules/tailtrail.mdc`, `.github/copilot-instructions.md`, `.openai/chatgpt-instructions.md`, and `GEMINI.md`.

See `ASSISTANT-COMPATIBILITY.md` for support levels and limitations. Assistant-specific prompt packs live in `adapters/prompts/`.

## Evaluation Harness

```bash
python3 scripts/tailtrail.py eval audit
python3 scripts/tailtrail.py eval audit --format json
python3 scripts/tailtrail.py eval audit --strict
python3 scripts/tailtrail.py eval audit --write-report --approved
python3 scripts/tailtrail.py eval portfolio run --portfolio --strict
python3 scripts/tailtrail.py eval guardrails precision --strict
python3 scripts/tailtrail.py eval outcome summarize
python3 scripts/tailtrail.py eval workflow review
python3 scripts/tailtrail.py eval meta quick --root .
python3 scripts/tailtrail.py eval tokens route --path src/app.py
python3 scripts/tailtrail.py eval tokens proof report
python3 scripts/tailtrail.py eval report value --root .
python3 scripts/tailtrail.py eval artifact analyze artifact.md
python3 scripts/tailtrail.py eval scenario list
python3 scripts/tailtrail.py eval scenario run --scenario validation-bug
python3 scripts/tailtrail.py eval scenario compare --scenario dependency-decision
python3 scripts/tailtrail.py eval scenario report --scenario security-triage
python3 scripts/tailtrail.py eval scenario report --scenario buildweek-validation
python3 scripts/tailtrail.py eval scenario report --scenario validation-bug --write-result --approved
python3 scripts/tailtrail.py eval normalize --source token-proof --input token-proof.json --format json
python3 scripts/tailtrail.py eval normalize --source outcome --input outcome.json --write-event --approved
python3 scripts/tailtrail.py eval normalize --source outcome --input outcome.json --write-event --dry-run
python3 scripts/tailtrail.py eval validate-events .tailtrail/evaluation/events.jsonl
```

Use `eval ...` when you want one evidence command family instead of remembering separate benchmark, efficacy, guardrail, outcome, workflow, token, report, and Meta-Harness commands. EH-2 aliases are thin delegations to existing scripts; they do not add new scoring or change write/approval rules.

`eval audit` inventories existing evidence surfaces, assigns each one a decision (`alias`, `merge`, `needs-decision`, or `retire`), and records the canonical `eval ...` surface. It is read-only unless `--write-report --approved` is used.

Current Evaluation Harness output answers:

- which current evidence commands are alias-ready
- which features should merge under one `eval` surface
- which aliases are compatibility-only
- whether any ambiguity blocks future alias work
- whether any audited script, doc, registry ID, or approval/privacy signal is missing

Implemented EH-2 alias groups:

- `eval portfolio run|report`
- `eval guardrails precision`
- `eval outcome capture|summarize`
- `eval workflow capture|summarize|review|propose|decide`
- `eval meta quick|review|readiness|analyze|propose|proposal-status|proposal-record`
- `eval tokens route|reduce|receipt|ledger|proof|telemetry|savings|budget|bridge`
- `eval report enterprise|value|compare|trend|aggregate|pr`
- `eval artifact analyze|benchmark`

Implemented EH-3 event commands:

- `eval normalize --source <kind> --input <path>`: converts compact local evidence JSON into the shared Evaluation Harness event shape.
- `eval normalize --source <kind> --input <path> --write-event --approved`: appends one sanitized event to `.tailtrail/evaluation/events.jsonl`.
- `eval normalize --source <kind> --input <path> --write-event --dry-run`: proves the event shape without writing or needing approval.
- `eval validate-events [path]`: validates Evaluation Harness event JSONL.

Supported EH-3 source kinds:

- `manual`
- `outcome`
- `quality-loop`
- `meta`
- `token-proof`
- `efficacy`
- `benchmark`

EH-3 event commands reject raw prompt, raw source, raw log, secret-like, and password-like fields. Exact token savings still require measured telemetry.

Implemented EH-4/EH-8 scenario commands:

- `eval scenario list`: lists committed deterministic scenarios, including `buildweek-validation`.
- `eval scenario run --scenario <id>`: scores one scenario and prints Markdown or JSON.
- `eval scenario compare --scenario <id>`: shows winner and delta from baseline.
- `eval scenario report --scenario <id>`: renders a readable scenario report.
- `eval scenario report --scenario buildweek-validation`: renders the Build Week demo proof as committed fixture evidence.
- `eval scenario report --scenario <id> --write-result --approved`: writes an approved report under `benchmarks/evaluation/results/` unless a path is supplied.

Scenario scoring reads saved fixture artifacts only. It does not run live agents, tests, CI, scanners, package managers, model/API calls, or hidden telemetry.

Still pending:

- `eval portfolio compare`: planned for portfolio consolidation
- `eval guardrails report`: planned for guardrail report consolidation
- `eval outcome export`: planned for outcome export consolidation
