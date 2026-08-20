#!/usr/bin/env python3
"""Question-level AIDLC clarification and revision control plane.

This module never reads project source or changes an approved requirement
boundary. It exposes saved AIDLC questions to Interactive Plan Mode, records a
sanitized challenge, and promotes a host/AIDLC-generated replacement only after
an explicit question-level approval.
"""
from __future__ import annotations

import argparse
import importlib.util
import json
from pathlib import Path
from typing import Any


ROOT = Path(__file__).resolve().parents[1]
REASON_CODES = {"unclear", "incorrect-assumption", "missing-option", "unclear-reasoning", "other"}


def module(name: str, filename: str) -> Any:
    spec = importlib.util.spec_from_file_location(name, ROOT / "scripts" / filename)
    loaded = importlib.util.module_from_spec(spec)
    assert spec and spec.loader
    spec.loader.exec_module(loaded)
    return loaded


LOCK = module("aidlc_question_lock", "planning-lock.py")
LEDGER = module("aidlc_question_ledger", "run-ledger.py")
OFFICIAL = module("aidlc_question_official", "official-aidlc-requirements.py")


def _paths(root: Path, run_id: str) -> tuple[Path, Path, bool]:
    root = root.resolve()
    base = LEDGER.state_dir(root, run_id) / "planning"
    official = base / "official-aidlc-requirements-v1.json"
    local = base / "aidlc-requirements-v1.json"
    if official.is_file():
        return official, base / "aidlc-question-revisions-v1.json", True
    if local.is_file():
        return local, base / "aidlc-question-revisions-v1.json", False
    raise ValueError("AIDLC requirements questions are unavailable; start or resume AIDLC Requirements mode first")


def _document(root: Path, run_id: str) -> tuple[dict[str, Any], Path, Path, bool]:
    LOCK.assert_discussion_allowed(root.resolve(), run_id)
    artifact, state_path, official = _paths(root, run_id)
    document = LOCK.read(artifact)
    if not isinstance(document.get("questions"), list) or not document["questions"]:
        raise ValueError("AIDLC questions have not been recorded yet; the configured host must complete the active Requirements stage first")
    return document, artifact, state_path, official


def _state(path: Path, run_id: str) -> dict[str, Any]:
    if path.is_file():
        payload = LOCK.read(path)
        if payload.get("type") != "tailtrail-aidlc-question-revision-state" or payload.get("run_id") != run_id:
            raise ValueError("AIDLC question revision state is invalid")
        return payload
    return {"schema_version": "1", "type": "tailtrail-aidlc-question-revision-state", "run_id": run_id, "question_revision": 1, "pending": None, "history": []}


def _question(document: dict[str, Any], question_id: str) -> dict[str, Any]:
    identifier = question_id.strip()
    for row in document["questions"]:
        if isinstance(row, dict) and str(row.get("id", "")) == identifier:
            return row
    available = ", ".join(str(row.get("id", "")) for row in document["questions"] if isinstance(row, dict))
    raise ValueError(f"unknown AIDLC question `{identifier}`; available: {available}")


def show(root: Path, run_id: str, question_id: str) -> dict[str, Any]:
    document, artifact, state_path, official = _document(root, run_id)
    question = _question(document, question_id)
    state = _state(state_path, run_id)
    return {
        "type": "tailtrail-aidlc-question",
        "run_id": run_id,
        "question_revision": state["question_revision"],
        "authority": "official-ai-dlc-pack" if official else "tailtrail-aidlc-lite",
        "artifact": artifact.relative_to(root.resolve()).as_posix(),
        "question": question,
        "boundary": "Read-only planning evidence. It does not inspect source, change requirements, or approve implementation.",
    }


def clarify(root: Path, run_id: str, question_id: str) -> dict[str, Any]:
    payload = show(root, run_id, question_id)
    question = payload["question"]
    payload.update({
        "type": "tailtrail-aidlc-question-clarification",
        "clarification": {
            "plain_language_goal": "Choose the option that states the intended behavior for this decision; the recommendation is advisory.",
            "why_it_matters": question["reasoning"],
            "recommended_option": question["recommended"],
            "host_action": "Explain or rephrase this question in simpler language while preserving its options, recommendation, and decision meaning. Do not change the plan.",
        },
        "next": "If the wording is merely unclear, return the explanation/rephrase without a plan change. If it is wrong, challenge it with a reason code.",
    })
    LEDGER.append_event(root.resolve(), run_id, "aidlc_question_clarified", {"question_id": question_id, "question_revision": payload["question_revision"], "authority": payload["authority"]})
    return payload


def challenge(root: Path, run_id: str, question_id: str, reason_code: str) -> dict[str, Any]:
    if reason_code not in REASON_CODES:
        raise ValueError("reason-code must be one of: " + ", ".join(sorted(REASON_CODES)))
    document, artifact, state_path, official = _document(root, run_id)
    question = _question(document, question_id)
    state = _state(state_path, run_id)
    if state.get("pending"):
        raise ValueError("an AIDLC question revision is already pending; approve or replace it before opening another")
    proposal = {
        "proposal_id": f"aidlc-question-v{state['question_revision'] + 1}-{question_id}",
        "question_id": question_id,
        "base_question_revision": state["question_revision"],
        "reason_code": reason_code,
        "authority": "official-ai-dlc-pack" if official else "tailtrail-aidlc-lite",
        "status": "host-revision-required",
    }
    state["pending"] = proposal
    LEDGER.atomic_json(state_path, state)
    LEDGER.append_event(root.resolve(), run_id, "aidlc_question_revision_proposed", proposal)
    return {
        "type": "tailtrail-aidlc-question-revision-proposal",
        "run_id": run_id,
        "proposal": proposal,
        "question": question,
        "host_action": "Use the active AIDLC authority to generate a complete replacement for this one question, including options, TailTrail advisory recommendation, and reasoning. Standard/Full must use the pinned official AIDLC Requirements rules.",
        "boundary": "No question, answer, requirement, anchor, source, or implementation state has changed.",
    }


