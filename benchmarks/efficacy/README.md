# TailTrail Measured Efficacy Protocol (BL-1 and BL-1.5)

This directory holds reproducible efficacy scenarios and paired telemetry used
by `python3 scripts/tailtrail.py efficacy run`. It exists to produce **measured**
evidence about TailTrail's effect on real coding tasks, so public and internal
claims stop relying only on local estimates.

The runner is deliberately conservative: it consumes committed artifacts and
optional paired provider telemetry, never calls a live model, and refuses to
label estimated numbers as measured.

BL-1 proves the measured runner works. BL-1.5 adds a measured evidence
portfolio so TailTrail can evaluate multiple task types instead of leaning on
one scenario.

## Protocol

Each scenario is a folder under `benchmarks/efficacy/<scenario>/` containing:

- `scenario.md` — human-readable description of the task, inputs, and what the
  scenario is trying to test.
- `baseline-artifact.md` — the answer produced without TailTrail guidance,
  captured verbatim.
- `tailtrail-artifact.md` — the answer produced with TailTrail guidance,
  captured verbatim.
- `expected.json` — deterministic pattern checks, following the schema used by
  `scripts/efficacy-benchmark.py`.
- `token-usage.jsonl` (optional) — paired baseline and TailTrail token usage
  records from a real provider run. Only records with `mode=measured` and
  complete baseline + TailTrail token totals count toward measured claims.

`expected.json` may include `scenario_class`, such as:

- `bug-fix`
- `review`
- `security`
- `ci-sonar`
- `dependency`
- `feature`
- `token-heavy`
- `learning-governance`

## Portfolio

The committed portfolio covers representative enterprise task types:

| Scenario | Class | Token evidence |
|---|---|---|
| `bug-fix-focused-tests` | `bug-fix` | measured sample |
| `review-only` | `review` | measured sample |
| `security-vulnerability-triage` | `security` | measured sample |
| `ci-sonar-failure` | `ci-sonar` | measured sample |
| `dependency-decision` | `dependency` | measured sample |
| `cross-file-feature` | `feature` | estimate only |
| `token-heavy-artifact` | `token-heavy` | estimate only |
| `learning-meta-harness-governance` | `learning-governance` | estimate only |
| `governance-remediation` | `learning-governance` | measured sample |

The portfolio is considered public-claim-ready only when:

- at least 8 scenarios exist,
- all target scenario classes are covered,
- at least 5 scenarios have measured or local-evidence token labels,
- deterministic artifact checks pass, and
- claim boundaries remain visible.

## Evidence Labels

The runner separates two evidence layers so no one can conflate them:

- **Artifact evidence** — deterministic pattern checks against the two
  committed artifacts. Always computed. Reported as a score and a per-check
  pass/miss list.
- **Token evidence** — labeled `measured` only when telemetry supplies
  complete baseline + TailTrail token blocks. Otherwise labeled `estimate`
  with an explicit reason; estimate numbers come from a local character-count
  approximation of the two artifacts and MUST NOT be presented as measured
  tokens.

The overall report label is:

- `measured` when every scored scenario has measured telemetry,
- `estimate` when none do, and
- `mixed` otherwise (measured claims apply only to the listed measured
  records; the rest remain estimates).

## Half-Populated Records

A telemetry record that advertises `mode=measured` but omits baseline or
TailTrail token totals is treated as untrustworthy. By default it is added to
the ignored list with a reason, and the scenario falls back to the `estimate`
label unless another complete measured record survives. Under `--strict`, the
runner exits with a non-zero status so CI can enforce the invariant.

Complete measured record shape:

```json
{
  "mode": "measured",
  "task_id": "governance-remediation-sample",
  "provider": "sample",
  "model": "sample-model",
  "source": "committed_fake_usage_metadata_for_schema_validation",
  "baseline": {"input_tokens": 1200, "output_tokens": 800},
  "tailtrail": {"input_tokens": 900, "output_tokens": 650}
}
```

Either `total_tokens` alone, or the pair `input_tokens` + `output_tokens`, is
accepted for each block.

## Reproducing A Run

```bash
python3 scripts/tailtrail.py efficacy run
python3 scripts/tailtrail.py efficacy run --scenario governance-remediation
python3 scripts/tailtrail.py efficacy run --portfolio
python3 scripts/tailtrail.py efficacy run --portfolio --strict --format json
python3 scripts/tailtrail.py efficacy run --format json
python3 scripts/tailtrail.py efficacy run --strict --format json
python3 scripts/tailtrail.py efficacy run --write-result
```

`efficacy report` is a friendly alias for `efficacy run` and takes the same
flags. Results can be pinned by pointing `--write-result` at a stable path
under `benchmarks/results/`.

## Honesty Rules

- Do not add sample telemetry with numbers that pretend to reflect real
  provider usage; label sample records as `sample` and note this in the
  `source` field.
- Do not paste raw prompts, source code, secrets, credentials, PII, PHI,
  customer data, or private paths into any artifact in this directory.
- Artifact scoring compares two committed answers; it is not a universal claim
  about any model or vendor.
- Publishing a `measured` result requires a real provider run captured as
  paired baseline and TailTrail usage. TailTrail does not create measured
  telemetry from character counts, file sizes, or estimates.

## CI

The public CI workflow runs the efficacy runner in strict JSON mode on every
manual validation run so schema and labeling regressions fail visibly. See
`.github/workflows/tailtrail-ci.yml` for the exact step.
