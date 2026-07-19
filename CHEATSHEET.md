# TailTrail Cheatsheet

The default first command is:

```bash
python3 scripts/tailtrail.py start "goal"
```

## Problem To Command

| Problem | Command |
|---|---|
| I have a coding task. | `python3 scripts/tailtrail.py start "goal"` |
| I want the full Start plan. | `python3 scripts/tailtrail.py start "goal" --verbose` |
| I want only a plan. | `python3 scripts/tailtrail.py guide "goal"` |
| I know the file involved. | `python3 scripts/tailtrail.py start "goal" --changed path/to/file` |
| I want a focused impact map. | `python3 scripts/tailtrail.py graph --changed path/to/file` |
| I want deeper symbol hints. | `python3 scripts/tailtrail.py graph ast --changed path/to/file --depth v1` |
| I have CI/build/test logs. | `python3 scripts/tailtrail.py ci summarize --file ci.log` |
| I have Sonar output. | `python3 scripts/tailtrail.py sonar summarize --file sonar.log` |
| I have vulnerability output. | `python3 scripts/tailtrail.py vulnerability summarize --file audit.log` |
| I want scanner impact. | `python3 scripts/tailtrail.py graph overlay --sonar sonar.log --changed path/to/file` |
| I want local check discovery. | `python3 scripts/tailtrail.py quality scan --root .` |
| I want precise test guidance. | `python3 scripts/tailtrail.py test plan --changed src/service/foo.py` |
| I want to run one approved check. | `python3 scripts/tailtrail.py quality run --approved --command "exact command"` |
| I want guardrail checking. | `python3 scripts/tailtrail.py guard check` |
| I want guardrail blocking. | `python3 scripts/tailtrail.py guard check --enforce` |
| I cloned a repo with TailTrail files. | `python3 scripts/tailtrail.py setup-scan --root .` |
| I need AIDLC artifacts. | `python3 scripts/tailtrail.py aidlc init --root . --depth standard` |
| I want to capture an outcome. | `python3 scripts/tailtrail.py outcome capture ... --approved` |
| I want a local enterprise report. | `python3 scripts/tailtrail.py report --month YYYY-MM` |
| I want token savings evidence. | `python3 scripts/tailtrail.py savings report --telemetry .tailtrail/token-usage.jsonl` |
| I want package health checks. | `python3 scripts/tailtrail.py doctor` |

## Short Phrases For Assistants

Use these in chat when an assistant has TailTrail instructions loaded:

| Phrase | Intent |
|---|---|
| `Use TailTrail start.` | Let Navigator choose the workflow. |
| `Use TailTrail review.` | Review for scope, safeguards, dependencies, and validation gaps. |
| `Use AIDLC.` | Use lifecycle artifacts for broader or risky work. |
| `Use dependency gate.` | Challenge dependency changes before adding packages. |
| `Use handoff.` | Produce review/continuation evidence. |
| `Use release flow.` | Prepare validation, risk, rollback, and owner notes. |

## Remember

- `start` is the safest first command.
- `start` is compact by default and includes post-change Review plus Meta-Harness next steps.
- `start --verbose` shows the full Navigator plan.
- `guide` is plan-only.
- `guard check` is local enforcement-lite.
- `quality run` and scanner runs require explicit approval.
- Exact token savings require measured model/API telemetry.
- TailTrail is advisory unless a command explicitly uses enforce/approved behavior.
