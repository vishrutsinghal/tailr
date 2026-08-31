#!/usr/bin/env python3
"""Capture a Debug Harness failure intake, fingerprint, and code-path map.

Scope: Code, Architecture, Database, and API-integration domains only. Cloud,
Security, and Network domains are explicitly deferred (see DEBUG-HARNESS.md
Section 7.7) and are always reported as `domains_not_investigated`.
"""
from __future__ import annotations

import argparse
import hashlib
import importlib.util
import json
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parents[1]
SUPPORTED_DOMAINS = {"code", "architecture", "database", "api-integration"}
ALL_DOMAINS = {"code", "architecture", "database", "cloud-infrastructure", "security", "api-integration", "network"}


def load(name: str, filename: str) -> Any:
    spec = importlib.util.spec_from_file_location(name, ROOT / "scripts" / filename)
    assert spec and spec.loader
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


L = load("debug_intake_ledger", "run-ledger.py")
GRAPH = load("debug_intake_graph", "code-graph-mapper.py")
PLANNING = load("debug_intake_planning", "planning-lock.py")
PRIVACY = load("debug_intake_privacy", "debug-privacy.py")
GOVERNANCE = load("debug_intake_governance", "debug-governance.py")


def debug_dir(root: Path, run_id: str) -> Path:
    return L.state_dir(root, run_id) / "debug"


def intake_path(root: Path, run_id: str) -> Path:
    return debug_dir(root, run_id) / "intake" / "debug-intake-v1.json"


def fingerprint_path(root: Path, run_id: str) -> Path:
    return debug_dir(root, run_id) / "fingerprint" / "failure-fingerprint-v1.json"


def canonical(value: Any) -> str:
    return json.dumps(value, sort_keys=True, separators=(",", ":"))


def code_graph_evidence(root: Path) -> dict[str, Any]:
    """Best-effort, read-only evidence from the existing Code Graph Mapper cache.

    Never triggers a fresh scan; if no cache exists, degrades honestly instead
    of guessing (DEBUG-HARNESS.md Section 7.4/19)."""
    path = GRAPH.cache_path(root, None)
    cache, error = GRAPH.load_cache(path)
    if cache is None:
        return {
            "available": False,
            "reason": error or "No Code Graph Mapper cache exists. Run `tailtrail graph refresh --root .` first.",
            "likely_path": [], "endpoints": [], "db_tables": [], "service_edges": [],
        }
    graph = cache.get("graph", {})
    return {
        "available": True,
        "reason": None,
        "likely_path": list(graph.get("suggested_read_order", []))[:10],
        "endpoints": graph.get("endpoints", [])[:20],
        "db_tables": graph.get("db_tables", [])[:20],
        "service_edges": graph.get("service_edges", [])[:20],
    }


def classify_domains(symptom: str, error_text: str, graph: dict[str, Any]) -> list[str]:
    """Rank candidate domains from cheap, zero-risk evidence only.

    Outward-elimination order (DEBUG-HARNESS.md Section 7.3): code is always a
    candidate; architecture/database/api-integration are added only when the
    existing cache or the reported text already points that way."""
    text = f"{symptom}\n{error_text}".lower()
    candidates: list[str] = ["code"]
    if graph["service_edges"] or any(term in text for term in ("service", "microservice", "boundary", "layer")):
        candidates.append("architecture")
    if graph["db_tables"] or any(term in text for term in ("database", "sql", "query", "table", "migration", "transaction")):
        candidates.append("database")
    if graph["endpoints"] or any(term in text for term in ("api", "endpoint", "route", "contract", "http", "request")):
        candidates.append("api-integration")
    return list(dict.fromkeys(candidates))


