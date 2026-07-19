# TailTrail Navigator

TailTrail Navigator is the single orchestration layer for choosing TailTrail features.

It prevents every feature from auto-triggering independently. Navigator should inspect the user goal, changed files, risk signals, and existing TailTrail state, then recommend the smallest useful workflow.

## Inputs

- user goal or task description
- optional changed files
- optional repo root
- existing `aidlc-docs/`
- existing `.tailtrail/learnings.md`
- existing `.tailtrail/learning-index.md`
- existing `.tailtrail/graph-learning-index.json`
- existing `.tailtrail/learning-refresh-actions.json`
- installed pack manifest
- local policy file when present

## Decision Rules

- Tiny typo, comment, or docs-only work: use lean TailTrail, skip AIDLC, review graph, handoff, and learning capture.
- Bug fix, refactor, implementation, review, validation, auth, CI/Sonar, dependency, or shared-helper work: recommend Code Review Graph Lite when changed files are known or can be supplied.
- Meaningful code-change work: check Code Graph Mapper cache status before broad source reads. If missing, recommend graph map. If stale or invalid, recommend refresh or recreate. If fresh, recommend using cached read order before exact source inspection. Skip this for tiny typo or docs-only work.
- Broad, risky, regulated, production, migration, release, or multi-file work: recommend AIDLC standard unless the user skips it.
- Dependency/package/library/upgrade work: recommend Dependency Gate.
- CI, Sonar, pipeline, quality gate, test, or validation work: recommend QA / CI-Sonar lens and exact validation evidence.
- PR, release, approval, transfer, or handoff work: recommend Handoff.
- Existing project learnings: suggest at most relevant curated notes, never raw history by default.
- Matching graph-aware learnings: show them in the plan with `use learnings`, `ignore learnings`, and `edit plan` choices.
- Missing or unusable learning context: explain the skip reason as `no index`, `tiny task`, `stale graph`, or `no matching tags/files/rules`.
- Stale, weak, contradictory, or user-reported bad learning signals: suggest Learning Refresh, but do not run it.
- Meaningful completed work: trigger a post-task learning capture section in the plan with a suggested `hooks/learning-capture-hook.py` command, but do not run it automatically or write learning files without user approval.

## Approval Rule

Navigator returns a plan first. It does not edit files.

The plan must tell the user:

- selected features
- skipped features
- likely impacted files
- load and avoid lists
- suggested commands
- implementation plan
- validation expectations
- learning approval choices when learnings are surfaced
- learning skip reasons when learning context is skipped
- post-task learning capture trigger when useful
- approval instructions

The user can edit the plan before implementation.

## Overrides

Respect explicit user intent:

- `use AIDLC only`
- `skip review graph`
- `skip AIDLC`
- `without AIDLC`
- `review only`
- `skip handoff`

## Boundaries

- no background service
- no hidden implementation
- no autonomous edits
- no model calls
- no raw prompt logging
- no automatic learning capture
- no automatic learning refresh actions
- learnings are advisory only and never override current source, CI, scanner, policy, guardrails, or explicit user instructions
- no feature auto-triggering outside Navigator
