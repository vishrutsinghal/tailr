# TailTrail Evaluation Harness

TailTrail Evaluation Harness is the planned umbrella for proving whether TailTrail improves AI-assisted development outcomes.

It consolidates the evidence-related features that currently exist as separate surfaces:

- Benchmark Harness
- Measured Efficacy Evidence
- Guardrail Precision
- Outcome Telemetry
- Quality Loop
- Meta-Harness
- Token Harness proof and measured telemetry
- Enterprise/value reporting
- Build Week demo evidence
- future agent/scenario evaluation inspired by q-evaluation-harness-style repeatable task benchmarking

The goal is not to delete working features immediately. The goal is to create one product model, one report vocabulary, and one command family while keeping old commands as compatibility aliases until the new design is stable.

## Design Review Recommendations

This section records the accepted design-review outcome. It refines the plan below so the umbrella stays consistent with TailTrail's core direction: small, removable, evidence-first changes rather than a heavy new platform.

### Committed Slice vs Conditional Phases

- Committed first slice: **EH-0, EH-1, EH-2, EH-3, EH-4, EH-8**. This delivers the full `eval` command family (every existing evidence feature reachable), a deterministic scenario engine, and the Build Week demo as a scenario record.
- Conditional phases (evidence-gated): **EH-5, EH-6, EH-7**. Start these only after EH-4 shows real use. They add deeper evidence normalization, not new feature coverage.
- Pulled forward from EH-7: a single narrow piece — Token Harness proof emitting one normalized event — is included in the committed slice, because token evidence is TailTrail's headline claim and a scenario report without it feels incomplete in demos.
- Deferred and split out: **EH-9 (live-agent mode)** moves to its own separate RFC/design doc. It is a different risk class (cost, sandboxing, secrets, supply chain) and must not be carried as an in-track phase.
- Implementation order is fixed for V1: **EH-0 -> EH-1 -> EH-2 -> EH-3 -> EH-4 -> EH-8 -> EH-5 -> EH-7 -> EH-6**. EH-8 may ship inside EH-4 if the Build Week fixture is ready during scenario work.

### Coverage Note

After the committed slice, 100% of existing evidence features are usable under `eval ...` (via EH-2 aliases). What EH-5/EH-6/EH-7 add is deeper cross-feature evidence normalization into `.tailtrail/evaluation/events.jsonl`, not new surface. Until then the shared event stream is populated by scenario (EH-4), the demo scenario (EH-8), and token proof (pulled-forward slice) only; portfolio/meta/full-token feeds arrive with EH-5/6/7.

### Schema Core Is Frozen; Everything Else Is Additive

To prevent downstream breakage once EH-4/5/6/7 depend on the schema:

- Frozen required core: `schema_version`, `event_id`, `created_at`, `source_feature`, `task_class`, `scores` (as an open map), `claim_boundaries`.
- All other fields are optional and additive. New fields must never be required in a way that breaks older events.
- Compatibility rule: readers ignore unknown fields; a schema change that removes or renames a core field requires a `schema_version` bump and a migration note.

### Scores Must Be Rubric-Backed, Not Soft Floats

Deterministic scoring requires a defined, inspectable rubric. Until a rubric justifies fractional values, prefer boolean/integer signals over floats.

- Each dimension must map to countable, inspectable signals (for example, `dependency_discipline = 1.0 if manifest diff is empty else 0.0`).
- Float scores (such as `0.8`) are allowed only when the rubric documents exactly which signals produce that value.
- Until validated against real scenarios, label scores `heuristic` per the adapter contract; do not present them as measured.

### Privacy Is an Invariant, Not a Default

Evaluation events may be shared as project context, so the rule is absolute:

- Never store raw source, raw prompts, raw scanner logs, or secrets in eval events.
- Store only compact references (paths, IDs, hashes) and short summaries.
- This replaces any "no raw ... by default" phrasing elsewhere in this document.

### Deprecation Signal With a Definition of Done

Old commands stay working with no removal date, but the migration must be able to finish at the command layer:

- After EH-4, `eval` is documented first; old commands print a one-line "also available as `eval ...`" notice.
- Definition of done for command migration: docs list `eval` first, help groups old commands under compatibility, and the registry lists `eval` as primary.

### Doc-Drift Alignment

The phase ordering in this file's "Recommended Implementation Order" and the "Evaluation Harness Consolidation Track" in `ROADMAP.md` must list phases in the same order. Keep them synchronized and covered by the existing registry-drift check.

### Command Conflict Rule

When old features have overlapping names, `eval` owns the canonical meaning:

- `eval tokens route` maps to `token-harness route`, not legacy `token route`.
- `eval tokens auto` maps to `token-auto.py` only if a later phase needs an explicit autopilot command.
- `eval tokens budget` maps to `token-budget-coach.py`.
- `eval tokens telemetry` maps to `token-telemetry.py`.
- `eval tokens savings` maps to `token-savings.py`.
- `eval scenario ...` is reserved for Evaluation Harness scenarios only. It must not call `benchmark-tailtrail.py` directly except through explicit compatibility actions such as `eval artifact analyze`.
- `eval meta ...` maps to Meta-Harness behavior only, not generic benchmark analysis.

If an alias is ambiguous, EH-0 must mark it `needs-decision` and block it from EH-2 until the mapping is explicit.

## Product Thesis

TailTrail guides AI coding work. Evaluation Harness proves whether that guidance helped.

Evaluation Harness answers:

- Did the implementation satisfy the requirement?
- Did focused validation pass?
- Did review catch real issues?
- Did TailTrail preserve safeguards?
- Did it avoid unnecessary dependencies?
- Did it avoid broad rewrites?
- Did it ask approval before heavy commands?
- Did it reduce context safely?
- Did measured token telemetry support the savings claim?
- Did workflow quality improve over repeated tasks?
- Is there enough evidence to change TailTrail itself?

## Non-Goals

Do not implement these in the first consolidation slice:

- no live model/API calls
- no automatic Codex/Claude execution
- no background observer
- no hidden prompt logging
- no automatic TailTrail source edits
- no automatic upload of metadata
- no replacement of existing commands in one breaking release
- no leaderboard claims without repeatable scenario evidence
- no exact token-savings claims without measured telemetry

Live-agent evaluation can come later as an opt-in mode after deterministic scenario scoring is stable.

## Current Feature Inventory

### Benchmark Harness

Current surfaces:

- `scripts/benchmark-tailtrail.py`
- `scripts/analyze-benchmark.py`
- `benchmarks/scenarios/`
- `python3 scripts/tailtrail.py benchmark ...`
- `python3 scripts/tailtrail.py analyze ...`

Current role:

- scores saved baseline/TailTrail artifacts
- detects whether TailTrail-style artifacts include expected review, validation, dependency, and safeguard behavior

New Evaluation Harness home:

- `eval scenario score`
- `eval scenario report`
- `eval artifact compare`

Keep old commands as aliases:

- `benchmark ...` -> `eval scenario ...`
- `analyze ...` -> `eval artifact analyze`

### Measured Efficacy Evidence

Current surfaces:

- `scripts/efficacy-run.py`
- `scripts/efficacy-benchmark.py`
- `benchmarks/efficacy/`
- `python3 scripts/tailtrail.py efficacy run`
- `python3 scripts/tailtrail.py efficacy report`
- `python3 scripts/tailtrail.py benchmark efficacy`

Current role:

- portfolio evidence across bug fix, review, security, CI/Sonar, dependency, feature, token-heavy artifact, and learning-governance scenarios
- strict measured/estimated token labeling

New Evaluation Harness home:

- `eval portfolio run`
- `eval portfolio report`
- `eval portfolio compare`

Keep old commands as aliases:

- `efficacy run` -> `eval portfolio run`
- `efficacy report` -> `eval portfolio report`
- `benchmark efficacy` -> `eval portfolio run`

### Guardrail Precision

Current surfaces:

- `scripts/guardrail-precision.py`
- `benchmarks/guardrail-precision/`
- `python3 scripts/tailtrail.py guardrail precision`

Current role:

- tests guardrail false-positive and precision behavior before stricter enforcement

New Evaluation Harness home:

- `eval guardrails precision`
- `eval guardrails report`

Keep old command as alias:

- `guardrail precision` -> `eval guardrails precision`

### Outcome Telemetry

Current surfaces:

- `scripts/outcome-telemetry.py`
- `python3 scripts/tailtrail.py outcome capture`
- `python3 scripts/tailtrail.py outcome summarize`

Current role:

- captures approved compact outcomes such as task type, workflow used, acceptance, validation result, review result, time-saved band, fit, and learning quality

New Evaluation Harness home:

- `eval outcome capture`
- `eval outcome summarize`
- `eval outcome export`

Keep old commands as aliases:

- `outcome capture` -> `eval outcome capture`
- `outcome summarize` -> `eval outcome summarize`

### Quality Loop

Current surfaces:

- `scripts/quality-loop.py`
- `python3 scripts/tailtrail.py quality-loop capture`
- `python3 scripts/tailtrail.py quality-loop review`

Current role:

- reviews TailTrail workflow quality, feature overlap, missed gates, weak routing, and tuning opportunities

New Evaluation Harness home:

- `eval workflow capture`
- `eval workflow review`
- `eval workflow recommend`

Keep old commands as aliases:

- `quality-loop capture` -> `eval workflow capture`
- `quality-loop review` -> `eval workflow review`

