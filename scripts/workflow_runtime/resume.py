"""Derive the shortest safe Phase 6 continuation without dispatching work."""
from __future__ import annotations

import json
from pathlib import Path
from typing import Any

from workflow_runtime import compiler, context, correction, evidence, freshness, ownership, retry, storage, task_scope


def plan(root: Path, workflow_id: str) -> dict[str, Any]:
    root = root.resolve(); compiled = compiler.show(root, workflow_id); replay = storage.replay(root, workflow_id)
    if not replay["valid"]: return {"type":"tailtrail-workflow-resume-plan","workflow_id":workflow_id,"status":"blocked","reason":"journal replay is invalid","issues":replay["issues"],"boundary":"Read-only; no continuation was dispatched."}
    projection = replay["last_valid_projection"]; completion = evidence.receipt_path(root, workflow_id)
    if completion.is_file() and json.loads(completion.read_text(encoding="utf-8")).get("state") == "evidence-incomplete-accepted":
        return {"type":"tailtrail-workflow-resume-plan","workflow_id":workflow_id,"status":"needs-decision","reason":"accepted evidence-incomplete closure is not success and cannot trigger retry or correction","next_stage_id":None,"preserved_passed_stage_ids":[stage_id for stage_id,row in projection["stages"].items() if row["status"] == "passed"],"boundary":"Read-only; no retry or recovery was inferred."}
    scope = task_scope.freshness(root, workflow_id)
    if not scope["valid"]: return {"type":"tailtrail-workflow-resume-plan","workflow_id":workflow_id,"status":"blocked","reason":"canonical task scope is invalid","issues":scope["issues"],"boundary":"Read-only; no continuation was dispatched."}
    packets = correction.show(root, workflow_id); latest = packets["latest"]; stages = projection.get("stages", {}); selected = None
    for stage in compiled["stages"]:
        stage_id = stage["stage_id"]; current = stages.get(stage_id, {}).get("status", "pending"); dependencies = stage.get("prerequisites", [])
        if current in {"passed","skipped"}: continue
        if all(stages.get(item, {}).get("status") in {"passed","skipped"} for item in dependencies): selected = stage; break
    if selected is None:
        status = "complete" if projection["workflow_status"] == "completed" else "blocked"
        return {"type":"tailtrail-workflow-resume-plan","workflow_id":workflow_id,"status":status,"reason":"no dependency-ready incomplete stage exists","next_stage_id":None,"preserved_passed_stage_ids":[stage_id for stage_id,row in stages.items() if row["status"] == "passed"],"boundary":"Read-only; no continuation was dispatched."}
    stage_id = selected["stage_id"]; current = stages[stage_id]["status"]; retry_decision = retry.decide(root, workflow_id, stage_id) if current in {"failed","blocked","stale"} else None
    action = "approval-required" if current == "awaiting_approval" else "retry" if retry_decision and retry_decision["eligible"] else "recovery-replan" if latest and latest["status"] in {"recovery-replan","needs-decision"} else "bounded-correction" if current in {"failed","blocked","stale"} else "execute-stage"
    return {"type":"tailtrail-workflow-resume-plan","workflow_id":workflow_id,"status":"resume-ready" if action in {"retry","execute-stage"} else action,"next_stage_id":stage_id,"next_action":action,"stage_status":current,"retry":retry_decision,"correction_ref":latest.get("artifact") if latest else None,"preserved_passed_stage_ids":[item for item,row in stages.items() if row["status"] == "passed"],"preserved_requirement_uids":ownership.show(root, workflow_id)["requirement_uids"],"scope":scope,"checkpoint_ref":freshness.checkpoint_path(root, workflow_id).relative_to(root).as_posix() if freshness.checkpoint_path(root, workflow_id).is_file() else None,"context":context.resume_summary(root, workflow_id),"boundary":"Shortest dependency-ready continuation only. Passed unaffected stages remain preserved; resume uses compact context references rather than full history; no capability, retry, correction, or recovery was executed."}
