from __future__ import annotations

import importlib.util
import io
import json
import tempfile
import unittest
import zipfile
from pathlib import Path

import jsonschema


ROOT = Path(__file__).resolve().parents[1]


def load():
    spec = importlib.util.spec_from_file_location("aidlc_official_install_test", ROOT / "scripts" / "aidlc-official-install.py")
    assert spec and spec.loader
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


installer = load()


def archive() -> bytes:
    output = io.BytesIO()
    with zipfile.ZipFile(output, "w") as bundle:
        bundle.writestr("aidlc-rules/aws-aidlc-rules/core-workflow.md", "# Official flow\n")
        bundle.writestr("aidlc-rules/aws-aidlc-rule-details/inception/requirements-analysis.md", "# Requirements\n")
    return output.getvalue()


class OfficialAidlcInstallTests(unittest.TestCase):
    def test_installs_real_archive_layout_and_produces_compatible_manifest(self) -> None:
        with tempfile.TemporaryDirectory() as temp:
            root = Path(temp)
            result = installer.install(root, revision="v1.0.1", host="copilot", archive_bytes=archive(), license_bytes=b"MIT-0\n", commit="e49341d")
            manifest = json.loads((root / result["manifest"]).read_text(encoding="utf-8"))
            self.assertEqual(result["state"], "installed")
            self.assertEqual(manifest["host_adapter"]["rules_path"], "aws-aidlc-rules/core-workflow.md")
            self.assertTrue((root / ".tailtrail" / "official-aidlc" / "aws-aidlc-rule-details" / "inception" / "requirements-analysis.md").is_file())
            detector_spec = importlib.util.spec_from_file_location("aidlc_detector_test", ROOT / "scripts" / "aidlc-official-detect.py")
            assert detector_spec and detector_spec.loader
            detector = importlib.util.module_from_spec(detector_spec); detector_spec.loader.exec_module(detector)
            self.assertTrue(detector.status(root)["compatible"])

    def test_never_overwrites_existing_pinned_pack(self) -> None:
        with tempfile.TemporaryDirectory() as temp:
            root = Path(temp)
            installer.install(root, revision="v1.0.1", host="generic", archive_bytes=archive(), license_bytes=b"MIT-0\n")
            with self.assertRaisesRegex(ValueError, "already exists"):
                installer.install(root, revision="v1.0.1", host="generic", archive_bytes=archive(), license_bytes=b"MIT-0\n")

    def test_rejects_archive_without_official_core_workflow(self) -> None:
        broken = io.BytesIO()
        with zipfile.ZipFile(broken, "w") as bundle:
            bundle.writestr("aidlc-rules/README.md", "missing core")
        with tempfile.TemporaryDirectory() as temp:
            with self.assertRaisesRegex(ValueError, "core-workflow"):
                installer.install(Path(temp), revision="v1.0.1", host="generic", archive_bytes=broken.getvalue(), license_bytes=b"MIT-0\n")

    def test_manifest_schema_accepts_restrictive_v1_and_closed_v2_only(self) -> None:
        schema = json.loads((ROOT / "schemas" / "official-aidlc-pack.schema.json").read_text(encoding="utf-8"))
        validator = jsonschema.Draft202012Validator(schema)
        jsonschema.Draft202012Validator.check_schema(schema)
        with tempfile.TemporaryDirectory() as temp:
            root = Path(temp)
            result = installer.install(
                root, revision="v1.0.1", host="codex", archive_bytes=archive(),
                license_bytes=b"MIT-0\n", commit="e49341d",
            )
            v1 = json.loads((root / result["manifest"]).read_text(encoding="utf-8"))
        validator.validate(v1)

        v2 = {
            "schema_version": "2",
            "type": "tailtrail-bundled-official-aidlc-pack",
            "bundle": {
                "format_version": "1", "tailtrail_version": "1.1.0",
                "bundle_version": "1", "created_from": "verified-upstream-release",
            },
            "official": {
                "source": installer.OFFICIAL_SOURCE, "revision": "v1.0.1",
                "commit": "a" * 40, "source_archive_sha256": "b" * 64,
                "license": {"spdx": "MIT-0", "file": "LICENSE", "sha256": "c" * 64},
            },
            "compatibility": {
                "minimum_tailtrail_version": "1.1.0",
                "maximum_tailtrail_version_exclusive": "2.0.0",
                "manifest_schema": "2", "supported_hosts": ["codex", "copilot", "claude"],
            },
            "required_capabilities": {"requirements": list(installer.REQUIRED_REQUIREMENTS_CAPABILITIES)},
            "integrity": {"algorithm": "sha256", "files": [{"path": "LICENSE", "sha256": "c" * 64}]},
        }
        validator.validate(v2)
        v2["unexpected"] = True
        self.assertTrue(list(validator.iter_errors(v2)))


if __name__ == "__main__":
    unittest.main()
