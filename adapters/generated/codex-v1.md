# TailTrail Composed Host Surface — Codex

**Adapter version:** `v3`
**Host source:** `AGENTS.md`
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
- A rejected requirement preserves its run and routes to requirements/design.
- Completion uses saved requirement-linked evidence; do not invent command or CI results.
- `wait-ci` does not create learning. Linked CI acceptance may create a
  candidate-only learning artifact and deterministic evaluation.
- verified local official requirements/checkpoint artifacts.
- First action in Codex chat: `tailtrail start "<your task>"`
- Enforceable repository policy remains `ci-authoritative`.
- Global settings, network activity, and account changes are approval-required.

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
