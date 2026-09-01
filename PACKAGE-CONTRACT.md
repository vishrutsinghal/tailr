# TailTrail Package Contract

TailTrail 0.6 is distributed as a self-contained Python wheel and source
distribution. Normal installed execution uses resources below the installed
`tailtrail` package and never searches the current directory, parent
directories, or a source checkout. `tailtrail_cli.py` is a source-checkout
compatibility wrapper; it opts into that mode with
`TAILTRAIL_SOURCE_COMPAT_ROOT`.

## Supported runtime

- CPython 3.12 and 3.13 are supported.
- Packaging metadata rejects Python versions outside `>=3.12,<3.14`.
- `tailtrail --version` and `tailtrail version --format json` report the
  compatibility decision without running a project command.
- The package has no runtime dependencies. Its existing build requirements are
  setuptools and wheel.

## Stable surfaces

The console command and these Python names are compatibility-controlled:
`tailtrail.main`, `tailtrail.package_status`, `tailtrail.PackageStatus`, and
`tailtrail.ExitCode`. Repository scripts, `tailtrail.scripts`, and migration
implementation modules are internal. Additive fields may be introduced in JSON
objects; existing field meanings and documented exit classes are preserved for
the 0.6 line.

Exit classes are: `0` success, `1` validation failure, `2` usage or rejected
input, `3` unavailable runtime/resource, and `70` internal package failure.
Machine requests use JSON objects. Package errors use `tailtrail-error`; a
legacy command that cannot emit native JSON is contained in a
`tailtrail-command-result` envelope.

Guided-setup JSON is compact by default: it retains identity, status,
diagnostics, issue text, counts, and `plan_summary`, while omitting bulk path
arrays and plan entries. Existing lifecycle JSON remains full in the 0.6 line;
`--compact` selects the summary and `--verbose` selects full setup detail.
`tailtrail setup`, `upgrade`, `release info`, and `qualify`
are additive 0.6 command surfaces; upgrade accepts only a local hash-pinned
wheel and requires `--approved` before changing the active environment.

## Resources, integrity, and migrations

`package-manifest.json` is the source inventory contract. Wheel construction
copies its Core schemas, adapters, templates, registries, command modules, and
static resources under the installed package and writes
`package-integrity.json` with one SHA-256 digest per resource. Every normal CLI
invocation verifies required resources and the complete digest inventory before
dispatch. Missing, malformed, path-escaping, and hash-mismatched resources fail
closed with non-sensitive categorical diagnostics.

Migration API version `1` represents the initial packaged-state format. No
data migration is required for TailTrail 0.6; future migrations must be
versioned, forward-only by default, idempotently testable, and retain an
explicit recovery path. Migration internals are not part of the stable Python
API.

## Release proof

Build with a fixed `SOURCE_DATE_EPOCH`, inspect both artifacts with
`python3 scripts/package-release-proof.py`, and install each artifact outside
the checkout. The maintained proof checks the artifact inventory and hashes,
forbidden local/secret/cache paths, hello, doctor, planning, activation,
evidence, closure, recovery, migration import, JSON errors, and the supported
Python matrix. Artifact success does not by itself declare the later
enterprise installer or host phases complete.
