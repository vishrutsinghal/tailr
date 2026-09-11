# TailTrail MCP Server

TailTrail MCP support is an optional local bridge for MCP-capable assistants. It exposes inspection-first TailTrail tools plus one explicit approval-gated computational control runner, without loading large TailTrail docs.

## Commands

```bash
python3 scripts/tailtrail.py mcp tools
python3 scripts/tailtrail.py mcp doctor
python3 scripts/tailtrail.py mcp serve
```

Use `mcp tools` to inspect the available tool contract. Use `mcp doctor` before configuring an assistant. Use `mcp serve` only from an MCP client that speaks stdio JSON-RPC.

## Tools

- `navigator_plan`: returns a TailTrail Navigator plan and the canonical v2
  `scope_contract`. JSON and Markdown are rendered from the same JSON transport
  object, so their normalized decision fingerprint and path roles cannot
  diverge. It does not implement, scan, or edit files.
- `navigator_scope_proposal_record`: validates one Codex, Claude, or Copilot
  scope proposal against the exact bounded evidence packet. The schema-v2
  proposal binds the packet, scope decision, target, goal, requirement
  statements, candidate IDs, current content hashes, and evidence-edge IDs.
  Supply either the packet returned by `tailtrail_start` for validation or the
  complete canonical evidence for an in-memory refined decision. It requires
  `approved: true` but writes nothing, creates no run or Planning Lock, and
  grants no execution authority. Invented paths, missing edges, changed hashes,
  unsupported roles, incomplete requirement coverage, additional fields, and
  attempted authority escalation are rejected categorically.
- `intent_resolve`: resolves loose user words to a versioned typed TailTrail
  operation recommendation. It is read-only and never creates a run, infers
  approval, executes work, or grants authority. Supply `active_state` only for
  stateful follow-ups such as discussion, status, approval, continue, or close.
- `tailtrail_session_status`: reads the common conversation attachment, exact
  run ID, generation, and last safe logical point. It cannot attach a run or
  grant authority.
- `tailtrail_stop`: requires `confirmed: true` for the explicit user request,
  then detaches routing while preserving the canonical run. It may pause the
  local workflow and expire bounded session authority, but never rejects,
  cancels, deletes, executes, or closes the run.
- `tailtrail_resume`: requires one exact `run_id`, validates attachment and
  target freshness, and reattaches without approving or advancing work.
- `start_report`: returns a non-persisted TailTrail Start report and the same
  canonical v2 scope contract. It does not edit files, create authority, or
  capture learnings.
- `guardrail_check`: runs deterministic guardrail checking on a provided diff or safe staged diff input and returns structured findings.
- `graph_map`: returns Code Review Graph Lite read-order guidance. It does not refresh heavy graph caches.
- `install_status`: reads `.tailtrail-install.json` when present and reports Core, Extended, or unknown status.
- `eval_scenario_list`: lists committed Evaluation Harness scenarios.
- `eval_scenario_report`: returns a deterministic scenario report from committed fixtures. It does not write result files.
- `adoption_validation_report`: returns the PM-7 usability coverage, friction
  metrics, safety gates, and repeated-evidence recommendations. It is read-only,
  records no participants, and never changes wording or defaults.
- `ledger_state`, `anchor_show`, `harness_checkpoint_show`, `completion_feedback_show`, and `planning_lock_show`: inspect the local run trail and the approval state for a Start run.
- `profile_view`, `validation_receipt_show`, and `release_confidence_show`: inspect declared testing tiers, requirement-linked proof, and the latest receipt-based release-confidence view.
- `git_readiness`, `recovery_boundary_show`, and `recovery_reconciliation_show`: inspect Phase 4 Mode A readiness, boundary state, and the latest no-write conflict classification.
- `architecture_assessment_show` and `maintainability_assessment_show`: inspect the latest requirement-linked architecture or maintainability assessment.
- `planning_question_context_show`: reads the saved Question Orchestrator input contract for one run, including active AIDLC authority, requirement IDs, labelled known facts, unresolved decisions, and the no-source-body boundary. It cannot generate or revise questions.
- `aidlc_official_status`, `aidlc_official_bridge_show`, `aidlc_official_state_show`, and `aidlc_official_sanitize_validate`: inspect pinned-pack compatibility, immutable bridge identity, canonical ownership, and the fail-closed reference boundary.
- `aidlc_official_session_status`: projects the verified Phase I runtime attachment, current official stage, and append-only transition count. It is read-only and cannot attach a session, import a receipt, or execute the official pack.
- `host_conformance_report`: reports Phase J instruction conformance and
  receipt-backed runtime conformance separately for Codex, Copilot, and Claude.
  Missing receipts remain `not-validated`; this read-only tool cannot prepare a
  bundle, record evidence, control a host, or fabricate a pass.
