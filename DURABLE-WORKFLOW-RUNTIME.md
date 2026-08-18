# TailTrail Durable Workflow Runtime

Status: design proposal for review; not implemented.

This document defines a local-first workflow runtime that turns a TailTrail Navigator plan into a structured, observable, resumable, and approval-aware execution record.

The runtime is not intended to make TailTrail an autonomous multi-agent platform. Its purpose is narrower: coordinate the TailTrail capabilities that already exist, preserve evidence between stages, and make it clear what was planned, what ran, what passed, what failed, and what remains.

## Executive Summary

TailTrail already knows how to recommend AIDLC, code mapping, testing, review, security, quality, learning, token optimization, evaluation, and handoff. Today, those capabilities can still feel like separate commands and documents. The Durable Workflow Runtime will give them one shared lifecycle.

The proposed runtime will:

- convert an approved Navigator plan into a typed workflow instance
- execute or recommend only registered TailTrail capabilities
- preserve stage status without storing raw prompts, source code, or secrets
- pause before writes, scanners, broad reads, external providers, or other guarded actions
- resume interrupted work without repeating completed discovery
- invalidate stale evidence when relevant code changes
- retry only eligible failed stages
- produce a compact user-facing status and a detailed machine-readable receipt
- feed sanitized outcome evidence to Evaluation Harness and Meta-Harness
- remain deterministic and local-only by default

The initial implementation should use the Python standard library and JSON files. It should not require a model API, background service, database, message broker, container runtime, or distributed systems platform.

## Problem Being Solved

Navigator can recommend a strong workflow, but a recommendation alone does not guarantee that the workflow is followed. Several gaps remain:

- the selected stages do not share one durable status record
- an interrupted task may require rediscovery on the next session
- implementation, testing, review, and fulfilment evidence can become disconnected
- users cannot always see why a stage was skipped or blocked
- retries may repeat earlier work unnecessarily
- Meta-Harness must reconstruct behavior from separate event sources
- multiple assistants may interpret the same Navigator plan differently
- there is no single lifecycle contract for CLI, MCP, hooks, and future integrations

The runtime closes these gaps without changing TailTrail's human-approval model.

## Product Principle

Use deterministic orchestration for the lifecycle and intelligent assistance only inside bounded stages.

The runtime decides lifecycle mechanics such as stage order, prerequisites, approval, state transitions, evidence requirements, retries, freshness, and completion. An assistant may still help classify a task, clarify requirements, implement code, explain findings, or suggest a fix, but it must return results through a defined stage contract.

## Scope

### In Scope

- local workflow creation from Navigator output
- predefined workflow templates
- typed stage and capability contracts
- explicit state transitions
- approval gates
- stage evidence and artifact references
- resumability and staleness detection
- bounded retries
- cancellation and supersession
- compact event journal
- CLI integration
- Navigator and Start integration
- Feature Registry validation
- MCP read and approval-aware action tools
- Evaluation Harness and Meta-Harness evidence adapters
- deterministic tests and fixtures
- optional CI continuation for approved, non-interactive stages

### Out of Scope for the First Release

- autonomous agents communicating without a fixed workflow
- mandatory model or inference API calls
- automatic code-changing retries
- silent approval of guarded actions
- background daemons
- distributed queues or Pub/Sub
- Redis, graph databases, or vector databases
- mandatory containers or Kubernetes
- automatic upload of workflow data
- storing raw prompts, source bodies, scanner logs, secrets, or user identity
- replacing AIDLC, Navigator, Feature Registry, Learning, Evaluation Harness, or Meta-Harness

## Relationship To Existing TailTrail Features

The runtime coordinates existing features; it does not absorb their responsibilities.

| TailTrail component | Existing responsibility | Runtime responsibility |
|---|---|---|
| Navigator | classify the task and recommend the route | turn an approved route into a workflow instance |
| Feature Registry | define available features, commands, evidence, and maturity | validate that every requested capability exists and is permitted |
| AIDLC | manage lifecycle depth and development artifacts | represent AIDLC activities as workflow stages and references |
| Code Graph Mapper | provide repository relationships and read order | record graph version, freshness, and stage use |
| Token Harness | budget, route, reduce, and prove context use | attach budget and context receipts to stages |
| Guardrails and policy | define restrictions and approvals | enforce gates before stage transition or action execution |
| Test Precision | plan and report focused validation | produce validation evidence for the test stage |
| Review | identify code and requirement-fulfilment findings | produce review evidence and guarded fix-loop transitions |
| Learning Agent | retain governed repository patterns | receive post-task capture suggestions after completion |
| Evaluation Harness | assess outcome quality | consume completed workflow evidence |
| Meta-Harness | improve TailTrail behavior from repeated evidence | evaluate workflow fit, failure patterns, and routing quality |
| MCP server | expose TailTrail capabilities to assistants | expose workflow status and guarded lifecycle operations |

