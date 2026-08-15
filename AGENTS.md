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

### Hello response boundary

For `hello tailtrail`, `hello TailTrail`, `hello taitrail`, or `tailtrail hello`,
return the actual ASCII TailTrail banner and installation result **verbatim as
the complete response**. Do not preface it with narration, summarize it, add a
todo/status update, omit the banner, or suggest `doctor` after it. If the command
fails, return its actual error output verbatim instead.

`tailtrail start` is a Planning Lock command. It always returns planning only, even when the same prompt says implement, set up, create, replicate, or do similar. When this host can execute project commands, run `tailtrail start "<goal>"` and return its complete Start Report with run ID; when the local TailTrail MCP server is configured, call the single `tailtrail_start` tool with `approved: true`, rather than splitting lock creation from plan rendering. After a successful Start tool or CLI invocation, the only assistant response is the exact Start Report stdout (starting `# TailTrail Start Plan` and including its run ID); copy the complete Start Report verbatim outside any collapsible terminal/tool-result panel, then stop. Before sending, verify it contains `Planning Lock`, `Scope`, `Requirements`, `Selected TailTrail features`, `Plan`, `Focused validation`, and `Approval`; the selected-features table is mandatory and may not be shortened, renamed, or replaced with `Next step`. If any section is missing, paste CLI stdout again rather than sending a partial summary. Never synthesize a substitute plan or task list, and never add `Steps`, `in-progress`, `Next I'll`, a request to proceed, implementation, test, documentation, branch, or PR work. If stdout cannot be copied, say only that the command report could not be copied; do not reconstruct it from the goal. If neither capability exists, say clearly that the plan is not persisted and provide the exact command. Do not edit files, run project commands/scanners/Terraform, or mutate Git after planning until the user separately approves the exact Planning Lock run ID.

For an explicit `tailtrail start ... --verbose` request, return the complete CLI verbose report verbatim. Before sending, verify it contains `Planning Lock`, `Start Here`, `Navigator Decision`, `Selected TailTrail features`, `Deferred TailTrail features`, `Guided delivery`, `Validation`, `Evidence posture`, and `Approval`. `Summary`, `Selected files`, and `Next step` are never substitutes for those sections; paste the CLI stdout again if any required verbose section is absent.

Treat `tailtrail start,`, `tailtrail start:`, and `tailtrail start -` as the same explicit command. A `hands-free` or `end-to-end` request requires a comprehensive Program Delivery plan—feature requirements, dependency order, first active slice, and approval gate—before any execution.

### Current-turn Start boundary

Evaluate TailTrail Start only from the **current user message**. A prior chat
mention, pasted **error output**, log, stack trace, or follow-up debugging
request is not a new Start invocation and must not create a **new Planning Lock**.
If an existing run is awaiting approval, identify and reuse that exact
run ID when asking for approval. If it is already approved, continue the
in-scope debugging work under that run without asking for Start approval again.
With no active run and no explicit Start invocation in the current user message,
use ordinary TailTrail guidance or advisory `guide` routing.

When the user rejects or declines an awaiting-approval TailTrail Start plan, do not inspect project source, offer source inspection, run project commands/tests/scanners, edit files, mutate Git, or create a new Planning Lock. Preserve the active run ID; read only its saved Planning Lock and Start report, then run `tailtrail planning feedback-template --run-id <active-run-id>`. Return its blank requirement-by-requirement feedback form; never invent a decision or rejection reason. The user may review each requirement, say `Reject all — <reason>`, or say `Use AIDLC Requirements mode`. Record these paths with `tailtrail planning feedback`, `tailtrail planning reject-all`, or `tailtrail planning aidlc-cycle` respectively. For AIDLC, return the complete `TailTrail AIDLC Requirements` report with the current boundary, focused questions, and next response format. On first material rejection, AIDLC is optional; on second material rejection, use AIDLC Requirements mode before another material proposal.

When a user answers an active AIDLC Requirements report, record every offered-choice answer through `tailtrail planning aidlc-cycle --run-id <active-run-id> --answers '<json>'` and return the revised boundary for a separate approval. On Windows native shells, prefer `--answers-base64 <base64-utf8-json>` so argument quoting cannot corrupt JSON. When the user approves that boundary, run `tailtrail planning aidlc-cycle --run-id <active-run-id> --approved`, return its Execution Handoff, and continue normal TailTrail implementation only under that same activated run and immutable AIDLC-derived anchor. Calling `aidlc-cycle` without a transition flag only starts or resumes the saved AIDLC brief; it records no duplicate gathering event. Do not create a new Start run or bypass this approval boundary.

