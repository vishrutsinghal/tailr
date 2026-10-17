#!/usr/bin/env python3
"""Ground and validate AIDLC questions without becoming a question authority.

Navigator supplies the proposed requirement boundary and repository-inventory
evidence.  Lite AIDLC may generate local questions; Standard and Full AIDLC
remain owned by the verified official pack and the configured host.  This
module provides the shared context, quality, and traceability contract around
both paths.
"""
from __future__ import annotations

import argparse
import importlib.util
import json
import re
from pathlib import Path
from typing import Any


ROOT = Path(__file__).resolve().parents[1]


def _load_intake_pipeline() -> Any:
    spec = importlib.util.spec_from_file_location("question_orchestrator_intake", ROOT / "scripts" / "intake_pipeline.py")
    if spec is None or spec.loader is None:
        raise RuntimeError("unable to load the approved intake pipeline dependency")
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module.IntakePipeline


class NavigatorIntake:
    """Navigator-owned host exchange boundary backed by the intake pipeline."""

    def __init__(self, root: Path) -> None:
        self.root = root.resolve()
        self._pipeline = _load_intake_pipeline()(self.root)

    def issue_question(
        self,
        run_id: str,
        field_id: str,
        question: dict[str, Any],
        *,
        packet_version: int | None = None,
        idempotency_key: str | None = None,
    ) -> dict[str, Any]:
        text = str(question.get("question", "")).strip()
        if not text:
            raise ValueError("question requires non-empty question text")
        return self._pipeline.issue_question(
            run_id,
            field_id,
            text,
            packet_version=packet_version,
            idempotency_key=idempotency_key,
        )

    def record_observation(
        self,
        run_id: str,
        observation: dict[str, Any],
        *,
        question_id: str | None = None,
        packet_version: int | None = None,
        idempotency_key: str | None = None,
    ) -> dict[str, Any]:
        return self._pipeline.record_observation(
            run_id,
            observation,
            question_id=question_id,
            packet_version=packet_version,
            idempotency_key=idempotency_key,
        )

    def record_direct_answer(
        self,
        run_id: str,
        field_id: str,
        value: Any,
        *,
        question_id: str,
        packet_version: int | None = None,
        idempotency_key: str | None = None,
    ) -> dict[str, Any]:
        return self._pipeline.record_answer(
            run_id,
            field_id,
            value,
            source="direct-question",
            question_id=question_id,
            packet_version=packet_version,
            idempotency_key=idempotency_key,
        )

    def record_narration_answer(
        self,
        run_id: str,
        field_id: str,
        value: Any,
        narration: str,
        *,
        question_id: str | None = None,
        packet_version: int | None = None,
        idempotency_key: str | None = None,
    ) -> dict[str, Any]:
        observation = self.record_observation(
            run_id,
            {"narration": narration},
            question_id=question_id,
            packet_version=packet_version,
            idempotency_key=f"{idempotency_key}:observation" if idempotency_key else None,
        )
        return self._pipeline.record_answer(
            run_id,
            field_id,
            value,
            source="narration-observation",
            question_id=question_id,
            observation_id=observation["payload"]["observation_id"],
            packet_version=packet_version,
            idempotency_key=idempotency_key,
        )


PROFILE_FIELDS: dict[str, tuple[tuple[str, str], ...]] = {
    "documentation-only": (
        ("document-path", "Which document is changing?"),
        ("prose-only", "Are code and configuration changes excluded?"),
    ),
    "existing-code-change": (
        ("expected-behavior", "What observable behavior should change?"),
        ("existing-owner", "Which existing path participates in that behavior?"),
        ("proof-command", "Which existing test and command prove the change?"),
    ),
    "new-feature": (
        ("proposed-owner", "Which proposed implementation path owns the feature?"),
        ("public-route", "Which entry point or caller will use the feature?"),
        ("proof-command", "Which test path and command will prove the feature?"),
    ),
    "configuration-data": (
        ("configuration-path", "Which configuration or data path changes?"),
        ("behavior-surface", "Which behavior consumes the changed value?"),
        ("proof-command", "Which command validates the changed configuration or data?"),
    ),
    "qa-validation-only": (
        ("validation-target", "Which behavior or requirement is being validated?"),
        ("proof-command", "Which command should run for the validation?"),
    ),
    "review-read-only": (
        ("review-scope", "What should be inspected?"),
        ("review-question", "What decision or conclusion is required?"),
    ),
}

