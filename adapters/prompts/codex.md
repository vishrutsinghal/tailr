# TailTrail Prompts For Codex

## Start A Task

```text
Use TailTrail Navigator for this task. Show the plan only first, including files to inspect, selected TailTrail features, skipped features, validation, review, and approval questions. Do not implement until I approve.
```

For a short explicit Navigator request, use the requested depth: `using TailTrail Navigator, <scope>` for context discovery; `... plan <scope>` for a TailTrail decision only; `... implement <scope>` for that decision plus a separately labeled implementation proposal. Never treat the word “implementation” in this control phrase as permission to edit.

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

## Discuss An Awaiting Plan

```text
Use TailTrail Interactive Plan Mode for the active run. Explain the selected
files, requirements, TailTrail features, AIDLC mode, validation, drift, token
estimate, or approval boundary from saved planning evidence only. Keep the same
run ID. Do not inspect source, change the plan, or implement work unless I
explicitly approve the separate investigation or revision flow.
```

To deepen an awaiting Lite plan without restarting it, say: `Switch this run to
Standard AIDLC.` TailTrail must show a versioned mode-switch proposal first;
approval begins Standard AIDLC requirements, not implementation.
