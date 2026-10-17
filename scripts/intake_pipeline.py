"""Minimal Phase 1A intake contract and interaction event pipeline."""
from __future__ import annotations

import hashlib
import json
import re
import uuid
from pathlib import Path
from typing import Any


class IntakeError(ValueError):
    """Raised when an intake operation cannot satisfy its contract."""


def _new_id(prefix: str) -> str:
    return f"{prefix}-{uuid.uuid4().hex[:16]}"


def _canonical(value: Any) -> str:
    return json.dumps(value, sort_keys=True, separators=(",", ":"))


def _content_fingerprint(value: Any) -> str:
    return "sha256:" + hashlib.sha256(_canonical(value).encode("utf-8")).hexdigest()


def _write_json(path: Path, value: dict[str, Any]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    temporary = path.with_suffix(path.suffix + ".tmp")
    temporary.write_text(json.dumps(value, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    temporary.replace(path)


_SENSITIVE_KEY = re.compile(r"(?:password|passphrase|secret|token|api[_-]?key|private[_-]?key)", re.I)
_SENSITIVE_VALUE = re.compile(r"(?:Bearer\s+|token\s*[:=]\s*|secret\s*[:=]\s*)\S+", re.I)
_ANCHOR_VERSION = re.compile(r"^anchor-v[1-9][0-9]*$")
_PACKET_VIEW_PROJECTION_KINDS = frozenset({"scope", "requirement", "validation", "approval"})
_PATH_ROLES = frozenset({"implementation-owner", "inspection-input", "proof-only"})
_NEW_FILE_VERDICTS = frozenset({
    "new-confirmed", "extend-recommended", "collision-blocked", "unverified", "not-applicable",
})
_CORRECTION_PREMISES = frozenset({"accepted", "not-applicable"})


def _redact(value: Any, key: str | None = None) -> Any:
    if key and _SENSITIVE_KEY.search(key):
        return "[REDACTED]"
    if isinstance(value, dict):
        return {str(name): _redact(item, str(name)) for name, item in value.items()}
    if isinstance(value, list):
        return [_redact(item) for item in value]
    if isinstance(value, str):
        return _SENSITIVE_VALUE.sub("[REDACTED]", value)
    return value


class IntakePipeline:
    """Persist the Phase 1A contract and correlate interaction events."""

    def __init__(self, root: Path) -> None:
        self.root = root.resolve()
        self.runs_root = self.root / ".tailtrail" / "intake"

    def create_run(self, goal: str, profile: str) -> dict[str, str]:
        if not goal.strip() or not profile.strip():
            raise IntakeError("goal and profile are required")
        run_id = _new_id("run")
        contract_id = _new_id("contract")
        packet_version = 1
        contract = {
            "schema_version": "1",
            "type": "tailtrail-intake-contract",
            "run_id": run_id,
            "contract_id": contract_id,
            "profile": profile,
            "goal": goal,
            "packet_version": packet_version,
            "status": "intake",
        }
        contract["fingerprint"] = _content_fingerprint(contract)
        run_root = self.runs_root / run_id
        _write_json(run_root / "contract.json", contract)
        return {
            "run_id": run_id,
            "contract_id": str(contract["contract_id"]),
            "packet_version": "1",
            "fingerprint": str(contract["fingerprint"]),
        }

    def load_contract(self, run_id: str) -> dict[str, Any]:
        path = self.runs_root / run_id / "contract.json"
        if not path.is_file():
            raise IntakeError(f"unknown intake run: {run_id}")
        return json.loads(path.read_text(encoding="utf-8"))

    def _run_root(self, run_id: str) -> Path:
        return self.runs_root / str(run_id)

    def _integrity_path(self, run_id: str) -> Path:
        return self._run_root(run_id) / "event-integrity.jsonl"

    def _projection_path(self, run_id: str) -> Path:
        return self._run_root(run_id) / "projection.json"

    def _packet_view_path(self, run_id: str, anchor_version: str) -> Path:
        """Return the immutable view location for one authoritative anchor."""
        return self._run_root(run_id) / "packet-views" / f"{anchor_version}.json"

    def _packet_finalization_receipt_path(self, run_id: str, anchor_version: str) -> Path:
        """Keep private source-evidence separate from the public packet-view schema."""
        return self._run_root(run_id) / "packet-views" / f"{anchor_version}.receipt.json"

    def _packet_invalidation_path(self, run_id: str, anchor_version: str) -> Path:
        """Keep invalidation evidence beside, but never inside, immutable views."""
        return self._run_root(run_id) / "packet-views" / f"{anchor_version}.invalidation.json"

    def _state_path(self, run_id: str) -> Path:
        return self._run_root(run_id) / "lifecycle.json"

    def _lifecycle(self, run_id: str) -> dict[str, Any]:
        path = self._state_path(run_id)
        if path.is_file():
            return json.loads(path.read_text(encoding="utf-8"))
        return {"run_id": run_id, "status": "active", "history": []}

    def _save_lifecycle(self, run_id: str, status: str, reason: str) -> dict[str, Any]:
        self.load_contract(run_id)
        lifecycle = self._lifecycle(run_id)
        lifecycle["status"] = status
        lifecycle.setdefault("history", []).append({"status": status, "reason": reason})
        _write_json(self._state_path(run_id), lifecycle)
        return lifecycle

    def pause_run(self, run_id: str, reason: str = "paused") -> dict[str, Any]:
        return self._save_lifecycle(run_id, "paused", reason)

    def expire_run(self, run_id: str, reason: str = "expired") -> dict[str, Any]:
        return self._save_lifecycle(run_id, "expired", reason)

    def abandon_run(self, run_id: str, reason: str = "abandoned") -> dict[str, Any]:
        return self._save_lifecycle(run_id, "abandoned", reason)

    def resume_run(self, run_id: str, reason: str = "explicit resume") -> dict[str, Any]:
        lifecycle = self._lifecycle(run_id)
        if lifecycle.get("status") not in {"paused", "expired", "abandoned"}:
            raise IntakeError(f"run {run_id} is not resumable from {lifecycle.get('status', 'unknown')}")
        return self._save_lifecycle(run_id, "active", reason)

    def assert_execution_allowed(self, run_id: str) -> None:
        status = self._lifecycle(run_id).get("status")
        if status in {"expired", "abandoned", "paused"}:
            raise IntakeError(f"run {run_id} is {status}; explicit resume is required before execution")

    def replay(self, run_id: str) -> dict[str, Any]:
        """Replay events into a deterministic, redacted packet projection."""
        contract = self.load_contract(run_id)
        events_path = self._run_root(run_id) / "events.jsonl"
        events = [json.loads(line) for line in events_path.read_text(encoding="utf-8").splitlines() if line.strip()] if events_path.is_file() else []
        integrity_path = self._integrity_path(run_id)
        integrity = [json.loads(line) for line in integrity_path.read_text(encoding="utf-8").splitlines() if line.strip()] if integrity_path.is_file() else []
        if integrity and len(integrity) != len(events):
            raise IntakeError("event integrity ledger does not match event stream length")

        previous = ""
        projection: dict[str, list[Any]] = {"questions": [], "observations": [], "answers": []}
        for index, event in enumerate(events, start=1):
            if event.get("sequence") != index or event.get("run_id") != run_id or event.get("contract_id") != contract["contract_id"]:
                raise IntakeError(f"event stream integrity failure at sequence {index}")
            event_fingerprint = _content_fingerprint(event)
            if integrity:
                record = integrity[index - 1]
                if record.get("event_fingerprint") != event_fingerprint or record.get("previous") != previous:
                    raise IntakeError(f"event integrity failure at sequence {index}")
            previous = event_fingerprint
            event_type = event.get("event_type")
            if event_type == "question-issued":
                projection["questions"].append(_redact(event["payload"]))
            elif event_type == "host-observation-recorded":
                projection["observations"].append(_redact(event["payload"]))
            elif event_type == "answer-recorded":
                projection["answers"].append(_redact(event["payload"]))

        packet_view = _redact({
            "contract": {key: value for key, value in contract.items() if key != "fingerprint"},
            "events": projection,
        })
        result = {
            "run_id": run_id,
            "status": "valid",
            "contract": contract,
            "packet_view": packet_view,
            "contract_fingerprint": contract["fingerprint"],
            "packet_view_fingerprint": _content_fingerprint(packet_view),
            "event_count": len(events),
            "lifecycle": self._lifecycle(run_id),
        }
        _write_json(self._projection_path(run_id), result)
        return result

    def finalize_packet_view(
        self,
        run_id: str,
        *,
        anchor_version: str,
        accepted_answers: list[dict[str, Any]],
        requirement_projections: list[dict[str, Any]],
        expected_packet_view_fingerprint: str,
        anchor_fingerprint: str | None = None,
        operational_bindings: dict[str, Any] | None = None,
    ) -> dict[str, Any]:
        """Materialize one immutable Navigator packet view for an anchor.

        The caller selects only answers already accepted by Navigator through
        the append-only intake stream; it cannot supply acceptance assertions.
        The pipeline verifies answer lineage and the exact replay snapshot
        before minting an anchor-bound view.  This deliberately does not
        change ``contract.packet_version``: the anchor is the only versioned
        authority for a finalized packet.
        """
        if not _ANCHOR_VERSION.fullmatch(anchor_version):
            raise IntakeError("anchor_version must use the form anchor-vN")
        if not isinstance(expected_packet_view_fingerprint, str) or not re.fullmatch(
            r"sha256:[a-f0-9]{64}", expected_packet_view_fingerprint
        ):
            raise IntakeError("expected_packet_view_fingerprint must be a SHA-256 fingerprint")
        if not isinstance(accepted_answers, list) or not accepted_answers:
            raise IntakeError("packet finalization requires at least one Navigator-accepted answer")
        if not isinstance(requirement_projections, list) or not requirement_projections:
            raise IntakeError("packet finalization requires at least one requirement projection")

        replay = self.replay(run_id)
        if replay["packet_view_fingerprint"] != expected_packet_view_fingerprint:
            raise IntakeError("stale packet finalization input; replay intake and obtain a fresh fingerprint")

        events_path = self._run_root(run_id) / "events.jsonl"
        events = [
            json.loads(line)
            for line in events_path.read_text(encoding="utf-8").splitlines()
            if line.strip()
        ] if events_path.is_file() else []
        answers = {
            str(event.get("payload", {}).get("answer_id")): event.get("payload", {})
            for event in events
            if event.get("event_type") == "answer-recorded"
            and str(event.get("payload", {}).get("answer_id", "")).strip()
        }
        question_ids = {
            str(event.get("payload", {}).get("question_id"))
            for event in events
            if event.get("event_type") == "question-issued"
        }
        observation_ids = {
            str(event.get("payload", {}).get("observation_id"))
            for event in events
            if event.get("event_type") == "host-observation-recorded"
        }
        accepted_by_navigator = {
            str(event.get("payload", {}).get("answer_id"))
            for event in events
            if event.get("event_type") == "answer-accepted"
            and event.get("payload", {}).get("evidence") == {"outcome": "accepted", "verified_by": "navigator"}
        }

        accepted_ids: list[str] = []
        accepted_records: list[dict[str, Any]] = []
        values_by_field: dict[str, str] = {}
        for index, accepted in enumerate(accepted_answers, start=1):
            if not isinstance(accepted, dict):
                raise IntakeError(f"accepted answer {index} must be an object")
            answer_id = str(accepted.get("answer_id", "")).strip()
            if not answer_id or answer_id in accepted_ids:
                raise IntakeError("accepted answers must contain unique recorded answer IDs")
            if answer_id not in accepted_by_navigator:
                raise IntakeError(f"accepted answer `{answer_id}` has no Navigator-validated acceptance event")
            answer = answers.get(answer_id)
            if not isinstance(answer, dict):
                raise IntakeError(f"accepted answer `{answer_id}` is missing from the integrity-checked intake stream")
            field_id = str(answer.get("field_id", "")).strip()
            if not field_id or answer.get("value") in (None, ""):
                raise IntakeError(f"accepted answer `{answer_id}` has incomplete field or value")
            question_id = answer.get("question_id")
            observation_id = answer.get("observation_id")
            if question_id is not None and str(question_id) not in question_ids:
                raise IntakeError(f"accepted answer `{answer_id}` has an unknown question lineage")
            if observation_id is not None and str(observation_id) not in observation_ids:
                raise IntakeError(f"accepted answer `{answer_id}` has an unknown observation lineage")
            value_fingerprint = _canonical(answer["value"])
            previous = values_by_field.get(field_id)
            if previous is not None and previous != value_fingerprint:
                raise IntakeError(f"contradictory accepted answers for profile field `{field_id}`")
            values_by_field[field_id] = value_fingerprint
            accepted_ids.append(answer_id)
            accepted_records.append({
                "answer_id": answer_id,
                "field_id": field_id,
                "value": answer["value"],
                "question_id": question_id,
                "observation_id": observation_id,
            })

        normalized_projections: list[dict[str, str]] = []
        seen_projections: set[tuple[str, str, str]] = set()
        for index, projection in enumerate(requirement_projections, start=1):
            if not isinstance(projection, dict):
                raise IntakeError(f"requirement projection {index} must be an object")
            requirement_uid = str(projection.get("requirement_uid", "")).strip()
            consumer_component_id = str(projection.get("consumer_component_id", "")).strip()
            projection_kind = str(projection.get("projection_kind", "")).strip()
            if not requirement_uid or not consumer_component_id or projection_kind not in _PACKET_VIEW_PROJECTION_KINDS:
                raise IntakeError(f"requirement projection {index} is incomplete or has an unsupported kind")
            key = (requirement_uid, consumer_component_id, projection_kind)
            if key in seen_projections:
                raise IntakeError("packet finalization requires unique requirement projections")
            seen_projections.add(key)
            normalized_projections.append({
                "requirement_uid": requirement_uid,
                "consumer_component_id": consumer_component_id,
                "projection_kind": projection_kind,
            })

        operational_packet: dict[str, Any] | None = None
        if anchor_fingerprint is not None or operational_bindings is not None:
            operational_packet = self._build_operational_packet(
                anchor_version=anchor_version,
                anchor_fingerprint=anchor_fingerprint,
                operational_bindings=operational_bindings,
                accepted_records=accepted_records,
                projected_requirement_ids={projection["requirement_uid"] for projection in normalized_projections},
            )

        view_path = self._packet_view_path(run_id, anchor_version)
        if view_path.exists():
            raise IntakeError(
                f"packet view for `{anchor_version}` already exists; material changes require a new anchor version"
            )
        packet_view = {
            "schema_version": "1",
            "type": "tailtrail-host-question-flow-packet-view",
            "packet_view_id": _new_id("packet-view"),
            "run_id": run_id,
            "contract_id": replay["contract"]["contract_id"],
            "anchor_version": anchor_version,
            "status": "materialized",
            "requirement_projections": normalized_projections,
        }
        if operational_packet is not None:
            packet_view["operational_packet"] = operational_packet
        source_answer_fingerprint = _content_fingerprint(accepted_records)
        receipt = {
            "schema_version": "1",
            "type": "tailtrail-host-question-flow-packet-finalization-receipt",
            "packet_view_id": packet_view["packet_view_id"],
            "run_id": run_id,
            "contract_id": replay["contract"]["contract_id"],
            "anchor_version": anchor_version,
            "accepted_answer_ids": accepted_ids,
            "source_answer_fingerprint": source_answer_fingerprint,
            "source_packet_view_fingerprint": replay["packet_view_fingerprint"],
            "packet_view_fingerprint": _content_fingerprint(packet_view),
        }
        _write_json(view_path, packet_view)
        _write_json(self._packet_finalization_receipt_path(run_id, anchor_version), receipt)
        invalidated = self._invalidate_prior_packet_views(run_id, anchor_version, packet_view["packet_view_id"])
        self._append_event(
            replay["contract"],
            "packet-finalized",
            {
                "packet_view_id": packet_view["packet_view_id"],
                "anchor_version": anchor_version,
                "source_answer_fingerprint": source_answer_fingerprint,
                "invalidated_packet_view_ids": invalidated,
            },
        )
        return {"status": "requirements-finalized", "packet_view": packet_view, "receipt": receipt}

    def _build_operational_packet(
        self,
        *,
        anchor_version: str,
        anchor_fingerprint: str | None,
        operational_bindings: dict[str, Any] | None,
        accepted_records: list[dict[str, Any]],
        projected_requirement_ids: set[str],
    ) -> dict[str, Any]:
        """Build the Phase 3 redacted operational projection from accepted IDs only.

        The input remains deliberately narrow: it can cite accepted answer IDs,
        but it cannot import raw host answers or invent an acceptance decision.
        Every derived item carries its source IDs so downstream consumers only
        receive an immutable, auditable projection.
        """
        if not isinstance(anchor_fingerprint, str) or not re.fullmatch(r"sha256:[a-f0-9]{64}", anchor_fingerprint):
            raise IntakeError("operational packet finalization requires an anchor SHA-256 fingerprint")
        if not isinstance(operational_bindings, dict):
            raise IntakeError("operational packet finalization requires binding objects")
        requirements = operational_bindings.get("requirements")
        if not isinstance(requirements, list) or not requirements:
            raise IntakeError("operational packet finalization requires at least one requirement binding")

        accepted_by_id = {record["answer_id"]: record for record in accepted_records}
        consumed_ids: set[str] = set()
        path_roles: dict[str, str] = {}
        requirement_ids: set[str] = set()
        normalized_requirements: list[dict[str, Any]] = []

        def source_ids(value: Any, label: str) -> list[str]:
            if not isinstance(value, list) or not value or any(not isinstance(item, str) or item not in accepted_by_id for item in value):
                raise IntakeError(f"{label} must cite one or more Navigator-accepted answer IDs")
            normalized = sorted(set(value))
            consumed_ids.update(normalized)
            return normalized

        for index, requirement in enumerate(requirements, start=1):
            if not isinstance(requirement, dict):
                raise IntakeError(f"requirement binding {index} must be an object")
            requirement_uid = str(requirement.get("requirement_uid", "")).strip()
            statement = str(requirement.get("statement", "")).strip()
            if not requirement_uid or not statement or requirement_uid in requirement_ids:
                raise IntakeError("requirement bindings need unique requirement_uids and statements")
            requirement_ids.add(requirement_uid)
            requirement_sources = source_ids(requirement.get("source_answer_ids"), f"requirement `{requirement_uid}`")
            profile_fields = requirement.get("profile_fields")
            if not isinstance(profile_fields, list) or not profile_fields or any(not isinstance(field, str) or not field for field in profile_fields):
                raise IntakeError(f"requirement `{requirement_uid}` needs profile_fields")
            accepted_fields = {accepted_by_id[answer_id]["field_id"] for answer_id in requirement_sources}
            if not set(profile_fields).issubset(accepted_fields):
                raise IntakeError(f"requirement `{requirement_uid}` profile_fields must be evidenced by its source answers")

            normalized_paths: list[dict[str, Any]] = []
            path_bindings = requirement.get("path_bindings")
            if not isinstance(path_bindings, list) or not path_bindings:
                raise IntakeError(f"requirement `{requirement_uid}` needs path bindings")
            for path_index, binding in enumerate(path_bindings, start=1):
                if not isinstance(binding, dict):
                    raise IntakeError(f"path binding {path_index} for `{requirement_uid}` must be an object")
                path = str(binding.get("path", "")).strip()
                role = str(binding.get("role", "")).strip()
                if not path or role not in _PATH_ROLES:
                    raise IntakeError(f"path binding {path_index} for `{requirement_uid}` has an unsupported path role")
                existing = binding.get("existing")
                if not isinstance(existing, bool):
                    raise IntakeError(f"path binding `{path}` must declare whether it already exists")
                if existing and not (self.root / path).exists():
                    raise IntakeError(f"existing path `{path}` requires filesystem existence evidence")
                if not existing and binding.get("host_declared") is not True:
                    raise IntakeError(f"proposed path `{path}` requires an explicit host declaration")
                binding_sources = source_ids(binding.get("source_answer_ids"), f"path binding `{path}`")
                previous_role = path_roles.get(path)
                if previous_role is not None and previous_role != role:
                    raise IntakeError(f"contradictory path roles for `{path}`")
                path_roles[path] = role
                verdict = str(binding.get("new_file_verdict", "not-applicable")).strip()
                if verdict not in _NEW_FILE_VERDICTS:
                    raise IntakeError(f"path binding `{path}` has an unsupported new-file verdict")
                if existing and verdict != "not-applicable":
                    raise IntakeError(f"existing path `{path}` must use new-file verdict `not-applicable`")
                if not existing and verdict == "not-applicable":
                    raise IntakeError(f"proposed path `{path}` requires a new-file verdict")
                if not existing and not str(binding.get("ownership_evidence", "")).strip():
                    raise IntakeError(f"proposed path `{path}` requires ownership or convention evidence")
                normalized_paths.append({
                    "path_binding_id": _new_id("path-binding"), "path": path, "role": role,
                    "existing": existing, "new_file_verdict": verdict,
                    "ownership_evidence": str(binding.get("ownership_evidence", "")).strip() or None,
                    "source_answer_ids": binding_sources,
                })

            normalized_proofs: list[dict[str, Any]] = []
            proofs = requirement.get("proof_bindings")
            if not isinstance(proofs, list) or not proofs:
                raise IntakeError(f"requirement `{requirement_uid}` needs proof bindings")
            for proof_index, proof in enumerate(proofs, start=1):
                if not isinstance(proof, dict):
                    raise IntakeError(f"proof binding {proof_index} for `{requirement_uid}` must be an object")
                command = str(proof.get("command", "")).strip()
                path = str(proof.get("path", "")).strip()
                if not command or not path:
                    raise IntakeError(f"proof binding {proof_index} for `{requirement_uid}` is incomplete")
                normalized_proofs.append({
                    "proof_binding_id": _new_id("proof-binding"), "command": command, "path": path,
                    "source_answer_ids": source_ids(proof.get("source_answer_ids"), f"proof binding `{path}`"),
                })

            criteria = requirement.get("criteria")
            if not isinstance(criteria, dict):
                raise IntakeError(f"requirement `{requirement_uid}` needs criteria bindings")
            positive = criteria.get("positive")
            negative = criteria.get("negative")
            if not isinstance(positive, list) or not positive or not isinstance(negative, list) or not negative:
                raise IntakeError(f"requirement `{requirement_uid}` needs positive and negative criteria")
            criteria_sources = source_ids(criteria.get("source_answer_ids"), f"criteria for `{requirement_uid}`")

            premise = requirement.get("correction_premise", {"status": "not-applicable", "source_answer_ids": requirement_sources})
            if not isinstance(premise, dict) or str(premise.get("status", "")).strip() not in _CORRECTION_PREMISES:
                raise IntakeError(f"correction premise for `{requirement_uid}` must be accepted or not-applicable")
            premise_sources = source_ids(premise.get("source_answer_ids"), f"correction premise for `{requirement_uid}`")
            owner_evidence = requirement.get("owner_participation_evidence", [])
            if premise.get("status") == "accepted" and (not isinstance(owner_evidence, list) or not owner_evidence):
                raise IntakeError(f"accepted correction premise for `{requirement_uid}` requires owner participation evidence")
            normalized_owner_evidence = []
            for evidence_index, evidence in enumerate(owner_evidence):
                if not isinstance(evidence, dict) or not str(evidence.get("kind", "")).strip():
                    raise IntakeError(f"owner participation evidence {evidence_index + 1} for `{requirement_uid}` is incomplete")
                normalized_owner_evidence.append({
                    "kind": str(evidence["kind"]),
                    "source_answer_ids": source_ids(evidence.get("source_answer_ids"), f"owner evidence for `{requirement_uid}`"),
                })
            normalized_requirements.append({
                "requirement_id": _new_id("requirement"), "requirement_uid": requirement_uid, "statement": statement,
                "source_answer_ids": requirement_sources, "profile_fields": sorted(set(profile_fields)),
                "path_bindings": normalized_paths, "proof_bindings": normalized_proofs,
                "criteria": {"positive": list(positive), "negative": list(negative), "source_answer_ids": criteria_sources},
                "correction_premise": {"status": str(premise["status"]), "source_answer_ids": premise_sources},
                "owner_participation_evidence": normalized_owner_evidence,
            })

        unconsumed = sorted(set(accepted_by_id) - consumed_ids)
        if unconsumed:
            raise IntakeError(f"unused Navigator-accepted answers require clarification: {', '.join(unconsumed)}")
        if projected_requirement_ids != requirement_ids:
            raise IntakeError("operational requirements must exactly match their approved requirement projections")
        audit = {
            "consumed": sorted(consumed_ids), "unused": [], "contradicted": [],
            "inferred": [], "projected_without_source": [],
        }
        return {
            "anchor_fingerprint": anchor_fingerprint,
            "requirements": normalized_requirements,
            "projection_audit": audit,
        }

    def _invalidate_prior_packet_views(self, run_id: str, anchor_version: str, replacement_view_id: str) -> list[str]:
        """Record dependent-view invalidation when a newer anchor is finalized."""
        target_number = int(anchor_version.removeprefix("anchor-v"))
        invalidated: list[str] = []
        views_root = self._run_root(run_id) / "packet-views"
        for view_path in sorted(views_root.glob("anchor-v*.json")):
            prior_version = view_path.stem
            if prior_version == anchor_version or not _ANCHOR_VERSION.fullmatch(prior_version):
                continue
            if int(prior_version.removeprefix("anchor-v")) >= target_number:
                continue
            prior_view = json.loads(view_path.read_text(encoding="utf-8"))
            receipt_path = self._packet_invalidation_path(run_id, prior_version)
            if receipt_path.exists():
                continue
            invalidation = {
                "schema_version": "1", "type": "tailtrail-host-question-flow-packet-view-invalidation",
                "invalidated_packet_view_id": prior_view["packet_view_id"], "invalidated_anchor_version": prior_version,
                "replacement_anchor_version": anchor_version, "replacement_packet_view_id": replacement_view_id,
                "reason": "anchor-revised",
            }
            _write_json(receipt_path, invalidation)
            invalidated.append(prior_view["packet_view_id"])
        return invalidated

    def _check_packet_version(self, contract: dict[str, Any], packet_version: int | None) -> None:
        if packet_version is None:
            return
        current = contract.get("packet_version")
        if packet_version != current:
            raise IntakeError(
                f"stale packet version {packet_version} for run {contract['run_id']} (current {current})"
            )

    def revise_contract(
        self,
        run_id: str,
        changes: dict[str, Any],
        *,
        packet_version: int | None = None,
        approved: bool = False,
    ) -> dict[str, Any]:
        """Advance the contract to a new approved packet version and refresh its fingerprint."""
        if not approved:
            raise IntakeError("contract revision requires explicit approval")
        if not isinstance(changes, dict) or not changes:
            raise IntakeError("changes must be a non-empty object")
        contract = self.load_contract(run_id)
        self._check_packet_version(contract, packet_version)
        protected = {"run_id", "contract_id", "schema_version", "type"}
        safe_changes = {key: value for key, value in changes.items() if key not in protected}
        if not safe_changes:
            raise IntakeError("changes must include at least one revisable field")
        updated = dict(contract)
        updated.update(safe_changes)
        updated["packet_version"] = contract["packet_version"] + 1
        stable = {key: value for key, value in updated.items() if key != "fingerprint"}
        updated["fingerprint"] = _content_fingerprint(stable)
        _write_json(self.runs_root / str(run_id) / "contract.json", updated)
        result = self._append_event(
            updated, "anchor-revised", {"packet_version": updated["packet_version"], "changes": safe_changes}
        )
        self.replay(run_id)
        return result

    def issue_question(
        self,
        run_id: str,
        field_id: str,
        text: str,
        *,
        packet_version: int | None = None,
        idempotency_key: str | None = None,
    ) -> dict[str, Any]:
        if not field_id.strip() or not text.strip():
            raise IntakeError("field_id and question text are required")
        contract = self.load_contract(run_id)
        self._check_packet_version(contract, packet_version)
        question = {
            "question_id": _new_id("question"),
            "field_id": field_id,
            "text": text,
        }
        return self._append_event(
            contract, "question-issued", question, primary_id_key="question_id", idempotency_key=idempotency_key
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
        if not isinstance(observation, dict) or not observation:
            raise IntakeError("observation must be a non-empty object")
        contract = self.load_contract(run_id)
        self._check_packet_version(contract, packet_version)
        payload = {
            "observation_id": _new_id("observation"),
            "question_id": question_id,
            "observation": observation,
        }
        return self._append_event(
            contract,
            "host-observation-recorded",
            payload,
            primary_id_key="observation_id",
            idempotency_key=idempotency_key,
        )

    def record_answer(
        self,
        run_id: str,
        field_id: str,
        value: Any,
        *,
        source: str,
        question_id: str | None = None,
        observation_id: str | None = None,
        packet_version: int | None = None,
        idempotency_key: str | None = None,
    ) -> dict[str, Any]:
        if not field_id.strip() or not source.strip():
            raise IntakeError("field_id and source are required")
        if question_id is None and observation_id is None:
            raise IntakeError("answer requires question_id or observation_id")
        contract = self.load_contract(run_id)
        self._check_packet_version(contract, packet_version)
        payload = {
            "answer_id": _new_id("answer"),
            "field_id": field_id,
            "value": value,
            "source": source,
            "question_id": question_id,
            "observation_id": observation_id,
        }
        return self._append_event(
            contract, "answer-recorded", payload, primary_id_key="answer_id", idempotency_key=idempotency_key
        )

    def accept_answer(
        self,
        run_id: str,
        answer_id: str,
        evidence: dict[str, Any],
        *,
        packet_version: int | None = None,
        idempotency_key: str | None = None,
    ) -> dict[str, Any]:
        """Record Navigator-owned acceptance for one existing answer.

        Phase 2 produces the acceptance evidence. This method records its
        constrained result so Phase 2B finalization never trusts a caller's
        assertion that an answer was accepted.
        """
        if not answer_id.strip():
            raise IntakeError("answer_id is required for acceptance")
        if not isinstance(evidence, dict) or evidence.get("outcome") != "accepted" or evidence.get("verified_by") != "navigator":
            raise IntakeError("answer acceptance requires Navigator-validated evidence")
        contract = self.load_contract(run_id)
        self._check_packet_version(contract, packet_version)
        self.replay(run_id)
        events_path = self._run_root(run_id) / "events.jsonl"
        answer_exists = any(
            event.get("event_type") == "answer-recorded"
            and str(event.get("payload", {}).get("answer_id", "")) == answer_id
            for event in (
                json.loads(line)
                for line in events_path.read_text(encoding="utf-8").splitlines()
                if line.strip()
            )
        )
        if not answer_exists:
            raise IntakeError(f"answer `{answer_id}` is missing from the integrity-checked intake stream")
        return self._append_event(
            contract,
            "answer-accepted",
            {"answer_id": answer_id, "evidence": {"outcome": "accepted", "verified_by": "navigator"}},
            idempotency_key=idempotency_key,
        )

    def _idempotency_index_path(self, run_id: str) -> Path:
        return self.runs_root / str(run_id) / "idempotency.json"

    def _load_idempotency_index(self, run_id: str) -> dict[str, Any]:
        path = self._idempotency_index_path(run_id)
        if not path.is_file():
            return {}
        return json.loads(path.read_text(encoding="utf-8"))

    def _append_event(
        self,
        contract: dict[str, Any],
        event_type: str,
        payload: dict[str, Any],
        *,
        primary_id_key: str | None = None,
        idempotency_key: str | None = None,
    ) -> dict[str, Any]:
        # The persisted envelope below must match schemas/host-question-flow-event.schema.json
        # (Phase 0, locked) exactly; idempotency and content-fingerprint bookkeeping are kept
        # out-of-band so they never appear as extra envelope or payload keys on disk.
        run_id = str(contract["run_id"])
        run_root = self.runs_root / run_id
        events_path = run_root / "events.jsonl"
        stable_payload = payload
        if primary_id_key is not None:
            stable_payload = {key: value for key, value in payload.items() if key != primary_id_key}
        content_fingerprint = _content_fingerprint({"event_type": event_type, "payload": stable_payload})

        if idempotency_key:
            index = self._load_idempotency_index(run_id)
            existing = index.get(idempotency_key)
            if existing is not None:
                if existing["content_fingerprint"] != content_fingerprint:
                    raise IntakeError(
                        f"idempotency key {idempotency_key!r} already used with different event content"
                    )
                result = dict(existing["event"])
                result["content_fingerprint"] = content_fingerprint
                return result

        sequence = 1
        if events_path.is_file():
            sequence = len(events_path.read_text(encoding="utf-8").splitlines()) + 1
        event = {
            "schema_version": "1",
            "type": "tailtrail-intake-event",
            "event_id": _new_id("event"),
            "run_id": contract["run_id"],
            "contract_id": contract["contract_id"],
            "packet_version": contract["packet_version"],
            "sequence": sequence,
            "event_type": event_type,
            "payload": payload,
        }
        events_path.parent.mkdir(parents=True, exist_ok=True)
        with events_path.open("a", encoding="utf-8") as handle:
            handle.write(json.dumps(event, sort_keys=True) + "\n")

        previous = ""
        integrity_path = self._integrity_path(run_id)
        if integrity_path.is_file():
            records = [line for line in integrity_path.read_text(encoding="utf-8").splitlines() if line.strip()]
            if records:
                previous = str(json.loads(records[-1]).get("event_fingerprint", ""))
        with integrity_path.open("a", encoding="utf-8") as handle:
            handle.write(json.dumps({
                "sequence": sequence,
                "event_id": event["event_id"],
                "event_fingerprint": _content_fingerprint(event),
                "previous": previous,
            }, sort_keys=True) + "\n")

        if idempotency_key:
            index = self._load_idempotency_index(run_id)
            index[idempotency_key] = {"event": event, "content_fingerprint": content_fingerprint}
            _write_json(self._idempotency_index_path(run_id), index)

        result = dict(event)
        result["content_fingerprint"] = content_fingerprint
        self.replay(run_id)
        return result