ACCEPTANCE_STATES = (
    "received",
    "normalized",
    "mapped-to-profile-field",
    "evidence-checked",
    "accepted",
    "contradicted",
    "insufficient",
    "clarification-required",
    "user-decision-required",
)


class NavigatorHostProtocol:
    """Phase 2's Navigator-owned host-question protocol core.

    This class deliberately keeps the host exchange separate from Planning
    Lock, scope, and proof authorization.  It can collect and evidence-check
    *candidates*, but it never turns a host assertion into operational
    authority.  Later phases own packet finalization and the authorization
    projection.
    """

    max_clarification_rounds = 5
    max_questions_per_round = 3

    def __init__(self, intake: NavigatorIntake) -> None:
        self.intake = intake
        self._issued_fields: dict[str, str] = {}
        self._clarification_rounds: dict[str, int] = {}

    @staticmethod
    def profile_task(
        goal: str,
        *,
        task_type: str = "",
        change_intent: str = "",
        paths: list[str] | None = None,
        request_mode: str = "implementation",
    ) -> dict[str, str]:
        """Choose one bounded profile from explicit facts before judgment."""
        normalized_paths = [str(path).lower() for path in (paths or [])]
        kinds = {Path(path).suffix for path in normalized_paths}
        text = f"{goal} {task_type} {change_intent}".lower()
        if request_mode == "read-only" or task_type.lower() == "review":
            return {"profile": "review-read-only", "reason": "declared read-only or review task", "confidence": "declared"}
        if normalized_paths and kinds <= {".md", ".rst", ".txt", ".adoc"}:
            return {"profile": "documentation-only", "reason": "named paths are documentation", "confidence": "path-kind"}
        if normalized_paths and kinds <= {".json", ".yaml", ".yml", ".toml", ".ini", ".cfg", ".csv"}:
            return {"profile": "configuration-data", "reason": "named paths are configuration or data", "confidence": "path-kind"}
        if task_type.lower() in {"qa", "validation"} or "validation-only" in text:
            return {"profile": "qa-validation-only", "reason": "declared QA or validation task", "confidence": "declared"}
        if change_intent.lower() in {"new", "new-feature", "new capability"} or any(word in text for word in ("create", "new feature", "add feature")):
            return {"profile": "new-feature", "reason": "declared or explicit new-capability intent", "confidence": "declared"}
        return {"profile": "existing-code-change", "reason": "default implementation change profile", "confidence": "judgment"}

    @staticmethod
    def profile_fields(profile: str) -> list[dict[str, str]]:
        try:
            fields = PROFILE_FIELDS[profile]
        except KeyError as error:
            raise ValueError(f"unsupported Navigator profile `{profile}`") from error
        return [{"field_id": field_id, "question": question} for field_id, question in fields]

    def plan_questions(
        self,
        profile: str,
        *,
        answered_fields: set[str] | None = None,
    ) -> list[dict[str, str]]:
        """Plan at most one small question batch without allocating IDs."""
        answered = answered_fields or set()
        return [
            field for field in self.profile_fields(profile)
            if field["field_id"] not in answered
        ][:self.max_questions_per_round]

    def issue_profile_questions(
        self,
        run_id: str,
        profile: str,
        *,
        answered_fields: set[str] | None = None,
        packet_version: int | None = None,
    ) -> list[dict[str, str]]:
        """Issue planned questions through Phase 1A and retain ID-to-field lineage."""
        issued: list[dict[str, str]] = []
        for field in self.plan_questions(profile, answered_fields=answered_fields):
            event = self.intake.issue_question(
                run_id,
                field["field_id"],
                {"question": field["question"]},
                packet_version=packet_version,
            )
            question_id = str(event["payload"]["question_id"])
            self._issued_fields[question_id] = field["field_id"]
            issued.append({**field, "question_id": question_id})
        return issued

    @staticmethod
    def _candidate(
        field_id: str,
        value: Any,
        *,
        source: str,
        question_id: str | None,
        observation_id: str | None,
    ) -> dict[str, Any]:
        if not field_id.strip():
            raise ValueError("candidate answer requires a profile field")
        normalized = " ".join(value.split()) if isinstance(value, str) else value
        if normalized in (None, ""):
            raise ValueError("candidate answer requires a value")
        return {
            "field_id": field_id,
            "value": normalized,
            "source": source,
            "question_id": question_id,
            "observation_id": observation_id,
            "state": "mapped-to-profile-field",
            "state_history": ["received", "normalized", "mapped-to-profile-field"],
            "authority_granted": False,
            "finalization_allowed": False,
        }

    def record_direct_candidate(
        self,
        run_id: str,
        question_id: str,
        value: Any,
        *,
        packet_version: int | None = None,
    ) -> dict[str, Any]:
        """Record a direct response as a candidate; caller status is ignored."""
        field_id = self._issued_fields.get(question_id)
        if field_id is None:
            raise ValueError("direct response references an unknown Navigator question")
        self.intake.record_direct_answer(
            run_id, field_id, value, question_id=question_id, packet_version=packet_version
        )
        return self._candidate(field_id, value, source="direct-question", question_id=question_id, observation_id=None)

    def ingest_narration(
        self,
        run_id: str,
        profile: str,
        narration: str,
        candidates: list[dict[str, Any]],
        *,
        packet_version: int | None = None,
    ) -> dict[str, Any]:
        """Persist narration once as an observation batch, never as accepted answers."""
        if not narration.strip():
            raise ValueError("narration must be non-empty")
        allowed = {row["field_id"] for row in self.profile_fields(profile)}
        mapped: list[dict[str, Any]] = []
        for row in candidates:
            field_id = str(row.get("field_id", "")).strip()
            if field_id not in allowed:
                raise ValueError(f"candidate field `{field_id}` is not part of profile `{profile}`")
            mapped.append({"field_id": field_id, "value": row.get("value")})
        event = self.intake.record_observation(
            run_id,
            {"narration": narration, "candidate_fields": [row["field_id"] for row in mapped]},
            packet_version=packet_version,
        )
        observation_id = str(event["payload"]["observation_id"])
        return {
            "observation": event["payload"],
            "candidates": [
                self._candidate(row["field_id"], row["value"], source="narration", question_id=None, observation_id=observation_id)
                for row in mapped
            ],
        }

    @staticmethod
    def evidence_check(candidate: dict[str, Any], evidence: dict[str, Any]) -> dict[str, Any]:
        """Advance a candidate only from Navigator-owned evidence, never host status."""
        if candidate.get("state") != "mapped-to-profile-field":
            raise ValueError("candidate must be mapped to a profile field before evidence checking")
        outcome = str(evidence.get("outcome", "insufficient"))
        verified_by = str(evidence.get("verified_by", ""))
        if outcome not in {"accepted", "contradicted", "insufficient"}:
            raise ValueError("evidence outcome must be accepted, contradicted, or insufficient")
        if outcome == "accepted" and verified_by != "navigator":
            outcome = "insufficient"
        state = outcome if outcome != "insufficient" else "clarification-required"
        return {
            **candidate,
            "state": state,
            "state_history": [*candidate["state_history"], "evidence-checked", outcome, *( ["clarification-required"] if outcome == "insufficient" else [] )],
            "evidence": dict(evidence),
            "authority_granted": False,
            "finalization_allowed": False,
        }

    def clarification_route(
        self,
        run_id: str,
        profile: str,
        unresolved_fields: set[str],
    ) -> dict[str, Any]:
        """Bound clarification and make a dead end an explicit user decision."""
        round_number = self._clarification_rounds.get(run_id, 0) + 1
        if round_number > self.max_clarification_rounds:
            return {
                "state": "user-decision-required",
                "reason": "clarification-round-limit-reached",
                "unresolved_fields": sorted(unresolved_fields),
                "authority_granted": False,
            }
        self._clarification_rounds[run_id] = round_number
        questions = [
            row for row in self.plan_questions(profile)
            if row["field_id"] in unresolved_fields
        ]
        if not questions:
            return {
                "state": "user-decision-required",
                "reason": "no-bounded-question-can-resolve-the-gap",
                "unresolved_fields": sorted(unresolved_fields),
                "authority_granted": False,
            }
        return {
            "state": "awaiting-clarification",
            "round": round_number,
            "questions": questions[:self.max_questions_per_round],
            "authority_granted": False,
        }


