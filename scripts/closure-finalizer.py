#!/usr/bin/env python3
"""Finalize one approved TailTrail run from recorded closure evidence.

The finalizer runs only deterministic local harness assessments selected by the
approved execution handoff.  It never runs a receipt command, provisions an
environment, performs recovery, or converts missing behavioural evidence into a
pass.
"""

from __future__ import annotations

import argparse
import hashlib
import importlib.util
import json
import sys
from pathlib import Path
from typing import Any


ROOT = Path(__file__).resolve().parents[1]
if str(ROOT / "scripts") not in sys.path:
    sys.path.insert(0, str(ROOT / "scripts"))


def load(name: str, script: str) -> Any:
    spec = importlib.util.spec_from_file_location(name, ROOT / "scripts" / script)
    module = importlib.util.module_from_spec(spec)
    assert spec and spec.loader
    sys.modules[name] = module
    spec.loader.exec_module(module)
    return module


L = load("closure_finalizer_ledger", "run-ledger.py")
LOCK = load("closure_finalizer_lock", "planning_lock.py")
RECORDER = load("closure_finalizer_recorder", "closure-recorder.py")
ARCHITECTURE = load("closure_finalizer_architecture", "architecture-fitness.py")
BEHAVIOUR = load("closure_finalizer_behaviour", "behavior-harness.py")
MAINTAINABILITY = load("closure_finalizer_maintainability", "maintainability-harness.py")
REPORT = load("closure_finalizer_report", "completion-report.py")
DELIVERY = load("closure_finalizer_delivery_record", "delivery-record.py")
DEBUG_SECTION = load("closure_finalizer_debug_section", "debug-completion.py")
CORRECTION = load("closure_finalizer_correction", "closure-correction.py")
WORKFLOW_EVIDENCE = load("closure_finalizer_workflow_evidence", "workflow_runtime/evidence.py")
NAVIGATOR_GRAPH = load("closure_finalizer_navigator_graph", "navigator_graph_lifecycle.py")
REFRESH = load("closure_finalizer_refresh", "learning-refresh.py")
HARNESS = load("closure_finalizer_harness", "harness-review.py")
ANCHOR = load("closure_finalizer_anchor", "change-intent-anchor.py")
VR = load("closure_finalizer_verbose_reporting", "verbose-reporting.py")


def _resolve_command_from_registry(command_id_or_str: str, registry: dict[str, Any]) -> str:
    """Resolve command_id to actual command string for display and reporting.
    
    Supports both new format (command_id: "cmd-abc123") and old format
    (embedded command string). Returns the actual command.
    
    Args:
        command_id_or_str: Either a command ID (cmd-XXXXXX) or command string
        registry: Command registry mapping IDs to metadata
    
    Returns:
        The actual command string to display
    """
    if isinstance(command_id_or_str, str) and command_id_or_str.startswith("cmd-"):
        # New format: command_id reference
        if command_id_or_str in registry:
            return str(registry[command_id_or_str].get("command", ""))
        # Fallback if not found
        return command_id_or_str
    # Old format or string command: return as-is
    return command_id_or_str


def read(path: Path) -> dict[str, Any]:
    return json.loads(path.read_text(encoding="utf-8"))


def canonical(value: dict[str, Any]) -> str:
    return json.dumps(value, sort_keys=True, separators=(",", ":"))


def relative(root: Path, path: Path) -> str:
    try:
        return path.relative_to(root).as_posix()
    except ValueError:
        return path.name


def latest_record(root: Path, run_id: str) -> dict[str, Any]:
    records = L.state_dir(root, run_id) / "closure-records"
    candidates: list[tuple[int, int, str, dict[str, Any]]] = []
    for path in sorted(records.glob("closure-*.json")):
        item = read(path)
        if item.get("type") == "tailtrail-closure-record":
            checkpoint = str(item.get("checkpoint", ""))
            digits = "".join(character for character in Path(checkpoint).stem if character.isdigit())
            candidates.append((int(digits or 0), path.stat().st_mtime_ns, path.name, item))
    if not candidates:
        raise ValueError("no closure record exists; run `tailtrail closure record --root . --run-id <run-id>` first or provide --input")
    return max(candidates, key=lambda row: row[:3])[3]


