# TailTrail Start Plan - Full Review Record

**Presentation version:** `5`

## Planning Lock

- **Run ID:** `start-20261103074542-c5f97c`
- **Status:** `approved`
- **Goal:** Complete Phase 3 Proof Bindings and Readiness from TAILTRAIL-HOST-TAILTRAIL-EVIDENCE-VALIDATION-DESIGN.md as one approval plan. TailTrail must select every mandatory field from its owned profile registry, validate Navigator-accepted fresh answers and complete requirement-specific proof bindings, and mint a target-bound pre-Start planning-readiness receipt without requiring an approved anchor; intake-recorded receipts remain non-authorizing and existing post-anchor packet views remain compatible. For Host Question Flow Build requests identified by a host-contract transport or planning-readiness receipt input, public CLI Start must require a fresh matching planning-readiness receipt before Planning Lock and reject raw host contracts, intake-recorded receipts, stale or replayed evidence, changed-target evidence, and mismatched receipts with actionable guidance; ordinary Start routes outside Host Question Flow remain compatible. MCP tailtrail_start must expose the planning-readiness receipt and forward it unchanged to the public CLI validator while preserving existing callers that do not use Host Question Flow. Prove the combined behavior with python3 -m unittest tests.test_intake_pipeline tests.test_public_route_gate tests.test_mcp_server -v.
- **Request mode:** `implementation`
- **Managed writes allowed:** `true`
- **Execution status:** planning only; no source change, proof command, scanner, or Git operation has run.
- **Plan revision:** active `2`; pending `none`.

## Bound Planning Inputs

| ID | Role | Path or reference | Access | Status | Integrity |
|---|---|---|---|---|---|
| `IN-02` | requirement-artifact | `/Users/vsingha7/Desktop/tailr/TAILTRAIL-HOST-TAILTRAIL-EVIDENCE-VALIDATION-DESIGN.md` | read-only | inspected | `2cdec26124ac3acbf3ad4c8646e8f9608e7bf9d963fb9225623b12e5aec027c6` |
- These inputs remain read-only context and never grant editable implementation scope.

## Command Reference Registry

| ID | Kind | Command |
|---|---|---|
| `cmd-0772cb` | proof | `python3 -m unittest tests.test_intake_pipeline -v` |
| `cmd-5886f1` | proof | `python3 -m unittest tests.test_mcp_server -v` |
| `cmd-c0e115` | proof | `python3 -m unittest tests.test_public_route_gate -v` |

## Validation Requirements And Focused Validation Matrix

### REQ-01

**Description:** TailTrail must select every mandatory field from its owned profile registry, validate Navigator-accepted fresh answers and complete requirement-specific proof bindings, and mint a target-bound pre-Start planning-readiness receipt without requiring an approved anchor; intake-recorded receipts remain non-authorizing and existing post-anchor packet views remain compatible.

- **Requirement type:** `change`
- **Validation state:** `required`
- **Editable owner(s):** `scripts/intake_pipeline.py`
- **Read-only input(s):** `TAILTRAIL-HOST-TAILTRAIL-EVIDENCE-VALIDATION-DESIGN.md`, `scripts/adoption-validation.py`, `scripts/advanced-runtime.py`, `scripts/aidlc-official-bridge.py`, `scripts/aidlc-official-detect.py`, `scripts/aidlc-official-host.py`, `scripts/closure-contract.py`, `scripts/context-receipt.py`, `scripts/context_receipt.py`, `scripts/debug-host-diagnosis.py`, `scripts/host-adapter-conformance.py`, `scripts/host-decision.py`, `scripts/host-interpretation-builder.py`, `scripts/host-reply-validate.py`, `scripts/host-runtime-conformance.py`, `scripts/host-workspace-adapter.py`, `scripts/host_contract.py`, `scripts/install-copilot.py`, `scripts/learning-refresh.py`, `scripts/learning-use-receipt.py`, `scripts/learning-v3.py`, `scripts/navigator-installed-release-proof.py`, `scripts/new_file_due_diligence.py`, `scripts/package-release-proof.py`, `scripts/planning_lock.py`, `scripts/question-orchestrator.py`, `scripts/requirement_intake.py`, `scripts/run-ledger.py`, `scripts/workflow_runtime/start_integration.py`
- **Proof path(s):** `tests/test_intake_pipeline.py`, `tests/test_mcp_server.py`, `tests/test_public_route_gate.py`
- **Success criteria:** The stated requirement is observably satisfied on its approved path.
- **Preservation criteria:** Do not change behavior outside this approved requirement boundary.
- **Requirement behaviour scenarios:**
  - `BHV-PHASE3-READINESS`: Submit accepted fresh profile answers with complete requirement-specific proof bindings, then retry and submit stale, unrelated, or changed-target evidence. → The valid input mints one target-bound planning-readiness receipt and retries idempotently; invalid inputs mint no authorizing receipt and fail closed.

