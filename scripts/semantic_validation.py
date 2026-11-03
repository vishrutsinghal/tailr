"""Deterministic Phase 2 validators for semantic-delta rows and dependency closure.

Everything here is mechanical: no model inference, no runtime execution.  The
validators only check that a row's state is supported by the evidence it cites
and that owner scope includes the typed schemas its files reference.
"""

from __future__ import annotations

import json
import re
from pathlib import Path
from typing import Any

SEMANTIC_STATES = frozenset({"missing", "partial", "satisfied", "unknown"})
TRUSTED_SATISFIED_REASON = "trusted-observation-matches-requested-assertion"
_TYPED_CONST = re.compile(r"^tailtrail-[a-z0-9][a-z0-9-]*$")


def validate_semantic_row(row: dict[str, Any]) -> list[dict[str, str]]:
    """Return findings for one semantic-delta row; an empty list means it is supported."""
    findings: list[dict[str, str]] = []

    def add(code: str, detail: str) -> None:
        findings.append({"requirement_id": str(row.get("requirement_id", "")), "code": code, "detail": detail})

    state = row.get("state")
    reason = str(row.get("reason") or "")
    if state not in SEMANTIC_STATES:
        add("invalid-state", f"state `{state}` is not a supported semantic state")
        return findings

    if state == "satisfied":
        if reason != TRUSTED_SATISFIED_REASON:
            add("satisfied-without-trusted-observation", "satisfied requires a trusted behavior observation")
        if row.get("current_observed_assertion") != row.get("expected_assertion"):
            add("satisfied-assertion-mismatch", "observed assertion must equal the expected assertion")
        if not row.get("evidence"):
            add("satisfied-without-evidence", "satisfied requires cited evidence references")

    if state in {"missing", "partial"}:
        if not str(row.get("expected_assertion") or "").strip():
            add("missing-expected-assertion", "missing or partial rows must name the expected assertion")
        if not str(row.get("pre_change_scenario") or "").strip():
            add("missing-proof-scenario", "missing or partial rows must name a behavior-specific proof scenario")

    if state == "unknown" and reason.startswith("trusted-"):
        add("unknown-with-trusted-reason", "unknown rows cannot cite a trusted-observation reason")

    return findings


def validate_plan_gate(rows: list[dict[str, Any]], owner_paths: list[str]) -> list[dict[str, str]]:
    """Reject implementation scope when every requested behavior is already satisfied."""
    findings: list[dict[str, str]] = []
    if rows and owner_paths and all(row.get("state") == "satisfied" for row in rows):
        findings.append({
            "requirement_id": "*",
            "code": "already-satisfied-with-implementation-scope",
            "detail": "all requested behaviors are satisfied; implementation owners need a separate justification",
        })
    for row in rows:
        findings.extend(validate_semantic_row(row))
    return findings


def _schema_index(root: Path) -> dict[str, set[str]]:
    """Map each schema file to the typed identifiers it declares (`type` const values)."""
    index: dict[str, set[str]] = {}
    schema_root = root / "schemas"
    if not schema_root.is_dir():
        return index
    for schema_path in sorted(schema_root.glob("*.json")):
        try:
            schema = json.loads(schema_path.read_text(encoding="utf-8"))
        except (OSError, json.JSONDecodeError):
            continue
        identifiers: set[str] = set()
        type_prop = (schema.get("properties") or {}).get("type") if isinstance(schema, dict) else None
        if isinstance(type_prop, dict):
            const = type_prop.get("const")
            if isinstance(const, str) and _TYPED_CONST.match(const):
                identifiers.add(const)
            for value in type_prop.get("enum") or []:
                if isinstance(value, str) and _TYPED_CONST.match(value):
                    identifiers.add(value)
        index[schema_path.relative_to(root).as_posix()] = identifiers
    return index


def dependency_closure(
    root: Path,
    owner_paths: list[str],
    *,
    justified_unchanged: list[str] | None = None,
) -> list[dict[str, str]]:
    """Report typed schemas referenced by owner files but absent from owner scope.

    A reference is a quoted schema filename or a quoted typed identifier
    (`tailtrail-...`) declared by a schema's `type` const or enum.  Schemas
    listed in ``justified_unchanged`` are accepted as deliberate exclusions.
    """
    owners = {path.replace("\\", "/") for path in owner_paths}
    justified = {path.replace("\\", "/") for path in (justified_unchanged or [])}
    index = _schema_index(root)
    findings: list[dict[str, str]] = []
    for owner in sorted(owners):
        target = root / owner
        if not target.is_file():
            continue
        try:
            text = target.read_text(encoding="utf-8")
        except (OSError, UnicodeDecodeError):
            continue
        for schema, identifiers in sorted(index.items()):
            if schema in owners or schema in justified:
                continue
            name = Path(schema).name
            referenced = any(f'"{token}"' in text or f"'{token}'" in text for token in {name, *identifiers})
            if referenced:
                findings.append({
                    "code": "schema-dependency-omitted",
                    "owner": owner,
                    "schema": schema,
                    "detail": f"`{owner}` references `{schema}` but the schema is outside owner scope",
                })
    return findings
