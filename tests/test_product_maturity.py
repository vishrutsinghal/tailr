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
    path = ROOT / "scripts" / "product-maturity.py"
    spec = importlib.util.spec_from_file_location("product_maturity_test", path)
    if spec is None or spec.loader is None:
        raise RuntimeError(f"Unable to load {path}")
    module = importlib.util.module_from_spec(spec)
    sys.modules[spec.name] = module
    spec.loader.exec_module(module)
    return module


product_maturity = load_script()


class ProductMaturityTests(unittest.TestCase):
    def run_cli(self, *args: str) -> subprocess.CompletedProcess[str]:
        return subprocess.run(
            [sys.executable, (ROOT / "scripts" / "tailtrail.py").as_posix(), "maturity", *args],
            cwd=ROOT,
            text=True,
            capture_output=True,
            check=False,
        )

    def test_baseline_is_versioned_sealed_and_complete(self) -> None:
        baseline = json.loads((ROOT / "tailtrail-meta" / "product-maturity-baseline-v1.json").read_text(encoding="utf-8"))

        self.assertEqual(baseline["baseline_version"], "1.0.0")
        self.assertEqual(baseline["program_phase"], "PM-0")
        self.assertEqual(baseline["integrity"]["digest"], product_maturity.seal_payload(baseline))
        self.assertGreaterEqual(len(baseline["usability_scenarios"]), 6)
        self.assertTrue(all(item["current"] < 8 for item in baseline["ratings"]))

    def test_current_baseline_passes_freeze_and_ownership_validation(self) -> None:
        result = product_maturity.validate(ROOT)

        self.assertEqual(result["status"], "passed", result["issues"])
        self.assertEqual(result["feature_freeze"], "passed")
        self.assertEqual(result["ownership"], "passed")

    def test_unapproved_public_command_is_freeze_drift(self) -> None:
        original = product_maturity.discover_commands
        with mock.patch.object(product_maturity, "discover_commands", side_effect=lambda root: [*original(root), "new-top-level-feature"]):
            result = product_maturity.validate(ROOT)

        self.assertEqual(result["status"], "failed")
        self.assertTrue(any("new-top-level-feature" in issue for issue in result["issues"]))

    def test_approved_addition_requires_owner_and_reason(self) -> None:
        policy = json.loads((ROOT / "tailtrail-meta" / "product-maturity-policy-v1.json").read_text(encoding="utf-8"))
        broken = copy.deepcopy(policy)
        broken["freeze"]["approved_additions"]["mcp_tools"] = [{"id": "new_tool"}]

        issues = product_maturity.validate_policy(broken)

        self.assertTrue(any("approved addition" in issue for issue in issues))

    def test_duplicate_ownership_domain_is_rejected(self) -> None:
        inventory = product_maturity.build_inventory(ROOT)
        inventory["ownership"].append(copy.deepcopy(inventory["ownership"][0]))

        issues = product_maturity.validate_ownership(inventory)

        self.assertTrue(any("ambiguous" in issue for issue in issues))

    def test_pm1_owner_matrix_covers_every_mutating_domain(self) -> None:
        inventory = product_maturity.build_inventory(ROOT)
        owners = {item["domain"]: item for item in inventory["ownership"]}

        self.assertTrue(product_maturity.REQUIRED_OWNERSHIP_DOMAINS <= owners.keys())
        self.assertTrue(all(item["transition_authority"] == "Durable Workflow Runtime" for item in owners.values()))

    def test_scenarios_cover_quick_guided_expert_and_verbose(self) -> None:
        fixture = json.loads((ROOT / "benchmarks" / "product-maturity" / "pm0-scenarios-v1.json").read_text(encoding="utf-8"))
        levels = {item["level"] for item in fixture["scenarios"]}
        ids = {item["id"] for item in fixture["scenarios"]}

        self.assertTrue({"quick", "guided", "expert", "all"}.issubset(levels))
        self.assertIn("verbose-completeness", ids)
        self.assertEqual(product_maturity.validate_scenarios(fixture), [])

    def test_public_cli_baseline_inventory_validate_and_status(self) -> None:
        for command in ("baseline", "inventory", "validate", "status"):
            with self.subTest(command=command):
                result = self.run_cli(command, "--format", "json")
                self.assertEqual(result.returncode, 0, result.stdout + result.stderr)
                self.assertIsInstance(json.loads(result.stdout), dict)

    def test_write_requires_explicit_approval(self) -> None:
        result = self.run_cli("baseline", "--write")

        self.assertNotEqual(result.returncode, 0)
        self.assertIn("--write requires --approved", result.stderr)


if __name__ == "__main__":
    unittest.main()