## Architecture

```text
User task
   |
   v
Navigator classification and proposed plan
   |
   v
User approval or edited plan
   |
   v
Workflow Compiler
   |-- validates Feature Registry IDs
   |-- resolves policy and guardrail gates
   |-- expands a workflow template
   |-- freezes the approved execution contract
   v
Local Workflow Runtime
   |-- State Store
   |-- Transition Engine
   |-- Approval Manager
   |-- Evidence Manager
   |-- Freshness Manager
   |-- Retry Controller
   |-- Event Journal
   |
   +--> TailTrail capabilities and assistant actions
   |
   v
Completion Receipt
   |-- user summary
   |-- Evaluation Harness event
   |-- optional Learning capture suggestion
   +-- sanitized Meta-Harness evidence
```

## Runtime Model

### Workflow

A workflow is one approved TailTrail task lifecycle. It has a stable ID, selected template, repository identity hash, task classification, status, stage list, policy snapshot reference, and evidence summary.

### Stage

A stage is a bounded unit such as discovery, planning, implementation, testing, review, fulfilment, security, handoff, or learning suggestion.

Every stage declares:

- stable stage ID
- registered TailTrail capability IDs
- prerequisites
- input schema
- output schema
- evidence requirements
- approval class
- retry policy
- freshness inputs
- completion rule
- skip rule
- failure behavior

### Action

An action is an individual operation inside a stage. Examples include reading a graph, running a focused test, requesting a review, or generating a handoff report.

Actions are classified as:

- `read_local`: bounded local read with no project execution
- `write_tailtrail_state`: write only TailTrail runtime state
- `write_project`: modify project source, tests, configuration, or documentation
- `execute_project`: run tests, builds, linters, or project commands
- `scan_local`: run approved local quality or vulnerability scanners
- `external_provider`: use a network service, model, CI provider, or semantic provider
- `publish`: push, deploy, merge, upload, or otherwise change external state

Approval policy is evaluated against action class, repository policy, workflow stage, and current user approval.

### Evidence

Evidence proves that a stage satisfied its completion rule. Evidence stores compact facts and references, not raw content.

Examples:

- file paths and content hashes for inspected targets
- code-graph version and freshness hash
- test command, exit code, and report path
- review finding IDs and severity counts
- requirement IDs and fulfilment status
- scanner report path and normalized finding summary
- context receipt ID and measured or estimated token label
- approval event ID
- changed-file list and diff hash

## State Machine

Workflow statuses:

- `draft`: generated but not approved
- `awaiting_approval`: waiting for initial or stage approval
- `ready`: approved and able to start
- `running`: one stage is active
- `paused`: intentionally stopped and resumable
- `blocked`: cannot continue without external change or user decision
- `failed`: terminal failure under the current contract
- `cancelled`: intentionally ended by the user
- `superseded`: replaced by a newer workflow
- `completed`: all required stages passed or were validly skipped

Stage statuses:

- `pending`
- `ready`
- `awaiting_approval`
- `running`
- `passed`
- `failed`
- `blocked`
- `skipped`
- `stale`
- `cancelled`

Allowed high-level transitions:

```text
draft -> awaiting_approval -> ready -> running
running -> awaiting_approval -> running
running -> paused -> ready
running -> blocked -> ready
running -> failed
running -> completed
draft/ready/running/paused/blocked -> cancelled
draft/ready/running/paused/blocked -> superseded
```

Illegal transitions must fail closed with a structured error. A completed workflow must never return to running; a follow-up creates a linked workflow.

## Default Workflow Templates

### Small Change

```text
bootstrap -> discover -> implement -> focused-test -> review -> fulfilment -> complete
```

Use for a bounded bug fix or small feature. AIDLC and broad scanners remain absent unless task signals or policy require them.

### Delivery

```text
bootstrap -> discover -> clarify -> plan -> implement
          -> focused-test -> review -> fulfilment -> handoff -> complete
```