### Meta-Harness

Current surfaces:

- `scripts/harness-review.py`
- `scripts/meta-harness-analyze.py`
- `scripts/meta-harness-propose.py`
- `META-HARNESS-IMPLEMENTATION.md`
- `python3 scripts/tailtrail.py harness quick`
- `python3 scripts/tailtrail.py harness review`
- `python3 scripts/tailtrail.py harness readiness`
- `python3 scripts/tailtrail.py harness analyze`
- `python3 scripts/tailtrail.py harness propose`

Current role:

- post-task analysis of TailTrail behavior
- metric confidence
- bootstrap-fit scoring
- sanitized shared metadata
- readiness tiers
- registry-aware product-improvement proposals

New Evaluation Harness home:

- `eval meta quick`
- `eval meta review`
- `eval meta readiness`
- `eval meta analyze`
- `eval meta propose`
- `eval meta proposal-status`
- `eval meta proposal-record`

Keep old commands as aliases:

- `harness ...` -> `eval meta ...`

Meta-Harness remains the product-improvement analysis layer under Evaluation Harness. It should not become the whole Evaluation Harness.

### Token Harness Proof And Telemetry

Current surfaces:

- `scripts/token-harness.py`
- `scripts/token-harness-reduce.py`
- `scripts/token-harness-ledger.py`
- `scripts/token-harness-proof.py`
- `scripts/token-harness-bridge.py`
- `scripts/token-telemetry.py`
- `scripts/token-savings.py`
- `scripts/token-budget-coach.py`
- `scripts/context-receipt.py`
- `python3 scripts/tailtrail.py token-harness ...`
- `python3 scripts/tailtrail.py telemetry ...`
- `python3 scripts/tailtrail.py savings ...`
- `python3 scripts/tailtrail.py budget ...`
- `python3 scripts/tailtrail.py receipt ...`

Current role:

- context routing
- reducers
- receipts
- append-only token evidence ledger
- proof labels
- measured telemetry import
- budget calibration
- optional approved runtime compression bridge

New Evaluation Harness home:

- `eval tokens route`
- `eval tokens reduce`
- `eval tokens receipt`
- `eval tokens ledger`
- `eval tokens proof`
- `eval tokens telemetry`
- `eval tokens savings`
- `eval tokens budget`

Keep old commands as aliases:

- `token-harness ...` -> `eval tokens ...`
- `telemetry ...` -> `eval tokens telemetry ...`
- `savings ...` -> `eval tokens savings ...`
- `budget ...` -> `eval tokens budget ...`
- `receipt ...` -> `eval tokens receipt ...`

Token Harness should continue to own exactness and token-safety rules. Evaluation Harness consumes its evidence.

### Enterprise Reporting

Current surfaces:

- `scripts/tailtrail-report.py`
- `python3 scripts/tailtrail.py report`
- `python3 scripts/tailtrail.py report value`
- `python3 scripts/tailtrail.py report trend`
- `python3 scripts/tailtrail.py report pr`

Current role:

- local advisory reports from quality, outcomes, learning, refresh, optional AIDLC, token evidence, and value posture

New Evaluation Harness home:

- `eval report value`
- `eval report trend`
- `eval report pr`
- `eval report enterprise`

Keep old commands as aliases:

- `report value` -> `eval report value`
- `report trend` -> `eval report trend`
- `report pr` -> `eval report pr`

### Build Week Demo Evidence

Current surfaces:

- `buildweek-demo-project/`
- `buildweek-demo-project/DEMO-PROMPTS.md`
- `buildweek-demo-project/DEMO-RUNBOOK.md`
- `buildweek-demo-project/FEATURE-COVERAGE.md`

Current role:

- judge-friendly demo target with a failing validation test and optional evidence commands

New Evaluation Harness home:

- `eval scenario run --scenario buildweek-validation`
- `eval scenario report --scenario buildweek-validation`

Keep demo files as human-facing examples. Do not make Build Week demo the core test mechanism.

## New Feature: Scenario Harness

This is the new piece inspired by repeatable code-generation evaluation harnesses.

Purpose:

Run controlled task scenarios and compare workflow variants.

Example variants:

- `baseline`
- `tailtrail-start`
- `tailtrail-start-graph`
- `tailtrail-start-graph-review`
- `tailtrail-start-graph-review-token`

Initial implementation must be deterministic and local.

Do not run live agents in V1. Instead, evaluate saved artifacts and command outputs.

Future optional live mode:

```bash
python3 scripts/tailtrail.py eval scenario run-live --backend codex --scenario validation-bug --approved
python3 scripts/tailtrail.py eval scenario run-live --backend claude --scenario validation-bug --approved
```

Live mode requires:

- explicit approval
- isolated workspace
- timeout
- cost warning
- no secrets
- no hidden telemetry
- saved sanitized output
- no automatic leaderboard publication

## Proposed Command Surface

Primary umbrella command:

```bash
python3 scripts/tailtrail.py eval ...
```

Subcommands:

```bash
python3 scripts/tailtrail.py eval scenario list
python3 scripts/tailtrail.py eval scenario run --scenario validation-bug
python3 scripts/tailtrail.py eval scenario compare --scenario validation-bug
python3 scripts/tailtrail.py eval scenario report --scenario validation-bug

python3 scripts/tailtrail.py eval portfolio run
python3 scripts/tailtrail.py eval portfolio report

python3 scripts/tailtrail.py eval guardrails precision

python3 scripts/tailtrail.py eval outcome capture --approved ...
python3 scripts/tailtrail.py eval outcome summarize --month 2026-07

python3 scripts/tailtrail.py eval workflow capture --approved ...
python3 scripts/tailtrail.py eval workflow review --month 2026-07

python3 scripts/tailtrail.py eval meta quick --root .
python3 scripts/tailtrail.py eval meta readiness --root .
python3 scripts/tailtrail.py eval meta analyze --summary tailtrail-meta/harness-summary.jsonl
python3 scripts/tailtrail.py eval meta propose --root . --proposal-id MH-2026-07-001

python3 scripts/tailtrail.py eval tokens proof report
python3 scripts/tailtrail.py eval tokens telemetry import-openai --source usage.jsonl
python3 scripts/tailtrail.py eval tokens savings report

python3 scripts/tailtrail.py eval report value --month 2026-07
python3 scripts/tailtrail.py eval report trend
python3 scripts/tailtrail.py eval report pr --only quality --only tokens
```

Compatibility commands stay supported:

```bash
python3 scripts/tailtrail.py benchmark ...
python3 scripts/tailtrail.py efficacy ...
python3 scripts/tailtrail.py outcome ...
python3 scripts/tailtrail.py quality-loop ...
python3 scripts/tailtrail.py harness ...
python3 scripts/tailtrail.py token-harness ...
python3 scripts/tailtrail.py report ...
python3 scripts/tailtrail.py guardrail precision
```

Docs should call these compatibility commands after the Evaluation Harness is stable.

## Shared Schema

Create one normalized event/report schema so features can feed the same reports.

File:

```text
schemas/evaluation-harness-event.schema.json
```

Suggested JSON shape:

```json
{
  "schema_version": "1",
  "event_id": "eval-2026-07-001",
  "created_at": "2026-07-18T00:00:00Z",
  "source_feature": "scenario|portfolio|guardrail|outcome|workflow|meta|tokens|report",
  "scenario_id": "validation-bug",
  "variant": "baseline|tailtrail-start|tailtrail-start-graph|tailtrail-start-graph-review",
  "task_class": "bug-fix|review|security|ci-sonar|dependency|feature|token-heavy|learning",
  "root": ".",
  "input_ref": "benchmarks/evaluation/scenarios/validation-bug/task.md",
  "artifact_refs": [],
  "commands": [],
  "scores": {
    "requirement_fulfillment": 1.0,
    "tests_passed": 1.0,
    "safeguards_preserved": 1.0,
    "dependency_discipline": 1.0,
    "diff_focus": 1.0,
    "review_quality": 0.8,
    "approval_safety": 1.0,
    "token_quality": 0.7
  },
  "evidence": [
    {
      "label": "local-evidence",
      "kind": "test-result",
      "path": "reports/eval/validation-bug/tailtrail/result.json",
      "summary": "3 tests passed"
    }
  ],
  "token_usage": {
    "label": "estimated|local-evidence|measured|benchmark-measured",
    "baseline_total": null,
    "tailtrail_total": null,
    "source": "local-estimate|telemetry|ledger|scenario"
  },
  "outcome": {
    "accepted": null,
    "validation_outcome": "pass|fail|not_run",
    "review_outcome": "clean|findings|not_run"
  },
  "quality_findings": [],
  "meta_findings": [],
  "claim_boundaries": [
    "No exact token savings without measured telemetry."
  ]
}
```

## Scoring Dimensions

Use stable dimensions across scenario, portfolio, and reports:

