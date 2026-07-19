# Design

Purpose: add design detail only when the implementation boundary needs it.

## Use When

- new components, APIs, data contracts, or infrastructure are introduced
- NFRs affect implementation
- multiple units must coordinate
- migrations, rollback, or production behavior matter

## Actions

- Describe the smallest design that satisfies requirements.
- Reuse existing architecture, naming, validation, and error-handling patterns.
- Capture alternatives only when they explain a meaningful decision.
- Record NFR handling for security, privacy, performance, reliability, observability, accessibility, and operability when relevant.
- Apply `DEPENDENCY-GATE.md` before adding packages or services.

## Outputs

- `aidlc-docs/design.md`
- `aidlc-docs/nfr-notes.md` when needed
- `aidlc-docs/stage-gate-design.md` for standard or comprehensive depth

## Done When

- the implementation boundary is clear
- important tradeoffs are recorded
- new dependencies are approved or rejected
- coding can proceed without inventing architecture mid-change
