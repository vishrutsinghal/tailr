# TailTrail Meta-Harness Implementation Study

## Purpose

This file defines the planned TailTrail Meta-Harness implementation.

The goal is to improve TailTrail's own operating wrapper over time: Navigator routing, context selection, graph usage, validation recommendations, learning quality, scanner behavior, token budgeting, and metric confidence.

This is not a plan to train a model. It is a plan to review and improve the harness around AI-assisted development.

## Core Idea

AI results are shaped by more than the model. They are shaped by the full harness around the model:

- prompt shape
- selected workflow
- context loaded
- context avoided
- tools suggested
- commands run
- code graph or scanner evidence used
- validation performed
- review lens applied
- learning surfaced
- metrics published
- failure review after the task

TailTrail already owns much of this wrapper. The Meta-Harness layer will review whether that wrapper behaved well for a task and recommend improvements.

## Public Artifact Learning: Environment Bootstrap

A public Meta-Harness Terminal-Bench artifact shows one practical pattern that fits TailTrail well: before the agent starts solving, the harness gathers a compact environment snapshot and injects useful facts into the initial context.

The useful lesson is not the code. TailTrail should not vendor or copy that implementation. The useful lesson is the product pattern:

```text
before planning -> collect safe workspace facts -> avoid repeated discovery -> make the first plan sharper
```

For TailTrail, this becomes **Environment Bootstrap Snapshot**.

## Environment Bootstrap Snapshot

Environment Bootstrap Snapshot is the pre-task side of Meta-Harness.

Status: implemented. TailTrail exposes `bootstrap snapshot`, `bootstrap status`, and `bootstrap refresh` through `scripts/tailtrail.py`, writes `.tailtrail/bootstrap-snapshot.json` only when explicitly requested, feeds Navigator with snapshot freshness, and lets Harness Review score `bootstrap_fit`.

Harness Review answers: "Did TailTrail behave well after the task?"

Bootstrap Snapshot answers: "Did TailTrail start with enough safe facts to make a good first plan?"

### Purpose

Bootstrap Snapshot should:

- reduce repeated first-turn discovery
- improve Navigator route selection
- improve token budget estimates
- improve graph, scanner, testing, CI, and handoff prompts
- give repo overview tasks a better starting point
- avoid reading broad source trees before TailTrail knows what matters

### What It Captures

The snapshot should capture compact local facts:

- repo type, such as git workspace or plain folder
- TailTrail install state
- top-level project shape
- detected languages by manifest and extension
- package manager signals
- dependency manifests and lockfiles
- likely test tools
- likely test commands when safely inferable
- CI config presence
- scanner config presence
- Sonar, SARIF, Trivy, Grype, dependency-check, CycloneDX, SPDX, and lockfile signals
- Docker, Terraform, SQL, Java, Python, .NET, JavaScript/TypeScript, and frontend signals
- AIDLC docs presence
- local policy presence
- guardrail files presence
- learning files presence
- code graph cache presence and freshness
- context receipt and token telemetry presence
- recommended first reads
- context to avoid at the beginning

### What It Must Not Capture

The snapshot must not capture:

- source code bodies
- raw prompts
- raw logs
- environment variable values
- secrets
- private URLs
- user identity
- private repo names in shareable summaries
- absolute paths in shareable summaries
- large generated content
- command output that may include sensitive machine details

### Snapshot File

Planned local file:

- `.tailtrail/bootstrap-snapshot.json`

Example:

