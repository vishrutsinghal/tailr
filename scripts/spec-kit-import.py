#!/usr/bin/env python3
"""Create immutable, normalized TailTrail snapshots from an explicit Spec Kit feature."""
from __future__ import annotations

import argparse
import hashlib
import importlib.util
import json
import os
import re
import tempfile
from pathlib import Path
from typing import Any


ROOT = Path(__file__).resolve().parents[1]
REQUIREMENT = re.compile(r"^\s*(?:#{1,6}\s*)?(?:[-*]\s*)?(?P<id>(?:FR|NFR|REQ)-\d+)\s*[:\-]\s*(?P<statement>.+?)\s*$", re.IGNORECASE)
STORY = re.compile(r"^\s*(?:#{1,6}\s*)?(?P<id>(?:US|USER-STORY)-?\d+)\s*[:\-]\s*(?P<statement>.+?)\s*$", re.IGNORECASE)
TASK = re.compile(r"^\s*(?:[-*]\s*)?(?:\[[ xX]\]\s*)?(?P<id>T\d+)\s*[:\-]\s*(?P<statement>.+?)\s*$", re.IGNORECASE)
STORY_REFERENCE = re.compile(r"\[(US-?\d+|USER-STORY-?\d+)\]", re.IGNORECASE)
CONTRACT_REFERENCE = re.compile(r"(?:^|[\s(])(?P<path>contracts/[A-Za-z0-9._/-]+)", re.IGNORECASE)


def module(name: str) -> Any:
    spec = importlib.util.spec_from_file_location(name, ROOT / "scripts" / f"{name.replace('_', '-')}.py")
    assert spec and spec.loader
    result = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(result)
    return result


DETECT = module("spec_kit_detect")
POLICY = module("spec_kit_policy")


def normalize_id(value: str) -> str:
    return value.upper().replace("USER-STORY-", "US-")


def read_lines(root: Path, relative: str) -> list[str]:
    return (root / relative).read_text(encoding="utf-8").splitlines()


def reject_sensitive(value: str, patterns: list[str], source: str) -> None:
    if any(re.search(pattern, value) for pattern in patterns):
        raise ValueError(f"privacy policy rejected normalized reference from {source}")


def collect_records(root: Path, relative: str, matcher: re.Pattern[str], patterns: list[str]) -> list[dict[str, str]]:
    records: list[dict[str, str]] = []
    for number, line in enumerate(read_lines(root, relative), 1):
        match = matcher.match(line)
        if not match:
            continue
        statement = match.group("statement").strip()
        reject_sensitive(statement, patterns, f"{relative}:{number}")
        records.append({"external_id": normalize_id(match.group("id")), "statement": statement, "source_path": relative, "source_locator": f"line:{number}"})
    return records


def unique(records: list[dict[str, str]], label: str) -> None:
    seen: set[str] = set()
    duplicates = {record["external_id"] for record in records if record["external_id"] in seen or seen.add(record["external_id"])}
    if duplicates:
        raise ValueError(f"duplicate {label} IDs: {', '.join(sorted(duplicates))}")


def snapshot_dir(root: Path, feature: str) -> Path:
    return root / ".tailtrail" / "spec-kit" / "sources" / feature


def version_for(directory: Path, revision: str) -> tuple[int, bool]:
    previous: list[tuple[int, Path]] = []
    for path in directory.glob("source-v*.json"):
        match = re.fullmatch(r"source-v(\d+)\.json", path.name)
        if match:
            previous.append((int(match.group(1)), path))
    for version, path in sorted(previous):
        try:
            if json.loads(path.read_text(encoding="utf-8")).get("source_revision") == revision:
                return version, True
        except (OSError, json.JSONDecodeError):
            raise ValueError(f"existing source snapshot is unreadable: {path}")
    return (max((version for version, _ in previous), default=0) + 1, False)


