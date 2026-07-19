# TailTrail Prompts For GitHub Copilot

## Start A Task

```text
Use TailTrail from .github/copilot-instructions.md. Provide a Navigator-first plan only. Include likely files, selected TailTrail features, skipped features, validation, review, and approval questions. Do not implement until I approve.
```

## Implement

```text
Use TailTrail. Read relevant source, callers, tests, and policy before suggesting code. Reuse existing patterns, avoid new dependencies, preserve safeguards, and keep the change small.
```

## Review

```text
Use TailTrail Review for these changes. Check code health and requirement fulfillment. Include severity, file, function, line, issue, fix, validation, and confidence.
```

## AIDLC

```text
Use TailTrail AIDLC for this broad/risky/multi-step work. Ask questions with recommended answers and reasoning before implementation planning.
```

## Scanner Safe

```text
Use TailTrail scanner approval. Do not run or suggest broad scanner/build/test execution without showing the exact command and asking for approval.
```

## Token Saving

```text
Use TailTrail token-saving guidance. Route only when useful, keep exact evidence exact, and do not claim exact token savings without measured telemetry.
```

## Handoff

```text
Use TailTrail Handoff. Record task intent, changed files, reused code, validation run/not run, skipped work, remaining risk, and next approval.
```

