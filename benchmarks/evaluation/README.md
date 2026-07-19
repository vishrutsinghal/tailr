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

Scoring is local, deterministic, and text-signal based. It does not run models, scanners, tests, package managers, CI, or live agents.

Claim boundary: scenario scores are fixture evidence, not live model performance. Exact token savings require measured telemetry.
