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


importer = module("spec-kit-import.py", "spec_kit_amendment_import")
bridge = module("spec-kit-bridge.py", "spec_kit_amendment_bridge")
lock = module("planning-lock.py", "spec_kit_amendment_lock")
amendment = module("spec-kit-amendment.py", "spec_kit_amendment_test")
slices = module("spec-kit-slices.py", "spec_kit_amendment_slices_test")


class SpecKitAmendmentTests(unittest.TestCase):
    def write(self, root: Path, relative: str, content: str) -> None:
        path = root / relative
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(content, encoding="utf-8")

    def activate(self, root: Path) -> None:
        self.write(root, "specs/001-orders/spec.md", """FR-001: Amend an order before fulfilment.
FR-002: Preserve cancellation behavior.
## Acceptance Criteria
- The service accepts a valid amendment.
""")
        importer.import_feature(root, "001-orders", "planning")
        source = bridge.load(root, "001-orders")
        report = {"goal": "Use Spec Kit feature 001-orders", "guided_delivery": {"mode": "guided-delivery"}, "navigator": {"requirement_matrix": bridge.requirement_matrix(source, ["src/orders.py"])}, "spec_kit_source": source}
        lock.create(root, report["goal"], "amendment-run")
        lock.save_start_report(root, "amendment-run", report)
        lock.activate(root, "amendment-run", True)

    def test_material_amendment_requires_import_and_explicit_approval(self) -> None:
        with tempfile.TemporaryDirectory() as temp:
            root = Path(temp); self.activate(root)
            self.write(root, "specs/001-orders/spec.md", """FR-001: Amend an order before fulfilment with idempotency.
FR-003: Record an immutable amendment audit event.
## Acceptance Criteria
- The service accepts a valid amendment.
""")
            self.assertEqual(amendment.check(root, "amendment-run")["state"], "import-required")
            importer.import_feature(root, "001-orders", "planning")
            proposed = amendment.propose(root, "amendment-run")
            self.assertEqual(proposed["state"], "approval-required")
            self.assertTrue(any(item["kind"] == "revoked" for item in proposed["changes"]))
            with self.assertRaisesRegex(ValueError, "requires --approved"):
                amendment.approve(root, "amendment-run", False)
            approved = amendment.approve(root, "amendment-run", True)
            self.assertEqual(approved["state"], "approved")
            self.assertTrue((root / approved["anchor"]).is_file())
            self.assertTrue((root / approved["correction"]).is_file())
            self.assertEqual(slices.show(root, "amendment-run")["source_lock"].endswith("source-lock-v2.json"), True)
            recovery = amendment.recovery(root, "amendment-run")
            self.assertEqual(recovery["state"], "planned")
            self.assertEqual(recovery["mode"], "task-owned-reconciliation")

    def test_non_material_imported_source_change_does_not_need_approval(self) -> None:
        with tempfile.TemporaryDirectory() as temp:
            root = Path(temp); self.activate(root)
            self.write(root, "specs/001-orders/spec.md", """# Order amendment
FR-001: Amend an order before fulfilment.
FR-002: Preserve cancellation behavior.
## Acceptance Criteria
- The service accepts a valid amendment.
""")
            importer.import_feature(root, "001-orders", "planning")
            proposed = amendment.propose(root, "amendment-run")
            self.assertEqual(proposed["state"], "non-material")


if __name__ == "__main__":
    unittest.main()
