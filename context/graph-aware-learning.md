# TailTrail Graph-Aware Learning

Use this context when a prior learning should be matched to the current code scope.

## Purpose

Graph-Aware Learning connects two separate TailTrail facts:

- Code Graph Mapper: current files, symbols, tests, callers, endpoints, DB tables, manifests, and freshness.
- Learning Agent V2: accepted reusable repo patterns with confidence scores.

The bridge links metadata only. It does not store source snippets, raw prompts, raw logs, or assistant responses.

## Matching Rules

Prefer strong matches:

- exact changed file
- linked test or caller
- exact symbol
- exact scanner rule ID
- endpoint, table, manifest, or validation-command match
- matching task tags such as `sonar`, `ci`, `dependency`, `security`, or `qa`

If the graph cache is stale, invalid, or missing, label matches as weaker and inspect current source before relying on any prior pattern.

## Retrieval Rules

- Load `.tailtrail/graph-learning-index.json` or `.tailtrail/learning-index.md` first.
- Surface at most three matches by default.
- Exclude rejected, sensitive, stale, low-confidence, or unapproved learnings from automatic retrieval.
- Explain why each learning matched.
- Show matches in a plan, never as hidden instructions.

## Boundaries

- Do not apply a learning blindly.
- Current source, scanner, CI, policy, and guardrail evidence wins over old learning.
- Do not load `.tailtrail/learning-events.jsonl` during normal implementation.
- Do not put learning facts inside the Code Graph Mapper cache.
