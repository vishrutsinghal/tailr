# Reverse Engineering

Purpose: understand existing behavior before changing a brownfield system.

## Use When

- the codebase is unfamiliar
- the requested change touches existing flows
- behavior is only visible through symptoms
- ownership boundaries or callers are unclear

## Actions

- Trace the current user or data flow.
- Identify important callers, tests, shared helpers, and configuration.
- Record behavior that must not regress.
- Find the shared root cause before patching a visible symptom.
- Keep exact source text for files that may be edited.

## Outputs

- `aidlc-docs/reverse-engineering.md` for standard or comprehensive depth
- `context/change-impact.md` for compact impact
- updated state and audit

## Done When

- the current behavior is explained
- likely root cause and affected callers are known
- regression-sensitive guards are named
- the next stage can plan from evidence, not guesswork
