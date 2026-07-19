# Guardrail Layers

Guardrail Layers are compact task-specific reminders. They extend `GUARDRAILS.md`; they do not replace it, weaken it, or create a hidden policy engine.

Use this file when a task is non-trivial, risky, review-heavy, QA-heavy, consistency-sensitive, dependency-sensitive, lifecycle-driven, release-related, CI/Sonar-related, or token-sensitive. Load only the relevant layer plus exact task material.

## Global Pointer

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

Always apply:

- `GUARDRAILS.md` for the behavior contract.
- `tailtrail-policy.md` when present in the target project.
- explicit user requirements for the current task.
- exact text for code, diffs, configs, commands, IDs, paths, hashes, dependency versions, security rules, policy text, and logs being debugged.

Do not let local policy, project memory, summaries, or token-saving choices weaken explicit safety rules.

## Implementation Layer

Use for coding, fixing, refactoring, and simplifying.

- Read relevant files before editing.
- Trace important callers, tests, shared helpers, and ownership boundaries.
- Reuse existing project patterns before adding abstractions or dependencies.
- Make the smallest maintainable change that solves the root problem.
- Preserve validation, authorization, escaping, accessibility basics, data integrity, logging, auditability, privacy, and error handling.
- Leave one focused runnable check for non-trivial logic when the project has a reasonable check path.

Avoid unrelated rewrites, broad formatting churn, speculative abstractions, and guard removal disguised as simplification.

## Code Consistency Layer

Use for implementation, refactoring, review, generated-code acceptance, and repo-wide cleanup decisions.

- Inspect nearby files before choosing names, folder placement, module boundaries, error handling, logging, validation style, test style, and configuration shape.
- Match existing naming conventions, import order, file organization, API shapes, response formats, exception patterns, and test structure unless there is a clear reason not to.
- Reuse existing helpers, constants, types, schemas, validators, fixtures, and factories before creating parallel versions.
- Keep formatting consistent with the repository's configured formatter or nearby code. Do not introduce formatting churn outside the changed area.
- Preserve established boundaries between generated code, application code, tests, migrations, adapters, and infrastructure files.
- When improving an inconsistent pattern, keep the scope explicit and explain why the change is worth the review cost.

Avoid one-off style inventions, duplicate helpers with new names, mixed error/validation patterns, and broad consistency rewrites unless explicitly requested.

## Review Layer

Use for code review, pull requests, simplification review, and final diff review.

- Lead with concrete findings ordered by severity.
- Ground findings in exact changed files, likely callers, tests, configs, or manifests.
- Check for unnecessary dependencies, duplicate logic, over-broad rewrites, weakened safeguards, missing validation, and behavior risk.
- Say clearly when there are no findings.
- Name residual risk or test gaps without padding the review with style-only comments.

Avoid generic advice, taste-only commentary, and findings that cannot be tied to evidence.

## QA / Validation Layer

Use for test planning, validation review, regression checks, and acceptance evidence.

- Separate passed, failed, skipped, blocked, and not-run checks.
- Preserve exact commands, first relevant failures, affected files, and environment assumptions.
- Map validation to changed behavior and likely regression paths.
- Prefer one focused check that would fail if the changed behavior breaks.
- If automation is unavailable, state the manual path and residual risk.

Do not claim tests, builds, lint, typecheck, scans, pushes, or deployments succeeded unless the command actually ran and succeeded.

## Dependency Layer

Use for adding, upgrading, replacing, removing, or recommending packages, tools, SDKs, services, or major platform capabilities.

- Apply `DEPENDENCY-GATE.md`.
- Prefer standard library, platform-native behavior, framework capabilities, database/cloud features, and already-installed dependencies.
- Preserve exact package names, versions, manifests, lockfile context, and approval notes.
- Check maintenance, security, license, supply-chain, runtime, upgrade, and ownership impact.
- If accepted, name the focused validation needed for the dependency path.

Do not approve a dependency just because it is convenient or popular.

## AIDLC Layer

Use for broad, risky, ambiguous, regulated, multi-team, long-running, or approval-heavy work.

- Use `AIDLC.md` to choose minimal, standard, or comprehensive depth.
- Resume from `aidlc-docs/aidlc-state.md` when present.
- Ask structured questions with recommended options and reasoning when ambiguity affects implementation.
- Use stage gates before moving from requirements to planning, planning to implementation, and implementation to validation for standard or comprehensive work.
- Record durable decisions in audit notes when they affect later owners or reviewers.

Do not create lifecycle artifacts for tiny low-risk edits unless the user asks.

## Handoff Layer

Use when work will be reviewed, paused, transferred, approved, released, or continued by another person or agent.

- Capture task intent, changed files, reused behavior, intentionally skipped work, validation run, validation not run, remaining risk, and next owner or approval.
- Include dependency decisions and preserved guardrails when relevant.
- Include rollback, monitoring, or operations notes when production behavior is affected.
- Keep validation evidence exact enough for the next owner to reproduce or trust the handoff.

Avoid chat-history dumps. Handoff should be compact and actionable.

## CI / Sonar Layer

Use for CI failures, Sonar issues, static analysis, quality gates, scans, and pipeline remediation.

- Preserve exact job name, stage, rule ID, severity, file, line, command, first relevant failure, and link or path when available.
- Fix the smallest root cause, not only the visible reported line.
- Check whether the same rule appears in nearby code or shared helpers before patching one symptom.
- Keep generated files, vendor folders, lockfiles, and baseline files within local policy boundaries.
- Rerun or name the exact check needed to verify the issue is resolved.

Do not summarize away rule IDs, file paths, failing lines, or scanner output needed for diagnosis.

## Release Layer

Use for release readiness, approval packages, rollout notes, and production handoff.

- Capture scope, final diff summary, validation evidence, dependency decisions, risk, rollback or recovery notes, documentation impact, and approval owner.
- Include environment, migration, configuration, monitoring, and support notes when deployment is in scope.
- Separate release readiness from deployment execution unless the user explicitly asks to deploy.
- Preserve exact version, branch, artifact, environment, command, and approval text when relevant.

Do not invent deployment status, approvals, production results, or monitoring outcomes.

## Token Saving Layer

Use for routing context, slicing Markdown, summarizing output, cache reuse, and compression decisions.

- Prefer `context/TailTrail.map.md` and one slice from `context/slices.md`.
- Use `scripts/token-auto.py` to skip routing for tiny low-risk prompts when automation is available.
- Preserve exact task material when exactness risk is high.
- Summarize noisy output into counts, first failures, affected files, and next actions only when exact text is not required.
- Use compression only for bulky, stable, non-exact reference material.

Token saving must never hide material facts or make validation, policy, security, dependency, or source evidence lossy.
