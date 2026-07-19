# TailTrail Learning Agent V2

Use this context when a task discovers a reusable repo pattern, fixes a repeated issue, or needs a small set of prior learnings.

## Purpose

Learning Agent V2 turns repeated repo work into compact local knowledge:

- feature implementation patterns
- bug-fix approaches
- CI/CD fixes
- Sonar/static-analysis fixes
- validation commands
- dependency decisions
- explicit user acceptance or rejection signals

It is not a model trainer, background observer, user profiler, or raw chat history store.

## Core Rule

TailTrail can learn from user acceptance, but it should trust evidence more than acceptance.

User acceptance is one signal. It is not proof that a solution is correct.

## Confidence Bands

```text
0-39: do not use
40-59: weak historical note only
60-79: candidate learning, suggest with caution
80-100: trusted reusable repo pattern
```

Low-confidence accepted work can be recorded as an event only when useful. It must not be promoted into curated learnings unless validation, review, repeated success, or stronger evidence raises the score.

## Token-Safe Retrieval

Load order:

1. `.tailtrail/learning-index.md`
2. at most three matching curated learnings
3. exact source, diff, config, CI, Sonar, or scanner evidence needed for the current task

Do not load `.tailtrail/learning-events.jsonl` during normal implementation unless the user explicitly asks for history or debugging.

## Capture Rules

Capture only compact summaries:

- task type and tags
- prompt summary, not full prompt by default
- files or modules touched
- validation commands and outcomes
- solution summary
- explicit acceptance or rejection signal
- reusable learning candidate
- stale condition

Do not capture secrets, credentials, tokens, PII, PHI, customer data, raw logs, raw prompts, full assistant responses, or source-code snippets by default.

## Promotion Rules

Promote only when:

- the learning is reusable
- confidence meets the risk threshold
- sensitivity is normal
- current evidence does not contradict the learning
- the learning includes a stale condition or refresh rule

Current source, scanner, CI, policy, and guardrail evidence always wins over old learning.

## Commands

```bash
python3 scripts/tailtrail.py learn capture --type sonar --tags sonar,java --summary "Fixed validator complexity" --candidate "Extract named guard methods while preserving validation order." --validation-outcome pass --acceptance accepted
python3 scripts/tailtrail.py learn search --tags sonar,java --limit 3
python3 scripts/tailtrail.py learn promote --event-id 20260712-abc12345
python3 scripts/tailtrail.py learn summarize --month 2026-07
```
