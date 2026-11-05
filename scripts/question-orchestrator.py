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
import hashlib
import importlib.util
import json
import os
import re
import shlex
import tempfile
from pathlib import Path
from typing import Any


ROOT = Path(__file__).resolve().parents[1]


def _load_host_contract() -> Any:
    spec = importlib.util.spec_from_file_location(
        "tailtrail_navigator_intake_host_contract", ROOT / "scripts" / "host_contract.py"
    )
    if spec is None or spec.loader is None:
        raise RuntimeError("unable to load the host-input contract validator")
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


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


_PUBLIC_PROFILE_MAP = {
    "documentation-only": "documentation-only",
    "existing-code change": "existing-code-change",
    "new feature": "new-feature",
    "greenfield-new-project": "new-feature",
    "configuration/data": "configuration-data",
    "QA/validation-only": "qa-validation-only",
    "review/read-only": "review-read-only",
}
_PATH_FIELDS = {
    "document-path",
    "existing-owner",
    "proposed-owner",
    "configuration-path",
}


def _public_mandatory_fields(profile: str, path_projection: dict[str, Any]) -> list[dict[str, Any]]:
    fields: list[dict[str, Any]] = [dict(row) for row in NavigatorHostProtocol.profile_fields(profile)]
    for index, row in enumerate(path_projection.get("paths", []), start=1):
        if row.get("operational_role") == "proof-only":
            fields.append({
                "field_id": f"proof-adequacy-{index:03d}",
                "question": (
                    f"Classify proof `{row['path']}` as unchanged-proof, editable-proof, or new-proof; "
                    "provide its test cases, fixtures, assertions, and baseline command/result as JSON."
                ),
                "kind": "proof-adequacy",
                "expected_path": row["path"],
                "host_role": row["host_role"],
                "operational_role": row["operational_role"],
            })
            continue
        if row.get("operational_role") not in {
            "inspection-input", "configuration-output", "generated-output", "excluded", "external",
        }:
            continue
        fields.append({
            "field_id": f"declared-path-{index:03d}",
            "question": (
                f"Confirm the host-declared `{row['host_role']}` path `{row['path']}` "
                "and provide repository evidence for that classification."
            ),
            "kind": "declared-path-role",
            "expected_value": row["path"],
            "host_role": row["host_role"],
            "operational_role": row["operational_role"],
        })
    return fields


def _request_mandatory_fields(request: dict[str, Any]) -> list[dict[str, Any]]:
    saved = request.get("mandatory_fields")
    if isinstance(saved, list) and saved and all(isinstance(row, dict) for row in saved):
        return [dict(row) for row in saved]
    return [dict(row) for row in NavigatorHostProtocol.profile_fields(str(request["profile"]))]


def _canonical(value: Any) -> str:
    return json.dumps(value, sort_keys=True, separators=(",", ":"))


def _fingerprint(path: Path) -> str:
    return "sha256:" + hashlib.sha256(path.read_bytes()).hexdigest()


def _value_fingerprint(value: Any) -> str:
    return "sha256:" + hashlib.sha256(_canonical(value).encode("utf-8")).hexdigest()


_PROOF_ADEQUACY_ROLES = frozenset({"unchanged-proof", "editable-proof", "new-proof"})
_PROOF_BASELINE_OUTCOMES = frozenset({"pass", "fail", "not-run"})