| Tier | Command ID | Command | Candidate | State |
|---|---|---|---|---|
| behaviour | `cmd-0772cb` | `python3 -m unittest tests.test_intake_pipeline -v` | `tests/test_intake_pipeline.py` | resolved |
| contract | `cmd-0772cb` | `python3 -m unittest tests.test_intake_pipeline -v` | `tests/test_intake_pipeline.py` | resolved |
| unit | `cmd-0772cb` | `python3 -m unittest tests.test_intake_pipeline -v` | `tests/test_intake_pipeline.py` | resolved |

### REQ-02

**Description:** For Host Question Flow Build requests identified by a host-contract transport or planning-readiness receipt input, public CLI Start must require a fresh matching planning-readiness receipt before Planning Lock and reject raw host contracts, intake-recorded receipts, stale or replayed evidence, changed-target evidence, and mismatched receipts with actionable guidance; ordinary Start routes outside Host Question Flow remain compatible.

- **Requirement type:** `change`
- **Validation state:** `required`
- **Editable owner(s):** `scripts/task-start.py`
- **Read-only input(s):** `TAILTRAIL-HOST-TAILTRAIL-EVIDENCE-VALIDATION-DESIGN.md`, `scripts/adoption-validation.py`, `scripts/advanced-runtime.py`, `scripts/aidlc-official-bridge.py`, `scripts/aidlc-official-detect.py`, `scripts/aidlc-official-host.py`, `scripts/closure-contract.py`, `scripts/context-receipt.py`, `scripts/context_receipt.py`, `scripts/debug-host-diagnosis.py`, `scripts/host-adapter-conformance.py`, `scripts/host-decision.py`, `scripts/host-interpretation-builder.py`, `scripts/host-reply-validate.py`, `scripts/host-runtime-conformance.py`, `scripts/host-workspace-adapter.py`, `scripts/host_contract.py`, `scripts/install-copilot.py`, `scripts/learning-refresh.py`, `scripts/learning-use-receipt.py`, `scripts/learning-v3.py`, `scripts/navigator-installed-release-proof.py`, `scripts/new_file_due_diligence.py`, `scripts/package-release-proof.py`, `scripts/planning_lock.py`, `scripts/question-orchestrator.py`, `scripts/requirement_intake.py`, `scripts/run-ledger.py`, `scripts/workflow_runtime/start_integration.py`
- **Proof path(s):** `tests/test_intake_pipeline.py`, `tests/test_mcp_server.py`, `tests/test_public_route_gate.py`
- **Success criteria:** The stated requirement is observably satisfied on its approved path.
- **Preservation criteria:** Do not change behavior outside this approved requirement boundary.
- **Requirement behaviour scenarios:**
  - `BHV-02`: Compare the affected API responses before and after the approved change. → Existing fields, meanings, and status behavior remain compatible.
  - `BHV-PHASE3-CLI-GATE`: Invoke public CLI Start for Host Question Flow with a valid planning-readiness receipt and with raw, intake-only, stale, replayed, changed-target, or mismatched inputs. → Only the valid matching receipt permits Planning Lock creation; every invalid input creates no lock and returns precise corrective guidance, while ordinary Start remains compatible.

| Tier | Command ID | Command | Candidate | State |
|---|---|---|---|---|
| behaviour | `cmd-c0e115` | `python3 -m unittest tests.test_public_route_gate -v` | `tests/test_public_route_gate.py` | resolved |
| contract | `cmd-c0e115` | `python3 -m unittest tests.test_public_route_gate -v` | `tests/test_public_route_gate.py` | resolved |
| integration | `cmd-c0e115` | `python3 -m unittest tests.test_public_route_gate -v` | `tests/test_public_route_gate.py` | resolved |

### REQ-03

**Description:** MCP tailtrail_start must expose the planning-readiness receipt and forward it unchanged to the public CLI validator while preserving existing callers that do not use Host Question Flow.

