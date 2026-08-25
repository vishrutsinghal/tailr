from __future__ import annotations

import importlib.util
import json
import tempfile
import unittest
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]


def load_script(name: str, filename: str):
    spec = importlib.util.spec_from_file_location(name, ROOT / "scripts" / filename)
    module = importlib.util.module_from_spec(spec)
    assert spec and spec.loader
    spec.loader.exec_module(module)
    return module


SUPPLY = load_script("tailtrail_supply_chain_test", "supply-chain.py")
PLATFORM = load_script("tailtrail_platform_qualification_test", "platform-qualification.py")


class CrossPlatformSupplyChainTests(unittest.TestCase):
    def test_contract_is_exact_and_claims_require_observation(self) -> None:
        contract = json.loads((ROOT / "platform-release-contract.json").read_text(encoding="utf-8"))
        self.assertEqual(contract["supported_operating_systems"], ["linux", "macos", "windows"])
        self.assertEqual(contract["supported_python_versions"], ["3.12", "3.13"])
        self.assertEqual(contract["artifact_routes"], ["wheel", "sdist-to-wheel"])
        self.assertEqual(contract["host_profiles"], ["codex:core", "copilot:core", "claude:core"])
        self.assertFalse(contract["evidence_policy"]["configured_is_observed"])
        self.assertFalse(contract["evidence_policy"]["simulated_is_observed"])
        self.assertTrue(contract["evidence_policy"]["release_requires_identity_attestation"])

    def test_build_dependency_decision_is_exact_and_runtime_remains_empty(self) -> None:
        lock = json.loads((ROOT / "release-build-lock.json").read_text(encoding="utf-8"))
        self.assertEqual([(item["name"], item["version"]) for item in lock["dependencies"]], [("setuptools", "84.0.0"), ("wheel", "0.48.0"), ("packaging", "26.3")])
        pyproject = (ROOT / "pyproject.toml").read_text(encoding="utf-8")
        self.assertIn('requires = ["setuptools==84.0.0", "wheel==0.48.0", "packaging==26.3"]', pyproject)
        self.assertIn("dependencies = []", pyproject)

    def test_supply_chain_bundle_round_trip_and_tamper_fail_closed(self) -> None:
        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary)
            wheel = root / "tailtrail-0.6.0-py3-none-any.whl"
            sdist = root / "tailtrail-0.6.0.tar.gz"
            wheel.write_bytes(b"wheel bytes")
            sdist.write_bytes(b"sdist bytes")
            bundle = root / "evidence"
            commit = "1" * 40
            evidence = SUPPLY.create_bundle([wheel, sdist], bundle, "https://github.com/example/tailtrail", commit, 1704067200, verify_environment=False, verify_source=False)
            self.assertEqual(evidence["attestation"], "required-on-tag")
            self.assertEqual(SUPPLY.verify_bundle([wheel, sdist], bundle), [])
            self.assertEqual(SUPPLY.verify_bundle([wheel, sdist], bundle, require_attestation=True), ["identity-backed release attestation is required"])
            wheel.write_bytes(b"tampered")
            issues = SUPPLY.verify_bundle([wheel, sdist], bundle)
            self.assertTrue(any("digest or size mismatch" in issue for issue in issues), issues)

    def test_supply_chain_refuses_unlocked_build_environment(self) -> None:
        lock = {"dependencies": [{"name": "definitely-not-installed-tailtrail-fixture", "version": "1.0.0"}]}
        with self.assertRaisesRegex(ValueError, "does not match lock"):
            SUPPLY.verify_build_environment(lock)

    def _receipt(self, system: str, python: str, commit: str, wheel_hash: str, sdist_hash: str) -> dict[str, object]:
        checks: dict[str, str] = {"permission-model": "not-applicable" if system == "windows" else "pass", "symlink-boundary": "pass"}
        for route in ("wheel", "sdist-to-wheel"):
            checks[f"{route}:artifact-install"] = "pass"
            checks[f"{route}:console-launcher"] = "pass"
            for host in ("codex", "copilot", "claude"):
                for operation in ("install", "verify", "update", "rollback", "uninstall"):
                    checks[f"{route}:{host}:{operation}"] = "pass"
        return {
            "schema_version": "1", "type": "tailtrail-platform-qualification-receipt", "observed": True,
            "runner": {"os": system, "system": system, "release": "test", "machine": "test", "ci": True},
            "python": python, "source_commit": commit,
            "artifacts": {"wheel": {"filename": "wheel.whl", "sha256": wheel_hash}, "sdist_to_wheel": {"filename": "sdist.whl", "sha256": sdist_hash}},
            "checks": checks, "valid": True,
        }

    def test_matrix_report_requires_exact_six_hosted_receipts(self) -> None:
        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary)
            receipts = root / "receipts"
            receipts.mkdir()
            wheel = root / "wheel.whl"
            sdist_wheel = root / "sdist.whl"
            wheel.write_bytes(b"wheel")
            sdist_wheel.write_bytes(b"sdist wheel")
            commit = "2" * 40
            for system in ("linux", "macos", "windows"):
                for python in ("3.12", "3.13"):
                    payload = self._receipt(system, python, commit, PLATFORM.digest(wheel), PLATFORM.digest(sdist_wheel))
                    (receipts / f"{system}-{python}.json").write_text(json.dumps(payload), encoding="utf-8")
            report = PLATFORM.report(receipts, ROOT / "platform-release-contract.json", commit, wheel, sdist_wheel)
            self.assertTrue(report["valid"], report["issues"])
            (receipts / "windows-3.13.json").unlink()
            report = PLATFORM.report(receipts, ROOT / "platform-release-contract.json", commit, wheel, sdist_wheel)
            self.assertFalse(report["valid"])
            self.assertTrue(any("matrix coverage mismatch" in issue for issue in report["issues"]))

    def test_workflow_pins_actions_and_attests_only_after_matrix_gate(self) -> None:
        workflow = (ROOT / ".github" / "workflows" / "platform-supply-chain.yml").read_text(encoding="utf-8")
        self.assertNotIn("actions/checkout@v", workflow)
        self.assertNotIn("actions/setup-python@v", workflow)
        self.assertIn("os: [ubuntu-latest, macos-latest, windows-latest]", workflow)
        self.assertIn('python-version: ["3.12", "3.13"]', workflow)
        self.assertIn("needs: qualification-gate", workflow)
        self.assertIn("id-token: write", workflow)
        self.assertIn("attestations: write", workflow)
        self.assertIn("actions/attest@1e69f48acb82d1966a394da916b4c1698aa569d6", workflow)


if __name__ == "__main__":
    unittest.main()
