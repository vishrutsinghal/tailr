#!/usr/bin/env python3
"""Durable, authority-free requirement intake before a Planning Lock exists."""

from __future__ import annotations

import argparse
import base64
import hashlib
import importlib.util
import json
import re
import sys
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

import requirement_evidence
from shell_quote import quote


ROOT = Path(__file__).resolve().parents[1]
IDENTIFIER = re.compile(r"^intake-[a-f0-9]{16}$")
SENSITIVE = (
    re.compile(r"-----BEGIN [A-Z0-9 ]*PRIVATE KEY-----", re.IGNORECASE),
    re.compile(r"\b(?:AKIA|ASIA)[A-Z0-9]{16}\b"),
    re.compile(r"\b(?:password|secret|token|api[_ -]?key)\s*[:=]\s*\S+", re.IGNORECASE),
    re.compile(r"\bBearer\s+[A-Za-z0-9._~+/=-]+", re.IGNORECASE),
)


def _ledger() -> Any:
    spec = importlib.util.spec_from_file_location(
        "tailtrail_requirement_intake_ledger", ROOT / "scripts" / "run-ledger.py"
    )
    module = importlib.util.module_from_spec(spec)
    assert spec and spec.loader
    spec.loader.exec_module(module)
    return module


LEDGER = _ledger()


def _visual_requirement() -> Any:
    spec = importlib.util.spec_from_file_location(
        "tailtrail_requirement_intake_visual", ROOT / "scripts" / "visual_requirement.py"
    )
    module = importlib.util.module_from_spec(spec)
    assert spec and spec.loader
    spec.loader.exec_module(module)
    return module


def utc_now() -> str:
    return datetime.now(timezone.utc).replace(microsecond=0).isoformat()


def canonical(value: Any) -> str:
    return json.dumps(value, sort_keys=True, separators=(",", ":"))


def safe_intake_id(value: str) -> str:
    if not IDENTIFIER.fullmatch(value):
        raise ValueError("intake ID must be an exact TailTrail requirement-intake identifier")
    return value


def intake_root(root: Path) -> Path:
    return root.resolve() / ".tailtrail" / "requirement-intakes"


def intake_dir(root: Path, intake_id: str) -> Path:
    return intake_root(root) / safe_intake_id(intake_id)


def identity(root: Path, goal: str, route: str, host: str | None) -> dict[str, str]:
    return {
        "root": root.resolve().as_posix(),
        "goal": goal,
        "route": route,
        "host": host or "none",
    }


def intake_id_for(root: Path, goal: str, route: str, host: str | None) -> str:
    digest = hashlib.sha256(canonical(identity(root, goal, route, host)).encode("utf-8")).hexdigest()
    return f"intake-{digest[:16]}"


def _continuation(
    intake_id: str,
    state: str,
    command_prefix: str,
    intake_identity: dict[str, str],
) -> dict[str, Any]:
    if state == "answered":
        mode = {
            "aidlc-standard": "standard",
            "aidlc-full": "full",
            "lite-questions": "lite",
        }[intake_identity["route"]]
        host = intake_identity.get("host", "none")
        host_argument = "" if host == "none" else f" --host {quote(host)}"
        return {
            "action": "requirements-resume",
            "intake_id": intake_id,
            "prompt": f"Resume TailTrail requirement intake {intake_id} and continue its {mode} route.",
            "command": (
                f"{command_prefix} start {quote(intake_identity['goal'])} "
                f"--root {quote(intake_identity['root'])} "
                f"--requirement-intake-id {intake_id} --aidlc {mode}{host_argument}"
            ),
            "boundary": "Resuming consumes only this goal/root/host-bound answered intake, then re-evaluates requirements before graph, scope, or Planning Lock work.",
        }
    return {
        "action": "requirements-answer",
        "intake_id": intake_id,
        "prompt": f"Answer the material questions for TailTrail requirement intake {intake_id}.",
        "command": (
            f"{command_prefix} requirements answer --root . --intake-id {intake_id} "
            "--answers '<JSON object keyed by decision ID>'"
        ),
        "boundary": "Answers update only this pre-lock intake and grant no implementation authority.",
    }


