#!/usr/bin/env python3
"""Create and enforce bounded execution slices for an approved Spec Kit anchor."""
from __future__ import annotations

import argparse
import importlib.util
import json
import re
from pathlib import Path
from typing import Any


ROOT = Path(__file__).resolve().parents[1]


def module(file: str, name: str) -> Any:
    spec = importlib.util.spec_from_file_location(name, ROOT / "scripts" / file)
    assert spec and spec.loader
    result = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(result)
    return result


LEDGER = module("run-ledger.py", "spec_kit_slices_ledger")
BRIDGE = module("spec-kit-bridge.py", "spec_kit_slices_bridge")


def directory(root: Path, run_id: str) -> Path:
    return LEDGER.state_dir(root, run_id) / "spec-kit"


def read(path: Path) -> dict[str, Any]:
    return json.loads(path.read_text(encoding="utf-8"))


def paths(root: Path, run_id: str) -> dict[str, Path]:
    base = directory(root, run_id)
    def current(prefix: str) -> Path:
        candidates: list[tuple[int, Path]] = []
        for path in base.glob(f"{prefix}-v*.json"):
            match = re.fullmatch(re.escape(prefix) + r"-v(\d+)\.json", path.name)
            if match:
                candidates.append((int(match.group(1)), path))
        return max(candidates, default=(1, base / f"{prefix}-v1.json"))[1]
    return {"source_lock": current("source-lock"), "mapping": current("requirement-mapping"), "slices": current("task-slice-mapping"), "amendment": base / "amendment-state-v1.json"}


def initialize(root: Path, run_id: str) -> dict[str, Any]:
    root = root.resolve()
    anchor_path = LEDGER.state_dir(root, run_id) / "anchors" / "approved-v1.json"
    if not anchor_path.is_file():
        raise ValueError("approve the TailTrail anchor before creating Spec Kit task slices")
    report_path = LEDGER.state_dir(root, run_id) / "planning" / "start-report-v1.json"
    report = read(report_path).get("report", {})
    source = report.get("spec_kit_source") if isinstance(report, dict) else None
    if not isinstance(source, dict):
        raise ValueError("this run has no selected Spec Kit requirement source")
    current = BRIDGE.load(root, str(source.get("feature_id", "")))
    if current["source_revision"] != source.get("source_revision") or current["import"] != source.get("import"):
        raise ValueError("Spec Kit source/import identity changed; amendment review is required before creating slices")
    out = paths(root, run_id)
    if any(path.exists() for path in out.values()):
        if all(path.is_file() for path in out.values()):
            state = read(out["slices"])
            return {"state": "existing", "run_id": run_id, "active_slice": state["active_slice"], "artifact": out["slices"].relative_to(root).as_posix()}
        raise ValueError("partial Spec Kit slice state exists; do not overwrite immutable evidence")
    anchor = read(anchor_path)
    imported = {item["external_id"]: item for item in source.get("requirements", [])}
    mappings: list[dict[str, Any]] = []
    for row in anchor.get("requirements", []):
        reference = row.get("source_reference")
        if not isinstance(reference, dict) or reference.get("external_id") not in imported:
            raise ValueError("approved anchor is missing a valid Spec Kit source reference")
        mappings.append({"external_id": reference["external_id"], "requirement_uid": row["requirement_uid"], "display_id": row["display_id"], "source_path": reference["path"], "source_locator": reference["locator"], "likely_paths": row.get("likely_paths", []), "evidence_plan": row.get("evidence_plan", [])})
    if set(imported) != {item["external_id"] for item in mappings}:
        raise ValueError("approved anchor does not map every imported Spec Kit requirement exactly once")
    slices = []
    for index, mapping in enumerate(mappings, 1):
        slices.append({"slice_id": f"slice-{index}", "state": "active" if index == 1 else "pending", "requirement_uids": [mapping["requirement_uid"]], "external_ids": [mapping["external_id"]], "task_ids": [], "boundary": "Only this requirement and its approved impact/evidence scope may execute."})
    source_lock = {"schema_version": "1", "type": "tailtrail-spec-kit-source-lock", "run_id": run_id, "feature_id": source["feature_id"], "source_uid": source["source_uid"], "source_revision": source["source_revision"], "snapshot": source["snapshot"], "import": source["import"], "anchor": anchor_path.relative_to(root).as_posix(), "anchor_fingerprint": anchor["approved_fingerprint"]}
    requirement_mapping = {"schema_version": "1", "type": "tailtrail-spec-kit-requirement-mapping", "run_id": run_id, "source_lock": out["source_lock"].relative_to(root).as_posix(), "mappings": mappings, "rule": "Every imported requirement maps to one approved TailTrail requirement UID; source wording remains owned by Spec Kit."}
    slice_state = {"schema_version": "1", "type": "tailtrail-spec-kit-task-slice-mapping", "run_id": run_id, "source_lock": out["source_lock"].relative_to(root).as_posix(), "active_slice": "slice-1", "slices": slices, "unassigned_task_ids": [item.get("external_id") for item in source.get("tasks", []) if isinstance(item, dict)], "rule": "Unassigned future tasks are not executable; task-to-slice refinement remains explicit."}
    amendment = {"schema_version": "1", "type": "tailtrail-spec-kit-amendment-state", "run_id": run_id, "state": "none", "source_revision": source["source_revision"], "rule": "A changed Spec Kit source requires a future amendment review; this state never rewrites the approved source lock."}
    for key, payload in (("source_lock", source_lock), ("mapping", requirement_mapping), ("slices", slice_state), ("amendment", amendment)):
        LEDGER.atomic_json(out[key], payload)
    LEDGER.append_event(root, run_id, "spec_kit_anchor_and_slices_created", {"source_lock": out["source_lock"].relative_to(root).as_posix(), "mapping": out["mapping"].relative_to(root).as_posix(), "active_slice": "slice-1", "requirement_uids": [item["requirement_uid"] for item in mappings]})
    return {"state": "created", "run_id": run_id, "active_slice": "slice-1", "artifacts": {key: value.relative_to(root).as_posix() for key, value in out.items()}, "unassigned_task_ids": slice_state["unassigned_task_ids"]}


