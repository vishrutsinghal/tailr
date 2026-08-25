# TailTrail Public Release Metadata

This file records the public release license and provenance decisions for TailTrail.

## License

- Public license: Apache-2.0.
- License text: `LICENSE`.
- Plugin manifest field: `.codex-plugin/plugin.json` -> `license`.
- Expected manifest value: `Apache-2.0`.

## Ownership

- Public release owner: TailTrail project maintainers.
- Copyright holder text: Copyright 2026 TailTrail project maintainers.

## Provenance

- TailTrail is original local development guidance tooling.
- TailTrail does not vendor third-party source code, assets, or documentation.
- Files are original TailTrail project files unless a file explicitly states otherwise.
- Optional generated local outputs under `.tailtrail/` are user/project runtime artifacts and are not part of the public release source.
- `release-manifest.json` is the versioned authority for candidate scope,
  version sources, approved public upstream repositories, workflows,
  distribution policy, and smoke ordering.
- `platform-release-contract.json` is the OS, Python, artifact, host-profile,
  limitation, and observed-evidence authority.
- `release-build-lock.json` records exact build-only dependencies, ownership,
  upgrade expectations, and rollback. TailTrail has no runtime dependencies.
- Tagged artifacts are identity-attested by the hosted release workflow only
  after the exact platform matrix passes. Deterministic local provenance is an
  inspectable candidate, not a signature.

## Public Release Boundary

This metadata applies only to the public/open-market distribution. Internal distributions intentionally exclude public release, license, contribution, conduct, security, release-check, roadmap, and admin release files.
