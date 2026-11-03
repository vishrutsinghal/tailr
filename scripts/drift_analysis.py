#!/usr/bin/env python3
"""Deterministic requirement-drift analysis for the Sequential Worker Pipeline.

Implements the Drift Analysis stage gate from
`docs/arch/navigator-pipeline-orchestration.md` (§4.3 Drift-Corrected Handoff)
and `docs/arch/sequential-worker-pipeline.md` (§4.2 Drift Analysis): before the
`TESTING -> INFRA` transition, compare the actual changed paths against the
latest approved anchor (`.tailtrail/runs/<run_id>/anchors/approved-vN.json`
via `change-intent-anchor.latest_approved`, not the frozen v1 file -- a
mid-run `correct` amendment must be visible here or the sanctioned correction
path silently stops working for closure).

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

SCOPE_DRIFT = "new-drift"
UNIMPLEMENTED = "requirement-unimplemented"
CONCRETENESS = "anchor-not-concrete"
FULFILLMENT = "fulfillment-unverified"
STALE_EVIDENCE = "stale-evidence"
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


def _load_anchor_module() -> Any:
    """Load change-intent-anchor the same dual-context way as planning_lock."""
    try:
        import change_intent_anchor  # type: ignore  # noqa: PLC0415

        return change_intent_anchor
    except ImportError:
        pass
    spec = importlib.util.spec_from_file_location(
        "drift_analysis_change_intent_anchor", ROOT / "scripts" / "change-intent-anchor.py"
    )
    if spec is None or spec.loader is None:
        raise RuntimeError("unable to load scripts/change-intent-anchor.py")
    module = importlib.util.module_from_spec(spec)
    sys.modules[spec.name] = module
    spec.loader.exec_module(module)
    return module


anchor_mod = _load_anchor_module()


def _load_execution_evidence() -> Any:
    """Load the managed evidence reader without making it execution authority."""
    try:
        import execution_evidence  # type: ignore  # noqa: PLC0415

        return execution_evidence
    except ImportError:
        pass
    spec = importlib.util.spec_from_file_location(
        "drift_analysis_execution_evidence", ROOT / "scripts" / "execution-evidence.py"
    )
    if spec is None or spec.loader is None:
        raise RuntimeError("unable to load scripts/execution-evidence.py")
    module = importlib.util.module_from_spec(spec)
    sys.modules[spec.name] = module
    spec.loader.exec_module(module)
    return module


def _current_plan_fingerprint(
    root: Path, run_id: str, requirements: list[dict[str, Any]], execution: Any,
) -> str:
    """Use the same effective-plan custody fingerprint as managed execution."""
    requirement_map = {
        str(row.get("requirement_uid")): row
        for row in requirements
        if str(row.get("requirement_uid", "")).strip()
    }
    overlay = execution._approved_revision_overlay(root, run_id)
    amendments = execution.approved_proof_amendments(root, run_id, requirement_map)
    merged_overlay = {
        uid: {
            "commands": sorted(
                set(overlay.get(uid, {}).get("commands", []))
                | set(amendments.get(uid, {}).get("commands", set()))
            ),
            "tiers": sorted(
                set(overlay.get(uid, {}).get("tiers", []))
                | set(amendments.get(uid, {}).get("tiers", set()))
            ),
        }
        for uid in set(overlay) | set(amendments)
    }
    return anchor_mod.approved_plan_fingerprint(
        anchor_mod.effective_plan_contracts(requirement_map, merged_overlay),
        requirements_data=requirement_map,
    )


def _managed_evidence(
    root: Path, run_id: str, requirements: list[dict[str, Any]],
) -> tuple[list[dict[str, Any]], list[dict[str, Any]]]:
    """Return current managed receipts and requirement-linked stale receipts.

    The sequential gate owns no separate evidence store. It reads the same
    append-only managed stream as closure, accepts only command/CI receipts
    for this run and the current effective plan, and reports stale receipts
    rather than allowing an earlier plan's proof to silently pass a new one.
    """
    try:
        execution = _load_execution_evidence()
        current_fingerprint = _current_plan_fingerprint(root, run_id, requirements, execution)
        events = execution.show(root, run_id).get("events", [])
    except (OSError, ValueError, json.JSONDecodeError, RuntimeError):
        return [], []

    current: list[dict[str, Any]] = []
    stale: list[dict[str, Any]] = []
    approved_uids = {
        str(row.get("requirement_uid"))
        for row in requirements
        if str(row.get("requirement_uid", "")).strip()
    }
    for event in events if isinstance(events, list) else []:
        if not isinstance(event, dict):
            continue
        if event.get("run_id") != run_id or event.get("kind") not in {"command-result", "ci-receipt"}:
            continue
        linked = {str(uid) for uid in event.get("requirement_uids", [])}
        if not linked or not linked & approved_uids:
            continue
        stamped = event.get("plan_fingerprint")
        if stamped and stamped != current_fingerprint:
            stale.append(event)
        elif stamped == current_fingerprint:
            current.append(event)
    return current, stale


def _latest_anchor(root: Path, run_id: str) -> tuple[dict[str, Any], str]:
    """Load the latest approved anchor (v1 when never corrected).

    Returns (anchor, label) where label is the versioned filename for
    evidence. Raises ValueError when no approved anchor exists.
    """
    path, anchor = anchor_mod.latest_approved(root, run_id)
    if not isinstance(anchor, dict):
        raise ValueError("latest approved anchor is not an object")
    return anchor, f"anchors/{Path(path).name}"


def _read_json(path: Path) -> dict[str, Any]:
    return json.loads(path.read_text(encoding="utf-8"))


def _anchor_path(value: Any) -> str | None:
    """Extract a path from a plain-string or {path, role} anchor entry."""
    if isinstance(value, str):
        return value.strip() or None
    if isinstance(value, dict):
        path = value.get("path")
        return str(path).strip() or None if isinstance(path, str) else None
    return None


def _normalize_path(value: str | dict[str, str]) -> str:
    """Normalize a manifest entry, stripping `path.py:L20-L45` line ranges.

    Tolerates role-tagged `{path, role}` anchor entries (Issue 6 follow-up):
    a bare `str(dict)` here would corrupt to `"{'path': ...}"`, the same bug
    class already fixed for other anchor consumers under Issue 4b.
    """
    found = _anchor_path(value)
    entry = (found if found is not None else str(value)).strip().replace("\\", "/")
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


def _evidence_tiers(item: dict[str, Any]) -> list[str]:
    """Return the explicitly asserted tiers for one evidence event."""
    tiers = item.get("tiers")
    if not isinstance(tiers, list) or not tiers:
        tiers = [item.get("tier")] if item.get("tier") else []
    return sorted({str(tier).strip() for tier in tiers if str(tier).strip()})


def _current_evidence_by_binding(
    requirement_uid: str, evidence_items: list[dict[str, Any]],
) -> list[dict[str, Any]]:
    """Select the latest event for each compatible proof binding.

    Evidence is append-only.  A retry may replace an earlier result only when
    it addresses the same requirement, executable command, tier, and scenario
    assertion.  Different commands, tiers, or scenarios deliberately remain
    independent so a passing command cannot hide a failure for another
    required binding.  Legacy evidence without a command retains a separate
    legacy binding for backwards-compatible handoff evidence.
    """
    selected: dict[tuple[str, str, str, tuple[str, ...], str], tuple[int, dict[str, Any]]] = {}
    for position, item in enumerate(evidence_items):
        if not isinstance(item, dict):
            continue
        uids = item.get("requirement_uids")
        if uids and requirement_uid not in uids:
            continue
        command = str(item.get("command", "")).strip()
        if not command:
            # Inline handoff evidence has no append-only receipt ordering and
            # therefore must not silently replace a saved managed result.
            # It remains supported as a separate legacy binding.
            command = (
                "<legacy-managed-command>"
                if item.get("kind") in {"command-result", "ci-receipt"}
                else "<legacy-inline-command>"
            )
        scenarios = tuple(sorted({
            str(value).strip()
            for value in (item.get("scenario_ids", []) or [])
            if str(value).strip()
        }))
        assertion = str(item.get("scenario_assertion_fingerprint", "")).strip()
        for tier in _evidence_tiers(item):
            # The list preserves the append-only stream order; a later item
            # with this exact identity is the current retry result.
            selected[(requirement_uid, command, tier, scenarios, assertion)] = (position, item)
    current: list[dict[str, Any]] = []
    seen: set[int] = set()
    for _, item in selected.values():
        marker = id(item)
        if marker not in seen:
            seen.add(marker)
            current.append(item)
    return current


def _requirement_validated(
    row: dict[str, Any], evidence_items: list[dict[str, Any]]
) -> bool:
    """Mirror scripts/harness-checkpoint.py's `validated` computation.

    A requirement is validated only with authoritative (trusted/attested),
    passing evidence at every required tier, linked to that requirement.
    Passing-but-unlinked tests are not proof (design §10.2).
    """
    requirement_uid = str(row.get("requirement_uid"))
    linked = _current_evidence_by_binding(requirement_uid, evidence_items)
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
        passed.update(_evidence_tiers(item))
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


def _injected_anchor_freshness(
    root: Path, run_id: str, anchor: dict[str, Any]
) -> list[dict[str, Any]]:
    """Fail closed when an injected anchor is stale against disk.

    Callers must inject freshly loaded anchors (never cached); when the
    on-disk latest carries a different `approved_fingerprint`, the injected
    copy is stale and validation against it would be wrong. Unreadable disk
    state is not a verdict -- the injected anchor is used as-is then, which
    keeps synthetic test anchors working without fixtures.
    """
    given = anchor.get("approved_fingerprint")
    if not isinstance(given, str) or not given:
        return []
    try:
        _, latest = anchor_mod.latest_approved(root, run_id)
    except (OSError, ValueError):
        return []
    if not isinstance(latest, dict):
        return []
    current = latest.get("approved_fingerprint")
    if isinstance(current, str) and current and current != given:
        return [
            {
                "classification": "anchor-stale",
                "category": "baseline",
                "message": (
                    "Injected anchor is stale: on-disk latest approved anchor "
                    "has a newer approved_fingerprint; reload via "
                    "change-intent-anchor.latest_approved instead of reusing "
                    "a cached copy."
                ),
            }
        ]
    return []


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
    root: Path,
    run_id: str,
    evidence: dict[str, Any] | None = None,
    *,
    anchor: dict[str, Any] | None = None,
) -> dict[str, Any]:
    """Compare actual changed paths against the approved requirement baseline.

    Returns a deterministic, read-only drift report. Fail closed: a missing
    anchor or missing change evidence is drift, never an automatic pass.

    The baseline is the latest approved anchor (a mid-run `correct`
    amendment included), never the frozen v1 file. Callers may inject an
    already-loaded anchor for in-process convenience, but must load it fresh
    via `change-intent-anchor.latest_approved` -- never a cached copy: a
    stale injection fails closed with `anchor-stale`.
    """
    root = Path(root).resolve()
    if anchor is not None:
        if not isinstance(anchor, dict):
            return _fail_closed(
                "anchor-missing",
                "Injected anchor is not an object; a stage transition cannot be "
                "validated without the requirement baseline.",
            )
        stale = _injected_anchor_freshness(root, run_id, anchor)
        if stale:
            return _fail_closed(
                "anchor-stale",
                "Injected anchor is stale against the on-disk latest approved anchor.",
                stale,
            )
        anchor_label = "anchors/injected"
    else:
        try:
            anchor, anchor_label = _latest_anchor(root, run_id)
        except (OSError, ValueError, json.JSONDecodeError):
            return _fail_closed(
                "anchor-missing",
                "Approved anchor is missing; a stage transition cannot be "
                "validated without the requirement baseline.",
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
    inline_evidence = (
        evidence.get("evidence")
        if isinstance(evidence, dict) and isinstance(evidence.get("evidence"), list)
        else []
    )
    managed_evidence, stale_managed_evidence = _managed_evidence(root, run_id, requirements)
    # A caller may attach fresh handoff facts, but it must not need to copy
    # TailTrail's own managed receipt stream into every handoff.  Merge both
    # sources before evaluating tiers; a linked non-pass from either source
    # still wins through `_requirement_validated`.
    evidence_items = [*managed_evidence, *inline_evidence]

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
            stale = [
                item for item in stale_managed_evidence
                if str(row.get("requirement_uid")) in {
                    str(uid) for uid in item.get("requirement_uids", [])
                }
            ]
            if stale:
                findings.append(
                    {
                        "classification": STALE_EVIDENCE,
                        "category": "fulfillment",
                        "requirement_uid": row.get("requirement_uid"),
                        "display_id": display_id,
                        "message": (
                            f"{display_id} has saved evidence for a different approved plan; "
                            "rerun the approved proof for the current plan"
                        ),
                    }
                )
            fulfillment = (
                "validated"
                if not stale and _requirement_validated(row, evidence_items)
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
            "source": f"{source}+managed-execution" if managed_evidence or stale_managed_evidence else source,
            "changed_paths": sorted(changed_set),
            "anchor": anchor_label,
            "managed_receipts": len(managed_evidence),
            "stale_managed_receipts": len(stale_managed_evidence),
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
