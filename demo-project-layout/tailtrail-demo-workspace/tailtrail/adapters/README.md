# TailTrail Adapters

TailTrail is Codex-first, but the core workflow is portable. This folder contains source adapter files for common AI coding tools.

Run:

```bash
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

## Rules

- Keep adapters short.
- Keep TailTrail-owned wording original.
- Link to canonical files instead of duplicating long guidance.
- Use `context/TailTrail.map.md` before loading multiple TailTrail docs.
- Keep code, diffs, configs, commands, dependency versions, paths, IDs, hashes, and security rules exact.
