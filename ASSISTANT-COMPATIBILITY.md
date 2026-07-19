# TailTrail Assistant Compatibility

TailTrail is Codex-first. Other assistants are supported through portable instruction adapters, and behavior depends on how each assistant loads and follows project instructions.

## Support Matrix

| Assistant | Support Level | Best Use | Main Limitation |
|---|---:|---|---|
| Codex | Strong | Full local workflow, scripts, skills, Navigator, review, graphing, guardrails, tests, and repo edits. | Best-supported path because TailTrail is designed around Codex-local workflows. |
| Claude | Good | Planning, implementation guidance, review, lifecycle notes, and instruction-following in repos with `CLAUDE.md`. | No native TailTrail skill execution; command execution depends on the user's local setup. |
| Cursor | Good | Repo-local coding rules, small implementation work, refactors, and review prompts through `.cursor/rules/tailtrail.mdc`. | Depends on Cursor rule loading and workspace configuration. |
| GitHub Copilot | Medium | Inline coding guidance, dependency discipline, and lightweight review through `.github/copilot-instructions.md`. | May not consistently invoke a full Navigator-style workflow without user prompting. |
| ChatGPT | Medium | Planning, review, explanation, and portable guidance through `.openai/chatgpt-instructions.md`. | Local command execution and repo access depend on the user's ChatGPT environment. |
| Gemini | Medium | General implementation guidance, review, and handoff through `GEMINI.md`. | Behavior depends on Gemini project-instruction support and local tool access. |

## Validated Adapter Contract

Every TailTrail assistant adapter must include the same minimum behavior:

- Navigator-first workflow for non-trivial tasks.
- Approval before implementation.
- Post-change review after code changes.
- Scanner approval before Sonar, vulnerability, audit, build, broad test, or heavy local commands.
- Learnings are advisory and never override current source, CI, scanners, policy, guardrails, or explicit user direction.
- Token-saving claims stay estimated unless measured telemetry is provided.
- Evidence labels are explicit: heuristic, local-ast, provider-backed, measured/validated.
- `tailtrail-policy.md` is respected when present without weakening safety rules.

Run:

```bash
python3 scripts/tailtrail.py adapters check
python3 scripts/sync-adapters.py --check
```

## Prompt Packs

Assistant-specific prompt packs live under `adapters/prompts/`.

Use them when a user wants short prompts instead of remembering command syntax:

```text
Use TailTrail Navigator for this task. Show the plan only first.
```

Each prompt pack includes:

- first-task prompt
- implementation prompt
- review prompt
- AIDLC prompt
- scanner-safe prompt
- token-saving prompt
- handoff prompt

## Claim Boundary

TailTrail can claim validated adapter coverage only for the instruction files and local checks in this repository. It should not claim identical behavior across assistants unless measured by assistant-specific evaluation runs.

