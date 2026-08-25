# Phase E6 design

`tailtrail-enforcement-policy.json` is the only E6 policy authority. The dependency-free `tailtrail enforce` CLI loads and validates it, applies only safe additive overrides, maps existing Guard and Dependency Gate findings into a common contract, and owns the additional approval, stale-completion, redaction, and release-manifest rules. It never executes project code.

Every finding receives a content fingerprint before baseline and suppression evaluation. Exact baseline findings remain visible and non-blocking. Suppressions are exact, bounded, attributable, and expiring; high severity is never suppressible. Schema, input-size, malformed approval, stale suppression, and policy-version failures become blocking policy findings rather than silent fallback.

The checked-in composite GitHub action and workflow are thin consumers. They use a pinned TailTrail version input, full history when available, explicit initial-commit fallback, read-only contents permission, stable JSON/SARIF artifacts, and no write token. Other CI systems call the same CLI with a diff file or explicit base/head range.
