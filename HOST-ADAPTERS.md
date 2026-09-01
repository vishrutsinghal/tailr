# TailTrail Host Adapter Contract

Phase E4 gives Codex, GitHub Copilot, and Claude the same versioned repository
adapter contract over the E3 transactional installer. The machine-readable
authority is `adapters/host-compatibility-v1.json`; its closed schema is
`schemas/host-adapter-contract.schema.json`.

Validation: `python3 scripts/tailtrail.py adapters conformance` checks the
versioned local composition contract; real-host and support evidence remain the
separate gates below.

## Qualification truth

Each E4 adapter is `contract-tested`: local tests cover its exact Core files,
instruction composition, first action, diagnostics, update, repair, rollback,
uninstall, migration, conflict handling, and receipt preparation. This does not
mean `runtime-observed` or `supported`.

- `runtime-observed` requires six fresh, sanitized, canonical-run-linked
  receipts for one exact host version.
- `supported` additionally requires the E5 platform matrix and E10 real-host
  release matrix. E4 declares no supported host versions.
- A missing executable is `not-detected`, not a failure of installed adapter
  integrity. Copilot versions are host-reported because IDE and service
  versions cannot be inferred safely from a repository.

## Exact Core surfaces

| Host | Managed Core files | First action |
| --- | --- | --- |
| Codex | `AGENTS.md`, `.codex-plugin/plugin.json`, and the `tailtrail`, `tailtrail-review`, and `tailtrail-start` skills | `tailtrail start "<your task>"` in Codex chat |
| GitHub Copilot | `.github/copilot-instructions.md`, `.github/prompts/tailtrail-start.prompt.md` | `/tailtrail-start <your task>` in Copilot Chat |
| Claude | `CLAUDE.md`, `.claude/commands/tailtrail-start.md` | `/tailtrail-start <your task>` in Claude Code |

Core is the default. Extended adds one complete versioned runtime under
`.tailtrail/install/payload/common/<version>/` and a small compatible launcher
under `.tailtrail/install/payload/<host>/` without changing the host-native
entry surface.

Every contract includes mandatory reload guidance. Codex starts a new task,
Copilot starts a new chat, and Claude starts a new Code session; each contract
also defines the stronger restart fallback when the first refresh is stale.

## Composition and enforcement

The fixed precedence is host safety, user request, verified official AI-DLC
stage rules, then TailTrail assurance rules. `doctor` checks ownership hashes,
the exact Core manifest, adapter version, required host files, and host-specific
composition markers from the installed target.

Host instruction loading and workflow invocation are host-assisted. CI remains
authoritative for enforceable repository policy, especially for Copilot where
instruction loading cannot guarantee a full workflow invocation. Global host
settings, network activity, and account changes are never part of install or
doctor; all remain separately approval-required.

## Lifecycle

```text
tailtrail install --host <codex|copilot|claude> --profile core --target .
tailtrail setup --host <codex|copilot|claude> --profile core --target .
tailtrail verify --host <host> --target .
tailtrail doctor --host <host> --target . --format json
tailtrail update --host <host> --target .
tailtrail rollback --to <transaction-id> --target .
tailtrail uninstall --host <host> --target .
```

Adapter metadata migrations use the same E3 staging, ownership, backup,
automatic restoration, and rollback path as file updates. Modified or unrelated
user files are preserved unless the user explicitly selects the existing
`--force` backup path.

## Portable runtime receipts

Prepare an immutable six-scenario bundle without claiming it ran:

```text
tailtrail adapters runtime prepare --host <host> --root .
```

Recording remains separate. Receipts contain sanitized observations and local
artifact references; they cannot replace canonical state or turn missing,
failed, stale, or incompatible evidence into success.

`tailtrail qualify report` is the single support gate. It requires instruction
conformance, six current real-host receipts for every selected host, the exact
hosted OS/Python matrix report, and an observed identity-verified publication
receipt. The aggregate verifies GitHub attestations for the report, wheel, and
publication receipt. Any missing input is `evidence-incomplete` with a nonzero
exit.

## E4/E5/E10 boundary

E4 qualifies adapter contracts on the current local development platform. E5
owns Windows, macOS, Linux, Python, artifact, path, and permission matrices.
E10 owns real executions in named host versions. Neither is implied by E4.
