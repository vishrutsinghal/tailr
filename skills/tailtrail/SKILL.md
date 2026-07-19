---
name: tailtrail
description: Use for coding, bug fixing, refactoring, reviewing diffs, choosing dependencies, planning implementation, reducing context noise, or when the user asks for a smaller, simpler, cleaner, reuse-first, low-boilerplate, or easy-to-review implementation. Supports steady, lean, and strict modes. TailTrail guides Codex to use Navigator-first planning when useful, inspect relevant code first, reuse existing project patterns, prefer standard library and platform-native capabilities, avoid unnecessary dependencies, keep diffs small, preserve safeguards, validate honestly, and keep token-saving exactness boundaries clear.
---

# TailTrail

Use TailTrail to keep local development changes small, clear, and grounded in the codebase.

## Modes

Use `steady` unless the user asks for another mode.

| Mode | Use when | Behavior |
|---|---|---|
| `steady` | Normal implementation work | Build the requested change with the trail check and keep the explanation compact. |
| `lean` | The user asks for the smallest clear implementation | Prefer the shortest maintainable path and call out anything intentionally skipped. |
| `strict` | Scope is unclear, broad, or likely overbuilt | Challenge unnecessary scope before coding, then propose or build the smallest useful version. |

Mode can be requested in plain language, such as `@tailtrail lean add this endpoint` or `@tailtrail strict review this design`.

## Trail Check

Before proposing or editing code:

1. Confirm the requested change is needed for the stated outcome.
2. Inspect the files, callers, tests, and data flow that the change touches.
3. Look for existing helpers, utilities, types, components, conventions, and nearby patterns.
4. Prefer standard library, platform-native behavior, database constraints, framework features, and already-installed dependencies before adding custom code.
5. Avoid new dependencies unless they remove meaningful risk or complexity.
6. Choose the smallest maintainable diff that solves the real problem.

For broad, repeated, or noisy tasks, use `context/TailTrail.map.md` to choose one relevant TailTrail slice. Do not load roadmap, design, examples, or future-scope docs unless the task needs them.

For user requests that are broad, unclear, cross-file, scanner-driven, review-heavy, or likely to involve multiple TailTrail features, use the Navigator-first flow before implementation. Prefer the command surface when available:

```bash
python3 scripts/tailtrail.py guide "user goal"
python3 scripts/tailtrail.py start "user goal"
python3 scripts/tailtrail.py next
```

Navigator is advisory and deterministic. It should show the likely TailTrail path, impacted files, context to load, context to avoid, suggested commands, and approval questions. Do not run scanners, vulnerability checks, broad builds, or learning capture without explicit approval.

For broad, risky, ambiguous, multi-team, regulated, or long-running work, use `AIDLC.md` at the smallest useful depth. Use `templates/change-brief.md` only for non-trivial work, and resume from `aidlc-docs/aidlc-state.md` instead of reloading every lifecycle artifact.

For non-trivial, risky, dependency-sensitive, lifecycle-driven, or unclear work, apply `GUARDRAILS.md`. Use only the relevant guardrail sections; do not load the full file for tiny low-risk edits.

If `tailtrail-policy.md` exists in the target project, follow it for local commands, validation expectations, ownership, restricted folders, dependency approval rules, and security requirements. Treat `tailtrail-policy.example.md` as a template only.

## Implementation Rules

- Read before changing. A small diff in the wrong place is still wrong.
- Fix shared causes, not just the visible symptom. When touching a function or component, inspect its important callers and fix the common path when that is the real source.
- Reuse project naming, layout, error handling, validation style, and test style.
- Prefer direct code over speculative layers, single-use abstractions, future-only configuration, broad rewrites, and scaffolding that the task did not ask for.
- Keep important guards even when they add lines: trust-boundary validation, authorization, escaping, error handling that prevents data loss, accessibility basics, and explicit user requirements.
- Do not claim tests passed, code was pushed, a deployment happened, or an approval was granted unless that action actually succeeded.
- Label unknowns and assumptions instead of inventing project behavior.
- Before adding or changing a dependency, apply `DEPENDENCY-GATE.md` and prefer existing project capabilities first.
- For non-trivial logic, add one focused runnable check that would fail if the behavior regresses. Do not add large test scaffolding unless the change already uses that pattern.
- If a shortcut is intentional and has a clear limit, name the limit briefly in a `tailtrail:` comment near the code.

## Token And Context Discipline

Use Token Harness when context is large, repetitive, scanner/log-heavy, or when token-saving claims may be discussed.

Useful commands:

```bash
python3 scripts/tailtrail.py token-harness route --path path/to/file
python3 scripts/tailtrail.py token-harness reduce --path path/to/artifact
python3 scripts/tailtrail.py token-harness proof report
python3 scripts/tailtrail.py token-harness bridge plan --path build.log
```

Rules:

- Source, diffs, configs, dependency manifests, lock files, security policy, secrets, unknown content, and `must-be-exact` evidence must stay exact.
- Structured reducers can compact safe bulky artifacts while preserving retrieval pointers.
- The Runtime Compression Bridge is disabled by default, requires local policy opt-in, requires `--approved` to run an adapter, and must reject adapter output that violates exactness.
- Do not claim exact token savings unless measured model/API telemetry is supplied. Otherwise label results as estimated or local evidence.

## Learning And Metrics

Learning, outcome capture, quality loop, and Meta-Harness evidence are advisory. They can improve future guidance only when confidence, validation, and approval rules are satisfied.

- Do not record raw prompts, source, logs, secrets, repo names, user identity, PII, PHI, or customer data.
- Do not promote low-confidence or stale learning as fact.
- Current source, tests, CI, scanners, policy, guardrails, and explicit user instructions always override learnings.
- Meta-Harness proposals should remain proposal-first, human-approved, test-backed, and reversible.

## Response Shape

Lead with the change or recommendation. Keep the explanation short unless the user asks for detail.

When useful, include:

- Active mode, only when it affects the decision.
- What was reused.
- What was intentionally skipped.
- Evidence or assumptions, when the work is non-trivial or risky.
- When the skipped work should be added.

Do not pad the answer with broad design notes, feature tours, or optional architectures that the task does not need.

## Review Mode

When reviewing code or a diff, look first for:

- Duplicate helpers or logic that can reuse existing code.
- New dependencies that standard library, platform, framework, or installed packages already cover.
- Abstractions with only one real use.
- Large changes that can be split into a smaller root-cause fix.
- Removed validation, authorization, accessibility, or data-loss protections.
- Tests that are too broad for the change, or missing one focused check for non-trivial logic.
- Whether the implementation actually satisfies the user request, AIDLC requirements, or approved Navigator plan.

Return concrete findings and suggested reductions. Do not ask for rewrites only to satisfy style preference.
