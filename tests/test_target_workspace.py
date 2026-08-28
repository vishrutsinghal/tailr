from __future__ import annotations

import subprocess
import sys
import tempfile
import unittest
import json
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, (ROOT / "scripts").as_posix())

import target_workspace


class TargetWorkspaceTests(unittest.TestCase):
    def test_explicit_root_has_priority_over_prompt_path(self) -> None:
        with tempfile.TemporaryDirectory() as temp:
            result = target_workspace.resolve("changes must be made in /not-the-target", explicit_root=Path(temp))
        self.assertEqual(result["status"], "verified")
        self.assertEqual(result["source"], "--root")

    def test_host_workspace_has_priority_over_prompt_path(self) -> None:
        with tempfile.TemporaryDirectory() as temp:
            result = target_workspace.resolve("changes must be made in /not-the-target", host_workspace=Path(temp))
        self.assertEqual(result["status"], "verified")
        self.assertEqual(result["source"], "host-workspace")

    def test_inaccessible_prompt_target_fails_closed(self) -> None:
        result = target_workspace.resolve("changes has to be made in this repo /Users/example/missing-project")
        self.assertEqual(result["status"], "inaccessible")
        self.assertEqual(result["source"], "goal")
        self.assertEqual(result["requested"], "/Users/example/missing-project")

    def test_registered_alias_resolves_and_unknown_alias_is_unmapped(self) -> None:
        with tempfile.TemporaryDirectory() as temp:
            resolved = target_workspace.resolve("add UI", alias="frontend", aliases={"frontend": Path(temp)})
        unknown = target_workspace.resolve("add UI", alias="frontend", aliases={})
        self.assertEqual(resolved["status"], "verified")
        self.assertEqual(resolved["source"], "alias")
        self.assertEqual(unknown["status"], "unmapped")

    def test_cli_returns_json_and_nonzero_for_an_inaccessible_target(self) -> None:
        result = subprocess.run(
            [sys.executable, (ROOT / "scripts" / "tailtrail.py").as_posix(), "target", "resolve", "changes must be made in /missing/project", "--format", "json"],
            cwd=ROOT,
            text=True,
            capture_output=True,
            check=False,
        )
        self.assertEqual(result.returncode, 2)
        self.assertIn('"status": "inaccessible"', result.stdout)

    def test_implicit_workspace_requires_confirmation_when_only_test_matches_exist(self) -> None:
        with tempfile.TemporaryDirectory() as temp:
            root = Path(temp)
            fit = target_workspace.assess_plan_fit(
                "add delivery-address validation across the API and order service",
                root,
                [{"path": "tests/test_validation.py", "reason": "goal-matched target"}],
                resolution_source="host-cwd",
            )
        self.assertTrue(fit["blocking"])
        self.assertEqual(fit["status"], "needs-confirmation")
        self.assertEqual(fit["production_candidates"], [])

    def test_implicit_workspace_is_accepted_when_production_scope_is_found(self) -> None:
        with tempfile.TemporaryDirectory() as temp:
            root = Path(temp)
            fit = target_workspace.assess_plan_fit(
                "add delivery-address validation across the API and order service",
                root,
                [
                    {"path": "src/order_service/service.py", "reason": "architecture role candidate"},
                    {"path": "tests/test_validation.py", "reason": "goal-matched target"},
                ],
                resolution_source="host-cwd",
            )
        self.assertFalse(fit["blocking"])
        self.assertEqual(fit["production_candidates"], ["src/order_service/service.py"])

    def test_implicit_documentation_only_request_does_not_require_production_scope(self) -> None:
        with tempfile.TemporaryDirectory() as temp:
            fit = target_workspace.assess_plan_fit(
                "fix a typo in README",
                Path(temp),
                [{"path": "README.md", "reason": "goal-matched target"}],
                resolution_source="host-cwd",
            )
        self.assertFalse(fit["blocking"])

    def test_input_roles_keep_references_read_only_and_redact_external_locator(self) -> None:
        with tempfile.TemporaryDirectory() as temp:
            root = Path(temp) / "target"
            reference = Path(temp) / "reference"
            root.mkdir()
            reference.mkdir()
            (reference / "pyproject.toml").write_text("[project]\nname = 'reference'\n", encoding="utf-8")
            registry = target_workspace.input_roles(
                root,
                reference_roots=[reference.as_posix()],
                design_references=["https://www.figma.com/file/private-design-token?secret=never-store"],
            )
            checked = target_workspace.validate_input_roles(registry, root)
            summary = target_workspace.reference_summary(registry)
        self.assertEqual(checked["status"], "matched")
        self.assertEqual(registry["inputs"][0]["access"], "read-write-after-approval")
        self.assertEqual(registry["inputs"][1]["access"], "read-only")
        self.assertNotIn("private-design-token", registry["inputs"][2]["locator"])
        self.assertEqual(summary[0]["project"]["manifests"], ["pyproject.toml"])

    def test_reference_repository_cannot_overlap_editable_target(self) -> None:
        with tempfile.TemporaryDirectory() as temp:
            root = Path(temp)
            with self.assertRaisesRegex(ValueError, "overlaps the editable target"):
                target_workspace.input_roles(root, reference_roots=[root.as_posix()])

    def test_roles_cli_returns_bounded_read_only_summary(self) -> None:
        with tempfile.TemporaryDirectory() as temp:
            root = Path(temp) / "target"
            reference = Path(temp) / "reference"
            root.mkdir()
            reference.mkdir()
            (reference / "package.json").write_text("{}\n", encoding="utf-8")
            result = subprocess.run(
                [sys.executable, (ROOT / "scripts" / "tailtrail.py").as_posix(), "target", "roles", "--root", root.as_posix(), "--reference-root", reference.as_posix(), "--summary", "--format", "json"],
                cwd=ROOT,
                text=True,
                capture_output=True,
                check=False,
            )
        self.assertEqual(result.returncode, 0, result.stderr)
        payload = json.loads(result.stdout)
        self.assertEqual(payload["inputs"][1]["access"], "read-only")
        self.assertEqual(payload["reference_summary"][0]["project"]["manifests"], ["package.json"])


if __name__ == "__main__":
    unittest.main()
