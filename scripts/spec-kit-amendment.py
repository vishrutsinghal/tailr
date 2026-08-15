#!/usr/bin/env python3
"""Detect, approve, and safely route Spec Kit source amendments for one TailTrail run."""
from __future__ import annotations

import argparse
import hashlib
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


LEDGER = module("run-ledger.py", "spec_kit_amendment_ledger")
DETECT = module("spec-kit-detect.py", "spec_kit_amendment_detect")
SLICES = module("spec-kit-slices.py", "spec_kit_amendment_slices")
EVIDENCE = module("spec-kit-evidence.py", "spec_kit_amendment_evidence")


def read(path: Path) -> dict[str, Any]:
    return json.loads(path.read_text(encoding="utf-8"))


def write(path: Path, value: dict[str, Any]) -> None:
    LEDGER.atomic_json(path, value)


def directory(root: Path, run_id: str) -> Path:
    return LEDGER.state_dir(root, run_id) / "spec-kit"


def versioned(directory_: Path, prefix: str) -> list[tuple[int, Path]]:
    rows: list[tuple[int, Path]] = []
    for path in directory_.glob(f"{prefix}-v*.json"):
        match = re.fullmatch(re.escape(prefix) + r"-v(\d+)\.json", path.name)
        if match:
            rows.append((int(match.group(1)), path))
    return sorted(rows)


def latest(directory_: Path, prefix: str) -> tuple[int, Path]:
    rows = versioned(directory_, prefix)
    if not rows:
        raise ValueError(f"no `{prefix}` artifact exists for this run")
    return rows[-1]


def source_snapshot(root: Path, feature: str, revision: str) -> tuple[Path, dict[str, Any], dict[str, Any]]:
    base = root / ".tailtrail" / "spec-kit" / "sources" / feature
    for _, path in versioned(base, "source"):
        source = read(path)
        if source.get("source_revision") == revision:
            number = re.search(r"-v(\d+)\.json$", path.name)
            assert number
            imported = base / f"import-v{number.group(1)}.json"
            if not imported.is_file():
                raise ValueError("matching Spec Kit import snapshot is missing")
            return path, source, read(imported)
    raise ValueError("current Spec Kit source is not imported; run `tailtrail spec-kit import` before proposing an amendment")


def locked(root: Path, run_id: str) -> dict[str, Any]:
    return read(latest(directory(root, run_id), "source-lock")[1])


def changes(old: list[dict[str, Any]], new: list[dict[str, Any]]) -> list[dict[str, Any]]:
    before = {row["external_id"]: row for row in old}
    after = {row["external_id"]: row for row in new}
    rows: list[dict[str, Any]] = []
    for external_id in sorted(set(before) | set(after)):
        if external_id not in before:
            rows.append({"external_id": external_id, "kind": "added", "current": after[external_id]})
        elif external_id not in after:
            rows.append({"external_id": external_id, "kind": "revoked", "previous": before[external_id]})
        elif before[external_id]["statement"] != after[external_id]["statement"]:
            rows.append({"external_id": external_id, "kind": "changed", "previous": before[external_id], "current": after[external_id]})
        else:
            rows.append({"external_id": external_id, "kind": "unchanged"})
    return rows


def check(root: Path, run_id: str) -> dict[str, Any]:
    root = root.resolve(); lock = locked(root, run_id)
    detection = DETECT.detect(root, lock["feature_id"])
    if detection["state"] != "compatible":
        return {"type": "tailtrail-spec-kit-drift", "run_id": run_id, "state": "blocked", "issues": detection["issues"], "boundary": "Do not execute or amend while the selected Spec Kit source is incompatible."}
    current = detection.get("source_revision")
    if current == lock["source_revision"]:
        return {"type": "tailtrail-spec-kit-drift", "run_id": run_id, "state": "locked", "source_revision": current, "boundary": "The approved Spec Kit source matches the immutable source lock."}
    try:
        _, _, imported = source_snapshot(root, lock["feature_id"], str(current))
    except ValueError:
        return {"type": "tailtrail-spec-kit-drift", "run_id": run_id, "state": "import-required", "previous_source_revision": lock["source_revision"], "current_source_revision": current, "next": "Import the current source explicitly, then propose an amendment. No slice may proceed."}
    _, _, previous = source_snapshot(root, lock["feature_id"], lock["source_revision"])
    delta = changes(previous["requirements"], imported["requirements"])
    material = any(row["kind"] != "unchanged" for row in delta)
    return {"type": "tailtrail-spec-kit-drift", "run_id": run_id, "state": "material-change" if material else "non-material", "previous_source_revision": lock["source_revision"], "current_source_revision": current, "changes": delta, "boundary": "Changed source is advisory until an explicit amendment proposal and approval. A material change freezes affected slices."}


