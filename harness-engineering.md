# TailTrail Harness Engineering

## Document status and reading guide

**Status:** design proposal. This document describes a future TailTrail harness;
it does not claim that the runtime, commands, schemas, adapters, or control loops
below already exist.

This document records the working decisions behind TailTrail Harness Engineering:

1. The hard agent-coding problem is not only syntax, lint, or type failures. It
   is proving that a multi-file change actually fulfills the requested behavior
   across callers, tests, and architectural boundaries.
2. Fast deterministic controls are important inputs, but the primary product
   value is a requirement-aware completion loop that reduces repeated human
   prompts such as "run it again and fix the next failure."
3. Drift awareness requires an approved anchor. TailTrail must compare each
   correction cycle against a user-approved desired state, not merely against
   the latest diff or a green test suite.
4. The anchor is represented by `approved.md`; the observed state of each agent
   attempt is represented by `actual.md`. Their comparison exposes behavior,
   architecture, scope, and evidence drift.
5. Maintainability, Architecture Fitness, and Behaviour are complementary
   harnesses. They should share one approved anchor and one correction loop,
   rather than become disconnected features.
6. Human judgment remains essential for ambiguous requirements, changed public
   contracts, design trade-offs, and approval of changed expected behavior.

### What exists today versus what this design proposes

TailTrail already has building blocks: Navigator planning, local policy and
guardrails, Code Graph impact hints, Test Precision, requirement-aware review,
quality/test command guidance, evaluation artifacts, and registry/governance
drift checks. Those features are useful inputs, but they are not yet one
persisted approved-anchor and correction-loop implementation.

| Capability | Current position | Proposed harness addition |
| --- | --- | --- |
| Task planning | Navigator can produce a scoped plan and likely impact. | Turn the approved plan into a versioned desired-state contract. |
| Requirements | Review can compare a diff with a compact goal. | Track every required outcome through explicit completion states across cycles. |
| Impact | Code Graph and Test Precision find likely callers/tests. | Compare actual changed paths and behavior against the approved impact boundary. |
| Validation | Tests, quality commands, and review are available separately. | Select controls, normalize results, and feed one bounded correction task to the agent. |
| Drift | Registry/governance drift checks protect TailTrail's own docs and feature inventory. | Add task-level requirement, architecture, behavior, scope, and evidence drift detection. |
| Agent control | Guidance files and commands influence an agent. | Keep the agent anchored without claiming a universal autonomous orchestration runtime. |

### Design decisions and rejected simplifications

| Decision | Reason |
| --- | --- |
| Do not make the harness primarily an approval workflow. | Approval is necessary, but it does not by itself tell whether a multi-file change is complete. |
| Do not make it only a fast lint/test wrapper. | Modern agents often repair simple diagnostics; the costly failures are incomplete logic, missed callers, and test/behavior mismatches. |
| Do not use one opaque drift score. | A score hides why work drifted. TailTrail must report requirement, architecture, behavior, scope, and evidence reasons separately. |
| Do not treat green tests as completion proof. | Tests may be narrow, missing, stale, or weakened by the agent. Requirements need linked evidence. |
| Do not let an agent overwrite expected behavior. | Silent updates to an approved fixture are behavior-level test-chasing. Only humans approve a changed desired state. |
| Do not cache the entire repository. | The anchor should be a compact, privacy-preserving contract and evidence index, not a raw source/prompt archive. |
| Do not create unbounded self-correction. | Correction loops must stop on pass, repeated failure, ambiguity, timeout, scope expansion, or human escalation. |

### Core vocabulary

| Term | Meaning |
| --- | --- |
| **Change Intent Anchor** | A user-approved local contract describing the relevant current state, desired state, boundaries, invariants, and required evidence. |
| **Approved state** | The desired behavior and architectural shape accepted by a human, stored in `approved.md`. |
| **Actual state** | The observed behavior, changed paths, control results, and unresolved gaps produced by the current agent attempt, stored in `actual.md`. |
| **Drift checkpoint** | A per-cycle comparison of actual state to approved state. |
| **Completion gap** | A requirement that is failed, blocked, ambiguous, or implemented without adequate evidence. |
| **Correction packet** | The smallest agent task that explains one gap, exact evidence, allowed scope, and next validation. |
| **Harness template** | A reusable set of guides, controls, scenario formats, and rules for a known project topology or technology stack. |

### End-to-end reference lifecycle

```mermaid
flowchart TB
    A[Developer task] --> B[Navigator or AIDLC requirement gathering]
    B --> C[Current state, impact map, and risks]
    C --> D[Draft approved.md]
    D --> E{Human approves desired state?}
    E -->|Revise| B
    E -->|Approve| F[Change Intent Anchor]
    F --> G[Agent implementation]
    G --> H[actual.md: observed code, paths, and checks]
    H --> I[Drift checkpoint]
    I --> J{Requirement, architecture, behavior, scope, and evidence aligned?}
    J -->|No| K[One bounded correction packet]
    K --> G
    J -->|Yes| L[Maintainability review]
    L --> M[Human review and handoff]
    M --> N[Optional approved learning: improve guide, scenario, or sensor]
```

## Navigator as Harness Router

Navigator should steer Harness Engineering; Harness Engineering should not replace
Navigator. Navigator decides whether a task needs no harness, a lightweight
anchor, a requirement-completion loop, or the full maintainability/architecture/
behaviour set. The harness then uses the selected anchor to evaluate the agent's
actual change and provide correction feedback.

```text
Navigator: What is the smallest harness level that makes this task trustworthy?
Harness:   Did the current change reach the approved desired state without drift?
```

The full harness must not run for every task. A typo, comment edit, formatting
change, or tiny configuration change with no behavior impact should retain the
normal lean TailTrail workflow. Requiring approval artifacts, scenarios, and
correction loops for such work would add friction and teach users to ignore the
harness.

```mermaid
flowchart TB
    A[Developer task] --> B[Navigator]
    B --> C{Task complexity and risk}
    C -->|Tiny or no behavior change| D[Normal lean workflow]
    C -->|Small code change| E[Light Change Intent Anchor]
    C -->|Multi-file logic or behavior risk| F[Completion Harness proposal]
    E --> G[Agent change]
    F --> H{Human approves anchor?}
    H -->|Yes| G
    H -->|Revise| B
    G --> I{Evidence or drift gap?}
    I -->|No| J[Review and handoff]
    I -->|Yes| K[Completion Harness loop]
    K --> G
```

### Harness levels selected by Navigator

| Level | When Navigator selects it | What TailTrail creates | What it intentionally avoids |
| --- | --- | --- | --- |
| **No harness** | Documentation, comments, formatting, or a trivial non-behavioral configuration edit | Normal plan and proportional validation guidance | No anchor, scenario, or correction-loop state. |
| **Light Change Intent Anchor** | Small code fix with a clear requirement and one focused test path | Goal, one/two expected outcomes, changed-path boundary, focused evidence command | No multi-cycle correction loop unless a drift signal appears. |
| **Requirement Completion Harness** | Logic/validation/business-rule change, multiple files/callers, regression risk, tests likely to change | `approved.md`, `actual.md`, requirement matrix, focused evidence plan, bounded correction loop | No broad architecture template or expensive inference unless needed. |
| **Full three-lens harness** | Architecture boundary, security/data/API change, workflow/state-machine change, or risky multi-module work | Completion Harness plus Maintainability, Architecture Fitness, and Behaviour checks | No autonomous unlimited run; humans still approve material scope/intent changes. |
| **AIDLC-assisted harness** | Broad, ambiguous, regulated, multi-team, or long-running feature | AIDLC gathers/clarifies requirements before Navigator proposes the anchor | AIDLC is not added to small, well-scoped fixes. |

### Routing signals

Navigator should use explainable local signals rather than a hidden complexity
score. Any selected harness level must say why it was selected and which heavier
controls were intentionally skipped.

| Signal | Suggested routing implication |
| --- | --- |
| One known file, no behavior change, no affected caller/test | No harness or normal lean workflow. |
| Small code fix with a clear expected outcome and focused existing test | Light anchor. |
| More than one likely implementation file or important caller | Completion Harness. |
| Validation, business rule, state transition, or error-contract change | Completion Harness with Behaviour evidence. |
| Existing test failure or an expected test update | Completion Harness with failure classification and test-chasing protection. |
| Public API, schema/data model, dependency, auth/security, or architectural boundary | Full three-lens harness and explicit re-approval conditions. |
| Requirement says "all flows", "preserve", "do not break", or "regression" | Completion Harness because preserved behavior needs explicit evidence. |
| One failed agent correction attempt | Escalate the current run to a Completion Harness checkpoint. |

### Default behavior after implementation

For meaningful code changes, Navigator should default to a **light anchor**, not
a full correction loop. After the agent edits code, TailTrail evaluates the
available evidence:

