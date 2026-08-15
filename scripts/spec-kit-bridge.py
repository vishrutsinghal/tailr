#!/usr/bin/env python3
"""Expose an imported Spec Kit feature to Navigator without taking source ownership."""
from __future__ import annotations

import argparse
import importlib.util
import json
import re
from pathlib import Path
from typing import Any


ROOT = Path(__file__).resolve().parents[1]
FEATURE_IN_GOAL = re.compile(r"(?:intent\s+bridge|spec[ -]?kit)\s+feature\s+([A-Za-z0-9][A-Za-z0-9._-]*)", re.IGNORECASE)


def detector() -> Any:
    spec = importlib.util.spec_from_file_location("tailtrail_spec_kit_detect_for_bridge", ROOT / "scripts" / "spec-kit-detect.py")
    assert spec and spec.loader
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


DETECT = detector()


def feature_from_goal(goal: str) -> str | None:
    match = FEATURE_IN_GOAL.search(goal)
    return match.group(1) if match else None


def latest_source(directory: Path) -> tuple[int, Path]:
    choices: list[tuple[int, Path]] = []
    for path in directory.glob("source-v*.json"):
        match = re.fullmatch(r"source-v(\d+)\.json", path.name)
        if match:
            choices.append((int(match.group(1)), path))
    if not choices:
        raise ValueError("no imported Spec Kit snapshot exists; run `tailtrail spec-kit import` explicitly first")
    return max(choices)


def load(root: Path, feature: str) -> dict[str, Any]:
    root = root.resolve()
    directory = root / ".tailtrail" / "spec-kit" / "sources" / feature
    version, source_path = latest_source(directory)
    source = json.loads(source_path.read_text(encoding="utf-8"))
    imported = json.loads((directory / f"import-v{version}.json").read_text(encoding="utf-8"))
    current = DETECT.detect(root, feature)
    if current["state"] != "compatible":
        raise ValueError("Spec Kit source is no longer compatible: " + "; ".join(current["issues"] or [current["state"]]))
    if current.get("source_revision") != source.get("source_revision"):
        raise ValueError("Spec Kit source changed after import; import the new version and create an amendment review before planning")
    requirements = imported.get("requirements", [])
    if not isinstance(requirements, list) or not requirements:
        raise ValueError("imported Spec Kit snapshot has no requirements")
    return {
        "type": "tailtrail-spec-kit-navigator-source",
        "schema_version": "1",
        "feature_id": feature,
        "source_uid": source["source_uid"],
        "source_revision": source["source_revision"],
        "snapshot_version": version,
        "snapshot": source_path.relative_to(root).as_posix(),
        "import": (directory / f"import-v{version}.json").relative_to(root).as_posix(),
        "requirements": requirements,
        "stories": json.loads((directory / f"stories-v{version}.json").read_text(encoding="utf-8")).get("stories", []),
        "tasks": json.loads((directory / f"tasks-v{version}.json").read_text(encoding="utf-8")).get("tasks", []),
        "boundary": "Spec Kit owns requirement wording and source artifacts. TailTrail adds code-impact, evidence, drift, recovery, and closure controls only.",
    }


def requirement_matrix(bridge: dict[str, Any], likely_paths: list[str]) -> list[dict[str, Any]]:
    rows: list[dict[str, Any]] = []
    for source in bridge["requirements"]:
        rows.append({
            "display_id": source["external_id"],
            "kind": "change",
            "statement": source["statement"],
            "acceptance_criteria": ["Prove the imported Spec Kit requirement through the approved local evidence."],
            "preserve_rules": ["Do not alter Spec Kit source artifacts or behavior outside the approved imported requirement."],
            "likely_paths": likely_paths,
            "evidence_plan": ["Link focused computational evidence to this imported requirement."],
            "validation_contract": {"state": "required", "tiers": ["unit"]},
            "architecture_contract": {"required_paths": [], "protected_paths": [], "forbidden_imports": []},
            "behavior_contract": {"scenarios": []},
            "source_reference": {"source_uid": bridge["source_uid"], "source_revision": bridge["source_revision"], "path": source["source_path"], "locator": source["source_locator"], "external_id": source["external_id"]},
        })
    return rows


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("status", nargs="?", default="status", choices=("status",))
    parser.add_argument("--root", type=Path, default=Path.cwd())
    parser.add_argument("--feature", required=True)
    args = parser.parse_args()
    try:
        print(json.dumps(load(args.root, args.feature), indent=2, sort_keys=True))
    except (OSError, ValueError, json.JSONDecodeError) as error:
        print(f"Spec Kit Navigator bridge error: {error}")
        return 2
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
