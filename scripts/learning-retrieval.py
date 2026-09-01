#!/usr/bin/env python3
"""Project-framed Learning V3 retrieval and contradiction gate for Navigator."""

from __future__ import annotations

import argparse
import fnmatch
import importlib.util
import json
import sys
from datetime import datetime, timezone
from pathlib import Path
from typing import Any


ROOT = Path(__file__).resolve().parents[1]
REFRESH_ACTIONS = Path(".tailtrail/learning-refresh-actions.json")
MAX_MATCHES = 3
THRESHOLDS = {"lite": 60, "standard": 50, "full": 45}
BLOCKING_REFRESH_ACTIONS = {"mark-stale", "suppress", "archive", "delete"}


def load_v3():
    spec = importlib.util.spec_from_file_location("tailtrail_retrieval_learning_v3", ROOT / "scripts" / "learning-v3.py")
    if spec is None or spec.loader is None:
        raise RuntimeError("Unable to load Learning V3")
    module = importlib.util.module_from_spec(spec)
    sys.modules[spec.name] = module
    spec.loader.exec_module(module)
    return module


V3 = load_v3()


def load_receipts():
    spec = importlib.util.spec_from_file_location("tailtrail_retrieval_learning_receipts", ROOT / "scripts" / "learning-use-receipt.py")
    if spec is None or spec.loader is None:
        raise RuntimeError("Unable to load Learning use receipts")
    module = importlib.util.module_from_spec(spec)
    sys.modules[spec.name] = module
    spec.loader.exec_module(module)
    return module


RECEIPTS = load_receipts()


def load_governance():
    spec = importlib.util.spec_from_file_location("tailtrail_retrieval_learning_governance", ROOT / "scripts" / "learning-governance.py")
    if spec is None or spec.loader is None:
        raise RuntimeError("Unable to load Learning governance")
    module = importlib.util.module_from_spec(spec)
    sys.modules[spec.name] = module
    spec.loader.exec_module(module)
    return module


GOVERNANCE = load_governance()


def load_calibration():
    spec = importlib.util.spec_from_file_location("tailtrail_retrieval_learning_calibration", ROOT / "scripts" / "learning-calibration.py")
    if spec is None or spec.loader is None:
        raise RuntimeError("Unable to load Learning calibration")
    module = importlib.util.module_from_spec(spec)
    sys.modules[spec.name] = module
    spec.loader.exec_module(module)
    return module


CALIBRATION = load_calibration()


def normalized(values: list[str] | None) -> list[str]:
    return sorted({str(value).strip().lower() for value in (values or []) if str(value).strip()})


def parse_time(value: str | None) -> datetime | None:
    if not value:
        return None
    try:
        parsed = datetime.fromisoformat(value.replace("Z", "+00:00"))
    except ValueError:
        return None
    return parsed if parsed.tzinfo else parsed.replace(tzinfo=timezone.utc)


def path_matches(pattern: str, candidate: str) -> bool:
    pattern_value = Path(pattern).as_posix().lower()
    candidate_value = Path(candidate).as_posix().lower()
    return fnmatch.fnmatch(candidate_value, pattern_value) or fnmatch.fnmatch(candidate_value, f"*/{pattern_value}")


def refresh_actions(root: Path) -> dict[str, str]:
    path = root / REFRESH_ACTIONS
    if not path.is_file():
        return {}
    try:
        value = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError):
        return {"*": "invalid-refresh-ledger"}
    actions = value.get("actions", []) if isinstance(value, dict) else []
    result: dict[str, str] = {}
    for item in actions if isinstance(actions, list) else []:
        if isinstance(item, dict) and item.get("learning_id") and item.get("action"):
            result[str(item["learning_id"])] = str(item["action"])
    return result


def task_frame(
    root: Path,
    *,
    task_types: list[str],
    tags: list[str],
    paths: list[str],
    requirement_ids: list[str] | None = None,
    mode: str = "lite",
) -> dict[str, Any]:
    if mode not in THRESHOLDS:
        raise V3.LearningV3Error(f"unsupported retrieval mode: {mode}")
    frame = {
        "project_frame": {"kind": "repository", "id": V3.project_frame(root)},
        "task_types": normalized(task_types),
        "tags": normalized(tags),
        "paths": normalized([Path(item).as_posix() for item in paths]),
        "requirement_ids": normalized(requirement_ids),
        "mode": mode,
    }
    if not any(frame[field] for field in ("task_types", "tags", "paths", "requirement_ids")):
        raise V3.LearningV3Error("Learning retrieval requires an established task frame")
    return frame


