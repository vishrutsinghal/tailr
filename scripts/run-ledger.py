#!/usr/bin/env python3
"""Local, append-only run state for the Phase 1 requirement foundation."""

from __future__ import annotations

import argparse
import hashlib
import json
import os
import tempfile
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

try:
    import fcntl  # type: ignore
except ImportError:  # Windows uses msvcrt below.
    fcntl = None
try:
    import msvcrt  # type: ignore
except ImportError:  # POSIX uses fcntl above.
    msvcrt = None


SCHEMA_VERSION = "1"
EVENT_TYPES = {"run_created", "planning_lock_created", "planning_lock_approved", "planning_activated", "planning_discussion_recorded", "planning_investigation_recorded", "target_resolution_recorded", "start_report_saved", "anchor_drafted", "anchor_approved", "anchor_invalidated", "proposal_rejected", "aidlc_requirements_requested", "aidlc_requirements_answered", "aidlc_requirements_approved", "aidlc_recommendations_accepted", "official_aidlc_bridge_created", "official_aidlc_bridge_activated", "official_aidlc_requirements_requested", "official_aidlc_requirements_answered", "official_aidlc_requirements_approved", "official_aidlc_revision_routed", "official_aidlc_runtime_attached", "official_aidlc_transition_imported", "official_aidlc_runtime_recovery_routed", "graph_receipt", "harness_plan", "harness_check", "harness_checkpoint", "completion_review", "completion_report_created", "closure_recorded", "closure_finalized", "closure_correction_routed", "closure_positive_learning_captured", "closure_evaluation_calibrated", "evaluation_calibrated", "harness_feedback", "validation_receipt", "higher_tier_executed", "completion_gate", "release_confidence_assessed", "recovery_boundary_created", "recovery_requirement_activated", "recovery_requirement_checkpointed", "recovery_planned", "recovery_applied", "recovery_reconciled", "mode_b_captured", "mode_b_sealed", "mode_b_planned", "mode_b_applied", "recovery_diagnosed", "program_initialized", "program_amended", "program_checkpointed", "program_orchestrated", "program_correction_recorded", "architecture_assessed", "behavior_assessed", "maintainability_baseline_captured", "maintainability_assessed", "requirement_impact_mapped", "harness_convergence_assessed", "harness_template_selected", "minimum_tier_selected", "ci_evidence_ingested", "flaky_test_observed", "journey_mapped", "contract_parsed", "environment_lifecycle_assessed", "deployment_safety_planned", "release_policy_evaluated", "agent_graph_planned", "cloud_runner_assessed", "live_evaluation_recorded", "claim_audited", "evidence_metrics_reported", "context_continuity_rendered", "context_continuity_calibrated", "context_continuity_advisory_recorded", "context_continuity_advisory_rejected", "execution_failure_intake", "execution_failure_recorded", "execution_failure_diagnosed", "execution_failure_blocked", "execution_failure_mapped", "execution_failure_correction_routed", "execution_failure_resolved"}

EVENT_TYPES.update({"debug_plan_approved", "debug_intake_recorded", "debug_reproduction_drafted", "debug_reproduction_revised", "debug_reproduction_approved", "debug_reproduction_rejected", "debug_investigation_handoff_created", "debug_orientation_recorded", "debug_hypothesis_added", "debug_hypotheses_reprioritized", "debug_experiment_proposed", "debug_experiment_recorded", "debug_investigation_blocked", "debug_replan_approved", "debug_root_cause_proven", "debug_correction_proposed", "debug_correction_approved", "debug_harness_converged", "debug_completion_report_created", "debug_closure_section_created", "debug_governance_recorded"})

