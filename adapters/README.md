# TailTrail Adapters

TailTrail is Codex-first, but the core workflow is portable. This folder contains source adapter files for common AI coding tools.

For support levels and limitations, see `ASSISTANT-COMPATIBILITY.md`.

Run:

```bash
python3 scripts/tailtrail.py adapters check
python3 scripts/tailtrail.py adapters sync
python3 scripts/sync-adapters.py --check
python3 scripts/sync-adapters.py --write
```

## Adapter Targets

| Tool | Source | Target |
|---|---|---|
| Claude | `adapters/claude.md` | `CLAUDE.md` |
| Cursor | `adapters/cursor.mdc` | `.cursor/rules/tailtrail.mdc` |
| GitHub Copilot | `adapters/copilot-instructions.md` | `.github/copilot-instructions.md` |
| ChatGPT | `adapters/chatgpt-instructions.md` | `.openai/chatgpt-instructions.md` |
| Gemini | `adapters/gemini.md` | `GEMINI.md` |

## Prompt Packs

Short prompt packs live in `adapters/prompts/`.

| Tool | Prompt Pack |
|---|---|
| Codex | `adapters/prompts/codex.md` |
| Claude | `adapters/prompts/claude.md` |
| Cursor | `adapters/prompts/cursor.md` |
| GitHub Copilot | `adapters/prompts/copilot.md` |
| ChatGPT | `adapters/prompts/chatgpt.md` |
| Gemini | `adapters/prompts/gemini.md` |

## Rules

- Keep adapters short.
- Keep TailTrail-owned wording original.
- Link to canonical files instead of duplicating long guidance.
- Use `context/TailTrail.map.md` before loading multiple TailTrail docs.
- Keep code, diffs, configs, commands, dependency versions, paths, IDs, hashes, and security rules exact.
- Keep the adapter contract phrases present. `tailtrail adapters check` validates Navigator-first, approval, review, scanner approval, advisory learnings, token-claim boundaries, evidence labels, and local policy behavior.
