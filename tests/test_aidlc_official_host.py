from __future__ import annotations

import hashlib
import importlib.util
import json
import tempfile
import unittest
from pathlib import Path


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


if __name__ == "__main__":
    unittest.main()
