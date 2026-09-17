#!/usr/bin/env python3
"""Propose and approve a versioned, pre-implementation TailTrail plan revision."""
from __future__ import annotations

import argparse
import copy
import hashlib
import importlib.util
import json
import sys
from datetime import datetime, timezone
from pathlib import Path
from typing import Any


ROOT = Path(__file__).resolve().parents[1]
if str(ROOT / "scripts") not in sys.path:
    sys.path.insert(0, str(ROOT / "scripts"))
import navigator_scope as SCOPE
from workflow_runtime import start_integration as WORKFLOW_START
BOUNDARY = (
    "A plan revision changes only versioned TailTrail planning metadata. It does not inspect or edit project "
    "source, run tests, scanners, builds, package managers, Git, or implementation commands."
)
CHANGE_KINDS = {"scope-add", "scope-remove", "requirement-add", "requirement-remove", "requirement-update", "proof-update"}
STANDARD_MODE_FEATURES = {
    "included": [
        "Navigator planning and Planning Lock",
        "Verified official AI-DLC Requirements Analysis, executed by the configured host",
        "TailTrail advisory recommendation and reasoning attached to each official host-generated question",
        "Canonical approved anchor and requirement-linked execution handoff",
    ],
    "not_included": ["The remaining Full official lifecycle stages after Requirements Analysis"],
}


def module(name: str, filename: str) -> Any:
    spec = importlib.util.spec_from_file_location(name, ROOT / "scripts" / filename)
    loaded = importlib.util.module_from_spec(spec)
    assert spec and spec.loader
    spec.loader.exec_module(loaded)
    return loaded


LOCK = module("planning_revision_lock", "planning_lock.py")
LEDGER = module("planning_revision_ledger", "run-ledger.py")
ANCHOR = module("planning_revision_anchor", "change-intent-anchor.py")
REQUIREMENTS = module("planning_revision_requirements", "requirement_discovery.py")
INTENT_BRIDGE = module("planning_revision_intent_bridge", "spec-kit-bridge.py")
OFFICIAL_BRIDGE = module("planning_revision_official_bridge", "aidlc-official-bridge.py")


def utc_now() -> str:
    return datetime.now(timezone.utc).replace(microsecond=0).isoformat()


def canonical(value: Any) -> str:
    return json.dumps(value, sort_keys=True, separators=(",", ":"))


def fingerprint(value: Any) -> str:
    return "sha256:" + hashlib.sha256(canonical(value).encode("utf-8")).hexdigest()


def revision_dir(root: Path, run_id: str) -> Path:
    return LEDGER.state_dir(root, run_id) / "planning" / "revisions"


def revision_path(root: Path, run_id: str, number: int) -> Path:
    return revision_dir(root, run_id) / f"revision-v{number}.json"


def revision_report_path(root: Path, run_id: str, number: int) -> Path:
    return revision_dir(root, run_id) / f"start-report-v{number}.json"


def route_dir(root: Path, run_id: str) -> Path:
    return LEDGER.state_dir(root, run_id) / "planning" / "authority-routes"


def route_path(root: Path, run_id: str, number: int) -> Path:
    return route_dir(root, run_id) / f"route-{number:03d}.json"


def _safe_text(value: Any, field: str, *, required: bool = True) -> str:
    result = str(value or "").strip()
    if required and not result:
        raise ValueError(f"revision change needs `{field}`")
    if len(result) > 500 or "\x00" in result:
        raise ValueError(f"revision change `{field}` must be a bounded safe text value")
    return result


def _safe_path(value: Any) -> str:
    path = Path(_safe_text(value, "path"))
    if path.is_absolute() or ".." in path.parts or path.as_posix() in {"", "."}:
        raise ValueError("revision change path must be repository-relative without parent traversal")
    return path.as_posix()


def _list_of_text(value: Any, field: str) -> list[str]:
    if not isinstance(value, list) or not value:
        raise ValueError(f"revision change `{field}` must be a non-empty list")
    result = [_safe_text(item, field) for item in value]
    return list(dict.fromkeys(result))


def _requirements(report: dict[str, Any], root: Path, run_id: str) -> list[dict[str, Any]]:
    navigator = report.setdefault("navigator", {})
    if not isinstance(navigator, dict):
        raise ValueError("saved Navigator report is invalid")
    matrix = navigator.get("requirement_matrix")
    if not isinstance(matrix, list) or not matrix:
        # The helper reads the current immutable/active report, which is exactly this base revision.
        generated = LOCK._proposal_from_start_report(root, run_id)  # type: ignore[attr-defined]
        matrix = generated.get("requirements", []) if isinstance(generated, dict) else []
        navigator["requirement_matrix"] = matrix
    normalized: list[dict[str, Any]] = []
    for index, raw in enumerate(matrix, start=1):
        if not isinstance(raw, dict):
            raise ValueError("saved requirement matrix contains an invalid row")
        row = copy.deepcopy(raw)
        statement = _safe_text(row.get("statement"), "statement")
        row["statement"] = statement
        row["display_id"] = _safe_text(row.get("display_id") or f"REQ-{index:02d}", "display_id")
        row["requirement_uid"] = _safe_text(row.get("requirement_uid") or ANCHOR.uid(run_id, statement), "requirement_uid")
        row.setdefault("kind", "change")
        row.setdefault("acceptance_criteria", ["The approved outcome is observable through its named evidence."])
        row.setdefault("preserve_rules", ["Do not change behavior outside the approved scope."])
        row.setdefault("likely_paths", [])
        row.setdefault("evidence_plan", ["Run the focused validation selected by the approved Navigator plan."])
        normalized.append(row)
    navigator["requirement_matrix"] = normalized
    return normalized


def _requirement(rows: list[dict[str, Any]], value: Any) -> dict[str, Any]:
    identifier = _safe_text(value, "requirement_uid")
    matches = [row for row in rows if identifier in {str(row.get("requirement_uid")), str(row.get("display_id"))}]
    if len(matches) != 1:
        raise ValueError(f"revision change references unknown requirement `{identifier}`")
    return matches[0]


def _impact_rows(report: dict[str, Any]) -> list[dict[str, Any]]:
    navigator = report.setdefault("navigator", {})
    values = navigator.setdefault("likely_impacted_files", [])
    if not isinstance(values, list):
        raise ValueError("saved Navigator impact list is invalid")
    return values


def _add_impact(report: dict[str, Any], path: str, reason: str) -> None:
    impacts = _impact_rows(report)
    if not any(isinstance(row, dict) and row.get("path") == path for row in impacts):
        impacts.append({"path": path, "reason": f"user-approved planning revision: {reason}"})


def _remove_impact_if_unreferenced(report: dict[str, Any], rows: list[dict[str, Any]], path: str) -> None:
    if any(path in row.get("likely_paths", []) for row in rows):
        return
    navigator = report["navigator"]
    navigator["likely_impacted_files"] = [
        row for row in _impact_rows(report)
        if not (isinstance(row, dict) and row.get("path") == path)
    ]


