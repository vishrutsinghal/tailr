# Release supply chain

`platform-release-contract.json` is the machine-readable E5 support and
evidence boundary. TailTrail supports canonical wheel and sdist distribution
on CPython 3.12 and 3.13 only after the exact Linux, macOS, and Windows hosted
matrix succeeds for a source commit. A configured job, a local simulation, or
one operating system cannot substitute for an observed receipt.

## Canonical build

The release workflow uses the exact build-only packages in
`release-build-lock.json`, a fixed `SOURCE_DATE_EPOCH`, and no runtime
dependencies. It builds wheel and sdist twice and compares bytes, builds an
additional wheel from the sdist, and inspects archive paths and packaged
resource hashes before qualification. Publication must reuse these artifacts;
it must not rebuild them.

## Evidence bundle

Run:

```bash
python3 scripts/supply-chain.py create \
  --artifact dist/tailtrail-0.6.0-py3-none-any.whl \
  --artifact dist/tailtrail-0.6.0.tar.gz \
  --output release-evidence --commit <full-git-sha>
python3 scripts/supply-chain.py verify \
  --artifact dist/tailtrail-0.6.0-py3-none-any.whl \
  --artifact dist/tailtrail-0.6.0.tar.gz \
  --bundle release-evidence
```

The bundle contains `SHA256SUMS`, a CycloneDX 1.6 SBOM, an in-toto/SLSA
provenance candidate, and `release-evidence.json`. The candidate records build
inputs and subjects but is not a signature. On a `v*` tag, the least-privilege
identity-attestation job creates GitHub/Sigstore attestations only after the
six-cell platform gate passes. Consumers verify each downloaded subject with:

```bash
gh attestation verify tailtrail-0.6.0-py3-none-any.whl --repo <owner/repository>
gh attestation verify tailtrail-0.6.0.tar.gz --repo <owner/repository>
```

Detached checksums detect changed bytes but do not establish publisher
identity. Verify both the identity attestation and the checksum. Never treat a
locally edited `release-evidence.json` as signed proof.

The trusted discovery metadata is `release-channel-v1.json`; inspect it with
`tailtrail release info`. A qualifying `v*` tag runs platform qualification,
creates GitHub identity attestations, verifies tag/package version agreement,
and publishes the already-built canonical wheel, sdist, checksums, SBOM, and
release evidence to GitHub Releases. Publication never rebuilds an artifact.
The workflow definition is not proof that a release ran; support aggregation
requires a separate observed publication receipt.
The hosted platform aggregate and the post-publication observation receipt are
also identity-attested. `tailtrail qualify report` verifies those attestations
and the canonical wheel before it can return `supported: true`.

## Platform receipts

Each hosted runner installs the canonical wheel and the wheel built from the
canonical sdist into separate isolated environments. It exercises the console
launcher, spaces and Unicode paths, CRLF preservation, permissions and
symlinks where the OS exposes them, plus install, verify, update, rollback, and
uninstall for Codex, Copilot, and Claude Core. The aggregate command requires
exactly Linux/macOS/Windows x Python 3.12/3.13, the same source SHA, and the same
artifact hashes.

## Package-manager boundary

Homebrew, WinGet, Chocolatey, system packages, and similar adapters are not
supported yet. A future adapter must consume the already-qualified canonical
artifact, verify its published SHA-256 and identity attestation, and call the
same transactional installer. It may not fork lifecycle logic.