- **Requirement type:** `change`
- **Validation state:** `required`
- **Editable owner(s):** `scripts/mcp-server.py`
- **Read-only input(s):** `TAILTRAIL-HOST-TAILTRAIL-EVIDENCE-VALIDATION-DESIGN.md`, `scripts/adoption-validation.py`, `scripts/advanced-runtime.py`, `scripts/aidlc-official-bridge.py`, `scripts/aidlc-official-detect.py`, `scripts/aidlc-official-host.py`, `scripts/closure-contract.py`, `scripts/context-receipt.py`, `scripts/context_receipt.py`, `scripts/debug-host-diagnosis.py`, `scripts/host-adapter-conformance.py`, `scripts/host-decision.py`, `scripts/host-interpretation-builder.py`, `scripts/host-reply-validate.py`, `scripts/host-runtime-conformance.py`, `scripts/host-workspace-adapter.py`, `scripts/host_contract.py`, `scripts/install-copilot.py`, `scripts/learning-refresh.py`, `scripts/learning-use-receipt.py`, `scripts/learning-v3.py`, `scripts/navigator-installed-release-proof.py`, `scripts/new_file_due_diligence.py`, `scripts/package-release-proof.py`, `scripts/planning_lock.py`, `scripts/question-orchestrator.py`, `scripts/requirement_intake.py`, `scripts/run-ledger.py`, `scripts/workflow_runtime/start_integration.py`
- **Proof path(s):** `tests/test_intake_pipeline.py`, `tests/test_mcp_server.py`, `tests/test_public_route_gate.py`
- **Success criteria:** The stated requirement is observably satisfied on its approved path.
- **Preservation criteria:** Do not change behavior outside this approved requirement boundary.
- **Requirement behaviour scenarios:**
  - `BHV-02`: Compare the affected API responses before and after the approved change. → Existing fields, meanings, and status behavior remain compatible.
  - `BHV-PHASE3-MCP-ROUTE`: Invoke MCP tailtrail_start with a planning-readiness receipt and through an existing non-Host-Question-Flow caller. → The receipt reaches the CLI validator unchanged and existing callers that omit the new input retain their prior behavior.

| Tier | Command ID | Command | Candidate | State |
|---|---|---|---|---|
| behaviour | `cmd-5886f1` | `python3 -m unittest tests.test_mcp_server -v` | `tests/test_mcp_server.py` | resolved |
| contract | `cmd-5886f1` | `python3 -m unittest tests.test_mcp_server -v` | `tests/test_mcp_server.py` | resolved |
| integration | `cmd-5886f1` | `python3 -m unittest tests.test_mcp_server -v` | `tests/test_mcp_server.py` | resolved |
| unit | `cmd-5886f1` | `python3 -m unittest tests.test_mcp_server -v` | `tests/test_mcp_server.py` | resolved |

## Plan