| Dimension | Question | Example Signals |
|---|---|---|
| Requirement Fulfillment | Did it solve the actual task? | expected behavior, requirement checklist, post-change review |
| Validation | Did focused validation run and pass? | test command, CI summary, exact pass/fail |
| Safety / Safeguards | Were guards preserved? | auth, validation, escaping, privacy, data integrity |
| Dependency Discipline | Did it avoid unnecessary packages? | dependency gate, manifest diff |
| Diff Focus | Was the change small and scoped? | changed files, unrelated churn |
| Review Quality | Did review find useful issues and verify requirement fulfillment? | review findings, false positives, residual risk |
| Approval Safety | Did it ask before heavy or risky actions? | scanner/build approval, provider-output approval |
| Token Quality | Did it reduce context without losing material facts? | Token Harness evidence labels, receipts, telemetry |
| Workflow Fit | Did TailTrail choose the right feature path? | Navigator choices, Quality Loop, Meta-Harness |
| Product Learning | Is there enough evidence to improve TailTrail itself? | Meta-Harness readiness, registry-aware proposals |

Scores must be deterministic in V1.

## Scenario Directory Design

Create:

```text
benchmarks/evaluation/
  README.md
  scenarios/
    validation-bug/
      scenario.yaml
      task.md
      baseline/
        output.md
        result.json
      tailtrail-start/
        output.md
        result.json
      tailtrail-start-graph/
        output.md
        result.json
      expected.json
```

`scenario.yaml`:

```yaml
id: validation-bug
task_class: bug-fix
description: Fix boundary validation without weakening existing checks.
target_files:
  - src/claims_api/validation.py
focused_validation:
  - python3 -m unittest discover -s tests
variants:
  - baseline
  - tailtrail-start
  - tailtrail-start-graph
  - tailtrail-start-graph-review
score_weights:
  requirement_fulfillment: 0.25
  validation: 0.20
  safety: 0.15
  dependency_discipline: 0.10
  diff_focus: 0.10
  review_quality: 0.10
  approval_safety: 0.05
  token_quality: 0.05
```

Keep scenario fixtures small and reviewable.

## Implementation Phases

### Phase EH-0: Usage And Overlap Audit

Status: committed slice, run first.

Purpose: consolidating dead surface just relabels dead surface. Before adding the `eval` router, inventory which evidence scripts actually produce used output and where they overlap.

EH-0 is an audit phase, not a refactor phase. It must produce a machine-readable decision report that EH-2 uses to avoid building ambiguous or redundant aliases.

#### EH-0 Implementation Files

Add:

```text
scripts/evaluation-audit.py
reports/evaluation-harness/.gitkeep
tests/test_evaluation_audit.py
```

Update:

```text
scripts/tailtrail.py
TAILTRAIL-COMMANDS.md
USER-GUIDE.md
ROADMAP.md
EVALUATION-HARNESS.md
scripts/check-tailtrail.py
tailtrail-registry.json
```

Do not add `scripts/evaluation-harness.py` in EH-0 unless it is help-only. The router belongs to EH-2.

#### EH-0 Command

Primary command:

```bash
python3 scripts/tailtrail.py eval audit
python3 scripts/tailtrail.py eval audit --format json
python3 scripts/tailtrail.py eval audit --strict
python3 scripts/tailtrail.py eval audit --write-report --approved
```

Implementation detail:

- `tailtrail.py eval audit` may call `scripts/evaluation-audit.py`.
- If `tailtrail.py eval` does not exist yet, add only the `audit` action in EH-0. Other `eval` actions return a clear EH-2/EH-4 pending message.
- `--write-report` writes to:

```text
reports/evaluation-harness/eh0-audit.json
reports/evaluation-harness/eh0-audit.md
```

Writing requires `--approved`.

#### Evidence Feature Scope

EH-0 audits these current evidence surfaces:

| Feature Group | Scripts / Commands |
|---|---|
| Benchmark Harness | `benchmark-tailtrail.py`, `analyze-benchmark.py`, `tailtrail benchmark`, `tailtrail analyze` |
| Measured Efficacy | `efficacy-run.py`, `efficacy-benchmark.py`, `tailtrail efficacy`, `tailtrail benchmark efficacy` |
| Guardrail Precision | `guardrail-precision.py`, `tailtrail guardrail precision` |
| Outcome Telemetry | `outcome-telemetry.py`, `tailtrail outcome` |
| Quality Loop | `quality-loop.py`, `tailtrail quality-loop` |
| Meta-Harness | `harness-review.py`, `meta-harness-analyze.py`, `meta-harness-propose.py`, `tailtrail harness` |
| Token Evidence | `token-harness*.py`, `token-telemetry.py`, `token-savings.py`, `token-budget-coach.py`, `context-receipt.py` |
| Enterprise Reporting | `tailtrail-report.py`, `tailtrail report` |
| Build Week Evidence | `buildweek-demo-project/` and future `benchmarks/evaluation/` |

#### Audit Signals

For each feature group, collect:

- commands exposed in `scripts/tailtrail.py`
- scripts that exist on disk
- docs that mention the command or script
- tests that mention the command or script
- registry feature IDs that claim ownership
- output files or fixture directories, when deterministic and local
- evidence labels used by the feature
- whether writes require `--approved`
- whether raw prompts/source/logs/secrets are stored
- whether the feature overlaps another feature

No command execution is required for EH-0 except reading local files. EH-0 must be deterministic and stdlib-only.

#### Decision Values

Every audited feature gets exactly one decision:

| Decision | Meaning | EH-2 Behavior |
|---|---|---|
| `alias` | Feature is active, non-ambiguous, and should be reachable under `eval`. | EH-2 may add a direct alias. |
| `merge` | Feature is active but should be grouped with a related feature. | EH-2 may add an alias only through the merged canonical group. |
| `needs-decision` | Feature or command mapping is ambiguous. | EH-2 must not expose it under `eval`. |
| `retire` | Feature should not be exposed through `eval` yet. | Old command remains; no deletion in EH-0. |

Retire never means "delete now." Deletion requires a separate compatibility review after EH-4.

#### Canonical Mapping Rules

EH-0 must produce the canonical mapping table for EH-2:

| Current Surface | Canonical Eval Surface |
|---|---|
| `benchmark ...` | `eval artifact ...` or `eval scenario ...` depending on audit result |
| `analyze ...` | `eval artifact analyze ...` |
| `efficacy ...` | `eval portfolio ...` |
| `guardrail precision` | `eval guardrails precision ...` |
| `outcome ...` | `eval outcome ...` |
| `quality-loop ...` | `eval workflow ...` |
| `harness ...` | `eval meta ...` |
| `token-harness route` | `eval tokens route ...` |
| `token route` | `eval tokens auto ...` only if retained after audit |
| `telemetry ...` | `eval tokens telemetry ...` |
| `savings ...` | `eval tokens savings ...` |
| `budget ...` | `eval tokens budget ...` |
| `receipt ...` | `eval tokens receipt ...` |
| `report value|trend|pr` | `eval report value|trend|pr` |

If `benchmark ...` and `scenario ...` overlap, EH-0 must choose one canonical home and mark the other as compatibility-only.

#### EH-0 Output Schema

JSON output shape:

```json
{
  "schema_version": "1",
  "type": "evaluation-harness-audit",
  "created_at": "2026-07-18T00:00:00Z",
  "status": "passed|needs-decision|failed",
  "features": [
    {
      "feature_group": "token-evidence",
      "current_commands": ["tailtrail token-harness", "tailtrail telemetry", "tailtrail savings"],
      "scripts": ["scripts/token-harness.py", "scripts/token-telemetry.py", "scripts/token-savings.py"],
      "docs": ["TOKEN-HARNESS.md", "TAILTRAIL-COMMANDS.md", "USER-GUIDE.md"],
      "tests": ["tests/test_token_harness.py", "tests/test_deterministic_tools.py"],
      "registry_ids": ["token-harness"],
      "evidence_labels": ["estimated", "local-evidence", "measured", "benchmark-measured"],
      "writes_require_approval": true,
      "raw_data_storage": "blocked",
      "overlaps": ["enterprise-reporting"],
      "decision": "alias",
      "canonical_eval_surface": "eval tokens",
      "reason": "active feature with clear token-evidence ownership"
    }
  ],
  "blocked_aliases": [
    {
      "current_surface": "tailtrail token route",
      "reason": "ambiguous with token-harness route until audit chooses canonical meaning"
    }
  ],
  "recommendations": [
    "Expose token-harness route as eval tokens route.",
    "Keep legacy token route as compatibility-only until usage proves it is still needed."
  ]
}
```

Markdown output should be short and implementation-facing:

```text
# TailTrail Evaluation Harness EH-0 Audit

- Status: needs-decision
- Feature groups audited: 9
- Alias-ready: 7
- Merge-needed: 1
- Blocked: 1

## Blocked Aliases

- `tailtrail token route` -> ambiguous with `token-harness route`

## EH-2 Ready Aliases

- `eval portfolio` -> efficacy
- `eval guardrails` -> guardrail precision
- `eval meta` -> harness/meta
```

#### Strict Mode

`--strict` exits non-zero when:

- a feature group has no decision
- a feature marked `alias` has no canonical eval surface
- a canonical eval surface conflicts with another feature
- a script listed in the audit does not exist
- a command is exposed in `tailtrail.py` but not assigned to a feature group
- a feature stores raw prompts/source/logs/secrets without an explicit blocking note
- a write-capable feature lacks approval gating

Default mode exits zero and prints the report, even when decisions are needed.

#### EH-0 Tests

Add tests for:

- audit includes every known evidence feature group
- strict mode fails on an intentionally ambiguous mapping fixture
- `retire` does not delete or mark old commands as removed
- write-capable features are flagged when approval gating is missing
- raw-data storage is flagged unless marked blocked/sanitized
- Markdown and JSON outputs are stable
- `tailtrail.py eval audit` dispatches correctly

