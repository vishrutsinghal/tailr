#!/usr/bin/env python3
"""Validate and inspect TailTrail's enterprise closure baseline."""

from __future__ import annotations

import argparse
import ast
import hashlib
import importlib.util
import json
import re
import subprocess
import sys
from datetime import datetime, timezone
from pathlib import Path
from typing import Any


ROOT = Path(__file__).resolve().parents[1]
REGISTRY_PATH = ROOT / "enterprise-closure-registry.json"
SCHEMA_PATH = ROOT / "enterprise-closure-registry.schema.json"
FEATURE_REGISTRY_PATH = ROOT / "tailtrail-registry.json"

PHASES = {f"E{number}" for number in range(13)}
PRIORITIES = {"P0", "P1", "P2"}
MATURITY_VALUES = {"supported", "preview", "experimental", "planned", "retired"}
REQUIREMENT_STATUSES = {"planned", "in-progress", "blocked", "complete"}
INVENTORY_CATEGORIES = {
    "commands",
    "schemas",
    "adapters",
    "persisted-artifacts",
    "ci-controls",
    "install-surfaces",
    "release-files",
    "support-claims",
}
ALLOWED_CHANGE_CLASSES = {
    "correctness",
    "security",
    "packaging",
    "compatibility",
    "release",
    "support",
    "evidence",
}
HOST_SURFACES = {
    "codex": ["AGENTS.md", ".codex-plugin/plugin.json", "adapters/prompts/codex.md"],
    "copilot": [".github/copilot-instructions.md", ".github/prompts/tailtrail-start.prompt.md", "adapters/prompts/copilot.md"],
    "claude": ["CLAUDE.md", ".claude/commands/tailtrail-start.md", "adapters/prompts/claude.md"],
}
STATE_LITERAL_PATTERN = re.compile(r"\.tailtrail(?:-install\.json|/[A-Za-z0-9_./{}<>*:-]+)")
PROGRAM_KEYS = {"id", "title", "authority_document", "current_phase", "default_owner", "feature_freeze"}
FREEZE_KEYS = {"state", "until_phase", "allowed_change_classes"}
BASELINE_KEYS = {"captured_at", "git_commit", "branch", "worktree_state", "release_candidate_state", "declaration", "untracked_dispositions"}
DISPOSITION_KEYS = {"path", "disposition", "owner", "reason"}
INVENTORY_CONTRACT_KEYS = {"id", "category", "owner", "surface", "maturity", "sources", "discovery", "validation"}
REQUIREMENT_KEYS = {"id", "title", "category", "owner", "priority", "phase", "dependencies", "implementation_paths", "validation", "acceptance", "evidence", "maturity", "status"}
DEFECT_KEYS = {"id", "requirement_id", "title", "owner", "phase", "status", "evidence"}


def read_json(path: Path) -> Any:
    return json.loads(path.read_text(encoding="utf-8"))


def load_registry(path: Path = REGISTRY_PATH) -> dict[str, Any]:
    value = read_json(path)
    if not isinstance(value, dict):
        raise ValueError("enterprise closure registry root must be an object")
    return value


def load_feature_registry_validator(root: Path):
    path = root / "scripts" / "tailtrail-registry.py"
    spec = importlib.util.spec_from_file_location("tailtrail_feature_registry_for_enterprise", path)
    if spec is None or spec.loader is None:
        raise ValueError(f"unable to load feature registry validator from {path}")
    module = importlib.util.module_from_spec(spec)
    sys.modules[spec.name] = module
    spec.loader.exec_module(module)
    return module


def check_closed_keys(value: dict[str, Any], expected: set[str], label: str, issues: list[str]) -> None:
    for key in sorted(expected - set(value)):
        issues.append(f"{label} missing required key `{key}`")
    for key in sorted(set(value) - expected):
        issues.append(f"{label} has unexpected key `{key}`")


def git_value(root: Path, *arguments: str) -> str | None:
    result = subprocess.run(
        ["git", *arguments],
        cwd=root,
        text=True,
        capture_output=True,
        check=False,
    )
    return result.stdout.strip() if result.returncode == 0 else None


