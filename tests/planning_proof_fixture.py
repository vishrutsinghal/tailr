"""Test helper: register runnable proof on a started plan before approval.

The planning audit gate (`planning_lock.require_clean_audit`) refuses to
approve a plan whose proof-required requirements have no runnable proof
command bound to an eligible proof path. Fixtures that approve a plan must
therefore register proof through the same propose/approve path a real host
uses, instead of skipping the gate.
"""

from __future__ import annotations

import importlib.util
import json
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parents[1]
DEFAULT_PROOF_PATH = "tests/fixture_proof_check.py"


def _load_revision():
    spec = importlib.util.spec_from_file_location(
        "planning_proof_fixture_revision", ROOT / "scripts" / "planning-revision.py"
    )
    module = importlib.util.module_from_spec(spec)
    assert spec and spec.loader
    spec.loader.exec_module(module)
    return module


_REVISION = _load_revision()


def _load_requirements():
    spec = importlib.util.spec_from_file_location(
        "planning_proof_fixture_requirements", ROOT / "scripts" / "requirement_discovery.py"
    )
    module = importlib.util.module_from_spec(spec)
    assert spec and spec.loader
    spec.loader.exec_module(module)
    return module


_REQUIREMENTS = _load_requirements()


def write_proof_file(root: Path, proof_path: str = DEFAULT_PROOF_PATH) -> None:
    """Create the proof module. Call before task-start, or the lock reads it as drift."""
    target = root / proof_path
    target.parent.mkdir(parents=True, exist_ok=True)
    if not target.exists():
        target.write_text(
            "import unittest\n\n\nclass FixtureProofCheck(unittest.TestCase):\n"
            "    def test_fixture_proof(self) -> None:\n        self.assertTrue(True)\n",
            encoding="utf-8",
        )


def register_proof(root: Path, run_id: str, *, proof_path: str = DEFAULT_PROOF_PATH) -> dict[str, Any]:
    """Record and approve one proof-update per requirement, bound to its own tiers."""
    write_proof_file(root, proof_path)
    generated = _REVISION.LOCK._proposal_from_start_report(root, run_id)
    changes: list[dict[str, Any]] = []
    for row in generated.get("requirements", []):
        contract = row.get("validation_contract") or {}
        # The audit requires every tier the requirement wording implies; register those too.
        implied = _REQUIREMENTS._tiers(str(row.get("statement", "")))
        tiers = sorted({str(tier) for tier in contract.get("tiers", []) if str(tier).strip()} | set(implied))
        if not tiers:
            continue
        if "behaviour" in tiers:
            # Behaviour proof needs a requirement-bound scenario with a concrete action and outcome.
            changes.append({
                "kind": "behaviour-scenario-add",
                "requirement_uid": row["display_id"],
                "reason": "Bind a requirement-specific behaviour scenario for this fixture.",
                "scenario": {
                    "scenario_id": f"BHV-{row['display_id']}",
                    "action": f"Run the fixture proof command `{proof_path}`",
                    "expected_outcome": str(row.get("statement", "")) or "Requirement behaviour is preserved",
                },
            })
        changes.append({
            "kind": "proof-update",
            "requirement_uid": row["display_id"],
            "reason": "Register the runnable proof command for this fixture.",
            "evidence_plan": ["Run the fixture proof command"],
            "checks": [{"command": f"python3 -m unittest {proof_path}", "tiers": tiers}],
            "editable_paths": [proof_path],
        })
    proposed = _REVISION.propose(root, run_id, json.dumps(changes), True)
    return _REVISION.approve(root, run_id, proposed["revision"], True)
