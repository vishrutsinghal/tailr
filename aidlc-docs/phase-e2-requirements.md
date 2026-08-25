# Phase E2 Requirements — Self-Contained Package

Status: implemented; validation pending final enterprise gates.

## Boundary and ownership

E2 is owned by `tailtrail-packaging` and depends on closed E1 release truth.
It delivers the product kernel and artifact contract only. E3+ installer UX,
platform matrices beyond Python, live host proof, CI productization, security
operations, pilots, and GA remain governed by their existing phase owners and
must not be represented as complete by E2 evidence.

## Complete requirements

1. Build wheel and sdist artifacts containing the Core command runtime,
   schemas, adapters, templates, registries, migration namespace, and static
   resources without requiring a repository checkout.
2. Replace checkout-searching console bootstrap with an importable package
   kernel, explicit package resource resolution, stable public API, and a thin
   source compatibility wrapper.
3. Verify all packaged resources with a generated SHA-256 inventory and fail
   closed for missing, corrupt, malformed, or path-escaping entries.
4. Define stable version, package status, text/JSON, error, exit-code,
   deprecation, schema, and migration policies for the 0.6 compatibility line.
5. Support CPython 3.12 and 3.13 consistently in metadata, Ruff, CI, docs, and
   executable proof; reject unsupported versions clearly.
6. Inspect both artifacts for required inventory and exclude tests, local state,
   caches, IDE files, user proposals/backups, symbolic links, and secret-like
   paths.
7. From an environment outside the checkout, prove hello, doctor, Start,
   approval, versioned recovery, source/command evidence, complete closure,
   migration import, and native or contained JSON responses.
8. Add focused positive and negative tests, release proof tooling, installer
   inventory, feature/release/enterprise registry ownership, and CI gates so no
   E2 behavior is manual-only.

## Acceptance

Both artifacts install successfully. The installed console never searches for
a checkout. Every declared runtime resource is present and hash-correct. The
Core lifecycle completes with requirement-linked evidence after an actual
recovery exercise. Negative resource and JSON cases fail categorically. The
complete supported Python matrix and all E0-E2 release gates pass before the E2
registry entries may be closed.
