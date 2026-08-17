# TailTrail Quickstart

Use this page after [installing TailTrail](INSTALL.md). For a full command
catalog, use [TAILTRAIL-COMMANDS.md](TAILTRAIL-COMMANDS.md).

## One command to begin

In an AI host with TailTrail installed, say:

```text
tailtrail start "describe the change you need"
```

For Copilot, `/tailtrail-start "describe the change you need"` is also a
convenient entry point.

TailTrail creates a Planning Lock. It plans only; no source, tests, scanners,
or Git changes run until you approve.

## What happens next

1. Read the requirements, scope, selected TailTrail features, and focused
   validation shown in the plan.
2. Ask questions or revise the plan if something is unclear.
3. Approve the same run when it is right.
4. TailTrail scopes implementation and returns one Completion Report with
   requirement status, evidence, drift, recovery posture, and token posture.

Example:

```text
tailtrail start "fix the zero quantity validation defect and add focused validation"
```

```text
Approve this plan. Implement the smallest maintainable change and run the focused validation.
```

## When to use options

| Need | Use |
| --- | --- |
| A normal feature or bug fix | `tailtrail start "goal"` |
| More planning detail | `tailtrail start "goal" --verbose` |
| You know a likely file | `tailtrail start "goal" --changed path/to/file` |
| A large delivery split into slices | `tailtrail start "hands-free: goal" --verbose` |
| A full official lifecycle | `tailtrail start "goal" --aidlc full` |
| Only a lightweight recommendation | `tailtrail guide "goal"` |

## If you use the source checkout directly

Use the same commands through the portable CLI:

```bash
python3 scripts/tailtrail.py start "fix the zero quantity validation defect"
python3 scripts/tailtrail.py start "fix the zero quantity validation defect" --verbose
```

On Windows, replace `python3` with `py -3` and forward slashes with backslashes
where appropriate.

## Before you commit

```bash
python3 scripts/tailtrail.py guard check
python3 scripts/tailtrail.py dependency validate --root .
```

Use the advisory local hook for a combined summary:

```bash
python3 hooks/guard-advisory-hook.py --root .
```

## Next page

- [CHEATSHEET.md](CHEATSHEET.md) — I have a specific problem; what command fits?
- [USEFUL-PROMPTS.md](USEFUL-PROMPTS.md) — copyable prompts for common tasks.
- [INSTALL.md](INSTALL.md) — installation, host profile, updates, and verification.
