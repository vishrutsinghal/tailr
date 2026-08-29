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


class NavigatorDebugRoutingTests(unittest.TestCase):
    def test_bug_report_phrasing_classifies_as_debug(self):
        goal = "orders sometimes charged twice when payment times out"
        self.assertEqual(tailtrail.classify_start_intent(goal, [goal]), "debug")

    def test_ordinary_feature_request_classifies_as_build(self):
        goal = "add pagination to the orders list endpoint"
        self.assertEqual(tailtrail.classify_start_intent(goal, [goal]), "build")

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


if __name__ == "__main__":
    unittest.main()
