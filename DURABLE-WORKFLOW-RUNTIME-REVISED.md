# TailTrail Durable Workflow Runtime — Revised Design

Status: revised design proposal for review; not implemented.
Revision basis: review findings from August 18, 2026.
Changes from original: DWR-minus phase added, `clarify` stage defined, module size contract added,
invalidation rule made explicit, approval fatigue mitigations strengthened, `--no-workflow` escape
hatch added, phase exit criteria added. All other sections kept from the original.

---

## What Changed From The Original And Why

| Section | Change | Reason |
|---|---|---|
| Implementation Phases | Added **DWR-minus** before DWR-0 | Prove storage model before building the engine |
| Delivery template | Defined `clarify` explicitly | Was undefined — every stage must have a capability ID |
| Module layout | Added 300-line size contract | Prevent monolith recurrence by design |
| Plan invalidation | Replaced vague rule with 3 explicit triggers | Vague rule causes user frustration and workarounds |
| Approval model | Added session approval + policy pre-approval | Approval fatigue is listed as a risk but had no real mitigation |
| Migration | Added `--no-workflow` flag | Existing Codex/Copilot integrations break when output format changes |
| Each phase | Added "Phase exit criteria" | Phases had deliverables but no measurable done condition |
| Risks table | Added approval fatigue concrete mitigations | Original mitigation was advice, not mechanism |

Everything else — the problem statement, product principle, scope, state machine, event model,
data storage, retry rules, security controls, MCP integration, token harness integration,
learning integration, evaluation harness, meta-harness, test strategy, and end-state vision —
is kept from the original unchanged.

---

## Executive Summary

TailTrail already knows how to recommend AIDLC, code mapping, testing, review, security, quality,
learning, token optimization, evaluation, and handoff. Today, those capabilities can still feel
like separate commands and documents. The Durable Workflow Runtime will give them one shared lifecycle.

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

The initial implementation should use the Python standard library and JSON files. It should not
require a model API, background service, database, message broker, container runtime, or
distributed systems platform.

---

## Problem Being Solved

Navigator can recommend a strong workflow, but a recommendation alone does not guarantee that the
workflow is followed. Several gaps remain:

- the selected stages do not share one durable status record
- an interrupted task may require rediscovery on the next session
- implementation, testing, review, and fulfilment evidence can become disconnected
- users cannot always see why a stage was skipped or blocked
- retries may repeat earlier work unnecessarily
- Meta-Harness must reconstruct behavior from separate event sources
- multiple assistants may interpret the same Navigator plan differently
- there is no single lifecycle contract for CLI, MCP, hooks, and future integrations

The runtime closes these gaps without changing TailTrail's human-approval model.

---

## Product Principle

Use deterministic orchestration for the lifecycle and intelligent assistance only inside bounded stages.

The runtime decides lifecycle mechanics such as stage order, prerequisites, approval, state
transitions, evidence requirements, retries, freshness, and completion. An assistant may still
help classify a task, clarify requirements, implement code, explain findings, or suggest a fix,
but it must return results through a defined stage contract.

---

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

---

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

---

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

---

## Runtime Model

### Workflow

A workflow is one approved TailTrail task lifecycle. It has a stable ID, selected template,
repository identity hash, task classification, status, stage list, policy snapshot reference,
and evidence summary.

### Stage

A stage is a bounded unit such as discovery, planning, implementation, testing, review,
fulfilment, security, handoff, or learning suggestion.

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

An action is an individual operation inside a stage. Actions are classified as:

- `read_local`: bounded local read with no project execution
- `write_tailtrail_state`: write only TailTrail runtime state
- `write_project`: modify project source, tests, configuration, or documentation
- `execute_project`: run tests, builds, linters, or project commands
- `scan_local`: run approved local quality or vulnerability scanners
- `external_provider`: use a network service, model, CI provider, or semantic provider
- `publish`: push, deploy, merge, upload, or otherwise change external state

