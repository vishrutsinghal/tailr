#!/usr/bin/env python3

from __future__ import annotations

import argparse
import importlib.util
import json
import subprocess
from collections import Counter
from datetime import datetime, timezone
from pathlib import Path
from typing import Any


TAILTRAIL_DIR = Path(".tailtrail")
ROOT = Path(__file__).resolve().parents[1]
HARNESS_REVIEW = TAILTRAIL_DIR / "harness-review.md"
HARNESS_RECOMMENDATIONS = TAILTRAIL_DIR / "harness-recommendations.json"
HARNESS_SUMMARY = TAILTRAIL_DIR / "harness-summary.json"
HARNESS_LOCAL_SUMMARY = TAILTRAIL_DIR / "harness-local-summary.json"

BOOTSTRAP = TAILTRAIL_DIR / "bootstrap-snapshot.json"
QUALITY_EVENTS = TAILTRAIL_DIR / "quality-events.jsonl"
OUTCOME_EVENTS = TAILTRAIL_DIR / "outcome-events.jsonl"
LEARNING_EVENTS = TAILTRAIL_DIR / "learning-events.jsonl"
LEARNING_INDEX = TAILTRAIL_DIR / "learning-index.md"
GRAPH_LEARNING_INDEX = TAILTRAIL_DIR / "graph-learning-index.json"
LEARNING_REFRESH_ACTIONS = TAILTRAIL_DIR / "learning-refresh-actions.jsonl"
TOKEN_BUDGET_EVENTS = TAILTRAIL_DIR / "token-budget-events.jsonl"
CONTEXT_RECEIPTS = TAILTRAIL_DIR / "context-receipts.jsonl"
TOKEN_USAGE = TAILTRAIL_DIR / "token-usage.jsonl"
TOKEN_HARNESS_LEDGER = TAILTRAIL_DIR / "token-harness-events.jsonl"
QUALITY_RUNS = TAILTRAIL_DIR / "quality-runs"
VULNERABILITY_RUNS = TAILTRAIL_DIR / "vulnerability-runs"
SHARED_GRAPH = Path("tailtrail-meta") / "code-graph-cache.json"
SHARED_META_DIR = Path("tailtrail-meta")
SHARED_HARNESS_SUMMARY = SHARED_META_DIR / "harness-summary.jsonl"
SHARED_SCHEMA = SHARED_META_DIR / "harness-summary.schema.json"
SHARED_README = SHARED_META_DIR / "README.md"
LOCAL_GRAPH = TAILTRAIL_DIR / "code-graph-cache.json"

ALLOWED_SUMMARY_KEYS = {
    "schema_version",
    "type",
    "created_month",
    "tailtrail_version",
    "overall_fit",
    "overall_score_band",
    "dimension_fits",
    "artifact_presence",
    "graph_cache_status",
    "graph_cache_source",
    "recommendation_codes",
    "privacy",
}
UNSAFE_TEXT_MARKERS = ("/", "\\", "@", "http://", "https://", "file:", "ssh:", "git@")

ALLOWED_SHARED_EVENT_KEYS = {
    "schema_version",
    "event_type",
    "tailtrail_version",
    "created_month",
    "task_type",
    "language_family",
    "workflow_selected",
    "review_scope",
    "requirement_fulfillment",
    "clarification_needed",
    "validation_fit",
    "token_budget_fit",
    "metric_confidence",
    "learning_signal",
    "scanner_type",
    "issue_type",
    "token_strategy",
    "token_exactness_class",
    "token_evidence_label",
    "token_reduction_band",
    "token_proof_label",
    "token_quality_outcome",
    "token_holdout",
    "token_confidence_gate",
    "overall_fit",
    "overall_score_band",
    "dimension_fits",
    "artifact_presence",
    "graph_cache_status",
    "graph_cache_source",
    "recommendation_codes",
    "privacy",
}


def now() -> str:
    return datetime.now(timezone.utc).replace(microsecond=0).isoformat()


def read_json(path: Path) -> dict[str, Any] | None:
    if not path.exists():
        return None
    try:
        value = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError):
        return None
    return value if isinstance(value, dict) else None


def read_jsonl(path: Path) -> list[dict[str, Any]]:
    if not path.exists():
        return []
    rows: list[dict[str, Any]] = []
    for line in path.read_text(encoding="utf-8").splitlines():
        line = line.strip()
        if not line:
            continue
        try:
            value = json.loads(line)
        except json.JSONDecodeError:
            continue
        if isinstance(value, dict):
            rows.append(value)
    return rows


def load_bootstrap_module() -> Any | None:
    path = ROOT / "scripts" / "bootstrap-snapshot.py"
    spec = importlib.util.spec_from_file_location("tailtrail_bootstrap_for_harness_review", path)
    if spec is None or spec.loader is None:
        return None
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def month_key(value: str | None) -> str:
    if not value:
        return "unknown"
    try:
        parsed = datetime.fromisoformat(value.replace("Z", "+00:00"))
    except ValueError:
        return "unknown"
    return f"{parsed.year:04d}-{parsed.month:02d}"


def event_month(event: dict[str, Any]) -> str:
    for key in ("timestamp", "created_at", "checked_at"):
        value = event.get(key)
        if isinstance(value, str):
            month = month_key(value)
            if month != "unknown":
                return month
    return "unknown"


def filter_month(events: list[dict[str, Any]], month: str | None) -> list[dict[str, Any]]:
    if not month:
        return events
    return [event for event in events if event_month(event) == month]


def count_values(events: list[dict[str, Any]], key: str) -> dict[str, int]:
    counter: Counter[str] = Counter()
    for event in events:
        value = event.get(key)
        if isinstance(value, list):
            for item in value:
                counter[str(item)] += 1
        else:
            counter[str(value or "unknown")] += 1
    return dict(counter.most_common())


def reduction_band(before: int, after: int) -> str:
    if before <= 0:
        return "unknown"
    saved = max(0, before - after)
    pct = percent(saved, before)
    if pct <= 0:
        return "none"
    if pct <= 20:
        return "low"
    if pct <= 60:
        return "medium"
    return "high"


