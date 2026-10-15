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


if __name__ == "__main__":
    unittest.main()