| Post-change signal | Navigator handoff |
| --- | --- |
| Focused tests pass, approved paths were preserved, and no completion row is missing | Proceed to normal TailTrail Review and handoff. |
| Test/check fails | Enter the Requirement Completion Harness and produce one bounded correction packet. |
| Agent changes an unexpected path, dependency, protected file, API, schema, or security boundary | Mark scope/architecture drift; invalidate anchor when material and ask for re-approval. |
| Test change lacks a requirement link or weakens an assertion | Mark evidence drift and require review before treating it as proof. |
| Requirement row has no focused evidence | Mark `implemented-not-validated`; request/run the smallest adequate check. |

### Example Navigator output

For a task such as "change existing validation logic and add focused tests," a
Navigator report should look like this:

```text
Harness recommendation: Requirement Completion Harness

Why selected:
- logic change affects shared validation and its service caller
- focused tests must prove both changed and preserved behavior
- error propagation is a likely multi-file completion risk

Proposed anchor:
- desired behavior: zero rejected; positive amount remains accepted
- architecture: service uses shared validation path
- evidence: validation and service-path tests
- correction budget: at most two cycles before human escalation

Skipped for now:
- AIDLC: task is currently small and requirements are clear
- provider-backed semantic analysis: local graph and focused source inspection are sufficient

Next action:
Review and approve approved.md before implementation.
```

Navigator remains advisory and deterministic. It can recommend a harness level,
prepare the anchor, and explain its routing decision; it must not silently start
an expensive agent loop, rewrite expected behavior, expand scope, or declare
completion without the evidence defined by the approved anchor.

## Purpose

TailTrail's harness engineering work builds an outer quality harness around a
coding agent. It should increase the chance that an agent gets a change right on
the first attempt, then provide fast feedback that lets the agent correct issues
before they reach human review.

```text
TailTrail Harness = feedforward guides
                  + feedback sensors
                  + bounded self-correction loop
```

The harness is not a replacement for the coding model, developer judgment,
existing tests, CI, security review, or repository policy. It makes those
controls available to the agent at the right time and turns their results into
actionable feedback.

