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

## Trail Check

Before proposing or editing code: confirm the change is needed; inspect the files, callers, tests, and data flow it touches; reuse existing helpers, types, components, and conventions; prefer standard library, platform-native behavior, and installed dependencies; avoid new dependencies unless `DEPENDENCY-GATE.md` approves; choose the smallest maintainable diff; preserve validation, authorization, escaping, accessibility, and explicit requirements. For broad or noisy tasks, pick one slice via `context/Tailtrail.map.md` instead of loading every doc.

For an explicit Navigator request, keep the response at the requested depth instead of turning `implementation` into a generic task keyword. Navigator is advisory and deterministic: likely path, impacted files, context to load and avoid, suggested commands, approval questions. Do not run scanners, builds, or learning capture without explicit approval.

## Core — follow exactly, do not skim

- Navigator-first workflow for non-trivial tasks; ask for approval before implementation. `tailtrail start` is planning-only: never implement, edit, run project/scanner/Terraform/Git commands after planning without a separate explicit `approve` (`looks good` / `go ahead` never approve).
- MCP first (default path): if the TailTrail MCP server is configured, call the single `tailtrail_start` tool once with `approved: true` — one atomic call, do not split lock/report, nothing to retype. Else if this host can run project commands, run `tailtrail start "<goal>"` (CLI fallback). Else state the plan is not persisted and give the exact command. Return the tool/CLI output as the complete Start Report verbatim (starts `# TailTrail Start Plan`, includes the run ID) outside any collapsible terminal/tool-result panel, then stop. Never synthesize a substitute plan or task list. Verify `Planning Lock`, `Scope`, `Requirements`, `Selected TailTrail features`, `Plan`, `Focused validation`, `Approval`; the selected-features table is mandatory — never replace it with `Next step`. If a section is missing, paste stdout again. For official runs, never end the turn at the Start Report: generate and record questions, then return the Requirements report in the same turn.
- Before sending any Start, closure, or hello reply: verify the run ID, `text` fence, and required headings are all present; if anything is missing, paste the stdout again instead of sending a partial reply.
- Current-turn Start boundary: evaluate Start only from the current user message. A prior mention, pasted error output, log, stack trace, or follow-up is not a new Planning Lock. Reuse an awaiting-approval run ID; with no active run and no explicit Start, use guide routing.
- Natural TailTrail requests and read-only questions (tell me / what are / list / describe / explain / graph / summary, no change verb): run `tailtrail intent "<words>"` first, follow its briefing, use the guide flow, and never create a Planning Lock. `tailtrail intent resolve "<words>"` / MCP `intent_resolve` is read-only and grants no authority.
- Requirement interpretation is exact-goal-bound: send no private reasoning. Pass artifacts via `requirement_artifact` (SHA-256 bound) before scope; bind clauses with source IDs, keep quoted literals in `quoted`, build requirements from outcome / constraint / scope only, keep questions open. Missing or unreadable artifacts stop before scope and Planning Lock.
- Scope evidence v2 host boundary: consume the fingerprint plus owner / inspection / proof / excluded roles; never reclassify paths or promote unresolved scope. Scope work happens before Planning Lock persistence; unresolved Build scope creates no lock.
- `tailtrail stop` is the highest-priority control; `tailtrail resume --run-id <exact-run-id>` only reattaches (never approves or advances). Rejected plan: do not inspect source, tests, scanners, or Git and do not create a new run; return the `feedback-template` blank form for the same run ID (`AIDLC Requirements mode` on second material rejection).
- Activated run: retain `execution_handoff`, obey `closure.command`; never substitute a generic summary. Lite/Off `approved-plan-auto-grant` continues internally; Standard/Full and Intent Bridge show the defensive handoff. Close with `completion-report` plus `closure finalize`, returning stdout verbatim.
- `hello tailtrail` variants: run `tailtrail hello`, return the ASCII TailTrail banner plus result verbatim as the complete response, preserve the command-emitted `text` fence, no narration, no todo/status update, never suggest `doctor` after it.
- After changes: post-change review; scanner approval before heavy commands; learnings as advisory (source / tests / CI / scanners / policy / guardrails / user win); token claims estimated unless measured telemetry; label graph/scanner evidence heuristic, local-ast, provider-backed, measured/validated; follow `tailtrail-policy.md`, never weaken safety rules.
- Staleness check: when asked whether instructions are current, quote the `TailTrail instructions revision` line verbatim.

## Pointers — load on demand, never paste detail from memory

- Intent: `scripts/expand-intent.py` or `tailtrail intent ...`; fallback `context/intent-aliases.md` (+ `.tailtrail/intent-overrides.json`).
- Commands and flows: `TAILTRAIL-COMMANDS.md`; lifecycle: `AIDLC.md` + `aidlc-docs/aidlc-state.md`; bugs: `DEBUG-HARNESS.md`; risks: `GUARDRAILS.md` + `context/guardrail-layers.md`; deps: `DEPENDENCY-GATE.md`.
- Portable commands: quote for the host shell (POSIX single-quotes break `cmd.exe`; `list2cmdline` quoting on Windows); prefer `sys.executable -m ...` proofs that run on sh, cmd, and PowerShell.

---
_TailTrail instructions revision: `265b0eb4e59a` — quote this line if asked whether instructions are current._
