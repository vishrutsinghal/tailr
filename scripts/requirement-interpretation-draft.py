#!/usr/bin/env python3
"""Dry-run a host requirement interpretation without creating any run.

Reads the goal, requirement artifacts, and a draft (clauses, requirements,
material questions, host), assembles the submission envelope with computed
SHA-256 artifact evidence, and runs the real TailTrail validators locally.

Success prints the base64 submission string on stdout (exit 0) for use with
`tailtrail start --requirement-interpretation-base64`. Failure prints the
named validator errors on stderr (exit 2). This command never writes state,
creates runs, or touches the network.
"""

from __future__ import annotations

import argparse
import base64
import hashlib
import importlib.util
import json
import sys
from pathlib import Path
from typing import Any


ROOT = Path(__file__).resolve().parents[1]
if str(ROOT / "scripts") not in sys.path:
    sys.path.insert(0, str(ROOT / "scripts"))


def _load(name: str, filename: str) -> Any:
    spec = importlib.util.spec_from_file_location(name, ROOT / "scripts" / filename)
    module = importlib.util.module_from_spec(spec)
    assert spec and spec.loader
    sys.modules[name] = module
    spec.loader.exec_module(module)
    return module


def _read_artifact(path: Path, index: int) -> dict[str, Any]:
    try:
        content = path.read_text(encoding="utf-8")
    except (OSError, ValueError, UnicodeDecodeError) as error:
        raise ValueError(
            f"requirement artifact is missing or unreadable: {path} ({error})"
        ) from error
    digest = hashlib.sha256(content.encode("utf-8")).hexdigest()
    return {"input_id": f"IN-{index:02d}", "sha256": digest, "content": content}


def _build_evidence(
    artifacts: list[dict[str, Any]], clauses: list[dict[str, Any]]
) -> list[dict[str, Any]]:
    evidence = []
    for artifact in artifacts:
        input_id = str(artifact["input_id"])
        source_ids = sorted({
            str(row.get("clause_id", ""))
            for row in clauses
            if isinstance(row, dict) and str(row.get("source_input_id", "")) == input_id
        })
        if not source_ids:
            raise ValueError(
                "artifact evidence must match inspected hashes and artifact-grounded clauses"
                f" [no artifact-grounded clauses reference {input_id}]"
            )
        evidence.append({
            "input_id": input_id,
            "sha256": str(artifact["sha256"]),
            "source_clause_ids": source_ids,
        })
    return evidence


def validate_draft(
    goal: str,
    artifact_paths: list[str | Path],
    draft: dict[str, Any],
    host: str | None = None,
) -> tuple[dict[str, Any] | None, list[str]]:
    """Validate one draft with the real validators; pure function, no I/O.

    Returns (envelope, []) on success or (None, [error messages]) on
    failure. Reading artifact files may raise ValueError.
    """
    if not isinstance(draft, dict):
        return None, ["draft must be a JSON object"]
    artifacts = [
        _read_artifact(Path(value).expanduser(), index)
        for index, value in enumerate(artifact_paths, start=2)
    ]
    proposal = {
        "schema_version": "1",
        "type": "tailtrail-host-requirement-interpretation",
        "host": host or draft.get("host"),
        "goal": goal,
        "private_reasoning_excluded": True,
        "clauses": draft.get("clauses", []),
        "artifact_evidence": _build_evidence(artifacts, draft.get("clauses", [])),
        "requirements": draft.get("requirements", []),
        "material_questions": draft.get("material_questions", []),
    }
    discovery = _load("draft_requirement_discovery", "requirement_discovery.py")
    try:
        discovery.interpretation(
            goal,
            proposal,
            host or proposal.get("host"),
            [{"input_id": item["input_id"], "sha256": item["sha256"], "content": item["content"]}
             for item in artifacts],
        )
    except ValueError as error:
        return None, [str(error)]
    return proposal, []


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="Dry-run a requirement interpretation (no side effects).")
    parser.add_argument("--goal", required=True, help="Exact goal string the draft is bound to.")
    parser.add_argument("--requirement-artifact", action="append", default=[],
                        help="Requirement artifact file. Repeatable; bound as IN-02, IN-03, ...")
    parser.add_argument("--draft", type=Path, required=True,
                        help="Draft JSON with host, clauses, requirements, and material_questions.")
    parser.add_argument("--host", default=None, choices=("codex", "copilot", "claude"),
                        help="Active host; defaults to the draft host field.")
    args = parser.parse_args(argv)

    try:
        draft = json.loads(args.draft.read_text(encoding="utf-8"))
    except (OSError, ValueError) as error:
        print(f"dry-run error: cannot read draft {args.draft} ({error})", file=sys.stderr)
        return 2
    try:
        proposal, errors = validate_draft(args.goal, args.requirement_artifact, draft, args.host)
    except ValueError as error:
        print(f"dry-run error: {error}", file=sys.stderr)
        return 2
    if proposal is None:
        for message in errors:
            print(f"dry-run error: {message}", file=sys.stderr)
        return 2
    print(base64.b64encode(json.dumps(proposal, separators=(",", ":")).encode("utf-8")).decode("ascii"))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
