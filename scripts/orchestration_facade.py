#!/usr/bin/env python3
"""PM-2 six-verb application façade over TailTrail's canonical services."""
from __future__ import annotations

import argparse
import importlib.util
import json
import subprocess
import sys
from pathlib import Path
from typing import Any


ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "scripts"))


def _module(name: str, filename: str) -> Any:
    spec = importlib.util.spec_from_file_location(name, ROOT / "scripts" / filename)
    loaded = importlib.util.module_from_spec(spec)
    assert spec and spec.loader
    sys.modules[name] = loaded
    spec.loader.exec_module(loaded)
    return loaded


LOCK = _module("pm2_planning_lock", "planning-lock.py")
DISCUSSION = _module("pm2_planning_discussion", "planning-discussion.py")
CLOSURE = _module("pm2_closure_close", "closure-close.py")
PRESENTATION = _module("pm3_presentation", "presentation.py")
from orchestration import run_resolution
from workflow_runtime import adapters, approvals, compiler, executor, ownership, state


ACTIVE_LOCK_STATES = {"awaiting-approval", "approved"}


def resolve_run(root: Path, run_id: str | None, *, states: set[str] | None = None) -> str:
    return run_resolution.resolve_run(root, run_id, LOCK.show, states=states)


def _workflow(root: Path, run_id: str) -> str | None:
    return run_resolution.workflow_id(root, run_id, ownership.suggested_id, ownership.binding_path)


def _next(value: dict[str, Any]) -> str:
    if value.get("state") == "awaiting-approval": return "Review the saved plan, then run `tailtrail approve --run-id <run-id>`."
    if value.get("state") == "stage-awaiting-approval": return "Run `tailtrail approve --run-id <run-id>` for the exact displayed stage."
    if value.get("state") == "stage-running": return "Execute the typed host handoff, save its result JSON, then run `tailtrail continue --run-id <run-id> --result-ref <path>`."
    if value.get("state") in {"failed", "blocked", "stale"}: return "Use the displayed correction or recovery route; the façade will not guess past failed evidence."
    if value.get("state") == "completed": return "Run `tailtrail close --run-id <run-id>` to finalize evidence and show acceptance choices."
    return "Run `tailtrail continue --run-id <run-id>` to advance the next dependency-ready control step."


def start(args: list[str]) -> int:
    command = [sys.executable, str(ROOT / "scripts" / "task-start.py"), *args]
    return subprocess.run(command, cwd=Path.cwd(), check=False).returncode


def discuss(root: Path, run_id: str | None, question: str) -> dict[str, Any]:
    selected = resolve_run(root, run_id, states={"awaiting-approval"})
    result = DISCUSSION.discuss(root.resolve(), selected, question)
    return {"type":"tailtrail-orchestration-result","verb":"discuss","run_id":selected,"state":"awaiting-approval",
            "result":result,"next_action":_next({"state":"awaiting-approval"}),
            "boundary":"Saved-plan discussion only. No source inspection, plan approval, workflow execution, or project mutation occurred."}


def _stage(root: Path, workflow_id: str) -> tuple[dict[str, Any], dict[str, Any] | None]:
    execution = executor.status(root, workflow_id)
    stage_id = execution.get("next_stage_id")
    plan = compiler.show(root, workflow_id)
    row = next((item for item in plan["stages"] if item["stage_id"] == stage_id), None)
    return execution, row


