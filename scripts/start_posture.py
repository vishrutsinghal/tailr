"""Evidence and operational posture builders for TailTrail Start.

These helpers are deliberately side-effect free. They assemble local planning
metadata only; execution and report rendering remain in ``task-start.py``.
"""
from __future__ import annotations

import json
import math
import re
from pathlib import Path
from typing import Any

import code_graph_inventory
import code_relationships


SLICE_MARGIN_LINES = 20
BEHAVIOR_WINDOW_LINES = 160
SMALL_FILE_LINES = 240


def approx_tokens(chars: int, chars_per_token: int) -> int:
    return math.ceil(chars / chars_per_token) if chars > 0 else 0


def file_chars(path: Path) -> int:
    try:
        return len(path.read_text(encoding="utf-8"))
    except (OSError, UnicodeDecodeError):
        return 0


def existing_file_tokens(root: Path, paths: list[str], chars_per_token: int) -> tuple[int, list[dict[str, Any]]]:
    total, files = 0, []
    for item in paths:
        path = root / item
        if not path.is_file():
            continue
        chars = file_chars(path)
        tokens = approx_tokens(chars, chars_per_token)
        total += tokens
        files.append({"path": item, "chars": chars, "approx_tokens": tokens})
    return total, files


def _merge_ranges(ranges: list[tuple[int, int]], line_count: int) -> list[tuple[int, int]]:
    normalized = sorted(
        (max(1, start), min(line_count, end))
        for start, end in ranges
        if start <= end and line_count > 0
    )
    merged: list[list[int]] = []
    for start, end in normalized:
        if merged and start <= merged[-1][1] + 1:
            merged[-1][1] = max(merged[-1][1], end)
        else:
            merged.append([start, end])
    return [(start, end) for start, end in merged]


