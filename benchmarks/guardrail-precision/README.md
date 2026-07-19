# Guardrail Precision Baseline

This benchmark measures TailTrail guardrail precision on committed fixtures. It exists so class-scoped enforcement through `--fail-on` has evidence behind it.

Run it locally:

```bash
python3 scripts/tailtrail.py guardrail precision
python3 scripts/tailtrail.py guardrail precision --strict --format json
python3 scripts/tailtrail.py guardrail precision --rule dependency-gate
```

## Protocol

Each fixture is a `.diff` file with a matching `.meta.json` file. Labels are `expected-finding` or `expected-clean`. Rules use the BL-5 canonical class names: `dependency-gate`, `safeguard-removal`, `local-state`, and `validation-claim`.

The runner reports precision, recall, false-positive rate, fixture count, confidence, threshold, and status per rule. Results are evidence-labeled as `committed-fixture`, matching TailTrail's measured-evidence discipline from BL-1.

## Honesty Rules

- No real credentials, tokens, secrets, PII, customer paths, or private repo names.
- Keep fixtures short and self-contained.
- `expected-clean` fixtures should be near misses, not obviously unrelated diffs.
- Do not mutate fixtures during the run.
- Do not present these numbers as universal precision for all repositories.

## Adding Fixtures

Add one `.diff` file and one `.meta.json` file under the relevant rule and label folder. The metadata must include `id`, `label`, `rule`, `summary`, `extra_texts`, and `notes`.

## Changing Thresholds

Thresholds live in `thresholds.json`. Lowering a threshold requires an explicit explanation in the same PR. Raising a threshold should be backed by additional fixtures or measured stability over time.