def exclusion_reasons(record: dict[str, Any], frame: dict[str, Any]) -> list[str]:
    reasons: list[str] = []
    task_types, tags = set(frame["task_types"]), set(frame["tags"])
    requirements, paths = set(frame["requirement_ids"]), frame["paths"]
    for exclusion in record["applicability"]["exclusions"]:
        value = exclusion.lower()
        if value.startswith("learning:"):
            continue
        if value.startswith("task:") and value[5:] in task_types:
            reasons.append(f"task exclusion matched `{exclusion}`")
        elif value.startswith("tag:") and value[4:] in tags:
            reasons.append(f"tag exclusion matched `{exclusion}`")
        elif value.startswith("requirement:") and value[12:] in requirements:
            reasons.append(f"requirement exclusion matched `{exclusion}`")
        elif value.startswith("path:") and any(path_matches(value[5:], path) for path in paths):
            reasons.append(f"path exclusion matched `{exclusion}`")
        elif value in task_types | tags | requirements:
            reasons.append(f"applicability exclusion matched `{exclusion}`")
    return reasons


def applicability(
    record: dict[str, Any],
    frame: dict[str, Any],
    observed_utility: int = 0,
    confidence_score: int | None = None,
) -> tuple[int, list[str]]:
    scope = record["applicability"]
    task_hits = set(normalized(scope["task_types"])) & set(frame["task_types"])
    tag_hits = set(normalized(scope["tags"])) & set(frame["tags"])
    requirement_hits = set(normalized(scope["requirement_ids"])) & set(frame["requirement_ids"])
    path_hits = sorted({path for pattern in scope["path_patterns"] for path in frame["paths"] if path_matches(pattern, path)})
    score, reasons = 0, []
    if task_hits:
        score += 35
        reasons.append("task type: " + ", ".join(sorted(task_hits)))
    if tag_hits:
        score += min(25, 10 * len(tag_hits))
        reasons.append("tags: " + ", ".join(sorted(tag_hits)))
    if path_hits:
        score += 45
        reasons.append("paths: " + ", ".join(path_hits[:3]))
    if requirement_hits:
        score += 45
        reasons.append("requirements: " + ", ".join(sorted(requirement_hits)))
    if not reasons:
        return 0, []
    confidence = int(record["utility"]["confidence_score"] if confidence_score is None else confidence_score)
    score += int(confidence * 0.20)
    if record["utility"]["curated"]:
        score += 5
        reasons.append("curated learning")
    score += observed_utility
    if observed_utility:
        reasons.append(f"observed closure association utility: {observed_utility:+d}")
    return min(100, score), reasons


def provenance_reasons(root: Path, record: dict[str, Any], by_record_id: dict[str, dict[str, Any]]) -> list[str]:
    ref = record["provenance"]["source_ref"]
    expected = record["provenance"]["source_fingerprint"]
    if ref.startswith("learning-v3:"):
        source = by_record_id.get(ref.split(":", 1)[1])
        if not source or expected != "sha256:" + source["chain"]["digest"]:
            return ["V3 provenance predecessor is missing or changed"]
    elif "#line=" in ref:
        relative, line_text = ref.rsplit("#line=", 1)
        try:
            line_number = int(line_text)
            line = (root / relative).read_text(encoding="utf-8").splitlines()[line_number - 1]
            source_value = json.loads(line)
        except (OSError, ValueError, IndexError, json.JSONDecodeError):
            return ["referenced source evidence is missing or unreadable"]
        if expected != "sha256:" + V3.sha256(source_value):
            return ["referenced source evidence fingerprint changed"]
    return []