Use for normal feature delivery with explicit acceptance criteria.

### Risk-Sensitive

```text
bootstrap -> discover -> aidlc -> threat-or-risk-plan -> implement
          -> tests -> security -> quality -> review -> fulfilment
          -> approval -> handoff -> complete
```

Use when authentication, authorization, privacy, secrets, regulated data, dependencies, migrations, or high-impact infrastructure are involved.

### Review Only

```text
bootstrap -> scope-diff -> graph-impact -> review
          -> requirement-fulfilment -> optional-fix-approval -> complete
```

No implementation occurs unless the user approves a fix-loop workflow.

### CI Or Scanner Remediation

```text
bootstrap -> ingest-findings -> graph-overlay -> root-cause
          -> fix-plan -> approval -> implement -> focused-validation
          -> finding-recheck -> review -> complete
```

### Repository Discovery

```text
bootstrap -> graph-freshness -> bounded-discovery -> architecture-summary -> complete
```

This remains read-only unless the user starts a follow-up change workflow.

## Workflow Compilation

The Workflow Compiler receives the Navigator plan and performs these deterministic steps:

1. Validate the plan schema.
2. Resolve every selected feature to a Feature Registry ID.
3. Reject unavailable, disabled, or contradictory features.
4. Select the smallest matching workflow template.
5. Add mandatory stages from active policy and guardrail layers.
6. Resolve stage prerequisites into an acyclic graph.
7. Detect duplicate stages and merge only compatible evidence requirements.
8. Determine approval classes.
9. Attach context budgets and graph/bootstrap references.
10. Produce a frozen draft with a stable plan hash.
11. Present the compact plan and meaningful approval questions.
12. Start only after approval of the current plan hash.

If the user edits the plan, the compiler creates a new revision and invalidates approval for the old hash.

## Data Storage

Recommended local structure:

```text
.tailtrail/
  workflows/
    index.json
    ttw-2026-0818-001/
      workflow.json
      plan.json
      events.jsonl
      approvals.jsonl
      evidence.json
      completion-receipt.json
```

These files are local runtime state and should not be committed by default.

Shareable project context remains in the existing reviewed locations, such as committed code-map artifacts or sanitized `tailtrail-meta` summaries. Workflow records must not silently become shared metadata.

### Workflow Schema Draft

```json
{
  "schema_version": "1",
  "workflow_id": "ttw-2026-0818-001",
  "workflow_revision": 1,
  "template_id": "delivery",
  "status": "awaiting_approval",
  "created_at": "2026-08-18T10:00:00Z",
  "updated_at": "2026-08-18T10:00:00Z",
  "repository_ref": "sha256:REDACTED",
  "task_class": ["feature"],
  "plan_hash": "sha256:REDACTED",
  "policy_hash": "sha256:REDACTED",
  "current_stage_id": null,
  "stages": [
    {
      "stage_id": "discover",
      "capability_ids": ["bootstrap-snapshot", "code-graph-mapper"],
      "status": "pending",
      "requires": [],
      "approval_class": "read_local",
      "attempt": 0,
      "max_attempts": 1,
      "evidence_ids": []
    }
  ],
  "claim_boundaries": [
    "Completion means required workflow stages passed; it does not prove production correctness."
  ]
}
```

### Event Schema Draft

Each event is append-only and includes:

- schema version
- event ID
- workflow ID and revision
- sequence number
- timestamp
- event type
- stage ID when relevant
- capability IDs
- categorical reason code
- evidence references
- previous and next state

Allowed event types should include:

- `workflow_created`
- `plan_revised`
- `approval_requested`
- `approval_granted`
- `approval_rejected`
- `stage_ready`
- `stage_started`
- `stage_passed`
- `stage_failed`
- `stage_blocked`
- `stage_skipped`
- `stage_stale`
- `workflow_paused`
- `workflow_resumed`
- `workflow_cancelled`
- `workflow_superseded`
- `workflow_completed`

The journal must be append-only. Current state is a projection that can be rebuilt and validated from events.

## Approval Model

Approval is scoped, revocable by plan change, and never inferred from silence.

### Initial Approval

Approves the compiled plan revision, selected stages, listed files or scopes, and explicitly named actions. It does not automatically approve later scanner, publish, dependency, or destructive actions.

### Stage Approval

Required when a stage introduces a guarded action not covered by the initial approval, such as:

