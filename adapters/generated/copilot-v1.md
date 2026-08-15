# TailTrail Composed Host Surface — Copilot

**Adapter version:** `v2`
**Host source:** `adapters/copilot-instructions.md`

## Precedence

1. Host safety
2. User request
3. Official AI-DLC stage rules for a verified Full-mode run
4. TailTrail assurance rules

A lower layer cannot weaken a higher layer. Official rules select lifecycle
stages; TailTrail preserves the approved anchor, evidence, drift, recovery, and
closure boundaries.

## Host contract

- `tailtrail start` is planning-only and requires approval before implementation.
- A rejected requirement preserves its run and routes to requirements/design.
- Completion uses saved requirement-linked evidence; do not invent command or CI results.
- `wait-ci` does not create learning. Linked CI acceptance may create a
  candidate-only learning artifact and deterministic evaluation.
- CLI or configured MCP required for persisted control-plane artifacts.

## Conformance scenarios

- **small-bug:** Navigator-first planning lock; smallest focused fix only after approval.
- **hands-free-feature:** Program Delivery plan, requirement slices, and approval before execution.
- **rejected-requirement:** Preserve run ID and route feedback to requirements/design without implementation.
- **evidence-failure:** Create a bounded Build & Test correction path with requirement-linked evidence gap.
- **recovery:** Preserve approved anchor and use task-scoped recovery evidence.
- **ci-wait:** Wait for linked CI evidence; no positive learning before acceptance.

## Interactive Plan boundary

- Preserve the current run ID for questions and plan-update requests.
- Explain saved evidence first; source investigation and plan revision require their separate approvals.
- Do not start implementation after a why-question or a revision request.
- Route AIDLC and Intent Bridge wording changes to their designated authority.

## Boundary

This generated surface validates local instruction composition only. It does not
guarantee runtime behavior by the host or replace host safety policy.
