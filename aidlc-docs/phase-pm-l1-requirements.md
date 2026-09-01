# PM-L1 Learning V3 Contract And Migration Requirements

Status: implemented under the user's explicit PM-L1 implementation authority on 2026-09-01.

## Scope

PM-L1 replaces new candidate and curated-learning writes with one append-only,
project-framed V3 contract. It preserves legacy stores and readers, and migrates
eligible legacy candidates only by sanitized reference. Navigator ranking and
conflict gating remain PM-L2; use receipts remain PM-L3; first-class conflict
and negative-learning transitions remain PM-L4.

## Requirements

- **PM-L1-R1 — Closed V3 contract:** every record contains versioned learning
  class, provenance, applicability, freshness, utility, content, privacy,
  lifecycle, and digest-chain domains with no undeclared fields.
- **PM-L1-R2 — Append-only lifecycle:** creation, amendment, supersession, and
  revocation append records with contiguous sequence numbers, an exact previous
  record, and a SHA-256 chain. Terminal records cannot be changed.
- **PM-L1-R3 — Canonical writes:** Learning Agent capture, closure candidates,
  curated promotion, and the legacy curated command write a valid V3 record
  before emitting a legacy compatibility projection.
- **PM-L1-R4 — Deterministic readers:** V3 state and validation are strict;
  compatibility reads combine active V3 state with unmigrated legacy events,
  deduplicate references, and hide superseded or revoked records.
- **PM-L1-R5 — Preservation migration:** migration is idempotent, approval-gated
  for writes, supports a non-mutating dry run, retains the legacy bytes, and
  copies only a sanitized candidate plus relative applicability and a source
  line/fingerprint.
- **PM-L1-R6 — Privacy:** reject sensitive candidate text, raw-prompt flags,
  absolute or parent-traversing paths, raw source/log/prompt fields, identity
  fields, and records outside the current pseudonymous repository frame.
- **PM-L1-R7 — Compatibility:** retain `.tailtrail/learning-events.jsonl` and
  `.tailtrail/learnings.md` readers/projections for at least two releases; do
  not silently delete or rewrite them.
- **PM-L1-R8 — Assurance and distribution:** integrate the contract into
  maturity validation, package/release manifests, registry ownership, command
  documentation, and focused positive and hostile tests.

No dependency is added or changed; the dependency gate is not triggered.
