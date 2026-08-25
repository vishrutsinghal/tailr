# Enterprise Phase E1 Requirements — Test and Release Truth

Date: 2026-08-22

Authority: `ENTERPRISE-READINESS-ASSESSMENT.md`, Phase E1

Approval: the user explicitly requested E1 implementation end to end. This
approves requirements, workflow, and implementation; validation and closure
remain evidence-gated.

## Boundary

E1 restores internal repository truth before package restructuring. It may fix
correctness, release, compatibility, evidence, and support defects allowed by
the E0 feature freeze. It must not add dependencies, claim installed-package or
real-host readiness, activate enterprise providers, publish, tag, push, or
silently adopt unrelated local files.

## Requirements

### ENT-E1-001 — Complete suite truth

- Support the evaluation-calibration event emitted by the Phase 8 adapter.
- Keep the committed evaluation-scenario inventory and tests identical.
- Preserve the separate Full-mode Planning Lock boundary in Navigator output.
- Verify inaccessible targets with an isolated, deterministic fixture rather
  than a developer-specific absolute path.
- Render the approved UI-system preservation contract in compact Start output.
- Run the complete supported unit and contract suite with no baseline exception
  list.

### ENT-E1-002 — Root Navigator compatibility

- Keep the documented root `navigator.py` entry point importable and executable
  while `scripts/navigator.py` remains canonical.
- Resolve repository script modules without environment-specific `PYTHONPATH`.
- Leave a focused import/callable compatibility test.

### ENT-E1-003 — One release truth

- Make `release-manifest.json` the versioned authority for candidate additions
  and exclusions, required release files, versions, workflows, public URL
  allowlists, repository hygiene, distribution policy, and smoke commands.
- Make repository doctor, release check, public-doc audit, smoke, CI, and export
  consume or validate that authority.
- Permit only explicitly approved public upstream repositories; reject private
  or accidental repository references within the candidate scope.
- Exclude untracked user files and generated `.tailtrail` state from the
  candidate without deleting or concealing them.
- Run release and doctor preflight before the smoke journey creates local state.
- Add the declared issue templates, pull-request template, and demo rather than
  retaining stale missing-file claims.
- Reconcile `.github/workflows/trust.yml`, support/versioning/release metadata,
  and the release checklist with actual gates.

## Negative assurance

Focused tests must prove failure for a missing required file, wrong version,
private repository reference, stale workflow, and local `.tailtrail` state.
They must also prove an approved pinned upstream reference is accepted and the
candidate snapshot excludes generated local state.

## Validation and exit

- `python3 -m unittest discover -s tests -p 'test_*.py' -v`
- `python3 scripts/enterprise-readiness.py validate`
- `python3 scripts/tailtrail-registry.py validate --strict`
- `python3 scripts/check-tailtrail.py`
- `python3 scripts/public-doc-audit.py`
- `python3 scripts/release-check.py`
- `python3 scripts/tailtrail.py doctor`
- `python3 scripts/smoke-test.py`
- `python3 -m compileall -q scripts tests navigator.py`
- `git diff --check`

E1 closes only when all commands pass, all E1 defects are recorded closed, and
the manifest-built candidate is clean of prohibited local artifacts. This does
not close E2-E12 or assert the current working tree itself is committed.
