#!/usr/bin/env python3
"""Render one evidence-backed end-of-task completion report for a TailTrail run."""
from __future__ import annotations

import argparse
import importlib.util
import json
from pathlib import Path
from typing import Any


ROOT = Path(__file__).resolve().parents[1]


def ledger() -> Any:
    spec = importlib.util.spec_from_file_location("completion_report_ledger", ROOT / "scripts" / "run-ledger.py")
    module = importlib.util.module_from_spec(spec)
    assert spec and spec.loader
    spec.loader.exec_module(module)
    return module


L = ledger()


def read(path: Path) -> dict[str, Any]:
    return json.loads(path.read_text(encoding="utf-8"))


def latest(directory: Path, pattern: str) -> tuple[dict[str, Any] | None, str | None]:
    files = sorted(directory.glob(pattern))
    if not files:
        return None, None
    path = files[-1]
    return read(path), path.relative_to(directory.parents[0]).as_posix()


def status(value: bool | None, *, not_selected: bool = False) -> str:
    if not_selected:
        return "not-assessed"
    if value is None:
        return "unavailable"
    return "pass" if value else "fail"


def build(root: Path, run_id: str, record: bool = True) -> dict[str, Any]:
    directory = L.state_dir(root, run_id)
    anchor = read(directory / "anchors" / "approved-v1.json")
    checkpoint, checkpoint_path = latest(directory / "checkpoints", "checkpoint-*.json")
    review, review_path = latest(directory / "reviews", "review-*.json")
    gate, gate_path = latest(directory / "completion-gates", "gate-*.json")
    architecture, architecture_path = latest(directory / "architecture", "assessment-*.json")
    behavior, behavior_path = latest(directory / "behavior", "assessment-*.json")
    maintainability, maintainability_path = latest(directory / "maintainability", "assessment-*.json")
    boundary_path = directory / "recovery" / "boundary.json"
    boundary = read(boundary_path) if boundary_path.is_file() else None
    receipts = [read(path) for path in sorted((directory / "validation-receipts").glob("*.json"))]

    actual = {row.get("requirement_uid"): row for row in (checkpoint or {}).get("requirements", [])}
    findings_by_requirement: dict[str, list[dict[str, Any]]] = {}
    for finding in (review or {}).get("findings", []):
        findings_by_requirement.setdefault(str(finding.get("requirement_uid", "")), []).append(finding)
    requirements = []
    for requirement in anchor.get("requirements", []):
        uid = requirement["requirement_uid"]
        observed = actual.get(uid, {})
        validated = observed.get("state") == "validated" and not findings_by_requirement.get(uid)
        requirements.append({
            "requirement_uid": uid,
            "display_id": requirement.get("display_id", uid),
            "statement": requirement.get("statement", ""),
            "status": "complete" if validated else ("incomplete" if checkpoint else "unavailable"),
            "evidence": observed.get("evidence", []),
            "findings": findings_by_requirement.get(uid, []),
        })

    scope_findings = [item for item in (architecture or {}).get("findings", []) if item.get("category") == "scope"]
    unresolved_drift = [
        item for item in (checkpoint or {}).get("drift", [])
        if item.get("classification") in {"new-drift", "regressed", "needs-decision"}
    ] + [
        item for item in (review or {}).get("findings", [])
        if item.get("classification") in {"new-drift", "regressed", "needs-decision"}
    ]
    architecture_required = any(
        any((row.get("architecture_contract") or {}).get(key) for key in ("required_paths", "protected_paths", "forbidden_imports"))
        for row in anchor.get("requirements", [])
    )
    behavior_required = behavior is not None
    passed_tiers = sorted({str(item.get("tier")) for item in receipts if item.get("outcome") == "pass"})
    failed_receipts = [item for item in receipts if item.get("outcome") != "pass"]
    requirement_complete = sum(item["status"] == "complete" for item in requirements)

    def harness(name: str, artifact: dict[str, Any] | None, artifact_path: str | None, *, required: bool = False, complete: bool | None = None, basis: str) -> dict[str, Any]:
        if artifact is None:
            return {"name": name, "used": False, "status": "required-evidence-missing" if required else "not-selected", "basis": basis, "artifact": None}
        outcome = complete if complete is not None else artifact.get("complete")
        return {"name": name, "used": True, "status": status(outcome), "basis": basis, "artifact": artifact_path}

    harnesses = [
        harness("Requirement Completion Harness", checkpoint, checkpoint_path, required=True, complete=requirement_complete == len(requirements) and bool(review) and bool(gate) and review.get("complete") and gate.get("complete"), basis="approved anchor + checkpoint + completion review + evidence gate"),
        harness("Architecture Fitness Harness", architecture, architecture_path, required=architecture_required, basis="approved architecture contract or recorded architecture assessment"),
        harness("Behaviour Harness", behavior, behavior_path, basis="recorded approved-scenario assessment"),
        harness("Maintainability Harness", maintainability, maintainability_path, basis="recorded refactor/maintainability assessment"),
        harness("Evidence-Aware Testing", gate, gate_path, required=True, basis="completion gate and validation receipts"),
    ]

    payload = {
        "schema_version": "1",
        "type": "tailtrail-completion-report",
        "run_id": run_id,
        "evidence_label": "local-evidence",
        "requirement_status": {
            "complete": requirement_complete,
            "total": len(requirements),
            "requirements": requirements,
        },
        "harnesses": harnesses,
        "changed_scope": {
            "status": "approved" if checkpoint and not scope_findings else ("changed-beyond-approved" if scope_findings else "unavailable"),
            "changed_paths": (checkpoint or {}).get("changed_paths", []),
            "findings": scope_findings,
        },
        "architecture": {
            "status": status(architecture.get("complete") if architecture else None, not_selected=not architecture_required and architecture is None),
            "required": architecture_required,
            "findings": (architecture or {}).get("findings", []),
        },
        "behaviour": {
            "status": status(behavior.get("complete") if behavior else None, not_selected=not behavior_required),
            "required": behavior_required,
            "findings": (behavior or {}).get("findings", []),
        },
        "tests": {
            "status": status(gate.get("complete") if gate else None),
            "passed_tiers": passed_tiers,
            "failed_or_unavailable_receipts": failed_receipts,
            "findings": (gate or {}).get("findings", []),
        },
        "drift": {
            "status": "none-unresolved" if checkpoint and not unresolved_drift else ("unresolved" if unresolved_drift else "unavailable"),
            "findings": unresolved_drift,
        },
        "recovery_checkpoint": {
            "status": "available" if boundary else "not-configured",
            "boundary": boundary,
        },
        "source_artifacts": {
            "approved_anchor": "anchors/approved-v1.json",
            "checkpoint": checkpoint_path,
            "completion_review": review_path,
            "completion_gate": gate_path,
            "architecture": architecture_path,
            "behaviour": behavior_path,
            "maintainability": maintainability_path,
            "recovery_boundary": "recovery/boundary.json" if boundary else None,
        },
        "boundary": "The report aggregates saved local artifacts. Missing or failed evidence is not reported as a pass.",
    }
    ready = (
        payload["requirement_status"]["complete"] == payload["requirement_status"]["total"]
        and payload["changed_scope"]["status"] == "approved"
        and payload["tests"]["status"] == "pass"
        and payload["drift"]["status"] == "none-unresolved"
        and payload["architecture"]["status"] in {"pass", "not-assessed"}
        and payload["behaviour"]["status"] in {"pass", "not-assessed"}
    )
    payload["overall_status"] = "complete" if ready else "evidence-incomplete"
    if record:
        reports = directory / "completion-reports"
        reports.mkdir(parents=True, exist_ok=True)
        path = reports / f"report-{len(list(reports.glob('report-*.json'))) + 1}.json"
        L.atomic_json(path, payload)
        L.append_event(root, run_id, "completion_report_created", {
            "artifact": path.relative_to(directory).as_posix(),
            "overall_status": payload["overall_status"],
            "harnesses": [{"name": item["name"], "used": item["used"], "status": item["status"]} for item in harnesses],
        })
        payload["run_artifact"] = path.as_posix()
    return payload


