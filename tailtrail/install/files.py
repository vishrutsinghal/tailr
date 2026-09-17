"""Single-ownership file operations for install/update flows.

Both the transactional engine and the legacy per-host scripts copy,
hash, and write the same pack files. Those operations live here so
there is exactly one implementation: atomic writes (tempfile +
os.replace + fsync), SHA-256 hashing, and symlink-aware safe paths.
Manifest *formats* still differ per flow (tracked follow-up); the bytes
on disk do not.
"""

from __future__ import annotations

import hashlib
import os
import shutil
import tempfile
from pathlib import Path


def sha256_bytes(data: bytes) -> str:
    """Hex digest of bytes."""
    return hashlib.sha256(data).hexdigest()


def sha256_file(path: Path) -> str:
    """Hex digest of a file's bytes."""
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def atomic_write_bytes(path: Path, data: bytes) -> None:
    """Write bytes atomically (tempfile + fsync + os.replace)."""
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


def atomic_write_text(path: Path, text: str) -> None:
    """Write text atomically as UTF-8."""
    atomic_write_bytes(path, text.encode("utf-8"))


def atomic_copy(source: Path, destination: Path) -> None:
    """Copy a file atomically (via a temporary file in the target dir)."""
    destination.parent.mkdir(parents=True, exist_ok=True)
    descriptor, temporary = tempfile.mkstemp(prefix=f".{destination.name}.", dir=destination.parent)
    os.close(descriptor)
    try:
        shutil.copy2(source, temporary)
        os.replace(temporary, destination)
    finally:
        if os.path.exists(temporary):
            os.unlink(temporary)


def safe_managed_path(root: Path, relative: str) -> Path:
    """Resolve a managed relative path, refusing escapes and symlinks."""
    from .engine import InstallFailure

    value = Path(relative)
    if value.is_absolute() or not value.parts or any(part in {"", ".", ".."} for part in value.parts):
        raise InstallFailure("unsafe-path", f"unsafe managed path: {relative}")
    destination = root / value
    current = root
    for part in value.parts[:-1]:
        current = current / part
        if current.is_symlink():
            raise InstallFailure("unsafe-path", f"managed path crosses a symlink: {relative}")
    return destination