def context_slices(root: Path, plan: dict[str, Any], chars_per_token: int) -> list[dict[str, Any]]:
    """Derive a small working set from existing owner, literal, and proof evidence."""
    scope = plan.get("scope_evidence") if isinstance(plan.get("scope_evidence"), dict) else {}
    purposes: dict[str, str] = {}
    for requirement in scope.get("requirements", []):
        if not isinstance(requirement, dict):
            continue
        for path in requirement.get("implementation_owners", []):
            purposes[str(path)] = "implementation"
        for path in requirement.get("inspection_paths", []):
            purposes.setdefault(str(path), "inspection")
        for path in requirement.get("proof_paths", []):
            purposes.setdefault(str(path), "proof")
    candidate_roles = {
        str(row.get("path")): str(row.get("role"))
        for row in scope.get("candidates", [])
        if isinstance(row, dict)
    }
    for path, purpose in list(purposes.items()):
        if candidate_roles.get(path) == "configuration":
            purposes[path] = "configuration"

    literals = list(dict.fromkeys(
        str(value).strip()
        for row in plan.get("requirement_matrix", [])
        if isinstance(row, dict)
        for value in row.get("quoted_literals", [])
        if str(value).strip()
    ))
    query_terms = {
        str(value).casefold()
        for row in plan.get("requirement_matrix", [])
        if isinstance(row, dict)
        for value in row.get("query_terms", [])
        if len(str(value)) >= 4
    }
    owner_stems = {
        Path(path).stem.casefold()
        for path, purpose in purposes.items()
        if purpose == "implementation"
    }
    inspection_stems = {
        Path(path).stem.casefold()
        for path, purpose in purposes.items()
        if purpose in {"inspection", "configuration"}
    }
    slices: list[dict[str, Any]] = []
    for relative, purpose in sorted(purposes.items()):
        path = root / relative
        try:
            text = path.read_text(encoding="utf-8")
        except (OSError, UnicodeDecodeError):
            slices.append({
                "path": relative, "purpose": purpose, "symbols": [],
                "start_line": None, "end_line": None,
                "reason": "scoped path is not safely readable for slice estimation",
                "confidence": "low",
                "expansion_trigger": "resolve a safe readable symbol range before focused estimation",
            })
            continue
        lines = text.splitlines() or [""]
        facts = code_relationships.extract(path, root, text)
        definitions = [row for row in facts.get("definitions", []) if int(row.get("line", 0)) > 0]
        ranges: list[tuple[int, int]] = []
        strong_anchor = False

        literal_lines = [
            index for index, line in enumerate(lines, start=1)
            if any(literal.casefold() in line.casefold() for literal in literals)
        ]
        for line in literal_lines[:8]:
            ranges.append((line - SLICE_MARGIN_LINES, line + SLICE_MARGIN_LINES))
        strong_anchor = bool(literal_lines)

        if purpose == "implementation":
            bindings = {
                str(row.get("value"))
                for row in facts.get("behavior", [])
                if row.get("kind") == "import-binding"
                and any(stem in str(row.get("detail", "")).casefold() for stem in inspection_stems)
            }
            call_lines = [
                int(row.get("line", 0))
                for row in facts.get("behavior", [])
                if row.get("kind") == "call" and str(row.get("value")) in bindings
            ]
            for line in call_lines[:8]:
                ranges.append((line - SLICE_MARGIN_LINES, line + BEHAVIOR_WINDOW_LINES))
            strong_anchor = strong_anchor or bool(call_lines)
            stem = Path(relative).stem.casefold()
            matching_definitions = [
                row for row in definitions
                if str(row.get("value", "")).casefold() == stem
                or query_terms.intersection(re.findall(r"[a-z0-9]+", str(row.get("value", "")).casefold()))
            ]
            for row in (matching_definitions or definitions[:1]):
                line = int(row["line"])
                ranges.append((line - SLICE_MARGIN_LINES, line + SLICE_MARGIN_LINES))
        elif purpose == "proof":
            proof_lines = [
                index for index, line in enumerate(lines, start=1)
                if any(stem in line.casefold() for stem in owner_stems)
                or any(marker in line for marker in ("describe(", "it(", "test("))
            ]
            for line in proof_lines[:12]:
                ranges.append((line - SLICE_MARGIN_LINES, line + SLICE_MARGIN_LINES))
            strong_anchor = bool(proof_lines and definitions)
        else:
            for row in definitions[:4]:
                line = int(row["line"])
                ranges.append((line - SLICE_MARGIN_LINES, line + SLICE_MARGIN_LINES))

        confidence = "high" if strong_anchor and definitions else "medium" if ranges else "low"
        confidence_reason = (
            "exact behavior and owning-symbol anchors were resolved"
            if confidence == "high"
            else "a bounded range was resolved, but exact behavior-and-symbol anchoring is incomplete"
            if confidence == "medium"
            else "no bounded symbol or behavior range was resolved"
        )
        if not ranges and len(lines) <= SMALL_FILE_LINES:
            ranges = [(1, len(lines))]
            confidence = "medium"
            confidence_reason = "the whole scoped file is small, but no narrower symbol or behavior anchor was resolved"
        if not ranges:
            slices.append({
                "path": relative, "purpose": purpose,
                "symbols": [str(row.get("value")) for row in definitions[:4]],
                "start_line": None, "end_line": None,
                "reason": "filename is scoped but no bounded symbol or behavior range was resolved",
                "confidence": "low",
                "confidence_reason": confidence_reason,
                "expansion_trigger": "resolve the owning symbol or load the full scoped file",
            })
            continue
        for start, end in _merge_ranges(ranges, len(lines)):
            body = "\n".join(lines[start - 1:end])
            symbols = [
                str(row.get("value")) for row in definitions
                if start <= int(row.get("line", 0)) <= end
            ]
            slices.append({
                "path": relative,
                "purpose": purpose,
                "symbols": list(dict.fromkeys(symbols)),
                "start_line": start,
                "end_line": end,
                "reason": {
                    "implementation": "owns the selected behavior and its bounded handler dependencies",
                    "inspection": "provides directly related implementation evidence",
                    "proof": "contains the directly linked focused proof",
                    "configuration": "configures the selected implementation owner",
                }[purpose],
                "confidence": confidence,
                "confidence_reason": confidence_reason,
                "estimated_tokens": approx_tokens(len(body), chars_per_token),
                "expansion_trigger": "required state, handler, error path, or proof dependency falls outside this slice",
            })
    return slices


def repository_context_ceiling(
    root: Path,
    scoped_paths: list[str],
    chars_per_token: int,
) -> dict[str, int]:
    """Estimate readable repository context from metadata without reading bodies."""
    root = root.resolve()
    paths = {path.resolve() for path in code_graph_inventory.relevant_files(root)}
    for relative in scoped_paths:
        path = (root / relative).resolve()
        try:
            path.relative_to(root)
        except ValueError:
            continue
        if path.is_file():
            paths.add(path)
    total_bytes = 0
    readable_files = 0
    for path in paths:
        try:
            total_bytes += path.stat().st_size
            readable_files += 1
        except OSError:
            continue
    return {
        "file_count": readable_files,
        "bytes": total_bytes,
        "approx_tokens": approx_tokens(total_bytes, chars_per_token),
    }


