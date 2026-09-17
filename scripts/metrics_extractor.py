#!/usr/bin/env python3
"""TailTrail quantitative scope-complexity metrics for AIDLC mode selection.

Extracts metrics from Navigator scope_evidence + optional code-graph-cache.json.
Called by aidlc_mode_selection() in task-start.py.

Three tiers:
  Tier 1 — cheap, always available (likely_impacted_files)
  Tier 2 — graph-derived from scope_evidence document
  Tier 3 — AST/mapper metrics from committed graph cache (optional enrichment)
"""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any

DEFAULT_THRESHOLDS: dict[str, Any] = {
    # Standard escalation thresholds (any one fires → Standard candidate)
    "affected_files_standard": 20,
    "cross_layer_edges_standard": 2,
    "call_chain_depth_stddev_standard": 3.0,
    "module_resolution_ambiguous_standard": 3,
    "new_external_deps_standard": 1,
    "behavior_chain_incomplete_standard": True,

    # Standard floor (minimum scope to qualify for Standard)
    "affected_files_standard_floor": 10,
    "cross_layer_edges_standard_floor": 1,

    # Full escalation thresholds (any one fires → Full candidate)
    "affected_files_full": 80,
    "cross_layer_edges_full": 6,
    "call_chain_depth_stddev_full": 5.0,
    "behavior_chain_incomplete_full": True,

    # Lite floor (keeps Lite even if keyword fires)
    "affected_files_lite_floor": 5,
    "changed_lines_lite_floor": 50,
}


THRESHOLD_OVERRIDE_RELPATH = Path(".tailtrail") / "aidlc-scope-thresholds.json"


def read_threshold_override(root: Path) -> tuple[dict[str, Any] | None, str | None]:
    """Read the raw project override file. Never raises.

    Returns (raw dict or None, error or None). Missing file is not an
    error — it means defaults apply.
    """
    threshold_path = Path(root) / THRESHOLD_OVERRIDE_RELPATH
    if not threshold_path.is_file():
        return None, None
    try:
        raw = json.loads(threshold_path.read_text(encoding="utf-8"))
    except (json.JSONDecodeError, OSError) as error:
        return None, f"unparseable: {error}"
    if not isinstance(raw, dict):
        return None, "override root is not an object"
    return raw, None


def validate_thresholds(values: Any) -> tuple[dict[str, Any], list[str]]:
    """Split a raw override into (clean entries, warnings). Never raises.

    Unknown keys, wrong types, and negative numerics are dropped with a
    warning so safe defaults always win. Booleans are strict (``1``/``0``
    are not accepted for flag keys, and vice versa).
    """
    if not isinstance(values, dict):
        return {}, ["override is not an object"]
    clean: dict[str, Any] = {}
    warnings: list[str] = []
    for key, value in values.items():
        default = DEFAULT_THRESHOLDS.get(key)
        if default is None:
            warnings.append(f"unknown threshold ignored: {key}")
            continue
        if isinstance(default, bool):
            if type(value) is bool:
                clean[key] = value
            else:
                warnings.append(f"{key} must be true/false; keeping default {default}")
            continue
        if isinstance(value, bool) or not isinstance(value, (int, float)):
            warnings.append(f"{key} must be a number; keeping default {default}")
        elif value < 0:
            warnings.append(f"{key} must be >= 0; keeping default {default}")
        else:
            clean[key] = value
    return clean, warnings


def load_thresholds(root: Path) -> dict[str, Any]:
    """Load effective thresholds: defaults overlaid with validated overrides."""
    raw, _ = read_threshold_override(root)
    clean, _ = validate_thresholds(raw or {})
    merged = dict(DEFAULT_THRESHOLDS)
    merged.update(clean)
    return merged


def _infer_layer(path: str) -> str:
    """Infer the architectural layer from a file path."""
    p = path.lower()
    if p.startswith("tests/") or p.startswith("test/") or "/test" in p or p.endswith("_test.py") or p.endswith("_test.go"):
        return "test"
    if p.startswith("src/"):
        return "src"
    if p.startswith("config/") or p.endswith(("yml", ".yaml", ".toml", ".json")):
        return "config"
    if "docs/" in p or p.startswith("doc/"):
        return "docs"
    return "other"


