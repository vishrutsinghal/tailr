"""Manifest-driven host payload selection.

E3 owns the common lifecycle. Host-specific conformance remains an E4 gate,
but every current host already resolves its files through this catalog.
"""

from __future__ import annotations

import json
from dataclasses import dataclass
from pathlib import Path

from ..hosts.contracts import HOSTS, core_files


PROFILES = ("core", "extended")


@dataclass(frozen=True)
class Payload:
    source: Path
    destination: str


def source_root() -> Path:
    package_root = Path(__file__).resolve().parents[1]
    return package_root if (package_root / "package-manifest.json").is_file() else package_root.parent


def _safe_relative(value: str) -> str:
    path = Path(value)
    if path.is_absolute() or not path.parts or any(part in {"", ".", ".."} for part in path.parts):
        raise ValueError(f"unsafe installer path: {value}")
    return path.as_posix()


def payloads(host: str, profile: str, root: Path | None = None) -> tuple[Payload, ...]:
    if host not in HOSTS:
        raise ValueError(f"unsupported host: {host}")
    if profile not in PROFILES:
        raise ValueError(f"unsupported profile: {profile}")
    root = root or source_root()
    contract_root = root if (root / "adapters" / "host-compatibility-v1.json").is_file() else source_root()
    selected: dict[str, Path] = {
        _safe_relative(destination): root / _safe_relative(source)
        for source, destination in core_files(host, contract_root)
    }
    if profile == "extended":
        manifest = json.loads((root / "package-manifest.json").read_text(encoding="utf-8"))
        prefix = Path(".tailtrail/install/payload") / host
        for relative in manifest["required_files"]:
            safe = _safe_relative(relative)
            selected[(prefix / safe).as_posix()] = root / safe
        for directory in manifest["required_directories"]:
            safe_dir = _safe_relative(directory)
            source_dir = root / safe_dir
            for path in sorted(source_dir.rglob("*")):
                if path.is_file() and "__pycache__" not in path.parts and path.suffix not in {".pyc", ".pyo"} and path.name != ".DS_Store":
                    relative = path.relative_to(root)
                    selected[(prefix / relative).as_posix()] = path
    missing = [path.as_posix() for path in selected.values() if not path.is_file()]
    if missing:
        raise FileNotFoundError(f"installer payload is incomplete: {', '.join(missing)}")
    return tuple(Payload(source=source, destination=destination) for destination, source in sorted(selected.items()))
