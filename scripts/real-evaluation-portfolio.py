#!/usr/bin/env python3
"""Prepare, grade, unblind, and report the PM-5 real evaluation portfolio."""
from __future__ import annotations

import argparse
import hashlib
import json
import re
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parents[1]
CATALOG = ROOT / "benchmarks/evaluation/real-portfolio/v1.json"
PM5_ROOT = Path(".tailtrail/evaluation/pm5")
RAW_MARKERS = ("prompt", "response", "source", "code", "secret", "credential", "absolute_path", "repository_url")
REVIEWER_REF = re.compile(r"^[A-Za-z0-9_.:-]{1,80}$")


def read_json(path: Path) -> dict[str, Any]:
    value = json.loads(path.read_text(encoding="utf-8"))
    if not isinstance(value, dict):
        raise ValueError(f"{path.name} must contain one JSON object")
    return value


def fingerprint(value: Any) -> str:
    payload = json.dumps(value, sort_keys=True, separators=(",", ":"))
    return hashlib.sha256(payload.encode("utf-8")).hexdigest()


def catalog_errors(value: dict[str, Any]) -> list[str]:
    issues: list[str] = []
    tasks = value.get("tasks")
    if value.get("schema_version") != "1" or value.get("type") != "tailtrail-real-evaluation-portfolio":
        issues.append("portfolio contract is incompatible")
    if value.get("evidence_label") != "evaluation-protocol":
        issues.append("catalog must be labeled `evaluation-protocol`")
    if not isinstance(value.get("minimum_repetitions"), int) or value["minimum_repetitions"] < 2:
        issues.append("minimum_repetitions must be at least 2")
    if not isinstance(tasks, list) or len(tasks) < 15:
        return [*issues, "portfolio needs at least 15 tasks"]
    identifiers = [str(row.get("task_id", "")) for row in tasks if isinstance(row, dict)]
    if len(identifiers) != len(tasks) or "" in identifiers or len(identifiers) != len(set(identifiers)):
        issues.append("task IDs must be non-empty and unique")
    repositories = {row.get("repository_fixture") for row in tasks if isinstance(row, dict)}
    if None in repositories or len(repositories) < 3:
        issues.append("portfolio needs at least three named repository fixtures")
    for row in tasks:
        requirements = row.get("requirements") if isinstance(row, dict) else None
        if not isinstance(requirements, list) or len(requirements) < 2:
            issues.append(f"{row.get('task_id', 'task') if isinstance(row, dict) else 'task'}: needs at least two requirements")
    return issues


def safe_path(root: Path, supplied: Path) -> Path:
    base = root.resolve()
    candidate = (base / supplied).resolve() if not supplied.is_absolute() else supplied.resolve()
    try:
        candidate.relative_to(base)
    except ValueError as error:
        raise ValueError("artifact path must remain inside the selected project root") from error
    return candidate


def contains_raw_field(value: Any) -> bool:
    if isinstance(value, dict):
        return any(
            any(marker in str(key).lower() for marker in RAW_MARKERS) or contains_raw_field(item)
            for key, item in value.items()
        )
    if isinstance(value, list):
        return any(contains_raw_field(item) for item in value)
    return False


def write_immutable(path: Path, value: dict[str, Any]) -> None:
    rendered = json.dumps(value, indent=2, sort_keys=True) + "\n"
    if path.exists():
        if path.read_text(encoding="utf-8") != rendered:
            raise ValueError(f"refusing to overwrite immutable artifact {path.name}")
        return
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(rendered, encoding="utf-8")


def validate_catalog() -> dict[str, Any]:
    catalog = read_json(CATALOG)
    issues = catalog_errors(catalog)
    repositories = {row.get("repository_fixture") for row in catalog.get("tasks", []) if isinstance(row, dict)}
    return {
        "type": "tailtrail-real-evaluation-validation",
        "status": "passed" if not issues else "failed",
        "task_count": len(catalog.get("tasks", [])),
        "repository_fixture_count": len(repositories),
        "issues": issues,
        "evidence_label": "evaluation-protocol",
    }