1. **REQ-01:** Implement TailTrail must select every mandatory field from its owned profile registry, validate Navigator-accepted fresh answers and complete requirement-specific proof bindings, and mint a target-bound pre-Start planning-readiness receipt without requiring an approved anchor; intake-recorded receipts remain non-authorizing and existing post-anchor packet views remain compatible. in `scripts/intake_pipeline.py`; verify with `cmd-0772cb`, `cmd-0772cb`, `cmd-0772cb`; inspect `TAILTRAIL-HOST-TAILTRAIL-EVIDENCE-VALIDATION-DESIGN.md`, `scripts/adoption-validation.py`, `scripts/advanced-runtime.py`, `scripts/aidlc-official-bridge.py`, `scripts/aidlc-official-detect.py`, `scripts/aidlc-official-host.py`, `scripts/closure-contract.py`, `scripts/context-receipt.py`, `scripts/context_receipt.py`, `scripts/debug-host-diagnosis.py`, `scripts/host-adapter-conformance.py`, `scripts/host-decision.py`, `scripts/host-interpretation-builder.py`, `scripts/host-reply-validate.py`, `scripts/host-runtime-conformance.py`, `scripts/host-workspace-adapter.py`, `scripts/host_contract.py`, `scripts/install-copilot.py`, `scripts/learning-refresh.py`, `scripts/learning-use-receipt.py`, `scripts/learning-v3.py`, `scripts/navigator-installed-release-proof.py`, `scripts/new_file_due_diligence.py`, `scripts/package-release-proof.py`, `scripts/planning_lock.py`, `scripts/question-orchestrator.py`, `scripts/requirement_intake.py`, `scripts/run-ledger.py`, `scripts/workflow_runtime/start_integration.py`; prove against `tests/test_intake_pipeline.py`, `tests/test_mcp_server.py`, `tests/test_public_route_gate.py`.
2. **REQ-02:** Implement For Host Question Flow Build requests identified by a host-contract transport or planning-readiness receipt input, public CLI Start must require a fresh matching planning-readiness receipt before Planning Lock and reject raw host contracts, intake-recorded receipts, stale or replayed evidence, changed-target evidence, and mismatched receipts with actionable guidance; ordinary Start routes outside Host Question Flow remain compatible. in `scripts/task-start.py`; verify with `cmd-c0e115`, `cmd-c0e115`, `cmd-c0e115`; inspect `TAILTRAIL-HOST-TAILTRAIL-EVIDENCE-VALIDATION-DESIGN.md`, `scripts/adoption-validation.py`, `scripts/advanced-runtime.py`, `scripts/aidlc-official-bridge.py`, `scripts/aidlc-official-detect.py`, `scripts/aidlc-official-host.py`, `scripts/closure-contract.py`, `scripts/context-receipt.py`, `scripts/context_receipt.py`, `scripts/debug-host-diagnosis.py`, `scripts/host-adapter-conformance.py`, `scripts/host-decision.py`, `scripts/host-interpretation-builder.py`, `scripts/host-reply-validate.py`, `scripts/host-runtime-conformance.py`, `scripts/host-workspace-adapter.py`, `scripts/host_contract.py`, `scripts/install-copilot.py`, `scripts/learning-refresh.py`, `scripts/learning-use-receipt.py`, `scripts/learning-v3.py`, `scripts/navigator-installed-release-proof.py`, `scripts/new_file_due_diligence.py`, `scripts/package-release-proof.py`, `scripts/planning_lock.py`, `scripts/question-orchestrator.py`, `scripts/requirement_intake.py`, `scripts/run-ledger.py`, `scripts/workflow_runtime/start_integration.py`; prove against `tests/test_intake_pipeline.py`, `tests/test_mcp_server.py`, `tests/test_public_route_gate.py`.
3. **REQ-03:** Implement MCP tailtrail_start must expose the planning-readiness receipt and forward it unchanged to the public CLI validator while preserving existing callers that do not use Host Question Flow. in `scripts/mcp-server.py`; verify with `cmd-5886f1`, `cmd-5886f1`, `cmd-5886f1`, `cmd-5886f1`; inspect `TAILTRAIL-HOST-TAILTRAIL-EVIDENCE-VALIDATION-DESIGN.md`, `scripts/adoption-validation.py`, `scripts/advanced-runtime.py`, `scripts/aidlc-official-bridge.py`, `scripts/aidlc-official-detect.py`, `scripts/aidlc-official-host.py`, `scripts/closure-contract.py`, `scripts/context-receipt.py`, `scripts/context_receipt.py`, `scripts/debug-host-diagnosis.py`, `scripts/host-adapter-conformance.py`, `scripts/host-decision.py`, `scripts/host-interpretation-builder.py`, `scripts/host-reply-validate.py`, `scripts/host-runtime-conformance.py`, `scripts/host-workspace-adapter.py`, `scripts/host_contract.py`, `scripts/install-copilot.py`, `scripts/learning-refresh.py`, `scripts/learning-use-receipt.py`, `scripts/learning-v3.py`, `scripts/navigator-installed-release-proof.py`, `scripts/new_file_due_diligence.py`, `scripts/package-release-proof.py`, `scripts/planning_lock.py`, `scripts/question-orchestrator.py`, `scripts/requirement_intake.py`, `scripts/run-ledger.py`, `scripts/workflow_runtime/start_integration.py`; prove against `tests/test_intake_pipeline.py`, `tests/test_mcp_server.py`, `tests/test_public_route_gate.py`.
## Selected TailTrail Features

| Feature | When used | Why it is selected |
|---|---|---|
| Navigator | planning | established the evidence-bound scope and approval boundary |
| Token Autopilot | as required by the plan | selected for this task |
| Bootstrap Snapshot | as required by the plan | selected for this task |
| Code Review Graph Lite | as required by the plan | selected for this task |
| Code Graph Mapper | as required by the plan | selected for this task |
| Learning Capture Trigger | as required by the plan | selected for this task |
| Review Lens | as required by the plan | selected for this task |
| Focused QA Lens | as required by the plan | selected for this task |
| Test Precision Planner | as required by the plan | selected for this task |
| Handoff | as required by the plan | selected for this task |
| Project Learnings | as required by the plan | selected for this task |
| Learning Refresh Awareness | as required by the plan | selected for this task |

### Required before closure

- **Focused testing and validation:** prove the changed behavior, required preservation cases, and regression boundary with factual computational evidence
- **Canonical completion and closure:** prevent completion while required evidence is missing, unavailable, or failing