def discover_commands(root: Path) -> list[str]:
    source = (root / "scripts" / "tailtrail.py").read_text(encoding="utf-8")
    tree = ast.parse(source)
    for node in tree.body:
        if not isinstance(node, ast.Assign):
            continue
        if not any(isinstance(target, ast.Name) and target.id == "COMMANDS" for target in node.targets):
            continue
        if not isinstance(node.value, ast.Dict):
            break
        return sorted(
            key.value
            for key in node.value.keys
            if isinstance(key, ast.Constant) and isinstance(key.value, str)
        )
    return []


def discover_schemas(root: Path) -> list[str]:
    return sorted(
        path.relative_to(root).as_posix()
        for path in root.rglob("*.schema.json")
        if ".git" not in path.parts and ".tailtrail" not in path.parts
    )


def discover_adapters(root: Path) -> dict[str, Any]:
    files = sorted(
        path.relative_to(root).as_posix()
        for path in (root / "adapters").rglob("*")
        if path.is_file()
    )
    return {"files": files, "host_surfaces": HOST_SURFACES}


def discover_state_literals(root: Path) -> list[str]:
    values: set[str] = set()
    for path in sorted((root / "scripts").rglob("*.py")):
        try:
            source = path.read_text(encoding="utf-8")
        except UnicodeDecodeError:
            continue
        for value in STATE_LITERAL_PATTERN.findall(source):
            values.add(value.rstrip(".,;:)]}"))
    return sorted(values)


def discover_ci_controls(root: Path) -> list[dict[str, Any]]:
    controls: list[dict[str, Any]] = []
    for path in sorted((root / ".github" / "workflows").glob("*.y*ml")):
        names = []
        for raw in path.read_text(encoding="utf-8").splitlines():
            match = re.match(r"\s*-\s+name:\s*(.+?)\s*$", raw)
            if match:
                names.append(match.group(1).strip('"\''))
        controls.append({"workflow": path.relative_to(root).as_posix(), "named_steps": names})
    return controls


def discover_install_surfaces(root: Path) -> dict[str, Any]:
    local_source = (root / "scripts" / "install-local.py").read_text(encoding="utf-8")
    surface_source = (root / "scripts" / "install_surfaces.py").read_text(encoding="utf-8")
    profiles_match = re.search(r"PROFILES\s*=\s*\((.*?)\)", local_source, re.DOTALL)
    surfaces_match = re.search(r"SURFACES\s*=\s*\((.*?)\)", surface_source, re.DOTALL)

    def literal_tuple(match: re.Match[str] | None) -> list[str]:
        if match is None:
            return []
        value = ast.literal_eval("(" + match.group(1) + ")")
        return sorted(str(item) for item in value)

    return {
        "profiles": literal_tuple(profiles_match),
        "surfaces": literal_tuple(surfaces_match),
        "hosts": sorted(HOST_SURFACES),
    }


def release_file_inventory(root: Path, registry: dict[str, Any]) -> list[dict[str, Any]]:
    contract = next(
        (item for item in registry.get("inventory_contracts", []) if item.get("category") == "release-files"),
        {},
    )
    manifest_path = root / "release-manifest.json"
    if manifest_path.is_file():
        try:
            manifest = json.loads(manifest_path.read_text(encoding="utf-8"))
        except json.JSONDecodeError:
            sources = contract.get("sources", [])
        else:
            sources = manifest.get("required_release_files", [])
    else:
        sources = contract.get("sources", [])
    result = []
    for relative in sources:
        path = root / relative
        result.append({"path": relative, "state": "present" if path.is_file() else "missing"})
    return result


def support_claim_inventory(root: Path, registry: dict[str, Any]) -> list[dict[str, str]]:
    contract = next(
        (item for item in registry.get("inventory_contracts", []) if item.get("category") == "support-claims"),
        {},
    )
    claims: list[dict[str, str]] = []
    for relative in contract.get("sources", []):
        path = root / relative
        if not path.is_file():
            continue
        heading = "document"
        for raw in path.read_text(encoding="utf-8").splitlines():
            if raw.startswith("## "):
                heading = raw[3:].strip()
            elif raw.startswith("- "):
                claims.append({"source": relative, "section": heading, "claim": raw[2:].strip()})
    return claims


