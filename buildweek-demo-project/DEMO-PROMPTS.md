# TailTrail Build Week Demo Prompts

Use these prompts from the TailTrail repo root:

```bash
cd /Users/vsingha7/Documents/tailtrail
```

The demo target is:

```text
buildweek-demo-project
```

## 1. Open With The Problem

Prompt:

```text
I am demoing TailTrail on buildweek-demo-project. First show the current bug by running the focused unit tests. Do not fix anything yet.
```

Expected command:

```bash
python3 -m unittest discover -s buildweek-demo-project/tests
```

Expected result:

```text
FAILED (failures=1)
AssertionError: ClaimValidationError not raised
```

## 2. Navigator Plan Only

Prompt:

```text
Run TailTrail Navigator first for this task:
fix the claim amount validation bug and add focused validation

Use root buildweek-demo-project and changed file src/claims_api/validation.py.
Show the plan only. Do not implement until I approve.
```

Expected command:

```bash
python3 scripts/tailtrail.py start "fix the claim amount validation bug and add focused validation" --root buildweek-demo-project --changed src/claims_api/validation.py
```

What to show in the demo:

- Navigator-first plan
- files to inspect first
- graph/code intelligence suggestion
- approval-first behavior
- post-change review prompt
- token/evidence posture

## 3. Code Graph Before Editing

Prompt:

```text
Use TailTrail Code Graph for buildweek-demo-project before editing. Map src/claims_api/validation.py at Semantic V2 depth and explain the likely impacted tests and callers.
```

Expected command:

```bash
python3 scripts/tailtrail.py graph ast --root buildweek-demo-project --changed src/claims_api/validation.py --depth v2
```

What to show:

- `validate_claim_amount`
- likely test: `tests/test_claim_validation.py`
- changed symbol impact
- evidence labels: `heuristic` and `local-ast`

## 4. Optional Provider-Backed Evidence

Prompt:

```text
Use TailTrail Semantic V3 on buildweek-demo-project with the approved local provider output. Show how provider-backed evidence is labeled. Do not run external providers.
```

Expected command:

```bash
python3 scripts/tailtrail.py graph ast --root buildweek-demo-project --changed src/claims_api/validation.py --depth v3 --provider-output buildweek-demo-project/tailtrail-meta/providers/sample-semantic.json --approved
```

What to show:

- `## Semantic V3`
- `provider-backed` evidence count
- provider output is local JSON only
- no JDT, Roslyn, LSP, SCIP, tree-sitter, network, or MCP provider is auto-run

## 5. Approve The Fix

Prompt:

```text
Approve the TailTrail plan. Implement the smallest maintainable fix in buildweek-demo-project so zero claim amounts are rejected. Read only the target validation file and focused test unless you need more context. Do not add dependencies. Preserve existing validation behavior.
```

Expected code change:

- Change the amount guard from `amount < 0` to `amount <= 0` so zero-dollar claims raise `ClaimValidationError("claim amount must be positive")`.

Target file:

```text
buildweek-demo-project/src/claims_api/validation.py
```

## 6. Focused Validation

Prompt:

```text
Run the focused validation for buildweek-demo-project and show the result. Do not claim success unless the command passes.
```

Expected command:

```bash
python3 -m unittest discover -s buildweek-demo-project/tests
```

Expected result after fix:

```text
Ran 3 tests
OK
```

## 7. TailTrail Review After The Fix

Prompt:

```text
Use TailTrail Review after the fix. Review the changed demo project scope for code health and requirement fulfillment. Confirm whether the implementation satisfies the original request: zero claim amounts must be rejected. Show severity, file, function, line, issue, fix, validation, confidence, and residual risk.
```

Useful command:

```bash
python3 scripts/tailtrail.py review --root buildweek-demo-project
```

What to show:

- review is post-change
- review checks requirement fulfillment, not only generic code health
- no safe-fix should be applied without approval

## 8. CI Failure Summary

Prompt:

```text
Use TailTrail CI summary on the sample failing CI log for buildweek-demo-project. Preserve exact command, test name, and failure message.
```

Expected command:

```bash
python3 scripts/tailtrail.py ci summarize --file buildweek-demo-project/logs/ci-failure.log
```

What to show:

- command detected
- failing test detected
- exact assertion preserved
- next action is focused

## 9. Token / Value Honesty

Prompt:

```text
Use TailTrail value reporting for buildweek-demo-project. Show the value posture, but keep token savings honest: estimated unless measured telemetry is provided.
```

Expected command:

```bash
python3 scripts/tailtrail.py report value --root buildweek-demo-project
```

What to say:

```text
TailTrail reports local estimates unless measured model/API telemetry is provided. That keeps product claims defensible.
```

## 10. Repeatable Build Week Proof

Prompt:

```text
Show the repeatable TailTrail Build Week proof scenario. Use Evaluation Harness and keep the claim boundaries clear.
```

Expected command:

```bash
python3 scripts/tailtrail.py eval scenario report --scenario buildweek-validation
```

Optional JSON command:

```bash
python3 scripts/tailtrail.py eval scenario report --scenario buildweek-validation --format json
```

What to show:

- `tailtrail` is the winning variant.
- The scenario uses committed saved artifacts only.
- The report includes claim boundaries.
- It does not run live agents, tests, scanners, package managers, CI, or model APIs.
- It does not claim exact token savings without measured telemetry.

## 11. Final Pitch Prompt

Prompt:

```text
Summarize this TailTrail demo for Build Week judges in 45 seconds. Focus on the problem, the workflow, the repeatable evidence, and why this helps developers using Codex.
```

Expected talking points:

- Codex is powerful, but local development can drift without structure.
- TailTrail adds Navigator-first planning.
- Code graphing narrows context before edits.
- Guardrails and policy preserve safety.
- Focused tests validate the change.
- Review checks code health and requirement fulfillment.
- Evidence labels make claims clear.
- Evaluation Harness turns the Build Week demo into repeatable saved-artifact proof.
- Token savings are estimated unless measured telemetry exists.

## Short One-Shot Demo Prompt

Use this if time is limited:

```text
Use TailTrail on buildweek-demo-project to demo an end-to-end safe Codex workflow. First run the failing tests, then show the Navigator plan for fixing src/claims_api/validation.py, then show the code graph, then wait for my approval before implementing the smallest fix. If there is time, finish by showing the Evaluation Harness buildweek-validation proof scenario.
```

Expected command sequence:

```bash
python3 -m unittest discover -s buildweek-demo-project/tests
python3 scripts/tailtrail.py start "fix the claim amount validation bug and add focused validation" --root buildweek-demo-project --changed src/claims_api/validation.py
python3 scripts/tailtrail.py graph ast --root buildweek-demo-project --changed src/claims_api/validation.py --depth v2
python3 scripts/tailtrail.py eval scenario report --scenario buildweek-validation
```
