#!/usr/bin/env python3
"""Deterministic requirement-drift analysis for the Sequential Worker Pipeline.

Implements the Drift Analysis stage gate from
`docs/arch/navigator-pipeline-orchestration.md` (§4.3 Drift-Corrected Handoff)
and `docs/arch/sequential-worker-pipeline.md` (§4.2 Drift Analysis): before the
`TESTING -> INFRA` transition, compare the actual changed paths against the
immutable approved anchor (`.tailtrail/runs/<run_id>/anchors/approved-v1.json`).

Checks (all fail closed):

- `anchor-missing`: the approved baseline is absent, so a transition can never
  be validated.
- `no-change-evidence`: no changed paths were found in the HandoffManifest,
  planning lock, or latest checkpoint.
- `new-drift` (scope): a changed path is outside the approved editable union
  (`likely_paths` + validation `editable_paths`/`proposed_paths`), reusing the
  scope logic from `scripts/harness-checkpoint.py`.
- `requirement-unimplemented`: an approved `change` requirement has zero changed
  paths in its `likely_paths` — the "coding for the test" case. `preserve`
  requirements are exempt because they are constraints, not new work.

The analysis is deterministic and read-only: it never edits files, runs
commands, or grants authority. Callers (`scripts/pipeline_judge.py`) consume
`drift_detected`; the full findings are auditable evidence.
"""

from __future__ import annotations

import argparse
import importlib.util
import json
import re
import sys
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parents[1]

ANCHOR_FILENAME = "approved-v1.json"
SCOPE_DRIFT = "new-drift"
UNIMPLEMENTED = "requirement-unimplemented"
CONCRETENESS = "anchor-not-concrete"
FULFILLMENT = "fulfillment-unverified"
_NONPASSING_OUTCOMES = {"fail", "blocked", "timed-out", "unavailable"}
_AUTHORITATIVE_QUALITIES = {"trusted", "attested"}
_LINE_RANGE = re.compile(r"^L\d+(?:-L?\d+)?$")


def _load_planning_lock() -> Any:
    """Load the planning lock in both import contexts (flat or `scripts.` package)."""
    try:
        import planning_lock  # type: ignore  # noqa: PLC0415

        return planning_lock
    except ImportError:
        pass
    spec = importlib.util.spec_from_file_location(
        "drift_analysis_planning_lock", ROOT / "scripts" / "planning_lock.py"
    )
    if spec is None or spec.loader is None:
        raise RuntimeError("unable to load scripts/planning_lock.py")
    module = importlib.util.module_from_spec(spec)
    sys.modules[spec.name] = module
    spec.loader.exec_module(module)
    return module


pl = _load_planning_lock()


def _read_json(path: Path) -> dict[str, Any]:
    return json.loads(path.read_text(encoding="utf-8"))


def _normalize_path(value: str) -> str:
    """Normalize a manifest entry, stripping `path.py:L20-L45` line ranges."""
    entry = str(value).strip().replace("\\", "/")
    if ":" in entry:
        candidate, _, suffix = entry.rpartition(":")
        if candidate and _LINE_RANGE.fullmatch(suffix):
            return candidate
    return entry


def _approved_requirements(anchor: dict[str, Any]) -> list[dict[str, Any]]:
    return [
        row
        for row in anchor.get("requirements", [])
        if isinstance(row, dict) and row.get("status") == "approved"
    ]


def _approved_editable(requirements: list[dict[str, Any]]) -> set[str]:
    """Approved editable union, matching scripts/harness-checkpoint.py scope logic."""
    editable: set[str] = set()
    for row in requirements:
        editable.update(
            _normalize_path(path)
            for path in row.get("likely_paths", [])
            if str(path).strip()
        )
        contract = row.get("validation_contract") or {}
        for key in ("editable_paths", "proposed_paths"):
            editable.update(
                _normalize_path(path)
                for path in contract.get(key, [])
                if str(path).strip()
            )
    return editable


def _validate_concreteness(requirements: list[dict[str, Any]]) -> list[dict[str, Any]]:
    """Planning-time concreteness gate (design §10.3).

    A vague anchor cannot be drift-checked: every `change` requirement needs
    observable `acceptance_criteria` and `likely_paths`; every `preserve`
    requirement needs explicit `preserve_rules`. Vague requirements fail
    closed here instead of silently at runtime.
    """
    findings: list[dict[str, Any]] = []
    for row in requirements:
        display_id = str(row.get("display_id") or row.get("requirement_uid") or "REQ")
        kind = str(row.get("kind") or "change")
        problems: list[str] = []
        if kind == "change":
            if not [c for c in row.get("acceptance_criteria", []) if str(c).strip()]:
                problems.append("acceptance_criteria")
            if not [p for p in row.get("likely_paths", []) if str(p).strip()]:
                problems.append("likely_paths")
        elif kind == "preserve":
            if not [r for r in row.get("preserve_rules", []) if str(r).strip()]:
                problems.append("preserve_rules")
        if problems:
            findings.append(
                {
                    "classification": CONCRETENESS,
                    "category": "requirement",
                    "requirement_uid": row.get("requirement_uid"),
                    "display_id": display_id,
                    "message": (
                        f"{display_id} is not concrete enough to drift-check; "
                        f"missing: {', '.join(problems)}"
                    ),
                }
            )
    return findings


