# TailTrail Learning Agent V3

Use this context when a task discovers a reusable repo pattern, fixes a repeated issue, or needs a small set of prior learnings.

## Purpose

Learning Agent V3 turns repeated repo work into compact local knowledge using
the append-only `.tailtrail/learning-v3/events.jsonl` contract:

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

1. establish the repository project frame and current task frame
2. request the closed Learning V3 use proposal
3. inspect at most three explained, high-value matches only after the user chooses them
4. inspect exact source, diff, config, CI, Sonar, or scanner evidence needed for the current task

Do not load `.tailtrail/learning-v3/events.jsonl`, `.tailtrail/learning-index.md`,
or the legacy `.tailtrail/learning-events.jsonl` into normal implementation
context. Navigator uses `tailtrail learn retrieve` as a read-only gate and
renders advice only as a default-deny proposal. Stale, suppressed, private,
excluded, missing-source, and conflicting advice stays blocked; Lite remains
quiet when no high-value match exists.

When a proposed learning is explicitly applied, treated as advisory, ignored,
rejected, or found stale, record that decision with `tailtrail learn receipt
record` against the approved requirement UID. Do not infer a decision from
implementation text or chat narration. Canonical closure will join the receipt
to saved requirement, drift, Harness, failure, validation, and Completion
Report evidence. Treat the resulting utility only as a bounded observed
association; it is never causal and never outranks current evidence.

Before surfacing advice, also apply PM-L4 governance. A changed policy, graph,
symbol, manifest, ownership, source, or validation fingerprint blocks the
record. An open challenge, pairwise conflict, repeated adverse receipt signal,
or invalid governance ledger also blocks it. Never render blocked advice.
Revalidation, conflict resolution, negative promotion, and dismissal require
existing project-relative evidence and explicit approval. Negative promotion
may create sanitized `avoid-history`; it never copies raw failure content.

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
python3 scripts/tailtrail.py learn v3 validate --root .
python3 scripts/tailtrail.py learn v3 migrate --root . --dry-run
python3 scripts/tailtrail.py learn retrieve --root . --task-types qa --tags validation --path tests/test_service.py
python3 scripts/tailtrail.py learn receipt record --root . --run-id <run-id> --learning-id <learning-id> --decision applied --decision-type validation --requirement-uid <requirement-uid> --rationale "Selected after proposal review" --approved
python3 scripts/tailtrail.py learn receipt validate --root . --run-id <run-id>
python3 scripts/tailtrail.py learn governance state --root .
python3 scripts/tailtrail.py learn governance negative-scan --root .
```
