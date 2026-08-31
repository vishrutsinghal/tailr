#!/usr/bin/env python3
"""Create a versioned Debug Harness project-orientation projection.

The projection reuses the existing Code Graph Mapper cache and its metadata
inventory. It never parses source, refreshes the graph, executes project
commands, or advances the DWR stage by itself.
"""
from __future__ import annotations

import argparse
import hashlib
import importlib.util
import json
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parents[1]
STAGE_ID = "d-03-project-orientation"


def load(name: str, filename: str) -> Any:
    spec = importlib.util.spec_from_file_location(name, ROOT / "scripts" / filename)
    assert spec and spec.loader
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


LEDGER = load("debug_orientation_ledger", "run-ledger.py")
GRAPH = load("debug_orientation_graph", "code-graph-mapper.py")


def _canonical(value: Any) -> str:
    return json.dumps(value, sort_keys=True, separators=(",", ":"))


def _fingerprint(value: Any) -> str:
    return "sha256:" + hashlib.sha256(_canonical(value).encode("utf-8")).hexdigest()


def _directory(root: Path, run_id: str) -> Path:
    return LEDGER.state_dir(root.resolve(), run_id) / "debug" / "orientation"


def orientation_path(root: Path, run_id: str) -> Path:
    return _directory(root, run_id) / "orientation-v1.json"


def _read(path: Path, expected_type: str) -> dict[str, Any]:
    if not path.is_file():
        raise ValueError(f"required debug artifact does not exist: {path.name}")
    value = json.loads(path.read_text(encoding="utf-8"))
    if not isinstance(value, dict) or value.get("type") != expected_type:
        raise ValueError(f"debug artifact has invalid type: {path.name}")
    return value


def _handoff(root: Path, run_id: str) -> dict[str, Any]:
    path = LEDGER.state_dir(root, run_id) / "debug" / "investigation-handoff-v1.json"
    value = _read(path, "tailtrail-debug-investigation-handoff")
    runtime = value.get("workflow_runtime")
    if not isinstance(runtime, dict) or runtime.get("compiler", {}).get("template_id") != "debug-investigation":
        raise ValueError("debug orientation requires the native debug-investigation workflow")
    return value


def _start_targets(root: Path, run_id: str) -> list[str]:
    path = LEDGER.state_dir(root, run_id) / "planning" / "start-report-v1.json"
    if not path.is_file(): return []
    saved = json.loads(path.read_text(encoding="utf-8")); report = saved.get("report", saved)
    navigator = report.get("navigator", {}) if isinstance(report, dict) else {}
    rows = navigator.get("likely_impacted_files", []) if isinstance(navigator, dict) else []
    paths = [str(row.get("path")) for row in rows if isinstance(row, dict) and str(row.get("path", "")).strip()]
    return list(dict.fromkeys(paths))[:20]


def _cache(root: Path, targets: list[str]) -> tuple[Path, dict[str, Any] | None, dict[str, Any]]:
    shared = root / "tailtrail-meta" / "code-graph-cache.json"
    local = root / ".tailtrail" / "code-graph-cache.json"
    path = shared if shared.is_file() else local
    payload, error = GRAPH.load_cache(path)
    if payload is None:
        status = {"status": "missing" if error == "missing" else "invalid", "reasons": [error or "missing"], "scope": targets}
        return path, None, status
    entries = GRAPH.cache_entries(payload) if hasattr(GRAPH, "cache_entries") else ([*payload.get("entries", [])] if isinstance(payload.get("entries"), list) else [payload])
    requested = set(targets)
    matching = [row for row in entries if isinstance(row, dict) and (not requested or requested.intersection({str(item) for item in row.get("scope", [])}))]
    entry = matching[0] if matching else None
    if entry is None:
        return path, None, {"status": "missing", "reasons": ["No saved graph entry covers the debug target scope."], "scope": targets}
    return path, entry, GRAPH.status_for(root, entry, targets)


