from __future__ import annotations

import sys
import unittest
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "scripts"))

import navigator as NAV  # noqa: E402


def _load_task_start():
    import importlib.util

    spec = importlib.util.spec_from_file_location(
        "eval_precedence_task_start", ROOT / "scripts" / "task-start.py",
    )
    assert spec and spec.loader
    module = importlib.util.module_from_spec(spec)
    sys.modules[spec.name] = module
    spec.loader.exec_module(module)
    return module


START = _load_task_start()  # noqa: E402


IMPL_GOAL = "Create the Phase 2A Navigator Host Protocol and prove it with evidence"
READONLY_GOAL = "Create a security proof report"


class EvalRoutingPrecedenceTests(unittest.TestCase):
    def test_implementation_declaration_blocks_eval_despite_trigger_words(self) -> None:
        plan = NAV.evaluation_harness_plan(IMPL_GOAL, ["implementation"], "tailtrail", [])
        self.assertTrue(plan["selected"])
        self.assertFalse(NAV.evaluation_only_requested(IMPL_GOAL, plan, "implementation"))

    def test_no_declaration_preserves_keyword_fallback(self) -> None:
        plan = NAV.evaluation_harness_plan(IMPL_GOAL, [], "tailtrail", [])
        if plan["selected"]:
            self.assertTrue(NAV.evaluation_only_requested(IMPL_GOAL, plan, None))

    def test_readonly_report_goal_stays_eval(self) -> None:
        plan = NAV.evaluation_harness_plan(READONLY_GOAL, [], "tailtrail", [])
        self.assertTrue(plan["selected"])
        self.assertTrue(NAV.evaluation_only_requested(READONLY_GOAL, plan, None))
        self.assertTrue(NAV.evaluation_only_requested(READONLY_GOAL, plan, "qa"))

    def test_decide_routes_implementation_past_eval(self) -> None:
        report = NAV.decide(IMPL_GOAL, ROOT, [], "tailtrail", declared_task_type="implementation")
        self.assertNotEqual(report.get("navigator_mode"), "evaluation_harness")

    def test_decide_keeps_eval_fallback_without_declaration(self) -> None:
        report = NAV.decide(READONLY_GOAL, ROOT, [], "tailtrail")
        self.assertEqual(report.get("navigator_mode"), "evaluation_harness")
        self.assertEqual(
            report.get("routing_evidence", {}).get("authority_source"), "keyword-fallback",
        )


class ImplementationScopeInvariantTests(unittest.TestCase):
    def test_implementation_without_scope_is_blocking(self) -> None:
        report = {"goal": "x", "navigator": {"task_types": ["implementation"]}}
        self.assertTrue(START.declared_implementation_missing_scope(report, "implementation"))
        boundary = START.implementation_scope_missing_report(report, "implementation")
        self.assertTrue(boundary.get("scope_quality_boundary"))
        self.assertEqual(boundary.get("blocking_reason"), "missing-canonical-scope-evidence")
        self.assertIn("No Planning Lock", boundary.get("boundary", ""))

    def test_non_implementation_never_triggers(self) -> None:
        report = {"goal": "x", "navigator": {}}
        for declared in (None, "", "qa", "doc", "infra"):
            self.assertFalse(START.declared_implementation_missing_scope(report, declared))

    def test_scope_present_or_debug_never_triggers(self) -> None:
        report = {"goal": "x", "navigator": {"scope_evidence": {"state": "resolved"}}}
        self.assertFalse(START.declared_implementation_missing_scope(report, "implementation"))
        debug_report = {"goal": "x", "debug_plan": {}, "navigator": {}}
        self.assertFalse(START.declared_implementation_missing_scope(debug_report, "implementation"))


class ImplementationLockInvariantTests(unittest.TestCase):
    def _valid_report(self) -> dict:
        import navigator_scope as scope

        seeds = [scope.seed("scripts/task-start.py", "explicit-path", "user-provided-path")]
        candidates = scope.candidates_from_seeds(ROOT, seeds, ["implementation"])
        owned = [c for c in candidates if c.get("role") == "implementation-owner"]
        self.assertTrue(owned, "fixture needs an implementation-owner candidate")
        doc = scope.evidence_document(
            ROOT, "do the thing",
            [{"requirement_id": "REQ-01", "display_id": "REQ-01", "statement": "Do the thing.",
              "query_terms": ["thing"], "quoted_literals": []}],
            candidates,
        )
        # Resolve the single row the way an answered scope would: the
        # fingerprint is recomputed so the decision stays valid.
        doc["requirements"] = [{
            "requirement_id": "REQ-01", "display_id": "REQ-01",
            "statement_fingerprint": scope.fingerprint("Do the thing."),
            "query_terms": ["thing"], "scope_state": "resolved",
            "implementation_owners": ["scripts/task-start.py"],
            "inspection_paths": [], "proof_paths": [],
            "excluded_candidates": [], "confidence": "high",
            "reason_codes": ["bounded-static-owner-resolved"],
        }]
        doc.pop("decision_fingerprint", None)
        doc["decision_fingerprint"] = scope.fingerprint(scope._fingerprintable_document(doc))
        return {"goal": "do the thing",
                "navigator": {"scope_evidence": doc, "scope_quality": {"blocking": False},
                              "requirement_query_frame": {"requirements": [{"display_id": "REQ-01"}]},
                              "requirement_matrix": [{"display_id": "REQ-01"}]}}

    def test_valid_report_passes(self) -> None:
        # Seed an owner edge so the requirement resolves; quality stays passing.
        self.assertEqual(START.implementation_lock_blockers(self._valid_report(), "implementation"), [])

    def test_missing_evidence_blocks(self) -> None:
        report = {"goal": "x", "navigator": {}}
        blockers = START.implementation_lock_blockers(report, "implementation")
        self.assertEqual([b["reason"] for b in blockers], ["missing-canonical-scope-evidence"])

    def test_blocking_quality_blocks(self) -> None:
        report = self._valid_report()
        report["navigator"]["scope_quality"] = {"blocking": True}
        reasons = [b["reason"] for b in START.implementation_lock_blockers(report, "implementation")]
        self.assertIn("scope-quality-blocking-or-missing", reasons)

    def test_invalid_fingerprint_blocks(self) -> None:
        report = self._valid_report()
        report["navigator"]["scope_evidence"]["decision_fingerprint"] = "sha256:tampered"
        reasons = [b["reason"] for b in START.implementation_lock_blockers(report, "implementation")]
        self.assertIn("scope-decision-fingerprint-invalid", reasons)

    def test_non_implementation_never_blocks(self) -> None:
        report = {"goal": "x", "navigator": {}}
        for declared in (None, "", "qa", "doc"):
            self.assertEqual(START.implementation_lock_blockers(report, declared), [])


if __name__ == "__main__":
    unittest.main()
