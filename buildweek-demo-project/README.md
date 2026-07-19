# TailTrail Build Week Demo Project

This is a clean, standalone demo target for showing TailTrail in a competition or product pitch.

It is intentionally small. The goal is to demonstrate how TailTrail helps Codex work on a real repo without overwhelming judges with TailTrail's full source tree.

## Demo Story

The repo contains a small Python claims intake service with one intentional validation bug:

- claim amounts must be positive
- the current implementation allows `0`
- the test suite has a focused failing regression test

TailTrail should help the assistant:

1. Start with Navigator instead of jumping into edits.
2. Inspect the relevant files first.
3. Use the code graph to avoid broad repo reads.
4. Make the smallest validation fix.
5. Run focused tests.
6. Review the implementation against the original requirement.
7. Produce evidence and token posture without claiming exact savings.
8. Show repeatable Evaluation Harness proof through the committed `buildweek-validation` scenario.

## Quick Commands

From the TailTrail repo root:

```bash
python3 scripts/tailtrail.py start "fix the claim amount validation bug and add focused validation" --root buildweek-demo-project --changed src/claims_api/validation.py
python3 scripts/tailtrail.py graph ast --root buildweek-demo-project --changed src/claims_api/validation.py --depth v2
python3 scripts/tailtrail.py test plan --root buildweek-demo-project --changed src/claims_api/validation.py --goal "fix zero amount validation"
python3 -m unittest discover -s buildweek-demo-project/tests
python3 scripts/tailtrail.py review --root buildweek-demo-project
python3 scripts/tailtrail.py report value --root buildweek-demo-project
python3 scripts/tailtrail.py eval scenario report --scenario buildweek-validation
```

For copy-paste prompts to use during the demo, see `DEMO-PROMPTS.md`.

For the full capability map, see `FEATURE-COVERAGE.md`.

## Repeatable Proof Scenario

The live demo workspace is backed by a deterministic Evaluation Harness scenario:

```bash
python3 scripts/tailtrail.py eval scenario report --scenario buildweek-validation
python3 scripts/tailtrail.py eval scenario report --scenario buildweek-validation --format json
```

Use this when judges or reviewers ask for repeatable evidence. It compares a baseline artifact with a TailTrail-guided artifact and keeps the claim boundary explicit: committed fixture evidence only, not live model performance or exact token savings.

## Optional Evidence Demos

```bash
python3 scripts/tailtrail.py ci summarize --file buildweek-demo-project/logs/ci-failure.log
python3 scripts/tailtrail.py sonar summarize --file buildweek-demo-project/logs/sonar-sample.log
python3 scripts/tailtrail.py vulnerability summarize --file buildweek-demo-project/logs/trivy-sample.json
python3 scripts/tailtrail.py graph ast --root buildweek-demo-project --changed src/claims_api/validation.py --depth v3 --provider-output buildweek-demo-project/tailtrail-meta/providers/sample-semantic.json --approved
```

## Expected Initial Test Result

One test should fail before the fix:

```text
test_rejects_zero_amount ... FAIL
```

After fixing `validate_claim_amount`, all tests should pass.

## Pitch Line

TailTrail turns Codex from a prompt-by-prompt coding assistant into a local development control layer: Navigator-first planning, code graph context, approval gates, focused tests, review, evidence labels, repeatable Evaluation Harness proof, and measured-or-estimated value reporting.