def inventory_projection(root: Path, registry: dict[str, Any]) -> dict[str, Any]:
    feature_registry = read_json(root / "tailtrail-registry.json")
    maturity_mapping = registry.get("maturity_mapping", {})
    features = []
    for item in feature_registry.get("features", []):
        if not isinstance(item, dict):
            continue
        features.append(
            {
                "id": item.get("id"),
                "surface": item.get("surface"),
                "feature_status": item.get("status"),
                "enterprise_maturity": maturity_mapping.get(item.get("status")),
                "owner": item.get("owner"),
            }
        )
    return {
        "schema_version": "1",
        "type": "tailtrail-enterprise-baseline-inventory",
        "commands": discover_commands(root),
        "schemas": discover_schemas(root),
        "adapters": discover_adapters(root),
        "persisted_artifacts": discover_state_literals(root),
        "ci_controls": discover_ci_controls(root),
        "install_surfaces": discover_install_surfaces(root),
        "release_files": release_file_inventory(root, registry),
        "support_claims": support_claim_inventory(root, registry),
        "features": features,
    }


def untracked_paths(root: Path) -> list[str]:
    result = subprocess.run(
        ["git", "ls-files", "-o", "--exclude-standard"],
        cwd=root,
        text=True,
        capture_output=True,
        check=False,
    )
    if result.returncode != 0:
        return []
    return sorted(line for line in result.stdout.splitlines() if line)


def worktree_is_dirty(root: Path) -> bool | None:
    result = subprocess.run(
        ["git", "status", "--porcelain"],
        cwd=root,
        text=True,
        capture_output=True,
        check=False,
    )
    return bool(result.stdout.strip()) if result.returncode == 0 else None


def disposition_matches(path: str, declared: str) -> bool:
    return path == declared or (declared.endswith("/") and path.startswith(declared))


def phase_number(phase: str) -> int:
    return int(phase[1:]) if phase in PHASES else 99