- adding or changing dependencies
- running a broad build or test suite
- running Sonar, vulnerability, secret, container, or infrastructure scanners
- using external semantic providers
- modifying security-sensitive code
- applying review fixes
- publishing, pushing, deploying, or merging

### Approval Record

An approval record contains:

- approval ID
- workflow and plan revision
- approved stage and action classes
- exact command or bounded operation when relevant
- scope and expiry condition
- timestamp
- decision: approved, rejected, or edited

No raw user message is required.

## Resume And Freshness

`tailtrail resume` should:

1. locate the latest resumable workflow for the repository
2. verify schema and event integrity
3. compare repository, policy, graph, bootstrap, dependency-manifest, and changed-file hashes
4. mark affected passed stages stale
5. preserve unaffected passed stages
6. show the shortest valid continuation plan
7. request approval if the plan or guarded scope changed

Freshness dependencies should be stage-specific. A documentation edit should not invalidate a completed dependency scan. A manifest change should invalidate dependency, token-context, build, and relevant security evidence. A policy change should require recompilation of all pending guarded stages.

## Retry And Failure Rules

Retries must be explicit and bounded.

- read-only deterministic stages may retry automatically once for transient file races
- TailTrail state writes may retry only when atomic-write recovery is safe
- project commands may retry only with user approval or an active policy rule
- code-changing actions never retry automatically
- external provider calls never retry unless explicitly enabled and bounded
- publish actions never retry automatically

A retry creates a new attempt record. It must not overwrite previous evidence.

Failure classes:

- `validation_failure`: command completed and behavior failed
- `tool_failure`: tool could not execute
- `policy_block`: active policy prohibited the action
- `approval_required`: user decision is needed
- `stale_input`: required evidence changed
- `contract_error`: stage output did not satisfy schema
- `capability_unavailable`: registry feature or command is missing
- `external_failure`: provider, CI, or network dependency failed

## Concurrency And Locking

V1 should allow only one running code-changing workflow per repository. Read-only discovery or reporting may run concurrently if it does not alter shared runtime projections.

Use an atomic lock file containing workflow ID, process ID, creation time, and repository hash. Stale locks should be diagnosed, not silently deleted. `workflow doctor` can recommend a recovery action.

## CLI Design

Primary user commands:

```text
tailtrail start "<task>"
tailtrail status
tailtrail next
tailtrail resume
tailtrail pause
tailtrail cancel
```

Detailed workflow commands:

```text
tailtrail workflow list
tailtrail workflow show [WORKFLOW_ID]
tailtrail workflow plan [WORKFLOW_ID]
tailtrail workflow approve [WORKFLOW_ID] --revision N
tailtrail workflow reject [WORKFLOW_ID] --reason-code CODE
tailtrail workflow resume [WORKFLOW_ID]
tailtrail workflow retry [WORKFLOW_ID] --stage STAGE_ID
tailtrail workflow skip [WORKFLOW_ID] --stage STAGE_ID --reason-code CODE
tailtrail workflow events [WORKFLOW_ID]
tailtrail workflow receipt [WORKFLOW_ID]
tailtrail workflow doctor [WORKFLOW_ID]
```

`start` remains the obvious entry point. Users should not need to learn the detailed commands for normal work.

### Compact Status Example

```text
TailTrail workflow ttw-2026-0818-001
Delivery: 5 of 8 stages complete
Current: focused validation
Waiting: approval to run the repository test command
Next: test -> review -> requirement fulfilment
Context: within approved budget
```

Verbose and JSON formats can expose full evidence and transition details.

## Navigator Integration

Navigator should remain the planner. It should not mutate runtime state while producing a guide-only response.

Proposed behavior:

- `guide`: return a plan only; do not create a workflow
- `start`: compile a draft workflow and request approval
- approved `start`: persist the workflow and begin the first eligible stage
- implementation completion: advance to focused validation rather than ending silently
- failed validation: pause for fix-plan approval
- successful validation: advance to review and requirement fulfilment
- completed workflow: suggest learning capture and value reporting

Navigator output should stay concise. Detailed skipped features and contracts should be available through `workflow show --verbose`.

## Feature Registry Integration

Add registry metadata for runtime-consumable features:

```json
{
  "workflow_contract": {
    "stage_types": ["discover", "implement", "test", "review"],
    "action_classes": ["read_local", "write_project"],
    "input_schema": "schemas/workflow/example-input.schema.json",
    "output_schema": "schemas/workflow/example-output.schema.json",
    "approval_required": true,
    "retry_class": "manual"
  }
}
```

