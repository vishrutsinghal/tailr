---
name: tailtrail-start
description: Use when the user explicitly asks TailTrail to handle a task, including natural requests such as "Use TailTrail to fix...", exact "tailtrail start" forms, hands-free, or end-to-end requests. Create or request one persisted Planning Lock and return the complete TailTrail Start Report before any implementation.
---

# TailTrail Start

## Core — follow exactly, do not skim

- Navigator-first workflow for non-trivial tasks; ask for approval before implementation. `tailtrail start` is planning-only: never implement, edit, run project/scanner/Terraform/Git commands after planning without a separate explicit `approve` (`looks good` / `go ahead` never approve). A `hands-free` or `end-to-end` request needs a full Program Delivery plan first, never immediate execution.
- MCP first (default path): if the TailTrail MCP server is configured, call the single `tailtrail_start` tool once with `approved: true` — one atomic call, nothing to retype. Do not split lock/report into separate calls. Else if this host can run project commands, resolve the launcher (`.tailtrail/install/payload/<host>/scripts/tailtrail.py`, then `tailtrail/scripts/tailtrail.py`, then `scripts/tailtrail.py`) and run `tailtrail start "<goal>"` (CLI fallback). Else state the plan is not persisted and give the exact command.
- Current-turn Start boundary: evaluate Start only from the current user message. A prior mention, pasted error output, log, stack trace, or follow-up is not a new Planning Lock. Reuse an awaiting-approval run ID; with no active run and no explicit Start, use guide routing.
- Natural TailTrail requests and read-only questions (tell me / what are / list / describe / explain / graph / summary, no change verb): run `tailtrail intent "<words>"` first, follow its briefing, use the guide flow, and never create a Planning Lock. `tailtrail intent resolve "<words>"` / MCP `intent_resolve` is read-only and grants no authority.
- Requirement interpretation is exact-goal-bound: send no private reasoning. Pass artifacts via `requirement_artifact` (SHA-256 bound) before scope; bind clauses with source IDs, keep quoted literals in `quoted`, build requirements from outcome / constraint / scope only, keep questions open. Missing or unreadable artifacts stop before scope and Planning Lock. Pass `--verbose` through (never inside the goal); on Windows prefer `--answers-base64` so quoting cannot corrupt JSON.
- Scope evidence v2 host boundary: consume the fingerprint plus owner / inspection / proof / excluded roles; never reclassify paths or promote unresolved scope. Scope work happens before Planning Lock persistence; unresolved Build scope creates no lock. A symptom-first request uses the same machinery for a Debug Start Plan (planning metadata only, no intake, reproduction, source, tests, or correction authority).
- Return the tool/CLI output as the complete Start Report verbatim (starts `# TailTrail Start Plan`, includes the run ID) outside any collapsible terminal/tool-result panel, then stop. Never synthesize a substitute plan or task list. Verify `Planning Lock`, `Scope`, `Requirements`, `Selected TailTrail features`, `Plan`, `Focused validation`, `Approval`; the selected-features table is mandatory — never replace it with `Next step`. Preserve fences, table pipes, backticks, spacing; never retype, normalize, or HTML-escape. If a section is missing, paste stdout again. If stdout cannot be copied, say only that; never reconstruct a plan from the goal. For official runs, never end the turn at the Start Report: generate and record questions, then return the Requirements report in the same turn.
- Before sending any Start, closure, or hello reply: verify the run ID, `text` fence, and required headings are all present; if anything is missing, paste the stdout again instead of sending a partial reply.
- `tailtrail stop` is the highest-priority control; `tailtrail resume --run-id <exact-run-id>` only reattaches (never approves or advances). Rejected plan: do not inspect source, tests, scanners, or Git and do not create a new run; return the `feedback-template` blank form for the same run ID (`AIDLC Requirements mode` on second material rejection). Record feedback with `tailtrail planning feedback`, `reject-all --reason`, or `aidlc-cycle`; answer AIDLC reports with `aidlc-cycle --answers '<json>'`, approve the boundary with `aidlc-cycle --approved`, and retain the Execution Handoff.
## Approved-run closure

- Retain `execution_handoff`, obey `closure.command`; never substitute a generic summary. Lite/Off `approved-plan-auto-grant` continues internally; Standard/Full and Intent Bridge show the defensive handoff. Close with `completion-report` plus `closure finalize`, returning stdout verbatim (never invent token use: measured only with linked host/provider telemetry).
- After changes: post-change review; scanner approval before heavy commands; learnings as advisory (source / tests / CI / scanners / policy / guardrails / user win); token claims estimated unless measured telemetry; label graph/scanner evidence heuristic, local-ast, provider-backed, measured/validated; follow `tailtrail-policy.md`, never weaken safety rules.
- Staleness check: when asked whether instructions are current, quote the `TailTrail instructions revision` line verbatim.

## Pointers — load on demand, never paste detail from memory

- Intent: `scripts/expand-intent.py` or `tailtrail intent ...`; fallback `context/intent-aliases.md` (+ `.tailtrail/intent-overrides.json`).
- Commands and flows: `TAILTRAIL-COMMANDS.md`; lifecycle: `AIDLC.md` + `aidlc-docs/aidlc-state.md`; bugs: `DEBUG-HARNESS.md`; risks: `GUARDRAILS.md` + `context/guardrail-layers.md`; deps: `DEPENDENCY-GATE.md`.
- Portable commands: quote for the host shell (POSIX single-quotes break `cmd.exe`; `list2cmdline` quoting on Windows); prefer `sys.executable -m ...` proofs that run on sh, cmd, and PowerShell.

---
_TailTrail instructions revision: `9dce4f402022` — quote this line if asked whether instructions are current._