def freshness_reasons(
    root: Path,
    record: dict[str, Any],
    actions: dict[str, str],
    by_record_id: dict[str, dict[str, Any]],
) -> tuple[list[str], list[dict[str, str]]]:
    blocked: list[str] = []
    checks: list[dict[str, str]] = []
    if record["freshness"]["status"] != "current":
        blocked.append(f"lifecycle status is {record['freshness']['status']}")
    deadline = parse_time(record["freshness"].get("revalidate_after"))
    if deadline and deadline <= datetime.now(timezone.utc):
        blocked.append("revalidation deadline has elapsed")
    action = actions.get(record["learning_id"])
    if action in BLOCKING_REFRESH_ACTIONS:
        blocked.append(f"approved refresh action is `{action}`")
    if actions.get("*"):
        blocked.append("refresh-action ledger is invalid")
    blocked.extend(provenance_reasons(root, record, by_record_id))
    missing_explicit = [
        pattern for pattern in record["applicability"]["path_patterns"]
        if not any(char in pattern for char in "*?[") and not (root / pattern).is_file()
    ]
    if missing_explicit and "source-change" in record["freshness"]["invalidators"]:
        blocked.append("source-change invalidator triggered")
    saved_snapshot = record["freshness"].get("invalidator_snapshot")
    if isinstance(saved_snapshot, dict):
        current_snapshot = V3.invalidator_snapshot(
            root,
            path_patterns=record["applicability"]["path_patterns"],
            source_ref=record["provenance"]["source_ref"],
        )
        for invalidator in record["freshness"]["invalidators"]:
            triggered = saved_snapshot.get(invalidator) != current_snapshot.get(invalidator)
            checks.append({
                "invalidator": invalidator,
                "state": "triggered" if triggered else "not-triggered",
                "evidence": f"{invalidator} content fingerprint changed" if triggered else "content fingerprint matches captured snapshot",
            })
            if triggered:
                blocked.append(f"{invalidator} invalidator triggered")
        return sorted(set(blocked)), checks
    captured_at = parse_time(record["freshness"].get("captured_at"))
    captured_timestamp = captured_at.timestamp() if captured_at else None
    pattern_files: list[Path] = []
    missing_explicit_path = False
    for pattern in record["applicability"]["path_patterns"]:
        matches = [path for path in root.glob(pattern) if path.is_file()]
        pattern_files.extend(matches)
        if not matches and not any(char in pattern for char in "*?["):
            missing_explicit_path = True

    def modified_after(paths: list[Path]) -> list[str]:
        if captured_timestamp is None:
            return ["capture-time-unavailable"]
        changed: list[str] = []
        for path in paths:
            try:
                # Learning V3 timestamps intentionally use whole-second precision.
                if path.stat().st_mtime > captured_timestamp + 1.0:
                    changed.append(path.relative_to(root).as_posix())
            except (OSError, ValueError):
                changed.append(path.as_posix())
        return sorted(set(changed))

    for invalidator in record["freshness"]["invalidators"]:
        state = "not-triggered"
        evidence = "no matching invalidator evidence changed after capture"
        if invalidator == "source-change":
            changed = modified_after(pattern_files)
            if missing_explicit_path or changed:
                state = "triggered"
                evidence = "explicit source path missing" if missing_explicit_path else "source changed after capture: " + ", ".join(changed[:3])
                blocked.append("source-change invalidator triggered")
        elif invalidator == "policy-change":
            changed = modified_after([path for path in (root / "tailtrail-policy.md", root / "GUARDRAILS.md") if path.is_file()])
            if changed:
                state, evidence = "triggered", "policy changed after capture: " + ", ".join(changed)
                blocked.append("policy-change invalidator triggered")
        elif invalidator == "ownership-change":
            changed = modified_after([path for path in (root / ".github" / "CODEOWNERS", root / "CODEOWNERS") if path.is_file()])
            if changed:
                state, evidence = "triggered", "ownership changed after capture: " + ", ".join(changed)
                blocked.append("ownership-change invalidator triggered")
        elif invalidator == "validation-change":
            validation_files = [path for path in pattern_files if any(part.lower() in {"test", "tests", "__tests__"} for part in path.parts)]
            changed = modified_after(validation_files)
            if changed:
                state, evidence = "triggered", "validation changed after capture: " + ", ".join(changed[:3])
                blocked.append("validation-change invalidator triggered")
        elif invalidator == "graph-change":
            changed = modified_after([path for path in (root / ".tailtrail" / "code-graph-cache.json", root / ".tailtrail" / "graph-learning-index.json") if path.is_file()])
            if changed:
                state, evidence = "triggered", "graph evidence changed after capture: " + ", ".join(changed)
                blocked.append("graph-change invalidator triggered")
        elif invalidator == "symbol-change":
            changed = modified_after(pattern_files)
            if missing_explicit_path or changed:
                state = "triggered"
                evidence = "scoped symbol path missing" if missing_explicit_path else "symbol-scoped source changed after capture: " + ", ".join(changed[:3])
                blocked.append("symbol-change invalidator triggered")
        elif invalidator == "manifest-change":
            names = ("pyproject.toml", "setup.py", "setup.cfg", "package.json", "package-lock.json", "pnpm-lock.yaml", "yarn.lock", "Cargo.toml", "Cargo.lock", "go.mod", "go.sum", "requirements.txt", "Pipfile", "Pipfile.lock", "poetry.lock", "Gemfile", "Gemfile.lock")
            changed = modified_after([root / name for name in names if (root / name).is_file()])
            if changed:
                state, evidence = "triggered", "manifest changed after capture: " + ", ".join(changed[:3])
                blocked.append("manifest-change invalidator triggered")
        else:
            state, evidence = "unresolved", "the invalidator is not recognized by PM-L2"
            blocked.append(f"unresolved invalidator `{invalidator}`")
        checks.append({"invalidator": invalidator, "state": state, "evidence": evidence})
    return sorted(set(blocked)), checks