def _path_rows(root: Path, cache: dict[str, Any], freshness: str) -> list[dict[str, str]]:
    if freshness != "fresh": return []
    rows: list[dict[str, str]] = []
    for group in ("source_files", "watch_files"):
        values = cache.get(group, {})
        if not isinstance(values, dict): continue
        for path, metadata in values.items():
            if not isinstance(metadata, dict) or not (root / path).is_file(): continue
            digest = metadata.get("sha256")
            if isinstance(digest, str) and digest:
                rows.append({"path": str(path), "evidence": "confirmed-local-path-and-hash", "sha256": digest})
    return rows[:50]


def _hint(entry: Any, key: str, fallback: str = "") -> str:
    return str(entry.get(key, fallback)) if isinstance(entry, dict) else str(entry)


def _graph_hints(cache: dict[str, Any]) -> dict[str, list[Any]]:
    graph = cache.get("graph", {}) if isinstance(cache.get("graph"), dict) else {}
    endpoints = [{"file": _hint(row, "file"), "line": _hint(row, "line", "?"), "method": _hint(row, "method"), "route": _hint(row, "route"), "evidence": "heuristic"} for row in graph.get("endpoints", []) if isinstance(row, dict)]
    tables = [{"file": _hint(row, "file"), "line": _hint(row, "line", "?"), "table": _hint(row, "table"), "evidence": "heuristic"} for row in graph.get("db_tables", []) if isinstance(row, dict)]
    services = [{"file": _hint(row, "file"), "line": _hint(row, "line", "?"), "target": _hint(row, "target"), "evidence": "heuristic"} for row in graph.get("service_edges", []) if isinstance(row, dict)]
    return {
        "suggested_read_order": [str(item) for item in graph.get("suggested_read_order", [])][:30],
        "likely_callers": [str(item) for item in graph.get("likely_callers", [])][:30],
        "likely_tests": [str(item) for item in graph.get("likely_tests", [])][:30],
        "nearby_manifests": [str(item) for item in graph.get("nearby_manifests", [])][:30],
        "endpoints": endpoints[:30], "database_boundaries": tables[:30], "service_edges": services[:30],
    }


def _refresh(root: Path, targets: list[str], status: dict[str, Any]) -> dict[str, Any]:
    reasons = [str(item) for item in status.get("reasons", [])]
    if status.get("status") == "fresh":
        return {"state": "not-needed", "kind": "reuse", "command": None, "reasons": reasons}
    inventory_only = bool(reasons) and all("inventory" in item.lower() for item in reasons)
    args = " ".join(f'--changed "{path}"' for path in targets[:10])
    command = "python3 scripts/tailtrail.py graph refresh --root ." + (f" {args}" if args else "")
    return {"state": "approval-required", "kind": "incremental" if inventory_only else "bounded-refresh", "command": command, "reasons": reasons}


