#!/usr/bin/env python3
"""Perform one explicitly approved, bounded, read-only plan investigation."""
from __future__ import annotations

import argparse
import hashlib
import importlib.util
import json
import re
from datetime import datetime, timezone
from pathlib import Path
from typing import Any


ROOT = Path(__file__).resolve().parents[1]
MAX_FILES = 12
MAX_BYTES_PER_FILE = 512 * 1024
BOUNDARY = (
    "Explicit approved read-only source inspection of already planned paths only; no source edit, test, scanner, "
    "build, package manager, Git, or plan mutation occurred."
)
SENSITIVE_NAMES = {".env", ".npmrc", ".pypirc", "id_rsa", "id_ed25519"}
SENSITIVE_SUFFIXES = {".pem", ".key", ".p12", ".pfx"}
SYMBOL_PATTERN = re.compile(
    r"^\s*(?:async\s+def|def|class|function|interface|type|export\s+(?:async\s+)?function|export\s+class|func)\s+([A-Za-z_][A-Za-z0-9_]{0,99})",
    re.MULTILINE,
)


def module(name: str, filename: str) -> Any:
    spec = importlib.util.spec_from_file_location(name, ROOT / "scripts" / filename)
    loaded = importlib.util.module_from_spec(spec)
    assert spec and spec.loader
    spec.loader.exec_module(loaded)
    return loaded


LOCK = module("planning_investigation_lock", "planning-lock.py")
LEDGER = module("planning_investigation_ledger", "run-ledger.py")
GRAPH_SCHEMA_VERSION = "1"


def utc_now() -> str:
    return datetime.now(timezone.utc).replace(microsecond=0).isoformat()


def saved_report(root: Path, run_id: str) -> dict[str, Any]:
    path = LOCK.active_start_report_path(root, run_id)
    if not path.is_file():
        raise ValueError(f"Start report for run `{run_id}` does not exist")
    payload = LOCK.read(path).get("report")
    if not isinstance(payload, dict):
        raise ValueError(f"Start report for run `{run_id}` is invalid")
    return payload


def planned_paths(report: dict[str, Any]) -> set[str]:
    allowed: set[str] = set()
    navigator = report.get("navigator") if isinstance(report.get("navigator"), dict) else {}
    for item in navigator.get("likely_impacted_files", []):
        if isinstance(item, dict) and isinstance(item.get("path"), str):
            allowed.add(item["path"].replace("\\", "/"))
    for item in navigator.get("requirement_matrix", []):
        if not isinstance(item, dict):
            continue
        for field in ("likely_paths", "paths", "proof_paths"):
            value = item.get(field)
            if isinstance(value, list):
                allowed.update(str(path).replace("\\", "/") for path in value if isinstance(path, str))
    source = report.get("spec_kit_source")
    if isinstance(source, dict):
        for row in source.get("requirements", []):
            if isinstance(row, dict):
                allowed.update(str(path).replace("\\", "/") for path in row.get("paths", []) if isinstance(path, str))
    return allowed


def safe_planned_path(root: Path, value: str, allowed: set[str]) -> tuple[str, Path]:
    candidate = Path(value)
    if candidate.is_absolute() or ".." in candidate.parts:
        raise ValueError("investigation paths must be repository-relative planned paths")
    normalized = candidate.as_posix()
    if normalized not in allowed:
        raise ValueError(f"`{normalized}` is outside the saved planned investigation scope")
    resolved = (root / candidate).resolve()
    try:
        resolved.relative_to(root.resolve())
    except ValueError as error:
        raise ValueError("investigation path resolves outside the project root") from error
    if not resolved.is_file():
        raise ValueError(f"planned investigation path `{normalized}` is not a readable file")
    if resolved.name.lower() in SENSITIVE_NAMES or resolved.suffix.lower() in SENSITIVE_SUFFIXES:
        raise ValueError("sensitive credential files are not eligible for planning investigation")
    return normalized, resolved


def source_fact(relative: str, path: Path) -> dict[str, Any]:
    raw = path.read_bytes()
    if len(raw) > MAX_BYTES_PER_FILE:
        raise ValueError(f"planned path `{relative}` exceeds the {MAX_BYTES_PER_FILE} byte investigation limit")
    if b"\x00" in raw:
        raise ValueError(f"planned path `{relative}` appears binary and is not eligible for source investigation")
    try:
        text = raw.decode("utf-8")
    except UnicodeDecodeError as error:
        raise ValueError(f"planned path `{relative}` is not UTF-8 text") from error
    symbols = list(dict.fromkeys(SYMBOL_PATTERN.findall(text)))[:20]
    return {
        "path": relative,
        "sha256": "sha256:" + hashlib.sha256(raw).hexdigest(),
        "line_count": len(text.splitlines()),
        "symbols": symbols,
    }


