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

- `navigator_plan`: returns a TailTrail Navigator plan. It does not implement, scan, or edit files.
- `start_report`: returns a compact TailTrail Start report. It does not edit files or capture learnings.
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
  Harness-result, drift, or CI event. It never runs the command it records.
- `harness_control_check`: an approval-gated controlled tool. It requires `approved: true`, an approved Planning Lock for the same `run_id`, accepts a repository-relative control file rather than a raw shell command, and records local computational evidence only.
- `source_patch_apply`: an approval-gated source-change tool. It requires `approved: true` and an approved Planning Lock for the same `run_id`; it accepts one repository-safe unified Git patch only.
- `planning_lock_start`: creates an `awaiting-approval` Planning Lock after the user explicitly asks to start TailTrail. It writes TailTrail metadata only; it does not edit project source or run project commands.
- `planning_lock_approve`: records the separate explicit approval for one Planning Lock run. For a saved `tailtrail_start` run, it also activates that exact saved Start Report and creates the required immutable requirement anchor. It does not edit project source or run project commands.
- `tailtrail_start`: the recommended atomic Start action. It creates the Planning Lock and returns the complete TailTrail Start or Debug Start Report in one call; it never implements, opens Debug Intake, or runs project commands. Optional `workflow: build|debug` and sanitized evidence-presence booleans select debug planning without transporting raw error or command content.
- `debug_reproduction_draft`: creates or revises local reproduction metadata for an approved Debug Start Plan; it grants no investigation or source-write authority.
- `debug_reproduction_approve`: requires the exact current revision, freezes the investigation anchor, and returns an investigation-only handoff; it never approves a correction or source edit.
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
- Inspection tools are read-only. Controlled computation and source patch application require both `approved: true` and an approved Planning Lock for the exact run.
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

1. The user invokes a Start entry point: `tailtrail start "<goal>"`, a host command, or MCP `tailtrail_start` with `approved: true`.
2. The atomic action creates one `awaiting-approval` Planning Lock and returns the complete Start Report with its run ID.
3. The user approves the exact Planning Lock run with `tailtrail planning activate --root . --run-id <run-id> --approved` or `planning_lock_approve` with `approved: true`. Guided-delivery and hands-free Start runs then create `anchors/approved-v1.json` from the saved Start Report.
4. The assistant calls read-only support tools only when useful.
5. The assistant implements code or runs controlled checks only after the matching lock is approved.
6. The assistant runs guardrail or review checks when appropriate.
7. As host-visible edits, commands, Harnesses, or CI outcomes occur, the
   assistant records only those factual events with `execution_evidence_record`.
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

DI-12 adds `debug_evaluation_report` and `debug_release_gate` as read-only
inspection tools. `debug_evaluation_run` requires explicit approval and saves
only a deterministic report from committed fixtures. It performs no model,
host, network, test, scanner, or project execution. The release gate remains
blocked until the existing host-runtime validator supplies genuine passing
Codex, Copilot, and Claude receipts linked to accepted complete Debug runs.