Acceptance:

- each existing evidence feature is marked keep/merge/retire with a reason
- EH-2 aliases only wrap features marked keep or merge
- `retire` means "do not expose through `eval` yet"; it does not mean delete the old command during EH-0
- any removal or deprecation requires a separate compatibility review after EH-4
- ambiguous aliases are marked `needs-decision` and blocked from EH-2 until resolved
- `python3 scripts/tailtrail.py eval audit --strict` passes before EH-2 begins
- `reports/evaluation-harness/eh0-audit.md` can be written with `--write-report --approved`

### Phase EH-1: Umbrella Documentation

Status: implemented.

Purpose:

EH-1 makes Evaluation Harness understandable before more command behavior is added. The main risk after EH-0 is not missing code; it is product drift: users seeing many separate evidence features without one clear model for when to use them, what each one proves, and which command family will become canonical.

EH-1 is therefore a documentation and governance phase. It should not add new scoring logic, execute benchmarks, rewrite old commands, or introduce new event formats. It should make `EVALUATION-HARNESS.md` the implementation hub and keep all other docs as short entry points that link back to that hub.

#### Files To Update

`EVALUATION-HARNESS.md`

- Role: primary implementation hub.
- Purpose: owns the complete Evaluation Harness design, phase order, command migration model, canonical mappings, privacy boundaries, schema direction, and acceptance criteria.
- Required EH-1 content:
  - product thesis and non-goals
  - existing feature inventory
  - canonical `eval ...` command map
  - phase-by-phase implementation plan
  - compatibility policy for old commands
  - privacy and claim-boundary rules
  - explicit "what is not implemented yet" list
  - acceptance criteria for each phase
- Why needed: without one hub, Benchmark Harness, Efficacy, Token Harness, Meta-Harness, Outcome Telemetry, and Quality Loop will keep evolving as separate products.

`ROADMAP.md`

- Role: executive tracker.
- Purpose: shows the Evaluation Harness track in brief while pointing to `EVALUATION-HARNESS.md` for detailed design.
- Required EH-1 content:
  - EH phase list in the same order as this file
  - short status notes for EH-0 and EH-1
  - clear statement that `EVALUATION-HARNESS.md` is the major implementation hub
  - no duplicate long-form design that can drift from the hub
- Why needed: roadmap is used for planning and demos; it should show progress without becoming a second source of truth.

`USER-GUIDE.md`

- Role: end-user explanation.
- Purpose: explains when a user should care about Evaluation Harness and which current command is safe to run.
- Required EH-1 content:
  - "use this when you want evidence, not implementation"
  - current command: `python3 scripts/tailtrail.py eval audit`
  - explanation that EH-0/EH-1 do not run tasks, scans, model calls, or hidden telemetry
  - pointer to future phases without asking users to memorize them
- Why needed: users should understand that Evaluation Harness is for proof and reporting, not a replacement for Navigator implementation flow.

`TAILTRAIL-COMMANDS.md`

- Role: command catalog.
- Purpose: lists the current `eval` command and planned future command family without implying unfinished commands already work.
- Required EH-1 content:
  - current command examples for `eval audit`
  - `--strict`, `--format json`, and `--write-report --approved`
  - pending command family with "planned after EH-0/EH-1" language
- Why needed: command docs must be accurate; they should prevent users from trying unfinished aliases.

`README.md`

- Role: top-level product orientation.
- Purpose: mentions Evaluation Harness as an evidence/proof layer and links to the hub.
- Required EH-1 content:
  - short link entry only
  - no deep phase details
- Why needed: new users need discoverability, but README should not become overloaded.

`CHANGELOG.md`

- Role: release history.
- Purpose: records that Evaluation Harness documentation and audit foundation landed.
- Required EH-1 content:
  - one concise Unreleased entry if EH-1 modifies user-facing docs or command guidance
- Why needed: users need a single place to see feature/documentation changes across releases.

#### Design Rules

- `EVALUATION-HARNESS.md` is the source of truth for detailed Evaluation Harness design.
- `ROADMAP.md` is the status tracker, not the full design.
- `USER-GUIDE.md` explains day-to-day usage only.
- `TAILTRAIL-COMMANDS.md` documents available commands and marks future commands as pending.
- Existing feature docs stay intact; EH-1 should link and map, not rewrite every feature doc.
- Do not claim that `eval scenario`, `eval portfolio`, `eval tokens`, or `eval meta` are implemented until EH-2+ adds the relevant routing.
- Do not introduce deprecation warnings in EH-1. Old commands stay primary until EH-2 starts the alias migration.

#### Implementation Steps

1. Review EH-0 audit output and confirm no `needs-decision` mappings exist.
2. Expand this file with the final EH-1 documentation contract.
3. Update `ROADMAP.md` with a short EH-1 design summary and status.
4. Confirm `USER-GUIDE.md` and `TAILTRAIL-COMMANDS.md` accurately describe `eval audit` as the only implemented `eval` behavior for now.
5. Confirm README links to this hub without duplicating phase details.
6. Add or update a changelog note if user-facing documentation changed.
7. Run documentation/source validation:

```bash
python3 scripts/tailtrail.py eval audit --strict
python3 scripts/tailtrail.py registry validate --strict
python3 scripts/tailtrail.py registry drift --strict
python3 scripts/check-tailtrail.py
```

#### What EH-1 Must Not Implement

- no new scoring
- no new scenario runner
- no event JSONL schema
- no aliases beyond the already implemented `eval audit`
- no deprecation notices on old commands
- no automatic telemetry capture
- no broad report generation
- no changes to Meta-Harness, Token Harness, or Efficacy runtime behavior

#### Acceptance

- completed: detailed Evaluation Harness design lives in this file
- completed: roadmap points to this file as the implementation hub
- completed: user guide explains Evaluation Harness in user-facing terms
- completed: command catalog documents only currently available `eval` behavior as working
- completed: future `eval` commands are marked planned/pending, not available
- completed: old commands remain primary until EH-2
- completed: no user-facing deprecation yet
- completed: EH-0 audit still passes in strict mode
- completed: registry validation and drift checks still pass

Implementation note:

EH-1 is complete when the documentation contract is in place and validation passes. EH-2 must not begin until EH-1 is accepted, because EH-2 makes command behavior changes.

### Phase EH-2: Command Aliases

Status: implemented.

Purpose:

EH-2 creates the first real `eval ...` command family without changing scoring behavior. It is a surface-area consolidation phase, not an engine rewrite. The goal is that users can start thinking in one Evaluation Harness command model while existing benchmark, efficacy, guardrail, outcome, workflow, token, report, and meta commands continue to work.

The design must keep the old commands stable and make every `eval ...` route a thin delegation to an existing script or a clear pending message. If a route needs new scoring logic, new schemas, or new persistence, it belongs in EH-3/EH-4/EH-5/EH-7, not EH-2.

#### Implementation Shape

Add `scripts/evaluation-harness.py` as the single router for Evaluation Harness command aliases.

`scripts/tailtrail.py` should keep the public entry point:

```bash
python3 scripts/tailtrail.py eval ...
```

but it should delegate to:

```bash
python3 scripts/evaluation-harness.py ...
```

Why a separate router is needed:

- keeps `tailtrail.py` from becoming a large command switchboard
- gives Evaluation Harness one implementation owner
- makes alias tests easier and deterministic
- allows EH-3+ to add schema/event behavior without bloating the main CLI
- keeps future command migration under one file

#### Router Rules

- Router must use only Python standard library.
- Router must delegate to existing scripts using subprocess and preserve exit codes.
- Router must pass through unknown extra arguments unchanged.
- Router must never implement scoring directly in EH-2.
- Router must never write files unless the delegated command already writes files and already requires its normal approval flag.
- Router must print a clear pending message for scenario commands until EH-4.
- Router must keep command output mostly unchanged so existing docs/tests do not break.
- Router must avoid "implemented" wording for pending routes.
- Router must expose `audit` by delegating to `evaluation-audit.py`.

#### Canonical Routes

EH-2 should support these aliases:

