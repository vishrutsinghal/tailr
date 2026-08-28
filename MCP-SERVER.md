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
- `tailtrail_start`: the recommended atomic Start action. It creates the Planning Lock and returns the complete TailTrail Start Report in one call; it never implements or runs project commands.

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