def explicit_conflicts(records: list[dict[str, Any]]) -> dict[str, set[str]]:
    current_ids = {record["learning_id"] for record in records if record["freshness"]["status"] == "current"}
    result = {learning_id: set() for learning_id in current_ids}
    for record in records:
        if record["learning_id"] not in current_ids:
            continue
        for exclusion in record["applicability"]["exclusions"]:
            if exclusion.lower().startswith("learning:"):
                target = exclusion.split(":", 1)[1]
                if target in current_ids and target != record["learning_id"]:
                    result[record["learning_id"]].add(target)
                    result[target].add(record["learning_id"])
    return result


def build_proposal(
    root: Path,
    *,
    task_types: list[str],
    tags: list[str],
    paths: list[str],
    requirement_ids: list[str] | None = None,
    mode: str = "lite",
) -> dict[str, Any]:
    frame = task_frame(root, task_types=task_types, tags=tags, paths=paths, requirement_ids=requirement_ids, mode=mode)
    records = list(V3.latest_records(V3.read_records(root)).values())
    by_record_id = {record["record_id"]: record for record in V3.read_records(root)}
    actions = refresh_actions(root)
    conflict_map = explicit_conflicts(records)
    governance_blocks = GOVERNANCE.blocking_reasons(root)
    calibration_adjustments, calibration_blocks = CALIBRATION.load_adjustments(root)
    utility = RECEIPTS.utility_adjustments(root)
    eligible: list[dict[str, Any]] = []
    blocked: list[dict[str, Any]] = []
    threshold = THRESHOLDS[mode]
    for record in records:
        observed = utility.get(record["learning_id"], {"total_delta": 0, "attribution_count": 0})
        observed_delta = int(observed["total_delta"])
        raw_confidence = int(record["utility"]["confidence_score"])
        calibration_delta = int(calibration_adjustments.get(record["learning_class"], 0))
        effective_confidence = max(0, min(100, raw_confidence + calibration_delta))
        score, explanations = applicability(record, frame, observed_delta, effective_confidence)
        if not explanations:
            continue
        if calibration_delta:
            explanations.append(f"class calibration adjustment: {calibration_delta:+d}")
        reasons, checks = freshness_reasons(root, record, actions, by_record_id)
        reasons.extend(exclusion_reasons(record, frame))
        conflicts = sorted(conflict_map.get(record["learning_id"], set()))
        if conflicts:
            reasons.append("explicit contradiction with " + ", ".join(conflicts))
        reasons.extend(governance_blocks.get("*", []))
        reasons.extend(governance_blocks.get(record["learning_id"], []))
        reasons.extend(calibration_blocks)
        if score < threshold:
            reasons.append(f"applicability score {score} is below {mode} threshold {threshold}")
        if record["privacy"]["sensitivity"] != "normal":
            reasons.append("non-normal sensitivity is not eligible for Navigator retrieval")
        if reasons:
            blocked.append({
                "learning_id": record["learning_id"],
                "record_id": record["record_id"],
                "reasons": sorted(set(reasons)),
                "invalidator_checks": checks,
            })
            continue
        eligible.append({
            "learning_id": record["learning_id"],
            "record_id": record["record_id"],
            "learning_class": record["learning_class"],
            "applicability_score": score,
            "confidence_score": effective_confidence,
            "observed_utility_delta": observed_delta,
            "attribution_count": int(observed["attribution_count"]),
            "match_explanations": explanations,
            "invalidator_checks": checks,
            "summary": record["content"]["summary"],
            "proposed_advice": record["content"]["advice"],
        })
    eligible.sort(key=lambda item: (-item["applicability_score"], -item["confidence_score"], item["learning_id"]))
    selected = eligible[:MAX_MATCHES]
    state = "proposed" if selected else ("blocked" if blocked else "quiet")
    return {
        "schema_version": "1",
        "type": "tailtrail-learning-use-proposal",
        "state": state,
        "task_frame": frame,
        "threshold": threshold,
        "result_cap": MAX_MATCHES,
        "matches": selected,
        "blocked": sorted(blocked, key=lambda item: item["learning_id"]),
        "approval": {
            "required": bool(selected),
            "default": "do-not-use",
            "choices": ["use selected learnings", "ignore all learnings", "edit selected learning IDs"],
        },
        "boundary": "Proposal only: no learning advice is injected into requirements, plans, implementation instructions, source, or task state until the user explicitly chooses it. Current source, tests, policy, CI, scanner, guardrail, and user evidence always wins.",
    }


