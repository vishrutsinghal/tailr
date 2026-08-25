# Repository and CI enforcement

Phase E6 provides deterministic repository enforcement that does not depend on
a coding assistant, MCP client, or named host. The installed command is:

```bash
tailtrail enforce validate --root .
tailtrail enforce check --root . --base <base-sha> --head <head-sha> --format json
tailtrail enforce check --root . --diff change.patch --format sarif --output report.sarif
```

`tailtrail-enforcement-policy.json` is the closed v1 authority. It classifies
each rule as `enforced`, `host-assisted`, or `advisory`. The Core enforced rules
cover protected-path approval, evidence truth, stale completion, Dependency
Gate decisions, safeguard preservation, local runtime state, sensitive-value
redaction, and release-manifest integrity. Overrides may tighten limits, add
protected paths, enable optional rules, or raise severity. They cannot disable
Core rules, lower severity, change classification, enable high-severity
suppression, or introduce unknown fields.

## Findings and exit behavior

JSON follows `schemas/repository-enforcement-report.schema.json`. SARIF 2.1.0
contains the same rule, severity, path, line, bounded evidence, remediation,
classification, state, blocking value, and fingerprint. New medium/high
`enforced` findings exit nonzero. Host-assisted and advisory findings remain
visible but never masquerade as independent enforcement.

The CLI reads a supplied diff, an explicit Git base/head range, an initial
commit, or the staged diff. An unavailable base—common in shallow clones and
fork boundaries—uses a fail-closed initial-commit diff instead of silently
checking nothing. Oversized or malformed inputs fail closed. The checker reads
repository text and metadata only; it never executes project commands.

## Approvals

Protected changes require a closed record under `tailtrail-meta/approvals/`
with policy version, decision, owner, reason, exact path scopes, and an expiry
within the policy maximum. Conversational approval is not machine evidence.
Malformed or overly long records block. Expired well-formed records become
inactive, so they cannot authorize a later protected change or poison unrelated
changes forever.

## Baselines and suppressions

`tailtrail-enforcement-baseline.json` contains exact finding fingerprints.
Baseline findings remain in reports as `baseline` and are non-blocking only for
that exact rule/path/line/message/evidence identity at medium severity. High
findings remain blocking even when their exact fingerprint is recorded. Changed
or new findings get new fingerprints and block normally.

`tailtrail-enforcement-suppressions.json` requires exact fingerprint, rule,
path, owner, reason, and expiry. Expired or overlong entries block policy
validation. High-severity findings cannot be suppressed. Suppressed medium
findings remain visible as `suppressed`; there are no wildcard suppressions.

## Policy migration

Migration is explicit and non-overwriting:

```bash
tailtrail enforce migrate --input legacy-v0.json --output policy-v1.json
```

Only the closed v0 `{version,enforce}` shape is accepted. Unknown rules or an
existing output fail without mutation. Core protections are always enabled in
the result.

## GitHub and other CI providers

`.github/actions/enforce/action.yml` accepts an exact TailTrail version and
produces JSON/SARIF. Released consumers use `distribution: pypi`; TailTrail's
own workflow uses `distribution: checkout` to test the candidate source. The
workflow pins third-party actions, uses only `contents: read`, uploads reports
as evidence, handles initial commits, and works for forks without secrets or
write tokens.

Other providers install the exact TailTrail version and invoke the same CLI
with a provider-generated unified diff. CI configuration changes transport and
artifact upload only; it does not change policy semantics.

## Limitations

Repository enforcement is not a test runner, SAST/secret scanner replacement,
human review, compliance certification, or proof of host behavior. Its
redaction rules deliberately target strong credential forms to reduce false
positives; broader organization-specific detectors belong in additive policy
and dedicated scanners.
