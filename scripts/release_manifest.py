#!/usr/bin/env python3

from __future__ import annotations

import json
import re
import subprocess
from pathlib import Path
from typing import Any, Iterable


MANIFEST_NAME = "release-manifest.json"
REPOSITORY_URL = re.compile(r"(?:https?://github\.com/|git@github\.com:)[A-Za-z0-9_.-]+/[A-Za-z0-9_.-]+")


def load(root: Path) -> dict[str, Any]:
    path = root / MANIFEST_NAME
    data = json.loads(path.read_text(encoding="utf-8"))
    if not isinstance(data, dict):
        raise ValueError(f"{MANIFEST_NAME} must contain a JSON object")
    return data


def git_files(root: Path) -> list[str]:
    result = subprocess.run(["git", "ls-files"], cwd=root, text=True, capture_output=True, check=False)
    if result.returncode == 0:
        return sorted(line for line in result.stdout.splitlines() if line)
    return sorted(path.relative_to(root).as_posix() for path in root.rglob("*") if path.is_file() and ".git" not in path.parts)


def candidate_files(root: Path, manifest: dict[str, Any]) -> list[str]:
    paths = set(git_files(root))
    paths.update(str(path) for path in manifest.get("candidate_additions", []))
    paths.update(str(path) for path in manifest.get("required_release_files", []))
    hygiene = manifest.get("repository_hygiene", {})
    allowed = set(str(path) for path in hygiene.get("allowed_paths", []))
    forbidden_names = set(str(name) for name in hygiene.get("forbidden_names", []))
    forbidden_parts = set(str(part) for part in hygiene.get("forbidden_parts", []))
    exclusions = manifest.get("candidate_exclusions", {})
    excluded_files = set(str(path) for path in exclusions.get("files", []))
    excluded_prefixes = tuple(str(prefix) for prefix in exclusions.get("prefixes", []))
    return sorted(
        path for path in paths
        if (root / path).is_file()
        and path not in excluded_files
        and not path.startswith(excluded_prefixes)
        and (path in allowed or (Path(path).name not in forbidden_names and not forbidden_parts.intersection(Path(path).parts)))
    )


def _version_from_pyproject(body: str) -> str | None:
    project = re.search(r"(?ms)^\[project\]\s*(.*?)(?=^\[|\Z)", body)
    if not project:
        return None
    match = re.search(r'(?m)^version\s*=\s*["\']([^"\']+)["\']', project.group(1))
    return match.group(1) if match else None


def validate(root: Path, manifest: dict[str, Any] | None = None, paths: Iterable[str] | None = None) -> list[str]:
    manifest = manifest or load(root)
    errors: list[str] = []
    if manifest.get("schema_version") != "1":
        errors.append("release manifest schema_version must be 1")
    product = manifest.get("product", {})
    version = str(product.get("version", ""))
    required = [str(path) for path in manifest.get("required_release_files", [])]
    for path in required:
        if not (root / path).is_file():
            errors.append(f"missing release file: {path}")
    pyproject = root / "pyproject.toml"
    if pyproject.is_file() and _version_from_pyproject(pyproject.read_text(encoding="utf-8")) != version:
        errors.append(f"pyproject.toml version must equal release manifest version {version}")
    plugin = root / ".codex-plugin" / "plugin.json"
    if plugin.is_file():
        try:
            plugin_version = json.loads(plugin.read_text(encoding="utf-8")).get("version")
        except json.JSONDecodeError as error:
            errors.append(f"invalid plugin manifest JSON: {error}")
        else:
            if plugin_version != version:
                errors.append(f".codex-plugin/plugin.json version must equal release manifest version {version}")
    package_init = root / "tailtrail" / "__init__.py"
    if package_init.is_file():
        package_match = re.search(r'(?m)^__version__\s*=\s*["\']([^"\']+)["\']', package_init.read_text(encoding="utf-8"))
        if not package_match or package_match.group(1) != version:
            errors.append(f"tailtrail/__init__.py version must equal release manifest version {version}")
    for workflow in manifest.get("workflows", []):
        path = str(workflow.get("path", ""))
        target = root / path
        if not target.is_file():
            errors.append(f"missing release workflow: {path}")
            continue
        body = target.read_text(encoding="utf-8", errors="replace")
        for fragment in workflow.get("required_fragments", []):
            if str(fragment) not in body:
                errors.append(f"stale release workflow {path}: missing {fragment}")
    hygiene = manifest.get("repository_hygiene", {})
    allowed = set(str(path) for path in hygiene.get("allowed_paths", []))
    for relative in paths if paths is not None else git_files(root):
        relative = str(relative)
        if relative in allowed:
            continue
        path = Path(relative)
        if path.name in hygiene.get("forbidden_names", []):
            errors.append(f"release candidate contains forbidden local artifact: {relative}")
        elif any(part in hygiene.get("forbidden_parts", []) for part in path.parts):
            errors.append(f"release candidate contains forbidden local state: {relative}")
    return errors


def auditable_files(root: Path, manifest: dict[str, Any]) -> list[str]:
    audit = manifest.get("public_audit", {})
    suffixes = set(str(value) for value in audit.get("text_suffixes", []))
    excluded = set(str(value) for value in audit.get("excluded_files", []))
    return [path for path in candidate_files(root, manifest) if path not in excluded and Path(path).suffix in suffixes]


def repository_reference_findings(body: str, allowed_urls: Iterable[str]) -> list[str]:
    allowed = tuple(str(url).rstrip("/") for url in allowed_urls)
    findings: list[str] = []
    for match in REPOSITORY_URL.finditer(body):
        reference = match.group(0)
        normalized = reference.replace("git@github.com:", "https://github.com/").rstrip("/")
        if not any(normalized == item or normalized.startswith(item + "/") for item in allowed):
            findings.append(reference)
    return findings