def _parse_proof_adequacy(value: Any, *, expected_path: str, host_role: str, command: str) -> dict[str, Any]:
    """Validate a host finding about whether one proof path must change.

    The finding remains non-authoritative until Navigator validates it against
    the declared proof path and its source evidence.  This contract prevents a
    test that needs fixture or assertion changes from being silently rendered
    as run-only proof.
    """
    try:
        payload = json.loads(value) if isinstance(value, str) else value
    except json.JSONDecodeError as error:
        raise ValueError("proof-adequacy answer must be a JSON object") from error
    if not isinstance(payload, dict):
        raise ValueError("proof-adequacy answer must be a JSON object")
    required = {"path", "role", "test_cases", "fixtures", "assertions", "baseline"}
    if set(payload) != required:
        raise ValueError("proof-adequacy answer must contain exactly path, role, test_cases, fixtures, assertions, and baseline")
    path = str(payload.get("path", "")).replace("\\", "/").strip()
    role = str(payload.get("role", "")).strip()
    if path != expected_path:
        raise ValueError(f"proof-adequacy answer must target declared proof path `{expected_path}`")
    if role not in _PROOF_ADEQUACY_ROLES:
        raise ValueError("proof-adequacy role must be unchanged-proof, editable-proof, or new-proof")
    if host_role == "existing-proof-path" and role == "new-proof":
        raise ValueError("an existing proof path cannot be classified as new-proof")
    if host_role == "proposed-proof-path" and role != "new-proof":
        raise ValueError("a proposed proof path must be classified as new-proof")
    normalized_lists: dict[str, list[str]] = {}
    for key in ("test_cases", "fixtures", "assertions"):
        rows = payload.get(key)
        if not isinstance(rows, list) or not rows or any(not isinstance(item, str) or not item.strip() for item in rows):
            raise ValueError(f"proof-adequacy {key} must be a non-empty string array")
        normalized_lists[key] = list(dict.fromkeys(item.strip() for item in rows))
    baseline = payload.get("baseline")
    if not isinstance(baseline, dict) or set(baseline) != {"command", "outcome", "observed"}:
        raise ValueError("proof-adequacy baseline must contain exactly command, outcome, and observed")
    baseline_command = str(baseline.get("command", "")).strip()
    outcome = str(baseline.get("outcome", "")).strip()
    observed = str(baseline.get("observed", "")).strip()
    if baseline_command != command:
        raise ValueError("proof-adequacy baseline command must equal the declared proof command")
    if outcome not in _PROOF_BASELINE_OUTCOMES or not observed:
        raise ValueError("proof-adequacy baseline requires pass, fail, or not-run plus an observed result")
    if role == "unchanged-proof" and outcome != "pass":
        raise ValueError("unchanged-proof requires a passing baseline result")
    if role == "new-proof" and outcome != "not-run":
        raise ValueError("new-proof requires a not-run baseline result")
    return {
        "schema_version": "1",
        "path": path,
        "role": role,
        **normalized_lists,
        "baseline": {"command": baseline_command, "outcome": outcome, "observed": observed},
    }


def _atomic_json(path: Path, value: Any) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with tempfile.NamedTemporaryFile("w", encoding="utf-8", dir=path.parent, delete=False) as handle:
        json.dump(value, handle, indent=2, sort_keys=True)
        handle.write("\n")
        temporary = Path(handle.name)
    os.replace(temporary, path)


def _public_run_root(root: Path, run_id: str) -> Path:
    if not re.fullmatch(r"run-[a-f0-9]{16}", run_id):
        raise ValueError("run ID must be an exact Navigator intake identifier")
    return root.resolve() / ".tailtrail" / "intake" / run_id


def _public_request_path(root: Path, run_id: str) -> Path:
    return _public_run_root(root, run_id) / "public-request.json"


def _load_public_request(root: Path, run_id: str) -> dict[str, Any]:
    path = _public_request_path(root, run_id)
    if not path.is_file():
        raise ValueError(f"public Navigator intake request for `{run_id}` does not exist")
    value = json.loads(path.read_text(encoding="utf-8"))
    if not isinstance(value, dict) or value.get("run_id") != run_id:
        raise ValueError(f"public Navigator intake request for `{run_id}` is invalid")
    fingerprint = value.get("fingerprint")
    unsigned = {key: item for key, item in value.items() if key != "fingerprint"}
    if fingerprint != _value_fingerprint(unsigned):
        raise ValueError(f"public Navigator intake request for `{run_id}` failed its integrity check")
    return value


