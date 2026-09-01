# PM-L3 — Use Receipts And Closure Attribution Requirements

Status: implemented
Authority: explicit user request on 2026-09-01
Dependencies: PM-L0 canonical ownership, PM-L1 Learning V3, PM-L2 use proposal,
approved requirement anchor, and canonical Completion Report

## Functional requirements

- **PML3-001 — Explicit decision:** record `applied`, `advisory`, `ignored`,
  `rejected`, and `stale` only after explicit approval and against a learning in
  the saved PM-L2 proposal.
- **PML3-002 — Requirement identity:** every receipt names one or more UIDs from
  the immutable approved anchor and one closed decision type.
- **PML3-003 — Append-only integrity:** decisions and attributions use a
  contiguous sequence, per-receipt predecessor, repository frame, and SHA-256
  digest chain; mutation or cross-project copying fails closed.
- **PML3-004 — Freshness and proposal integrity:** applied/advisory decisions
  require the exact current V3 record surfaced as an eligible proposal match.
  Changed, terminal, missing, or blocked advice cannot be applied.
- **PML3-005 — Evidence join:** canonical closure joins each latest decision to
  requirement status, drift, selected Harness status, unresolved execution
  failures, validation status, and the Completion Report fingerprint/reference.
- **PML3-006 — Categorical attribution:** outcomes are limited to
  `potentially-helped`, `neutral`, `insufficient`, `possible-harm`,
  `rejected-by-evidence`, `stale`, or `inconclusive` and always state
  `causal_claim: false`.
- **PML3-007 — Bounded utility:** attribution updates retrieval utility from
  observed association only, caps security/dependency/release/data-migration
  domains at ±5, other domains at ±10, and aggregate retrieval adjustment at
  ±20.
- **PML3-008 — Superseding attribution:** repeating identical closure evidence
  is idempotent; changed closure evidence appends a new attribution and only the
  latest attribution following the latest decision is active.
- **PML3-009 — Privacy:** store sanitized summaries and project-relative
  references only; never store raw prompts, raw source, raw logs, identity
  fields, secrets, or causal claims.
- **PML3-010 — Product integration:** expose receipt record/attribute/show/
  validate through `tailtrail learn receipt`, include the stream in packages
  and installers, render attribution in the canonical Completion Report, and
  validate ownership through Product Maturity controls.
- **PML3-011 — Compatibility:** retain existing workflow
  `learning-link-v1.json` candidate links and legacy learning stores. PM-L3
  introduces a distinct receipt fact and deletes or rewrites none of them.

## Acceptance evidence

- Focused tests cover every decision state, approval/anchor/proposal/freshness
  denial, idempotency, predecessor/digest tamper detection, positive and
  negative closure evidence, latest-attribution projection, domain caps,
  retrieval feedback, canonical report rendering, CLI routing, and privacy.
- Registry, package, release, installer, Product Maturity, JSON, and integrated
  learning/closure suites pass on the final tree.

## Boundary

A receipt records a human/host decision and later observed evidence. It does
not prove that a learning caused an outcome, grant implementation authority,
promote a learning, weaken current evidence, or turn missing evidence into
success.
