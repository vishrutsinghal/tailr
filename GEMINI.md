# TailTrail For Gemini

Use TailTrail for implementation, review, planning, and handoff in this repository.

## Adapter Contract

- Use a Navigator-first workflow for non-trivial tasks: understand the goal, identify likely files and TailTrail features, then ask for approval before implementation.
- After code changes, recommend post-change review against both code health and requirement fulfillment.
- Require scanner approval before running Sonar, vulnerability, audit, build, broad test, or other heavy local commands.
- Treat learnings as advisory; current source, tests, CI, scanners, policy, guardrails, and explicit user direction always win.
- Keep token-saving claims estimated unless measured telemetry is provided.
- Label evidence clearly when using graph or scanner metadata: heuristic, local-ast, provider-backed, measured/validated.
- Follow `tailtrail-policy.md` when present and never use local policy to weaken TailTrail safety rules.

## Core Rules

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

- Read the task and inspect relevant files before editing.
- Trace important callers, tests, configs, and data flow.
- Reuse existing helpers, utilities, types, components, conventions, and tests.
- Prefer standard library, platform-native features, framework behavior, and installed dependencies.
- Apply `DEPENDENCY-GATE.md` before adding or changing dependencies.
- Keep the smallest maintainable diff that solves the root problem.
- Preserve validation, authorization, escaping, accessibility, data integrity, error handling, and explicit requirements.
- Apply `GUARDRAILS.md` for non-trivial, risky, dependency-sensitive, lifecycle-driven, review-heavy, or unclear work.
- Use `context/guardrail-layers.md` for the relevant implementation, review, QA, dependency, AIDLC, handoff, CI/Sonar, release, or token-saving layer.
- Do not claim tests passed, code was pushed, a deployment happened, or approval was granted unless that action actually succeeded.
- If `tailtrail-policy.md` exists, follow it for local commands, validation expectations, dependency approvals, restricted folders, ownership, and security requirements. Treat `tailtrail-policy.example.md` as a template only.

## Token Discipline

Apply Token Autopilot automatically:

- Skip routing for tiny low-risk requests.
- Route non-trivial, broad, risky, noisy, review, dependency, AIDLC, or handoff work to one slice.
- For broad or repeated work, load `context/TailTrail.map.md` and one slice from `context/slices.md`.
- Summarize noisy logs with `templates/tool-summary.md`.

Keep exact text for code, diffs, configs, commands, dependency versions, paths, IDs, hashes, and security-sensitive rules.

If local scripts are available, use `python3 scripts/token-auto.py "<prompt>"` for the backend decision.

## Short TailTrail Commands

When the user says `hello tailtrail`, `tailtrail hello`, `use TailTrail`, `use review`, `use dependency gate`, `use AIDLC`, `use AIDLC and review`, `review then AIDLC`, `use handoff`, or `save tokens`, expand the intent before acting.

For `hello tailtrail`, `hello TailTrail`, `hello taitrail`, or `tailtrail hello`, run `tailtrail hello` when the launcher is installed, otherwise run `python3 scripts/tailtrail.py hello`. Show the command output; do not replace it with a conversational greeting.

If local scripts are available, run `python3 scripts/expand-intent.py "<user phrase>"` and follow the expanded prompt. If the script is not available, use `context/intent-aliases.md` as the fallback.

Respect project or organization overrides in `.tailtrail/intent-overrides.json` or `tailtrail/intent-overrides.json` when present.

Supported short commands also include `use delivery flow`, `use risk flow`, `use release flow`, `use architecture review`, `use security review`, `use QA review`, `use CI Sonar`, `use maintainability review`, `use dependency review`, and `project learnings`.

## AIDLC

Use `AIDLC.md` for broad, risky, ambiguous, regulated, multi-team, or long-running work. Use only the active stage playbook from `aidlc/stages/`.

For handoff, use `aidlc/stages/handoff.md` and the matching handoff template.

## Guardrails

Use only relevant sections from `GUARDRAILS.md` and only the relevant layer from `context/guardrail-layers.md`. Preserve exact code, diffs, configs, commands, dependency versions, IDs, paths, hashes, security rules, policy text, and logs being debugged. For non-trivial work, include evidence, assumptions, skipped areas, and residual risk.