def _safe_stddev(values: list[int]) -> float:
    """Compute population standard deviation, returning 0.0 for trivial lists."""
    if not values or len(values) < 2:
        return 0.0
    mean = sum(values) / len(values)
    variance = sum((v - mean) ** 2 for v in values) / len(values)
    return round(variance ** 0.5, 4)


def cheap_scope_metrics(likely_impacted_files: list[dict[str, Any]]) -> dict[str, Any]:
    """Compute Tier-1 metrics from plan['likely_impacted_files'].

    Always available, no graph cache required.
    """
    if not likely_impacted_files:
        return {
            "affected_files": 0,
            "changed_lines_estimate": 0,
            "layer_breakdown": {},
            "source": "likely_impacted_files_only",
            "available": False,
        }

    paths = [str(item.get("path", "")) for item in likely_impacted_files]
    layers: dict[str, int] = {}
    total_lines = 0
    for item in likely_impacted_files:
        layer = item.get("layer", _infer_layer(item.get("path", "")))
        layers[layer] = layers.get(layer, 0) + 1
        total_lines += int(item.get("changed_lines_estimate", 0))

    return {
        "affected_files": len(paths),
        "affected_paths": paths,
        "changed_lines_estimate": total_lines,
        "layer_breakdown": layers,
        "source": "likely_impacted_files_only",
        "available": len(paths) > 0,
    }


def _candidate_layer(candidates: list[dict[str, Any]], candidate_id) -> str | None:
    """Look up the layer of a candidate by its ID."""
    if candidate_id is None:
        return None
    for row in candidates:
        if isinstance(row, dict) and str(row.get("candidate_id")) == str(candidate_id):
            return row.get("layer")
    return None


def graph_scope_metrics(scope_evidence: dict[str, Any]) -> dict[str, Any]:
    """Compute Tier-2 metrics from the Navigator scope_evidence document."""
    if not isinstance(scope_evidence, dict):
        return {"source": "scope_evidence", "available": False, "error": "scope_evidence is not a dict"}

    metrics: dict[str, Any] = {
        "source": "scope_evidence",
        "available": True,
    }

    candidates = scope_evidence.get("candidates", [])
    impl_files = [
        row for row in candidates
        if isinstance(row, dict) and row.get("role") == "implementation-owner"
    ]
    metrics["affected_files"] = len(impl_files)
    metrics["affected_paths"] = [str(row.get("path", "")) for row in impl_files]

    layers: dict[str, int] = {}
    for row in impl_files:
        layer = row.get("layer", "unknown")
        layers[layer] = layers.get(layer, 0) + 1
    metrics["layer_breakdown"] = layers

    edges = scope_evidence.get("edges", [])
    cross_layer_count = 0
    for edge in edges:
        if not isinstance(edge, dict):
            continue
        from_layer = _candidate_layer(candidates, edge.get("from_candidate_id"))
        to_layer = _candidate_layer(candidates, edge.get("to_candidate_id"))
        if from_layer and to_layer and from_layer != to_layer:
            cross_layer_count += 1
    metrics["cross_layer_edges"] = cross_layer_count

    module_resolution = scope_evidence.get("module_resolution", {})
    ambiguous_count = sum(
        1 for entry in module_resolution.get("ambiguous_modules", [])
        if isinstance(entry, dict) and entry.get("ambiguous", False)
    )
    metrics["module_resolution_ambiguous"] = ambiguous_count

    behavior_chains = scope_evidence.get("behavior_chains", [])
    incomplete_chains = sum(
        1 for chain in behavior_chains
        if isinstance(chain, dict) and chain.get("state") in {"partial", "broken", "missing"}
    )
    metrics["behavior_chain_incomplete"] = incomplete_chains > 0
    metrics["call_chain_depths"] = [
        int(chain.get("depth", 0)) for chain in behavior_chains
        if isinstance(chain, dict)
    ]
    metrics["call_chain_depth_stddev"] = _safe_stddev(metrics["call_chain_depths"])

    investigation = scope_evidence.get("investigation", {})
    metrics["investigation_files_read"] = int(investigation.get("files_read", 0))

    return metrics


_EXTERNAL_SERVICE_EDGE_TYPES = frozenset({"http-url", "service-config"})


