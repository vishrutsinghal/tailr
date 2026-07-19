# TailTrail Quickstart

Use this page when you want the shortest path from a real task to the right TailTrail workflow.

## Install (Optional)

No install is required for the portable workflow. The docs keep `python3 scripts/tailtrail.py ...` as the always-available fallback.

If you want a `tailtrail` command on `PATH` from this checkout:

```bash
pipx install .          # provides `tailtrail` on PATH
pip install --user .    # alternative, same result
```

After install, `tailtrail do "goal"` and `tailtrail start "goal"` delegate to the same source-tree dispatcher as `python3 scripts/tailtrail.py do "goal"` and `python3 scripts/tailtrail.py start "goal"`.

## Choose a surface (optional)

Managed TailTrail packs support two file-breadth surfaces:

- `--surface core` -> minimal first-run pack: `start`, Navigator, guardrails, governance, adapters, and quick docs.
- `--surface extended` -> everything, and the default: reporting, learning, benchmarks, meta-harness, quality, security, AIDLC, hooks, and token tools.

Examples:

```bash
python3 scripts/tailtrail.py install codex --target /path/to/project --dry-run
python3 scripts/tailtrail.py install codex --target /path/to/project
python3 scripts/tailtrail.py install copilot --target /path/to/project --surface core
python3 scripts/tailtrail.py install local --target /path/to/project --profile copilot --surface core
python3 scripts/tailtrail.py install status --target /path/to/project
python3 scripts/tailtrail.py install upgrade-to-extended --target /path/to/project
```

Use Core for low-friction onboarding or demos where the user only needs the first-run workflow. Use Extended when the repo needs learning, reporting, scanner intelligence, AIDLC, benchmarks, hooks, or meta-harness features. Existing installs stay Extended unless you explicitly choose Core.

## Start Here

For almost every non-trivial task, begin with:

```bash
python3 scripts/tailtrail.py do "describe your task"
python3 scripts/tailtrail.py start "describe your task"
```

Example:

```bash
python3 scripts/tailtrail.py do "fix Sonar cognitive complexity in PaymentValidator"
```

If you already know the likely file:

```bash
python3 scripts/tailtrail.py do "fix Sonar cognitive complexity" --changed src/main/java/com/acme/PaymentValidator.java
```

`do` is the daily alias for `start`. Free-form input such as `python3 scripts/tailtrail.py "fix Sonar cognitive complexity"` also routes to `start`. `start` runs Navigator first and returns a plan before implementation. Review the plan, edit it if needed, then approve the work. TailTrail does not implement, run scanners, capture learnings, or change files just because `start` was run.

The default Start report is compact. It shows the recommended path, files to inspect first, key commands, post-change Review, Meta-Harness checks, token/evidence posture, and approval prompts. Use `--verbose` when you want the full Navigator plan:

```bash
python3 scripts/tailtrail.py start "fix Sonar cognitive complexity" --changed src/main/java/com/acme/PaymentValidator.java --verbose
```

## Choose By Task

| I need to... | Use this first |
|---|---|
| Start a coding task | `python3 scripts/tailtrail.py do "goal"` or `python3 scripts/tailtrail.py start "goal"` |
| Show the full Start plan | `python3 scripts/tailtrail.py start "goal" --verbose` |
| Get only the plan | `python3 scripts/tailtrail.py guide "goal"` |
| Review a changed file | `python3 scripts/tailtrail.py graph --changed path/to/file` |
| Check local guardrails before commit | `python3 scripts/tailtrail.py guard check` |
| Enforce high-severity guardrails | `python3 scripts/tailtrail.py guard check --enforce` |
| Summarize CI/build/test logs | `python3 scripts/tailtrail.py ci summarize --file ci.log` |
| Summarize Sonar/static-analysis output | `python3 scripts/tailtrail.py sonar summarize --file sonar.log` |
| Summarize vulnerability/audit output | `python3 scripts/tailtrail.py vulnerability summarize --file audit.log` |
| Connect scanner output to impact | `python3 scripts/tailtrail.py graph overlay --sonar sonar.log --changed path/to/file` |
| Find likely local quality checks | `python3 scripts/tailtrail.py quality scan --root .` |
| Run one approved local check | `python3 scripts/tailtrail.py quality run --approved --command "exact command"` |
| Check a cloned repo for TailTrail files | `python3 scripts/tailtrail.py setup-scan --root .` |
| Use TailTrail from an MCP-capable assistant | `python3 scripts/tailtrail.py mcp tools` |

## Common Workflows

Bug fix:

```bash
python3 scripts/tailtrail.py start "fix null handling in claim mapper" --changed src/claims/mapper.py
python3 scripts/tailtrail.py guard check
```

Sonar issue:

```bash
python3 scripts/tailtrail.py sonar summarize --file sonar.log
python3 scripts/tailtrail.py graph overlay --sonar sonar.log --changed src/service/foo.py
python3 scripts/tailtrail.py start "fix Sonar issue" --changed src/service/foo.py
```

Vulnerability issue:

```bash
python3 scripts/tailtrail.py vulnerability summarize --file audit.log
python3 scripts/tailtrail.py graph overlay --vulnerability audit.log --changed package.json
python3 scripts/tailtrail.py start "plan vulnerability remediation" --changed package.json
```

Before commit:

```bash
python3 scripts/tailtrail.py guard check
python3 scripts/tailtrail.py guard check --enforce
python3 scripts/tailtrail.py guard check --fail-on dependency-gate,local-state
```

Turn on enforcement only when a repo is ready for it. See `GUARDRAILS.md` for the optional `--fail-on` classes and the minimal pre-commit configuration.

MCP-capable assistant:

```bash
python3 scripts/tailtrail.py mcp doctor
python3 scripts/tailtrail.py mcp tools
python3 scripts/tailtrail.py mcp serve
```

MCP is optional and read-only. It exposes Navigator, Start report, guardrail check, graph map, and install status tools to MCP hosts. It does not implement code, run scanners, fix files, upload telemetry, or replace user approval.

## What To Read Next

- Use `CHEATSHEET.md` for a one-page command map.
- Use `USER-GUIDE.md` for full installation and feature usage.
- Use `TAILTRAIL-COMMANDS.md` for the complete command catalog.
- Use `ROADMAP.md` only when planning TailTrail product development.

## Boundaries

TailTrail helps with local, evidence-aware AI coding workflows. It does not replace source inspection, tests, CI, scanners, code review, security review, legal review, or release approval.