This design is informed by Birgitta Boeckeler's
[Harness engineering for coding agent users](https://martinfowler.com/articles/harness-engineering.html).

## Outcome

A well-built harness should:

- improve first-pass agent quality with relevant rules, examples, tools, and
  acceptance checks before editing;
- catch deterministic problems quickly through local computational checks;
- present findings in a compact form an agent can use to self-correct;
- reserve human review for requirements and judgment automation cannot reliably
  decide; and
- improve its guides and sensors when the same failure happens repeatedly.

## Model

```mermaid
flowchart LR
    A[Developer goal] --> B[Feedforward guides]
    B --> C[Coding agent]
    C --> D[Computational sensors]
    D --> E{Checks pass?}
    E -->|No| F[Structured correction feedback]
    F --> C
    E -->|Yes| G[Optional inferential review]
    G --> H[Human review of remaining judgment]
    H --> I[Improve a guide or sensor]
    I --> B
```

### Feedforward guides

Guides reduce the likelihood of a poor first implementation.

| Guide | TailTrail role |
| --- | --- |
| `AGENTS.md`, policy, skills, and guardrails | Explain repository rules, safeguards, conventions, and constraints. |
| Navigator plan | Turns a goal into a small, explicit plan and likely validation path. |
| Code Graph and context routing | Selects relevant source, callers, tests, and policy rather than loading an entire repository. |
| Test Precision | Identifies the smallest reliable checks before the agent edits. |
| Structural rules and harness templates | Define architecture boundaries, forbidden dependencies, and topology conventions. |

### Feedback sensors

Sensors observe the agent's change and report whether it is moving toward the
desired state.

| Sensor | Execution type | Feedback |
| --- | --- | --- |
| Focused tests | Computational | Failing test, expected/actual behavior, and relevant source and test paths. |
| Lint, format, type, and build checks | Computational | Rule ID, location, exact diagnostic, and next action. |
| AST and structural checks | Computational | Boundary violations, dependency drift, changed symbols, and affected tests. |
| Dependency and security checks | Computational | Exact component/finding, severity, and relevant policy gate. |
| TailTrail Review | Inferential | Requirement gaps, unnecessary complexity, weak validation, and missed project patterns. |
| Semantic/provider-backed analysis | Inferential or provider-backed | Advisory relationship evidence, explicitly labeled by source. |

## Computational first

| Execution type | Characteristics | Examples |
| --- | --- | --- |
| **Computational** | Deterministic, CPU-run, fast, and reliable enough for each relevant change. | Tests, linters, type checkers, builds, AST analysis, structural and architecture checks. |
| **Inferential** | Richer semantic judgment but slower, costlier, and non-deterministic. | Agent reasoning, AI code review, semantic analysis, LLM-as-judge. |

Computational controls should run first whenever they can answer the question.
They catch mechanical and structural problems without consuming model reasoning.
Inferential controls should then focus on requirements, overengineering,
trade-offs, and semantic intent.

## Correction loop

1. TailTrail selects applicable guides and computational sensors for the task.
2. The coding agent makes a small change.
3. TailTrail runs the smallest approved local checks.
4. TailTrail returns a compact correction packet with the exact command,
   affected path/symbol, evidence, failure reason, and next action.
5. The agent corrects the change and the selected checks run again.
6. The loop stops on pass, timeout, repeated failure, ambiguous output, scope
   expansion, or human escalation.
7. After fast checks pass, TailTrail Review can inspect semantic and
   requirement-level issues.

The loop must be bounded. TailTrail should never retry indefinitely or turn an
unrun, skipped, timed-out, or ambiguous control into a passing result.

## Token Harness Integration

Token Harness is a supporting capability for Harness Engineering. It does not
decide whether a requirement is correct or complete. Its role is to make each
anchor, checkpoint, correction packet, and review packet small enough for an
agent to use efficiently while preserving the exact evidence required for trust.

```mermaid
flowchart LR
    A[approved.md and selected source] --> B[Token Harness context plan]
    B --> C[Agent correction task]
    C --> D[actual.md and control output]
    D --> E[Smallest unmet anchor row]
    E --> B
```

### Token Harness responsibilities inside one run

| Harness stage | Token Harness responsibility | Safe context to provide |
| --- | --- | --- |
| Anchor proposal | Build the smallest exact context needed to understand current state and desired outcomes. | Compact goal, applicable policy, selected source/callers/tests, graph summary, known unknowns. |
| Initial implementation | Create an agent packet tied to approved scope and evidence plan. | Relevant `approved.md` rows, exact changed files, required helpers, focused tests, allowed commands. |
| Failed checkpoint | Prevent the agent from rereading unrelated history. | Unmet requirement row, relevant diff, exact failed output, affected source/caller/test, one next action. |
| Review | Keep semantic review focused on the completed change. | Compact diff summary, changed tests with rationale, checkpoint state, unresolved risks, exact retrieval pointers. |
| Retrospective | Produce privacy-safe evidence about context choices. | Context receipt metadata, selected/avoided artifact pointers, run ID, checkpoint number, evidence label. |

Example correction packet context:

```text
Load exactly:
- approved.md: zero-dollar submission behavior and architecture rule
- actual.md: service-path mismatch
- src/claims_api/service.py
- tests/test_claim_service.py
- exact focused test failure

Avoid:
- full roadmap and unrelated architecture documents
- unrelated repository modules
- previous long agent conversation
- unrelated scanner logs
```

### Exactness boundaries

Token reduction must never change the evidence that the harness uses to judge
completion. The following material remains exact and retrievable:

- approved requirements, invariants, allowed scope, and re-approval conditions;
- current diff, changed source, policy/security rules, dependency manifests, and
  lock files when relevant;
- exact failed test, build, lint, type, scanner, or structural-check evidence;
- public API/schema/security boundary changes; and
- the original approved and actual scenario content used by a checkpoint.

Safe bulky material can be reduced only when the Token Harness records a
retrieval pointer and does not remove a material fact. Examples include verbose
tool logs, repetitive scanner output, large JSON reports, or long documentation
that is not itself part of the requirement or evidence.

### Required Token Harness updates

The existing Token Harness concepts should be extended, not rebuilt:

| Update | Purpose |
| --- | --- |
| Run and checkpoint linkage | Associate context receipts and Token Harness ledger events with `run_id`, anchor fingerprint, and checkpoint number. |
| Anchor-aware classification | Mark anchor rows and exact failure evidence as `must-be-exact`; mark safely reducible background artifacts separately. |
| Correction-packet route | Build the next packet from the smallest unmet requirement row rather than prior chat history. |
| Per-cycle receipts | Record selected, avoided, and escalated context for each correction cycle without raw prompts/source. |
| Context-growth signal | Flag when repeated corrections require progressively broader context, which may indicate an unclear anchor, missed impact path, or loop drift. |
| Measured-claim boundary | Keep estimated/local context evidence separate from actual provider token telemetry. |

Useful local records could look like:

```text
.tailtrail/runs/<run-id>/context/checkpoint-01-receipt.json
.tailtrail/runs/<run-id>/context/checkpoint-02-receipt.json
.tailtrail/token-harness-events.jsonl
```

The harness may say that it loaded less irrelevant context or used a local
context receipt. It must not claim exact token savings, cost reduction, or model
efficiency unless normalized before/after provider usage telemetry exists.

## Evaluation Harness Integration

Evaluation Harness operates one level above a single harness run. The Change
Intent Anchor and Completion Harness ask whether **this change** reached the
approved desired state. Evaluation Harness asks whether using TailTrail Harness
Engineering improves outcomes across repeatable scenarios or approved local
portfolio evidence.

```mermaid
flowchart LR
    A[One approved/actual run] --> B[Completion evidence]
    B --> C[Sanitized saved scenario]
    C --> D[Evaluation Harness comparison]
    D --> E[Harness quality findings]
    E --> F[Human-approved guide, sensor, or template improvement]
```

| Layer | Primary question | Typical evidence |
| --- | --- | --- |
| Completion Harness | Did this agent change fulfill the approved task? | `approved.md`, `actual.md`, checkpoints, focused controls, review result. |
| Evaluation Harness | Does the harness improve completion quality across tasks? | Saved baseline/TailTrail artifacts, deterministic scenario scores, approved outcome records. |

### What Evaluation Harness should measure

Evaluation must not reduce the new harness to a generic "tests passed" score.
Its dimensions should reflect the actual design goals:

| Evaluation dimension | What it measures |
| --- | --- |
| Requirement completion | Share of required anchor rows that reach `validated` rather than missing, failed, or ambiguous. |
| Architecture preservation | Whether approved required paths and boundaries were preserved rather than bypassed. |
| Behaviour evidence | Whether approved scenarios have credible focused evidence, not only narrow agent-written tests. |
| Scope discipline | Unexpected files, dependencies, API/schema changes, or unapproved boundary expansion. |
| Test integrity | Requirement-linked test changes versus weakened, skipped, or suspicious assertions. |
| Correction efficiency | Number of bounded cycles before pass, escalation, or abandonment. |
| Escalation quality | Whether the harness stopped for an ambiguity instead of allowing the agent to invent behavior. |
| Review readiness | Whether a human receives approved intent, actual result, evidence, and unresolved risks in one handoff. |
| Context discipline | Whether receipts show relevant, bounded context; exact token savings remain a separate measured metric. |

### Deterministic evaluation scenarios

The first Evaluation Harness integration should use saved, sanitized artifacts,
not live model calls. Each scenario can compare a baseline outcome with a
TailTrail Harness outcome.

```text
Scenario: multi-file validation change

Baseline artifact:
- direct validation function changed
- service caller missed
- unit test passes
- required submission behavior remains incomplete

TailTrail Harness artifact:
- approved desired behavior and service-path architecture rule
- missing caller path detected at checkpoint
- one bounded correction packet issued
- focused service test passes
- requirement matrix becomes complete
```

The scenario scorer should verify facts present in the artifacts. It should not
pretend to prove that a live model will always behave identically. Optional live
agent evaluation is a later explicit-approval mode, after deterministic scenario
scoring is stable.

### Required Evaluation Harness updates

| Update | Purpose |
| --- | --- |
| Harness scenario type | Add saved scenarios for approved/actual comparison, architecture drift, behavior drift, test-chasing, and escalation. |
| Anchor-aware event schema | Normalize run ID, anchor version/fingerprint, completion states, drift categories, checkpoint count, and evidence labels. |
| Baseline vs. harness rubric | Score the quality of completion evidence and handoff, not just code/test output. |
| Scenario fixtures | Commit sanitized `approved`, `actual`, baseline, and expected-score fixtures that are reproducible without a live model. |
| Portfolio reporting | Summarize recurring completion gaps, drift categories, correction cycles, and unresolved-decision rates using opt-in local evidence. |
| Claim guardrails | Separate observed local evidence from measured claims about defect reduction, review-time reduction, or token savings. |

Potential fixture layout:

```text
benchmarks/evaluation/scenarios/harness-completion-validation/
  scenario.json
  baseline-artifact.md
  tailtrail-artifact.md
  approved.md
  actual.md
  expected.json
  README.md
```

### Learning from evaluation without surveillance

Evaluation results should improve TailTrail only through a controlled steering
loop. For example, repeated service-path omissions could propose a stronger
Navigator caller check or a new approved scenario. Repeated false-positive
architecture findings could weaken or retire a noisy rule.

Any such change remains proposal-first, human-approved, test-backed, reversible,
and privacy-preserving. TailTrail should not upload raw prompts, source code,
customer data, logs, agent transcripts, or repository identities merely to
measure harness quality.

### Integration sequence

1. Implement the Change Intent Anchor and Requirement Completion Harness.
2. Link Token Harness receipts and ledger events to run IDs/checkpoints.
3. Add deterministic Evaluation Harness fixtures for approved/actual comparison
   and drift detection.
4. Gather opt-in local outcome evidence from real tasks.
5. Use the evidence to improve guides, sensors, and templates.
6. Make quality, review-effort, or token-efficiency claims only when the
   corresponding evidence is measured and credible.

## Change Intent Anchor

Drift awareness needs an anchor. Without an approved reference for the desired
result, a coding agent and a reviewer can only compare the latest diff with the
latest test output. That makes it easy to confuse "the suite is green" with
"the requested change is complete."

TailTrail should create a versioned, local **Change Intent Anchor** before
implementation. It is an approved contract connecting the current project
state, the desired project state, the allowed change boundary, and the evidence
required to demonstrate completion.

```text
Current state -> approved desired state -> observed result and evidence
```

The anchor is not a copy of the whole repository and should not be described as
only a cache. It is a small, reviewable change contract. Caching can make its
local representation fast to retrieve; the important property is that the user
approved the intent before an agent starts correcting toward it.

```mermaid
flowchart LR
    A[User task] --> B[Requirement decomposition]
    B --> C[Current-state and impact map]
    C --> D[Proposed desired-state contract]
    D --> E{User approves?}
    E -->|No or revised| B
    E -->|Yes| F[Local Change Intent Anchor]
    F --> G[Agent implementation]
    G --> H[Harness review checkpoint]
    H --> I[Compare actual state to anchor]
    I --> J{Drift or completion gap?}
    J -->|Yes| K[Bounded correction task]
    K --> G
    J -->|No| L[Completion evidence and human review]
```

### Creating the anchor

For a small task, Navigator, Code Graph, Test Precision, local policy, and exact
source inspection should produce the first anchor proposal. For a broad, risky,
or ambiguous task, AIDLC can deepen requirement gathering before the proposal is
shown to the user. AIDLC is not required for every small fix; the anchor must be
small enough to remain useful.

The user approves the desired state, not an implementation recipe. The agent
may choose a different small implementation if it still reaches the approved
behavior and preserves the approved architectural boundaries and invariants.

| Anchor element | Purpose | Example for a claim-validation change |
| --- | --- | --- |
| Goal | Compact statement of intended outcome | Reject zero-dollar claims while keeping positive claims valid. |
| Current state | Relevant observed baseline, including known failures | `validate_claim_amount(0)` is currently accepted; service behavior relies on it. |
| Desired behavior | Observable outcomes that must become true | Zero rejected through validation and submission; positive amount still accepted. |
| Architecture expectations | Required path, boundaries, and places that must not be bypassed | Submission continues through service to shared validation; no controller-only workaround. |
| Impact boundary | Expected source, caller, test, config, and public-contract scope | Validation, service, and focused claim tests; no dependency/API/schema change. |
| Invariants | Behavior that must remain true | Preserve error type/response contract and existing positive-amount flow. |
| Evidence plan | Focused checks that can prove each outcome | Validation and service-path tests; configured type/lint checks if relevant. |
| Known unknowns | Decisions the agent must not invent | Whether service maps validation errors into a public response. |
| Approval fingerprint | Inputs that make this exact approval valid | Goal/requirements, policy version, baseline revision, relevant paths, and selected controls. |

### Example anchor

```yaml
anchor_version: 1
run_id: claim-zero-amount-001
goal: Reject zero-dollar claim amounts while keeping positive claim amounts valid.

current_state:
  - validate_claim_amount accepts 0
  - claim submission calls validate_claim through the service path

desired_state:
  behaviour:
    - Zero amount raises ClaimValidationError.
    - Positive amount remains accepted.
    - Submission flow preserves the validation failure contract.
  architecture:
    - Use the existing shared validation path.
    - Do not implement a controller-only or caller-specific special case.

expected_scope:
  source:
    - src/claims_api/validation.py
    - src/claims_api/service.py
  tests:
    - tests/test_claim_validation.py
    - tests/test_claim_service.py
  prohibited_without_reapproval:
    - public API change
    - dependency change
    - schema/data migration

evidence_plan:
  - focused validation test for zero and positive amounts
  - focused submission-path test
  - diff review for unrelated scope expansion

known_unknowns:
  - Confirm expected public error mapping if the service currently catches validation errors.
```

The human-facing view should be Markdown, concise, and approval-ready. The
machine-readable view should be sanitized JSON or YAML that supports stable
comparison throughout the correction loop.

### Desired state is not a frozen implementation

The anchor must not overconstrain good engineering. It should state outcomes,
invariants, and important boundaries, not prescribe exact line-by-line edits.

For example, the anchor can require that every claim submission uses shared
validation. It should not require a specific `if amount <= 0` expression if a
project's existing validation helper already provides the correct behavior.

This separation makes the anchor useful for both drift detection and reuse:

| Anchor says | Agent remains free to |
| --- | --- |
| Zero claims are rejected in all submission paths | Choose the smallest compatible validation implementation. |
| Shared validation path is preserved | Refactor within the validation layer when it reduces duplication. |
| Positive claims remain valid | Add the most focused regression coverage matching local test conventions. |
| No public API change without re-approval | Improve internal error handling without changing the external contract. |

### Checkpoints: detect drift during the loop

After each meaningful agent edit, TailTrail should create a **drift checkpoint**.
The checkpoint compares the actual diff, current source path, test results, and
review findings against the approved anchor. It should report explicit state and
reasons, not a single opaque "drift score."

```mermaid
flowchart TB
    A[Approved Change Intent Anchor] --> B[Agent edit]
    B --> C[Architecture fitness comparison]
    B --> D[Behaviour evidence comparison]
    C --> E[Checkpoint status]
    D --> E
    E --> F{Anchor satisfied?}
    F -->|No| G[Smallest drift correction]
    G --> B
    F -->|Yes| H[Maintainability and human review]
```

Example checkpoint:

```text
Checkpoint 2 of 3

Anchor status: partially satisfied

Behaviour:
- Zero rejected by validation: validated
- Positive amount accepted: validated
- Submission preserves validation failure: failed

Architecture:
- Shared validation path: preserved
- Unexpected dependency or protected-path change: none

Drift:
- src/claims_api/service.py converts ClaimValidationError into a success result.

Next correction:
Preserve the validation error in the service path. Re-run the focused service
and validation tests. Do not expand into an API-contract change.
```

The checkpoint should separate these categories:

| Checkpoint category | Question | Typical response |
| --- | --- | --- |
| Requirement coverage | Is every approved outcome validated, failed, blocked, or awaiting a decision? | Correct the unmet outcome or ask the user a focused question. |
| Architecture fitness | Does the actual change preserve required paths and boundaries? | Move logic to the approved layer or request re-approval for a boundary change. |
| Behaviour evidence | Do tests and direct observations demonstrate the desired behavior and preserved invariants? | Add/run focused coverage or fix the behavior. |
| Scope drift | Did the diff move beyond the approved impact boundary? | Classify as required, regression, optional hardening, or unrelated; re-approve if material. |
| Evidence drift | Did a test change, skipped control, or weak assertion make proof less trustworthy? | Require a requirement-linked rationale or escalate. |

### Anchor invalidation and re-approval

An approval only applies to the precise desired state that was reviewed. TailTrail
must invalidate the anchor and request re-approval when a material input changes:

- the developer clarifies, narrows, or expands a requirement;
- a correction needs a new important source path, caller path, or test domain;
- the work changes a public API, security boundary, data model, schema, or
  dependency;
- project policy, an approved architectural rule, or a protected-path rule has
  changed since approval;
- a baseline failure previously considered unrelated is found to affect the
  requested behavior; or
- new evidence exposes two reasonable but incompatible interpretations of the
  desired behavior.

Minor implementation movement within an approved boundary should not force
re-approval. The point is to preserve developer control over material intent
changes, not to interrupt every normal correction.

Example invalidation:

```text
Anchor requires re-approval.

Reason: correction requires changing the public submission response contract.
The approved anchor preserved the existing error-response behavior.

New decision needed:
1. Return the validation error to callers as a client error.
2. Preserve the current response and narrow the requirement to internal validation.
```

### Local storage and privacy

The anchor should live with the local run as an approved/actual document pair:

```text
.tailtrail/runs/<run-id>/approved.md
.tailtrail/runs/<run-id>/actual.md
.tailtrail/runs/<run-id>/checkpoints/checkpoint-01.json
```

The stored form must be compact and privacy-preserving. It should retain exact
requirements, controlled paths, result summaries, approval state, and evidence
pointers. It should not automatically copy raw prompts, full source files,
secrets, customer data, or unredacted logs into durable learning or telemetry.

The approval fingerprint should include a stable baseline revision or diff
identity, applicable policy fingerprint, normalized requirement text, selected
paths, and selected controls. If these inputs materially change, TailTrail can
tell the developer exactly why the anchor is no longer valid.

### Approved and actual documents

`approved.md` is the human-approved desired-state anchor. `actual.md` is the
current observed state generated after an agent edit and its selected checks.
Together they combine the Change Intent Anchor and approved-scenario concepts:

```text
approved.md = what the project is approved to become
actual.md   = what the project currently does after this agent attempt
comparison  = where behavior, architecture, scope, or evidence has drifted
```

`approved.md` is not merely a test fixture. It may contain the goal, behavioral
scenarios, architecture expectations, invariants, expected scope, evidence plan,
known unknowns, and approval fingerprint. `actual.md` uses the same scenario
structure where possible, but records observed results, actual changed paths,
checks run, and unresolved gaps.

Example `approved.md`:

```md
# TailTrail Change Intent Anchor

## Goal

Reject zero-dollar claim amounts while keeping positive claim amounts valid.

## Approved behaviour

### Scenario: zero-dollar claim submission

**Input**

Claim amount: `0`

**Expected result**

Submission: rejected
Error type: `ClaimValidationError`
Message: `Claim amount must be greater than zero`

### Scenario: positive claim submission

**Input**

Claim amount: `100`

**Expected result**

Submission: accepted

## Architecture expectations

- Submission uses the existing service to shared-validation path.
- No controller-only special case.
- No public response-contract change without re-approval.

## Allowed scope

- `src/claims_api/validation.py`
- `src/claims_api/service.py`
- focused claim tests

## Required evidence

- Zero-value validation and submission scenarios pass.
- Positive-value regression scenario passes.
```

Example `actual.md` after an incomplete agent attempt:

```md
# TailTrail Actual State

## Scenario: zero-dollar claim submission

**Observed result**

Validation: rejected
Submission: accepted

## Scenario: positive claim submission

**Observed result**

Submission: accepted

## Architecture observation

- Shared validation rejects zero.
- Service converts the validation error into a success result.

## Evidence run

- Validation test: passed
- Positive-value test: passed
- Submission-path test: failed
```

The comparison report can then state the gap without requiring a reviewer to
read all test assertion code or an agent to reread the whole task history:

```text
Anchor status: partially satisfied

Behaviour drift:
- Approved: zero-dollar submission is rejected.
- Actual: zero-dollar submission is accepted.

Architecture drift:
- Approved: service preserves the shared-validation outcome.
- Actual: service converts the validation error to success.

Next correction:
Fix service error propagation. Do not change approved behavior or public API.
```

For a larger feature, the root `approved.md` can link to focused approved
scenarios, while `actual/` contains generated counterparts:

```text
.tailtrail/runs/<run-id>/
  approved.md
  scenarios/
    checkout.approved.md
    refund.approved.md
  actual.md
  actual/
    checkout.actual.md
    refund.actual.md
  comparison-report.md
```

Only a human can change an approved expected behavior. An agent may create a
proposal or regenerate `actual.md`, but it must never silently overwrite an
approved document. This prevents the scenario equivalent of test-chasing: an
agent cannot make a failing behavior check pass merely by rewriting the expected
output to match an incorrect implementation.

### Approved scenarios as behaviour anchors

For behavior that is easy to represent as domain data, `approved.md` can contain
or link to **approved scenarios** (also called approved fixtures). This approach
is based on the [Approved Scenarios pattern](https://lexler.github.io/augmented-coding-patterns/patterns/approved-scenarios/): validate the scenario runner once, then review human-readable input and expected output rather than large volumes of agent-written assertion code.

An approved scenario is not a generic snapshot. It should contain only the
domain-specific input, expected output, important side effects, and call sequence
that a reviewer can validate by eye.

| Scenario content | Why it belongs in the approved state |
| --- | --- |
| Input data, parameters, and initial state | Explains the condition the behavior must handle. |
| Expected result | Gives the agent and reviewer an unambiguous behavioral destination. |
| Expected side effects or service calls | Captures important workflow/order contracts where the final return value is insufficient. |
| Normalization rules | Excludes dynamic IDs, timestamps, ordering, or other non-deterministic values from false diffs. |
| Requirement link | Shows exactly which desired outcome the scenario proves. |
| Approval metadata | Makes clear who approved a changed expected behavior and why. |

Example approved scenario for a multi-step workflow:

```md
# Scenario: checkout with discount

## Input

User: premium member
Cart: laptop x1, mouse x1
Discount code: SAVE20

## Expected service calls

1. Reserve inventory for laptop and mouse.
2. Calculate pricing for the premium member and discount code.
3. Process payment for the discounted total.

## Expected result

Order: confirmed
Discount: applied
Email: order confirmation sent
```

When the scenario runner executes the current code, it writes the analogous
actual result. TailTrail then performs a domain-readable diff:

```text
Scenario: checkout with discount

Approved: pricing occurs before payment and discount is applied.
Actual: payment is attempted before pricing; no discount is applied.

Behaviour drift: required workflow order and price outcome are not satisfied.
Next correction: restore the pricing step before payment. Do not change the
approved scenario without human approval.
```

Approved scenarios are especially useful for API contracts, event payloads,
workflow transitions, CLI output, generated reports, call sequences, structured
JSON/YAML, and visually inspectable domain output. They are a poor fit for huge
opaque object graphs, unstable output, performance claims, or purely internal
implementation details. In those cases, the anchor should reference focused
tests, metrics, or another appropriate evidence type instead.

#### Scenario lifecycle

```text
1. Developer approves expected behavior in approved.md or <name>.approved.md.
2. Trusted runner executes the scenario against current code.
3. Runner writes actual.md or <name>.actual.md; it never overwrites approved.md.
4. TailTrail compares approved and actual state.
5. Agent receives a correction packet for a mismatch.
6. If the product requirement legitimately changes, the agent may draft a proposal.
7. Human reviews and explicitly promotes the proposal to approved state.
```

The runner itself is part of the harness and must be independently tested.
Otherwise a friendly fixture diff can provide false confidence because the
scenario execution logic is wrong.

## Architecture Fitness Harness

The **Architecture Fitness Harness** compares the actual shape of a change to
the architectural expectations in the approved Change Intent Anchor. It answers:

> Did the agent achieve the desired behavior through the intended system path,
> while preserving the boundaries that make the project maintainable?

This matters because a change can appear to work in one test while being placed
in the wrong layer, bypassing shared validation, duplicating business logic, or
creating a forbidden dependency direction.

```text
Approved path:
request -> service -> shared validation -> domain error

Architecture drift:
request -> controller-only special case -> success response
```

The first path keeps the business rule reusable and consistent across callers.
The second may satisfy one local test while allowing other callers to bypass the
rule entirely.

### Architecture rules belong in the anchor

Architecture fitness is project-specific. TailTrail should not invent a universal
layering model. Instead, the user/team defines a small set of relevant rules in
policy, a harness template, or the anchor itself.

| Architecture expectation | Computational evidence | Example drift |
| --- | --- | --- |
| Layer direction | Import/call graph, AST rule, architecture test | Controller directly imports repository/database module. |
| Required business path | Call graph and focused integration test | Submission bypasses shared validation helper. |
| Forbidden dependency | Manifest/import diff and dependency gate | Small validation change adds a new validation package. |
| Protected boundary | Changed-path check and policy | Agent modifies auth, schema, or generated code without approval. |
| Module ownership | File structure, symbols, and local conventions | Domain logic is added to UI/controller instead of service/domain layer. |
| Public contract stability | API/schema diff and focused contract test | Error response shape changes unexpectedly. |

Architecture sensor output must name the boundary and the proof, not merely say
"architecture issue."

```text
Architecture drift: the zero-amount rule was added in the HTTP controller.

Anchor expectation:
All claim submissions use src/claims_api/validation.py through the service path.

Evidence:
- controller now checks amount == 0 directly
- service path remains unchanged
- another claim caller does not use the controller path

Required correction:
Move the rule to the shared validation path, then run the focused caller tests.
```

### Architecture fitness states

| State | Meaning | Next action |
| --- | --- | --- |
| `preserved` | Actual code follows approved boundaries and paths. | Continue behavior/completion review. |
| `drifted` | Actual code violates an approved boundary or bypasses a required path. | Issue bounded correction task. |
| `expanded-needs-approval` | A legitimate solution requires a new boundary, dependency, API, or data-model change. | Re-anchor and obtain approval. |
| `unknown` | Static evidence cannot establish the path or boundary. | Inspect exact source or run an approved focused check. |

Architecture fitness should begin with deterministic, explainable local signals:
changed paths, imports, AST relationships, known module rules, and focused
contract tests. Inferential review can then decide whether an unusual structure
is justified, but it should not replace direct source and structural evidence.

## Behaviour Harness

The **Behaviour Harness** compares the observed user- or system-visible behavior
to the desired behavior and invariants in the anchor. It answers:

> Does the system now do what the user requested across the relevant flows, and
> does it still preserve the behavior the change was not allowed to break?

It is the main defense against a change that passes a narrow unit test but fails
through a caller, adapter, serializer, API response, state transition, or edge
case that the agent missed.

### Behaviour contract

The desired-state behavior should be written as observable claims, not internal
implementation guesses. For the claims example:

```text
Requirement: zero-dollar claims are invalid.

Behaviour contract:
1. Direct amount validation rejects zero.
2. Claim submission also rejects zero.
3. Positive claims still succeed.
4. The expected validation error/response contract is preserved.
5. Unrelated claim flows retain their prior behavior.
```

TailTrail tracks the contract as a requirement-to-evidence matrix:

| Behaviour | Evidence | State |
| --- | --- | --- |
| Zero rejected by validator | Focused unit test passes | `validated` |
| Zero rejected by submission path | No service-path check has run | `implemented-not-validated` |
| Positive value accepted | Regression test passes | `validated` |
| Error response preserved | Service test shows success instead of expected error | `failed` |
| Unrelated claim flow unchanged | Pre-existing failure in another test | `blocked` or baseline issue |

The task cannot be marked complete merely because two rows are green. Every
required row must be `validated`, `not-applicable` with a reason, or explicitly
accepted as `blocked`/`needs-decision` by a human.

### Behaviour evidence hierarchy

Different requirements need different kinds of proof. TailTrail should state the
strength and limit of the evidence it has.

| Evidence type | Best for | Limitation |
| --- | --- | --- |
| Focused unit test | Local rules, edge cases, error types | May miss caller integration and public behavior. |
| Service/integration test | Cross-module flow and error propagation | May still miss deployment/runtime configuration. |
| Approved fixture or contract test | Stable API, serialization, event, or data-shape behavior | Requires a trusted fixture/contract. |
| Existing regression suite | Preserving nearby known behavior | May not cover the new requirement. |
| Manual verification | Ambiguous UX or externally visible behavior | Human evidence should be recorded as manual, not inferred. |

Tests generated or changed by the agent are evidence, not automatic truth. The
test-chasing protections in the Requirement Completion Harness apply to every
behavior row.

### Behaviour drift output

```text
Behaviour drift: requirement is only partially fulfilled.

Validated:
- validate_claim_amount rejects zero
- positive amount remains accepted

Missing/failed:
- claim submission returns success after ClaimValidationError

Anchor rule:
- zero-dollar claims must be rejected through every approved submission path

Next correction:
Repair error propagation in the service path. Do not alter the positive-amount
path or weaken the zero-value assertion. Re-run the two focused tests.
```

Behaviour harnessing is harder than maintainability or architecture fitness:
clear requirements and trusted tests are essential. When the desired behavior is
ambiguous, TailTrail must surface a decision rather than fabricate a test or
choose the easiest implementation path.

### Full walkthrough: a multi-file logic change

This walkthrough illustrates the expected experience when an agent changes
existing logic, touches multiple files, and encounters several test failures.

**Developer task:**

> Reject zero-dollar claim amounts. Positive amounts must remain valid. Apply the
> rule through all claim submission paths and add focused validation.

#### Step 1: build and approve the anchor

Navigator identifies `validation.py`, `service.py`, focused validation tests,
and likely submission-path tests. The proposed `approved.md` states:

```text
Required behavior
- zero is rejected by shared validation
- positive values remain valid
- submission preserves the validation failure

Architecture
- service uses shared validation
- no controller-only special case

Evidence
- validation test: zero rejected
- validation test: positive accepted
- service-path test: rejection preserved
```

The developer approves it. The agent now has a concrete destination without
being forced into a particular implementation.

#### Step 2: agent makes an incomplete first change

The agent updates `validate_claim_amount` to reject zero and adds a direct unit
test. It does not change the service, which catches `ClaimValidationError` and
returns a successful result.

TailTrail writes `actual.md` and creates checkpoint one:

```text
Requirement coverage
- zero rejected by validator: validated
- positive value accepted: validated
- zero rejected through submission: failed

Architecture
- shared validation changed: preserved
- service error path: behavior drift

Scope
- no unexpected paths

Next correction
Preserve ClaimValidationError through src/claims_api/service.py. Do not alter
the public contract or unrelated callers.
```

The developer does not need to discover or restate the next issue.

#### Step 3: agent corrects the service but changes a test

The agent updates the service and changes an existing test assertion. TailTrail
does not assume that a changed test is legitimate. It classifies the test change:

| Question | Result |
| --- | --- |
| Does the changed assertion link to the approved requirement? | Yes: zero must be rejected. |
| Does production code now exhibit the approved behavior? | Yes: service returns the expected validation error. |
| Was an assertion removed, output broadened, or test skipped? | No. |
| Do focused validation and service tests pass? | Yes. |

The test update becomes evidence rather than test-chasing.

#### Step 4: completion and human review

The next checkpoint reports every required behavior as `validated`, the shared
architecture path as `preserved`, no scope expansion, and focused checks passed.
TailTrail Review then spends its inferential effort on the remaining questions:

- Did the implementation reuse existing validation and error conventions?
- Did it introduce unnecessary abstraction or duplicate logic?
- Did the diff fulfill the request without unrelated churn?
- Is there any unresolved business or public-contract decision for a human?

Only then does the change reach human review. The human sees the approved intent,
actual evidence, changed tests with rationale, and any unresolved risks instead
of a sequence of raw failures and agent retries.

## Requirement Completion Harness

Fast computational feedback is necessary, but it is not the most difficult
agent-coding problem. Modern coding agents usually resolve syntax, formatting,
and straightforward type errors quickly. The harder failure mode is incomplete
requirement fulfillment across a real change path:

- a new rule changes the primary implementation but an important caller still
  assumes the old behavior;
- a test fails because the implementation is wrong, or because an existing test
  encodes behavior that the new requirement intentionally replaces;
- a fix for one failing test creates a regression in another flow; or
- the agent makes tests green by weakening an assertion rather than correcting
  the behavior.

For this class of work, TailTrail should provide a **Requirement Completion
Harness**. It sits after an initial implementation and before human review. Its
job is to determine whether the requested behavior is complete across impacted
code and tests, then give the agent the smallest useful correction task.

```mermaid
flowchart TB
    A[Requirement and acceptance criteria] --> B[Initial agent change]
    B --> C[Impact-aware completion review]
    C --> D[Focused tests and diagnostics]
    D --> E{Completion gaps?}
    E -->|Yes| F[One bounded correction task]
    F --> B
    E -->|No| G[Requirement evidence report]
    G --> H[Human review of remaining judgment]
```

### The completion question

The completion harness does not ask only, "Are tests green?" It asks:

> For every requested outcome, what implementation path, caller behavior, test
> evidence, and unresolved decision show that this change is actually complete?

Every requirement should end in one of these explicit states:

| State | Meaning | Human action |
| --- | --- | --- |
| `validated` | Implementation and focused evidence support the requirement. | Review the result, not a missing proof. |
| `implemented-not-validated` | Code appears present, but no adequate focused evidence has run. | Run or approve the required check. |
| `failed` | A test, check, or direct observation contradicts the requirement. | Send one bounded correction task to the agent. |
| `needs-decision` | Requirement, expected behavior, or test expectation is ambiguous. | Make the decision; do not let the agent invent it. |
| `not-applicable` | Requirement does not apply to this path, with a recorded reason. | Confirm the reason during review. |
| `blocked` | A required environment, fixture, dependency, or permission prevents proof. | Resolve the blocker or accept explicit risk. |

Green tests are strong evidence, but they are not a complete requirement state
by themselves. A focused suite can be incomplete, an agent can update a test to
match incorrect logic, and some requirements depend on behavior in callers that
the selected test did not exercise.

### Requirement-to-evidence matrix

Before implementation, Navigator should transform the task into a small,
reviewable matrix. The matrix remains the completion harness's source of truth
after the agent edits code.

Example task:

> Reject zero-dollar claim amounts while keeping positive claim amounts valid.

| Requirement | Likely implementation path | Impacted caller or behavior | Required evidence | Completion state |
| --- | --- | --- | --- | --- |
| Zero amount is rejected | `validate_claim_amount` | `validate_claim` and claim submission | Zero-value test passes after the fix | Pending |
| Positive amount remains accepted | `validate_claim_amount` | Normal claim submission | Positive-value test passes | Pending |
| Error is preserved through the service | Validation/service path | Submission response | Focused service-path test or contract check | Pending |
| No unrelated behavior changes | Changed diff and existing suite | Nearby claims flows | Diff review and selected regression tests | Pending |

The matrix is deliberately small. It is not a speculative test plan for the
whole repository. Each row must tie directly to requested behavior, a meaningful
regression risk, or an explicit human decision.

### Impact-aware completion review

After the initial edit, the harness compares four local signals:

1. **Requirement matrix** - what had to become true.
2. **Actual diff** - which files, symbols, tests, and expectations changed.
3. **Impact map** - direct callers, validation paths, likely tests, and relevant
   contracts identified by Code Graph and exact source inspection.
4. **Focused evidence** - test, type, lint, build, structural, and review
   outcomes that actually ran.

This lets TailTrail ask useful completion questions:

| Observation | Completion interpretation | Next action |
| --- | --- | --- |
| Validation function changed but its main service caller was not inspected | Possible incomplete behavior path | Inspect the caller and run the focused service test. |
| A test fails after a rule change | Could be regression or obsolete expectation | Compare the assertion with the requirement before editing source or test. |
| Agent changed a test but not matching requirement evidence | Possible test-chasing | Require rationale and inspect whether production behavior is correct. |
| Tests pass but requested edge case is uncovered | `implemented-not-validated`, not complete | Add or select a focused edge-case test. |
| Several failures point to one shared helper | Root cause is probably shared | Repair the helper and rerun its direct callers/tests first. |
| Failure existed before the task and is unrelated to diff | Separate baseline issue | Record as pre-existing; do not absorb it without approval. |

### Bounded correction tasks

The harness should never give the agent an unstructured instruction such as
"Tests failed, fix everything." That invites broad edits, test-chasing, and
unnecessary token use.

Instead, it produces one bounded correction task at a time. A correction packet
contains the requirement, exact evidence, allowed scope, next action, and
focused validation command.

```text
Completion gap: service path still accepts a zero-dollar claim.

Requirement: zero-dollar amounts must be rejected while positive amounts remain valid.

Evidence:
- tests/test_claim_service.py:42 fails: expected ClaimValidationError
- src/claims_api/service.py:8 calls validate_claim but converts the error to success
- src/claims_api/validation.py already rejects amount <= 0

Allowed scope:
- src/claims_api/service.py
- tests/test_claim_service.py

Required next action:
Preserve the validation error in the service path. Do not change unrelated API
contracts or weaken the zero-value assertion.

Validation after correction:
python3 -m unittest tests.test_claim_service
python3 -m unittest tests.test_claim_validation
```

This packet gives the agent enough exact evidence to correct the next issue
without reloading unrelated repository history or guessing why the test failed.

### Classify failures before editing

When a logic change produces failing tests, TailTrail should classify the failure
before asking the agent to edit anything:

| Classification | What it means | Safe response |
| --- | --- | --- |
| `implementation-regression` | New code violates existing behavior that should remain true. | Fix production logic; preserve the existing test. |
| `required-expectation-change` | Test encodes behavior intentionally replaced by the new requirement. | Update the test with a requirement-linked explanation and cover the new behavior. |
| `incomplete-impact-change` | Direct change is correct, but a caller, adapter, serializer, config path, or related test was missed. | Fix the missing path and rerun the smallest related checks. |

If TailTrail cannot confidently classify a failure from requirement, source, and
test evidence, it must return `needs-decision`. This is safer than allowing the
agent to select the interpretation that makes the suite pass fastest.

### Test-chasing protection

Test changes deserve extra scrutiny during a correction loop because changing a
test can hide a defect. A test modification is allowed only when it is tied to an
explicit requirement change, a corrected invalid fixture, a documented
production contract, or newly required edge-case coverage.

For each changed test, the completion report should show:

| Test change | Requirement link | Production behavior checked | Review posture |
| --- | --- | --- | --- |
| Assertion changed from accept-zero to reject-zero | Zero amounts must be rejected | Validation and service response both reject zero | Review required |
| Added positive-amount regression case | Positive amounts remain valid | Validation and submission still accept positive amount | Focused evidence |

TailTrail should flag a test change as `needs-decision` when it only removes an
assertion, broadens accepted output, skips a failing case, or lacks a clear link
to the requested behavior.

### Stopping rules and human escalation

Completion loops must protect quality and developer time. Default stopping rules
should include:

- no more than two or three correction cycles for one requirement without a
  human review point;
- immediate escalation when a correction expands into a new feature, dependency,
  data migration, security boundary, public API change, or broad refactor;
- immediate escalation when test evidence and requirement text support competing
  interpretations;
- stop when a selected test/check times out, is unavailable, or has ambiguous
  output; report `blocked` rather than treating it as a pass; and
- stop when a failure is established as pre-existing and outside the approved
  task scope, unless the developer explicitly expands scope.

The human should receive a decision packet, not a raw pile of logs:

```text
Human decision needed: existing service test expects zero amounts to be accepted,
but the new requirement says they must be rejected.

Evidence:
- Product requirement: reject zero-dollar claims.
- Existing test: expects successful submission for zero.
- Current implementation: validation rejects zero; service behavior is undecided.

Decision options:
1. Treat the new requirement as authoritative and update the service contract/test.
2. Preserve service acceptance and narrow the requirement to direct validation only.
```

### Benefits and risks of review-phase completion harnessing

| Benefit | Why it matters |
| --- | --- |
| Less repeated prompting | Agent receives a precise next correction rather than repeated human instructions to rerun and fix tests. |
| Better multi-file completion | Code Graph and the matrix connect logic changes to callers, tests, and behavior paths. |
| More trustworthy green tests | Test changes are linked to requirements and inspected for test-chasing. |
| Lower human review toil | Review begins with completion evidence and unresolved decisions, not an unknown set of failures. |
| Better agent learning loop | Repeated gaps can become new guides, focused tests, or structural sensors. |

| Risk | Mitigation |
| --- | --- |
| Scope creep from continuously discovered related work | Classify findings as required, regression, optional hardening, or unrelated; only the first two stay in the loop by default. |
| Test-chasing | Require requirement-linked reasons for changed tests and inspect production behavior alongside assertions. |
| False completion from a green narrow suite | Use the requirement-to-evidence matrix and mark uncovered requirements `implemented-not-validated`. |
| Unbounded agent loops | Enforce correction-cycle limits and escalate to a concise human decision packet. |
| Wrong interpretation of an ambiguous requirement | Return `needs-decision`; do not let the agent choose the easiest interpretation. |
| Excess context and token use | Send only the requirement row, relevant diff, caller/test evidence, and next action in each correction packet. |

## Maintainability Harness

The **Maintainability Harness** is the first concrete TailTrail harness category.
It regulates whether an agent-generated change remains understandable,
consistent, safe to modify, and inexpensive to review after it lands.

It includes code standards and code quality, but it is broader than formatting or
linting. A formatter can identify whitespace drift and a linter can identify an
unused import. TailTrail should also ask whether a small bug fix became a broad
refactor, whether an existing helper was ignored, whether a new abstraction is
actually needed, and whether the tests still prove the requested behavior.

The maintainability question is:

> Will this change be easy for the next developer or agent to understand,
> validate, modify, and review without rediscovering its intent?

### What it regulates

| Area | What TailTrail should protect | Typical signals |
| --- | --- | --- |
| Readability | Clear names, focused functions, conventional error handling, direct control flow | Long or deeply nested functions, vague names, inconsistent error paths |
| Consistency | Reuse existing helpers, types, validation style, APIs, and local patterns | Duplicate helper, parallel implementation, incompatible naming or exception style |
| Complexity | Smallest maintainable solution; no speculative layers or configuration | New wrapper, abstraction, configuration flag, or broad rewrite for a small task |
| Test quality | Focused regression proof and meaningful assertions | Missing edge-case test, weakened assertion, skipped test, test changed only to turn green |
| Change hygiene | Scoped diff with no unrelated formatting churn or generated-file edits | Changed paths outside task scope, unrelated renames, large line count for a small fix |
| Dependency hygiene | Platform/native and existing capabilities before new packages | New dependency when an existing helper or standard-library path is sufficient |
| Documentation hygiene | Public feature changes update their command, registry, guide, and release notes | New command/script with no test, registry entry, or documentation |

### Three control levels

TailTrail should use three complementary levels instead of pretending every
maintainability problem is computable.

| Level | When it runs | Controls | Purpose |
| --- | --- | --- | --- |
| Computational baseline | Every relevant change | Focused tests, formatter/linter/type checks, diff scope, changed-test detection, simple complexity/duplicate/forbidden-import checks | Catch fast, deterministic mechanical and structural problems. |
| Local rule checks | When policy or repository conventions define a rule | Protected paths, dependency gate, module boundaries, no-unrelated-file rule, required docs/tests for a feature change | Enforce project-specific maintainability safeguards consistently. |
| Inferential maintainability review | After fast checks pass or on demand | Reuse-first analysis, abstraction necessity, requirement-linked test review, complexity and overengineering review | Exercise semantic judgment that tools cannot decide reliably. |

This ordering matters. Inferential review should not spend model reasoning on
formatting, obvious diagnostics, or checks the CPU can run in seconds. It should
focus on the questions with real judgment: whether the change is overbuilt,
whether a test is meaningful, and whether the chosen implementation matches the
repository's existing design.

### Example: more than a lint rule

Task:

> Reject zero-dollar claim amounts and add focused validation.

An agent changes `validation.py`, adds a new `ClaimAmountValidator` class,
duplicates existing exception handling, modifies three unrelated modules, and
updates a test assertion to pass.

The computational controls may report a green test suite. The Maintainability
Harness should still surface this review finding:

```text
Maintainability gap: the task is a targeted validation change, but the diff adds
a single-use validator abstraction and duplicates the existing validation error
path. Reuse validate_claim_amount and keep the change in the established
validation/service flow. The changed test needs a requirement-linked explanation
before it can be treated as evidence.
```

That is TailTrail's differentiated value: it turns generic code-quality signals
into a requirement- and repository-aware correction task.

### Maintainability correction packet

When the harness finds a maintainability issue, it should send a focused repair
task rather than a vague request to "clean up the code."

```text
Maintainability gap: duplicate validation helper introduced.

Evidence:
- src/claims_api/validation.py already exposes validate_claim_amount.
- src/claims_api/amount_validator.py duplicates the positive-amount rule.
- The requested change concerns zero-value validation only.

Required correction:
Reuse validate_claim_amount and remove the duplicate helper if it has no other
approved use. Keep existing error types and public behavior unchanged.

Focused validation:
python3 -m unittest tests.test_claim_validation
```

### Guardrails against false positives

Maintainability controls can become a noisy style gate if they are too broad.
TailTrail should report only high-value, evidence-backed findings:

- do not flag personal style preferences as defects;
- do not demand shorter code if it would weaken validation, readability, or a
  necessary business rule;
- do not require reuse when the existing helper is unsuitable for the new
  behavior; explain the mismatch instead;
- separate `required` findings from `optional hardening` and `style note` items;
- preserve exact diff, policy, test, and source evidence behind each finding;
- allow a project to opt out of a low-value rule without disabling unrelated
  safeguards; and
- measure false-positive rate and recurring review findings before promoting a
  rule to an always-on gate.

### Initial implementation focus

The first Maintainability Harness release should compose existing TailTrail
features instead of building a new monolithic reviewer:

1. Use Navigator, Code Graph, policy, and changed-path scope as feedforward
   guides.
2. Run existing focused tests and repository-configured lint/type/build commands
   as computational sensors.
3. Add deterministic diff checks for unexpected paths, changed tests, dependency
   manifests, and generated/protected files.
4. Run TailTrail Review with the task, compact diff summary, impacted callers,
   test changes, and computational findings.
5. Return only the highest-value correction task, then rerun focused checks.
6. Record repeated approved findings as candidates for a future policy rule,
   structural check, or harness template.

Success for this harness is not a larger number of comments. It is fewer
avoidable human review comments, smaller and more consistent agent diffs, and
clearer evidence that the requested change is maintainable.

## Planned implementation

### Phase 1 — Control contract and local fast checks

Define a machine-readable control contract describing trigger, command, timeout,
scope, result parser, severity, and whether a control is mandatory, advisory, or
approval-gated. Reuse repository-native tools; do not add dependencies merely to
fill out the framework.

Create the Change Intent Anchor in this phase. `harness plan` should propose the
current state, desired behavior, architecture expectations, impact boundary,
invariants, known unknowns, evidence plan, and approval fingerprint. It remains
read-only until the developer approves the desired state.

```bash
python3 scripts/tailtrail.py harness plan "fix validation bug" --changed src/service/foo.py
python3 scripts/tailtrail.py harness check --changed src/service/foo.py
python3 scripts/tailtrail.py harness feedback --run <run-id>
```

### Phase 2 — Structured feedback and bounded correction

Create an LLM-ready feedback packet from exact local findings. Support a bounded
agent correction cycle only through an explicitly approved and capability-aware
adapter.

Add the Requirement Completion Harness in this phase: build the
requirement-to-evidence matrix, compare it with the observed diff, caller/test
impact map, and actual check results, then issue one classified correction task
per gap. Require explicit treatment of changed tests so a green suite cannot be
created by weakening assertions without a requirement-linked reason.

Persist a drift checkpoint after each correction cycle. Compare actual code,
tests, architecture path, scope, and evidence to the approved anchor. Invalidate
the anchor and require re-approval when a material requirement, policy, path,
public contract, dependency, data-model, or security-boundary change appears.

```bash
python3 scripts/tailtrail.py harness steer <run-id> --adapter codex --max-cycles 2 --approved
```

### Phase 3 — Maintainability and architecture sensors

Build on Code Graph, guardrails, and project policy to add configurable checks
for prohibited imports, dependency direction, module boundaries, protected paths,
and repeated structural failure patterns. Add behavior-contract checks that map
each desired outcome to focused unit, service/integration, fixture/contract, or
manual evidence; distinguish a passing narrow test from full requirement proof.

### Phase 4 — Steering-loop improvement

When a finding recurs, TailTrail proposes a better guide, focused test,
structural rule, or result parser. Human approval is required before it changes
repository policy or control configuration.

### Proposed command contract

These commands are design targets, not currently implemented commands. The first
release should remain local, deterministic where possible, and explicit about
what has and has not run.

```bash
# Propose current state, desired state, scope, scenarios, and evidence plan.
tailtrail harness plan "reject zero-dollar claims" --changed src/claims_api/validation.py

# Display the generated anchor for human review.
tailtrail harness anchor show <run-id>

# Record explicit approval of the desired state.
tailtrail harness anchor approve <run-id>

# Run only selected safe computational controls and write actual.md.
tailtrail harness check <run-id>

# Compare approved.md with actual.md and render a drift checkpoint.
tailtrail harness checkpoint <run-id>

# Produce exactly one bounded next task when a completion gap exists.
tailtrail harness feedback <run-id>

# Later, with explicit approval and a supported adapter, send that bounded task
# to an agent for no more than the configured number of correction cycles.
tailtrail harness steer <run-id> --adapter codex --max-cycles 2 --approved

# Draft but never automatically promote a changed expected behavior.
tailtrail harness scenario propose <run-id> --scenario zero-dollar-submission
```

### Minimal local data contract

The first implementation should use simple versioned JSON for machine state and
Markdown for human review. It should avoid a database, daemon, cloud service, or
new dependency.

| Artifact | Writer | Contents | Mutability |
| --- | --- | --- | --- |
| `approved.md` | TailTrail drafts; human approves | Goal, desired behavior, scenarios, architecture expectations, scope, invariants, evidence plan, known unknowns | Immutable after approval; human re-approval required for material change. |
| `change-intent-anchor.json` | TailTrail | Same anchor in normalized, fingerprinted machine form | Rewritten only when a new/re-approved anchor is created. |
| `actual.md` | TailTrail after each check | Observed behavior, changed paths, controls run, results, and gaps | Regenerated each cycle. |
| `checkpoint-<n>.json` | TailTrail | Requirement/architecture/behavior/scope/evidence comparison and correction state | Append-only per cycle. |
| `comparison-report.md` | TailTrail | Human-readable diff between approved and actual state | Regenerated each cycle. |
| `proposal.md` | Agent/TailTrail | Proposed changed expected behavior or scope expansion | Never becomes approved state without human action. |

### Compatibility with existing TailTrail surfaces

The harness should compose existing surfaces rather than reimplement them:

| Existing surface | Harness use |
| --- | --- |
| Navigator / `start` | Produces initial goal decomposition, impact boundary, risk posture, and suggested validation. |
| AIDLC | Adds deeper requirement gathering and acceptance criteria only for broad, risky, or ambiguous tasks. |
| Code Graph | Supplies likely callers, shared helpers, impacted symbols, and candidate tests for anchor/checkpoint comparison. |
| Test Precision | Produces focused test matrix and commands for behavioral evidence. |
| Guardrails / policy | Defines allowed controls, protected paths, dependency rules, and escalation conditions. |
| Review | Performs requirement, maintainability, and semantic judgment after computational findings are available. |
| Evaluation Harness | Provides deterministic fixtures and later measures whether harness controls improve outcomes. |
| Learning / Meta-Harness | Proposes better guides/sensors only from approved, privacy-safe recurring evidence. |

## Expected files

| File | Planned responsibility |
| --- | --- |
| `scripts/harness-controls.py` | Select, run, time-bound, and normalize computational controls. |
| `scripts/harness-feedback.py` | Build compact correction packets from exact local evidence. |
| `scripts/change-intent-anchor.py` | Propose, validate, fingerprint, approve, invalidate, and compare the local current/desired-state contract. |
| `scripts/harness-checkpoint.py` | Persist and render requirement, architecture, scope, and evidence drift after each correction cycle. |
| `scripts/completion-review.py` | Compare requirements, diff, impact map, tests, and review evidence; classify gaps and emit bounded correction tasks. |
| `scripts/tailtrail.py` | Provide `harness plan`, `check`, `feedback`, and later `steer`. |
| `scripts/navigator_core.py`, `scripts/task-start.py` | Supply scope, policy, tests, graph, and validation recommendations. |
| `scripts/test-precision.py`, `scripts/ci-summary.py`, `scripts/quality-run.py` | Reused focused-test and local quality runners. |
| `scripts/guardrail-check.py`, `scripts/code-graph-mapper.py`, `scripts/review-run.py` | Structural sensors, policy evidence, and inferential review. |
| `schemas/harness-control.schema.json`, `schemas/harness-result.schema.json` | Versioned control and result contracts. |
| `schemas/change-intent-anchor.schema.json`, `schemas/harness-checkpoint.schema.json` | Versioned approved target-state, fingerprint, invalidation, and checkpoint contracts. |
| `schemas/requirement-evidence.schema.json` | Versioned requirement matrix, completion state, test-change rationale, and escalation contract. |
| `templates/harness-feedback.md`, `templates/harness-template.example.yml` | Feedback output and project-local template example. |
| `templates/change-intent-anchor.md`, `templates/harness-checkpoint.md` | Human-readable approved intent and per-cycle drift report. |
| `templates/completion-review.md` | Human- and agent-readable requirement completion report. |
| `tests/test_change_intent_anchor.py`, `tests/test_harness_checkpoint.py`, `tests/test_harness_controls.py`, `tests/test_harness_feedback.py`, `tests/test_completion_review.py` | Anchor approval/invalidation, checkpoint comparison, control selection, parsing, failure classification, test-chasing, and escalation tests. |

## Boundaries

- Prefer computational controls; inferential controls never replace source,
  tests, linters, type checks, or other deterministic evidence.
- Run only safe local commands allowed by project policy. Networked scanners,
  package installation, and destructive commands remain explicit approval paths.
- Do not create a background agent, daemon, hidden retry loop, or hidden
  telemetry service.
- Do not store raw prompts, source, secrets, PII, PHI, customer data, or
  unredacted logs in learning or outcome records.
- Do not claim defect prevention, review-time reduction, or token savings without
  measured evidence from real usage.

## Success criteria

- A task has visible selected guides and computational sensors before editing.
- Fast local checks produce precise `pass`, `fail`, `skipped`, or `blocked`
  results.
- Failed controls give an agent enough exact evidence to correct the issue
  without rereading unrelated repository content.
- Each requested outcome is tracked as `validated`, `failed`,
  `implemented-not-validated`, `needs-decision`, `not-applicable`, or `blocked`.
- Every correction checkpoint compares the actual change to a user-approved
  Change Intent Anchor and names requirement, architecture, behavior, scope, or
  evidence drift rather than emitting an opaque score.
- Material scope, policy, public-contract, dependency, data-model, or security
  changes invalidate the anchor and require re-approval.
- A changed test has a requirement-linked rationale and production-behavior
  evidence, or it is escalated for human review.
- Repeated failures escalate instead of producing unbounded correction loops.
- Human reviewers receive changes that have already passed relevant deterministic
  controls, plus a concise record of what was checked.
- Harness improvements are proposed from recurring evidence and remain
  human-approved, testable, and reversible.