def _file_sha256(path: Path) -> str | None:
    """Hex digest of a file, or None when unreadable.

    Local duplicate of the mapper's helper: importing code-graph-mapper
    here would burden every Start with that module's full load.
    """
    import hashlib

    try:
        digest = hashlib.sha256()
        with path.open("rb") as handle:
            for chunk in iter(lambda: handle.read(1024 * 1024), b""):
                digest.update(chunk)
    except OSError:
        return None
    return digest.hexdigest()


def mapper_cache_freshness(
    root: Path, cache: dict[str, Any], affected_paths: list[str]
) -> tuple[bool, str | None]:
    """Check whether a mapper cache is fresh enough to trust for Tier 3.

    Verifies only in-scope files that carry cached sha256 metadata
    (``source_files`` / ``watch_files`` / ``scanner_evidence``): a missing
    or content-changed file means the cached symbols for this scope may
    mislead, so the cache is stale. Caches with no metadata at all
    (legacy/test shapes) cannot be verified and are trusted as before.
    Never raises; verification cost is bounded by the affected set.
    """
    metadata: dict[str, Any] = {}
    for group in ("source_files", "watch_files", "scanner_evidence"):
        rows = cache.get(group, {})
        if isinstance(rows, dict):
            metadata.update(rows)
    if not metadata:
        return True, None
    for relative in affected_paths:
        entry = metadata.get(relative)
        if not isinstance(entry, dict) or not isinstance(entry.get("sha256"), str):
            continue
        actual = _file_sha256(Path(root) / relative)
        if actual is None:
            return False, f"stale: {relative} is missing after the graph was built"
        if actual != entry["sha256"]:
            return False, f"stale: {relative} changed after the graph was built"
    return True, None


def mapper_scope_metrics(cache: dict[str, Any], affected_paths: list[str]) -> dict[str, Any]:
    """Compute Tier-3 metrics from code-graph-cache.json (mapper output).

    Call only with a cache approved by :func:`mapper_cache_freshness`.
    """
    metrics: dict[str, Any] = {"available": True, "source": "mapper"}

    graph = cache.get("graph", {}) if isinstance(cache.get("graph"), dict) else {}
    symbols = graph.get("symbols", [])
    endpoints = graph.get("endpoints", [])
    edges = graph.get("edges", [])
    service_edges = graph.get("service_edges", [])

    affected_set = set(affected_paths)
    metrics["symbols_in_scope"] = sum(
        1 for s in symbols
        if isinstance(s, dict) and str(s.get("file", "")) in affected_set
    )
    metrics["endpoints_in_scope"] = sum(
        1 for e in endpoints
        if isinstance(e, dict) and str(e.get("file", "")) in affected_set
    )
    external = sum(
        1 for e in edges
        if isinstance(e, dict) and e.get("kind") == "external_dep"
    )
    # The mapper emits external references as service_edges (http-url,
    # service-config), not as graph.edges — count in-scope ones too.
    external += sum(
        1 for e in service_edges
        if isinstance(e, dict)
        and e.get("edge_type") in _EXTERNAL_SERVICE_EDGE_TYPES
        and str(e.get("source_file", "")) in affected_set
    )
    metrics["external_dependency_edges"] = external

    return metrics


def load_code_graph_cache(root: Path) -> dict[str, Any]:
    """Load project-level code graph cache from standard locations.

    Searches the standard locations in order:
    1. ``tailtrail-meta/code-graph-cache.json`` (project-shared)
    2. ``.tailtrail/code-graph-cache.json`` (local-only)

    Returns an empty dict if no cache file is found.
    """
    candidate_paths = [
        root / "tailtrail-meta" / "code-graph-cache.json",
        root / ".tailtrail" / "code-graph-cache.json",
    ]
    for path in candidate_paths:
        if path.is_file():
            try:
                data = json.loads(path.read_text(encoding="utf-8"))
                if isinstance(data, dict):
                    return data
            except (json.JSONDecodeError, OSError):
                pass
    return {}


