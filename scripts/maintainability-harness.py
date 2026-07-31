#!/usr/bin/env python3
"""Deterministic, requirement-scoped maintainability assessment."""
from __future__ import annotations

import argparse
import ast
import importlib.util
import json
from collections import defaultdict
from pathlib import Path
from typing import Any


ROOT = Path(__file__).resolve().parents[1]


def load_ledger() -> Any:
    spec = importlib.util.spec_from_file_location("maintainability_ledger", ROOT / "scripts" / "run-ledger.py")
    module = importlib.util.module_from_spec(spec)
    assert spec and spec.loader
    spec.loader.exec_module(module)
    return module


LEDGER = load_ledger()


def read_json(path: Path) -> dict[str, Any]:
    return json.loads(path.read_text(encoding="utf-8"))


def relative_path(value: str) -> str:
    path = Path(value)
    if path.is_absolute() or ".." in path.parts:
        raise ValueError("changed paths must be repository-relative")
    return path.as_posix()


def matches(path: str, prefix: str) -> bool:
    return path == prefix or path.startswith(prefix.rstrip("/") + "/")


def is_test_path(path: str) -> bool:
    name = Path(path).name
    return "tests" in Path(path).parts or name.startswith("test_") or name.endswith("_test.py")


def python_symbols(path: Path) -> tuple[list[str], list[dict[str, Any]]]:
    """Return locally parsed definitions and deliberately advisory class signals."""
    if path.suffix != ".py" or not path.is_file():
        return [], []
    try:
        tree = ast.parse(path.read_text(encoding="utf-8"))
    except (SyntaxError, UnicodeDecodeError):
        return [], []
    symbols: list[str] = []
    abstractions: list[dict[str, Any]] = []
    suffixes = ("Adapter", "Factory", "Handler", "Manager", "Validator")
    for node in tree.body:
        if isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef)):
            symbols.append(node.name)
        elif isinstance(node, ast.ClassDef):
            symbols.append(node.name)
            methods = [item for item in node.body if isinstance(item, (ast.FunctionDef, ast.AsyncFunctionDef))]
            if node.name.endswith(suffixes) and len(methods) <= 1:
                abstractions.append({"symbol": node.name, "line": node.lineno, "methods": len(methods)})
    return symbols, abstractions


def assess(root: Path, run_id: str, changed: list[str]) -> dict[str, Any]:
    directory = LEDGER.state_dir(root, run_id)
    anchor = read_json(directory / "anchors" / "approved-v1.json")
    paths = sorted(set(relative_path(item) for item in changed))
    findings: list[dict[str, Any]] = []
    advisories: list[dict[str, Any]] = []
    allowed = sorted({path for row in anchor["requirements"] for path in row.get("likely_paths", [])})

    for path in paths:
        if allowed and not any(matches(path, item) for item in allowed):
            findings.append({"category": "scope", "classification": "new-drift", "path": path, "message": "changed path is outside approved likely paths", "evidence": "approved-anchor"})

    test_paths = [path for path in paths if is_test_path(path)]
    source_paths = [path for path in paths if not is_test_path(path)]
    if test_paths and not source_paths:
        findings.append({"category": "test-chasing", "classification": "needs-decision", "paths": test_paths, "message": "only test paths changed; verify this is not adapting tests to an unfixed requirement", "evidence": "local-path"})

    definitions: dict[str, list[str]] = defaultdict(list)
    for path in source_paths:
        symbols, abstractions = python_symbols(root / path)
        for symbol in symbols:
            definitions[symbol].append(path)
        for item in abstractions:
            advisories.append({"category": "unnecessary-abstraction", "classification": "advisory", "path": path, "message": f"single-method `{item['symbol']}` looks like a specialised abstraction; confirm direct reuse was not enough", "symbol": item["symbol"], "line": item["line"], "evidence": "local-ast-heuristic"})
    for symbol, defined_in in sorted(definitions.items()):
        unique = sorted(set(defined_in))
        if len(unique) > 1:
            advisories.append({"category": "duplicate-logic", "classification": "advisory", "paths": unique, "message": f"`{symbol}` is defined in more than one changed production path; compare for existing reuse", "symbol": symbol, "evidence": "local-ast"})

    payload = {
        "schema_version": "1",
        "type": "tailtrail-maintainability-harness",
        "run_id": run_id,
        "changed_paths": paths,
        "findings": findings,
        "advisories": advisories,
        "complete": not findings,
        "evidence_label": "approved-anchor + local-path + local-ast",
        "boundary": "scope and test-only checks are deterministic; duplicate and abstraction signals are advisory and require source review",
    }
    folder = directory / "maintainability"
    artifact = folder / f"assessment-{len(list(folder.glob('assessment-*.json'))) + 1}.json"
    LEDGER.atomic_json(artifact, payload)
    LEDGER.append_event(root, run_id, "maintainability_assessed", {"artifact": artifact.relative_to(directory).as_posix(), "findings": len(findings), "advisories": len(advisories), "complete": payload["complete"]})
    return payload


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--root", type=Path, default=Path.cwd())
    parser.add_argument("--run-id", required=True)
    parser.add_argument("--changed", action="append", required=True)
    args = parser.parse_args()
    try:
        print(json.dumps(assess(args.root.resolve(), args.run_id, args.changed), indent=2, sort_keys=True))
        return 0
    except (OSError, ValueError, KeyError, json.JSONDecodeError) as error:
        print(f"Maintainability harness error: {error}")
        return 2


if __name__ == "__main__":
    raise SystemExit(main())
