import importlib.util
import json
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
SCRIPTS = ROOT / "scripts"
if SCRIPTS.as_posix() not in sys.path:
    sys.path.insert(0, SCRIPTS.as_posix())


def load_script(name: str):
    path = SCRIPTS / name
    spec = importlib.util.spec_from_file_location(name.replace("-", "_").replace(".py", ""), path)
    assert spec and spec.loader
    module = importlib.util.module_from_spec(spec)
    sys.modules[spec.name] = module
    spec.loader.exec_module(module)
    return module


surfaces = load_script("install_surfaces.py")
copilot = load_script("install-copilot.py")
local = load_script("install-local.py")
launcher = load_script("install-launcher.py")
updater = load_script("update-copilot.py")


def run(*args: str, cwd: Path = ROOT) -> subprocess.CompletedProcess[str]:
    return subprocess.run([sys.executable, *args], cwd=cwd, text=True, capture_output=True, check=False)


def relative_files(root: Path) -> set[str]:
    return {path.relative_to(root).as_posix() for path in root.rglob("*") if path.is_file()}


class InstallProfileTests(unittest.TestCase):
    def test_windows_launcher_uses_cmd_shims(self):
        bin_dir = Path("C:/TailTrail/bin")
        self.assertEqual(launcher.command_destination(bin_dir, "tailtrail", windows=True), bin_dir / "tailtrail.cmd")
        self.assertEqual(launcher.command_destination(bin_dir, "hello", windows=True), bin_dir / "hello.cmd")
        self.assertIn("@echo off", launcher.launcher_body(windows=True))
        self.assertIn("tailtrail.py", launcher.launcher_body(windows=True))
        self.assertIn("hello %2", launcher.hello_alias_body(windows=True))

    def test_core_manifest_is_subset_of_extended_manifest(self):
        extended_files = set(copilot.PACK_FILES)
        extended_dirs = set(copilot.PACK_DIRS)
        extended_scripts = set(copilot.PACK_SCRIPTS)
        self.assertLessEqual(set(surfaces.CORE_FILES), extended_files)
        self.assertLessEqual(set(surfaces.CORE_CONTEXT), extended_files)
        self.assertLessEqual(set(surfaces.CORE_TEMPLATES), extended_files)
        self.assertLessEqual(set(surfaces.CORE_DIRS), extended_dirs)
        self.assertLessEqual(set(surfaces.CORE_SCRIPTS), extended_scripts)

    def test_core_is_materially_smaller(self):
        self.assertLess(len(surfaces.CORE_SCRIPTS), 0.5 * len(copilot.PACK_SCRIPTS))

    def test_extended_default_resolves_same_as_explicit_extended(self):
        default_files, default_dirs, default_scripts = surfaces.resolve(
            surfaces.DEFAULT_SURFACE,
            copilot.PACK_FILES,
            copilot.PACK_DIRS,
            copilot.PACK_SCRIPTS,
        )
        extended_files, extended_dirs, extended_scripts = surfaces.resolve(
            "extended",
            copilot.PACK_FILES,
            copilot.PACK_DIRS,
            copilot.PACK_SCRIPTS,
        )
        self.assertEqual((default_files, default_dirs, default_scripts), (extended_files, extended_dirs, extended_scripts))
        steps_default = local.steps_for("copilot", Path("/tmp/example"), "tailtrail", "standard", "optional", False, surfaces.DEFAULT_SURFACE)
        steps_explicit = local.steps_for("copilot", Path("/tmp/example"), "tailtrail", "standard", "optional", False, "extended")
        self.assertEqual(steps_default[0].command, steps_explicit[0].command)

    def test_codex_profile_installs_project_guidance_without_overwriting(self):
        with tempfile.TemporaryDirectory() as tmp:
            target = Path(tmp)
            steps = local.steps_for("codex", target, "tailtrail", "standard", "optional", False, "extended")
            self.assertEqual(len(steps), 1)
            self.assertEqual(steps[0].action, "copy")
            self.assertEqual(steps[0].destination, target / "AGENTS.md")

            (target / "AGENTS.md").write_text("existing guidance\n", encoding="utf-8")
            preserved = local.steps_for("codex", target, "tailtrail", "standard", "optional", False, "extended")
            self.assertEqual(preserved[0].action, "skip")
            self.assertIn("preserve", preserved[0].note or "")

    def test_codex_plugin_profile_installs_plugin_source(self):
        with tempfile.TemporaryDirectory() as tmp:
            target = Path(tmp)
            steps = local.steps_for("codex-plugin", target, "tailtrail", "standard", "optional", False, "extended")
            self.assertGreaterEqual(len(steps), 3)
            self.assertEqual(steps[0].action, "copy")
            self.assertEqual(steps[0].destination, target / "AGENTS.md")
            self.assertEqual(steps[1].action, "copytree")
            self.assertEqual(steps[1].destination, target / ".codex-plugin")
            self.assertEqual(steps[2].action, "copytree")
            self.assertEqual(steps[2].destination, target / "skills")
            self.assertEqual(len(steps), 3)

    def test_installer_preflight_uses_adapter_sync_not_release_tree_audit(self):
        body = (SCRIPTS / "install-local.py").read_text(encoding="utf-8")
        self.assertIn('"sync-adapters.py"', body)
        self.assertNotIn('str(ROOT / "scripts" / "check-tailtrail.py")', body)

    def test_claude_profile_installs_guidance_and_atomic_start_command(self):
        with tempfile.TemporaryDirectory() as tmp:
            target = Path(tmp)
            steps = local.steps_for("claude", target, "tailtrail", "standard", "optional", False, "extended")
            self.assertEqual([step.action for step in steps], ["copy", "copy"])
            self.assertEqual(steps[0].destination, target / "CLAUDE.md")
            self.assertEqual(steps[1].destination, target / ".claude" / "commands" / "tailtrail-start.md")

    def test_core_omits_extended_only_files(self):
        core_files, core_dirs, core_scripts = surfaces.resolve("core", copilot.PACK_FILES, copilot.PACK_DIRS, copilot.PACK_SCRIPTS)
        core_entries = set(copilot.pack_entries_for(core_files, core_dirs, core_scripts))
        extended_only = {
            "scripts/learning-agent.py",
            "scripts/quality-loop.py",
            "scripts/meta-harness-analyze.py",
            "scripts/tailtrail-report.py",
            "hooks/learning-capture-hook.py",
        }
        self.assertTrue(extended_only.isdisjoint(core_entries))
        self.assertNotIn("hooks", set(core_dirs))
        self.assertNotIn("benchmarks", set(core_dirs))
        self.assertNotIn("aidlc", set(core_dirs))

    def test_core_contains_first_run_functionality(self):
        core_files, core_dirs, core_scripts = surfaces.resolve("core", copilot.PACK_FILES, copilot.PACK_DIRS, copilot.PACK_SCRIPTS)
        entries = set(copilot.pack_entries_for(core_files, core_dirs, core_scripts))
        required = {
            "scripts/tailtrail.py",
            "scripts/task-start.py",
            "scripts/navigator.py",
            "scripts/navigator_core.py",
            "scripts/navigator_render.py",
            "scripts/prompt_profile.py",
            "scripts/token_budget_coach.py",
            "scripts/guardrail-check.py",
            "scripts/sync-governance.py",
            "GOVERNANCE.md",
            "GUARDRAILS.md",
            "TAILTRAIL-COMMANDS.md",
            "context/guardrail-layers.md",
        }
        self.assertLessEqual(required, entries)

    def test_copilot_start_prompt_uses_the_installed_pack_path(self):
        rendered = copilot.start_prompt_body(Path("tools/tailtrail"))
        self.assertIn('python3 tools/tailtrail/scripts/tailtrail.py start "<goal>"', rendered)
        self.assertNotIn("--open-report", rendered)
        self.assertNotIn("{{TAILTRAIL_START_COMMAND}}", rendered)

    def test_upgrade_to_extended_is_additive(self):
        with tempfile.TemporaryDirectory() as tmp:
            target = Path(tmp) / "core"
            result = run("scripts/install-copilot.py", "--target", target.as_posix(), "--surface", "core")
            self.assertEqual(result.returncode, 0, result.stderr + result.stdout)
            _, to_add, blocked = copilot.plan_upgrade(target, Path("."))
            core_files, core_dirs, core_scripts = surfaces.resolve("core", copilot.PACK_FILES, copilot.PACK_DIRS, copilot.PACK_SCRIPTS)
            core_entries = set(copilot.pack_entries_for(core_files, core_dirs, core_scripts))
            self.assertTrue(to_add)
            self.assertFalse(blocked)
            self.assertTrue(core_entries.isdisjoint(to_add))

    def test_manifest_records_surface(self):
        with tempfile.TemporaryDirectory() as tmp:
            core_target = Path(tmp) / "core"
            extended_target = Path(tmp) / "extended"
            core = run("scripts/install-copilot.py", "--target", core_target.as_posix(), "--surface", "core")
            extended = run("scripts/install-copilot.py", "--target", extended_target.as_posix())
            self.assertEqual(core.returncode, 0, core.stderr + core.stdout)
            self.assertEqual(extended.returncode, 0, extended.stderr + extended.stdout)
            core_manifest = json.loads((core_target / ".tailtrail-install.json").read_text(encoding="utf-8"))
            extended_manifest = json.loads((extended_target / ".tailtrail-install.json").read_text(encoding="utf-8"))
            self.assertEqual(core_manifest["surface"], "core")
            self.assertEqual(extended_manifest["surface"], "extended")

    def test_unknown_surface_rejected(self):
        with self.assertRaises(ValueError):
            surfaces.resolve("gold", copilot.PACK_FILES, copilot.PACK_DIRS, copilot.PACK_SCRIPTS)
        with tempfile.TemporaryDirectory() as tmp:
            result = run("scripts/install-copilot.py", "--target", tmp, "--surface", "gold")
        self.assertNotEqual(result.returncode, 0)
        self.assertIn("invalid choice", result.stderr)

    def test_core_manifest_lists_are_sorted(self):
        for name in ("CORE_FILES", "CORE_DIRS", "CORE_SCRIPTS", "CORE_CONTEXT", "CORE_TEMPLATES"):
            values = list(getattr(surfaces, name))
            self.assertEqual(values, sorted(values), name)

    def test_core_surface_includes_registry_owned_core_entries(self):
        files, _dirs, scripts = surfaces.resolve("core", copilot.PACK_FILES, copilot.PACK_DIRS, copilot.PACK_SCRIPTS)

        self.assertIn("tailtrail-registry.json", files)
        self.assertIn("scripts/tailtrail-registry.py", scripts)

    def test_extended_pack_includes_every_registered_feature_script_and_root_guide(self):
        registry = json.loads((ROOT / "tailtrail-registry.json").read_text(encoding="utf-8"))
        registered_scripts = {
            script
            for feature in registry["features"]
            for script in feature.get("scripts", [])
        }
        registered_root_docs = {
            doc
            for feature in registry["features"]
            for doc in feature.get("docs", [])
            if "/" not in doc
        }
        self.assertLessEqual(registered_scripts, set(copilot.PACK_SCRIPTS))
        self.assertLessEqual(registered_root_docs, set(copilot.PACK_FILES))

    def test_extended_pack_includes_phase7_through_phase12_runtime_surface(self):
        entries = set(copilot.pack_entries_for(copilot.PACK_FILES, copilot.PACK_DIRS, copilot.PACK_SCRIPTS))
        self.assertTrue({
            "scripts/workflow_runtime/context.py",
            "scripts/workflow_runtime/outcomes.py",
            "scripts/workflow_runtime/mcp_bridge.py",
            "scripts/workflow_runtime/ci.py",
            "scripts/workflow_runtime/assurance.py",
            "scripts/workflow_runtime/denials.py",
            "scripts/workflow_runtime/retention.py",
            "scripts/workflow_runtime/release.py",
            "scripts/workflow_runtime/enterprise.py",
            "scripts/workflow_runtime/enterprise_transport.py",
            "scripts/workflow_runtime/enterprise_recovery.py",
            "schemas/workflow-context-receipt.schema.json",
            "schemas/workflow-token-telemetry.schema.json",
            "schemas/workflow-learning-link.schema.json",
            "schemas/workflow-evaluation-event.schema.json",
            "schemas/workflow-meta-harness-signal.schema.json",
            "schemas/workflow-ci-policy.schema.json",
            "schemas/workflow-ci-receipt.schema.json",
            "schemas/workflow-ci-continuation.schema.json",
            "schemas/workflow-denial-audit.schema.json",
            "schemas/workflow-retention-policy.schema.json",
            "schemas/workflow-retention-plan.schema.json",
            "schemas/workflow-retention-cleanup.schema.json",
            "schemas/workflow-assurance-report.schema.json",
            "schemas/workflow-release-scenario.schema.json",
            "schemas/workflow-real-run-proof.schema.json",
            "schemas/workflow-release-gate.schema.json",
            "schemas/workflow-compatibility-report.schema.json",
            "schemas/workflow-retirement-decision.schema.json",
            "schemas/workflow-enterprise-policy.schema.json",
            "schemas/workflow-enterprise-binding.schema.json",
            "schemas/workflow-enterprise-lease.schema.json",
            "schemas/workflow-enterprise-event.schema.json",
            "schemas/workflow-enterprise-link.schema.json",
            "schemas/workflow-enterprise-backup.schema.json",
            "schemas/workflow-enterprise-migration.schema.json",
            "schemas/workflow-enterprise-conformance.schema.json",
            "schemas/workflow-enterprise-entry.schema.json",
            "schemas/workflow-enterprise-replay.schema.json",
            "schemas/workflow-enterprise-observability.schema.json",
            "schemas/workflow-enterprise-restore-validation.schema.json",
        } <= entries)

    def test_copilot_update_rewrites_manifest_with_the_installed_surface(self):
        with tempfile.TemporaryDirectory() as tmp:
            target = Path(tmp)
            report = updater.update_copilot(target, Path("tailtrail"), "preserve", False)
            manifest = json.loads((target / "tailtrail" / ".tailtrail-install.json").read_text(encoding="utf-8"))
        self.assertFalse(report.conflicts)
        self.assertEqual(manifest["surface"], "extended")
        self.assertIn("scripts/completion-report.py", manifest["files"])
        self.assertIn("scripts/official-aidlc-runtime.py", manifest["files"])
        self.assertIn("scripts/aidlc-official-install.py", manifest["files"])
        self.assertIn("scripts/host-runtime-conformance.py", manifest["files"])
        self.assertIn("schemas/official-aidlc-session.schema.json", manifest["files"])
        self.assertIn("schemas/official-aidlc-transition-receipt.schema.json", manifest["files"])
        self.assertIn("schemas/host-runtime-receipt.schema.json", manifest["files"])
        self.assertIn("adapters/runtime-scenarios-v1.json", manifest["files"])

    def test_copilot_update_renders_start_prompt_for_project_and_pack(self):
        with tempfile.TemporaryDirectory() as tmp:
            target = Path(tmp)
            updater.update_copilot(target, Path("tailtrail"), "preserve", False)
            for prompt in (
                target / ".github" / "prompts" / "tailtrail-start.prompt.md",
                target / "tailtrail" / ".github" / "prompts" / "tailtrail-start.prompt.md",
            ):
                rendered = prompt.read_text(encoding="utf-8")
                self.assertNotIn('--open-report', rendered)
                self.assertNotIn("{{TAILTRAIL_START_COMMAND}}", rendered)


if __name__ == "__main__":
    unittest.main()