def compute_complexity(
    likely_impacted_files: list[dict[str, Any]],
    scope_evidence: dict[str, Any] | None,
    root: Path,
) -> dict[str, Any]:
    """Compute full complexity metrics dict from all available tiers.

    This is the single entry point called by aidlc_mode_selection() in task-start.py.
    Returns a dict like:
      {
        "source": "likely_impacted_only|scope_evidence|scope_evidence+mapper",
        "available": bool,
        "affected_files": int,
        "cross_layer_edges": int,
        "call_chain_depth_stddev": float,
        "module_resolution_ambiguous": int,
        "behavior_chain_incomplete": bool,
        "changed_lines_estimate": int,
        "layer_breakdown": {layer: count},
        "thresholds": {...},
      }
    """
    thresholds = load_thresholds(root)

    complexity = cheap_scope_metrics(likely_impacted_files)

    if isinstance(scope_evidence, dict) and scope_evidence:
        scope_metrics = graph_scope_metrics(scope_evidence)
        if scope_metrics.get("available"):
            complexity["source"] = "scope_evidence"
            complexity["affected_files"] = scope_metrics.get("affected_files", complexity["affected_files"])
            complexity["affected_paths"] = scope_metrics.get("affected_paths", complexity.get("affected_paths", []))
            complexity["cross_layer_edges"] = scope_metrics.get("cross_layer_edges", 0)
            complexity["module_resolution_ambiguous"] = scope_metrics.get("module_resolution_ambiguous", 0)
            complexity["behavior_chain_incomplete"] = scope_metrics.get("behavior_chain_incomplete", False)
            complexity["call_chain_depths"] = scope_metrics.get("call_chain_depths", [])
            complexity["call_chain_depth_stddev"] = scope_metrics.get("call_chain_depth_stddev", 0.0)
            complexity["layer_breakdown"] = scope_metrics.get("layer_breakdown", complexity.get("layer_breakdown", {}))
            complexity["investigation_files_read"] = scope_metrics.get("investigation_files_read", 0)

            cache = load_code_graph_cache(root)
            if cache:
                affected = complexity.get("affected_paths", [])
                fresh, stale_reason = mapper_cache_freshness(root, cache, affected)
                if not fresh:
                    # Phase 7: degrade to Tier 1+2 with a logged reason instead
                    # of trusting symbols from a drifted graph.
                    complexity["tier3_skipped"] = stale_reason
                else:
                    mapper_metrics = mapper_scope_metrics(cache, affected)
                    if mapper_metrics.get("available"):
                        complexity["source"] = "scope_evidence+mapper"
                        complexity["symbols_in_scope"] = mapper_metrics.get("symbols_in_scope", 0)
                        complexity["endpoints_in_scope"] = mapper_metrics.get("endpoints_in_scope", 0)
                        complexity["external_dependency_edges"] = mapper_metrics.get("external_dependency_edges", 0)
                        # Gate key read by evaluate_scope_signal (new_external_deps_standard).
                        complexity["new_external_deps"] = mapper_metrics.get("external_dependency_edges", 0)

    complexity["thresholds"] = thresholds
    return complexity


def extract_scope_complexity_metrics(
    root: Path,
    document: dict[str, Any],
) -> dict[str, Any]:
    """Extract scope-complexity metrics from a scope-evidence document.

    This is the consolidated entry point used by
    ``assess_scope_quality(compute_complexity=True)`` in navigator_scope.py
    (Phase 4). It decomposes the document into the params expected by
    :func:`compute_complexity` and delegates to it so both paths share
    the same three-tier metric pipeline.

    The document is expected to carry the same shape produced by
    Navigator's ``scope_evidence`` payload, i.e.:
      - ``likely_impacted_files`` — list of likely-impacted-file rows
      - ``scope_evidence`` — the full scope-evidence dict (may be nested
        under ``scope_evidence`` or passed as the document itself when the
        caller already has the raw scope-evidence payload)
    """
    if not isinstance(document, dict):
        return {
            "source": "unavailable",
            "available": False,
            "affected_files": 0,
            "changed_lines_estimate": 0,
            "layer_breakdown": {},
            "thresholds": load_thresholds(root),
            "error": "document-not-a-dict",
        }

    likely = document.get("likely_impacted_files") or []
    if not isinstance(likely, list):
        likely = []

    # The document may already BE the scope-evidence dict, or it may
    # carry a nested scope_evidence field. Both shapes are accepted.
    scope_ev = document.get("scope_evidence")
    if scope_ev is None and document.get("candidates") is not None:
        scope_ev = document

    return compute_complexity(likely, scope_ev, root)