def _questions(sufficiency: dict[str, Any]) -> list[dict[str, Any]]:
    return [
        {
            "decision_id": str(row["id"]),
            "decision_class": str(row["decision_class"]),
            "question": str(row["question"]),
            "impact": [str(value) for value in row.get("impact", [])],
            "evidence_refs": [str(value) for value in row.get("evidence_refs", [])],
        }
        for row in sufficiency.get("material_decisions", [])
        if isinstance(row, dict) and row.get("id") and row.get("question")
    ]


def create(
    root: Path,
    goal: str,
    interpreted: dict[str, Any],
    *,
    route: str,
    host: str | None,
    requested_mode: str | None,
    command_prefix: str,
    evidence: dict[str, Any],
    route_posture: dict[str, Any] | None = None,
) -> dict[str, Any]:
    """Create or idempotently reuse one goal-bound pre-lock intake."""
    resolved_root = root.resolve()
    requirement_evidence.validate(evidence, root=resolved_root, goal=goal)
    intake_id = intake_id_for(resolved_root, goal, route, host)
    directory = intake_dir(resolved_root, intake_id)
    current_path = directory / "current.json"
    expected_identity = identity(resolved_root, goal, route, host)
    with LEDGER.RunLock(directory / ".lock"):
        if current_path.exists():
            current = LEDGER.read_json(current_path)
            if current.get("identity") != expected_identity:
                raise ValueError("requirement intake identity does not match the current request")
            if (
                current.get("requirement_evidence") != evidence
                or not isinstance(current.get("requirement_interpretation"), dict)
                or current.get("route_posture") != route_posture
            ):
                revision = int(current.get("revision", 0)) + 1
                current = {
                    **current,
                    "revision": revision,
                    "updated_at": utc_now(),
                    "requirement_evidence": evidence,
                    "requirement_interpretation": interpreted,
                    "route_posture": route_posture,
                }
                LEDGER.atomic_json(
                    directory / "revisions" / f"revision-{revision:04d}.json", current
                )
                LEDGER.atomic_json(current_path, current)
            return current
        now = utc_now()
        sufficiency = interpreted.get("sufficiency", {})
        artifact = {
            "schema_version": "1",
            "type": "tailtrail-requirement-intake",
            "intake_id": intake_id,
            "revision": 1,
            "state": "awaiting-requirements",
            "created_at": now,
            "updated_at": now,
            "identity": expected_identity,
            "requested_mode": requested_mode,
            "requirements": interpreted.get("requirements", []),
            "questions": _questions(sufficiency if isinstance(sufficiency, dict) else {}),
            "answers": {},
            "requirement_sufficiency": sufficiency,
            "requirement_evidence": evidence,
            "route_posture": route_posture,
            "requirement_interpretation": interpreted,
            "continuation": _continuation(
                intake_id, "awaiting-requirements", command_prefix, expected_identity
            ),
            "authority": {
                "planning_lock": False,
                "scope": False,
                "implementation": False,
            },
            "boundary": "Durable requirement intake only. No graph lifecycle, scope decision, Planning Lock, workflow, or implementation authority exists.",
        }
        LEDGER.atomic_json(directory / "revisions" / "revision-0001.json", artifact)
        LEDGER.atomic_json(current_path, artifact)
        return artifact


def load(root: Path, intake_id: str) -> dict[str, Any]:
    path = intake_dir(root.resolve(), intake_id) / "current.json"
    if not path.is_file():
        raise ValueError(f"requirement intake `{intake_id}` does not exist")
    artifact = LEDGER.read_json(path)
    if artifact.get("intake_id") != intake_id or artifact.get("type") != "tailtrail-requirement-intake":
        raise ValueError("requirement intake identity is invalid")
    intake_identity = artifact.get("identity", {})
    requirement_evidence.validate(
        artifact.get("requirement_evidence", {}),
        root=Path(str(intake_identity.get("root", ""))),
        goal=str(intake_identity.get("goal", "")),
    )
    return artifact


