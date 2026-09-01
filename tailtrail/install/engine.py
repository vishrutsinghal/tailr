"""Recoverable, conflict-aware transactional installer engine."""

from __future__ import annotations

import hashlib
import json
import os
import shutil
import stat
import tempfile
import time
import uuid
from contextlib import contextmanager
from pathlib import Path
from typing import Callable, Iterator

from ..hosts.contracts import adapter_version
from ..hosts.diagnostics import diagnose

from .catalog import HOSTS, PROFILES, payload_version, payloads, source_root
from .models import InstallPlan, InstallResult, PlanEntry


STATE_SCHEMA = "1"
MANIFEST_SCHEMA = "1"
BACKUP_RETENTION = 5


class InstallFailure(RuntimeError):
    """A categorical installer failure safe to present to users."""

    def __init__(self, code: str, message: str):
        super().__init__(message)
        self.code = code


class UncleanInterruption(BaseException):
    """Test/support hook representing termination before cleanup can run."""


def _hash_bytes(data: bytes) -> str:
    return hashlib.sha256(data).hexdigest()


def _hash_file(path: Path) -> str:
    return _hash_bytes(path.read_bytes())


def _atomic_bytes(path: Path, data: bytes) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    descriptor, temporary = tempfile.mkstemp(prefix=f".{path.name}.", dir=path.parent)
    try:
        with os.fdopen(descriptor, "wb") as stream:
            stream.write(data)
            stream.flush()
            os.fsync(stream.fileno())
        os.replace(temporary, path)
    finally:
        if os.path.exists(temporary):
            os.unlink(temporary)


def _atomic_json(path: Path, payload: object) -> None:
    _atomic_bytes(path, (json.dumps(payload, indent=2, sort_keys=True) + "\n").encode("utf-8"))


