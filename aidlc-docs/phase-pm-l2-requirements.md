# PM-L2 — Navigator Retrieval And Conflict Gate Requirements

Status: implemented
Authority: user-requested PM-L2 implementation, 2026-09-01
Dependency: PM-L1 Learning V3 contract and canonical reader

## Requirements

| ID | Requirement | Acceptance evidence |
| --- | --- | --- |
| PM-L2-001 | Retrieval starts only after repository and task framing. | Empty frames fail closed; proposal records the exact project/task frame. |
| PM-L2-002 | Rank by explicit applicability and return no more than three deterministic results. | Labeled ranking fixtures cover task, tag, path, requirement, confidence, ordering, and hard cap. |
| PM-L2-003 | Explain why every candidate matched and which invalidators were checked. | Every eligible match carries `match_explanations` and `invalidator_checks`. |
| PM-L2-004 | Stale, suppressed, terminal, provenance-invalid, missing-source, excluded, private, or conflicting records cannot surface advice. | Negative fixtures assert an empty match set and absence of blocked advice in rendered output. |
| PM-L2-005 | Navigator creates a default-deny use proposal rather than injecting learning into instructions. | Proposal default is `do-not-use`; rendering labels advice as not instruction and does not alter requirements, plan, source, or task state. |
| PM-L2-006 | Lite remains quiet without a high-value match. | Zero/weak-match fixtures produce `quiet` and Navigator emits no learning section. |
| PM-L2-007 | The contract ships and is enforced by maturity/registry/package controls. | Closed schema, package/release manifests, install profile, registry, and maturity validation include PM-L2. |

## Boundaries

- PM-L2 is read-only and creates no use receipt; PM-L3 owns requirement-linked use receipts and closure attribution.
- PM-L2 consumes PM-L1 V3 facts and existing refresh actions but does not amend, revoke, or delete them.
- PM-L4 owns the durable conflict ledger and negative-learning transition model; PM-L2 only blocks explicit contradictions at retrieval time.
- Current source, tests, policy, CI, scanner, guardrails, and explicit user direction always outrank a proposal.
- No dependency was added or changed.
