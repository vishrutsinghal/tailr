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
- `harness_control_check`: an approval-gated controlled tool. It requires `approved: true`, an approved Planning Lock for the same `run_id`, accepts a repository-relative control file rather than a raw shell command, and records local computational evidence only.
- `source_patch_apply`: an approval-gated source-change tool. It requires `approved: true` and an approved Planning Lock for the same `run_id`; it accepts one repository-safe unified Git patch only.
- `planning_lock_start`: creates an `awaiting-approval` Planning Lock after the user explicitly asks to start TailTrail. It writes TailTrail metadata only; it does not edit project source or run project commands.
- `planning_lock_approve`: records the separate explicit approval for one Planning Lock run. It does not edit project source or run project commands.

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

1. The assistant calls `navigator_plan`.
2. The assistant shows the plan.
3. When the host has MCP configured, it calls `planning_lock_start` with the user-requested goal and `approved: true`; otherwise it runs `tailtrail start "<goal>"`. Both paths return an exact run ID.
4. The user approves the exact Planning Lock run with `tailtrail planning approve --root . --run-id <run-id> --approved` or `planning_lock_approve` with `approved: true`.
5. The assistant calls read-only support tools only when useful.
6. The assistant implements code or runs controlled checks only after the matching lock is approved.
7. The assistant runs guardrail or review checks when appropriate.
8. The user reviews final output.

For evidence or demo prompts, the assistant can call `eval_scenario_list`, then `eval_scenario_report` for the selected scenario. Scenario reports are deterministic local fixture evidence, not live model/API performance claims.

## Fallback

Non-MCP assistants should continue using TailTrail instruction files and CLI commands:

```bash
python3 scripts/tailtrail.py start "goal"
python3 scripts/tailtrail.py guard check
python3 scripts/tailtrail.py graph --changed path/to/file
```
