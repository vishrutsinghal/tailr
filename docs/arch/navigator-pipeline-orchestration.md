# Navigator Pipeline Orchestration Design

## 1. Vision
To prevent "agent drift" and "coding for the test," TailTrail moves from a single-stage planning process to a **Sequential Worker Pipeline**. The **Navigator** acts as the sole orchestrator (the Brain), while the **Pipeline Judge** acts as the deterministic enforcement layer (the Guard). 

The goal is to ensure the agent cannot transition from "fixing code" to "writing tests" without an explicit, validated handoff, and cannot edit production code while in a "testing" state.

## 2. The Command Chain (Single Communication Point)
To avoid fragmented logic, the agent never interacts with the Judge or the Pipeline Manager directly. All communication is brokered by the Navigator.

**Communication Flow:**
`User` $\longleftrightarrow$ `Navigator` $\longleftrightarrow$ `Host Agent`

**The Validation Loop:**
1. **Agent** proposes a set of actions (e.g., "I want to edit these 3 files").
2. **Navigator** intercepts the proposal.
3. **Navigator** calls `PipelineJudge.validate_proposal(active_badge, paths)`.
4. **Judge** returns a binary `(Allowed, Reason)`.
5. **Navigator** either:
   - **Approved:** Updates the Planning Lock and tells the Agent: *"Proposal approved. You may now proceed with edits."*
   - **Rejected:** Tells the Agent: *"Proposal rejected. [Reason]. Please revise your paths to match the current stage boundary."*

## 3. Responsibility Matrix

| Component | Role | Primary Responsibility | What it does NOT do |
| :--- | :--- | :--- | :--- |
| **Navigator** | **Orchestrator** | Strategy and communication. Assigns tasks, manages the conversation, and triggers stage transitions based on Judge approval. | Does not determine if a path is "legal" or manage the low-level state of the pipeline. |
| **Pipeline Judge** | **Enforcer** | The "Reflexive Brain." Pure deterministic validation of paths and transitions against the active `WorkerContract` and Drift Analysis. | Does not manage the conversation, the la-level pipeline state, or the overall task strategy. |
| **Pipeline Manager** | **State Store** | The "Deterministic Ledger." Tracks `active_stage`, `completed_stages`, and the `HandoffManifest`. | Does not make semantic decisions, validate requirements, or "think" about the task. |
| **Host Agent** | **Worker** | Executes the logic, proposes files, and writes code. | Does not decide its own permissions or stage transitions. |

## 4. Detailed Implementation Logic

### 4.1 Role-Aware Prompting (The "Steering")
The Navigator will now vary its prompts based on the `active_stage` retrieved from the `PipelineManager`:

- **IMPLEMENTATION Stage:** 
  - *Prompt:* "Identify the production symbols and modules that own this behavior. Do not include test files."
  - *Judge Gate:* Prohibits `test` roles.
- **TESTING Stage:** 
  - *Prompt:* "Identify the test classes or spec files that prove this behavior. Production files are read-only."
  - *Judge Gate:* Prohibits `production-source` roles.
- **INFRA Stage:** 
  - *Prompt:* "Identify the Terraform or K8s manifests that govern this resource."
  - *Judge Gate:* Prohibits `production-source` and `test` roles.

### 4.2 The "Write-Access Gate" (The "Lock")
The system implements a hard-stop at the approval layer (plus guarded in-repo writes):
1. Every patch/proposal path is validated before approval or application.
2. The `PipelineJudge` checks the path's role.
3. If `role` $\in$ `ProhibitedRoles[active_badge]`, the approval/application is aborted (`source_patch_apply` raises; `guard_write` raises `SecurityBoundaryError`).

`WriteGuardian` denies by default when no pipeline run exists; only an explicit `permissive=True` declares an unenforced write (installer flows, which have no run by nature). Intercepting host-agent writes in-process is out of scope — those are gated at proposal/approval time instead.

### 4.3 The Drift-Corrected Handoff
Transitions between stages are not automatic; they are **evidence-gated**.

**Testing $\rightarrow$ Infra Transition:**
1. Agent submits a `HandoffManifest` (Changes $\rightarrow$ Test Results).
2. Navigator calls `PipelineJudge.verify_transition()`.
3. Judge runs **Drift Analysis** $\rightarrow$ Compares final code against original requirements.
4. If `drift_detected == true` $\rightarrow$ **Transition Blocked**. The Navigator tells the agent: *"Your fix passes the tests but violates REQ-01. Return to Implementation stage."*

## 5. Complex Scenario Handling

### Scenario: The "Bug Discovery" during Testing
- **Event:** While in `TESTING` stage, the agent finds a bug in `auth.py` that must be fixed to make the test pass.
- **Process:**
  1. Agent attempts to edit `auth.py`.
  2. `PipelineJudge` blocks the write (Production is prohibited in `TESTING`).
  3. Navigator informs the agent: *"You found a production bug. You cannot fix it while in the Testing slice. I am returning you to the Implementation stage."*
  4. `PipelineManager` resets `active_stage` to `IMPLEMENTATION`.
  5. Agent fixes the bug $\rightarrow$ returns to `TESTING`.

### Scenario: Hands-Free Slicing
- **Process:** The Navigator breaks the broad "Hands-Free" goal into three distinct slices. It treats each slice as a mini-run with its own approved owner list and badge. This prevents the agent from "over-reaching" and editing the entire repo in one prompt.

## 6. Integration Points
- **`scripts/navigator.py`**: Now calls `PipelineManager.get_current_stage()` to determine which prompt template to use.
- **`scripts/pipeline_judge.py`**: Updated to be a stateless utility that takes `(badge, path)` and returns a boolean.
- **`scripts/planning_lock.py`**: Expanded to store the `pipeline` state and `handoff_manifest`.