def most_common_normalized(events: list[dict[str, Any]], key: str, default: str = "unknown") -> str:
    counts = Counter(normalize_category(str(event.get(key, default))) for event in events if event.get(key) not in (None, ""))
    if not counts:
        return default
    return counts.most_common(1)[0][0]


def token_harness_summary(root: Path, token_usage: list[dict[str, Any]]) -> dict[str, Any]:
    events = [event for event in read_jsonl(root / TOKEN_HARNESS_LEDGER) if event.get("type") == "tailtrail-token-harness-event"]
    if not events:
        return {
            "strategy": "unknown",
            "exactness_class": "unknown",
            "evidence_label": "unknown",
            "reduction_band": "unknown",
            "proof_label": "estimated" if not token_usage else "measured",
            "quality_outcome": "unknown",
            "holdout": "unknown",
            "confidence_gate": "not-measured" if not token_usage else "unknown",
            "event_count": 0,
        }
    before = sum(int(event.get("tokens_before", 0)) for event in events if isinstance(event.get("tokens_before"), int))
    after = sum(int(event.get("tokens_after", 0)) for event in events if isinstance(event.get("tokens_after"), int))
    failed = any(event.get("event_type") == "quality_result" and normalize_category(str(event.get("validation_outcome", ""))) == "fail" for event in events)
    passed = any(event.get("event_type") == "quality_result" and normalize_category(str(event.get("validation_outcome", ""))) == "pass" for event in events)
    measured_events = [event for event in events if normalize_category(str(event.get("evidence_label", ""))) in {"measured", "benchmark-measured"}]
    holdout_values = {str(event.get("holdout")).lower() for event in events if "holdout" in event}
    if failed:
        quality = "fail"
    elif passed:
        quality = "pass"
    else:
        quality = "not-run"
    return {
        "strategy": most_common_normalized(events, "strategy"),
        "exactness_class": most_common_normalized(events, "exactness_class"),
        "evidence_label": most_common_normalized(events, "evidence_label", "local-evidence"),
        "reduction_band": reduction_band(before, after),
        "proof_label": "measured" if measured_events or token_usage else "local-evidence",
        "quality_outcome": quality,
        "holdout": "true" if "true" in holdout_values else ("false" if "false" in holdout_values else "unknown"),
        "confidence_gate": "passed" if measured_events else ("not-measured" if not token_usage else "unknown"),
        "event_count": len(events),
    }


def percent(part: int, total: int) -> float:
    return round((part / total) * 100, 2) if total else 0.0


def graph_status(root: Path) -> dict[str, Any]:
    shared = root / SHARED_GRAPH
    local = root / LOCAL_GRAPH
    path = shared if shared.exists() else local
    source = "shared" if shared.exists() else "local"
    cache = read_json(path)
    if not path.exists():
        return {"status": "missing", "source": "none", "path": shared.as_posix()}
    if cache is None:
        return {"status": "invalid", "source": source, "path": path.as_posix()}
    freshness = cache.get("freshness") if isinstance(cache.get("freshness"), dict) else {}
    return {
        "status": str(freshness.get("status") or "available"),
        "source": source,
        "path": path.as_posix(),
        "confidence": cache.get("graph", {}).get("confidence") if isinstance(cache.get("graph"), dict) else None,
        "scope_count": len(cache.get("scope", [])) if isinstance(cache.get("scope"), list) else 0,
    }


def bootstrap_status(root: Path, snapshot: dict[str, Any] | None) -> dict[str, Any]:
    if snapshot is None:
        return {
            "status": "missing",
            "reason": "No bootstrap snapshot found.",
            "recommendation": "Create `.tailtrail/bootstrap-snapshot.json` before repo overview, scanner, graph, handoff, or broad implementation prompts.",
        }
    if snapshot.get("type") != "tailtrail-bootstrap-snapshot":
        return {
            "status": "invalid",
            "reason": "Bootstrap snapshot has an unexpected shape.",
            "recommendation": "Refresh the bootstrap snapshot before relying on it.",
        }
    module = load_bootstrap_module()
    if module is not None:
        try:
            status = module.snapshot_status(root)
        except (OSError, json.JSONDecodeError, TypeError, ValueError):
            status = None
        if isinstance(status, dict):
            actual = str(status.get("status", "fresh"))
            return {
                "status": actual,
                "reason": str(status.get("reason", "Bootstrap snapshot status was recomputed.")),
                "recommendation": str(status.get("recommended_action", "")),
            }
    freshness = snapshot.get("freshness") if isinstance(snapshot.get("freshness"), dict) else {}
    status = str(freshness.get("status") or "fresh")
    if status == "fresh":
        return {
            "status": "fresh",
            "reason": "Bootstrap snapshot is present with safe repo/runtime facts.",
            "recommendation": "",
        }
    return {
        "status": status,
        "reason": f"Bootstrap snapshot freshness is `{status}`.",
        "recommendation": "Refresh the bootstrap snapshot before broad Navigator planning.",
    }


