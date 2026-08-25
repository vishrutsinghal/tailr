"""Small, stable, side-effect-free TailTrail Python API."""

from __future__ import annotations

from dataclasses import dataclass
from enum import IntEnum
from pathlib import Path

from .resources import package_root, verify_package


class ExitCode(IntEnum):
    OK = 0
    VALIDATION_FAILED = 1
    USAGE = 2
    UNAVAILABLE = 3
    INTERNAL_ERROR = 70


@dataclass(frozen=True)
class PackageStatus:
    version: str
    root: Path
    valid: bool
    issues: tuple[str, ...]


def package_status() -> PackageStatus:
    from . import __version__

    issues = tuple(verify_package())
    return PackageStatus(version=__version__, root=package_root(), valid=not issues, issues=issues)
