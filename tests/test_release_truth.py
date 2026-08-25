from __future__ import annotations

import copy
import importlib.util
import json
import sys
import tempfile
import unittest
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, (ROOT / "scripts").as_posix())

import release_manifest  # noqa: E402


def load_script(name: str):
    path = ROOT / "scripts" / name
    spec = importlib.util.spec_from_file_location(f"release_truth_{name.replace('-', '_')}", path)
    assert spec and spec.loader
    module = importlib.util.module_from_spec(spec)
    sys.modules[spec.name] = module
    spec.loader.exec_module(module)
    return module


class ReleaseTruthTests(unittest.TestCase):
    def setUp(self) -> None:
        self.manifest = release_manifest.load(ROOT)

    def test_repository_manifest_and_candidate_are_valid(self) -> None:
        errors = release_manifest.validate(ROOT, self.manifest, release_manifest.candidate_files(ROOT, self.manifest))
        self.assertEqual(errors, [])

    def test_missing_required_file_fails(self) -> None:
        manifest = copy.deepcopy(self.manifest)
        manifest["required_release_files"] = ["missing-required-file.md"]
        manifest["workflows"] = []
        with tempfile.TemporaryDirectory() as temp:
            errors = release_manifest.validate(Path(temp), manifest, [])
        self.assertIn("missing release file: missing-required-file.md", errors)

    def test_wrong_version_fails(self) -> None:
        manifest = copy.deepcopy(self.manifest)
        manifest["required_release_files"] = []
        manifest["workflows"] = []
        with tempfile.TemporaryDirectory() as temp:
            root = Path(temp)
            (root / ".codex-plugin").mkdir()
            (root / "pyproject.toml").write_text('[project]\nversion = "9.9.9"\n', encoding="utf-8")
            (root / ".codex-plugin" / "plugin.json").write_text(json.dumps({"version": "9.9.9"}), encoding="utf-8")
            errors = release_manifest.validate(root, manifest, [])
        self.assertTrue(any("version must equal release manifest version" in error for error in errors))

    def test_stale_workflow_fails(self) -> None:
        manifest = copy.deepcopy(self.manifest)
        manifest["required_release_files"] = []
        manifest["workflows"] = [{"path": ".github/workflows/trust.yml", "required_fragments": ["required release gate"]}]
        with tempfile.TemporaryDirectory() as temp:
            root = Path(temp)
            target = root / ".github" / "workflows" / "trust.yml"
            target.parent.mkdir(parents=True)
            target.write_text("name: stale\n", encoding="utf-8")
            errors = release_manifest.validate(root, manifest, [])
        self.assertIn("stale release workflow .github/workflows/trust.yml: missing required release gate", errors)

    def test_private_reference_fails_and_approved_upstream_passes(self) -> None:
        private = "https://github.com/" + "private-owner/private-repository"
        approved = "https://github.com/awslabs/aidlc-workflows/tree/v1.0.1"
        allowed = self.manifest["public_audit"]["allowed_repository_urls"]
        self.assertEqual(release_manifest.repository_reference_findings(approved, allowed), [])
        self.assertEqual(release_manifest.repository_reference_findings(private, allowed), [private])

    def test_local_state_fails_but_is_excluded_from_candidate_snapshot(self) -> None:
        errors = release_manifest.validate(ROOT, self.manifest, [".tailtrail/runs/local.json"])
        self.assertIn("release candidate contains forbidden local state: .tailtrail/runs/local.json", errors)
        self.assertNotIn(".tailtrail/runs/local.json", release_manifest.candidate_files(ROOT, self.manifest))

    def test_smoke_runs_release_preflight_before_stateful_journey(self) -> None:
        smoke = self.manifest["smoke"]
        preflight = [command[0] for command in smoke["preflight_commands"]]
        journey = [command[0] for command in smoke["journey_commands"]]
        self.assertIn("scripts/release-check.py", preflight)
        self.assertIn("scripts/tailtrail.py", journey)
        self.assertNotIn(["scripts/release-check.py"], smoke["journey_commands"])

    def test_root_navigator_compatibility_entry_point_imports(self) -> None:
        navigator = load_script("../navigator.py")
        self.assertTrue(callable(navigator.decide))
        self.assertTrue(callable(navigator.main))


if __name__ == "__main__":
    unittest.main()