Approval policy is evaluated against action class, repository policy, workflow stage, and
current user approval.

### Evidence

Evidence proves that a stage satisfied its completion rule. Evidence stores compact facts and
references, not raw content.

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

---

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

Illegal transitions must fail closed with a structured error. A completed workflow must never
return to running; a follow-up creates a linked workflow.

---

## Default Workflow Templates

### Small Change

```text
bootstrap -> discover -> implement -> focused-test -> review -> fulfilment -> complete
```

Use for a bounded bug fix or small feature. AIDLC and broad scanners remain absent unless
task signals or policy require them.

### Delivery

```text
bootstrap -> discover -> clarify -> plan -> implement
          -> focused-test -> review -> fulfilment -> handoff -> complete
```

**`clarify` stage definition** *(revised — was undefined in the original)*

The `clarify` stage maps to the AIDLC Requirements stage.

- Capability ID: `aidlc-requirements`
- Approval class: `read_local` (no source edits; reads goal and Navigator plan only)
- Input schema: Navigator plan, goal statement, known facts from the discovery stage
- Output schema: approved requirement boundary, AIDLC questions and answers, assumptions,
  non-goals, and acceptance criteria
- Completion rule: at least one requirement accepted by the user and a non-empty acceptance
  criteria list recorded
- Skip rule: may be skipped when the task is a direct bug fix with a single well-defined
  acceptance criterion already stated in the goal — requires an explicit skip reason code
- Failure behavior: `blocked`; the workflow pauses for requirement clarification

This stage is optional for the Small Change template and required for Delivery, Risk-Sensitive,
and any template where the acceptance criteria are not stated in the initial goal.

### Risk-Sensitive

```text
bootstrap -> discover -> aidlc -> threat-or-risk-plan -> implement
          -> tests -> security -> quality -> review -> fulfilment
          -> approval -> handoff -> complete
```

Use when authentication, authorization, privacy, secrets, regulated data, dependencies,
migrations, or high-impact infrastructure are involved.

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

---

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

**Plan invalidation triggers** *(revised — original was vague)*

A new revision is created and previous approval is invalidated when exactly one of these
three conditions is true:

1. The user explicitly changes the stage list or stage order.
2. A policy or guardrail file changes in a way that affects an unstarted guarded stage.
3. The repository identity hash changes (different branch, different repository, or a forced
   commit that changes the HEAD SHA).

Nothing else triggers a revision. Task description edits, comment changes, token budget
adjustments, and non-guarded metadata updates do not create a new revision. This makes the
invalidation rule predictable and prevents the user from losing approval for trivial reasons.

If the user edits the plan in any way that does not meet the above three conditions, the change
is recorded as a plan annotation but does not reset approval.

---

## Approval Model *(revised — original mitigation for approval fatigue was insufficient)*

Approval is scoped, revocable by plan change, and never inferred from silence.

### Initial Approval

Approves the compiled plan revision, selected stages, listed files or scopes, and explicitly
named actions. It does not automatically approve later scanner, publish, dependency, or
destructive actions.

### Stage Approval

Required when a stage introduces a guarded action not covered by the initial approval, such as:

- adding or changing dependencies
- running a broad build or test suite
- running Sonar, vulnerability, secret, container, or infrastructure scanners
- using external semantic providers
- modifying security-sensitive code
- applying review fixes
- publishing, pushing, deploying, or merging

### Session Approval *(new)*

To reduce approval fatigue without removing the approval record, a user may grant a session
approval for one or more action classes for the duration of the current session:

```text
tailtrail workflow approve --session --action-class read_local write_tailtrail_state
```

- Session approval records are written to `approvals.jsonl` like any other approval.
- They expire when the session ends, the workflow is paused, or the plan is revised.
- They never cover `write_project`, `execute_project`, `scan_local`, `external_provider`,
  or `publish` actions.