def _new_display_id(rows: list[dict[str, Any]]) -> str:
    used = {str(row.get("display_id", "")) for row in rows}
    index = 1
    while f"REQ-{index:02d}" in used:
        index += 1
    return f"REQ-{index:02d}"


def _sync_requirement_projections(report: dict[str, Any], rows: list[dict[str, Any]], removed_display_ids: set[str]) -> None:
    """Keep derived plan projections aligned with the revised requirement matrix."""
    active_display_ids = {str(row.get("display_id")) for row in rows}
    active_requirement_ids = {
        str(row.get("requirement_id") or REQUIREMENTS.stable_requirement_id(str(row.get("statement", ""))))
        for row in rows
    }
    # Derived projections use both human-facing display IDs and stable query
    # frame IDs. Resolve the stable IDs of removed rows before pruning so a
    # revision cannot retain either representation, while active stable IDs do
    # not trigger the stale-reference gate.
    removed_requirement_ids: set[str] = set()
    navigator = report.get("navigator") if isinstance(report.get("navigator"), dict) else {}
    frame = navigator.get("requirement_query_frame") if isinstance(navigator, dict) else None
    if isinstance(frame, dict):
        for item in frame.get("requirements", []):
            if isinstance(item, dict) and str(item.get("display_id", "")) in removed_display_ids:
                removed_requirement_ids.add(str(item.get("requirement_id", "")))
    allowed_requirement_references = active_display_ids | active_requirement_ids
    removed_requirement_references = removed_display_ids | removed_requirement_ids

    def prune(value: Any) -> None:
        if isinstance(value, dict):
            for key, item in list(value.items()):
                if key == "requirement_ids" and isinstance(item, list):
                    value[key] = [identifier for identifier in item if str(identifier) not in removed_requirement_references]
                    continue
                if isinstance(item, list):
                    value[key] = [
                        child for child in item
                        if not (
                            isinstance(child, dict)
                            and str(child.get("display_id", "")) in removed_display_ids
                        )
                    ]
                    for child in value[key]:
                        prune(child)
                else:
                    prune(item)
        elif isinstance(value, list):
            for item in value:
                prune(item)

    prune(report)
    navigator = report.setdefault("navigator", {})
    frame = navigator.get("requirement_query_frame")
    if isinstance(frame, dict):
        framed_rows: list[dict[str, Any]] = []
        combined_terms: list[str] = []
        for row in rows:
            terms = REQUIREMENTS.query_terms(str(row.get("statement", "")))
            row["query_terms"] = terms
            stable_id = str(row.get("requirement_id") or REQUIREMENTS.stable_requirement_id(str(row.get("statement", ""))))
            row["requirement_id"] = stable_id
            framed_rows.append({
                "display_id": str(row.get("display_id")),
                "requirement_id": stable_id,
                "statement": str(row.get("statement", "")),
                "query_terms": terms,
            })
            combined_terms.extend(terms)
        frame["requirements"] = framed_rows
        frame["query_terms"] = list(dict.fromkeys(combined_terms))

    # Fail closed if a known derived requirement-id collection retained a
    # removed display ID. This catches new projections until they are wired to
    # the canonical matrix instead of silently publishing contradictory plans.
    def stale_references(value: Any, path: str = "report") -> list[str]:
        stale: list[str] = []
        if isinstance(value, dict):
            for key, item in value.items():
                child_path = f"{path}.{key}"
                if key == "requirement_ids" and isinstance(item, list):
                    stale.extend(
                        f"{child_path}:{identifier}"
                        for identifier in item
                        if str(identifier) not in allowed_requirement_references
                    )
                else:
                    stale.extend(stale_references(item, child_path))
        elif isinstance(value, list):
            for index, item in enumerate(value):
                stale.extend(stale_references(item, f"{path}[{index}]"))
        return stale

    stale = stale_references(report)
    if stale:
        raise ValueError("revised plan retained stale requirement references: " + ", ".join(stale[:5]))


def _v2_scope(report: dict[str, Any]) -> dict[str, Any] | None:
    navigator = report.get("navigator") if isinstance(report.get("navigator"), dict) else {}
    evidence = navigator.get("scope_evidence") if isinstance(navigator, dict) else None
    return evidence if isinstance(evidence, dict) and str(evidence.get("schema_version")) == "2" else None


def _scope_requirement(evidence: dict[str, Any], row: dict[str, Any]) -> dict[str, Any]:
    identifiers = {
        str(row.get("display_id", "")),
        str(row.get("requirement_id", "")),
    }
    matches = [
        item for item in evidence.get("requirements", [])
        if isinstance(item, dict)
        and ({str(item.get("display_id", "")), str(item.get("requirement_id", ""))} & identifiers)
    ]
    if len(matches) != 1:
        raise ValueError(f"v2 scope evidence does not contain exactly one row for `{row.get('display_id', 'requirement')}`")
    return matches[0]


def _explicit_scope_authority(change: dict[str, Any]) -> bool:
    return change.get("scope_authority") == "explicit-user-scope" and change.get("confirmed") is True


def _candidate(evidence: dict[str, Any], path: str) -> dict[str, Any] | None:
    return next((row for row in evidence.get("candidates", []) if isinstance(row, dict) and row.get("path") == path), None)


def _ensure_v2_requirement(evidence: dict[str, Any], row: dict[str, Any]) -> dict[str, Any]:
    try:
        return _scope_requirement(evidence, row)
    except ValueError:
        candidates = [item for item in evidence.get("candidates", []) if isinstance(item, dict)]
        created = {
            "requirement_id": str(row.get("requirement_id") or row.get("display_id")),
            "display_id": str(row.get("display_id", "")),
            "statement_fingerprint": SCOPE.fingerprint(str(row.get("statement", ""))),
            "query_terms": REQUIREMENTS.query_terms(str(row.get("statement", ""))),
            "scope_state": "unresolved",
            "implementation_owners": [],
            "inspection_paths": sorted(str(item.get("path")) for item in candidates if item.get("status") == "inspection-only"),
            "proof_paths": sorted(str(item.get("path")) for item in candidates if item.get("status") == "proof-only"),
            "excluded_candidates": [
                {"path": str(item.get("path")), "reason_codes": list(item.get("reason_codes", []))}
                for item in candidates if item.get("status") in {"excluded", "rejected"}
            ],
            "confidence": "none",
            "reason_codes": ["ownership-evidence-required"],
        }
        evidence.setdefault("requirements", []).append(created)
        return created