# --- R1: Calibration runway — mode-decision log -----------------------------
#
# Every dual-gate mode decision appends one bounded JSONL entry to
# .tailtrail/aidlc-mode-decisions.jsonl so that real runs accumulate
# scope_signal / scope_floor_lite / zero-metrics observations. The summary
# feeds threshold calibration (Phase 3 defaults) and gates R2 (the Phase 6
# re-evaluation hook). Entries are privacy-safe: the goal text is never
# written, only a truncated SHA-256 and its length.

MODE_DECISION_LOG_LIMIT = 500
MODE_DECISION_ENTRY_VERSION = 1


def mode_decision_log_path(root: Path) -> Path:
    """Return the JSONL log path for AIDLC mode decisions."""
    return Path(root) / ".tailtrail" / "aidlc-mode-decisions.jsonl"


def build_mode_decision_entry(
    goal: str,
    requested: str | None,
    calibration: dict[str, Any],
    selected: dict[str, Any],
    ts: str | None = None,
) -> dict[str, Any]:
    """Build one sanitized decision-log entry.

    ``calibration`` carries the signals computed inside the dual-gate path of
    ``aidlc_mode_selection()`` (intent, keyword_signal, scope_signal,
    scope_floor_lite, routing_selected, complexity). ``selected`` is the
    preflight result. The raw goal text is deliberately excluded.
    """
    import hashlib
    from datetime import datetime, timezone

    complexity = calibration.get("complexity") or {}
    thresholds = complexity.get("thresholds") or {}
    affected_files = complexity.get("affected_files", 0)
    # Zero-metrics: no scope evidence was available and Tier 1 found nothing.
    zero_metrics = (
        affected_files == 0
        and complexity.get("source") == "likely_impacted_files_only"
        and not complexity.get("cross_layer_edges")
        and not complexity.get("behavior_chain_incomplete", False)
    )
    return {
        "entry_version": MODE_DECISION_ENTRY_VERSION,
        "ts": ts or datetime.now(timezone.utc).isoformat(timespec="seconds"),
        "goal_sha256": hashlib.sha256(goal.encode("utf-8")).hexdigest()[:16],
        "goal_chars": len(goal),
        "requested_flag": requested,
        "intent": calibration.get("intent"),
        "hands_free": bool(calibration.get("hands_free")),
        "keyword_signal": bool(calibration.get("keyword_signal")),
        "scope_signal": bool(calibration.get("scope_signal")),
        "scope_floor_lite": bool(calibration.get("scope_floor_lite")),
        "routing_selected": bool(calibration.get("routing_selected")),
        "selection": selected.get("selection"),
        "mode": selected.get("mode"),
        "requested_mode": selected.get("requested_mode"),
        "mode_state": selected.get("state"),
        "metrics_source": complexity.get("source"),
        "zero_metrics": zero_metrics,
        "affected_files": affected_files,
        "changed_lines_estimate": complexity.get("changed_lines_estimate", 0),
        "cross_layer_edges": complexity.get("cross_layer_edges", 0),
        "call_chain_depth_stddev": complexity.get("call_chain_depth_stddev", 0.0),
        "module_resolution_ambiguous": complexity.get("module_resolution_ambiguous", 0),
        "new_external_deps": complexity.get("new_external_deps", 0),
        "behavior_chain_incomplete": bool(complexity.get("behavior_chain_incomplete", False)),
        "thresholds": dict(thresholds),
    }

def append_mode_decision(root: Path, entry: dict[str, Any]) -> dict[str, Any]:
    """Append one decision entry to the JSONL log; never raises.

    Keeps the log bounded to the last ``MODE_DECISION_LOG_LIMIT`` entries so
    the calibration runway cannot grow unbounded. Returns a status dict:
      {"logged": bool, "path": str, "entries": int | None, "error": str?}
    """
    log_path = mode_decision_log_path(root)
    try:
        log_path.parent.mkdir(parents=True, exist_ok=True)
        existing: list[str] = []
        if log_path.exists():
            existing = [
                line for line in log_path.read_text(encoding="utf-8").splitlines()
                if line.strip()
            ]
        existing.append(json.dumps(entry, sort_keys=True, ensure_ascii=False))
        if len(existing) > MODE_DECISION_LOG_LIMIT:
            existing = existing[-MODE_DECISION_LOG_LIMIT:]
        log_path.write_text("\n".join(existing) + "\n", encoding="utf-8")
        return {"logged": True, "path": str(log_path), "entries": len(existing)}
    except (OSError, TypeError, ValueError) as exc:
        return {"logged": False, "path": str(log_path), "error": str(exc)}


