# TailTrail Prompts For Codex

## Start A Task

```text
Use TailTrail Navigator for this task. Show the plan only first, including files to inspect, selected TailTrail features, skipped features, validation, review, and approval questions. Do not implement until I approve.
```

## Implement

```text
Use TailTrail. Read the relevant source, callers, tests, config, and policy first. Reuse existing project patterns, avoid new dependencies, make the smallest maintainable change, and run or name focused validation.
```

## Review

```text
Use TailTrail Review on the changed scope. Check code health and requirement fulfillment. Show severity, file, function, line, issue, impact, fix, validation, confidence, and whether the fix is safe to apply. Do not apply fixes without approval.
```

## AIDLC

```text
Use TailTrail AIDLC standard depth. Ask clarification questions with recommended answers and reasoning. Update lifecycle artifacts only after the plan is clear.
```

## Scanner Safe

```text
Use TailTrail Navigator for this scanner-related task. Ask before running Sonar, vulnerability, audit, build, broad test, or other heavy commands. Show the exact command and why it is needed.
```

## Token Saving

```text
Use TailTrail token-saving rules. Route only if the task is broad, noisy, risky, review-heavy, dependency-sensitive, or lifecycle-related. Preserve exact code, diffs, configs, commands, paths, IDs, hashes, dependency versions, logs, policy, and security evidence.
```

## Handoff

```text
Use TailTrail Handoff. Summarize task intent, changed files, reused patterns, validation run, validation not run, skipped work, remaining risk, and the next owner or approval needed.
```