def render(payload: dict[str, Any]) -> str:
    requirements = payload["requirement_status"]
    tests = payload["tests"]
    tiers = " + ".join(tests["passed_tiers"]) or "none recorded"
    lines = [
        "# TailTrail Completion Report",
        "",
        f"Run: `{payload['run_id']}`",
        f"Overall: **{payload['overall_status']}**",
        "",
        f"Requirement status: **{requirements['complete']}/{requirements['total']} complete**",
        f"Changed scope: **{payload['changed_scope']['status']}**",
        f"Architecture: **{payload['architecture']['status']}**",
        f"Behaviour evidence: **{payload['behaviour']['status']}**",
        f"Tests: **{tests['status']}** ({tiers})",
        f"Drift: **{payload['drift']['status']}**",
        f"Recovery checkpoint: **{payload['recovery_checkpoint']['status']}**",
        "",
        "## Harness usage",
        "",
        "| Harness | Used | Status | Selection / evidence basis |",
        "| --- | --- | --- | --- |",
    ]
    for harness in payload["harnesses"]:
        lines.append(f"| {harness['name']} | {'yes' if harness['used'] else 'no'} | {harness['status']} | {harness['basis']} |")
    lines.extend([
        "",
        "| Requirement | Status | Evidence |",
        "| --- | --- | --- |",
    ])
    for requirement in requirements["requirements"]:
        evidence = len(requirement["evidence"])
        lines.append(f"| {requirement['display_id']} — {requirement['statement']} | {requirement['status']} | {evidence} saved item(s) |")
    return "\n".join(lines) + "\n"


def show(root: Path, run_id: str, sequence: int | None = None) -> dict[str, Any]:
    directory = L.state_dir(root, run_id) / "completion-reports"
    reports = sorted(directory.glob("report-*.json"))
    if not reports:
        raise ValueError("no completion report exists")
    if sequence is None:
        return read(reports[-1])
    path = directory / f"report-{sequence}.json"
    if not path.is_file():
        raise ValueError(f"completion report {sequence} does not exist")
    return read(path)


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--root", type=Path, default=Path.cwd())
    parser.add_argument("--run-id", required=True)
    parser.add_argument("--show", action="store_true", help="Read the latest saved report without creating one.")
    parser.add_argument("--sequence", type=int)
    parser.add_argument("--format", choices=("markdown", "json"), default="markdown")
    args = parser.parse_args()
    try:
        result = show(args.root.resolve(), args.run_id, args.sequence) if args.show else build(args.root.resolve(), args.run_id)
        print(json.dumps(result, indent=2, sort_keys=True) if args.format == "json" else render(result), end="")
        return 0
    except (OSError, ValueError, KeyError, json.JSONDecodeError) as error:
        print(f"Completion report error: {error}")
        return 2


if __name__ == "__main__":
    raise SystemExit(main())
