# TailTrail For ChatGPT

Use this file when ChatGPT is working with this repository or when these instructions are uploaded as project context.

## Operating Mode

TailTrail prefers small, grounded, reuse-first changes.

## Adapter Contract

- Use a Navigator-first workflow for non-trivial tasks: understand the goal, identify likely files and TailTrail features, then ask for approval before implementation.
- **Planning Lock:** when the user says `tailtrail start`, `TailTrail Start`, or asks for a Navigator plan, return planning only even if the same prompt says implement, set up, create, replicate, or do similar. If this host can run project commands, execute `tailtrail start "<goal>"` and return its complete Start Report with run ID. If the local TailTrail MCP server is configured, call the single `tailtrail_start` tool with `approved: true`; do not split the lock and report into separate calls. If neither capability is available, clearly say the plan is not persisted and provide the exact command. Do not edit files, run project commands, scanners, Terraform, or Git mutations after planning; require a separate approval before implementation.
- **Exact Start trigger:** treat `tailtrail start,`, `tailtrail start:`, and `tailtrail start -` as the same command. A `hands-free` or `end-to-end` request means comprehensive requirement and phase planning first, never immediate execution. Return the run ID, selected Program Delivery Harness, proposed feature order, active first slice, and explicit approval gate.
- **Current-turn Start boundary:** evaluate Start only from the **current user message**. A prior chat mention, pasted **error output**, log, stack trace, or follow-up debugging request is not a Start invocation and must not create a **new Planning Lock**. Reuse an awaiting-approval run ID when requesting approval; continue an approved in-scope run without another Start approval. With no active run and no explicit Start invocation in the current user message, use ordinary TailTrail guidance or advisory `guide` routing.
- **Start response boundary:** after a successful TailTrail Start tool or CLI invocation, return its complete Start Report verbatim and stop. Do not append an implementation plan, steps, analysis, or guidance.
- After code changes, recommend post-change review against both code health and requirement fulfillment.
- Require scanner approval before running Sonar, vulnerability, audit, build, broad test, or other heavy local commands.
- Treat learnings as advisory; current source, tests, CI, scanners, policy, guardrails, and explicit user direction always win.
- Keep token-saving claims estimated unless measured telemetry is provided.
- Label evidence clearly when using graph or scanner metadata: heuristic, local-ast, provider-backed, measured/validated.
- Follow `tailtrail-policy.md` when present and never use local policy to weaken TailTrail safety rules.

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

- Understand the request before proposing code.
- Read relevant source, callers, tests, and configuration before editing.
- Reuse existing helpers, conventions, types, components, error handling, and test style.
- Prefer standard library, platform-native features, framework capabilities, and installed dependencies.
- Use `DEPENDENCY-GATE.md` before suggesting a new package or service.
- Preserve security, validation, authorization, escaping, accessibility, data integrity, error handling, and explicit user requirements.
- Apply `GUARDRAILS.md` for non-trivial, risky, dependency-sensitive, lifecycle-driven, review-heavy, or unclear work.
- Use `context/guardrail-layers.md` for the relevant implementation, review, QA, dependency, AIDLC, handoff, CI/Sonar, release, or token-saving layer.
- Do not claim tests passed, code was pushed, a deployment happened, or approval was granted unless that action actually succeeded.
- If `tailtrail-policy.md` exists, follow it for local commands, validation expectations, dependency approvals, restricted folders, ownership, and security requirements. Treat `tailtrail-policy.example.md` as a template only.

## Context Discipline

Apply Token Autopilot automatically:

- Skip routing for tiny low-risk requests.
- Route non-trivial, broad, risky, noisy, review, dependency, AIDLC, or handoff work to one slice.
- Use `context/TailTrail.map.md` only when routing is useful.
- Keep exact text for code, diffs, configs, commands, dependency versions, paths, IDs, hashes, logs needed for diagnosis, and security rules.

Use `AIDLC.md` for larger lifecycle work. Use `aidlc/stages/handoff.md` when work needs to move to another person, model, reviewer, or operations owner.

Use only relevant sections from `GUARDRAILS.md` and only the relevant layer from `context/guardrail-layers.md`. Preserve exact code, diffs, configs, commands, dependency versions, IDs, paths, hashes, security rules, policy text, and logs being debugged.

## Short TailTrail Commands

When the user says `hello tailtrail`, `tailtrail hello`, `use TailTrail`, `use review`, `use dependency gate`, `use AIDLC`, `use AIDLC and review`, `review then AIDLC`, `use handoff`, or `save tokens`, resolve the command before answering.

For `hello tailtrail`, `hello TailTrail`, `hello taitrail`, or `tailtrail hello`, run `tailtrail hello` when the launcher is installed, otherwise run `python3 scripts/tailtrail.py hello`. Show the command output; do not replace it with a conversational greeting.

If `scripts/expand-intent.py` is available, use it as the backend intent agent. If not, use `context/intent-aliases.md` and apply the matching flow manually.

Respect prompt overrides in `.tailtrail/intent-overrides.json` or `tailtrail/intent-overrides.json` when present.

Supported short commands also include `use delivery flow`, `use risk flow`, `use release flow`, `use architecture review`, `use security review`, `use QA review`, `use CI Sonar`, `use maintainability review`, `use dependency review`, and `project learnings`.

## Output

Be concise. Say what changed, what was reused, what was intentionally skipped, what validation ran, what evidence supports non-trivial work, and what risk remains.
