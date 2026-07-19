# TailTrail Flow Catalog

Named flows let users ask for an outcome instead of naming every TailTrail feature.

Use `scripts/expand-intent.py` to resolve short flow names into the current internal prompt, run order, load list, avoid list, validation, and notes.

## Flows

| Flow | Short Prompt | Purpose |
|---|---|---|
| `delivery` | `Use delivery flow.` | Plan with AIDLC, implement carefully, review, validate, and prepare handoff when useful. |
| `risk` | `Use risk flow.` | Check dependency, security, validation, data integrity, and rollout risk before or during implementation. |
| `review` | `Use review flow.` | Review exact changes for correctness, unnecessary dependencies, duplicate logic, broad rewrites, weakened safeguards, and missing checks. |
| `handoff` | `Use handoff flow.` | Create a compact transfer package for reviewer, QA, operations, or another assistant. |
| `release` | `Use release flow.` | Prepare final validation and release handoff without adding heavy deployment automation. |

## Flow Rules

- Load one flow at a time.
- Keep source code, diffs, configs, commands, dependency versions, IDs, paths, hashes, stack traces, and security rules exact.
- Prefer AIDLC state and handoff summaries over chat memory for multi-step work.
- Do not turn every tiny change into a lifecycle flow. Use plain TailTrail for small, low-risk edits.

## Suggested Daily Use

```text
Use delivery flow for this feature.
```

```text
Use risk flow before adding this package.
```

```text
Use release flow to prepare this change for approval.
```