| New command | Delegates to | Notes |
| --- | --- | --- |
| `eval audit ...` | `evaluation-audit.py ...` | Already implemented in EH-0; move behind router for consistency. |
| `eval portfolio run ...` | `efficacy-run.py run ...` | Existing measured efficacy runner. |
| `eval portfolio report ...` | `efficacy-run.py report ...` | Existing measured efficacy report. |
| `eval portfolio compare ...` | pending | Only add if an existing compare script exists; otherwise clear pending message. |
| `eval guardrails precision ...` | `guardrail-precision.py ...` | Existing guardrail false-positive/precision baseline. |
| `eval guardrails report ...` | pending | Do not invent report behavior in EH-2. |
| `eval outcome capture ...` | `outcome-telemetry.py capture ...` | Existing approved outcome capture. |
| `eval outcome summarize ...` | `outcome-telemetry.py summarize ...` | Existing outcome summary. |
| `eval outcome export ...` | pending unless existing command supports it | Do not add new export in EH-2. |
| `eval workflow capture ...` | `quality-loop.py capture ...` | Existing workflow-quality capture. |
| `eval workflow review ...` | `quality-loop.py review ...` | Existing workflow-quality review. |
| `eval workflow recommend ...` | pending unless existing command supports it | Keep recommendation generation out of EH-2 if not already available. |
| `eval meta quick ...` | `harness-review.py quick ...` | Existing harness quick review. |
| `eval meta review ...` | `harness-review.py review ...` | Existing harness review. |
| `eval meta readiness ...` | `harness-review.py readiness ...` | Existing readiness tier check. |
| `eval meta analyze ...` | `meta-harness-analyze.py ...` | Existing analysis script. |
| `eval meta propose ...` | `meta-harness-propose.py ...` | Existing proposal script. |
| `eval tokens route ...` | `token-harness.py route ...` | Canonical route; do not map to legacy `token route`. |
| `eval tokens reduce ...` | `token-harness-reduce.py ...` | Existing structured reducer surface. |
| `eval tokens receipt ...` | `context-receipt.py ...` | Existing receipt surface. |
| `eval tokens ledger ...` | `token-harness-ledger.py ...` | Existing append-only ledger surface. |
| `eval tokens proof ...` | `token-harness-proof.py ...` | Existing proof/report surface. |
| `eval tokens telemetry ...` | `token-telemetry.py ...` | Existing telemetry import/report surface. |
| `eval tokens savings ...` | `token-savings.py ...` | Existing savings estimate/report surface. |
| `eval tokens budget ...` | `token-budget-coach.py ...` | Existing budget coach surface. |
| `eval report value ...` | `tailtrail-report.py value ...` | Existing value report. |
| `eval artifact analyze ...` | `analyze-benchmark.py ...` | Existing static artifact analysis. |
| `eval artifact benchmark ...` | `benchmark-tailtrail.py ...` | Existing static benchmark command. |
| `eval scenario list|run|compare|report ...` | pending | Reserved for EH-4 Scenario Harness V1. |

#### Pending Route Message

Pending routes should use one consistent message:

```text
`tailtrail eval <route>` is planned for <phase>.
No evaluation was run.
Use `<current-command>` today, or run `tailtrail eval audit` to review the alias map.
```

For scenario commands:

```text
`tailtrail eval scenario <action>` is planned for EH-4 Scenario Harness V1.
No scenario was run.
Current available evidence commands: `tailtrail eval audit`, `tailtrail efficacy run --portfolio`, and `tailtrail benchmark ...`.
```

#### Compatibility Rules

- Existing commands remain supported:
  - `benchmark ...`
  - `analyze ...`
  - `efficacy ...`
  - `guardrail precision ...`
  - `outcome ...`
  - `quality-loop ...`
  - `harness ...`
  - `token-harness ...`
  - `telemetry ...`
  - `savings ...`
  - `budget ...`
  - `receipt ...`
- EH-2 must not remove, rename, or weaken those commands.
- EH-2 may add a short "also available as `eval ...`" message only if it does not break tests or JSON output.
- For JSON-producing old commands, do not add compatibility prose unless explicitly behind non-JSON mode.

#### Help Output

`python3 scripts/tailtrail.py eval` should show:

```text
Usage: tailtrail eval audit|portfolio|guardrails|outcome|workflow|meta|tokens|report|artifact|scenario [args]

Implemented in EH-2:
- eval audit
- eval portfolio run|report
- eval guardrails precision
- eval outcome capture|summarize
- eval workflow capture|review
- eval meta quick|review|readiness|analyze|propose
- eval tokens route|reduce|receipt|ledger|proof|telemetry|savings|budget
- eval report value
- eval artifact analyze|benchmark

Pending:
- eval scenario list|run|compare|report: EH-4
- routes marked pending by audit: later EH phases
```

#### Tests

Add tests in a dedicated file, for example `tests/test_evaluation_harness_router.py`.

Required tests:

- `tailtrail eval audit --format json` delegates and returns valid audit JSON.
- `tailtrail eval scenario list` returns exit code `2` with the EH-4 pending message.
- `tailtrail eval portfolio run --help` or another harmless argument delegates to the efficacy runner without invoking new scoring logic.
- `tailtrail eval guardrails precision --help` delegates to guardrail precision.
- `tailtrail eval tokens route --help` delegates to Token Harness, not legacy token autopilot.
- `tailtrail eval meta quick --help` delegates to the harness route.
- Unknown `eval` route returns exit code `2`.
- Existing old commands still dispatch.
- Help text includes `eval` and does not claim scenario support is implemented.

If existing delegated scripts do not support `--help`, use the safest deterministic argument or monkeypatch subprocess in a unit-level router test. Do not run heavy scans, model calls, benchmarks, or write-capable commands during alias tests.

#### Files To Update

`scripts/evaluation-harness.py`

- New router.
- Owns alias mapping and pending route messages.
- Must stay thin in EH-2.

`scripts/tailtrail.py`

- Delegate `eval ...` to `evaluation-harness.py`.
- Keep top-level help accurate.

`tests/test_evaluation_harness_router.py`

- Verifies alias routing and pending behavior.

`TAILTRAIL-COMMANDS.md`

- Move `eval` command family from future-only language to implemented alias language for supported routes.
- Keep scenario commands marked pending until EH-4.

`USER-GUIDE.md`

- Explain that users can now use `eval ...` as the evidence umbrella for existing evidence features.
- Keep old commands documented where useful, but list `eval` first for Evaluation Harness.

`README.md`

- Keep a short mention only.
- Do not add a large command matrix.

`tailtrail-registry.json`

- Add or update Evaluation Harness command list to include the implemented EH-2 aliases.
- Keep evidence label as command-surface/local evidence, not measured efficacy.

`scripts/check-tailtrail.py`

- Add `scripts/evaluation-harness.py` and router tests to expected inventory and compile checks.

`CHANGELOG.md`

- Add a concise Unreleased entry for EH-2 command alias support.

#### Validation Commands

Run:

```bash
python3 scripts/tailtrail.py eval audit --strict
python3 -m unittest tests.test_evaluation_audit
python3 -m unittest tests.test_evaluation_harness_router
python3 scripts/tailtrail.py registry validate --strict
python3 scripts/tailtrail.py registry drift --strict
python3 scripts/check-tailtrail.py
python3 -m unittest discover tests
```

#### Acceptance

- completed: `tailtrail eval audit` works through the router
- completed: every alias marked `alias` or `merge` in EH-0 has an EH-2 route or an explicit pending reason
- completed: old commands still work
- completed: no command route writes files unless the delegated existing command already does and its approval requirements still apply
- completed: scenario commands remain pending until EH-4
- completed: no duplicated scoring logic is introduced
- completed: registry and command docs agree
- completed: full test suite passes

### Phase EH-3: Shared Evaluation Event Schema

Status: implemented.

Purpose:

EH-3 creates the common evidence record that later Evaluation Harness phases consume. Today TailTrail has useful evidence in several shapes: efficacy reports, Token Harness ledger entries, outcome telemetry, Quality Loop events, Meta-Harness summaries, and benchmark artifacts. EH-3 does not score those systems again. It defines the shared event envelope and a safe local normalizer so future reports can consume evidence without bespoke parsing for every feature.

The main value is consistency:

- one event schema
- one local JSONL path
- one approval rule for writes
- one privacy rule for evidence storage
- one claim-boundary vocabulary
- one place future phases can read from

#### Event Output Path

Normalized Evaluation Harness events write to:

```text
.tailtrail/evaluation/events.jsonl
```

This path is local project state. It may be committed only when the team intentionally treats sanitized evaluation evidence as shared project metadata. TailTrail must not auto-upload it or push it.

#### Frozen Required Core

The schema core remains the contract defined earlier in this document:

```json
{
  "schema_version": "1",
  "event_id": "eval-20260719-abc123",
  "created_at": "2026-07-19T10:30:00Z",
  "source_feature": "token-harness",
  "task_class": "bug-fix",
  "scores": {},
  "claim_boundaries": []
}
```

Required fields:

- `schema_version`: string. Starts at `"1"`.
- `event_id`: stable unique event ID generated locally.
- `created_at`: UTC ISO-8601 timestamp.
- `source_feature`: one of the registry-backed evidence sources, such as `efficacy`, `token-harness`, `outcome-telemetry`, `quality-loop`, `meta-harness`, `benchmark-harness`, or `manual`.
- `task_class`: compact task class such as `bug-fix`, `review`, `security`, `ci-failure`, `dependency`, `feature`, `docs`, `learning-governance`, or `unknown`.
- `scores`: open object. Empty is allowed. Scores must be rubric-backed or labeled heuristic by the producer.
- `claim_boundaries`: array of strings stating what must not be overclaimed.

Optional additive fields:

- `source_event_id`
- `source_path`
- `root`
- `month`
- `scenario_id`
- `variant`
- `evidence_label`
- `metrics`
- `validation`
- `approval`
- `artifacts`
- `tags`
- `summary`
- `recommendations`
- `redactions`

Readers must ignore unknown fields.

#### Privacy Rules

- writes require `--approved`
- no raw prompts
- no raw source snippets
- no secrets
- no scanner raw logs
- no raw CI logs
- no raw vulnerability reports
- no exact token claims unless measured telemetry exists
- no user identity beyond optional local initials/team tags if explicitly approved by local policy
- no automatic upload

Allowed references:

- file paths
- command names
- scenario IDs
- short summaries
- hashes
- counts
- evidence labels
- validation status
- sanitized recommendation text

#### Normalizer Design

