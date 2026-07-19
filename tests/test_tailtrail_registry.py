from __future__ import annotations

import importlib.util
import json
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]


def load_script(name: str, relative: str):
    spec = importlib.util.spec_from_file_location(name, ROOT / relative)
    if spec is None or spec.loader is None:
        raise RuntimeError(f"Unable to load {relative}")
    module = importlib.util.module_from_spec(spec)
    sys.modules[name] = module
    spec.loader.exec_module(module)
    return module


tailtrail_registry = load_script("tailtrail_registry_test", "scripts/tailtrail-registry.py")


class TailTrailRegistryTests(unittest.TestCase):
    def load_registry(self) -> dict:
        return json.loads((ROOT / "tailtrail-registry.json").read_text(encoding="utf-8"))

    def test_registry_schema_file_is_well_formed(self) -> None:
        schema = json.loads((ROOT / "tailtrail-registry.schema.json").read_text(encoding="utf-8"))

        self.assertEqual(schema["$schema"], "https://json-schema.org/draft/2020-12/schema")
        self.assertEqual(schema["properties"]["schema_version"]["const"], "1")
        required = set(schema["properties"]["features"]["items"]["required"])
        self.assertEqual(required, tailtrail_registry.REQUIRED_FEATURE_KEYS)

    def test_registry_foundation_validates_current_file(self) -> None:
        issues = tailtrail_registry.validate_registry(self.load_registry())

        self.assertEqual(issues, [])

    def test_registry_has_unique_ids_and_script_claims(self) -> None:
        registry = self.load_registry()
        features = registry["features"]
        ids = [feature["id"] for feature in features]
        scripts = [script for feature in features for script in feature["scripts"]]

        self.assertEqual(len(ids), len(set(ids)))
        self.assertEqual(len(scripts), len(set(scripts)))

    def test_registry_lists_only_existing_docs_scripts_and_tests(self) -> None:
        for feature in self.load_registry()["features"]:
            for key in ("docs", "scripts", "tests"):
                with self.subTest(feature=feature["id"], key=key):
                    missing = [item for item in feature[key] if not (ROOT / item).is_file()]
                    self.assertEqual(missing, [])

    def test_validator_detects_missing_file(self) -> None:
        registry = self.load_registry()
        registry["features"][0]["scripts"].append("scripts/does-not-exist.py")

        issues = tailtrail_registry.validate_registry(registry)

        self.assertTrue(any("does-not-exist.py" in issue for issue in issues))

    def test_validator_detects_duplicate_script_claim(self) -> None:
        registry = self.load_registry()
        registry["features"][1]["scripts"].append(registry["features"][0]["scripts"][0])

        issues = tailtrail_registry.validate_registry(registry)

        self.assertTrue(any("claimed by both" in issue for issue in issues))

    def test_validator_detects_unknown_dependency(self) -> None:
        registry = self.load_registry()
        registry["features"][0]["depends_on"].append("unknown-feature")

        issues = tailtrail_registry.validate_registry(registry)

        self.assertTrue(any("unknown-feature" in issue for issue in issues))

    def test_validator_detects_unclaimed_tailtrail_command(self) -> None:
        registry = self.load_registry()
        for feature in registry["features"]:
            feature["commands"] = [command for command in feature["commands"] if command != "tailtrail review"]

        issues = tailtrail_registry.validate_registry(registry)

        self.assertTrue(any("command `review` is not claimed" in issue for issue in issues))

    def test_validator_detects_orphan_script(self) -> None:
        registry = self.load_registry()
        for feature in registry["features"]:
            feature["scripts"] = [script for script in feature["scripts"] if script != "scripts/review-run.py"]

        issues = tailtrail_registry.validate_registry(registry)

        self.assertTrue(any("scripts/review-run.py" in issue and "not claimed" in issue for issue in issues))

    def test_validator_requires_tests_for_implemented_features(self) -> None:
        registry = self.load_registry()
        registry["features"][0]["tests"] = []

        issues = tailtrail_registry.validate_registry(registry)

        self.assertTrue(any("implemented feature must list at least one test file" in issue for issue in issues))

    def test_cli_list_show_and_surfaces(self) -> None:
        registry = self.load_registry()

        self.assertGreaterEqual(len(tailtrail_registry.filtered_features(registry, "core", None)), 1)
        self.assertIsNotNone(tailtrail_registry.feature_by_id(registry, "meta-harness"))

    def test_registry_projections_support_later_consumers(self) -> None:
        registry = self.load_registry()
        workflow = tailtrail_registry.workflow_projection(registry, "review")
        mcp = tailtrail_registry.mcp_projection(registry)
        surfaces = tailtrail_registry.registry_surface_entries(registry, "core")

        self.assertIn("review", workflow["feature_ids"])
        self.assertIn("tailtrail review", workflow["commands"])
        self.assertTrue(any(item["tool"] == "navigator_plan" and item["read_only"] for item in mcp))
        self.assertIn("registry", surfaces["features"])
        self.assertIn("scripts/tailtrail-registry.py", surfaces["scripts"])

    def test_cli_can_use_alternate_registry_path_for_validation_helpers(self) -> None:
        with tempfile.TemporaryDirectory() as temp:
            root = Path(temp)
            for relative in ["doc.md", "script.py", "test_file.py"]:
                (root / relative).write_text("", encoding="utf-8")
            registry = {
                "schema_version": "1",
                "features": [
                    {
                        "id": "demo",
                        "title": "Demo",
                        "status": "implemented",
                        "surface": "core",
                        "roadmap_ref": "demo",
                        "owner": "tailtrail-core",
                        "governance_class": "product",
                        "commands": [],
                        "docs": ["doc.md"],
                        "scripts": ["script.py"],
                        "tests": ["test_file.py"],
                        "mcp_tools": [],
                        "requires_approval": False,
                        "read_only": True,
                        "evidence_label": "local-evidence",
                        "depends_on": [],
                        "since_version": "v1",
                        "deprecated_in_version": None,
                    }
                ],
            }

            issues = tailtrail_registry.validate_registry(registry, root)

        self.assertEqual(issues, [])

    def test_installed_pack_validation_does_not_require_test_files_on_disk(self) -> None:
        with tempfile.TemporaryDirectory() as temp:
            root = Path(temp)
            (root / ".tailtrail-install.json").write_text("{}", encoding="utf-8")
            for relative in ["doc.md", "script.py"]:
                (root / relative).write_text("", encoding="utf-8")
            registry = {
                "schema_version": "1",
                "features": [
                    {
                        "id": "demo",
                        "title": "Demo",
                        "status": "implemented",
                        "surface": "core",
                        "roadmap_ref": "demo",
                        "owner": "tailtrail-core",
                        "governance_class": "product",
                        "commands": [],
                        "docs": ["doc.md"],
                        "scripts": ["script.py"],
                        "tests": ["tests/test_demo.py"],
                        "mcp_tools": [],
                        "requires_approval": False,
                        "read_only": True,
                        "evidence_label": "local-evidence",
                        "depends_on": [],
                        "since_version": "v1",
                        "deprecated_in_version": None,
                    }
                ],
            }

            issues = tailtrail_registry.validate_registry(registry, root)

        self.assertEqual(issues, [])

    def test_cli_validate_is_advisory_unless_strict(self) -> None:
        registry = self.load_registry()
        registry["features"][0]["scripts"].append("scripts/does-not-exist.py")
        with tempfile.TemporaryDirectory() as temp:
            registry_path = Path(temp) / "registry.json"
            registry_path.write_text(json.dumps(registry), encoding="utf-8")
            advisory = subprocess.run(
                [
                    sys.executable,
                    (ROOT / "scripts" / "tailtrail-registry.py").as_posix(),
                    "--registry",
                    registry_path.as_posix(),
                    "validate",
                ],
                cwd=ROOT,
                text=True,
                capture_output=True,
                check=False,
            )
            strict = subprocess.run(
                [
                    sys.executable,
                    (ROOT / "scripts" / "tailtrail-registry.py").as_posix(),
                    "--registry",
                    registry_path.as_posix(),
                    "validate",
                    "--strict",
                ],
                cwd=ROOT,
                text=True,
                capture_output=True,
                check=False,
            )

        self.assertEqual(advisory.returncode, 0)
        self.assertIn("Advisory mode", advisory.stdout)
        self.assertEqual(strict.returncode, 1)


if __name__ == "__main__":
    unittest.main()