- A session approval cannot be used to pre-approve a stage whose action class is unknown
  at compile time.

### Policy Pre-Approval *(new)*

A `tailtrail-policy.md` or `.tailtrail/policy-overrides.json` may pre-approve specific
well-understood, low-risk stages without a runtime interactive prompt:

```json
{
  "pre_approved_stages": [
    {
      "stage_id": "bootstrap",
      "action_class": "read_local",
      "rationale": "Bootstrap is always read-only and idempotent."
    },
    {
      "stage_id": "discover",
      "action_class": "read_local",
      "rationale": "Graph read approved for this repository."
    }
  ]
}
```

Pre-approved stages still write an approval event. The event records the policy reference,
not a user interaction. This gives teams control over which stages are interactive without
making any stage approval-free in the audit trail.

### Approval Record

An approval record contains:

- approval ID
- workflow and plan revision
- approved stage and action classes
- exact command or bounded operation when relevant
- scope and expiry condition
- timestamp
- decision: approved, rejected, or edited
- approval source: interactive, session, or policy-reference

No raw user message is required.

---

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

Shareable project context remains in the existing reviewed locations, such as committed
code-map artifacts or sanitized `tailtrail-meta` summaries. Workflow records must not
silently become shared metadata.

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

Allowed event types:

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

The journal must be append-only. Current state is a projection that can be rebuilt and
validated from events.

---

## Resume And Freshness

`tailtrail resume` should:

1. locate the latest resumable workflow for the repository
2. verify schema and event integrity
3. compare repository, policy, graph, bootstrap, dependency-manifest, and changed-file hashes
4. mark affected passed stages stale
5. preserve unaffected passed stages
6. show the shortest valid continuation plan
7. request approval if the plan or guarded scope changed

Freshness dependencies should be stage-specific. A documentation edit should not invalidate
a completed dependency scan. A manifest change should invalidate dependency, token-context,
build, and relevant security evidence. A policy change should require recompilation of all
pending guarded stages.

---

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

---

## Concurrency And Locking

V1 should allow only one running code-changing workflow per repository. Read-only discovery
or reporting may run concurrently if it does not alter shared runtime projections.

Use an atomic lock file containing workflow ID, process ID, creation time, and repository
hash. Stale locks should be diagnosed, not silently deleted. `workflow doctor` can recommend
a recovery action.

---

## CLI Design

Primary user commands:

```text
tailtrail start "<task>"
tailtrail start "<task>" --no-workflow      # escape hatch — returns existing compact report
tailtrail status
tailtrail next
tailtrail resume
tailtrail pause
tailtrail cancel
```

**`--no-workflow` flag** *(new — see Migration section)*

When `--no-workflow` is passed, `start` behaves exactly as it did before the Durable Workflow
Runtime was introduced: it returns a Navigator compact plan and Planning Lock without creating
or mutating any workflow state. Remove this flag only after DWR-4 is complete and validated.

Detailed workflow commands:

```text
tailtrail workflow list
tailtrail workflow show [WORKFLOW_ID]
tailtrail workflow plan [WORKFLOW_ID]
tailtrail workflow approve [WORKFLOW_ID] --revision N
tailtrail workflow approve [WORKFLOW_ID] --session --action-class CLASS [CLASS...]
tailtrail workflow reject [WORKFLOW_ID] --reason-code CODE
tailtrail workflow resume [WORKFLOW_ID]
tailtrail workflow retry [WORKFLOW_ID] --stage STAGE_ID
tailtrail workflow skip [WORKFLOW_ID] --stage STAGE_ID --reason-code CODE
tailtrail workflow events [WORKFLOW_ID]
tailtrail workflow receipt [WORKFLOW_ID]
tailtrail workflow doctor [WORKFLOW_ID]
```

`start` remains the obvious entry point. Users should not need to learn the detailed commands
for normal work.

### Compact Status Example

