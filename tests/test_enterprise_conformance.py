import importlib.util
import json
import tempfile
import unittest
import zipfile
import subprocess
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]


def load_module():
    path = ROOT / "scripts/enterprise-conformance.py"
    spec = importlib.util.spec_from_file_location("enterprise_conformance_test", path)
    module = importlib.util.module_from_spec(spec)
    assert spec and spec.loader
    spec.loader.exec_module(module)
    return module


class EnterpriseConformanceTests(unittest.TestCase):
    def setUp(self):
        self.module = load_module()

    def test_catalog_covers_all_enterprise_domains_and_threat_cases(self):
        catalog = self.module.read_json(self.module.CATALOG)
        self.assertEqual([], self.module.catalog_errors(catalog))
        self.assertGreaterEqual(len(catalog["controls"]), 10)
        self.assertEqual(
            {"path-traversal", "symlink-escape", "command-injection", "untrusted-provider-json", "sensitive-data-leakage"},
            set(catalog["threat_cases"]),
        )

    def test_static_conformance_passes_without_inventing_platform_receipts(self):
        report = self.module.inspect(ROOT, run_probes=False)
        self.assertEqual("passed", report["status"])
        self.assertFalse(report["release_qualification"]["qualified"])
        self.assertEqual("not-observed", report["release_qualification"]["status"])
        self.assertFalse(report["compatibility"]["configured_is_observed"])

    def test_hosted_platform_report_must_cover_the_exact_matrix(self):
        with tempfile.TemporaryDirectory() as temporary:
            path = Path(temporary) / "platform.json"
            path.write_text(json.dumps({"type": "tailtrail-platform-qualification-report", "valid": True, "observed_cells": 5}), encoding="utf-8")
            blocked = self.module.inspect(ROOT, platform_report=path, run_probes=False)
            self.assertFalse(blocked["release_qualification"]["qualified"])
            path.write_text(json.dumps({"type": "tailtrail-platform-qualification-report", "valid": True, "observed_cells": 6}), encoding="utf-8")
            qualified = self.module.inspect(ROOT, platform_report=path, run_probes=False)
            self.assertTrue(qualified["release_qualification"]["qualified"])

    def test_offline_bundle_is_approval_gated_and_contains_no_project_evidence(self):
        with tempfile.TemporaryDirectory() as temporary:
            target = Path(temporary) / "enterprise.zip"
            with self.assertRaisesRegex(ValueError, "--approved"):
                self.module.create_bundle(ROOT, target, False)
            result = self.module.create_bundle(ROOT, target, True)
            self.assertTrue(target.is_file())
            with zipfile.ZipFile(target) as archive:
                names = set(archive.namelist())
                manifest = json.loads(archive.read("manifest.json"))
            self.assertEqual(set(result["files"]), names)
            self.assertEqual(set(manifest["files"]), names - {"manifest.json"})
            self.assertFalse(any("receipt" in name or ".tailtrail" in name for name in names))

    def test_missing_control_file_fails_closed(self):
        catalog = self.module.read_json(self.module.CATALOG)
        with tempfile.TemporaryDirectory() as temporary:
            copied = json.loads(json.dumps(catalog))
            copied["controls"][0]["required_paths"] = ["missing-contract.json"]
            path = Path(temporary) / "catalog.json"
            path.write_text(json.dumps(copied), encoding="utf-8")
            report = self.module.inspect(ROOT, path, run_probes=False)
        self.assertEqual("blocked", report["status"])
        self.assertIn("compatibility: missing missing-contract.json", report["issues"])

    def test_enterprise_readiness_cli_routes_conformance(self):
        result = subprocess.run(
            [sys.executable, str(ROOT / "scripts/tailtrail.py"), "enterprise-readiness", "--root", str(ROOT), "conformance", "--skip-probes"],
            cwd=ROOT,
            text=True,
            capture_output=True,
            check=False,
        )
        self.assertEqual(0, result.returncode, result.stderr)
        report = json.loads(result.stdout)
        self.assertEqual("passed", report["status"])
        self.assertEqual("not-observed", report["release_qualification"]["status"])


if __name__ == "__main__":
    unittest.main()