def _answer_events(root: Path, run_id: str) -> dict[str, dict[str, Any]]:
    path = _public_run_root(root, run_id) / "events.jsonl"
    if not path.is_file():
        return {}
    events = [json.loads(line) for line in path.read_text(encoding="utf-8").splitlines() if line.strip()]
    return {
        str(event.get("payload", {}).get("answer_id")): event.get("payload", {})
        for event in events
        if event.get("event_type") == "answer-recorded"
    }


def _question_events(root: Path, run_id: str) -> dict[str, dict[str, Any]]:
    path = _public_run_root(root, run_id) / "events.jsonl"
    if not path.is_file():
        return {}
    events = [json.loads(line) for line in path.read_text(encoding="utf-8").splitlines() if line.strip()]
    return {
        str(event.get("payload", {}).get("question_id")): event.get("payload", {})
        for event in events
        if event.get("event_type") == "question-issued"
    }


def _command_runs_path(command: str, path: str) -> bool:
    module = path.removesuffix(".py").replace("/", ".")
    return path in command or re.search(rf"(?<![\w.]){re.escape(module)}(?![\w.])", command) is not None


def _shell_join(parts: list[str]) -> str:
    if os.name == "nt":
        import subprocess

        return subprocess.list2cmdline(parts)
    return " ".join(shlex.quote(part) for part in parts)


def public_intake_open(
    root: Path,
    goal: str,
    raw_host_contract: dict[str, Any],
    *,
    host: str | None = None,
    aidlc: str | None = None,
) -> dict[str, Any]:
    """Open the supported pre-Start Navigator questionnaire."""
    root = root.resolve()
    validated_result = _load_host_contract().validate(raw_host_contract, root=root, goal=goal)
    if validated_result.get("state") != "accepted":
        details = validated_result.get("open_fields") or validated_result.get("conflicts") or ["unknown contract gap"]
        raise ValueError("host-input contract is not accepted: " + "; ".join(str(item) for item in details))
    validated = validated_result["validated"]
    if validated.get("request_mode") != "implementation":
        raise ValueError("planning-readiness intake is only for implementation host contracts")
    profile = _PUBLIC_PROFILE_MAP.get(str(validated.get("profile")))
    if profile is None:
        raise ValueError(f"unsupported public Navigator intake profile `{validated.get('profile')}`")
    host_contract_module = _load_host_contract()
    path_projection = host_contract_module.operational_path_projection(validated, root=root)
    mandatory_fields = _public_mandatory_fields(profile, path_projection)
    pipeline = _load_intake_pipeline()(root)
    created = pipeline.create_run(goal, profile)
    questions = []
    for row in mandatory_fields:
        event = pipeline.issue_question(created["run_id"], row["field_id"], row["question"])
        questions.append({**row, "question_id": event["payload"]["question_id"]})
    request = {
        "schema_version": "1",
        "type": "tailtrail-public-navigator-intake-request",
        "run_id": created["run_id"],
        "goal": goal,
        "profile": profile,
        "host": host,
        "aidlc": aidlc,
        "host_contract": validated,
        "host_contract_fingerprint": validated["fingerprint"],
        "path_role_projection": path_projection,
        "mandatory_fields": mandatory_fields,
    }
    request["fingerprint"] = _value_fingerprint(request)
    _atomic_json(_public_request_path(root, created["run_id"]), request)
    return {
        "schema_version": "1",
        "type": "tailtrail-public-navigator-intake",
        "status": "awaiting-candidate-answers",
        "run_id": created["run_id"],
        "profile": profile,
        "mandatory_questions": questions,
        "completeness": {"required": len(questions), "accepted": 0, "missing": [row["field_id"] for row in questions]},
        "authority": "Questions and candidates grant no Planning Lock or implementation authority.",
    }


