from __future__ import annotations

import importlib.util
import json
import sys
import tempfile
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]


def load(name: str, relative: str):
    spec = importlib.util.spec_from_file_location(name, ROOT / relative)
    module = importlib.util.module_from_spec(spec)
    assert spec and spec.loader
    sys.modules[name] = module
    spec.loader.exec_module(module)
    return module


lock = load("tier_binding_lock_test", "scripts/planning_lock.py")
audit = load("tier_binding_audit_test", "scripts/planning-audit.py")
revision = load("tier_binding_revision_test", "scripts/planning-revision.py")

from tests.test_planning_audit import _plan  # noqa: E402


def _report(tiers: list[str], commands: list[str], paths: list[str]) -> dict:
    return {"requirements": [{
        "display_id": "REQ-01",
        "requirement_uid": "REQ-01",
        "validation_contract": {
            "tiers": tiers,
            "commands": commands,
            "checks": [],
            "candidate_paths": paths,
        },
    }]}


class TierBindingTests(unittest.TestCase):
    def test_per_tier_repeated_command_resolves_every_tier(self) -> None:
        cmd = "python3 tests/test_x.py"
        report = _report(["unit", "behaviour", "integration"], [cmd, cmd, cmd], ["tests/test_x.py"])
        rows = lock.effective_plan_projection(report)["focused_validation"]
        self.assertEqual({row["status"] for row in rows}, {"resolved"})
        self.assertEqual({row["command_id"] for row in rows}, {lock._command_id(cmd)})

    def test_tier_without_positional_command_stays_unresolved(self) -> None:
        cmd = "python3 tests/test_x.py"
        report = _report(["unit", "behaviour", "integration"], [cmd], ["tests/test_x.py"])
        rows = {row["tier"]: row for row in lock.effective_plan_projection(report)["focused_validation"]}
        self.assertEqual(rows["unit"]["status"], "resolved")
        self.assertEqual(rows["integration"]["status"], "unresolved")

    def test_revision_pair_union_keeps_tier_alignment(self) -> None:
        with tempfile.TemporaryDirectory() as temp:
            root = Path(temp)
            _plan(root, "pair-union", [{
                "display_id": "REQ-01", "requirement_uid": "REQ-01", "kind": "change",
                "statement": "Render the plan.",
                "acceptance_criteria": ["plan renders"],
                "likely_paths": ["scripts/verbose-reporting.py"],
                "validation_contract": {
                    "state": "required", "tiers": ["unit"], "commands": ["python3 tests/test_x.py"],
                    "candidate_paths": ["tests/test_x.py"],
                },
            }])
            change = json.dumps([{
                "kind": "proof-update", "requirement_uid": "REQ-01",
                "reason": "attach behaviour and integration proof",
                "evidence_plan": ["Run each tier."],
                "commands": ["python3 tests/test_x.py", "python3 tests/test_x.py"],
                "tiers": ["behaviour", "integration"],
            }])
            revision.propose(root, "pair-union", change, True)
            proposed = revision.show(root, "pair-union").get("proposed_report", {})

        contract = proposed["navigator"]["requirement_matrix"][0]["validation_contract"]
        self.assertEqual(len(contract["tiers"]), len(contract["commands"]))
        self.assertEqual(sorted(contract["tiers"]), ["behaviour", "integration", "unit"])

    def test_one_targeted_shared_proof_path_satisfies_binding(self) -> None:
        row = {
            "display_id": "REQ-01", "requirement_uid": "REQ-01", "kind": "change",
            "validation_contract": {"state": "required"},
            "scope_evidence": {"proof_paths": ["_run_r2_tests.py", "tests/test_x.py"]},
        }
        checks = [{
            "kind": "proof", "command": "python3 tests/test_x.py", "tiers": ["unit"],
            "candidate_paths": ["_run_r2_tests.py", "tests/test_x.py"],
        }]
        findings = audit._proof_binding_findings("run", row, checks)
        self.assertFalse([f for f in findings if f["type"] == "proof-command-does-not-target-path"])

    def test_no_targeted_proof_path_is_still_flagged(self) -> None:
        row = {
            "display_id": "REQ-01", "requirement_uid": "REQ-01", "kind": "change",
            "validation_contract": {"state": "required"},
            "scope_evidence": {"proof_paths": ["tests/test_x.py"]},
        }
        checks = [{
            "kind": "proof", "command": "python3 tests/test_other.py", "tiers": ["unit"],
            "candidate_paths": ["tests/test_x.py"],
        }]
        findings = audit._proof_binding_findings("run", row, checks)
        self.assertTrue([f for f in findings if f["type"] == "proof-command-does-not-target-path"])


if __name__ == "__main__":
    unittest.main()