```json
{
  "schema_version": "1",
  "created_at": "2026-07-15T10:30:00Z",
  "root_kind": "git",
  "tailtrail_installed": true,
  "languages": ["java", "python", "terraform"],
  "manifests": ["pom.xml", "requirements.txt"],
  "lockfiles": ["poetry.lock"],
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

### Planned Commands

```bash
python3 scripts/tailtrail.py bootstrap snapshot --root .
python3 scripts/tailtrail.py bootstrap snapshot --root . --write-result
python3 scripts/tailtrail.py bootstrap status --root .
python3 scripts/tailtrail.py bootstrap refresh --root .
python3 scripts/tailtrail.py bootstrap refresh --root .
```

`snapshot` should create the local snapshot.

`status` should report whether the snapshot is present, fresh, stale, missing, or too noisy.

`refresh` should update it after meaningful repo changes.

### Navigator Integration

Navigator should use the snapshot when it is fresh.

Expected behavior:

- For `tailtrail start`, create or refresh the snapshot when the command mode allows TailTrail artifact writes.
- For `tailtrail guide`, prefer read-only behavior. If the snapshot is missing, show a recommendation and ask approval before writing.
- For tiny prompts, skip snapshot creation unless the user asks for repo overview, graph, scanner, testing, CI, vulnerability, handoff, or architecture work.
- For repo overview prompts, suggest or use snapshot before Code Graph Mapper.
- For scanner and vulnerability prompts, use snapshot to identify relevant manifests and scanner files before broad reads.
- For cross-repo prompts, keep snapshots separate per repo.

### Code Graph Mapper Relationship

Bootstrap Snapshot is not a replacement for Code Graph Mapper.

Use them together:

- Bootstrap Snapshot: small, fast, safe workspace facts.
- Code Graph Mapper: deeper symbol, reference, endpoint, table, config, and test relationship map.

Navigator should generally use Bootstrap Snapshot first, then decide whether Code Graph Mapper is needed.

### Harness Review Integration

Harness Review should add a **Bootstrap Fit** dimension.

Possible Bootstrap Fit labels:

- `not_needed`
- `used_and_helpful`
- `missing_but_would_help`
- `stale`
- `too_noisy`
- `unsafe_field_detected`

Harness Review should ask:

- Was a snapshot available?
- Was it fresh enough?
- Did Navigator use it?
- Did it reduce repeated discovery?
- Did it improve token budget estimation?
- Did it avoid broad first reads?
- Did it stay compact and safe?

Example finding:

```text
Finding: Navigator performed broad repo discovery even though no bootstrap snapshot existed.
Recommendation: Create `.tailtrail/bootstrap-snapshot.json` before repo overview, scanner, graph, or handoff prompts.
Confidence: medium
Expected benefit: fewer repeated first-turn reads and better token budget estimation.
```

### Shareable Summary Fields

Layer 2 sanitized summaries can include categorical bootstrap fields:

```json
{
  "bootstrap_snapshot_used": true,
  "bootstrap_snapshot_fit": "used_and_helpful",
  "bootstrap_snapshot_freshness": "fresh",
  "bootstrap_helped_route_selection": true,
  "bootstrap_helped_token_budget": true
}
```

These fields must not include raw file paths, repo names, source snippets, command output, or private identifiers.

### Implementation Rules

V1 should:

- use Python standard library only
- inspect filenames, manifests, and directory names
- avoid reading source bodies
- avoid executing project code
- avoid shell-heavy probing
- keep output compact
- write only under `.tailtrail/`
- include freshness metadata
- include an explanation of why the snapshot is considered stale

V1 should not:

- run package managers
- run tests
- run scanners
- read secrets
- inspect `.env` values
- upload anything
- call a model
- call external APIs

### Example User Experience

Repo overview prompt:

```text
Use TailTrail Navigator to tell me the important features of this repo.
```

Ideal TailTrail behavior:

```text
Navigator sees no fresh bootstrap snapshot.
It asks approval to create `.tailtrail/bootstrap-snapshot.json`.
After approval, it summarizes repo shape, languages, manifests, tests, CI, scanner signals, and whether Code Graph Mapper should run.
It does not edit source files.
```

Scanner prompt:

```text
Use TailTrail to review possible Sonar and vulnerability issues before I open a PR.
```

Ideal TailTrail behavior:

```text
Navigator uses the bootstrap snapshot to identify Java/Python/Terraform manifests and scanner config.
It recommends Quality Signal Scanner and Security And Vulnerability Intelligence.
It asks before running heavy scans.
It uses Code Graph Mapper only if graph impact is useful.
```

### Why It Belongs In TailTrail

Bootstrap Snapshot is a strong fit because:

- it reduces repeated discovery
- it helps TailTrail save tokens before context grows
- it improves Navigator accuracy
- it supports demos with a clear "first useful plan" story
- it is safe and local
- it does not require model calls
- it can be evaluated later by Harness Review

## Important Claim Boundary

TailTrail should say:

```text
TailTrail is inspired by Meta-Harness-style end-to-end harness optimization.
It reviews local workflow evidence to improve routing, context, validation, learning, and metric confidence over time.
```

TailTrail should not say:

```text
TailTrail guarantees correct code.
TailTrail automatically trains itself on user work.
TailTrail proves exact ROI without measured telemetry.
TailTrail uploads logs or prompts for product improvement by default.
```

## Difference From Learning Agent V2

Learning Agent V2 and Meta-Harness are related, but they solve different problems.

| Area | Learning Agent V2 | Meta-Harness Layer |
| --- | --- | --- |
| Main question | What repo pattern should future tasks reuse? | Did TailTrail choose the right workflow and evidence path? |
| Scope | Project behavior and accepted development patterns | TailTrail behavior around the task |
| Example input | Accepted fix pattern, validation outcome, repo tags | Navigator plan, context receipts, token budget, quality events, outcome evidence |
| Example output | "Reuse this validation helper for claim DTO checks." | "Navigator should have selected Test Precision and skipped AIDLC for this small bug fix." |
| Safety model | Confidence-gated advisory learning | Read-only harness review plus sanitized optional summaries |
| Main risk | Stale or user-biased repo memory | Overclaiming product improvement or collecting too much telemetry |

Short version:

- Learning Agent V2 improves project memory.
- Meta-Harness improves TailTrail's decision system.

## When It Runs

Meta-Harness should not slow the user down during normal implementation.

It runs after work, or when explicitly requested.

Recommended trigger points:

- after `tailtrail start` completes a meaningful task
- after a value report is generated
- after a benchmark run
- after a learning refresh
- before a product demo or pilot review
- when the user asks for harness review, workflow quality, metric confidence, or TailTrail behavior analysis

It should not run automatically on every tiny prompt.

## When Learning Is Strong Enough To Apply

Meta-Harness data should not directly change TailTrail behavior just because a few tasks produced a signal.

TailTrail should apply Meta-Harness learning only when the evidence crosses a reviewable threshold:

- the same behavior issue appears across multiple meaningful tasks
- the issue has a measurable product impact, such as wrong Navigator route, missed review lens, weak validation, stale graph reuse, noisy context loading, or token budget underestimation
- the same recommendation appears in more than one local or shared harness summary
- the proposed change can be expressed as a deterministic TailTrail rule, prompt profile, parser, budget heuristic, test trigger, or documentation improvement
- the change can be verified with unit tests, golden Navigator plans, benchmark scenarios, or before/after value reports
- the change does not weaken guardrails, local policy, validation, scanner approval, security, dependency controls, or explicit user instructions

Example threshold:

```text
If 12 Java + Sonar tasks show:
- Navigator skipped Code Graph Mapper
- later broad source reads happened
- token budget was underestimated
- review needed scanner context

