# PM-7 Adoption Validation Requirements

- `PM-7-R1`: Define versioned new-user and experienced-user scenarios with
  explicit participant, repetition, coverage, friction, comprehension, and
  zero-safety-weakening thresholds.
- `PM-7-R2`: Record only approval-gated, sanitized, immutable usability receipts;
  reject raw prompt, source, log, identity, traversal, malformed, stale, and
  tampered data while retaining abandoned and adverse observations.
- `PM-7-R3`: Measure time-to-valid-plan, approvals, redundant approvals,
  abandonment, interventions, false interventions, completion comprehension,
  and safety boundaries per cohort and overall.
- `PM-7-R4`: Keep protocol fixtures out of qualification, fail closed on
  incomplete or invalid evidence, and expose a separate nonzero release gate.
- `PM-7-R5`: Generate wording/default recommendations only after repeated
  independent observed signals; require explicit proposal/decision approval and
  never auto-edit source or weaken a safeguard.
- `PM-7-R6`: Ship canonical CLI and read-only MCP surfaces, schemas, host packs,
  package/release inventories, documentation, and positive, negative, privacy,
  tamper, compatibility, reproducibility, and safety regression tests.

No dependency change is required. Real people and observation evidence cannot
be fabricated by the implementation; until collected, the only valid product
claim is `no-adoption-claim`.