def _change_v2_owner(
    root: Path,
    report: dict[str, Any],
    row: dict[str, Any],
    path: str,
    change: dict[str, Any],
    *,
    remove: bool,
) -> dict[str, Any]:
    evidence = _v2_scope(report)
    if evidence is None:
        return {}
    requirement = _ensure_v2_requirement(evidence, row)
    owners = [str(value) for value in requirement.get("implementation_owners", []) if isinstance(value, str)]
    if remove:
        requirement["implementation_owners"] = [value for value in owners if value != path]
        return {"scope_authority": "saved-v2-decision", "confirmed": True}

    candidate = _candidate(evidence, path)
    if candidate is not None and candidate.get("role") == "test":
        raise ValueError(
            f"`{path}` is proof-only test evidence and cannot become an implementation owner in a code-change revision; use a test-only requirement boundary instead"
        )
    evidence_backed = bool(
        candidate
        and candidate.get("role") == "implementation-owner"
        and candidate.get("status") == "included"
        and (candidate.get("evidence_edge_ids") or "explicit-path" in candidate.get("seed_sources", []))
    )
    explicit = _explicit_scope_authority(change)
    if not evidence_backed and not explicit:
        raise ValueError(
            f"scope-add for `{path}` needs saved implementation-owner evidence or `scope_authority: explicit-user-scope` with `confirmed: true`"
        )
    if candidate is None:
        generated = SCOPE.candidates_from_seeds(
            root,
            [SCOPE.seed(path, "explicit-path", "explicit-user-scope-confirmed")],
            report.get("navigator", {}).get("task_types", []),
        )
        candidate = next((item for item in generated if item.get("path") == path), None)
        if candidate is None:
            raise ValueError(f"explicit scope path `{path}` could not be classified inside the target repository")
        if candidate.get("role") != "implementation-owner":
            raise ValueError(f"explicit scope path `{path}` is `{candidate.get('role')}`, not an implementation-owner path")
        evidence.setdefault("candidates", []).append(candidate)
    elif explicit and candidate.get("role") == "implementation-owner":
        candidate["status"] = "included"
        candidate["confidence"] = "high"
        candidate["seed_sources"] = sorted(set(candidate.get("seed_sources", [])) | {"explicit-path"})
        candidate["reason_codes"] = sorted(set(candidate.get("reason_codes", [])) | {"explicit-user-scope-confirmed"})
        provenance = list(candidate.get("evidence_provenance", []))
        explicit_provenance = {"source": "explicit-path", "strength": "strong", "kind": "discovery-seed"}
        if explicit_provenance not in provenance:
            provenance.append(explicit_provenance)
        candidate["evidence_provenance"] = provenance
    requirement["implementation_owners"] = sorted(set(owners) | {path})
    return {
        "scope_authority": "saved-v2-evidence" if evidence_backed else "explicit-user-scope",
        "confirmed": True,
        "evidence_edge_ids": list(candidate.get("evidence_edge_ids", [])),
    }


def _finalize_v2_scope(root: Path, run_id: str, report: dict[str, Any], rows: list[dict[str, Any]], revision: int) -> None:
    evidence = _v2_scope(report)
    if evidence is None:
        return
    active_display_ids = {str(row.get("display_id")) for row in rows}
    evidence["requirements"] = [
        item for item in evidence.get("requirements", [])
        if isinstance(item, dict) and str(item.get("display_id")) in active_display_ids
    ]
    candidates = [item for item in evidence.get("candidates", []) if isinstance(item, dict)]
    by_path = {str(item.get("path")): item for item in candidates}
    for row in rows:
        requirement = _ensure_v2_requirement(evidence, row)
        requirement["statement_fingerprint"] = SCOPE.fingerprint(str(row.get("statement", "")))
        requirement["query_terms"] = REQUIREMENTS.query_terms(str(row.get("statement", "")))
        owners = sorted(set(str(value) for value in requirement.get("implementation_owners", []) if str(value)))
        requirement["implementation_owners"] = owners
        requirement["scope_state"] = "resolved" if owners else "unresolved"
        confidences = [str(by_path.get(path, {}).get("confidence", "none")) for path in owners]
        requirement["confidence"] = "high" if "high" in confidences else "medium" if "medium" in confidences else "low" if owners else "none"
        requirement["reason_codes"] = ["planning-revision-owner-confirmed"] if owners else ["ownership-evidence-required"]
        row["likely_paths"] = owners
        row["scope_evidence"] = {
            "decision_fingerprint": None,
            "implementation_owners": owners,
            "inspection_paths": list(requirement.get("inspection_paths", [])),
            "proof_paths": list(requirement.get("proof_paths", [])),
            "confidence": requirement["confidence"],
            "reason_codes": list(requirement["reason_codes"]),
        }
    evidence["state"] = "resolved" if all(item.get("scope_state") == "resolved" for item in evidence["requirements"]) else "unresolved"
    evidence["host_reasoning"] = {
        "state": "recorded",
        "proposal": {
            "source": "versioned-planning-revision",
            "revision": revision,
            "private_reasoning_excluded": True,
        },
    }
    evidence["summary"] = {
        "included": sum(item.get("status") == "included" for item in candidates),
        "inspection_only": sum(item.get("status") == "inspection-only" for item in candidates),
        "proof_only": sum(item.get("status") == "proof-only" for item in candidates),
        "excluded": sum(item.get("status") == "excluded" for item in candidates),
        "rejected": sum(item.get("status") == "rejected" for item in candidates),
    }
    investigation = evidence.get("investigation") if isinstance(evidence.get("investigation"), dict) else {}
    investigation["evidence_packet_fingerprint"] = SCOPE.fingerprint({
        "requirements": sorted(str(item.get("requirement_id")) for item in evidence["requirements"]),
        "candidates": sorted((str(item.get("path")), str(item.get("candidate_id"))) for item in candidates),
        "edges": sorted(str(item.get("edge_id")) for item in evidence.get("edges", []) if isinstance(item, dict)),
        "limits": evidence.get("limits", {}),
        "revision": revision,
    })
    evidence["investigation"] = investigation
    evidence.pop("decision_fingerprint", None)
    evidence["decision_fingerprint"] = SCOPE.fingerprint(evidence)
    for row in rows:
        row["scope_evidence"]["decision_fingerprint"] = evidence["decision_fingerprint"]
    navigator = report.setdefault("navigator", {})
    navigator["scope_evidence"] = evidence
    navigator["scope_host_packet"] = SCOPE.host_reasoning_packet(evidence)
    navigator["scope_quality"] = SCOPE.assess_scope_quality(
        root,
        str(report.get("goal", "")),
        navigator.get("task_types", []),
        evidence,
    )
    if navigator["scope_quality"].get("blocking") is not False:
        raise ValueError("revised v2 scope does not pass the scope-quality gate: " + ", ".join(navigator["scope_quality"].get("reason_codes", [])))
    navigator["likely_impacted_files"] = SCOPE.project_likely_impacted(candidates)
    lock = LOCK.show(root, run_id)
    binding = SCOPE.decision_binding(root, evidence, lock.get("target_identity", {}))
    original = lock.get("scope_decision", {})
    report["scope_decision_revision"] = {
        "schema_version": "1",
        "type": "tailtrail-scope-decision-revision",
        "revision": revision,
        "base_decision_fingerprint": original.get("decision_fingerprint"),
        "scope_decision": binding,
        "authority": "versioned-planning-revision",
    }
    descriptor = report.get("workflow_runtime")
    if isinstance(descriptor, dict):
        descriptor["scope_binding"] = WORKFLOW_START.scope_binding(report)