```text
TailTrail workflow ttw-2026-0818-001
Delivery: 5 of 8 stages complete
Current: focused validation
Waiting: approval to run the repository test command
Next: test -> review -> requirement fulfilment
Context: within approved budget
```

---

## Suggested Python Module Layout *(revised — module size contract added)*

```text
scripts/
  workflow-runtime.py              # thin CLI wrapper; no business logic

  workflow_runtime/
    __init__.py
    cli.py          # argument parsing and output formatting only
    compiler.py     # Workflow Compiler — step 1 through 12
    engine.py       # Transition Engine — state machine and stage sequencing
    models.py       # typed dataclasses for Workflow, Stage, Action, Evidence
    transitions.py  # legal transition table and transition validator
    templates.py    # template definitions and template selector
    approvals.py    # approval records, session approval, policy pre-approval
    evidence.py     # evidence collection, schema validation, size enforcement
    freshness.py    # hash computation and stale-stage detection
    retries.py      # retry eligibility and attempt records
    events.py       # event schema, append-only journal, replay, sequence check
    storage.py      # atomic file I/O, lock management, path validation
    policy.py       # policy loading, pre-approval resolution, guardrail enforcement
    registry.py     # Feature Registry capability lookup and drift validation
    receipts.py     # completion receipt generation and sanitization

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

**Module size contract** *(new)*

No module inside `workflow_runtime/` may exceed 300 lines. Each module's docstring must
state its single responsibility in one sentence. This is an acceptance criterion for DWR-0.

When a module approaches 250 lines during development, split it before the pull request is
merged. The Compiler (`compiler.py`) and Engine (`engine.py`) are the highest-risk modules
for size growth. If either exceeds 200 lines before DWR-2 is complete, treat it as a scope
signal and split immediately.

Keep wrappers as pure import-and-call shims. Business logic belongs in importable
underscore-named modules so unit tests do not require subprocesses.

---

## Implementation Phases

### DWR-minus: Storage Proof *(new — implement before DWR-0)*

**Purpose:** prove the storage model and file structure in isolation before the engine is built.
No orchestration, no compiler, no transitions, no approval manager.

Deliverables:

- workflow ID generation (format: `ttw-YYYYMMDD-NNN`)
- `workflow.json` writer with schema validation
- append-only `events.jsonl` writer
- event replay that projects the same state as the live workflow
- `tailtrail workflow show` reading from the file and displaying it
- `tailtrail workflow events` reading the journal

Acceptance:

- the storage format is validated by the JSON schemas from DWR-0
- replay of any saved `events.jsonl` produces the same status as the live workflow
- an interrupted write (simulated by truncating the file) does not corrupt the last valid state
- `workflow show` on a file with a sequence gap in `events.jsonl` reports a detected gap,
  not a wrong status

Phase exit criteria:

> DWR-minus is complete when: replay test passes for all event types, the interrupted-write
> recovery test passes, and `tailtrail workflow show` reads a hand-crafted valid workflow file
> without error.

---

### DWR-0: Contract And Inventory

Deliverables:

- map existing Navigator routes and Feature Registry IDs to stage types
- define schemas, state transitions, action classes, and reason codes
- define workflow storage and privacy boundary
- add registry entry for the runtime
- add architecture and command documentation
- **module size contract documented and enforced** (no module > 300 lines)
- **`clarify` stage capability ID and schema defined**

Acceptance:

- every initial stage maps to existing TailTrail behavior
- no duplicate feature taxonomy is introduced
- schemas reject illegal status and transition values
- no module in `workflow_runtime/` exceeds 300 lines at end of phase

Phase exit criteria:

> DWR-0 is complete when: all schemas validate their own example fixtures, every stage in all
> six templates has a defined capability ID in the Feature Registry, and the module size
> constraint passes a line-count check.

---

### DWR-1: Local State Engine

Deliverables:

- workflow models and atomic JSON storage (building on DWR-minus)
- transition engine with legal/illegal validation
- workflow create, list, show, status, pause, cancel, and events commands
- lock and doctor behavior

Acceptance:

- projection can be rebuilt from events
- illegal transitions fail closed with a structured error
- interrupted writes recover without corrupting the last valid state

Phase exit criteria:

> DWR-1 is complete when: every legal and illegal transition has a passing test, the event
> replay test passes, and `tailtrail workflow doctor` diagnoses and reports a stale lock
> without deleting it.

---

### DWR-1.5: Workflow Compiler *(new — split from DWR-2)*

**Purpose:** build and validate the Workflow Compiler independently before connecting it to
`start`. This is the highest-risk component. If the compiler is wrong, every downstream
workflow is wrong.

Deliverables:

- all 12 compiler steps implemented and individually testable
- acyclic prerequisite graph resolver
- duplicate-stage detection and compatible-evidence merge
- plan hash and revision generation
- compiler test suite with deterministic fixtures (no live Navigator calls)

Acceptance:

- each of the 12 steps has at least one passing unit test
- the prerequisite resolver rejects a cycle with a structured error
- the plan hash changes when the stage list changes and does not change when
  only the task description changes
- contradictory features (e.g. `aidlc-off` and `aidlc-standard`) cause a structured
  rejection, not a silent merge

Phase exit criteria:

> DWR-1.5 is complete when: compiler unit tests pass for all 12 steps, the cycle-detection
> test passes, and the hash stability test passes (same stages = same hash regardless of
> description change).

---

### DWR-2: Navigator And Approval Integration

Deliverables:

- wire Workflow Compiler (from DWR-1.5) to `start`
- `start` draft and approval flow (in-memory draft; persist only after approval)
- plan revisions and hashes
- stage approval records
- session approval (`--session --action-class`)
- policy pre-approval (`pre_approved_stages` in policy file)
- concise status and `next` output
- `--no-workflow` flag on `start`

Acceptance:

- `guide` remains read-only and never creates workflow state
- no workflow persists before approval
- edited plans invalidate previous approval only on the three defined triggers
- Navigator output does not become noisier than the current compact mode
- session approval writes an approval event with `approval_source: session`
- policy pre-approval writes an approval event with `approval_source: policy-reference`

Phase exit criteria:

> DWR-2 is complete when: the `guide` read-only test passes, the `start` approval gate test
> passes, the plan-revision invalidation test covers all three triggers and no others, and
> `tailtrail start "task" --no-workflow` returns a compact plan identical to the pre-DWR output.

---

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

Phase exit criteria:

> DWR-3 is complete when: the freshness invalidation matrix test covers at least 8 change
> types (source edit, manifest change, policy change, graph stale, doc-only edit, branch
> change, dependency add, security finding), resume successfully preserves unaffected stages
> and marks affected ones stale, and the completion receipt passes schema validation.

---

### DWR-4: Core Capability Adapters

Deliverables:

- bootstrap and graph discovery adapters
- implementation boundary adapter
- focused testing adapter
- review and requirement-fulfilment adapter
- security and quality approval adapters
- handoff adapter

Acceptance:

- small, delivery, risk, review-only, CI-remediation, and discovery templates run end to end
  using deterministic fixtures
- every adapter uses Feature Registry IDs and typed outputs

Phase exit criteria:

> DWR-4 is complete when: the `small change -> focused test -> review -> fulfilment ->
> completion receipt` vertical path passes an Evaluation Harness deterministic scenario,
> and `tailtrail start "task" --no-workflow` is confirmed still working before removing the flag.

---

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

Phase exit criteria:

> DWR-5 is complete when: token label test confirms no `measured` claim without telemetry,
> the learning capture proposal test confirms only post-completion trigger, and the
> Meta-Harness signal test confirms no raw prompt or source body is present.

---

### DWR-6: MCP And CI Continuation

Deliverables:

- minimal MCP workflow tools
- optional CI continuation for explicitly approved non-interactive stages
- registry and governance drift checks

Acceptance:

- MCP cannot forge approvals or bypass transition rules
- CI cannot perform project writes, fixes, publish actions, or external scans unless
  explicitly configured and approved by policy

Phase exit criteria:

> DWR-6 is complete when: the forged-approval negative test passes for all MCP state-changing
> tools, and the CI continuation test confirms no project writes occur without a policy-backed
> approval record.

---

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

---

## Test Strategy

### Unit Tests

- schema validation for all 7 schemas
- every legal and illegal state transition
- event ordering and replay
- plan hashing and revision invalidation — three triggers and no others
- approval scope and expiry
- session approval expiry on pause and plan revision
- policy pre-approval resolution and event record
- retry eligibility per action class
- freshness invalidation matrix (8 change types minimum)
- atomic storage recovery
- lock handling (stale lock diagnosis, not silent deletion)
- registry capability validation and drift detection
- privacy redaction and event size limits
- compiler steps 1 through 12 individually
- acyclic graph resolver — cycle detection
- module size guard (no module > 300 lines)

### Integration Tests

- `start -> approve -> execute -> validate -> review -> complete`
- `start --no-workflow` returns compact plan without workflow state
- pause and resume after repository change
- failed test followed by approved fix loop
- rejected scanner approval
- stale graph refresh
- policy change during a paused workflow
- missing capability and registry drift
- MCP status and guarded transition behavior
- Evaluation and Meta-Harness event production
- session approval covers read_local stages, blocked on write_project

### Deterministic Scenarios

- small bug fix with focused unit test
- feature requiring AIDLC (`clarify` stage) and handoff
- review-only request with optional fixes rejected
- CI failure with graph overlay and recheck
- vulnerability finding requiring explicit scan and fix approval
- dependency request rejected by policy
- cross-repo reference workflow
- interrupted workflow resumed after changed files

### Negative Tests

- forged approval ID
- modified plan after approval (only the three defined triggers cause revision)
- non-trigger edit (task description change) does not invalidate approval
- event journal sequence gap
- attempted transition from `completed` to `running`
- imported workflow containing path traversal
- event containing a secret-like value
- retry of code-changing action without approval
- command reconstructed from an untrusted event
- external provider invoked without opt-in
- session approval used for a `write_project` action (must be rejected)
- `start` with DWR active changes output format (regression guard until `--no-workflow` removed)

---

## Migration And Compatibility *(revised — `--no-workflow` escape hatch added)*

- Existing commands continue to work.
- `start`, `guide`, `next`, review, test, scanner, graph, and handoff commands become
  adapters gradually.
- No existing workflow history is migrated automatically.
- Existing `.tailtrail` files remain authoritative for their current features.
- The runtime stores references to existing artifacts rather than copying them.
- Compatibility aliases should print the corresponding workflow stage only after the runtime
  is stable.
- Feature Registry and documentation drift checks must cover the new command surface.

**`--no-workflow` transition period:**

The `--no-workflow` flag on `start` must be available from the moment the Durable Workflow
Runtime changes `start` output in DWR-2. It must not be removed until all of the following
are true:

1. DWR-4 is complete and the small-change vertical path has passed an Evaluation Harness
   scenario.
2. The installed SKILL.md and AGENTS.md in Codex/Copilot integrations have been updated to
   handle the new output format.
3. At least one real project has used the workflow runtime through a complete task cycle.

Until the flag is removed, every release note must mention that `--no-workflow` is available
for integrations that depend on the pre-DWR compact output format.

---

## Risks And Mitigations *(revised — approval fatigue row updated)*

| Risk | Mitigation |
|---|---|
| More process slows small tasks | smallest matching template; tiny tasks may remain direct and read-only via `--no-workflow` |
| Navigator output becomes noisy | compact default status; verbose details on demand |
| Runtime duplicates existing features | adapters and registry IDs; no parallel feature taxonomy |
| Stale state creates wrong decisions | stage-specific hashes and explicit stale status |
| Approval fatigue | **Session approval** covers low-risk action classes for a session; **policy pre-approval** covers idempotent read-only stages without interactive prompts; both still write approval events |
| Hidden autonomy | deterministic transitions and explicit approval records |
| Workflow files leak sensitive data | strict schemas, redaction, size caps, local-only default |
| Retrying creates unwanted changes | no automatic retries for project writes or publish actions |
| State corruption | atomic writes, append-only events, replay validation, doctor command |
| Distributed design overwhelms local use | defer enterprise adapter until measured need exists |
| Workflow Compiler correctness | DWR-1.5 treats the compiler as its own phase with independent tests before wiring to `start` |
| Module monolith recurrence | 300-line module size contract enforced from DWR-0 with a line-count check |
| Existing integrations break when output format changes | `--no-workflow` escape hatch maintained through DWR-4 |

---

## Decisions Required Before Implementation

1. Should `start` create a draft workflow immediately, or only after the user approves the
   displayed plan?
   **Recommended:** create an in-memory draft, persist only after approval.

2. Should tiny informational tasks create workflow state?
   **Recommended:** no; use read-only Navigator guidance and optional discovery receipts.

3. Should local workflow records ever be committed?
   **Recommended:** no; only explicitly sanitized summaries may be shared.

4. How long should completed local workflows be retained?
   **Recommended:** configurable count-based retention with manual cleanup, no background
   deletion in V1.

5. Should a successful code-changing workflow require both review and requirement fulfilment?
   **Recommended:** yes for default templates, with explicit policy-backed skip reasons.

6. Can CI advance a workflow?
   **Recommended:** only approved non-interactive validation/reporting stages; never code
   fixes or publishing by default.

7. Should multiple active workflows be allowed?
   **Recommended:** multiple drafts/read-only workflows, but one code-changing workflow per
   repository.

8. *(new)* Should the `clarify` stage be skippable without a reason code for tasks with
   clear acceptance criteria?
   **Recommended:** yes, but only with an explicit skip reason code recorded in the event
   journal. Silent skip is not allowed.

9. *(new)* Should session approval be available before the user approves the initial plan?
   **Recommended:** no. Session approval may only be granted after the initial plan approval
   is on record.

---

## Operational Metrics

Measure runtime usefulness before considering distributed execution:

- workflows started, approved, completed, cancelled, and blocked
- median stages per workflow
- stage failure and skip rates
- resume success rate
- stale-stage recomputation rate
- approval prompt count per workflow
- session approval usage rate (signals whether interactive approval is too frequent)
- policy pre-approval usage rate (signals which stages teams routinely approve)
- percentage of completed code changes with focused validation and review
- requirement-fulfilment pass rate
- context budget expansion rate
- measured or estimated token evidence coverage
- workflow fit findings from Meta-Harness

These metrics must remain categorical or aggregate unless real measured evidence is available.
Do not claim productivity, quality, or token improvement from workflow completion alone.

---

## Recommended First Release

Implement DWR-minus, DWR-0, DWR-1, DWR-1.5, DWR-2, and DWR-3 first. This provides:

- proven storage model (DWR-minus)
- durable contract and schemas (DWR-0)
- local state engine (DWR-1)
- validated Workflow Compiler independent of `start` (DWR-1.5)
- approval flow and `--no-workflow` escape hatch (DWR-2)
- evidence, resume, freshness (DWR-3)

Then connect one complete vertical path in DWR-4:

```text
small change -> focused test -> review -> requirement fulfilment -> completion receipt
```

Validate that path through Evaluation Harness before connecting risk, scanner,
cross-repository, and CI workflows. Remove `--no-workflow` only after this path is validated.

---

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

The user should experience one clear workflow, while TailTrail retains the precision,
guardrails, evidence, and reversibility needed for enterprise AI-assisted development.

