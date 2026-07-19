# Testing Baseline

Use this extension when behavior changes, guards are touched, or risk is not trivial.

## Check

- One focused check covers the changed behavior.
- Existing related tests are reused where possible.
- Regression-sensitive guards are tested or explicitly reviewed.
- Build, lint, or type checks are run when project policy requires them.
- Noisy output is summarized with exact first failure preserved.

## Handoff

Record command, exit status, first relevant failure, and remaining validation gap in `aidlc-docs/validation-handoff.md`.
