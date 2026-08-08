# TailTrail For Claude

Use TailTrail as the project workflow for local development.

## Adapter Contract

- Use a Navigator-first workflow for non-trivial tasks: understand the goal, identify likely files and TailTrail features, then ask for approval before implementation.
- **Planning Lock:** when the user says `tailtrail start`, `TailTrail Start`, or asks for a Navigator plan, return planning only even if the same prompt says implement, set up, create, replicate, or do similar. If the local TailTrail MCP server is configured, call the single `tailtrail_start` tool with `approved: true`; do not split the lock and report into separate calls. If this host can run project commands and the MCP tool is not available, execute `tailtrail start "<goal>"`. In both cases, **return the tool or CLI output verbatim and stop — do not append your own implementation plan, steps, analysis, or guidance after the Start Report.** If neither capability is available, clearly say the plan is not persisted and provide the exact command. Do not edit files, run project commands, scanners, Terraform, or Git mutations after planning; require a separate approval before implementation.
- **Exact Start trigger:** treat `tailtrail start,`, `tailtrail start:`, and `tailtrail start -` as the same command. A `hands-free` or `end-to-end` request means comprehensive requirement and phase planning first, never immediate execution. Return the run ID, selected Program Delivery Harness, proposed feature order, active first slice, and explicit approval gate.
- **Current-turn Start boundary:** evaluate Start only from the **current user message**. A prior chat mention, pasted **error output**, log, stack trace, or follow-up debugging request is not a Start invocation and must not create a **new Planning Lock**. Reuse an awaiting-approval run ID when requesting approval; continue an approved in-scope run without another Start approval. With no active run and no explicit Start invocation in the current user message, use ordinary TailTrail guidance or advisory `guide` routing.
- **Start response boundary:** after a successful TailTrail Start tool or CLI invocation, return its complete Start Report verbatim and stop. Do not append an implementation plan, steps, analysis, or guidance.
- After code changes, recommend post-change review against both code health and requirement fulfillment.
- Require scanner approval before running Sonar, vulnerability, audit, build, broad test, or other heavy local commands.
- Treat learnings as advisory; current source, tests, CI, scanners, policy, guardrails, and explicit user direction always win.
- Keep token-saving claims estimated unless measured telemetry is provided.
- Label evidence clearly when using graph or scanner metadata: heuristic, local-ast, provider-backed, measured/validated.
- Follow `tailtrail-policy.md` when present and never use local policy to weaken TailTrail safety rules.

## Core Behavior

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

- Read the task fully before editing.
- Inspect the relevant source, callers, tests, and data flow.
- Reuse existing helpers, types, components, conventions, and test style.
- Prefer standard library, platform-native behavior, framework features, and already-installed dependencies.
- Avoid new dependencies unless `DEPENDENCY-GATE.md` clearly approves them.
- Make the smallest maintainable change that solves the real problem.
- Preserve validation, authorization, escaping, accessibility, data integrity, error handling, and explicit user requirements.
- Apply `GUARDRAILS.md` for non-trivial, risky, dependency-sensitive, lifecycle-driven, review-heavy, or unclear work.
- Use `context/guardrail-layers.md` for the relevant implementation, review, QA, dependency, AIDLC, handoff, CI/Sonar, release, or token-saving layer.
- Do not claim tests passed, code was pushed, a deployment happened, or approval was granted unless that action actually succeeded.
- If `tailtrail-policy.md` exists, follow it for local commands, validation expectations, dependency approvals, restricted folders, ownership, and security requirements. Treat `tailtrail-policy.example.md` as a template only.

## Context Loading

Apply Token Autopilot automatically before loading TailTrail context:

- If the request is tiny and low-risk, skip routing and do not load TailTrail docs.
- If the request is non-trivial, broad, risky, noisy, review-heavy, dependency-sensitive, or lifecycle-related, route to one slice.
- Keep code, diffs, configs, commands, file paths, IDs, hashes, dependency versions, stack traces, and security rules exact.

When routing is useful, start with `context/TailTrail.map.md` for broad or repeated work. Load one slice from `context/slices.md`, then exact source files.

Do not load `DESIGN.md`, `ROADMAP.md`, all examples, all AIDLC artifacts, or raw logs unless the task specifically needs them.

If local scripts are available, use `python3 scripts/token-auto.py "<prompt>"` or `python3 hooks/token-autopilot-hook.py "<prompt>"` for the backend decision.

## Short TailTrail Commands

When the user says `hello tailtrail`, `tailtrail hello`, `use TailTrail`, `use review`, `use dependency gate`, `use AIDLC`, `use AIDLC and review`, `review then AIDLC`, `use handoff`, or `save tokens`, expand the intent before acting.

For `hello tailtrail`, `hello TailTrail`, `hello taitrail`, or `tailtrail hello`, run `tailtrail hello` when the launcher is installed, otherwise run `python3 scripts/tailtrail.py hello`. Show the command output; do not replace it with a conversational greeting.

If local scripts are available, run `python3 scripts/expand-intent.py "<user phrase>"` and follow the expanded prompt, load list, avoid list, and run order. If the script is not available, use `context/intent-aliases.md` as the manual fallback.

Respect project or organization overrides in `.tailtrail/intent-overrides.json` or `tailtrail/intent-overrides.json` when present.

Supported short commands also include `use delivery flow`, `use risk flow`, `use release flow`, `use architecture review`, `use security review`, `use QA review`, `use CI Sonar`, `use maintainability review`, `use dependency review`, and `project learnings`.

## AIDLC

Use `AIDLC.md` for broad, risky, ambiguous, multi-team, regulated, or long-running work. Resume from `aidlc-docs/aidlc-state.md` when present.

Use only the active stage playbook from `aidlc/stages/`. Use `aidlc/stages/handoff.md` when transferring work to review, validation, operations, or another agent.

## Guardrails

Use only relevant sections from `GUARDRAILS.md` and only the relevant layer from `context/guardrail-layers.md`. Preserve exact code, diffs, configs, commands, dependency versions, IDs, paths, hashes, security rules, policy text, and logs being debugged. For non-trivial work, note files read, commands run, checks performed, assumptions, skipped areas, and residual risk.

## Response Style

Lead with the implementation result or review finding. Keep summaries short: changed, reused, skipped, validated, risk.