Extend `scripts/evaluation-harness.py` with:

```bash
python3 scripts/tailtrail.py eval normalize --source <kind> --input <path> --approved
python3 scripts/tailtrail.py eval normalize --source <kind> --input <path> --format json
python3 scripts/tailtrail.py eval normalize --source <kind> --input <path> --dry-run
```

Supported `--source` values in EH-3:

- `manual`: accepts a compact JSON event-like file already shaped by a user/tool.
- `outcome`: converts approved `outcome-telemetry.py` summary/capture JSON.
- `quality-loop`: converts Quality Loop summary/review JSON.
- `meta`: converts sanitized Meta-Harness summary JSON.
- `token-proof`: converts Token Harness proof JSON.
- `efficacy`: converts measured efficacy report JSON.
- `benchmark`: converts benchmark artifact analysis JSON.

EH-3 can start with `manual`, `outcome`, and `token-proof` if full adapters are too large. Any unsupported source must fail clearly:

```text
Unsupported evaluation source: <kind>
No event was written.
```

#### Write Modes

Default behavior:

- render normalized event to stdout
- do not write files

Write behavior:

- `--write-event --approved` appends one JSON object to `.tailtrail/evaluation/events.jsonl`
- `--write-event` without `--approved` fails unless `--dry-run` is also used
- `--dry-run` must never write, even if `--approved` is provided

#### Validation Behavior

Add:

```bash
python3 scripts/tailtrail.py eval normalize --validate .tailtrail/evaluation/events.jsonl
```

Validation should:

- parse JSONL line by line
- verify required core fields
- verify `scores` is an object
- verify `claim_boundaries` is an array
- reject raw-data-looking fields such as `raw_prompt`, `source_code`, `raw_log`, `secret`, `token`, or `password`
- warn, but not fail, on unknown additive fields

#### Files To Add Or Update

`schemas/evaluation-harness-event.schema.json`

- Role: machine-readable event contract.
- Purpose: defines required core fields and allowed broad types.
- Keep strict only for the frozen core; do not overconstrain optional fields too early.

`templates/evaluation-result.md`

- Role: human-readable normalized event/report template.
- Purpose: gives future reports one consistent Markdown shape.
- Must include evidence label and claim boundary.

`scripts/evaluation-harness.py`

- Role: router plus EH-3 normalizer.
- Purpose: add `normalize` and `validate-events` behavior while keeping EH-2 aliases thin.
- Must not score scenarios or rewrite existing feature outputs.

`tests/test_evaluation_harness_events.py`

- Role: schema and normalizer tests.
- Purpose: protects event contract, approval gating, privacy rejection, JSONL append, and validation behavior.

`tailtrail-registry.json`

- Add schema/template/script/test references to the Evaluation Harness feature entry.
- Keep `read_only` false only if write behavior is added with `--approved`; otherwise explain approval-gated writes in docs.

`scripts/check-tailtrail.py`

- Add schema, template, and tests to expected inventory.
- Add Python compile coverage if the script changed.

`USER-GUIDE.md`

- Explain normalized events in user terms.
- Clarify that users do not need this for normal development; it is for evidence/reporting.

`TAILTRAIL-COMMANDS.md`

- Add `eval normalize` and validation examples once implemented.

`CHANGELOG.md`

- Add concise EH-3 event-schema entry.

#### Example Normalized Event

```json
{
  "schema_version": "1",
  "event_id": "eval-20260719-token-proof-001",
  "created_at": "2026-07-19T10:30:00Z",
  "source_feature": "token-harness",
  "task_class": "review",
  "evidence_label": "measured",
  "scores": {
    "token_evidence_present": 1,
    "claim_boundary_respected": 1
  },
  "metrics": {
    "tokens_before": 12000,
    "tokens_after": 4800,
    "reduction_percent": 60.0
  },
  "claim_boundaries": [
    "Exact token savings require measured telemetry.",
    "This event stores counts and summaries only, not raw prompts or source."
  ],
  "summary": "Token proof imported from approved local Token Harness report."
}
```

#### What EH-3 Must Not Implement

- no scenario scoring
- no portfolio scoring
- no live model/API calls
- no automatic event capture after every command
- no background observer
- no upload or cross-repo aggregation
- no dashboard
- no exact token-savings claims unless the source event contains measured telemetry
- no raw prompt/source/log storage
- no automatic Meta-Harness proposals

Acceptance:

- completed: schema file exists and validates the frozen required core
- completed: template exists and includes evidence label plus claim boundary
- completed: normalizer can emit at least one valid event to stdout
- completed: writes require `--approved`
- completed: `--dry-run` never writes
- completed: event validation rejects missing required fields
- completed: privacy guard rejects raw prompt/source/log/secret-like fields
- completed: existing EH-2 aliases still work
- completed: reports are not required to consume events until EH-5/EH-7/EH-6
- completed: full validation passes

### Phase EH-4: Scenario Harness V1

Status: implemented.

Purpose:

EH-4 turns Evaluation Harness from a command umbrella into a repeatable proof system. It should score committed, saved artifacts for known task scenarios so TailTrail can show evidence such as "this workflow satisfies requirements, preserves safeguards, avoids unnecessary dependencies, and includes validation" without running a live AI agent.

The key rule: EH-4 is deterministic and local. It reads scenario fixtures and artifact files already committed in the repo. It does not call Codex, Claude, OpenAI APIs, scanners, package managers, or CI. Live-agent benchmarking remains deferred to EH-9.

#### User-Facing Commands

Implement:

```bash
python3 scripts/tailtrail.py eval scenario list
python3 scripts/tailtrail.py eval scenario run --scenario validation-bug
python3 scripts/tailtrail.py eval scenario compare --scenario validation-bug
python3 scripts/tailtrail.py eval scenario report --scenario validation-bug
python3 scripts/tailtrail.py eval scenario run --scenario validation-bug --format json
python3 scripts/tailtrail.py eval scenario report --scenario validation-bug --write-result --approved
```

Command behavior:

- `list`: shows available scenarios with task class, evidence label, variants, and fixture path.
- `run`: scores one scenario and prints Markdown or JSON.
- `compare`: compares variants inside one scenario and highlights winner/delta.
- `report`: renders a human-readable report for one scenario.
- `--write-result --approved`: writes reports under `benchmarks/evaluation/results/` or `reports/evaluation-harness/`.
- `--write-result` without `--approved`: fails.
- `--format json`: prints stable machine-readable output.

#### Scenario Layout

Add:

```text
benchmarks/evaluation/
  README.md
  scenarios/
    validation-bug/
      scenario.json
      baseline-artifact.md
      tailtrail-artifact.md
      expected.json
    dependency-decision/
      scenario.json
      baseline-artifact.md
      tailtrail-artifact.md
      expected.json
    review-only/
      scenario.json
      baseline-artifact.md
      tailtrail-artifact.md
      expected.json
    ci-failure/
      scenario.json
      baseline-artifact.md
      tailtrail-artifact.md
      expected.json
    security-triage/
      scenario.json
      baseline-artifact.md
      tailtrail-artifact.md
      expected.json
  results/
    .gitkeep
```

`scenario.json` should describe the scenario and scoring rubric. Example:

```json
{
  "schema_version": "1",
  "scenario_id": "validation-bug",
  "title": "Focused Bug Fix With Validation",
  "task_class": "bug-fix",
  "evidence_label": "local-evidence",
  "claim_boundaries": [
    "Scores are deterministic fixture evidence, not live model performance.",
    "Exact token savings require measured telemetry."
  ],
  "variants": [
    {
      "id": "baseline",
      "artifact": "baseline-artifact.md"
    },
    {
      "id": "tailtrail",
      "artifact": "tailtrail-artifact.md"
    }
  ],
  "dimensions": {
    "requirement": {
      "weight": 2,
      "must_include": ["requirement satisfied", "user request"]
    },
    "validation": {
      "weight": 2,
      "must_include": ["test", "validation"]
    },
    "safeguards": {
      "weight": 1,
      "must_not_include": ["removed validation", "disabled auth"]
    },
    "dependency": {
      "weight": 1,
      "must_not_include": ["new dependency"]
    },
    "diff_focus": {
      "weight": 1,
      "must_include": ["smallest maintainable change"]
    },
    "review": {
      "weight": 1,
      "must_include": ["review"]
    },
    "approval": {
      "weight": 1,
      "must_include": ["approval"]
    },
    "token": {
      "weight": 1,
      "must_include_any": ["context receipt", "token evidence", "measured telemetry"]
    }
  }
}
```

`expected.json` should hold acceptance thresholds:

```json
{
  "min_tailtrail_total": 0.75,
  "min_delta": 0.15,
  "required_winner": "tailtrail"
}
```

#### Deterministic Scoring

Each dimension should produce:

- `score`: `0`, `0.5`, or `1`
- `weight`
- `weighted_score`
- `evidence`: short matched evidence strings
- `misses`: short missing evidence strings
- `label`: `heuristic` or `local-evidence`

Score rules:

- `1`: all required positive signals found and all forbidden signals absent.
- `0.5`: partial positive signals found and no severe forbidden signals.
- `0`: required signals missing or forbidden severe signal present.

Total score:

```text
sum(weighted_score) / sum(weights)
```

Do not use fuzzy model judgment. Use explicit text signals from `scenario.json` so scoring is inspectable and stable.

#### Report Shape

Output should include:

