from __future__ import annotations

import copy
import hashlib
import importlib.util
import json
import subprocess
import sys
import unittest
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
if (ROOT / "scripts").as_posix() not in sys.path:
    sys.path.insert(0, (ROOT / "scripts").as_posix())
SCENARIO = ROOT / "benchmarks" / "evaluation" / "navigator-scope" / "installed-release-v1.json"
SCHEMA = ROOT / "schemas" / "navigator-installed-release-proof.schema.json"


def load(name: str, relative: str):
    spec = importlib.util.spec_from_file_location(name, ROOT / relative)
    assert spec and spec.loader
    module = importlib.util.module_from_spec(spec)
    sys.modules[spec.name] = module
    spec.loader.exec_module(module)
    return module


PROOF = load("fsr7_installed_release_test", "scripts/navigator-installed-release-proof.py")
CONTRACTS = load("fsr7_contracts_test", "scripts/workflow_runtime/contracts.py")


class NavigatorInstalledReleaseTests(unittest.TestCase):
    def test_scenario_is_closed_integrity_sealed_and_privacy_bounded(self) -> None:
        scenario = json.loads(SCENARIO.read_text(encoding="utf-8"))
        PROOF.validate_scenario(scenario)
        material = {key: value for key, value in scenario.items() if key != "integrity"}
        digest = hashlib.sha256(json.dumps(material, sort_keys=True, separators=(",", ":")).encode()).hexdigest()
        self.assertEqual(digest, scenario["integrity"]["digest"])
        self.assertEqual("synthetic", scenario["privacy"]["fixture"])
        self.assertFalse(scenario["privacy"]["external_fixture_retained"])
        self.assertFalse(scenario["privacy"]["hosted_agent_claim"])

        tampered = copy.deepcopy(scenario)
        tampered["expected"]["implementation_owners"] = ["src/pages/account/AccountPage.tsx"]
        with self.assertRaisesRegex(PROOF.InstalledReleaseProofError, "integrity digest"):
            PROOF.validate_scenario(tampered)

        catalog = json.loads((ROOT / scenario["source_catalog"]).read_text(encoding="utf-8"))
        source = next(
            row for row in catalog["scenarios"]
            if row["id"] == scenario["source_scenario_id"]
        )
        self.assertIn(
            "*Telemetry trace endpoint is not configured.*",
            source["goal"],
        )

    def test_report_schema_is_closed_and_requires_separate_integrity_and_behavior(self) -> None:
        schema = json.loads(SCHEMA.read_text(encoding="utf-8"))
        self.assertFalse(schema["additionalProperties"])
        self.assertIn("installation_integrity", schema["required"])
        self.assertIn("behavioral_proof", schema["required"])
        invalid = {
            "schema_version": "1",
            "type": "tailtrail-navigator-installed-release-proof",
            "status": "passed",
        }
        issues = CONTRACTS.validate_document(invalid, schema)
        self.assertTrue(issues)

    def test_cli_route_fails_closed_before_install_for_missing_artifacts(self) -> None:
        command = [
            sys.executable,
            str(ROOT / "scripts" / "tailtrail.py"),
            "eval",
            "scope",
            "installed-release-proof",
            "--wheel",
            "missing.whl",
            "--sdist",
            "missing.tar.gz",
        ]
        result = subprocess.run(command, cwd=ROOT, text=True, capture_output=True, check=False)
        payload = json.loads(result.stdout)
        self.assertEqual(2, result.returncode)
        self.assertEqual("failed", payload["status"])
        self.assertEqual("tailtrail-navigator-installed-release-proof-error", payload["type"])

    def test_release_and_package_manifests_own_fsr7_artifacts(self) -> None:
        package = json.loads((ROOT / "package-manifest.json").read_text(encoding="utf-8"))
        release = json.loads((ROOT / "release-manifest.json").read_text(encoding="utf-8"))
        required = {
            "scripts/navigator-installed-release-proof.py",
            "schemas/navigator-installed-release-proof.schema.json",
            "benchmarks/evaluation/navigator-scope/installed-release-v1.json",
        }
        package_inventory = set(package["required_files"]) | set(package["runtime_required"])
        release_inventory = set(release["candidate_additions"]) | set(release["required_release_files"])
        self.assertLessEqual(required, package_inventory)
        self.assertLessEqual(required, release_inventory)


if __name__ == "__main__":
    unittest.main()