def approve(root: Path, run_id: str | None) -> dict[str, Any]:
    selected = resolve_run(root, run_id, states=ACTIVE_LOCK_STATES)
    lock = LOCK.show(root.resolve(), selected)
    if lock["status"] == "awaiting-approval":
        activated = LOCK.activate(root.resolve(), selected, True)
        workflow_id = (activated.get("workflow_runtime") or {}).get("workflow_id")
        result = {"type":"tailtrail-orchestration-result","verb":"approve","run_id":selected,
                  "workflow_id":workflow_id,"state":"plan-approved","result":activated}
        result["next_action"] = _next({"state":"ready"}); result["boundary"] = "The exact Planning Lock was activated. No project command or source edit was executed."
        return result
    workflow_id = _workflow(root, selected)
    if not workflow_id: raise ValueError("approved run has no durable workflow; use its saved execution handoff")
    execution, stage = _stage(root, workflow_id)
    if stage is None:
        state_name = "completed" if execution.get("workflow_status") == "completed" else "blocked"
        return {"type":"tailtrail-orchestration-result","verb":"approve","run_id":selected,"workflow_id":workflow_id,
                "state":state_name,"result":execution,"next_action":_next({"state":state_name}),"boundary":"No approval was created because there is no incomplete stage."}
    action = stage["adapter_action_class"]
    operation = {"write_project":"fix-application","execute_project":"broad-test-build","scan_local":"scanner"}.get(action, "other-guarded")
    decision = approvals.decide(root.resolve(), workflow_id, stage_ids=[stage["stage_id"]], action_classes=[action],
        operation_kind=operation, operation_ref=compiler.show(root, workflow_id)["artifact"], decision="approved",
        rationale=f"Approve the exact dependency-ready `{stage['stage_id']}` stage selected by the frozen workflow graph.")
    advanced = executor.start(root.resolve(), workflow_id, stage["stage_id"], decision["record"]["approval_id"])
    workflow_status = advanced.get("workflow_status") or (advanced.get("execution") or {}).get("workflow_status")
    state_name = "completed" if workflow_status == "completed" else "blocked" if workflow_status in {"blocked","failed"} else "stage-running"
    result = {"type":"tailtrail-orchestration-result","verb":"approve","run_id":selected,"workflow_id":workflow_id,
              "state":state_name,"stage_id":stage["stage_id"],"approval":decision["record"],"result":advanced}
    result["next_action"] = _next({"state":state_name}); result["boundary"] = "Approval is limited to the exact frozen stage/action class. TailTrail prepared metadata only; the host still owns factual execution."
    return result


def continue_run(root: Path, run_id: str | None, result_ref: str | None) -> dict[str, Any]:
    selected = resolve_run(root, run_id, states={"approved"}); workflow_id = _workflow(root, selected)
    if not workflow_id: raise ValueError("approved run has no durable workflow to continue")
    execution, stage = _stage(root, workflow_id)
    if stage is None:
        state_name = "completed" if execution.get("workflow_status") == "completed" else execution.get("workflow_status", "blocked")
        return {"type":"tailtrail-orchestration-result","verb":"continue","run_id":selected,"workflow_id":workflow_id,"state":state_name,
                "result":execution,"next_action":_next({"state":state_name}),"boundary":"Read-only terminal status; nothing was dispatched."}
    stage_state = next(item["status"] for item in execution["stages"] if item["stage_id"] == stage["stage_id"])
    if stage_state == "running":
        if not result_ref:
            state_name = "stage-running"; result = execution
        else:
            adapters.record(root.resolve(), workflow_id, stage["stage_id"], stage["adapter_id"], result_ref)
            result = executor.finish(root.resolve(), workflow_id, stage["stage_id"])
            workflow_status = result.get("workflow_status")
            state_name = "completed" if workflow_status == "completed" else workflow_status if workflow_status in {"failed","blocked"} else "ready"
    elif stage_state == "awaiting_approval":
        state_name = "stage-awaiting-approval"; result = execution
    else:
        result = executor.start(root.resolve(), workflow_id, stage["stage_id"], None)
        state_name = "stage-awaiting-approval" if result.get("status") == "awaiting-approval" else "stage-running"
    output = {"type":"tailtrail-orchestration-result","verb":"continue","run_id":selected,"workflow_id":workflow_id,
              "state":state_name,"stage_id":stage["stage_id"],"result":result}
    output["next_action"] = _next({"state":state_name}); output["boundary"] = "Only the next dependency-ready frozen stage was considered. No host result was inferred."
    return output