DECISION_CLASSES = {
    "user-decision",
    "policy-decision",
    "architecture-decision",
    "evidence-decision",
    "extension-opt-in",
}
STOP_WORDS = {
    "a", "an", "and", "are", "as", "at", "be", "before", "by", "for",
    "from", "how", "in", "is", "it", "must", "of", "on", "or", "the",
    "this", "to", "what", "when", "which", "with",
}
ASSERTED_REPOSITORY_FACT = re.compile(
    r"\b(?:repository|current|existing|already)\b.{0,48}"
    r"\b(?:contains|defines|fields?|installed|limits?|status|structured|uses?)\b",
    re.IGNORECASE,
)


def _has_ungrounded_repository_assertion(value: str) -> bool:
    """Distinguish claimed repository facts from explicitly conditional advice."""
    for sentence in re.split(r"(?<=[.!?])\s+", value):
        lowered = sentence.lower()
        if not ASSERTED_REPOSITORY_FACT.search(sentence):
            continue
        if any(marker in lowered for marker in (" if ", " when ", " unless ", " where available", " where possible")):
            continue
        return True
    return False


def _requirement_id(row: dict[str, Any], index: int) -> str:
    return str(row.get("display_id") or row.get("id") or f"REQ-{index:02d}").strip()


def _tokens(value: str) -> set[str]:
    return {
        token for token in re.findall(r"[a-z0-9][a-z0-9_-]+", value.lower())
        if token not in STOP_WORDS and len(token) > 2
    }


