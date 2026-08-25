# TailTrail Public Release Checklist

Use this checklist before any open-market release.

## Required Before First Public Release

- [x] Confirm final public license choice is recorded in `PUBLIC-RELEASE-METADATA.md`.
- [x] Confirm `.codex-plugin/plugin.json` uses the same license identifier.
- [x] Confirm `NOTICE.md` contains accurate provenance and attribution.
- [x] Confirm `PUBLIC-CLAIMS.md` matches current product capability and evidence.
- [x] Replace the temporary security contact in `SECURITY.md` with the final public reporting path.
- [ ] Run `python3 scripts/tailtrail.py doctor`.
- [ ] Run `python3 scripts/release-check.py`.
- [ ] Confirm `release-manifest.json` validates the candidate file scope, version sources, public-reference allowlist, workflow gates, distribution policy, and smoke ordering.
- [ ] Confirm the canonical wheel and sdist rebuilt byte-for-byte with the exact `release-build-lock.json` inputs and fixed source epoch.
- [ ] Confirm `scripts/package-release-proof.py` accepts the canonical artifacts and the wheel built from the canonical sdist installs successfully.
- [ ] Confirm `scripts/supply-chain.py verify` accepts `SHA256SUMS`, CycloneDX SBOM, provenance candidate, dependency inventory, and release evidence.
- [ ] Confirm the exact Linux/macOS/Windows x CPython 3.12/3.13 hosted receipt aggregate passes for the release commit and both artifact routes.
- [ ] On a `v*` tag, confirm GitHub identity attestations exist for both canonical artifacts and verify them with `gh attestation verify`; checksum files alone are not publisher identity.
- [ ] Run the tampered artifact, checksum, provenance, receipt hash, missing-cell, and non-hosted-receipt negative tests.
- [ ] Run `git diff --check`.
- [ ] Confirm no `.DS_Store`, `__pycache__`, `.tailtrail/`, private logs, secrets, benchmark generated outputs, or local state are tracked.
- [ ] Confirm no proprietary company code, internal-only policy text, private repo names, credentials, tokens, PII, PHI, customer data, or sensitive logs are present.
- [ ] Confirm README quick start works from a fresh clone.
- [ ] Confirm `python3 scripts/tailtrail.py start "fix Sonar issue" --changed path/to/file` behaves safely when the file does not exist.
- [ ] Confirm public docs do not claim exact token savings unless measured model/API telemetry is provided.
- [ ] Confirm public docs do not imply TailTrail replaces tests, CI, scanners, code review, security review, legal review, or compliance approval.
- [ ] Tag the release only after the checklist is complete.

## Recommended Before Broad Promotion

- [x] Add GitHub issue templates.
- [x] Add a changelog.
- [ ] Add tagged release notes.
- [x] Add a public demo walkthrough.
- [x] Add a short architecture diagram.
- [x] Add a compressed public roadmap.
- [x] Add a public documentation audit.
- [x] Add a fresh-clone smoke test script.
- [x] Add `.github/workflows/trust.yml` CI that runs enterprise-registry validation, `scripts/check-tailtrail.py`, `scripts/public-doc-audit.py`, `scripts/release-check.py`, the complete unit/contract suite, registry and adapter checks, guard/dependency gates, and the manifest-driven fresh-clone smoke.
- [x] Add canonical wheel/sdist distribution qualification after the Python entry point stabilized.
- [ ] Add package-manager adapters only after canonical hashes and identity attestations are published; each adapter must reuse the transactional installer.

## Release Positioning

Describe TailTrail as:

- local-first
- documentation-first
- assistant-agnostic
- approval-first
- token-aware, not token-magic
- learning-aware, not self-training
- scanner-aware, not a scanner replacement