def validate_registry(registry: dict[str, Any], root: Path = ROOT) -> list[str]:
    issues: list[str] = []
    expected_root = {
        "schema_version",
        "program",
        "candidate_baseline",
        "maturity_mapping",
        "inventory_contracts",
        "requirements",
        "known_defects",
    }
    if set(registry) != expected_root:
        for key in sorted(expected_root - set(registry)):
            issues.append(f"registry missing required key `{key}`")
        for key in sorted(set(registry) - expected_root):
            issues.append(f"registry has unexpected key `{key}`")
    if registry.get("schema_version") != "1":
        issues.append("schema_version must be `1`")

    program = registry.get("program")
    if not isinstance(program, dict):
        issues.append("program must be an object")
        program = {}
    else:
        check_closed_keys(program, PROGRAM_KEYS, "program", issues)
    authority = program.get("authority_document")
    if not isinstance(authority, str) or not (root / authority).is_file():
        issues.append("program authority_document must reference an existing file")
    if program.get("current_phase") not in PHASES:
        issues.append("program current_phase must be E0 through E12")
    if not isinstance(program.get("default_owner"), str) or not program.get("default_owner"):
        issues.append("program default_owner must be non-empty")
    freeze = program.get("feature_freeze")
    if not isinstance(freeze, dict):
        issues.append("program feature_freeze must be an object")
    else:
        check_closed_keys(freeze, FREEZE_KEYS, "program feature_freeze", issues)
        if freeze.get("state") != "active" or freeze.get("until_phase") != "E12":
            issues.append("feature freeze must remain active through E12")
        classes = freeze.get("allowed_change_classes")
        if not isinstance(classes, list) or set(classes) != ALLOWED_CHANGE_CLASSES:
            issues.append(f"feature freeze allowed_change_classes must equal {sorted(ALLOWED_CHANGE_CLASSES)}")

    mapping = registry.get("maturity_mapping")
    if not isinstance(mapping, dict) or set(mapping) != {"implemented", "planned", "deprecated"}:
        issues.append("maturity_mapping must cover implemented, planned, and deprecated")
        mapping = {}
    for key, value in mapping.items():
        if value not in MATURITY_VALUES:
            issues.append(f"maturity_mapping `{key}` has invalid value `{value}`")

    contracts = registry.get("inventory_contracts")
    if not isinstance(contracts, list):
        issues.append("inventory_contracts must be a list")
        contracts = []
    categories: list[str] = []
    contract_ids: list[str] = []
    for index, contract in enumerate(contracts):
        if not isinstance(contract, dict):
            issues.append(f"inventory_contracts[{index}] must be an object")
            continue
        label = str(contract.get("id", f"inventory_contracts[{index}]"))
        check_closed_keys(contract, INVENTORY_CONTRACT_KEYS, label, issues)
        contract_ids.append(label)
        category = contract.get("category")
        if isinstance(category, str):
            categories.append(category)
        if category not in INVENTORY_CATEGORIES:
            issues.append(f"{label} has invalid inventory category `{category}`")
        for key in ("id", "owner", "surface", "maturity", "discovery", "validation"):
            if not isinstance(contract.get(key), str) or not contract.get(key):
                issues.append(f"{label} {key} must be a non-empty string")
        if contract.get("maturity") not in MATURITY_VALUES:
            issues.append(f"{label} has invalid maturity `{contract.get('maturity')}`")
        sources = contract.get("sources")
        if not isinstance(sources, list) or not sources or any(not isinstance(item, str) or not item for item in sources):
            issues.append(f"{label} sources must be a non-empty string list")
        elif category != "release-files":
            for relative in sources:
                if not (root / relative).exists():
                    issues.append(f"{label} source is missing `{relative}`")
    if set(categories) != INVENTORY_CATEGORIES:
        issues.append(f"inventory categories must equal {sorted(INVENTORY_CATEGORIES)}")
    for duplicate in sorted({item for item in categories if categories.count(item) > 1}):
        issues.append(f"inventory category `{duplicate}` is duplicated")
    for duplicate in sorted({item for item in contract_ids if contract_ids.count(item) > 1}):
        issues.append(f"inventory contract id `{duplicate}` is duplicated")

    requirements = registry.get("requirements")
    if not isinstance(requirements, list) or not requirements:
        issues.append("requirements must be a non-empty list")
        requirements = []
    requirement_ids = [item.get("id") for item in requirements if isinstance(item, dict)]
    valid_ids = {item for item in requirement_ids if isinstance(item, str)}
    for duplicate in sorted({item for item in valid_ids if requirement_ids.count(item) > 1}):
        issues.append(f"requirement id `{duplicate}` is duplicated")
    phases_seen: set[str] = set()
    for index, requirement in enumerate(requirements):
        if not isinstance(requirement, dict):
            issues.append(f"requirements[{index}] must be an object")
            continue
        label = str(requirement.get("id", f"requirements[{index}]"))
        check_closed_keys(requirement, REQUIREMENT_KEYS, label, issues)
        phase = requirement.get("phase")
        if phase in PHASES:
            phases_seen.add(phase)
        else:
            issues.append(f"{label} phase must be E0 through E12")
        if not re.fullmatch(r"ENT-E(?:[0-9]|1[0-2])-[0-9]{3}", label):
            issues.append(f"{label} has invalid requirement id")
        if isinstance(phase, str) and label.startswith("ENT-E") and not label.startswith(f"ENT-{phase}-"):
            issues.append(f"{label} id does not match phase `{phase}`")
        for key in ("title", "category", "owner"):
            if not isinstance(requirement.get(key), str) or not requirement.get(key):
                issues.append(f"{label} {key} must be a non-empty string")
        if requirement.get("priority") not in PRIORITIES:
            issues.append(f"{label} priority must be P0, P1, or P2")
        if requirement.get("maturity") not in MATURITY_VALUES:
            issues.append(f"{label} maturity is invalid")
        if requirement.get("status") not in REQUIREMENT_STATUSES:
            issues.append(f"{label} status is invalid")
        for key in ("implementation_paths", "validation", "acceptance"):
            values = requirement.get(key)
            if not isinstance(values, list) or not values or any(not isinstance(item, str) or not item for item in values):
                issues.append(f"{label} {key} must be a non-empty string list")
        evidence = requirement.get("evidence")
        if not isinstance(evidence, list) or any(not isinstance(item, str) or not item for item in evidence):
            issues.append(f"{label} evidence must be a string list")
        if requirement.get("status") == "complete" and not evidence:
            issues.append(f"{label} complete requirement must record evidence")
        dependencies = requirement.get("dependencies")
        if not isinstance(dependencies, list):
            issues.append(f"{label} dependencies must be a list")
        else:
            for dependency in dependencies:
                if dependency not in valid_ids:
                    issues.append(f"{label} depends on unknown requirement `{dependency}`")
                    continue
                dependency_phase = next(
                    (item.get("phase") for item in requirements if isinstance(item, dict) and item.get("id") == dependency),
                    None,
                )
                if isinstance(phase, str) and isinstance(dependency_phase, str) and phase_number(dependency_phase) > phase_number(phase):
                    issues.append(f"{label} depends on later-phase requirement `{dependency}`")
    if phases_seen != PHASES:
        issues.append(f"requirements must cover every phase E0-E12; missing {sorted(PHASES - phases_seen)}")

    defects = registry.get("known_defects")
    if not isinstance(defects, list):
        issues.append("known_defects must be a list")
        defects = []
    defect_ids: list[str] = []
    for index, defect in enumerate(defects):
        if not isinstance(defect, dict):
            issues.append(f"known_defects[{index}] must be an object")
            continue
        label = str(defect.get("id", f"known_defects[{index}]"))
        check_closed_keys(defect, DEFECT_KEYS, label, issues)
        defect_ids.append(label)
        if defect.get("requirement_id") not in valid_ids:
            issues.append(f"{label} references unknown requirement `{defect.get('requirement_id')}`")
        if defect.get("phase") not in PHASES:
            issues.append(f"{label} has invalid phase")
        if defect.get("status") not in {"open", "closed"}:
            issues.append(f"{label} has invalid status")
        for key in ("title", "owner", "evidence"):
            if not isinstance(defect.get(key), str) or not defect.get(key):
                issues.append(f"{label} {key} must be a non-empty string")
    for duplicate in sorted({item for item in defect_ids if defect_ids.count(item) > 1}):
        issues.append(f"known defect id `{duplicate}` is duplicated")
    if len(defects) < 10:
        issues.append("known_defects must record the five test defects and release/smoke/install/host blockers")

    baseline = registry.get("candidate_baseline")
    if not isinstance(baseline, dict):
        issues.append("candidate_baseline must be an object")
        baseline = {}
    else:
        check_closed_keys(baseline, BASELINE_KEYS, "candidate_baseline", issues)
    actual_commit = git_value(root, "rev-parse", "HEAD")
    actual_branch = git_value(root, "branch", "--show-current")
    if actual_commit is None:
        issues.append("candidate baseline cannot resolve the current Git commit")
    elif baseline.get("git_commit") != actual_commit:
        issues.append(f"candidate baseline commit `{baseline.get('git_commit')}` does not match HEAD `{actual_commit}`")
    if actual_branch is None:
        issues.append("candidate baseline cannot resolve the current Git branch")
    elif baseline.get("branch") != actual_branch:
        issues.append(f"candidate baseline branch `{baseline.get('branch')}` does not match current branch `{actual_branch}`")
    dirty = worktree_is_dirty(root)
    declared_worktree = baseline.get("worktree_state")
    if dirty is None:
        issues.append("candidate baseline cannot resolve the current Git worktree state")
    elif dirty and declared_worktree != "dirty-explicitly-classified":
        issues.append("candidate baseline must declare dirty-explicitly-classified for the current worktree")
    elif not dirty and declared_worktree != "clean":
        issues.append("candidate baseline must declare clean for the current worktree")
    if any(isinstance(item, dict) and item.get("status") == "open" for item in defects) and baseline.get("release_candidate_state") != "blocked":
        issues.append("candidate baseline must remain blocked while known defects are open")
    dispositions = baseline.get("untracked_dispositions")
    if not isinstance(dispositions, list):
        issues.append("candidate_baseline untracked_dispositions must be a list")
        dispositions = []
    declared = []
    for item in dispositions:
        if not isinstance(item, dict):
            issues.append("untracked disposition must be an object")
            continue
        check_closed_keys(item, DISPOSITION_KEYS, f"untracked disposition `{item.get('path', 'unknown')}`", issues)
        for key in ("path", "disposition", "owner", "reason"):
            if not isinstance(item.get(key), str) or not item.get(key):
                issues.append(f"untracked disposition {key} must be non-empty")
        if item.get("disposition") not in {"include", "exclude", "pending-review"}:
            issues.append(f"untracked disposition for `{item.get('path')}` is invalid")
        if isinstance(item.get("path"), str):
            declared.append(item["path"])
    for path in untracked_paths(root):
        if not any(disposition_matches(path, item) for item in declared):
            issues.append(f"untracked path `{path}` has no candidate disposition")

    try:
        projection = inventory_projection(root, registry)
    except (OSError, ValueError, SyntaxError, json.JSONDecodeError) as exc:
        issues.append(f"inventory projection failed: {exc}")
        return issues
    if not projection["commands"]:
        issues.append("command inventory is empty")
    if not projection["schemas"]:
        issues.append("schema inventory is empty")
    for relative in projection["schemas"]:
        try:
            read_json(root / relative)
        except (OSError, json.JSONDecodeError) as exc:
            issues.append(f"schema `{relative}` is not valid JSON: {exc}")
    for host, paths in HOST_SURFACES.items():
        for relative in paths:
            if not (root / relative).is_file():
                issues.append(f"{host} adapter surface is missing `{relative}`")
    if not projection["persisted_artifacts"]:
        issues.append("persisted artifact inventory is empty")
    if not projection["ci_controls"]:
        issues.append("CI control inventory is empty")
    install = projection["install_surfaces"]
    required_profiles = {"codex", "codex-plugin", "copilot", "claude"}
    if not required_profiles.issubset(set(install.get("profiles", []))):
        issues.append("install profile inventory must contain Codex, Codex plugin, Copilot, and Claude")
    if set(install.get("surfaces", [])) != {"core", "extended"}:
        issues.append("install surface inventory must contain exactly core and extended")
    if not projection["support_claims"]:
        issues.append("support claim inventory is empty")

    authority_text = (root / authority).read_text(encoding="utf-8") if isinstance(authority, str) and (root / authority).is_file() else ""
    for phase in sorted(PHASES, key=phase_number):
        if f"### Phase {phase} " not in authority_text:
            issues.append(f"authority document is missing phase `{phase}`")
    if "## 18. Requirement-to-Phase Closure Matrix" not in authority_text:
        issues.append("authority document is missing the requirement-to-phase closure matrix")

    feature_registry = read_json(root / "tailtrail-registry.json")
    try:
        feature_validator = load_feature_registry_validator(root)
        for issue in feature_validator.validate_registry(feature_registry, root):
            issues.append(f"feature registry: {issue}")
    except (OSError, ValueError, ImportError, SyntaxError) as exc:
        issues.append(f"feature registry validation failed: {exc}")
    unknown_maturity = [
        item.get("id")
        for item in feature_registry.get("features", [])
        if isinstance(item, dict) and item.get("status") not in mapping
    ]
    if unknown_maturity:
        issues.append(f"feature maturity is unknown for: {sorted(str(item) for item in unknown_maturity)}")

    return issues


