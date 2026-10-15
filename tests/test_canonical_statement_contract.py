from __future__ import annotations

import importlib.util
import sys
import unittest
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "scripts"))


def load(name: str, relative: str):
    spec = importlib.util.spec_from_file_location(name, ROOT / relative)
    module = importlib.util.module_from_spec(spec)
    assert spec and spec.loader
    sys.modules[name] = module
    spec.loader.exec_module(module)
    return module


discovery = load("contract_discovery_test", "scripts/requirement_discovery.py")
revision = load("contract_revision_test", "scripts/planning-revision.py")


def _statement(length: int) -> str:
    return "x" * length


def _row(statement: str) -> dict:
    return {
        "requirement_uid": "req-1", "display_id": "REQ-01", "kind": "change",
        "statement": statement, "acceptance_criteria": ["Done."],
        "preserve_rules": [], "likely_paths": ["src/work.py"],
        "evidence_plan": ["Run unit proof."],
        "validation_contract": {"state": "required", "tiers": ["unit"],
                                "commands": ["pytest tests/test_work.py"]},
    }


class CanonicalStatementContractTests(unittest.TestCase):
    def test_shared_ceiling_is_1500(self) -> None:
        self.assertEqual(discovery.MAX_CANONICAL_REQUIREMENT_STATEMENT_CHARS, 1500)
        self.assertEqual(revision._canonical_limit(), 1500)

    def test_saved_statements_survive_revision_loading(self) -> None:
        for length in (500, 1000, 1500):
            report = {"navigator": {"requirement_matrix": [_row(_statement(length))]}}
            rows = revision._requirements(report, Path("."), "run-1")
            change = {
                "kind": "proof-update", "requirement_uid": "req-1",
                "reason": "attach proof",
                "evidence_plan": ["Run unit proof."],
                "commands": ["pytest tests/test_more.py"],
            }
            revision._apply_change(Path("."), report, rows, change, "run-1")
            self.assertEqual(rows[0]["validation_contract"]["tiers"], ["unit"])
            self.assertEqual(len(rows[0]["validation_contract"]["commands"]), 2)

    def test_1501_rejected_with_precise_errors(self) -> None:
        report = {"navigator": {"requirement_matrix": [_row(_statement(1501))]}}
        with self.assertRaisesRegex(ValueError, "saved canonical requirement"):
            revision._requirements(report, Path("."), "run-1")
        rows = [_row("Do the thing.")]
        change = {
            "kind": "requirement-update", "requirement_uid": "req-1",
            "reason": "reword",
            "statement": _statement(1501),
        }
        with self.assertRaisesRegex(ValueError, "revision change `statement`"):
            revision._apply_change(Path("."), {"navigator": {}}, rows, change, "run-1")

    def test_reason_keeps_its_own_smaller_limit(self) -> None:
        rows = [_row("Do the thing.")]
        change = {
            "kind": "proof-update", "requirement_uid": "req-1",
            "reason": "y" * 501,
            "evidence_plan": ["Run unit proof."],
        }
        with self.assertRaisesRegex(ValueError, "revision change `reason`"):
            revision._apply_change(Path("."), {"navigator": {}}, rows, change, "run-1")


if __name__ == "__main__":
    unittest.main()
