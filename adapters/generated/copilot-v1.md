# TailTrail Composed Host Surface — Copilot

**Adapter version:** `v3`
**Host source:** `adapters/copilot-instructions.md`
**Qualification:** `contract-tested` (not runtime-observed or supported)

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
- An explicit TailTrail task in ordinary language routes to planning-only Start; preserve the user's goal and let Navigator discover scope and controls.
- A request asking only for an approach routes to `guide`; an active-run why, scope, file, or validation question routes to `discuss` on the same run.
- `looks good`, `go ahead`, `proceed`, and similar wording never approve. Only explicit approval may reach an approval-controlled operation.
- `tailtrail intent resolve` and MCP `intent_resolve` are read-only typed recommendations. They never create a run, infer approval, or execute work.
- For ordinary Lite/Off Build Start, use host language understanding to classify exact-goal-bound context, outcome, constraint, evidence, scope, and question clauses. Keep quoted literals separate from semantic intent terms; send no private reasoning.
- Pass every explicitly referenced local requirement file through `requirement_artifacts`. Consume its bounded inspection ID and SHA-256, bind artifact clauses with `source_input_id` and `artifact_evidence`, and never replace unread content with a generic requirement.
- Pass the validated typed interpretation to `tailtrail_start`. Missing, unreadable, unsupported, truncated, or unbound required artifacts and material ambiguity stop before scope and Planning Lock; host interpretation never grants scope or execution authority.
- For agent-host Standard/Full Build Start, consume `official_requirement_authority`, read every exact verified governing rule and required artifact, and resubmit with `authority: official-ai-dlc-pack`, the matching mode/Requirements stage, and identical `authority_references`. Official requirements must exist before Navigator scope discovery; TailTrail maps but never rewrites them.
- Consume bounded static scope evidence with the active host's reasoning; compare owners, callers, proof, alternatives, preservation, and uncertainty.
- Return typed evidence-edge references without private chain-of-thought. Never invent scope or override an unresolved/rejected proposal.
- Treat target selection and scope quality as separate gates. A Scope Confirmation report is non-persisted: ask only SCOPE-Q1 when present, claim no run ID, and retain the exact v2 decision fingerprint after resolution.
- A rejected requirement preserves its run and routes to requirements/design.
- Run approved local proof through `execution_evidence_run` so TailTrail captures exit code, duration, and redacted output; label-only results remain unverified.
- Completion uses the current saved requirement-linked evidence snapshot; do not invent command or CI results.
- `wait-ci` does not create learning. Linked CI acceptance may create a
  candidate-only learning artifact and deterministic evaluation.
- CLI or configured MCP required for persisted control-plane artifacts.
- First action in GitHub Copilot Chat: `/tailtrail-start <your task>`
- Enforceable repository policy remains `ci-authoritative`.
- Global settings, network activity, and account changes are approval-required.

## Conformance scenarios

- **small-bug:** Navigator-first planning lock; smallest focused fix only after approval.
- **hands-free-feature:** Program Delivery plan, requirement slices, and approval before execution.
- **rejected-requirement:** Preserve run ID and route feedback to requirements/design without implementation.
- **evidence-failure:** Create a bounded Build & Test correction path with requirement-linked evidence gap.
- **recovery:** Preserve approved anchor and use task-scoped recovery evidence.
- **ci-wait:** Wait for linked CI evidence; no positive learning before acceptance.

## Scope evidence v2 host boundary

- Consume the canonical normalized decision fingerprint and owner, inspection, proof, and excluded roles returned by CLI or MCP.
- Host reasoning may explain public evidence-edge references, uncertainty, and alternatives; it cannot reclassify a path or promote unresolved/conflicting evidence.
- Scope investigation occurs before Planning Lock persistence. Unresolved or conflicting Build scope creates no Planning Lock; Debug Start records command-free orientation only.
- Normal Start lets Navigator transactionally reuse, create, refresh, or rebuild metadata-only graph state. Debug Start may only reuse a fresh graph before reproduction approval.
- Graph suggestions and complete prior-run mappings remain advisory until hash and current-source relationship validation; no approval transfers between runs.
- Closure refreshes actual changed graph scope and records an immutable run mapping for later relevant retrieval.
- Planning Lock approval, Debug reproduction/correction approval, AIDLC authority, Intent Bridge authority, and closure drift remain separate gates.

- **resolved:** `resolved` / `pass` / editable role `implementation-owner`.
- **unresolved:** `unresolved` / `block` / editable role `none`.
- **conflicting:** `ambiguous` / `block` / editable role `none`.
- **docs-only:** `resolved` / `pass` / editable role `documentation`.
- **test-only:** `resolved` / `pass` / editable role `test`.
- **debug-start:** `unresolved` / `orientation-only` / editable role `none`.

## Active-host scope reasoning boundary

