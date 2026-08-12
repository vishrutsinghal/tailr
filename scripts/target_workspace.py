#!/usr/bin/env python3
"""Resolve and identify the editable workspace for a TailTrail planning run.

TW-1 provides read-only target resolution. TW-2 adds a local, sanitized
identity snapshot used by Planning Lock activation and managed-write checks.
Policy enforcement and host-native adapters remain separate phases.
"""

from __future__ import annotations

import argparse
import hashlib
import importlib.util
import json
import re
import subprocess
from urllib.parse import urlparse
from pathlib import Path
from typing import Any


ABSOLUTE_LOCAL_PATH = re.compile(r"(?<!https:)(?<!http:)(?<![A-Za-z0-9])(?:[A-Za-z]:[\\/]|/)[^\s`'\"<>|]+")
TARGET_ROOT_CUES = (
    "changes must be made", "changes have to be made", "changes has to be made",
    "change has to be made", "change needs to be made", "changes need to be made",
    "implement in", "implement within", "target repo", "target repository",
    "target root", "project root",
)
STATUSES = {"verified", "ambiguous", "inaccessible", "unmapped", "blocked"}
MANIFESTS = ("package.json", "pyproject.toml", "pom.xml", "build.gradle", "build.gradle.kts", "go.mod", "Cargo.toml", "Gemfile")
LANGUAGE_SUFFIXES = {".py": "Python", ".ts": "TypeScript", ".tsx": "TypeScript", ".js": "JavaScript", ".jsx": "JavaScript", ".java": "Java", ".cs": "C#", ".go": "Go", ".rb": "Ruby", ".rs": "Rust"}
INPUT_ROLE_ACCESS = {
    "target": "read-write-after-approval",
    "related-repo": "read-only",
    "reference-repo": "read-only",
    "design-reference": "read-only",
    "requirement-artifact": "read-only",
    "evidence-artifact": "read-only",
}
LOCAL_REPOSITORY_ROLES = {"related-repo", "reference-repo"}


def host_adapter() -> Any:
    spec = importlib.util.spec_from_file_location("tailtrail_host_workspace_adapter", Path(__file__).with_name("host-workspace-adapter.py"))
    module = importlib.util.module_from_spec(spec)
    assert spec and spec.loader
    spec.loader.exec_module(module)
    return module


def enterprise_policy() -> Any:
    spec = importlib.util.spec_from_file_location("tailtrail_enterprise_target_policy", Path(__file__).with_name("enterprise-target-policy.py"))
    module = importlib.util.module_from_spec(spec)
    assert spec and spec.loader
    spec.loader.exec_module(module)
    return module


def prompt_candidate(goal: str) -> str | None:
    lowered = goal.lower()
    for match in ABSOLUTE_LOCAL_PATH.finditer(goal):
        raw = match.group(0).rstrip(".,:;)]}")
        context = lowered[max(0, match.start() - 180):match.start()]
        if raw and any(cue in context for cue in TARGET_ROOT_CUES):
            return raw
    return None


def parse_aliases(values: list[str]) -> dict[str, Path]:
    aliases: dict[str, Path] = {}
    for value in values:
        name, separator, raw_path = value.partition("=")
        if not separator or not name.strip() or not raw_path.strip():
            raise ValueError("aliases must use name=/absolute/or/local/path")
        aliases[name.strip()] = Path(raw_path.strip()).expanduser()
    return aliases


def candidate(source: str, path: Path, requested: str | None = None) -> dict[str, str]:
    return {"source": source, "requested": requested or path.as_posix(), "path": path.expanduser().as_posix()}


def _git(root: Path, *args: str) -> str | None:
    result = subprocess.run(["git", *args], cwd=root, text=True, capture_output=True, check=False)
    value = result.stdout.strip() if result.returncode == 0 else ""
    return value or None