def ensure_delivery_record(root: Path, run_id: str) -> str:
    """Generate and verify the canonical human-readable closure projection."""
    resolved_root = root.resolve()
    generated = DELIVERY.generate(resolved_root, run_id)
    relative_path = generated.get("path")
    if generated.get("type") != "tailtrail-delivery-record" or generated.get("run_id") != run_id:
        raise ValueError(f"delivery record generation returned mismatched run metadata; retry with `tailtrail closure finalize --root . --run-id {run_id}`")
    if not isinstance(relative_path, str) or not relative_path:
        raise ValueError(f"delivery record generation did not return its path; retry with `tailtrail closure finalize --root . --run-id {run_id}`")
    expected = DELIVERY.record_path(resolved_root, run_id).resolve()
    actual = (resolved_root / relative_path).resolve()
    if actual != expected or not actual.is_file():
        raise ValueError(f"delivery record is missing at `{expected.relative_to(resolved_root).as_posix()}`; retry with `tailtrail closure finalize --root . --run-id {run_id}`")
    body = actual.read_text(encoding="utf-8")
    required = [f"Run: `{run_id}`", "## Implementation", "## Closure"]
    missing = [marker for marker in required if marker not in body]
    if missing:
        raise ValueError("delivery record verification failed; missing: " + ", ".join(missing))
    return actual.relative_to(resolved_root).as_posix()


def selected_harnesses(root: Path, run_id: str) -> list[str]:
    path = L.state_dir(root, run_id) / "planning" / "execution-handoff-v1.json"
    if not path.is_file():
        debug_root = L.state_dir(root, run_id) / "debug"
        convergence = debug_root / "convergence" / "harness-convergence-v1.json"
        if (debug_root / "intake" / "debug-intake-v1.json").is_file():
            if convergence.is_file():
                return [
                    str(row.get("control")) for row in read(convergence).get("selected_controls", [])
                    if isinstance(row, dict) and row.get("control") in {
                        "Architecture Fitness Harness", "Behaviour Harness", "Maintainability Harness"
                    }
                ]
            return []
        raise ValueError("execution handoff is required; activate the approved Planning Lock first with `tailtrail planning activate --root . --run-id <run-id> --approved`")
    closure = read(path).get("closure", {})
    values = closure.get("selected_harnesses", []) if isinstance(closure, dict) else []
    return [str(value) for value in values if isinstance(value, str)]


def behavior_scenarios(root: Path, run_id: str) -> list[dict[str, Any]]:
    _, anchor = ANCHOR.latest_approved(root, run_id)
    rows: list[dict[str, Any]] = []
    for requirement in anchor.get("requirements", []):
        contract = requirement.get("behavior_contract", {})
        scenarios = contract.get("scenarios", []) if isinstance(contract, dict) else []
        if not isinstance(scenarios, list):
            continue
        for scenario in scenarios:
            if not isinstance(scenario, dict):
                continue
            rows.append({"requirement_uid": requirement["requirement_uid"], **scenario})
    return rows


def missing_behavior(root: Path, run_id: str) -> dict[str, Any]:
    """Persist a fail-closed assessment rather than inferring a user journey."""
    directory = L.state_dir(root, run_id)
    payload = {
        "schema_version": "1", "type": "tailtrail-behavior-harness", "run_id": run_id,
        "scenarios": [],
        "findings": [{
            "category": "behaviour", "classification": "needs-decision",
            "message": "Behaviour Harness was selected but no declared scenario evidence was supplied.",
            "evidence": "approved-execution-handoff",
        }],
        "complete": False, "evidence_label": "approved-execution-handoff",
        "boundary": "TailTrail does not infer a user-flow pass from unit, integration, or contract receipts.",
    }
    folder = directory / "behavior"
    artifact = folder / f"assessment-{len(list(folder.glob('assessment-*.json'))) + 1}.json"
    L.atomic_json(artifact, payload)
    L.append_event(root, run_id, "behavior_assessed", {
        "artifact": artifact.relative_to(directory).as_posix(), "findings": 1, "complete": False,
    })
    return {**payload, "run_artifact": artifact.as_posix()}


def run_behavior(root: Path, run_id: str, scenarios_path: Path | None) -> dict[str, Any]:
    directory = L.state_dir(root, run_id)
    if scenarios_path is None:
        scenarios = behavior_scenarios(root, run_id)
        if not scenarios:
            return missing_behavior(root, run_id)
        scenarios_path = directory / "finalizers" / "approved-behavior-scenarios.json"
        L.atomic_json(scenarios_path, {"scenarios": scenarios})
    try:
        closure = latest_record(root, run_id)
    except ValueError:
        return missing_behavior(root, run_id)
    candidates = [root / value for value in closure.get("receipt_artifacts", []) if isinstance(value, str)]
    receipt_payload = directory / "finalizers" / "current-validation-receipts.json"
    rows = [read(path) for path in candidates if path.is_file()]
    if not rows:
        return missing_behavior(root, run_id)
    L.atomic_json(receipt_payload, {"receipts": rows})
    return BEHAVIOUR.assess(root, run_id, scenarios_path, receipt_payload)


