# Public Benchmark Fixtures

This portfolio is a public, reproducible set of **sanitized fixture-scored**
comparisons. It never runs a model or sends code anywhere. Each scenario keeps
the task prompt and paired sample outcomes separate so the deterministic scorer
can check the same observable expectations every time.

The committed fixture result is
`benchmarks/results/public-benchmark-2026-08.json`. Re-run the command below
after changing a fixture; do not relabel this result as a model run.

Run it locally:

```powershell
py -3 scripts\tailtrail.py benchmark run-public
py -3 scripts\tailtrail.py benchmark public run --format json
```

The five fixtures cover dependency discipline, validation, API delivery,
maintainable refactoring, and static-analysis remediation. They are not proof
that every model, repository, or team receives the same outcome.

## Carefully captured real model runs

TailTrail does not invoke a model. After a contributor has independently run
both prompts, they may supply sanitized output artifacts plus a receipt:

```json
{
  "type": "tailtrail-model-run-receipt",
  "schema_version": "1",
  "scenario_id": "validation-zero-quantity",
  "provider": "provider-name",
  "model": "model-version",
  "recorded_at": "2026-08-17",
  "sanitized": true,
  "consent": "approved",
  "telemetry": {
    "baseline_total_tokens": 1200,
    "tailtrail_total_tokens": 980
  }
}
```

Then explicitly write the provenance-only record. The saved result contains
only hashes, provider/model metadata, and complete supplied token totals. It
does not store raw prompts, responses, project source, paths, identifiers, or
credentials.

```powershell
py -3 scripts\tailtrail.py benchmark capture-model-run --scenario validation-zero-quantity --receipt receipt.json --baseline baseline.md --tailtrail tailtrail.md --approved
py -3 scripts\tailtrail.py benchmark model-runs
```

Incomplete telemetry is retained as `model-run-unmeasured`; it never becomes a
measured claim.
