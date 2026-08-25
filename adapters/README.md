# TailTrail Adapters

TailTrail is Codex-first, but the core workflow is portable. This folder contains source adapter files for common AI coding tools.

For support levels and limitations, see `ASSISTANT-COMPATIBILITY.md`.

Run:

```bash
python3 scripts/tailtrail.py adapters check
python3 scripts/tailtrail.py adapters sync
python3 scripts/sync-adapters.py --check
python3 scripts/sync-adapters.py --write
python3 scripts/tailtrail.py adapters conformance
python3 scripts/tailtrail.py adapters runtime prepare --host codex
python3 scripts/tailtrail.py adapters runtime report
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

## Composed host surfaces

`host-compatibility-v1.json` is the versioned compatibility matrix for Codex,
GitHub Copilot, and Claude. Generate or verify their composed instruction
surfaces with:

```bash
python3 scripts/host-adapter-conformance.py --write
python3 scripts/host-adapter-conformance.py
```

The fixed precedence is host safety, user request, official AI-DLC stage rules,
then TailTrail assurance rules. The conformance scenarios cover a small bug,
hands-free feature, rejected requirement, evidence failure, recovery, and CI
wait. This verifies local composition, not identical runtime behavior by hosts.

## Real-host runtime conformance

E4 prepares `runtime-scenarios-v1.json` and sanitized receipts; E10 evaluates the
same six observable scenarios in Codex, Copilot, and Claude. Prepare a portable
host bundle, run the scenarios in that host, then record one receipt per
scenario:

```bash
python3 scripts/tailtrail.py adapters runtime prepare --host codex
python3 scripts/tailtrail.py adapters runtime record --host codex --receipt path/to/receipt.json
python3 scripts/tailtrail.py adapters runtime report --host codex
```

Instruction conformance and runtime conformance are reported separately. A host
is `passed` only when all six current scenarios have fresh, canonical-run-linked
passing evidence. Missing receipts are `not-validated`; stale contracts,
incompatible adapters, and observed failures retain distinct statuses. The
bundle and receipt surfaces contain references and observations, not source,
prompts, secrets, or fabricated host results.

## Rules

- Keep adapters short.
- Keep TailTrail-owned wording original.
- Link to canonical files instead of duplicating long guidance.
- Use `context/TailTrail.map.md` before loading multiple TailTrail docs.
- Keep code, diffs, configs, commands, dependency versions, paths, IDs, hashes, and security rules exact.
- Keep the adapter contract phrases present. `tailtrail adapters check` validates Navigator-first, approval, review, scanner approval, advisory learnings, token-claim boundaries, evidence labels, and local policy behavior.
