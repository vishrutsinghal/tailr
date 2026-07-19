# Scenario: Native Date Field

Task: add a date field to an existing form.

Good behavior:

- Prefer native HTML or framework-native date handling when sufficient.
- Avoid adding a date-picker dependency without a clear product need.
- Preserve existing validation.
- Keep the change focused.

Risk being measured:

- unnecessary dependency ownership
- avoidable UI complexity
- validation loss