- `execution_evidence_show`: reads the append-only requirement-linked execution
  evidence stream for one run. It is read-only and does not reinterpret chat
  text as proof.
- `execution_evidence_record`: the controlled evidence-ingestion tool. It
  requires `approved: true` and an approved Planning Lock for the exact run,
  then validates and records one host-supplied source-edit, command-result,
  Harness-result, drift, or artifact-backed CI event. It never runs the command
  it records; a label-only result remains unverified.
- `execution_evidence_run`: executes one exact validation command and tier from
  the approved anchor, then captures exit code, duration, environment, scenario
  IDs, hashes, and bounded redacted stdout/stderr as trusted evidence. It cannot
  execute an unapproved command or broaden the approved boundary.
- `harness_control_check`: an approval-gated controlled tool. It requires `approved: true`, an approved Planning Lock for the same `run_id`, accepts a repository-relative control file rather than a raw shell command, and records local computational evidence only.
- `source_patch_apply`: an approval-gated source-change tool. It requires `approved: true` and an approved Planning Lock for the same `run_id`; it accepts one repository-safe unified Git patch only.
- `planning_lock_start`: creates an `awaiting-approval` Planning Lock after the user explicitly asks to start TailTrail. It writes TailTrail metadata only; it does not edit project source or run project commands.
- `planning_lock_approve`: records the separate explicit approval for one Planning Lock run. For a saved `tailtrail_start` run, it also activates that exact saved Start Report and creates the required immutable requirement anchor. It does not edit project source or run project commands.
- `tailtrail_start`: the recommended atomic Start action. It computes Start
  once as JSON, creates the Planning Lock, returns the requested complete JSON
  or Markdown Start/Debug Start Report, and exposes the exact canonical v2
  `scope_contract` alongside it. CLI, MCP, Codex, Copilot, and Claude retain
  the same normalized decision fingerprint and owner/inspection/proof/excluded
  roles. The tool never implements, strengthens unresolved scope, opens Debug
  Intake, or runs project commands. Optional `workflow: build|debug` and
  sanitized evidence-presence booleans select debug planning without
  transporting raw error or command content. For Debug Start, the active host
  supplies `debug_diagnosis` after bounded read-only inspection of current
  source slices, callers, tests, configuration, and supplied artifacts.
  TailTrail validates the exact goal/root/host, current hashes, public evidence,
  test cases, and advisory-only authority, then calculates the working-set
  estimate from current line ranges. Missing diagnosis from an active host
  creates no Planning Lock. The contract cannot claim reproduction, root cause,
  execution, or approval. For ordinary Lite/Off Build Start,
  the optional `requirement_interpretation` object carries the active host's
  exact-goal-bound typed clauses and requirements. `requirement_artifacts`
  supplies explicitly referenced local requirement files. TailTrail reads them
  only as bounded UTF-8 planning inputs, returns hash-bound inspection metadata,
  and requires `source_input_id` clauses plus matching `artifact_evidence`.
  TailTrail validates host
  identity, source grounding, clause roles, reverse outcome/constraint coverage,
  exact named-target retention, requirement linkage, literals, semantic intent
  terms, and the no-private-reasoning boundary. The typed sufficiency result
  exposes outcome, constraint, scope, named-target, and open-decision dimensions.
  Question clauses remain material decisions and stop
  before Planning Lock, and the object never grants scope or execution authority.
  For agent-host Standard/Full Build Start, the first response exposes
  `official_requirement_authority` with the verified mode, Requirements stage,
  and exact governing references. The host must consume those rules and return
  `authority: official-ai-dlc-pack` with identical `authority_references`
  before scope discovery. TailTrail preserves those requirement rows, maps
  local scope without rewriting them, and records their approval when the
  Start Plan is explicitly approved.
  The response exposes `requirement_route` independently from `scope_contract`.
  Hosts must consume this typed projection directly: `deferred` forbids graph
  work, owner questions, and Planning Lock creation, while `eligible` permits
  bounded scope investigation. Requirement intake takes precedence even when
  scope investigation is disabled or unavailable.
  MCP validates the combined transport before returning it. A deferred route
  combined with a scope contract, host reasoning packet, or created run is a
  conformance failure, not a state the host may reinterpret. Scope state without
  a typed requirement route is rejected for the same reason.
  When deterministic investigation leaves two or more strong hash-bound owner
  alternatives, the first response creates no run and exposes
  `host_reasoning_packet`. The active Codex, Copilot, or Claude host may validate
  one public-evidence proposal and resubmit the same Start with `host` and
  `host_scope_proposal`. Start reruns investigation and accepts the proposal
  only when every binding is still exact; rejected or stale proposals remain
  blocked with `run_created: false`. A successful refinement may create the
  normal awaiting-approval Planning Lock, but never implementation authority.
