"""Cheap repository inventory used to validate a reusable Code Graph cache."""
from __future__ import annotations

import hashlib
import importlib.util
import sys
from pathlib import Path
from typing import Any


SKIP_DIRS = {
    ".git", ".hg", ".idea", ".svn", ".tailtrail", "tailtrail-meta",
    "__pycache__", "aidlc-rules", "node_modules", "vendor", "dist", "build",
    "target", "coverage", ".next", ".nuxt", ".venv", "venv", "bin", "obj",
}
RELEVANT_SUFFIXES = {
    ".cjs", ".cs", ".go", ".java", ".js", ".jsx", ".mjs", ".py", ".sql",
    ".ts", ".tsx", ".tf", ".tfvars", ".vue", ".svelte", ".json", ".properties",
    ".toml", ".xml", ".yaml", ".yml",
}
RELEVANT_NAMES = {
    "pom.xml", "build.gradle", "build.gradle.kts", "gradle.properties", "requirements.txt",
    "pyproject.toml", "setup.py", "tox.ini", "pytest.ini", "sonar-project.properties",
    "package.json", "package-lock.json", "pnpm-lock.yaml", "yarn.lock",
    "Directory.Build.props", "Directory.Build.targets", "Dockerfile", "Jenkinsfile", "Makefile",
}
RELEVANT_NAME_SUFFIXES = {".csproj", ".sln"}
ALGORITHM = "path-size-mtime-ns-v1"


def _policy() -> Any:
    """Shared workspace policy, loaded once (Phase 3 cache migration)."""
    global _POLICY
    if _POLICY is None:
        spec = importlib.util.spec_from_file_location(
            "inventory_workspace_policy",
            Path(__file__).resolve().parents[1] / "scripts" / "repository_path_policy.py",
        )
        if spec is None or spec.loader is None:
            raise RuntimeError("unable to load scripts/repository_path_policy.py")
        module = importlib.util.module_from_spec(spec)
        sys.modules[spec.name] = module
        spec.loader.exec_module(module)
        _POLICY = module
    return _POLICY


_POLICY: Any = None


def _skipped(path: Path, root: Path | None = None) -> bool:
    if any(part in SKIP_DIRS for part in path.parts):
        return True
    if root is None:
        return False
    try:
        relative = path.relative_to(root).as_posix()
    except ValueError:
        return True
    role, _ = _policy().classify_path(root, relative)
    return role != "application"


def relevant_files(root: Path) -> list[Path]:
    root = root.resolve()
    files: list[Path] = []
    for path in root.rglob("*"):
        if not path.is_file() or _skipped(path, root):
            continue
        if path.suffix in RELEVANT_SUFFIXES or path.name in RELEVANT_NAMES or path.suffix in RELEVANT_NAME_SUFFIXES:
            files.append(path)
    return sorted(files)


def snapshot(root: Path) -> dict[str, Any]:
    """Return metadata-only freshness evidence without reading file contents."""
    root = root.resolve()
    digest = hashlib.sha256()
    count = 0
    for path in relevant_files(root):
        stat = path.stat()
        relative = path.relative_to(root).as_posix()
        digest.update(f"{relative}\0{stat.st_size}\0{stat.st_mtime_ns}\n".encode("utf-8"))
        count += 1
    return {"algorithm": ALGORITHM, "file_count": count, "fingerprint": f"sha256:{digest.hexdigest()}"}
