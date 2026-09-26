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
    def test_identity_ignores_manifest_owned_installed_pack_inventory(self) -> None:
        with tempfile.TemporaryDirectory() as temp:
            root = Path(temp)
            app = root / "src" / "service.py"
            app.parent.mkdir()
            app.write_text("value = 1\n", encoding="utf-8")
            pack = root / "tailtrail"
            (pack / "scripts").mkdir(parents=True)
            (pack / ".tailtrail-install.json").write_text("{}\n", encoding="utf-8")
            (pack / "scripts" / "runtime.py").write_text("old = True\n", encoding="utf-8")
            before = target_workspace.identity(root)
            (pack / "scripts" / "runtime.py").write_text("new = True\n", encoding="utf-8")
            (pack / "scripts" / "added.py").write_text("added = True\n", encoding="utf-8")
            after = target_workspace.identity(root)
        self.assertEqual(before["fingerprint"], after["fingerprint"])
        self.assertEqual(1, after["project"]["inventory_count"])

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

    def test_implicit_workspace_identity_does_not_treat_test_matches_as_scope_evidence(self) -> None:
        with tempfile.TemporaryDirectory() as temp:
            root = Path(temp)
            fit = target_workspace.assess_plan_fit(
                "add delivery-address validation across the API and order service",
                root,
                [{"path": "tests/test_validation.py", "reason": "goal-matched target"}],
                resolution_source="host-cwd",
            )
        self.assertFalse(fit["blocking"])
        self.assertEqual(fit["status"], "verified")
        self.assertEqual(fit["production_candidates"], [])
        self.assertEqual(fit["discovered_candidates"], ["tests/test_validation.py"])

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
        self.assertEqual(fit["production_candidates"], [])
        self.assertEqual(
            fit["discovered_candidates"],
            ["src/order_service/service.py", "tests/test_validation.py"],
        )

    def test_explicit_missing_changed_path_blocks_before_planning_lock(self) -> None:
        with tempfile.TemporaryDirectory() as temp:
            root = Path(temp)
            fit = target_workspace.assess_plan_fit(
                "add delivery-address validation", root,
                [{"path": "src/order_service/validation.py", "reason": "user-provided target"}],
                resolution_source="host-cwd", changed=["src/order_service/validation.py"],
            )
        self.assertTrue(fit["blocking"])
        self.assertEqual(fit["status"], "changed-path-missing")
        self.assertEqual(fit["missing_changed_paths"], ["src/order_service/validation.py"])

    def test_explicit_existing_changed_path_is_accepted(self) -> None:
        with tempfile.TemporaryDirectory() as temp:
            root = Path(temp); target = root / "src" / "service.py"
            target.parent.mkdir(); target.write_text("value = 1\n", encoding="utf-8")
            fit = target_workspace.assess_plan_fit(
                "fix service validation", root,
                [{"path": "src/service.py", "reason": "user-provided target"}],
                resolution_source="host-cwd", changed=["src/service.py"],
            )
        self.assertFalse(fit["blocking"])
        self.assertEqual(fit["existing_changed_paths"], ["src/service.py"])

    def test_explicit_greenfield_changed_path_in_existing_directory_is_accepted(self) -> None:
        with tempfile.TemporaryDirectory() as temp:
            root = Path(temp)
            (root / "tf").mkdir()
            (root / "tf" / "data.tf").write_text("data \"aws_ssm_parameter\" \"x\" {}\n", encoding="utf-8")
            fit = target_workspace.assess_plan_fit(
                "create a new secret in tf/secrets.tf following tf/data.tf", root,
                [{"path": "tf/data.tf", "reason": "cited pattern file"}],
                resolution_source="host-cwd", changed=["tf/secrets.tf"],
            )
        self.assertFalse(fit["blocking"])
        self.assertEqual(fit["status"], "verified")
        self.assertEqual(fit["greenfield_changed_paths"], ["tf/secrets.tf"])

    def test_explicit_greenfield_changed_path_in_missing_directory_still_blocks(self) -> None:
        with tempfile.TemporaryDirectory() as temp:
            root = Path(temp)
            fit = target_workspace.assess_plan_fit(
                "create a new secret", root,
                [{"path": "tf/secrets.tf", "reason": "user-provided target"}],
                resolution_source="host-cwd", changed=["tf/secrets.tf"],
            )
        self.assertTrue(fit["blocking"])
        self.assertEqual(fit["status"], "changed-path-missing")
        self.assertEqual(fit["missing_changed_paths"], ["tf/secrets.tf"])

    def test_explicit_greenfield_changed_path_with_non_source_role_still_blocks(self) -> None:
        with tempfile.TemporaryDirectory() as temp:
            root = Path(temp)
            (root / "docs").mkdir()
            fit = target_workspace.assess_plan_fit(
                "add a new doc", root,
                [{"path": "docs/existing.md", "reason": "user-provided target"}],
                resolution_source="host-cwd", changed=["docs/new-guide.md"],
            )
        self.assertTrue(fit["blocking"])
        self.assertEqual(fit["status"], "changed-path-missing")
        self.assertEqual(fit["missing_changed_paths"], ["docs/new-guide.md"])

    def test_start_missing_changed_path_creates_no_planning_lock(self) -> None:
        with tempfile.TemporaryDirectory() as temp:
            root = Path(temp)
            result = subprocess.run([
                sys.executable, (ROOT / "scripts" / "task-start.py").as_posix(),
                "add delivery-address validation", "--root", root.as_posix(),
                "--changed", "src/order_service/validation.py", "--verbose",
            ], cwd=ROOT, text=True, capture_output=True, check=False)
            run_state_exists = (root / ".tailtrail" / "runs").exists()

        self.assertEqual(result.returncode, 2, result.stdout + result.stderr)
        self.assertIn("# TailTrail Pre-Target Start Plan", result.stdout)
        self.assertIn("## Invalid explicit paths", result.stdout)
        self.assertIn("src/order_service/validation.py", result.stdout)
        self.assertIn("local AIDLC Lite remains", result.stdout)
        self.assertNotIn("official Full AIDLC requirements stage", result.stdout)
        self.assertFalse(run_state_exists)

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

    def test_requirement_artifact_becomes_hash_bound_planning_input(self) -> None:
        with tempfile.TemporaryDirectory() as temp:
            root = Path(temp) / "target"
            artifact = Path(temp) / "requirements.md"
            root.mkdir()
            artifact.write_text("# Requirements\n\nAdd four table scenarios.\n", encoding="utf-8")
            registry = target_workspace.input_roles(
                root, requirement_artifacts=[artifact.as_posix()]
            )
            prepared = target_workspace.inspect_requirement_artifacts(registry)

        self.assertTrue(prepared["ready"])
        receipt = prepared["registry"]["inputs"][1]
        self.assertEqual(receipt["status"], "inspected")
        self.assertEqual(len(receipt["sha256"]), 64)
        self.assertNotIn("content", receipt)
        self.assertEqual(
            prepared["planning_inputs"][0]["content"],
            "# Requirements\n\nAdd four table scenarios.\n",
        )

    def test_required_artifact_fails_closed_when_missing_or_truncated(self) -> None:
        with tempfile.TemporaryDirectory() as temp:
            root = Path(temp) / "target"
            root.mkdir()
            missing = target_workspace.inspect_requirement_artifacts(
                target_workspace.input_roles(
                    root, requirement_artifacts=[(Path(temp) / "missing.md").as_posix()]
                )
            )
            large = Path(temp) / "large.md"
            large.write_text("requirement\n" * 10, encoding="utf-8")
            truncated = target_workspace.inspect_requirement_artifacts(
                target_workspace.input_roles(root, requirement_artifacts=[large.as_posix()]),
                max_bytes=8,
            )

        self.assertFalse(missing["ready"])
        self.assertEqual(missing["blocking"][0]["status"], "unavailable")
        self.assertFalse(truncated["ready"])
        self.assertEqual(truncated["blocking"][0]["status"], "truncated")

    def test_start_inspects_required_artifact_before_host_interpretation_or_scope(self) -> None:
        with tempfile.TemporaryDirectory() as temp:
            root = Path(temp) / "target"
            root.mkdir()
            artifact = Path(temp) / "requirements.md"
            artifact.write_text("Add pipeline table scenarios.\n", encoding="utf-8")
            completed = subprocess.run(
                [
                    sys.executable,
                    (ROOT / "scripts" / "task-start.py").as_posix(),
                    "Add tests from the requirement artifact.",
                    "--root", root.as_posix(),
                    "--host", "codex",
                    "--requirement-artifact", artifact.as_posix(),
                    "--format", "json",
                ],
                cwd=ROOT,
                text=True,
                capture_output=True,
                check=False,
            )
            run_state_exists = (root / ".tailtrail" / "runs").exists()

        self.assertEqual(completed.returncode, 2, completed.stderr)
        report = json.loads(completed.stdout)
        self.assertEqual(report["status"], "awaiting-host-interpretation")
        self.assertEqual(report["requirement_artifacts"][0]["status"], "inspected")
        self.assertEqual(len(report["requirement_artifacts"][0]["sha256"]), 64)
        self.assertIsNone(report["planning_lock"])
        self.assertFalse(run_state_exists)

    def test_start_blocks_unavailable_required_artifact_before_scope(self) -> None:
        with tempfile.TemporaryDirectory() as temp:
            root = Path(temp) / "target"
            root.mkdir()
            completed = subprocess.run(
                [
                    sys.executable,
                    (ROOT / "scripts" / "task-start.py").as_posix(),
                    "Add tests from the requirement artifact.",
                    "--root", root.as_posix(),
                    "--host", "codex",
                    "--requirement-artifact", (Path(temp) / "missing.md").as_posix(),
                    "--format", "json",
                ],
                cwd=ROOT,
                text=True,
                capture_output=True,
                check=False,
            )
            run_state_exists = (root / ".tailtrail" / "runs").exists()

        self.assertEqual(completed.returncode, 2, completed.stderr)
        report = json.loads(completed.stdout)
        self.assertEqual(report["status"], "required-planning-input-unavailable")
        self.assertIsNone(report["planning_lock"])
        self.assertFalse(run_state_exists)

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

    def test_added_source_file_reports_inventory_drift_without_blocking(self) -> None:
        with tempfile.TemporaryDirectory() as temp:
            root = Path(temp)
            saved = target_workspace.identity(root)
            (root / "new-module.py").write_text("VALUE = 1\n", encoding="utf-8")
            result = target_workspace.verify_identity(saved, root)
        self.assertEqual(result["status"], "inventory-drift")
        self.assertFalse(result["blocking"])
        self.assertEqual(result["inventory_drift"]["added"], ["new-module.py"])
        self.assertFalse(result["inventory_drift"]["in_sync"])

    def test_removed_and_modified_files_are_named_in_drift(self) -> None:
        with tempfile.TemporaryDirectory() as temp:
            root = Path(temp)
            (root / "gone.py").write_text("GONE = 1\n", encoding="utf-8")
            (root / "keep.py").write_text("KEEP = 1\n", encoding="utf-8")
            saved = target_workspace.identity(root)
            (root / "gone.py").unlink()
            (root / "keep.py").write_text("KEEP = 2\n", encoding="utf-8")
            result = target_workspace.verify_identity(saved, root)
        self.assertEqual(result["status"], "inventory-drift")
        self.assertFalse(result["blocking"])
        self.assertEqual(result["inventory_drift"]["removed"], ["gone.py"])
        self.assertEqual([row["path"] for row in result["inventory_drift"]["changed"]], ["keep.py"])

    def test_line_ending_twins_do_not_drift(self) -> None:
        with tempfile.TemporaryDirectory() as temp:
            root = Path(temp)
            (root / "module.py").write_bytes(b"def value():\n    return 1\n")
            saved = target_workspace.identity(root)
            (root / "module.py").write_bytes(b"def value():\r\n    return 1\r\n")
            result = target_workspace.verify_identity(saved, root)
        self.assertEqual(result["status"], "matched")
        self.assertTrue(result["inventory_drift"]["in_sync"])

    def test_legacy_identity_without_file_detail_never_blocks(self) -> None:
        with tempfile.TemporaryDirectory() as temp:
            root = Path(temp)
            saved = target_workspace.identity(root)
            del saved["inventory_detail"]
            (root / "new-module.py").write_text("VALUE = 1\n", encoding="utf-8")
            result = target_workspace.verify_identity(saved, root)
        self.assertEqual(result["status"], "inventory-drift")
        self.assertFalse(result["blocking"])
        self.assertEqual(result["inventory_drift"]["baseline"], "manifests-only")
        self.assertFalse(result["inventory_drift"]["in_sync"])

    def test_different_root_or_remote_still_blocks(self) -> None:
        with tempfile.TemporaryDirectory() as temp:
            root = Path(temp)
            saved = target_workspace.identity(root)
            moved = dict(saved, root=(root / "elsewhere").as_posix())
            self.assertTrue(target_workspace.verify_identity(moved, root)["blocking"])
            remote = json.loads(json.dumps(saved))
            remote["git"]["remote_host"] = "example.org"
            blocked = target_workspace.verify_identity(remote, root)
        self.assertEqual(blocked["status"], "mismatch")
        self.assertTrue(blocked["blocking"])

    def test_identity_fingerprint_is_deterministic_alongside_detail(self) -> None:
        with tempfile.TemporaryDirectory() as temp:
            root = Path(temp)
            first = target_workspace.identity(root)
            second = target_workspace.identity(root)
        self.assertEqual(first["fingerprint"], second["fingerprint"])
        self.assertIn("inventory_detail", first)
        self.assertEqual(first["inventory_detail"]["scheme"], "content-sha256-crlf-normalized-v1")


if __name__ == "__main__":
    unittest.main()