- `debug_reproduction_draft`: creates or revises local reproduction metadata for an approved Debug Start Plan; it grants no investigation or source-write authority.
- `debug_reproduction_approve`: requires the exact current revision, freezes the investigation anchor, and returns an investigation-only handoff; it never approves a correction or source edit.
- `debug_reproduction_attempt_show`: reads factual before/after attempt state and any sanitized missing-input request; approval alone is never proof.
- `debug_reproduction_attempt_record`: records a typed attempt only when linked to a real requirement-owned `command-result` evidence fingerprint; it never runs the command.
- `debug_reproduction_reopen`: after `awaiting-reproduction-input`, creates the next separately approvable revision while preserving the same run, requirement UID, earlier approved revisions, and attempt evidence.
- `debug_orientation_show`: reads the saved D-03 project orientation, graph
  freshness, evidence labels, and refresh proposal without creating state.
- `debug_orientation_create`: requires `approved: true` and the native approved
  debug handoff, then versions a local metadata projection over the existing
  Code Graph cache. It never refreshes the graph, reads source bodies, runs
  project commands, or advances DWR by itself.
- `debug_experiment_record`: requires `approved: true`, an open hypothesis, an
  explicit expected signal, and a real requirement-linked Execution Evidence
  fingerprint. DI-6 binds the result to the failure fingerprint, rejects an
  identical unchanged probe, records precise outcome classes, and blocks at
  the three-experiment cycle limit. It records metadata only and never runs the
  experiment or approves Recovery/Replan.
- `debug_correction_propose`: creates the bounded DI-7 file/symbol,
  preservation, architecture, validation, behaviour, and recovery contract
  from a proven hypothesis. It writes metadata only.
- `debug_correction_approve`: freezes that exact contract and records only D-08
  `write_project` authority. Unresolved assumptions or missing scope block it.
- `debug_correction_scope_check`: compares host-reported changed paths with the
  approved correction and records requirement-linked drift or in-scope
  evidence; it never edits, reverts, stages, tests, or commits files.
- `debug_harness_convergence_show`: read-only selected-control preview or saved
  DI-8 per-requirement Harness table.
- `debug_harness_convergence_finalize`: approval-gated typed convergence. It
  may invoke existing deterministic local Architecture/Maintainability
  assessments and otherwise consumes saved evidence; it does not run project
  commands, source changes, recovery, Git, providers, publish, deploy, or
  closure acceptance.

## Safety Boundaries

- Local stdio only.
- Inspection tools are read-only. Controlled computation and source patch application require both `approved: true` and an approved Planning Lock for the exact run. The pre-lock `navigator_scope_proposal_record` exception requires explicit approval but is validation-only, writes nothing, and grants no authority.
- No arbitrary shell command tool; the controlled runner uses existing repository-native control definitions.
- No deploy, push, commit, package-install, arbitrary shell, or arbitrary write-result tool.
- No network listener.
- No telemetry upload.
- No background service.
- No automatic full development chain.

MCP improves access and consistency. It does not replace user approval. Implementation, scanner execution, fixes, broad reads, and learning capture still need the normal TailTrail approval workflow.

## Example MCP Configuration

Exact configuration differs by host. The command should point at this checkout or installed pack:

```json
{
  "mcpServers": {
    "tailtrail": {
      "command": "python3",
      "args": ["/path/to/tailtrail/scripts/mcp-server.py", "serve"]
    }
  }
}
```

For a managed pack inside a project:

```json
{
  "mcpServers": {
    "tailtrail": {
      "command": "python3",
      "args": ["tailtrail/scripts/mcp-server.py", "serve"]
    }
  }
}
```

## Recommended Flow

1. The user invokes a Start entry point: natural TailTrail task language,
   `tailtrail start "<goal>"`, a host command, or MCP `tailtrail_start` with
   `approved: true`. A client may first call read-only `intent_resolve`, but it
   must separately invoke and authorize the recommended operation.
2. The atomic action creates one `awaiting-approval` Planning Lock and returns the complete Start Report with its run ID.
   Before scope discovery, TailTrail freezes one canonical requirement set and
   carries its fingerprint unchanged through the scope query, plan, optional
   hands-free sequencing, and approval anchor. MCP clients must not regenerate
   or rewrite those rows.