def _remote_identity(raw: str | None) -> tuple[str | None, str | None]:
    if not raw:
        return None, None
    value = re.sub(r"://[^/@]+@", "://", raw.strip())
    ssh = re.match(r"(?:[^@]+@)?([^:/]+):/?(.+)$", value)
    http = re.match(r"https?://([^/]+)/(.+)$", value)
    match = http or ssh
    if not match:
        return None, None
    return match.group(1).lower(), match.group(2).removesuffix(".git").strip("/")


def identity(root: Path) -> dict[str, Any]:
    """Capture safe, deterministic target identity without reading source bodies."""
    root = root.resolve()
    manifests = [name for name in MANIFESTS if (root / name).is_file()]
    languages: set[str] = set()
    inventory: list[str] = []
    for path in list(root.rglob("*"))[:10_000]:
        if not path.is_file() or any(part in {".git", ".tailtrail", "node_modules", ".venv", "venv", "__pycache__"} for part in path.parts):
            continue
        relative = path.relative_to(root).as_posix()
        if path.suffix.lower() in LANGUAGE_SUFFIXES:
            languages.add(LANGUAGE_SUFFIXES[path.suffix.lower()])
            inventory.append(relative)
    remote_host, remote_path = _remote_identity(_git(root, "config", "--get", "remote.origin.url"))
    stable = {"root": root.as_posix(), "remote_host": remote_host, "remote_path": remote_path, "manifests": manifests, "languages": sorted(languages), "inventory": sorted(inventory)}
    digest = hashlib.sha256(json.dumps(stable, sort_keys=True, separators=(",", ":")).encode("utf-8")).hexdigest()
    return {
        "schema_version": "1",
        "type": "tailtrail-target-workspace-identity",
        "root": root.as_posix(),
        "repository_kind": "git" if _git(root, "rev-parse", "--is-inside-work-tree") == "true" else "directory",
        "git": {"remote_host": remote_host, "remote_path": remote_path, "head": _git(root, "rev-parse", "HEAD")},
        "project": {"manifests": manifests, "languages": sorted(languages), "inventory_count": len(inventory)},
        "fingerprint": f"sha256:{digest}",
    }


def verify_identity(saved: dict[str, Any], root: Path) -> dict[str, Any]:
    """Compare a bound identity at activation/control time.

    A Git HEAD change is visible but not blocking by itself. A different root,
    repository identity, or material file inventory change blocks execution.
    """
    current = identity(root)
    if saved.get("type") != "tailtrail-target-workspace-identity":
        return {"status": "legacy", "blocking": False, "reason": "legacy Planning Lock has no target identity", "current": current}
    for field in ("root", "fingerprint"):
        if saved.get(field) != current.get(field):
            return {"status": "mismatch", "blocking": True, "reason": f"target {field} differs from the Planning Lock", "expected": saved, "current": current}
    expected_git = saved.get("git", {}) if isinstance(saved.get("git"), dict) else {}
    current_git = current["git"]
    if (expected_git.get("remote_host"), expected_git.get("remote_path")) != (current_git.get("remote_host"), current_git.get("remote_path")):
        return {"status": "mismatch", "blocking": True, "reason": "target Git repository identity differs from the Planning Lock", "expected": saved, "current": current}
    return {"status": "head-changed" if expected_git.get("head") != current_git.get("head") else "matched", "blocking": False, "reason": "Git HEAD changed after planning; target identity still matches." if expected_git.get("head") != current_git.get("head") else "target identity matches the Planning Lock", "expected": saved, "current": current}


def _is_external(value: str) -> bool:
    return urlparse(value).scheme in {"http", "https"}


def _external_locator(value: str) -> str:
    parsed = urlparse(value)
    return f"{parsed.scheme}://{parsed.netloc}/<redacted>" if parsed.netloc else "external://<unresolved>"


def _relationship(path: Path, target: Path) -> str:
    if path == target:
        return "same-as-target"
    try:
        path.relative_to(target)
        return "inside-target"
    except ValueError:
        pass
    try:
        target.relative_to(path)
        return "contains-target"
    except ValueError:
        return "external"