Registry drift validation should reject:

- unknown capability IDs in templates
- missing input or output schemas
- unsupported action classes
- undocumented approval requirements
- runtime commands that are not registered
- evidence claims stronger than the feature's registered evidence label

## MCP Integration

MCP should expose a small workflow surface rather than one tool per internal transition.

Read-only tools:

- `workflow_status`
- `workflow_plan`
- `workflow_next`
- `workflow_events`
- `workflow_receipt`

State-changing tools:

- `workflow_start`
- `workflow_approve`
- `workflow_pause`
- `workflow_resume`
- `workflow_cancel`
- `workflow_retry_stage`

Every state-changing tool must validate workflow revision, policy, approval scope, and current transition. MCP must not allow an assistant to forge user approval.

## Token Harness Integration

Each stage receives a context budget and emits a context receipt when routing is worthwhile.

The runtime should:

- use bootstrap and fresh graph summaries before broad reads
- load only stage-relevant governance and feature slices
- retain references to prior stage evidence instead of reinjecting full outputs
- request budget expansion when evidence shows the initial estimate is insufficient
- never truncate exact policy, source, security, dependency, or validation evidence that materially affects the decision
- label token evidence as estimated or measured

Resume should prefer compact stage summaries and artifact references. It must not replay the entire workflow history into the assistant context.

## Review And Guarded Fix Loop

Review is a required stage for code-changing default templates.

The review stage should check:

- code health and maintainability
- requirement fulfilment against approved task criteria
- safeguards and policy
- focused test adequacy
- dependency discipline
- affected callers, tests, endpoints, tables, and configuration

Findings must include severity, description, file, line when available, symbol or function, evidence, and suggested next action.

Review findings do not trigger automatic fixes. The runtime creates a proposed fix stage, presents affected files and validation, and asks for approval. Approved fixes return to validation and review before completion.

## Learning Integration

Learning capture remains advisory and confidence-gated.

After a meaningful completed, rejected, or revised workflow, the runtime may propose a compact learning candidate containing:

- reusable pattern or decision
- applicable files, tags, or feature IDs
- validation outcome
- acceptance signal
- confidence inputs
- expiry or refresh hint

Low-confidence or user-overridden unsafe patterns must not enter reusable learning. Workflow evidence may record the decision categorically without recording raw user history.

## Evaluation Harness Integration

On completion, cancellation, or terminal failure, the runtime can emit a normalized evaluation event containing:

- task class
- selected and skipped feature IDs
- workflow fit signals
- stage completion and skip counts
- validation result
- review result
- requirement fulfilment result
- approval compliance
- context evidence label
- retry and stale-stage counts
- claim boundaries

This enables scenario and portfolio evaluation to measure whether the workflow helped without treating mere completion as proof of code correctness.

## Meta-Harness Integration

Meta-Harness should analyze repeated runtime evidence, not operate inside every task.

Useful signals include:

- Navigator consistently selected workflows that were too heavy or too light
- stages were frequently skipped for the same reason
- a capability was selected but unavailable
- token budgets repeatedly required expansion
- graph evidence was stale or unused
- validation failed after review passed
- requirement fulfilment repeatedly required clarification
- approval prompts were noisy or missing
- retries did not improve outcomes

Meta-Harness may create reviewable product proposals after evidence thresholds are met. It must not edit workflow templates or routing rules automatically.

## Security And Privacy Controls

- Runtime state stays local by default.
- Store repository identity as a hash, not a remote URL.
- Never store raw prompts, source bodies, secrets, tokens, credentials, full logs, or user identity.
- Store exact commands only when needed for validation evidence; redact environment values.
- Enforce maximum event and evidence sizes.
- Use atomic writes and restrictive file permissions where supported.
- Validate all loaded JSON against schemas.
- Treat workflow files as untrusted input when imported or restored.
- Reject path traversal and paths outside the target repository unless an approved cross-repo reference is active.
- Do not execute commands reconstructed from event history.
- Re-resolve commands from registered capabilities and active policy at execution time.
- Preserve an audit trail for approvals, skips, retries, and plan revisions.

## Suggested Python Module Layout

