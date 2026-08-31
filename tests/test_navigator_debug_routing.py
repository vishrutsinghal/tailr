from __future__ import annotations
import importlib.util, sys, unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]


def load(name, path):
    spec = importlib.util.spec_from_file_location(name, ROOT / path)
    module = importlib.util.module_from_spec(spec)
    assert spec and spec.loader
    sys.modules[name] = module
    spec.loader.exec_module(module)
    return module


tailtrail = load("navigator_debug_routing_test_tailtrail", "scripts/tailtrail.py")
navigator = load("navigator_debug_routing_test_navigator", "scripts/navigator.py")
navigator_core = load("navigator_debug_routing_test_core", "scripts/navigator_core.py")


class NavigatorDebugRoutingTests(unittest.TestCase):
    def test_bug_report_phrasing_classifies_as_debug(self):
        goal = "orders sometimes charged twice when payment times out"
        self.assertEqual(tailtrail.classify_start_intent(goal, [goal]), "debug")
        decision = navigator_core.classify_workflow_intent(goal)
        self.assertEqual(decision.workflow_type, "debug-investigation")
        self.assertEqual(decision.reason_code, "symptom-first-phrase")
        self.assertIn("deterministic reproduction command and observed outcome", decision.unknown_evidence)

    def test_ordinary_feature_request_classifies_as_build(self):
        goal = "add pagination to the orders list endpoint"
        self.assertEqual(tailtrail.classify_start_intent(goal, [goal]), "build")
        self.assertEqual(navigator_core.classify_workflow_intent(goal).reason_code, "implementation-intent")

    def test_ambiguous_fix_defaults_to_build_and_shows_debug_alternative(self):
        decision = navigator_core.classify_workflow_intent("fix payment retry logic")
        self.assertEqual(decision.workflow_type, "build")
        self.assertEqual(decision.reason_code, "ambiguous-default-build")
        self.assertIn("--debug", decision.alternative or "")

    def test_investigate_why_routes_to_debug(self):
        decision = navigator_core.classify_workflow_intent("investigate why cancellation publishes two events")
        self.assertEqual(decision.workflow_type, "debug-investigation")

    def test_navigator_report_exposes_typed_debug_decision(self):
        report = navigator.decide(
            "payments are sometimes charged twice after timeout",
            ROOT,
            [],
            "python3 scripts/tailtrail.py",
            detect_git_changes=False,
        )
        classification = report["workflow_classification"]
        self.assertEqual(classification["workflow_type"], "debug-investigation")
        self.assertEqual(classification["known_symptom"], "payments are sometimes charged twice after timeout")
        self.assertTrue(classification["unknown_evidence"])
        self.assertEqual(report["task_types"], ["debug"])
        self.assertEqual(report["recommended_workflow"][0], "debug_intake")
        self.assertNotIn("implementation", report["recommended_workflow"])
        self.assertTrue(any(item["name"] == "Debug Harness" for item in report["selected_features"]))

    def test_error_or_command_flag_forces_debug(self):
        goal = "checkout is misbehaving"
        self.assertEqual(tailtrail.classify_start_intent(goal, [goal, "--error", "trace.txt"]), "debug")
        self.assertEqual(tailtrail.classify_start_intent(goal, [goal, "--command", "pytest -k checkout"]), "debug")

    def test_explicit_debug_and_build_flags_override_heuristics(self):
        bug_goal = "orders sometimes charged twice when payment times out"
        feature_goal = "add pagination to the orders list endpoint"
        self.assertEqual(tailtrail.classify_start_intent(bug_goal, [bug_goal, "--build"]), "build")
        self.assertEqual(tailtrail.classify_start_intent(feature_goal, [feature_goal, "--debug"]), "debug")

    def test_forward_args_drop_build_only_flags_and_keep_debug_flags(self):
        args = ["a bug report", "--changed", "src/x.py", "--verbose", "--error", "trace.txt", "--run-id", "run-1", "--attach", "--debug"]
        self.assertEqual(
            tailtrail.filter_debug_forward_args(args),
            ["a bug report", "--error", "trace.txt", "--run-id", "run-1", "--attach"],
        )

    def test_forward_args_keep_root(self):
        args = ["a bug report", "--root", "/tmp/target-project", "--run-id", "run-1"]
        self.assertEqual(
            tailtrail.filter_debug_forward_args(args),
            ["a bug report", "--root", "/tmp/target-project", "--run-id", "run-1"],
        )


if __name__ == "__main__":
    unittest.main()