3. The user approves the exact Planning Lock run with `tailtrail planning activate --root . --run-id <run-id> --approved` or `planning_lock_approve` with `approved: true`. Guided-delivery and hands-free Start runs then create `anchors/approved-v1.json` from the saved Start Report.
4. The assistant calls read-only support tools only when useful.
5. The assistant implements code or runs controlled checks only after the matching lock is approved.
6. The assistant runs guardrail or review checks when appropriate.
7. The assistant records source edits, runs every approved local validation
   command with `execution_evidence_run`, and uses `execution_evidence_record`
   only for external artifact-backed CI/Harness facts.
8. The assistant runs `tailtrail closure finalize --root . --run-id <run-id>`;
   the finalizer derives selected-Harness evidence from the saved stream.
9. The user reviews the real Completion Report.

For evidence or demo prompts, the assistant can call `eval_scenario_list`, then `eval_scenario_report` for the selected scenario. Scenario reports are deterministic local fixture evidence, not live model/API performance claims.

## Fallback

Non-MCP assistants should continue using TailTrail instruction files and CLI commands:

```bash
python3 scripts/tailtrail.py start "goal"
python3 scripts/tailtrail.py guard check
python3 scripts/tailtrail.py graph --changed path/to/file
```
## Debug Harness lifecycle (DI-11)

The read-only `debug_preflight` tool creates the hard-capped, fingerprinted
source/test/configuration/artifact packet consumed by one host reasoning pass
before `tailtrail_start`. It creates no run and executes no project command.
An unresolved local helper is returned as a typed partial trace with correction
scope blocked. The MCP handoff still succeeds when an artifact or bounded
reproduction route exists; `request-more-evidence` is valid only when neither
reproduction nor necessary external context is available.

The MCP server exposes the complete Debug control plane while leaving project
execution with the host. Read-only tools show intake, reproduction,
orientation, hypotheses, correction, governance, convergence, Debug closure,
the shared DWR current/resume/replay state, and the unified Completion Report.

Controlled tools cover reproduction revision/approval, hypothesis
add/reprioritize, experiment propose/record, root-cause proof, correction,
convergence, and canonical closure. They require `approved: true`, write only
TailTrail metadata/evidence, preserve the same run/workflow/requirement IDs,
and do not run arbitrary commands, edit source, accept delivery, commit, push,
or deploy. `debug_closure_finalize` delegates to the canonical Closure
Finalizer; use `completion_report_show` to read its unified result.

For traced Debug runs, `debug_root_cause_prove` binds the proven fault layer to
exact behavior-graph nodes. The correction packet then selects composition,
renderer, final-output, or cross-layer proof from those nodes and blocks
approval if any required boundary lacks a focused test. Debug convergence
requires a passing requirement-linked receipt for each exact selected command.

`debug_reproduction_show`, `debug_reproduction_draft`,
`debug_reproduction_revise`, and `debug_reproduction_approve` also return a
derived `next_actions` object. It is the same state-aware contract rendered by
the CLI: action IDs, compact user prompts, availability, effects, the staged
route to a code fix, and the authority boundary. It is not persisted and does
not grant or advance authority; MCP clients must present it without promoting
blocked or future actions.

DI-12 adds `debug_evaluation_report` and `debug_release_gate` as read-only
inspection tools. `debug_evaluation_run` requires explicit approval and saves
only a deterministic report from committed fixtures. It performs no model,
host, network, test, scanner, or project execution. The release gate remains
blocked until the existing host-runtime validator supplies genuine passing
Codex, Copilot, and Claude receipts linked to accepted complete Debug runs.

## FSR-6 scope assurance parity

Navigator scope calibration executes CLI Start scenarios and verifies the MCP
decision path through the existing real-run release proof. The release gate
requires identical CLI/MCP scope fingerprints, zero unsafe run artifacts on
unresolved, conflicting, or rollback paths, passing host-adapter conformance,
and a passing executable false-stop calibration. MCP cannot override a failed
threshold, manufacture a receipt, or create a Planning Lock for a stopped case.

## FSR-7 artifact execution boundary

`eval scope installed-release-proof` is intentionally a local CLI release
operation, not an MCP tool. It creates an isolated virtual environment,
installs a caller-supplied wheel, and launches packaged host entrypoints. MCP
cannot silently install or execute release artifacts. MCP parity remains in
the preceding scope release proof; FSR-7 adds installed Codex behavior and
installed Copilot/Claude packaging conformance without broadening authority.