def _unknowns(goal: str, requirements: list[dict[str, Any]]) -> list[dict[str, Any]]:
    text = " ".join([goal, *(str(row.get("statement", "")) for row in requirements)]).lower()
    candidates = (
        ("normalization", ("normaliz", "canonical"), ["public-behavior", "data-contract"]),
        ("rejection-contract", ("reject", "invalid", "error"), ["public-behavior", "compatibility"]),
        ("backward-compatibility", ("backward", "compatib", "preserve"), ["compatibility", "migration"]),
        ("architecture-ownership", ("api", "service", "caller", "boundary"), ["architecture", "scope"]),
        ("evidence", ("evidence", "test", "proof", "validation"), ["completion", "testing"]),
        ("privacy", ("personal", "address", "pii", "privacy"), ["privacy", "error-contract"]),
        ("release", ("rollout", "rollback", "production", "release"), ["release", "recovery"]),
    )
    return [
        {"topic": topic, "classification": "user-decision", "decision_impact": impact}
        for topic, markers, impact in candidates if any(marker in text for marker in markers)
    ]


def prepare_context(
    run_id: str,
    mode: str,
    goal: str,
    requirements: list[dict[str, Any]],
    start_report: dict[str, Any] | None = None,
) -> dict[str, Any]:
    """Build a compact question input contract from saved planning evidence.

    This function does not read source bodies.  Paths and roles are hypotheses
    from Navigator's saved inventory until a separately approved investigation
    or implementation-stage inspection confirms them.
    """
    report = start_report or {}
    navigator = report.get("navigator", {}) if isinstance(report, dict) else {}
    architecture = report.get("architecture_plan", {}) if isinstance(report, dict) else {}
    validation = report.get("focused_validation_plan", {}) if isinstance(report, dict) else {}
    requirement_rows = [
        {
            "requirement_id": _requirement_id(row, index),
            "statement": str(row.get("statement", "")).strip(),
            "kind": str(row.get("kind", "change")).strip() or "change",
        }
        for index, row in enumerate(requirements, start=1)
    ]
    known_facts: list[dict[str, Any]] = []
    for row in requirement_rows:
        known_facts.append({
            "fact_id": f"USER-{row['requirement_id']}",
            "fact": row["statement"],
            "evidence": f"user-requirement:{row['requirement_id']}",
            "confidence": "user-stated",
        })
    scope_rows = architecture.get("scope_roles", []) if isinstance(architecture, dict) else []
    if not scope_rows and isinstance(navigator, dict):
        scope_rows = navigator.get("likely_impacted_files", [])
    for index, item in enumerate(scope_rows or [], start=1):
        if not isinstance(item, dict) or not str(item.get("path", "")).strip():
            continue
        path = str(item["path"]).strip()
        role = str(item.get("role") or item.get("reason") or "planning candidate").strip()
        known_facts.append({
            "fact_id": f"INV-{index:02d}",
            "fact": f"Repository inventory identified `{path}` as {role}.",
            "evidence": path,
            "confidence": "repository-inventory-hypothesis",
        })
    tiers = validation.get("tiers", []) if isinstance(validation, dict) else []
    if isinstance(tiers, list) and tiers:
        known_facts.append({
            "fact_id": "PLAN-EVIDENCE-01",
            "fact": "Navigator selected candidate validation tiers: " + ", ".join(str(tier) for tier in tiers) + ".",
            "evidence": "saved-start-report:focused_validation_plan",
            "confidence": "planning-hypothesis",
        })
    return {
        "schema_version": "1",
        "type": "tailtrail-question-context",
        "run_id": run_id,
        "aidlc_mode": mode,
        "question_authority": "local-lite" if mode == "lite" else "official-ai-dlc-pack",
        "goal": goal,
        "requirements": requirement_rows,
        "known_facts": known_facts,
        "unknowns": _unknowns(goal, requirements),
        "question_policy": {
            "ask_only_material_decisions": True,
            "repository_answerable_items_require_discovery": True,
            "official_authority_preserved": mode in {"standard", "full"},
            "source_bodies_read": False,
            "boundary": "Use saved user wording and repository inventory only. Do not present an inventory hypothesis as confirmed source behavior.",
        },
    }