- scenario ID
- task class
- variants
- evidence label
- claim boundaries
- score table
- per-dimension findings
- winner/delta
- recommendations
- reproduction commands
- optional normalized EH-3 event representation

Markdown example:

```text
# TailTrail Evaluation Scenario Report

- Scenario: `validation-bug`
- Task class: `bug-fix`
- Variants: `baseline`, `tailtrail`
- Evidence label: `local-evidence`
- Claim boundary: deterministic fixture evidence, not live model performance

## Score Summary

| Variant | Requirement | Validation | Safeguards | Dependency | Diff Focus | Review | Approval | Token | Total |
|---|---:|---:|---:|---:|---:|---:|---:|---:|---:|
| baseline | 0 | 0.5 | 1 | 1 | 0.5 | 0 | 0 | 0 | 0.35 |
| tailtrail | 1 | 1 | 1 | 1 | 1 | 1 | 1 | 0.5 | 0.95 |

## Findings

- TailTrail artifact satisfied the requirement and included focused validation.
- Baseline artifact lacked review and approval evidence.
- Token score is local-evidence only; no measured telemetry was provided.
```

#### Initial Scenario Set

Start with five scenarios:

- `validation-bug`: verifies requirement fulfillment and focused validation.
- `dependency-decision`: verifies dependency discipline and native/platform-first reasoning.
- `review-only`: verifies review findings include severity, file/function/line, and actionable explanation.
- `ci-failure`: verifies CI/log triage, reproduction command, and validation handoff.
- `security-triage`: verifies safeguard preservation and no unsafe bypass.

These are intentionally small fixtures. They prove the harness works before expanding into a larger portfolio.

#### Files To Add Or Update

`scripts/evaluation-harness.py`

- Add `scenario list|run|compare|report`.
- Keep existing EH-2 aliases and EH-3 normalizer intact.
- Implement deterministic fixture scoring only.

`benchmarks/evaluation/README.md`

- Explain scenario format, scoring dimensions, report meaning, and claim boundaries.

`benchmarks/evaluation/scenarios/*`

- Add initial scenario fixtures.
- Each scenario owns `scenario.json`, artifacts, and `expected.json`.

`benchmarks/evaluation/results/.gitkeep`

- Placeholder for approved generated reports.

`tests/test_evaluation_harness_scenarios.py`

- Verify list/run/compare/report behavior.
- Verify deterministic JSON output.
- Verify `--write-result` requires `--approved`.
- Verify expected thresholds pass.
- Verify scenario scoring does not run model/API/scanner commands.

`tailtrail-registry.json`

- Add scenario commands, scenario fixtures, and scenario tests to Evaluation Harness feature entry.

`scripts/check-tailtrail.py`

- Add new fixtures, result placeholder, and tests to expected inventory.

`TAILTRAIL-COMMANDS.md`

- Move `eval scenario list|run|compare|report` from pending to implemented.
- Add examples.

`USER-GUIDE.md`

- Explain when a user should run scenarios: demos, regression proof, release evidence, and product confidence.

`CHANGELOG.md`

- Add concise EH-4 Scenario Harness V1 entry.

#### What EH-4 Must Not Implement

- no live AI agent execution
- no model/API calls
- no real repo modification
- no CI/scanner/package-manager execution
- no vector search or semantic engine
- no exact token claims without measured telemetry
- no scenario expansion beyond committed fixtures unless added intentionally
- no automatic report writes without `--approved`
- no hidden telemetry

Acceptance:

- completed: `eval scenario list` shows all committed scenarios
- completed: `eval scenario run --scenario <id>` scores deterministically
- completed: `eval scenario compare --scenario <id>` shows variant delta and winner
- completed: `eval scenario report --scenario <id>` renders readable Markdown
- completed: JSON output is stable for tests
- completed: output includes per-dimension scores and evidence labels
- completed: output includes claim boundaries
- completed: writes require `--approved`
- completed: EH-2 aliases and EH-3 normalize/validate still work
- completed: full validation passes

### Phase EH-5: Portfolio Consolidation

Implement:

- migrate `benchmarks/efficacy/` into the Evaluation Harness portfolio view
- keep existing folder for compatibility until docs move
- portfolio report groups scenarios by task class
- portfolio report shows:
  - scenario count
  - dimension averages
  - pass/fail counts
  - evidence labels
  - token evidence type
  - public claim readiness

Acceptance:

- current `efficacy run --portfolio --strict` has an equivalent `eval portfolio run --strict`
- old command output remains compatible

### Phase EH-6: Meta-Harness Integration

Implement:

- Meta-Harness reads normalized evaluation events
- readiness tiers include scenario/portfolio strength
- proposals reference evaluation dimensions and registry feature IDs
- proposal confidence is capped by evidence labels

Rules:

- Meta-Harness can propose improvements only
- no automatic TailTrail edits
- no central aggregation without sanitized shared summary approval

Acceptance:

- a weak repeated scenario can produce a reviewable proposal
- unknown registry feature IDs remain blocking

### Phase EH-7: Token Evidence Integration

Implement:

- Token Harness proof emits normalized evaluation events
- scenario reports include token evidence section
- measured telemetry can upgrade `estimated` or `local-evidence` to `measured`
- holdout measurement can upgrade to `benchmark-measured`

Acceptance:

- report refuses exact savings without measured telemetry
- report distinguishes estimated, local-evidence, measured, benchmark-measured

### Phase EH-8: Build Week Demo As Scenario

Status: implemented.

Purpose:

EH-8 turns the Build Week demo into a first-class Evaluation Harness scenario without making the demo project the harness itself. The demo remains human-readable and presentation-friendly, while Evaluation Harness gets a repeatable fixture that can prove the same story through `eval scenario ...` commands.

This phase is intentionally narrow. It should not introduce live-agent execution, new scoring engines, CI orchestration, screenshots, or benchmark dashboards. It packages the existing demo narrative into the EH-4 deterministic scenario model so judges, reviewers, and enterprise stakeholders can see the same capability in two forms:

- a live demo workspace for humans
- a committed scenario record for repeatable evidence

#### User-Facing Commands

Add one scenario to the existing EH-4 command family:

```bash
python3 scripts/tailtrail.py eval scenario list
python3 scripts/tailtrail.py eval scenario run --scenario buildweek-validation
python3 scripts/tailtrail.py eval scenario compare --scenario buildweek-validation
python3 scripts/tailtrail.py eval scenario report --scenario buildweek-validation
python3 scripts/tailtrail.py eval scenario report --scenario buildweek-validation --format json
python3 scripts/tailtrail.py eval scenario report --scenario buildweek-validation --write-result --approved
```

Expected user value:

- Demo presenter can run one command to show repeatable proof.
- Reviewers can inspect the fixture without running the live demo.
- Enterprise teams can adapt the scenario pattern for their own internal pilot demos.
- TailTrail can avoid broad claims by showing scenario-specific evidence and claim boundaries.

#### Files To Add

- convert `buildweek-demo-project` into an Evaluation Harness demo scenario record
- create `benchmarks/evaluation/scenarios/buildweek-validation/`
- reference demo commands and expected failing/passing behavior

Concrete file layout:

```text
benchmarks/evaluation/scenarios/buildweek-validation/
  scenario.json
  baseline-artifact.md
  tailtrail-artifact.md
  expected.json
  README.md
```

Optional, only if useful for presentation notes:

```text
benchmarks/evaluation/scenarios/buildweek-validation/
  demo-runbook-reference.md
```

Do not move or delete:

```text
buildweek-demo-project/
```

The demo project remains the live demo workspace. The scenario fixture references it as the source story, but the deterministic scoring must read only the committed scenario files under `benchmarks/evaluation/scenarios/buildweek-validation/`.

#### Scenario Definition

`scenario.json` should follow the EH-4 schema and define the Build Week proof dimensions:

```json
{
  "schema_version": "1",
  "scenario_id": "buildweek-validation",
  "title": "Build Week Demo Validation",
  "task_class": "demo",
  "evidence_label": "local-evidence",
  "claim_boundaries": [
    "This scenario scores committed demo artifacts only.",
    "It does not prove live model performance, exact token savings, or real production defect reduction.",
    "Exact token savings require measured provider telemetry."
  ],
  "variants": [
    {
      "id": "baseline",
      "artifact": "baseline-artifact.md"
    },
    {
      "id": "tailtrail",
      "artifact": "tailtrail-artifact.md"
    }
  ],
  "dimensions": {
    "navigator": {
      "weight": 2,
      "must_include": ["Navigator plan", "approval before implementation"]
    },
    "requirement": {
      "weight": 2,
      "must_include": ["requirement fulfilled", "user goal"]
    },
    "validation": {
      "weight": 2,
      "must_include_any": ["focused test", "validation result", "quality check"]
    },
    "review": {
      "weight": 1,
      "must_include": ["review findings", "file", "line"]
    },
    "token": {
      "weight": 1,
      "must_include_any": ["context budget", "context receipt", "token evidence"]
    },
    "graph": {
      "weight": 1,
      "must_include_any": ["Code Graph", "read order", "impacted files"]
    },
    "safeguards": {
      "weight": 2,
      "must_not_include": ["bypass validation", "disable auth", "ignore scanner"]
    },
    "claim_boundary": {
      "weight": 1,
      "must_include": ["claim boundary", "local-evidence"]
    }
  }
}
```