def resolved_interpretation(artifact: dict[str, Any]) -> dict[str, Any]:
    """Project an answered intake back into the typed Start interpretation."""
    if artifact.get("state") != "answered":
        raise ValueError("requirement intake must be fully answered before Start can resume")
    source = artifact.get("requirement_interpretation")
    if not isinstance(source, dict):
        goal = str(artifact.get("identity", {}).get("goal", ""))
        source = {
            "schema_version": "1",
            "type": "tailtrail-requirement-interpretation",
            "source": "legacy-requirement-intake",
            "host": None,
            "goal_fingerprint": "sha256:" + hashlib.sha256(
                goal.encode("utf-8")
            ).hexdigest(),
            "private_reasoning_excluded": True,
            "clauses": [],
            "requirements": list(artifact.get("requirements", [])),
            "material_questions": [
                str(row.get("question"))
                for row in artifact.get("questions", [])
                if isinstance(row, dict) and row.get("question")
            ],
            "state": artifact.get("requirement_sufficiency", {}).get("state"),
            "sufficiency": dict(artifact.get("requirement_sufficiency", {})),
        }
    questions = {
        str(row.get("decision_id")): row
        for row in artifact.get("questions", [])
        if isinstance(row, dict) and row.get("decision_id")
    }
    answers = artifact.get("answers", {})
    if set(questions) != set(answers):
        raise ValueError("requirement intake answers do not resolve every material decision")
    resolved = [
        {
            "id": decision_id,
            "decision_class": row["decision_class"],
            "answer": str(answers[decision_id]),
            "impact": list(row.get("impact", [])),
            "evidence_refs": list(row.get("evidence_refs", [])),
        }
        for decision_id, row in questions.items()
    ]
    sufficiency = dict(source.get("sufficiency", {}))
    resolved_dimensions = []
    for row in sufficiency.get("dimensions", []):
        if not isinstance(row, dict):
            continue
        updated = dict(row)
        if updated.get("id") == "material-decisions":
            updated.update({
                "status": "satisfied",
                "reason": "Every material decision was answered in the durable requirement intake.",
                "evidence_refs": [str(item["id"]) for item in resolved],
            })
        resolved_dimensions.append(updated)
    sufficiency.update({
        "state": "sufficient",
        "confidence": "medium",
        "material_decisions": [],
        "resolved_material_decisions": resolved,
        "recommended_route": "scope",
        "post_intake_route": artifact["identity"]["route"],
        "intake_id": artifact["intake_id"],
        "intake_revision": artifact["revision"],
        "dimensions": resolved_dimensions,
    })
    return {
        **source,
        "source": "answered-requirement-intake",
        "state": "sufficient",
        "material_questions": [],
        "sufficiency": sufficiency,
        "intake_resolution": {
            "intake_id": artifact["intake_id"],
            "revision": artifact["revision"],
            "route": artifact["identity"]["route"],
            "resolved_decision_ids": sorted(questions),
            "authority": artifact["authority"],
        },
    }


def _safe_answer(value: Any) -> str:
    if not isinstance(value, str):
        raise ValueError("each requirement answer must be text")
    answer = " ".join(value.split())
    if not answer or len(answer) > 2000:
        raise ValueError("each requirement answer must contain 1 to 2000 characters")
    if any(pattern.search(answer) for pattern in SENSITIVE):
        raise ValueError("requirement answers must not contain credentials or secret values")
    return answer


def answer(
    root: Path,
    intake_id: str,
    answers: dict[str, Any],
    *,
    command_prefix: str,
) -> dict[str, Any]:
    """Append a bounded answer revision without creating delivery authority."""
    if not answers:
        raise ValueError("provide at least one requirement answer")
    directory = intake_dir(root.resolve(), intake_id)
    with LEDGER.RunLock(directory / ".lock"):
        current_path = directory / "current.json"
        if not current_path.is_file():
            raise ValueError(f"requirement intake `{intake_id}` does not exist")
        current = LEDGER.read_json(current_path)
        intake_identity = current.get("identity", {})
        requirement_evidence.validate(
            current.get("requirement_evidence", {}),
            root=Path(str(intake_identity.get("root", ""))),
            goal=str(intake_identity.get("goal", "")),
        )
        offered = {str(row["decision_id"]) for row in current.get("questions", [])}
        unknown = sorted(set(answers) - offered)
        if unknown:
            raise ValueError("answers contain unknown decision IDs: " + ", ".join(unknown))
        merged = dict(current.get("answers", {}))
        merged.update({str(key): _safe_answer(value) for key, value in answers.items()})
        state = "answered" if offered and offered <= set(merged) else "awaiting-requirements"
        revision = int(current.get("revision", 0)) + 1
        updated = {
            **current,
            "revision": revision,
            "state": state,
            "updated_at": utc_now(),
            "answers": merged,
            "continuation": _continuation(
                intake_id, state, command_prefix, dict(intake_identity)
            ),
        }
        LEDGER.atomic_json(directory / "revisions" / f"revision-{revision:04d}.json", updated)
        LEDGER.atomic_json(current_path, updated)
        return updated