def bootstrap_fit(root: Path, snapshot: dict[str, Any] | None) -> dict[str, Any]:
    status = bootstrap_status(root, snapshot)
    if snapshot is None:
        return {
            **status,
            "label": "missing",
            "score": 35,
            "reason": "Bootstrap Snapshot is missing.",
            "recommendation": status["recommendation"],
        }
    if status["status"] != "fresh":
        return {
            **status,
            "label": "stale",
            "score": 40,
            "reason": status["reason"],
            "recommendation": status["recommendation"],
        }

    scan_limits = snapshot.get("scan_limits") if isinstance(snapshot.get("scan_limits"), dict) else {}
    files_scanned = int(scan_limits.get("files_scanned", 0) or 0)
    max_files = int(scan_limits.get("max_files", 2500) or 2500)
    first_reads = snapshot.get("recommended_first_reads", []) if isinstance(snapshot.get("recommended_first_reads"), list) else []
    manifests = snapshot.get("manifests", []) if isinstance(snapshot.get("manifests"), list) else []
    top_dirs = snapshot.get("top_level_dirs", []) if isinstance(snapshot.get("top_level_dirs"), list) else []
    useful_signals = sum(
        1
        for key in ("languages", "manifests", "test_signals", "ci_signals", "scanner_signals", "recommended_first_reads")
        if isinstance(snapshot.get(key), list) and snapshot.get(key)
    )
    noisy_reasons: list[str] = []
    if files_scanned >= max_files:
        noisy_reasons.append("snapshot hit the file scan limit")
    if len(first_reads) >= 12:
        noisy_reasons.append("recommended first-read list is saturated")
    if len(manifests) > 12:
        noisy_reasons.append("many manifests were detected")
    if len(top_dirs) > 30:
        noisy_reasons.append("many top-level directories were detected")
    if noisy_reasons:
        return {
            **status,
            "label": "noisy",
            "score": 60,
            "reason": "Bootstrap Snapshot is fresh but noisy: " + "; ".join(noisy_reasons) + ".",
            "recommendation": "Use Bootstrap Snapshot as a starting map, but rely on Code Graph Mapper or targeted manifest reads before broad source discovery.",
        }
    if useful_signals:
        return {
            **status,
            "label": "useful",
            "score": 85,
            "reason": f"Bootstrap Snapshot is fresh and contains {useful_signals} useful safe signal group(s).",
            "recommendation": "",
        }
    return {
        **status,
        "label": "missing",
        "score": 45,
        "reason": "Bootstrap Snapshot exists but has little usable repo signal.",
        "recommendation": "Refresh Bootstrap Snapshot and inspect README/manifests directly before broad Navigator planning.",
    }


def band(label: str, score: int, reasons: list[str], recommendations: list[str]) -> dict[str, Any]:
    if score >= 80:
        fit = "strong"
    elif score >= 60:
        fit = "medium"
    elif score >= 40:
        fit = "weak"
    else:
        fit = "missing"
    return {
        "label": label,
        "score": score,
        "fit": fit,
        "reasons": reasons,
        "recommendations": recommendations,
    }


def score_band(score: float) -> str:
    if score >= 80:
        return "80-100"
    if score >= 60:
        return "60-79"
    if score >= 40:
        return "40-59"
    return "0-39"


def recommendation_code(text: str) -> str:
    words: list[str] = []
    for raw in text.lower().replace("/", " ").replace(".", " ").replace(",", " ").split():
        token = "".join(char for char in raw if char.isalnum() or char == "-").strip("-")
        if token and token not in {"the", "and", "for", "with", "when", "where", "before", "after", "tailtrail"}:
            words.append(token)
        if len(words) == 5:
            break
    return "-".join(words) or "review-harness-fit"


def artifact_presence(counts: dict[str, int]) -> dict[str, str]:
    return {key: "present" if int(value) > 0 else "missing" for key, value in counts.items()}


def shareable_summary(review: dict[str, Any]) -> dict[str, Any]:
    created = str(review.get("created_at", ""))
    month = month_key(created)
    counts = {key: int(value) for key, value in review.get("artifact_counts", {}).items()}
    graph = review.get("graph_cache", {}) if isinstance(review.get("graph_cache"), dict) else {}
    summary = {
        "schema_version": "1",
        "type": "tailtrail-harness-summary-shareable",
        "created_month": month,
        "tailtrail_version": "local",
        "overall_fit": str(review.get("overall_fit", "unknown")),
        "overall_score_band": score_band(float(review.get("overall_score", 0.0))),
        "dimension_fits": {
            str(item.get("label", "unknown")): str(item.get("fit", "unknown"))
            for item in review.get("dimensions", [])
            if isinstance(item, dict)
        },
        "artifact_presence": artifact_presence(counts),
        "graph_cache_status": str(graph.get("status", "unknown")),
        "graph_cache_source": str(graph.get("source", "unknown")),
        "recommendation_codes": sorted(
            {
                recommendation_code(str(item.get("recommendation", "")))
                for item in review.get("recommendations", [])
                if isinstance(item, dict)
            }
        ),
        "privacy": "Shareable summary uses allowlisted categorical fields only. No raw prompts, logs, source, file paths, repo names, branches, users, emails, private URLs, package names, customer identifiers, or secrets.",
    }
    validate_shareable_summary(summary)
    return summary


def unsafe_values(value: Any, path: str = "") -> list[str]:
    issues: list[str] = []
    if isinstance(value, dict):
        for key, child in value.items():
            if key not in ALLOWED_SUMMARY_KEYS and path == "":
                issues.append(f"unexpected top-level field `{key}`")
            issues.extend(unsafe_values(child, f"{path}.{key}" if path else str(key)))
    elif isinstance(value, list):
        for index, child in enumerate(value):
            issues.extend(unsafe_values(child, f"{path}[{index}]"))
    elif isinstance(value, str):
        lower = value.lower()
        if any(marker in lower for marker in UNSAFE_TEXT_MARKERS):
            issues.append(f"unsafe text marker at `{path}`")
    return issues


def validate_shareable_summary(summary: dict[str, Any]) -> None:
    missing = sorted(ALLOWED_SUMMARY_KEYS - set(summary))
    unexpected = sorted(set(summary) - ALLOWED_SUMMARY_KEYS)
    issues = [f"missing field `{item}`" for item in missing]
    issues.extend(f"unexpected field `{item}`" for item in unexpected)
    issues.extend(unsafe_values(summary))
    if issues:
        raise SystemExit("Shareable summary failed sanitizer:\n- " + "\n- ".join(issues))


def normalize_category(value: str | None, default: str = "unknown") -> str:
    if not value:
        return default
    lowered = value.strip().lower().replace(" ", "-").replace("_", "-")
    if any(marker in lowered for marker in UNSAFE_TEXT_MARKERS):
        raise SystemExit(f"Shared harness metadata value is not safe to share: `{value}`")
    token = "".join(char for char in lowered if char.isalnum() or char == "-").strip("-")
    return token or default


