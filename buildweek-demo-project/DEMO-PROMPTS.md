# TailTrail Build Week Demo Prompts

Use these prompts from the TailTrail repo root:

```bash
cd /Users/vsingha7/Documents/tailtrail
```

The demo target is:

```text
buildweek-demo-project
```

## Inspiration

This project started from the same frustrations I keep seeing in AI-assisted coding:

- Long prompts can actually make things worse. The AI gets distracted, loses the important bits, and starts wandering off the actual task.
- When the context gets too heavy, the code quality drops. Instead of a simple fix, the assistant often rewrites things, adds redundant helpers, or invents a whole new path.
- Small tasks become overkill. A tiny validation change turns into a new method, a long refactor, and a bunch of extra lines that weren’t needed.
- Token anxiety is real. People worry whether there’s enough left, whether the prompt is too expensive, and whether the model will still have the key details.

TailTrail is my answer to that. It’s not about forcing the AI to be perfect—it’s about giving it a clean, structured way in:

- start with a navigator-first plan,
- keep the scope tight,
- limit the prompt to the real change,
- use code graphing to find the right files,
- and keep token posture honest.

That’s the story behind this demo.

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

- Codex is powerful, but without structure it can wander off, overcomplicate small fixes, and lose the real goal.
- TailTrail keeps the workflow grounded: start with a plan, not a random code rewrite.
- Navigator-first planning makes the next step obvious and keeps the AI focused on the exact change.
- Code graphing finds the right files and tests before editing, so we don’t patch the wrong place.
- Guardrails and policy make the workflow safer, not harder—they help avoid risky or unsupported changes.
- Focused tests prove the fix, and the demo shows validation before we claim success.
- Review is about requirement fulfillment, not just generic style advice.
- Evidence labels keep the story honest: what was estimated, what was validated, and what is local proof.
- Evaluation Harness turns this into repeatable saved-artifact proof, not a one-time live demo.
- TailTrail respects token concerns by keeping claims honest and only talking about exact savings when real telemetry exists.
- It’s designed to make simple changes stay simple, while still giving the AI enough structure to be useful.

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
