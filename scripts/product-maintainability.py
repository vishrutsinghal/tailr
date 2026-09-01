#!/usr/bin/env python3
"""PM-4 registry inventory, dependency-direction, and documentation-owner checks."""
from __future__ import annotations

import argparse
import ast
import hashlib
import json
from pathlib import Path
from typing import Any


ROOT = Path(__file__).resolve().parents[1]
REGISTRY = "tailtrail-registry.json"
OWNERS = "tailtrail-meta/document-owners-v1.json"
OUTPUT = "tailtrail-meta/maintainability-inventory-v1.json"
PATH_FIELDS = ("docs", "scripts", "tests")


def _read(path: Path) -> dict[str, Any]:
    value = json.loads(path.read_text(encoding="utf-8"))
    if not isinstance(value, dict): raise ValueError(f"{path.name} must contain one JSON object")
    return value


def _digest(value: Any) -> str:
    return hashlib.sha256(json.dumps(value, sort_keys=True, separators=(",", ":")).encode("utf-8")).hexdigest()


def _registry_projection(root: Path, registry: dict[str, Any]) -> tuple[dict[str, Any], list[str]]:
    issues: list[str] = []
    features = registry.get("features") if isinstance(registry.get("features"), list) else []
    ids = {str(item.get("id")) for item in features if isinstance(item, dict)}
    commands: set[str] = set(); mcp_tools: set[str] = set(); paths = {field:set() for field in PATH_FIELDS}
    dependency_graph: dict[str, list[str]] = {}
    ownership: dict[tuple[str, str], set[str]] = {}
    for feature in features:
        if not isinstance(feature, dict): continue
        feature_id = str(feature.get("id", "")); dependency_graph[feature_id] = sorted(str(item) for item in feature.get("depends_on", []))
        for dependency in dependency_graph[feature_id]:
            if dependency not in ids: issues.append(f"feature `{feature_id}` depends on unknown feature `{dependency}`")
        commands.update(str(item) for item in feature.get("commands", [])); mcp_tools.update(str(item) for item in feature.get("mcp_tools", []))
        for field in PATH_FIELDS:
            for item in feature.get(field, []):
                relative = str(item); paths[field].add(relative)
                if not (root / relative).exists(): issues.append(f"feature `{feature_id}` declares missing {field[:-1]} `{relative}`")
                if field == "scripts": ownership.setdefault((field, relative), set()).add(str(feature.get("owner", "")))
    visiting: set[str] = set(); visited: set[str] = set()
    def visit(node: str, trail: tuple[str, ...]) -> None:
        if node in visiting: issues.append("feature dependency cycle: " + " -> ".join((*trail, node))); return
        if node in visited: return
        visiting.add(node)
        for child in dependency_graph.get(node, []): visit(child, (*trail, node))
        visiting.remove(node); visited.add(node)
    for node in sorted(dependency_graph): visit(node, ())
    conflicting = [f"{field}:{path}" for (field,path), owners in ownership.items() if len(owners) > 1]
    if conflicting: issues.extend(f"conflicting registry owners for `{item}`" for item in sorted(conflicting))
    return {"feature_count":len(features),"commands":sorted(commands),"mcp_tools":sorted(mcp_tools),
            "paths":{key:sorted(value) for key,value in paths.items()},"dependency_graph":dependency_graph}, issues


def _imports(path: Path) -> set[str]:
    try: tree = ast.parse(path.read_text(encoding="utf-8"))
    except (OSError, SyntaxError, UnicodeDecodeError): return set()
    result: set[str] = set()
    for node in ast.walk(tree):
        if isinstance(node, ast.Import): result.update(alias.name for alias in node.names)
        elif isinstance(node, ast.ImportFrom) and node.module: result.add(node.module)
    return result


def _module_projection(root: Path) -> tuple[dict[str, Any], list[str], list[str]]:
    issues: list[str] = []; warnings: list[str] = []; rows: list[dict[str, Any]] = []
    files = sorted((root / "scripts" / "orchestration").glob("*.py")) + sorted((root / "scripts" / "workflow_runtime").glob("*.py"))
    for path in files:
        relative = path.relative_to(root).as_posix(); imports = sorted(_imports(path)); line_count = len(path.read_text(encoding="utf-8").splitlines())
        layer = "application" if "/orchestration/" in f"/{relative}" else "domain"
        if layer == "domain" and any(name == "orchestration" or name.startswith("orchestration.") or name == "presentation" for name in imports):
            issues.append(f"domain module `{relative}` imports an outward application/presentation layer")
        if line_count > 500: warnings.append(f"module-budget:{relative}:{line_count}>500")
        rows.append({"path":relative,"layer":layer,"line_count":line_count,"imports":imports})
    return {"module_budget_lines":500,"files":rows}, issues, warnings


def _documentation_projection(root: Path, owners: dict[str, Any]) -> tuple[dict[str, Any], list[str]]:
    issues: list[str] = []; rows = owners.get("owners") if isinstance(owners.get("owners"), list) else []
    seen: set[str] = set()
    for row in rows:
        path = str(row.get("path", "")) if isinstance(row, dict) else ""
        if not path: issues.append("documentation owner entry has no path"); continue
        if path in seen: issues.append(f"documentation owner is duplicated for `{path}`")
        seen.add(path)
        if not str(row.get("owner", "")).strip(): issues.append(f"documentation owner is missing for `{path}`")
        if not (root / path).is_file(): issues.append(f"owned documentation is missing: `{path}`")
    return {"owner_contract":OWNERS,"owners":rows}, issues


def build(root: Path) -> dict[str, Any]:
    root = root.resolve(); registry = _read(root / REGISTRY); owners = _read(root / OWNERS)
    registry_view, registry_issues = _registry_projection(root, registry)
    modules, module_issues, warnings = _module_projection(root)
    documentation, documentation_issues = _documentation_projection(root, owners)
    issues = sorted(set((*registry_issues, *module_issues, *documentation_issues)))
    core = {"schema_version":"1","type":"tailtrail-maintainability-inventory","registry":registry_view,
            "documentation":documentation,"modules":modules,
            "validation":{"status":"passed" if not issues else "failed","issues":issues,"warnings":warnings},
            "boundary":"Deterministic repository metadata and Python-import analysis only; module budgets are warnings and no source is executed or rewritten."}
    return {**core, "fingerprint": _digest(core)}


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__); parser.add_argument("action", choices=("inventory","validate","status")); parser.add_argument("--root",type=Path,default=Path.cwd()); parser.add_argument("--write",action="store_true"); parser.add_argument("--approved",action="store_true"); parser.add_argument("--format",choices=("json",),default="json"); args=parser.parse_args()
    try:
        value=build(args.root)
        if args.write:
            if not args.approved: raise ValueError("--write requires --approved")
            path=args.root.resolve()/OUTPUT; path.parent.mkdir(parents=True,exist_ok=True); path.write_text(json.dumps(value,indent=2,sort_keys=True)+"\n",encoding="utf-8"); value={**value,"artifact":OUTPUT}
        print(json.dumps(value,indent=2,sort_keys=True)); return 0 if value["validation"]["status"]=="passed" else 2
    except (OSError,ValueError,json.JSONDecodeError) as error:
        print(f"TailTrail maintainability error: {error}"); return 2


if __name__ == "__main__": raise SystemExit(main())
