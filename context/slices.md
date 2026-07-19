# TailTrail Slices

Slices are named context bundles. They keep TailTrail useful without loading every guidance file on every run.

## `core`

Use for normal implementation, bug fixing, refactoring, and dependency choices.

Load:

- `AGENTS.md`
- `skills/tailtrail/SKILL.md`
- relevant `GUARDRAILS.md` sections for non-trivial or risky work
- `context/guardrail-layers.md` implementation layer for non-trivial or risky work
- `context/guardrail-layers.md` code consistency layer when names, structure, validation style, error handling, tests, or formatting may drift
- `tailtrail-policy.md` when present in the target project

Avoid by default:

- `DESIGN.md`
- `ROADMAP.md`
- all examples unless one directly matches the task

## `review`

Use for reviewing diffs, reducing unnecessary code, or checking that simplification preserved safeguards.

Load:

- `skills/tailtrail-review/SKILL.md`
- `GUARDRAILS.md` evidence, validation truth, exactness, safeguard, and review sections
- `context/guardrail-layers.md` review layer
- `context/guardrail-layers.md` code consistency layer
- `tailtrail-policy.md` when present and local review, validation, ownership, or restricted-folder rules matter
- `DEPENDENCY-GATE.md` when dependencies changed
- `context/change-impact.md`
- exact changed files or diff

Avoid by default:

- broad repo scans
- unrelated examples
- future-scope roadmap notes

## `router`

Use when the task is mainly about reducing token usage or deciding which context-saving technique applies.

Load:

- `context/TailTrail.map.md`
- `context/token-router.md`
- `context/guardrail-layers.md` token saving layer when exactness risk matters
- `GUARDRAILS.md` exactness and token-saving sections when routing risky content

Optional:

- `templates/router-decision.md` for large or repeated work

## `project-map`

Use when the relevant code area is unclear.

Load:

- `context/project-map.md`
- `context/change-impact.md`
- exact source files found from targeted search

Avoid by default:

- whole directories
- generated files
- dependency trees

## `output`

Use when terminal, test, build, lint, browser, MCP, or API output is too large.

Load:

- `templates/tool-summary.md`
- exact first failure or exact field needed for the task
- `GUARDRAILS.md` validation truth and exactness sections for risky failures
- `context/guardrail-layers.md` QA / validation layer
- `context/guardrail-layers.md` CI / Sonar layer for pipeline, scan, or Sonar work
- `tailtrail-policy.md` when present and local CI, validation, or release expectations matter

Avoid by default:

- raw full logs unless the log itself is being debugged

## `cache`

Use when stable project facts or repeated tool results are being rediscovered.

Load:

- `context/cache-index.md`
- `context/code-graph-mapper.md` for heavy Sonar, vulnerability, QA, dependency, review, or handoff work
- `templates/context-brief.md`

Avoid by default:

- stale summaries whose source files, commands, versions, or policies changed

## `code-graph`

Use when a heavy task needs a reusable source-read map instead of repeated broad code discovery.

Load:

- `context/code-graph-mapper.md`
- `tailtrail-meta/code-graph-cache.json` metadata only when present and relevant
- exact changed files, scanner-reported files, or target files

Avoid by default:

- raw full source folders
- stale graph caches
- treating graph metadata as validation proof

## `compression`

Use only for bulky, stable, non-exact references.

Load:

- `context/compression-policy.md`
- `context/prune-rules.md`
- `GUARDRAILS.md` exactness and token-saving sections
- `context/guardrail-layers.md` token saving layer

Never compress:

- code
- diffs
- configs
- commands
- security, validation, authorization, or approval rules

## `aidlc`

Use for portable AI Development Lifecycle work, especially broad, risky, ambiguous, multi-team, regulated, or long-running tasks.

Load:

- `AIDLC.md`
- `GUARDRAILS.md` evidence, uncertainty, approval, validation truth, and exactness sections
- `context/guardrail-layers.md` AIDLC layer
- `context/guardrail-layers.md` handoff or release layer when transfer, approval, or release readiness is in scope
- `tailtrail-policy.md` when present in the target project
- `aidlc/stages/README.md`
- the active stage playbook from `aidlc/stages/`
- `templates/aidlc-state.md` when starting new lifecycle state
- `templates/aidlc-audit.md` when recording durable decisions
- the active AIDLC template needed for the current phase or stage
- `aidlc-docs/aidlc-state.md` in a target project when resuming work

Avoid by default:

- every lifecycle artifact
- every template
- old audit details unless needed for a decision

Common active templates:

- `templates/requirements.md` for requirements capture
- `templates/workflow-plan.md` for planning
- `templates/implementation-plan.md` for approved construction work
- `templates/change-brief.md` for pre-change planning
- `templates/question-file.md` for non-trivial ambiguity
- `templates/stage-gate.md` for approvals
- `templates/diff-handoff.md` for implementation handoff
- `templates/validation-handoff.md` for test and build evidence
- `templates/operations-notes.md` for production handoff

Also load:

- `DEPENDENCY-GATE.md` before adding or changing dependencies
- `tailtrail-policy.md` when present and local dependency, validation, ownership, or security rules matter

## `examples`

Use only when the user asks for examples or the agent needs one calibration case.

Load one:

- `examples/native-date-field.md`
- `examples/stdlib-csv.md`
- `examples/shared-bug-fix.md`
- `examples/preserve-guard.md`

Avoid loading the full examples folder by default.
