#!/usr/bin/env python3
"""Draft, approve, invalidate, and review Phase 1 change-intent anchors."""

from __future__ import annotations

import argparse
import hashlib
import importlib.util
import json
from pathlib import Path
from typing import Any


ROOT = Path(__file__).resolve().parents[1]


def load_ledger() -> Any:
    spec = importlib.util.spec_from_file_location("tailtrail_run_ledger", ROOT / "scripts" / "run-ledger.py")
    if spec is None or spec.loader is None: raise RuntimeError("run-ledger.py is unavailable")
    module = importlib.util.module_from_spec(spec); spec.loader.exec_module(module); return module


LEDGER = load_ledger()
KINDS = {"change", "preserve", "constraint", "safety", "decision", "debug-investigation"}
STATUSES = {"proposed", "approved", "revoked", "blocked", "validated"}
MATERIAL_INVALIDATIONS = {"scope", "public-contract", "dependency", "data-model", "security", "acceptance-criteria", "preserve-rule"}


def canonical(value: Any) -> str:
    return json.dumps(value, sort_keys=True, separators=(",", ":"))


def fingerprint(value: Any) -> str:
    return "sha256:" + hashlib.sha256(canonical(value).encode()).hexdigest()


def anchor_dir(root: Path, run_id: str) -> Path:
    return LEDGER.state_dir(root, run_id) / "anchors"


def uid(run_id: str, statement: str) -> str:
    return "req-" + hashlib.sha256(f"{run_id}:{statement.strip()}".encode()).hexdigest()[:12]


def validate_requirement(row: dict[str, Any]) -> list[str]:
    required = {"requirement_uid", "display_id", "kind", "statement", "acceptance_criteria", "preserve_rules", "likely_paths", "evidence_plan", "status"}
    issues = [f"missing `{field}`" for field in sorted(required - set(row))]
    if row.get("kind") not in KINDS: issues.append("kind is not allowed")
    if row.get("status") not in STATUSES: issues.append("status is not allowed")
    for field in ("acceptance_criteria", "preserve_rules", "likely_paths", "evidence_plan"):
        if field in row and not isinstance(row[field], list): issues.append(f"{field} must be a list")
    return issues


def normalize_draft(run_id: str, source: dict[str, Any], version: int) -> dict[str, Any]:
    rows = source.get("requirements", [])
    if not isinstance(rows, list) or not rows: raise ValueError("draft needs at least one requirement row")
    normalized: list[dict[str, Any]] = []
    seen: set[str] = set()
    for index, raw in enumerate(rows, 1):
        if not isinstance(raw, dict): raise ValueError(f"requirement {index} is not an object")
        statement = str(raw.get("statement", "")).strip()
        if not statement: raise ValueError(f"requirement {index} needs a statement")
        row = {"requirement_uid": raw.get("requirement_uid") or uid(run_id, statement), "display_id": raw.get("display_id") or f"REQ-{index:02d}", "kind": raw.get("kind", "change"), "statement": statement, "acceptance_criteria": raw.get("acceptance_criteria", []), "preserve_rules": raw.get("preserve_rules", []), "likely_paths": raw.get("likely_paths", []), "evidence_plan": raw.get("evidence_plan", []), "validation_contract": raw.get("validation_contract", {"state": "required", "tiers": ["unit"]}), "architecture_contract": raw.get("architecture_contract", {"required_paths": [], "protected_paths": [], "forbidden_imports": []}), "behavior_contract": raw.get("behavior_contract", {"scenarios": []}), "maintainability_contract": raw.get("maintainability_contract", {"rules": []}), "ui_contract": raw.get("ui_contract", {}), "status": "proposed"}
        if isinstance(raw.get("source_reference"), dict):
            row["source_reference"] = raw["source_reference"]
        issues = validate_requirement(row)
        if issues: raise ValueError(f"requirement {index}: " + "; ".join(issues))
        if row["requirement_uid"] in seen: raise ValueError(f"duplicate requirement_uid `{row['requirement_uid']}`")
        seen.add(row["requirement_uid"]); normalized.append(row)
    return {"schema_version": "1", "type": "tailtrail-change-intent-anchor", "run_id": run_id, "proposal_version": version, "goal": str(source.get("goal", "")).strip(), "requirements": normalized, "material_invalidation_rules": sorted(MATERIAL_INVALIDATIONS), "status": "draft"}


def drafts(directory: Path) -> list[Path]:
    return sorted(directory.glob("draft-v*.json"))


def draft(root: Path, run_id: str, input_path: Path) -> dict[str, Any]:
    source = json.loads(input_path.read_text(encoding="utf-8"))
    directory = anchor_dir(root, run_id); version = len(drafts(directory)) + 1
    anchor = normalize_draft(run_id, source, version)
    anchor["fingerprint"] = fingerprint(anchor)
    path = directory / f"draft-v{version}.json"; LEDGER.atomic_json(path, anchor)
    LEDGER.append_event(root, run_id, "anchor_drafted", {"proposal_version": version, "fingerprint": anchor["fingerprint"], "requirements": [row["requirement_uid"] for row in anchor["requirements"]]})
    return {"path": path.as_posix(), **anchor}


def latest_draft(root: Path, run_id: str) -> tuple[Path, dict[str, Any]]:
    available = drafts(anchor_dir(root, run_id))
    if not available: raise ValueError("no draft exists for this run")
    path = available[-1]; return path, json.loads(path.read_text(encoding="utf-8"))