def prepare(root: Path, task_id: str, repetition: int, baseline_hash: str, tailtrail_hash: str, approved: bool) -> dict[str, Any]:
    if not approved:
        raise ValueError("prepare requires --approved")
    if repetition < 1:
        raise ValueError("repetition must be at least 1")
    catalog = read_json(CATALOG)
    if problems := catalog_errors(catalog):
        raise ValueError("; ".join(problems))
    task = next((row for row in catalog["tasks"] if row["task_id"] == task_id), None)
    if task is None:
        raise ValueError("unknown portfolio task")
    for name, value in (("baseline", baseline_hash), ("tailtrail", tailtrail_hash)):
        if len(value) != 64 or any(character not in "0123456789abcdef" for character in value.lower()):
            raise ValueError(f"{name} hash must be one SHA-256 hex digest")
    pair_id = f"pair-{fingerprint([catalog['portfolio_id'], task_id, repetition, baseline_hash, tailtrail_hash])[:16]}"
    swapped = int(fingerprint(pair_id)[0], 16) % 2 == 1
    arms = {"A": tailtrail_hash if swapped else baseline_hash, "B": baseline_hash if swapped else tailtrail_hash}
    mapping = {"A": "tailtrail" if swapped else "baseline", "B": "baseline" if swapped else "tailtrail"}
    assignment = {"schema_version": "1", "type": "tailtrail-evaluation-assignment", "pair_id": pair_id, "mapping": mapping,
                  "boundary": "Keep this assignment from the blinded grader until grading is complete."}
    packet = {
        "schema_version": "1", "type": "tailtrail-blind-evaluation-packet", "pair_id": pair_id,
        "portfolio_id": catalog["portfolio_id"], "task_id": task_id, "task_class": task["task_class"],
        "repetition": repetition, "requirements": task["requirements"], "arms": arms,
        "required_metrics": catalog["required_metrics"], "blinded": True,
        "boundary": "Artifact hashes and sanitized metrics only; variant identity is withheld from the grader.",
    }
    base = root.resolve() / PM5_ROOT
    packet_path = base / "packets" / pair_id / "packet.json"
    assignment_path = base / "assignments" / f"{pair_id}.json"
    write_immutable(packet_path, packet)
    write_immutable(assignment_path, assignment)
    return {**packet, "packet_ref": packet_path.relative_to(root.resolve()).as_posix(),
            "assignment_ref": assignment_path.relative_to(root.resolve()).as_posix()}


def metrics(value: dict[str, Any], required: list[str], arm: str) -> dict[str, Any]:
    row = value.get(arm)
    if not isinstance(row, dict) or set(row) != set(required):
        raise ValueError(f"arm {arm} must contain exactly the required metrics")
    for key, item in row.items():
        if key == "provider_total_tokens" and item is None:
            continue
        if not isinstance(item, int) or isinstance(item, bool) or item < 0:
            raise ValueError(f"arm {arm} metric {key} must be a non-negative integer or allowed null token value")
    if row["requirements_total"] < 1 or row["requirements_completed"] > row["requirements_total"]:
        raise ValueError(f"arm {arm} has invalid requirement totals")
    return row