class InstallEngine:
    def __init__(self, target: Path, *, package_root: Path | None = None, fault: Callable[[str], None] | None = None):
        self.requested_target = Path(target)
        self.package_root = package_root or source_root()
        self.version = payload_version(self.package_root)
        self.fault = fault or (lambda _checkpoint: None)
        self.target = self._validate_target(self.requested_target)
        self.state_root = self.target / ".tailtrail" / "install"
        self.manifests_root = self.state_root / "manifests"
        self.transactions_root = self.state_root / "transactions"
        self.lock_path = self.state_root / "lifecycle.lock"
        self.journal_path = self.state_root / "journal-v1.jsonl"
        for state_path in (self.target / ".tailtrail", self.state_root):
            if state_path.is_symlink():
                raise InstallFailure("unsafe-state", f"installer state path must not be a symlink: {state_path}")

    def _contract_root(self) -> Path:
        return self.package_root if (self.package_root / "adapters" / "host-compatibility-v1.json").is_file() else source_root()

    @staticmethod
    def _validate_target(target: Path) -> Path:
        if not target.exists() or not target.is_dir():
            raise InstallFailure("invalid-target", f"installation target is not an existing directory: {target}")
        if target.is_symlink():
            raise InstallFailure("unsafe-target", f"installation target must not be a symlink: {target}")
        resolved = target.resolve()
        if resolved == Path(resolved.anchor):
            raise InstallFailure("unsafe-target", "installation into a filesystem root is not allowed")
        mode = stat.S_IMODE(resolved.stat().st_mode)
        if mode & 0o222 == 0 or not os.access(resolved, os.W_OK | os.X_OK):
            raise InstallFailure("inaccessible-target", f"installation target is not writable: {resolved}")
        return resolved

    def _manifest_path(self, host: str) -> Path:
        return self.manifests_root / f"{host}.json"

    def installed_hosts(self) -> tuple[str, ...]:
        return tuple(host for host in HOSTS if self._manifest_path(host).is_file())

    def _references_by_other_hosts(self, host: str) -> set[str]:
        references: set[str] = set()
        for other in HOSTS:
            if other == host:
                continue
            manifest = self._load_manifest(other)
            files = (manifest or {}).get("files", {})
            if isinstance(files, dict):
                references.update(files)
        return references

    def _load_manifest(self, host: str) -> dict[str, object] | None:
        path = self._manifest_path(host)
        if not path.exists():
            return None
        if path.is_symlink():
            raise InstallFailure("corrupt-manifest", f"ownership manifest must not be a symlink: {path}")
        try:
            payload = json.loads(path.read_text(encoding="utf-8"))
        except (OSError, json.JSONDecodeError) as error:
            raise InstallFailure("corrupt-manifest", f"cannot read ownership manifest: {error}") from error
        if payload.get("schema_version") != MANIFEST_SCHEMA or payload.get("host") != host or not isinstance(payload.get("files"), dict):
            raise InstallFailure("corrupt-manifest", f"invalid ownership manifest: {path}")
        return payload

    @contextmanager
    def _lock(self) -> Iterator[None]:
        self.state_root.mkdir(parents=True, exist_ok=True)
        payload = {"schema_version": STATE_SCHEMA, "pid": os.getpid(), "created_at": int(time.time())}
        try:
            descriptor = os.open(self.lock_path, os.O_CREAT | os.O_EXCL | os.O_WRONLY, 0o600)
        except FileExistsError:
            try:
                current = json.loads(self.lock_path.read_text(encoding="utf-8"))
                pid = int(current.get("pid", -1))
                os.kill(pid, 0)
            except (OSError, ValueError, json.JSONDecodeError):
                self.lock_path.unlink(missing_ok=True)
                descriptor = os.open(self.lock_path, os.O_CREAT | os.O_EXCL | os.O_WRONLY, 0o600)
            else:
                raise InstallFailure("installer-locked", f"another installer transaction is active (pid {pid})")
        with os.fdopen(descriptor, "w", encoding="utf-8") as stream:
            json.dump(payload, stream, sort_keys=True)
            stream.flush()
            os.fsync(stream.fileno())
        try:
            yield
        finally:
            self.lock_path.unlink(missing_ok=True)

    def _journal(self, transaction_id: str, operation: str, state: str, **extra: object) -> None:
        event = {"schema_version": STATE_SCHEMA, "transaction_id": transaction_id, "operation": operation, "state": state, "at": int(time.time()), **extra}
        self.journal_path.parent.mkdir(parents=True, exist_ok=True)
        with self.journal_path.open("a", encoding="utf-8") as stream:
            stream.write(json.dumps(event, sort_keys=True) + "\n")
            stream.flush()
            os.fsync(stream.fileno())

    def _destination(self, relative: str) -> Path:
        value = Path(relative)
        if value.is_absolute() or not value.parts or any(part in {"", ".", ".."} for part in value.parts):
            raise InstallFailure("unsafe-path", f"unsafe managed path: {relative}")
        destination = self.target / value
        current = self.target
        for part in value.parts[:-1]:
            current = current / part
            if current.is_symlink():
                raise InstallFailure("unsafe-path", f"managed path crosses a symlink: {relative}")
        return destination

    def plan(self, operation: str, host: str, profile: str | None = None, *, force: bool = False) -> InstallPlan:
        if host not in HOSTS:
            raise InstallFailure("unsupported-host", f"supported hosts are: {', '.join(HOSTS)}")
        manifest = self._load_manifest(host)
        selected_profile = profile or str((manifest or {}).get("profile", "core"))
        if selected_profile not in PROFILES:
            raise InstallFailure("unsupported-profile", f"supported profiles are: {', '.join(PROFILES)}")
        if operation not in {"install", "update", "repair"}:
            raise InstallFailure("unsupported-operation", f"cannot plan operation: {operation}")
        previous_files = (manifest or {}).get("files", {})
        assert isinstance(previous_files, dict)
        entries: list[PlanEntry] = []
        conflicts: list[str] = []
        desired: set[str] = set()
        for payload in payloads(host, selected_profile, self.package_root):
            relative = payload.destination
            desired.add(relative)
            destination = self._destination(relative)
            source_hash = _hash_file(payload.source)
            previous = previous_files.get(relative, {})
            previous_hash = previous.get("sha256") if isinstance(previous, dict) else None
            current_hash = _hash_file(destination) if destination.is_file() and not destination.is_symlink() else None
            if destination.exists() and (destination.is_symlink() or not destination.is_file()):
                conflicts.append(relative)
                action = "conflict"
            elif current_hash == source_hash:
                action = "unchanged"
            elif current_hash is None:
                action = "create"
            elif previous_hash and current_hash == previous_hash:
                action = "replace"
            elif force:
                action = "replace-with-backup"
            else:
                conflicts.append(relative)
                action = "conflict"
            entries.append(PlanEntry(relative, source_hash, payload.source.stat().st_size, action, payload.source.as_posix(), current_hash))
        other_references = self._references_by_other_hosts(host)
        removals = tuple(sorted(set(previous_files) - desired - other_references))
        plan_material = json.dumps({"operation": operation, "host": host, "profile": selected_profile, "target": self.target.as_posix(), "entries": [entry.__dict__ for entry in entries], "removals": removals}, sort_keys=True).encode()
        return InstallPlan(STATE_SCHEMA, _hash_bytes(plan_material)[:24], operation, self.version, host, selected_profile, self.target.as_posix(), str(manifest.get("version")) if manifest else None, tuple(entries), tuple(sorted(conflicts)), removals)

    def _transaction_paths(self, transaction_id: str) -> tuple[Path, Path, Path]:
        root = self.transactions_root / transaction_id
        return root, root / "backup", root / "state.json"

    def _snapshot(self, transaction_id: str, plan: InstallPlan, manifest: dict[str, object] | None) -> None:
        root, backup, state = self._transaction_paths(transaction_id)
        root.mkdir(parents=True, exist_ok=False)
        backup.mkdir()
        before: dict[str, str] = {}
        candidates = {entry.path for entry in plan.entries if entry.action in {"replace", "replace-with-backup"}} | set(plan.removals)
        for relative in sorted(candidates):
            path = self._destination(relative)
            if path.is_file() and not path.is_symlink():
                destination = backup / relative
                destination.parent.mkdir(parents=True, exist_ok=True)
                shutil.copy2(path, destination)
                before[relative] = _hash_file(destination)
        if manifest is not None:
            _atomic_json(root / "before-manifest.json", manifest)
        _atomic_json(root / "plan.json", plan.as_dict())
        _atomic_json(state, {"schema_version": STATE_SCHEMA, "state": "prepared", "host": plan.host, "operation": plan.operation, "backups": before, "created": []})

    def _restore_transaction(self, transaction_id: str, *, automatic: bool, force: bool = False) -> tuple[list[str], list[str]]:
        root, backup, state_path = self._transaction_paths(transaction_id)
        if not state_path.is_file():
            raise InstallFailure("unknown-transaction", f"transaction is not available: {transaction_id}")
        state = json.loads(state_path.read_text(encoding="utf-8"))
        plan = json.loads((root / "plan.json").read_text(encoding="utf-8"))
        host = str(plan["host"])
        after_manifest_path = root / "after-manifest.json"
        after_manifest = json.loads(after_manifest_path.read_text(encoding="utf-8")) if after_manifest_path.is_file() else None
        after_files = after_manifest.get("files", {}) if isinstance(after_manifest, dict) else {}
        conflicts: list[str] = []
        restored: list[str] = []
        touched = set(state.get("created", [])) | set(state.get("backups", {}))
        other_references = self._references_by_other_hosts(host)
        for relative in sorted(touched):
            destination = self._destination(relative)
            expected_after = after_files.get(relative, {}).get("sha256") if isinstance(after_files.get(relative), dict) else None
            if destination.exists() and not automatic and not force:
                if expected_after is None or not destination.is_file() or destination.is_symlink() or _hash_file(destination) != expected_after:
                    conflicts.append(relative)
                    continue
            backed_up = backup / relative
            if backed_up.is_file():
                destination.parent.mkdir(parents=True, exist_ok=True)
                os.replace(backed_up, destination)
                restored.append(relative)
            elif relative in other_references:
                continue
            elif destination.is_file() or destination.is_symlink():
                destination.unlink()
                restored.append(relative)
        if conflicts:
            return restored, conflicts
        before_manifest = root / "before-manifest.json"
        manifest_path = self._manifest_path(host)
        if before_manifest.is_file():
            _atomic_bytes(manifest_path, before_manifest.read_bytes())
        else:
            manifest_path.unlink(missing_ok=True)
        state["state"] = "recovered" if automatic else "rolled-back"
        _atomic_json(state_path, state)
        self._journal(transaction_id, str(plan["operation"]), state["state"], host=host)
        return restored, []

    def recover(self) -> list[str]:
        recovered: list[str] = []
        if not self.transactions_root.exists():
            return recovered
        for root in sorted(self.transactions_root.iterdir()):
            state_path = root / "state.json"
            if not state_path.is_file():
                continue
            try:
                state = json.loads(state_path.read_text(encoding="utf-8"))
            except (OSError, json.JSONDecodeError) as error:
                raise InstallFailure("corrupt-transaction", f"cannot recover transaction {root.name}: {error}") from error
            if state.get("state") in {"prepared", "applying", "verifying"}:
                self._restore_transaction(root.name, automatic=True, force=True)
                recovered.append(root.name)
        return recovered

    def apply(self, operation: str, host: str, profile: str | None = None, *, dry_run: bool = False, force: bool = False) -> InstallResult:
        if dry_run:
            if operation in {"update", "repair"} and self._load_manifest(host) is None:
                return InstallResult(operation, "not-installed", self.target.as_posix(), host, profile or "unknown", self.version, issues=[f"{host} is not installed"])
            plan = self.plan(operation, host, profile, force=force)
            result = InstallResult(operation, "dry-run", self.target.as_posix(), host, plan.profile, self.version, plan=plan.as_dict())
            if plan.conflicts:
                result.status = "conflict"
                result.preserved.extend(plan.conflicts)
                result.issues.append("managed-path conflicts require review or --force")
            return result
        with self._lock():
            recovered = self.recover()
            if operation in {"update", "repair"} and self._load_manifest(host) is None:
                return InstallResult(operation, "not-installed", self.target.as_posix(), host, profile or "unknown", self.version, recovered_transactions=recovered, issues=[f"{host} is not installed"])
            plan = self.plan(operation, host, profile, force=force)
            result = InstallResult(operation, "dry-run" if dry_run else "passed", self.target.as_posix(), host, plan.profile, self.version, recovered_transactions=recovered, plan=plan.as_dict())
            if plan.conflicts:
                result.status = "conflict"
                result.preserved.extend(plan.conflicts)
                result.issues.append("managed-path conflicts require review or --force")
                return result
            if dry_run:
                return result
            manifest_before = self._load_manifest(host)
            current_adapter = adapter_version(self._contract_root())
            adapter_current = (manifest_before or {}).get("adapter_version") == current_adapter
            if all(entry.action == "unchanged" for entry in plan.entries) and not plan.removals and adapter_current:
                result.status = "current"
                return result
            transaction_id = f"{int(time.time())}-{uuid.uuid4().hex[:12]}"
            result.transaction_id = transaction_id
            self._snapshot(transaction_id, plan, manifest_before)
            root, _backup, state_path = self._transaction_paths(transaction_id)
            self._journal(transaction_id, operation, "prepared", host=host, plan_id=plan.plan_id)
            state = json.loads(state_path.read_text(encoding="utf-8"))
            staging = root / "staging"
            try:
                state["state"] = "applying"
                _atomic_json(state_path, state)
                for entry in plan.entries:
                    if entry.action == "unchanged":
                        continue
                    source = Path(entry.source)
                    staged = staging / entry.path
                    staged.parent.mkdir(parents=True, exist_ok=True)
                    shutil.copy2(source, staged)
                    if _hash_file(staged) != entry.sha256:
                        raise InstallFailure("corrupt-staging", f"staged hash mismatch: {entry.path}")
                    self.fault(f"staged:{entry.path}")
                    destination = self._destination(entry.path)
                    destination.parent.mkdir(parents=True, exist_ok=True)
                    os.replace(staged, destination)
                    result.changed.append(entry.path)
                    if entry.action == "create":
                        state["created"].append(entry.path)
                    _atomic_json(state_path, state)
                    self.fault(f"applied:{entry.path}")
                for relative in plan.removals:
                    destination = self._destination(relative)
                    previous = (manifest_before or {}).get("files", {}).get(relative, {}) if isinstance((manifest_before or {}).get("files", {}), dict) else {}
                    expected = previous.get("sha256") if isinstance(previous, dict) else None
                    if destination.is_file() and expected and _hash_file(destination) == expected:
                        destination.unlink()
                        result.removed.append(relative)
                    elif destination.exists():
                        result.preserved.append(relative)
                files = {entry.path: {"sha256": entry.sha256, "size": entry.size, "owner": "tailtrail", "transaction_id": transaction_id} for entry in plan.entries}
                previous_adapter = (manifest_before or {}).get("adapter_version")
                migrations = list((manifest_before or {}).get("migrations", []))
                if previous_adapter != current_adapter:
                    migrations.append(f"adapter:{previous_adapter or 'unrecorded'}->{current_adapter}")
                manifest = {"schema_version": MANIFEST_SCHEMA, "tool": "tailtrail", "version": self.version, "adapter_version": current_adapter, "host": host, "profile": plan.profile, "target": self.target.as_posix(), "installed_at": int(time.time()), "transaction_id": transaction_id, "files": files, "migrations": migrations, "ownership": "tailtrail-managed", "backups": sorted(state["backups"])}
                _atomic_json(root / "after-manifest.json", manifest)
                _atomic_json(self._manifest_path(host), manifest)
                state["state"] = "verifying"
                _atomic_json(state_path, state)
                self.fault("before-verify")
                verification = self.verify(host)
                if not verification.ok:
                    raise InstallFailure("verification-failed", "; ".join(verification.issues))
                state["state"] = "complete"
                _atomic_json(state_path, state)
                self._journal(transaction_id, operation, "complete", host=host)
                shutil.rmtree(staging, ignore_errors=True)
                self._prune_transactions(host)
                return result
            except UncleanInterruption:
                # Models SIGKILL/power loss: the durable prepared/applying state
                # is intentionally left for the next command's recovery pass.
                raise
            except BaseException as error:
                restored, conflicts = self._restore_transaction(transaction_id, automatic=True, force=True)
                result.status = "restored"
                result.preserved.extend(conflicts)
                result.issues.append(str(error))
                result.issues.append(f"automatic restoration completed for {len(restored)} path(s)")
                if isinstance(error, (KeyboardInterrupt, SystemExit)):
                    raise
                return result

    def verify(self, host: str) -> InstallResult:
        manifest = self._load_manifest(host)
        result = InstallResult("verify", "passed", self.target.as_posix(), host, str((manifest or {}).get("profile", "unknown")), str((manifest or {}).get("version", self.version)))
        if manifest is None:
            result.status = "not-installed"
            return result
        files = manifest["files"]
        assert isinstance(files, dict)
        for relative, entry in sorted(files.items()):
            path = self._destination(relative)
            expected = entry.get("sha256") if isinstance(entry, dict) else None
            if not path.is_file() or path.is_symlink():
                result.issues.append(f"missing managed file: {relative}")
            elif not expected or _hash_file(path) != expected:
                result.issues.append(f"modified managed file: {relative}")
        if result.issues:
            result.status = "failed"
        return result

    def status(self, host: str) -> InstallResult:
        result = self.verify(host)
        result.operation = "status"
        if result.status == "passed":
            result.status = "current" if result.version == self.version else "update-available"
        return result

    def doctor(self, host: str) -> InstallResult:
        result = self.verify(host)
        result.operation = "doctor"
        manifest = self._load_manifest(host)
        result.diagnostics = diagnose(self.target, host, manifest=manifest, root=self._contract_root())
        result.issues.extend(item for item in result.diagnostics["issues"] if item not in result.issues)
        if result.issues:
            result.status = "failed"
        if result.status == "passed" and self.lock_path.exists():
            result.status = "failed"
            result.issues.append("installer lifecycle lock is unexpectedly present")
        return result

    def rollback(self, transaction_id: str, *, force: bool = False, dry_run: bool = False) -> InstallResult:
        root, _backup, _state = self._transaction_paths(transaction_id)
        if not (root / "plan.json").is_file():
            raise InstallFailure("unknown-transaction", f"transaction is not available: {transaction_id}")
        plan = json.loads((root / "plan.json").read_text(encoding="utf-8"))
        host = str(plan["host"])
        result = InstallResult("rollback", "dry-run" if dry_run else "passed", self.target.as_posix(), host, str(plan["profile"]), str(plan["version"]), transaction_id=transaction_id)
        if dry_run:
            result.plan = plan
            return result
        with self._lock():
            result.recovered_transactions = self.recover()
            restored, conflicts = self._restore_transaction(transaction_id, automatic=False, force=force)
            result.changed.extend(restored)
            result.preserved.extend(conflicts)
            if conflicts:
                result.status = "conflict"
                result.issues.append("rollback preserved user-modified managed files")
            return result

    def uninstall(self, host: str, *, force: bool = False, dry_run: bool = False) -> InstallResult:
        if dry_run:
            manifest = self._load_manifest(host)
            result = InstallResult("uninstall", "dry-run", self.target.as_posix(), host, str((manifest or {}).get("profile", "unknown")), str((manifest or {}).get("version", self.version)))
            if manifest is None:
                result.status = "not-installed"
                return result
            files = manifest["files"]
            assert isinstance(files, dict)
            other_references = self._references_by_other_hosts(host)
            for relative, entry in sorted(files.items()):
                destination = self._destination(relative)
                expected = entry.get("sha256") if isinstance(entry, dict) else None
                if relative in other_references:
                    continue
                if destination.is_file() and not destination.is_symlink() and expected and _hash_file(destination) == expected:
                    result.removed.append(relative)
                elif destination.exists():
                    result.preserved.append(relative)
            if result.preserved and not force:
                result.status = "conflict"
                result.issues.append("uninstall preserved modified managed files")
            return result
        with self._lock():
            recovered = self.recover()
            manifest = self._load_manifest(host)
            result = InstallResult("uninstall", "dry-run" if dry_run else "passed", self.target.as_posix(), host, str((manifest or {}).get("profile", "unknown")), str((manifest or {}).get("version", self.version)), recovered_transactions=recovered)
            if manifest is None:
                result.status = "not-installed"
                return result
            files = manifest["files"]
            assert isinstance(files, dict)
            other_references = self._references_by_other_hosts(host)
            candidates: list[str] = []
            for relative, entry in sorted(files.items()):
                destination = self._destination(relative)
                expected = entry.get("sha256") if isinstance(entry, dict) else None
                if relative in other_references:
                    continue
                if destination.is_file() and not destination.is_symlink() and expected and _hash_file(destination) == expected:
                    candidates.append(relative)
                elif destination.exists():
                    result.preserved.append(relative)
            if result.preserved and not force:
                result.status = "conflict"
                result.issues.append("uninstall preserved modified managed files; rerun with --force to back up and remove them")
                return result
            if dry_run:
                result.removed.extend(candidates)
                return result
            # A forced uninstall still preserves user bytes in a transaction backup.
            transaction_id = f"{int(time.time())}-{uuid.uuid4().hex[:12]}"
            result.transaction_id = transaction_id
            entries = tuple(PlanEntry(path, str(entry.get("sha256", "")), int(entry.get("size", 0)), "replace", "", str(entry.get("sha256", ""))) for path, entry in sorted(files.items()) if isinstance(entry, dict) and path not in other_references)
            plan = InstallPlan(STATE_SCHEMA, transaction_id, "uninstall", result.version, host, result.profile, self.target.as_posix(), result.version, entries)
            self._snapshot(transaction_id, plan, manifest)
            root, backup, state_path = self._transaction_paths(transaction_id)
            state = json.loads(state_path.read_text(encoding="utf-8"))
            state["state"] = "applying"
            _atomic_json(state_path, state)
            for relative in sorted(files):
                if relative in other_references:
                    result.preserved.append(relative)
                    continue
                destination = self._destination(relative)
                if destination.is_file() or destination.is_symlink():
                    if relative in result.preserved and force:
                        backup_path = backup / relative
                        backup_path.parent.mkdir(parents=True, exist_ok=True)
                        if not backup_path.exists():
                            shutil.copy2(destination, backup_path, follow_symlinks=False)
                    destination.unlink()
                    result.removed.append(relative)
            self._manifest_path(host).unlink(missing_ok=True)
            _atomic_json(root / "after-manifest.json", {"schema_version": MANIFEST_SCHEMA, "host": host, "files": {}})
            state["state"] = "complete"
            _atomic_json(state_path, state)
            self._journal(transaction_id, "uninstall", "complete", host=host)
            self._prune_empty_directories()
            self._prune_transactions(host)
            return result

    def _prune_empty_directories(self) -> None:
        for path in sorted((item for item in self.target.rglob("*") if item.is_dir()), key=lambda item: len(item.parts), reverse=True):
            if path == self.state_root or self.state_root in path.parents:
                continue
            try:
                path.rmdir()
            except OSError:
                pass

    def _prune_transactions(self, host: str) -> None:
        complete: list[Path] = []
        for root in self.transactions_root.iterdir() if self.transactions_root.exists() else ():
            state_path = root / "state.json"
            plan_path = root / "plan.json"
            if not state_path.is_file() or not plan_path.is_file():
                continue
            state = json.loads(state_path.read_text(encoding="utf-8"))
            plan = json.loads(plan_path.read_text(encoding="utf-8"))
            if plan.get("host") == host and state.get("state") in {"complete", "rolled-back", "recovered"}:
                complete.append(root)
        for old in sorted(complete, key=lambda path: path.name, reverse=True)[BACKUP_RETENTION:]:
            shutil.rmtree(old)
