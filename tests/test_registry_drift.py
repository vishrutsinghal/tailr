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


registry_drift = load_script("registry_drift_test", "scripts/registry-drift.py")


class RegistryDriftTests(unittest.TestCase):
    def write_root(self, root: Path, *, command_doc: str = "tailtrail demo\n", changelog: str = "## Unreleased\n", roadmap: str = "", public_doc: str = "") -> None:
        (root / "scripts").mkdir()
        (root / "tests").mkdir()
        (root / "docs").mkdir()
        (root / "scripts" / "tailtrail.py").write_text(
            "COMMANDS = {'demo': 'Demo command'}\n",
            encoding="utf-8",
        )
        (root / "scripts" / "demo.py").write_text("from __future__ import annotations\n", encoding="utf-8")
        (root / "tests" / "test_demo.py").write_text("", encoding="utf-8")
        (root / "docs" / "demo.md").write_text("", encoding="utf-8")
        (root / "TAILTRAIL-COMMANDS.md").write_text(command_doc, encoding="utf-8")
        (root / "CHANGELOG.md").write_text(changelog, encoding="utf-8")
        (root / "ROADMAP.md").write_text(roadmap, encoding="utf-8")
        (root / "PUBLIC-CLAIMS.md").write_text(public_doc, encoding="utf-8")
        (root / "TAILTRAIL-PITCH.md").write_text("", encoding="utf-8")
        (root / "README.md").write_text(public_doc, encoding="utf-8")
        (root / "USER-GUIDE.md").write_text("", encoding="utf-8")
        (root / "tailtrail-registry.json").write_text(json.dumps(self.registry()), encoding="utf-8")

    def registry(self) -> dict:
        return {
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
                    "commands": ["tailtrail demo"],
                    "docs": ["docs/demo.md"],
                    "scripts": ["scripts/demo.py", "scripts/tailtrail.py"],
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

    def test_clean_temp_root_has_no_drift(self) -> None:
        with tempfile.TemporaryDirectory() as temp:
            root = Path(temp)
            self.write_root(root)

            report = registry_drift.collect_drift(root, changed_files=[])

        self.assertEqual(report["status"], "passed")
        self.assertEqual(report["issues"], [])

    def test_missing_command_doc_is_reported(self) -> None:
        with tempfile.TemporaryDirectory() as temp:
            root = Path(temp)
            self.write_root(root, command_doc="")

            report = registry_drift.collect_drift(root, changed_files=[])

        self.assertEqual(report["status"], "failed")
        self.assertTrue(any(issue["category"] == "command-docs" for issue in report["issues"]))

    def test_changelog_required_for_feature_impacting_change(self) -> None:
        with tempfile.TemporaryDirectory() as temp:
            root = Path(temp)
            self.write_root(root, changelog="# Changelog\n")

            report = registry_drift.collect_drift(root, changed_files=["scripts/demo.py"])

        self.assertTrue(any(issue["category"] == "changelog" for issue in report["issues"]))

    def test_stale_roadmap_wording_is_reported(self) -> None:
        with tempfile.TemporaryDirectory() as temp:
            root = Path(temp)
            self.write_root(root, roadmap="`tailtrail demo` is not implemented yet.\n")

            report = registry_drift.collect_drift(root, changed_files=[])

        self.assertTrue(any(issue["category"] == "roadmap" for issue in report["issues"]))

    def test_public_claim_issue_is_reported(self) -> None:
        with tempfile.TemporaryDirectory() as temp:
            root = Path(temp)
            self.write_root(root, public_doc="TailTrail guarantees token savings.\n")

            report = registry_drift.collect_drift(root, changed_files=[])

        self.assertTrue(any(issue["category"] == "claims" for issue in report["issues"]))

    def test_cli_strict_fails_for_current_unreleased_change_without_changelog_when_forced(self) -> None:
        result = subprocess.run(
            [
                sys.executable,
                (ROOT / "scripts" / "registry-drift.py").as_posix(),
                "--format",
                "json",
            ],
            cwd=ROOT,
            text=True,
            capture_output=True,
            check=False,
        )

        self.assertEqual(result.returncode, 0, result.stderr)
        payload = json.loads(result.stdout)
        self.assertEqual(payload["type"], "tailtrail-registry-drift-report")


if __name__ == "__main__":
    unittest.main()