def _role_record(role: str, value: str, target: Path, index: int) -> dict[str, Any]:
    if _is_external(value):
        return {
            "input_id": f"IN-{index:02d}", "role": role, "locator": _external_locator(value),
            "kind": "external-reference", "access": INPUT_ROLE_ACCESS[role], "status": "declared-unread",
            "inspection": "host-access-and-explicit-approval-required",
        }
    path = Path(value).expanduser().resolve()
    relationship = _relationship(path, target)
    if role in LOCAL_REPOSITORY_ROLES and relationship != "external":
        raise ValueError(f"{role} `{path.as_posix()}` overlaps the editable target; select it as the target or provide a separate read-only repository")
    return {
        "input_id": f"IN-{index:02d}", "role": role, "locator": path.as_posix(),
        "kind": "local-directory" if path.is_dir() else "local-artifact",
        "access": INPUT_ROLE_ACCESS[role], "status": "available-unread" if path.exists() else "unavailable",
        "relationship": relationship, "inspection": "read-only-bounded-summary",
    }


def input_roles(
    root: Path,
    *,
    reference_roots: list[str] | None = None,
    related_repos: list[str] | None = None,
    design_references: list[str] | None = None,
    requirement_artifacts: list[str] | None = None,
    evidence_artifacts: list[str] | None = None,
) -> dict[str, Any]:
    """Create the TW-3 role registry without reading source or external data."""
    target = root.resolve()
    roles: list[dict[str, Any]] = [{
        "input_id": "IN-01", "role": "target", "locator": target.as_posix(),
        "kind": "local-directory", "access": INPUT_ROLE_ACCESS["target"],
        "status": "verified", "inspection": "navigator-discovery-after-planning-lock",
    }]
    grouped = (
        ("reference-repo", reference_roots or []),
        ("related-repo", related_repos or []),
        ("design-reference", design_references or []),
        ("requirement-artifact", requirement_artifacts or []),
        ("evidence-artifact", evidence_artifacts or []),
    )
    index = 2
    for role, values in grouped:
        for value in values:
            if not str(value).strip():
                raise ValueError(f"{role} values must not be empty")
            roles.append(_role_record(role, str(value).strip(), target, index))
            index += 1
    registry = {
        "schema_version": "1", "type": "tailtrail-input-role-registry",
        "target_root": target.as_posix(), "inputs": roles,
        "boundary": "Only the single target may be edited after Planning Lock approval. All other declared inputs remain read-only and may be summarized only within their inspection boundary.",
    }
    validate_input_roles(registry, target)
    return registry


def validate_input_roles(registry: dict[str, Any], root: Path) -> dict[str, Any]:
    """Validate role separation before activation or managed writes."""
    if not registry:
        return {"status": "legacy", "target": root.resolve().as_posix(), "read_only_inputs": 0}
    inputs = registry.get("inputs")
    if registry.get("type") != "tailtrail-input-role-registry" or not isinstance(inputs, list):
        raise ValueError("Planning Lock input-role registry is missing or invalid")
    targets = [item for item in inputs if isinstance(item, dict) and item.get("role") == "target"]
    if len(targets) != 1:
        raise ValueError("input-role registry must contain exactly one target")
    unknown_roles = [item.get("input_id", "unknown") for item in inputs if not isinstance(item, dict) or item.get("role") not in INPUT_ROLE_ACCESS]
    if unknown_roles:
        raise ValueError("input-role registry contains an unknown role: " + ", ".join(unknown_roles))
    target = targets[0]
    if target.get("access") != INPUT_ROLE_ACCESS["target"] or target.get("locator") != root.resolve().as_posix():
        raise ValueError("input-role registry target does not match the active workspace")
    invalid = [item.get("input_id", "unknown") for item in inputs if isinstance(item, dict) and item.get("role") != "target" and item.get("access") != "read-only"]
    if invalid:
        raise ValueError("non-target inputs must remain read-only: " + ", ".join(invalid))
    return {"status": "matched", "target": target["locator"], "read_only_inputs": len(inputs) - 1}


