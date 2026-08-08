# TailTrail MCP: a practical guide from basics to advanced use

## Why this guide exists

**tailtrail-mcp.md** is the architecture and implementation design. This guide
explains the same system as if you are learning MCP for the first time: what
the protocol is, where TailTrail fits, what happens in each request, why the
server is deliberately narrow, and how to extend it without weakening the
product.

The examples use TailTrail's local MCP server in **scripts/mcp-server.py**.
Names and paths below are real TailTrail concepts; example IDs and JSON values
are illustrative.

---

## 1. MCP in one sentence

**Model Context Protocol (MCP)** is a standard way for an AI host such as
Codex, Claude, or an IDE to discover and call well-defined tools supplied by a
local or remote server.

Without MCP, an assistant mainly receives instructions in Markdown and may need
to decide for itself which command to run. With MCP, the host can ask a server:

~~~text
What capabilities do you provide?
Call this named capability with this structured input.
Return a structured result I can inspect.
~~~

MCP does **not** make a model smarter by itself. It gives the model a safer,
more observable interface to useful capabilities.

---

## 2. The main MCP pieces

| Concept | Plain-language meaning | TailTrail example |
| --- | --- | --- |
| **Host / client** | The application containing the assistant. It connects to MCP servers. | Codex, Claude Code, or an IDE agent. |
| **MCP server** | A process that advertises tools and handles calls. | scripts/mcp-server.py serve. |
| **Tool** | A named operation with an input schema and result. | navigator_plan, anchor_show, tailtrail_start. |
| **Tool schema** | A contract describing valid input. | run_id must be a string; approved must be a boolean. |
| **Tool call** | A host asking the server to perform one operation. | Call planning_lock_show for a run. |
| **Transport** | How host and server exchange messages. | TailTrail uses local standard input/output (stdio). |
| **JSON-RPC** | The message envelope used by MCP in this server. | initialize, tools/list, and tools/call. |
| **Artifact** | A persisted piece of local evidence created by TailTrail. | anchors/approved-v1.json or checkpoints/checkpoint-1.json. |

The important distinction is:

~~~text
MCP is the interface.
TailTrail is the workflow and evidence system behind that interface.
~~~

---

## 3. Why TailTrail needs MCP

TailTrail has many useful operations: Navigator planning, requirement anchors,
testing evidence, architecture assessments, recovery evidence, and completion
reports. Giving every host a long set of Markdown instructions creates three
problems:

1. Each host may interpret the instructions differently.
2. It is difficult to see exactly what the assistant called and why.
3. A broad command interface can accidentally become an unsafe “run anything”
   interface.

TailTrail MCP solves this by exposing narrow, inspectable capability calls.

~~~mermaid
flowchart LR
    U["Developer request"] --> H["AI host<br/>Codex / Claude / IDE"]
    H -->|"typed tool call"| S["TailTrail MCP server<br/>local stdio"]
    S --> P["TailTrail Python modules"]
    P --> A["Local repository and<br/>.tailtrail evidence artifacts"]
    A --> P
    P --> S
    S -->|"structured result + evidence pointers"| H
    H --> U
~~~

The server is not an autonomous coding agent. It does not keep running after a
call, schedule background work, or silently execute a full delivery chain.

---

## 4. TailTrail's local-first safety model

TailTrail intentionally uses a **local stdio** MCP server:

- no web server or listening TCP port;
- no cloud service or telemetry upload;
- no stored raw prompt history;
- no arbitrary shell execution tool;
- no generic “write any file” tool;
- no direct deploy, push, commit, or package-install tool.

This choice is architectural, not cosmetic. AI tools are powerful because they
can act. A product must make authority visible and narrow.

TailTrail therefore has two main capability tiers:

| Tier | Typical tools | What they can do |
| --- | --- | --- |
| **Read-only** | navigator_plan, anchor_show, workflow_dashboard_show, graph_map | Inspect source-derived guidance or saved artifacts. They do not modify project source. |
| **Controlled** | tailtrail_start, planning_lock_approve, harness_control_check, source_patch_apply | Write limited TailTrail metadata, run an allowlisted control file, or apply a repository-safe patch—but only with explicit approval rules. |

The exact tool allowlists live near the top of **scripts/mcp-server.py**:
READ_ONLY_TOOLS and CONTROLLED_TOOLS. A reviewer can answer “what can this
server do?” by reading a short declared list, not by guessing from the whole
codebase.