def approve(root: Path, run_id: str) -> dict[str, Any]:
    _, anchor = latest_draft(root, run_id)
    approved_path = anchor_dir(root, run_id) / "approved-v1.json"
    if approved_path.exists(): raise ValueError("approved anchor is immutable; invalidate and draft a new run/version")
    anchor["status"] = "approved"
    for row in anchor["requirements"]: row["status"] = "approved"
    anchor["approved_fingerprint"] = fingerprint({key: value for key, value in anchor.items() if key != "fingerprint"})
    LEDGER.atomic_json(approved_path, anchor)
    LEDGER.append_event(root, run_id, "anchor_approved", {"path": approved_path.relative_to(root).as_posix(), "fingerprint": anchor["approved_fingerprint"], "requirements": [row["requirement_uid"] for row in anchor["requirements"]]})
    return {"path": approved_path.as_posix(), **anchor}


def feedback(root: Path, run_id: str, feedback_json: str) -> dict[str, Any]:
    _, anchor = latest_draft(root, run_id)
    feedback_rows = json.loads(feedback_json)
    if not isinstance(feedback_rows, list): raise ValueError("feedback must be a JSON list")
    expected = {row["requirement_uid"] for row in anchor["requirements"]}
    provided = {str(row.get("requirement_uid", "")) for row in feedback_rows if isinstance(row, dict)}
    if provided != expected: raise ValueError("feedback must include exactly one row for every requirement_uid")
    for row in feedback_rows:
        if row.get("decision") not in {"approve", "reject"}: raise ValueError("feedback decision must be approve or reject")
        if row["decision"] == "reject" and not str(row.get("comment", "")).strip(): raise ValueError("rejected requirement needs a comment")
    prior = [event for event in LEDGER.read_events(LEDGER.state_dir(root, run_id) / "events.jsonl") if event["event_type"] == "proposal_rejected"]
    rejected = [row for row in feedback_rows if row["decision"] == "reject"]
    escalation = "none" if not rejected else ("aidlc-requirements-required" if len(prior) >= 1 else "ask-targeted-questions-or-offer-aidlc")
    payload = {"proposal_version": anchor["proposal_version"], "feedback": feedback_rows, "rejected_requirement_uids": [row["requirement_uid"] for row in rejected], "next_requirement_mode": escalation}
    if rejected:
        LEDGER.append_event(root, run_id, "proposal_rejected", payload)
    return payload


def invalidate(root: Path, run_id: str, reason: str) -> dict[str, Any]:
    if reason not in MATERIAL_INVALIDATIONS: raise ValueError("reason must be a material invalidation rule")
    path = anchor_dir(root, run_id) / "approved-v1.json"
    if not path.exists(): raise ValueError("no approved anchor exists")
    payload = {"reason": reason, "approved_path": path.relative_to(root).as_posix(), "approved_fingerprint": json.loads(path.read_text(encoding="utf-8"))["approved_fingerprint"]}
    LEDGER.append_event(root, run_id, "anchor_invalidated", payload); return payload


def graph_receipt(root: Path, run_id: str, requirement_uids: list[str], paths: list[str], evidence_label: str) -> dict[str, Any]:
    approved_path = anchor_dir(root, run_id) / "approved-v1.json"
    if not approved_path.exists(): raise ValueError("approve an anchor before recording graph evidence")
    approved = json.loads(approved_path.read_text(encoding="utf-8"))
    known = {row["requirement_uid"] for row in approved["requirements"]}
    if not requirement_uids or not set(requirement_uids).issubset(known): raise ValueError("receipt must reference approved requirement_uids only")
    if evidence_label not in {"local-ast", "heuristic", "provider-backed"}: raise ValueError("unsupported graph evidence label")
    payload = {"requirement_uids": requirement_uids, "paths": paths, "evidence_label": evidence_label, "rule": "selected symbols/callers/tests only; no repository graph snapshot"}
    return LEDGER.append_event(root, run_id, "graph_receipt", payload)


def main() -> int:
    parser = argparse.ArgumentParser(description="Manage immutable TailTrail change-intent anchors.")
    sub = parser.add_subparsers(dest="command", required=True)
    for name in ("draft", "approve", "feedback", "invalidate", "graph-receipt", "show"):
        item = sub.add_parser(name); item.add_argument("--root", type=Path, default=Path.cwd()); item.add_argument("--run-id", required=True)
        if name == "draft": item.add_argument("--input", type=Path, required=True)
        if name == "feedback": item.add_argument("--feedback", required=True)
        if name == "invalidate": item.add_argument("--reason", choices=sorted(MATERIAL_INVALIDATIONS), required=True)
        if name == "graph-receipt":
            item.add_argument("--requirement-uid", action="append", required=True)
            item.add_argument("--path", action="append", default=[])
            item.add_argument("--evidence-label", choices=("local-ast", "heuristic", "provider-backed"), required=True)
    args = parser.parse_args(); root = args.root.resolve()
    try:
        if args.command == "draft": result = draft(root, args.run_id, args.input)
        elif args.command == "approve": result = approve(root, args.run_id)
        elif args.command == "feedback": result = feedback(root, args.run_id, args.feedback)
        elif args.command == "invalidate": result = invalidate(root, args.run_id, args.reason)
        elif args.command == "graph-receipt": result = graph_receipt(root, args.run_id, args.requirement_uid, args.path, args.evidence_label)
        else: _, result = latest_draft(root, args.run_id)
        print(json.dumps(result, indent=2, sort_keys=True)); return 0
    except (ValueError, OSError, json.JSONDecodeError) as error:
        print(f"Change intent anchor error: {error}"); return 2


if __name__ == "__main__":
    raise SystemExit(main())
