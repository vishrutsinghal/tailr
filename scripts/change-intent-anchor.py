#!/usr/bin/env python3
"""Draft, approve, invalidate, and review Phase 1 change-intent anchors."""

from __future__ import annotations

import argparse
import copy
import hashlib
import importlib.util
import json
import re
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
PATH_ROLES = {"implementation-owner", "proof-only", "inspection-only", "unknown"}


def canonical(value: Any) -> str:
    return json.dumps(value, sort_keys=True, separators=(",", ":"))


def fingerprint(value: Any) -> str:
    return "sha256:" + hashlib.sha256(canonical(value).encode()).hexdigest()


def anchor_dir(root: Path, run_id: str) -> Path:
    return LEDGER.state_dir(root, run_id) / "anchors"


def uid(run_id: str, statement: str) -> str:
    return "req-" + hashlib.sha256(f"{run_id}:{statement.strip()}".encode()).hexdigest()[:12]


def normalize_likely_path_entry(item: Any) -> str | dict[str, str]:
    """Accept a plain path string (the original shape) or a {path, role} object.

    A plain string passes through untouched -- every existing caller and
    every anchor already on disk keeps its exact original shape. Only a
    caller that opts in by supplying an object gets the validated path+role
    form; nothing forces an upgrade on callers that don't ask for one.
    """
    if isinstance(item, str):
        if not item.strip(): raise ValueError("likely_paths entry must be a non-empty string")
        return item
    if isinstance(item, dict):
        path = item.get("path")
        if not isinstance(path, str) or not path.strip(): raise ValueError("likely_paths object entry needs a non-empty `path`")
        role = item.get("role", "unknown")
        if role not in PATH_ROLES: raise ValueError(f"likely_paths role `{role}` must be one of {sorted(PATH_ROLES)}")
        return {"path": path, "role": role}
    raise ValueError("likely_paths entry must be a path string or a {path, role} object")


def normalize_likely_paths(raw: Any) -> list[str | dict[str, str]]:
    if not isinstance(raw, list): raise ValueError("likely_paths must be a list")
    normalized: list[str | dict[str, str]] = []
    seen: set[str] = set()
    for item in raw:
        entry = normalize_likely_path_entry(item)
        path = entry if isinstance(entry, str) else entry["path"]
        if path in seen: continue
        seen.add(path); normalized.append(entry)
    return normalized


def validate_requirement(row: dict[str, Any]) -> list[str]:
    required = {"requirement_uid", "display_id", "kind", "statement", "acceptance_criteria", "preserve_rules", "likely_paths", "evidence_plan", "status"}
    issues = [f"missing `{field}`" for field in sorted(required - set(row))]
    if row.get("kind") not in KINDS: issues.append("kind is not allowed")
    if row.get("status") not in STATUSES: issues.append("status is not allowed")
    for field in ("acceptance_criteria", "preserve_rules", "likely_paths", "evidence_plan"):
        if field in row and not isinstance(row[field], list): issues.append(f"{field} must be a list")
    if "requirement_id" in row and not re.fullmatch(r"req-frame-[a-f0-9]{12}", str(row["requirement_id"])):
        issues.append("requirement_id must be a stable requirement-frame ID")
    if "query_terms" in row and (
        not isinstance(row["query_terms"], list)
        or any(not isinstance(term, str) or len(term) < 3 for term in row["query_terms"])
        or len(set(row["query_terms"])) != len(row["query_terms"])
    ):
        issues.append("query_terms must be unique strings of at least three characters")
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
        try:
            likely_paths = normalize_likely_paths(raw.get("likely_paths", []))
        except ValueError as error:
            raise ValueError(f"requirement {index}: {error}") from error
        row = {"requirement_uid": raw.get("requirement_uid") or uid(run_id, statement), "display_id": raw.get("display_id") or f"REQ-{index:02d}", "kind": raw.get("kind", "change"), "statement": statement, "acceptance_criteria": raw.get("acceptance_criteria", []), "preserve_rules": raw.get("preserve_rules", []), "likely_paths": likely_paths, "evidence_plan": raw.get("evidence_plan", []), "validation_contract": raw.get("validation_contract", {"state": "required", "tiers": ["unit"]}), "architecture_contract": raw.get("architecture_contract", {"required_paths": [], "protected_paths": [], "forbidden_imports": []}), "behavior_contract": raw.get("behavior_contract", {"scenarios": []}), "maintainability_contract": raw.get("maintainability_contract", {"rules": []}), "ui_contract": raw.get("ui_contract", {}), "status": "proposed"}
        if raw.get("requirement_id"):
            row["requirement_id"] = str(raw["requirement_id"])
        if raw.get("query_terms"):
            row["query_terms"] = list(raw["query_terms"])
        if isinstance(raw.get("source_reference"), dict):
            row["source_reference"] = raw["source_reference"]
        if isinstance(raw.get("scope_evidence"), dict):
            row["scope_evidence"] = raw["scope_evidence"]
        issues = validate_requirement(row)
        if issues: raise ValueError(f"requirement {index}: " + "; ".join(issues))
        if row["requirement_uid"] in seen: raise ValueError(f"duplicate requirement_uid `{row['requirement_uid']}`")
        seen.add(row["requirement_uid"]); normalized.append(row)
    result = {"schema_version": "1", "type": "tailtrail-change-intent-anchor", "run_id": run_id, "proposal_version": version, "goal": str(source.get("goal", "")).strip(), "requirements": normalized, "material_invalidation_rules": sorted(MATERIAL_INVALIDATIONS), "status": "draft"}
    if isinstance(source.get("scope_decision"), dict):
        result["scope_decision"] = source["scope_decision"]
    return result


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


