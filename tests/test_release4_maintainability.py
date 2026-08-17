from __future__ import annotations

import importlib.util
import sys
import tempfile
import unittest
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
SCRIPTS = ROOT / "scripts"
if SCRIPTS.as_posix() not in sys.path:
    sys.path.insert(0, SCRIPTS.as_posix())


def load(name: str, filename: str):
    spec = importlib.util.spec_from_file_location(name, ROOT / "scripts" / filename)
    assert spec and spec.loader
    module = importlib.util.module_from_spec(spec)
    sys.modules[name] = module
    spec.loader.exec_module(module)
    return module


navigator = load("tailtrail_release4_navigator", "navigator.py")
discovery = load("tailtrail_release4_discovery", "navigator_discovery.py")
task_start = load("tailtrail_release4_task_start", "task-start.py")
posture = load("tailtrail_release4_start_posture", "start_posture.py")


class Release4MaintainabilityTests(unittest.TestCase):
    def test_navigator_discovery_wrappers_preserve_local_selection(self) -> None:
        with tempfile.TemporaryDirectory() as temp:
            root = Path(temp)
            source = root / "src" / "orders" / "validation.py"
            source.parent.mkdir(parents=True)
            source.write_text("def validate_quantity(value):\n    return value > 0\n", encoding="utf-8")
            test = root / "tests" / "test_validation.py"
            test.parent.mkdir(parents=True)
            test.write_text("def test_zero_quantity(): pass\n", encoding="utf-8")
            goal = "fix zero quantity validation"
            self.assertEqual(navigator.goal_discovered_paths(root, goal), discovery.goal_discovered_paths(root, goal))
            self.assertEqual(navigator.repository_discovered_paths(root, goal), discovery.repository_discovered_paths(root, goal))
            self.assertFalse(navigator.is_actionable_changed_path(root, ".tailtrail/state.json"))
            self.assertTrue(navigator.is_actionable_changed_path(root, "src/orders/validation.py"))

    def test_start_posture_extraction_preserves_token_and_operational_contract(self) -> None:
        with tempfile.TemporaryDirectory() as temp:
            root = Path(temp)
            source = root / "src" / "validation.py"
            source.parent.mkdir(parents=True)
            source.write_text("x" * 40, encoding="utf-8")
            plan = {"likely_impacted_files": [{"path": "src/validation.py"}], "avoid": []}
            self.assertEqual(
                task_start.token_posture(root, plan),
                posture.token_posture(root, plan, task_start.LARGE_CONTEXT_FILES, task_start.APPROX_CHARS_PER_TOKEN),
            )
            self.assertEqual(task_start.setup_posture(root, "tailtrail"), posture.setup_posture(root, "tailtrail", task_start.ROOT))

    def test_start_rendering_contract_remains_intact_after_extraction(self) -> None:
        with tempfile.TemporaryDirectory() as temp:
            root = Path(temp)
            source = root / "src" / "order_service" / "validation.py"
            source.parent.mkdir(parents=True)
            source.write_text("def validate_quantity(value):\n    return value > 0\n", encoding="utf-8")
            test = root / "tests" / "unit" / "test_validation.py"
            test.parent.mkdir(parents=True)
            test.write_text("import unittest\n", encoding="utf-8")
            report = task_start.build_report("fix zero quantity validation", root, ["src/order_service/validation.py", "tests/unit/test_validation.py"], "tailtrail")
            compact = task_start.compact_start_report(report)
            verbose = task_start.verbose_start_report(report)
            for heading in ("## Scope", "## Requirements", "## Selected TailTrail features", "## Focused validation", "## Approval"):
                self.assertIn(heading, compact)
            for heading in ("## Planning Lock", "## Start Here", "## Navigator Decision", "## Selected TailTrail features", "## Deferred TailTrail features", "## Guided Delivery", "## Validation", "## Evidence posture", "## Approval"):
                self.assertIn(heading, verbose)

    def test_extracted_modules_are_part_of_the_real_planning_path(self) -> None:
        navigator_body = (ROOT / "scripts" / "navigator.py").read_text(encoding="utf-8")
        start_body = (ROOT / "scripts" / "task-start.py").read_text(encoding="utf-8")
        self.assertIn("import navigator_discovery as discovery", navigator_body)
        self.assertIn("return discovery.goal_discovered_paths", navigator_body)
        self.assertIn("import start_posture", start_body)
        self.assertIn("start_posture.token_posture", start_body)
        self.assertIn("start_posture.evaluation_posture", start_body)
