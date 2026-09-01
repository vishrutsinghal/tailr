# PM-L0 Learning Inventory And Ownership Requirements

Status: implemented under the user's explicit PM-L0 implementation authority on 2026-09-01.

## Scope

PM-L0 inventories the existing learning and learning-adjacent control plane,
assigns canonical ownership, and defines compatibility and migration boundaries.
It does not introduce the PM-L1 Learning V3 record, PM-L3 use receipts, or PM-L4
conflict ledger.

## Requirements

- **PM-L0-R1 — Complete inventory:** cover Learning Agent, closure learning,
  Debug candidates, graph learning, refresh and review, Quality Loop, Evaluation
  Harness, Meta-Harness, Outcome Telemetry, and workflow learning links, including
  their commands, source modules, and persistent artifacts.
- **PM-L0-R2 — Fact ownership:** assign exactly one canonical owner and artifact
  to candidate, curated learning, use receipt, freshness action, conflict, and
  observed outcome facts. Future artifacts must be visibly marked with their
  owning phase rather than represented as implemented.
- **PM-L0-R3 — Mutable ownership:** every inventoried mutable artifact has one
  canonical owner even when several callers delegate to its writer API.
- **PM-L0-R4 — Compatibility:** identify overlapping learning commands and
  writers, preserve approval, privacy, safety, and data semantics, and require a
  compatibility window of at least two releases.
- **PM-L0-R5 — Non-destructive migration:** every migration retains existing
  evidence and uses compatibility routing or reference joins. No existing
  artifact may be silently deleted, overwritten, or reclassified.
- **PM-L0-R6 — Deterministic assurance:** provide a versioned closed schema, a
  committed SHA-256-sealed inventory, local validation, CLI rendering, negative
  tests, package inclusion, and feature-registry ownership.
- **PM-L0-R7 — Boundary preservation:** inventory validation reads repository
  control metadata only. It must not read runtime learning content, source
  content, prompts, logs, user data, network services, or models.

## Acceptance

`tailtrail maturity learning-inventory` returns the committed ownership model,
and `tailtrail maturity validate` fails on missing systems or writers, ambiguous
mutable ownership, duplicate facts, a short alias window, a destructive
migration, schema drift, or an invalid integrity seal.

No dependency was added or changed; the dependency gate is not triggered.