def load_release_manifest_module():
    path = ROOT / "scripts" / "release_manifest.py"
    spec = importlib.util.spec_from_file_location("release_manifest_for_enterprise_readiness", path)
    if spec is None or spec.loader is None:
        raise ValueError(f"unable to load release manifest validator from {path}")
    module = importlib.util.module_from_spec(spec)
    sys.modules[spec.name] = module
    spec.loader.exec_module(module)
    return module


def bundle_digest(value: Any) -> str:
    canonical = json.dumps(value, sort_keys=True, separators=(",", ":"))
    return "sha256:" + hashlib.sha256(canonical.encode("utf-8")).hexdigest()


def requirement_readiness(registry: dict[str, Any]) -> dict[str, Any]:
    requirements = [item for item in registry.get("requirements", []) if isinstance(item, dict)]
    incomplete = [
        {"id": item.get("id"), "status": item.get("status"), "maturity": item.get("maturity")}
        for item in requirements
        if item.get("status") != "complete"
    ]
    return {"total": len(requirements), "complete": len(requirements) - len(incomplete), "incomplete": incomplete}


def defect_readiness(registry: dict[str, Any]) -> dict[str, Any]:
    defects = [item for item in registry.get("known_defects", []) if isinstance(item, dict)]
    open_defects = sorted(item.get("id") for item in defects if item.get("status") != "closed")
    return {"total": len(defects), "closed": len(defects) - len(open_defects), "open": open_defects}


