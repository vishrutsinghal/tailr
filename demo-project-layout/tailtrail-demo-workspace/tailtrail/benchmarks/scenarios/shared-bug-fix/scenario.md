# Scenario: Shared Bug Fix

Task: one visible caller reports incorrect formatting, but the formatter is shared.

Good behavior:

- Inspect shared helper/caller boundary.
- Fix the common path when it is the root cause.
- Avoid a one-off patch at the visible caller.
- Name a focused check.

Risk being measured:

- symptom patching
- duplicate logic
- missed caller impact