EVENT_TYPES.update({"host_runtime_conformance_recorded", "spec_kit_anchor_and_slices_created", "spec_kit_slice_advanced", "spec_kit_evidence_planned", "spec_kit_evidence_recorded", "spec_kit_amendment_proposed", "spec_kit_amendment_approved", "spec_kit_recovery_planned", "spec_kit_convergence_recorded", "spec_kit_observability_recorded", "planning_revision_proposed", "planning_revision_approved", "planning_authority_routed", "planning_aidlc_mode_switch_proposed", "planning_aidlc_mode_switch_approved", "planning_aidlc_mode_switch_fell_back", "planning_feature_controls_proposed", "planning_feature_controls_approved", "question_context_prepared", "question_quality_validated", "official_aidlc_host_questions_recorded", "aidlc_question_clarified", "aidlc_question_revision_proposed", "aidlc_question_revision_recorded", "aidlc_question_revision_approved", "workflow_ownership_bound", "workflow_capability_plan_declared", "workflow_preapproval_granted", "workflow_scope_captured", "workflow_code_change_lock_acquired", "workflow_code_change_lock_released", "workflow_storage_initialized", "workflow_storage_snapshot_captured", "workflow_state_created", "workflow_state_paused", "workflow_state_resumed", "workflow_state_cancelled", "workflow_compiler_plan_created", "workflow_runtime_activated", "workflow_stage_approval_recorded", "workflow_stage_approval_expired", "workflow_evidence_collected", "workflow_freshness_updated", "workflow_completion_receipt_recorded", "execution_evidence_recorded", "workflow_adapter_prepared", "workflow_adapter_result_recorded", "workflow_template_stage_advanced", "workflow_template_completed", "workflow_operational_checkpoint_recorded", "workflow_freshness_classified", "workflow_retry_prepared", "workflow_retry_recorded", "workflow_correction_packet_created", "workflow_recovery_replan_routed", "workflow_context_recorded", "workflow_token_telemetry_recorded", "workflow_learning_candidate_linked", "workflow_evaluation_emitted", "workflow_ci_receipt_ingested", "workflow_ci_continuation_advanced", "workflow_action_denied", "workflow_retention_cleanup_completed", "workflow_release_scenario_recorded", "workflow_real_run_proof_recorded", "workflow_enterprise_adapter_activated", "workflow_enterprise_child_linked", "workflow_enterprise_lease_acquired", "workflow_enterprise_event_ingested", "workflow_enterprise_backup_verified", "workflow_enterprise_migration_applied", "workflow_enterprise_rollback_applied", "workflow_enterprise_support_bundle_exported"})


def utc_now() -> str:
    return datetime.now(timezone.utc).replace(microsecond=0).isoformat()


def state_dir(root: Path, run_id: str) -> Path:
    return root / ".tailtrail" / "runs" / run_id


def canonical(value: Any) -> str:
    return json.dumps(value, sort_keys=True, separators=(",", ":"))


def event_id(run_id: str, sequence: int, event_type: str) -> str:
    digest = hashlib.sha256(f"{run_id}:{sequence}:{event_type}".encode()).hexdigest()[:16]
    return f"evt-{sequence:04d}-{digest}"


class RunLock:
    def __init__(self, path: Path) -> None:
        self.path = path
        self.handle: Any = None

    def __enter__(self) -> None:
        self.path.parent.mkdir(parents=True, exist_ok=True)
        self.handle = self.path.open("a+", encoding="utf-8")
        if fcntl is not None:
            fcntl.flock(self.handle.fileno(), fcntl.LOCK_EX)
        elif msvcrt is not None:
            self.handle.seek(0)
            if not self.handle.read(1):
                self.handle.write("0")
                self.handle.flush()
            self.handle.seek(0)
            msvcrt.locking(self.handle.fileno(), msvcrt.LK_LOCK, 1)

    def __exit__(self, exc_type: object, exc: object, tb: object) -> None:
        if self.handle is None:
            return
        if fcntl is not None:
            fcntl.flock(self.handle.fileno(), fcntl.LOCK_UN)
        elif msvcrt is not None:
            self.handle.seek(0)
            msvcrt.locking(self.handle.fileno(), msvcrt.LK_UNLCK, 1)
        self.handle.close()