def show(root: Path, run_id: str) -> dict[str, Any]:
    state = read(paths(root.resolve(), run_id)["slices"])
    return {"type": "tailtrail-spec-kit-slice-status", "schema_version": "1", **state}


def assert_active(root: Path, run_id: str, requirement_uid: str) -> dict[str, Any]:
    state = show(root, run_id)
    active = next(item for item in state["slices"] if item["slice_id"] == state["active_slice"])
    if requirement_uid not in active["requirement_uids"]:
        raise ValueError(f"requirement `{requirement_uid}` is not in active slice `{active['slice_id']}`")
    return {"type": "tailtrail-spec-kit-active-slice", "schema_version": "1", "run_id": run_id, "active_slice": active["slice_id"], "requirement_uid": requirement_uid, "state": "allowed", "boundary": active["boundary"]}


def advance(root: Path, run_id: str, completed_requirement_uid: str, approved: bool) -> dict[str, Any]:
    if not approved:
        raise ValueError("advancing a Spec Kit task slice requires --approved")
    root = root.resolve(); out = paths(root, run_id); state = read(out["slices"])
    active_index = next(index for index, item in enumerate(state["slices"]) if item["slice_id"] == state["active_slice"])
    active = state["slices"][active_index]
    if completed_requirement_uid not in active["requirement_uids"]:
        raise ValueError("only the active slice may be completed")
    active["state"] = "completed"
    if active_index + 1 < len(state["slices"]):
        next_slice = state["slices"][active_index + 1]; next_slice["state"] = "active"; state["active_slice"] = next_slice["slice_id"]
    else:
        state["active_slice"] = None
    LEDGER.atomic_json(out["slices"], state)
    LEDGER.append_event(root, run_id, "spec_kit_slice_advanced", {"completed_requirement_uid": completed_requirement_uid, "active_slice": state["active_slice"]})
    return {"type": "tailtrail-spec-kit-slice-advance", "schema_version": "1", "run_id": run_id, "completed_requirement_uid": completed_requirement_uid, "next_active_slice": state["active_slice"], "state": "advanced"}


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    subs = parser.add_subparsers(dest="action", required=True)
    for action in ("init", "show", "assert-active", "advance"):
        item = subs.add_parser(action); item.add_argument("--root", type=Path, default=Path.cwd()); item.add_argument("--run-id", required=True)
        if action == "assert-active": item.add_argument("--requirement-uid", required=True)
        if action == "advance": item.add_argument("--completed-requirement-uid", required=True); item.add_argument("--approved", action="store_true")
    args = parser.parse_args()
    try:
        if args.action == "init": result = initialize(args.root, args.run_id)
        elif args.action == "show": result = show(args.root, args.run_id)
        elif args.action == "assert-active": result = assert_active(args.root, args.run_id, args.requirement_uid)
        else: result = advance(args.root, args.run_id, args.completed_requirement_uid, args.approved)
    except (OSError, ValueError, KeyError, StopIteration, json.JSONDecodeError) as error:
        print(f"Spec Kit slice bridge error: {error}"); return 2
    print(json.dumps(result, indent=2, sort_keys=True)); return 0


if __name__ == "__main__":
    raise SystemExit(main())