def candidate_readiness(root: Path) -> list[str]:
    module = load_release_manifest_module()
    try:
        manifest = module.load(root)
    except (OSError, ValueError, json.JSONDecodeError) as error:
        return [f"release manifest could not be loaded: {error}"]
    return module.validate(root, manifest)


def ga_release_gate(registry: dict[str, Any], root: Path, *, approved: bool = False) -> dict[str, Any]:
    """Compute the orchestrated E0-E11 GA readiness decision for ENT-E12-001.

    This never fabricates a `ready` decision: every blocking reason is derived
    from the actual registry contents and release manifest, and publication
    additionally requires an explicit caller-supplied `approved=True` decision
    even when every other check is clean.
    """
    registry_issues = validate_registry(registry, root)
    requirement_summary = requirement_readiness(registry)
    defect_summary = defect_readiness(registry)
    candidate_issues = candidate_readiness(root)

    blocking_reasons: list[str] = []
    if registry_issues:
        blocking_reasons.append("registry-invalid")
    if requirement_summary["incomplete"]:
        blocking_reasons.append("incomplete-requirements")
    if defect_summary["open"]:
        blocking_reasons.append("open-defects")
    if candidate_issues:
        blocking_reasons.append("candidate-inconsistent")
    if not approved:
        blocking_reasons.append("not-approved-for-publication")

    payload: dict[str, Any] = {
        "type": "tailtrail-enterprise-ga-bundle",
        "schema_version": "1",
        "generated_at": datetime.now(timezone.utc).isoformat(),
        "source_commit": git_value(root, "rev-parse", "HEAD"),
        "approved": approved,
        "registry_issues": registry_issues,
        "requirement_summary": requirement_summary,
        "defect_summary": defect_summary,
        "candidate_issues": candidate_issues,
        "blocking_reasons": blocking_reasons,
        "decision": "ready" if not blocking_reasons else "blocked",
    }
    payload["bundle_fingerprint"] = bundle_digest(payload)
    return payload


