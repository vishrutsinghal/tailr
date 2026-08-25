# Phase E5 design

The canonical build job creates wheel and sdist with a fixed epoch and exact build pins, repeats the build byte-for-byte, builds an additional wheel from the sdist, and generates a closed evidence bundle. A six-cell hosted matrix downloads those immutable artifacts, installs both artifact routes into isolated environments, and emits one receipt per actual OS/Python runner. The aggregate gate validates exact matrix coverage, commit identity, hashes, checks, artifact routes, and three host profiles.

Supply-chain evidence has separate trust levels. Checksums, SBOM, and provenance candidate are deterministic inspection metadata. Only the tagged-release attestation job may call the identity-backed signer, with `id-token: write` and `attestations: write`; a local run remains `required-on-tag`. Publication consumes the already-qualified artifacts and never rebuilds them.