---

## 5. MCP transport: what actually travels over stdio

When a configured MCP host starts TailTrail, it launches a child process such
as:

~~~powershell
py -3 D:\path\to\tailtrail\scripts\mcp-server.py serve
~~~

The host writes one JSON message per line to the process's standard input.
TailTrail writes one JSON response per line to standard output. Standard output
must stay protocol-clean: ordinary debug prints there would corrupt the MCP
conversation.

The minimal lifecycle is:

~~~text
1. Host starts the local server process.
2. Host sends initialize.
3. Server returns protocol version, name, and capabilities.
4. Host sends tools/list.
5. Server returns tool definitions and JSON schemas.
6. Host sends tools/call when a tool is useful.
7. Server validates, dispatches, and returns structured tool content.
8. Host can end the process when the session ends.
~~~

TailTrail's handle() and serve() functions implement this small JSON-RPC loop.
Supported methods are intentionally limited to initialize, tools/list,
tools/call, and notifications/initialized.

### Example: initialization

Host request:

~~~json
{
  "jsonrpc": "2.0",
  "id": 1,
  "method": "initialize",
  "params": {}
}
~~~

TailTrail response, simplified:

~~~json
{
  "jsonrpc": "2.0",
  "id": 1,
  "result": {
    "protocolVersion": "2024-11-05",
    "serverInfo": {"name": "tailtrail-mcp", "version": "1"},
    "capabilities": {"tools": {}}
  }
}
~~~

### Example: tool discovery

Host request:

~~~json
{"jsonrpc": "2.0", "id": 2, "method": "tools/list", "params": {}}
~~~

One returned tool definition looks like:

~~~json
{
  "name": "planning_lock_show",
  "description": "Read one TailTrail Planning Lock.",
  "inputSchema": {
    "type": "object",
    "properties": {
      "root": {"type": "string"},
      "run_id": {"type": "string"}
    },
    "required": ["run_id"]
  }
}
~~~

The schema lets the host validate obvious mistakes before it calls the tool. It
is also documentation that stays close to executable code.

---

## 6. How one TailTrail MCP tool is built

Each tool has five connected pieces:

~~~mermaid
flowchart LR
    A["Tool name in allowlist"] --> B["Definition + JSON input schema"]
    B --> C["Python handler"]
    C --> D["Existing TailTrail module / CLI contract"]
    D --> E["Structured result, evidence, errors"]
    E --> F["Focused tests + MCP doctor"]
~~~

1. **Allowlist**
   The tool is declared read-only or controlled. A handler that exists but is
   not allowlisted cannot be called through MCP.

2. **Definition**
   tool_definitions() exposes the stable name, user-facing description, and
   input schema.

3. **Handler**
   A function such as planning_lock_show(args) validates and converts input,
   then calls an existing implementation.

4. **Shared business logic**
   The handler should reuse a TailTrail module or CLI script. The MCP layer is
   a bridge; it should not become a second Navigator, second harness, or second
   recovery implementation.

5. **Tests and diagnosis**
   Tests check inventory, ordering, schemas, safety requirements, and key
   handler behavior. tailtrail mcp doctor catches contract drift.

### Example: a read-only artifact tool

anchor_show reads:

~~~text
.tailtrail/runs/<run-id>/anchors/approved-v1.json
~~~

It returns actual approved requirements rather than a conversational summary.
That matters because requirement IDs, preservation rules, and evidence plans
must remain exact when they control later validation or recovery.

Example call:

~~~json
{
  "name": "anchor_show",
  "arguments": {
    "root": "D:/work/claims-service",
    "run_id": "start-20260802-abc123"
  }
}
~~~

Example result shape:

~~~json
{
  "tool": "anchor_show",
  "result": {
    "run_id": "start-20260802-abc123",
    "requirements": [
      {
        "requirement_uid": "req-7c1f...",
        "display_id": "REQ-01",
        "statement": "Reject zero claim amounts",
        "preserve_rules": ["Positive claim amounts remain valid"]
      }
    ]
  },
  "execution": {"read_only": true, "exit_code": 0}
}
~~~

---

## 7. The important TailTrail Start flow

The most useful MCP action is tailtrail_start. It exists because splitting a
Start action into several loosely related calls can produce confusing state:
the host may create a lock but forget to show the actual plan, or show a plan
without persisting it.