def verify_ga_bundle(bundle: dict[str, Any], registry: dict[str, Any], root: Path) -> dict[str, Any]:
    """Detect tampering and registry drift against a previously produced GA bundle."""
    issues: list[str] = []
    if bundle.get("type") != "tailtrail-enterprise-ga-bundle":
        return {"status": "blocked", "issues": ["not-a-ga-bundle"]}
    stored_fingerprint = bundle.get("bundle_fingerprint")
    recomputed_fingerprint = bundle_digest({key: value for key, value in bundle.items() if key != "bundle_fingerprint"})
    if stored_fingerprint != recomputed_fingerprint:
        issues.append("bundle-fingerprint-invalid")
    fresh = ga_release_gate(registry, root, approved=bool(bundle.get("approved")))
    for key in ("registry_issues", "requirement_summary", "defect_summary", "candidate_issues"):
        if bundle.get(key) != fresh.get(key):
            issues.append("registry-drift-since-bundle")
            break
    return {"status": "blocked" if issues else "passed", "issues": issues}


def render_status(registry: dict[str, Any], issues: list[str]) -> str:
    requirements = [item for item in registry.get("requirements", []) if isinstance(item, dict)]
    counts = {status: sum(item.get("status") == status for item in requirements) for status in sorted(REQUIREMENT_STATUSES)}
    e0 = [item for item in requirements if item.get("phase") == "E0"]
    e0_complete = bool(e0) and all(item.get("status") == "complete" for item in e0)
    current_phase = registry.get("program", {}).get("current_phase", "unknown")
    current = [item for item in requirements if item.get("phase") == current_phase]
    current_complete = bool(current) and all(item.get("status") == "complete" for item in current)
    lines = [
        "# TailTrail Enterprise Readiness",
        "",
        f"- Registry: **{'passed' if not issues else 'failed'}**",
        f"- Current phase: `{registry.get('program', {}).get('current_phase', 'unknown')}`",
        f"- Feature freeze: `{registry.get('program', {}).get('feature_freeze', {}).get('state', 'unknown')}` through `E12`",
        f"- E0 exit gate: **{'passed' if e0_complete and not issues else 'blocked'}**",
        f"- {current_phase} exit gate: **{'passed' if current_complete and not issues else 'blocked'}**",
        f"- Requirements: {len(requirements)} ({', '.join(f'{key}={value}' for key, value in counts.items())})",
        f"- Known defects: {len(registry.get('known_defects', []))}",
    ]
    if issues:
        lines.extend(["", "## Validation issues", "", *[f"- {issue}" for issue in issues]])
    return "\n".join(lines) + "\n"


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--root", type=Path, default=ROOT)
    parser.add_argument("--registry", type=Path, default=REGISTRY_PATH)
    subparsers = parser.add_subparsers(dest="command", required=True)
    validate = subparsers.add_parser("validate")
    validate.add_argument("--format", choices=("text", "json"), default="text")
    status = subparsers.add_parser("status")
    status.add_argument("--format", choices=("markdown", "json"), default="markdown")
    inventory = subparsers.add_parser("inventory")
    inventory.add_argument("--format", choices=("json",), default="json")
    ga_gate = subparsers.add_parser("ga-gate")
    ga_gate.add_argument("--approved", action="store_true")
    ga_gate.add_argument("--write", type=Path, default=None)
    ga_verify = subparsers.add_parser("ga-verify")
    ga_verify.add_argument("--bundle", type=Path, required=True)
    return parser