def public_intake_record(root: Path, run_id: str, answers: list[dict[str, Any]]) -> dict[str, Any]:
    """Persist host findings as candidates, never accepted facts."""
    if not isinstance(answers, list) or not answers:
        raise ValueError("candidate answers must be a non-empty list")
    root = root.resolve()
    _load_public_request(root, run_id)
    questions = _question_events(root, run_id)
    pipeline = _load_intake_pipeline()(root)
    recorded = []
    seen: set[str] = set()
    for index, row in enumerate(answers, start=1):
        if not isinstance(row, dict):
            raise ValueError(f"candidate answer {index} must be an object")
        question_id = str(row.get("question_id", "")).strip()
        question = questions.get(question_id)
        if question is None or question_id in seen:
            raise ValueError(f"candidate answer {index} references an unknown or duplicate question")
        seen.add(question_id)
        value = row.get("value")
        if not isinstance(value, str) or not value.strip():
            raise ValueError(f"candidate answer {index} requires a non-empty string value")
        event = pipeline.record_answer(
            run_id,
            str(question["field_id"]),
            value.strip(),
            source="direct-question",
            question_id=question_id,
        )
        recorded.append({
            "answer_id": event["payload"]["answer_id"],
            "question_id": question_id,
            "field_id": question["field_id"],
            "state": "candidate",
        })
    return {
        "type": "tailtrail-public-navigator-candidates",
        "status": "candidates-recorded",
        "run_id": run_id,
        "candidates": recorded,
        "authority_granted": False,
        "next_action": f"Validate these candidates with `tailtrail navigator intake validate --run-id {run_id} --evidence-file <file>`.",
    }