def saving_techniques(plan: dict[str, Any], repository_files: int, scoped_files: int) -> list[str]:
    """Name only major token controls evidenced in the current plan."""
    techniques: list[str] = []
    evidence = plan.get("scope_evidence") if isinstance(plan.get("scope_evidence"), dict) else {}
    investigation = evidence.get("investigation") if isinstance(evidence.get("investigation"), dict) else {}
    cache = investigation.get("cache") if isinstance(investigation.get("cache"), dict) else {}
    if cache.get("status") == "fresh":
        techniques.append("Code Graph slice reuse")
    if repository_files > scoped_files and scoped_files > 0:
        techniques.append("Navigator scope narrowing")
    requirements = [row for row in plan.get("requirement_matrix", []) if isinstance(row, dict)]
    if any(
        isinstance(row.get("validation_contract"), dict)
        and row["validation_contract"].get("commands")
        for row in requirements
    ):
        techniques.append("Focused validation selection")
    return techniques[:4]


def token_posture(root: Path, plan: dict[str, Any], large_context_files: tuple[str, ...], chars_per_token: int) -> dict[str, Any]:
    used_paths = list(dict.fromkeys(str(item["path"]) for item in plan.get("likely_impacted_files", []) if isinstance(item, dict) and item.get("path")))
    avoid_text = " ".join(str(item) for item in plan.get("avoid", []))
    avoided_paths = [item for item in large_context_files if item in avoid_text and (root / item).is_file()]
    scoped_file_ceiling, used_files = existing_file_tokens(root, used_paths, chars_per_token)
    slices = context_slices(root, plan, chars_per_token)
    slice_confidences = {str(row.get("confidence", "low")) for row in slices}
    forecast_available = bool(slices) and "low" not in slice_confidences
    planned_working_set = (
        sum(int(row.get("estimated_tokens", 0)) for row in slices)
        if forecast_available
        else None
    )
    used_tokens = int(planned_working_set) if planned_working_set is not None else scoped_file_ceiling
    explicit_avoided_tokens, avoided_files = existing_file_tokens(root, avoided_paths, chars_per_token)
    repository = repository_context_ceiling(root, used_paths, chars_per_token)
    baseline = scoped_file_ceiling
    avoided_tokens = max(0, baseline - used_tokens)
    largest = max(used_files, key=lambda row: int(row.get("approx_tokens", 0)), default=None)
    comparison_available = forecast_available and bool(used_files) and baseline > 0
    confidence = (
        "low" if not forecast_available
        else "medium" if "medium" in slice_confidences
        else "high"
    )
    confidence_reason = (
        "at least one scoped path has no reliable bounded range"
        if confidence == "low"
        else "at least one bounded slice lacks an exact combined behavior-and-symbol anchor"
        if confidence == "medium"
        else "every planned slice has exact behavior and owning-symbol anchors"
    )
    breakdown = {
        purpose: sum(
            int(row.get("estimated_tokens", 0))
            for row in slices
            if row.get("purpose") == purpose
        )
        for purpose in ("implementation", "inspection", "proof", "configuration")
    }
    repository_avoided = max(0, repository["approx_tokens"] - used_tokens)
    return {
        "mode": "graph_slice_forecast" if forecast_available else "file_body_upper_bound",
        "evidence": "Merged Navigator-selected line ranges compared with the complete bodies of the same scoped files; actual model/API usage remains telemetry-owned.",
        "used_tokens": used_tokens,
        "planned_working_set_tokens": planned_working_set,
        "scoped_file_ceiling_tokens": scoped_file_ceiling,
        "forecast_confidence": confidence,
        "forecast_confidence_reason": confidence_reason,
        "forecast_available": forecast_available,
        "context_slices": slices,
        "purpose_breakdown": breakdown,
        "avoided_tokens": avoided_tokens,
        "baseline_tokens": baseline,
        "estimated_saved_tokens": avoided_tokens,
        "estimated_reduction_percent": round((avoided_tokens / baseline) * 100, 2) if comparison_available and baseline else None,
        "comparison_state": "scoped-file-slice-estimate" if comparison_available else "not-calculable",
        "comparison_reason": (
            "Compared the planned working set with complete bodies of the same scoped files."
            if comparison_available
            else "A low-confidence or unreadable scoped path prevents a reliable focused estimate."
        ),
        "used_file_count": len(used_files),
        "largest_used_file": largest,
        "used_files": used_files,
        "avoided_files": avoided_files,
        "explicit_avoided_tokens": explicit_avoided_tokens,
        "repository_file_count": repository["file_count"],
        "repository_bytes": repository["bytes"],
        "repository_ceiling_tokens": repository["approx_tokens"],
        "repository_context_avoided_tokens": repository_avoided,
        "repository_reduction_percent": round((repository_avoided / repository["approx_tokens"]) * 100, 2) if repository["approx_tokens"] else None,
        "saving_techniques": saving_techniques(
            plan, repository["file_count"], len(used_files)
        ),
        "repository_boundary": "Relevant source, test, manifest, and configuration files; dependency, VCS, generated, build, coverage, TailTrail state, and known vendor directories are excluded.",
    }


