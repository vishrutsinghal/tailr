from __future__ import annotations

import importlib.util
import json
import tempfile
import unittest
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]


def module(file: str, name: str):
    spec = importlib.util.spec_from_file_location(name, ROOT / "scripts" / file)
    assert spec and spec.loader
    result = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(result)
    return result


importer = module("spec-kit-import.py", "spec_kit_slices_import_test")
bridge = module("spec-kit-bridge.py", "spec_kit_slices_bridge_test")
lock = module("planning-lock.py", "spec_kit_slices_lock_test")
slices = module("spec-kit-slices.py", "spec_kit_slices_test")


class SpecKitSliceTests(unittest.TestCase):
    def write(self, root: Path, relative: str, content: str) -> None:
        path = root / relative
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(content, encoding="utf-8")

    def activate(self, root: Path) -> dict[str, object]:
        self.write(root, "specs/001-orders/spec.md", """FR-001: Amend an order before fulfilment.
FR-002: Preserve cancellation behavior.
## Acceptance Criteria
- The service accepts a valid amendment.
""")
        importer.import_feature(root, "001-orders", "planning")
        source = bridge.load(root, "001-orders")
        report = {"goal": "Use Spec Kit feature 001-orders", "guided_delivery": {"mode": "guided-delivery"}, "navigator": {"requirement_matrix": bridge.requirement_matrix(source, ["src/orders.py"])}, "spec_kit_source": source}
        lock.create(root, report["goal"], "slice-run")
        lock.save_start_report(root, "slice-run", report)
        return lock.activate(root, "slice-run", True)

    def test_activation_creates_complete_source_mapping_and_first_active_slice(self) -> None:
        with tempfile.TemporaryDirectory() as temp:
            root = Path(temp)
            activated = self.activate(root)
            result = activated["spec_kit_slices"]
            self.assertEqual(result["state"], "created")
            self.assertEqual(result["active_slice"], "slice-1")
            self.assertEqual(activated["execution_handoff"]["spec_kit_slice"]["active_slice"], "slice-1")
            mapping = json.loads((root / result["artifacts"]["mapping"]).read_text(encoding="utf-8"))
            self.assertEqual([item["external_id"] for item in mapping["mappings"]], ["FR-001", "FR-002"])
            state = slices.show(root, "slice-run")
            self.assertEqual(state["slices"][0]["state"], "active")
            self.assertEqual(state["slices"][1]["state"], "pending")

    def test_only_active_requirement_is_allowed_and_advance_requires_approval(self) -> None:
        with tempfile.TemporaryDirectory() as temp:
            root = Path(temp)
            activated = self.activate(root)
            anchor = json.loads((root / activated["anchor"]["artifact"]).read_text(encoding="utf-8"))
            first, second = [item["requirement_uid"] for item in anchor["requirements"]]
            self.assertEqual(slices.assert_active(root, "slice-run", first)["state"], "allowed")
            with self.assertRaisesRegex(ValueError, "not in active"):
                slices.assert_active(root, "slice-run", second)
            with self.assertRaisesRegex(ValueError, "requires --approved"):
                slices.advance(root, "slice-run", first, False)
            advanced = slices.advance(root, "slice-run", first, True)
            self.assertEqual(advanced["next_active_slice"], "slice-2")
            self.assertEqual(slices.assert_active(root, "slice-run", second)["state"], "allowed")


if __name__ == "__main__":
    unittest.main()