def _apply_change(root: Path, report: dict[str, Any], rows: list[dict[str, Any]], change: dict[str, Any], run_id: str) -> dict[str, Any]:
    kind = _safe_text(change.get("kind"), "kind")
    if kind not in CHANGE_KINDS:
        raise ValueError(f"unsupported revision change kind `{kind}`")
    reason = _safe_text(change.get("reason"), "reason")
    normalized: dict[str, Any] = {"kind": kind, "reason": reason}
    if kind in {"scope-add", "scope-remove"}:
        row = _requirement(rows, change.get("requirement_uid"))
        path = _safe_path(change.get("path"))
        paths = [str(item) for item in row.get("likely_paths", []) if isinstance(item, str)]
        if kind == "scope-add":
            if path in paths:
                raise ValueError(f"`{path}` is already in requirement `{row['display_id']}` scope")
            row["likely_paths"] = [*paths, path]
            _add_impact(report, path, reason)
            normalized.update(_change_v2_owner(root, report, row, path, change, remove=False))
        else:
            if path not in paths:
                raise ValueError(f"`{path}` is not in requirement `{row['display_id']}` scope")
            row["likely_paths"] = [item for item in paths if item != path]
            _remove_impact_if_unreferenced(report, rows, path)
            normalized.update(_change_v2_owner(root, report, row, path, change, remove=True))
        normalized.update({"requirement_uid": row["requirement_uid"], "display_id": row["display_id"], "path": path})
    elif kind == "requirement-update":
        row = _requirement(rows, change.get("requirement_uid"))
        if _v2_scope(report) is not None and change.get("retain_scope_confirmed") is not True:
            raise ValueError("v2 requirement-update needs `retain_scope_confirmed: true` so ownership is not silently carried across changed wording")
        row["statement"] = _safe_text(change.get("statement"), "statement")
        if row.get("requirement_id"):
            row["requirement_id"] = REQUIREMENTS.stable_requirement_id(row["statement"])
        if row.get("query_terms"):
            row["query_terms"] = REQUIREMENTS.query_terms(row["statement"])
        normalized.update({"requirement_uid": row["requirement_uid"], "display_id": row["display_id"], "statement": row["statement"]})
    elif kind == "proof-update":
        row = _requirement(rows, change.get("requirement_uid"))
        row["evidence_plan"] = _list_of_text(change.get("evidence_plan"), "evidence_plan")
        normalized.update({"requirement_uid": row["requirement_uid"], "display_id": row["display_id"], "evidence_plan": row["evidence_plan"]})
    elif kind == "requirement-add":
        statement = _safe_text(change.get("statement"), "statement")
        display_id = _safe_text(change.get("display_id") or _new_display_id(rows), "display_id")
        if any(row["display_id"] == display_id for row in rows):
            raise ValueError(f"requirement display ID `{display_id}` already exists")
        paths = [_safe_path(item) for item in change.get("likely_paths", [])] if isinstance(change.get("likely_paths", []), list) else []
        row = {
            "requirement_uid": ANCHOR.uid(run_id, statement), "display_id": display_id, "kind": change.get("requirement_kind", "change"),
            "requirement_id": REQUIREMENTS.stable_requirement_id(statement), "query_terms": REQUIREMENTS.query_terms(statement),
            "statement": statement, "acceptance_criteria": _list_of_text(change.get("acceptance_criteria"), "acceptance_criteria"),
            "preserve_rules": _list_of_text(change.get("preserve_rules"), "preserve_rules"), "likely_paths": list(dict.fromkeys(paths)),
            "evidence_plan": _list_of_text(change.get("evidence_plan"), "evidence_plan"),
        }
        if row["kind"] not in ANCHOR.KINDS:
            raise ValueError("requirement_kind is not allowed")
        rows.append(row)
        evidence = _v2_scope(report)
        if evidence is not None:
            _ensure_v2_requirement(evidence, row)
        for path in row["likely_paths"]:
            _add_impact(report, path, reason)
        normalized.update({"requirement_uid": row["requirement_uid"], "display_id": display_id, "statement": statement})
    else:  # requirement-remove
        row = _requirement(rows, change.get("requirement_uid"))
        if len(rows) == 1:
            raise ValueError("a plan revision must retain at least one requirement")
        rows.remove(row)
        evidence = _v2_scope(report)
        if evidence is not None:
            evidence["requirements"] = [
                item for item in evidence.get("requirements", [])
                if not isinstance(item, dict) or str(item.get("display_id")) != str(row.get("display_id"))
            ]
        for path in row.get("likely_paths", []):
            _remove_impact_if_unreferenced(report, rows, str(path))
        normalized.update({"requirement_uid": row["requirement_uid"], "display_id": row["display_id"]})
    return normalized


def _delta(base: list[dict[str, Any]], revised: list[dict[str, Any]]) -> dict[str, Any]:
    base_by_uid = {row["requirement_uid"]: row for row in base}
    revised_by_uid = {row["requirement_uid"]: row for row in revised}
    changed = sorted(uid for uid in set(base_by_uid) & set(revised_by_uid) if canonical(base_by_uid[uid]) != canonical(revised_by_uid[uid]))
    paths_before = {path for row in base for path in row.get("likely_paths", [])}
    paths_after = {path for row in revised for path in row.get("likely_paths", [])}
    proof_changed = sorted(uid for uid in set(base_by_uid) & set(revised_by_uid) if base_by_uid[uid].get("evidence_plan") != revised_by_uid[uid].get("evidence_plan"))
    return {
        "requirements_changed": sorted([*changed, *(uid for uid in revised_by_uid if uid not in base_by_uid), *(uid for uid in base_by_uid if uid not in revised_by_uid)]),
        "scope_added": sorted(paths_after - paths_before),
        "scope_removed": sorted(paths_before - paths_after),
        "proof_changed": proof_changed,
    }


def _route_context(changes: list[dict[str, Any]]) -> list[dict[str, Any]]:
    """Persist only structured revision intent, never raw conversation text."""
    values: list[dict[str, Any]] = []
    for change in changes:
        kind = _safe_text(change.get("kind"), "kind")
        if kind not in CHANGE_KINDS:
            raise ValueError(f"unsupported revision change kind `{kind}`")
        row = {"kind": kind, "reason": _safe_text(change.get("reason"), "reason")}
        for field in ("requirement_uid", "display_id", "path"):
            if change.get(field) is not None:
                row[field] = _safe_text(change.get(field), field)
        values.append(row)
    return values


