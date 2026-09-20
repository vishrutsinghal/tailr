from __future__ import annotations

import hashlib
import importlib.util
import json
import sys
import tempfile
import unittest
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]

REQUIRED_LF_EXTENSIONS = (
    ".py", ".md", ".mdc", ".json", ".jsonl", ".yml", ".yaml",
    ".toml", ".txt", ".csv",
)


def load_detect():
    spec = importlib.util.spec_from_file_location(
        "tailtrail_official_detect_endings", ROOT / "scripts" / "aidlc-official-detect.py"
    )
    assert spec and spec.loader
    module = importlib.util.module_from_spec(spec)
    sys.modules[spec.name] = module
    spec.loader.exec_module(module)
    return module


def write_pack(pack: Path, newline: bytes) -> None:
    files = {
        "LICENSE": b"MIT-0\n",
        "core-workflow.md": b"# workflow\n",
        "aws-aidlc-rules/core-workflow.md": b"# Requirements Analysis\n",
    }
    for relative, content in files.items():
        path = pack / relative
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_bytes(content.replace(b"\n", newline))
    manifest = {
        "schema_version": "1",
        "type": "tailtrail-official-aidlc-pack",
        "official": {
            "source": "https://github.com/awslabs/aidlc-workflows",
            "revision": "v1.0.1",
            "license": {"spdx": "MIT-0", "file": "LICENSE"},
        },
        "host_adapter": {"host": "codex", "rules_path": "core-workflow.md"},
        "integrity": {
            "algorithm": "sha256",
            "files": [
                {
                    "path": relative,
                    "sha256": hashlib.sha256(
                        content.replace(b"\n", b"\n")
                    ).hexdigest(),
                }
                for relative, content in files.items()
            ],
        },
    }
    (pack / "manifest.json").write_bytes(
        json.dumps(manifest).replace("\n", "\n").encode("utf-8")
    )


class LineEndingTests(unittest.TestCase):
    def test_gitattributes_pins_lf_for_text_types(self) -> None:
        attributes = (ROOT / ".gitattributes").read_text(encoding="utf-8")
        for extension in REQUIRED_LF_EXTENSIONS:
            with self.subTest(extension=extension):
                self.assertIn(f"{extension} text eol=lf", attributes)

    def test_lf_pack_verifies_byte_identically(self) -> None:
        detect = load_detect()
        with tempfile.TemporaryDirectory() as temp:
            pack = Path(temp) / ".tailtrail" / "official-aidlc"
            write_pack(pack, b"\n")
            result = detect.status(Path(temp))
        self.assertTrue(result["compatible"], result.get("issues"))
        self.assertEqual(result.get("issues"), [])

    def test_crlf_checkout_breaks_byte_pinned_hashes(self) -> None:
        # Documents why .gitattributes forces eol=lf: the manifest pins the
        # LF bytes, so a CRLF checkout of the same content must fail closed
        # with an integrity mismatch rather than verify.
        detect = load_detect()
        with tempfile.TemporaryDirectory() as temp:
            pack = Path(temp) / ".tailtrail" / "official-aidlc"
            write_pack(pack, b"\r\n")
            result = detect.status(Path(temp))
        self.assertFalse(result["compatible"])
        self.assertTrue(
            any("integrity hash mismatch" in issue for issue in result["issues"]),
            result["issues"],
        )


if __name__ == "__main__":
    unittest.main()