def attach_visual(
    root: Path,
    intake_id: str,
    attachment: dict[str, Any],
    observation: dict[str, Any],
    *,
    command_prefix: str,
) -> dict[str, Any]:
    """Bind one host-resolved image to an existing visual requirement intake.

    This is metadata-only. The image remains at the host-provided local path;
    the intake stores a hash-bound receipt and the host's bounded observation.
    """
    visual = _visual_requirement()
    normalized = visual.normalize_visual_attachments([attachment])[0]
    with visual.staged_attachments([normalized]) as staged:
        staged_attachment = staged[0]
        inspected = visual.inspect_visual_artifact(staged_attachment["local_path"])
        if inspected.get("status") != "inspected":
            raise ValueError(
                "visual attachment is not readable: "
                + str(inspected.get("reason_code", "visual-artifact-unavailable"))
            )
        inspected["locator"] = staged_attachment["local_path"]
        payload = dict(observation)
        payload["locator"] = staged_attachment["local_path"]
        bound, issues = visual.bind_observations(payload, [inspected])
        if issues:
            raise ValueError("visual observations are invalid: " + "; ".join(issues))
        record = {
            **bound[0],
            "attachment_id": normalized["attachment_id"],
        }
    # The staging path is intentionally not durable: it was deleted above.
    record.pop("locator", None)
    directory = intake_dir(root.resolve(), intake_id)
    with LEDGER.RunLock(directory / ".lock"):
        current_path = directory / "current.json"
        if not current_path.is_file():
            raise ValueError(f"requirement intake `{intake_id}` does not exist")
        current = LEDGER.read_json(current_path)
        questions = list(current.get("questions", []))
        visual_questions = [row for row in questions if row.get("decision_class") == visual.VISUAL_DECISION_CLASS]
        if not visual_questions:
            raise ValueError("requirement intake has no unresolved visual requirement")
        answers = dict(current.get("answers", {}))
        for question in visual_questions:
            decision_id = str(question["decision_id"])
            if record["complete"]:
                answers[decision_id] = record["summary"]
            else:
                question["question"] = "; ".join(record["open_questions"])
        offered = {str(row["decision_id"]) for row in questions}
        state = "answered" if offered and offered <= set(answers) else "awaiting-requirements"
        revision = int(current.get("revision", 0)) + 1
        updated = {
            **current,
            "revision": revision,
            "state": state,
            "updated_at": utc_now(),
            "questions": questions,
            "answers": answers,
            "visual_requirements": [
                *[row for row in current.get("visual_requirements", []) if isinstance(row, dict) and row.get("attachment_id") != record["attachment_id"]],
                record,
            ],
            "continuation": _continuation(
                intake_id, state, command_prefix, dict(current.get("identity", {}))
            ),
        }
        LEDGER.atomic_json(directory / "revisions" / f"revision-{revision:04d}.json", updated)
        LEDGER.atomic_json(current_path, updated)
        return updated


def evidence_lines(evidence: dict[str, Any] | None, answers: dict[str, Any] | None = None) -> list[str]:
    if not isinstance(evidence, dict):
        return []
    answers = answers or {}
    metrics = evidence.get("metrics", {})
    lines = [
        "## Bounded requirement evidence",
        "",
        (
            f"- Inspected `{metrics.get('files_read', 0)}` decision-relevant file(s) "
            f"across `{metrics.get('directories_scanned', 0)}` bounded directories; "
            f"found `{metrics.get('findings', 0)}` supporting convention(s)."
        ),
    ]
    for decision in evidence.get("decisions", []):
        if not isinstance(decision, dict):
            continue
        decision_id = str(decision.get("decision_id"))
        recorded_answer = answers.get(decision_id)
        if recorded_answer is not None:
            lines.append(
                f"- **{decision_id}:** `{decision.get('state')}`; recorded answer `{recorded_answer}` "
                "supersedes any repository-convention advisory below."
            )
            continue
        recommendation = decision.get("recommendation")
        if isinstance(recommendation, dict):
            detail = (
                f"advisory recommendation `{recommendation.get('option')}` "
                f"(`{recommendation.get('confidence')}` confidence)"
            )
        else:
            detail = "no evidence-backed recommendation"
        lines.append(
            f"- **{decision.get('decision_id')}:** `{decision.get('state')}`; {detail}."
        )
    lines.extend([f"- {evidence.get('boundary')}", ""])
    return lines


