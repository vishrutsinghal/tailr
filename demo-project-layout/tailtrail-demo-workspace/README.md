# TailTrail Demo Workspace

This is a tiny, synthetic workspace for demonstrating TailTrail. It is intentionally small: one service, one validation bug, one test story, and one TailTrail walkthrough.

The demo shows how TailTrail helps an assistant plan before changing code, reuse local context through Code Graph Mapper, plan focused tests, prepare review/handoff notes, and capture learnings only after approval.

## What Is Included

```text
tailtrail-demo-workspace/
  README.md
  DEMO-SCRIPT.md
  DEMO-DATA.md
  tailtrail/
  services/
    claims-api/
  shared/
    validation-rules/
    sql/
  infra/
    terraform/
  ci/
  docs/
    architecture/
    aidlc/
    handoff/
  .tailtrail/
```

## Demo Service

`services/claims-api` is a dependency-free Python service. It has:

- one HTTP endpoint in `src/claims_api/app.py`
- one validation module in `src/claims_api/validation.py`
- one config file in `config/settings.json`
- one small unit-test suite in `tests/test_validation.py`
- one intentional validation bug for TailTrail to find and plan around

The intentional bug: `validate_claim` currently allows a claim amount of `0`. Demo policy says amount must be greater than `0`.

## Quick Commands

From this workspace:

```bash
python3 services/claims-api/tests/test_validation.py
python3 services/claims-api/src/claims_api/app.py
```

From the TailTrail repo root, use the real TailTrail wrapper against this demo workspace:

```bash
python3 scripts/tailtrail.py hello
python3 scripts/tailtrail.py guide "tell me important features of this repo" --root demo-project-layout/tailtrail-demo-workspace
python3 scripts/tailtrail.py guide "fix claim amount validation and add focused tests" --root demo-project-layout/tailtrail-demo-workspace --changed services/claims-api/src/claims_api/validation.py --changed services/claims-api/tests/test_validation.py --view compact
```

## Demo Rules

- Keep all data synthetic.
- Do not add external dependencies.
- Do not run scanners, tests, builds, graph mapping, or learning capture unless the presenter explicitly approves the command.
- Use TailTrail Navigator before implementation prompts.
- Use Code Graph Mapper before broad source reads when the task is meaningful code work.
- Capture learning only after the user accepts the outcome or reviewer feedback is known.

