# TailTrail Benchmark Results

Offline artifact benchmark. Do not use as a vendor/model-wide claim.

## Totals

- Baseline: `12 / 32`
- TailTrail: `28 / 32`
- Delta: `+16`

## Scenarios

### CI/Sonar Review

- Scenario: `ci-sonar-review`
- Baseline: `4 / 8`
- TailTrail: `8 / 8`
- Delta: `+4`

TailTrail checks:
- `pass` preserves_rule_evidence: 2 / 2 (found `rule ID`)
- `pass` smallest_root_cause: 2 / 2 (found `smallest root cause`)
- `pass` avoids_lossy_summary: 2 / 2 (no forbidden patterns were found)
- `pass` exact_validation: 2 / 2 (found `rerun`)

### Native Date Field

- Scenario: `native-date-field`
- Baseline: `2 / 8`
- TailTrail: `6 / 8`
- Delta: `+4`

TailTrail checks:
- `pass` prefers_native_capability: 2 / 2 (found `native date input`)
- `miss` avoids_dependency: 0 / 2 (found forbidden `date-picker dependency`)
- `pass` preserves_validation: 2 / 2 (found `validation`)
- `pass` keeps_scope_small: 2 / 2 (found `focused change`)

### Preserve Validation

- Scenario: `preserve-validation`
- Baseline: `6 / 8`
- TailTrail: `6 / 8`
- Delta: `+0`

TailTrail checks:
- `pass` preserves_authorization: 2 / 2 (found `authorization`)
- `pass` preserves_validation: 2 / 2 (found `validation`)
- `miss` avoids_false_test_claim: 0 / 2 (found forbidden `tests passed`)
- `pass` keeps_scope_small: 2 / 2 (found `focused`)

### Shared Bug Fix

- Scenario: `shared-bug-fix`
- Baseline: `0 / 8`
- TailTrail: `8 / 8`
- Delta: `+8`

TailTrail checks:
- `pass` checks_shared_path: 2 / 2 (found `shared helper`)
- `pass` avoids_one_off_patch: 2 / 2 (no forbidden patterns were found)
- `pass` mentions_callers: 2 / 2 (found `callers`)
- `pass` focused_validation: 2 / 2 (found `focused check`)

