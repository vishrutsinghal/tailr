#!/usr/bin/env python3
"""Report a deterministic paired multi-file delivery evaluation dataset."""
from __future__ import annotations

import argparse
import json
from pathlib import Path
from typing import Any


ROOT = Path(__file__).resolve().parents[1]
DEFAULT_DATASET = ROOT / "benchmarks" / "evaluation" / "delivery-dataset" / "v1.json"
METRICS = ("missed_callers", "missed_tests", "correction_cycles", "scope_drift_paths", "false_interventions", "developer_review_minutes")


def read_dataset(path: Path) -> dict[str, Any]:
    payload = json.loads(path.read_text(encoding="utf-8"))
    if not isinstance(payload, dict):
        raise ValueError("dataset must be a JSON object")
    return payload


def errors(dataset: dict[str, Any]) -> list[str]:
    found: list[str] = []
    tasks = dataset.get("tasks")
    if dataset.get("schema_version") != "1":
        found.append("schema_version must be `1`")
    if dataset.get("type") != "tailtrail-delivery-evaluation-dataset":
        found.append("type must be `tailtrail-delivery-evaluation-dataset`")
    if not isinstance(tasks, list) or not 10 <= len(tasks) <= 20:
        found.append("tasks must contain 10–20 paired multi-file tasks")
        return found
    seen: set[str] = set()
    for index, task in enumerate(tasks, 1):
        if not isinstance(task, dict):
            found.append(f"task {index} must be an object")
            continue
        task_id = task.get("task_id")
        if not isinstance(task_id, str) or not task_id:
            found.append(f"task {index} needs task_id")
        elif task_id in seen:
            found.append(f"duplicate task_id: {task_id}")
        else:
            seen.add(task_id)
        files = task.get("files")
        if not isinstance(files, list) or len(files) < 2 or not all(isinstance(item, str) for item in files):
            found.append(f"{task_id}: files must name at least two paths")
        variants = task.get("variants")
        if not isinstance(variants, dict) or set(variants) != {"baseline", "tailtrail"}:
            found.append(f"{task_id}: variants must contain baseline and tailtrail")
            continue
        for name, variant in variants.items():
            if not isinstance(variant, dict):
                found.append(f"{task_id}/{name}: variant must be an object")
                continue
            requirements = variant.get("requirements")
            if not isinstance(requirements, dict) or not all(isinstance(requirements.get(key), int) for key in ("completed", "total")):
                found.append(f"{task_id}/{name}: requirements need integer completed and total")
            elif requirements["completed"] < 0 or requirements["total"] < 1 or requirements["completed"] > requirements["total"]:
                found.append(f"{task_id}/{name}: invalid requirement count")
            for metric in METRICS:
                if not isinstance(variant.get(metric), int) or variant[metric] < 0:
                    found.append(f"{task_id}/{name}: {metric} must be a non-negative integer")
    return found


def aggregate(tasks: list[dict[str, Any]], variant: str) -> dict[str, Any]:
    completed = sum(task["variants"][variant]["requirements"]["completed"] for task in tasks)
    total = sum(task["variants"][variant]["requirements"]["total"] for task in tasks)
    metrics = {metric: sum(task["variants"][variant][metric] for task in tasks) for metric in METRICS}
    return {"requirements": {"completed": completed, "total": total, "completion_rate": round(completed / total, 4)}, **metrics}


def report(dataset: dict[str, Any]) -> dict[str, Any]:
    problems = errors(dataset)
    if problems:
        raise ValueError("; ".join(problems))
    tasks = dataset["tasks"]
    baseline = aggregate(tasks, "baseline")
    tailtrail = aggregate(tasks, "tailtrail")
    deltas = {"requirement_completion_rate": round(tailtrail["requirements"]["completion_rate"] - baseline["requirements"]["completion_rate"], 4)}
    deltas.update({metric: tailtrail[metric] - baseline[metric] for metric in METRICS})
    return {
        "schema_version": "1",
        "type": "tailtrail-delivery-evaluation-report",
        "dataset_id": dataset.get("dataset_id"),
        "task_count": len(tasks),
        "evidence_label": dataset.get("evidence_label", "local-evidence"),
        "claim_boundaries": dataset.get("claim_boundaries", []),
        "baseline": baseline,
        "tailtrail": tailtrail,
        "delta_tailtrail_minus_baseline": deltas,
        "tasks": [{"task_id": task["task_id"], "title": task["title"], "task_class": task["task_class"], "files": task["files"]} for task in tasks],
    }


def render(payload: dict[str, Any]) -> str:
    baseline, tailtrail, delta = payload["baseline"], payload["tailtrail"], payload["delta_tailtrail_minus_baseline"]
    lines = ["# TailTrail Delivery Evaluation Dataset", "", f"- Dataset: `{payload['dataset_id']}`", f"- Tasks: `{payload['task_count']}`", f"- Evidence label: `{payload['evidence_label']}`", "", "## Paired outcomes", "", "| Metric | Baseline | TailTrail | Delta (TT − baseline) |", "| --- | ---: | ---: | ---: |", f"| Requirement completion | {baseline['requirements']['completed']}/{baseline['requirements']['total']} ({baseline['requirements']['completion_rate']:.1%}) | {tailtrail['requirements']['completed']}/{tailtrail['requirements']['total']} ({tailtrail['requirements']['completion_rate']:.1%}) | {delta['requirement_completion_rate']:+.1%} |"]
    labels = {"missed_callers": "Missed caller cases", "missed_tests": "Missed test cases", "correction_cycles": "Correction cycles", "scope_drift_paths": "Scope-drift paths", "false_interventions": "False interventions", "developer_review_minutes": "Developer review time (minutes)"}
    for metric in METRICS:
        lines.append(f"| {labels[metric]} | {baseline[metric]} | {tailtrail[metric]} | {delta[metric]:+d} |")
    lines.extend(["", "## Dataset tasks", ""])
    for task in payload["tasks"]:
        lines.append(f"- `{task['task_id']}` — {task['title']} ({task['task_class']}): {', '.join(task['files'])}")
    lines.extend(["", "## Claim boundaries", ""])
    for boundary in payload["claim_boundaries"]:
        lines.append(f"- {boundary}")
    return "\n".join(lines) + "\n"


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("action", choices=("list", "report", "validate"))
    parser.add_argument("--dataset", type=Path, default=DEFAULT_DATASET)
    parser.add_argument("--format", choices=("markdown", "json"), default="markdown")
    args = parser.parse_args(argv)
    try:
        dataset = read_dataset(args.dataset)
        problems = errors(dataset)
        if args.action == "validate":
            if problems:
                print("Dataset validation failed:\n- " + "\n- ".join(problems))
                return 1
            print(f"Dataset validation passed: {len(dataset['tasks'])} paired multi-file tasks.")
            return 0
        if problems:
            raise ValueError("; ".join(problems))
        if args.action == "list":
            payload = {"dataset_id": dataset.get("dataset_id"), "tasks": [{"task_id": task["task_id"], "title": task["title"], "files": task["files"]} for task in dataset["tasks"]]}
            print(json.dumps(payload, indent=2) if args.format == "json" else "\n".join(f"- `{item['task_id']}` — {item['title']}" for item in payload["tasks"]))
            return 0
        payload = report(dataset)
        print(json.dumps(payload, indent=2, sort_keys=True) if args.format == "json" else render(payload), end="")
        return 0
    except (OSError, ValueError, json.JSONDecodeError) as error:
        print(f"Delivery dataset error: {error}")
        return 2


if __name__ == "__main__":
    raise SystemExit(main())