def main(argv: list[str] | None = None) -> int:
    args = build_parser().parse_args(argv)
    root = args.root.resolve()
    registry = load_registry(args.registry.resolve())
    issues = validate_registry(registry, root)
    if args.command == "inventory":
        print(json.dumps(inventory_projection(root, registry), indent=2, sort_keys=True))
        return 1 if issues else 0
    if args.command == "status":
        if args.format == "json":
            print(json.dumps({"valid": not issues, "issues": issues, "registry": registry}, indent=2, sort_keys=True))
        else:
            print(render_status(registry, issues), end="")
        return 1 if issues else 0
    if args.command == "ga-gate":
        bundle = ga_release_gate(registry, root, approved=args.approved)
        if args.write is not None:
            args.write.write_text(json.dumps(bundle, indent=2, sort_keys=True) + "\n", encoding="utf-8")
        print(json.dumps(bundle, indent=2, sort_keys=True))
        return 0 if bundle["decision"] == "ready" else 1
    if args.command == "ga-verify":
        bundle = read_json(args.bundle.resolve())
        result = verify_ga_bundle(bundle, registry, root)
        print(json.dumps(result, indent=2, sort_keys=True))
        return 0 if result["status"] == "passed" else 1
    if args.format == "json":
        print(json.dumps({"valid": not issues, "issues": issues}, indent=2, sort_keys=True))
    elif issues:
        print("TailTrail enterprise closure registry validation issues:")
        for issue in issues:
            print(f"- {issue}")
    else:
        print("TailTrail enterprise closure registry validation passed.")
    return 1 if issues else 0


if __name__ == "__main__":
    raise SystemExit(main())
