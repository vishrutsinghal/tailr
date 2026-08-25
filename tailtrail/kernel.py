"""Installed-runtime kernel for compatibility, dispatch, and diagnostics."""

from __future__ import annotations

import os
import sys
from pathlib import Path

from .errors import PackageResourceError, UnsupportedPythonError
from .resources import package_root, verify_package


SUPPORTED_MIN = (3, 12)
SUPPORTED_MAX_EXCLUSIVE = (3, 14)


def python_compatibility(version: tuple[int, int] | None = None) -> tuple[bool, str]:
    version = version or (sys.version_info.major, sys.version_info.minor)
    supported = SUPPORTED_MIN <= version < SUPPORTED_MAX_EXCLUSIVE
    return supported, f"Python {version[0]}.{version[1]} is {'supported' if supported else 'unsupported'}; TailTrail 0.6 requires Python >=3.12,<3.14."


def require_supported_python() -> None:
    supported, message = python_compatibility()
    if not supported:
        raise UnsupportedPythonError(message)


def runtime_root() -> Path:
    installed = package_root()
    if (installed / "scripts" / "tailtrail.py").is_file():
        return installed
    compatibility = os.environ.get("TAILTRAIL_SOURCE_COMPAT_ROOT")
    if compatibility:
        candidate = Path(compatibility).resolve()
        if (candidate / "scripts" / "tailtrail.py").is_file():
            return candidate
    raise PackageResourceError("TailTrail package resources are unavailable; reinstall the wheel or sdist.")


def prepare_dispatch() -> Path:
    require_supported_python()
    root = runtime_root()
    if root == package_root():
        issues = verify_package(root)
        if issues:
            raise PackageResourceError(issues[0])
    scripts = root / "scripts"
    if scripts.as_posix() not in sys.path:
        sys.path.insert(0, scripts.as_posix())
    return root
