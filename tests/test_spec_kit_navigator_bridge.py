from __future__ import annotations

import importlib.util
import json
import sys
import tempfile
import unittest
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
SCRIPTS = ROOT / "scripts"
if str(SCRIPTS) not in sys.path:
    sys.path.insert(0, str(SCRIPTS))


def module(file: str, name: str):
    spec = importlib.util.spec_from_file_location(name, ROOT / "scripts" / file)
    assert spec and spec.loader
    loaded = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(loaded)
    return loaded


bridge = module("spec-kit-bridge.py", "spec_kit_navigator_bridge_test")
importer = module("spec-kit-import.py", "spec_kit_navigator_import_test")
lock = module("planning-lock.py", "spec_kit_navigator_lock_test")
task_start = module("task-start.py", "spec_kit_navigator_task_start_test")


class SpecKitNavigatorBridgeTests(unittest.TestCase):
    def write(self, root: Path, relative: str, content: str) -> None:
        path = root / relative
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(content, encoding="utf-8")

    def imported_fixture(self, root: Path) -> dict[str, object]:
        self.write(root, "specs/014-orders/spec.md", """FR-001: Customers can amend an order.
FR-002: The service preserves cancellation behavior.
## Acceptance Criteria
- Amendment succeeds before fulfilment.
""")
        importer.import_feature(root, "014-orders", "planning")
        return bridge.load(root, "014-orders")

    def test_imported_requirements_become_the_traceable_matrix(self) -> None:
        with tempfile.TemporaryDirectory() as temp:
            root = Path(temp)
            source = self.imported_fixture(root)
            matrix = bridge.requirement_matrix(source, ["src/orders/service.py"])
            self.assertEqual([row["display_id"] for row in matrix], ["FR-001", "FR-002"])
            self.assertEqual(matrix[0]["source_reference"]["external_id"], "FR-001")
            self.assertEqual(matrix[0]["likely_paths"], ["src/orders/service.py"])

    def test_changed_source_blocks_planning_bridge_until_a_new_import_and_amendment(self) -> None:
        with tempfile.TemporaryDirectory() as temp:
            root = Path(temp)
            self.imported_fixture(root)
            spec = root / "specs/014-orders/spec.md"
            spec.write_text(spec.read_text(encoding="utf-8") + "\nFR-003: Record an audit event.\n", encoding="utf-8")
            with self.assertRaisesRegex(ValueError, "changed after import"):
                bridge.load(root, "014-orders")

    def test_activation_preserves_source_reference_in_anchor(self) -> None:
        with tempfile.TemporaryDirectory() as temp:
            root = Path(temp)
            source = self.imported_fixture(root)
            report = {"goal": "Use Spec Kit feature 014-orders", "guided_delivery": {"mode": "guided-delivery"}, "navigator": {"requirement_matrix": bridge.requirement_matrix(source, ["src/orders/service.py"])}, "spec_kit_source": source}
            lock.create(root, report["goal"], "spec-kit-plan")
            lock.save_start_report(root, "spec-kit-plan", report)
            activated = lock.activate(root, "spec-kit-plan", True)
            anchor = json.loads((root / activated["anchor"]["artifact"]).read_text(encoding="utf-8"))
            self.assertEqual(anchor["requirements"][0]["display_id"], "FR-001")
            self.assertEqual(anchor["requirements"][0]["source_reference"]["source_uid"], "speckit://local/014-orders")

    def test_navigator_start_uses_imported_requirements_without_regeneration(self) -> None:
        with tempfile.TemporaryDirectory() as temp:
            root = Path(temp)
            self.imported_fixture(root)
            report = task_start.build_report("Use existing Spec Kit feature 014-orders", root, [], "python3 scripts/tailtrail.py", spec_kit_feature="014-orders")
            self.assertEqual(report["spec_kit_source"]["feature_id"], "014-orders")
            self.assertEqual([row["display_id"] for row in report["navigator"]["requirement_matrix"]], ["FR-001", "FR-002"])
            self.assertEqual(report["navigator"]["selected_features"][0]["name"], "Intent Bridge")
            rendered = task_start.render_markdown(report, verbose=True)
            self.assertIn("**FR-001:** Customers can amend an order.", rendered)

    def test_goal_parser_requires_explicit_feature_phrase(self) -> None:
        self.assertEqual(bridge.feature_from_goal("Use existing Spec Kit feature 014-orders"), "014-orders")
        self.assertEqual(bridge.feature_from_goal("Use Intent Bridge feature 014-orders"), "014-orders")
        self.assertIsNone(bridge.feature_from_goal("Use Spec Kit and TailTrail"))


if __name__ == "__main__":
    unittest.main()
