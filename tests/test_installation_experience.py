"""Validation: ``python3 -m unittest tests.test_installation_experience``."""

from __future__ import annotations

import hashlib
import importlib.util
import json
import subprocess
import sys
import tempfile
import unittest
import zipfile
from pathlib import Path
from unittest import mock


ROOT = Path(__file__).resolve().parents[1]
if ROOT.as_posix() not in sys.path:
    sys.path.insert(0, ROOT.as_posix())

from tailtrail.hosts.contracts import HOSTS, contract
from tailtrail.install import InstallEngine
from tailtrail.install.cli import _auto_hosts
from tailtrail.upgrade import upgrade


def load_script(name: str, filename: str):
    spec = importlib.util.spec_from_file_location(name, ROOT / "scripts" / filename)
    assert spec and spec.loader
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


PUBLICATION = load_script("installation_publication_test", "release-publication.py")
QUALIFICATION = load_script("installation_qualification_test", "installation-qualification.py")


def run(*args: str, expected: int = 0) -> subprocess.CompletedProcess[str]:
    result = subprocess.run([sys.executable, "scripts/tailtrail.py", *args], cwd=ROOT, text=True, capture_output=True, check=False)
    if result.returncode != expected:
        raise AssertionError(f"expected {expected}, got {result.returncode}\nstdout:\n{result.stdout}\nstderr:\n{result.stderr}")
    return result


