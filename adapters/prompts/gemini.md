# TailTrail Prompts For Gemini

## Start A Task

```text
Use TailTrail from GEMINI.md. Start with a Navigator-first plan only. Include likely files, selected TailTrail features, skipped features, validation, review, and approval questions. Do not implement until I approve.
```

## Implement

```text
Use TailTrail. Read relevant source, callers, tests, and policy first. Reuse existing helpers and patterns, avoid new dependencies, preserve safeguards, and keep the smallest maintainable diff.
```

## Review

```text
Use TailTrail Review on the changed scope. Check code health, requirement fulfillment, validation gaps, dependency risk, duplicate logic, and weakened safeguards.
```

## AIDLC

```text
Use TailTrail AIDLC when lifecycle structure adds value. Ask clarification questions with recommended answers and reasoning before implementation.
```

## Scanner Safe

```text
Use TailTrail scanner approval. Show the exact Sonar, vulnerability, audit, build, broad test, or other heavy command and wait for approval.
```

## Token Saving

```text
Use TailTrail token-saving guidance. Skip routing for tiny tasks, route broad/noisy/risky tasks to one slice, and preserve exact evidence.
```

## Handoff

```text
Use TailTrail Handoff. Capture task, changed files, validation run/not run, skipped work, remaining risk, and next approval.
```