- When deterministic evidence leaves two or more hash-bound strong owners, consume the requested packet and return one schema-v2 public-evidence proposal.
- Bind every proposal to the exact packet, scope decision, target, goal, requirement statement, candidate identity, current content hash, and evidence edges.
- Submit the proposal through CLI or MCP validation before Start persistence. Unsupported, stale, or authority-expanding proposals create no run and must not be rewritten as confidence.
- Host identity is transport metadata: Codex, Copilot, and Claude must produce the same normalized decision for the same proposal.

- **supported-selection:** `accepted` / scope `resolved` / run created `false`.
- **invented-path:** `rejected` / scope `ambiguous` / run created `false`.
- **unsupported-edge:** `rejected` / scope `ambiguous` / run created `false`.
- **stale-packet:** `rejected` / scope `ambiguous` / run created `false`.
- **authority-escalation:** `rejected` / scope `ambiguous` / run created `false`.

## Requirement-before-scope host boundary

- Consume MCP `requirement_route` directly; do not infer requirement state from rendered prose.
- Preserve target identity, then requirement sufficiency, then implementation scope as the only question order.
- A `deferred` requirement route forbids graph work, owner questions, and Planning Lock creation.
- Scope release failure cannot preempt an unresolved requirement intake.
- Only a typed `eligible` route permits bounded scope investigation or one validated scope question.
- A missing route or deferred route combined with scope, host-refinement, or run authority is a conformance failure; never reinterpret it.

- **host-interpretation-required:** requirement `host-interpretation-required` / route `host-interpretation` / scope question `false` / run created `false`.
- **lite-intake:** requirement `clarification-required` / route `lite-questions` / scope question `false` / run created `false`.
- **standard-intake:** requirement `standard-recommended` / route `aidlc-standard` / scope question `false` / run created `false`.
- **full-intake:** requirement `full-recommended` / route `aidlc-full` / scope question `false` / run created `false`.
- **scope-disabled-requirements-open:** requirement `clarification-required` / route `lite-questions` / scope question `false` / run created `false`.
- **answered-intake:** requirement `sufficient` / route `scope` / scope question `true` / run created `false`.
- **eligible-scope-question:** requirement `sufficient` / route `scope` / scope question `true` / run created `false`.

## Interactive Plan boundary

- Preserve the current run ID for questions and plan-update requests.
- Explain saved evidence first; source investigation and plan revision require their separate approvals.
- Do not start implementation after a why-question or a revision request.
- Route AIDLC and Intent Bridge wording changes to their designated authority.

## Debug next-action boundary

- After every reproduction proposal, revision, show, or approval transition, return the canonical `Next actions` and `Route to a code fix` guidance.
- Preserve the exact run ID and revision in compact natural-language prompts for approval, revision, explanation, rejection, status, stop, and resume as applicable.
- Contract approval is not reproduction proof. Run only the approved bounded procedure, record factual command evidence, and record a typed pre-fix attempt.
- A not-reproduced or inconclusive attempt keeps hypotheses and correction blocked and returns a sanitized `awaiting-reproduction-input` request after bounded difference checks.
- New user evidence creates a separately approved reproduction revision. Post-fix closure requires a factual restored attempt against the same approved boundary.
- A future correction prompt is staged guidance only; it never grants source-write authority or advances the lifecycle automatically.

## Common stop and exact resume

- `tailtrail stop` uses the common durable attachment control, preserves the exact run, and returns later ordinary prompts to the normal host agent.
- `tailtrail resume --run-id <exact-run-id>` reattaches only that run without approving or advancing workflow execution.

## Durable Workflow MCP boundary

- Use the same canonical workflow ID and approved run across status, evidence,
  correction, resume, and closure.
- Read-only workflow MCP tools inspect local state only; controlled workflow
  tools require explicit approval and cannot invent Planning Lock, AIDLC,
  dependency, recovery, or closure authority.
- Host receipts are sanitized, linked evidence. They do not replace the
  canonical workflow status or completion boundary.
- CI continuation requires the exact approved CI policy plus run, target,
  plan, scope, commit, artifact-hash, and trusted-provenance bindings. It may
  advance validation/reporting metadata only; it never fixes source, changes
  dependencies/infrastructure, scans, calls providers, publishes, deploys,
  merges, recovers, or finalizes closure.
- Negative assurance returns categorical issue and denial codes only; hosts must
  not echo hostile prompts, source, logs, identities, credentials, or commands.
- Retention is local, count-based, and manual. There is no background deletion
  or upload; exact candidate and plan bindings plus explicit approval are required.

- Phase 11 release proof accepts only linked sanitized scenario, template, and host receipts. Missing evidence remains blocked.
- A passing release gate never retires `--no-workflow`; separate exact-gate approval and a reviewed release change are required.

- Phase 12 enterprise continuation is optional, provider-neutral, and local-default. Hosts must require the passing Phase 11 gate, complete approved entry policy, per-workflow activation, tenant/actor authority, and current fencing token.
- Enterprise receipts and observability are sanitized metadata shadows only; canonical local ownership, approvals, evidence, recovery, and closure always win. Hosts must not upload raw workflow/source/log data or infer provider readiness from local conformance.

## Boundary

This generated surface validates local instruction composition only. It does not
guarantee runtime behavior by the host or replace host safety policy.