tailtrail_start performs one **metadata-only atomic Start flow**:

~~~mermaid
sequenceDiagram
    participant H as AI host
    participant M as TailTrail MCP
    participant T as Task Start
    participant R as .tailtrail run artifacts

    H->>M: tailtrail_start(goal, approved:true)
    M->>T: invoke task-start with a planning run ID
    T->>R: create planning/lock-v1.json
    T->>R: save planning/start-report-v1.json
    T-->>M: complete Start Report and run ID
    M-->>H: structured planning-only result
    Note over H,R: No source edit, test, scanner, Git mutation, or implementation
~~~

The approved:true argument on tailtrail_start means the user explicitly asked
to start TailTrail and permits creation of local TailTrail metadata. It does
**not** approve source edits.

Example call:

~~~json
{
  "name": "tailtrail_start",
  "arguments": {
    "goal": "Fix claim amount validation and add focused tests",
    "root": "D:/work/claims-service",
    "changed": ["src/claims_api/validation.py"],
    "approved": true
  }
}
~~~

The returned Start Report tells the host which TailTrail controls were selected,
what likely paths must be inspected, and the Planning Lock run ID. Per the
Start rule, the host must stop after returning that report.

### Approval and anchor activation

Only after the user approves the exact run can the host call:

~~~json
{
  "name": "planning_lock_approve",
  "arguments": {
    "root": "D:/work/claims-service",
    "run_id": "start-20260802-abc123",
    "approved": true
  }
}
~~~

For a run created by tailtrail_start, this uses the saved Start Report and
activates it. Guided-delivery and hands-free work then receive:

~~~text
.tailtrail/runs/<run-id>/anchors/approved-v1.json
~~~

This protects against **approval-time re-planning**: the agent cannot quietly
re-run Navigator against a changed repository and call that changed plan the
one the user approved.

Tiny/lean tasks may intentionally remain Planning-Lock-only. A broad or
hands-free task needs a durable requirement anchor because later checkpoints,
drift detection, and recovery need a stable requirement identity.

---

## 8. How artifacts connect MCP to Harness Engineering

MCP calls should return pointers to evidence rather than pretend that prose is
proof. TailTrail's run directory gives all tools a shared vocabulary:

~~~text
.tailtrail/
  runs/
    <run-id>/
      planning/
        lock-v1.json                 # writes blocked or permitted
        start-report-v1.json         # exact proposal seen before approval
      anchors/
        approved-v1.json             # immutable desired requirements
      checkpoints/
        checkpoint-1.json            # observed actual state + drift
      controls/                      # validation receipts where applicable
      feedback/                      # bounded correction inputs
      recovery/                      # task-scoped recovery evidence
      completion/                    # final report artifacts
~~~

| Question a host asks | Tool family | Artifact used |
| --- | --- | --- |
| What did we agree to build? | Anchor | anchors/approved-v1.json |
| Are writes allowed yet? | Planning Lock | planning/lock-v1.json |
| What actually changed and passed? | Checkpoint | checkpoints/checkpoint-N.json |
| Did the agent drift? | Completion / continuity / dashboard | checkpoint drift plus feedback artifacts |
| Is architecture aligned? | Architecture assessment | saved architecture evidence |
| Can we safely recover this task only? | Recovery boundary / reconciliation | task ownership and recovery artifacts |

The agent may summarize these results for a developer, but canonical data
remains available for a later tool call, a future UI, or a test.

---

## 9. Controlled tools: why they are not arbitrary commands

The most dangerous beginner design is a tool like:

~~~text
run_command(command: string)
~~~

It looks flexible but lets a model turn an ambiguous prompt into arbitrary shell
behavior. It is difficult to review, hard to make portable, and can
accidentally run destructive actions.

TailTrail instead uses narrow controlled tools.

### harness_control_check

This tool runs a repository-relative, predeclared control list—not free-form
shell text. It requires:

1. approved:true in the tool input;
2. an approved Planning Lock for the same run_id;
3. a safe relative control definition;
4. a run-specific evidence result.

Permission is both **explicit** and **scoped**. A valid approval for one task
does not automatically authorize every unrelated task.

### source_patch_apply

