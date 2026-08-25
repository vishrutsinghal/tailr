from __future__ import annotations

import copy
import importlib.util
import json
import subprocess
import sys
import unittest
from pathlib import Path
from unittest import mock


ROOT = Path(__file__).resolve().parents[1]


def load_script():
    path = ROOT / "scripts" / "enterprise-readiness.py"
    spec = importlib.util.spec_from_file_location("enterprise_readiness_test", path)
    if spec is None or spec.loader is None:
        raise RuntimeError(f"Unable to load {path}")
    module = importlib.util.module_from_spec(spec)
    sys.modules[spec.name] = module
    spec.loader.exec_module(module)
    return module


enterprise_readiness = load_script()


class EnterpriseReadinessTests(unittest.TestCase):
    def registry(self) -> dict:
        return json.loads((ROOT / "enterprise-closure-registry.json").read_text(encoding="utf-8"))

    def test_schema_and_registry_are_well_formed(self) -> None:
        schema = json.loads((ROOT / "enterprise-closure-registry.schema.json").read_text(encoding="utf-8"))
        registry = self.registry()

        self.assertEqual(schema["$schema"], "https://json-schema.org/draft/2020-12/schema")
        self.assertEqual(schema["properties"]["schema_version"]["const"], "1")
        self.assertEqual(registry["schema_version"], "1")

    def test_current_e0_registry_validates(self) -> None:
        issues = enterprise_readiness.validate_registry(self.registry(), ROOT)

        self.assertEqual(issues, [])

    def test_all_phases_have_owned_requirements_and_e0_is_complete(self) -> None:
        requirements = self.registry()["requirements"]

        self.assertEqual({item["phase"] for item in requirements}, enterprise_readiness.PHASES)
        self.assertTrue(all(item["owner"] for item in requirements))
        self.assertTrue(all(item["status"] == "complete" for item in requirements if item["phase"] == "E0"))

    def test_inventory_projects_every_required_category(self) -> None:
        projection = enterprise_readiness.inventory_projection(ROOT, self.registry())

        self.assertIn("enterprise-readiness", projection["commands"])
        self.assertIn("enterprise-closure-registry.schema.json", projection["schemas"])
        self.assertEqual(set(projection["adapters"]["host_surfaces"]), {"codex", "copilot", "claude"})
        self.assertTrue(projection["persisted_artifacts"])
        self.assertTrue(projection["ci_controls"])
        self.assertTrue({"codex", "codex-plugin", "copilot", "claude"}.issubset(projection["install_surfaces"]["profiles"]))
        self.assertEqual(set(projection["install_surfaces"]["surfaces"]), {"core", "extended"})
        self.assertTrue(projection["release_files"])
        self.assertTrue(projection["support_claims"])
        self.assertTrue(projection["features"])
        self.assertNotIn(None, {item["enterprise_maturity"] for item in projection["features"]})

    def test_release_inventory_reports_manifest_files_as_present(self) -> None:
        inventory = enterprise_readiness.release_file_inventory(ROOT, self.registry())
        states = {item["path"]: item["state"] for item in inventory}

        self.assertEqual(states["README.md"], "present")
        self.assertEqual(states["DEMO.md"], "present")

    def test_validator_rejects_duplicate_requirement_id(self) -> None:
        registry = copy.deepcopy(self.registry())
        registry["requirements"].append(copy.deepcopy(registry["requirements"][0]))

        issues = enterprise_readiness.validate_registry(registry, ROOT)

        self.assertTrue(any("requirement id `ENT-E0-001` is duplicated" in issue for issue in issues))

    def test_validator_rejects_unknown_nested_field(self) -> None:
        registry = copy.deepcopy(self.registry())
        registry["requirements"][0]["future_escape_hatch"] = True

        issues = enterprise_readiness.validate_registry(registry, ROOT)

        self.assertIn("ENT-E0-001 has unexpected key `future_escape_hatch`", issues)

    def test_validator_rejects_duplicate_inventory_category(self) -> None:
        registry = copy.deepcopy(self.registry())
        duplicate = copy.deepcopy(registry["inventory_contracts"][0])
        duplicate["id"] = "another-command-inventory"
        registry["inventory_contracts"].append(duplicate)

        issues = enterprise_readiness.validate_registry(registry, ROOT)

        self.assertIn("inventory category `commands` is duplicated", issues)

    def test_validator_keeps_candidate_blocked_while_defects_are_open(self) -> None:
        registry = copy.deepcopy(self.registry())
        registry["candidate_baseline"]["release_candidate_state"] = "declared"

        issues = enterprise_readiness.validate_registry(registry, ROOT)

        self.assertIn("candidate baseline must remain blocked while known defects are open", issues)

    def test_validator_rejects_baseline_commit_or_branch_drift(self) -> None:
        registry = copy.deepcopy(self.registry())
        registry["candidate_baseline"]["git_commit"] = "0" * 40
        registry["candidate_baseline"]["branch"] = "not-the-current-branch"

        issues = enterprise_readiness.validate_registry(registry, ROOT)

        self.assertTrue(any("does not match HEAD" in issue for issue in issues))
        self.assertTrue(any("does not match current branch" in issue for issue in issues))

    def test_validator_rejects_missing_owner_and_validation(self) -> None:
        registry = copy.deepcopy(self.registry())
        registry["requirements"][0]["owner"] = ""
        registry["requirements"][0]["validation"] = []

        issues = enterprise_readiness.validate_registry(registry, ROOT)

        self.assertTrue(any("ENT-E0-001 owner" in issue for issue in issues))
        self.assertTrue(any("ENT-E0-001 validation" in issue for issue in issues))

    def test_validator_rejects_unknown_and_later_phase_dependencies(self) -> None:
        registry = copy.deepcopy(self.registry())
        registry["requirements"][0]["dependencies"] = ["ENT-E12-002", "ENT-E9-999"]

        issues = enterprise_readiness.validate_registry(registry, ROOT)

        self.assertTrue(any("depends on later-phase requirement `ENT-E12-002`" in issue for issue in issues))
        self.assertTrue(any("depends on unknown requirement `ENT-E9-999`" in issue for issue in issues))

    def test_validator_rejects_complete_requirement_without_evidence(self) -> None:
        registry = copy.deepcopy(self.registry())
        registry["requirements"][0]["evidence"] = []

        issues = enterprise_readiness.validate_registry(registry, ROOT)

        self.assertTrue(any("complete requirement must record evidence" in issue for issue in issues))

    def test_validator_rejects_unknown_maturity_and_missing_phase(self) -> None:
        registry = copy.deepcopy(self.registry())
        registry["maturity_mapping"]["implemented"] = "unknown"
        registry["requirements"] = [item for item in registry["requirements"] if item["phase"] != "E12"]
        registry["requirements"][-1]["dependencies"] = []

        issues = enterprise_readiness.validate_registry(registry, ROOT)

        self.assertTrue(any("invalid value `unknown`" in issue for issue in issues))
        self.assertTrue(any("requirements must cover every phase" in issue for issue in issues))

    def test_validator_rejects_unclassified_untracked_path(self) -> None:
        with mock.patch.object(enterprise_readiness, "untracked_paths", return_value=["unclassified.tmp"]):
            issues = enterprise_readiness.validate_registry(self.registry(), ROOT)

        self.assertIn("untracked path `unclassified.tmp` has no candidate disposition", issues)

    def test_cli_validate_status_and_inventory(self) -> None:
        commands = [
            ["validate", "--format", "json"],
            ["status", "--format", "json"],
            ["inventory", "--format", "json"],
        ]
        for arguments in commands:
            with self.subTest(arguments=arguments):
                result = subprocess.run(
                    [sys.executable, (ROOT / "scripts" / "enterprise-readiness.py").as_posix(), *arguments],
                    cwd=ROOT,
                    text=True,
                    capture_output=True,
                    check=False,
                )
                self.assertEqual(result.returncode, 0, result.stdout + result.stderr)
                self.assertIsInstance(json.loads(result.stdout), dict)

    def test_top_level_cli_dispatches_enterprise_readiness(self) -> None:
        result = subprocess.run(
            [sys.executable, (ROOT / "scripts" / "tailtrail.py").as_posix(), "enterprise-readiness", "status"],
            cwd=ROOT,
            text=True,
            capture_output=True,
            check=False,
        )

        self.assertEqual(result.returncode, 0, result.stdout + result.stderr)
        self.assertIn("E0 exit gate: **passed**", result.stdout)
        registry = json.loads((ROOT / "enterprise-closure-registry.json").read_text(encoding="utf-8"))
        phase = registry["program"]["current_phase"]
        phase_requirements = [item for item in registry["requirements"] if item["phase"] == phase]
        expected = "passed" if phase_requirements and all(item["status"] == "complete" for item in phase_requirements) else "blocked"
        self.assertIn(f"{phase} exit gate: **{expected}**", result.stdout)


if __name__ == "__main__":
    unittest.main()