```text
scripts/
  workflow-runtime.py              # thin CLI wrapper
  workflow_runtime/
    __init__.py
    cli.py
    compiler.py
    engine.py
    models.py
    transitions.py
    templates.py
    approvals.py
    evidence.py
    freshness.py
    retries.py
    events.py
    storage.py
    policy.py
    registry.py
    receipts.py

schemas/workflow/
  workflow.schema.json
  plan.schema.json
  stage.schema.json
  event.schema.json
  approval.schema.json
  evidence.schema.json
  completion-receipt.schema.json

context/workflows/
  small-change.json
  delivery.json
  risk-sensitive.json
  review-only.json
  ci-remediation.json
  repo-discovery.json
```

Keep wrappers as pure import-and-call shims. Business logic belongs in importable underscore-named modules so unit tests do not require subprocesses.

## Implementation Phases

### DWR-0: Contract And Inventory

Deliverables:

- map existing Navigator routes and Feature Registry IDs to stage types
- define schemas, state transitions, action classes, and reason codes
- define workflow storage and privacy boundary
- add registry entry for the runtime
- add architecture and command documentation

Acceptance:

- every initial stage maps to existing TailTrail behavior
- no duplicate feature taxonomy is introduced
- schemas reject illegal status and transition values

### DWR-1: Local State Engine

Deliverables:

- workflow models and atomic JSON storage
- append-only event journal
- transition engine
- workflow create, list, show, status, pause, cancel, and events commands
- lock and doctor behavior

Acceptance:

- projection can be rebuilt from events
- illegal transitions fail closed
- interrupted writes recover without corrupting the last valid state

### DWR-2: Navigator And Approval Integration

Deliverables:

- Workflow Compiler
- `start` draft and approval flow
- plan revisions and hashes
- stage approval records
- concise status and `next` output

Acceptance:

- `guide` remains read-only
- no workflow runs before approval
- edited plans invalidate previous approval
- Navigator output does not become noisier than the current compact mode

### DWR-3: Evidence, Resume, And Freshness

Deliverables:

- evidence manager
- stage-specific freshness hashes
- resume and stale-stage recomputation
- bounded retry controller
- completion receipt

Acceptance:

- unaffected passed stages remain passed after a change
- relevant stages become stale when source, policy, graph, or manifests change
- code-changing actions never retry automatically

### DWR-4: Core Capability Adapters

Deliverables:

- bootstrap and graph discovery adapters
- implementation boundary adapter
- focused testing adapter
- review and requirement-fulfilment adapter
- security and quality approval adapters
- handoff adapter

Acceptance:

- small, delivery, risk, review-only, CI-remediation, and discovery templates run end to end using deterministic fixtures
- every adapter uses Feature Registry IDs and typed outputs

### DWR-5: Token, Learning, Evaluation, And Meta-Harness

Deliverables:

- stage context budgets and receipts
- learning capture suggestions
- normalized evaluation events
- sanitized Meta-Harness workflow signals

Acceptance:

- resume uses summaries and references instead of full history
- token claims retain estimated or measured labels
- no raw task or source content enters shared evidence

### DWR-6: MCP And CI Continuation

Deliverables:

- minimal MCP workflow tools
- optional CI continuation for explicitly approved non-interactive stages
- registry and governance drift checks

Acceptance:

- MCP cannot forge approvals or bypass transition rules
- CI cannot perform project writes, fixes, publish actions, or external scans unless explicitly configured and approved by policy

### DWR-7: Optional Enterprise Runtime Adapter

Evidence-gated and deferred.

Possible deliverables:

- pluggable state-store interface
- durable distributed-workflow adapter
- event transport adapter
- cross-repository parent and child workflow IDs
- centralized observability projection

Entry criteria:

- real adoption shows local workflow state is insufficient
- teams need long-running or cross-repository continuation
- operational ownership, security review, tenancy, retention, and cost controls are defined
- local mode remains supported and default

## Test Strategy

### Unit Tests

- schema validation
- every legal and illegal transition
- event ordering and replay
- plan hashing and revision invalidation
- approval scope and expiry
- retry eligibility
- freshness invalidation matrix
- atomic storage recovery
- lock handling
- registry capability validation
- privacy redaction and event size limits

### Integration Tests

- `start -> approve -> execute -> validate -> review -> complete`
- pause and resume after repository change
- failed test followed by approved fix loop
- rejected scanner approval
- stale graph refresh
- policy change during a paused workflow
- missing capability and registry drift
- MCP status and guarded transition behavior
- Evaluation and Meta-Harness event production

