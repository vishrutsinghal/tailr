import hashlib
import importlib.util
import io
import json
import tempfile
import unittest
import zipfile
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
DETECTOR_PATH = ROOT / "scripts" / "aidlc-official-detect.py"
INSTALLER_PATH = ROOT / "scripts" / "aidlc-official-install.py"


def load_detector():
    spec = importlib.util.spec_from_file_location("tailtrail_aidlc_official_detect_test", DETECTOR_PATH)
    assert spec and spec.loader
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


detector = load_detector()


def load_installer():
    spec = importlib.util.spec_from_file_location("tailtrail_aidlc_official_install_detect_test", INSTALLER_PATH)
    assert spec and spec.loader
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


installer = load_installer()
COMMIT = "a" * 40
V2_FILES = {
    "aws-aidlc-rules/core-workflow.md": b"# Official flow\n",
    "aws-aidlc-rule-details/inception/requirements-analysis.md": b"# Requirements\n",
    "aws-aidlc-rule-details/common/question-format-guide.md": b"# Questions\n",
    "aws-aidlc-rule-details/common/content-validation.md": b"# Content validation\n",
    "aws-aidlc-rule-details/common/session-continuity.md": b"# Session continuity\n",
}


def write_v2_pack(root: Path) -> Path:
    bundle_root = root / "aidlc-rules"
    bundle_root.mkdir(parents=True)
    (bundle_root / "VERSION").write_text("0.1.8\n", encoding="utf-8")
    for relative, content in V2_FILES.items():
        path = bundle_root / relative
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_bytes(content)
    archive = io.BytesIO()
    with zipfile.ZipFile(archive, "w") as bundle:
        for relative, content in V2_FILES.items():
            bundle.writestr(f"aidlc-rules/{relative}", content)
    installer.prepare_checked_in_bundle(
        root,
        revision="v1.0.1",
        commit=COMMIT,
        archive_bytes=archive.getvalue(),
        license_bytes=b"MIT No Attribution\n",
        commit_evidence=json.dumps({"sha": COMMIT}).encode(),
        acquired_at="2026-11-04T00:00:00Z",
    )
    return bundle_root / "manifest.json"


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

    def test_valid_schema_v2_bundle_is_compatible_and_host_neutral(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            manifest = write_v2_pack(root)
            result = detector.status(root, manifest.relative_to(root))

        self.assertEqual(result["state"], "compatible")
        self.assertTrue(result["compatible"])
        self.assertEqual(result["official"]["commit"], COMMIT)
        self.assertEqual(result["integrity"]["verified_files"], len(V2_FILES) + 4)

    def test_schema_v2_rejects_unexpected_file_and_provenance_conflict(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            manifest_path = write_v2_pack(root)
            (manifest_path.parent / "unexpected.txt").write_text("unexpected\n", encoding="utf-8")
            result = detector.status(root, manifest_path.relative_to(root))
            self.assertEqual(result["state"], "altered")
            self.assertIn("integrity inventory has an unexpected file: unexpected.txt", result["issues"])

            (manifest_path.parent / "unexpected.txt").unlink()
            provenance_path = manifest_path.parent / "PROVENANCE.json"
            provenance = json.loads(provenance_path.read_text(encoding="utf-8"))
            provenance["official"]["commit"] = "b" * 40
            provenance_path.write_text(json.dumps(provenance, indent=2, sort_keys=True) + "\n", encoding="utf-8")
            manifest = json.loads(manifest_path.read_text(encoding="utf-8"))
            for entry in manifest["integrity"]["files"]:
                if entry["path"] == "PROVENANCE.json":
                    entry["sha256"] = sha256(provenance_path)
            manifest_path.write_text(json.dumps(manifest, indent=2, sort_keys=True) + "\n", encoding="utf-8")
            result = detector.status(root, manifest_path.relative_to(root))

        self.assertEqual(result["state"], "incompatible")
        self.assertIn("manifest and PROVENANCE.json disagree on official commit", result["issues"])
