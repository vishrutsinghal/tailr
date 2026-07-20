# TailTrail Project Guidance

TailTrail keeps coding work small, clear, and reuse-first.

## Synchronized Governance Block

<!-- tailtrail-governance:start -->
- Read relevant source, callers, tests, configuration, and policy before changing code.
- Reuse existing helpers, types, conventions, validation style, and project patterns before adding new abstractions.
- Prefer standard library, platform-native behavior, framework capabilities, and already-installed dependencies before adding packages.
- Make the smallest maintainable change that solves the root problem without unrelated rewrites or formatting churn.
- Preserve safeguards: authentication, authorization, validation, escaping, accessibility, data integrity, privacy, logging, auditability, error handling, data-loss prevention, and explicit user requirements.
- Do not claim tests, builds, scans, pushes, deployments, merges, or approvals succeeded unless they actually ran and succeeded.
- Preserve exact source, diffs, configs, commands, file paths, IDs, hashes, dependency names and versions, security rules, policy text, and logs when exactness affects the task.
- Token saving must not hide material facts or make validation, policy, security, dependency, or source evidence lossy.
- Use `tailtrail-policy.md` when present, and never let local policy, project memory, summaries, or learnings weaken explicit safety rules.
<!-- tailtrail-governance:end -->

Before changing code:

1. Read the task fully and inspect the relevant files.
2. Trace the real code path, including important callers and tests.
3. Reuse existing helpers, utilities, components, types, and conventions.
4. Prefer standard library, platform-native behavior, framework features, and already-installed dependencies.
5. Avoid new dependencies and speculative abstractions unless the task clearly needs them.
6. Make the smallest maintainable change that solves the root problem.

Do not remove safeguards to shorten code. Preserve trust-boundary validation, authorization, escaping, accessibility basics, data-loss prevention, and explicit user requirements.

Use `GUARDRAILS.md` for non-trivial, risky, review-heavy, dependency-sensitive, lifecycle-driven, or unclear work. Do not claim facts, validation, pushes, deployments, or approvals without evidence. Preserve exact code, diffs, configs, commands, dependency versions, security rules, and policy text when exactness affects the task.

If `tailtrail-policy.md` exists in the target project, read it for local commands, dependency approval rules, validation expectations, ownership, restricted folders, and security requirements. If only `tailtrail-policy.example.md` exists, treat it as a template, not active policy.

For non-trivial logic, leave one focused runnable check that would fail if the behavior breaks. Keep explanations brief: say what changed, what was intentionally skipped, and when to add the skipped work.

For broad, risky, ambiguous, multi-team, regulated, or long-running work, use the portable lifecycle in `AIDLC.md`. Keep generated lifecycle artifacts in `aidlc-docs/`, resume from `aidlc-docs/aidlc-state.md`, and apply `DEPENDENCY-GATE.md` before adding or changing dependencies.

When the user gives an explicit `tailtrail <command>` request, run the equivalent TailTrail CLI command from the current project root. If the launcher is unavailable, use `python3 scripts/tailtrail.py <command>` from a source checkout. Return the actual command result, including any error or validation status; never replace an unrun command with a generic success summary. When the user gives a short TailTrail command such as `hello tailtrail`, `hello TailTrail`, `hello taitrail`, `tailtrail hello`, `use AIDLC`, `use review`, `use AIDLC and review`, `use dependency gate`, `use handoff`, or `save tokens`, expand it with `scripts/expand-intent.py` when available. Treat TailTrail casing and the common `taitrail` typo as TailTrail for short commands. For hello commands, run `tailtrail hello` when the launcher is installed, otherwise run `python3 scripts/tailtrail.py hello`; do not answer with only a conversational greeting. Return the command's ASCII TailTrail banner and installation result verbatim in the chat response; do not summarize or omit the banner. If the script is unavailable, use `context/intent-aliases.md`. Respect `.tailtrail/intent-overrides.json` or `tailtrail/intent-overrides.json` when present.

Use named flows and review lenses when requested: `delivery flow`, `risk flow`, `release flow`, `architecture review`, `security review`, `QA review`, `maintainability review`, and `dependency review`. Capture durable project facts in `.tailtrail/learnings.md` only when they will help future agents avoid repeated discovery or repeated mistakes.
