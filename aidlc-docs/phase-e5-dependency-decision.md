# E5 dependency decision

- Decision: approve exact build pins for `setuptools==84.0.0`, `wheel==0.48.0`, and wheel's resolved `packaging==26.3` dependency; reject new runtime, SBOM, provenance, and platform-test packages.
- Problem: PEP 517 needs a backend and wheel builder, while reproducible release inputs cannot use the previous open-ended `setuptools>=61` range.
- Alternatives: the standard library cannot build a standards-compliant wheel; the existing setuptools backend is smaller than replacing the build system. CycloneDX JSON, hashes, provenance candidates, and matrix receipts are generated with the standard library.
- Risk: these tools expand the release supply chain and their pins can age. They execute only in the build environment and TailTrail continues to declare zero runtime dependencies.
- Owner: `tailtrail-release`, with security advisory response shared by `tailtrail-security`.
- Upgrade: review monthly and before release; change the lock and `pyproject.toml` atomically.
- Validation: build wheel and sdist twice with a fixed epoch, compare bytes, build a wheel from the sdist, inspect all artifacts, verify the evidence bundle, and run tamper negatives.
- Rollback: revert both pin locations and generated evidence, then rerun all E5 gates before publication.