def propose(root: Path, run_id: str) -> dict[str, Any]:
    root = root.resolve(); result = check(root, run_id)
    if result["state"] in {"locked", "blocked", "import-required"}:
        return result
    out = directory(root, run_id); number = len(versioned(out, "amendment")) + 1
    mapping = read(latest(out, "requirement-mapping")[1])["mappings"]
    uids = {row["external_id"]: row["requirement_uid"] for row in mapping}
    for row in result["changes"]:
        row["requirement_uid"] = uids.get(row["external_id"])
    state = "approval-required" if result["state"] == "material-change" else "non-material"
    payload = {"schema_version": "1", "type": "tailtrail-spec-kit-amendment", "run_id": run_id, "amendment_version": number, "previous_source_revision": result["previous_source_revision"], "current_source_revision": result["current_source_revision"], "state": state, "changes": result["changes"], "affected_requirement_uids": sorted({row["requirement_uid"] for row in result["changes"] if row.get("requirement_uid") and row["kind"] != "unchanged"}), "rule": "This proposal does not edit source, replace the original anchor, or silently resume an affected slice."}
    path = out / f"amendment-v{number}.json"; write(path, payload)
    amendment_state = out / "amendment-state-v1.json"
    write(amendment_state, {"schema_version": "1", "type": "tailtrail-spec-kit-amendment-state", "run_id": run_id, "state": state, "latest_amendment": path.relative_to(root).as_posix(), "source_revision": result["current_source_revision"], "affected_requirement_uids": payload["affected_requirement_uids"]})
    LEDGER.append_event(root, run_id, "spec_kit_amendment_proposed", {"artifact": path.relative_to(root).as_posix(), "state": state, "affected_requirement_uids": payload["affected_requirement_uids"]})
    return {"artifact": path.relative_to(root).as_posix(), **payload}


def anchor_uid(run_id: str, statement: str) -> str:
    return "req-" + hashlib.sha256(f"{run_id}:{statement.strip()}".encode()).hexdigest()[:12]