def reference_summary(registry: dict[str, Any]) -> list[dict[str, Any]]:
    """Return a bounded metadata-only summary for declared read-only inputs."""
    summary: list[dict[str, Any]] = []
    for item in registry.get("inputs", []):
        if not isinstance(item, dict) or item.get("role") == "target":
            continue
        row = {key: item.get(key) for key in ("input_id", "role", "locator", "kind", "status", "inspection")}
        if item.get("kind") == "local-directory" and item.get("status") == "available-unread":
            snapshot = identity(Path(str(item["locator"])))
            row["project"] = snapshot["project"]
            row["repository_kind"] = snapshot["repository_kind"]
        summary.append(row)
    return summary


def resolve(
    goal: str,
    *,
    explicit_root: Path | None = None,
    host_workspace: Path | None = None,
    alias: str | None = None,
    aliases: dict[str, Path] | None = None,
    cwd: Path | None = None,
) -> dict[str, Any]:
    """Resolve one target using the documented precedence order.

    `host_workspace` is a host-adapter input in TW-1.  It is intentionally a
    supplied value, not an attempt to infer hidden host state.
    """
    aliases = aliases or {}
    cwd = cwd or Path.cwd()
    selected: list[dict[str, str]] = []
    if explicit_root is not None:
        selected.append(candidate("--root", explicit_root))
    elif host_workspace is not None:
        selected.append(candidate("host-workspace", host_workspace))
    elif alias is not None:
        if alias not in aliases:
            return {"status": "unmapped", "source": "alias", "requested": alias, "candidates": [], "reason": "workspace alias is not registered in this resolver invocation"}
        selected.append(candidate("alias", aliases[alias], alias))
    else:
        prompt = prompt_candidate(goal)
        if prompt:
            selected.append(candidate("goal", Path(prompt), prompt))
        else:
            selected.append(candidate("host-cwd", cwd))

    unique = {item["path"]: item for item in selected}
    if len(unique) != 1:
        return {"status": "ambiguous", "source": "multiple", "requested": None, "candidates": list(unique.values()), "reason": "more than one editable target has the same precedence"}
    choice = next(iter(unique.values()))
    path = Path(choice["path"])
    if not path.is_dir():
        return {"status": "inaccessible", "source": choice["source"], "requested": choice["requested"], "candidates": [choice], "reason": "the selected target repository is not accessible from this host"}
    return {"status": "verified", "source": choice["source"], "requested": choice["requested"], "root": path.resolve(), "candidates": [choice], "reason": "one accessible editable target was resolved"}


def markdown(result: dict[str, Any]) -> str:
    lines = ["# TailTrail Target Workspace", "", f"- Status: **{result['status']}**", f"- Source: `{result.get('source', 'unknown')}`"]
    if result.get("requested"):
        lines.append(f"- Requested: `{result['requested']}`")
    if result.get("root"):
        lines.append(f"- Resolved root: `{Path(result['root']).as_posix()}`")
    lines.append(f"- Reason: {result['reason']}")
    if result.get("candidates"):
        lines.extend(["", "## Candidates", ""])
        lines.extend(f"- `{item['requested']}` — {item['source']}" for item in result["candidates"])
    return "\n".join(lines) + "\n"


def roles_markdown(registry: dict[str, Any], summary: bool = False) -> str:
    lines = ["# TailTrail Input Roles", "", f"- Target: `{registry['target_root']}`", "- Boundary: only the target may be edited after Planning Lock approval.", "", "| Input | Role | Access | Status |", "| --- | --- | --- | --- |"]
    for item in registry["inputs"]:
        lines.append(f"| `{item['locator']}` | {item['role']} | {item['access']} | {item['status']} |")
    if summary:
        lines.extend(["", "## Read-only reference summary", ""])
        rows = reference_summary(registry)
        if not rows:
            lines.append("- No read-only inputs were declared.")
        for row in rows:
            project = row.get("project", {}) if isinstance(row.get("project"), dict) else {}
            signal = ", ".join(project.get("languages", [])) or "not inspected"
            lines.append(f"- `{row['input_id']}` `{row['role']}`: {row['status']}; languages: {signal}.")
    return "\n".join(lines) + "\n"


