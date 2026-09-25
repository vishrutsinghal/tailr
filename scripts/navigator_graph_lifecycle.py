#!/usr/bin/env python3
"""Navigator-owned persistent graph and cross-run mapping lifecycle.

Only TailTrail metadata is written. Project source is read statically and is
never imported or executed. Graph state accelerates discovery but never grants
implementation authority; current-source scope evidence remains decisive.
"""

from __future__ import annotations

import hashlib
import importlib.util
import json
import os
import re
import sys
import tempfile
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Iterable

SCRIPT_DIR = Path(__file__).resolve().parent
if SCRIPT_DIR.as_posix() not in sys.path:
    sys.path.insert(0, SCRIPT_DIR.as_posix())

import navigator_discovery
import navigator_scope
import code_graph_cache


CACHE_RELATIVE = Path("tailtrail-meta") / "code-graph-cache.json"
MAPPING_RELATIVE = Path("tailtrail-meta") / "navigator-run-mappings-v1.json"
GRAPH_MODES = {"auto", "reuse", "refresh", "rebuild", "off"}


def _load_mapper() -> Any:
    path = SCRIPT_DIR / "code-graph-mapper.py"
    spec = importlib.util.spec_from_file_location("tailtrail_navigator_graph_mapper", path)
    if spec is None or spec.loader is None:
        raise RuntimeError("Code Graph Mapper is unavailable")
    module = importlib.util.module_from_spec(spec)
    sys.modules[spec.name] = module
    spec.loader.exec_module(module)
    return module


def _now() -> str:
    return datetime.now(timezone.utc).isoformat()


def _canonical(value: Any) -> bytes:
    return json.dumps(value, sort_keys=True, separators=(",", ":"), ensure_ascii=False).encode("utf-8")


def fingerprint(value: Any) -> str:
    return "sha256:" + hashlib.sha256(_canonical(value)).hexdigest()


def _atomic_json(path: Path, value: Any) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    payload = json.dumps(value, indent=2, sort_keys=True, ensure_ascii=False).encode("utf-8") + b"\n"
    handle = tempfile.NamedTemporaryFile(prefix=path.name + ".", suffix=".tmp", dir=path.parent, delete=False)
    temporary = Path(handle.name)
    try:
        with handle:
            handle.write(payload)
            handle.flush()
            os.fsync(handle.fileno())
        os.replace(temporary, path)
    finally:
        if temporary.exists():
            temporary.unlink()


def _safe_paths(root: Path, values: Iterable[str]) -> list[str]:
    paths: list[str] = []
    for value in values:
        normalized, rejection = navigator_scope.normalize_repository_path(root, str(value))
        if normalized and not rejection and not navigator_scope.sensitive_path_reason(normalized):
            role, _ = navigator_scope.classify_repository_role(root, normalized)
            if role not in {"generated", "managed-tooling", "documentation", "unknown"}:
                paths.append(normalized)
    return sorted(dict.fromkeys(paths))


def _goal_terms(goal: str) -> set[str]:
    ignored = {
        "after", "also", "before", "does", "from", "have", "into", "need", "remove",
        "since", "that", "there", "this", "user", "when", "with", "without",
    }
    return {
        term.casefold()
        for term in re.findall(r"[A-Za-z][A-Za-z0-9_-]{2,}", goal)
        if term.casefold() not in ignored
    }


def _load_mappings(root: Path) -> dict[str, Any]:
    path = root / MAPPING_RELATIVE
    if not path.is_file():
        return {"schema_version": "1", "type": "tailtrail-navigator-run-mapping-index", "mappings": []}
    try:
        value = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError):
        return {"schema_version": "1", "type": "tailtrail-navigator-run-mapping-index", "mappings": []}
    if not isinstance(value, dict) or value.get("schema_version") != "1" or not isinstance(value.get("mappings"), list):
        return {"schema_version": "1", "type": "tailtrail-navigator-run-mapping-index", "mappings": []}
    return value