def render(value: dict[str, Any]) -> str:
    lines = ["# TailTrail Learning Use Proposal", "", f"- State: `{value['state']}`", f"- Threshold: `{value['threshold']}`", f"- Result cap: `{value['result_cap']}`"]
    if value["state"] == "quiet":
        lines.append("- No high-value project-framed learning matched; Lite remains quiet.")
    for item in value["matches"]:
        lines.extend(["", f"## {item['learning_id']}", "", f"- Summary: {item['summary']}", f"- Applicability: `{item['applicability_score']}`", f"- Confidence: `{item['confidence_score']}`", "- Match explanations:"])
        lines.extend(f"  - {reason}" for reason in item["match_explanations"])
        lines.append(f"- Proposed advice (not instruction): {item['proposed_advice']}")
    if value["blocked"]:
        lines.extend(["", "## Blocked", ""])
        for item in value["blocked"]:
            lines.append(f"- `{item['learning_id']}`: {'; '.join(item['reasons'])}")
    lines.extend(["", "## Decision", "", f"- Default: `{value['approval']['default']}`", f"- Choices: {', '.join(value['approval']['choices'])}", f"- Boundary: {value['boundary']}"])
    return "\n".join(lines) + "\n"


def split_csv(value: str | None) -> list[str]:
    return [item.strip() for item in (value or "").split(",") if item.strip()]


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--root", type=Path, default=Path.cwd())
    parser.add_argument("--task-types", required=True)
    parser.add_argument("--tags")
    parser.add_argument("--path", action="append", default=[])
    parser.add_argument("--requirement-ids")
    parser.add_argument("--mode", choices=tuple(THRESHOLDS), default="lite")
    parser.add_argument("--format", choices=("json", "markdown"), default="markdown")
    args = parser.parse_args()
    try:
        value = build_proposal(
            args.root.resolve(), task_types=split_csv(args.task_types), tags=split_csv(args.tags), paths=args.path,
            requirement_ids=split_csv(args.requirement_ids), mode=args.mode,
        )
    except (OSError, ValueError, json.JSONDecodeError, V3.LearningV3Error) as error:
        print(f"Learning retrieval error: {error}")
        return 2
    print(json.dumps(value, indent=2, sort_keys=True) if args.format == "json" else render(value), end="\n" if args.format == "json" else "")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