def status(root: Path, run_id: str | None) -> dict[str, Any]:
    selected = resolve_run(root, run_id, states=ACTIVE_LOCK_STATES); lock = LOCK.show(root.resolve(), selected); workflow_id = _workflow(root, selected)
    if lock["status"] == "awaiting-approval": state_name = "awaiting-approval"; workflow = None
    elif workflow_id:
        workflow = state.show(root.resolve(), workflow_id)
        stage_id = workflow.get("current_stage"); stage_row = (workflow.get("stage_states") or {}).get(stage_id, {}) if stage_id else {}
        stage_status = stage_row.get("status")
        state_name = "stage-running" if stage_status == "running" else "stage-awaiting-approval" if stage_status == "awaiting_approval" else str(workflow.get("workflow_status", workflow.get("status", "blocked")))
    else: workflow = None; state_name = "approved-no-workflow"
    result = {"type":"tailtrail-orchestration-result","verb":"status","run_id":selected,"workflow_id":workflow_id,"state":state_name,
              "planning":{"status":lock.get("status"),"writes_allowed":lock.get("writes_allowed") is True},"workflow":workflow}
    result["next_action"] = _next({"state":state_name}); result["boundary"] = "Read-only canonical status. No plan, approval, source, evidence, or workflow state was changed."
    return result


def close(root: Path, run_id: str | None, decision: str | None, input_path: Path | None, scenarios: Path | None, ci_receipt: Path | None) -> dict[str, Any]:
    selected = resolve_run(root, run_id, states={"approved"})
    closed = CLOSURE.close(root.resolve(), selected, decision, input_path, scenarios, ci_receipt)
    return {"type":"tailtrail-orchestration-result","verb":"close","run_id":selected,"state":closed.get("state", "unknown"),
            "result":closed,"next_action":closed.get("next_action") or ("Choose one displayed acceptance option." if closed.get("state") == "awaiting-acceptance" else "Closure state recorded."),
            "boundary":"Closure uses the canonical finalizer and saved evidence. It does not infer missing proof or promote learning without acceptance."}


def render(value: dict[str, Any]) -> str:
    return PRESENTATION.render_markdown(PRESENTATION.from_orchestration(value))


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__); sub = parser.add_subparsers(dest="verb", required=True)
    start_p = sub.add_parser("start"); start_p.add_argument("args", nargs=argparse.REMAINDER)
    for verb in ("discuss", "approve", "continue", "status", "close"):
        item = sub.add_parser(verb); item.add_argument("--root", type=Path, default=Path.cwd()); item.add_argument("--run-id"); item.add_argument("--format", choices=("markdown","json"), default="markdown")
        if verb == "discuss": item.add_argument("--question", required=True)
        if verb == "continue": item.add_argument("--result-ref")
        if verb == "close":
            item.add_argument("--decision", choices=("accept-user","wait-ci","accept-ci","reopen")); item.add_argument("--input", type=Path); item.add_argument("--scenarios", type=Path); item.add_argument("--ci-receipt", type=Path)
    args = parser.parse_args()
    if args.verb == "start": return start(args.args)
    try:
        value = discuss(args.root,args.run_id,args.question) if args.verb == "discuss" else approve(args.root,args.run_id) if args.verb == "approve" else continue_run(args.root,args.run_id,args.result_ref) if args.verb == "continue" else status(args.root,args.run_id) if args.verb == "status" else close(args.root,args.run_id,args.decision,args.input,args.scenarios,args.ci_receipt)
        print(json.dumps(value,indent=2,sort_keys=True) if args.format == "json" else render(value)); return 0
    except (OSError, ValueError, KeyError, json.JSONDecodeError) as error:
        print(f"TailTrail {args.verb} error: {error}", file=sys.stderr); return 2


if __name__ == "__main__": raise SystemExit(main())