def _linked_evidence(
    uid: str, evidence_items: list[dict[str, Any]]
) -> list[dict[str, Any]]:
    """Evidence linked to one requirement (unlinked items apply to all)."""
    rows: list[dict[str, Any]] = []
    for item in evidence_items:
        if not isinstance(item, dict):
            continue
        uids = item.get("requirement_uids")
        if not uids or uid in uids:
            rows.append(item)
    return rows


def _requirement_validated(
    row: dict[str, Any], evidence_items: list[dict[str, Any]]
) -> bool:
    """Mirror scripts/harness-checkpoint.py's `validated` computation.

    A requirement is validated only with authoritative (trusted/attested),
    passing evidence at every required tier, linked to that requirement.
    Passing-but-unlinked tests are not proof (design §10.2).
    """
    linked = _linked_evidence(str(row.get("requirement_uid")), evidence_items)
    authoritative = [
        item
        for item in linked
        if item.get("evidence_quality") in _AUTHORITATIVE_QUALITIES
    ]
    required = {
        str(tier)
        for tier in (row.get("validation_contract") or {}).get("tiers", [])
        if str(tier)
    }
    passed: set[str] = set()
    for item in authoritative:
        if item.get("outcome") != "pass":
            continue
        tiers = item.get("tiers")
        if not isinstance(tiers, list) or not tiers:
            tiers = [item.get("tier")] if item.get("tier") else []
        passed.update(str(tier) for tier in tiers if str(tier))
    nonpassing = any(
        item.get("outcome") in _NONPASSING_OUTCOMES for item in linked
    )
    return bool(authoritative) and not nonpassing and required.issubset(passed)


def _changed_from_evidence(evidence: dict[str, Any] | None) -> list[str]:
    if not isinstance(evidence, dict):
        return []
    manifest = evidence.get("change_manifest")
    if not isinstance(manifest, list):
        return []
    return [str(item) for item in manifest if isinstance(item, str) and item.strip()]


def _changed_from_lock(root: Path, run_id: str) -> list[str]:
    """Fall back to the HandoffManifest recorded in the Planning Lock."""
    try:
        lock = pl.show(root, run_id)
    except (OSError, ValueError, KeyError, json.JSONDecodeError):
        return []
    pipeline = lock.get("pipeline") if isinstance(lock, dict) else None
    handoff = (pipeline or {}).get("last_handoff") if isinstance(pipeline, dict) else None
    manifest = handoff.get("change_manifest") if isinstance(handoff, dict) else None
    if not isinstance(manifest, list):
        return []
    return [str(item) for item in manifest if isinstance(item, str) and item.strip()]


def _changed_from_checkpoint(root: Path, run_id: str) -> list[str]:
    """Last resort: the latest harness checkpoint's changed paths."""
    checkpoints = sorted(
        (pl.L.state_dir(root, run_id) / "checkpoints").glob("checkpoint-*.json")
    )
    if not checkpoints:
        return []
    try:
        payload = _read_json(checkpoints[-1])
    except (OSError, json.JSONDecodeError):
        return []
    paths: list[str] = []
    for item in payload.get("changed_paths", []):
        value = item.get("path") if isinstance(item, dict) else item
        if isinstance(value, str) and value.strip():
            paths.append(value.strip())
    return paths


def _resolve_changed_paths(
    root: Path, run_id: str, evidence: dict[str, Any] | None
) -> tuple[list[str], str]:
    """Changed-path source priority: HandoffManifest -> lock -> checkpoint."""
    from_evidence = _changed_from_evidence(evidence)
    if from_evidence:
        return from_evidence, "handoff-manifest"
    from_lock = _changed_from_lock(root, run_id)
    if from_lock:
        return from_lock, "planning-lock"
    from_checkpoint = _changed_from_checkpoint(root, run_id)
    if from_checkpoint:
        return from_checkpoint, "checkpoint"
    return [], "none"


def _fail_closed(
    reason: str,
    message: str,
    findings: list[dict[str, Any]] | None = None,
) -> dict[str, Any]:
    return {
        "drift_detected": True,
        "findings": findings or [{"classification": reason, "message": message}],
        "scope_assessment": {
            "status": "unresolved",
            "reason": reason,
            "approved_editable_paths": [],
            "actual_changed_paths": [],
            "unexpected_paths": [],
        },
        "requirements": [],
        "evidence": {"source": "none", "changed_paths": []},
    }


