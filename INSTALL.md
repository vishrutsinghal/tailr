# Install TailTrail

This is the canonical installation, update, and verification guide. Run the
commands from a TailTrail source checkout, and replace the target path with the
project TailTrail should guide.

## Pick one host profile

| Host | Windows | macOS / Linux |
| --- | --- | --- |
| Codex | `py -3 scripts\tailtrail.py install codex-plugin --target "D:\path\to\project"` | `python3 scripts/tailtrail.py install codex-plugin --target "/absolute/path/to/project"` |
| GitHub Copilot | `py -3 scripts\tailtrail.py install local --target "D:\path\to\project" --profile copilot` | `python3 scripts/tailtrail.py install local --target "/absolute/path/to/project" --profile copilot` |
| Claude | `py -3 scripts\tailtrail.py install local --target "D:\path\to\project" --profile claude` | `python3 scripts/tailtrail.py install local --target "/absolute/path/to/project" --profile claude` |

On Windows, use `py -3`; do not use a bare `python`, which can resolve to the
Microsoft Store alias instead of a real Python runtime.

After installation, open the target project in the host and start a **new
chat**. The new chat loads the installed TailTrail instructions.

## Verify

Use one read-only command from the TailTrail checkout:

```powershell
py -3 scripts\tailtrail.py install verify --target "D:\path\to\project"
```

```bash
python3 scripts/tailtrail.py install verify --target "/absolute/path/to/project"
```

It checks the installed guidance and runs TailTrail's local `hello` smoke
check. It does not alter the target project, run project tests, or invoke an
agent.

## Update an existing install

### GitHub Copilot

Preview first, then update. The updater preserves changed managed files unless
you explicitly choose a replacement strategy.

```powershell
py -3 scripts\update-tailtrail.py --root "D:\path\to\project" --dry-run
py -3 scripts\update-tailtrail.py --root "D:\path\to\project"
```

To make recoverable backups and replace TailTrail-managed files:

```powershell
py -3 scripts\update-tailtrail.py --root "D:\path\to\project" --strategy backup-overwrite
```

### Codex and Claude

Use the original installer with a dry run, then `--force` only after reviewing
or committing local changes to TailTrail-managed files:

```bash
python3 scripts/tailtrail.py install codex-plugin --target "/absolute/path/to/project" --dry-run
python3 scripts/tailtrail.py install codex-plugin --target "/absolute/path/to/project" --force
```

For Claude, replace `codex-plugin` with `local --profile claude`.

`--force` refreshes TailTrail-managed guidance and skills; it does not update
your application source code.

## Optional surfaces

Managed packs support:

- `--surface core` — small first-run pack with Start, Navigator, guardrails,
  adapters, hooks, and quick docs.
- `--surface extended` — the default full pack, including AIDLC, reports,
  learning, benchmarks, quality/security helpers, and token tools.

Use Core for lightweight onboarding. Upgrade later without deleting files:

```bash
python3 scripts/tailtrail.py install upgrade-to-extended --target /path/to/project
```

## Optional official AI-DLC Full mode

Lite and Standard AIDLC are included. Full mode is opt-in and uses a pinned,
integrity-checked official workflow pack:

```bash
python3 scripts/tailtrail.py aidlc official install --root /path/to/project --host codex
python3 scripts/tailtrail.py aidlc official host install --root /path/to/project --host codex
```

It activates only for an explicit approved `--aidlc full` run. See
[TAILTRAIL-COMMANDS.md](TAILTRAIL-COMMANDS.md) for the full AIDLC reference.
