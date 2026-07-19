# TailTrail Learning Governance

TailTrail learning is local, advisory, and evidence-weighted. It helps future work start with better repo context, but it must not become a silent source of bad patterns.

## Purpose

Use learning governance to decide whether a prior event is safe to reuse, needs more evidence, should stay as weak history, or should be suppressed from future retrieval.

Learning governance protects against:

- user-biased acceptance of weak fixes
- stale code, policy, scanner, or validation assumptions
- repeated rejected patterns
- missing validation evidence
- dependency or security shortcuts
- noisy learning files that increase token cost

## Core Rule

User acceptance is useful evidence, not proof.

Current source, tests, CI, scanner output, local policy, guardrails, and explicit user instructions always override old learnings.

## Confidence Bands

| Score | Meaning | Retrieval behavior |
|---:|---|---|
| 0-39 | do not use | Do not retrieve during normal work. |
| 40-59 | weak historical note | Show only for debugging, refresh, or explicit history review. |
| 60-79 | candidate learning | Suggest with caution and require current-source inspection. |
| 80-100 | trusted reusable repo pattern | Eligible for curated reuse if it is normal sensitivity and not stale. |

Low-confidence accepted work can be recorded as an event when the user explicitly wants history, but it must not be promoted into `.tailtrail/learnings.md` unless stronger evidence raises the score.

## When To Capture

Capture a learning only when the result is likely reusable:

- a repeated bug pattern was fixed
- a CI, Sonar, lint, or vulnerability issue had a reusable resolution
- a validation command was confirmed
- a dependency decision was approved through the dependency gate
- a reviewer or owner gave useful feedback
- a project convention was discovered and confirmed

Prefer compact summaries over raw history.

## When Not To Capture

Do not capture:

- secrets, credentials, tokens, PII, PHI, customer data, or raw logs
- full user prompts, full assistant responses, or source snippets by default
- one-off tiny edits with no future value
- speculative ideas that were not validated
- fixes that removed validation, authorization, escaping, accessibility, data-loss prevention, or policy safeguards
- dependency changes that skipped required approval
- rejected solutions unless the rejection reason is useful avoid-history

## Review Command

Run learning review before broad reuse, monthly hygiene checks, or after TailTrail gives weak suggestions:

```bash
python3 scripts/tailtrail.py learn review --root .
python3 scripts/tailtrail.py learn review --root . --write-result
python3 scripts/tailtrail.py learn review --root . --format json
```

The review command reads compact local learning metadata and reports:

- weak or do-not-use event counts
- rejected event counts
- missing validation evidence
- guardrail weakening signals
- low-confidence user overrides
- duplicate learning candidates
- conflicting learning candidates
- stale or blocking refresh actions

It does not edit learning files.

## Refresh Actions

Use refresh actions only after review:

```bash
python3 scripts/tailtrail.py learn refresh recommend --root .
python3 scripts/tailtrail.py learn refresh stale --root . --days 90
python3 scripts/tailtrail.py learn refresh apply --root . --learning-id 20260712-abc12345 --action suppress --reason "Rejected by reviewer" --approved
```

Approved blocking actions such as `mark-stale`, `suppress`, `archive`, and `delete` prevent automatic retrieval.

## Promotion Rules

Promote to curated learnings only when:

- the event is reusable
- confidence is at least 80 or meets the risk-specific threshold
- validation passed or objective evidence is strong
- sensitivity is normal
- the learning has a stale condition
- no refresh action suppresses it
- current source and policy do not contradict it

Promotion should be explicit:

```bash
python3 scripts/tailtrail.py learn promote --root . --event-id 20260712-abc12345
```

## Token Discipline

Normal work should read `.tailtrail/learning-index.md` first and retrieve at most three matching learnings. Do not load `.tailtrail/learning-events.jsonl` into normal implementation context unless the user explicitly asks for learning history or debugging.

If learning files grow noisy, run review and refresh instead of loading more context.

## Enterprise Use

Use Enterprise Reporting for trend review:

```bash
python3 scripts/tailtrail.py report --month 2026-07
```

The report includes learning hygiene signals. Use them to improve TailTrail rules, Navigator behavior, local policy, or team guidance. Do not use them for hidden user scoring or surveillance.