def _is_aidlc_bound(report: dict[str, Any]) -> bool:
    return isinstance(report.get("aidlc_requirements"), dict) or (report.get("aidlc_mode", {}) or {}).get("mode") == "full"


def _official_design_route(context: list[dict[str, Any]]) -> bool:
    text = " ".join(item.get("reason", "") for item in context).lower()
    return any(word in text for word in ("architecture", "architectural", "design", "data model", "public contract"))


def _route_aidlc(root: Path, run_id: str, report: dict[str, Any], context: list[dict[str, Any]]) -> dict[str, Any]:
    full = (report.get("aidlc_mode", {}) or {}).get("mode") == "full"
    route = "official-aidlc-design" if full and _official_design_route(context) else ("official-aidlc-requirements" if full else "aidlc-requirements")
    existing = sorted(route_dir(root, run_id).glob("route-*.json"))
    number = len(existing) + 1
    destination = route_path(root, run_id, number)
    payload = {
        "schema_version": "1", "type": "tailtrail-planning-authority-route", "run_id": run_id,
        "route_id": f"route-{number:03d}", "authority": "official-ai-dlc-pack" if full else "aidlc-requirements",
        "route": route, "state": "authority-refinement-required", "revision_context": context,
        "boundary": "TailTrail did not create a parallel local plan revision. AIDLC owns requirement/design refinement; TailTrail preserves the Planning Lock, evidence, and later anchor controls.",
        "created_at": utc_now(),
    }
    if route == "official-aidlc-design":
        payload["next"] = "Run the verified official AI-DLC Design stage through the configured host, then return its sanitized stage outcome before a new requirement boundary is approved."
        LEDGER.atomic_json(destination, payload)
        LEDGER.append_event(root, run_id, "planning_authority_routed", {"route": route, "artifact": destination.relative_to(root).as_posix()})
        return {**payload, "artifact": destination.relative_to(root).as_posix()}
    refinement = LOCK.request_aidlc_requirements(root, run_id, context)
    payload["refinement_artifact"] = refinement["artifact"]
    payload["next"] = "Answer the AIDLC requirement questions, review its revised boundary, then use the existing AIDLC approval gate."
    LEDGER.atomic_json(destination, payload)
    LEDGER.append_event(root, run_id, "planning_authority_routed", {"route": route, "artifact": destination.relative_to(root).as_posix(), "refinement": refinement["artifact"]})
    return {**payload, "artifact": destination.relative_to(root).as_posix(), "aidlc_refinement": refinement}


def _route_intent_bridge(root: Path, run_id: str, report: dict[str, Any], context: list[dict[str, Any]]) -> dict[str, Any]:
    source = report["spec_kit_source"]
    feature = str(source.get("feature_id", "")).strip()
    if not feature:
        raise ValueError("Intent Bridge report has no feature identifier")
    current = INTENT_BRIDGE.load(root, feature)
    source_changed = current.get("source_revision") != source.get("source_revision") or current.get("import") != source.get("import")
    existing = sorted(route_dir(root, run_id).glob("route-*.json"))
    number = len(existing) + 1
    destination = route_path(root, run_id, number)
    payload = {
        "schema_version": "1", "type": "tailtrail-planning-authority-route", "run_id": run_id,
        "route_id": f"route-{number:03d}", "authority": "intent-bridge-source", "route": "intent-bridge-amendment",
        "state": "source-amendment-required", "feature_id": feature,
        "saved_source_revision": source.get("source_revision"), "current_source_revision": current.get("source_revision"),
        "source_changed": source_changed, "revision_context": context,
        "boundary": "The imported requirement wording remains source-owned. TailTrail recorded an amendment request only; it did not rewrite imported requirements, source artifacts, or the Start report.",
        "created_at": utc_now(),
    }
    if source_changed:
        payload["next"] = "The imported source changed. Use the existing Intent Bridge amendment workflow for an activated run, or restart pre-approval planning from the newly imported source snapshot; do not apply a local wording revision."
    else:
        payload["next"] = "Update the authoritative requirement source, explicitly import its new snapshot, then create/review planning from that source. The current imported wording remains unchanged."
    LEDGER.atomic_json(destination, payload)
    LEDGER.append_event(root, run_id, "planning_authority_routed", {"route": payload["route"], "artifact": destination.relative_to(root).as_posix(), "source_changed": source_changed})
    return {**payload, "artifact": destination.relative_to(root).as_posix()}


def propose_aidlc_standard(root: Path, run_id: str, approved_proposal: bool) -> dict[str, Any]:
    """Create a reviewed Lite-to-Standard lifecycle proposal without starting AIDLC."""
    if approved_proposal is not True:
        raise ValueError("AIDLC Standard mode proposal requires --approved-proposal")
    root = root.resolve()
    LOCK.assert_discussion_allowed(root, run_id)
    state = LOCK.revision_state(root, run_id)
    if state.get("pending_revision") is not None:
        raise ValueError(f"plan revision v{state['pending_revision']} is already awaiting approval; approve or supersede it first")
    saved = LOCK.active_start_report(root, run_id)
    report = copy.deepcopy(saved.get("report"))
    if not isinstance(report, dict):
        raise ValueError("active Start report is invalid")
    current = (report.get("aidlc_mode") or {}).get("mode", "lite")
    if current != "lite":
        raise ValueError(f"only an awaiting Lite run may switch to Standard AIDLC; this run is `{current}`")
    if isinstance(report.get("spec_kit_source"), dict):
        raise ValueError("Intent Bridge requirements are source-owned; use its amendment/authority route instead of a local Standard AIDLC switch")
    number = int(state.get("active_revision", 1)) + 1
    report["aidlc_mode"] = {
        "mode": "standard",
        "selection": "interactive-plan-proposal",
        "state": "awaiting-mode-approval",
        "boundary": "The requested Standard AIDLC Requirements stage begins only after this exact mode-switch revision is approved.",
    }
    report["aidlc_mode_features"] = copy.deepcopy(STANDARD_MODE_FEATURES)
    proposal = {
        "schema_version": "1", "type": "tailtrail-aidlc-mode-switch", "run_id": run_id,
        "revision": number, "base_revision": int(state.get("active_revision", 1)), "state": "awaiting-approval",
        "from_mode": "lite", "to_mode": "standard", "approval_required": True,
        "base_report_fingerprint": fingerprint(saved.get("report", {})), "revised_report_fingerprint": fingerprint(report),
        "added_controls": STANDARD_MODE_FEATURES["included"][1:], "not_included": STANDARD_MODE_FEATURES["not_included"],
        "boundary": "This proposal changes only TailTrail planning metadata. It does not start AIDLC questions, inspect project source, run tests, edit source, or permit implementation.",
        "created_at": utc_now(), "proposed_report": report,
    }
    destination = revision_path(root, run_id, number)
    with LEDGER.RunLock(LEDGER.state_dir(root, run_id) / ".lock"):
        LEDGER.atomic_json(destination, proposal)
        LEDGER.atomic_json(LOCK.revision_state_path(root, run_id), {**state, "pending_revision": number, "pending_artifact": destination.relative_to(root).as_posix()})
    LEDGER.append_event(root, run_id, "planning_aidlc_mode_switch_proposed", {"revision": number, "from_mode": "lite", "to_mode": "standard", "artifact": destination.relative_to(root).as_posix()})
    return {**proposal, "artifact": destination.relative_to(root).as_posix()}


