from __future__ import annotations

import importlib.util
import io
import json
import tempfile
import unittest
import zipfile
from pathlib import Path


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


if __name__ == "__main__":
    unittest.main()
