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


def load_thresholds(root: Path) -> dict[str, Any]:
    """Load project-specific thresholds from .tailtrail/aidlc-scope-thresholds.json."""
    threshold_path = root / ".tailtrail" / "aidlc-scope-thresholds.json"
    if not threshold_path.is_file():
        return dict(DEFAULT_THRESHOLDS)
    try:
        user_thresholds = json.loads(threshold_path.read_text(encoding="utf-8"))
        if isinstance(user_thresholds, dict):
            merged = dict(DEFAULT_THRESHOLDS)
            merged.update(user_thresholds)
            return merged
    except (json.JSONDecodeError, OSError):
        pass
    return dict(DEFAULT_THRESHOLDS)


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


def mapper_scope_metrics(cache: dict[str, Any], affected_paths: list[str]) -> dict[str, Any]:
    """Compute Tier-3 metrics from code-graph-cache.json (mapper output).

    Only called when the cache file exists and is not stale.
    """
    metrics: dict[str, Any] = {"available": True, "source": "mapper"}

    symbols = cache.get("graph", {}).get("symbols", [])
    endpoints = cache.get("graph", {}).get("endpoints", [])
    edges = cache.get("graph", {}).get("edges", [])

    affected_set = set(affected_paths)
    metrics["symbols_in_scope"] = sum(
        1 for s in symbols
        if isinstance(s, dict) and str(s.get("file", "")) in affected_set
    )
    metrics["endpoints_in_scope"] = sum(
        1 for e in endpoints
        if isinstance(e, dict) and str(e.get("file", "")) in affected_set
    )
    metrics["external_dependency_edges"] = sum(
        1 for e in edges
        if isinstance(e, dict) and e.get("kind") == "external_dep"
    )

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
                mapper_metrics = mapper_scope_metrics(cache, complexity.get("affected_paths", []))
                if mapper_metrics.get("available"):
                    complexity["source"] = "scope_evidence+mapper"
                    complexity["symbols_in_scope"] = mapper_metrics.get("symbols_in_scope", 0)
                    complexity["endpoints_in_scope"] = mapper_metrics.get("endpoints_in_scope", 0)
                    complexity["external_dependency_edges"] = mapper_metrics.get("external_dependency_edges", 0)

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
        or complexity.get("behavior_chain_incomplete", False) is True
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