This tool accepts one unified Git patch after approval. It validates that patch
paths stay inside the repository and does not commit, push, or run arbitrary
post-patch commands. It is intentionally narrower than granting an agent a
general filesystem or shell tool.

### Why MCP approval is not enough on its own

An MCP host might have its own unrestricted terminal or filesystem tools. Those
tools could bypass TailTrail. The MCP boundary protects actions performed
through TailTrail; host adapters and repository guidance repeat the workflow
rule so the agent's behavior also stays aligned.

---

## 10. A complete multi-file example

Consider:

> Fix zero claim amount validation. Ensure the service path rejects it and add
> focused tests. Do not change unrelated claim models.

### Planning

1. Host calls tailtrail_start.
2. Navigator selects requirement completion, impact mapping, focused testing,
   and architecture fitness because the behavior crosses validation and service
   layers.
3. The host returns the Start Report and stops.

### Approval

4. User approves start-20260802-abc123.
5. Host calls planning_lock_approve.
6. The saved plan becomes an immutable anchor:

~~~text
REQ-01: Reject zero claim amounts.
Likely paths: validation.py, service.py, tests/test_claim_validation.py
Preserve: positive claim amounts remain valid.
Proof: focused validation and service-path evidence.
~~~

### Implementation and evidence

7. The implementation agent reads selected files and makes the smallest
   approved change.
8. It runs selected real controls after approval.
9. It records results in a checkpoint. A requirement is marked validated only
   when recorded evidence supports that state.
10. architecture_assessment_show can reveal a missed service caller;
    workflow_dashboard_show can show unresolved drift or missing evidence.

### Correction and completion

11. If service-path evidence is missing, Context Continuity can render a short
    packet: active REQ-01, preserve positive amounts, current gap: service-path
    evidence missing.
12. The agent makes one bounded correction, validates again, and writes a new
    checkpoint.
13. A completion report summarizes requirement state, scope, evidence,
    unresolved drift, and recovery availability.

MCP does not do the coding. It makes important TailTrail steps callable,
auditable, and consistently connected to shared state.

---

## 11. Adding a new tool safely

Use this checklist before adding a tool such as behavior_assessment_show.

### Step 1: decide whether MCP is actually needed

Add a tool when a host needs a repeatable, structured capability across several
clients. Do **not** add a tool just because a helper function exists.

Good candidate:

~~~text
Show the latest saved Behaviour Harness assessment for a run.
~~~

Poor candidate:

~~~text
Run all quality actions until the repository looks good.
~~~

### Step 2: define a narrow contract

Choose a stable tool name, required and optional input, output shape, expected
errors, mutability tier, and evidence path.

~~~json
{
  "name": "behavior_assessment_show",
  "inputSchema": {
    "type": "object",
    "properties": {
      "root": {"type": "string"},
      "run_id": {"type": "string"}
    },
    "required": ["run_id"]
  }
}
~~~

### Step 3: reuse existing domain logic

Write the behavior assessment in a reusable TailTrail module first. CLI, MCP
handler, and a future dashboard should call that same module. This avoids one
behavior for CLI users and another for MCP users.

### Step 4: add the handler and allowlist entry

The handler should do boundary work only: resolve root, validate a safe path or
ID, call the domain module, and package result metadata.

~~~python
def behavior_assessment_show(args):
    root = root_from(args)
    result = behavior_module.show(root, run_id(args))
    return {
        "tool": "behavior_assessment_show",
        "result": result,
        "execution": {"read_only": True, "exit_code": 0},
    }
~~~

### Step 5: test the contract

At minimum test:

- the tool appears in the intended allowlist;
- it appears in tools/list with valid schema;
- the handler reads expected fixture/artifact;
- malformed input gives a clear failure;
- it does not write source or execute a command;
- tailtrail mcp doctor still passes.

### Step 6: document user-level value

Explain when an agent should call it, what returned evidence means, and what it
cannot prove. Avoid adding a tool that no host knows how to use.

---

## 12. Common mistakes and how TailTrail avoids them

