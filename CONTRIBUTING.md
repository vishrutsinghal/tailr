# Contributing To TailTrail

Thanks for helping improve TailTrail. The project is intentionally local, small, and explainable.

## Development Principles

- Keep workflows documentation-first unless automation clearly pays for itself.
- Prefer Python standard library scripts.
- Avoid new dependencies unless there is a strong reason.
- Keep all file changes reviewable.
- Preserve security, validation, privacy, accessibility, data integrity, and exactness guardrails.
- Do not add hidden telemetry, background services, or automatic prompt capture.
- Do not vendor third-party source, assets, or documentation without explicit provenance and license review.

## Before Opening A Change

Run:

```bash
python3 scripts/tailtrail.py doctor
python3 scripts/tailtrail.py registry validate --strict
python3 scripts/tailtrail.py registry drift
python3 scripts/release-check.py
git diff --check
```

Governance text is single-sourced in `GOVERNANCE.md`. If you edit the marked governance block, run `python3 scripts/tailtrail.py governance sync`, then `python3 scripts/tailtrail.py governance check --strict`; do not hand-edit generated marked blocks in adapters, instruction files, or roadmap copies.

Feature inventory is single-sourced in `tailtrail-registry.json`. If you add or change a TailTrail command, script, feature, doc, test, install surface, MCP exposure, approval requirement, or evidence label, update the registry in the same change and run `python3 scripts/tailtrail.py registry validate --strict`.

Feature change checklist:

- registry entry updated
- command help updated
- `TAILTRAIL-COMMANDS.md` updated
- `USER-GUIDE.md` or feature doc updated
- `ROADMAP.md` status updated
- `CHANGELOG.md` Unreleased entry added
- tests added or updated
- install/check-tailtrail inventory updated
- public claim boundaries preserved
- `python3 scripts/tailtrail.py registry drift` reviewed

For Python changes, also run:

```bash
python3 -m py_compile scripts/*.py hooks/*.py
```

## Pull Request Expectations

Include:

- purpose of the change
- files changed
- validation commands run
- known skipped checks
- user-facing behavior change
- privacy/security impact, if any

Keep generated local state out of commits. `.tailtrail/`, `__pycache__/`, `.DS_Store`, and benchmark result outputs should remain untracked.

## Public Release Hygiene

Before public release, run:

```bash
python3 scripts/release-check.py
```

Do not publish if the release check reports private placeholders, tracked local state, missing governance files, or an `UNLICENSED` manifest.
