import hashlib
import importlib.util
import json
import tempfile
import unittest
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
DETECTOR_PATH = ROOT / "scripts" / "aidlc-official-detect.py"


def load_detector():
    spec = importlib.util.spec_from_file_location("tailtrail_aidlc_official_detect_test", DETECTOR_PATH)
    assert spec and spec.loader
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


detector = load_detector()


def sha256(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def write_pack(root: Path, *, source: str | None = None) -> Path:
    pack = root / ".tailtrail" / "official-aidlc"
    pack.mkdir(parents=True)
    (pack / "LICENSE").write_text("MIT-0\n", encoding="utf-8")
    (pack / "core-workflow.md").write_text("# Official AI-DLC workflow\n", encoding="utf-8")
    manifest = {
        "schema_version": "1",
        "type": "tailtrail-official-aidlc-pack",
        "official": {
            "source": source or detector.OFFICIAL_SOURCE,
            "revision": "v2.0.0",
            "license": {"spdx": "MIT-0", "file": "LICENSE"},
        },
        "host_adapter": {"host": "codex", "rules_path": "core-workflow.md"},
        "integrity": {
            "algorithm": "sha256",
            "files": [
                {"path": "LICENSE", "sha256": sha256(pack / "LICENSE")},
                {"path": "core-workflow.md", "sha256": sha256(pack / "core-workflow.md")},
            ],
        },
    }
    path = pack / "manifest.json"
    path.write_text(json.dumps(manifest, indent=2), encoding="utf-8")
    return path


class OfficialAidlcCompatibilityTests(unittest.TestCase):
    def test_missing_pack_is_reported_without_mutation(self):
        with tempfile.TemporaryDirectory() as tmp:
            result = detector.status(Path(tmp))
        self.assertEqual(result["state"], "not-installed")
        self.assertFalse(result["compatible"])
        self.assertTrue(result["read_only"])

    def test_valid_pinned_pack_is_compatible(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            write_pack(root)
            result = detector.status(root)
        self.assertEqual(result["state"], "compatible")
        self.assertTrue(result["compatible"])
        self.assertEqual(result["integrity"]["verified_files"], 2)

    def test_altered_pack_is_detected_by_integrity_hash(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            write_pack(root)
            (root / ".tailtrail" / "official-aidlc" / "core-workflow.md").write_text("altered\n", encoding="utf-8")
            result = detector.status(root)
        self.assertEqual(result["state"], "altered")
        self.assertIn("integrity hash mismatch: core-workflow.md", result["issues"])

    def test_incompatible_metadata_is_rejected(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            write_pack(root, source="https://example.invalid/not-official")
            result = detector.status(root)
        self.assertEqual(result["state"], "incompatible")
        self.assertIn(f"official source must be `{detector.OFFICIAL_SOURCE}`", result["issues"])

    def test_manifest_path_cannot_escape_project_root(self):
        with tempfile.TemporaryDirectory() as tmp:
            with self.assertRaises(ValueError):
                detector.status(Path(tmp), "../manifest.json")
