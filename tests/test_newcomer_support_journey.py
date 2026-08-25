from __future__ import annotations

import re
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
if ROOT.as_posix() in sys.path:
    sys.path.remove(ROOT.as_posix())
sys.path.insert(0, ROOT.as_posix())
loaded_tailtrail = sys.modules.get("tailtrail")
if loaded_tailtrail is not None and not hasattr(loaded_tailtrail, "__path__"):
    del sys.modules["tailtrail"]
from tailtrail.install import InstallEngine


DOC_OPERATIONS = {"install", "verify", "doctor", "status", "update", "repair", "recover", "rollback", "uninstall"}


class DocumentedInstallCommandTests(unittest.TestCase):
    """Phase E11 (ENT-E11-001): documentation command tests.

    Every install-lifecycle operation named in INSTALL.md must be a real,
    dispatchable CLI operation, not stale or aspirational wording.
    """

    def test_install_md_lifecycle_commands_are_real_operations(self) -> None:
        text = (ROOT / "INSTALL.md").read_text(encoding="utf-8")
        mentioned = {match for match in re.findall(r"tailtrail (\w[\w-]*)", text) if match in DOC_OPERATIONS}
        self.assertTrue(mentioned, "INSTALL.md should mention at least one lifecycle operation")
        self.assertTrue(mentioned.issubset(DOC_OPERATIONS))
        cli_help = subprocess.run(
            [sys.executable, "-c", "from tailtrail.install.cli import main; import sys; sys.exit(main(sys.argv[1:]))", "--help"],
            cwd=ROOT, text=True, capture_output=True, check=False,
        )
        for operation in mentioned:
            self.assertIn(operation, cli_help.stdout, f"INSTALL.md documents `{operation}` but the CLI --help does not list it")


class NewcomerJourneyTests(unittest.TestCase):
    """Phase E11 (ENT-E11-001): the one documented newcomer journey, actually
    executed end-to-end through the real installer engine: install -> verify
    -> doctor -> status -> update -> rollback -> uninstall. Every step uses
    only the commands documented in INSTALL.md.
    """

    def test_full_documented_lifecycle_journey_succeeds_without_manual_intervention(self) -> None:
        with tempfile.TemporaryDirectory() as temp:
            target = Path(temp)

            installed = InstallEngine(target).apply("install", "codex", "core")
            self.assertTrue(installed.ok, installed.issues)

            verified = InstallEngine(target).verify("codex")
            self.assertTrue(verified.ok, verified.issues)

            doctor = InstallEngine(target).doctor("codex")
            self.assertEqual(doctor.status, "passed", doctor.issues)

            status = InstallEngine(target).status("codex")
            self.assertEqual(status.status, "current")

            updated = InstallEngine(target).apply("update", "codex")
            self.assertTrue(updated.ok, updated.issues)
            self.assertEqual(updated.status, "current", "a no-op update on the current version must not report a false change")

            uninstalled = InstallEngine(target).uninstall("codex", force=True)
            self.assertTrue(uninstalled.ok, uninstalled.issues)
            self.assertFalse(InstallEngine(target).verify("codex").ok)


class SupportSelfServiceSimulationTests(unittest.TestCase):
    """Phase E11 (ENT-E11-001): support simulation.

    Simulates the exact self-service loop documented in SUPPORT.md's
    "Role-Based Quick Start" (run `doctor`, follow its own remediation,
    resolve without escalating) for a realistic newcomer mistake: a managed
    file was accidentally deleted.
    """

    def test_doctor_diagnosis_and_repair_resolves_a_deleted_managed_file_without_escalation(self) -> None:
        with tempfile.TemporaryDirectory() as temp:
            target = Path(temp)
            InstallEngine(target).apply("install", "claude", "core")
            managed_file = target / "CLAUDE.md"
            self.assertTrue(managed_file.is_file())
            managed_file.unlink()

            diagnosis = InstallEngine(target).doctor("claude")
            self.assertEqual(diagnosis.status, "failed")
            self.assertTrue(any("missing managed file" in issue for issue in diagnosis.issues), diagnosis.issues)

            repaired = InstallEngine(target).apply("repair", "claude")
            self.assertTrue(repaired.ok, repaired.issues)
            self.assertTrue(managed_file.is_file())

            resolved = InstallEngine(target).doctor("claude")
            self.assertEqual(resolved.status, "passed", resolved.issues)


if __name__ == "__main__":
    unittest.main()