def public_intake_validate(root: Path, run_id: str, validations: list[dict[str, Any]]) -> dict[str, Any]:
    """Validate candidates against repository files before accepting them."""
    if not isinstance(validations, list) or not validations:
        raise ValueError("candidate validations must be a non-empty list")
    root = root.resolve()
    request = _load_public_request(root, run_id)
    pipeline = _load_intake_pipeline()(root)
    answers = _answer_events(root, run_id)
    states = {str(row.get("answer_id")): row for row in pipeline.replay(run_id).get("answer_states", [])}
    accepted = []
    seen: set[str] = set()
    for index, row in enumerate(validations, start=1):
        if not isinstance(row, dict):
            raise ValueError(f"candidate validation {index} must be an object")
        answer_id = str(row.get("answer_id", "")).strip()
        answer = answers.get(answer_id)
        if answer is None or answer_id in seen:
            raise ValueError(f"candidate validation {index} references an unknown or duplicate answer")
        seen.add(answer_id)
        if states.get(answer_id, {}).get("state") != "candidate":
            raise ValueError(f"answer `{answer_id}` is not an unvalidated candidate")
        field_id = str(answer.get("field_id", ""))
        mandatory = {str(item["field_id"]): item for item in _request_mandatory_fields(request)}
        allowed = set(mandatory)
        if field_id not in allowed:
            raise ValueError(f"answer `{answer_id}` is outside the active profile registry")
        evidence_paths = row.get("evidence_paths")
        if not isinstance(evidence_paths, list) or not evidence_paths:
            raise ValueError(f"answer `{answer_id}` requires repository evidence paths")
        refs = []
        for evidence_path in evidence_paths:
            relative = str(evidence_path).strip().replace("\\", "/")
            relative_path = Path(relative)
            target = (root / relative_path).resolve()
            managed = relative_path.parts[:1] in ((".tailtrail",), ("tailtrail-meta",), (".git",))
            try:
                target.relative_to(root)
                inside_root = True
            except ValueError:
                inside_root = False
            if (
                not relative
                or relative_path.is_absolute()
                or ".." in relative_path.parts
                or managed
                or not inside_root
                or not target.is_file()
            ):
                raise ValueError(f"answer `{answer_id}` has an invalid evidence path `{relative}`")
            refs.append({"path": relative, "content_fingerprint": _fingerprint(target)})
        raw_value = str(answer.get("value", "")).strip()
        value = raw_value.replace("\\", "/")
        field_contract = mandatory[field_id]
        if field_contract.get("kind") == "declared-path-role":
            if value != field_contract.get("expected_value"):
                raise ValueError(
                    f"answer `{answer_id}` must confirm declared path `{field_contract.get('expected_value')}` exactly"
                )
        if field_id in _PATH_FIELDS:
            if Path(value).is_absolute() or ".." in Path(value).parts:
                raise ValueError(f"answer `{answer_id}` must use a repository-relative path")
            if field_id != "proposed-owner" and not (root / value).exists():
                raise ValueError(f"answer `{answer_id}` names a missing existing path `{value}`")
        if field_id == "proof-command":
            declared_proofs = [
                str(item.get("path", ""))
                for item in request["host_contract"].get("paths", [])
                if item.get("role") in {"existing-proof-path", "proposed-proof-path"}
            ]
            if not declared_proofs or not any(_command_runs_path(value, path) for path in declared_proofs):
                raise ValueError(f"answer `{answer_id}` proof command does not run a declared proof path")
        if field_contract.get("kind") == "proof-adequacy":
            adequacy = _parse_proof_adequacy(
                raw_value,
                expected_path=str(field_contract.get("expected_path", "")),
                host_role=str(field_contract.get("host_role", "")),
                command=str(request["host_contract"].get("proof", {}).get("command", "")),
            )
            if adequacy["role"] != "new-proof" and adequacy["path"] not in {ref["path"] for ref in refs}:
                raise ValueError(
                    f"proof-adequacy answer for `{adequacy['path']}` must cite that proof file as repository evidence"
                )
        event = pipeline.accept_answer(
            run_id,
            answer_id,
            {"outcome": "accepted", "verified_by": "navigator", "evidence_refs": refs},
        )
        accepted.append({"answer_id": answer_id, "field_id": field_id, "event_id": event["event_id"], "state": "accepted"})
    status = public_intake_status(root, run_id)
    return {
        "type": "tailtrail-public-navigator-validation",
        "status": "accepted" if status["completeness"]["complete"] else "clarification-required",
        "run_id": run_id,
        "accepted": accepted,
        "completeness": status["completeness"],
        "next_action": (
            f"Finalize with `tailtrail navigator intake finalize --run-id {run_id} --bindings-file <file>`."
            if status["completeness"]["complete"]
            else "Record and validate the remaining mandatory fields before finalization."
        ),
    }


def public_intake_status(root: Path, run_id: str) -> dict[str, Any]:
    root = root.resolve()
    request = _load_public_request(root, run_id)
    pipeline = _load_intake_pipeline()(root)
    replay = pipeline.replay(run_id)
    required = [str(row["field_id"]) for row in _request_mandatory_fields(request)]
    rows = []
    accepted_by_field: dict[str, list[str]] = {}
    for row in replay.get("answer_states", []):
        state = str(row.get("state", "candidate"))
        if state == "accepted":
            for ref in row.get("evidence_refs", []):
                path = root / str(ref.get("path", ""))
                if not path.is_file() or _fingerprint(path) != ref.get("content_fingerprint"):
                    state = "stale"
                    break
        item = {"answer_id": row.get("answer_id"), "field_id": row.get("field_id"), "state": state}
        rows.append(item)
        if state == "accepted":
            accepted_by_field.setdefault(str(row.get("field_id")), []).append(str(row.get("answer_id")))
    duplicate_fields = sorted(field for field, identifiers in accepted_by_field.items() if len(identifiers) > 1)
    missing = sorted(field for field in required if len(accepted_by_field.get(field, [])) != 1)
    return {
        "type": "tailtrail-public-navigator-intake-status",
        "run_id": run_id,
        "profile": request["profile"],
        "answers": rows,
        "completeness": {
            "required": len(required),
            "accepted": sum(1 for field in required if len(accepted_by_field.get(field, [])) == 1),
            "missing": missing,
            "duplicate_fields": duplicate_fields,
            "complete": not missing and not duplicate_fields,
        },
        "planning_readiness": "eligible-for-finalization" if not missing and not duplicate_fields else "incomplete",
    }