### Deterministic Scenarios

- small bug fix with focused unit test
- feature requiring AIDLC and handoff
- review-only request with optional fixes rejected
- CI failure with graph overlay and recheck
- vulnerability finding requiring explicit scan and fix approval
- dependency request rejected by policy
- cross-repo reference workflow
- interrupted workflow resumed after changed files

### Negative Tests

- forged approval ID
- modified plan after approval
- event journal sequence gap
- attempted transition from completed to running
- imported workflow containing path traversal
- event containing a secret-like value
- retry of code-changing action without approval
- command reconstructed from an untrusted event
- external provider invoked without opt-in

## Migration And Compatibility

- Existing commands continue to work.
- `start`, `guide`, `next`, review, test, scanner, graph, and handoff commands become adapters gradually.
- No existing workflow history is migrated automatically.
- Existing `.tailtrail` files remain authoritative for their current features.
- The runtime stores references to existing artifacts rather than copying them.
- Compatibility aliases should print the corresponding workflow stage only after the runtime is stable.
- Feature Registry and documentation drift checks must cover the new command surface.

## Operational Metrics

Measure runtime usefulness before considering distributed execution:

- workflows started, approved, completed, cancelled, and blocked
- median stages per workflow
- stage failure and skip rates
- resume success rate
- stale-stage recomputation rate
- approval prompt count per workflow
- percentage of completed code changes with focused validation and review
- requirement-fulfilment pass rate
- context budget expansion rate
- measured or estimated token evidence coverage
- workflow fit findings from Meta-Harness

These metrics must remain categorical or aggregate unless real measured evidence is available. Do not claim productivity, quality, or token improvement from workflow completion alone.

## Risks And Mitigations

| Risk | Mitigation |
|---|---|
| More process slows small tasks | smallest matching template; tiny tasks may remain direct and read-only |
| Navigator output becomes noisy | compact default status; verbose details on demand |
| Runtime duplicates existing features | adapters and registry IDs; no parallel feature taxonomy |
| Stale state creates wrong decisions | stage-specific hashes and explicit stale status |
| Approval fatigue | scope approvals carefully and combine only related bounded actions |
| Hidden autonomy | deterministic transitions and explicit approval records |
| Workflow files leak sensitive data | strict schemas, redaction, size caps, local-only default |
| Retrying creates unwanted changes | no automatic retries for project writes or publish actions |
| State corruption | atomic writes, append-only events, replay validation, doctor command |
| Distributed design overwhelms local use | defer enterprise adapter until measured need exists |

## Decisions Required Before Implementation

1. Should `start` create a draft workflow immediately, or only after the user approves the displayed plan? Recommended: create an in-memory draft, persist only after approval.
2. Should tiny informational tasks create workflow state? Recommended: no; use read-only Navigator guidance and optional discovery receipts.
3. Should local workflow records ever be committed? Recommended: no; only explicitly sanitized summaries may be shared.
4. How long should completed local workflows be retained? Recommended: configurable count-based retention with manual cleanup, no background deletion in V1.
5. Should a successful code-changing workflow require both review and requirement fulfilment? Recommended: yes for default templates, with explicit policy-backed skip reasons.
6. Can CI advance a workflow? Recommended: only approved non-interactive validation/reporting stages; never code fixes or publishing by default.
7. Should multiple active workflows be allowed? Recommended: multiple drafts/read-only workflows, but one code-changing workflow per repository.

## Recommended First Release

Implement DWR-0 through DWR-3 first. This provides the durable contract, local state, approvals, status, resume, freshness, and evidence foundation without coupling every TailTrail feature immediately.

Then connect one complete vertical path in DWR-4:

```text
small change -> focused test -> review -> requirement fulfilment -> completion receipt
```

Validate that path through Evaluation Harness before connecting risk, scanner, cross-repository, and CI workflows.

## End-State Vision

The end state is one coherent TailTrail development lifecycle:

```text
Describe the goal
  -> TailTrail plans the smallest suitable route
  -> the user approves or edits it
  -> registered capabilities execute through bounded stages
  -> progress survives interruptions
  -> tests, review, safeguards, and requirements provide completion evidence
  -> token and outcome receipts show what happened
  -> governed learning helps the repository
  -> aggregated evidence helps improve TailTrail itself
```

The user should experience one clear workflow, while TailTrail retains the precision, guardrails, evidence, and reversibility needed for enterprise AI-assisted development.