def normalize_list(values: list[str] | None, default: str = "unknown") -> list[str]:
    normalized: list[str] = []
    for value in values or []:
        for item in value.split(","):
            item = item.strip()
            if item:
                normalized.append(normalize_category(item, default))
    return sorted(set(normalized)) or [default]


def shared_event_from_review(review: dict[str, Any], args: argparse.Namespace) -> dict[str, Any]:
    summary = shareable_summary(review)
    metric = summary["dimension_fits"].get("metric_confidence", "unknown")
    validation = summary["dimension_fits"].get("validation_fit", "unknown")
    learning = summary["dimension_fits"].get("learning_fit", "unknown")
    token = review.get("token_harness", {}) if isinstance(review.get("token_harness"), dict) else {}
    return {
        "schema_version": "1",
        "event_type": "harness_summary",
        "tailtrail_version": summary["tailtrail_version"],
        "created_month": summary["created_month"],
        "task_type": normalize_category(getattr(args, "task_type", None)),
        "language_family": normalize_category(getattr(args, "language_family", None)),
        "workflow_selected": normalize_list(getattr(args, "workflow", None)),
        "review_scope": normalize_category(getattr(args, "review_scope", None)),
        "requirement_fulfillment": normalize_category(getattr(args, "requirement_fulfillment", None)),
        "clarification_needed": bool(getattr(args, "clarification_needed", False)),
        "validation_fit": normalize_category(getattr(args, "validation_fit", None), validation),
        "token_budget_fit": normalize_category(getattr(args, "token_budget_fit", None)),
        "metric_confidence": normalize_category(getattr(args, "metric_confidence", None), metric),
        "learning_signal": normalize_category(getattr(args, "learning_signal", None), learning),
        "scanner_type": normalize_category(getattr(args, "scanner_type", None)),
        "issue_type": normalize_category(getattr(args, "issue_type", None)),
        "token_strategy": normalize_category(str(token.get("strategy", "unknown"))),
        "token_exactness_class": normalize_category(str(token.get("exactness_class", "unknown"))),
        "token_evidence_label": normalize_category(str(token.get("evidence_label", "unknown"))),
        "token_reduction_band": normalize_category(str(token.get("reduction_band", "unknown"))),
        "token_proof_label": normalize_category(str(token.get("proof_label", "unknown"))),
        "token_quality_outcome": normalize_category(str(token.get("quality_outcome", "unknown"))),
        "token_holdout": normalize_category(str(token.get("holdout", "unknown"))),
        "token_confidence_gate": normalize_category(str(token.get("confidence_gate", "unknown"))),
        "overall_fit": summary["overall_fit"],
        "overall_score_band": summary["overall_score_band"],
        "dimension_fits": summary["dimension_fits"],
        "artifact_presence": summary["artifact_presence"],
        "graph_cache_status": summary["graph_cache_status"],
        "graph_cache_source": summary["graph_cache_source"],
        "recommendation_codes": summary["recommendation_codes"],
        "privacy": "Commit-friendly categorical TailTrail harness metadata only. No prompts, responses, source, diffs, paths, repo names, users, emails, tickets, private URLs, package names, scanner raw output, secrets, or exact token usage.",
    }


def validate_shared_event(event: dict[str, Any]) -> None:
    missing = sorted(ALLOWED_SHARED_EVENT_KEYS - set(event))
    unexpected = sorted(set(event) - ALLOWED_SHARED_EVENT_KEYS)
    issues = [f"missing field `{item}`" for item in missing]
    issues.extend(f"unexpected field `{item}`" for item in unexpected)
    issues.extend(unsafe_values_with_allowed(event, ALLOWED_SHARED_EVENT_KEYS))
    if event.get("event_type") != "harness_summary":
        issues.append("event_type must be `harness_summary`")
    if not isinstance(event.get("clarification_needed"), bool):
        issues.append("clarification_needed must be boolean")
    if not isinstance(event.get("workflow_selected"), list):
        issues.append("workflow_selected must be a list")
    if issues:
        raise SystemExit("Shared harness metadata failed sanitizer:\n- " + "\n- ".join(issues))


def unsafe_values_with_allowed(value: Any, allowed: set[str], path: str = "") -> list[str]:
    issues: list[str] = []
    if isinstance(value, dict):
        for key, child in value.items():
            if key not in allowed and path == "":
                issues.append(f"unexpected top-level field `{key}`")
            issues.extend(unsafe_values_with_allowed(child, allowed, f"{path}.{key}" if path else str(key)))
    elif isinstance(value, list):
        for index, child in enumerate(value):
            issues.extend(unsafe_values_with_allowed(child, allowed, f"{path}[{index}]"))
    elif isinstance(value, str):
        lower = value.lower()
        if any(marker in lower for marker in UNSAFE_TEXT_MARKERS):
            issues.append(f"unsafe text marker at `{path}`")
    return issues


def shared_schema() -> dict[str, Any]:
    properties = {key: {"description": "Allowlisted categorical TailTrail harness metadata."} for key in sorted(ALLOWED_SHARED_EVENT_KEYS)}
    properties["clarification_needed"] = {"type": "boolean"}
    properties["workflow_selected"] = {"type": "array", "items": {"type": "string"}}
    return {
        "$schema": "https://json-schema.org/draft/2020-12/schema",
        "title": "TailTrail Shared Harness Summary Event",
        "type": "object",
        "additionalProperties": False,
        "required": sorted(ALLOWED_SHARED_EVENT_KEYS),
        "properties": properties,
    }


def shared_readme() -> str:
    return """# TailTrail Shared Metadata

This folder is for sanitized TailTrail process metadata that a repository may choose to commit.

Shared files must contain categorical workflow evidence only. They must not contain raw prompts, assistant responses, source code, diffs, file paths, repo names, branch names, users, emails, private URLs, package names, scanner raw output, secrets, or exact token usage.

Supported shared files:

- `code-graph-cache.json`: shared code graph cache for faster repo understanding.
- `harness-summary.jsonl`: optional append-only Meta-Harness evidence events, including sanitized categorical Token Harness feedback such as strategy, exactness class, reduction band, proof label, quality outcome, holdout, and confidence gate.
- `harness-summary.schema.json`: schema for the shared harness summary event shape.

`.tailtrail/` remains local private runtime state. Review this folder before committing it for the first time.
"""


