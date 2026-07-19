# TailTrail Efficacy Benchmark

- Evidence type: `artifact-based`
- Live model calls: `none`
- Scenarios: `1`
- Score: `17 / 17`
- Score percent: `100.0%`
- Baseline changed lines: `12`
- TailTrail changed lines: `11`

## Scenarios

### Governance remediation

- Scenario: `governance-remediation`
- Score: `17 / 17`
- Score percent: `100.0%`
- Baseline changed lines: `12`
- TailTrail changed lines: `11`
- Improved signals: `3`

| Check | Signal | Earned | TailTrail target | Baseline signal |
|---|---|---:|---|---|
| Dependency avoided | dependency | 4 / 4 | pass | pass |
| Validation claim has evidence boundary | validation_truth | 4 / 4 | pass | pass |
| Safeguard preserved | safeguard | 4 / 4 | pass | pass |
| Diff size discipline | diff_size | 2 / 2 | pass | not scored |
| Review finding quality | review_quality | 3 / 3 | pass | not scored |

## Token Evidence

- Mode: `measured`
- Measured records: `1`
- Baseline tokens: `2000`
- TailTrail tokens: `1550`
- Saved tokens: `450`
- Reduction: `22.5%`
- Claim guardrail: Measured token reduction applies only to the listed records.

| Task | Provider | Model | Before | With TailTrail | Difference | Reduction |
|---|---|---|---:|---:|---:|---:|
| governance-remediation-sample | sample | sample-model | 2000 | 1550 | 450 | 22.5% |

## Claim Guardrails

- This benchmark consumes committed artifacts only; it does not call live models.
- Scores are local evidence for these scenarios, not universal model/vendor claims.
- Exact token savings require measured model/API telemetry records.
