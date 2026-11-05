from __future__ import annotations

import hashlib
import json
import os
import shutil
import tempfile
import threading
import time
import unittest
from concurrent.futures import ThreadPoolExecutor
from pathlib import Path
from unittest import mock

from tailtrail.aidlc_bundle import (
    BindingInputs,
    LegacyRunInputs,
    ProjectionInputs,
    RecoveryInputs,
    ResolverInputs,
    StatusInputs,
    bind_run,
    provision,
    recover_staging,
    resolve,
    resolve_bound_run,
    resolve_legacy_run,
    status,
)


ROOT = Path(__file__).resolve().parents[1]
BUNDLE_SOURCE = ROOT / "aidlc-rules"


def sha256(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def copy_bundle(destination: Path) -> Path:
    shutil.copytree(BUNDLE_SOURCE, destination)
    return destination


def write_module(path: Path) -> Path:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text("# resolver execution marker\n", encoding="utf-8")
    return path


def bundle_files(bundle: Path) -> dict[str, dict[str, object]]:
    return {
        path.relative_to(bundle).as_posix(): {
            "sha256": sha256(path),
            "size": path.stat().st_size,
            "owner": "tailtrail",
            "transaction_id": "tx-test",
        }
        for path in sorted(bundle.rglob("*"))
        if path.is_file()
    }


def source_checkout(root: Path) -> Path:
    module = write_module(root / "tailtrail" / "aidlc_bundle.py")
    (root / "pyproject.toml").write_text("[project]\nname='fixture'\n", encoding="utf-8")
    (root / "package-manifest.json").write_text(
        json.dumps({"required_directories": ["aidlc-rules"]}) + "\n",
        encoding="utf-8",
    )
    copy_bundle(root / "aidlc-rules")
    return module


def installed_package(root: Path) -> tuple[Path, Path]:
    package = root / "tailtrail"
    module = write_module(package / "aidlc_bundle.py")
    bundle = copy_bundle(package / "aidlc-rules")
    (package / "package-manifest.json").write_text(
        json.dumps({"required_directories": ["aidlc-rules"]}) + "\n",
        encoding="utf-8",
    )
    inventory = {
        path.relative_to(package).as_posix(): sha256(path)
        for path in sorted(package.rglob("*"))
        if path.is_file()
    }
    integrity = {"schema_version": "1", "algorithm": "sha256", "files": inventory}
    (package / "package-integrity.json").write_text(
        json.dumps(integrity, indent=2, sort_keys=True) + "\n",
        encoding="utf-8",
    )
    return module, bundle


def managed_payload(root: Path, host: str = "codex") -> tuple[Path, Path, Path]:
    version = "1.1.0"
    install_root = root / ".tailtrail" / "install"
    shared = install_root / "payload" / "common" / version
    module = write_module(shared / "tailtrail" / "aidlc_bundle.py")
    bundle = copy_bundle(shared / "aidlc-rules")
    files = {
        f".tailtrail/install/payload/common/{version}/aidlc-rules/{relative}": record
        for relative, record in bundle_files(bundle).items()
    }
    ownership = {
        "schema_version": "1",
        "tool": "tailtrail",
        "version": version,
        "adapter_version": "v1",
        "host": host,
        "profile": "extended",
        "target": root.as_posix(),
        "installed_at": 1,
        "transaction_id": "tx-test",
        "files": files,
        "migrations": [],
        "ownership": "tailtrail-managed",
        "backups": [],
    }
    manifest = install_root / "manifests" / f"{host}.json"
    manifest.parent.mkdir(parents=True)
    manifest.write_text(json.dumps(ownership, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    return module, shared, manifest


class AidlcBundleResolverTests(unittest.TestCase):
    def test_source_checkout_resolves_independently_of_current_working_directory(self) -> None:
        with tempfile.TemporaryDirectory() as temp, tempfile.TemporaryDirectory() as unrelated:
            root = Path(temp)
            module = source_checkout(root)
            previous = Path.cwd()
            try:
                os.chdir(unrelated)
                result = resolve(ResolverInputs(host="codex", module_path=module, environment={}))
            finally:
                os.chdir(previous)

        self.assertEqual(result["state"], "ready")
        self.assertEqual(result["resource_provider"], "source-checkout")
        self.assertEqual(result["trust_posture"], "development-local")
        self.assertEqual(result["effective_mode"], "full")
        self.assertFalse(result["network_used"])
        self.assertTrue(result["package_integrity_fingerprint"].startswith("sha256:"))
        self.assertEqual(result["issues"], [])

    def test_installed_package_requires_exact_outer_and_inner_integrity(self) -> None:
        with tempfile.TemporaryDirectory() as temp:
            module, bundle = installed_package(Path(temp))
            result = resolve(ResolverInputs(host="copilot", module_path=module, environment={}))
            (bundle / "aws-aidlc-rules" / "core-workflow.md").write_text("altered\n", encoding="utf-8")
            altered = resolve(ResolverInputs(host="copilot", module_path=module, environment={}))

        self.assertEqual(result["state"], "ready")
        self.assertEqual(result["resource_provider"], "installed-package")
        self.assertEqual(result["trust_posture"], "corruption-detection-only")
        self.assertEqual(altered["state"], "blocked")
        self.assertIn("hash-mismatch", {item["category"] for item in altered["issues"]})
        self.assertIn("outer-hash-mismatch", {item["category"] for item in altered["issues"]})

    def test_managed_payload_is_bound_to_versioned_ownership_manifest(self) -> None:
        with tempfile.TemporaryDirectory() as temp:
            module, shared, manifest = managed_payload(Path(temp))
            result = resolve(
                ResolverInputs(
                    host="codex",
                    module_path=module,
                    managed_shared_root=shared,
                    managed_ownership_manifest=manifest,
                    environment={},
                )
            )
            ownership = json.loads(manifest.read_text(encoding="utf-8"))
            key = next(value for value in ownership["files"] if value.endswith("/LICENSE"))
            ownership["files"][key]["sha256"] = "0" * 64
            manifest.write_text(json.dumps(ownership), encoding="utf-8")
            altered = resolve(
                ResolverInputs(
                    host="codex",
                    module_path=module,
                    managed_shared_root=shared,
                    managed_ownership_manifest=manifest,
                    environment={},
                )
            )

        self.assertEqual(result["state"], "ready")
        self.assertEqual(result["resource_provider"], "managed-payload")
        self.assertEqual(result["trust_posture"], "corruption-detection-only")
        self.assertEqual(altered["state"], "blocked")
        self.assertIn("outer-hash-mismatch", {item["category"] for item in altered["issues"]})

    def test_only_exact_bound_identity_receipt_elevates_release_trust(self) -> None:
        with tempfile.TemporaryDirectory() as temp:
            module, _ = installed_package(Path(temp))
            baseline = resolve(ResolverInputs(host="claude", module_path=module, environment={}))
            unbound = resolve(
                ResolverInputs(
                    host="claude",
                    module_path=module,
                    artifact_identity_receipt={"identity_verified": True, "payload_fingerprint": "sha256:" + "0" * 64},
                    environment={},
                )
            )
            verified = resolve(
                ResolverInputs(
                    host="claude",
                    module_path=module,
                    artifact_identity_receipt={
                        "receipt_id": "release-fixture",
                        "identity_verified": True,
                        "payload_fingerprint": baseline["package_integrity_fingerprint"],
                    },
                    environment={},
                )
            )

        self.assertEqual(unbound["artifact_identity_status"], "unbound")
        self.assertEqual(unbound["trust_posture"], "corruption-detection-only")
        self.assertEqual(verified["artifact_identity_status"], "verified")
        self.assertEqual(verified["artifact_identity_receipt"], "release-fixture")
        self.assertEqual(verified["trust_posture"], "authenticated-release")

    def test_receipt_fingerprint_is_stable_and_binds_identity(self) -> None:
        with tempfile.TemporaryDirectory() as temp:
            module = source_checkout(Path(temp))
            first = resolve(ResolverInputs(host="codex", module_path=module, environment={}))
            second = resolve(ResolverInputs(host="codex", module_path=module, environment={}))

        self.assertEqual(first, second)
        self.assertTrue(first["receipt_fingerprint"].startswith("sha256:"))
        self.assertEqual(first["official_source"], "https://github.com/awslabs/aidlc-workflows")
        self.assertEqual(len(first["official_commit"]), 40)

    def test_legacy_v1_and_unsafe_symlink_fail_closed_without_mutation(self) -> None:
        with tempfile.TemporaryDirectory() as temp:
            root = Path(temp)
            module = source_checkout(root)
            manifest = root / "aidlc-rules" / "manifest.json"
            original = manifest.read_bytes()
            manifest.write_text(json.dumps({"schema_version": "1", "type": "tailtrail-official-aidlc-pack"}), encoding="utf-8")
            legacy = resolve(ResolverInputs(host="codex", module_path=module, environment={}))
            self.assertEqual(manifest.read_text(encoding="utf-8"), json.dumps({"schema_version": "1", "type": "tailtrail-official-aidlc-pack"}))
            manifest.write_bytes(original)
            link = root / "aidlc-rules" / "unsafe-link"
            try:
                link.symlink_to(root / "pyproject.toml")
            except (OSError, NotImplementedError):
                self.skipTest("symbolic links are unavailable")
            unsafe = resolve(ResolverInputs(host="codex", module_path=module, environment={}))

        self.assertEqual(legacy["state"], "blocked")
        self.assertIn("incompatible-schema", {item["category"] for item in legacy["issues"]})
        self.assertEqual(unsafe["state"], "blocked")
        self.assertIn("unsafe-path", {item["category"] for item in unsafe["issues"]})

    def test_ambiguous_complete_provider_context_fails_closed(self) -> None:
        with tempfile.TemporaryDirectory() as temp:
            root = Path(temp)
            module = source_checkout(root)
            package = root / "tailtrail"
            copy_bundle(package / "aidlc-rules")
            (package / "package-integrity.json").write_text(
                json.dumps({"schema_version": "1", "algorithm": "sha256", "files": {}}),
                encoding="utf-8",
            )
            result = resolve(ResolverInputs(host="codex", module_path=module, environment={}))

        self.assertEqual(result["state"], "blocked")
        self.assertIn("ambiguous-provider", {item["category"] for item in result["issues"]})

    def test_resolution_never_uses_network(self) -> None:
        with tempfile.TemporaryDirectory() as temp:
            module = source_checkout(Path(temp))
            with mock.patch("urllib.request.urlopen", side_effect=AssertionError("network access")) as urlopen:
                result = resolve(ResolverInputs(host="codex", module_path=module, environment={}))

        self.assertEqual(result["state"], "ready")
        urlopen.assert_not_called()

    def test_managed_provider_must_own_the_running_module(self) -> None:
        with tempfile.TemporaryDirectory() as temp:
            root = Path(temp)
            module = source_checkout(root / "source")
            _, shared, manifest = managed_payload(root / "target")
            result = resolve(
                ResolverInputs(
                    host="codex",
                    module_path=module,
                    managed_shared_root=shared,
                    managed_ownership_manifest=manifest,
                    environment={},
                )
            )

        self.assertEqual(result["state"], "blocked")
        self.assertIn("ambiguous-provider", {item["category"] for item in result["issues"]})

    def _ready_projection(self, root: Path, *, project_name: str = "project") -> tuple[dict[str, object], Path, Path]:
        source = root / "source"
        module = source_checkout(source)
        receipt = resolve(ResolverInputs(host="codex", module_path=module, environment={}))
        self.assertEqual(receipt["state"], "ready")
        project = root / project_name
        project.mkdir(parents=True)
        return receipt, source, project

    def test_atomic_projection_creates_closed_pack_receipt_and_future_selector(self) -> None:
        with tempfile.TemporaryDirectory() as temp:
            receipt, source, project = self._ready_projection(Path(temp), project_name="deep/project/root")
            source_before = bundle_files(source / "aidlc-rules")
            result = provision(ProjectionInputs(receipt, project))
            pack = project / result["pack_path"]
            selector = json.loads((project / ".tailtrail/official-aidlc/current.json").read_text(encoding="utf-8"))
            projection = json.loads((pack / "projection-receipt.json").read_text(encoding="utf-8"))
            projected = {
                key: value for key, value in bundle_files(pack).items()
                if key != "projection-receipt.json"
            }

        self.assertEqual(result["state"], "ready")
        self.assertEqual(result["status"], "created")
        self.assertFalse(result["network_used"])
        self.assertEqual(selector["pack_fingerprint"], result["pack_fingerprint"])
        self.assertEqual(projection["source_resolution_fingerprint"], receipt["receipt_fingerprint"])
        self.assertEqual(projection["pack_fingerprint"], result["pack_fingerprint"])
        self.assertEqual(projected, source_before)

    def test_repeat_projection_reuses_without_pack_or_selector_churn(self) -> None:
        with tempfile.TemporaryDirectory() as temp:
            receipt, _, project = self._ready_projection(Path(temp))
            first = provision(ProjectionInputs(receipt, project))
            pack = project / first["pack_path"]
            selector_path = project / ".tailtrail/official-aidlc/current.json"
            before = {
                path.relative_to(project).as_posix(): (path.stat().st_mtime_ns, sha256(path))
                for path in [*sorted(pack.rglob("*")), selector_path]
                if path.is_file()
            }
            time.sleep(0.002)
            second = provision(ProjectionInputs(receipt, project))
            after = {
                path.relative_to(project).as_posix(): (path.stat().st_mtime_ns, sha256(path))
                for path in [*sorted(pack.rglob("*")), selector_path]
                if path.is_file()
            }

        self.assertEqual(first["status"], "created")
        self.assertEqual(second["status"], "reused")
        self.assertEqual(first["pack_fingerprint"], second["pack_fingerprint"])
        self.assertEqual(before, after)

    def test_two_callers_create_once_and_reuse_once(self) -> None:
        with tempfile.TemporaryDirectory() as temp:
            receipt, _, project = self._ready_projection(Path(temp))
            barrier = threading.Barrier(2)

            def call() -> dict[str, object]:
                barrier.wait(timeout=5)
                return provision(ProjectionInputs(receipt, project, lock_timeout_seconds=5.0))

            with ThreadPoolExecutor(max_workers=2) as executor:
                results = list(executor.map(lambda _value: call(), range(2)))

        self.assertEqual(sorted(result["status"] for result in results), ["created", "reused"])
        self.assertEqual(len({result["pack_fingerprint"] for result in results}), 1)

    def test_altered_destination_and_conflicting_selector_fail_without_overwrite(self) -> None:
        with tempfile.TemporaryDirectory() as temp:
            receipt, _, project = self._ready_projection(Path(temp))
            created = provision(ProjectionInputs(receipt, project))
            pack = project / created["pack_path"]
            license_path = pack / "LICENSE"
            license_path.write_text("altered destination\n", encoding="utf-8")
            altered_bytes = license_path.read_bytes()
            altered = provision(ProjectionInputs(receipt, project))
            self.assertEqual(license_path.read_bytes(), altered_bytes)

            second_project = project.parent / "selector-conflict"
            second_project.mkdir()
            first_for_second = provision(ProjectionInputs(receipt, second_project))
            selector_path = second_project / ".tailtrail/official-aidlc/current.json"
            selector = json.loads(selector_path.read_text(encoding="utf-8"))
            selector["pack_fingerprint"] = "sha256:" + "f" * 64
            selector["pack_path"] = ".tailtrail/official-aidlc/packs/" + "f" * 64
            selector.pop("selector_fingerprint")
            selector["selector_fingerprint"] = "sha256:" + hashlib.sha256(
                json.dumps(selector, sort_keys=True, separators=(",", ":")).encode("utf-8")
            ).hexdigest()
            selector_path.write_text(json.dumps(selector, indent=2, sort_keys=True) + "\n", encoding="utf-8")
            conflict = provision(ProjectionInputs(receipt, second_project))

        self.assertEqual(altered["state"], "blocked")
        self.assertIn("altered-destination", {item["category"] for item in altered["issues"]})
        self.assertEqual(first_for_second["status"], "created")
        self.assertEqual(conflict["state"], "blocked")
        self.assertIn("selector-conflict", {item["category"] for item in conflict["issues"]})

    def test_unsafe_target_and_unknown_rename_error_fail_closed(self) -> None:
        with tempfile.TemporaryDirectory() as temp:
            root = Path(temp)
            receipt, _, project = self._ready_projection(root)
            outside = root / "outside"
            outside.mkdir()
            try:
                (project / ".tailtrail").symlink_to(outside, target_is_directory=True)
            except (OSError, NotImplementedError):
                self.skipTest("symbolic links are unavailable")
            unsafe = provision(ProjectionInputs(receipt, project))
            self.assertEqual(list(outside.iterdir()), [])

            rename_project = root / "rename-error"
            rename_project.mkdir()
            with mock.patch("tailtrail.aidlc_bundle.os.rename", side_effect=OSError(5, "unknown rename failure")) as rename:
                rename_failure = provision(ProjectionInputs(receipt, rename_project))
            destination_exists = (rename_project / rename_failure["pack_path"]).exists()

        self.assertEqual(unsafe["state"], "blocked")
        self.assertIn("unsafe-target", {item["category"] for item in unsafe["issues"]})
        self.assertEqual(rename_failure["state"], "blocked")
        self.assertEqual(rename.call_count, 1)
        self.assertFalse(destination_exists)

    def test_stale_staging_is_reported_and_removed_only_by_explicit_recovery(self) -> None:
        with tempfile.TemporaryDirectory() as temp:
            receipt, _, project = self._ready_projection(Path(temp))

            def crash(checkpoint: str) -> None:
                if checkpoint == "after-staging-marker":
                    raise SystemExit("simulated process crash")

            with self.assertRaisesRegex(SystemExit, "simulated process crash"):
                provision(ProjectionInputs(receipt, project, fault=crash))
            staging_root = project / ".tailtrail/official-aidlc/packs"
            stale_path = next(path for path in staging_root.iterdir() if path.name.startswith(".staging-"))
            ordinary = provision(ProjectionInputs(receipt, project))
            self.assertTrue(stale_path.is_dir())
            stale = next(row for row in ordinary["stale_staging"] if row["path"] == stale_path.name)
            recovered = recover_staging(RecoveryInputs(
                project,
                staging_name=stale_path.name,
                staging_fingerprint=stale["staging_fingerprint"],
            ))
            stale_exists_after_recovery = stale_path.exists()

        self.assertEqual(ordinary["status"], "created")
        self.assertEqual(recovered["state"], "recovered")
        self.assertFalse(stale_exists_after_recovery)

    def test_lock_timeout_is_bounded_and_does_not_create_partial_pack(self) -> None:
        with tempfile.TemporaryDirectory() as temp:
            receipt, _, project = self._ready_projection(Path(temp))
            locked = threading.Event()
            release = threading.Event()

            def hold(checkpoint: str) -> None:
                if checkpoint == "after-lock":
                    locked.set()
                    release.wait(timeout=5)

            with ThreadPoolExecutor(max_workers=1) as executor:
                future = executor.submit(provision, ProjectionInputs(receipt, project, fault=hold))
                self.assertTrue(locked.wait(timeout=5))
                timed_out = provision(ProjectionInputs(receipt, project, lock_timeout_seconds=0.05))
                release.set()
                created = future.result(timeout=5)

        self.assertEqual(timed_out["state"], "blocked")
        self.assertIn("lock-timeout", {item["category"] for item in timed_out["issues"]})
        self.assertEqual(created["status"], "created")

    def test_frozen_run_binding_ignores_later_future_selector_changes(self) -> None:
        with tempfile.TemporaryDirectory() as temp:
            receipt, _, project = self._ready_projection(Path(temp))
            projection = provision(ProjectionInputs(receipt, project))
            bound = bind_run(BindingInputs(project, "run-active", projection))
            selector_path = project / ".tailtrail/official-aidlc/current.json"
            selector = json.loads(selector_path.read_text(encoding="utf-8"))
            selector["pack_fingerprint"] = "sha256:" + "f" * 64
            selector["pack_path"] = ".tailtrail/official-aidlc/packs/" + "f" * 64
            selector.pop("selector_fingerprint")
            selector["selector_fingerprint"] = "sha256:" + hashlib.sha256(
                json.dumps(selector, sort_keys=True, separators=(",", ":")).encode("utf-8")
            ).hexdigest()
            selector_path.write_text(json.dumps(selector, indent=2, sort_keys=True) + "\n", encoding="utf-8")
            resolved = resolve_bound_run(project, "run-active")

        self.assertEqual(bound["state"], "ready")
        self.assertEqual(bound["status"], "created")
        self.assertEqual(resolved["state"], "ready")
        self.assertEqual(resolved["pack_fingerprint"], projection["pack_fingerprint"])
        self.assertEqual(resolved["binding_fingerprint"], bound["binding_fingerprint"])
        self.assertFalse(resolved["selector_consulted"])

    def test_binding_reuses_exact_identity_and_rejects_conflicting_or_unsafe_input(self) -> None:
        with tempfile.TemporaryDirectory() as temp:
            receipt, _, project = self._ready_projection(Path(temp))
            projection = provision(ProjectionInputs(receipt, project))
            first = bind_run(BindingInputs(project, "run-one", projection))
            binding_path = project / first["binding_path"]
            before = binding_path.read_bytes()
            reused = bind_run(BindingInputs(project, "run-one", projection))
            conflicting_projection = dict(projection)
            conflicting_projection["pack_fingerprint"] = "sha256:" + "e" * 64
            conflict = bind_run(BindingInputs(project, "run-one", conflicting_projection))
            unsafe = bind_run(BindingInputs(project, "../outside", projection))
            after = binding_path.read_bytes()

        self.assertEqual(reused["status"], "reused")
        self.assertEqual(conflict["state"], "blocked")
        self.assertIn("invalid-projection", {item["category"] for item in conflict["issues"]})
        self.assertEqual(unsafe["state"], "blocked")
        self.assertIn("unsafe-run-id", {item["category"] for item in unsafe["issues"]})
        self.assertEqual(before, after)

    def test_altered_bound_pack_fails_closed_without_rewriting_binding(self) -> None:
        with tempfile.TemporaryDirectory() as temp:
            receipt, _, project = self._ready_projection(Path(temp))
            projection = provision(ProjectionInputs(receipt, project))
            bound = bind_run(BindingInputs(project, "run-altered", projection))
            binding_path = project / bound["binding_path"]
            before = binding_path.read_bytes()
            pack = project / projection["pack_path"]
            (pack / "LICENSE").write_text("altered after binding\n", encoding="utf-8")
            resolved = resolve_bound_run(project, "run-altered")
            after = binding_path.read_bytes()

        self.assertEqual(resolved["state"], "blocked")
        self.assertIn("altered-bound-pack", {item["category"] for item in resolved["issues"]})
        self.assertEqual(before, after)

    def test_legacy_v1_continuation_requires_existing_bridge_activation_and_never_mints_binding(self) -> None:
        with tempfile.TemporaryDirectory() as temp:
            project = Path(temp)
            pack = project / ".tailtrail/official-aidlc"
            pack.mkdir(parents=True)
            (pack / "LICENSE").write_text("MIT-0\n", encoding="utf-8")
            (pack / "core-workflow.md").write_text("# legacy workflow\n", encoding="utf-8")
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
                        {"path": name, "sha256": sha256(pack / name)}
                        for name in ("LICENSE", "core-workflow.md")
                    ],
                },
            }
            (pack / "manifest.json").write_text(json.dumps(manifest), encoding="utf-8")
            bridge = {
                "schema_version": "1",
                "type": "tailtrail-official-aidlc-bridge",
                "tailtrail_run_id": "legacy-run",
                "compatibility_manifest": ".tailtrail/official-aidlc/manifest.json",
            }
            activation = {
                "schema_version": "1",
                "type": "tailtrail-official-aidlc-bridge-activation",
                "tailtrail_run_id": "legacy-run",
                "state": "approved-awaiting-host-attachment",
                "bridge_artifact": ".tailtrail/runs/legacy-run/aidlc-official/bridge-v1.json",
            }
            authority = project / ".tailtrail/runs/legacy-run/aidlc-official"
            authority.mkdir(parents=True)
            (authority / "bridge-v1.json").write_text(json.dumps(bridge), encoding="utf-8")
            (authority / "activation-v1.json").write_text(json.dumps(activation), encoding="utf-8")
            continued = resolve_legacy_run(LegacyRunInputs(project, "legacy-run"))
            denied = resolve_legacy_run(LegacyRunInputs(project, "new-run"))
            binding_root_exists = (pack / "run-bindings").exists()

        self.assertEqual(continued["state"], "legacy-read-only")
        self.assertFalse(continued["can_authorize_new_full"])
        self.assertEqual(denied["state"], "blocked")
        self.assertFalse(binding_root_exists)

    def test_status_is_read_only_and_reports_projection_binding_and_provision_need(self) -> None:
        with tempfile.TemporaryDirectory() as temp:
            root = Path(temp)
            receipt, _, project = self._ready_projection(root)
            empty = root / "empty-project"
            empty.mkdir()
            before_empty = list(empty.rglob("*"))
            absent = status(StatusInputs(empty, resolution_receipt=receipt, run_id="run-status"))
            after_empty = list(empty.rglob("*"))

            projection = provision(ProjectionInputs(receipt, project))
            bound = bind_run(BindingInputs(project, "run-status", projection))
            tracked = {
                path.relative_to(project).as_posix(): (path.stat().st_mtime_ns, sha256(path))
                for path in project.rglob("*") if path.is_file()
            }
            ready = status(StatusInputs(project, resolution_receipt=receipt, run_id="run-status"))
            after = {
                path.relative_to(project).as_posix(): (path.stat().st_mtime_ns, sha256(path))
                for path in project.rglob("*") if path.is_file()
            }

        self.assertEqual(absent["state"], "provision-required")
        self.assertTrue(absent["provisioning_required"])
        self.assertEqual(before_empty, after_empty)
        self.assertEqual(ready["state"], "ready")
        self.assertFalse(ready["provisioning_required"])
        self.assertEqual(ready["frozen_run"]["binding_fingerprint"], bound["binding_fingerprint"])
        self.assertEqual(tracked, after)


if __name__ == "__main__":
    unittest.main()
