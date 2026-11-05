from __future__ import annotations

import importlib.util
import io
import json
import os
import tempfile
import unittest
import zipfile
from pathlib import Path
from unittest import mock

import jsonschema


ROOT = Path(__file__).resolve().parents[1]
COMMIT = "a" * 40
LICENSE = b"MIT No Attribution\nCopyright Example\n"
CORE = "aws-aidlc-rules/core-workflow.md"
DETAIL = "aws-aidlc-rule-details/inception/requirements-analysis.md"
CAPABILITY_FILES = {
    "aws-aidlc-rule-details/common/question-format-guide.md": b"# Questions\n",
    "aws-aidlc-rule-details/common/content-validation.md": b"# Content validation\n",
    "aws-aidlc-rule-details/common/session-continuity.md": b"# Session continuity\n",
}


def complete(files: dict[str, bytes]) -> dict[str, bytes]:
    return {**CAPABILITY_FILES, **files}


def load():
    spec = importlib.util.spec_from_file_location(
        "aidlc_bundle_provenance_test",
        ROOT / "scripts" / "aidlc-official-install.py",
    )
    assert spec and spec.loader
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


installer = load()


def official_archive(files: dict[str, bytes]) -> bytes:
    output = io.BytesIO()
    with zipfile.ZipFile(output, "w") as bundle:
        for path, content in complete(files).items():
            bundle.writestr(f"aidlc-rules/{path}", content)
    return output.getvalue()


def seed_checkout(root: Path, files: dict[str, bytes]) -> None:
    bundle = root / "aidlc-rules"
    (bundle / "VERSION").parent.mkdir(parents=True, exist_ok=True)
    (bundle / "VERSION").write_text("0.1.8\n", encoding="utf-8")
    for path, content in complete(files).items():
        target = bundle / path
        target.parent.mkdir(parents=True, exist_ok=True)
        target.write_bytes(content)


def prepare(root: Path, files: dict[str, bytes], **overrides):
    arguments = {
        "revision": "v1.0.1",
        "commit": COMMIT,
        "archive_bytes": official_archive(files),
        "license_bytes": LICENSE,
        "commit_evidence": json.dumps({"sha": COMMIT}).encode(),
        "acquired_at": "2026-11-04T00:00:00Z",
    }
    arguments.update(overrides)
    return installer.prepare_checked_in_bundle(root, **arguments)


