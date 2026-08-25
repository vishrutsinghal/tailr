# Versioning

TailTrail uses semantic versioning for public releases.

## Version Source Of Truth

Before a public tag, these must agree:

- `release-manifest.json` -> `product.version` (release authority)
- `pyproject.toml` -> `project.version`
- `.codex-plugin/plugin.json` -> `version`
- `tailtrail/__init__.py` -> `__version__`
- Git tag in the form `vMAJOR.MINOR.PATCH`

`CHANGELOG.md` must describe the candidate under `Unreleased`; the release
process moves those entries to the matching version heading when the tag is
created.

## Version Rules

- Patch: documentation updates, small script fixes, validation updates, or non-breaking hardening.
- Minor: new compatible commands, docs, templates, report sections, or parser support.
- Major: breaking command behavior, install layout, file contract, output schema, or default privacy behavior.

The 0.6 compatibility window covers CPython 3.12 and 3.13, the console and
Python API named in `PACKAGE-CONTRACT.md`, documented exit classes, and stable
JSON field meanings. Additive JSON fields are minor-compatible. Removing or
reinterpreting a documented field, exit class, or stable Python name requires a
major release and migration notes.

## Release Tag Rules

- Use tags like `v0.6.0`.
- Do not move a published tag.
- A release tag must reference the same full commit recorded by all six hosted
  platform receipts and the provenance subjects. Never rebuild after tagging.
- Release notes should include:
  - added
  - changed
  - fixed
  - security/privacy
  - migration notes
  - validation commands
  - known limitations

## Public Claim Rule

Do not describe exact token savings, quality improvement, risk reduction, or productivity impact unless the release notes point to measured local evidence. Estimates must be labeled as estimates.

## Supported Version Window

- The latest published minor release and the one immediately prior minor
  release (`N` and `N-1`) receive fixes. Older minor releases are unsupported
  once a new minor release ships.
- Patch releases within a supported minor line are always cumulative; install
  the latest patch of a supported minor line rather than an older patch.
- Declared Python, OS, and host support windows are the ones actually green in
  `.github/workflows/trust.yml` and `platform-supply-chain.yml` for that exact
  tag; a version is not "supported" on a platform without a passing hosted
  receipt for that platform.

## Deprecation Policy

- A command, flag, JSON field, or file contract is marked deprecated in
  `CHANGELOG.md` and `TAILTRAIL-COMMANDS.md` for at least one full minor
  release before removal.
- Deprecated surfaces keep working during the deprecation window and print or
  return a explicit deprecation notice; they are never silently removed mid-line.
- Removal requires a major release and migration notes describing the
  replacement command, flag, or field.

## Continuous Release Governance

Every maintained release line has a recurring review schedule. This section
defines the schedule; it does not claim any cycle has run yet. A review only
counts as "exercised" once it produces a dated, real record (a `CHANGELOG.md`
entry, a `PUBLIC-CLAIMS.md` pilot record, a closure-registry defect, or an
equivalent artifact) — not a calendar entry alone.

| Review | Cadence | Owner input |
| --- | --- | --- |
| Compatibility (Python/OS/host matrix) | Each minor release | `.github/workflows/trust.yml` and `platform-supply-chain.yml` receipts |
| Dependency | Each release, plus monthly security-only pass | `DEPENDENCY-GATE.md` decisions |
| Restore and migration drill | Quarterly | `tests/test_workflow_recovery.py`-class fixtures and enterprise backup/restore contracts |
| Security | Each release, and immediately after any disclosed vulnerability | `SECURITY.md` severity levels and response timeline |
| Host-runtime revalidation | Each supported host or host-version bump | `ENT-E10-001` real-run scenario receipts |
| Efficacy and pilot | Semi-annual | `PUBLIC-CLAIMS.md` Pilot Protocol |
| Deprecation | Each minor release | This document's Deprecation Policy |
| Support | Quarterly | `SUPPORT.md` role-based quick start and runbook accuracy |

A maintained release line is only "continuously governed" once every row above
has at least one dated real record; an empty or all-scheduled table is not a
completed review.
