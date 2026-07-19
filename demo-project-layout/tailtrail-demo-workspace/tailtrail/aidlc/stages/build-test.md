# Build And Test

Purpose: produce trustworthy validation evidence without flooding context.

## Actions

- Run the smallest relevant validation first.
- Run broader validation when risk, depth, or project policy requires it.
- Summarize noisy output with `templates/tool-summary.md`.
- Keep exact failing lines for diagnosis.
- Record commands, exit status, first relevant failure, changed files, and next action.

## Outputs

- `aidlc-docs/validation-handoff.md`
- updated `aidlc-docs/aidlc-state.md`
- updated audit entry

## Done When

- validation evidence is recorded
- failures have next actions or accepted risk
- output is summarized without losing exact failure detail
- closeout approval is ready when required
