# TailTrail For GitHub Copilot

Use TailTrail for generated code, code review, implementation plans, dependency choices, and larger AI-assisted lifecycle work in this repository.

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

- Read and inspect relevant files before suggesting changes.
- Trace important callers, tests, configuration, and data flow when behavior can be affected.
- Reuse existing project helpers, utilities, components, types, naming, validation style, error handling, and test style.
- Prefer standard library, platform-native features, framework capabilities, database constraints, and already-installed dependencies before recommending new packages.
- Keep changes small, reviewable, and rooted in the real code path.
- Preserve security, validation, authorization, escaping, accessibility, data integrity, error handling, privacy, observability, and explicit user requirements.
- Add or recommend one focused check for non-trivial logic when the project has a runnable test pattern.
- Do not request rewrites only for personal style preference.
- Apply `GUARDRAILS.md` for non-trivial, risky, dependency-sensitive, lifecycle-driven, review-heavy, or unclear work.
- Use `context/guardrail-layers.md` for the relevant implementation, review, QA, dependency, AIDLC, handoff, CI/Sonar, release, or token-saving layer.
- Do not claim tests passed, code was pushed, a deployment happened, or approval was granted unless that action actually succeeded.
- If `tailtrail-policy.md` exists, follow it for local commands, validation expectations, dependency approvals, restricted folders, ownership, and security requirements. Treat `tailtrail-policy.example.md` as a template only.

## Dependency Rule

Before recommending a new dependency, answer:

- What exact problem does it solve?
- Is the problem already solved by the standard library, platform, framework, database, cloud service, or installed dependency?
- Is a small direct implementation safer and easier to own?
- What new security, license, upgrade, runtime, bundle-size, or supply-chain risk does it add?

If this repository includes `DEPENDENCY-GATE.md`, follow it.

## TailTrail Pack Files

If this repository includes TailTrail support files, use them this way:

- `AGENTS.md`: portable project guidance.
- `GUARDRAILS.md`: evidence, uncertainty, validation truth, exactness, and safeguard rules.
- `context/guardrail-layers.md`: compact task-specific guardrail layers.
- `tailtrail-policy.md`: optional active local project policy when present.
- `tailtrail-policy.example.md`: optional policy template, not active policy.
- `AIDLC.md`: lifecycle workflow for broad, risky, ambiguous, multi-team, regulated, or long-running work.
- `DEPENDENCY-GATE.md`: dependency approval policy.
- `context/TailTrail.map.md`: first file to read when context may get large.
- `context/slices.md`: choose one context slice instead of loading every TailTrail file.
- `aidlc/stages/`: load only the active AIDLC stage playbook.
- `templates/`: use compact handoff, validation, question, and stage-gate templates.

If these files are not present, still follow the Core Rules above.

## Short TailTrail Commands

When the user says a short command such as `hello tailtrail`, `tailtrail hello`, `use TailTrail`, `use review`, `use dependency gate`, `use AIDLC`, `use AIDLC and review`, `review then AIDLC`, `use handoff`, or `save tokens`, resolve it before acting.

For `hello tailtrail`, `hello TailTrail`, `hello taitrail`, or `tailtrail hello`, run `tailtrail hello` when the launcher is installed, otherwise run `python3 scripts/tailtrail.py hello`. Show the command output; do not replace it with a conversational greeting.

If available, use `scripts/expand-intent.py` or the installed pack path shown below to expand the command into the full TailTrail workflow. If the script cannot be run, follow `context/intent-aliases.md` and apply the matching expanded flow manually.

Project or organization prompt overrides may live in `.tailtrail/intent-overrides.json` or `tailtrail/intent-overrides.json`. Respect those overrides when present.

Supported short commands also include `use delivery flow`, `use risk flow`, `use release flow`, `use architecture review`, `use security review`, `use QA review`, `use CI Sonar`, `use maintainability review`, `use dependency review`, and `project learnings`.

## Token And Context Rules

- Apply Token Autopilot automatically before loading TailTrail support files.
- Skip routing for tiny low-risk requests where routing would cost more than it saves.
- Route non-trivial, broad, risky, noisy, review, dependency, AIDLC, or handoff work to one slice.
- Do not load unrelated design, roadmap, examples, lifecycle artifacts, or raw logs by default.
- Keep exact text for source code, diffs, configs, commands, dependency versions, file paths, IDs, hashes, stack traces, and security rules.
- Summarize noisy logs into command, result, first relevant failure, affected files, and next action.

If local TailTrail scripts are available, `scripts/token-auto.py` is the backend decision helper. Copilot should follow the same decision logic even when it cannot run the script directly.

## AIDLC And Handoff

Use AIDLC only when lifecycle structure adds value. For small, clear changes, keep the workflow light.

For handoff, summarize:

- task and intent
- changed files
- existing code reused
- work intentionally skipped
- validation run
- validation not run
- remaining risk
- next approval or owner

## Guardrails

Use only relevant sections from `GUARDRAILS.md` and only the relevant layer from `context/guardrail-layers.md`. Preserve exact code, diffs, configs, commands, dependency versions, IDs, paths, hashes, security rules, policy text, and logs being debugged. For non-trivial work, include evidence, assumptions, skipped areas, and residual risk.