| Mistake | Why it hurts | TailTrail answer |
| --- | --- | --- |
| One mega-tool for all work | Hidden decisions, unclear authority, hard debugging | Small named tools with one purpose. |
| Arbitrary shell tool | Unsafe and difficult to audit | Repository-defined controls only. |
| Tool name claims more than it proves | Creates false confidence | Evidence/artifact pointers and explicit labels. |
| A write tool with no run identity | One task can affect another | Controlled actions require matching run_id. |
| Conversational approval only | Ambiguous and non-replayable | approved:true plus lock and saved artifacts. |
| Re-implementing CLI logic in MCP | Behavior drifts between surfaces | MCP handlers reuse TailTrail modules/scripts. |
| Returning giant source or logs by default | Burns context and hides key facts | Focused artifacts; Token Harness exactness rules. |
| Adding every harness as a tool | Tool discovery becomes unusable | Add tools only when contracts and evidence are stable. |

---

## 13. Configure and verify locally

First verify the server contract from the TailTrail checkout:

~~~powershell
py -3 scripts/tailtrail.py mcp doctor
py -3 scripts/tailtrail.py mcp tools
~~~

Use doctor before adding the server to a host configuration. It verifies tool
registry, schema shape, handler coverage, and allowlist ordering.

A generic host configuration looks like:

~~~json
{
  "mcpServers": {
    "tailtrail": {
      "command": "py",
      "args": ["-3", "D:/PD/tailr-main/tailtrail/scripts/mcp-server.py", "serve"]
    }
  }
}
~~~

Host configuration locations vary. The important part is that the host starts
the same local server command and that the command uses a working Python
launcher. On Windows, TailTrail documents py -3 because bare python can resolve
to an unavailable Microsoft Store alias.

---

## 14. Debugging MCP systematically

~~~mermaid
flowchart TD
    A["Is Python available?"] --> B["Does mcp doctor pass?"]
    B --> C["Does host configuration point to mcp-server.py serve?"]
    C --> D["Does tools/list show TailTrail tools?"]
    D --> E["Does one read-only call work?"]
    E --> F["Does run ID and root point to intended project?"]
    F --> G["Only then inspect approval / control / artifact issues"]
~~~

Useful distinctions:

- **Server will not start:** Python path, script path, or host configuration is
  wrong.
- **Tools do not appear:** host did not complete initialization or connected to
  a different server.
- **Read-only tool fails:** root path, run ID, or expected artifact is missing.
- **Controlled tool refuses to run:** this is often correct—the exact Planning
  Lock may still be awaiting approval.
- **A tool returns no evidence:** distinguish absent artifact from a failed
  check. Do not call absence a pass.

For direct protocol experimentation, use a dedicated test client or the host's
MCP inspector. Do not type ordinary log output into the server's standard input
stream; it expects JSON-RPC messages.

---

## 15. MCP, CLI, and instructions: when to use each

| Need | Best surface |
| --- | --- |
| A human wants to run TailTrail manually | CLI: tailtrail start, tailtrail planning activate, and related commands. |
| A host needs a structured read of an artifact | MCP read-only tool. |
| A host needs a guarded action with an auditable contract | MCP controlled tool, after approval. |
| A host has no MCP support | TailTrail instructions plus CLI fallback. |
| A developer needs architecture detail | tailtrail-mcp.md and this guide. |

The CLI is not a lesser fallback. It remains the portable, debuggable base
surface. MCP makes the same underlying capabilities easier for an AI host to
discover and call consistently.

---

## 16. Advanced direction: where MCP can grow

TailTrail should add MCP capability slowly and only after underlying artifact
contracts are reliable. Good future additions include:

- read-only projections for stable harness artifacts;
- a workflow dashboard with per-harness status;
- proposal tools that return requirements, scope, unknowns, and confidence but
  never auto-approve them;
- controlled execution only for policy-approved, repository-native checks;
- a local UI that reads the same artifact protocol instead of inventing state.

TailTrail should avoid by default:

- an autonomous run_everything tool;
- generic cloud or Kubernetes execution;
- automatic deployment or Git push;
- live model evaluation by default;
- tools that hide several material decisions behind one “smart” action;
- claims of saved tokens, quality, or performance without measurements.

The standard for a new TailTrail MCP tool is:

~~~text
Clear purpose + typed input + narrow authority + reusable implementation
+ evidence-bearing output + focused tests + documented limits
~~~

That is how MCP supports TailTrail's larger goal: not simply making an agent
able to act, but making its decisions, evidence, and boundaries visible enough
to trust.

---

## 17. File-by-file TailTrail MCP implementation map

This section is the practical map to use when explaining TailTrail in an
interview. The key message is that TailTrail is not one large MCP file. It is a
thin protocol layer over small, testable workflow modules and shared artifacts.

