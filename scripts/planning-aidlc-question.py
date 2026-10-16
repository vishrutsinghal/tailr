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

# Phase 2.5: Task profile definitions with acceptance criteria
TASK_PROFILES = {
    "documentation-only": {
        "name": "Documentation Only",
        "description": "Changes to documentation, comments, or non-executable content only",
        "acceptance_criteria": [
            "No executable code changes",
            "All changes are documentation or comments",
            "No runtime behavior modifications",
        ],
        "question_template": "Is this change documentation-only (comments, docs, README)?",
    },
    "existing-code-change": {
        "name": "Existing Code Change",
        "description": "Modifications to existing executable code without creating new features",
        "acceptance_criteria": [
            "Modifies existing functions or classes",
            "No new public API surface created",
            "Maintains backward compatibility",
        ],
        "question_template": "Does this modify existing code without adding new public APIs?",
    },
    "new-feature": {
        "name": "New Feature",
        "description": "Implementation of new functionality and public API surface",
        "acceptance_criteria": [
            "Creates new public functions, classes, or modules",
            "Backward compatible with existing code",
            "Has explicit acceptance tests",
        ],
        "question_template": "Is this a new feature with new public APIs?",
    },
    "configuration-data": {
        "name": "Configuration / Data",
        "description": "Changes to configuration files, data structures, or constants",
        "acceptance_criteria": [
            "Only configuration or data structure changes",
            "No code logic modifications",
            "Updates validated against schema if applicable",
        ],
        "question_template": "Is this change to configuration or data only?",
    },
    "qa-validation-only": {
        "name": "QA / Validation Only",
        "description": "Test-only changes: unit tests, integration tests, validation logic",
        "acceptance_criteria": [
            "No production code changes",
            "Only test or validation code",
            "Covers at least one production code path",
        ],
        "question_template": "Is this change test or validation code only?",
    },
    "review-read-only": {
        "name": "Review / Read-Only",
        "description": "Code review, audit, or inspection without making changes",
        "acceptance_criteria": [
            "No source code modifications",
            "Documentation or process review only",
            "Read-only inspection or analysis",
        ],
        "question_template": "Is this a read-only review or inspection?",
    },
    "integration": {
        "name": "Integration",
        "description": "Integration testing, multi-component interaction, end-to-end validation",
        "acceptance_criteria": [
            "Tests multiple components or systems",
            "Validates integration points",
            "Includes end-to-end or contract testing",
        ],
        "question_template": "Does this cover integration testing across components?",
    },
}


def module(name: str, filename: str) -> Any:
    spec = importlib.util.spec_from_file_location(name, ROOT / "scripts" / filename)
    loaded = importlib.util.module_from_spec(spec)
    assert spec and spec.loader
    spec.loader.exec_module(loaded)
    return loaded


LOCK = module("aidlc_question_lock", "planning_lock.py")
LEDGER = module("aidlc_question_ledger", "run-ledger.py")
OFFICIAL = module("aidlc_question_official", "official-aidlc-requirements.py")


# Phase 2.5: Task profile detection and routing
def detect_task_profile(task_metadata: dict[str, Any] | None) -> str:
    """Detect task profile from metadata. Returns profile key or raises ValueError for unknown profile."""
    if not task_metadata:
        return "existing-code-change"  # default profile
    
    profile = task_metadata.get("profile", "existing-code-change")
    if profile not in TASK_PROFILES:
        raise ValueError(f"unknown task profile `{profile}`; supported profiles: {', '.join(sorted(TASK_PROFILES.keys()))}")
    return profile


def get_profile_questions(profile: str) -> list[dict[str, Any]]:
    """Generate profile-specific questions and acceptance criteria."""
    if profile not in TASK_PROFILES:
        raise ValueError(f"unknown task profile `{profile}`")
    
    prof = TASK_PROFILES[profile]
    return [
        {
            "id": f"PROFILE-{profile.upper()}-1",
            "question": prof["question_template"],
            "profile": profile,
            "reasoning": f"Confirms this work fits the {prof['name']} category",
            "options": [
                {"id": "yes", "text": f"Yes, this is {prof['name'].lower()}"},
                {"id": "no", "text": f"No, this is a different profile"},
                {"id": "review", "text": "Needs clarification"},
            ],
            "recommended": "yes",
            "acceptance_criteria": prof["acceptance_criteria"],
        }
    ]