def higher_tier_status(root: Path, run_id: str) -> dict[str, Any]:
    directory = L.state_dir(root, run_id)
    _, anchor = ANCHOR.latest_approved(root, run_id)
    try:
        closure = latest_record(root, run_id)
    except ValueError:
        closure = {}
    receipts = [read(root / path) for path in closure.get("receipt_artifacts", []) if isinstance(path, str) and (root / path).is_file()]
    high = {"integration", "contract", "e2e", "infrastructure", "release-smoke"}
    required = [
        {"requirement_uid": row["requirement_uid"], "tier": tier}
        for row in anchor.get("requirements", [])
        for tier in (row.get("validation_contract", {}) or {}).get("tiers", [])
        if tier in high and (row.get("validation_contract", {}) or {}).get("state", "required") == "required"
    ]
    missing = [item for item in required if not any(
        item["requirement_uid"] in receipt.get("requirement_uids", [receipt.get("requirement_uid")])
        and item["tier"] in receipt.get("tiers", [receipt.get("tier")])
        and receipt.get("outcome") == "pass"
        and receipt.get("evidence_quality") in {"trusted", "attested"}
        for receipt in receipts
    )]
    return {
        "required": required, "missing": missing,
        "status": "pass" if not missing else "required-evidence-missing",
        "boundary": "The finalizer reads the current closure snapshot and accepts only trusted managed-command or attested artifact-backed higher-tier receipts.",
    }


