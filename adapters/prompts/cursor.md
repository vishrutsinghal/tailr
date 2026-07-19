# TailTrail Prompts For Cursor

## Start A Task

```text
Use TailTrail from .cursor/rules/tailtrail.mdc. Show a Navigator-first plan only. Include likely files, selected features, skipped features, validation, review, and approval questions. Do not implement until I approve.
```

## Implement

```text
Use TailTrail. Read relevant files first, reuse existing helpers and patterns, avoid new dependencies, preserve safeguards, and make the smallest maintainable change.
```

## Review

```text
Use TailTrail Review on the changed files. Check code health, requirement fulfillment, validation gaps, duplicate logic, weakened safeguards, and dependency risk.
```

## AIDLC

```text
Use TailTrail AIDLC only if lifecycle structure adds value. Ask questions with recommended answers and reasoning before planning implementation.
```

## Scanner Safe

```text
Use TailTrail scanner approval. Show the exact Sonar, vulnerability, audit, build, or broad test command first and wait for approval.
```

## Token Saving

```text
Use TailTrail token-saving rules. Load only relevant context slices and preserve exact code, diffs, configs, commands, IDs, paths, logs, policy, and security evidence.
```

## Handoff

```text
Use TailTrail Handoff. Summarize changed files, intent, validation, skipped work, residual risk, and next owner.
```