def main() -> int:
    parser = argparse.ArgumentParser(description="Resolve one TailTrail editable target workspace without reading source or changing files.")
    sub = parser.add_subparsers(dest="action", required=True)
    resolve_parser = sub.add_parser("resolve")
    resolve_parser.add_argument("goal", nargs="*", help="Task request used only for a prompt candidate.")
    resolve_parser.add_argument("--root", type=Path)
    resolve_parser.add_argument("--host-workspace", type=Path)
    resolve_parser.add_argument("--alias")
    resolve_parser.add_argument("--workspace-alias", action="append", default=[], metavar="NAME=PATH")
    resolve_parser.add_argument("--format", choices=("markdown", "json"), default="markdown")
    roles_parser = sub.add_parser("roles", help="Declare one editable target and read-only inputs for a TailTrail run.")
    roles_parser.add_argument("--root", type=Path, default=Path.cwd())
    roles_parser.add_argument("--reference-root", action="append", default=[])
    roles_parser.add_argument("--related-repo", action="append", default=[])
    roles_parser.add_argument("--design-reference", action="append", default=[])
    roles_parser.add_argument("--requirement-artifact", action="append", default=[])
    roles_parser.add_argument("--evidence-artifact", action="append", default=[])
    roles_parser.add_argument("--summary", action="store_true", help="Include bounded metadata-only summaries for declared read-only directories.")
    roles_parser.add_argument("--format", choices=("markdown", "json"), default="markdown")
    host_parser = sub.add_parser("host-workspace", help="Resolve a declared Codex, Copilot, or Claude workspace before target planning.")
    host_parser.add_argument("--host", required=True, choices=("codex", "copilot", "claude"))
    host_parser.add_argument("--workspace")
    host_parser.add_argument("--host-platform", choices=("auto", "windows", "macos", "linux", "wsl", "container"), default="auto")
    host_parser.add_argument("--format", choices=("markdown", "json"), default="markdown")
    policy_parser = sub.add_parser("policy", help="Inspect or enforce an opt-in local enterprise target policy.")
    policy_parser.add_argument("--root", type=Path, required=True)
    policy_parser.add_argument("--policy", type=Path, required=True)
    policy_parser.add_argument("--actor")
    policy_parser.add_argument("--target-alias")
    policy_parser.add_argument("--format", choices=("markdown", "json"), default="json")
    args = parser.parse_args()
    try:
        if args.action == "host-workspace":
            result = host_adapter().resolve(args.host, args.workspace, host_platform=args.host_platform)
            if args.format == "json":
                print(json.dumps(result, indent=2, default=str, sort_keys=True))
            else:
                print(host_adapter().markdown(result), end="")
            return 0 if result["status"] in {"verified", "not-provided"} else 2
        if args.action == "policy":
            result = enterprise_policy().evaluate(args.root, enterprise_policy().load(args.policy), actor=args.actor, selected_alias=args.target_alias)
            print(json.dumps(result, indent=2, default=str, sort_keys=True))
            return 2 if result["blocking"] else 0
        if args.action == "roles":
            result = input_roles(args.root, reference_roots=args.reference_root, related_repos=args.related_repo, design_references=args.design_reference, requirement_artifacts=args.requirement_artifact, evidence_artifacts=args.evidence_artifact)
            if args.summary:
                result["reference_summary"] = reference_summary(result)
            if args.format == "json":
                print(json.dumps(result, indent=2, default=str, sort_keys=True))
            else:
                print(roles_markdown(result, args.summary), end="")
            return 0
        goal = " ".join(args.goal).strip()
        result = resolve(goal, explicit_root=args.root, host_workspace=args.host_workspace, alias=args.alias, aliases=parse_aliases(args.workspace_alias))
    except ValueError as error:
        parser.error(str(error))
    if args.format == "json":
        print(json.dumps(result, indent=2, default=str, sort_keys=True))
    else:
        print(markdown(result), end="")
    return 0 if result["status"] == "verified" else 2


if __name__ == "__main__":
    raise SystemExit(main())