def finalize(root: Path, run_id: str, input_path: Path | None = None, scenarios_path: Path | None = None) -> dict[str, Any]:
    root = root.resolve()
    if input_path is not None:
        resolved_input = input_path.resolve()
        if read(resolved_input).get("run_id") != run_id:
            raise ValueError("closure input run_id must match --run-id; pass `--input <artifact>` with a matching run_id to `tailtrail closure finalize --root . --run-id <run-id>`")
        closure = RECORDER.record(root, resolved_input)
    else:
        # Rebuild managed evidence when the stream contains executable
        # receipts. Legacy/manual closure flows can have a valid saved record
        # without a managed stream, so retain that record as their source.
        collected = RECORDER.collected_input(root, run_id)
        if collected.get("receipts"):
            closure = RECORDER.record(root, run_id=run_id)
        else:
            try:
                closure = latest_record(root, run_id)
            except ValueError:
                closure = RECORDER.record(root, run_id=run_id)
    LOCK.assert_write_allowed(root, run_id)
    selected = selected_harnesses(root, run_id)
    debug_intake = L.state_dir(root, run_id) / "debug" / "intake" / "debug-intake-v1.json"
    debug_convergence = L.state_dir(root, run_id) / "debug" / "convergence" / "harness-convergence-v1.json"
    key = {
        "closure_record_id": closure["record_id"], "selected_harnesses": selected,
        "scenarios": relative(root, scenarios_path.resolve()) if scenarios_path else "approved-anchor",
        "debug_convergence": hashlib.sha256(debug_convergence.read_bytes()).hexdigest() if debug_convergence.is_file() else None,
    }
    finalizer_id = "finalizer-" + hashlib.sha256(canonical(key).encode("utf-8")).hexdigest()[:16]
    directory = L.state_dir(root, run_id)
    saved = directory / "finalizers" / f"{finalizer_id}.json"
    if saved.is_file():
        return {**read(saved), "delivery_record": ensure_delivery_record(root, run_id), "reused": True}

    changed = [str(item) for item in closure.get("changed_paths", [])]
    assessments: dict[str, dict[str, Any]] = {}
    if "Architecture Fitness Harness" in selected:
        assessments["Architecture Fitness Harness"] = ARCHITECTURE.assess(root, run_id, changed)
    if "Behaviour Harness" in selected:
        assessments["Behaviour Harness"] = run_behavior(root, run_id, scenarios_path.resolve() if scenarios_path else None)
    if "Maintainability Harness" in selected:
        assessments["Maintainability Harness"] = MAINTAINABILITY.assess(root, run_id, changed)

    higher = higher_tier_status(root, run_id)
    debug_section = DEBUG_SECTION.generate(root, run_id) if debug_intake.is_file() else None
    report = REPORT.build(root, run_id)
    delivery_record = ensure_delivery_record(root, run_id)
    graph_lifecycle: dict[str, Any]
    run_mapping: dict[str, Any] | None = None
    try:
        lock_state = LOCK.show(root, run_id)
        start_report = LOCK.active_start_report(root, run_id).get("report", {})
        navigator_plan = start_report.get("navigator", {}) if isinstance(start_report, dict) else {}
        scope_evidence = navigator_plan.get("scope_evidence", {}) if isinstance(navigator_plan, dict) else {}
        
        # Load command registry from approved requirements for traceability
        approved_anchor = ANCHOR.approved(root, run_id)
        command_registry = {}
        if isinstance(approved_anchor, dict):
            for req in approved_anchor.get("requirements", []):
                if isinstance(req, dict):
                    contract = req.get("validation_contract", {})
                    if isinstance(contract, dict):
                        req_registry = contract.get("command_registry", {})
                        if isinstance(req_registry, dict):
                            command_registry.update(req_registry)
        
        graph_lifecycle = NAVIGATOR_GRAPH.manage(
            root,
            str(lock_state.get("goal", "")),
            changed,
            mode="auto" if changed else "reuse",
            attempt_id=run_id,
            phase="closure",
        )
        if isinstance(scope_evidence, dict) and scope_evidence.get("decision_fingerprint"):
            run_mapping = NAVIGATOR_GRAPH.record_run_mapping(
                root,
                run_id,
                str(lock_state.get("goal", "")),
                scope_evidence,
                changed,
                str(report.get("overall_status", "evidence-incomplete")),
                graph_lifecycle,
            )
        L.append_event(root, run_id, "navigator_graph_lifecycle_recorded", {
            "action": graph_lifecycle.get("action"),
            "cache_fingerprint": graph_lifecycle.get("cache_fingerprint"),
            "mapping_fingerprint": (run_mapping or {}).get("mapping_fingerprint"),
            "phase": "closure",
        })
    except (OSError, ValueError, RuntimeError, json.JSONDecodeError) as error:
        graph_lifecycle = {
            "schema_version": "1",
            "type": "tailtrail-navigator-graph-lifecycle",
            "phase": "closure",
            "action": "failed",
            "written": False,
            "implementation_authority": False,
            "error": str(error),
            "boundary": "Graph metadata refresh failed without changing closure evidence or source authority.",
        }
    try:
        sweep = REFRESH.sweep_v3(root)
        stale_learnings = {
            "triggered": [row["learning_id"] for row in sweep.get("triggered", [])],
            "needs_backfill": list(sweep.get("needs_backfill", [])),
        }
    except (OSError, ValueError):
        stale_learnings = {"triggered": [], "needs_backfill": [], "unavailable": True}
    try:
        harness_event = HARNESS.record_closure_event(root, run_id, {
            "requirements": {"complete": report["requirement_status"]["complete"], "total": report["requirement_status"]["total"]},
            "tests_status": report["tests"]["status"],
            "drift_status": report["drift"]["status"],
            "overall_status": report["overall_status"],
            "pipeline_stage": (report.get("pipeline", {}) or {}).get("active_stage", "unknown"),
            "token_estimate": str(report.get("token_usage", {}).get("status", "unknown")),
        })
        harness_review = {"recorded": harness_event is not None}
    except (OSError, ValueError, KeyError):
        harness_review = {"recorded": False, "unavailable": True}
    correction = None
    if report["overall_status"] != "complete":
        if debug_section and debug_section.get("debug_status") != "pass":
            correction = {
                "type": "tailtrail-debug-correction-replan-handoff",
                "run_id": run_id,
                "requirement_uid": debug_section.get("requirement_uid"),
                "status": "correction-required",
                "gaps": debug_section.get("gaps", []),
                "next": "Resolve only the listed Debug closure gaps under the existing approved run, then rerun Debug Harness convergence and closure finalize.",
                "boundary": "This handoff preserves the approved reproduction, hypothesis history, correction scope, and evidence stream. It grants no new source, Git, test, provider, deployment, or acceptance authority.",
            }
        else:
            correction = CORRECTION.handoff(root, run_id)
    payload = {
        "schema_version": "1", "type": "tailtrail-closure-finalizer", "finalizer_id": finalizer_id,
        "run_id": run_id, "closure_record_id": closure["record_id"], "selected_harnesses": selected,
        "assessments": {name: {"complete": item.get("complete"), "artifact": item.get("run_artifact")} for name, item in assessments.items()},
        "higher_tier_evidence": higher,
        "debug_section": {"status": debug_section.get("debug_status"), "artifact": DEBUG_SECTION.report_path(root, run_id).relative_to(root).as_posix()} if debug_section else None,
        "recovery": report["recovery_checkpoint"],
        "context_continuity": report["drift_learning"],
        "pipeline": report.get("pipeline", {"status": "not-recorded"}),
        "stale_learnings": stale_learnings,
        "harness_review": harness_review,
        "graph_lifecycle": graph_lifecycle,
        "run_mapping": run_mapping,
        "correction": correction,
        "completion_report": report.get("run_artifact"),
        "delivery_record": delivery_record,
        "command_registry": command_registry,
        "overall_status": report["overall_status"],
        "boundary": "Finalized deterministic local control evidence only. No receipt command, deployment, recovery action, or external environment was executed.",
    }
    # Attach the existing canonical report to an already activated DWR run.
    # It never creates a workflow for a legacy/non-DWR run or changes closure status.
    payload["workflow_closure"] = WORKFLOW_EVIDENCE.sync_closure(root, run_id, report)
    L.atomic_json(saved, payload)
    L.append_event(root, run_id, "closure_finalized", {
        "artifact": saved.relative_to(directory).as_posix(), "closure_record_id": closure["record_id"],
        "overall_status": report["overall_status"], "selected_harnesses": selected,
    })
    
    # Generate verbose closure report - MANDATORY for every finalized run
    try:
        verbose_result = generate_closure_report_verbose(root, run_id, payload)
        if isinstance(verbose_result, dict):
            # Ensure mandatory report was generated
            if verbose_result.get("mandatory") and verbose_result.get("status") == "generated":
                L.append_event(root, run_id, "verbose_closure_report_generated", verbose_result)
            else:
                raise ValueError(f"Closure verbose report generation failed: {verbose_result}")
    except Exception as error:
        # Mandatory report generation failed - log and re-raise
        L.append_event(root, run_id, "verbose_closure_report_generation_failed", {
            "error": str(error),
            "mandatory": True,
            "run_id": run_id,
        })
        raise ValueError(f"MANDATORY: Closure verbose report generation failed: {error}")
    
    return {**payload, "reused": False}