def write_shared_companions(root: Path) -> None:
    directory = root / SHARED_META_DIR
    directory.mkdir(parents=True, exist_ok=True)
    readme = root / SHARED_README
    schema = root / SHARED_SCHEMA
    if not readme.exists():
        readme.write_text(shared_readme(), encoding="utf-8")
    if not schema.exists():
        schema.write_text(json.dumps(shared_schema(), indent=2, sort_keys=True) + "\n", encoding="utf-8")


def append_shared_event(root: Path, event: dict[str, Any]) -> Path:
    validate_shared_event(event)
    write_shared_companions(root)
    path = root / SHARED_HARNESS_SUMMARY
    with path.open("a", encoding="utf-8") as handle:
        handle.write(json.dumps(event, sort_keys=True) + "\n")
    return path


def validate_shared_file(root: Path) -> dict[str, Any]:
    path = root / SHARED_HARNESS_SUMMARY
    events: list[dict[str, Any]] = []
    issues: list[str] = []
    if not path.exists():
        return {"path": SHARED_HARNESS_SUMMARY.as_posix(), "exists": False, "events": 0, "valid": True, "issues": []}
    for number, line in enumerate(path.read_text(encoding="utf-8").splitlines(), start=1):
        if not line.strip():
            continue
        try:
            event = json.loads(line)
        except json.JSONDecodeError as exc:
            issues.append(f"line {number}: invalid JSON: {exc.msg}")
            continue
        if not isinstance(event, dict):
            issues.append(f"line {number}: event is not an object")
            continue
        try:
            validate_shared_event(event)
        except SystemExit as exc:
            issues.append(f"line {number}: {exc}")
        events.append(event)
    return {
        "path": SHARED_HARNESS_SUMMARY.as_posix(),
        "exists": True,
        "events": len(events),
        "valid": not issues,
        "issues": issues,
    }


def run_git(root: Path, args: list[str]) -> subprocess.CompletedProcess[str]:
    return subprocess.run(["git", *args], cwd=root, text=True, capture_output=True, check=False)


def shared_status(root: Path) -> dict[str, Any]:
    rel = SHARED_HARNESS_SUMMARY.as_posix()
    validation = validate_shared_file(root)
    tracked = run_git(root, ["ls-files", "--error-unmatch", rel]).returncode == 0
    ignored = run_git(root, ["check-ignore", "-q", rel]).returncode == 0
    return {
        "type": "tailtrail-shared-harness-status",
        "schema_version": "1",
        "path": rel,
        "exists": validation["exists"],
        "tracked": tracked,
        "ignored": ignored,
        "valid": validation["valid"],
        "events": validation["events"],
        "issues": validation["issues"],
        "recommendation": shared_status_recommendation(validation["exists"], tracked, ignored, validation["valid"]),
    }


def shared_status_recommendation(exists: bool, tracked: bool, ignored: bool, valid: bool) -> str:
    if not exists:
        return "No shared harness metadata file exists yet. Use shared-summary --dry-run first."
    if not valid:
        return "Fix sanitizer issues before committing shared harness metadata."
    if ignored:
        return "File is ignored. Review .gitignore if the repo wants shared TailTrail harness metadata."
    if tracked:
        return "Shared harness metadata is tracked and sanitizer passed."
    return "Shared harness metadata exists and sanitizer passed. Review it before adding to git."


