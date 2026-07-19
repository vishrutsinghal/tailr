# TailTrail Prompts For ChatGPT

## Start A Task

```text
Use TailTrail from .openai/chatgpt-instructions.md. Show a Navigator-first plan only. Include likely files, selected TailTrail features, skipped features, validation, review, and approval questions. Do not implement until I approve.
```

## Implement

```text
Use TailTrail. Inspect relevant source, callers, tests, config, and policy before editing. Reuse existing conventions, avoid unnecessary dependencies, preserve safeguards, and keep the diff small.
```

## Review

```text
Use TailTrail Review. Check code health and requirement fulfillment against my original request or approved plan. Include severity, file, function, line, impact, fix, validation, and confidence.
```

## AIDLC

```text
Use TailTrail AIDLC for broad, risky, ambiguous, multi-team, regulated, or long-running work. Ask clarification questions with recommended answers and reasoning.
```

## Scanner Safe

```text
Use TailTrail scanner approval. Ask before running or recommending Sonar, vulnerability, audit, build, broad test, or other heavy commands.
```

## Token Saving

```text
Use TailTrail token-saving rules. Keep exact source, diffs, configs, commands, paths, IDs, hashes, dependency versions, logs, policy, and security evidence exact.
```

## Handoff

```text
Use TailTrail Handoff. Summarize task, changed files, reused patterns, validation, skipped work, residual risk, and next owner.
```

