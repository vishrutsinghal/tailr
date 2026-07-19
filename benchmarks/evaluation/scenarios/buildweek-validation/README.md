# Build Week Validation Scenario

This scenario turns the live `buildweek-demo-project/` story into deterministic Evaluation Harness evidence.

## What It Proves

- TailTrail can express the Build Week demo as a repeatable saved-artifact scenario.
- The TailTrail artifact shows Navigator-first planning, approval before implementation, Code Graph read order, focused validation, review evidence, token/evidence labeling, and explicit claim boundaries.
- The baseline artifact intentionally lacks several TailTrail-specific evidence signals so the deterministic scorer can compare the variants.

## What It Does Not Prove

- It does not run a live AI agent.
- It does not run tests, scanners, builds, package managers, or CI.
- It does not prove live model performance, production defect reduction, or exact token savings.
- Exact token-savings claims still require measured provider telemetry.

## Run

```bash
python3 scripts/tailtrail.py eval scenario report --scenario buildweek-validation
python3 scripts/tailtrail.py eval scenario report --scenario buildweek-validation --format json
```

Use this during a pitch when you want repeatable proof without executing the live demo workspace.

## Relationship To The Demo Project

The live demo remains in `buildweek-demo-project/` with prompts, runbook, tests, logs, and policy examples. This fixture is a sanitized evidence record that mirrors the strongest demo path while staying deterministic and local.

Enterprise teams can adapt this pattern by creating their own scenario directory with a small baseline artifact, a TailTrail-style artifact, a rubric in `scenario.json`, and conservative thresholds in `expected.json`.