def build_review(root: Path, month: str | None) -> dict[str, Any]:
    quality = filter_month(read_jsonl(root / QUALITY_EVENTS), month)
    outcomes = filter_month(read_jsonl(root / OUTCOME_EVENTS), month)
    learnings = filter_month(read_jsonl(root / LEARNING_EVENTS), month)
    refresh_actions = filter_month(read_jsonl(root / LEARNING_REFRESH_ACTIONS), month)
    budget_events = filter_month(read_jsonl(root / TOKEN_BUDGET_EVENTS), month)
    receipts = filter_month(read_jsonl(root / CONTEXT_RECEIPTS), month)
    token_usage = filter_month(read_jsonl(root / TOKEN_USAGE), month)
    token_harness = token_harness_summary(root, token_usage)
    bootstrap = read_json(root / BOOTSTRAP)
    graph = graph_status(root)

    quality_total = len(quality)
    outcome_total = len(outcomes)
    learning_total = len(learnings)

    fit_counts = count_values(quality, "workflow_fit")
    too_heavy = int(fit_counts.get("too-heavy", 0))
    too_light = int(fit_counts.get("too-light", 0))
    correct = int(fit_counts.get("correct", 0))
    workflow_score = 50
    workflow_reasons: list[str] = []
    workflow_recs: list[str] = []
    if quality_total:
        workflow_score = max(10, 90 - int(((too_heavy + too_light) / quality_total) * 70))
        workflow_reasons.append(f"{quality_total} quality event(s) checked; {correct} marked correct.")
        if too_heavy:
            workflow_recs.append("Review Navigator tiny/small-task routing; some events were marked too-heavy.")
        if too_light:
            workflow_recs.append("Review missed-gate routing; some events were marked too-light.")
    else:
        workflow_reasons.append("No quality-loop events found.")
        workflow_recs.append("Capture approved quality-loop events after meaningful tasks before tuning workflow rules.")

    bootstrap_fit_info = bootstrap_fit(root, bootstrap)
    bootstrap_score = int(bootstrap_fit_info["score"])
    bootstrap_reasons = [bootstrap_fit_info["reason"]]
    bootstrap_recs = [bootstrap_fit_info["recommendation"]] if bootstrap_fit_info["recommendation"] else []

    graph_present = graph["status"] not in {"missing", "invalid"}
    receipt_total = len(receipts)
    context_score = 40
    context_reasons: list[str] = []
    context_recs: list[str] = []
    if graph_present:
        context_score += 25
        context_reasons.append(f"Code graph cache is {graph['status']} from {graph['source']} metadata.")
    else:
        context_reasons.append("No valid code graph cache found.")
        context_recs.append("Use Code Graph Mapper for broad review, scanner, handoff, or implementation tasks before broad source reads.")
    if receipt_total:
        context_score += 25
        avoided = sum(int(item.get("avoided_tokens", 0)) for item in receipts)
        loaded = sum(int(item.get("loaded_tokens", 0)) for item in receipts)
        context_reasons.append(f"{receipt_total} context receipt(s) found; loaded approx {loaded}, avoided approx {avoided} tokens.")
    else:
        context_recs.append("Capture context receipts for tasks where token/value claims matter.")
    context_score = min(context_score, 95)

    validation_counts = count_values([*quality, *outcomes], "validation_outcome")
    validation_events = sum(validation_counts.values())
    validation_pass = int(validation_counts.get("pass", 0))
    validation_weak = int(validation_counts.get("not-run", 0)) + int(validation_counts.get("skipped", 0)) + int(validation_counts.get("unknown", 0))
    validation_score = 50
    validation_reasons: list[str] = []
    validation_recs: list[str] = []
    if validation_events:
        validation_score = max(15, 85 - int((validation_weak / validation_events) * 60))
        validation_reasons.append(f"{validation_events} validation signal(s); {validation_pass} pass, {validation_weak} weak or unknown.")
        if validation_weak:
            validation_recs.append("Require focused validation evidence before high-confidence value or quality claims.")
    else:
        validation_reasons.append("No validation outcome signals found.")
        validation_recs.append("Record validation outcome in quality-loop or outcome telemetry after meaningful work.")

    metric_score = 35
    metric_reasons: list[str] = []
    metric_recs: list[str] = []
    if token_usage:
        metric_score += 35
        metric_reasons.append(f"{len(token_usage)} measured token telemetry record(s) found.")
    else:
        metric_reasons.append("No measured token telemetry found.")
        metric_recs.append("Keep token savings claims directional until measured telemetry is imported.")
    if receipts:
        metric_score += 20
        metric_reasons.append("Context receipts provide local approximate token evidence.")
    if outcomes:
        metric_score += 10
        metric_reasons.append(f"{outcome_total} outcome event(s) can support value reporting.")
    metric_score = min(metric_score, 95)

    learning_score = 45
    learning_reasons: list[str] = []
    learning_recs: list[str] = []
    if learning_total:
        high = sum(1 for event in learnings if int(event.get("confidence_score", event.get("score", 0)) or 0) >= 80)
        learning_score += 25
        learning_reasons.append(f"{learning_total} learning event(s); {high} high-confidence reusable pattern(s).")
    else:
        learning_reasons.append("No learning events found.")
    if (root / LEARNING_INDEX).exists() or (root / GRAPH_LEARNING_INDEX).exists():
        learning_score += 15
        learning_reasons.append("Learning index is present.")
    else:
        learning_recs.append("Build or refresh learning indexes only after approved reusable learnings exist.")
    if refresh_actions:
        learning_score += 10
        learning_reasons.append(f"{len(refresh_actions)} learning refresh action(s) found.")
    learning_score = min(learning_score, 95)

    scanner_score = 50
    scanner_reasons: list[str] = []
    scanner_recs: list[str] = []
    quality_runs = root / QUALITY_RUNS
    vulnerability_runs = root / VULNERABILITY_RUNS
    if quality_runs.exists() or vulnerability_runs.exists():
        scanner_score += 25
        scanner_reasons.append("Approved local quality or vulnerability run output exists.")
    else:
        scanner_reasons.append("No approved local scanner run output found.")
    missed_gates = count_values(quality, "missed_gate_flags")
    missed_total = sum(missed_gates.values())
    if missed_total:
        scanner_score -= min(30, missed_total * 10)
        scanner_recs.append("Review missed gate flags; TailTrail may be skipping scanner/security routes.")
    scanner_score = max(10, min(scanner_score, 90))

    code_precision_score = 45
    code_precision_reasons: list[str] = []
    code_precision_recs: list[str] = []
    if graph_present:
        code_precision_score += 25
        code_precision_reasons.append("Code graph cache can provide read-order and related-file guidance.")
    if quality or outcomes:
        code_precision_score += 15
        code_precision_reasons.append("Outcome or quality events can connect workflow fit to implementation results.")
    if not graph_present:
        code_precision_recs.append("Create or refresh Code Graph Mapper cache before broad code review or scanner remediation.")
    code_precision_score = min(code_precision_score, 90)

    dimensions = [
        band("workflow_fit", workflow_score, workflow_reasons, workflow_recs),
        {**band("bootstrap_fit", bootstrap_score, bootstrap_reasons, bootstrap_recs), "bootstrap_fit_label": bootstrap_fit_info["label"]},
        band("context_fit", context_score, context_reasons, context_recs),
        band("validation_fit", validation_score, validation_reasons, validation_recs),
        band("metric_confidence", metric_score, metric_reasons, metric_recs),
        band("learning_fit", learning_score, learning_reasons, learning_recs),
        band("scanner_security_fit", scanner_score, scanner_reasons, scanner_recs),
        band("code_precision_fit", code_precision_score, code_precision_reasons, code_precision_recs),
    ]
    overall = round(sum(item["score"] for item in dimensions) / len(dimensions), 2)
    recommendations = [
        {"dimension": item["label"], "recommendation": rec}
        for item in dimensions
        for rec in item["recommendations"]
    ]

    return {
        "schema_version": "1",
        "type": "tailtrail-harness-review",
        "created_at": now(),
        "root": root.resolve().as_posix(),
        "month": month or "all",
        "overall_score": overall,
        "overall_fit": band("overall", int(overall), [], [])["fit"],
        "dimensions": dimensions,
        "artifact_counts": {
            "quality_events": quality_total,
            "outcome_events": outcome_total,
            "learning_events": learning_total,
            "learning_refresh_actions": len(refresh_actions),
            "token_budget_events": len(budget_events),
            "context_receipts": len(receipts),
            "token_usage_records": len(token_usage),
            "token_harness_events": int(token_harness.get("event_count", 0)),
            "bootstrap_snapshot": 1 if bootstrap else 0,
        },
        "token_harness": token_harness,
        "bootstrap_fit": bootstrap_fit_info,
        "graph_cache": graph,
        "recommendations": recommendations,
        "privacy": "Layer 1 is local-only. Do not commit .tailtrail harness outputs. No raw prompts, source snippets, logs, secrets, PII, PHI, customer data, repo names, or user identities are required.",
    }


