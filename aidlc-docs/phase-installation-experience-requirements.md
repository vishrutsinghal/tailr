# Installation Experience And Release Qualification Requirements

Approval: the user explicitly approved implementing all seven recommendations
on 2026-09-01. This approval covers repository-local code, tests,
documentation, and CI configuration. It does not fabricate external host runs,
hosted CI receipts, tags, attestations, or releases.

- `TT-INSTALL-001` — Provide one guided, deterministic setup command that
  installs or updates, verifies, diagnoses, and returns first-action/reload
  guidance. Automatic host choice must fail closed when ambiguous.
- `TT-INSTALL-002` — Provide one local-artifact upgrade command that verifies
  exact SHA-256 and package integrity, preflights project changes, requires
  explicit environment-mutation approval, avoids indexes/dependencies, and
  transactionally updates installed host payloads.
- `TT-INSTALL-003` — Make text and new guided-setup JSON compact by default,
  provide `--compact` for existing lifecycle JSON, and preserve the 0.6 full
  JSON contract plus exact setup plans/path lists through `--verbose`.
- `TT-INSTALL-004` — Store the Extended runtime once per version while
  preserving the governed per-host launcher path and reference-safe
  update/rollback/uninstall behavior.
- `TT-INSTALL-005` — Define one trusted release channel and a tagged workflow
  that publishes already-qualified, identity-attested canonical artifacts
  without rebuilding them.
- `TT-INSTALL-006` — Provide one fail-closed aggregate qualification gate over
  instruction conformance, six real-host receipts per selected host, the exact
  identity-attested hosted platform matrix, and an identity-attested observed
  publication receipt tied to the downloaded, attested wheel.
- `TT-INSTALL-007` — Put mandatory, host-specific reload instructions and
  stronger stale-session fallbacks in the closed adapter contract and surface
  them through setup/doctor.

Dependencies: no runtime or build dependency is added or changed. Python
standard-library argparse, hashing, zip handling, subprocess, paths, JSON, and
the existing E2-E5 installer/package/host/supply-chain controls are reused.

Evidence boundary: configured CI is not a run; generated scenario bundles are
not host observations; local checks are not hosted-platform receipts; release
metadata and a workflow are not an observed publication or signature.