def setup_posture(root: Path, command_prefix: str, source_root: Path) -> dict[str, Any]:
    installed = (root / ".tailtrail-install.json").is_file() or bool(list(root.glob("*/.tailtrail-install.json")))
    packaged = (source_root / "package-integrity.json").is_file()
    return {"source_checkout": not packaged and (source_root / ".codex-plugin").exists(), "installed_package": packaged, "installed_pack_detected": installed, "recommended_check": f"{command_prefix} doctor", "recommended_update_check": f"{command_prefix} update --root {json.dumps(root.as_posix())} --dry-run" if installed else f"{command_prefix} install local --inspect", "note": "Run update checks as dry-run first. Preserve local edits unless the user approves backup-overwrite."}


def review_posture(plan: dict[str, Any], command_prefix: str) -> dict[str, Any]:
    review_plan = plan.get("review_plan") if isinstance(plan.get("review_plan"), dict) else {}
    names = {item.get("name") for item in plan.get("selected_features", []) if isinstance(item, dict)}
    return {"selected": bool({"Review Lens", "Navigator-Led Review", "QA / CI-Sonar Lens", "Security Review"} & names), "scope": str(review_plan.get("default") or "uncommitted changes"), "command": f"{command_prefix} review", "prompt": "After implementation and focused validation, run TailTrail review on the changed scope. Show severity, file, function, line, impact, fix, validation, confidence, and safe-fix status. Do not apply fixes without approval.", "rule": "Review checks code health and requirement fulfillment against the approved plan or user request."}


def harness_posture(root: Path, command_prefix: str) -> dict[str, Any]:
    shared_path = root / "tailtrail-meta" / "harness-summary.jsonl"
    return {"command": f"{command_prefix} harness quick --root {json.dumps(root.as_posix())}", "confidence_command": f"{command_prefix} harness confidence --root {json.dumps(root.as_posix())}", "shared_dry_run_command": f"{command_prefix} harness shared-summary --root {json.dumps(root.as_posix())} --dry-run", "shared_status_command": f"{command_prefix} harness shared-status --root {json.dumps(root.as_posix())}", "shared_metadata_exists": shared_path.is_file(), "rule": "Meta-Harness is post-task advisory. It reviews TailTrail behavior and can dry-run sanitized shared metadata; it does not upload, commit, or change rules automatically."}


def bootstrap_posture(plan: dict[str, Any], command_prefix: str) -> dict[str, Any]:
    snapshot = plan.get("bootstrap_snapshot") if isinstance(plan.get("bootstrap_snapshot"), dict) else None
    if not snapshot:
        return {"selected": False, "status": "skipped", "command": f"{command_prefix} bootstrap status --root .", "rule": "Bootstrap Snapshot is skipped for tiny or low-signal prompts."}
    return {"selected": True, "status": snapshot.get("status", "unknown"), "command": snapshot.get("command") or f"{command_prefix} bootstrap status --root .", "rule": "Bootstrap Snapshot captures safe repo/runtime facts before broad Navigator planning; it does not read source bodies or execute project code."}


def evaluation_posture(goal: str, plan: dict[str, Any], command_prefix: str, trigger_words: set[str]) -> dict[str, Any]:
    lowered_goal = goal.lower()
    task_types = {str(item).lower() for item in plan.get("task_types", [])}
    triggered_terms = sorted(word for word in trigger_words if word in lowered_goal)
    selected = bool(triggered_terms) or (bool({"review", "qa", "ci", "security"} & task_types) and any(word in lowered_goal for word in {"proof", "metrics", "evidence", "report"}))
    scenario = "dependency-decision" if "dependency" in lowered_goal else "review-only" if "review" in lowered_goal else "ci-failure" if "ci" in lowered_goal or "sonar" in lowered_goal else "security-triage" if "security" in lowered_goal or "vulnerability" in lowered_goal else "validation-bug"
    return {"selected": selected, "reason": "triggered by " + ", ".join(triggered_terms) if triggered_terms else "not selected for this task", "scenario": scenario, "list_command": f"{command_prefix} eval scenario list", "run_command": f"{command_prefix} eval scenario run --scenario {scenario}", "report_command": f"{command_prefix} eval scenario report --scenario {scenario}", "write_report_command": f"{command_prefix} eval scenario report --scenario {scenario} --write-result --approved", "normalize_command": f"{command_prefix} eval normalize --source benchmark --input benchmarks/evaluation/results/{scenario}-scenario-report.json --dry-run", "rule": "Evaluation Harness reads committed fixtures and compact evidence only. It does not run live agents, tests, CI, scanners, package managers, model/API calls, or hidden telemetry."}