def render_markdown(review: dict[str, Any], compact: bool = False) -> str:
    lines = [
        "# TailTrail Harness Review",
        "",
        f"- Root: `{review['root']}`",
        f"- Month: `{review['month']}`",
        f"- Overall fit: `{review['overall_fit']}`",
        f"- Overall score: `{review['overall_score']}`",
        "",
        "## Dimensions",
        "",
    ]
    for item in review["dimensions"]:
        lines.append(f"### {item['label']}")
        lines.append("")
        lines.append(f"- Fit: `{item['fit']}`")
        lines.append(f"- Score: `{item['score']}`")
        if item.get("bootstrap_fit_label"):
            lines.append(f"- Bootstrap Fit Label: `{item['bootstrap_fit_label']}`")
        for reason in item["reasons"]:
            lines.append(f"- Evidence: {reason}")
        if item["recommendations"]:
            for rec in item["recommendations"]:
                lines.append(f"- Recommendation: {rec}")
        elif not compact:
            lines.append("- Recommendation: no immediate action.")
        lines.append("")
    lines.extend(["## Artifact Counts", ""])
    for key, value in review["artifact_counts"].items():
        lines.append(f"- {key}: `{value}`")
    lines.extend(["", "## Recommendations", ""])
    if review["recommendations"]:
        for item in review["recommendations"]:
            lines.append(f"- `{item['dimension']}`: {item['recommendation']}")
    else:
        lines.append("- No immediate harness tuning recommendations.")
    lines.extend(
        [
            "",
            "## Boundaries",
            "",
            "- Layer 1 is local-only and read-only unless `--write-result` is used.",
            "- Do not commit `.tailtrail/harness-review.md`, `.tailtrail/harness-summary.json`, or `.tailtrail/harness-recommendations.json`.",
            "- Harness findings are advisory. Current source, tests, CI, scanners, policy, guardrails, and explicit user instructions always win.",
        ]
    )
    return "\n".join(lines) + "\n"


def write_outputs(root: Path, review: dict[str, Any]) -> None:
    trail = root / TAILTRAIL_DIR
    trail.mkdir(parents=True, exist_ok=True)
    (root / HARNESS_REVIEW).write_text(render_markdown(review), encoding="utf-8")
    (root / HARNESS_RECOMMENDATIONS).write_text(json.dumps(review["recommendations"], indent=2, sort_keys=True) + "\n", encoding="utf-8")
    summary = {
        "schema_version": review["schema_version"],
        "type": "tailtrail-harness-summary-local",
        "created_at": review["created_at"],
        "month": review["month"],
        "overall_score": review["overall_score"],
        "overall_fit": review["overall_fit"],
        "artifact_counts": review["artifact_counts"],
        "token_harness": review.get("token_harness", {}),
        "recommendation_count": len(review["recommendations"]),
        "privacy": "Local .tailtrail summary only. Not for git sharing.",
    }
    (root / HARNESS_LOCAL_SUMMARY).write_text(json.dumps(summary, indent=2, sort_keys=True) + "\n", encoding="utf-8")


def write_shareable_summary(root: Path, summary: dict[str, Any]) -> Path:
    path = root / HARNESS_SUMMARY
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(summary, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    return path


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description="Review local TailTrail harness behavior from compact local artifacts.")
    subparsers = parser.add_subparsers(dest="command", required=True)
    for command in ("quick", "review", "confidence", "recommendations"):
        sub = subparsers.add_parser(command, help=f"Run local harness {command}.")
        sub.add_argument("--root", type=Path, default=Path("."), help="Target repo root.")
        sub.add_argument("--month", help="Optional YYYY-MM filter.")
        sub.add_argument("--format", choices=("markdown", "json"), default="markdown")
        sub.add_argument("--write-result", action="store_true", help="Write local .tailtrail harness outputs.")
    export = subparsers.add_parser("export-summary", help="Create an allowlisted sanitized shareable harness summary.")
    export.add_argument("--root", type=Path, default=Path("."), help="Target repo root.")
    export.add_argument("--month", help="Optional YYYY-MM filter.")
    export.add_argument("--from", dest="from_path", type=Path, help="Accepted for CLI compatibility; Layer 2 exports are rebuilt from local artifacts.")
    export.add_argument("--format", choices=("markdown", "json"), default="markdown")
    export.add_argument("--write-result", action="store_true", help="Write .tailtrail/harness-summary.json after sanitizer checks.")
    shared = subparsers.add_parser("shared-summary", help="Create or append sanitized commit-friendly harness metadata.")
    shared.add_argument("--root", type=Path, default=Path("."), help="Target repo root.")
    shared.add_argument("--month", help="Optional YYYY-MM filter.")
    shared.add_argument("--format", choices=("markdown", "json"), default="markdown")
    shared.add_argument("--dry-run", action="store_true", help="Show the event without writing it.")
    shared.add_argument("--write-result", action="store_true", help="Append to tailtrail-meta/harness-summary.jsonl.")
    shared.add_argument("--approved", action="store_true", help="Required with --write-result.")
    shared.add_argument("--task-type", help="Categorical task type, such as bug-fix-with-tests.")
    shared.add_argument("--language-family", help="Categorical language family, such as python, java, dotnet, sql, terraform.")
    shared.add_argument("--workflow", action="append", help="Workflow category or comma-separated categories.")
    shared.add_argument("--review-scope", help="Review scope category, such as uncommitted, branch, path, full-repo.")
    shared.add_argument("--requirement-fulfillment", help="Requirement fulfillment category.")
    shared.add_argument("--clarification-needed", action="store_true", help="Mark that clarification was needed.")
    shared.add_argument("--validation-fit", help="Validation fit category.")
    shared.add_argument("--token-budget-fit", help="Token budget fit category.")
    shared.add_argument("--metric-confidence", help="Metric confidence category.")
    shared.add_argument("--learning-signal", help="Learning signal category.")
    shared.add_argument("--scanner-type", help="Scanner category, such as sonar, sarif, trivy, grype.")
    shared.add_argument("--issue-type", help="Issue category, such as validation-gap or routing-too-heavy.")
    status = subparsers.add_parser("shared-status", help="Check shared harness metadata tracking and sanitizer status.")
    status.add_argument("--root", type=Path, default=Path("."), help="Target repo root.")
    status.add_argument("--month", help=argparse.SUPPRESS)
    status.add_argument("--format", choices=("markdown", "json"), default="markdown")
    sanitize = subparsers.add_parser("shared-sanitize", help="Validate tailtrail-meta/harness-summary.jsonl.")
    sanitize.add_argument("--root", type=Path, default=Path("."), help="Target repo root.")
    sanitize.add_argument("--month", help=argparse.SUPPRESS)
    sanitize.add_argument("--format", choices=("markdown", "json"), default="markdown")
    return parser