### Core entry points and contracts

| File | Purpose | Why it exists | How it is used |
| --- | --- | --- | --- |
| **scripts/mcp-server.py** | The actual local MCP server. It declares tools, schemas, handlers, safety checks, and the stdio JSON-RPC loop. | Keeps the MCP boundary explicit, local, and testable. | A host launches it with the serve action; it handles initialize, tools/list, and tools/call. |
| **scripts/tailtrail.py** | The human-facing TailTrail CLI router. Its mcp() function delegates serve, tools, and doctor to the server. | Makes MCP usable through the same portable TailTrail command surface as every other feature. | Developer runs py -3 scripts/tailtrail.py mcp doctor or mcp tools. |
| **MCP-SERVER.md** | Installation, tool contract, safety boundary, and host-configuration guide. | Separates operational setup from source code. | A developer uses it to configure a Codex, Claude, or IDE MCP client. |
| **tailtrail-mcp.md** | The detailed architecture and staged design document. | Records decisions about tool families, contracts, registry integration, and deliberate non-goals. | Read when changing MCP architecture or proposing a new tool family. |
| **tailtrail-mcp-learning-guide.md** | This interview and learning guide. | Explains what the architecture means in plain language with examples. | Use to prepare interview narratives and understand the request flow. |

### Workflow state and evidence modules

| File | Purpose | Why it exists | MCP relationship |
| --- | --- | --- | --- |
| **scripts/task-start.py** | Produces the Navigator-based Start Report and selects the applicable TailTrail workflow. | Planning must be visible before an agent edits code. | tailtrail_start invokes it so a persisted lock and the report are created together. |
| **scripts/planning-lock.py** | Creates, shows, approves, and activates Planning Locks. Persists the saved Start Report. | Separates “plan the work” from “permission to perform managed work.” | planning_lock_show, planning_lock_start, planning_lock_approve, and tailtrail_start depend on it. |
| **scripts/change-intent-anchor.py** | Drafts and approves immutable requirement anchors. | Requirement IDs, preservation rules, and acceptance criteria must not change silently during implementation. | anchor_show exposes approved-v1.json through MCP. |
| **scripts/run-ledger.py** | Maintains per-run local event history and run-directory layout. | Every tool needs one run identity and replayable evidence pointers. | ledger_state reads the run projection; many other tools resolve artifacts through the same layout. |
| **scripts/harness-checkpoint.py** | Records checkpoint-specific observed state, validation results, changed file fingerprints, and drift. | “Agent says done” is not enough; actual evidence must be recorded separately from approved intent. | harness_checkpoint_show exposes the latest or requested checkpoint. |
| **scripts/completion-review.py** and **scripts/completion-report.py** | Determine whether evidence is sufficient and create the final handoff summary. | A delivery needs one clear conclusion, including unresolved gaps. | completion_feedback_show and completion_report_show provide read-only inspection. |

### Computational lenses and support modules

| File | Purpose | Why it exists | MCP relationship |
| --- | --- | --- | --- |
| **scripts/navigator.py** and **scripts/navigator_core.py** | Determine task type, likely impact, selected TailTrail features, and planning guidance. | Hosts need a deterministic, explainable first decision instead of generic advice. | navigator_plan reads this decision without implementation. |
| **scripts/architecture-fitness.py** | Assesses expected paths, callers, contracts, and scope against the approved anchor. | Passing a focused unit test can still miss a service caller or change the wrong layer. | architecture_assessment_show reads its latest saved assessment. |
| **scripts/maintainability-harness.py** | Assesses unnecessary abstraction, duplicate logic, test-chasing, and scope creep. | Correct code can still be unnecessarily hard to maintain. | maintainability_assessment_show reads its latest saved assessment. |
| **scripts/behavior-harness.py** | Connects declared user/API scenarios to receipt evidence. | Unit tests alone do not prove a user-facing flow works. | Its artifacts can be added as read-only projections when the contract is stable. |
| **scripts/context-continuity.py** | Renders compact requirement reminders from anchor, checkpoint, feedback, and preservation evidence. | Prevents repeated mistakes across correction loops without reloading every artifact. | context_continuity_show and context_continuity_render expose saved or previewed packets. |
| **scripts/guardrail-check.py** | Checks a supplied diff or safe staged diff for TailTrail guardrail findings. | Turns important safety and scope rules into deterministic evidence. | guardrail_check wraps this controlled read-only analysis. |
| **scripts/code-graph-mapper.py** and related graph helpers | Produce local dependency/read-order guidance. | Multi-file changes need caller/test discovery before editing. | graph_map exposes a lightweight mapping path and avoids refreshing heavy caches by default. |