class AidlcBundleProvenanceTests(unittest.TestCase):
    def test_resolves_peeled_commit_from_git_ls_remote_evidence(self) -> None:
        tag_object = "b" * 40
        evidence = (
            f"{tag_object}\trefs/tags/v1.0.1\n"
            f"{COMMIT}\trefs/tags/v1.0.1^{{}}\n"
        ).encode()

        self.assertEqual(installer.resolve_full_commit("v1.0.1", evidence), COMMIT)

    def test_preserves_exact_rules_and_records_phase0_decisions(self) -> None:
        files = {CORE: b"# Official flow\n", DETAIL: b"# Requirements\n"}
        with tempfile.TemporaryDirectory() as temp:
            root = Path(temp)
            seed_checkout(root, files)
            before = {path: (root / "aidlc-rules" / path).stat().st_ino for path in files}

            result = prepare(root, files)

            self.assertEqual(result["state"], "prepared")
            self.assertEqual(result["matched_files"], sorted(complete(files)))
            self.assertEqual(result["added_files"], [])
            self.assertEqual(result["replaced_files"], [])
            self.assertEqual(
                before,
                {path: (root / "aidlc-rules" / path).stat().st_ino for path in files},
            )
            provenance = json.loads((root / "aidlc-rules" / "PROVENANCE.json").read_text(encoding="utf-8"))
            self.assertEqual(provenance["official"]["commit"], COMMIT)
            self.assertEqual(
                provenance["official"]["commit_evidence"]["acquisition"],
                "github-commit-api-over-https",
            )
            self.assertEqual(provenance["official"]["license"]["spdx"], "MIT-0")
            self.assertFalse(provenance["bundle"]["legacy_version"]["authoritative_for_provenance"])
            self.assertEqual(
                [entry["path"] for entry in provenance["bundle"]["inventory"]["files"]],
                sorted(complete(files)),
            )
            self.assertFalse(
                provenance["decisions"]["corruption_detection_only"]["production_full_allowed"]
            )
            self.assertFalse(provenance["decisions"]["schema_compatibility"]["silent_v1_promotion"])
            self.assertFalse(provenance["decisions"]["active_run_upgrade"]["retarget_existing_runs"])
            self.assertEqual(
                provenance["decisions"]["host_projection"]["selection"],
                "host-adapter-contract",
            )
            self.assertEqual((root / "aidlc-rules" / "BUNDLE_VERSION").read_text(), "1\n")
            self.assertEqual((root / "aidlc-rules" / "LICENSE").read_bytes(), LICENSE)
            manifest = json.loads((root / "aidlc-rules" / "manifest.json").read_text(encoding="utf-8"))
            schema = json.loads((ROOT / "schemas" / "official-aidlc-pack.schema.json").read_text(encoding="utf-8"))
            jsonschema.Draft202012Validator(schema).validate(manifest)
            self.assertEqual(manifest["schema_version"], "2")
            self.assertEqual(manifest["official"]["commit"], COMMIT)
            self.assertEqual(
                set(manifest["required_capabilities"]["requirements"]),
                set(installer.REQUIRED_REQUIREMENTS_CAPABILITIES),
            )
            declared = {entry["path"] for entry in manifest["integrity"]["files"]}
            actual = {
                path.relative_to(root / "aidlc-rules").as_posix()
                for path in (root / "aidlc-rules").rglob("*")
                if path.is_file() and path.name != "manifest.json"
            }
            self.assertEqual(declared, actual)

    def test_replaces_only_verified_content_mismatch(self) -> None:
        official = {CORE: b"# Official flow\n", DETAIL: b"# Requirements\n"}
        current = {CORE: b"# stale flow\n", DETAIL: official[DETAIL]}
        with tempfile.TemporaryDirectory() as temp:
            root = Path(temp)
            seed_checkout(root, current)
            unchanged_inode = (root / "aidlc-rules" / DETAIL).stat().st_ino

            result = prepare(root, official)

            self.assertEqual(result["replaced_files"], [CORE])
            self.assertEqual((root / "aidlc-rules" / CORE).read_bytes(), official[CORE])
            self.assertEqual((root / "aidlc-rules" / DETAIL).stat().st_ino, unchanged_inode)

    def test_adds_only_verified_missing_official_paths(self) -> None:
        resilient = "aws-aidlc-rule-details/extensions/resiliency/baseline/resiliency-baseline.md"
        current = {CORE: b"# Official flow\n", DETAIL: b"# Requirements\n"}
        official = {**current, resilient: b"# Resiliency baseline\n"}
        with tempfile.TemporaryDirectory() as temp:
            root = Path(temp)
            seed_checkout(root, current)

            result = prepare(root, official)

            self.assertEqual(result["added_files"], [resilient])
            self.assertEqual(result["replaced_files"], [])
            self.assertEqual((root / "aidlc-rules" / resilient).read_bytes(), official[resilient])

    def test_dry_run_verifies_without_writing(self) -> None:
        official = {CORE: b"# Official flow\n", DETAIL: b"# Requirements\n"}
        current = {CORE: b"# stale flow\n", DETAIL: official[DETAIL]}
        with tempfile.TemporaryDirectory() as temp:
            root = Path(temp)
            seed_checkout(root, current)

            result = prepare(root, official, dry_run=True)

            self.assertEqual(result["state"], "verified")
            self.assertEqual((root / "aidlc-rules" / CORE).read_bytes(), current[CORE])
            self.assertFalse((root / "aidlc-rules" / "PROVENANCE.json").exists())
            self.assertFalse((root / "aidlc-rules" / "manifest.json").exists())

    def test_rejects_incomplete_inventory_without_partial_writes(self) -> None:
        current = {CORE: b"# Official flow\n", DETAIL: b"# Requirements\n"}
        incomplete = {
            CORE: current[CORE],
            "aws-aidlc-rule-details/common/content-validation.md": b"# Different official path\n",
        }
        with tempfile.TemporaryDirectory() as temp:
            root = Path(temp)
            seed_checkout(root, current)

            with self.assertRaisesRegex(ValueError, "will not delete or relabel"):
                prepare(root, incomplete)

            self.assertEqual((root / "aidlc-rules" / DETAIL).read_bytes(), current[DETAIL])
            self.assertFalse((root / "aidlc-rules" / "PROVENANCE.json").exists())

    def test_rejects_untrusted_commit_or_license_before_writing(self) -> None:
        files = {CORE: b"# Official flow\n", DETAIL: b"# Requirements\n"}
        with tempfile.TemporaryDirectory() as temp:
            root = Path(temp)
            seed_checkout(root, files)

            with self.assertRaisesRegex(ValueError, "full lowercase"):
                prepare(root, files, commit="e49341d")
            with self.assertRaisesRegex(ValueError, "MIT-0"):
                prepare(root, files, license_bytes=b"unknown license\n")

            self.assertFalse((root / "aidlc-rules" / "PROVENANCE.json").exists())

    def test_rejects_symlinked_checkout_rule(self) -> None:
        files = {CORE: b"# Official flow\n", DETAIL: b"# Requirements\n"}
        with tempfile.TemporaryDirectory() as temp:
            root = Path(temp)
            seed_checkout(root, files)
            target = root / "aidlc-rules" / DETAIL
            target.unlink()
            target.symlink_to(root / "aidlc-rules" / CORE)

            with self.assertRaisesRegex(ValueError, "symbolic link"):
                prepare(root, files)

            self.assertFalse((root / "aidlc-rules" / "PROVENANCE.json").exists())

    def test_transaction_rolls_back_every_replaced_target(self) -> None:
        official = {CORE: b"# Official flow\n", DETAIL: b"# Requirements\n"}
        current = {CORE: b"# stale flow\n", DETAIL: official[DETAIL]}
        with tempfile.TemporaryDirectory() as temp:
            root = Path(temp)
            seed_checkout(root, current)
            calls = 0

            def fail_second_replace(source: str, destination: str) -> None:
                nonlocal calls
                calls += 1
                if calls == 2:
                    raise OSError("simulated interrupted transaction")
                os.replace(source, destination)

            with self.assertRaisesRegex(OSError, "simulated"):
                prepare(root, official, replace=fail_second_replace)

            self.assertEqual((root / "aidlc-rules" / CORE).read_bytes(), current[CORE])
            self.assertEqual((root / "aidlc-rules" / DETAIL).read_bytes(), current[DETAIL])
            self.assertFalse((root / "aidlc-rules" / "PROVENANCE.json").exists())
            self.assertFalse((root / "aidlc-rules" / "LICENSE").exists())
            self.assertFalse((root / "aidlc-rules" / "BUNDLE_VERSION").exists())
            self.assertFalse((root / "aidlc-rules" / "manifest.json").exists())

    def test_prepares_same_manifest_offline_from_verified_phase0_inputs(self) -> None:
        files = {CORE: b"# Official flow\n", DETAIL: b"# Requirements\n"}
        with tempfile.TemporaryDirectory() as temp:
            root = Path(temp)
            seed_checkout(root, files)
            prepare(root, files)
            manifest_path = root / "aidlc-rules" / "manifest.json"
            expected = manifest_path.read_bytes()
            manifest_path.unlink()

            with mock.patch.object(installer, "fetch", side_effect=AssertionError("network must not be used")):
                result = installer.prepare_bundle_manifest(root)

            self.assertEqual(result["state"], "prepared")
            self.assertEqual(manifest_path.read_bytes(), expected)
            self.assertEqual(result["manifest_file_count"], len(complete(files)) + 4)

    def test_offline_manifest_preparation_fails_closed_on_phase0_drift(self) -> None:
        files = {CORE: b"# Official flow\n", DETAIL: b"# Requirements\n"}
        with tempfile.TemporaryDirectory() as temp:
            root = Path(temp)
            seed_checkout(root, files)
            prepare(root, files)
            manifest_path = root / "aidlc-rules" / "manifest.json"
            manifest_path.unlink()
            (root / "aidlc-rules" / CORE).write_text("# altered\n", encoding="utf-8")

            with self.assertRaisesRegex(ValueError, "do not match the verified Phase 0 provenance"):
                installer.prepare_bundle_manifest(root)

            self.assertFalse(manifest_path.exists())


if __name__ == "__main__":
    unittest.main()
