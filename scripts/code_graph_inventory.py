"""Cheap repository inventory used to validate a reusable Code Graph cache."""
from __future__ import annotations

import hashlib
from pathlib import Path
from typing import Any


SKIP_DIRS = {
    ".git", ".hg", ".idea", ".svn", ".tailtrail", "tailtrail-meta",
    "__pycache__", "aidlc-rules", "node_modules", "vendor", "dist", "build",
    "target", "coverage", ".next", ".nuxt", ".venv", "venv", "bin", "obj",
}
RELEVANT_SUFFIXES = {
    ".cs", ".java", ".py", ".sql", ".tf", ".tfvars", ".json", ".properties",
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


def _skipped(path: Path) -> bool:
    return any(part in SKIP_DIRS for part in path.parts)


def relevant_files(root: Path) -> list[Path]:
    root = root.resolve()
    files: list[Path] = []
    for path in root.rglob("*"):
        if not path.is_file() or _skipped(path):
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
