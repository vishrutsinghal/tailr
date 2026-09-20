# TailTrail For Claude

Use TailTrail as the project workflow for local development.

## Core — follow exactly, do not skim

- Navigator-first workflow for non-trivial tasks; ask for approval before implementation. `tailtrail start` is planning-only: never implement, edit, run project/scanner/Terraform/Git commands after planning without a separate explicit `approve` (`looks good` / `go ahead` never approve).
- MCP first (default path): if the TailTrail MCP server is configured, call the single `tailtrail_start` tool once with `approved: true` — one atomic call, do not split lock/report, nothing to retype. Else if this host can run project commands, run `tailtrail start "<goal>"` (CLI fallback). Else state the plan is not persisted and give the exact command. Return the tool/CLI output as the complete Start Report verbatim (starts `# TailTrail Start Plan`, includes the run ID) outside any collapsible terminal/tool-result panel, then stop. Never synthesize a substitute plan or task list. Verify `Planning Lock`, `Scope`, `Requirements`, `Selected TailTrail features`, `Plan`, `Focused validation`, `Approval`; the selected-features table is mandatory — never replace it with `Next step`. Preserve fences, table pipes, backticks, spacing; never retype, normalize, or HTML-escape. If a section is missing, paste stdout again. For official runs, never end the turn at the Start Report: generate and record questions, then return the Requirements report in the same turn.
- Current-turn Start boundary: evaluate Start only from the current user message. A prior mention, pasted error output, log, stack trace, or follow-up is not a new Planning Lock. Reuse an awaiting-approval run ID; with no active run and no explicit Start, use guide routing.
- Natural TailTrail requests and read-only questions (tell me / what are / list / describe / explain / graph / summary, no change verb): run `tailtrail intent "<words>"` first, follow its briefing, use the guide flow, and never create a Planning Lock. `tailtrail intent resolve "<words>"` / MCP `intent_resolve` is read-only and grants no authority.
- Requirement interpretation is exact-goal-bound: send no private reasoning. Pass artifacts via `requirement_artifact` (SHA-256 bound) before scope; bind clauses with source IDs, keep quoted literals in `quoted`, build requirements from outcome / constraint / scope only, keep questions open. Missing or unreadable artifacts stop before scope and Planning Lock.
- Scope evidence v2 host boundary: consume the fingerprint plus owner / inspection / proof / excluded roles; never reclassify paths or promote unresolved scope. Scope work happens before Planning Lock persistence; unresolved Build scope creates no lock.
- `tailtrail stop` is the highest-priority control; `tailtrail resume --run-id <exact-run-id>` only reattaches (never approves or advances). Rejected plan: do not inspect source, tests, scanners, or Git and do not create a new run; return the `feedback-template` blank form for the same run ID (`AIDLC Requirements mode` on second material rejection).
- Activated run: retain `execution_handoff`, obey `closure.command`; never substitute a generic summary. Lite/Off `approved-plan-auto-grant` continues internally; Standard/Full and Intent Bridge show the defensive handoff. Close with `completion-report` plus `closure finalize`, returning stdout verbatim.
- `hello tailtrail` variants: run `tailtrail hello`, return the ASCII banner plus result verbatim as the complete response, preserve the `text` fence, no narration.
- Staleness check: when asked whether instructions are current, quote the `TailTrail instructions revision` line verbatim.
- After changes: post-change review; scanner approval before heavy commands; learnings as advisory (source / tests / CI / scanners / policy / guardrails / user win); token claims estimated unless measured telemetry; label graph/scanner evidence heuristic, local-ast, provider-backed, measured/validated; follow `tailtrail-policy.md`, never weaken safety rules.

## Pointers — load on demand, never paste detail from memory

- Intent: `scripts/expand-intent.py` or `tailtrail intent ...`; fallback `context/intent-aliases.md` (+ `.tailtrail/intent-overrides.json`).
- Commands and flows: `TAILTRAIL-COMMANDS.md`; lifecycle: `AIDLC.md` + `aidlc-docs/aidlc-state.md`; bugs: `DEBUG-HARNESS.md`; risks: `GUARDRAILS.md` + `context/guardrail-layers.md`; deps: `DEPENDENCY-GATE.md`.

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

---
_TailTrail instructions revision: `537aff1de58f` — quote this line if asked whether instructions are current._