def _decision_class(question: str) -> str:
    lowered = question.lower()
    if "extension" in lowered or "baseline" in lowered:
        return "extension-opt-in"
    if any(word in lowered for word in ("proof", "evidence", "test")):
        return "evidence-decision"
    if any(word in lowered for word in ("component", "boundary", "own", "api", "service")):
        return "architecture-decision"
    if any(word in lowered for word in ("policy", "privacy", "security", "retain", "log")):
        return "policy-decision"
    return "user-decision"


def _decision_impact(decision_class: str) -> list[str]:
    return {
        "extension-opt-in": ["lifecycle-rules", "validation"],
        "evidence-decision": ["completion", "testing"],
        "architecture-decision": ["architecture", "scope"],
        "policy-decision": ["policy", "safeguards"],
        "user-decision": ["acceptance-criteria", "public-behavior"],
    }[decision_class]


def _mapped_requirements(question: dict[str, Any], context: dict[str, Any]) -> tuple[list[str], bool]:
    valid = {str(row["requirement_id"]) for row in context.get("requirements", [])}
    supplied = [str(value) for value in question.get("requirement_ids", []) if str(value).strip()]
    if supplied:
        unknown = sorted(set(supplied) - valid)
        if unknown:
            raise ValueError(f"{question.get('id', '<question>')} references unknown requirements: {', '.join(unknown)}")
        return list(dict.fromkeys(supplied)), False
    question_tokens = _tokens(" ".join((str(question.get("question", "")), str(question.get("reasoning", "")))))
    scored = []
    for row in context.get("requirements", []):
        score = len(question_tokens & _tokens(str(row.get("statement", ""))))
        if score:
            scored.append((score, str(row["requirement_id"])))
    if scored:
        best = max(score for score, _ in scored)
        return [identifier for score, identifier in scored if score == best], True
    return sorted(valid), True


def _relevant_facts(question: dict[str, Any], context: dict[str, Any]) -> list[dict[str, Any]]:
    question_tokens = _tokens(" ".join((
        str(question.get("question", "")),
        str(question.get("recommended", "")),
        str(question.get("reasoning", "")),
    )))
    ranked = []
    for fact in context.get("known_facts", []):
        score = len(question_tokens & _tokens(str(fact.get("fact", ""))))
        if score:
            ranked.append((score, fact))
    return [fact for _, fact in sorted(ranked, key=lambda item: (-item[0], str(item[1].get("fact_id", ""))))[:3]]


