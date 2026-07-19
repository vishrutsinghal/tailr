# Submission Notes

## Track

Developer Tools.

## What This Demo Shows

TailTrail helps Codex work like a disciplined local development partner:

- starts with a Navigator plan
- avoids broad context reads
- maps likely affected files
- preserves validation and safeguards
- recommends focused tests
- reviews code health and requirement fulfillment
- labels evidence clearly
- keeps token-saving claims honest
- turns the live demo into repeatable Evaluation Harness proof

For a fuller capability map, see `FEATURE-COVERAGE.md`.

## What Is New And Meaningful

For Build Week submission, emphasize the recent TailTrail improvements:

- Navigator-default task flow
- adapter compatibility hardening
- evidence-labeled code intelligence
- explicit approval gates for provider-backed metadata
- registry drift validation
- judge-friendly demo workspace
- Evaluation Harness `buildweek-validation` scenario for deterministic baseline-vs-TailTrail proof

## Judge Testing Path

Judges can run the demo without external services:

```bash
python3 scripts/tailtrail.py doctor
python3 -m unittest discover -s buildweek-demo-project/tests
python3 scripts/tailtrail.py start "fix the claim amount validation bug and add focused validation" --root buildweek-demo-project --changed src/claims_api/validation.py
python3 scripts/tailtrail.py graph ast --root buildweek-demo-project --changed src/claims_api/validation.py --depth v2
python3 scripts/tailtrail.py eval scenario report --scenario buildweek-validation
```

No network, external scanners, databases, paid services, or live model calls are required for the core demo or the repeatable proof scenario.

## Clean Pitch Boundary

The strongest safe claim is:

```text
TailTrail gives Codex a local, approval-first development control layer and proves the Build Week story with deterministic saved-artifact evidence.
```

Do not claim the scenario proves live model performance, production defect reduction, scanner replacement, or exact token savings without measured provider telemetry.