## Architecture Analysis

- **Status:** `planning-hypothesis`.
- **Evidence boundary:** Derived from explicit user wording and repository path inventory only. Source, caller relationships, and edit necessity are not confirmed until after approval.

| Requirement | Invariant | Planned proof |
|---|---|---|
| REQ-01 | Every material service and API caller must be assessed before the implementation boundary is finalized. | Requirement-linked Code Graph receipt plus changed-scope reconciliation. |
| REQ-01 | Behaviour outside the approved change boundary remains compatible. | Existing preservation-path evidence plus focused regression proof. |

### Scoped evidence

| Path | Role | Planned use | Confidence |
|---|---|---|---|
| `scripts/adoption-validation.py` | validation boundary | Primary implementation candidate, subject to post-approval source and caller confirmation. | repository-inventory hypothesis |
| `scripts/advanced-runtime.py` | implementation candidate | Primary implementation candidate, subject to post-approval source and caller confirmation. | repository-inventory hypothesis |
| `scripts/aidlc-official-bridge.py` | implementation candidate | Primary implementation candidate, subject to post-approval source and caller confirmation. | repository-inventory hypothesis |
| `scripts/aidlc-official-detect.py` | implementation candidate | Primary implementation candidate, subject to post-approval source and caller confirmation. | repository-inventory hypothesis |
| `scripts/aidlc-official-host.py` | implementation candidate | Primary implementation candidate, subject to post-approval source and caller confirmation. | repository-inventory hypothesis |
| `scripts/closure-contract.py` | implementation candidate | Primary implementation candidate, subject to post-approval source and caller confirmation. | repository-inventory hypothesis |
| `scripts/context-receipt.py` | implementation candidate | Primary implementation candidate, subject to post-approval source and caller confirmation. | repository-inventory hypothesis |
| `scripts/context_receipt.py` | implementation candidate | Primary implementation candidate, subject to post-approval source and caller confirmation. | repository-inventory hypothesis |
| `scripts/debug-host-diagnosis.py` | implementation candidate | Primary implementation candidate, subject to post-approval source and caller confirmation. | repository-inventory hypothesis |
| `scripts/host-adapter-conformance.py` | domain/integration boundary | Primary implementation candidate, subject to post-approval source and caller confirmation. | repository-inventory hypothesis |
| `scripts/host-decision.py` | implementation candidate | Primary implementation candidate, subject to post-approval source and caller confirmation. | repository-inventory hypothesis |
| `scripts/host-interpretation-builder.py` | implementation candidate | Primary implementation candidate, subject to post-approval source and caller confirmation. | repository-inventory hypothesis |
| `scripts/host-reply-validate.py` | implementation candidate | Primary implementation candidate, subject to post-approval source and caller confirmation. | repository-inventory hypothesis |
| `scripts/host-runtime-conformance.py` | implementation candidate | Primary implementation candidate, subject to post-approval source and caller confirmation. | repository-inventory hypothesis |
| `scripts/host-workspace-adapter.py` | domain/integration boundary | Primary implementation candidate, subject to post-approval source and caller confirmation. | repository-inventory hypothesis |
| `scripts/host_contract.py` | implementation candidate | Primary implementation candidate, subject to post-approval source and caller confirmation. | repository-inventory hypothesis |
| `scripts/install-copilot.py` | implementation candidate | Inspect after approval; edit only if the confirmed architecture contract requires it. | repository-inventory hypothesis |
| `scripts/intake_pipeline.py` | implementation candidate | Primary implementation candidate, subject to post-approval source and caller confirmation. | repository-inventory hypothesis |
| `scripts/learning-refresh.py` | implementation candidate | Primary implementation candidate, subject to post-approval source and caller confirmation. | repository-inventory hypothesis |
| `scripts/learning-use-receipt.py` | implementation candidate | Primary implementation candidate, subject to post-approval source and caller confirmation. | repository-inventory hypothesis |
| `scripts/learning-v3.py` | implementation candidate | Primary implementation candidate, subject to post-approval source and caller confirmation. | repository-inventory hypothesis |
| `scripts/mcp-server.py` | implementation candidate | Primary implementation candidate, subject to post-approval source and caller confirmation. | repository-inventory hypothesis |
| `scripts/navigator-installed-release-proof.py` | implementation candidate | Primary implementation candidate, subject to post-approval source and caller confirmation. | repository-inventory hypothesis |
| `scripts/new_file_due_diligence.py` | implementation candidate | Inspect after approval; edit only if the confirmed architecture contract requires it. | repository-inventory hypothesis |
| `scripts/package-release-proof.py` | implementation candidate | Primary implementation candidate, subject to post-approval source and caller confirmation. | repository-inventory hypothesis |
| `scripts/planning_lock.py` | implementation candidate | Primary implementation candidate, subject to post-approval source and caller confirmation. | repository-inventory hypothesis |
| `scripts/question-orchestrator.py` | orchestration boundary | Primary implementation candidate, subject to post-approval source and caller confirmation. | repository-inventory hypothesis |
| `scripts/run-ledger.py` | implementation candidate | Primary implementation candidate, subject to post-approval source and caller confirmation. | repository-inventory hypothesis |
| `scripts/task-start.py` | implementation candidate | Primary implementation candidate, subject to post-approval source and caller confirmation. | repository-inventory hypothesis |
| `scripts/workflow_runtime/start_integration.py` | implementation candidate | Inspect after approval; edit only if the confirmed architecture contract requires it. | repository-inventory hypothesis |
| `tests/test_focused_validation_contracts.py` | test evidence | Primary implementation candidate, subject to post-approval source and caller confirmation. | repository-inventory hypothesis |
| `tests/test_host_question_flow_event_schema.py` | test evidence | Primary implementation candidate, subject to post-approval source and caller confirmation. | repository-inventory hypothesis |
| `tests/test_intake_pipeline.py` | test evidence | Primary implementation candidate, subject to post-approval source and caller confirmation. | repository-inventory hypothesis |
| `tests/test_new_file_due_diligence.py` | test evidence | Primary implementation candidate, subject to post-approval source and caller confirmation. | repository-inventory hypothesis |
| `tests/test_workflow_enterprise_mcp.py` | test evidence | Primary implementation candidate, subject to post-approval source and caller confirmation. | repository-inventory hypothesis |
| `tests/test_workflow_mcp.py` | test evidence | Primary implementation candidate, subject to post-approval source and caller confirmation. | repository-inventory hypothesis |