def evaluate_questions(
    questions: list[dict[str, Any]],
    context: dict[str, Any],
    authority: str,
) -> dict[str, Any]:
    """Enrich questions with traceability and enforce deterministic quality rules."""
    if not isinstance(questions, list) or not questions:
        raise ValueError("question orchestrator requires a non-empty question list")
    errors: list[str] = []
    warnings: list[str] = []
    seen_questions: set[str] = set()
    enriched: list[dict[str, Any]] = []
    traceability: list[dict[str, Any]] = []
    for item in questions:
        identifier = str(item.get("id", "")).strip()
        text = str(item.get("question", "")).strip()
        normalized_text = " ".join(re.findall(r"[a-z0-9]+", text.lower()))
        if normalized_text in seen_questions:
            errors.append(f"{identifier}: duplicates another question")
        seen_questions.add(normalized_text)
        options = item.get("options", [])
        option_text = [" ".join(str(option.get("text", "")).lower().split()) for option in options if isinstance(option, dict)]
        if len(option_text) != len(set(option_text)):
            errors.append(f"{identifier}: contains duplicate options")
        requirement_ids, inferred = _mapped_requirements(item, context)
        if inferred:
            warnings.append(f"{identifier}: requirement mapping was inferred; the active authority should provide it explicitly")
        decision_class = str(item.get("decision_class", "")).strip() or _decision_class(text)
        if decision_class not in DECISION_CLASSES:
            errors.append(f"{identifier}: unsupported decision_class `{decision_class}`")
        impacts = [str(value) for value in item.get("decision_impact", []) if str(value).strip()] or _decision_impact(decision_class)
        facts = _relevant_facts(item, context)
        known_context = [str(value) for value in item.get("known_context", []) if str(value).strip()] or [str(fact["fact"]) for fact in facts]
        evidence_refs = [str(value) for value in item.get("evidence_refs", []) if str(value).strip()] or [str(fact["evidence"]) for fact in facts]
        recommendation_claim = " ".join((
            str(item.get("recommended", "")),
            str(item.get("reasoning", "")),
        ))
        if _has_ungrounded_repository_assertion(recommendation_claim) and not item.get("evidence_refs"):
            errors.append(f"{identifier}: repository-specific recommendation needs explicit evidence_refs")
        enriched_item = {
            **item,
            "authority": authority,
            "requirement_ids": requirement_ids,
            "decision_class": decision_class,
            "decision_impact": impacts,
            "known_context": known_context,
            "evidence_refs": evidence_refs,
        }
        enriched.append(enriched_item)
        traceability.append({
            "question_id": identifier,
            "requirement_ids": requirement_ids,
            "decision_class": decision_class,
            "decision_impact": impacts,
            "evidence_refs": evidence_refs,
        })
    if errors:
        raise ValueError("question quality gate failed: " + "; ".join(errors))
    return {
        "questions": enriched,
        "quality": {
            "status": "passed",
            "authority": authority,
            "question_count": len(enriched),
            "warnings": warnings,
            "checks": [
                "unique questions and options",
                "valid requirement mapping",
                "material decision classification",
                "decision-impact traceability",
                "repository-claim grounding",
            ],
        },
        "traceability": traceability,
    }


def show(root: Path, run_id: str) -> dict[str, Any]:
    root = root.resolve()
    planning = root / ".tailtrail" / "runs" / run_id / "planning"
    candidates = sorted(
        planning.glob("question-context-v*.json"),
        key=lambda item: int(item.stem.rsplit("v", 1)[-1]),
    )
    if not candidates:
        raise ValueError(f"question context for run `{run_id}` does not exist")
    path = candidates[-1]
    payload = json.loads(path.read_text(encoding="utf-8"))
    if payload.get("type") != "tailtrail-question-context" or payload.get("run_id") != run_id:
        raise ValueError(f"question context for run `{run_id}` is invalid")
    return {**payload, "artifact": path.relative_to(root).as_posix()}


def main() -> int:
    parser = argparse.ArgumentParser(description="Inspect TailTrail's saved AIDLC Question Orchestrator context.")
    sub = parser.add_subparsers(dest="command", required=True)
    show_parser = sub.add_parser("show")
    show_parser.add_argument("--root", type=Path, default=Path.cwd())
    show_parser.add_argument("--run-id", required=True)
    args = parser.parse_args()
    try:
        payload = show(args.root, args.run_id)
    except ValueError as error:
        parser.error(str(error))
    print(json.dumps(payload, indent=2, sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
