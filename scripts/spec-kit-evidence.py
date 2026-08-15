#!/usr/bin/env python3
"""Plan and record per-requirement harness evidence for an approved Spec Kit slice."""
from __future__ import annotations

import argparse
import importlib.util
import json
from pathlib import Path
from typing import Any


ROOT = Path(__file__).resolve().parents[1]


def module(file: str, name: str) -> Any:
    spec = importlib.util.spec_from_file_location(name, ROOT / "scripts" / file)
    assert spec and spec.loader
    value = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(value)
    return value


LEDGER = module("run-ledger.py", "spec_kit_evidence_ledger")
SLICES = module("spec-kit-slices.py", "spec_kit_evidence_slices")


def read(path: Path) -> dict[str, Any]:
    return json.loads(path.read_text(encoding="utf-8"))


def artifact_reference(root: Path, path: Path) -> str:
    """Keep a usable pointer even when Windows represents Temp with an 8.3 path."""
    try:
        return path.relative_to(root).as_posix()
    except ValueError:
        # A checkpoint may be supplied outside the workspace. Preserve its exact
        # location rather than failing while rendering evidence.
        return str(path)


def folder(root: Path, run_id: str) -> Path:
    return LEDGER.state_dir(root, run_id) / "spec-kit"


def evidence_plan_path(root: Path, run_id: str) -> Path:
    source_lock = SLICES.paths(root, run_id)["source_lock"]
    version = source_lock.stem.rsplit("v", 1)[-1]
    return folder(root, run_id) / f"evidence-plan-v{version}.json"


def plan(root: Path, run_id: str) -> dict[str, Any]:
    root = root.resolve(); path = evidence_plan_path(root, run_id)
    if path.is_file():
        return {"state": "existing", "artifact": path.relative_to(root).as_posix(), **read(path)}
    state = SLICES.show(root, run_id)
    lock = read(SLICES.paths(root, run_id)["source_lock"])
    source = read(root / lock["snapshot"])
    contracts = [item for item in source.get("artifacts", []) if item.get("kind") == "contract"]
    mapping = read(SLICES.paths(root, run_id)["mapping"])["mappings"]
    active = next(item for item in state["slices"] if item["slice_id"] == state["active_slice"])
    active_uids = set(active["requirement_uids"])
    rows = []
    for item in mapping:
        controls = ["Requirement Completion Harness", "Evidence-Aware Testing"]
        tiers = ["focused"]
        if contracts:
            controls.append("Architecture Fitness Harness"); tiers.append("contract")
        if item["external_id"].startswith("US-"):
            controls.append("Behaviour Harness"); tiers.append("behaviour")
        rows.append({"external_id": item["external_id"], "requirement_uid": item["requirement_uid"], "slice_id": next(slice_["slice_id"] for slice_ in state["slices"] if item["requirement_uid"] in slice_["requirement_uids"]), "state": "active" if item["requirement_uid"] in active_uids else "deferred", "selected_controls": controls, "minimum_evidence": tiers, "proof_boundary": "A generic passing suite cannot complete this requirement; evidence must link to this requirement UID."})
    payload = {"schema_version": "1", "type": "tailtrail-spec-kit-evidence-plan", "run_id": run_id, "source_lock": lock["source_revision"], "active_slice": state["active_slice"], "requirements": rows, "contract_artifacts": [item["path"] for item in contracts], "rule": "Only the active slice may record completion. Architecture and behaviour assessments are required only when selected in the requirement plan."}
    LEDGER.atomic_json(path, payload)
    LEDGER.append_event(root, run_id, "spec_kit_evidence_planned", {"artifact": path.relative_to(root).as_posix(), "active_slice": state["active_slice"], "requirements": [item["requirement_uid"] for item in rows]})
    return {"state": "created", "artifact": path.relative_to(root).as_posix(), **payload}


def assessment(path: Path | None, requirement_uid: str, kind: str) -> tuple[bool, str | None]:
    if path is None:
        return False, f"{kind} assessment is required"
    payload = read(path)
    if not payload.get("complete"):
        return False, f"{kind} assessment is incomplete"
    if kind == "behaviour" and not any(item.get("requirement_uid") == requirement_uid and item.get("state") == "validated" for item in payload.get("scenarios", [])):
        return False, "behaviour assessment has no validated scenario for active requirement"
    return True, None


def record(root: Path, run_id: str, checkpoint_path: Path, architecture: Path | None, behavior: Path | None) -> dict[str, Any]:
    root = root.resolve(); plan_payload = read(evidence_plan_path(root, run_id)); state = SLICES.show(root, run_id)
    active = next(item for item in state["slices"] if item["slice_id"] == state["active_slice"])
    checkpoint = read(checkpoint_path)
    status = {item.get("requirement_uid"): item for item in checkpoint.get("requirements", [])}
    records = []
    for row in plan_payload["requirements"]:
        if row["requirement_uid"] not in active["requirement_uids"]:
            records.append({"requirement_uid": row["requirement_uid"], "external_id": row["external_id"], "state": "deferred", "blockers": ["future slice is not active"]}); continue
        blockers = []
        checkpoint_row = status.get(row["requirement_uid"])
        if not checkpoint_row or checkpoint_row.get("state") != "validated": blockers.append("requirement checkpoint is not validated")
        if "Architecture Fitness Harness" in row["selected_controls"]:
            ok, issue = assessment(architecture, row["requirement_uid"], "architecture")
            if not ok: blockers.append(str(issue))
        if "Behaviour Harness" in row["selected_controls"]:
            ok, issue = assessment(behavior, row["requirement_uid"], "behaviour")
            if not ok: blockers.append(str(issue))
        records.append({"requirement_uid": row["requirement_uid"], "external_id": row["external_id"], "state": "complete" if not blockers else "incomplete", "checkpoint": artifact_reference(root, checkpoint_path), "blockers": blockers})
    number = len(list(folder(root, run_id).glob("evidence-v*.json"))) + 1
    path = folder(root, run_id) / f"evidence-v{number}.json"
    payload = {"schema_version": "1", "type": "tailtrail-spec-kit-evidence", "run_id": run_id, "active_slice": state["active_slice"], "requirements": records, "architecture": artifact_reference(root, architecture) if architecture else None, "behaviour": artifact_reference(root, behavior) if behavior else None, "complete": all(item["state"] in {"complete", "deferred"} for item in records), "boundary": "This record is local checkpoint-backed evidence only; it does not execute tests or infer missing proof."}
    LEDGER.atomic_json(path, payload)
    LEDGER.append_event(root, run_id, "spec_kit_evidence_recorded", {"artifact": path.relative_to(root).as_posix(), "active_slice": state["active_slice"], "complete": payload["complete"]})
    return {"artifact": path.relative_to(root).as_posix(), **payload}


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__); sub = parser.add_subparsers(dest="action", required=True)
    for action in ("plan", "record"):
        item = sub.add_parser(action); item.add_argument("--root", type=Path, default=Path.cwd()); item.add_argument("--run-id", required=True)
        if action == "record": item.add_argument("--checkpoint", type=Path, required=True); item.add_argument("--architecture", type=Path); item.add_argument("--behavior", type=Path)
    args = parser.parse_args()
    try: result = plan(args.root, args.run_id) if args.action == "plan" else record(args.root, args.run_id, args.checkpoint, args.architecture, args.behavior)
    except (OSError, ValueError, KeyError, StopIteration, json.JSONDecodeError) as error: print(f"Spec Kit evidence bridge error: {error}"); return 2
    print(json.dumps(result, indent=2, sort_keys=True)); return 0


if __name__ == "__main__": raise SystemExit(main())
