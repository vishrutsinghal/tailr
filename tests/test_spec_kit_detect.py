from __future__ import annotations

import importlib.util
import tempfile
import unittest
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]


def load():
    spec = importlib.util.spec_from_file_location("spec_kit_detect_test", ROOT / "scripts" / "spec-kit-detect.py")
    assert spec and spec.loader
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


detect = load()


class SpecKitDetectionTests(unittest.TestCase):
    def write(self, root: Path, relative: str, content: str = "# Artifact\n") -> None:
        path = root / relative
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(content, encoding="utf-8")

    def test_absence_is_a_read_only_not_detected_result(self) -> None:
        with tempfile.TemporaryDirectory() as temp:
            root = Path(temp)
            result = detect.detect(root)
            self.assertEqual(result["state"], "not-detected")
            self.assertTrue(result["read_only"])
            self.assertFalse((root / ".tailtrail").exists())

    def test_detects_importable_feature_and_fingerprints_artifacts(self) -> None:
        with tempfile.TemporaryDirectory() as temp:
            root = Path(temp)
            self.write(root, ".specify/memory/constitution.md")
            self.write(root, "specs/014-order-amendment/spec.md")
            self.write(root, "specs/014-order-amendment/plan.md")
            self.write(root, "specs/014-order-amendment/tasks.md")
            self.write(root, "specs/014-order-amendment/contracts/api.yaml", "openapi: 3.0.0\n")
            result = detect.detect(root)
            self.assertEqual(result["state"], "compatible")
            self.assertEqual(result["features"][0]["feature_id"], "014-order-amendment")
            self.assertEqual(result["features"][0]["readiness"], "importable")
            self.assertTrue(result["source_revision"].startswith("sha256:"))
            self.assertEqual({entry["kind"] for entry in result["artifacts"]}, {"constitution", "spec", "plan", "tasks", "contract"})
            self.assertFalse((root / ".tailtrail").exists())

    def test_inspect_limits_output_to_requested_feature(self) -> None:
        with tempfile.TemporaryDirectory() as temp:
            root = Path(temp)
            self.write(root, "specs/001-alpha/spec.md")
            self.write(root, "specs/002-beta/spec.md")
            result = detect.detect(root, "002-beta")
            self.assertEqual(result["state"], "compatible")
            self.assertEqual([entry["feature_id"] for entry in result["features"]], ["002-beta"])
            self.assertTrue(all("002-beta" in entry["path"] for entry in result["artifacts"]))

    def test_oversized_artifact_is_incompatible_without_read_or_write_side_effects(self) -> None:
        with tempfile.TemporaryDirectory() as temp:
            root = Path(temp)
            self.write(root, "specs/001-large/spec.md", "x" * (1024 * 1024 + 1))
            result = detect.detect(root)
            self.assertEqual(result["state"], "incompatible")
            self.assertTrue(any("size limit" in issue for issue in result["issues"]))
            self.assertFalse((root / ".tailtrail").exists())

    def test_missing_requested_feature_is_explicit(self) -> None:
        with tempfile.TemporaryDirectory() as temp:
            root = Path(temp)
            self.write(root, "specs/001-alpha/spec.md")
            result = detect.detect(root, "999-missing")
            self.assertEqual(result["state"], "incompatible")
            self.assertIn("requested feature not found: 999-missing", result["issues"])


if __name__ == "__main__":
    unittest.main()