def graph_evidence(root: Path, facts: list[dict[str, Any]]) -> dict[str, Any]:
    """Check cache freshness only for the explicitly approved source paths.

    A generic cache checker may hash every cache entry. That would violate this
    investigation's source boundary, so this checks only the requested paths.
    """
    candidates = [root / "tailtrail-meta" / "code-graph-cache.json", root / ".tailtrail" / "code-graph-cache.json"]
    cache_path = next((path for path in candidates if path.is_file()), None)
    if cache_path is None:
        return {"status": "missing", "reused": False, "reasons": ["No Code Graph Mapper cache exists; no graph evidence was reused."]}
    try:
        cache = json.loads(cache_path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError) as error:
        return {"status": "invalid", "reused": False, "reasons": [f"Graph cache could not be read: {error}"]}
    if not isinstance(cache, dict) or cache.get("schema_version") != GRAPH_SCHEMA_VERSION:
        return {"status": "invalid", "reused": False, "reasons": ["Graph cache schema is unsupported."]}
    if cache.get("root") and Path(str(cache["root"])).resolve() != root.resolve():
        return {"status": "invalid", "reused": False, "reasons": ["Graph cache root does not match the current project root."]}
    scope = {str(item) for item in cache.get("scope", []) if isinstance(item, str)}
    requested = {str(item["path"]) for item in facts}
    if not requested.issubset(scope):
        return {"status": "missing", "reused": False, "reasons": ["Requested planned paths are outside the cached graph scope; no graph evidence was reused."]}
    cached_sources = cache.get("source_files")
    if not isinstance(cached_sources, dict):
        return {"status": "invalid", "reused": False, "reasons": ["Graph cache source metadata is invalid."]}
    reasons: list[str] = []
    for fact in facts:
        metadata = cached_sources.get(fact["path"])
        expected = metadata.get("sha256") if isinstance(metadata, dict) else None
        actual = str(fact["sha256"]).removeprefix("sha256:")
        if not isinstance(expected, str) or not expected:
            reasons.append(f"{fact['path']} has no usable cached source hash.")
        elif expected != actual:
            reasons.append(f"{fact['path']} changed after the graph was created.")
    if reasons:
        return {"status": "stale", "reused": False, "reasons": reasons}
    return {
        "status": "fresh",
        "reused": True,
        "reasons": ["Approved paths match cached source hashes; repository-wide inventory was not checked by this bounded investigation."],
    }


def artifact_path(root: Path, run_id: str, index: int) -> Path:
    return LEDGER.state_dir(root, run_id) / "planning" / "investigations" / f"investigation-{index:03d}.json"


def investigate(root: Path, run_id: str, paths: list[str], approved_read_only: bool) -> dict[str, Any]:
    if not approved_read_only:
        raise ValueError("planning investigation requires --approved-read-only")
    root = root.resolve()
    LOCK.assert_discussion_allowed(root, run_id)
    if not paths:
        raise ValueError("at least one --path is required")
    if len(paths) > MAX_FILES:
        raise ValueError(f"at most {MAX_FILES} planned paths may be investigated at once")
    report = saved_report(root, run_id)
    allowed = planned_paths(report)
    if not allowed:
        raise ValueError("the saved Start Report contains no planned source paths to investigate")
    checked: list[tuple[str, Path]] = []
    for value in dict.fromkeys(paths):
        checked.append(safe_planned_path(root, value, allowed))
    with LEDGER.RunLock(LEDGER.state_dir(root, run_id) / ".lock"):
        directory = artifact_path(root, run_id, 1).parent
        existing = sorted(directory.glob("investigation-*.json")) if directory.is_dir() else []
        index = len(existing) + 1
        facts = [source_fact(relative, path) for relative, path in checked]
        receipt = {
            "schema_version": "1",
            "type": "tailtrail-plan-investigation",
            "investigation_id": f"investigation-{index:03d}",
            "run_id": run_id,
            "status": "completed",
            "paths_read": [relative for relative, _ in checked],
            "source_facts": facts,
            "graph_evidence": graph_evidence(root, facts),
            "commands_run": [],
            "source_changed": False,
            "tests_run": False,
            "created_at": utc_now(),
            "boundary": BOUNDARY,
        }
        destination = artifact_path(root, run_id, index)
        LEDGER.atomic_json(destination, receipt)
    LEDGER.append_event(root, run_id, "planning_investigation_recorded", {
        "investigation_id": receipt["investigation_id"],
        "paths_read": receipt["paths_read"],
        "graph_status": receipt["graph_evidence"]["status"],
        "artifact": destination.relative_to(LEDGER.state_dir(root, run_id)).as_posix(),
    })
    return {**receipt, "artifact": destination.relative_to(root).as_posix()}


def show(root: Path, run_id: str, sequence: int | None = None) -> dict[str, Any]:
    root = root.resolve()
    directory = artifact_path(root, run_id, 1).parent
    artifacts = sorted(directory.glob("investigation-*.json")) if directory.is_dir() else []
    if not artifacts:
        raise ValueError(f"no planning investigation exists for run `{run_id}`")
    chosen = artifact_path(root, run_id, sequence) if sequence is not None else artifacts[-1]
    if not chosen.is_file():
        raise ValueError(f"planning investigation `{sequence}` does not exist for run `{run_id}`")
    return {**json.loads(chosen.read_text(encoding="utf-8")), "artifact": chosen.relative_to(root).as_posix()}


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    sub = parser.add_subparsers(dest="command", required=True)
    investigate_parser = sub.add_parser("investigate", help="Read only explicit planned source paths after approval.")
    investigate_parser.add_argument("--root", type=Path, default=Path.cwd())
    investigate_parser.add_argument("--run-id", required=True)
    investigate_parser.add_argument("--path", action="append", default=[])
    investigate_parser.add_argument("--approved-read-only", action="store_true")
    show_parser = sub.add_parser("show", help="Show a saved sanitized planning investigation receipt.")
    show_parser.add_argument("--root", type=Path, default=Path.cwd())
    show_parser.add_argument("--run-id", required=True)
    show_parser.add_argument("--sequence", type=int)
    args = parser.parse_args()
    try:
        result = investigate(args.root, args.run_id, args.path, args.approved_read_only) if args.command == "investigate" else show(args.root, args.run_id, args.sequence)
        print(json.dumps(result, indent=2, sort_keys=True))
        return 0
    except (OSError, ValueError, json.JSONDecodeError) as error:
        print(f"Planning investigation error: {error}")
        return 2


if __name__ == "__main__":
    raise SystemExit(main())
