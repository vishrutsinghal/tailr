# TailTrail For GitHub Copilot

Use TailTrail for generated code, code review, implementation plans, dependency choices, and larger AI-assisted lifecycle work in this repository.

## Adapter Contract

- Use a Navigator-first workflow for non-trivial tasks: understand the goal, identify likely files and TailTrail features, then ask for approval before implementation.
- **TailTrail CLI resolution:** before saying TailTrail Start cannot run, resolve the project-local CLI in this order: `.tailtrail/install/payload/copilot/scripts/tailtrail.py` for the current transactional Copilot payload, `tailtrail/scripts/tailtrail.py` for a legacy installed pack, then `scripts/tailtrail.py` for a TailTrail source checkout. Never prefer the legacy pack when the Copilot payload exists. On Windows, invoke the first existing path with `py -3`, then `python`, then `python3`; on macOS/Linux, use `python3`. Do not search the repository for a different script or substitute a manual plan while a canonical path exists.
- **Planning Lock:** when the user says `tailtrail start`, `TailTrail Start`, or asks for a Navigator plan, return planning only even if the same prompt says implement, set up, create, replicate, or do similar. If the local TailTrail MCP server is configured, call the single `tailtrail_start` tool with `approved: true`; do not split the lock and report into separate calls. If this host can run project commands and the MCP tool is not available, execute `start "<goal>"` through the resolved TailTrail CLI. In both cases, **return the tool or CLI output verbatim and stop — do not append your own implementation plan, steps, analysis, or guidance after the Start Report.** If neither canonical CLI path exists and no MCP tool is configured, clearly say the plan is not persisted and provide the matching installation or source-checkout command. Do not edit files, run project commands, scanners, Terraform, or Git mutations after planning; require a separate approval before implementation.
- **Exact Start trigger:** treat `tailtrail start,`, `tailtrail start:`, and `tailtrail start -` as the same command. A `hands-free` or `end-to-end` request means comprehensive requirement and phase planning first, never immediate execution. Return the run ID, selected Program Delivery Harness, proposed feature order, active first slice, and explicit approval gate.
- **Current-turn Start boundary:** evaluate Start only from the **current user message**. A prior chat mention, pasted **error output**, log, stack trace, or follow-up debugging request is not a Start invocation and must not create a **new Planning Lock**. Reuse an awaiting-approval run ID when requesting approval; continue an approved in-scope run without another Start approval. With no active run and no explicit Start invocation in the current user message, use ordinary TailTrail guidance or advisory `guide` routing.
- **Start response boundary (strict):** after a successful TailTrail Start tool or CLI invocation, the **only** normal assistant message is the exact Start Report stdout (beginning `# TailTrail Start Plan` and containing the returned run ID). Copy the **complete Start Report verbatim** outside any collapsible terminal/tool-result panel, then stop. Before sending, verify the reply contains every required heading: `Planning Lock`, `Scope`, `Requirements`, `Selected TailTrail features`, `Plan`, `Focused validation`, and `Approval`. The selected-features table is mandatory; do not shorten, rename, or replace it with `Next step`. If any required section is missing, paste the CLI stdout again instead of sending a partial summary. Never synthesize a substitute plan or task list. In particular, do not emit headings or phrases such as `Steps`, `in-progress`, `Next I'll`, `shall I proceed`, `implement`, `run tests`, `update docs`, `create branch`, or `prepare PR`. If stdout cannot be read or copied, say only that the command report could not be copied; do not reconstruct it from the goal.
- **Official AIDLC exception:** for a Standard or Full run at `official-aidlc-host-generation-required`, read the pinned official Requirements Analysis and question-format rules plus the saved Question Orchestrator context. Generate only material official questions/options and include requirement IDs, decision class and impact, known context, evidence references, a TailTrail advisory recommendation, and evidence-grounded reasoning. Record the sanitized questions for the same run, then return its complete Official AI-DLC Requirements report. Never substitute local questions, present inventory hypotheses as confirmed source behavior, inspect source, or implement work at this stage.
- **Verbose Start response:** when the current Start request includes `--verbose`, return the full CLI verbose report verbatim. It must include `Planning Lock`, `Start Here`, `Navigator Decision`, `Selected TailTrail features`, `Deferred TailTrail features`, `Guided delivery`, `Validation`, `Evidence posture`, and `Approval`. A `Summary`, `Selected files`, or `Next step` may appear only in addition to—not instead of—those sections. Before sending, check every heading; if one is missing, paste the CLI stdout again. Do not compress the verbose report into a narrative or checklist.
- **Rejected Start plan (strict):** if the user rejects, declines, or does not approve an active awaiting-approval Start plan, do **not** inspect project files, offer inspection, run tests/scanners, edit source, run Git, or create another Start run. Read only the saved Planning Lock and Start report, then run `tailtrail planning feedback-template --run-id <active-run-id>` and return its blank `TailTrail Plan Feedback` form. Never invent a rejection decision or comment. The user may: (1) review every requirement with `approve` or `reject — <reason>` and record it with `tailtrail planning feedback`; (2) say `Reject all — <reason>`, then run `tailtrail planning reject-all --run-id <active-run-id> --reason "<reason>"`; or (3) say `Use AIDLC Requirements mode`, then run `tailtrail planning aidlc-cycle --run-id <active-run-id>` and return its complete `TailTrail AIDLC Requirements` report. That report must include the current requirement boundary, focused questions, and the next response format. On the first material rejection, AIDLC is optional; on the second, it is required before another material proposal. Keep the same run ID and preserve prior planning evidence.
- **Batched AIDLC control plane:** use `tailtrail planning aidlc-cycle --run-id <active-run-id>` to start or resume an AIDLC Requirements report, `tailtrail planning aidlc-cycle --run-id <active-run-id> --answers '<json>'` to record every offered-choice answer (and `detail` for `Other`) and return the complete revised boundary, and `tailtrail planning aidlc-cycle --run-id <active-run-id> --approved` only when the user approves that boundary. On Windows native shells, use `--answers-base64 <base64-utf8-json>` instead of `--answers` so argument quoting cannot strip JSON quotes. The command writes only TailTrail planning artifacts until the explicit `--approved` activation. It preserves the same run ID and never duplicates a resumed gathering event. After activation, return the Execution Handoff and begin normal TailTrail implementation only under that same approved AIDLC anchor.
- **Graph cache freshness:** a Start plan may mark the reusable Code Graph Mapper cache stale when its metadata-only repository inventory detects added, removed, renamed, or changed relevant files. Do not refresh it during Planning Lock. Once the plan is approved, run the selected `tailtrail graph refresh --root <project-root>` command before relying on cached graph guidance; omit `--changed` when TailTrail discovered scope automatically. The user never needs to list newly added or untracked files.
- **Closure response (strict):** after implementation of an approved active run and its selected review/validation steps, run `tailtrail completion-report --root . --run-id <active-run-id>` and return its complete stdout. Do not replace it with a generic “what I changed” summary or invent test, token, drift, or learning claims. The report separates requirement delivery from TailTrail controls and shows actual model tokens only when host/provider telemetry is explicitly linked to that run ID.
- **Activated-run handoff (strict):** when `planning_lock_approve` or `tailtrail planning activate` returns `execution_handoff`, retain its exact run ID and obey `closure.command`. Before any final response after a source edit, execute that command through the same resolved TailTrail CLI used for Start and return its stdout verbatim. A `Changes made`, `Validation`, or next-steps narrative is never an alternative closure response.
- **Execution evidence (strict):** for an approved active run, record only host-visible facts as they occur: changed paths as `source-edit`, actual command outcomes as `command-result`, deterministic Harness artifacts as `harness-result`, and linked CI outcomes as `ci-receipt`. Use `tailtrail execution-evidence record` or MCP `execution_evidence_record` with the same run ID and approved requirement IDs. Never create evidence from a chat summary. Before the final Completion Report, run `tailtrail closure finalize --root . --run-id <active-run-id>` so selected Harnesses consume the saved stream.
- After code changes, recommend post-change review against both code health and requirement fulfillment.
- Require scanner approval before running Sonar, vulnerability, audit, build, broad test, or other heavy local commands.
- Treat learnings as advisory; current source, tests, CI, scanners, policy, guardrails, and explicit user direction always win.
- Keep token-saving claims estimated unless measured telemetry is provided.
- Label evidence clearly when using graph or scanner metadata: heuristic, local-ast, provider-backed, measured/validated.
- Follow `tailtrail-policy.md` when present and never use local policy to weaken TailTrail safety rules.

