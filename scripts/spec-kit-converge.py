#!/usr/bin/env python3
"""Create a read-only-in-source Spec Kit convergence report for an approved TailTrail run."""
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
    value = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(value)
    return value


LEDGER = module("run-ledger.py", "spec_kit_converge_ledger")
SLICES = module("spec-kit-slices.py", "spec_kit_converge_slices")
AMENDMENT = module("spec-kit-amendment.py", "spec_kit_converge_amendment")


def read(path: Path) -> dict[str, Any]:
    return json.loads(path.read_text(encoding="utf-8"))


def latest(directory: Path, prefix: str) -> Path | None:
    found: list[tuple[int, Path]] = []
    for path in directory.glob(f"{prefix}-v*.json"):
        match = re.fullmatch(re.escape(prefix) + r"-v(\d+)\.json", path.name)
        if match:
            found.append((int(match.group(1)), path))
    return max(found, default=(0, None))[1]


def relative(root: Path, path: Path | None) -> str | None:
    return path.relative_to(root).as_posix() if path else None


def converge(root: Path, run_id: str) -> dict[str, Any]:
    root = root.resolve(); base = LEDGER.state_dir(root, run_id) / "spec-kit"; paths = SLICES.paths(root, run_id)
    source_lock = read(paths["source_lock"]); mapping = read(paths["mapping"])["mappings"]; slice_state = SLICES.show(root, run_id)
    evidence_path = latest(base, "evidence")
    evidence = read(evidence_path) if evidence_path else {"requirements": []}
    evidence_by_uid = {row.get("requirement_uid"): row for row in evidence.get("requirements", []) if isinstance(row, dict)}
    drift = AMENDMENT.check(root, run_id)
    requirements: list[dict[str, Any]] = []
    for row in mapping:
        proof = evidence_by_uid.get(row["requirement_uid"])
        state = str(proof.get("state")) if proof else "incomplete"
        reason = "checkpoint-backed evidence is missing" if proof is None else None
        if drift["state"] in {"material-change", "import-required", "blocked"}:
            state = "source-amended" if drift["state"] == "material-change" else "needs-decision"
            reason = "current Spec Kit source is not safely aligned with this approved mapping"
        requirements.append({"external_id": row["external_id"], "requirement_uid": row["requirement_uid"], "state": state, "evidence": proof.get("checkpoint") if proof else None, "reason": reason, "likely_paths": row.get("likely_paths", [])})
    amendment_path = latest(base, "amendment")
    if amendment_path:
        amendment = read(amendment_path)
        if amendment.get("state") == "approved":
            for change in amendment.get("changes", []):
                if change.get("kind") == "revoked":
                    requirements.append({"external_id": change.get("external_id"), "requirement_uid": change.get("requirement_uid"), "state": "superseded", "evidence": None, "reason": "Requirement was revoked by an approved Spec Kit amendment.", "likely_paths": []})
    tasks = []
    import_payload = read(root / source_lock["import"])
    task_snapshot = Path(source_lock["import"]).with_name(Path(source_lock["import"]).name.replace("import-", "tasks-"))
    story_snapshot = Path(source_lock["import"]).with_name(Path(source_lock["import"]).name.replace("import-", "stories-"))
    if (root / task_snapshot).is_file():
        tasks = read(root / task_snapshot).get("tasks", [])
    stories = read(root / story_snapshot).get("stories", []) if (root / story_snapshot).is_file() else []
    checkpoints = sorted((LEDGER.state_dir(root, run_id) / "checkpoints").glob("checkpoint-*.json"))
    checkpoint = read(checkpoints[-1]) if checkpoints else {}
    ci_receipts = [read(path) for path in sorted((LEDGER.state_dir(root, run_id) / "validation-receipts").glob("*.json"))]
    known_external = {row["external_id"] for row in mapping}
    task_rows = [{"external_id": row.get("external_id"), "state": "complete" if row.get("external_id") in known_external and all(item["state"] == "complete" for item in requirements if item.get("external_id") == row.get("external_id")) else "deferred-by-approval", "reason": "Task is not separately mapped to an approved execution slice."} for row in tasks]
    pending_slices = [row for row in slice_state["slices"] if row["state"] != "completed"]
    unresolved = [row for row in requirements if row["state"] in {"incomplete", "source-amended", "needs-decision"}]
    blocked = drift["state"] in {"material-change", "import-required", "blocked"}
    closure_state = "blocked" if blocked else "gaps" if unresolved else "ready"
    follow_ups = []
    for row in unresolved:
        follow_ups.append({"requirement_uid": row["requirement_uid"], "external_id": row["external_id"], "action": "amendment review" if row["state"] in {"source-amended", "needs-decision"} else "record the required checkpoint-backed harness evidence"})
    for row in task_rows:
        if row["state"] == "deferred-by-approval": follow_ups.append({"requirement_uid": None, "external_id": row["external_id"], "action": "map this Spec Kit task to an approved slice before execution"})
    payload = {"schema_version": "1", "type": "tailtrail-spec-kit-convergence", "run_id": run_id, "feature_id": source_lock["feature_id"], "source_revision": source_lock["source_revision"], "current_source_state": drift["state"], "requirements": requirements, "stories": stories, "tasks": task_rows, "changed_symbols": checkpoint.get("changed_symbols", []), "validation_receipts": checkpoint.get("validation_receipts", [row.get("evidence") for row in requirements if row.get("evidence")]) + ci_receipts, "unresolved_drift": [] if drift["state"] == "locked" else [drift], "deferred_slices": [row["slice_id"] for row in pending_slices if row["state"] in {"pending", "active"}], "architecture": "pass" if all(row["state"] in {"complete", "deferred"} for row in requirements) else "incomplete", "behaviour": "pass" if all(row["state"] in {"complete", "deferred"} for row in requirements) else "incomplete", "closure_state": closure_state, "follow_up_tasks": follow_ups, "boundary": "This report reads TailTrail and imported Spec Kit artifacts only. It never edits Spec Kit files, runs tests, or invents missing source/evidence."}
    path = base / f"convergence-v{len(list(base.glob('convergence-v*.json'))) + 1}.json"
    LEDGER.atomic_json(path, payload)
    LEDGER.append_event(root, run_id, "spec_kit_convergence_recorded", {"artifact": relative(root, path), "closure_state": closure_state, "unresolved_requirements": [row["requirement_uid"] for row in unresolved]})
    return {"artifact": relative(root, path), **payload}


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__); parser.add_argument("--root", type=Path, default=Path.cwd()); parser.add_argument("--run-id", required=True)
    args = parser.parse_args()
    try:
        print(json.dumps(converge(args.root, args.run_id), indent=2, sort_keys=True)); return 0
    except (OSError, ValueError, KeyError, StopIteration, json.JSONDecodeError) as error:
        print(f"Spec Kit convergence error: {error}"); return 2


if __name__ == "__main__":
    raise SystemExit(main())