### Post-change checks

1. Confirm the authoritative boundary and material callers before the first edit.
2. Compare actual changed files and symbols with the approved impact map; justify or correct every unexpected path.
3. Detect missed callers, caller-specific business logic, wrong-layer placement, and public-contract drift.
4. Check dependency manifests and imports when the approved contract forbids a new dependency.
5. Run every requirement-linked validation tier and preserve unresolved evidence as a gap, not a pass.

## Behaviour Analysis

- **Status:** `planning-hypothesis`.
- **Evidence boundary:** Derived from explicit user wording and repository path inventory only. Actual states, transitions, side effects, responses, and edit necessity remain unconfirmed until after approval.

| Requirement | Scenario | Observable result | Required proof |
|---|---|---|---|
| REQ-02; REQ-03 | Exercise the existing API response at each affected workflow stage. | Existing fields, meanings, and status behavior remain compatible. | contract, integration |
| REQ-01 | Submit accepted fresh profile answers with complete requirement-specific proof bindings, then retry and submit stale, unrelated, or changed-target evidence. | The valid input mints one target-bound planning-readiness receipt and retries idempotently; invalid inputs mint no authorizing receipt and fail closed. | behaviour |
| REQ-02 | Invoke public CLI Start for Host Question Flow with a valid planning-readiness receipt and with raw, intake-only, stale, replayed, changed-target, or mismatched inputs. | Only the valid matching receipt permits Planning Lock creation; every invalid input creates no lock and returns precise corrective guidance, while ordinary Start remains compatible. | behaviour |
| REQ-03 | Invoke MCP tailtrail_start with a planning-readiness receipt and through an existing non-Host-Question-Flow caller. | The receipt reaches the CLI validator unchanged and existing callers that omit the new input retain their prior behavior. | behaviour |

### Scoped evidence