## Interactive Plan Mode

For an awaiting-approval run, users may ask why a file, requirement, selected
TailTrail feature, AIDLC mode, validation path, drift posture, token estimate,
or approval boundary was chosen. Keep the **same run ID**, answer from saved
planning evidence only, and do not inspect source or start implementation.

- Use `tailtrail planning explain` or `discuss` for an evidence-labelled answer.
- Use `planning investigate` only after explicit read-only approval and only on
  saved planned paths.
- Use `planning revise` only for a material update; it creates a versioned
  proposal which requires separate approval.
- Use `planning decision-show` for the compact lock/discussion/revision/AIDLC or
  Intent Bridge authority summary.
- For a numbered AIDLC question such as `Q5`, use `tailtrail planning
  aidlc-question clarify --run-id <id> --question-id Q5` before explaining or
  plainly rephrasing it. This is read-only and does not change the plan. If the
  user challenges correctness, create a sanitized `aidlc-question challenge`,
  have the active AIDLC authority generate a complete replacement, record it,
  show it, and require explicit `aidlc-question approve`. Standard/Full
  replacements must follow the pinned official AIDLC Requirements rules; never
  present a local substitute as official.
- If the user asks to switch an awaiting Lite run to Standard AIDLC, create the
  versioned `planning aidlc-standard` proposal, require approval of that exact
  revision, then begin Standard AIDLC requirements under the same run. This is
  not implementation approval; requirements still require their own approval.
- For any other feature choice, use the single `planning feature-controls-show`
  catalog and its versioned proposal/approval flow; do not invent per-feature
  switches or disable locked safeguards.
- Never treat a why-question or plan-update request as implementation approval.

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

For `hello tailtrail`, `hello TailTrail`, `hello taitrail`, or `tailtrail hello`, run `tailtrail hello` when the launcher is installed, otherwise run `python3 scripts/tailtrail.py hello`. Return the ASCII TailTrail banner and installation result **verbatim as the complete response**; do not preface it with narration, summarize it, add a todo/status update, omit the banner, or suggest `doctor` after it. If the command fails, return its actual error output verbatim instead.

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
