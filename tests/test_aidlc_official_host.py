from __future__ import annotations

import hashlib
import importlib.util
import json
import os
import tempfile
import unittest
from pathlib import Path
from unittest import mock

import jsonschema

from tailtrail.aidlc_bundle import BindingInputs, ProjectionInputs, ResolverInputs, bind_run, provision, resolve


ROOT = Path(__file__).resolve().parents[1]


def load():
    spec = importlib.util.spec_from_file_location("aidlc_official_host_test", ROOT / "scripts" / "aidlc-official-host.py")
    assert spec and spec.loader
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


host = load()


def sha256(content: bytes) -> str:
    return hashlib.sha256(content).hexdigest()


def compatible_pack(root: Path) -> None:
    pack = root / ".tailtrail" / "official-aidlc"
    core = pack / "aws-aidlc-rules" / "core-workflow.md"
    details = pack / "aws-aidlc-rule-details" / "common" / "process-overview.md"
    core.parent.mkdir(parents=True); details.parent.mkdir(parents=True)
    core.write_text("# Exact official core\n", encoding="utf-8")
    details.write_text("# Details\n", encoding="utf-8")
    files = []
    for path in (core, details):
        files.append({"path": path.relative_to(pack).as_posix(), "sha256": sha256(path.read_bytes())})
    (pack / "LICENSE").write_text("MIT-0\n", encoding="utf-8")
    files.append({"path": "LICENSE", "sha256": sha256((pack / "LICENSE").read_bytes())})
    (pack / "manifest.json").write_text(json.dumps({
        "schema_version": "1", "type": "tailtrail-official-aidlc-pack",
        "official": {"source": "https://github.com/awslabs/aidlc-workflows", "revision": "v1.0.1", "license": {"spdx": "MIT-0", "file": "LICENSE"}},
        "host_adapter": {"host": "codex", "rules_path": "aws-aidlc-rules/core-workflow.md"},
        "integrity": {"algorithm": "sha256", "files": files},
    }), encoding="utf-8")


def frozen_project(root: Path, run_id: str = "run-phase4") -> dict[str, object]:
    resolution = resolve(ResolverInputs(
        host="codex",
        module_path=ROOT / "tailtrail" / "aidlc_bundle.py",
        environment={},
    ))
    if resolution.get("state") != "ready":
        raise AssertionError(resolution)
    projection = provision(ProjectionInputs(resolution, root))
    if projection.get("state") != "ready":
        raise AssertionError(projection)
    binding = bind_run(BindingInputs(root, run_id, projection))
    if binding.get("state") != "ready":
        raise AssertionError(binding)
    (root / "AGENTS.md").write_text("# Codex guidance\n", encoding="utf-8")
    (root / ".github").mkdir()
    (root / ".github" / "copilot-instructions.md").write_text("# Copilot guidance\n", encoding="utf-8")
    (root / "CLAUDE.md").write_text("# Claude guidance\n", encoding="utf-8")
    return {"resolution": resolution, "projection": projection, "binding": binding, "run_id": run_id}