class InstallationExperienceTests(unittest.TestCase):
    def test_guided_setup_installs_verifies_and_returns_reload_guidance(self) -> None:
        with tempfile.TemporaryDirectory() as temporary:
            payload = json.loads(run("setup", "--host", "copilot", "--profile", "core", "--target", temporary, "--format", "json").stdout)
            self.assertTrue(payload["ok"], payload)
            self.assertEqual(payload["operation"], "setup")
            self.assertEqual(payload["detail_level"], "summary")
            self.assertNotIn("changed", payload)
            self.assertGreater(payload["counts"]["changed"], 0)
            self.assertEqual(payload["diagnostics"]["installation"], "passed")
            self.assertTrue(payload["diagnostics"]["reload"]["required"])

    def test_auto_setup_fails_closed_when_detection_is_ambiguous(self) -> None:
        with tempfile.TemporaryDirectory() as temporary:
            engine = InstallEngine(Path(temporary))
            with mock.patch("tailtrail.install.cli.shutil.which", side_effect=lambda value: f"/bin/{value}" if value in {"codex", "claude"} else None):
                with self.assertRaisesRegex(Exception, "choose --host"):
                    _auto_hosts(engine)
            self.assertEqual(list(Path(temporary).iterdir()), [])

    def test_compact_default_and_verbose_full_plan_are_both_available(self) -> None:
        with tempfile.TemporaryDirectory() as temporary:
            compact = json.loads(run("install", "--host", "claude", "--profile", "core", "--target", temporary, "--dry-run", "--format", "json", "--compact").stdout)
            verbose = json.loads(run("install", "--host", "claude", "--profile", "core", "--target", temporary, "--dry-run", "--format", "json", "--verbose").stdout)
            self.assertEqual(compact["detail_level"], "summary")
            self.assertIn("plan_summary", compact)
            self.assertNotIn("plan", compact)
            self.assertEqual(verbose["detail_level"], "full")
            self.assertTrue(verbose["plan"]["entries"])

    def test_extended_runtime_is_shared_and_reference_safe(self) -> None:
        with tempfile.TemporaryDirectory() as temporary:
            target = Path(temporary)
            for host in HOSTS:
                result = InstallEngine(target).apply("install", host, "extended")
                self.assertTrue(result.ok, result.issues)
            common_root = target / ".tailtrail" / "install" / "payload" / "common"
            versions = [path for path in common_root.iterdir() if path.is_dir()]
            self.assertEqual(len(versions), 1)
            for host in HOSTS:
                launcher = target / ".tailtrail" / "install" / "payload" / host / "scripts" / "tailtrail.py"
                self.assertTrue(launcher.is_file())
                self.assertFalse((launcher.parents[1] / "tailtrail").exists())
            removed = InstallEngine(target).uninstall("codex")
            self.assertTrue(removed.ok, removed.issues)
            self.assertTrue(versions[0].is_dir())
            self.assertTrue(InstallEngine(target).verify("copilot").ok)
            self.assertTrue(InstallEngine(target).verify("claude").ok)

    def test_every_host_contract_has_explicit_reload_and_fallback(self) -> None:
        schema = json.loads((ROOT / "schemas" / "host-adapter-contract.schema.json").read_text(encoding="utf-8"))
        required = schema["properties"]["hosts"]["items"]["required"]
        self.assertIn("reload", required)
        for host in HOSTS:
            reload = contract(host, ROOT)["reload"]
            self.assertTrue(reload["required"])
            self.assertEqual(reload["after"], ["install", "update", "repair", "upgrade"])
            self.assertTrue(reload["instruction"])
            self.assertTrue(reload["fallback"])

    def test_upgrade_validates_a_local_hash_pinned_wheel_without_network(self) -> None:
        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary)
            wheel = root / "tailtrail-9.9.9-py3-none-any.whl"
            with zipfile.ZipFile(wheel, "w") as archive:
                archive.writestr("tailtrail/package-manifest.json", json.dumps({"runtime_required": []}))
                archive.writestr("tailtrail/package-integrity.json", json.dumps({"schema_version": "1", "algorithm": "sha256", "files": {}}))
                archive.writestr("tailtrail/release-manifest.json", json.dumps({"product": {"version": "9.9.9"}}))
            digest = hashlib.sha256(wheel.read_bytes()).hexdigest()
            code, payload = upgrade(["--artifact", wheel.as_posix(), "--sha256", digest, "--target", root.as_posix(), "--dry-run", "--format", "json"])
            self.assertEqual(code, 0, payload)
            self.assertEqual(payload["version"], "9.9.9")
            self.assertEqual(payload["package"], "planned")
            code, payload = upgrade(["--artifact", wheel.as_posix(), "--sha256", "0" * 64, "--target", root.as_posix(), "--dry-run"])
            self.assertEqual(code, 3)
            self.assertIn("mismatch", payload["message"])

    def test_release_discovery_and_publication_workflow_are_explicit(self) -> None:
        payload = json.loads(run("release", "info", "--format", "json").stdout)
        self.assertEqual(payload["repository"], "https://github.com/vishrutsinghal/tailr")
        self.assertIn("gh attestation verify", payload["commands"]["identity"])
        workflow = (ROOT / ".github" / "workflows" / "platform-supply-chain.yml").read_text(encoding="utf-8")
        self.assertIn("release-publication:", workflow)
        self.assertIn("needs: identity-attestation", workflow)
        self.assertIn("gh release create", workflow)
        self.assertIn("release-publication-receipt.json", workflow)

    def test_publication_receipt_is_observed_and_qualification_requires_attestation_verification(self) -> None:
        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary)
            artifact = root / "tailtrail-0.6.0-py3-none-any.whl"
            artifact.write_bytes(b"qualified wheel")
            remote = {"url": "https://github.com/vishrutsinghal/tailr/releases/tag/v0.6.0", "tagName": "v0.6.0", "assets": [{"name": artifact.name}]}
            completed = subprocess.CompletedProcess(["gh"], 0, stdout=json.dumps(remote), stderr="")
            with mock.patch.dict("os.environ", {"GITHUB_RUN_ID": "12345"}), mock.patch.object(PUBLICATION.subprocess, "run", return_value=completed):
                receipt = PUBLICATION.observe("0.6.0", "a" * 40, artifact, root / "receipt.json")
            self.assertTrue(receipt["observed"])
            self.assertEqual(receipt["artifact_sha256"], hashlib.sha256(artifact.read_bytes()).hexdigest())
            with mock.patch.object(QUALIFICATION.shutil, "which", return_value="/usr/bin/gh"), mock.patch.object(QUALIFICATION.subprocess, "run", return_value=subprocess.CompletedProcess(["gh"], 0, stdout="verified", stderr="")):
                self.assertTrue(QUALIFICATION._identity_verified(artifact))
            with mock.patch.object(QUALIFICATION.shutil, "which", return_value=None):
                self.assertFalse(QUALIFICATION._identity_verified(artifact))

    def test_qualification_gate_reports_missing_real_evidence(self) -> None:
        with tempfile.TemporaryDirectory() as temporary:
            payload = json.loads(run("qualify", "report", "--root", temporary, "--format", "json", expected=3).stdout)
            self.assertFalse(payload["supported"])
            self.assertEqual(payload["status"], "evidence-incomplete")
            self.assertEqual(payload["gates"]["instruction_contract"], "passed")
            self.assertEqual(payload["gates"]["real_host_runtime"], "evidence-incomplete")
            self.assertEqual(payload["gates"]["platform_matrix"], "evidence-incomplete")
            self.assertEqual(payload["gates"]["signed_publication"], "evidence-incomplete")


if __name__ == "__main__":
    unittest.main()
