# TailTrail Shared Metadata

This folder is for sanitized TailTrail process metadata that a repository may choose to commit.

Shared files must contain categorical workflow evidence only. They must not contain raw prompts, assistant responses, source code, diffs, file paths, repo names, branch names, users, emails, private URLs, package names, scanner raw output, secrets, or exact token usage.

Supported shared files:

- `code-graph-cache.json`: shared code graph cache for faster repo understanding.
- `harness-summary.jsonl`: optional append-only Meta-Harness evidence events, including sanitized categorical Token Harness feedback such as strategy, exactness class, reduction band, proof label, quality outcome, holdout, and confidence gate.
- `harness-summary.schema.json`: schema for the shared harness summary event shape.

`.tailtrail/` remains local private runtime state. Review this folder before committing it for the first time.