def summarize_mode_decisions(root: Path) -> dict[str, Any]:
    """Summarize the decision log for threshold calibration (R1 review).

    Returns aggregate counts by mode/selection plus the calibration-critical
    observations: scope-signal escalations, keyword escalations, scope-floor
    holds, and zero-metrics runs. A multi-entry ``threshold_variants`` count
    flags threshold drift during the observation window.
    """
    log_path = mode_decision_log_path(root)
    summary: dict[str, Any] = {
        "available": False,
        "path": str(log_path),
        "entry_count": 0,
    }
    try:
        if not log_path.exists():
            return summary
        entries: list[dict[str, Any]] = []
        for line in log_path.read_text(encoding="utf-8").splitlines():
            line = line.strip()
            if not line:
                continue
            try:
                row = json.loads(line)
            except json.JSONDecodeError:
                continue
            if isinstance(row, dict):
                entries.append(row)
    except (OSError, ValueError) as exc:
        summary["error"] = str(exc)
        return summary
    if not entries:
        summary["available"] = True
        return summary

    def _count(key: str) -> dict[str, int]:
        counts: dict[str, int] = {}
        for row in entries:
            value = str(row.get(key))
            counts[value] = counts.get(value, 0) + 1
        return counts

    threshold_variants = {
        json.dumps(row.get("thresholds"), sort_keys=True) for row in entries
    }
    summary.update({
        "available": True,
        "entry_count": len(entries),
        "first_ts": entries[0].get("ts"),
        "last_ts": entries[-1].get("ts"),
        "by_mode": _count("mode"),
        "by_selection": _count("selection"),
        "scope_signal_count": sum(1 for r in entries if r.get("scope_signal")),
        "scope_floor_lite_count": sum(
            1 for r in entries if r.get("keyword_signal") and r.get("scope_floor_lite") and r.get("mode") == "lite"
        ),
        "keyword_standard_count": sum(
            1 for r in entries if r.get("keyword_signal") and not r.get("scope_floor_lite") and r.get("mode") == "standard"
        ),
        "zero_metrics_count": sum(1 for r in entries if r.get("zero_metrics")),
        "hands_free_count": sum(1 for r in entries if r.get("hands_free")),
                "threshold_variants": len(threshold_variants),
    })
    return summary


# --- R2: Phase 6 — Post-Discovery Re-Evaluation Hook -------------------------
#
# After scope discovery the mode selected at pre-scope Start may be too low for
# the actual scope revealed. This section re-applies the *same* scope_signal /
# scope_floor_lite thresholds that the initial selection used, so there is one
# definition of "too complex for Lite" across both decision points.
#
# Design constraints (see docs/arch/navigator_aidlc_improvements.md §Phase 6):
#   - Escalation-only: Lite -> Standard only. Never touches off/full/standard.
#   - Pre-lock only: re-evaluation happens between discovery and lock approval.
#   - Reuses compute_complexity() output (no new threshold constants).

_MODES_ELIGIBLE_FOR_ESCALATION = frozenset({"lite"})


def evaluate_scope_signal(
    complexity: dict[str, Any] | None,
) -> tuple[bool, bool]:
    """Return (scope_signal, scope_floor_lite) from a complexity dict.

    This is the single definition of the Standard-escalation test, shared by
    the initial mode selection in ``task-start.py`` and
    :func:`compute_re_evaluation`. Keeping it here means Phase 6 never
    introduces its own threshold constants (exit criterion #2).
    """
    if not isinstance(complexity, dict):
        return False, False
    thresholds = complexity.get("thresholds", {}) or {}
    scope_signal = (
        complexity.get("affected_files", 0)
        >= thresholds.get("affected_files_standard", DEFAULT_THRESHOLDS["affected_files_standard"])
        or complexity.get("cross_layer_edges", 0)
        >= thresholds.get("cross_layer_edges_standard", DEFAULT_THRESHOLDS["cross_layer_edges_standard"])
        or complexity.get("call_chain_depth_stddev", 0.0)
        >= thresholds.get("call_chain_depth_stddev_standard", DEFAULT_THRESHOLDS["call_chain_depth_stddev_standard"])
        or complexity.get("module_resolution_ambiguous", 0)
        >= thresholds.get("module_resolution_ambiguous_standard", DEFAULT_THRESHOLDS["module_resolution_ambiguous_standard"])
        or complexity.get("new_external_deps", 0)
        >= thresholds.get("new_external_deps_standard", DEFAULT_THRESHOLDS["new_external_deps_standard"])
        or (
            thresholds.get(
                "behavior_chain_incomplete_standard",
                DEFAULT_THRESHOLDS["behavior_chain_incomplete_standard"],
            )
            and complexity.get("behavior_chain_incomplete", False) is True
        )
    )
    scope_floor_lite = (
        complexity.get("affected_files", 9999)
        <= thresholds.get("affected_files_lite_floor", DEFAULT_THRESHOLDS["affected_files_lite_floor"])
        and complexity.get("changed_lines_estimate", 9999)
        <= thresholds.get("changed_lines_lite_floor", DEFAULT_THRESHOLDS["changed_lines_lite_floor"])
        )
    return scope_signal, scope_floor_lite