def validate_profile_requirements(profile: str, requirements: list[dict[str, Any]]) -> bool:
    """Validate that requirements align with profile acceptance criteria."""
    if profile not in TASK_PROFILES:
        return False
    
    prof = TASK_PROFILES[profile]
    # Check that at least one requirement description mentions profile-relevant keywords
    profile_keywords = {kw.lower() for kw in prof["name"].split() + prof["description"].split()}
    req_text = " ".join(str(r.get("description", "")).lower() for r in requirements)
    
    return any(kw in req_text for kw in profile_keywords) or len(requirements) == 0


def route_to_profile_questions(profile: str) -> dict[str, Any]:
    """Route question planning to profile-specific question generator."""
    prof = TASK_PROFILES.get(profile)
    if not prof:
        raise ValueError(f"unknown task profile `{profile}`")
    
    return {
        "type": "tailtrail-profile-question-route",
        "profile": profile,
        "profile_name": prof["name"],
        "profile_description": prof["description"],
        "acceptance_criteria": prof["acceptance_criteria"],
        "guidance": f"Questions for {prof['name']} profile: {prof['description']}",
    }


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


def list_profiles() -> dict[str, Any]:
    """List all available task profiles."""
    return {
        "type": "tailtrail-task-profiles-list",
        "profiles": {
            name: {
                "name": prof["name"],
                "description": prof["description"],
                "acceptance_criteria": prof["acceptance_criteria"],
            }
            for name, prof in TASK_PROFILES.items()
        },
    }


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    sub = parser.add_subparsers(dest="command", required=True)
    for name in ("show", "clarify", "challenge"):
        item = sub.add_parser(name); item.add_argument("--root", type=Path, default=Path.cwd()); item.add_argument("--run-id", required=True); item.add_argument("--question-id", required=True)
        if name == "challenge": item.add_argument("--reason-code", required=True, choices=sorted(REASON_CODES))
    record_parser = sub.add_parser("record"); record_parser.add_argument("--root", type=Path, default=Path.cwd()); record_parser.add_argument("--run-id", required=True); record_parser.add_argument("--question", required=True)
    approve_parser = sub.add_parser("approve"); approve_parser.add_argument("--root", type=Path, default=Path.cwd()); approve_parser.add_argument("--run-id", required=True); approve_parser.add_argument("--approved", action="store_true")
    
    # Phase 2.5: Task profile commands
    list_profiles_parser = sub.add_parser("list-profiles"); list_profiles_parser.add_argument("--root", type=Path, default=Path.cwd())
    detect_parser = sub.add_parser("detect-profile"); detect_parser.add_argument("--root", type=Path, default=Path.cwd()); detect_parser.add_argument("--task-metadata", required=True)
    route_parser = sub.add_parser("route-profile"); route_parser.add_argument("--root", type=Path, default=Path.cwd()); route_parser.add_argument("--profile", required=True)
    
    args = parser.parse_args()
    try:
        if args.command == "show": payload = show(args.root, args.run_id, args.question_id)
        elif args.command == "clarify": payload = clarify(args.root, args.run_id, args.question_id)
        elif args.command == "challenge": payload = challenge(args.root, args.run_id, args.question_id, args.reason_code)
        elif args.command == "record": payload = record(args.root, args.run_id, args.question)
        elif args.command == "approve": payload = approve(args.root, args.run_id, args.approved)
        elif args.command == "list-profiles": payload = list_profiles()
        elif args.command == "detect-profile":
            task_metadata = json.loads(args.task_metadata)
            profile = detect_task_profile(task_metadata)
            payload = {"type": "tailtrail-profile-detected", "profile": profile, "details": TASK_PROFILES[profile]}
        elif args.command == "route-profile": payload = route_to_profile_questions(args.profile)
        else: payload = approve(args.root, args.run_id, args.approved)
        print(json.dumps(payload, indent=2, sort_keys=True)); return 0
    except (OSError, ValueError, json.JSONDecodeError) as error:
        print(f"AIDLC question control error: {error}"); return 2


if __name__ == "__main__":
    raise SystemExit(main())
