# Demo Runbook

Target length: 2 minutes 45 seconds total, including the repeatable proof scenario.

Copy-paste prompts for each step are in `DEMO-PROMPTS.md`.

## 1. Problem Setup

Say:

```text
This is a small claims intake service. A regression test shows that zero-dollar claims are incorrectly accepted. I will use TailTrail to guide Codex through a safer local development workflow.
```

Run:

```bash
python3 -m unittest discover -s buildweek-demo-project/tests
```

Expected:

```text
FAILED
```

## 2. Navigator First

Run:

```bash
python3 scripts/tailtrail.py start "fix the claim amount validation bug and add focused validation" --root buildweek-demo-project --changed src/claims_api/validation.py
```

Show:

- recommended path
- files to inspect first
- post-change review prompt
- Code Intelligence section
- approval-first behavior

## 3. Code Graph

Run:

```bash
python3 scripts/tailtrail.py graph ast --root buildweek-demo-project --changed src/claims_api/validation.py --depth v2
```

Show:

- symbols
- local-ast and heuristic evidence labels
- likely tests
- changed symbol impact

## 4. Fix With Codex And GPT-5.6

Ask Codex:

```text
Approve the TailTrail plan. Make the smallest change to reject zero claim amounts. Do not change unrelated files.
```

Say:

```text
Codex using GPT-5.6 now works from the approved plan and focused context, rather than a broad repo read.
```

Expected code change:

- Change the amount guard from `amount < 0` to `amount <= 0` so zero-dollar claims raise `ClaimValidationError("claim amount must be positive")`.

## 5. Validate And Review

Run:

```bash
python3 -m unittest discover -s buildweek-demo-project/tests
python3 scripts/tailtrail.py review --root buildweek-demo-project
```

Show:

- focused tests passing
- review checks code health and requirement fulfillment

## 6. Repeatable Proof Scenario

Run:

```bash
python3 scripts/tailtrail.py eval scenario report --scenario buildweek-validation
```

Show:

- TailTrail wins the committed scenario comparison.
- The scenario is local, deterministic, and fixture-backed.
- Claim boundaries are explicit: no live model-performance claim and no exact token-savings claim without measured telemetry.

Say:

```text
The live demo is human-readable, and the Evaluation Harness scenario makes the same story repeatable for judges and enterprise reviewers.
```

## 7. Close

Say:

```text
The product is not just a script. It is a repeatable local workflow for safer Codex development: plan, inspect, change, test, review, prove, learn, and report.
```