def propose(
    root: Path,
    run_id: str,
    changes_json: str,
    approved_proposal: bool,
    supersede_pending: bool = False,
) -> dict[str, Any]:
    if approved_proposal is not True:
        raise ValueError("planning revision proposal requires --approved-proposal")
    root = root.resolve()
    LOCK.assert_discussion_allowed(root, run_id)
    state = LOCK.revision_state(root, run_id)
    pending_revision = state.get("pending_revision")
    if pending_revision is not None and not supersede_pending:
        raise ValueError(f"plan revision v{state['pending_revision']} is already awaiting approval; approve or supersede it first")
    if supersede_pending and pending_revision is None:
        raise ValueError("no pending plan revision exists to supersede")
    payload = LOCK.active_start_report(root, run_id)
    report = copy.deepcopy(payload.get("report"))
    if not isinstance(report, dict):
        raise ValueError("active Start report is invalid")
    try:
        changes = json.loads(changes_json)
    except json.JSONDecodeError as error:
        raise ValueError(f"revision changes must be valid JSON: {error}") from error
    if not isinstance(changes, list) or not changes:
        raise ValueError("revision changes must be a non-empty JSON list")
    if not all(isinstance(item, dict) for item in changes):
        raise ValueError("every revision change must be an object")
    context = _route_context(changes)
    if isinstance(report.get("spec_kit_source"), dict):
        return _route_intent_bridge(root, run_id, report, context)
    if _is_aidlc_bound(report):
        return _route_aidlc(root, run_id, report, context)
    rows = _requirements(report, root, run_id)
    base_rows = copy.deepcopy(rows)
    number = max(int(state.get("active_revision", 1)), int(pending_revision or 0)) + 1
    normalized_changes = [_apply_change(root, report, rows, item, run_id) for item in changes]
    removed_display_ids = {
        str(item.get("display_id"))
        for item in normalized_changes
        if item.get("kind") == "requirement-remove"
    }
    _sync_requirement_projections(report, rows, removed_display_ids)
    navigator = report.setdefault("navigator", {})
    navigator["requirement_matrix"] = rows
    # Hands-free v1 anchors normally derive rows from their feature program.
    # A reviewed IP-3 delta is the explicit replacement boundary for this run.
    navigator["revision_requirement_matrix"] = True
    _finalize_v2_scope(root, run_id, report, rows, number)
    proposed = {
        "schema_version": "1", "type": "tailtrail-plan-revision", "run_id": run_id,
        "revision": number, "base_revision": int(state.get("active_revision", 1)), "state": "awaiting-approval",
        "changes": normalized_changes, "delta_summary": _delta(base_rows, rows), "approval_required": True,
        "base_report_fingerprint": fingerprint(payload.get("report", {})), "revised_report_fingerprint": fingerprint(report),
        "requirement_continuity": [{"requirement_uid": row["requirement_uid"], "display_id": row["display_id"], "statement": row["statement"]} for row in rows],
        "rationale": [{"kind": item["kind"], "requirement_uid": item.get("requirement_uid"), "reason": item["reason"]} for item in normalized_changes],
        "boundary": BOUNDARY, "created_at": utc_now(), "proposed_report": report,
    }
    if pending_revision is not None:
        proposed["supersedes_revision"] = int(pending_revision)
    with LEDGER.RunLock(LEDGER.state_dir(root, run_id) / ".lock"):
        destination = revision_path(root, run_id, number)
        if destination.exists():
            raise ValueError(f"plan revision v{number} already exists")
        LEDGER.atomic_json(destination, proposed)
        superseded = list(state.get("superseded_revisions", [])) if isinstance(state.get("superseded_revisions", []), list) else []
        if pending_revision is not None:
            superseded.append({
                "revision": int(pending_revision),
                "superseded_by": number,
                "artifact": state.get("pending_artifact"),
            })
        next_state = {
            **state,
            "pending_revision": number,
            "pending_artifact": destination.relative_to(root).as_posix(),
            "superseded_revisions": superseded,
        }
        LEDGER.atomic_json(LOCK.revision_state_path(root, run_id), next_state)
    if pending_revision is not None:
        LEDGER.append_event(root, run_id, "planning_revision_superseded", {
            "revision": int(pending_revision),
            "superseded_by": number,
            "replacement_artifact": destination.relative_to(root).as_posix(),
        })
    LEDGER.append_event(root, run_id, "planning_revision_proposed", {
        "revision": number, "base_revision": proposed["base_revision"], "artifact": destination.relative_to(root).as_posix(),
        "requirement_uids": [item["requirement_uid"] for item in normalized_changes if item.get("requirement_uid")],
    })
    return {**proposed, "artifact": destination.relative_to(root).as_posix()}


def show(root: Path, run_id: str, revision: int | None = None) -> dict[str, Any]:
    root = root.resolve()
    state = LOCK.revision_state(root, run_id)
    number = revision if revision is not None else state.get("pending_revision")
    if number is None:
        raise ValueError(f"no proposed plan revision exists for run `{run_id}`")
    path = revision_path(root, run_id, int(number))
    if not path.is_file():
        raise ValueError(f"plan revision v{number} does not exist for run `{run_id}`")
    payload = {**json.loads(path.read_text(encoding="utf-8")), "artifact": path.relative_to(root).as_posix()}
    for item in state.get("superseded_revisions", []):
        if isinstance(item, dict) and item.get("revision") == int(number):
            payload["state"] = "superseded"
            payload["superseded_by_revision"] = item.get("superseded_by")
            break
    return payload


def authority_show(root: Path, run_id: str, sequence: int | None = None) -> dict[str, Any]:
    root = root.resolve()
    available = sorted(route_dir(root, run_id).glob("route-*.json"))
    if not available:
        raise ValueError(f"no AIDLC or Intent Bridge authority route exists for run `{run_id}`")
    path = route_path(root, run_id, sequence) if sequence is not None else available[-1]
    if not path.is_file():
        raise ValueError(f"authority route `{sequence}` does not exist for run `{run_id}`")
    return {**json.loads(path.read_text(encoding="utf-8")), "artifact": path.relative_to(root).as_posix()}