def main() -> int:
    parser = build_parser()
    args = parser.parse_args()
    root = args.root.resolve()
    review = build_review(root, args.month)
    if args.command in {"quick", "review", "confidence", "recommendations"} and getattr(args, "write_result", False):
        write_outputs(root, review)

    if args.command == "export-summary":
        summary = shareable_summary(review)
        written: Path | None = None
        if args.write_result:
            written = write_shareable_summary(root, summary)
        if args.format == "json":
            print(json.dumps(summary, indent=2, sort_keys=True))
        else:
            print("# TailTrail Shareable Harness Summary\n")
            print("- Status: sanitizer passed")
            print("- Scope: allowlisted categorical fields only")
            print("- Writes: `.tailtrail/harness-summary.json` only when `--write-result` is used")
            if args.from_path:
                print("- Note: `--from` was accepted for compatibility; summary was rebuilt from local compact artifacts.")
            if written:
                print(f"- Written: `{written.as_posix()}`")
            print("\n```json")
            print(json.dumps(summary, indent=2, sort_keys=True))
            print("```")
        return 0

    if args.command == "shared-summary":
        event = shared_event_from_review(review, args)
        validate_shared_event(event)
        written: Path | None = None
        if args.write_result and not args.approved:
            raise SystemExit("Refusing to write shared harness metadata without --approved.")
        if args.write_result:
            written = append_shared_event(root, event)
        if args.format == "json":
            print(json.dumps(event, indent=2, sort_keys=True))
        else:
            print("# TailTrail Shared Harness Metadata\n")
            print("- Status: sanitizer passed")
            print("- Scope: commit-friendly categorical metadata")
            print("- Target: `tailtrail-meta/harness-summary.jsonl`")
            if args.write_result:
                print(f"- Written: `{written.as_posix() if written else SHARED_HARNESS_SUMMARY.as_posix()}`")
            else:
                print("- Mode: dry-run; nothing was written")
            print("\n```json")
            print(json.dumps(event, indent=2, sort_keys=True))
            print("```")
        return 0

    if args.command in {"shared-status", "shared-sanitize"}:
        status = shared_status(root)
        if args.command == "shared-sanitize" and not status["valid"]:
            exit_code = 1
        else:
            exit_code = 0
        if args.format == "json":
            print(json.dumps(status, indent=2, sort_keys=True))
        else:
            title = "TailTrail Shared Harness Sanitizer" if args.command == "shared-sanitize" else "TailTrail Shared Harness Status"
            print(f"# {title}\n")
            print(f"- Path: `{status['path']}`")
            print(f"- Exists: `{str(status['exists']).lower()}`")
            print(f"- Tracked: `{str(status['tracked']).lower()}`")
            print(f"- Ignored: `{str(status['ignored']).lower()}`")
            print(f"- Valid: `{str(status['valid']).lower()}`")
            print(f"- Events: `{status['events']}`")
            print(f"- Recommendation: {status['recommendation']}")
            if status["issues"]:
                print("\n## Issues\n")
                for issue in status["issues"]:
                    print(f"- {issue}")
        return exit_code

    if args.command == "confidence":
        payload = {
            "type": "tailtrail-harness-confidence",
            "overall_score": review["overall_score"],
            "overall_fit": review["overall_fit"],
            "metric_confidence": next(item for item in review["dimensions"] if item["label"] == "metric_confidence"),
            "artifact_counts": review["artifact_counts"],
        }
        if args.format == "json":
            print(json.dumps(payload, indent=2, sort_keys=True))
        else:
            print("# TailTrail Harness Confidence\n")
            print(f"- Overall fit: `{payload['overall_fit']}`")
            print(f"- Overall score: `{payload['overall_score']}`")
            print(f"- Metric confidence: `{payload['metric_confidence']['fit']}`")
        return 0

    if args.command == "recommendations":
        payload = {"type": "tailtrail-harness-recommendations", "recommendations": review["recommendations"]}
        if args.format == "json":
            print(json.dumps(payload, indent=2, sort_keys=True))
        else:
            print("# TailTrail Harness Recommendations\n")
            if review["recommendations"]:
                for item in review["recommendations"]:
                    print(f"- `{item['dimension']}`: {item['recommendation']}")
            else:
                print("- No immediate harness tuning recommendations.")
        return 0

    if args.format == "json":
        print(json.dumps(review, indent=2, sort_keys=True))
    else:
        print(render_markdown(review, compact=args.command == "quick"), end="")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
