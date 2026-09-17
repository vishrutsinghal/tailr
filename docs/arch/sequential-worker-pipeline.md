# Sequential Worker Pipeline Architecture

## 1. Overview
The Sequential Worker Pipeline is an architectural evolution of the TailTrail scope management system. It replaces the "Mixed-Mode" planning approach with a specialized, stage-gated execution pipeline. Instead of a single agent acting as a generalist, the system orchestrates a sequence of "Workers" (Implementation, Testing, Infra), each bound by a deterministic "Sequential Badge" that restricts write-access to specific repository roles.

This design ensures a "Trust but Verify" model where the agent's semantic capabilities are checked by the CLI's deterministic enforcement, preventing scope drift and "coding for the test."

## 2. The Sequential Badge Model (Access Control)

### 2.1 Permission Sets
Each stage in the pipeline is assigned a "Badge" (a set of permissions). The badge is not just a label; it is a hard constraint enforced at the file-system level.

| Stage (Worker) | Badge | Allowed Write Roles | Read Access | Prohibited Write Roles |
| :--- | :--- | :--- | :--- | :--- |
| **Implementation** | `impl-badge` | `production-source`, `supporting-assets` | All | `test-paths`, `managed-tooling` |
| **Testing** | `test-badge` | `test-paths` | All | `production-source`, `supporting-assets` |
| **Infra** | `infra-badge` | `configuration`, `manifests` | All | `production-source`, `test-paths` |

### 2.2 Enforcement Mechanism (The Judge)
The CLI acts as the "Judge." Every write request in scope is validated:
`if path_role in ProhibitedRoles[active_badge]: Block_Write()`

Enforcement has two implemented layers: (a) planned/patch paths are validated against the active badge *before* approval or application (`validate_planned_paths`, enforced in `source_patch_apply` for runs with an active pipeline stage); (b) in-repo installer writes go through explicit `guard_write` calls. Host-agent writes happen outside this repo and cannot be intercepted in-process — gating those requires host integration. The drift gate (`drift_analysis.analyze`, fail-closed) is wired into TESTING → INFRA transitions and covered by pipeline tests.

## 3. Pipeline Lifecycle & Handoffs

### 3.1 The Execution Flow
1. **Requirement Analysis**: Host Agent analyzes the prompt $\rightarrow$ Identifies required stages $\rightarrow$ Creates a **Pipeline Plan**.
2. **Implementation Stage**:
   - `impl-badge` is activated.
   - Worker modifies production code.
   - Produces a **Change Manifest** (List of modified symbols and files).
3. **Testing Stage**:
   - `test-badge` is activated.
   - Worker receives the Change Manifest.
   - Worker writes tests and runs them.
   - Produces a **Verification Report** (Pass/Fail + Evidence).
4. **Infra Stage**:
   - `infra-badge` is activated.
   - Worker updates deployment scripts based on the verified changes.
5. **Final Closure**: Completion Report is generated only after all required stages are `completed`.

### 3.2 The Handoff Manifest
To prevent memory loss between workers, a structured `Handoff` object is passed:
```json
{
  "from_stage": "IMPLEMENTATION",
  "to_stage": "TESTING",
  "change_manifest": ["src/auth.py:L20-L45", "src/user.py:L10"],
  "requirement_pointers": ["REQ-01", "REQ-04"],
  "context": "Implemented JWT token rotation"
}
```

## 4. Complex Scenarios & Guardrails

### 4.1 The "Bug-Fix Loop" (Implementation $\leftrightarrow$ Testing)
When the Testing Worker finds a bug, the pipeline does not simply "fail." It enters a **Regression Loop**:
1. **Test Worker** $\rightarrow$ generates **Failure Evidence** (stack trace + failing test case).
2. **Handoff** $\rightarrow$ triggers a return to the **Implementation Stage**.
3. **Implementation Worker** $\rightarrow$ receives the evidence and applies a fix.
4. **Circuit Breaker**: If the loop exceeds 3 iterations, the system freezes and requests a "Design Review" from the user to prevent infinite guessing.

### 4.2 Preventing "Coding for the Test" (Drift Analysis)
A common failure mode is when an agent modifies production code solely to make a test pass, even if it violates the original requirement.
- **The Gate**: Before transitioning from `TESTING` $\rightarrow$ `INFRA`, the system triggers the **Drift Analysis** module.
- **Verification**: It compares the final state of the production code against the **Original Requirements**.
- **Action**: If the fix introduces "Requirement Drift," the transition is blocked, and the worker is sent back to the Implementation Stage with a "Drift Violation" warning.

### 4.3 Mixed Prompt Handling
For prompts requiring multiple changes (e.g., "Fix bug, add test, update infra"), the pipeline creates a **Composite Plan**. Instead of one mixed badge, it schedules the stages sequentially.
- **Sequentiality**: `Impl` $\rightarrow$ `Test` $\rightarrow$ `Infra`.
- **Verification**: Each stage must be signed off by its respective badge before the next begins.

### 4.4 Hands-Free Mode "Slicing"
In Hands-Free mode, the agent is prone to "over-reaching." To mitigate this, TailTrail implements **Slicing**:
- The agent is forced to propose a plan for **one stage at a time**.
- The user (or the system) approves "Slices" of the pipeline.
- This ensures that the "Impl Worker" doesn't silently modify infra files while fixing a bug.

## 5. Integration Mapping (Avoiding Duplication)

| New Pipeline Feature | Existing TailTrail Component | Integration Point |
| :--- | :--- | :--- |
| **Stage Tracking** | `Planning Lock` | Add `active_stage` and `pipeline_state` to lock metadata. |
| **Role Enforcement** | `classify_repository_role` | Use output of role classifier as the key for `ProhibitedRoles`. |
| **Drift Prevention** | `Drift Analysis` | Invoke as a mandatory "Stage Gate" before Infra transition. |
| **Write Protection** | File System Wrapper | Intercept `write` calls and validate against active badge. |