def approved_versions(directory: Path) -> list[Path]:
    return sorted(directory.glob("approved-v*.json"), key=lambda path: int(path.stem.rsplit("v", 1)[-1]))


def latest_approved(root: Path, run_id: str) -> tuple[Path, dict[str, Any]]:
    available = approved_versions(anchor_dir(root, run_id))
    if not available: raise ValueError("no approved anchor exists for this run")
    path = available[-1]
    return path, json.loads(path.read_text(encoding="utf-8"))


def correct(root: Path, run_id: str, requirement_uid: str, likely_paths: list[Any], reason: str) -> dict[str, Any]:
    """Write a new, higher-numbered approved anchor snapshot with one requirement's scope corrected.

    Every existing approved-vN.json file is immutable and untouched by this
    function -- it only ever writes a brand-new file at the next version
    number, the same append-only pattern workflow_runtime/freshness.py
    already uses for debug reproduction proposals. The "why" for this
    correction is not duplicated into a new ledger event here: the
    evidence-backed decision that led to it (a run's own fresh scope
    re-check and host decision) is already recorded durably by whatever
    caller invoked this -- this function's only job is to make the
    corrected scope the durable, readable record for later implementation
    and projection, not to re-assert the reasoning behind it.

    `likely_paths` accepts a mix of plain path strings and {path, role}
    objects (see `normalize_likely_paths`); a caller correcting an older,
    plain-string-only approved anchor keeps working unchanged.
    """
    if not str(reason).strip(): raise ValueError("correction requires a reason")
    corrected_paths = normalize_likely_paths(likely_paths)
    if not corrected_paths: raise ValueError("likely_paths must be a non-empty list of non-empty strings or {path, role} objects")
    base_path, base_anchor = latest_approved(root, run_id)
    base_version = int(base_path.stem.rsplit("v", 1)[-1])
    if not any(row["requirement_uid"] == requirement_uid for row in base_anchor["requirements"]):
        raise ValueError(f"requirement `{requirement_uid}` is not in the approved anchor")
    corrected = copy.deepcopy(base_anchor)
    row = next(item for item in corrected["requirements"] if item["requirement_uid"] == requirement_uid)
    previous_paths = normalize_likely_paths(row.get("likely_paths", []))
    if corrected_paths == previous_paths:
        raise ValueError("correction must change likely_paths; nothing to correct")
    row["likely_paths"] = corrected_paths
    corrections = list(corrected.get("corrections", []))
    corrections.append({
        "base_version": base_version,
        "requirement_uid": requirement_uid,
        "previous_likely_paths": previous_paths,
        "corrected_likely_paths": corrected_paths,
        "reason": reason.strip(),
        "created_at": LEDGER.utc_now(),
    })
    corrected["corrections"] = corrections
    corrected_path = anchor_dir(root, run_id) / f"approved-v{base_version + 1}.json"
    if corrected_path.exists(): raise ValueError(f"approved anchor version {base_version + 1} already exists")
    corrected["approved_fingerprint"] = fingerprint({key: value for key, value in corrected.items() if key not in {"fingerprint", "approved_fingerprint"}})
    LEDGER.atomic_json(corrected_path, corrected)
    return {"path": corrected_path.as_posix(), **corrected}


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
    for name in ("draft", "approve", "feedback", "invalidate", "graph-receipt", "correct", "show"):
        item = sub.add_parser(name); item.add_argument("--root", type=Path, default=Path.cwd()); item.add_argument("--run-id", required=True)
        if name == "draft": item.add_argument("--input", type=Path, required=True)
        if name == "feedback": item.add_argument("--feedback", required=True)
        if name == "invalidate": item.add_argument("--reason", choices=sorted(MATERIAL_INVALIDATIONS), required=True)
        if name == "graph-receipt":
            item.add_argument("--requirement-uid", action="append", required=True)
            item.add_argument("--path", action="append", default=[])
            item.add_argument("--evidence-label", choices=("local-ast", "heuristic", "provider-backed"), required=True)
        if name == "correct":
            item.add_argument("--requirement-uid", required=True)
            item.add_argument("--likely-path", action="append", required=True, help="Repeatable. A bare path (role defaults to `unknown`) or a JSON object like {\"path\": \"...\", \"role\": \"implementation-owner\"}.")
            item.add_argument("--reason", required=True)
    args = parser.parse_args(); root = args.root.resolve()
    try:
        if args.command == "draft": result = draft(root, args.run_id, args.input)
        elif args.command == "approve": result = approve(root, args.run_id)
        elif args.command == "feedback": result = feedback(root, args.run_id, args.feedback)
        elif args.command == "invalidate": result = invalidate(root, args.run_id, args.reason)
        elif args.command == "graph-receipt": result = graph_receipt(root, args.run_id, args.requirement_uid, args.path, args.evidence_label)
        elif args.command == "correct":
            likely_paths: list[Any] = [json.loads(value) if value.strip().startswith("{") else value for value in args.likely_path]
            result = correct(root, args.run_id, args.requirement_uid, likely_paths, args.reason)
        else: _, result = latest_draft(root, args.run_id)
        print(json.dumps(result, indent=2, sort_keys=True)); return 0
    except (ValueError, OSError, json.JSONDecodeError) as error:
        print(f"Change intent anchor error: {error}"); return 2


if __name__ == "__main__":
    raise SystemExit(main())