def create(root: Path, run_id: str) -> dict[str, Any]:
    root = root.resolve(); handoff = _handoff(root, run_id)
    approved = _read(root / handoff["reproduction_contract"], "tailtrail-reproduction-contract")
    workflow_id = str(handoff["workflow_runtime"]["workflow_id"])
    from workflow_runtime import state as workflow_state
    view = workflow_state.show(root, workflow_id)
    reproduction_state = view.get("stage_states", {}).get("d-02-reproduction", {}).get("status", "pending")
    targets = _start_targets(root, run_id); cache_path, cache, status = _cache(root, targets)
    cache_state = str(status.get("status", "invalid")); graph = cache or {}
    hints = _graph_hints(graph) if cache else {key: [] for key in ("suggested_read_order", "likely_callers", "likely_tests", "nearby_manifests", "endpoints", "database_boundaries", "service_edges")}
    refresh = _refresh(root, targets, status)
    orientation_status = "awaiting-reproduction-evidence" if reproduction_state not in {"passed", "skipped"} else ("ready" if cache_state == "fresh" else "refresh-required")
    prior = orientation_path(root, run_id)
    prior_value = json.loads(prior.read_text(encoding="utf-8")) if prior.is_file() else None
    revision = int((prior_value or {}).get("revision", 0)) + 1
    stable = {
        "run_id": run_id, "workflow_id": workflow_id, "stage_id": STAGE_ID,
        "requirement_uids": [str(handoff["requirement_uid"])], "reproduction_revision": int(approved["revision"]),
        "reproduction_stage_status": reproduction_state, "status": orientation_status,
        "target_paths": targets,
        "cache": {"status": cache_state, "artifact_ref": cache_path.relative_to(root).as_posix() if cache_path.is_file() else None, "schema_version": graph.get("schema_version"), "inventory_fingerprint": (graph.get("inventory") or {}).get("fingerprint"), "confidence": (graph.get("graph") or {}).get("confidence"), "reasons": [str(item) for item in status.get("reasons", [])]},
        "confirmed_paths": _path_rows(root, graph, cache_state), "heuristic_candidates": hints,
        "refresh_proposal": refresh,
        "unsupported_domains": ["cloud-infrastructure", "network", "security"],
        "evidence_labels": {"confirmed-local-path-and-hash": "Path existence and saved SHA-256 match current local files; this does not prove runtime behavior.", "heuristic": "Local Code Graph pattern evidence; inspect exact source before a conclusion or edit."},
        "adapter_handoff": {"stage_id": STAGE_ID, "adapter_id": "graph-discovery", "graph_ref": f".tailtrail/runs/{run_id}/debug/orientation/orientation-v1.json", "graph_version": str(graph.get("schema_version", "unavailable")), "inventory_fingerprint": (graph.get("inventory") or {}).get("fingerprint") or _fingerprint(None), "freshness": cache_state, "likely_callers": hints["likely_callers"], "likely_tests": hints["likely_tests"], "read_order": hints["suggested_read_order"], "evidence_label": "local-evidence"},
        "boundary": "Local graph-cache orientation only. No source was parsed or edited, no graph refresh or project command ran, no hypothesis was proven, and the DWR stage was not advanced.",
    }
    payload = {"schema_version": "1", "type": "tailtrail-debug-orientation", "revision": revision, **stable, "orientation_fingerprint": _fingerprint(stable)}
    archive = _directory(root, run_id) / f"orientation-v{revision}.json"
    LEDGER.atomic_json(archive, payload); LEDGER.atomic_json(prior, payload)
    LEDGER.append_event(root, run_id, "debug_orientation_recorded", {"artifact": archive.relative_to(root).as_posix(), "workflow_id": workflow_id, "stage_id": STAGE_ID, "status": orientation_status, "cache_status": cache_state, "orientation_fingerprint": payload["orientation_fingerprint"]})
    return {**payload, "artifact": archive.relative_to(root).as_posix()}


def show(root: Path, run_id: str) -> dict[str, Any]:
    root = root.resolve(); path = orientation_path(root, run_id)
    if not path.is_file(): raise ValueError(f"no debug orientation exists for run `{run_id}`")
    return {**json.loads(path.read_text(encoding="utf-8")), "artifact": path.relative_to(root).as_posix()}


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__); sub = parser.add_subparsers(dest="action", required=True)
    for action in ("create", "show"):
        item = sub.add_parser(action); item.add_argument("--root", type=Path, default=Path.cwd()); item.add_argument("--run-id", required=True)
    args = parser.parse_args()
    try:
        result = create(args.root, args.run_id) if args.action == "create" else show(args.root, args.run_id)
        print(json.dumps(result, indent=2, sort_keys=True)); return 0
    except (OSError, ValueError, json.JSONDecodeError) as error:
        print(f"Debug orientation error: {error}"); return 2


if __name__ == "__main__":
    raise SystemExit(main())
