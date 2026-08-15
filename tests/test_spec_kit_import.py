from __future__ import annotations

import importlib.util
import json
import tempfile
import unittest
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]


def load():
    spec = importlib.util.spec_from_file_location("spec_kit_import_test", ROOT / "scripts" / "spec-kit-import.py")
    assert spec and spec.loader
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


bridge = load()


class SpecKitImportTests(unittest.TestCase):
    def write(self, root: Path, relative: str, content: str) -> None:
        path = root / relative
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(content, encoding="utf-8")

    def fixture(self, root: Path) -> None:
        self.write(root, ".specify/memory/constitution.md", "# Constitution\n")
        self.write(root, "specs/014-order-amendment/spec.md", """# Order amendment

## Requirements
FR-001: Customers can amend an order before fulfilment.
FR-002: The service must update the documented contracts/api.yaml endpoint.

## User stories
US-001: A customer changes quantity.

## Acceptance Criteria
- Given an unfulfilled order, amendment succeeds.
""")
        self.write(root, "specs/014-order-amendment/tasks.md", "T001: Implement amendment [US-001]\n")
        self.write(root, "specs/014-order-amendment/contracts/api.yaml", "openapi: 3.0.0\n")

    def test_import_creates_complete_immutable_snapshot_set(self) -> None:
        with tempfile.TemporaryDirectory() as temp:
            root = Path(temp)
            self.fixture(root)
            result = bridge.import_feature(root, "014-order-amendment", "review")
            directory = root / ".tailtrail" / "spec-kit" / "sources" / "014-order-amendment"
            self.assertEqual(result["state"], "imported")
            self.assertEqual(result["version"], 1)
            self.assertEqual(len(result["artifacts_written"]), 7)
            imported = json.loads((directory / "import-v1.json").read_text(encoding="utf-8"))
            self.assertEqual(imported["privacy_boundary"], "normalized-references-only")
            self.assertEqual([item["external_id"] for item in imported["requirements"]], ["FR-001", "FR-002"])
            self.assertFalse(any("# Order amendment" in path.read_text(encoding="utf-8") for path in directory.glob("*.json")))

    def test_same_source_is_idempotent_and_changed_source_gets_new_version(self) -> None:
        with tempfile.TemporaryDirectory() as temp:
            root = Path(temp)
            self.fixture(root)
            first = bridge.import_feature(root, "014-order-amendment", "review")
            second = bridge.import_feature(root, "014-order-amendment", "review")
            self.assertEqual(first["state"], "imported")
            self.assertEqual(second["state"], "already-imported")
            spec = root / "specs/014-order-amendment/spec.md"
            spec.write_text(spec.read_text(encoding="utf-8") + "\nFR-003: Preserve audit history.\n", encoding="utf-8")
            third = bridge.import_feature(root, "014-order-amendment", "planning")
            self.assertEqual(third["state"], "imported")
            self.assertEqual(third["version"], 2)
            self.assertTrue((root / ".tailtrail/spec-kit/sources/014-order-amendment/source-v1.json").is_file())
            self.assertTrue((root / ".tailtrail/spec-kit/sources/014-order-amendment/source-v2.json").is_file())

    def test_rejects_missing_acceptance_criteria_without_creating_snapshot_state(self) -> None:
        with tempfile.TemporaryDirectory() as temp:
            root = Path(temp)
            self.write(root, "specs/001-invalid/spec.md", "FR-001: A requirement without proof.\n")
            with self.assertRaisesRegex(ValueError, "acceptance criteria"):
                bridge.import_feature(root, "001-invalid", "review")
            self.assertFalse((root / ".tailtrail").exists())

    def test_rejects_duplicate_requirement_ids_without_creating_snapshot_state(self) -> None:
        with tempfile.TemporaryDirectory() as temp:
            root = Path(temp)
            self.write(root, "specs/001-duplicate/spec.md", """FR-001: First.
FR-001: Second.
## Acceptance Criteria
- Example.
""")
            with self.assertRaisesRegex(ValueError, "duplicate requirement"):
                bridge.import_feature(root, "001-duplicate", "review")
            self.assertFalse((root / ".tailtrail").exists())

    def test_rejects_sensitive_normalized_reference_without_creating_snapshot_state(self) -> None:
        with tempfile.TemporaryDirectory() as temp:
            root = Path(temp)
            self.write(root, "specs/001-sensitive/spec.md", """FR-001: Do not reveal a secret value.
## Acceptance Criteria
- Example.
""")
            with self.assertRaisesRegex(ValueError, "privacy policy"):
                bridge.import_feature(root, "001-sensitive", "review")
            self.assertFalse((root / ".tailtrail").exists())

    def test_rejects_unknown_story_reference_without_creating_snapshot_state(self) -> None:
        with tempfile.TemporaryDirectory() as temp:
            root = Path(temp)
            self.write(root, "specs/001-story/spec.md", """FR-001: Change an order.
US-001: A customer changes an order.
## Acceptance Criteria
- Example.
""")
            self.write(root, "specs/001-story/tasks.md", "T001: Build it [US-999]\n")
            with self.assertRaisesRegex(ValueError, "unknown story"):
                bridge.import_feature(root, "001-story", "review")
            self.assertFalse((root / ".tailtrail").exists())


if __name__ == "__main__":
    unittest.main()