def approve(root: Path, run_id: str, approved: bool) -> dict[str, Any]:
    if not approved:
        raise ValueError("approving a Spec Kit amendment requires --approved")
    root = root.resolve(); out = directory(root, run_id); _, amendment_path = latest(out, "amendment"); amendment = read(amendment_path)
    if amendment["state"] != "approval-required":
        raise ValueError("only a material amendment awaiting approval can create an amended anchor")
    lock = locked(root, run_id); _, _, current = source_snapshot(root, lock["feature_id"], amendment["current_source_revision"])
    old_anchor = read(latest(LEDGER.state_dir(root, run_id) / "anchors", "approved")[1]); old_mapping = read(latest(out, "requirement-mapping")[1])["mappings"]
    old_by_external = {row["external_id"]: row for row in old_mapping}; anchor_by_uid = {row["requirement_uid"]: row for row in old_anchor["requirements"]}
    changed = {row["external_id"]: row["kind"] for row in amendment["changes"]}
    requirements: list[dict[str, Any]] = []
    mappings: list[dict[str, Any]] = []
    for index, source in enumerate(current["requirements"], 1):
        existing = old_by_external.get(source["external_id"])
        if existing:
            row = dict(anchor_by_uid[existing["requirement_uid"]]); row["statement"] = source["statement"]
            uid = row["requirement_uid"]
        else:
            uid = anchor_uid(run_id, source["statement"])
            row = {"requirement_uid": uid, "display_id": f"REQ-{index:02d}", "kind": "change", "statement": source["statement"], "acceptance_criteria": ["Prove the imported Spec Kit requirement through approved local evidence."], "preserve_rules": ["Do not alter Spec Kit source artifacts or behavior outside this approved requirement."], "likely_paths": [], "evidence_plan": ["Link focused computational evidence to this imported requirement."], "validation_contract": {"state": "required", "tiers": ["unit"]}, "architecture_contract": {"required_paths": [], "protected_paths": [], "forbidden_imports": []}, "behavior_contract": {"scenarios": []}, "status": "approved"}
        row["status"] = "approved"; row["source_reference"] = {"source_uid": lock["source_uid"], "source_revision": amendment["current_source_revision"], "path": source["source_path"], "locator": source["source_locator"], "external_id": source["external_id"]}
        requirements.append(row)
        mappings.append({"external_id": source["external_id"], "requirement_uid": uid, "display_id": row["display_id"], "source_path": source["source_path"], "source_locator": source["source_locator"], "likely_paths": row.get("likely_paths", []), "evidence_plan": row.get("evidence_plan", [])})
    version = len(versioned(LEDGER.state_dir(root, run_id) / "anchors", "approved")) + 1
    anchor = {**old_anchor, "proposal_version": version, "requirements": requirements, "amends": old_anchor.get("approved_fingerprint"), "amendment": amendment_path.relative_to(root).as_posix(), "status": "approved"}
    anchor["approved_fingerprint"] = "sha256:" + hashlib.sha256(json.dumps({key: value for key, value in anchor.items() if key != "approved_fingerprint"}, sort_keys=True, separators=(",", ":")).encode()).hexdigest()
    anchor_path = LEDGER.state_dir(root, run_id) / "anchors" / f"approved-v{version}.json"; write(anchor_path, anchor)
    current_snapshot = source_snapshot(root, lock["feature_id"], amendment["current_source_revision"])[0]
    current_import = current_snapshot.with_name(current_snapshot.name.replace("source-", "import-"))
    lock_path = out / f"source-lock-v{version}.json"; write(lock_path, {**lock, "source_revision": amendment["current_source_revision"], "snapshot": current_snapshot.relative_to(root).as_posix(), "import": current_import.relative_to(root).as_posix(), "anchor": anchor_path.relative_to(root).as_posix(), "anchor_fingerprint": anchor["approved_fingerprint"], "amendment": amendment_path.relative_to(root).as_posix()})
    mapping_path = out / f"requirement-mapping-v{version}.json"; write(mapping_path, {"schema_version": "1", "type": "tailtrail-spec-kit-requirement-mapping", "run_id": run_id, "source_lock": lock_path.relative_to(root).as_posix(), "mappings": mappings, "amendment": amendment_path.relative_to(root).as_posix()})
    old_slices = SLICES.show(root, run_id); existing_states = {uid: item["state"] for item in old_slices["slices"] for uid in item["requirement_uids"]}
    new_slices = []
    for index, mapping in enumerate(mappings, 1):
        kind = changed.get(mapping["external_id"], "added")
        prior = existing_states.get(mapping["requirement_uid"])
        state = "completed" if prior == "completed" and kind == "unchanged" else "pending"
        new_slices.append({"slice_id": f"slice-{index}", "state": state, "requirement_uids": [mapping["requirement_uid"]], "external_ids": [mapping["external_id"]], "task_ids": [], "boundary": "Only this requirement and its approved impact/evidence scope may execute."})
    active = next((row for row in new_slices if row["state"] != "completed"), None)
    if active: active["state"] = "active"
    slices_path = out / f"task-slice-mapping-v{version}.json"; write(slices_path, {"schema_version": "1", "type": "tailtrail-spec-kit-task-slice-mapping", "run_id": run_id, "source_lock": lock_path.relative_to(root).as_posix(), "active_slice": active["slice_id"] if active else None, "slices": new_slices, "amendment": amendment_path.relative_to(root).as_posix(), "rule": "The amended mapping preserves unchanged completed slices and reopens changed or added work."})
    correction = {"schema_version": "1", "type": "tailtrail-spec-kit-correction", "run_id": run_id, "amendment": amendment_path.relative_to(root).as_posix(), "state": "correction-ready", "affected_requirement_uids": amendment["affected_requirement_uids"], "preserve": ["original anchors, prior checkpoints, and unrelated repository work"], "next_active_slice": active["slice_id"] if active else None, "rule": "Correct only the amended requirement scope; never revert source code from an amendment artifact."}
    correction_path = out / f"correction-v{version}.json"; write(correction_path, correction)
    amendment["state"] = "approved"; amendment["approved_anchor"] = anchor_path.relative_to(root).as_posix(); amendment["correction"] = correction_path.relative_to(root).as_posix(); write(amendment_path, amendment)
    write(out / "amendment-state-v1.json", {"schema_version": "1", "type": "tailtrail-spec-kit-amendment-state", "run_id": run_id, "state": "approved", "latest_amendment": amendment_path.relative_to(root).as_posix(), "source_revision": amendment["current_source_revision"], "active_slice": correction["next_active_slice"]})
    evidence_plan = EVIDENCE.plan(root, run_id)
    LEDGER.append_event(root, run_id, "spec_kit_amendment_approved", {"amendment": amendment_path.relative_to(root).as_posix(), "anchor": anchor_path.relative_to(root).as_posix(), "correction": correction_path.relative_to(root).as_posix(), "active_slice": correction["next_active_slice"]})
    return {"type": "tailtrail-spec-kit-amendment-approval", "run_id": run_id, "state": "approved", "anchor": anchor_path.relative_to(root).as_posix(), "mapping": mapping_path.relative_to(root).as_posix(), "slices": slices_path.relative_to(root).as_posix(), "correction": correction_path.relative_to(root).as_posix(), "evidence_plan": evidence_plan.get("artifact"), "recovery": "Use the existing TailTrail Git recovery boundary when an approved correction cannot converge; it preserves unrelated work and never performs an automatic rollback."}


