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

After a successful `setup`/`install`, TailTrail registers its own command
directory on your user PATH when `tailtrail` does not already resolve
(Windows: HKCU Environment, no admin needed; other platforms print a shell
hint). Restart terminals and IDEs afterwards — PATH reloads per process —
then verify with `where.exe tailtrail` (Windows) or `command -v tailtrail`.
Pass `--no-path-register` to opt out.

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

### Scope-v2 release verification and rollback

Before promotion, run the packaged entrypoint—not a source-only import:

```bash
tailtrail eval scope release-proof --root /path/to/project --format json
```

The proof executes isolated CLI and MCP Starts, checks the same v2 decision
fingerprint and exact owner/proof roles, approves the lock, records a bounded
implementation fixture and command evidence, finalizes closure, and requires a
complete Completion Report. It also proves the negative rollback path creates
no run artifacts. Wheel/sdist inventory and checksums remain separately
mandatory through `scripts/package-release-proof.py` and the normal release
workflow.

For an investigation incident, use `eval scope rollback-enable` as documented
in `SUPPORT.md`. It never enables legacy lexical scope. For an update incident,
use the install transaction rollback; the prior signed managed payload is
restored while `.tailtrail/runs` is preserved byte-for-byte. WSL uses the Linux
artifact and is exercised as a compatibility fixture; it is not represented as
a separate hosted platform receipt.

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

## Navigator scope release and rollback

Before packaging or updating an installation, run:

```bash
tailtrail eval scope report --format json
tailtrail eval scope release-proof --root . --format json
python3 scripts/run-tests.py --jobs 1 --include test_self_contained_package
tailtrail adapters conformance
```

The scope report must show zero false stops, irrelevant options, and unsafe
locks for the committed FSR-6 corpus, plus complete supported-language profile
coverage. Package inventory proves that runtime code, schemas, fixtures, and
documentation are present; source-release inventory separately retains tests.

If an investigation regression appears, enable the fail-closed switch with
`tailtrail eval scope rollback-enable --root . --reason-code <incident> --approved`.
This blocks new scope-v2 Start runs without deleting installations or saved
runs and without reviving lexical ownership. After a corrected build passes
calibration and release proof, re-enable with `rollback-disable` under explicit
approval. Transactional installer rollback remains the separate byte-level
recovery mechanism.

For already-built artifacts, verify their exact inventories and hashes with
`python3 scripts/package-release-proof.py --wheel <artifact.whl> --sdist <artifact.tar.gz>`.

## FSR-7 installed real-run proof

After building the canonical wheel and source distribution, run:

```bash
tailtrail eval scope installed-release-proof \
  --wheel dist/tailtrail-0.6.0-py3-none-any.whl \
  --sdist dist/tailtrail-0.6.0.tar.gz \
  --source-root . \
  --output fsr7-installed-release-proof.json
```

The command creates a temporary external Git fixture, installs the wheel into
an isolated virtual environment, performs a Core install followed by an
Extended transactional update for Codex, Copilot, and Claude, and verifies
every host manifest. It then uses the installed Codex launcher to refresh a
real graph and execute the sealed incident-style Start request.

Installation integrity and Navigator behavior are separate fail-closed gates.
The proof compares selected source, wheel, source-distribution, installed, and
ownership-manifest hashes; the behavioral gate requires one page owner, one
inspection-only service, one proof-only component test, a fresh graph, no
scope question, presentation-independent literal matching, and a real
awaiting-approval Planning Lock. Plain, emphasized, quoted, and inline-code
spellings of the same reported message must not change scope. The complete
parsed Start report and exact stdout digest are retained. The temporary fixture
is deleted and no hosted-agent success is claimed.