def relevant_mapping_paths(root: Path, goal: str, limit: int = 8) -> list[str]:
    """Return hash-fresh paths from semantically related completed mappings."""
    wanted = _goal_terms(goal)
    ranked: list[tuple[int, str]] = []
    for row in _load_mappings(root).get("mappings", []):
        if not isinstance(row, dict):
            continue
        if row.get("closure_status") != "complete":
            continue
        overlap = len(wanted & {str(term).casefold() for term in row.get("query_terms", [])})
        if overlap <= 0:
            continue
        for path, expected in (row.get("path_hashes", {}) or {}).items():
            text, rejection, observed = navigator_scope.safe_text(root, str(path))
            del text
            if not rejection and observed == expected:
                ranked.append((overlap, str(path)))
    return [path for _, path in sorted(set(ranked), key=lambda item: (-item[0], item[1]))[:limit]]


def _discovery_paths(
    root: Path,
    goal: str,
    explicit_paths: Iterable[str],
    canonical_literals: Iterable[str] = (),
) -> tuple[list[str], list[str]]:
    explicit = _safe_paths(root, explicit_paths)
    if explicit:
        return explicit, ["explicit-scope-paths"]
    literals = tuple(str(value) for value in canonical_literals if str(value).strip())
    exact = navigator_discovery.exact_phrase_paths(
        root,
        goal,
        limit=16,
        canonical_literals=literals,
    )
    exact_paths = _safe_paths(root, [str(row.get("path", "")) for row in exact])
    reused = relevant_mapping_paths(root, goal)
    if exact_paths:
        return _safe_paths(root, [*exact_paths, *reused]), ["exact-user-literal-match", *( ["fresh-prior-run-mapping"] if reused else [])]
    lexical = navigator_discovery.goal_discovered_paths(
        root,
        goal,
        limit=8,
        canonical_literals=literals,
    )
    lexical_paths = _safe_paths(root, [str(row.get("path", "")) for row in lexical])
    if lexical_paths or reused:
        return _safe_paths(root, [*lexical_paths, *reused]), ["bounded-goal-discovery", *( ["fresh-prior-run-mapping"] if reused else [])]
    return [], ["repository-orientation-required"]


def _anchor_slice_relevance(
    root: Path,
    previous: dict[str, Any] | None,
    slice_paths: list[str],
) -> dict[str, Any]:
    """Evaluate anchor connectivity against the cached graph (Stage 3).

    Freshness comes from hashes elsewhere; relevance answers whether the
    cached graph holds a connected path from task anchors into cached scope.
    """
    if previous is None:
        return {"relevance": "missing", "connected": [], "reasons": ["no cached graph for anchor relevance"]}
    graph = previous.get("graph", {}) if isinstance(previous, dict) else {}
    references = graph.get("references", []) if isinstance(graph, dict) else []
    adjacency = navigator_scope.reference_adjacency(references)
    connected = navigator_scope.connected_files(slice_paths, adjacency)
    cached_scope = {str(item) for item in (previous.get("scope", []) or []) if item}
    reached = sorted(set(connected) & cached_scope)
    present = sorted(set(slice_paths) & cached_scope)
    if reached or present:
        reasons = []
        if present:
            reasons.append(f"{len(present)} anchor paths present in cached scope")
        if reached:
            reasons.append(f"{len(reached)} anchor-connected cached files")
        return {"relevance": "relevant", "connected": connected, "reasons": reasons}
    reasons = ["no anchor-connected path into cached scope"]
    absent = [path for path in slice_paths if not (root / path).is_file()]
    if absent:
        reasons.append(f"{len(absent)} anchor paths not found on disk")
    return {"relevance": "insufficient", "connected": connected, "reasons": reasons}