### Controlled execution and recovery modules

| File | Purpose | Why it exists | MCP relationship |
| --- | --- | --- | --- |
| **scripts/harness-controls.py** | Runs repository-defined validation controls and writes receipts. | Agents should not receive an arbitrary command runner. | harness_control_check accepts a safe relative control definition, then gates execution on approval and the run lock. |
| **scripts/task-recovery-boundary.py** and **scripts/task-recovery.py** | Capture task ownership, Git readiness, and safe recovery evidence. | A failed task must not roll back unrelated uncommitted work. | git_readiness and recovery_boundary_show expose no-write recovery facts. |
| **scripts/recovery-reconcile.py** and **scripts/recovery-diagnostician.py** | Classify overlaps and prepare bounded reconciliation/replan evidence. | A conflict needs evidence-based handling, not blind destructive reversal. | recovery_reconciliation_show exposes the latest classification without applying it. |
| **scripts/evaluation-harness.py** and **scripts/evaluation-dataset.py** | Evaluate TailTrail behavior using saved deterministic fixtures. | Product claims should be measured against repeatable scenarios, not invented from a demo. | eval_scenario_list and eval_scenario_report read committed evaluation evidence only. |

### Installation, registry, and verification files

| File | Purpose | Why it exists | How it is used |
| --- | --- | --- | --- |
| **scripts/install-local.py** | Installs the TailTrail pack into a target project and chooses a profile/surface. | The MCP server and host instructions must travel with the installed pack. | Ensures a project can receive the required docs and server script. |
| **scripts/install-copilot.py** | Creates Copilot-specific instructions and prompt assets. | Different hosts need different entry points even when workflow state is shared. | Gives Copilot users the TailTrail Start behavior and MCP-compatible assets. |
| **scripts/install_surfaces.py** | Defines installation file sets and host surfaces. | Keeps installer behavior declarative rather than duplicated in each installer. | Controls which MCP documentation and scripts are included. |
| **scripts/tailtrail-registry.py** and **tailtrail-registry.json** | Project capability inventory and validation projection. | A growing product needs an inspectable source of feature/tool ownership. | MCP tests compare tool expectations to the registry projection. |
| **tests/test_mcp_server.py** | Focused contract tests for the MCP server. | Tool names, order, schemas, approval boundaries, and stdio behavior can drift easily. | Verifies the server without needing a real AI host. |
| **scripts/check-tailtrail.py** | Pack/release integrity checks. | An installer should not ship references to missing required files. | Includes MCP server/documentation presence in distribution verification. |

### The end-to-end call chain

For an interviewer, explain this path in order:

~~~text
1. A host discovers tool schemas from scripts/mcp-server.py.
2. It calls tailtrail_start for a user-requested task.
3. mcp-server.py delegates to task-start.py.
4. task-start.py asks Navigator for a plan and calls planning-lock.py.
5. planning-lock.py creates .tailtrail run state and saves the exact Start Report.
6. User approval calls planning_lock_approve.
7. planning-lock.py activates the saved plan; change-intent-anchor.py creates approved-v1.json when required.
8. Implementation and selected deterministic controls run only after the matching lock is approved.
9. harness-checkpoint.py records actual evidence and drift.
10. Read-only MCP tools expose anchor, checkpoint, architecture, continuity, recovery, and completion evidence to any compatible host.
~~~

This is the architectural reason MCP fits TailTrail: every host uses the same
artifact protocol instead of maintaining its own interpretation of task state.

---

## 18. Interview preparation: how to explain TailTrail MCP

### Thirty-second answer

> I built a local MCP capability layer for TailTrail, an AI-agent reliability
> platform. Instead of exposing an unsafe generic command runner, the MCP
> server exposes typed read-only and approval-gated tools for Navigator plans,
> requirement anchors, validation evidence, drift, recovery, and completion.
> The tools reuse the same Python workflow modules and local run artifacts used
> by the CLI, so Codex, Copilot, Claude, or a future UI can inspect the same
> evidence without duplicating business logic.

