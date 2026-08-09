# Requirements

Purpose: turn the request into clear, testable intent.

## Actions

- Capture the original request in `aidlc-docs/audit.md`.
- Separate functional requirements from constraints and assumptions.
- Identify explicit non-goals.
- Identify security, privacy, accessibility, data integrity, performance, reliability, and compliance concerns.
- Create `aidlc-docs/questions.md` when ambiguity affects scope, safety, ownership, data, user experience, deployment, or approval.
- For each question, include meaningful choices, one recommended option, and brief reasoning.
- Check answered questions for missing, invalid, contradictory, or ambiguous responses.

## Outputs

- `aidlc-docs/requirements.md`
- `aidlc-docs/questions.md` when needed
- `aidlc-docs/stage-gate-requirements.md` for standard or comprehensive depth

## TailTrail integration

When TailTrail routes an awaiting-approval Planning Lock into AIDLC, this stage
owns requirement decomposition and questions. TailTrail supplies the saved goal,
proposed requirement boundary, and recorded rejection feedback; it preserves the
run, persists the stage artifact, detects drift, and enforces the approval gate.

Every question must use the `templates/question-file.md` contract: meaningful
choices, a recommended option, and brief reasoning. TailTrail must not replace
this stage with an unrelated generic question generator. Source inspection,
tests, and implementation remain blocked until this stage's revised requirement
boundary is approved.

## Done When

- requirements are clear enough to plan
- assumptions and non-goals are explicit
- open questions are answered or accepted as risk
- approval is recorded when required by depth
