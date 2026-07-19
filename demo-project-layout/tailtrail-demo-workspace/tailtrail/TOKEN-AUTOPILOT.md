# Token Autopilot

Token Autopilot is TailTrail's automatic token-saving decision layer. It decides whether a request needs routing at all, then chooses the cheapest safe strategy for non-trivial work.

It is intentionally lightweight. The goal is to save tokens without adding a process tax to tiny requests.

## Contract

For each prompt or task, Token Autopilot returns:

- whether to route or skip
- task size estimate
- selected route when routing is useful
- files or context to load
- files or context to avoid
- exactness risk
- reason
- next action

## Skip Rule

Skip routing when the prompt is small and low-risk.

Examples:

- "fix typo"
- "rename this variable"
- "format this file"
- "explain this function"
- "what does this error mean?"

When skipped, the assistant should answer directly or inspect only the exact file already in scope. It should not load TailTrail docs.

## Route Rule

Run routing when the prompt suggests:

- implementation or refactoring across files
- diff or pull request review
- dependency decisions
- AIDLC or handoff work
- logs, build output, test output, or stack traces
- security, config, authorization, validation, data, or privacy risk
- broad or unclear project areas
- repeated context or large docs
- tool, browser, API, MCP, or raw JSON/HTML output

## Backend Script

Use:

```bash
python3 scripts/token-auto.py "review this diff for dependency risk"
python3 scripts/token-auto.py --format json "fix failing tests from this log"
python3 scripts/token-auto.py --no-state "rename this variable"
```

By default it writes:

```text
.tailtrail/token-autopilot-state.json
```

## Hook

Hook-capable hosts can call:

```bash
python3 hooks/token-autopilot-hook.py "review this diff"
```

The hook prints a compact context injection only when routing is useful. For tiny work, it prints a skip decision.

## Assistant Integration

Adapters should instruct assistants to apply Token Autopilot automatically:

1. Decide whether the prompt is tiny and low-risk.
2. If tiny, skip routing and avoid TailTrail docs.
3. If non-trivial, classify route and load one slice.
4. Keep code, diffs, configs, commands, paths, IDs, hashes, dependency versions, stack traces, and security rules exact.
5. Summarize noisy output instead of pasting full logs.

## Success Criteria

Token Autopilot succeeds when:

- small requests do not load TailTrail docs
- non-trivial requests load one useful slice instead of many files
- exact material remains exact
- noisy output is summarized
- route decisions are recorded when scripts or hooks run
