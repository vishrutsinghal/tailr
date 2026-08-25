# Phase E5 requirements

Authority: `ENTERPRISE-READINESS-ASSESSMENT.md`, ENT-E5-001 and ENT-E5-002.

1. Qualify Linux, macOS, and Windows on CPython 3.12 and 3.13 using canonical built artifacts.
2. Exercise wheel and sdist-to-wheel installation, the console launcher, hostile/portable path forms, platform boundaries, and every Codex/Copilot/Claude Core lifecycle.
3. Require six truthful hosted receipts tied to one source commit and canonical artifact hashes; configured or simulated coverage is not observed evidence.
4. Rebuild reproducibly from locked build inputs, inspect publication contents, and fail on tampering.
5. Publish SHA-256 checksums, a CycloneDX SBOM, a provenance candidate, dependency inventory, and a release evidence manifest.
6. Identity-attest tagged release artifacts with least-privilege GitHub OIDC permissions; local metadata is never represented as a signature.
7. Publish exact limitations and keep package-manager adapters unsupported until they verify the same canonical hashes and lifecycle.
