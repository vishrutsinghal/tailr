from __future__ import annotations

import copy
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


task_start = load("tailtrail_focused_contracts_start_test", "scripts/task-start.py")
# Canonical import: task-start.py calls navigator_scope.* at call time through
# this exact module object, so stubs land where the repair looks.
import navigator_scope  # noqa: E402


def _sealed(requirements):
    document = {
        "schema_version": "2",
        "type": "tailtrail-navigator-scope-evidence",
        "state": "resolved",
        "requirements": requirements,
        "candidates": [],
        "edges": [],
        "investigation": {"state": "resolved"},
    }
    document["decision_fingerprint"] = navigator_scope.fingerprint(
        navigator_scope._fingerprintable_document(document)
    )
    return document


def _owner_row(req_id="REQ-01", owners=None):
    return {
        "requirement_id": req_id,
        "display_id": req_id,
        "scope_state": "resolved",
        "implementation_owners": list(owners or ["scripts/task-start.py"]),
        "inspection_paths": [],
        "proof_paths": [],
        "query_terms": [],
    }


class AttachFocusedValidationContractsTests(unittest.TestCase):
    def test_records_command_strings(self):
        requirement = {"display_id": "REQ-01", "validation_contract": {"state": "required", "tiers": ["unit"]}}
        rows = [{
            "tiers": ["unit"], "command": "python -m unittest tests.test_x",
            "candidate": "tests/test_x.py", "candidate_state": "existing",
        }]
        task_start.attach_focused_validation_contracts([requirement], rows)
        contract = requirement["validation_contract"]
        self.assertEqual(contract["commands"], ["python -m unittest tests.test_x"])

    def test_overwrites_stale_tiers_and_commands(self):
        requirement = {"display_id": "REQ-01", "validation_contract": {
            "state": "required", "tiers": ["unit", "integration"],
            "commands": ["stale command"],
            "candidate_paths": ["tests/test_scope_proof.py"],
        }}
        rows = [{
            "tiers": ["unit"], "command": "python -m unittest tests.test_x",
            "candidate": "tests/test_x.py", "candidate_state": "existing",
        }]
        task_start.attach_focused_validation_contracts([requirement], rows)
        contract = requirement["validation_contract"]
        self.assertEqual(contract["tiers"], ["unit"])
        self.assertEqual(contract["commands"], ["python -m unittest tests.test_x"])
        self.assertEqual(contract["state"], "required")
        # Scope-derived paths union, never drop: edit authority survives overwrite.
        self.assertEqual(
            contract["candidate_paths"], ["tests/test_scope_proof.py", "tests/test_x.py"]
        )

    def test_empty_rows_leave_contract_untouched(self):
        before = {"state": "required", "tiers": ["unit"]}
        requirement = {"display_id": "REQ-01", "validation_contract": copy.deepcopy(before)}
        task_start.attach_focused_validation_contracts([requirement], [])
        self.assertEqual(requirement["validation_contract"], before)
        self.assertNotIn("commands", requirement["validation_contract"])

    def test_static_required_rows_recorded(self):
        requirement = {"display_id": "REQ-01", "validation_contract": {"state": "required", "tiers": ["unit"]}}
        rows = [{"check_kind": "static", "required": True, "command": "python -m compileall scripts"}]
        task_start.attach_focused_validation_contracts([requirement], rows)
        contract = requirement["validation_contract"]
        self.assertIn("static", contract["tiers"])
        self.assertEqual(contract["commands"], ["python -m compileall scripts"])

    def test_preserves_multiple_commands_for_one_tier(self):
        requirement = {"display_id": "REQ-01", "validation_contract": {"state": "required", "tiers": ["unit"]}}
        rows = [
            {"tiers": ["unit"], "command": "python -m unittest tests.test_question_orchestrator", "candidate": "tests/test_question_orchestrator.py", "candidate_state": "existing"},
            {"tiers": ["unit"], "command": "python -m unittest tests.test_phase1a", "candidate": "tests/test_phase1a.py", "candidate_state": "existing"},
        ]
        task_start.attach_focused_validation_contracts([requirement], rows)
        contract = requirement["validation_contract"]
        self.assertEqual(contract["tiers"], ["unit"])
        self.assertEqual(contract["commands"], [
            "python -m unittest tests.test_question_orchestrator",
            "python -m unittest tests.test_phase1a",
        ])
        self.assertEqual(len(contract["checks"]), 2)


class ReresolvedMatrixRestampTests(unittest.TestCase):
    def setUp(self):
        self._orig_packet = navigator_scope.host_reasoning_packet
        self._orig_quality = navigator_scope.assess_scope_quality
        self._orig_impacted = navigator_scope.project_likely_impacted
        navigator_scope.host_reasoning_packet = lambda document: {}
        navigator_scope.assess_scope_quality = lambda *args, **kwargs: {"status": "passed", "blocking": False, "mode": "code-change", "accepted_paths": []}
        navigator_scope.project_likely_impacted = lambda candidates: []

    def tearDown(self):
        navigator_scope.host_reasoning_packet = self._orig_packet
        navigator_scope.assess_scope_quality = self._orig_quality
        navigator_scope.project_likely_impacted = self._orig_impacted

    def test_matrix_rows_restamped_to_reresolved_fingerprint(self):
        old_document = _sealed([_owner_row()])
        navigator = {
            "scope_evidence": old_document,
            "task_types": [],
            "requirement_matrix": [{
                "display_id": "REQ-01",
                "scope_evidence": {
                    "state": "resolved",
                    "implementation_owners": ["scripts/task-start.py"],
                    "decision_fingerprint": "sha256:stale-pref-answer-decision",
                },
            }],
        }
        qa_document = _sealed([_owner_row(owners=["scripts/task-start.py", "scripts/planning_lock.py"])])
        self.assertNotEqual(
            qa_document["decision_fingerprint"], old_document["decision_fingerprint"]
        )
        report = {"navigator": navigator}
        task_start.apply_reresolved_evidence(
            report, Path("."), "Implement command recording onto requirement rows",
            qa_document, 1,
        )
        row_scope = report["navigator"]["requirement_matrix"][0]["scope_evidence"]
        self.assertEqual(row_scope["decision_fingerprint"], qa_document["decision_fingerprint"])


if __name__ == "__main__":
    unittest.main()