def approve(root: Path, run_id: str, revision: int, approved: bool) -> dict[str, Any]:
    if approved is not True:
        raise ValueError("plan revision approval requires --approved")
    root = root.resolve()
    LOCK.assert_discussion_allowed(root, run_id)
    state = LOCK.revision_state(root, run_id)
    if state.get("pending_revision") != revision:
        raise ValueError(f"plan revision v{revision} is not the current pending revision for run `{run_id}`")
    proposed = show(root, run_id, revision)
    if proposed["base_revision"] != state.get("active_revision"):
        raise ValueError("plan revision base no longer matches the active reviewed revision")
    if proposed["revised_report_fingerprint"] != fingerprint(proposed.get("proposed_report", {})):
        raise ValueError("plan revision artifact fingerprint does not match its proposed report")
    snapshot = {"schema_version": "1", "type": "tailtrail-start-report", "run_id": run_id, "revision": revision, "goal": proposed["proposed_report"].get("goal", ""), "report": proposed["proposed_report"]}
    report_path = revision_report_path(root, run_id, revision)
    old_state = copy.deepcopy(state)
    next_state = {**state, "active_revision": revision, "active_report": report_path.relative_to(root).as_posix(), "pending_revision": None, "pending_artifact": None}
    with LEDGER.RunLock(LEDGER.state_dir(root, run_id) / ".lock"):
        LEDGER.atomic_json(report_path, snapshot)
        LEDGER.atomic_json(LOCK.revision_state_path(root, run_id), next_state)
    try:
        activated = LOCK.activate(root, run_id, True)
    except Exception:
        LEDGER.atomic_json(LOCK.revision_state_path(root, run_id), old_state)
        raise
    LEDGER.append_event(root, run_id, "planning_revision_approved", {
        "revision": revision, "artifact": proposed["artifact"], "active_report": report_path.relative_to(root).as_posix(),
        "anchor": (activated.get("anchor") or {}).get("artifact"),
    })
    return {"run_id": run_id, "revision": revision, "state": "execution-ready", "revision_artifact": proposed["artifact"], "active_report": report_path.relative_to(root).as_posix(), **activated}


def approve_aidlc_standard(root: Path, run_id: str, revision: int, approved: bool) -> dict[str, Any]:
    """Accept the lifecycle revision and begin official Standard requirements in-place."""
    if approved is not True:
        raise ValueError("AIDLC Standard mode approval requires --approved")
    root = root.resolve()
    LOCK.assert_discussion_allowed(root, run_id)
    state = LOCK.revision_state(root, run_id)
    if state.get("pending_revision") != revision:
        raise ValueError(f"AIDLC Standard revision v{revision} is not the current pending revision for run `{run_id}`")
    proposed = show(root, run_id, revision)
    if proposed.get("type") != "tailtrail-aidlc-mode-switch" or proposed.get("to_mode") != "standard":
        raise ValueError(f"plan revision v{revision} is not a Lite-to-Standard AIDLC mode proposal")
    if proposed.get("base_revision") != state.get("active_revision") or proposed.get("revised_report_fingerprint") != fingerprint(proposed.get("proposed_report", {})):
        raise ValueError("AIDLC Standard mode proposal no longer matches the active reviewed plan")
    report = copy.deepcopy(proposed["proposed_report"])
    report["aidlc_mode"]["selection"] = "interactive-plan-approved-mode-switch"
    preflight = OFFICIAL_BRIDGE.preflight(root, "standard")
    if preflight["mode"] != "standard":
        report["aidlc_mode"] = {
            "mode": "lite",
            "requested_mode": "standard",
            "selection": "interactive-plan-approved-mode-switch",
            "state": preflight["state"],
            "boundary": preflight["boundary"],
        }
    else:
        report["aidlc_mode"]["state"] = "official-host-requirements-pending"
        report["official_aidlc_bridge"] = OFFICIAL_BRIDGE.create(root, run_id, str(report.get("goal", "")), mode="standard")
    report_path = revision_report_path(root, run_id, revision)
    snapshot = {"schema_version": "1", "type": "tailtrail-start-report", "run_id": run_id, "revision": revision, "goal": report.get("goal", ""), "report": report}
    with LEDGER.RunLock(LEDGER.state_dir(root, run_id) / ".lock"):
        LEDGER.atomic_json(report_path, snapshot)
        LEDGER.atomic_json(LOCK.revision_state_path(root, run_id), {**state, "active_revision": revision, "active_report": report_path.relative_to(root).as_posix(), "pending_revision": None, "pending_artifact": None})
    if preflight["mode"] != "standard":
        LEDGER.atomic_json(report_path, {**snapshot, "report": report})
        LEDGER.append_event(root, run_id, "planning_aidlc_mode_switch_fell_back", {"revision": revision, "from_mode": "lite", "requested_mode": "standard", "reason": preflight["boundary"]})
        return {"run_id": run_id, "revision": revision, "state": "tailtrail-lite-fallback", "revision_artifact": proposed["artifact"], "active_report": report_path.relative_to(root).as_posix(), "aidlc_mode": report["aidlc_mode"], "boundary": preflight["boundary"]}
    requirements = LOCK.request_official_aidlc_requirements(root, run_id)
    report["aidlc_requirements"] = requirements
    LEDGER.atomic_json(report_path, {**snapshot, "report": report})
    LEDGER.append_event(root, run_id, "planning_aidlc_mode_switch_approved", {"revision": revision, "from_mode": "lite", "to_mode": "standard", "artifact": proposed["artifact"], "active_report": report_path.relative_to(root).as_posix(), "requirements": requirements["artifact"]})
    return {"run_id": run_id, "revision": revision, "state": requirements["state"], "revision_artifact": proposed["artifact"], "active_report": report_path.relative_to(root).as_posix(), "aidlc_requirements": requirements, "boundary": "The run remains awaiting approval. The host must record its official Requirements Analysis questions; answers and explicit approval still block implementation."}