def write_json(path: Path, payload: dict[str, Any]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    descriptor, name = tempfile.mkstemp(prefix=f".{path.name}.", dir=path.parent, text=True)
    try:
        with os.fdopen(descriptor, "w", encoding="utf-8", newline="\n") as stream:
            json.dump(payload, stream, indent=2, sort_keys=True)
            stream.write("\n")
        Path(name).replace(path)
    finally:
        temporary = Path(name)
        if temporary.exists():
            temporary.unlink()


def import_feature(root: Path, feature: str, mode: str) -> dict[str, Any]:
    root = root.resolve()
    detection = DETECT.detect(root, feature)
    if detection["state"] != "compatible":
        raise ValueError("feature is not importable: " + "; ".join(detection["issues"] or [detection["state"]]))
    policy = POLICY.load(root / ".tailtrail" / "spec-kit-policy.json") if detection["policy_source"] == "project" else POLICY.load(POLICY.TEMPLATE)
    feature_data = detection["features"][0]
    artifacts = feature_data["artifacts"]
    spec_paths = [item["path"] for item in artifacts if item["kind"] == "spec"]
    spec_path = spec_paths[0]
    patterns = policy["privacy"]["deny_reference_patterns"]
    requirements = collect_records(root, spec_path, REQUIREMENT, patterns)
    stories = collect_records(root, spec_path, STORY, patterns)
    if not requirements:
        requirements = stories.copy()
    unique(requirements, "requirement")
    unique(stories, "story")
    if not requirements:
        raise ValueError("specification contains no identifiable requirement or user-story IDs")
    spec_text = "\n".join(read_lines(root, spec_path)).lower()
    if "acceptance criteria" not in spec_text and "acceptance scenario" not in spec_text:
        raise ValueError("specification is missing acceptance criteria")
    task_paths = [item["path"] for item in artifacts if item["kind"] == "tasks"]
    tasks = collect_records(root, task_paths[0], TASK, patterns) if task_paths else []
    unique(tasks, "task")
    story_ids = {record["external_id"] for record in stories}
    for task in tasks:
        for reference in STORY_REFERENCE.findall(task["statement"]):
            if normalize_id(reference) not in story_ids:
                raise ValueError(f"task {task['external_id']} references unknown story {normalize_id(reference)}")
    contract_paths = {item["path"] for item in artifacts if item["kind"] == "contract"}
    for record in [*requirements, *stories, *tasks]:
        for reference in CONTRACT_REFERENCE.findall(record["statement"]):
            expected = (Path(record["source_path"]).parent / reference).as_posix()
            if expected not in contract_paths:
                raise ValueError(f"{record['external_id']} references unknown contract {reference}")
    revision = detection["source_revision"]
    assert revision
    directory = snapshot_dir(root, feature)
    version, existing = version_for(directory, revision)
    source_uid = f"speckit://local/{feature}"
    if existing:
        return {"type": "tailtrail-spec-kit-import-result", "schema_version": "1", "state": "already-imported", "feature_id": feature, "source_uid": source_uid, "source_revision": revision, "version": version, "mode": mode, "directory": directory.relative_to(root).as_posix(), "boundary": "Existing immutable snapshot matched the current source; no files were changed."}
    source_snapshot = {"schema_version": "1", "type": "tailtrail-spec-kit-source", "source_uid": source_uid, "feature_id": feature, "source_revision": revision, "artifacts": [{key: item[key] for key in ("path", "sha256", "kind")} for item in artifacts]}
    import_snapshot = {"schema_version": "1", "type": "tailtrail-spec-kit-import", "source_uid": source_uid, "source_revision": revision, "requirements": requirements, "privacy_boundary": "normalized-references-only"}
    payloads = {
        f"source-v{version}.json": source_snapshot,
        f"import-v{version}.json": import_snapshot,
        f"requirements-v{version}.json": {"schema_version": "1", "type": "tailtrail-spec-kit-requirements", "source_uid": source_uid, "source_revision": revision, "requirements": requirements},
        f"stories-v{version}.json": {"schema_version": "1", "type": "tailtrail-spec-kit-stories", "source_uid": source_uid, "source_revision": revision, "stories": stories},
        f"tasks-v{version}.json": {"schema_version": "1", "type": "tailtrail-spec-kit-tasks", "source_uid": source_uid, "source_revision": revision, "tasks": tasks},
        f"contracts-v{version}.json": {"schema_version": "1", "type": "tailtrail-spec-kit-contracts", "source_uid": source_uid, "source_revision": revision, "contracts": [item for item in artifacts if item["kind"] == "contract"]},
        f"fingerprints-v{version}.json": {"schema_version": "1", "type": "tailtrail-spec-kit-fingerprints", "source_uid": source_uid, "source_revision": revision, "mode": mode, "artifacts": artifacts},
    }
    if directory.exists() and len(list(directory.glob("source-v*.json"))) >= policy["retention"]["max_snapshots_per_feature"]:
        raise ValueError("source snapshot retention limit reached; do not delete immutable evidence automatically")
    for name, payload in payloads.items():
        write_json(directory / name, payload)
    return {"type": "tailtrail-spec-kit-import-result", "schema_version": "1", "state": "imported", "feature_id": feature, "source_uid": source_uid, "source_revision": revision, "version": version, "mode": mode, "directory": directory.relative_to(root).as_posix(), "artifacts_written": sorted(payloads), "privacy_boundary": "normalized-references-only", "boundary": "Spec Kit source remains read-only and authoritative; TailTrail stored only normalized references and fingerprints."}


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--root", type=Path, default=Path.cwd())
    parser.add_argument("--feature", required=True)
    parser.add_argument("--mode", choices=("review", "planning"), default="review")
    args = parser.parse_args()
    try:
        print(json.dumps(import_feature(args.root, args.feature, args.mode), indent=2, sort_keys=True))
    except (OSError, ValueError, json.JSONDecodeError) as error:
        print(f"Spec Kit import error: {error}")
        return 2
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