| Path | Role | Planned use | Confidence |
|---|---|---|---|
| `scripts/adoption-validation.py` | supporting candidate | Inspect after approval; edit only when the confirmed behaviour path requires it. | repository-inventory hypothesis |
| `scripts/advanced-runtime.py` | supporting candidate | Inspect after approval; edit only when the confirmed behaviour path requires it. | repository-inventory hypothesis |
| `scripts/aidlc-official-bridge.py` | supporting candidate | Inspect after approval; edit only when the confirmed behaviour path requires it. | repository-inventory hypothesis |
| `scripts/aidlc-official-detect.py` | supporting candidate | Inspect after approval; edit only when the confirmed behaviour path requires it. | repository-inventory hypothesis |
| `scripts/aidlc-official-host.py` | supporting candidate | Inspect after approval; edit only when the confirmed behaviour path requires it. | repository-inventory hypothesis |
| `scripts/closure-contract.py` | supporting candidate | Inspect after approval; edit only when the confirmed behaviour path requires it. | repository-inventory hypothesis |
| `scripts/context-receipt.py` | supporting candidate | Inspect after approval; edit only when the confirmed behaviour path requires it. | repository-inventory hypothesis |
| `scripts/context_receipt.py` | supporting candidate | Inspect after approval; edit only when the confirmed behaviour path requires it. | repository-inventory hypothesis |
| `scripts/debug-host-diagnosis.py` | supporting candidate | Inspect after approval; edit only when the confirmed behaviour path requires it. | repository-inventory hypothesis |
| `scripts/host-adapter-conformance.py` | supporting candidate | Inspect after approval; edit only when the confirmed behaviour path requires it. | repository-inventory hypothesis |
| `scripts/host-decision.py` | supporting candidate | Inspect after approval; edit only when the confirmed behaviour path requires it. | repository-inventory hypothesis |
| `scripts/host-interpretation-builder.py` | supporting candidate | Inspect after approval; edit only when the confirmed behaviour path requires it. | repository-inventory hypothesis |
| `scripts/host-reply-validate.py` | supporting candidate | Inspect after approval; edit only when the confirmed behaviour path requires it. | repository-inventory hypothesis |
| `scripts/host-runtime-conformance.py` | supporting candidate | Inspect after approval; edit only when the confirmed behaviour path requires it. | repository-inventory hypothesis |
| `scripts/host-workspace-adapter.py` | supporting candidate | Inspect after approval; edit only when the confirmed behaviour path requires it. | repository-inventory hypothesis |
| `scripts/host_contract.py` | supporting candidate | Inspect after approval; edit only when the confirmed behaviour path requires it. | repository-inventory hypothesis |
| `scripts/install-copilot.py` | supporting candidate | Inspect after approval; edit only when the confirmed behaviour path requires it. | repository-inventory hypothesis |
| `scripts/intake_pipeline.py` | supporting candidate | Inspect after approval; edit only when the confirmed behaviour path requires it. | repository-inventory hypothesis |
| `scripts/learning-refresh.py` | supporting candidate | Inspect after approval; edit only when the confirmed behaviour path requires it. | repository-inventory hypothesis |
| `scripts/learning-use-receipt.py` | supporting candidate | Inspect after approval; edit only when the confirmed behaviour path requires it. | repository-inventory hypothesis |
| `scripts/learning-v3.py` | supporting candidate | Inspect after approval; edit only when the confirmed behaviour path requires it. | repository-inventory hypothesis |
| `scripts/mcp-server.py` | supporting candidate | Inspect after approval; edit only when the confirmed behaviour path requires it. | repository-inventory hypothesis |
| `scripts/navigator-installed-release-proof.py` | supporting candidate | Inspect after approval; edit only when the confirmed behaviour path requires it. | repository-inventory hypothesis |
| `scripts/new_file_due_diligence.py` | supporting candidate | Inspect after approval; edit only when the confirmed behaviour path requires it. | repository-inventory hypothesis |
| `scripts/package-release-proof.py` | supporting candidate | Inspect after approval; edit only when the confirmed behaviour path requires it. | repository-inventory hypothesis |
| `scripts/planning_lock.py` | supporting candidate | Inspect after approval; edit only when the confirmed behaviour path requires it. | repository-inventory hypothesis |
| `scripts/question-orchestrator.py` | workflow orchestration | Inspect after approval; edit only when the confirmed behaviour path requires it. | repository-inventory hypothesis |
| `scripts/run-ledger.py` | supporting candidate | Inspect after approval; edit only when the confirmed behaviour path requires it. | repository-inventory hypothesis |
| `scripts/task-start.py` | supporting candidate | Inspect after approval; edit only when the confirmed behaviour path requires it. | repository-inventory hypothesis |
| `scripts/workflow_runtime/start_integration.py` | supporting candidate | Inspect after approval; edit only when the confirmed behaviour path requires it. | repository-inventory hypothesis |
| `tests/test_focused_validation_contracts.py` | supporting candidate | Inspect after approval; edit only when the confirmed behaviour path requires it. | repository-inventory hypothesis |
| `tests/test_host_question_flow_event_schema.py` | side-effect boundary | Inspect after approval; edit only when the confirmed behaviour path requires it. | repository-inventory hypothesis |
| `tests/test_intake_pipeline.py` | supporting candidate | Inspect after approval; edit only when the confirmed behaviour path requires it. | repository-inventory hypothesis |
| `tests/test_new_file_due_diligence.py` | supporting candidate | Inspect after approval; edit only when the confirmed behaviour path requires it. | repository-inventory hypothesis |
| `tests/test_workflow_enterprise_mcp.py` | workflow orchestration | Inspect after approval; edit only when the confirmed behaviour path requires it. | repository-inventory hypothesis |
| `tests/test_workflow_mcp.py` | workflow orchestration | Inspect after approval; edit only when the confirmed behaviour path requires it. | repository-inventory hypothesis |