def record(root: Path, run_id: str, question_json: str) -> dict[str, Any]:
    document, _, state_path, official = _document(root, run_id)
    state = _state(state_path, run_id)
    pending = state.get("pending")
    if not isinstance(pending, dict) or pending.get("status") != "host-revision-required":
        raise ValueError("no pending AIDLC question revision requires host output")
    candidate = json.loads(question_json)
    if not isinstance(candidate, dict) or str(candidate.get("id", "")) != pending["question_id"]:
        raise ValueError("replacement question must be an object with the pending question ID")
    if official:
        candidate = OFFICIAL.validate_host_questions([candidate])[0]
    else:
        required = ("id", "question", "options", "recommended", "reasoning")
        if any(not candidate.get(name) for name in required) or not isinstance(candidate.get("options"), list):
            raise ValueError("Lite replacement requires id, question, options, recommended, and reasoning")
        option_text = {str(item.get("text", "")) for item in candidate["options"] if isinstance(item, dict)}
        if str(candidate["recommended"]) not in option_text:
            raise ValueError("Lite replacement recommended value must match an option text")
    pending["candidate"] = candidate
    pending["status"] = "awaiting-question-approval"
    state["pending"] = pending
    LEDGER.atomic_json(state_path, state)
    LEDGER.append_event(root.resolve(), run_id, "aidlc_question_revision_recorded", {"proposal_id": pending["proposal_id"], "question_id": pending["question_id"], "authority": pending["authority"]})
    return {"type": "tailtrail-aidlc-question-revision", "run_id": run_id, "proposal": pending, "next": "Show the revised question to the user. It must be explicitly approved before it replaces the active question."}


def approve(root: Path, run_id: str, approved: bool) -> dict[str, Any]:
    if approved is not True:
        raise ValueError("AIDLC question revision approval requires --approved")
    document, artifact, state_path, _ = _document(root, run_id)
    state = _state(state_path, run_id)
    pending = state.get("pending")
    if not isinstance(pending, dict) or pending.get("status") != "awaiting-question-approval":
        raise ValueError("no recorded AIDLC question revision is awaiting approval")
    old = _question(document, str(pending["question_id"]))
    history_dir = state_path.parent / "aidlc-question-history"
    history_dir.mkdir(parents=True, exist_ok=True)
    snapshot = history_dir / f"questions-v{state['question_revision']}.json"
    LEDGER.atomic_json(snapshot, {"type": "tailtrail-aidlc-question-snapshot", "run_id": run_id, "question_revision": state["question_revision"], "questions": document["questions"]})
    document["questions"] = [pending["candidate"] if str(row.get("id", "")) == pending["question_id"] else row for row in document["questions"]]
    document["question_revision"] = state["question_revision"] + 1
    LEDGER.atomic_json(artifact, document)
    state["history"].append({"proposal_id": pending["proposal_id"], "question_id": pending["question_id"], "from_revision": state["question_revision"], "to_revision": document["question_revision"], "previous_question": old})
    state["question_revision"] = document["question_revision"]
    state["pending"] = None
    LEDGER.atomic_json(state_path, state)
    LEDGER.append_event(root.resolve(), run_id, "aidlc_question_revision_approved", {"proposal_id": pending["proposal_id"], "question_id": pending["question_id"], "question_revision": document["question_revision"], "snapshot": snapshot.relative_to(root.resolve()).as_posix()})
    return {"type": "tailtrail-aidlc-question-revision-approved", "run_id": run_id, "question_revision": document["question_revision"], "question_id": pending["question_id"], "next": "The affected question is reopened. Answer the current AIDLC question set again before approving the requirements boundary.", "boundary": "Only the question artifact changed. The approved anchor and implementation remain blocked."}


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    sub = parser.add_subparsers(dest="command", required=True)
    for name in ("show", "clarify", "challenge"):
        item = sub.add_parser(name); item.add_argument("--root", type=Path, default=Path.cwd()); item.add_argument("--run-id", required=True); item.add_argument("--question-id", required=True)
        if name == "challenge": item.add_argument("--reason-code", required=True, choices=sorted(REASON_CODES))
    record_parser = sub.add_parser("record"); record_parser.add_argument("--root", type=Path, default=Path.cwd()); record_parser.add_argument("--run-id", required=True); record_parser.add_argument("--question", required=True)
    approve_parser = sub.add_parser("approve"); approve_parser.add_argument("--root", type=Path, default=Path.cwd()); approve_parser.add_argument("--run-id", required=True); approve_parser.add_argument("--approved", action="store_true")
    args = parser.parse_args()
    try:
        if args.command == "show": payload = show(args.root, args.run_id, args.question_id)
        elif args.command == "clarify": payload = clarify(args.root, args.run_id, args.question_id)
        elif args.command == "challenge": payload = challenge(args.root, args.run_id, args.question_id, args.reason_code)
        elif args.command == "record": payload = record(args.root, args.run_id, args.question)
        else: payload = approve(args.root, args.run_id, args.approved)
        print(json.dumps(payload, indent=2, sort_keys=True)); return 0
    except (OSError, ValueError, json.JSONDecodeError) as error:
        print(f"AIDLC question control error: {error}"); return 2


if __name__ == "__main__":
    raise SystemExit(main())