def manage(
    root: Path,
    goal: str,
    explicit_paths: Iterable[str] = (),
    *,
    mode: str = "auto",
    attempt_id: str | None = None,
    phase: str = "start",
    canonical_literals: Iterable[str] = (),
    anchor_slice: dict[str, Any] | None = None,
) -> dict[str, Any]:
    """Choose and execute one safe graph metadata transition."""
    if mode not in GRAPH_MODES:
        raise ValueError("graph mode must be auto, reuse, refresh, rebuild, or off")
    root = root.resolve()
    mapper = _load_mapper()
    cache_path = root / CACHE_RELATIVE
    previous, load_error = mapper.load_cache(cache_path)
    before = mapper.status_for(root, previous, []) if previous else {
        "status": "missing" if load_error == "missing" else "invalid",
        "reasons": [load_error or "missing"],
        "scope": [],
    }
    freshness = before["status"] if before["status"] in {"fresh", "stale", "missing"} else "stale"
    relevance = "not-evaluated"
    relevance_reasons: list[str] = []
    cache_reuse_state: str | None = None
    slice_paths: list[str] = []
    slice_connected: list[str] = []
    if anchor_slice is not None:
        slice_paths = [str(item) for item in anchor_slice.get("paths", []) if str(item).strip()]
        info = _anchor_slice_relevance(root, previous, slice_paths)
        relevance = str(info["relevance"])
        slice_connected = list(info["connected"])
        relevance_reasons = list(info["reasons"])
        cache_reuse_state = f"{freshness}-{relevance}"
    # Debug Start has not received reproduction authority yet. It may validate
    # and reuse an existing metadata graph, but it must not broaden orientation
    # by scanning source bodies or creating new discovery scope.
    if mode == "off":
        target_paths = []
        discovery_reasons = ["user-disabled-graph"]
    elif phase == "debug-start":
        target_paths = _safe_paths(root, explicit_paths)
        discovery_reasons = ["debug-start-reuse-only"]
        if target_paths:
            discovery_reasons.append("explicit-scope-paths")
    else:
        target_paths, discovery_reasons = _discovery_paths(
            root,
            goal,
            explicit_paths,
            canonical_literals,
        )
    action = "reuse"
    reasons = list(discovery_reasons)
    if anchor_slice is not None and relevance != "not-evaluated":
        on_disk = {path for path in slice_paths if (root / path).is_file()}
        allowed = on_disk | set(slice_connected)
        dropped = [path for path in target_paths if path not in allowed]
        ordered = [path for path in target_paths if path in allowed]
        ordered.extend(path for path in sorted(allowed) if path not in set(ordered))
        target_paths = ordered[:200]
        reasons.append("anchor-slice-bounded-targets")
        if dropped:
            reasons.append("unconnected-lexical-excluded")
        reasons.extend(relevance_reasons)
    outside_slice_nominations = []
    if anchor_slice is not None and relevance != "not-evaluated":
        nominated = [path for path in _safe_paths(root, explicit_paths) if path not in allowed]
        outside_slice_nominations = [
            {"path": path, "reason": "outside-anchor-slice"} for path in sorted(nominated)
        ]
        if nominated:
            reasons.append("outside-slice-nomination-recorded")
    if mode == "off":
        action = "off"
    elif mode == "reuse":
        if anchor_slice is not None:
            reusable = cache_reuse_state == "fresh-relevant"
        else:
            reusable = before["status"] == "fresh"
        action = "reuse" if reusable else "defer"
        reasons.append("explicit-reuse" if action == "reuse" else "requested-reuse-not-fresh")
    elif mode == "rebuild":
        action = "rebuild"
        reasons.append("explicit-rebuild")
    elif mode == "refresh":
        action = "refresh" if previous else "create"
        reasons.append("explicit-refresh")
    elif not target_paths and before["status"] != "fresh":
        action = "defer"
        reasons.append("no-relevant-graph-scope")
    elif before["status"] == "missing":
        action = "create"
        reasons.append("persistent-graph-missing")
    elif before["status"] == "invalid":
        action = "rebuild"
        reasons.append("persistent-graph-invalid")
    elif before["status"] == "stale":
        action = "refresh"
        reasons.append("persistent-graph-stale")
    else:
        if anchor_slice is not None:
            if relevance == "relevant":
                reasons.append("fresh-relevant-graph-reused")
            else:
                action = "refresh"
                reasons.append("anchor-insufficient-extend")
        else:
            cached_scope = {str(value) for value in (previous or {}).get("scope", [])}
            if target_paths and not set(target_paths).issubset(cached_scope):
                action = "refresh"
                reasons.append("requested-scope-outside-cache")
            else:
                reasons.append("fresh-relevant-graph-reused")

    written = False
    cache = previous
    if action in {"create", "refresh", "rebuild"}:
        history = list((previous or {}).get("navigator_lifecycle_history", []))[-19:]
        prior_scope = _safe_paths(root, (previous or {}).get("scope", []))
        effective_paths = _safe_paths(
            root,
            [*(prior_scope if action == "refresh" else []), *target_paths],
        )[:200]
        cache = mapper.build_graph(root, effective_paths, f"navigator-{phase}", [], 40, previous=previous if action == "refresh" else None)
        transition = {
            "action": action,
            "at": _now(),
            "attempt_id": attempt_id,
            "phase": phase,
            "reason_codes": sorted(dict.fromkeys(reasons)),
            "target_paths": target_paths,
            "effective_scope": effective_paths,
        }
        cache["navigator_lifecycle_history"] = [*history, transition]
        mapper.write_cache(cache_path, cache)
        written = True
    after = mapper.status_for(root, cache, target_paths) if cache else before
    container_state, _ = code_graph_cache.read_container(cache_path)
    unsigned = {
        "schema_version": "1",
        "type": "tailtrail-navigator-graph-lifecycle",
        "attempt_id": attempt_id,
        "phase": phase,
        "requested_mode": mode,
        "action": action,
        "reason_codes": sorted(dict.fromkeys(reasons)),
        "target_paths": target_paths,
        "cache_path": CACHE_RELATIVE.as_posix(),
        "before_status": before,
        "after_status": after,
        "cache_shape": container_state["kind"],
        "cache_warnings": list(container_state["warnings"]),
        "freshness": freshness,
        "relevance": relevance,
        "cache_reuse_state": cache_reuse_state,
        "outside_slice_nominations": outside_slice_nominations,
        "cache_fingerprint": fingerprint(cache) if cache else None,
        "written": written,
        "metadata_only": True,
        "implementation_authority": False,
        "boundary": "Navigator may create or refresh TailTrail graph metadata; current-source scope evidence and Planning Lock approval remain mandatory.",
    }
    return {**unsigned, "fingerprint": fingerprint(unsigned)}