def compute_re_evaluation(
    initial_mode: str,
    complexity: dict[str, Any] | None,
    *,
    scope_quality_blocking: bool = False,
    complexity_available: bool = False,
) -> dict[str, Any] | None:
    """Phase 6: decide whether post-discovery scope warrants a mode bump.

    Called from **task-start.py** after scope discovery, before the Planning
    Lock is finalized. Re-applies the exact same ``scope_signal`` /
    ``scope_floor_lite`` test as the initial selection — no new thresholds.

    Returns a suggestion dict (or ``None`` when no escalation is warranted):

    * Fires only when ``initial_mode == "lite"`` (escalation-only).
    * Fires only when post-discovery ``scope_signal`` is true and
      ``scope_floor_lite`` is false.
    * Does **not** fire for ``off`` / ``full`` / explicit ``standard``.
    * Does **not** fire when discovery is still unresolved (``scope_quality``
      is blocking) — there is no clean evidence state to justify escalation.
    * Does **not** fire when complexity metrics are unavailable (zero-metrics)
      — no evidence to base a decision on; the run proceeds conservatively.
    """
    if initial_mode not in _MODES_ELIGIBLE_FOR_ESCALATION:
        return None

    if not complexity_available or not isinstance(complexity, dict):
        return None

    scope_signal, scope_floor_lite = evaluate_scope_signal(complexity)
    if not scope_signal or scope_floor_lite:
        return None

    # Gather the specific metrics that exceeded thresholds (transparency).
    thresholds = complexity.get("thresholds", {})
    triggered: list[str] = []
    checks = (
        ("affected_files", "affected_files_standard"),
        ("cross_layer_edges", "cross_layer_edges_standard"),
        ("call_chain_depth_stddev", "call_chain_depth_stddev_standard"),
        ("module_resolution_ambiguous", "module_resolution_ambiguous_standard"),
        ("new_external_deps", "new_external_deps_standard"),
    )
    for key, threshold_key in checks:
        value = complexity.get(key, 0)
        threshold = thresholds.get(threshold_key)
        if threshold is not None and value and not isinstance(value, bool) and value >= threshold:
            triggered.append(key)
    if complexity.get("behavior_chain_incomplete") is True:
        triggered.append("behavior_chain_incomplete")

    return {
        "re_evaluation_suggested": True,
        "suggested_mode": "standard",
        "initial_mode": initial_mode,
        "scope_signal": True,
        "scope_floor_lite": False,
        "triggered_signals": triggered,
        "complexity_snapshot": complexity,
        "reason": (
            "Post-discovery scope-complexity metrics exceeded the Standard "
            "escalation threshold (scope_signal=True) and the Lite scope-floor "
            "did not apply; Standard mode covers this depth without a Full "
            "official lifecycle transition."
        ),
    }


# --- Phase 5: calibration review CLI ---------------------------------------
#
# The feedback loop needs a runnable surface: `thresholds` shows the
# effective configuration (defaults + validated overrides), and
# `calibration` summarizes the R1 decision log into fire rates a human
# can act on. Both are read-only.


