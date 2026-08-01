# TailTrail Evaluation Scenarios

Evaluation scenarios are deterministic saved-artifact fixtures for proving TailTrail behavior without live agent runs.

Use:

```bash
python3 scripts/tailtrail.py eval scenario list
python3 scripts/tailtrail.py eval scenario run --scenario validation-bug
python3 scripts/tailtrail.py eval scenario compare --scenario validation-bug
python3 scripts/tailtrail.py eval scenario report --scenario validation-bug --format json
python3 scripts/tailtrail.py eval scenario report --scenario buildweek-validation
```

Implemented scenarios:

- `validation-bug`: focused bug fix with validation.
- `dependency-decision`: dependency-discipline reasoning.
- `review-only`: review output quality.
- `ci-failure`: CI/log triage and handoff.
- `security-triage`: safeguard-preserving security triage.
- `buildweek-validation`: Build Week demo proof as deterministic fixture evidence.

Each scenario directory contains:

- `scenario.json`: rubric, dimensions, variants, and claim boundaries.
- `baseline-artifact.md`: reference artifact to compare against.
- `tailtrail-artifact.md`: TailTrail-style artifact.
- `expected.json`: minimum acceptance thresholds.

## Delivery dataset: multi-file requirement completion

`delivery-dataset/v1.json` is a curated set of **12 realistic multi-file
delivery tasks**. Every task has paired `baseline` and `tailtrail` outcome
fixtures. It measures the delivery gaps TailTrail is designed to address:

| Metric | Unit | Direction |
| --- | --- | --- |
| Requirement completion | completed / total requirements | Higher is better |
| Missed caller cases | count | Lower is better |
| Missed test cases | count | Lower is better |
| Correction cycles | count | Lower is better |
| Scope drift paths | count | Lower is better |
| False interventions | count | Lower is better |
| Developer review time | minutes | Lower is better |

```bash
python3 scripts/tailtrail.py eval dataset validate
python3 scripts/tailtrail.py eval dataset list
python3 scripts/tailtrail.py eval dataset report
python3 scripts/tailtrail.py eval dataset report --format json
```

The dataset is deliberately explicit about its evidence boundary: it is a
deterministic, curated fixture used to validate metric shape, aggregation, and
comparison logic. It is **not** a live-agent benchmark or a productivity claim.
To make empirical claims, collect blinded repeated baseline and TailTrail runs
using the same task, model configuration, time budget, repository revision, and
review rubric; then import those measured outcomes into a new, separately
labelled dataset version.

Scoring is local, deterministic, and text-signal based. It does not run models, scanners, tests, package managers, CI, or live agents.

Claim boundary: scenario scores are fixture evidence, not live model performance. Exact token savings require measured telemetry.
