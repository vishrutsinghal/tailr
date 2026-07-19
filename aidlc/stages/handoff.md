# Handoff

Purpose: let another developer, reviewer, agent, or operations owner continue without rediscovering the work.

## Handoff Types

- **Change handoff**: pre-change alignment using `templates/change-brief.md`.
- **Diff handoff**: post-change review package using `templates/diff-handoff.md`.
- **Validation handoff**: build/test evidence using `templates/validation-handoff.md`.
- **Operations handoff**: deployment, monitoring, rollback, and support notes using `templates/operations-notes.md`.

## Required Content

- task and lifecycle depth
- current phase and stage
- changed files and relevant read-only files
- requirements satisfied
- helpers and conventions reused
- dependency decision
- guardrails preserved
- validation run and validation gaps
- known risks and follow-up
- next owner or approval needed

## Done When

- a reviewer can understand the change without reading every artifact
- exact source, diff, config, and command details can be reopened
- skipped work and residual risk are explicit
- state points to the next action