def grade(root: Path, packet_ref: Path, input_ref: Path, approved: bool) -> dict[str, Any]:
    if not approved:
        raise ValueError("grade requires --approved")
    packet_path, input_path = safe_path(root, packet_ref), safe_path(root, input_ref)
    packet, supplied = read_json(packet_path), read_json(input_path)
    if packet.get("type") != "tailtrail-blind-evaluation-packet" or packet.get("blinded") is not True:
        raise ValueError("packet is not a blinded PM-5 packet")
    if contains_raw_field(supplied):
        raise ValueError("grade input contains a prohibited raw-data field")
    reviewer_ref = str(supplied.get("reviewer_ref", "anonymous"))
    if not REVIEWER_REF.fullmatch(reviewer_ref):
        raise ValueError("reviewer_ref must be a short sanitized identifier")
    arms = {arm: metrics(supplied, packet["required_metrics"], arm) for arm in ("A", "B")}
    core = {
        "schema_version": "1", "type": "tailtrail-blind-evaluation-grade", "pair_id": packet["pair_id"],
        "task_id": packet["task_id"], "repetition": packet["repetition"], "arms": arms,
        "reviewer_ref": reviewer_ref, "blinded": True,
        "boundary": "Sanitized observations only; no variant identity, prompt, source, response, or token estimate is inferred.",
    }
    value = {**core, "grade_fingerprint": fingerprint(core)}
    path = packet_path.parent / "grade.json"
    write_immutable(path, value)
    return {**value, "artifact": path.relative_to(root.resolve()).as_posix()}


def classify_outcome(baseline: dict[str, Any], tailtrail: dict[str, Any]) -> str:
    if tailtrail["requirements_completed"] > baseline["requirements_completed"] and tailtrail["false_interventions"] <= baseline["false_interventions"]:
        return "positive"
    if tailtrail["requirements_completed"] < baseline["requirements_completed"] or tailtrail["false_interventions"] > baseline["false_interventions"]:
        return "negative"
    return "neutral"


def unblind(root: Path, grade_ref: Path, assignment_ref: Path, approved: bool) -> dict[str, Any]:
    if not approved:
        raise ValueError("unblind requires --approved")
    grade_value = read_json(safe_path(root, grade_ref))
    assignment = read_json(safe_path(root, assignment_ref))
    if grade_value.get("type") != "tailtrail-blind-evaluation-grade" or assignment.get("type") != "tailtrail-evaluation-assignment":
        raise ValueError("grade or assignment is not a PM-5 artifact")
    if grade_value.get("pair_id") != assignment.get("pair_id"):
        raise ValueError("grade and assignment pair IDs differ")
    mapping = assignment.get("mapping", {})
    if set(mapping) != {"A", "B"} or set(mapping.values()) != {"baseline", "tailtrail"}:
        raise ValueError("assignment mapping is invalid")
    variants = {mapping[arm]: value for arm, value in grade_value["arms"].items()}
    core = {
        "schema_version": "1", "type": "tailtrail-unblinded-paired-observation", "pair_id": grade_value["pair_id"],
        "task_id": grade_value["task_id"], "repetition": grade_value["repetition"], "variants": variants,
        "outcome": classify_outcome(variants["baseline"], variants["tailtrail"]),
        "grade_fingerprint": grade_value["grade_fingerprint"],
        "boundary": "One sanitized observation retained regardless of outcome; it is not a general efficacy claim.",
    }
    value = {**core, "observation_fingerprint": fingerprint(core)}
    path = root.resolve() / PM5_ROOT / "observations" / f"{grade_value['pair_id']}.json"
    write_immutable(path, value)
    return {**value, "artifact": path.relative_to(root.resolve()).as_posix()}