def render(artifact: dict[str, Any]) -> str:
    lines = [
        "# TailTrail Requirement Intake",
        "",
        f"**Intake ID:** `{artifact['intake_id']}`",
        f"**State:** `{artifact['state']}`",
        f"**Route:** `{artifact['identity']['route']}`",
        "",
        artifact["boundary"],
        "",
        "## Material questions",
        "",
    ]
    route_posture = artifact.get("route_posture")
    if isinstance(route_posture, dict):
        lines[-2:] = [
            "## Route handoff",
            "",
            f"- Saved route: `{artifact['identity']['route']}`.",
            f"- Official pack posture: `{route_posture.get('state')}`.",
            f"- {route_posture.get('boundary')}",
            "",
            "## Material questions",
            "",
        ]
    answers = artifact.get("answers", {})
    for row in artifact.get("questions", []):
        decision_id = str(row["decision_id"])
        lines.append(f"- **{decision_id}:** {row['question']}")
        if decision_id in answers:
            lines.append(f"  - Recorded answer: {answers[decision_id]}")
    lines.extend(["", *evidence_lines(artifact.get("requirement_evidence"), answers)])
    continuation = artifact["continuation"]
    lines.extend([
        "",
        "## Continue",
        "",
        f"- {continuation['prompt']}",
    ])
    if continuation.get("command"):
        lines.append(f"- `{continuation['command']}`")
    lines.append("")
    return "\n".join(lines)


def _read_answers(args: argparse.Namespace) -> dict[str, Any]:
    if args.answers is not None:
        value = json.loads(args.answers)
    elif args.answers_base64 is not None:
        value = json.loads(base64.b64decode(args.answers_base64, validate=True).decode("utf-8"))
    else:
        value = json.load(sys.stdin)
    if not isinstance(value, dict):
        raise ValueError("answers must be a JSON object keyed by decision ID")
    return value


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    sub = parser.add_subparsers(dest="command", required=True)
    show_parser = sub.add_parser("show")
    answer_parser = sub.add_parser("answer")
    attach_visual_parser = sub.add_parser("attach-visual")
    for item in (show_parser, answer_parser, attach_visual_parser):
        item.add_argument("--root", type=Path, default=Path.cwd())
        item.add_argument("--intake-id", required=True)
        item.add_argument("--format", choices=("markdown", "json"), default="markdown")
        item.add_argument("--command-prefix", default="tailtrail")
    group = answer_parser.add_mutually_exclusive_group(required=True)
    group.add_argument("--answers")
    group.add_argument("--answers-base64")
    group.add_argument("--answers-stdin", action="store_true")
    attach_visual_parser.add_argument("--attachment-id", required=True)
    attach_visual_parser.add_argument("--visual-artifact", required=True)
    observation_group = attach_visual_parser.add_mutually_exclusive_group(required=True)
    observation_group.add_argument("--visual-observations")
    observation_group.add_argument("--visual-observations-base64")
    args = parser.parse_args()
    try:
        if args.command == "show":
            artifact = load(args.root, args.intake_id)
        elif args.command == "answer":
            artifact = answer(
                args.root,
                args.intake_id,
                _read_answers(args),
                command_prefix=args.command_prefix,
            )
        else:
            raw_observation = (
                json.loads(args.visual_observations)
                if args.visual_observations is not None
                else json.loads(base64.b64decode(args.visual_observations_base64, validate=True).decode("utf-8"))
            )
            if not isinstance(raw_observation, dict):
                raise ValueError("visual observations must be a JSON object")
            artifact = attach_visual(
                args.root,
                args.intake_id,
                {"attachment_id": args.attachment_id, "local_path": args.visual_artifact},
                raw_observation,
                command_prefix=args.command_prefix,
            )
    except (OSError, ValueError, json.JSONDecodeError) as error:
        print(f"TailTrail requirement intake error: {error}", file=sys.stderr)
        return 2
    if args.format == "json":
        print(json.dumps(artifact, indent=2, sort_keys=True))
    else:
        print(render(artifact), end="")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