def generate_closure_report_verbose(root: Path, run_id: str, closure_payload: dict[str, Any]) -> dict[str, Any]:
    """Generate and save the comprehensive closure report verbose report.
    
    MANDATORY: This report must be generated for every finalized run.
    Called after finalization to generate professional markdown documentation
    with proof execution summary, token metrics, and completion checklist.
    
    Raises:
        ValueError: If report generation fails (mandatory requirement)
    """
    root = root.resolve()
    
    # Extract command registry from closure payload
    command_registry = closure_payload.get("command_registry", {})
    if not isinstance(command_registry, dict):
        raise ValueError(f"Cannot generate closure verbose report: invalid command_registry in closure payload")
    
    # Generate markdown report
    report_markdown = VR.generate_closure_report_verbose(
        run_id,
        closure_payload,
        command_registry
    )
    
    if not report_markdown or len(report_markdown) < 100:
        raise ValueError(f"Closure verbose report generation produced invalid output (length: {len(report_markdown or '')})")
    
    # Save reports (both markdown and JSON metadata)
    report_path = VR.save_verbose_reports(root, run_id, "closure", report_markdown)
    
    # Verify both files were created
    markdown_path = report_path
    json_path = report_path.parent / f"{report_path.stem.replace('-v1', '')}-v1.json"
    
    if not markdown_path.is_file():
        raise ValueError(f"Closure verbose markdown report not created: {markdown_path}")
    if not json_path.is_file():
        raise ValueError(f"Closure verbose metadata not created: {json_path}")
    
    L.append_event(root, run_id, "closure_report_verbose_generated", {
        "artifact": report_path.relative_to(root).as_posix(),
        "markdown_size": len(report_markdown),
        "mandatory": True,
        "status": "verified"
    })
    
    return {
        "status": "generated",
        "artifact": report_path.relative_to(root).as_posix(),
        "markdown_size": len(report_markdown),
        "run_id": run_id,
        "mandatory": True,
    }


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--root", type=Path, default=Path.cwd())
    parser.add_argument("--run-id", required=True)
    parser.add_argument("--input", type=Path, help="Optional Phase 0 closure input; it is recorded idempotently before finalization.")
    parser.add_argument("--scenarios", type=Path, help="Declared Behaviour Harness scenario JSON when behaviour was selected.")
    args = parser.parse_args()
    try:
        print(json.dumps(finalize(args.root, args.run_id, args.input, args.scenarios), indent=2, sort_keys=True))
        return 0
    except (OSError, ValueError, KeyError, json.JSONDecodeError) as error:
        print(f"Closure finalizer error: {error}")
        return 2


if __name__ == "__main__":
    raise SystemExit(main())
