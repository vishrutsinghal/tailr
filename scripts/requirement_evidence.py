#!/usr/bin/env python3
"""Bounded, decision-specific evidence gathering for pre-lock requirements."""

from __future__ import annotations

import hashlib
import json
import os
import re
from pathlib import Path
from typing import Any


MAX_FILES = 24
MAX_BYTES = 262_144
MAX_FILE_BYTES = 65_536
MAX_DIRECTORIES = 128
MAX_CANDIDATES = 96
EXCLUDED_PARTS = {
    ".git", ".tailtrail", "tailtrail-meta", "node_modules", "vendor",
    "dist", "build", "coverage", ".terraform", "__pycache__",
}
RESOURCE_PATTERNS = {
    "aws-secrets-manager": re.compile(
        r'\b(?:resource|data)\s+"aws_secretsmanager_(?:secret|secret_version)"'
    ),
    "ssm-parameter-store": re.compile(r'\b(?:resource|data)\s+"aws_ssm_parameter"'),
}


def canonical(value: Any) -> str:
    return json.dumps(value, sort_keys=True, separators=(",", ":"))


def fingerprint(value: Any) -> str:
    return "sha256:" + hashlib.sha256(canonical(value).encode("utf-8")).hexdigest()


def validate(packet: dict[str, Any], *, root: Path, goal: str) -> None:
    """Validate the saved packet's identity and tamper-evident fingerprint."""
    if packet.get("type") != "tailtrail-requirement-evidence":
        raise ValueError("requirement evidence type is invalid")
    unsigned = {key: value for key, value in packet.items() if key != "fingerprint"}
    if packet.get("fingerprint") != fingerprint(unsigned):
        raise ValueError("requirement evidence fingerprint is invalid")
    resolved_root = root.resolve()
    expected_root = "sha256:" + hashlib.sha256(
        resolved_root.as_posix().encode("utf-8")
    ).hexdigest()
    expected_goal = "sha256:" + hashlib.sha256(goal.encode("utf-8")).hexdigest()
    if packet.get("root_fingerprint") != expected_root:
        raise ValueError("requirement evidence root identity is invalid")
    if packet.get("goal_fingerprint") != expected_goal:
        raise ValueError("requirement evidence goal identity is invalid")
    if packet.get("limits", {}).get("execution_allowed") is not False:
        raise ValueError("requirement evidence must not grant execution authority")


def _eligible_terraform(root: Path) -> tuple[list[Path], int, bool]:
    paths: list[Path] = []
    directories_scanned = 0
    stopped = False
    for current, directory_names, file_names in os.walk(root, followlinks=False):
        directories_scanned += 1
        if directories_scanned > MAX_DIRECTORIES:
            stopped = True
            break
        directory_names[:] = sorted(
            name for name in directory_names if name not in EXCLUDED_PARTS
        )
        current_path = Path(current)
        for name in sorted(file_names):
            if not name.endswith(".tf"):
                continue
            path = current_path / name
            if path.is_symlink():
                continue
            paths.append(path)
            if len(paths) >= MAX_CANDIDATES:
                stopped = True
                return paths, directories_scanned, stopped
    return paths, directories_scanned, stopped