def recovery(root: Path, run_id: str) -> dict[str, Any]:
    root = root.resolve(); out = directory(root, run_id); state = read(out / "amendment-state-v1.json")
    if state.get("state") != "approved":
        raise ValueError("recovery planning requires an approved amendment")
    _, correction_path = latest(out, "correction"); correction = read(correction_path)
    boundary = LEDGER.state_dir(root, run_id) / "recovery" / "boundary.json"
    mode = "git-checkpoint-recovery" if boundary.is_file() else "task-owned-reconciliation"
    payload = {"schema_version": "1", "type": "tailtrail-spec-kit-recovery-plan", "run_id": run_id, "state": "planned", "mode": mode, "correction": correction_path.relative_to(root).as_posix(), "affected_requirement_uids": correction["affected_requirement_uids"], "preserve": correction["preserve"], "actions": ["inspect only the amended requirement evidence and approved scope", "prefer the existing Git requirement checkpoint when available", "otherwise reconcile task-owned hunks/symbols only", "rerun the selected Harness evidence before advancing"], "boundary": "This is a recovery plan only. It does not execute Git, modify source, or revert unrelated work."}
    path = out / f"recovery-v{len(versioned(out, 'recovery')) + 1}.json"; write(path, payload)
    LEDGER.append_event(root, run_id, "spec_kit_recovery_planned", {"artifact": path.relative_to(root).as_posix(), "mode": mode, "affected_requirement_uids": correction["affected_requirement_uids"]})
    return {"artifact": path.relative_to(root).as_posix(), **payload}


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__); sub = parser.add_subparsers(dest="action", required=True)
    for name in ("check", "propose", "approve", "recovery"):
        item = sub.add_parser(name); item.add_argument("--root", type=Path, default=Path.cwd()); item.add_argument("--run-id", required=True)
        if name == "approve": item.add_argument("--approved", action="store_true")
    args = parser.parse_args()
    try:
        result = check(args.root, args.run_id) if args.action == "check" else propose(args.root, args.run_id) if args.action == "propose" else approve(args.root, args.run_id, args.approved) if args.action == "approve" else recovery(args.root, args.run_id)
        print(json.dumps(result, indent=2, sort_keys=True)); return 0
    except (OSError, ValueError, KeyError, StopIteration, json.JSONDecodeError) as error:
        print(f"Spec Kit amendment bridge error: {error}"); return 2


if __name__ == "__main__":
    raise SystemExit(main())