### Activated-run closure boundary

When `tailtrail planning activate`, `planning_lock_approve`, or AIDLC activation returns an `execution_handoff`, retain that run's exact ID and obey its `closure.command`. Before any final response after a source edit, execute the command through the same resolved TailTrail CLI used for Start and return its stdout verbatim. A generic `Changes made`, `Validation`, or next-step narrative is never a valid TailTrail closure response. If closure evidence is missing, return the real `evidence-incomplete` Completion Report rather than inventing success.

For an approved active run, record only factual host-visible execution events as they occur: changed paths as `source-edit`, actual command outcomes as `command-result`, deterministic Harness artifacts as `harness-result`, and CI receipts as `ci-receipt`. Use `tailtrail execution-evidence record` or MCP `execution_evidence_record` with the exact run ID and requirement IDs. Never derive an event from a conversational claim. At closure, run `tailtrail closure finalize --root . --run-id <run-id>` before the Completion Report so selected Harnesses consume the saved evidence stream.

When an approved TailTrail plan selects a stale Code Graph Mapper cache because its metadata-only repository inventory changed, run the selected `tailtrail graph refresh --root <project-root>` command before relying on cached guidance. Do not refresh during Planning Lock. If Navigator discovered scope automatically, omit `--changed`; the mapper inventories relevant source, test, manifest, config, and IaC files, including untracked additions.

### Interactive Plan Mode host boundary

While a Planning Lock is awaiting approval, a user may ask why TailTrail chose
a file, requirement, feature, AIDLC mode, validation, drift posture, token
estimate, or approval boundary. Answer only from saved planning evidence using
`tailtrail planning explain` / `discuss`; keep the same run ID and do not start
implementation. A user may request a bounded saved-plan investigation only
through the approval-gated `planning investigate` flow, and may request a
material plan update only through `planning revise`. Use
`tailtrail planning decision-show --run-id <id>` to summarize saved discussion,
revision, and authority-routing state. AIDLC and Intent Bridge requirements
remain with their designated authority; never create a parallel local rewrite.
If the user explicitly asks to switch an awaiting Lite run to Standard AIDLC,
create only the versioned `planning aidlc-standard` proposal, require approval
of that exact revision, then begin Standard AIDLC requirements under the same
run. This mode approval never approves implementation; a separate AIDLC
requirements approval still applies. Refuse mode switches after activation,
from non-Lite modes, or for Intent Bridge source-owned requirements.
For any other optional TailTrail feature choice, use the single Expert Plan
Customization catalog (`planning feature-controls-show`) and its versioned
proposal/approval flow. Do not invent feature-specific approval paths; locked
core safeguards remain non-configurable.

Use named flows and review lenses when requested: `delivery flow`, `risk flow`, `release flow`, `architecture review`, `security review`, `QA review`, `maintainability review`, and `dependency review`. Capture durable project facts in `.tailtrail/learnings.md` only when they will help future agents avoid repeated discovery or repeated mistakes.

<!-- tailtrail-official-aidlc:codex:start -->
## Official AI-DLC Full-mode bridge (TailTrail managed)

This project has a pinned, integrity-verified official AI-DLC pack.
Apply its workflow only for an explicit TailTrail `--aidlc full` run with
an approved Full-mode bridge. Do not load it for TailTrail Lite, Standard,
or Off runs.

- Source: `https://github.com/awslabs/aidlc-workflows`
- Revision: `v1.0.1`
- Exact core rule: `.aidlc/aidlc-rules/aws-aidlc-rules/core-workflow.md`
- Rule details root: `.aidlc/aidlc-rules/aws-aidlc-rule-details`

For an active Full run, read the exact core rule before the relevant
official stage. Its detailed-rule paths resolve from the projected root
above. Host safety and the user request still take precedence; TailTrail
retains its approved-anchor, evidence, drift, recovery, and closure
controls. TailTrail stores only sanitized references to official artifacts.
<!-- tailtrail-official-aidlc:codex:end -->