def render(payload: dict[str, Any]) -> str:
    lines = ["# TailTrail Plan Revision", "", f"**Run ID:** `{payload['run_id']}`", f"**Revision:** v{payload['base_revision']} -> v{payload['revision']}", "**State:** awaiting approval — no project source, tests, scanners, Git, or implementation commands were run.", "", "## Changed requirements", ""]
    for item in payload["changes"]:
        target = item.get("display_id", item.get("requirement_uid", "plan"))
        lines.append(f"- **{target}:** `{item['kind']}` — {item['reason']}")
    delta = payload["delta_summary"]
    lines.extend(["", "## Delta", "", f"- Requirement rows changed: {len(delta['requirements_changed'])}", f"- Scope added: {', '.join(f'`{item}`' for item in delta['scope_added']) or 'none'}", f"- Scope removed: {', '.join(f'`{item}`' for item in delta['scope_removed']) or 'none'}", f"- Proof rows changed: {', '.join(f'`{item}`' for item in delta['proof_changed']) or 'none'}"])
    report = payload.get("proposed_report", {})
    navigator = report.get("navigator", {}) if isinstance(report, dict) else {}
    evidence = navigator.get("scope_evidence") if isinstance(navigator, dict) else None
    if isinstance(evidence, dict) and str(evidence.get("schema_version")) == "2":
        projection = SCOPE.role_projection(evidence)
        lines.extend(["", "## Revised scope roles", "", f"- Decision fingerprint: `{projection.get('decision_fingerprint')}`."])
        for title, key in (("Implementation owners", "implementation_owners"), ("Inspection paths", "inspection_paths"), ("Existing proof paths", "proof_paths")):
            lines.extend(["", f"### {title}", "", "| Path | Requirements | Confidence |", "| --- | --- | --- |"])
            rows = projection.get(key, [])
            if rows:
                for row in rows:
                    lines.append(f"| `{row.get('path')}` | {', '.join(row.get('requirement_ids', []))} | `{row.get('confidence')}` |")
            else:
                lines.append("| none | none | `none` |")
    lines.extend(["", "## Approval", "", f"- Approve exactly v{payload['revision']} to freeze this revised plan into the immutable anchor and activate this same run.", "- A v1 approval cannot activate this v2-or-later proposal.", ""])
    return "\n".join(lines)


def render_aidlc_standard(payload: dict[str, Any]) -> str:
    lines = ["# TailTrail AIDLC Mode Switch", "", f"**Run ID:** `{payload['run_id']}`", f"**Revision:** v{payload['base_revision']} -> v{payload['revision']}", "**Mode:** `lite` -> `standard`", "**State:** awaiting approval — no AIDLC questions, project source, tests, scanners, Git, or implementation commands were run.", "", "## Added Standard AIDLC controls", ""]
    lines.extend(f"- {item}" for item in payload.get("added_controls", []))
    lines.extend(["", "## Still not included", ""])
    lines.extend(f"- {item}" for item in payload.get("not_included", []))
    lines.extend(["", "## Approval", "", f"- Approve exactly v{payload['revision']} to begin Standard AIDLC requirements under this same run ID.", "- This does not approve implementation. A separate AIDLC requirement-boundary approval remains required.", ""])
    return "\n".join(lines)


def render_authority_route(payload: dict[str, Any]) -> str:
    state = str(payload.get("state", "authority-refinement-required")).replace("-", " ")
    lines = ["# TailTrail Authority Route", "", f"**Run ID:** `{payload['run_id']}`", f"**Authority:** `{payload['authority']}`", f"**Route:** `{payload['route']}`", f"**State:** {state} — no project source, tests, scanners, Git, or implementation commands were run.", "", "## Requested material change", ""]
    for item in payload.get("revision_context", []):
        target = item.get("requirement_uid", item.get("display_id", "requirement boundary"))
        lines.append(f"- **{target}:** `{item['kind']}` — {item['reason']}")
    lines.extend(["", "## Next", "", f"- {payload['next']}", "", "## Boundary", "", f"- {payload['boundary']}", ""])
    return "\n".join(lines)


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    sub = parser.add_subparsers(dest="command", required=True)
    propose_parser = sub.add_parser("propose", help="Persist one explicitly authorized proposed plan revision.")
    propose_parser.add_argument("--root", type=Path, default=Path.cwd())
    propose_parser.add_argument("--run-id", required=True)
    source = propose_parser.add_mutually_exclusive_group(required=True)
    source.add_argument("--changes", help="JSON list of material revision changes.")
    source.add_argument("--changes-base64", help="Base64 UTF-8 JSON changes for Windows shell safety.")
    propose_parser.add_argument("--approved-proposal", action="store_true")
    propose_parser.add_argument("--supersede-pending", action="store_true", help="Preserve and replace the current unapproved pending revision.")
    show_parser = sub.add_parser("show", help="Show one saved plan revision.")
    show_parser.add_argument("--root", type=Path, default=Path.cwd())
    show_parser.add_argument("--run-id", required=True)
    show_parser.add_argument("--revision", type=int)
    authority_parser = sub.add_parser("authority-show", help="Show the latest AIDLC or Intent Bridge authority route.")
    authority_parser.add_argument("--root", type=Path, default=Path.cwd())
    authority_parser.add_argument("--run-id", required=True)
    authority_parser.add_argument("--sequence", type=int)
    mode_parser = sub.add_parser("aidlc-standard", help="Propose a versioned Lite-to-Standard AIDLC switch for an awaiting run.")
    mode_parser.add_argument("--root", type=Path, default=Path.cwd())
    mode_parser.add_argument("--run-id", required=True)
    mode_parser.add_argument("--approved-proposal", action="store_true")
    mode_approve_parser = sub.add_parser("aidlc-standard-approve", help="Approve the exact Lite-to-Standard revision and begin requirements gathering.")
    mode_approve_parser.add_argument("--root", type=Path, default=Path.cwd())
    mode_approve_parser.add_argument("--run-id", required=True)
    mode_approve_parser.add_argument("--revision", type=int, required=True)
    mode_approve_parser.add_argument("--approved", action="store_true")
    approve_parser = sub.add_parser("approve", help="Approve the exact proposed revision and activate the same run.")
    approve_parser.add_argument("--root", type=Path, default=Path.cwd())
    approve_parser.add_argument("--run-id", required=True)
    approve_parser.add_argument("--revision", type=int, required=True)
    approve_parser.add_argument("--approved", action="store_true")
    args = parser.parse_args()
    try:
        if args.command == "propose":
            changes = args.changes
            if args.changes_base64 is not None:
                import base64
                changes = base64.b64decode(args.changes_base64, validate=True).decode("utf-8")
            result = propose(args.root, args.run_id, str(changes), args.approved_proposal, args.supersede_pending)
            print(render_authority_route(result) if result.get("type") == "tailtrail-planning-authority-route" else render(result))
        elif args.command == "show":
            print(json.dumps(show(args.root, args.run_id, args.revision), indent=2, sort_keys=True))
        elif args.command == "authority-show":
            print(json.dumps(authority_show(args.root, args.run_id, args.sequence), indent=2, sort_keys=True))
        elif args.command == "aidlc-standard":
            print(render_aidlc_standard(propose_aidlc_standard(args.root, args.run_id, args.approved_proposal)))
        elif args.command == "aidlc-standard-approve":
            result = approve_aidlc_standard(args.root, args.run_id, args.revision, args.approved)
            print(LOCK.render_aidlc_requirements(result["aidlc_requirements"]))
        else:
            result = approve(args.root, args.run_id, args.revision, args.approved)
            handoff = result.get("execution_handoff")
            print(LOCK.render_execution_handoff(handoff if isinstance(handoff, dict) else result))
        return 0
    except (OSError, ValueError, json.JSONDecodeError) as error:
        print(f"Planning revision error: {error}")
        return 2


if __name__ == "__main__":
    raise SystemExit(main())
