# Implementation

Purpose: make the approved change with exact source context and focused validation.

## Actions

- Read exact source files before editing.
- Reuse project helpers, conventions, and tests.
- Keep diffs small and reviewable.
- Preserve validation, authorization, escaping, accessibility, data integrity, and error handling.
- Add or update one focused check for non-trivial logic.
- Update state and audit after meaningful progress.

## Outputs

- code changes in the application repo
- `aidlc-docs/implementation-plan.md` before coding for standard or comprehensive depth
- `aidlc-docs/diff-handoff.md` after coding

## Done When

- the change matches approved requirements
- dependency decisions are recorded
- focused validation exists or the gap is documented
- diff handoff is ready for review