def public_intake_finalize(root: Path, run_id: str, bindings: dict[str, Any]) -> dict[str, Any]:
    """Mint the immutable receipt only after the public intake is complete."""
    if not isinstance(bindings, dict):
        raise ValueError("finalization bindings must be an object")
    root = root.resolve()
    request = _load_public_request(root, run_id)
    status = public_intake_status(root, run_id)
    if status["completeness"]["complete"] is not True:
        raise ValueError("planning readiness is incomplete: " + ", ".join(status["completeness"]["missing"]))
    pipeline = _load_intake_pipeline()(root)
    replay = pipeline.replay(run_id)
    accepted_ids = [str(row["answer_id"]) for row in replay.get("answer_states", []) if row.get("state") == "accepted"]
    states = {str(row["answer_id"]): row for row in replay.get("answer_states", [])}
    recorded_answers = _answer_events(root, run_id)
    accepted_by_field = {
        str(recorded_answers[answer_id].get("field_id")): {
            **recorded_answers[answer_id],
            **state,
        }
        for answer_id, state in states.items()
        if state.get("state") == "accepted" and answer_id in recorded_answers
    }
    operational = json.loads(json.dumps(bindings.get("operational_bindings")))
    if not isinstance(operational, dict):
        raise ValueError("finalization requires operational_bindings")
    requirements = operational.get("requirements")
    if not isinstance(requirements, list) or not requirements:
        raise ValueError("finalization requires at least one operational requirement")

    declared_projection = json.loads(json.dumps(request.get("path_role_projection", {})))
    mandatory_by_role_path = {
        (str(row.get("host_role")), str(row.get("expected_value"))): str(row.get("field_id"))
        for row in _request_mandatory_fields(request)
        if row.get("kind") == "declared-path-role"
    }
    for declared in declared_projection.get("paths", []):
        field_id = mandatory_by_role_path.get((str(declared.get("host_role")), str(declared.get("path"))))
        if field_id:
            answer = accepted_by_field.get(field_id)
            if answer is None or str(answer.get("value", "")) != str(declared.get("path", "")):
                raise ValueError(
                    f"declared path `{declared.get('path')}` lacks its accepted role-confirmation answer"
                )
            declared["source_answer_ids"] = [str(answer["answer_id"])]
            declared["evidence_fingerprint"] = answer.get("source_evidence_fingerprint")
    operational["declared_path_roles"] = declared_projection

    proof_adequacy_by_path: dict[str, dict[str, Any]] = {}
    for field in _request_mandatory_fields(request):
        if field.get("kind") != "proof-adequacy":
            continue
        field_id = str(field.get("field_id", ""))
        answer = accepted_by_field.get(field_id)
        if answer is None:
            raise ValueError(f"declared proof `{field.get('expected_path')}` lacks an accepted proof-adequacy answer")
        adequacy = _parse_proof_adequacy(
            answer.get("value"),
            expected_path=str(field.get("expected_path", "")),
            host_role=str(field.get("host_role", "")),
            command=str(request["host_contract"].get("proof", {}).get("command", "")),
        )
        adequacy["source_answer_id"] = str(answer["answer_id"])
        adequacy["evidence_fingerprint"] = answer.get("source_evidence_fingerprint")
        proof_adequacy_by_path[adequacy["path"]] = adequacy

    path_bindings: dict[tuple[str, str], list[dict[str, Any]]] = {}
    proof_paths: set[str] = set()
    for requirement in requirements:
        if not isinstance(requirement, dict):
            raise ValueError("operational requirements must be objects")
        if "requirement_kind" not in requirement:
            raise ValueError(
                f"operational requirement `{requirement.get('requirement_uid', '<missing>')}` "
                "requires explicit requirement_kind and requirement_kind_source_answer_ids"
            )
        kind_sources = requirement.get("requirement_kind_source_answer_ids")
        if not isinstance(kind_sources, list) or not kind_sources:
            raise ValueError(
                f"operational requirement `{requirement.get('requirement_uid', '<missing>')}` "
                "requires requirement_kind_source_answer_ids"
            )
        requirement_sources = {
            str(value) for value in requirement.get("source_answer_ids", []) if str(value)
        }
        if any(
            states.get(str(value), {}).get("state") != "accepted"
            or str(value) not in requirement_sources
            for value in kind_sources
        ):
            raise ValueError(
                f"operational requirement `{requirement.get('requirement_uid', '<missing>')}` "
                "requirement kind must cite accepted answers bound to that requirement"
            )
        for path_binding in requirement.get("path_bindings", []):
            if isinstance(path_binding, dict):
                key = (str(path_binding.get("path", "")), str(path_binding.get("role", "")))
                path_bindings.setdefault(key, []).append(path_binding)
        for proof in requirement.get("proof_bindings", []) if isinstance(requirement, dict) else []:
            source_id = str(proof.get("source_answer_id", ""))
            if source_id in states:
                proof.setdefault("source_answer_ids", [source_id])
                proof["evidence_fingerprint"] = states[source_id].get("source_evidence_fingerprint")
            proof_path = str(proof.get("path", ""))
            adequacy = proof_adequacy_by_path.get(proof_path)
            if adequacy is None:
                raise ValueError(f"proof binding `{proof_path}` lacks accepted proof-adequacy evidence")
            proof["proof_adequacy"] = adequacy
            proof.setdefault("source_answer_ids", []).append(str(adequacy["source_answer_id"]))
            proof["source_answer_ids"] = sorted(set(proof["source_answer_ids"]))
            proof_paths.add(proof_path)

    for declared in declared_projection.get("paths", []):
        path = str(declared.get("path", ""))
        role = str(declared.get("operational_role", ""))
        if role in {"implementation-owner", "inspection-input", "configuration-output", "generated-output"}:
            matches = path_bindings.get((path, role), [])
            if len(matches) != 1:
                raise ValueError(
                    f"host-declared `{declared.get('host_role')}` path `{path}` must have exactly one "
                    f"operational `{role}` binding"
                )
            binding = matches[0]
            if binding.get("existing") is not declared.get("existing"):
                raise ValueError(f"operational binding for `{path}` contradicts its existing/proposed state")
            source_ids = {str(value) for value in binding.get("source_answer_ids", [])}
            if declared.get("source_answer_ids") and not set(declared["source_answer_ids"]).issubset(source_ids):
                raise ValueError(f"operational binding for `{path}` omits its accepted role-confirmation answer")
        elif role == "proof-only" and path not in proof_paths:
            raise ValueError(f"host-declared proof path `{path}` is missing from executable proof bindings")
    projections = bindings.get("requirement_projections")
    if projections is None:
        projections = [
            {
                "requirement_uid": str(row.get("requirement_uid", "")),
                "consumer_component_id": "planning-lock",
                "projection_kind": "requirement",
            }
            for row in requirements
        ]
    receipt = pipeline.mint_planning_readiness(
        run_id,
        accepted_answer_ids=accepted_ids,
        requirement_projections=projections,
        operational_bindings=operational,
        expected_packet_view_fingerprint=replay["packet_view_fingerprint"],
        target_identity={
            "root": root.as_posix(),
            "host_contract_fingerprint": request["host_contract_fingerprint"],
        },
    )
    receipt_path = root / ".tailtrail" / "intake" / run_id / "planning-readiness" / f"{receipt['receipt_id']}.json"
    contract_path = _public_run_root(root, run_id) / "validated-host-contract.json"
    _atomic_json(contract_path, request["host_contract"])
    command = ["tailtrail", "start", str(request["goal"])]
    if request.get("host"):
        command.extend(["--host", str(request["host"])])
    if request.get("aidlc"):
        command.extend(["--aidlc", str(request["aidlc"])])
    for row in request["host_contract"].get("paths", []):
        if row.get("role") == "existing-implementation-owner":
            command.extend(["--changed", str(row["path"])])
    command.extend([
        "--host-contract-file", contract_path.as_posix(),
        "--planning-readiness-receipt-file", receipt_path.as_posix(),
    ])
    return {
        "type": "tailtrail-public-navigator-planning-readiness",
        "status": "planning-readiness",
        "run_id": run_id,
        "receipt_id": receipt["receipt_id"],
        "receipt_path": receipt_path.as_posix(),
        "receipt": receipt,
        "path_role_projection": declared_projection,
        "completeness": status["completeness"],
        "retry_command": _shell_join(command),
        "authority": "The receipt authorizes Start intake only; user approval is still required before implementation.",
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
    parser = argparse.ArgumentParser(description="Operate TailTrail's public Navigator intake and saved question context.")
    sub = parser.add_subparsers(dest="command", required=True)
    show_parser = sub.add_parser("show")
    show_parser.add_argument("--root", type=Path, default=Path.cwd())
    show_parser.add_argument("--run-id", required=True)
    open_parser = sub.add_parser("open")
    open_parser.add_argument("--root", type=Path, default=Path.cwd())
    open_parser.add_argument("--goal", required=True)
    open_parser.add_argument("--host-contract-file", type=Path, required=True)
    open_parser.add_argument("--host", choices=("codex", "copilot", "claude"))
    open_parser.add_argument("--aidlc", choices=("lite", "standard", "medium", "full", "off"))
    record_parser = sub.add_parser("record")
    record_parser.add_argument("--root", type=Path, default=Path.cwd())
    record_parser.add_argument("--run-id", required=True)
    record_parser.add_argument("--answers-file", type=Path, required=True)
    validate_parser = sub.add_parser("validate")
    validate_parser.add_argument("--root", type=Path, default=Path.cwd())
    validate_parser.add_argument("--run-id", required=True)
    validate_parser.add_argument("--evidence-file", type=Path, required=True)
    status_parser = sub.add_parser("status")
    status_parser.add_argument("--root", type=Path, default=Path.cwd())
    status_parser.add_argument("--run-id", required=True)
    finalize_parser = sub.add_parser("finalize")
    finalize_parser.add_argument("--root", type=Path, default=Path.cwd())
    finalize_parser.add_argument("--run-id", required=True)
    finalize_parser.add_argument("--bindings-file", type=Path, required=True)
    args = parser.parse_args()
    try:
        if args.command == "show":
            payload = show(args.root, args.run_id)
        elif args.command == "open":
            raw_contract = json.loads(args.host_contract_file.read_text(encoding="utf-8"))
            payload = public_intake_open(
                args.root, args.goal, raw_contract, host=args.host, aidlc=args.aidlc,
            )
        elif args.command == "record":
            payload = public_intake_record(
                args.root, args.run_id, json.loads(args.answers_file.read_text(encoding="utf-8")),
            )
        elif args.command == "validate":
            payload = public_intake_validate(
                args.root, args.run_id, json.loads(args.evidence_file.read_text(encoding="utf-8")),
            )
        elif args.command == "status":
            payload = public_intake_status(args.root, args.run_id)
        else:
            payload = public_intake_finalize(
                args.root, args.run_id, json.loads(args.bindings_file.read_text(encoding="utf-8")),
            )
    except (OSError, json.JSONDecodeError, ValueError) as error:
        parser.error(str(error))
    print(json.dumps(payload, indent=2, sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