class OfficialAidlcHostTests(unittest.TestCase):
    def test_codex_projection_preserves_agents_and_points_to_exact_pack(self) -> None:
        with tempfile.TemporaryDirectory() as temp:
            root = Path(temp); compatible_pack(root)
            (root / "AGENTS.md").write_text("# Project guidance\n", encoding="utf-8")
            result = host.install(root)
            agents = (root / "AGENTS.md").read_text(encoding="utf-8")
            self.assertEqual(result["state"], "installed")
            self.assertIn("# Project guidance", agents)
            self.assertIn(host.START, agents)
            self.assertIn("--aidlc full", agents)
            self.assertEqual((root / host.PROJECTED_CORE).read_text(encoding="utf-8"), "# Exact official core\n")
            self.assertTrue((root / host.PROJECTED_DETAILS / "common" / "process-overview.md").is_file())

    def test_projection_never_overwrites_existing_official_detail_files(self) -> None:
        with tempfile.TemporaryDirectory() as temp:
            root = Path(temp); compatible_pack(root)
            (root / "AGENTS.md").write_text("# Project guidance\n", encoding="utf-8")
            existing = root / host.PROJECTED_DETAILS
            existing.mkdir(parents=True)
            with self.assertRaisesRegex(ValueError, "already exists"):
                host.install(root)
            self.assertNotIn(host.START, (root / "AGENTS.md").read_text(encoding="utf-8"))

    def test_three_hosts_share_one_frozen_identity_and_fixed_modes_offline(self) -> None:
        with tempfile.TemporaryDirectory() as temp:
            root = Path(temp); frozen = frozen_project(root)
            with mock.patch("socket.create_connection", side_effect=AssertionError("network forbidden")):
                results = {name: host.install(root, name, frozen["run_id"]) for name in ("codex", "copilot", "claude")}
                statuses = {name: host.status(root, name, frozen["run_id"]) for name in results}
            schema = json.loads((ROOT / "schemas" / "official-aidlc-host-projection-receipt.schema.json").read_text(encoding="utf-8"))
            jsonschema.Draft202012Validator.check_schema(schema)
            validator = jsonschema.Draft202012Validator(schema)
            for row in results.values():
                validator.validate(json.loads((root / row["receipt"]).read_text(encoding="utf-8")))

        self.assertEqual({name: row["state"] for name, row in results.items()}, {"codex": "installed", "copilot": "installed", "claude": "installed"})
        self.assertEqual({name: row["projection_mode"] for name, row in results.items()}, {"codex": "copy", "copilot": "reference", "claude": "reference"})
        self.assertEqual(len({json.dumps(row["origin"], sort_keys=True) for row in results.values()}), 1)
        self.assertEqual(len({json.dumps(row["official_identity"], sort_keys=True) for row in results.values()}), 1)
        self.assertEqual({row["state"] for row in statuses.values()}, {"installed"})
        self.assertTrue(all(row["network_used"] is False for row in statuses.values()))

    def test_identical_projection_is_idempotent_and_ignores_later_selector_change(self) -> None:
        with tempfile.TemporaryDirectory() as temp:
            root = Path(temp); frozen = frozen_project(root)
            first = {name: host.install(root, name, frozen["run_id"]) for name in ("codex", "copilot", "claude")}
            artifacts = {
                name: root / first[name]["receipt"]
                for name in first
            }
            before_receipts = {name: path.read_bytes() for name, path in artifacts.items()}
            before_copy = {
                path.relative_to(root / host.PROJECTED_ROOT).as_posix(): path.stat().st_mtime_ns
                for path in (root / host.PROJECTED_ROOT).rglob("*") if path.is_file()
            }
            selector = root / ".tailtrail" / "official-aidlc" / "current.json"
            selector.write_text('{"intentionally":"not consulted by an active run"}\n', encoding="utf-8")
            second = {name: host.install(root, name, frozen["run_id"]) for name in ("codex", "copilot", "claude")}
            after_copy = {
                path.relative_to(root / host.PROJECTED_ROOT).as_posix(): path.stat().st_mtime_ns
                for path in (root / host.PROJECTED_ROOT).rglob("*") if path.is_file()
            }
            after_receipts = {name: path.read_bytes() for name, path in artifacts.items()}

        self.assertEqual({row["status"] for row in second.values()}, {"reused"})
        self.assertEqual(before_copy, after_copy)
        self.assertEqual(before_receipts, after_receipts)

    def test_codex_status_rejects_missing_additional_altered_symlink_and_nonregular_entries(self) -> None:
        mutations = ("missing", "additional", "altered", "symlink", "nonregular")
        for mutation in mutations:
            with self.subTest(mutation=mutation), tempfile.TemporaryDirectory() as temp:
                root = Path(temp); frozen = frozen_project(root); host.install(root, "codex", frozen["run_id"])
                copied = root / host.PROJECTED_ROOT
                target = copied / "LICENSE"
                if mutation == "missing":
                    target.unlink()
                elif mutation == "additional":
                    (copied / "unexpected.md").write_text("unexpected\n", encoding="utf-8")
                elif mutation == "altered":
                    target.write_text("altered\n", encoding="utf-8")
                elif mutation == "symlink":
                    target.unlink(); target.symlink_to(copied / "VERSION")
                else:
                    if not hasattr(os, "mkfifo"):
                        self.skipTest("FIFO proof requires os.mkfifo")
                    os.mkfifo(copied / "unexpected-fifo")
                result = host.status(root, "codex", frozen["run_id"])
                self.assertEqual(result["state"], "blocked", result)

    def test_reference_status_and_receipt_fail_closed_on_tampering(self) -> None:
        with tempfile.TemporaryDirectory() as temp:
            root = Path(temp); frozen = frozen_project(root)
            installed = host.install(root, "copilot", frozen["run_id"])
            instruction = root / ".github" / "copilot-instructions.md"
            instruction.write_text(instruction.read_text(encoding="utf-8").replace("Do not download", "Please download"), encoding="utf-8")
            self.assertEqual(host.status(root, "copilot", frozen["run_id"])["state"], "blocked")
            receipt = root / installed["receipt"]
            payload = json.loads(receipt.read_text(encoding="utf-8")); payload["trust_posture"] = "forged"
            receipt.write_text(json.dumps(payload), encoding="utf-8")
            result = host.status(root, "copilot", frozen["run_id"])
        self.assertEqual(result["state"], "blocked")
        self.assertTrue(any("integrity seal" in issue for issue in result["issues"]))

    def test_unrecognized_codex_destination_is_preserved_and_rejected(self) -> None:
        with tempfile.TemporaryDirectory() as temp:
            root = Path(temp); frozen = frozen_project(root)
            destination = root / host.PROJECTED_ROOT
            destination.mkdir(parents=True)
            user_file = destination / "user-owned.txt"
            user_file.write_text("preserve me\n", encoding="utf-8")
            with self.assertRaisesRegex(ValueError, "already exists"):
                host.install(root, "codex", frozen["run_id"])
            self.assertEqual(user_file.read_text(encoding="utf-8"), "preserve me\n")
            self.assertNotIn(host.START, (root / "AGENTS.md").read_text(encoding="utf-8"))

    def test_unsafe_projection_ancestor_is_rejected_without_external_write(self) -> None:
        with tempfile.TemporaryDirectory() as temp, tempfile.TemporaryDirectory() as external:
            root = Path(temp); frozen = frozen_project(root)
            (root / ".aidlc").symlink_to(Path(external), target_is_directory=True)
            with self.assertRaisesRegex(ValueError, "unsafe ancestor"):
                host.install(root, "codex", frozen["run_id"])
            self.assertEqual(list(Path(external).iterdir()), [])
            self.assertNotIn(host.START, (root / "AGENTS.md").read_text(encoding="utf-8"))


if __name__ == "__main__":
    unittest.main()