Then Meta-Harness can recommend:
"Route Java Sonar prompts to Code Graph Mapper earlier and increase the token budget band."
```

Do not apply Meta-Harness learning when:

- the signal comes from one task only
- the signal is purely subjective
- the user accepted a shortcut that scored low on validation, security, or maintainability
- the recommendation would make TailTrail more aggressive by default
- the pattern is repo-specific and should stay in Learning Agent V2 instead of product logic
- the evidence conflicts with current source, tests, CI, scanners, policy, guardrails, or explicit user direction

## Improvement Lifecycle

Meta-Harness should use a four-stage improvement loop.

### 1. Collect

TailTrail records approved, sanitized, categorical metadata after meaningful tasks.

Allowed examples:

- workflow selected
- workflow skipped
- validation outcome band
- review outcome band
- token budget fit
- graph freshness
- requirement fulfillment band
- learning confidence band
- scanner category
- issue category
- recommendation codes

Raw prompts, raw assistant responses, source code, diffs, file paths, user identity, repo names, branch names, private URLs, scanner raw output, and secrets must not appear in shareable metadata.

### 2. Analyze

Meta-Harness groups records and finds repeated TailTrail behavior patterns.

Example analyzer output:

```json
{
  "finding": "Navigator under-routes Code Graph Mapper for Java Sonar prompts",
  "confidence": "high",
  "evidence_count": 18,
  "recommended_change": "Add Sonar + Java + changed-files rule to Navigator graph selection",
  "risk": "low",
  "requires_human_approval": true
}
```

### 3. Propose

Meta-Harness should generate a reviewable proposal, not edit TailTrail automatically.

Each proposal should include:

- problem statement
- evidence count and confidence
- affected TailTrail feature
- likely files impacted
- exact behavior change
- test and benchmark plan
- expected improvement
- possible degradation risk
- rollback plan

### 4. Validate And Apply

Only after approval:

- implement the smallest deterministic change
- add or update tests
- run the relevant benchmark harness or scenario replay
- compare before/after behavior
- update docs and pitch wording when behavior changes

Meta-Harness can recommend TailTrail changes, but it must not silently edit TailTrail behavior.

## Files Likely Impacted By Meta-Harness Recommendations

Different recommendation families should touch different files.

Navigator routing:

- `scripts/navigator.py`
- `scripts/navigator_core.py`
- `scripts/navigator_render.py`
- `tests/test_navigator_core.py`
- `tests/golden/*`

Token budgeting:

- `scripts/token_budget_coach.py`
- `scripts/token-auto.py`
- `TOKEN-AUTOPILOT.md`
- `tests/test_deterministic_tools.py`

Code graph usage:

- `scripts/code-graph-mapper.py`
- `scripts/cache-summary.py`
- `context/code-graph-mapper.md`
- `tailtrail-meta/code-graph-cache.json`
- `tests/test_deterministic_tools.py`

Review behavior:

- `scripts/review-run.py`
- `scripts/review-output.py`
- `context/review-lenses.md`
- `tests/test_review_output.py`
- `tests/test_review_scope.py`

Learning governance:

- `scripts/learning-agent.py`
- `scripts/learning-refresh.py`
- `LEARNING-GOVERNANCE.md`

Meta-Harness itself:

- `scripts/meta-harness-analyze.py`
- `scripts/meta-harness-propose.py`
- `templates/meta-harness-proposal.md`
- `META-HARNESS-IMPLEMENTATION.md`
- `ROADMAP.md`
- `TAILTRAIL-PITCH.md`
- `tailtrail-meta/harness-summary.jsonl`
- `tests/test_meta_harness.py`

These are likely impact areas, not permission to edit all of them. Each proposal should name the minimal affected files before implementation.

## Verification And Degradation Detection

Every Meta-Harness-driven implementation should include before/after validation.

Required verification:

- existing unit tests still pass
- TailTrail doctor still passes
- new targeted regression test passes
- affected golden Navigator or report output is intentionally updated
- benchmark harness score improves or stays equal
- scanner, security, dependency, and validation guardrails are not weakened
- tiny tasks do not become noisier

Example before/after result:

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

Degradation signals to watch:

- false-positive route selection increased
- AIDLC appears for small tasks too often
- plans became too long for simple prompts
- token budget estimate worsened
- graph mapping runs when the task is tiny
- review findings became less specific
- scanner approval wording became unclear
- validation recommendations became weaker

## Rollback Model

Every Meta-Harness recommendation that changes TailTrail behavior should be reversible.

Recommended commit style:

```text
Tune Navigator graph routing for Java Sonar prompts

Meta-Harness-Proposal: MH-2026-07-001
Evidence: 18 sanitized task summaries
Validation: benchmark +6, no doctor failures
```

Rollback path:

```bash
git revert <commit-sha>
```

After rollback, record a local or shared recommendation outcome:

```json
{
  "proposal_id": "MH-2026-07-001",
  "status": "rolled_back",
  "reason": "Triggered Code Graph Mapper too often for small lint tasks",
  "future_action": "Add stricter changed-file and scanner-signal threshold"
}
```

Rollback records should be sanitized and categorical. They should not include raw prompts, source code, diffs, file paths, repo names, branch names, user names, private URLs, or secrets.

## Operating Modes

Meta-Harness should expose three modes:

| Mode | Purpose | Writes TailTrail behavior? |
| --- | --- | --- |
| `observe` | collect and summarize evidence | no |
| `recommend` | generate reviewable improvement proposals | no |
| `apply` | implement an approved proposal through normal code changes | only after explicit approval |

Default mode should be `observe` or `recommend`, never silent `apply`.

## Performance Model

| Mode | When used | Expected cost | Behavior |
| --- | --- | --- | --- |
| Skip | Tiny task, no artifacts, or user did not ask | 0 seconds | Do nothing and avoid noise. |
| Bootstrap | Before Navigator for repo overview, graph, scanner, test, CI, vulnerability, architecture, or handoff tasks | About 1-5 seconds | Capture safe workspace facts without reading source bodies or executing project code. |
| Quick | Normal post-task sanity check | About 1-3 seconds | Read compact TailTrail artifacts and return a short finding list. |
| Standard | User asks for harness review or metric confidence | About 3-10 seconds | Review Navigator, graph, token, learning, quality, and outcome artifacts. |
| Deep local | Demo, pilot, release, or team review | About 15-60 seconds | Compare multiple local tasks and find repeated behavior patterns. |
| Batch summary | Future enterprise/public opt-in aggregation | About 10-90 seconds depending on supplied summaries | Aggregate sanitized summaries only. |

V1 should be deterministic and local. It should not call a model or external API.

## Layer 1: Local Harness Review

Layer 1 is the default implementation.

Status: implemented for the first deterministic local review slice. `scripts/harness-review.py` exposes `quick`, `review`, `confidence`, and `recommendations` through `python3 scripts/tailtrail.py harness ...`. It is read-only unless `--write-result` is used, and writes only local `.tailtrail/harness-*` files.

### Purpose

Give the local user an explainable review of TailTrail's behavior for a task.

### Inputs

Layer 1 can read local TailTrail artifacts such as:

- `.tailtrail/bootstrap-snapshot.json`
- `.tailtrail/task-starts/*.json`
- `.tailtrail/quality-events.jsonl`
- `.tailtrail/outcome-events.jsonl`
- `.tailtrail/learning-events.jsonl`
- `.tailtrail/learning-refresh-actions.json`
- `.tailtrail/token-budget-events.jsonl`
- `.tailtrail/context-receipts.jsonl`
- `.tailtrail/token-usage.jsonl`
- `tailtrail-meta/code-graph-cache.json`
- benchmark result files when explicitly supplied
- scanner summaries when explicitly supplied

### Review Questions

Layer 1 should answer:

- Did Navigator classify the task correctly?
- Was the selected workflow too heavy, too light, or right-sized?
- Did TailTrail skip AIDLC for small tasks where lifecycle planning was unnecessary?
- Did TailTrail use AIDLC for broad, risky, regulated, or multi-step work?
- Did TailTrail create or use a fresh bootstrap snapshot before broad repo discovery?
- Did TailTrail use Code Graph Mapper when broad repo understanding, scanners, tests, or handoff needed it?
- Did TailTrail avoid broad source reads when graph/cache/slices were enough?
- Did TailTrail preserve local policy and guardrails?
- Did TailTrail suggest focused validation?
- Did TailTrail ask before heavy scans, vulnerability checks, broad builds, or writes?
- Did TailTrail publish metric confidence accurately?
- Did TailTrail use learning only when fresh, relevant, high-confidence, and advisory?

### Output

Layer 1 should produce a local report:

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

### Local Report Files

Planned generated files:

- `.tailtrail/harness-review.md`
- `.tailtrail/harness-recommendations.json`

Both should be local-only by default.

## Layer 2: Shareable Harness Summary

Layer 2 is optional and explicit.

Status: implemented for the first sanitizer-backed local export. `python3 scripts/tailtrail.py harness export-summary --root .` prints an allowlisted summary, and `--write-result` writes `.tailtrail/harness-summary.json`. It does not upload, commit, or append to `tailtrail-meta/`.

### Purpose

Allow users or teams to share product-useful signals without sharing private development details.

### Safety Rule

Use allowlisted summary fields only. Do not redact arbitrary raw content and assume it is safe.

The summary must not include:

- raw prompts
- raw logs
- source code
- source snippets
- absolute file paths
- repo names
- branch names
- user names
- emails
- customer identifiers
- private URLs
- private package names
- secrets
- stack traces with private paths
- issue/ticket IDs unless explicitly normalized

### Example Summary

```json
{
  "schema_version": "1",
  "tailtrail_version": "1.4.0",
  "task_type": "bug_fix_with_tests",
  "language_family": "java",
  "workflow_selected": ["navigator", "code_graph", "test_precision"],
  "bootstrap_snapshot_used": true,
  "bootstrap_snapshot_fit": "used_and_helpful",
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

### Planned Commands

```bash
python3 scripts/tailtrail.py harness export-summary --root . --write-result
python3 scripts/tailtrail.py harness export-summary --root . --from .tailtrail/harness-review.md
```

The command should write a local file first and ask the user to review it before sharing.

Planned file:

- `.tailtrail/harness-summary.json`

## Layer 2.5: Commit-Friendly Shared Harness Metadata

Status: implemented. TailTrail now supports dry-run, approved append, status, and sanitizer commands for shared harness metadata:

```bash
python3 scripts/tailtrail.py harness shared-summary --root . --dry-run
python3 scripts/tailtrail.py harness shared-summary --root . --write-result --approved
python3 scripts/tailtrail.py harness shared-status --root .
python3 scripts/tailtrail.py harness shared-sanitize --root .
```

The implementation writes only allowlisted categorical JSONL events to `tailtrail-meta/harness-summary.jsonl`, and only when `--write-result --approved` is used. It also includes `tailtrail-meta/README.md` and `tailtrail-meta/harness-summary.schema.json` so teams can review the boundary before committing the metadata.

This layer addresses an important practical problem:

```text
Local metadata helps only the current developer unless someone intentionally exports it.
But asking every user to manually push a separate metadata file is too much friction.
```

The better design is a split metadata model:

- private raw/local evidence stays in `.tailtrail/`
- sanitized commit-friendly evidence lives in a tracked shared folder
- the shared file is updated as part of normal TailTrail task completion
- the shared file rides along with normal repo commits and pushes

### Recommended Path

Use a path outside `.tailtrail/` because many repos intentionally ignore `.tailtrail/`.

Recommended tracked path:

```text
tailtrail-meta/harness-summary.jsonl
```

Optional companion files:

```text
tailtrail-meta/README.md
tailtrail-meta/harness-summary.schema.json
tailtrail-meta/.gitkeep
```

Why not `.tailtrail/harness-summary.jsonl`?

- `.tailtrail/` is local runtime state in many repos.
- It may contain raw task starts, token events, local telemetry, learning events, scanner summaries, and other data that should not be committed by default.
- Keeping the commit-friendly summary in `tailtrail-meta/` makes the boundary obvious: this folder is sanitized and shareable; `.tailtrail/` is local.

### What Gets Committed

Only allowlisted, categorical, product-useful metadata.

Example JSONL event:

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
  "recommendation_codes": [
    "ask-clarification-on-partial-fulfillment",
    "increase-budget-java-sonar-test"
  ]
}
```

### What Must Never Be Committed

The shared metadata must not include:

- raw user prompts
- raw assistant responses
- source code or source snippets
- diffs
- file paths
- function names
- repo names
- branch names
- user names
- emails
- ticket IDs unless normalized
- customer identifiers
- private package names
- private URLs
- scanner raw output
- secrets
- absolute local paths
- exact token usage unless the user intentionally marks it shareable

If TailTrail cannot prove a field is safe, omit it.

### How It Solves Product Improvement

When the metadata file is tracked in each repo:

1. Developers run TailTrail normally.
2. After meaningful tasks, TailTrail creates or updates a sanitized shared event.
3. The event is part of the repo diff, so it is pushed with normal code changes.
4. Later, TailTrail maintainers or enterprise admins can mine many repos for shared harness patterns.
5. Product improvements can be based on evidence without central telemetry or raw code access.

This avoids a hidden telemetry service while still creating a path for product learning.

### User Experience

After task completion:

```text
TailTrail can write a sanitized harness summary to:
tailtrail-meta/harness-summary.jsonl

This file contains categorical workflow evidence only.
It does not include prompts, source code, diffs, file paths, repo names, or user identity.

Approve writing this shared metadata event?
```

If approved, TailTrail writes one append-only JSONL record.

If the file is already tracked, it will be included when the developer commits normal repo changes.

If the file is untracked, TailTrail should say:

```text
tailtrail-meta/harness-summary.jsonl was created.
Review it before adding to git. Commit it only if your repo wants shared TailTrail improvement metadata.
```

### Why Approval Is Still Needed

Even sanitized metadata should not be silently written or committed.

Approval is needed because:

- some companies do not want process metadata committed
- some regulated repos may treat workflow metadata as sensitive
- users should inspect the first generated event
- the repository owner should choose whether `tailtrail-meta/` is shared

After a repo opts in, TailTrail can continue updating the tracked file, but it should still keep the content allowlisted and sanitizer-tested.

### Implemented Commands

```bash
python3 scripts/tailtrail.py harness shared-summary --root . --dry-run
python3 scripts/tailtrail.py harness shared-summary --root . --write-result --approved
python3 scripts/tailtrail.py harness shared-status --root .
python3 scripts/tailtrail.py harness shared-sanitize --root .
```

Command behavior:

- `shared-summary --dry-run`: show the sanitized event that would be written.
- `shared-summary --write-result --approved`: append the event to `tailtrail-meta/harness-summary.jsonl`.
- `shared-status`: report whether the shared file exists, is tracked, is ignored, or has unsafe fields.
- `shared-sanitize`: validate the file and flag unsafe fields.

### Aggregation Later

Later TailTrail product improvement can read shared metadata from checked-out repos:

```bash
python3 scripts/tailtrail.py harness aggregate-shared --roots repo-a repo-b repo-c
```

Or from explicit files:

```bash
python3 scripts/tailtrail.py harness aggregate-shared --summary repo-a/tailtrail-meta/harness-summary.jsonl --summary repo-b/tailtrail-meta/harness-summary.jsonl
```

No network service is required for V1.

### Governance Model

Recommended repo policy:

```text
tailtrail-meta/ is shareable TailTrail process metadata.
.tailtrail/ is local private TailTrail runtime state.
```

Recommended `.gitignore` stance:

```text
.tailtrail/
!tailtrail-meta/
!tailtrail-meta/harness-summary.jsonl
!tailtrail-meta/README.md
!tailtrail-meta/schema.json
```

Most repos will not need the `!tailtrail-meta/` entries unless they already ignore broad metadata folders.

### Risks And Mitigations

Risk: metadata becomes noisy.

Mitigation:

- append only meaningful task summaries
- cap event size
- rotate monthly if needed
- use recommendation codes rather than prose

Risk: metadata leaks private context.

Mitigation:

- allowlisted schema only
- sanitizer tests
- no raw text fields
- no paths or names
- dry-run preview

Risk: merge conflicts in JSONL.

Mitigation:

- append-only JSONL
- one event per line
- stable key order
- optional monthly files later, such as `tailtrail-meta/harness-summary-2026-07.jsonl`

Risk: users forget to commit the file.

Mitigation:

- if file is tracked, normal `git add -A` or commit flows include it
- TailTrail can remind when shared metadata is modified but unstaged
- no hidden auto-stage in V1

Risk: product team over-trusts shared metadata.

Mitigation:

- summaries are directional evidence only
- product changes still require benchmark, tests, and human review
- never treat shared summaries as proof of exact ROI or correctness

## Layer 3: Product Improvement Pipeline

Status: implemented as an explicit, deterministic aggregation workflow. It is not the default local behavior.

### Purpose

Aggregate sanitized summaries to improve TailTrail product behavior across teams or users.

Implemented command surface:

```bash
python3 scripts/tailtrail.py harness aggregate-shared --root . --format markdown
python3 scripts/tailtrail.py harness aggregate-shared --roots ../repo-a --roots ../repo-b
python3 scripts/tailtrail.py harness analyze --summary tailtrail-meta/harness-summary.jsonl
python3 scripts/tailtrail.py harness analyze --root . --write-result
```

Implemented local outputs:

- `.tailtrail/meta-harness-analysis.json`
- `.tailtrail/meta-harness-analysis.md`

These outputs are local private runtime files. They should not be committed.

### What It Can Improve

Layer 3 can identify repeated patterns such as:

- Shared `tailtrail-meta/harness-summary.jsonl` files show repeated workflow fit or fulfillment gaps across repos.
- Bootstrap Snapshot is missing for repo overview tasks and users repeatedly pay discovery cost.
- Bootstrap Snapshot is present but too noisy and does not improve Navigator choices.
- Java + Sonar + test tasks consistently need higher token budgets.
- Small bug fixes are over-routed into AIDLC when the prompt only asks for unit tests.
- Vulnerability prompts need stronger graph overlay recommendations.
- Value reports are often estimated-only because measured telemetry import is not easy enough.
- Code Graph Mapper is useful for repo overview prompts but not clearly suggested.
- Learning refresh warnings appear often in repos with fast-changing architecture.

### Product Changes It Can Recommend

Layer 3 can recommend:

- shared metadata schema changes
- shared metadata sanitizer improvements
- bootstrap snapshot field changes
- bootstrap freshness rule changes
- Navigator trigger changes
- token budget profile changes
- prompt compression profile changes
- graph-first read policy updates
- test precision routing updates
- scanner parser improvements
- benchmark scenario additions
- documentation improvements
- onboarding prompt improvements

### What It Must Not Do

Layer 3 must not:

- upload data automatically
- collect raw prompts
- collect raw logs
- collect source code
- collect file paths or repo names
- score individual developers
- rewrite TailTrail automatically
- claim exact ROI without measured telemetry

## Layer 3.5: Evidence-Gated Improvement Proposals

Status: implemented as a proposal and decision-record loop. It does not edit TailTrail source files automatically.

Purpose:

- Decide when repeated sanitized evidence is strong enough to propose a TailTrail product change.
- Show the likely impacted files, line hints, implementation prompts, verification plan, degradation checks, and rollback plan.
- Record explicit proposal decisions locally without turning user preference into product behavior automatically.

Implemented command surface:

```bash
python3 scripts/tailtrail.py harness propose --root . --proposal-id MH-2026-07-001
python3 scripts/tailtrail.py harness propose --root . --finding-id MH-F-001 --write-result
python3 scripts/tailtrail.py harness proposal-status --root .
python3 scripts/tailtrail.py harness proposal-record --root . --proposal-id MH-2026-07-001 --status accepted
python3 scripts/tailtrail.py harness proposal-record --root . --proposal-id MH-2026-07-001 --status rolled_back --reason noisy-small-task-routing
```

Implemented local outputs:

- `.tailtrail/meta-harness-proposals.jsonl`
- `.tailtrail/meta-harness-proposal.md`

Proposal records are local private runtime state. They should not be committed. Shared product evidence remains the sanitized categorical JSONL in `tailtrail-meta/harness-summary.jsonl`.

Implemented evidence gates:

- threshold must be at least two events
- invalid shared events are rejected by the sanitizer
- findings are generated only from allowed categorical shared fields
- proposals are marked as recommendations and include "review before adding" wording
- proposal records support `proposed`, `accepted`, `implemented`, `rejected`, `rolled_back`, and `superseded`
- no source edit is made by the proposal command

Implemented finding families:

- repeated recommendation codes
- validation fit gaps
- token budget underestimation
- metric confidence gaps
- requirement fulfillment gaps
- graph cache gaps
- AIDLC over-routing for small bug fixes
- scanner tasks without healthy graph context

## Integration With TailTrail Feature Registry

The Feature Registry and Meta-Harness solve different problems and should remain separate layers.

Feature Registry answers:

```text
What TailTrail features exist, which commands/docs/scripts/tests own them, and are they drifting?
```

Meta-Harness answers:

```text
Did TailTrail choose and use the right workflow for real tasks, and what should improve based on evidence?
```

Design rule:

```text
Registry = declared truth
Meta-Harness = observed truth
Navigator = route selection
```

The registry is the map. Navigator chooses the route. Meta-Harness reviews whether the route worked.

### What Should Overlap

The overlap is useful when it is explicit:

- feature IDs
- command names
- docs, scripts, and tests attached to a feature
- Core vs Extended install surface
- evidence labels such as `estimated`, `local-evidence`, `measured`, and `benchmark-measured`
- read-only/write-capable status
- approval requirements
- likely impacted files for product-improvement proposals

Meta-Harness should not invent a parallel feature taxonomy once the registry exists. It should reference registry IDs.

### What Should Stay Separate

The registry should not become a behavior analyzer:

- no workflow scoring
- no proposal generation
- no task outcome analysis
- no learning quality analysis
- no token budget fit analysis
- no automatic source edits

Meta-Harness should not become the feature inventory:

- no independent command catalog
- no independent Core/Extended surface table
- no independent docs/tests ownership map
- no independent MCP tool taxonomy

### Integration Sequence

1. Implement the Feature Registry standalone.
2. Register Meta-Harness itself as one registry feature.
3. Keep existing Meta-Harness commands working without requiring the registry.
4. Extend Meta-Harness proposal records to include `affected_features` with registry feature IDs.
5. Use registry ownership to enrich proposals with impacted commands, docs, scripts, tests, and install surface.
6. Add registry-aware validation for proposals only after registry strict validation is stable.
7. Let Navigator and MCP consume registry projections later, after registry drift checks are reliable in CI.

### Registry-Aware Validation Rules

Unknown feature IDs:

- First integration: advisory only.
- Later Phase 11.5 consumer mode: blocking only after registry strict validation is stable in CI.
- Developer task mode: do not run this validation unless the user explicitly asks for harness or registry analysis.

Evidence-label bounds:

- Meta-Harness must not output `measured` or `benchmark-measured` confidence for an affected feature whose registry entry only supports `estimated` or `local-evidence`.
- If multiple affected features have different evidence labels, the proposal confidence must not exceed the weakest relevant evidence label.
- This preserves TailTrail's claim discipline: evidence labels constrain product claims.

Impact expansion:

- Proposal impact lists direct `affected_features` by default.
- Do not traverse registry `depends_on` by default when listing impacted commands, docs, scripts, and tests.
- A future proposal impact command may add `--include-dependents` for explicit transitive impact review.
- Transitive impact is useful for central maintainers, but too noisy for default proposal output.

Readiness tie-in:

- Registry-aware proposal validation is implemented in Meta-Harness Readiness Tier 3, central maintainer mode.
- Level 1 developer task mode should only use already-approved/productized rules.
- Level 2 repo maintainer mode may report that registry-aware validation is available, but should not block local work.
- Level 3 central maintainer mode is where unknown feature IDs, evidence-label bounds, and registry-owned impact lists become proposal quality gates.

### Implemented Proposal Shape

```json
{
  "proposal_id": "MH-2026-07-001",
  "finding": "Navigator under-routes Code Graph Mapper for Java Sonar tasks",
  "affected_features": ["navigator", "code-graph-mapper", "quality-signal-scanner"],
  "proposal_evidence_label": "local-evidence",
  "registry_validation": {
    "valid": true,
    "proposal_evidence_label": "local-evidence",
    "evidence_label_rule": "Proposal confidence cannot exceed the weakest affected feature evidence label."
  },
  "recommended_change": "Route Java Sonar prompts to Code Graph Mapper earlier and increase the token budget band.",
  "requires_human_approval": true
}
```

### Implemented Proposal Impact Summary

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

### Safety Boundary

Registry integration must not make Meta-Harness more autonomous.

Allowed:

- reference registry feature IDs. Implemented through `affected_features`.
- validate that affected features exist. Implemented; unknown feature IDs return `no_proposal`.
- reuse registry evidence-label vocabulary. Implemented through `proposal_evidence_label`.
- bound proposal confidence by the weakest relevant registry evidence label. Implemented.
- show registry-owned scripts/docs/tests in proposal output. Implemented in `Registry Impact`.
- list direct affected features by default
- list dependent features only through an explicit future option
- report registry drift as context for product-improvement proposals. Implemented through readiness registry health and proposal validation.

Not allowed:

- edit registry entries automatically
- edit TailTrail source automatically
- generate docs from registry metadata
- run central aggregation during normal developer prompts
- upload summaries automatically
- block developer task execution because a product-improvement proposal has registry drift
- include raw prompts, source, paths, repo names, scanner raw output, user identity, or secrets in shared evidence

## Meta-Harness Readiness Tiers

Status: implemented. `python3 scripts/tailtrail.py harness readiness --root .` defines when Meta-Harness should stay quiet, when it should advise a repo maintainer, and when it should tell central TailTrail maintainers that evidence is strong enough to review a product-improvement proposal.

The key product rule:

```text
Navigator uses already-approved TailTrail behavior.
Meta-Harness discovers future improvements.
Maintainers approve, validate, and ship those improvements.
Users benefit after update.
```

Meta-Harness should not interrupt every developer task. It should make readiness decisions through evidence thresholds, not subjective judgment.

### Level 1: Developer Task Mode

Audience: normal developers using TailTrail for feature work, bug fixes, reviews, scans, tests, and handoff.

Behavior:

- Do not run heavy aggregation during every task.
- Do not ask developers to implement TailTrail product improvements during normal repo work.
- Use only already-approved/productized Meta-Harness-backed rules in Navigator.
- Show a compact explanation only when it is directly relevant.

Example Navigator wording:

```text
Why this path:
Meta-Harness-backed evidence shows graph-first reads help similar Sonar tasks.
Recommended path includes Code Graph Mapper.
```

Implemented behavior:

1. Developer task mode returns `stay_quiet` by default.
2. It blocks aggregation, proposal generation, metadata sharing, automatic TailTrail edits, and developer interruption.
3. Normal Navigator and Start flows do not load `.tailtrail/meta-harness-analysis.*`, readiness files, or shared aggregation files unless the user explicitly asks for harness analysis.
4. Navigator reads only `.tailtrail/meta-harness-proposals.jsonl` and shows at most three short hints from proposals that have been `accepted` or `implemented`.
5. A hint must intersect the current registry workflow feature IDs, so unrelated approved proposals stay hidden.

Acceptance check:

- Normal `start` and `guide` output stays compact.
- Meta-Harness notes appear only for relevant approved rules.
- Developer tasks do not trigger central aggregation or proposal generation.

### Level 2: Repo Maintainer Mode

Audience: repo owners, team leads, platform maintainers, or senior engineers reviewing how TailTrail is working in one repo or one team.

Behavior:

- Runs on demand after meaningful work or during periodic repo review.
- Reviews local evidence such as quality events, outcome telemetry, context receipts, token usage, graph freshness, scanner routing, learning confidence, and validation fit.
- Produces repo-level improvement recommendations.
- Does not change TailTrail product behavior.
- Does not upload data.

Example commands:

```bash
python3 scripts/tailtrail.py harness review --root .
python3 scripts/tailtrail.py harness shared-summary --root . --dry-run
python3 scripts/tailtrail.py harness shared-summary --root . --write-result --approved
```

Implemented command:

```bash
python3 scripts/tailtrail.py harness readiness --root .
```

Implemented repo-maintainer decisions:

- `stay_quiet`: no valid evidence or no actionable repeated signal.
- `advise_repo_maintainer`: sanitizer/input issues, repeated local findings, weak validation, or weak metric confidence should be reviewed locally.

Implemented behavior:

1. Reuses sanitized shared harness summaries and existing analysis logic.
2. Shows sanitizer/input readiness, evidence counts, findings, registry status, and next actions.
3. Keeps repo-local details in `.tailtrail/`.
4. Keeps `tailtrail-meta/harness-summary.jsonl` as the optional commit-friendly shared artifact.
5. Adds deterministic tests for quiet, repo advisory, and central product-improvement decisions.

Acceptance check:

- Repo maintainers can tell whether sharing a summary is useful.
- Weak or stale evidence does not become a central recommendation.
- Sharing remains explicit and approved.

### Level 3: Central TailTrail Maintainer Mode

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

Implemented central-maintainer decisions:

- `stay_quiet`: evidence is too small or no repeated product finding crossed threshold.
- `advise_repo_maintainer`: sanitizer/input evidence is not clean or registry maturity is not healthy.
- `recommend_central_tailtrail_improvement`: sanitized evidence is clean, repeated findings crossed threshold, and the Feature Registry is healthy.

Implemented behavior:

1. Extends `meta-harness-analyze.py` with readiness scoring.
2. Scores valid event count, invalid sanitizer issues, missing inputs, repeated findings, high-severity findings, registry health, weak metric confidence, and weak validation fit.
3. Adds `harness readiness --root .` and `harness readiness --roots repo-a --roots repo-b`.
4. Gates `harness propose`: if central readiness is not `recommend_central_tailtrail_improvement`, proposal output returns `no_proposal`.
5. Keeps central improvement based on approved categorical evidence only.

Acceptance check:

- Central maintainers know when a finding is ready to implement.
- One repo or one user preference cannot change product behavior.
- Proposal readiness is deterministic and test-backed.
- Product changes remain human-approved, committed, validated, and reversible.

Non-goals:

- No per-task central aggregation.
- No hidden upload.
- No raw prompt, source, diff, file path, repo name, branch name, user identity, private URL, scanner raw output, secret, or exact token usage in shared evidence.
- No automatic TailTrail self-editing.
- No automatic rollout to users.
- No hidden scoring of developers or teams.

## Hybrid Implementation Recommendation

The best design is a hybrid:

1. Local-first review by default.
2. Optional sanitized summary export.
3. Optional commit-friendly shared metadata in `tailtrail-meta/harness-summary.jsonl`.
4. Optional internal aggregation for enterprise admins from checked-out repos.
5. Optional public contribution flow only after privacy, legal, and governance review.
6. No automatic upload in the initial implementation.

This keeps TailTrail useful immediately while leaving room for product-level improvement later.

## CLI Surface

```bash
python3 scripts/tailtrail.py bootstrap snapshot --root .
python3 scripts/tailtrail.py bootstrap status --root .
python3 scripts/tailtrail.py harness quick --root .
python3 scripts/tailtrail.py harness review --root .
python3 scripts/tailtrail.py harness confidence --root .
python3 scripts/tailtrail.py harness recommendations --root . --format markdown
python3 scripts/tailtrail.py harness export-summary --root . --write-result
python3 scripts/tailtrail.py harness readiness --root .
```

Aggregation command:

```bash
python3 scripts/tailtrail.py harness aggregate-shared --summary summary-a.jsonl --summary summary-b.jsonl
python3 scripts/tailtrail.py harness readiness --summary summary-a.jsonl --summary summary-b.jsonl
```

## Implementation Files

- `scripts/harness-review.py`
- `scripts/bootstrap-snapshot.py` implemented
- `templates/harness-review.md`
- `tests/test_bootstrap_snapshot.py`
- `tests/test_harness_review.py`
- `tests/test_harness_summary_sanitizer.py`
- `.tailtrail/harness-review.md`
- `.tailtrail/harness-recommendations.json`
- `.tailtrail/harness-summary.json`
- `.tailtrail/bootstrap-snapshot.json`

## Review Dimensions

### Bootstrap Fit

Checks whether TailTrail started from a compact safe workspace snapshot when it would help.

Examples:

- Repo overview prompts should use or suggest Bootstrap Snapshot.
- Scanner prompts should use the snapshot to identify manifests and scanner files before broad reads.
- Tiny text-only prompts should skip the snapshot.
- Stale snapshots should be refreshed before Navigator relies on them.
- Snapshot output should remain compact and source-content-free.
- Harness Review reports one explicit label:
  - `missing`: no useful snapshot is available.
  - `useful`: a fresh snapshot has meaningful safe repo/runtime signals.
  - `stale`: the snapshot is invalid or workspace shape changed.
  - `noisy`: the snapshot is fresh but too broad to trust as a precise first-read map.

### Workflow Fit

Checks whether Navigator selected the right TailTrail features.

Examples:

- A small bug fix should usually avoid AIDLC.
- A broad regulated workflow should include AIDLC.
- A repo overview can use Code Graph Mapper if the user asks for architecture or important features.
- Vulnerability prompts should include Security And Vulnerability Intelligence.

### Context Fit

Checks whether TailTrail loaded focused context.

Examples:

- Prefer graph cache and changed files before full tree reads.
- Prefer policy and guardrail slices relevant to the task.
- Avoid roadmap and pitch files unless changing TailTrail itself.

### Validation Fit

Checks whether TailTrail recommended or captured meaningful validation.

Examples:

- Unit-level bug fix should include focused unit tests.
- Scanner issue fix should include scanner or equivalent validation.
- Refactor should include behavior-preserving test evidence.

### Metric Confidence

Checks whether TailTrail labels value and token claims honestly.

Confidence bands:

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

### Learning Fit

Checks whether learnings were safe to use.

Examples:

- High-confidence, recent, file/tag-relevant learning can be shown as advisory.
- Low-confidence accepted changes should not be recorded as trusted learning.
- Stale or contradictory learning should trigger refresh awareness.

### Scanner And Security Fit

Checks whether TailTrail handled scanner and security work carefully.

Examples:

- Ask before running heavy scans.
- Preserve exact scanner evidence.
- Do not claim remediation without fixed-version or validation evidence.
- Connect findings to graph impact when graph data exists.

### Code Precision Fit

Checks whether the harness identified concrete files, callers, tests, policies, and safeguards before code writing.

## Recommendation Format

Recommendations should be review-first.

Example:

```text
Recommended change:
Add a Navigator rule so small bug fixes that mention "add tests" do not automatically route to AIDLC.

Why:
Harness review found repeated small bug-fix prompts where AIDLC made the plan heavier than needed.

Proposed files:
- scripts/navigator.py
- tests/test_navigator_core.py
- ROADMAP.md

Suggested prompt/rule change:
When task_type includes "bug_fix" and the only feature-like signal is unit-test addition,
prefer review -> test_precision and skip AIDLC unless risk, compliance, release,
handoff, multi-step planning, or regulated-work keywords are present.

User note:
These are recommended changes. Review before adding.
```

## Privacy And Governance

V1 rules:

- No network calls.
- No model calls.
- No automatic uploads.
- No hidden background process.
- No command execution in Bootstrap Snapshot that runs project code.
- No raw prompt capture in shareable summaries.
- No source capture in shareable summaries.
- No user behavior scoring.
- No automatic TailTrail self-editing.

If a future enterprise aggregation path is added, it must support:

- admin-controlled enablement
- visible summary preview
- local sanitization tests
- opt-in export
- retention rules
- documented schema
- ability to disable contribution completely

## Implementation Phases

### Phase 0: Bootstrap Snapshot

Status: implemented.

Implemented:

- `bootstrap snapshot`
- `bootstrap status`
- `bootstrap refresh`
- `.tailtrail/bootstrap-snapshot.json`
- freshness checks
- tests that assert source-body and project-code execution safety flags plus signal-only output behavior
- Navigator recommendation when snapshot is missing for overview, graph, scanner, test, CI, vulnerability, architecture, or handoff tasks

### Phase A: Local Quick Review

Implement:

- `harness quick`
- read local task/outcome/context/token summary files
- produce concise findings
- no writes unless `--write-result`

### Phase B: Standard Harness Review

Implement:

- `harness review`
- Markdown report
- recommendation codes
- proposed file list
- metric confidence labels
- tests for workflow fit and metric confidence

### Phase C: Sanitized Summary Export

Implement:

- `harness export-summary`
- allowlisted JSON schema
- sanitizer tests
- local output only

### Phase D: Local Aggregation

Implement later:

- aggregate multiple local summaries
- show repeated TailTrail behavior issues
- no network

### Phase E: Enterprise Or Public Product Loop

Implement only after review:

- optional upload or manual contribution
- governance controls
- admin approval
- public contribution policy

## Acceptance Criteria

The feature is ready when:

- Bootstrap Snapshot can create a compact safe repo/runtime summary
- Navigator can use or recommend Bootstrap Snapshot in the right task types
- a user can run local harness review and get actionable findings
- generated recommendations explain proposed files and rationale
- metric confidence is clearly labeled
- sanitized summary export contains only allowlisted fields
- tests prove raw prompt/source/path/repo/user data is not exported
- no normal task becomes slower unless the user requests harness review
- snapshot creation is skipped for tiny tasks where it would add noise
- TailTrail pitch can mention Meta-Harness-style optimization without overclaiming

## Open Design Questions

These should be discussed before implementation:

- Should Bootstrap Snapshot be created automatically by `tailtrail start`, or should Navigator ask approval the first time?
- What exact freshness rule should mark a snapshot stale: elapsed time, manifest changes, git HEAD change, or code graph staleness?
- Should Bootstrap Snapshot be committed for shared repos, or treated as local `.tailtrail/` state only?
- Should `tailtrail start` offer an optional post-task harness review prompt, or should it stay fully manual?
- Should summaries be stored per task or rolled into monthly local reports?
- Should internal enterprise admins get a separate aggregation script?
- What fields are safe enough for public opt-in summary contribution?
- Should recommendation codes be versioned independently from TailTrail versions?
- Should benchmark harness scenarios be generated automatically from repeated harness findings, or only suggested?

## Best Current Recommendation

Start with Layer 1 only.

Before Layer 1, add Bootstrap Snapshot because it improves Navigator input quality and gives Harness Review a pre-task signal to score.

Then add Layer 1 local Harness Review.

Then add Layer 2 sanitized export after sanitizer tests exist.

Treat Layer 3 as a future product governance capability, not a default developer feature.

This gives TailTrail practical self-review without making the product feel heavy, noisy, or invasive.

## Token Harness Feedback Layer

Status: implemented as TH-6.

Meta-Harness now consumes sanitized Token Harness signals through the existing shared-summary path. The goal is not to make TailTrail self-editing; the goal is to detect repeated token-strategy behavior and create reviewable proposals.

Flow:

```text
.tailtrail/token-harness-events.jsonl
        -> harness shared-summary
        -> tailtrail-meta/harness-summary.jsonl
        -> harness analyze
        -> harness propose
```

Shared metadata includes only categorical token fields:

- `token_strategy`
- `token_exactness_class`
- `token_evidence_label`
- `token_reduction_band`
- `token_proof_label`
- `token_quality_outcome`
- `token_holdout`
- `token_confidence_gate`

Meta-Harness can now detect:

- token strategy quality risk
- token proof gap
- low/no reduction patterns
- holdout/control gap
- exactness mismatch

Proposals remain review-only. They identify likely files, recommended prompt changes, verification, and rollback guidance, but they do not edit TailTrail automatically.