### Post-change checks

1. Confirm the actor, starting state, authoritative state owner, and observable interface before the first edit.
2. Map each actual transition and side effect to an approved behaviour scenario and requirement ID.
3. Reconcile actual changed paths with the approved behaviour roles; justify or correct unexpected scope.
4. Require matching behaviour and integration receipts; unit evidence alone cannot complete the Behaviour Harness.
5. Report unresolved scenarios as evidence-incomplete or drifted, never as a generic pass.

## Focused Validation Coverage Summary

- **Requirements covered:** 3/3.
- **Proof command reuse:**
  - `cmd-0772cb` covers 1 requirement(s): REQ-01.
  - `cmd-5886f1` covers 1 requirement(s): REQ-03.
  - `cmd-c0e115` covers 1 requirement(s): REQ-02.

## Token Estimate

- Unavailable: scope is `ambiguous`, so a token estimate would not be reliable.
- This is an estimate from saved scope, not measured model/provider usage.

## Implementation Boundary

- **Editable scope:** `scripts/intake_pipeline.py`, `scripts/mcp-server.py`, `scripts/task-start.py`.
- **Read-only / proof-only scope:** `TAILTRAIL-HOST-TAILTRAIL-EVIDENCE-VALIDATION-DESIGN.md`, `scripts/adoption-validation.py`, `scripts/advanced-runtime.py`, `scripts/aidlc-official-bridge.py`, `scripts/aidlc-official-detect.py`, `scripts/aidlc-official-host.py`, `scripts/closure-contract.py`, `scripts/context-receipt.py`, `scripts/context_receipt.py`, `scripts/debug-host-diagnosis.py`, `scripts/host-adapter-conformance.py`, `scripts/host-decision.py`, `scripts/host-interpretation-builder.py`, `scripts/host-reply-validate.py`, `scripts/host-runtime-conformance.py`, `scripts/host-workspace-adapter.py`, `scripts/host_contract.py`, `scripts/install-copilot.py`, `scripts/learning-refresh.py`, `scripts/learning-use-receipt.py`, `scripts/learning-v3.py`, `scripts/navigator-installed-release-proof.py`, `scripts/new_file_due_diligence.py`, `scripts/package-release-proof.py`, `scripts/planning_lock.py`, `scripts/question-orchestrator.py`, `scripts/requirement_intake.py`, `scripts/run-ledger.py`, `scripts/workflow_runtime/start_integration.py`, `tests/test_intake_pipeline.py`, `tests/test_mcp_server.py`, `tests/test_public_route_gate.py`.
- **Excluded:** every path, command, external system, deployment, and data change not explicitly recorded above remains outside this approval.
- **Data impact:** no data impact is authorized unless a requirement above names it explicitly.

## Approval Checklist

- [x] Requirements are present and reviewable.
- [x] Every requirement has an editable implementation owner.
- [x] Runnable proof commands are registered and mapped to requirements.
- [x] Material questions are resolved.
- [x] Mandatory planning audit is clean for this exact plan revision.
- [ ] The host has reviewed the scope, preservation criteria, proof commands, analyses, and excluded boundary.

## Review Cycles Summary

| Cycle | Revision | Status | Action |
|---|---|---|---|
| 1 | v1 | initial review | Start Plan generated and mandatory audit required |
| 2 | v2 | revision recorded | Plan changed and must be audited again |

- **Total review cycles:** 2
- **Revision cycles:** 1
- **Latest audit:** `clean`; 0 finding(s).

## Approval Decision

**READY FOR APPROVAL** — review this plan, then explicitly approve this exact run. Approval is separate from activation and permits no unlisted work.

## Canonical Machine Record

- Machine-readable state remains available at [`.tailtrail/runs/start-20261103074542-c5f97c/planning/revisions/start-report-v2.json`](.tailtrail/runs/start-20261103074542-c5f97c/planning/revisions/start-report-v2.json); it is not the approval view.

---

*End of Start Plan.*