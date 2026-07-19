# TailTrail Meta-Harness Proposal

- Proposal ID:
- Status: proposed
- Evidence threshold:
- Source finding:
- Recommendation:

## Candidate Edits

Review before adding. These are recommendations, not automatic changes.

| File | Line Hint | Proposed Prompt/Change |
|---|---:|---|
|  |  |  |

## Verification Plan

- Run targeted unit tests for the changed TailTrail behavior.
- Run `python3 scripts/tailtrail.py doctor`.
- Re-run the relevant Navigator, review, graph, report, or learning scenario.
- Confirm no guardrail, local policy, validation, scanner approval, security, or public-claim boundary regressed.

## Rollback Plan

- Revert the product-change commit if behavior degrades.
- Record the proposal outcome with `tailtrail harness proposal-record --status rolled_back`.

## Safety Boundaries

- Do not upload data automatically.
- Do not collect raw prompts, raw logs, source code, diffs, file paths, repo names, branch names, users, private URLs, scanner raw output, secrets, or exact token usage in shared evidence.
- Do not score individual developers.
- Do not rewrite TailTrail automatically.
