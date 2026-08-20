"""DWR-4 proven small-change vertical path.

This adapter connects existing TailTrail controls in one narrow sequence:
approved small change -> saved focused validation -> completion review and
fulfilment -> canonical completion report -> DWR-3 receipt.  It does not edit
source, execute a command, retry failed work, or broaden to delivery/risk
templates. Host-visible execution facts must already be recorded.
"""
from __future__ import annotations

import importlib.util
from pathlib import Path
from typing import Any

from workflow_runtime import compiler, evidence, ownership


def _load(name: str, filename: str) -> Any:
    scripts = Path(__file__).resolve().parents[1]
    spec = importlib.util.spec_from_file_location(name, scripts / filename)
    module = importlib.util.module_from_spec(spec)
    assert spec and spec.loader
    spec.loader.exec_module(module)
    return module


EXECUTION = _load("dwr4_execution_evidence", "execution-evidence.py")
RECORDER = _load("dwr4_closure_recorder", "closure-recorder.py")
FINALIZER = _load("dwr4_closure_finalizer", "closure-finalizer.py")


VERTICAL_STAGES = ("implement", "focused-test", "review", "fulfilment")


def _context(root: Path, workflow_id: str) -> tuple[dict[str, Any], dict[str, Any]]:
    binding = ownership.show(root.resolve(), workflow_id)
    plan = compiler.show(root.resolve(), workflow_id)
    if plan.get("template_id") != "small-change":
        raise ValueError("DWR-4 supports only the compiled small-change template; delivery, risk, review-only, and discovery workflows remain deferred")
    stage_ids = {str(item.get("stage_id")) for item in plan.get("stages", [])}
    if not set(VERTICAL_STAGES) <= stage_ids:
        raise ValueError("small-change compiler plan is missing a required DWR-4 vertical stage")
    return binding, plan


def status(root: Path, workflow_id: str) -> dict[str, Any]:
    """Read readiness for the proven path without recording, finalizing, or executing."""
    root = root.resolve(); binding, plan = _context(root, workflow_id)
    events = EXECUTION.show(root, binding["tailtrail_run_id"]).get("events", [])
    source_edits = [item for item in events if item.get("kind") == "source-edit"]
    focused_passes = [item for item in events if item.get("kind") in {"command-result", "ci-receipt"} and item.get("outcome") == "pass" and item.get("tier") in {"unit", "focused"}]
    missing: list[str] = []
    if not source_edits:
        missing.append("saved source-edit evidence")
    if not focused_passes:
        missing.append("saved passing focused/unit validation receipt")
    collected = evidence.show(root, workflow_id, missing_ok=True)
    return {
        "type": "tailtrail-workflow-proven-vertical-status", "workflow_id": workflow_id,
        "tailtrail_run_id": binding["tailtrail_run_id"], "template_id": plan["template_id"],
        "stages": list(VERTICAL_STAGES), "status": "ready-to-finalize" if not missing else "evidence-needed",
        "missing": missing, "evidence": {"source_edit_events": len(source_edits), "focused_pass_receipts": len(focused_passes), "workflow_evidence": collected.get("artifact") if collected else None},
        "next": "Run `tailtrail workflow vertical finalize` after host execution facts are recorded." if not missing else "Record only factual host source-edit and focused validation results through execution-evidence first.",
        "boundary": "Read-only DWR-4 readiness. It does not execute implementation, tests, review, fulfilment, source edits, retries, or recovery.",
    }


def finalize(root: Path, workflow_id: str) -> dict[str, Any]:
    """Compose existing proof into the one DWR-4 vertical path; never execute it."""
    root = root.resolve(); ready = status(root, workflow_id)
    if ready["status"] != "ready-to-finalize":
        return {**ready, "vertical_status": "evidence-incomplete", "boundary": "DWR-4 did not create a closure record, run a command, or retry work because the required factual evidence is missing."}
    run_id = str(ready["tailtrail_run_id"])
    # Recorder builds checkpoint, requirement-completion gate, and review only
    # from prior host evidence. Finalizer adds selected assessments/report, and
    # its DWR-3 bridge writes the receipt for this already activated workflow.
    record = RECORDER.record(root, run_id=run_id)
    finalizer = FINALIZER.finalize(root, run_id)
    collected = evidence.collect(root, workflow_id)
    receipt = evidence.close(root, workflow_id)
    complete = finalizer.get("overall_status") == "complete" and receipt.get("state") == "completed"
    return {
        "type": "tailtrail-workflow-proven-vertical", "workflow_id": workflow_id, "run_id": run_id,
        "template_id": "small-change", "stages": list(VERTICAL_STAGES),
        "vertical_status": "complete" if complete else "evidence-incomplete",
        "closure_record": record.get("record_id"), "completion_report": finalizer.get("completion_report"),
        "completion_receipt": receipt.get("artifact"), "receipt_state": receipt.get("state"),
        "workflow_evidence": collected.get("artifact"),
        "next": "No DWR-4 continuation is needed." if complete else "Use the existing bounded correction/replan path; DWR-4 does not retry or repair project work.",
        "boundary": "DWR-4 composed existing saved evidence only. No implementation, test command, scanner, Git action, recovery action, or retry was run.",
    }