def atomic_json(path: Path, payload: dict[str, Any]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with tempfile.NamedTemporaryFile("w", encoding="utf-8", dir=path.parent, delete=False) as handle:
        json.dump(payload, handle, indent=2, sort_keys=True)
        handle.write("\n")
        temporary = Path(handle.name)
    os.replace(temporary, path)


def read_json(path: Path) -> dict[str, Any]:
    return json.loads(path.read_text(encoding="utf-8"))


def read_events(path: Path) -> list[dict[str, Any]]:
    if not path.exists():
        return []
    return [json.loads(line) for line in path.read_text(encoding="utf-8").splitlines() if line.strip()]


def validate_event(event: dict[str, Any], expected_sequence: int | None = None) -> list[str]:
    required = {"schema_version", "type", "run_id", "sequence", "event_id", "created_at", "event_type", "payload"}
    issues = [f"missing `{field}`" for field in sorted(required - set(event))]
    if event.get("schema_version") != SCHEMA_VERSION:
        issues.append("schema_version must be `1`")
    if event.get("type") != "tailtrail-run-event":
        issues.append("type must be `tailtrail-run-event`")
    if event.get("event_type") not in EVENT_TYPES:
        issues.append("event_type is not allowed")
    if expected_sequence is not None and event.get("sequence") != expected_sequence:
        issues.append("sequence is not monotonic")
    if isinstance(event.get("run_id"), str) and isinstance(event.get("sequence"), int) and isinstance(event.get("event_type"), str):
        if event.get("event_id") != event_id(event["run_id"], event["sequence"], event["event_type"]):
            issues.append("event_id does not match deterministic value")
    return issues


def init_run(root: Path, run_id: str, goal: str) -> dict[str, Any]:
    directory = state_dir(root, run_id)
    manifest_path = directory / "manifest.json"
    with RunLock(directory / ".lock"):
        if manifest_path.exists():
            raise ValueError(f"run `{run_id}` already exists")
        manifest = {"schema_version": SCHEMA_VERSION, "type": "tailtrail-run-manifest", "run_id": run_id, "goal": goal, "created_at": utc_now(), "status": "draft"}
        atomic_json(manifest_path, manifest)
    append_event(root, run_id, "run_created", {"goal": goal})
    return manifest


def append_event(root: Path, run_id: str, event_type: str, payload: dict[str, Any]) -> dict[str, Any]:
    if event_type not in EVENT_TYPES:
        raise ValueError(f"unsupported event type `{event_type}`")
    directory = state_dir(root, run_id)
    manifest_path = directory / "manifest.json"
    if not manifest_path.exists():
        raise ValueError(f"run `{run_id}` does not exist")
    with RunLock(directory / ".lock"):
        events_path = directory / "events.jsonl"
        events = read_events(events_path)
        sequence = len(events) + 1
        event = {"schema_version": SCHEMA_VERSION, "type": "tailtrail-run-event", "run_id": run_id, "sequence": sequence, "event_id": event_id(run_id, sequence, event_type), "created_at": utc_now(), "event_type": event_type, "payload": payload}
        issues = validate_event(event, sequence)
        if issues:
            raise ValueError("invalid event: " + "; ".join(issues))
        with events_path.open("a", encoding="utf-8") as handle:
            handle.write(canonical(event) + "\n")
            handle.flush()
            os.fsync(handle.fileno())
    return event


def projection(root: Path, run_id: str) -> dict[str, Any]:
    directory = state_dir(root, run_id)
    manifest = read_json(directory / "manifest.json")
    events = read_events(directory / "events.jsonl")
    approved = [event for event in events if event["event_type"] == "anchor_approved"]
    invalidated = [event for event in events if event["event_type"] == "anchor_invalidated"]
    activity = {event_type: len([event for event in events if event["event_type"] == event_type]) for event_type in sorted(EVENT_TYPES) if any(event["event_type"] == event_type for event in events)}
    return {"schema_version": SCHEMA_VERSION, "type": "tailtrail-run-projection", "run_id": run_id, "goal": manifest["goal"], "status": "invalidated" if invalidated else ("approved" if approved else "draft"), "events": len(events), "activity": activity, "approved_anchor": approved[-1]["payload"] if approved else None, "latest_invalidation": invalidated[-1]["payload"] if invalidated else None}


def parser() -> argparse.ArgumentParser:
    result = argparse.ArgumentParser(description="Manage append-only local TailTrail run events.")
    sub = result.add_subparsers(dest="command", required=True)
    init = sub.add_parser("init")
    init.add_argument("--root", type=Path, default=Path.cwd()); init.add_argument("--run-id", required=True); init.add_argument("--goal", required=True)
    append = sub.add_parser("append")
    append.add_argument("--root", type=Path, default=Path.cwd()); append.add_argument("--run-id", required=True); append.add_argument("--event-type", choices=sorted(EVENT_TYPES), required=True); append.add_argument("--payload", default="{}")
    for name in ("state", "validate"):
        item = sub.add_parser(name); item.add_argument("--root", type=Path, default=Path.cwd()); item.add_argument("--run-id", required=True)
    return result


def main() -> int:
    args = parser().parse_args(); root = args.root.resolve()
    try:
        if args.command == "init": payload = init_run(root, args.run_id, args.goal)
        elif args.command == "append": payload = append_event(root, args.run_id, args.event_type, json.loads(args.payload))
        else:
            payload = projection(root, args.run_id)
            if args.command == "validate":
                events = read_events(state_dir(root, args.run_id) / "events.jsonl")
                issues = [issue for index, event in enumerate(events, 1) for issue in validate_event(event, index)]
                payload = {"valid": not issues, "issues": issues, **payload}
                if issues: print(json.dumps(payload, indent=2, sort_keys=True)); return 1
        print(json.dumps(payload, indent=2, sort_keys=True)); return 0
    except (ValueError, OSError, json.JSONDecodeError) as error:
        print(f"Run ledger error: {error}"); return 2


if __name__ == "__main__":
    raise SystemExit(main())