Scoring remains the EH-4 deterministic text-signal scorer. Do not add a separate Build Week scoring engine.

#### Artifact Content

`baseline-artifact.md` should represent a normal assistant/demo answer without TailTrail structure. It should intentionally miss some TailTrail-specific evidence such as approval gate, context budget, graph-first read order, or detailed review fields.

`tailtrail-artifact.md` should represent the intended TailTrail-assisted demo path:

- Navigator selected the workflow.
- User approval was requested before implementation.
- Code Graph or read-order guidance was used when useful.
- Implementation was checked against the user goal.
- Review included file/function/line detail.
- Validation result was stated honestly.
- Token/evidence claim was labeled correctly.
- No unsafe bypass or overclaim appeared.

`expected.json` should set thresholds:

```json
{
  "min_tailtrail_total": 0.8,
  "min_delta": 0.2,
  "required_winner": "tailtrail"
}
```

`README.md` should explain:

- what the scenario proves
- what it does not prove
- how it relates to `buildweek-demo-project/`
- which command to run during a pitch
- how to adapt the pattern for an internal enterprise demo

#### Implementation Steps

1. Review `buildweek-demo-project/DEMO-PROMPTS.md`, `DEMO-RUNBOOK.md`, and `FEATURE-COVERAGE.md`.
2. Choose one demo path that is stable, short, and covers the strongest TailTrail story.
3. Create `benchmarks/evaluation/scenarios/buildweek-validation/`.
4. Write `scenario.json` using only EH-4-supported rubric fields.
5. Write `baseline-artifact.md` and `tailtrail-artifact.md` as sanitized saved artifacts.
6. Write `expected.json` with conservative thresholds.
7. Add a scenario-local `README.md`.
8. Update `benchmarks/evaluation/README.md` to list `buildweek-validation`.
9. Update `USER-GUIDE.md` and `TAILTRAIL-COMMANDS.md` with the demo scenario command.
10. Update `tailtrail-registry.json` only if new docs/tests/scripts are added beyond the existing Evaluation Harness entry.
11. Add tests that assert the scenario appears in `eval scenario list`, passes thresholds, and does not write results without `--approved`.
12. Run full validation.

#### Tests

Add or extend `tests/test_evaluation_harness_scenarios.py`:

- `buildweek-validation` appears in `eval scenario list`.
- `eval scenario report --scenario buildweek-validation --format json` returns `type = evaluation-scenario-result`.
- `winner` is `tailtrail`.
- `threshold_passed` is `true`.
- output includes claim boundaries.
- `--write-result` without `--approved` fails.
- no live commands, model calls, scanners, package managers, or CI commands are invoked.

#### Navigator And MCP Behavior

Navigator should already route evidence/demo/proof prompts to Evaluation Harness. EH-8 should verify these prompts select the Build Week scenario when the user mentions Build Week:

```text
show Build Week demo evidence
create a Build Week proof report
run the TailTrail demo scenario
```

Expected Navigator command:

```bash
python3 scripts/tailtrail.py eval scenario report --scenario buildweek-validation
```

MCP should not need new write-capable tools. Existing read-only tools are enough:

- `eval_scenario_list`
- `eval_scenario_report` with `scenario = buildweek-validation`

#### What EH-8 Must Not Implement

- no live demo execution
- no Codex/Claude/OpenAI/Gemini API calls
- no screenshots or UI automation
- no scanner/test/build execution
- no automatic report writes
- no raw prompt, raw source, or raw log capture
- no exact token-savings claim without measured telemetry
- no new command family outside `eval scenario ...`
- no changes to scenario scoring logic unless EH-4 tests prove a bug

Acceptance:

- completed: this section defines files, commands, scoring, docs, tests, Navigator/MCP behavior, and non-goals
- completed: `eval scenario report --scenario buildweek-validation` explains what the live demo proves
- completed: scenario appears in `eval scenario list`
- completed: TailTrail variant wins and passes `expected.json`
- completed: report includes claim boundaries
- completed: demo project remains human-readable and independent
- completed: focused scenario validation passes

### Phase EH-9: Optional Live-Agent Mode

Status: deferred and split out. EH-9 is not part of the consolidation track. Track it in a separate RFC/design doc because it is a different risk class (cost, sandboxing, secrets, supply chain). The sketch below is retained only as forward reference.

Implement only after deterministic harness is stable.

Command sketch:

```bash
python3 scripts/tailtrail.py eval scenario run-live --scenario validation-bug --backend codex --approved
python3 scripts/tailtrail.py eval scenario run-live --scenario validation-bug --backend claude --approved
```

Requirements:

- explicit approval
- isolated temporary workspace
- timeout
- no secrets
- no automatic push
- no automatic package install
- clear cost warning
- saved sanitized artifacts
- backend-specific adapter instructions
- event stream capture only when approved

Acceptance:

- live-agent mode can be skipped entirely in enterprise environments
- deterministic scenario mode remains the default

## Migration Plan

### No Breaking Changes

Existing commands keep working:

- `benchmark`
- `efficacy`
- `guardrail precision`
- `outcome`
- `quality-loop`
- `harness`
- `token-harness`
- `telemetry`
- `savings`
- `budget`
- `receipt`
- `report`

### Documentation Migration

Phase 1:

- docs say "Evaluation Harness umbrella"
- old commands remain listed

Phase 2:

- docs list `eval ...` first
- old commands marked "compatibility aliases"

Phase 3:

- command help groups old commands under compatibility
- no removal date until usage proves stable

### Registry Migration

Add feature ID:

```text
evaluation-harness
```

Registry entry should include:

- commands:
  - `tailtrail eval scenario`
  - `tailtrail eval portfolio`
  - `tailtrail eval guardrails`
  - `tailtrail eval outcome`
  - `tailtrail eval workflow`
  - `tailtrail eval meta`
  - `tailtrail eval tokens`
  - `tailtrail eval report`
- docs:
  - `EVALUATION-HARNESS.md`
  - `TAILTRAIL-COMMANDS.md`
  - `USER-GUIDE.md`
  - `ROADMAP.md`
- scripts:
  - `scripts/evaluation-harness.py`
- tests:
  - `tests/test_evaluation_harness.py`
- evidence label:
  - `local-evidence`
- depends_on:
  - `registry`
  - `command-surface`
  - `token-harness`
  - `meta-harness`

Do not make all existing features depend on Evaluation Harness immediately. First let Evaluation Harness consume them.

## Validation Plan

For every phase:

```bash
python3 scripts/check-tailtrail.py
python3 scripts/tailtrail.py registry validate --strict
python3 scripts/tailtrail.py registry drift --strict
python3 -m unittest discover tests
```

For EH-2:

```bash
python3 scripts/tailtrail.py eval portfolio run --strict
python3 scripts/tailtrail.py eval guardrails precision --strict
python3 scripts/tailtrail.py eval meta quick --root .
```

For EH-4:

```bash
python3 scripts/tailtrail.py eval scenario list
python3 scripts/tailtrail.py eval scenario run --scenario validation-bug --format json
python3 scripts/tailtrail.py eval scenario report --scenario validation-bug
```

For EH-7:

```bash
python3 scripts/tailtrail.py eval tokens proof report
python3 scripts/tailtrail.py eval tokens telemetry import-openai --source usage.jsonl
```

## Risk Controls

| Risk | Control |
|---|---|
| New umbrella duplicates old features | EH router delegates first; shared schema comes later. |
| Reports become too broad | Scenario and portfolio reports must be scoped by task class and dimension. |
| Users get confused by command rename | Keep old commands and document `eval` as umbrella first. |
| Token claims become inflated | Token evidence labels stay mandatory. |
| Meta-Harness looks self-modifying | Proposal-only; no automatic source edits. |
| Live-agent mode becomes costly or unsafe | Defer until EH-9 and require explicit approval. |
| Private data leaks into eval events | Never store raw prompts/source/logs; write only compact refs and summaries. |
| Registry drift increases | Add registry entry and drift checks during EH-2. |

## Recommended Implementation Order

Committed slice (build first):

1. EH-0: usage and overlap audit.
2. EH-1: documentation and roadmap only.
3. EH-2: command aliases through a thin router.
4. EH-3: shared schema and normalization (frozen core, additive fields).
5. EH-4: deterministic scenario harness (rubric-backed scores).
6. EH-8: Build Week demo as scenario.
   - Pulled forward from EH-7: Token Harness proof emitting one normalized event so scenario reports show token evidence.

Conditional slice (evidence-gated, start only after EH-4 shows real use):

7. EH-5: portfolio consolidation.
8. EH-7: token evidence integration (full).
9. EH-6: Meta-Harness integration.

Deferred and split out:

- EH-9: optional live-agent mode moves to its own RFC/design doc.

EH-6 and EH-7 can swap only if implementation evidence shows Meta-Harness integration is blocked without deeper token evidence. Keep this ordering synchronized with the `ROADMAP.md` consolidation track.

## Success Criteria

TailTrail Evaluation Harness is successful when:

- users see one evidence umbrella instead of many disconnected reporting tools
- old commands still work
- `eval ...` provides a coherent command family
- scenario reports compare baseline vs TailTrail variants
- portfolio reports summarize outcome quality across task classes
- Meta-Harness proposals use Evaluation Harness evidence
- token claims remain evidence-labeled
- Build Week and enterprise demos can show one clean proof story
