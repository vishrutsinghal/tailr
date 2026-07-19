# TailTrail Learning Refresh

Use this context when reviewing whether existing TailTrail learnings are still safe, useful, and worth retrieving.

## Purpose

Learning Refresh reviews learning quality and evidence. It does not judge users, train a model, or rewrite history.

It looks for:

- stale graph-linked files
- missing validation evidence
- low confidence scores
- user overrides
- rejected or sensitive learnings
- duplicate learning candidates
- policy, guardrail, dependency, or scanner profile changes

## Rules

- Recommend actions first.
- Do not change learning files without explicit approval.
- Current source, CI, scanner, policy, and guardrail evidence wins over old learning.
- Keep raw prompts and raw event history out of normal implementation context.
- Use refresh to reduce noisy retrieval, not to create another large memory file.

## Actions

- `keep`: still useful.
- `improve`: needs better evidence, scope, stale condition, or validation command.
- `demote`: should no longer be treated as trusted.
- `mark-stale`: linked code, rule, or validation evidence changed.
- `suppress`: should not auto-surface.
- `archive`: old/noisy learning should move out of normal retrieval.
- `merge`: duplicate learnings should be consolidated.
- `delete`: only with explicit approval and local policy support.