def open_intake(root: Path, run_id: str | None, symptom: str, error_text: str | None, command_text: str | None, attach: bool) -> dict[str, Any]:
    root = root.resolve()
    if run_id is None:
        if attach:
            raise ValueError("--attach requires an explicit --run-id")
        run_id = PLANNING.create(root, symptom, run_id=None)["run_id"]
    else:
        manifest_path = L.state_dir(root, run_id) / "manifest.json"
        if not manifest_path.exists():
            PLANNING.create(root, symptom, run_id=run_id)
        elif not attach:
            raise ValueError(f"run `{run_id}` already exists; pass --attach to open a debug investigation on it")
    graph = code_graph_evidence(root)
    candidate_domains = classify_domains(symptom, error_text or "", graph)
    not_investigated = sorted(ALL_DOMAINS - SUPPORTED_DOMAINS)
    privacy = PRIVACY.inspect({"reported_symptom": symptom, "attached_error": error_text, "attached_command": command_text})
    intake = {
        "schema_version": "1",
        "type": "tailtrail-debug-intake",
        "run_id": run_id,
        "reported_symptom": symptom,
        "attached_error": error_text,
        "attached_command": command_text,
        "reproduction_frequency": "unknown",
        "safety_impact": "unknown",
        "known_vs_assumed": {"known": [symptom], "assumed": []},
        "likely_path": graph["likely_path"],
        "candidate_domains": candidate_domains,
        "domains_eliminated": [],
        "domains_not_investigated": not_investigated,
        "created_at": L.utc_now(),
        "privacy": privacy,
        "evidence_class": "local-sensitive-exact",
        "portable": False,
    }
    L.atomic_json(intake_path(root, run_id), intake)
    symptom_hash = hashlib.sha256(symptom.encode("utf-8")).hexdigest()
    stack_signature = PRIVACY.hashed_lines(error_text)
    entry_point = graph["likely_path"][0] if graph["likely_path"] else None
    # Deliberately exclude run_id: the sanitized identity must match the same
    # failure across runs while every artifact still carries its owning run.
    fingerprint = hashlib.sha256(canonical({"symptom_hash": symptom_hash, "stack_signature_hashes": stack_signature, "entry_point": entry_point}).encode("utf-8")).hexdigest()
    fingerprint_record = {
        "schema_version": "1",
        "type": "tailtrail-failure-fingerprint",
        "run_id": run_id,
        "domain": candidate_domains[0] if candidate_domains else "unknown",
        "fingerprint": fingerprint,
        "symptom_hash": symptom_hash,
        "stack_signature_hashes": stack_signature,
        "entry_point": entry_point,
        "first_seen_at": L.utc_now(),
        "matched_learning_ids": [],
        "portable": True,
        "privacy": {"status": "sanitized", "raw_values": False, "detected_categories": privacy["categories"]},
    }
    L.atomic_json(fingerprint_path(root, run_id), fingerprint_record)
    L.append_event(root, run_id, "debug_intake_recorded", {"fingerprint": fingerprint, "candidate_domains": candidate_domains, "code_graph_available": graph["available"]})
    governance = GOVERNANCE.build(root, run_id)
    return {
        "intake": intake,
        "fingerprint": fingerprint_record,
        "code_graph_note": graph["reason"],
        "governance": governance,
        "next_investigation": "Approve a reproduction contract before any code changes (tailtrail debug reproduction draft/approve).",
    }


def show(root: Path, run_id: str) -> dict[str, Any]:
    root = root.resolve()
    path = intake_path(root, run_id)
    if not path.is_file():
        raise ValueError(f"no debug intake recorded for run `{run_id}`")
    fp_path = fingerprint_path(root, run_id)
    return {"intake": json.loads(path.read_text(encoding="utf-8")), "fingerprint": json.loads(fp_path.read_text(encoding="utf-8")) if fp_path.is_file() else None}


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    sub = parser.add_subparsers(dest="action", required=True)
    open_parser = sub.add_parser("open")
    open_parser.add_argument("--root", type=Path, default=Path.cwd())
    open_parser.add_argument("--run-id", default=None)
    open_parser.add_argument("--symptom", required=True)
    open_parser.add_argument("--error", type=Path, default=None)
    open_parser.add_argument("--command", default=None)
    open_parser.add_argument("--attach", action="store_true")
    show_parser = sub.add_parser("show")
    show_parser.add_argument("--root", type=Path, default=Path.cwd())
    show_parser.add_argument("--run-id", required=True)
    args = parser.parse_args()
    try:
        if args.action == "open":
            error_text = args.error.read_text(encoding="utf-8") if args.error else None
            result = open_intake(args.root, args.run_id, args.symptom, error_text, args.command, args.attach)
        else:
            result = show(args.root, args.run_id)
        print(json.dumps(result, indent=2, sort_keys=True))
        return 0
    except (OSError, ValueError, json.JSONDecodeError) as error:
        print(f"Debug intake error: {error}")
        return 2


if __name__ == "__main__":
    raise SystemExit(main())