def analyze(
    root: Path, run_id: str, evidence: dict[str, Any] | None = None
) -> dict[str, Any]:
    """Compare actual changed paths against the approved requirement baseline.

    Returns a deterministic, read-only drift report. Fail closed: a missing
    anchor or missing change evidence is drift, never an automatic pass.
    """
    root = Path(root).resolve()
    anchor_path = pl.L.state_dir(root, run_id) / "anchors" / ANCHOR_FILENAME
    try:
        anchor = _read_json(anchor_path)
    except (OSError, json.JSONDecodeError):
        return _fail_closed(
            "anchor-missing",
            "Approved anchor is missing; a stage transition cannot be "
            "validated without the immutable requirement baseline.",
        )

    requirements = _approved_requirements(anchor)

    # Planning-time concreteness gate (design §10.3): a vague anchor cannot
    # be drift-checked, so it fails closed before any comparison runs.
    concreteness = _validate_concreteness(requirements)
    if concreteness:
        return _fail_closed(
            CONCRETENESS,
            "Approved anchor is not concrete enough to drift-check.",
            concreteness,
        )

    changed, source = _resolve_changed_paths(root, run_id, evidence)
    if not changed:
        return _fail_closed(
            "no-change-evidence",
            "No change evidence was found in the handoff manifest, planning "
            "lock, or latest checkpoint.",
        )

    changed_set = {_normalize_path(item) for item in changed}
    approved_editable = _approved_editable(requirements)
    evidence_items = (
        evidence.get("evidence")
        if isinstance(evidence, dict) and isinstance(evidence.get("evidence"), list)
        else []
    )

    findings: list[dict[str, Any]] = []

    # Check A: scope drift — changed paths outside the approved editable union.
    unexpected = sorted(changed_set - approved_editable)
    for path in unexpected:
        findings.append(
            {
                "classification": SCOPE_DRIFT,
                "category": "scope",
                "path": path,
                "message": f"actual edit `{path}` is outside approved editable scope",
            }
        )

    # Checks B/C: per-requirement mapping. A `change` requirement with zero
    # changed paths in its likely_paths is unimplemented ("coding for the
    # test"); `preserve` requirements are exempt from that check.
    requirement_rows: list[dict[str, Any]] = []
    for row in requirements:
        likely = {
            _normalize_path(path)
            for path in row.get("likely_paths", [])
            if str(path).strip()
        }
        relevant = sorted(changed_set & likely)
        kind = str(row.get("kind") or "change")
        unimplemented = kind == "change" and not relevant
        display_id = str(row.get("display_id") or row.get("requirement_uid") or "REQ")
        if unimplemented:
            findings.append(
                {
                    "classification": UNIMPLEMENTED,
                    "category": "requirement",
                    "requirement_uid": row.get("requirement_uid"),
                    "display_id": display_id,
                    "message": (
                        f"{display_id} has no implementation changes in its "
                        "approved paths"
                    ),
                }
            )
        # Fulfillment check (design §10.2): passing tests are not proof unless
        # they are authoritative, passing, tier-complete, and linked to the
        # requirement. `preserve` requirements are exempt (constraints, not
        # new work).
        fulfillment = None
        if kind == "change":
            fulfillment = (
                "validated"
                if _requirement_validated(row, evidence_items)
                else "unverified"
            )
            if fulfillment == "unverified":
                findings.append(
                    {
                        "classification": FULFILLMENT,
                        "category": "fulfillment",
                        "requirement_uid": row.get("requirement_uid"),
                        "display_id": display_id,
                        "message": (
                            f"{display_id} lacks authoritative passing evidence "
                            "at its required tiers (implemented-unverified)"
                        ),
                    }
                )
        requirement_rows.append(
            {
                "requirement_uid": row.get("requirement_uid"),
                "display_id": display_id,
                "kind": kind,
                "statement": row.get("statement"),
                "likely_paths": sorted(likely),
                "changed_paths": relevant,
                "mapping": (
                    "mapped"
                    if relevant
                    else ("unimplemented" if unimplemented else "preserved")
                ),
                "fulfillment": fulfillment,
            }
        )

    return {
        "drift_detected": bool(findings),
        "findings": findings,
        "scope_assessment": {
            "status": "unresolved" if unexpected else "within-approved-scope",
            "approved_editable_paths": sorted(approved_editable),
            "actual_changed_paths": sorted(changed_set),
            "unexpected_paths": unexpected,
        },
        "requirements": requirement_rows,
        "evidence": {
            "source": source,
            "changed_paths": sorted(changed_set),
            "anchor": f"anchors/{ANCHOR_FILENAME}",
        },
    }


def main() -> int:
    parser = argparse.ArgumentParser(
        description=(
            "Detect requirement drift between actual changes and the "
            "approved anchor for a run."
        )
    )
    parser.add_argument("--root", type=Path, default=Path.cwd())
    parser.add_argument("--run-id", required=True)
    parser.add_argument(
        "--changed",
        action="append",
        default=[],
        help="Changed path from the handoff manifest (repeatable).",
    )
    args = parser.parse_args()
    try:
        evidence = {"change_manifest": args.changed} if args.changed else None
        payload = analyze(args.root.resolve(), args.run_id, evidence)
        print(json.dumps(payload, indent=2, sort_keys=True))
        return 0
    except (OSError, ValueError, json.JSONDecodeError) as error:
        print(f"Drift analysis error: {error}")
        return 2


if __name__ == "__main__":
    raise SystemExit(main())