### Ninety-second architecture answer

> The problem I wanted to solve was that coding-agent behavior often becomes
> opaque in a multi-file task. The agent may change one file, miss a caller, or
> say the task is complete after a narrow unit test. I used MCP as the
> integration layer, not as the reasoning engine. The core TailTrail workflow
> creates a planning lock and saves the exact Start Report. After explicit user
> approval, it creates an immutable requirement anchor with stable requirement
> IDs, acceptance criteria, preservation rules, likely paths, and evidence
> expectations. Implementation evidence is captured separately in checkpoints.
>
> The MCP server is intentionally local and stdio-only. It exposes read-only
> tools for inspecting Navigator decisions, anchors, checkpoints, architecture
> findings, continuity packets, recovery state, and completion reports. For
> action, it has only narrow approval-gated tools: safe Start metadata, a
> repository-defined control runner, and a repository-safe patch path. It does
> not expose arbitrary shell, deploy, push, or generic write tools. That makes
> the tool boundary testable and auditable while still allowing multiple hosts
> to use the same TailTrail protocol.

### Interviewer question: Why MCP instead of only a CLI?

**Answer:** The CLI remains the portable foundation, but an MCP host needs
machine-readable tool discovery, typed input, structured output, and a visible
tool-call trace. MCP lets different hosts call the same TailTrail capability
instead of reinterpreting long prompt instructions. It does not replace the
CLI; both reuse the same underlying modules and artifacts.

### Interviewer question: How did you handle safety?

**Answer:** I used local stdio instead of a network listener, separate
read-only from controlled tool allowlists, JSON schemas with no extra
properties, repository-relative path validation, matching run IDs, explicit
approved:true input, and an approved Planning Lock for controlled execution.
I intentionally excluded arbitrary shell, deployment, Git push/commit, and
package-install tools. The tests also check schema, allowlist, handler, and
tool-order consistency.

### Interviewer question: What is the difference between Planning Lock and
Requirement Anchor?

**Answer:** The Planning Lock answers whether TailTrail-managed writes are
allowed for a particular task run. The Requirement Anchor records what the
user approved the system to build: requirement IDs, scope, preservation rules,
and expected proof. The lock is an authority boundary; the anchor is the
desired-state contract. Checkpoints then record the actual state separately.

### Interviewer question: Why save the Start Report?

**Answer:** It prevents approval-time re-planning. If repository state changes
after a plan is shown, re-running Navigator could silently produce a different
scope. TailTrail saves the exact Start Report and derives the approved anchor
from that saved proposal, so the user approves a stable artifact rather than a
moving conversational target.

### Interviewer question: How do you know an agent completed the task?

**Answer:** I do not trust a natural-language claim. TailTrail links each
requirement to evidence plans and records actual checkpoints with changed-path
fingerprints, control results, requirement states, and drift classification.
Architecture, behavior, maintainability, and completion harnesses add
different lenses. The final report names unresolved evidence instead of calling
an incomplete task successful.

### Interviewer question: What would you improve next?

**Answer:** I would keep the server thin, add only stable read-only artifact
projections, improve a local workflow dashboard, add more calibrated evaluation
fixtures from real multi-file tasks, and use observed metrics to tune
interventions. I would not start by adding a broad autonomous execution tool,
because that would reduce inspectability and weaken the safety model.

---

## 19. Interview vocabulary: accurate phrases to use

Use these phrases because they describe real TailTrail implementation choices:

- **Thin local MCP capability layer**
- **stdio JSON-RPC transport**
- **typed tool contracts with JSON Schema**
- **read-only and approval-gated capability tiers**
- **shared CLI/MCP business logic**
- **immutable approved-intent anchor**
- **checkpointed actual-state evidence**
- **requirement-level drift detection**
- **bounded correction and recovery evidence**
- **deterministic computational controls**
- **artifact-backed, inspectable agent workflow**

Avoid overstating:

- Do not say “MCP guarantees the agent is correct.” It does not.
- Do not say “TailTrail autonomously completes all development.” It does not.
- Do not claim exact quality or token improvements unless measured telemetry or
  evaluation results support the claim.
- Do not call every planned MCP tool implemented. Say the current server has a
  narrow implemented tool surface and the architecture document describes
  future expansion.