def record_run_mapping(
    root: Path,
    run_id: str,
    goal: str,
    scope_evidence: dict[str, Any],
    changed_paths: Iterable[str],
    closure_status: str,
    graph_lifecycle: dict[str, Any],
) -> dict[str, Any]:
    """Append one immutable, hash-bound run mapping after closure."""
    root = root.resolve()
    paths = _safe_paths(root, [
        *[str(value) for row in scope_evidence.get("requirements", []) if isinstance(row, dict) for key in ("implementation_owners", "inspection_paths", "proof_paths") for value in row.get(key, [])],
        *[str(value) for value in changed_paths],
    ])
    path_hashes: dict[str, str] = {}
    for path in paths:
        _text, rejection, observed = navigator_scope.safe_text(root, path)
        if not rejection and observed:
            path_hashes[path] = observed
    identity = {
        "run_id": run_id,
        "goal_fingerprint": fingerprint(goal),
        "query_terms": sorted(_goal_terms(goal)),
        "scope_decision_fingerprint": scope_evidence.get("decision_fingerprint"),
        "closure_status": closure_status,
        "path_hashes": path_hashes,
        "graph_cache_fingerprint": graph_lifecycle.get("cache_fingerprint"),
    }
    mapping_fingerprint = fingerprint(identity)
    index = _load_mappings(root)
    for item in index["mappings"]:
        if isinstance(item, dict) and item.get("mapping_fingerprint") == mapping_fingerprint:
            return item
    row = {
        **identity,
        "recorded_at": _now(),
        "mapping_fingerprint": mapping_fingerprint,
    }
    # A run may produce more than one closure assessment. Retain each distinct,
    # hash-bound version so an incomplete assessment cannot erase later proof
    # (or vice versa), while exact replays stay idempotent.
    index["mappings"] = [*index["mappings"], row][-200:]
    index["updated_at"] = _now()
    _atomic_json(root / MAPPING_RELATIVE, index)
    return row
