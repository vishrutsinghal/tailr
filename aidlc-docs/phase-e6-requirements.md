# Phase E6 requirements

Authority: `ENTERPRISE-READINESS-ASSESSMENT.md`, ENT-E6-001.

1. One installed, provider-neutral CLI must enforce Core repository policy without model or host cooperation.
2. A closed v1 policy defines defaults, safe overrides, validation, migration, ownership, limits, and enforced/host-assisted/advisory classification.
3. Enforced rules cover approval scope, evidence truth, stale completion, dependencies, safeguards, local state, redaction, and release-manifest integrity.
4. Stable JSON and SARIF include rule ID, severity, exact path/line, bounded evidence, remediation, fingerprint, baseline/suppression state, and blocking truth.
5. Baselines match only exact fingerprints; suppressions require owner, reason, exact path/rule/fingerprint, and expiry. New high-severity findings cannot be suppressed.
6. GitHub integration uses pinned actions and read-only repository permissions; the CLI remains usable in other CI providers.
7. Positive and negative fixtures cover normal/range/initial diffs, shallow/fork input, permissions, expiry, schema drift, tampering, false positives, and every enforced rule.
