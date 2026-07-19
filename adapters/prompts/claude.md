# TailTrail Prompts For Claude

## Start A Task

```text
Use TailTrail from CLAUDE.md. Start with a Navigator-first plan only. Include likely files, selected TailTrail features, skipped features, validation, review, and approval questions. Do not implement until I approve.
```

## Implement

```text
Use TailTrail from CLAUDE.md. Inspect relevant source, callers, tests, and policy first. Reuse existing conventions, avoid new dependencies, keep the diff small, and preserve safeguards.
```

## Review

```text
Use TailTrail Review. Review changed code for code health and requirement fulfillment. Include severity, file, function, line, impact, fix, validation, confidence, and residual risk.
```

## AIDLC

```text
Use TailTrail AIDLC when the work is broad, risky, ambiguous, multi-team, regulated, or long-running. Ask clarification questions with recommended answers and reasoning.
```

## Scanner Safe

```text
Use TailTrail scanner approval rules. Do not run Sonar, vulnerability, audit, build, broad test, or heavy commands until you show the exact command and I approve.
```

## Token Saving

```text
Use TailTrail Token Autopilot rules. Skip routing for tiny tasks; route broad/noisy/risky work to one relevant slice. Keep exact evidence exact.
```

## Handoff

```text
Use TailTrail Handoff. Capture task, files, validation, skipped work, remaining risk, and next approval.
```