def calibration_report(root: Path) -> dict[str, Any]:
    """Summarize the R1 log plus threshold status for calibration review."""
    summary = summarize_mode_decisions(root)
    raw, read_error = read_threshold_override(root)
    _, warnings = validate_thresholds(raw or {})
    report: dict[str, Any] = {
        "threshold_path": str(Path(root) / THRESHOLD_OVERRIDE_RELPATH),
        "override_present": raw is not None,
        "override_error": read_error,
        "override_warnings": warnings,
        "effective_thresholds": load_thresholds(root),
        "log": summary,
    }
    entries = summary.get("entry_count", 0)
    notes: list[str] = []
    if not entries:
        notes.append("No decisions logged yet - run Starts to accumulate calibration data.")
    if (summary.get("threshold_variants") or 1) > 1:
        notes.append(
            "Thresholds changed during the observation window; "
            "compare fire rates before/after before tuning further."
        )
    if summary.get("zero_metrics_count"):
        notes.append(
            f"{summary['zero_metrics_count']} zero-metrics run(s): "
            "improve discovery input before touching thresholds."
        )
    report["notes"] = notes
    return report


def _render_thresholds(root: Path) -> str:
    raw, read_error = read_threshold_override(root)
    clean, warnings = validate_thresholds(raw or {})
    lines = [
        "# TailTrail Scope Thresholds",
        "",
        f"- Source: `{'project override' if raw else 'defaults'}` (`{THRESHOLD_OVERRIDE_RELPATH.as_posix()}`)",
    ]
    if read_error:
        lines.append(f"- Override error: {read_error} (defaults apply)")
    for warning in warnings:
        lines.append(f"- Warning: {warning}")
    lines.extend(["", "## Effective thresholds", ""])
    for key in sorted(load_thresholds(root)):
        marker = " (override)" if key in clean else ""
        lines.append(f"- `{key}`: `{load_thresholds(root)[key]}`{marker}")
    return "\n".join(lines) + "\n"


def _render_calibration(root: Path) -> str:
    report = calibration_report(root)
    summary = report["log"]
    lines = [
        "# TailTrail Calibration Review",
        "",
        f"- Decisions logged: `{summary.get('entry_count', 0)}`",
        f"- Window: `{summary.get('first_ts', '-')}` -> `{summary.get('last_ts', '-')}`",
        f"- By mode: `{json.dumps(summary.get('by_mode', {}), sort_keys=True)}`",
        f"- Scope-signal escalations: `{summary.get('scope_signal_count', 0)}`",
        f"- Keyword escalations held to Standard: `{summary.get('keyword_standard_count', 0)}`",
        f"- Scope-floor Lite holds: `{summary.get('scope_floor_lite_count', 0)}`",
        f"- Zero-metrics runs: `{summary.get('zero_metrics_count', 0)}`",
        f"- Threshold variants in window: `{summary.get('threshold_variants', '-')}`",
    ]
    for warning in report["override_warnings"]:
        lines.append(f"- Threshold warning: {warning}")
    if report["override_error"]:
        lines.append(f"- Threshold error: {report['override_error']} (defaults apply)")
    for note in report["notes"]:
        lines.append(f"- Note: {note}")
    return "\n".join(lines) + "\n"


def build_parser() -> argparse.ArgumentParser:
    import argparse

    parser = argparse.ArgumentParser(description="Inspect scope thresholds and calibration data (read-only).")
    parser.add_argument("--root", type=Path, default=Path.cwd(), help="Project root.")
    parser.add_argument("--format", choices=("text", "json"), default="text", help="Output format.")
    parser.add_argument(
        "command", choices=("thresholds", "calibration"), help="thresholds: effective config; calibration: R1 log review."
    )
    return parser


def main(argv: list[str] | None = None) -> int:
    args = build_parser().parse_args(argv)
    root = Path(args.root)
    if args.command == "thresholds":
        if args.format == "json":
            raw, read_error = read_threshold_override(root)
            clean, warnings = validate_thresholds(raw or {})
            print(json.dumps({
                "path": str(root / THRESHOLD_OVERRIDE_RELPATH),
                "override_present": raw is not None,
                "override_error": read_error,
                "override_warnings": warnings,
                "effective_thresholds": load_thresholds(root),
            }, indent=2, sort_keys=True))
        else:
            print(_render_thresholds(root), end="")
    else:
        if args.format == "json":
            print(json.dumps(calibration_report(root), indent=2, sort_keys=True, default=str))
        else:
            print(_render_calibration(root), end="")
    return 0


if __name__ == "__main__":
    import sys

    raise SystemExit(main(sys.argv[1:]))




