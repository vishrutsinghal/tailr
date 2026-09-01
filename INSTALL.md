# Install TailTrail

This is the canonical installation, update, and verification guide. TailTrail
requires CPython 3.12 or 3.13.

## Install the self-contained command

Install a released wheel (preferred) or sdist into an isolated environment,
then run TailTrail from any project directory. The command does not require a
TailTrail source checkout and has no runtime dependencies:

```bash
python3.12 -m venv .venv
.venv/bin/python -m pip install tailtrail-0.6.0-py3-none-any.whl
.venv/bin/tailtrail hello
.venv/bin/tailtrail doctor
```

On Windows, use `.venv\Scripts\python` and `.venv\Scripts\tailtrail`.
`tailtrail package-info --format json` verifies every packaged resource hash.
See [PACKAGE-CONTRACT.md](PACKAGE-CONTRACT.md) for supported APIs, exit codes,
JSON envelopes, integrity, and migration policy.
Before installing a downloaded release, verify its SHA-256 and GitHub identity
attestation as described in [SUPPLY-CHAIN.md](SUPPLY-CHAIN.md). A checksum
detects changed bytes but does not establish publisher identity.

Use the installed command to transactionally project host guidance into an
existing target repository. See [INSTALLER-LIFECYCLE.md](INSTALLER-LIFECYCLE.md)
for the complete plan, ownership, backup, recovery, and retention contract.
The exact Core files, first actions, composition rules, diagnostics, and
qualification boundaries are defined in [HOST-ADAPTERS.md](HOST-ADAPTERS.md).
E4 host adapters are contract-tested; this does not claim a runtime-observed or
release-supported host/operating-system version.
E5 platform support is commit-specific and begins only when the published
Linux/macOS/Windows x CPython 3.12/3.13 hosted receipt aggregate is green.

## Pick one host profile

For the guided path, select a host explicitly or let TailTrail proceed only
when local detection is unambiguous. `setup` installs or updates, verifies the
result, runs host diagnostics, and prints the exact reload and first action:

```bash
tailtrail setup --host codex --profile core --target /path/to/project
tailtrail setup --host auto --profile core --target /path/to/project
```

Automatic selection fails without mutation when zero or multiple hosts are
detected. Use `--host all` only when the repository intentionally supports all
three assistants.

| Host | Windows | macOS / Linux |
| --- | --- | --- |
| Codex | `tailtrail install --host codex --profile core --target "D:\path\to\project"` | `tailtrail install --host codex --profile core --target /path/to/project` |
| GitHub Copilot | `tailtrail install --host copilot --profile core --target "D:\path\to\project"` | `tailtrail install --host copilot --profile core --target /path/to/project` |
| Claude | `tailtrail install --host claude --profile core --target "D:\path\to\project"` | `tailtrail install --host claude --profile core --target /path/to/project` |

On Windows, use `py -3`; do not use a bare `python`, which can resolve to the
Microsoft Store alias instead of a real Python runtime.

After installation or update, follow the host-specific `Reload:` line. A new
host chat/session is required; use the reported stronger restart fallback when
a fresh session still sees stale instructions.

## Verify

Use the manifest-driven read-only verification command:

```powershell
tailtrail verify --host codex --target "D:\path\to\project"
```

```bash
tailtrail verify --host codex --target /path/to/project
```

It verifies every owned file against the installed ownership manifest. Use
`tailtrail doctor --host codex --target .` for lifecycle diagnostics and
`tailtrail status --host codex --target .` for version/profile status.

## Update an existing install

```bash
tailtrail update --host codex --target /path/to/project --dry-run
tailtrail update --host codex --target /path/to/project
```

Modified managed files are preserved and reported. After review, `--force`
backs them up before replacement. Use `tailtrail repair`, `tailtrail recover`,
or `tailtrail rollback --to <transaction-id>` for the corresponding recovery
path. `tailtrail uninstall --dry-run` previews hash-owned removals.

Use `tailtrail upgrade` to upgrade the installed Python package and every
already-installed project payload from one reviewed release wheel:

```bash
tailtrail upgrade --artifact tailtrail-0.6.0-py3-none-any.whl \
  --sha256 <exact-sha256> --host all --target /path/to/project --dry-run
tailtrail upgrade --artifact tailtrail-0.6.0-py3-none-any.whl \
  --sha256 <exact-sha256> --host all --target /path/to/project --approved
```

The command never contacts a package index: it checks the exact digest and
embedded package integrity, preflights project conflicts, updates project
payloads transactionally, then invokes pip with `--no-index --no-deps`.
Project transactions are rolled back if pip fails. `--approved` is required
because the active Python environment changes. Discover the trusted channel
and verification commands with `tailtrail release info`.

## Optional surfaces

Managed packs support:

- `--profile core` — small first-run host surface.
  adapters, hooks, and quick docs.
- `--profile extended` — packaged Extended resources plus the host surface.
  learning, benchmarks, quality/security helpers, and token tools.

Use Core for lightweight onboarding. Upgrade later without deleting files:

```bash
tailtrail update --host codex --profile extended --target /path/to/project
```

Extended stores the full runtime once at
`.tailtrail/install/payload/common/<version>/`. Each host retains a small
launcher at `.tailtrail/install/payload/<host>/scripts/tailtrail.py`. Shared
files are preserved while any other host manifest still references them.

Default text and guided-setup JSON results are summaries. Existing lifecycle
JSON remains full for 0.6 compatibility; add `--compact` where only counts and
`plan_summary` are needed. Add `--verbose` to setup for exact managed paths and
the complete deterministic plan.

## Qualification

```bash
tailtrail qualify prepare --host all --root .
tailtrail qualify report --host all --root . \
  --platform-report <hosted-platform-report.json> \
  --publication-receipt <observed-publication-receipt.json> \
  --artifact <downloaded-wheel>
```

Missing real-host, hosted-platform, or signed-publication evidence returns
`evidence-incomplete`; configured workflows and local tests never become a
support claim. The report invokes `gh attestation verify` for the wheel, hosted
platform aggregate, and observed publication receipt.

## Optional official AI-DLC Full mode

Lite and Standard AIDLC are included. Full mode is opt-in and uses a pinned,
integrity-checked official workflow pack:

```bash
python3 scripts/tailtrail.py aidlc official install --root /path/to/project --host codex
python3 scripts/tailtrail.py aidlc official host install --root /path/to/project --host codex
```

It activates only for an explicit approved `--aidlc full` run. See
[TAILTRAIL-COMMANDS.md](TAILTRAIL-COMMANDS.md) for the full AIDLC reference.