def report(root: Path) -> dict[str, Any]:
    catalog, observations = read_json(CATALOG), []
    issues = catalog_errors(catalog)
    for path in sorted((root.resolve() / PM5_ROOT / "observations").glob("*.json")):
        value = read_json(path)
        if value.get("type") == "tailtrail-unblinded-paired-observation":
            observations.append(value)
    by_task = {task["task_id"]: [] for task in catalog.get("tasks", [])}
    seen_pairs: set[str] = set()
    for row in observations:
        pair_id = str(row.get("pair_id", ""))
        if pair_id in seen_pairs:
            issues.append(f"duplicate observation pair: {pair_id}")
        elif row.get("task_id") not in by_task:
            issues.append(f"unknown observed task: {row.get('task_id')}")
        else:
            seen_pairs.add(pair_id)
            by_task[row["task_id"]].append(row)
    minimum = int(catalog.get("minimum_repetitions", 3))
    covered = sum(len(rows) >= minimum for rows in by_task.values())
    outcomes = {name: sum(row.get("outcome") == name for row in observations) for name in ("positive", "neutral", "negative")}
    metric_summary: dict[str, dict[str, float | int | None]] = {}
    for metric_name in catalog.get("required_metrics", []):
        paired = [
            (row["variants"]["baseline"].get(metric_name), row["variants"]["tailtrail"].get(metric_name))
            for row in observations
            if isinstance(row.get("variants"), dict)
        ]
        measured_pairs = [
            (baseline, tailtrail)
            for baseline, tailtrail in paired
            if isinstance(baseline, int) and not isinstance(baseline, bool)
            and isinstance(tailtrail, int) and not isinstance(tailtrail, bool)
        ]
        count = len(measured_pairs)
        baseline_mean = sum(pair[0] for pair in measured_pairs) / count if count else None
        tailtrail_mean = sum(pair[1] for pair in measured_pairs) / count if count else None
        metric_summary[metric_name] = {
            "measured_pair_count": count,
            "baseline_mean": baseline_mean,
            "tailtrail_mean": tailtrail_mean,
            "tailtrail_minus_baseline": tailtrail_mean - baseline_mean if count else None,
        }
    measured = bool(by_task) and covered == len(by_task) and not issues
    return {
        "schema_version": "1", "type": "tailtrail-real-evaluation-report", "portfolio_id": catalog.get("portfolio_id"),
        "status": "measured" if measured else "collecting" if observations else "protocol-ready",
        "task_count": len(by_task), "repository_fixture_count": len({row["repository_fixture"] for row in catalog.get("tasks", [])}),
        "minimum_repetitions": minimum, "required_observation_count": len(by_task) * minimum,
        "tasks_meeting_repetitions": covered, "observation_count": len(observations), "outcomes": outcomes,
        "metric_summary": metric_summary,
        "issues": issues, "claim_status": "scoped-measured-evidence" if measured else "no-performance-claim",
        "boundary": "Claims require every task to meet the repetition threshold. Neutral and negative outcomes are retained.",
    }


def parser() -> argparse.ArgumentParser:
    root = argparse.ArgumentParser(description=__doc__)
    commands = root.add_subparsers(dest="action", required=True)
    for action in ("validate", "report"):
        commands.add_parser(action).add_argument("--root", type=Path, default=Path.cwd())
    command = commands.add_parser("prepare")
    command.add_argument("--root", type=Path, default=Path.cwd()); command.add_argument("--task", required=True)
    command.add_argument("--repetition", type=int, required=True); command.add_argument("--baseline-hash", required=True)
    command.add_argument("--tailtrail-hash", required=True); command.add_argument("--approved", action="store_true")
    command = commands.add_parser("grade")
    command.add_argument("--root", type=Path, default=Path.cwd()); command.add_argument("--packet", type=Path, required=True)
    command.add_argument("--input", type=Path, required=True); command.add_argument("--approved", action="store_true")
    command = commands.add_parser("unblind")
    command.add_argument("--root", type=Path, default=Path.cwd()); command.add_argument("--grade", type=Path, required=True)
    command.add_argument("--assignment", type=Path, required=True); command.add_argument("--approved", action="store_true")
    return root


def main(argv: list[str] | None = None) -> int:
    args = parser().parse_args(argv)
    try:
        if args.action == "validate": value = validate_catalog()
        elif args.action == "report": value = report(args.root)
        elif args.action == "prepare": value = prepare(args.root, args.task, args.repetition, args.baseline_hash, args.tailtrail_hash, args.approved)
        elif args.action == "grade": value = grade(args.root, args.packet, args.input, args.approved)
        else: value = unblind(args.root, args.grade, args.assignment, args.approved)
        print(json.dumps(value, indent=2, sort_keys=True))
        return 0 if not value.get("issues") and value.get("status") != "failed" else 2
    except (OSError, ValueError, json.JSONDecodeError) as error:
        print(f"TailTrail real evaluation error: {error}")
        return 2


if __name__ == "__main__":
    raise SystemExit(main())
