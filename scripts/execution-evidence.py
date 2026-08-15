#!/usr/bin/env python3
"""Append and inspect sanitized, requirement-linked execution evidence."""
from __future__ import annotations

import argparse
import hashlib
import importlib.util
import json
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parents[1]
KINDS = {"source-edit", "command-result", "harness-result", "drift-finding", "ci-receipt"}


def load(name: str, filename: str) -> Any:
    spec = importlib.util.spec_from_file_location(name, ROOT / "scripts" / filename)
    module = importlib.util.module_from_spec(spec); assert spec and spec.loader; spec.loader.exec_module(module); return module


L = load("execution_evidence_ledger", "run-ledger.py")
LOCK = load("execution_evidence_lock", "planning-lock.py")
CONTRACT = load("execution_evidence_contract", "closure-contract.py")


def directory(root: Path, run_id: str) -> Path: return L.state_dir(root, run_id) / "execution"
def stream(root: Path, run_id: str) -> Path: return directory(root, run_id) / "evidence-stream.jsonl"
def canonical(value: Any) -> str: return json.dumps(value, sort_keys=True, separators=(",", ":"))


def validate(root: Path, run_id: str, event: Any) -> dict[str, Any]:
    if not isinstance(event, dict): raise ValueError("execution evidence must be a JSON object")
    allowed = {"kind", "requirement_uids", "changed_paths", "tier", "command_label", "command", "outcome", "environment", "asserted_behavior", "artifact", "evidence_label", "classification"}
    unknown = set(event) - allowed
    if unknown: raise ValueError(f"execution evidence has unsupported fields: {', '.join(sorted(unknown))}")
    kind = event.get("kind")
    if kind not in KINDS: raise ValueError("execution evidence kind is not supported")
    known = CONTRACT.approved_requirement_uids(root, run_id)
    uids = event.get("requirement_uids")
    if not isinstance(uids, list) or not uids or not all(isinstance(item, str) for item in uids): raise ValueError("requirement_uids must be a non-empty string list")
    if set(uids) - known: raise ValueError("execution evidence references unknown approved requirement UID(s)")
    changed = event.get("changed_paths", [])
    if not isinstance(changed, list) or not all(isinstance(item, str) for item in changed): raise ValueError("changed_paths must be a path list")
    normalized = {"schema_version": "1", "type": "tailtrail-execution-evidence", "run_id": run_id, "kind": kind, "requirement_uids": sorted(set(uids)), "changed_paths": sorted({CONTRACT.repository_path(item, "changed_paths item") for item in changed}), "evidence_boundary": "Host-supplied execution fact. TailTrail did not execute, reinterpret, or infer this event."}
    if kind == "source-edit" and not normalized["changed_paths"]: raise ValueError("source-edit evidence requires at least one changed path")
    if kind in {"command-result", "ci-receipt"}:
        receipt = CONTRACT.validate_receipt({key: event[key] for key in ("requirement_uids", "tier", "command_label", "command", "outcome", "environment", "asserted_behavior", "artifact", "evidence_label") if key in event}, known, 0)
        normalized.update(receipt)
    if kind in {"harness-result", "drift-finding"}:
        normalized["classification"] = CONTRACT.short_text(event.get("classification"), "classification")
    return normalized


def append(root: Path, run_id: str, event: Any, approved: bool) -> dict[str, Any]:
    if approved is not True: raise ValueError("execution evidence recording requires --approved")
    root = root.resolve(); LOCK.assert_write_allowed(root, run_id)
    normalized = validate(root, run_id, event); target = stream(root, run_id); target.parent.mkdir(parents=True, exist_ok=True)
    fingerprint = hashlib.sha256(canonical(normalized).encode()).hexdigest()[:16]
    existing = [json.loads(line) for line in target.read_text(encoding="utf-8").splitlines() if line.strip()] if target.is_file() else []
    prior = next((item for item in existing if item.get("fingerprint") == fingerprint), None)
    if prior: return {**prior, "reused": True, "artifact": target.relative_to(root).as_posix()}
    saved = {**normalized, "sequence": len(existing) + 1, "fingerprint": fingerprint}
    with target.open("a", encoding="utf-8") as handle: handle.write(canonical(saved) + "\n")
    index = {"schema_version": "1", "type": "tailtrail-execution-evidence-index", "run_id": run_id, "events": len(existing) + 1, "changed_paths": sorted({path for item in [*existing, saved] for path in item.get("changed_paths", [])}), "requirement_uids": sorted({uid for item in [*existing, saved] for uid in item.get("requirement_uids", [])}), "boundary": "Index of saved host-supplied evidence only; it does not evaluate completion."}
    L.atomic_json(target.parent / "receipt-index-v1.json", index)
    L.append_event(root, run_id, "execution_evidence_recorded", {"kind": saved["kind"], "fingerprint": fingerprint, "sequence": saved["sequence"], "artifact": target.relative_to(root).as_posix()})
    return {**saved, "reused": False, "artifact": target.relative_to(root).as_posix()}


def show(root: Path, run_id: str) -> dict[str, Any]:
    root = root.resolve(); target = stream(root, run_id)
    events = [json.loads(line) for line in target.read_text(encoding="utf-8").splitlines() if line.strip()] if target.is_file() else []
    return {"schema_version": "1", "type": "tailtrail-execution-evidence-log", "run_id": run_id, "events": events, "count": len(events), "boundary": "Read-only saved host evidence. It does not run commands or assess completion."}


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__); sub = parser.add_subparsers(dest="command", required=True)
    for command in ("record", "show"):
        item = sub.add_parser(command); item.add_argument("--root", type=Path, default=Path.cwd()); item.add_argument("--run-id", required=True)
        if command == "record": item.add_argument("--event", required=True); item.add_argument("--approved", action="store_true")
    args = parser.parse_args()
    try:
        result = append(args.root, args.run_id, json.loads(args.event), args.approved) if args.command == "record" else show(args.root, args.run_id)
        print(json.dumps(result, indent=2, sort_keys=True)); return 0
    except (OSError, ValueError, json.JSONDecodeError) as error: print(f"Execution evidence error: {error}"); return 2


if __name__ == "__main__": raise SystemExit(main())
