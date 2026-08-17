# TailTrail Benchmarks

TailTrail benchmarks are local, offline, and artifact-based. They do not call models, send code to services, or claim universal performance gains.

The goal is to compare saved baseline outputs with TailTrail-guided outputs across repeatable scenarios.

Use:

```bash
python3 scripts/benchmark-tailtrail.py
python3 scripts/benchmark-tailtrail.py --scenario native-date-field
python3 scripts/benchmark-tailtrail.py --format json
python3 scripts/tailtrail.py benchmark efficacy
python3 scripts/tailtrail.py benchmark efficacy --format json
```

Each scenario contains:

- `scenario.md`: task, risks, and scoring intent.
- `expected.json`: checks and point values.
- `baseline-output.md`: sample output without TailTrail guidance.
- `tailtrail-output.md`: sample output with TailTrail guidance.

Scores are evidence for local improvement only. Do not claim TailTrail improves every model, repo, or team by a fixed percentage.

## Efficacy Benchmarks

Efficacy scenarios live under `benchmarks/efficacy/`. They compare committed baseline artifacts with TailTrail-guided artifacts for concrete governance signals such as dependency discipline, validation truth, safeguard preservation, diff size, and review finding quality.

Each efficacy scenario contains:

- `scenario.md`: task and evidence boundary.
- `expected.json`: objective checks and point values.
- `baseline-artifact.md`: comparison artifact without TailTrail guidance.
- `tailtrail-artifact.md`: comparison artifact with TailTrail guidance.
- optional `token-usage.jsonl`: measured token telemetry sample.

Use efficacy results as reproducible local evidence only. Exact token claims require measured usage telemetry and apply only to the records in the report.

## Public Evidence Portfolio

`benchmarks/public/` contains five published, sanitized fixture comparisons:
dependency decisions, validation/caller proof, API contracts, bounded refactoring,
and safe complexity reduction. Run them with:

```bash
python3 scripts/tailtrail.py benchmark run-public
python3 scripts/tailtrail.py benchmark public run --format json
```

They are explicitly labeled `fixture-scored`: deterministic checks over saved
artifacts, not live-model evidence. Real model runs are never launched by
TailTrail. A contributor may explicitly record a sanitized receipt and artifact
hashes using `benchmark capture-model-run ... --approved`; incomplete telemetry
remains `model-run-unmeasured`, never measured.
