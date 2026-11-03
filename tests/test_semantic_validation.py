from __future__ import annotations

import json
import tempfile
import unittest
from pathlib import Path

from scripts.semantic_validation import dependency_closure, validate_plan_gate, validate_semantic_row

_SATISFIED = {
    "requirement_id": "REQ-01",
    "requested_assertion": "emit a receipt",
    "current_observed_assertion": "emit a receipt",
    "expected_assertion": "emit a receipt",
    "pre_change_scenario": "run the receipt proof",
    "state": "satisfied",
    "reason": "trusted-observation-matches-requested-assertion",
    "evidence": [{"path": "scripts/x.py", "content_fingerprint": "sha256:" + "a" * 64}],
}


def _codes(findings: list[dict]) -> list[str]:
    return [finding["code"] for finding in findings]


class SemanticRowTests(unittest.TestCase):
    def test_trusted_satisfied_row_is_supported(self) -> None:
        self.assertEqual(validate_semantic_row(dict(_SATISFIED)), [])

    def test_satisfied_without_trusted_observation_is_rejected(self) -> None:
        row = {**_SATISFIED, "reason": "static-evidence-cannot-prove-runtime-behavior"}
        self.assertIn("satisfied-without-trusted-observation", _codes(validate_semantic_row(row)))

    def test_satisfied_with_mismatched_assertion_is_rejected(self) -> None:
        row = {**_SATISFIED, "current_observed_assertion": "emit nothing"}
        self.assertIn("satisfied-assertion-mismatch", _codes(validate_semantic_row(row)))

    def test_missing_or_partial_rows_need_expected_assertion_and_scenario(self) -> None:
        for state in ("missing", "partial"):
            row = {
                "requirement_id": "REQ-02",
                "state": state,
                "reason": "no-readable-owner-evidence",
                "expected_assertion": "",
                "pre_change_scenario": "",
            }
            codes = _codes(validate_semantic_row(row))
            self.assertIn("missing-expected-assertion", codes)
            self.assertIn("missing-proof-scenario", codes)

    def test_unknown_row_cannot_borrow_a_trusted_reason(self) -> None:
        row = {"requirement_id": "REQ-03", "state": "unknown", "reason": "trusted-observation-matches-requested-assertion"}
        self.assertIn("unknown-with-trusted-reason", _codes(validate_semantic_row(row)))

    def test_invalid_state_is_rejected(self) -> None:
        self.assertEqual(_codes(validate_semantic_row({"state": "probably"})), ["invalid-state"])


class PlanGateTests(unittest.TestCase):
    def test_all_satisfied_rows_cannot_carry_implementation_scope(self) -> None:
        findings = validate_plan_gate([dict(_SATISFIED)], ["scripts/x.py"])
        self.assertIn("already-satisfied-with-implementation-scope", _codes(findings))

    def test_satisfied_rows_without_owner_scope_are_allowed(self) -> None:
        self.assertEqual(validate_plan_gate([dict(_SATISFIED)], []), [])

    def test_mixed_rows_keep_implementation_scope(self) -> None:
        unknown = {"requirement_id": "REQ-02", "state": "unknown", "reason": "static-evidence-cannot-prove-runtime-behavior"}
        self.assertEqual(validate_plan_gate([dict(_SATISFIED), unknown], ["scripts/x.py"]), [])


class DependencyClosureTests(unittest.TestCase):
    def _repo(self, temp: str) -> Path:
        root = Path(temp)
        (root / "schemas").mkdir()
        (root / "schemas" / "widget-event.schema.json").write_text(
            json.dumps({"properties": {"type": {"const": "tailtrail-widget-event"}}}), encoding="utf-8"
        )
        (root / "scripts").mkdir()
        return root

    def test_owner_referencing_schema_outside_scope_is_reported(self) -> None:
        with tempfile.TemporaryDirectory() as temp:
            root = self._repo(temp)
            (root / "scripts" / "emit.py").write_text('EVENT = "tailtrail-widget-event"\n', encoding="utf-8")
            findings = dependency_closure(root, ["scripts/emit.py"])
            self.assertEqual([item["schema"] for item in findings], ["schemas/widget-event.schema.json"])
            self.assertEqual(findings[0]["code"], "schema-dependency-omitted")

    def test_schema_in_scope_or_justified_closes_the_dependency(self) -> None:
        with tempfile.TemporaryDirectory() as temp:
            root = self._repo(temp)
            (root / "scripts" / "emit.py").write_text('EVENT = "tailtrail-widget-event"\n', encoding="utf-8")
            self.assertEqual(dependency_closure(root, ["scripts/emit.py", "schemas/widget-event.schema.json"]), [])
            self.assertEqual(
                dependency_closure(
                    root, ["scripts/emit.py"], justified_unchanged=["schemas/widget-event.schema.json"]
                ),
                [],
            )

    def test_unrelated_owner_produces_no_findings(self) -> None:
        with tempfile.TemporaryDirectory() as temp:
            root = self._repo(temp)
            (root / "scripts" / "plain.py").write_text("VALUE = 1\n", encoding="utf-8")
            self.assertEqual(dependency_closure(root, ["scripts/plain.py"]), [])


if __name__ == "__main__":
    unittest.main()