def _infrastructure_resource_evidence(
    root: Path,
    decision: dict[str, Any],
) -> tuple[dict[str, Any], dict[str, int]]:
    findings: list[dict[str, Any]] = []
    counts = {option: 0 for option in RESOURCE_PATTERNS}
    files_read = 0
    bytes_read = 0
    stopped_by: str | None = None
    candidates, directories_scanned, discovery_stopped = _eligible_terraform(root)
    if discovery_stopped:
        stopped_by = "discovery-limit"
    for path in candidates:
        if files_read >= MAX_FILES:
            stopped_by = "file-limit"
            break
        try:
            size = path.stat().st_size
        except OSError:
            continue
        if size > MAX_FILE_BYTES:
            continue
        if bytes_read + size > MAX_BYTES:
            stopped_by = "byte-limit"
            break
        try:
            content = path.read_text(encoding="utf-8")
        except (OSError, UnicodeDecodeError):
            continue
        files_read += 1
        bytes_read += size
        relative = path.relative_to(root).as_posix()
        content_hash = "sha256:" + hashlib.sha256(content.encode("utf-8")).hexdigest()
        for option, pattern in RESOURCE_PATTERNS.items():
            for match in pattern.finditer(content):
                line = content.count("\n", 0, match.start()) + 1
                counts[option] += 1
                findings.append({
                    "evidence_id": f"{decision['id']}-E-{len(findings) + 1:03d}",
                    "kind": "repository-convention",
                    "option": option,
                    "path": relative,
                    "line": line,
                    "content_hash": content_hash,
                    "strength": "supporting",
                })
    present = [option for option, count in counts.items() if count]
    recommendation: dict[str, Any] | None = None
    if len(present) == 1:
        recommendation = {
            "option": present[0],
            "confidence": "medium",
            "reason": "The bounded repository slice uses this resource type and found no competing supported type.",
            "evidence_ids": [row["evidence_id"] for row in findings if row["option"] == present[0]],
        }
    state = (
        "limit-reached"
        if stopped_by
        else "supported"
        if recommendation
        else "conflicting"
        if len(present) > 1
        else "no-evidence"
    )
    return ({
        "decision_id": str(decision["id"]),
        "decision_class": str(decision["decision_class"]),
        "state": state,
        "findings": findings,
        "recommendation": recommendation,
        "resolution": "ask-user",
        "reason": (
            "Repository convention is advisory; the material infrastructure choice still requires explicit confirmation."
            if findings
            else "No supported repository convention was found within the bounded Terraform slice."
        ),
    }, {
        "files_read": files_read,
        "bytes_read": bytes_read,
        "findings": len(findings),
        "stopped_by_limit": 1 if stopped_by else 0,
        "directories_scanned": directories_scanned,
    })


def gather(root: Path, goal: str, sufficiency: dict[str, Any]) -> dict[str, Any]:
    """Gather only evidence relevant to the existing material decisions."""
    resolved_root = root.resolve()
    decisions: list[dict[str, Any]] = []
    totals = {
        "files_read": 0,
        "bytes_read": 0,
        "findings": 0,
        "stopped_by_limit": 0,
        "directories_scanned": 0,
    }
    for decision in sufficiency.get("material_decisions", []):
        if not isinstance(decision, dict) or not decision.get("id"):
            continue
        if decision.get("decision_class") == "infrastructure-resource-type":
            row, metrics = _infrastructure_resource_evidence(resolved_root, decision)
        else:
            row = {
                "decision_id": str(decision["id"]),
                "decision_class": str(decision.get("decision_class", "material-requirement-decision")),
                "state": "unsupported-decision-class",
                "findings": [],
                "recommendation": None,
                "resolution": "ask-user",
                "reason": "No safe decision-specific static evidence strategy is registered for this question.",
            }
            metrics = {key: 0 for key in totals}
        decisions.append(row)
        for key in totals:
            totals[key] += metrics[key]
    packet = {
        "schema_version": "1",
        "type": "tailtrail-requirement-evidence",
        "goal_fingerprint": "sha256:" + hashlib.sha256(goal.encode("utf-8")).hexdigest(),
        "root_fingerprint": "sha256:" + hashlib.sha256(resolved_root.as_posix().encode("utf-8")).hexdigest(),
        "limits": {
            "max_files": MAX_FILES,
            "max_bytes": MAX_BYTES,
            "max_file_bytes": MAX_FILE_BYTES,
            "max_directories": MAX_DIRECTORIES,
            "max_candidates": MAX_CANDIDATES,
            "execution_allowed": False,
        },
        "metrics": totals,
        "decisions": decisions,
        "boundary": "Requirement evidence is advisory and pre-lock. It cannot prove implementation ownership, create scope, answer a material question, or grant authority.",
    }
    packet["fingerprint"] = fingerprint(packet)
    return packet
