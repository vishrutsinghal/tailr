# TailTrail Cheatsheet

Start with `tailtrail start "goal"`. It is planning only until you approve.

| I need to… | Say or run |
| --- | --- |
| Plan a coding task | `tailtrail start "goal"` |
| See a detailed plan | `tailtrail start "goal" --verbose` |
| Plan a large delivery | `tailtrail start "hands-free: goal" --verbose` |
| Tell TailTrail a likely file | `tailtrail start "goal" --changed path/to/file` |
| Ask why scope/files/features were selected | `tailtrail planning discuss --run-id <run-id> --question "Why was this selected?"` |
| Revise a plan | `tailtrail planning revision --run-id <run-id> --request "Keep scope to API and service"` |
| Use standard AIDLC | `tailtrail start "use AIDLC: goal"` |
| Use official Full AIDLC | `tailtrail start "goal" --aidlc full` |
| Map callers and focused tests | `tailtrail graph --changed path/to/file` |
| Plan focused validation | `tailtrail test plan --changed path/to/file` |
| Inspect CI or test output | `tailtrail ci summarize --file ci.log` |
| Inspect Sonar output | `tailtrail sonar summarize --file sonar.log` |
| Check guards before commit | `tailtrail guard check` |
| Validate a dependency decision | `tailtrail dependency validate --root .` |
| Check dependency decisions for a diff | `tailtrail dependency check --root . --diff changes.patch` |
| Get local non-blocking feedback | `python3 hooks/guard-advisory-hook.py --root .` |
| See installation health | `tailtrail install verify --target /path/to/project` |

## Chat phrases

| Say this | TailTrail behavior |
| --- | --- |
| `tailtrail start "goal"` | Planning Lock, no edits. |
| `Approve this plan.` | Activates the existing approved run. |
| `Reject all — <reason>` | Preserves the run and requests requirement feedback. |
| `Use AIDLC Requirements mode` | Collects a stronger requirement boundary before execution. |
| `Use full AIDLC mode` | Uses the approved official workflow bridge when installed. |
| `Why is service.py in scope?` | Opens a read-only evidence-backed plan discussion. |

## Remember

- `start` is the standard entry point; `guide` is advisory only.
- `hands-free` is explicit because it is designed for larger deliveries.
- TailTrail reports real receipts; it does not invent test, CI, token, or
  deployment outcomes.
- On Windows source checkouts, use `py -3 scripts\tailtrail.py …`.

Need setup or update instructions? Go to [INSTALL.md](INSTALL.md).
