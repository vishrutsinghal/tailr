#!/usr/bin/env python3
"""Deterministic, requirement-scoped maintainability baseline and assessment."""
from __future__ import annotations

import argparse
import ast
import hashlib
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


def _call_name(node: ast.Call) -> str:
    target = node.func
    if isinstance(target, ast.Name):
        return target.id
    if isinstance(target, ast.Attribute):
        parts = [target.attr]
        value = target.value
        while isinstance(value, ast.Attribute):
            parts.append(value.attr)
            value = value.value
        if isinstance(value, ast.Name):
            parts.append(value.id)
        return ".".join(reversed(parts))
    return "<dynamic-call>"


def _functions(tree: ast.Module) -> list[tuple[str, ast.FunctionDef | ast.AsyncFunctionDef]]:
    result: list[tuple[str, ast.FunctionDef | ast.AsyncFunctionDef]] = []
    for node in tree.body:
        if isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef)):
            result.append((node.name, node))
        elif isinstance(node, ast.ClassDef):
            result.extend(
                (f"{node.name}.{item.name}", item)
                for item in node.body
                if isinstance(item, (ast.FunctionDef, ast.AsyncFunctionDef))
            )
    return result


def python_structure(path: Path, relative: str) -> dict[str, Any]:
    if path.suffix != ".py" or not path.is_file():
        return {"symbols": [], "body_members": [], "call_members": [], "abstractions": []}
    try:
        tree = ast.parse(path.read_text(encoding="utf-8"))
    except (SyntaxError, UnicodeDecodeError):
        return {"symbols": [], "body_members": [], "call_members": [], "abstractions": []}
    symbols: list[str] = []
    bodies: list[dict[str, str]] = []
    calls: list[dict[str, Any]] = []
    abstractions: list[dict[str, Any]] = []
    for symbol, node in _functions(tree):
        symbols.append(symbol)
        body = ast.dump(ast.Module(body=node.body, type_ignores=[]), include_attributes=False)
        bodies.append({"fingerprint": hashlib.sha256(body.encode("utf-8")).hexdigest(), "member": f"{relative}:{symbol}"})
        sequence = [_call_name(item) for item in ast.walk(node) if isinstance(item, ast.Call)]
        if len(sequence) >= 2:
            encoded = json.dumps(sequence, separators=(",", ":"))
            calls.append({"fingerprint": hashlib.sha256(encoded.encode("utf-8")).hexdigest(), "member": f"{relative}:{symbol}", "sequence": sequence})
    suffixes = ("Adapter", "Factory", "Handler", "Manager", "Validator")
    for node in tree.body:
        if isinstance(node, ast.ClassDef):
            methods = [item for item in node.body if isinstance(item, (ast.FunctionDef, ast.AsyncFunctionDef))]
            if node.name.endswith(suffixes) and len(methods) <= 1:
                abstractions.append({"symbol": node.name, "line": node.lineno, "methods": len(methods), "path": relative})
    return {"symbols": symbols, "body_members": bodies, "call_members": calls, "abstractions": abstractions}


def _groups(members: list[dict[str, Any]]) -> list[dict[str, Any]]:
    grouped: dict[str, list[dict[str, Any]]] = defaultdict(list)
    for item in members:
        grouped[str(item["fingerprint"])].append(item)
    return [
        {"fingerprint": fingerprint, "members": [row["member"] for row in rows], **({"sequence": rows[0]["sequence"]} if "sequence" in rows[0] else {})}
        for fingerprint, rows in sorted(grouped.items()) if len(rows) > 1
    ]


def structural_snapshot(root: Path, paths: list[str]) -> dict[str, Any]:
    files: list[dict[str, str]] = []
    symbols: list[str] = []
    body_members: list[dict[str, Any]] = []
    call_members: list[dict[str, Any]] = []
    abstractions: list[dict[str, Any]] = []
    inspected: list[str] = []
    for value in sorted(set(paths)):
        relative = relative_path(value)
        path = root / relative
        if is_test_path(relative) or not path.is_file():
            continue
        inspected.append(relative)
        files.append({"path": relative, "sha256": hashlib.sha256(path.read_bytes()).hexdigest()})
        structure = python_structure(path, relative)
        symbols.extend(f"{relative}:{symbol}" for symbol in structure["symbols"])
        body_members.extend(structure["body_members"])
        call_members.extend(structure["call_members"])
        abstractions.extend(structure["abstractions"])
    return {
        "inspected_paths": inspected,
        "file_fingerprints": files,
        "symbols": sorted(symbols),
        "duplicate_function_body_groups": _groups(body_members),
        "duplicate_call_sequence_groups": _groups(call_members),
        "abstraction_candidates": abstractions,
    }


def _contract_paths(anchor: dict[str, Any]) -> list[str]:
    paths: list[str] = []
    for row in anchor.get("requirements", []):
        contract = row.get("maintainability_contract", {})
        candidates = contract.get("candidate_paths", []) if isinstance(contract, dict) else []
        paths.extend(str(value) for value in candidates if value)
        if not candidates:
            paths.extend(str(value) for value in row.get("likely_paths", []) if value)
    return sorted(set(relative_path(value) for value in paths))


def _rules(anchor: dict[str, Any]) -> list[dict[str, Any]]:
    result: list[dict[str, Any]] = []
    for row in anchor.get("requirements", []):
        contract = row.get("maintainability_contract", {})
        for rule in contract.get("rules", []) if isinstance(contract, dict) else []:
            if isinstance(rule, dict):
                result.append({"requirement_uid": row.get("requirement_uid"), **rule})
    return result


def _host_maintainability_evidence(directory: Path) -> set[str]:
    """Return requirement UIDs with an explicit saved host Harness result."""
    path = directory / "execution" / "evidence-stream.jsonl"
    if not path.is_file():
        return set()
    accepted = {"maintainability-improved", "duplication-reduced"}
    result: set[str] = set()
    for line in path.read_text(encoding="utf-8").splitlines():
        try:
            event = json.loads(line)
        except json.JSONDecodeError:
            continue
        if event.get("kind") == "harness-result" and event.get("classification") in accepted:
            result.update(str(value) for value in event.get("requirement_uids", []))
    return result


def capture_baseline(root: Path, run_id: str) -> dict[str, Any]:
    root = root.resolve()
    directory = LEDGER.state_dir(root, run_id)
    path = directory / "maintainability" / "baseline-v1.json"
    if path.is_file():
        return {**read_json(path), "run_artifact": path.relative_to(root).as_posix(), "reused": True}
    anchor = read_json(directory / "anchors" / "approved-v1.json")
    snapshot = structural_snapshot(root, _contract_paths(anchor))
    payload = {
        "schema_version": "1", "type": "tailtrail-maintainability-baseline", "run_id": run_id,
        "anchor_fingerprint": anchor.get("approved_fingerprint"), "snapshot": snapshot,
        "rules": _rules(anchor), "complete": bool(snapshot["inspected_paths"]),
        "evidence_label": "approved-anchor + local-file-sha256 + local-ast",
        "boundary": "Captured after explicit plan approval and before the first managed source edit. Exact structural matches are evidence, not proof that semantically similar business logic is equivalent.",
    }
    LEDGER.atomic_json(path, payload)
    LEDGER.append_event(root, run_id, "maintainability_baseline_captured", {
        "artifact": path.relative_to(directory).as_posix(), "paths": snapshot["inspected_paths"], "complete": payload["complete"],
    })
    return {**payload, "run_artifact": path.relative_to(root).as_posix(), "reused": False}


def assess(root: Path, run_id: str, changed: list[str]) -> dict[str, Any]:
    root = root.resolve()
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
        structure = python_structure(root / path, path)
        for symbol_path in structure["symbols"]:
            definitions[symbol_path.split(".")[-1]].append(path)
        for item in structure["abstractions"]:
            advisories.append({"category": "unnecessary-abstraction", "classification": "advisory", "path": path, "message": f"single-method `{item['symbol']}` looks like a specialised abstraction; confirm direct reuse was not enough", "symbol": item["symbol"], "line": item["line"], "evidence": "local-ast-heuristic"})
    for symbol, defined_in in sorted(definitions.items()):
        unique = sorted(set(defined_in))
        if len(unique) > 1:
            advisories.append({"category": "duplicate-logic", "classification": "advisory", "paths": unique, "message": f"`{symbol}` is defined in more than one changed production path; compare for existing reuse", "symbol": symbol, "evidence": "local-ast"})

    baseline_path = directory / "maintainability" / "baseline-v1.json"
    baseline = read_json(baseline_path) if baseline_path.is_file() else None
    rules = _rules(anchor)
    rule_results: list[dict[str, Any]] = []
    metrics: dict[str, Any] = {}
    if baseline:
        before = baseline["snapshot"]
        current = structural_snapshot(root, before.get("inspected_paths", []) + source_paths)
        metric_names = ("duplicate_function_body_groups", "duplicate_call_sequence_groups")
        metrics = {
            name: {"before": len(before.get(name, [])), "current": len(current.get(name, [])), "delta": len(current.get(name, [])) - len(before.get(name, []))}
            for name in metric_names
        }
        metrics["production_symbols"] = {"before": len(before.get("symbols", [])), "current": len(current.get("symbols", [])), "delta": len(current.get("symbols", [])) - len(before.get("symbols", []))}
        before_abstractions = {(item.get("path"), item.get("symbol")) for item in before.get("abstraction_candidates", [])}
        for item in current.get("abstraction_candidates", []):
            if (item.get("path"), item.get("symbol")) not in before_abstractions:
                advisories.append({"category": "new-abstraction", "classification": "advisory", "message": f"new abstraction candidate `{item.get('symbol')}` requires demonstrated current reuse", "path": item.get("path"), "symbol": item.get("symbol"), "evidence": "baseline-delta + local-ast-heuristic"})
        host_maintainability_evidence = _host_maintainability_evidence(directory)
        for rule in rules:
            state = "preserved"
            evidence = "approved baseline and post-change local structure"
            if rule.get("rule_id") == "MNT-01":
                before_duplicates = sum(metrics[name]["before"] for name in metric_names)
                current_duplicates = sum(metrics[name]["current"] for name in metric_names)
                if before_duplicates > current_duplicates:
                    state = "improved"
                elif before_duplicates > 0:
                    state = "regressed"
                    findings.append({"category": "duplication-not-reduced", "classification": "unchanged" if before_duplicates == current_duplicates else "regressed", "requirement_uid": rule.get("requirement_uid"), "message": "approved exact structural duplication did not decrease", "evidence": "baseline-delta + local-ast"})
                else:
                    if rule.get("requirement_uid") in host_maintainability_evidence:
                        state = "improved"
                        evidence = "requirement-linked host harness result; local AST found no exact group"
                    else:
                        state = "evidence-incomplete"
                        findings.append({"category": "semantic-duplication-proof", "classification": "required-evidence-missing", "requirement_uid": rule.get("requirement_uid"), "message": "the local AST baseline found no exact duplicate group; record a requirement-linked maintainability-improved or duplication-reduced Harness result from focused diff/review evidence", "evidence": "baseline-delta + local-ast-boundary"})
            rule_results.append({"requirement_uid": rule.get("requirement_uid"), "rule_id": rule.get("rule_id"), "state": state, "evidence": evidence})
    elif rules:
        findings.append({"category": "baseline", "classification": "required-evidence-missing", "message": "selected Maintainability rules have no approved pre-edit baseline", "evidence": "approved-maintainability-contract"})
        rule_results = [{"requirement_uid": rule.get("requirement_uid"), "rule_id": rule.get("rule_id"), "state": "evidence-incomplete", "evidence": "baseline missing"} for rule in rules]

    payload = {
        "schema_version": "2", "type": "tailtrail-maintainability-harness", "run_id": run_id,
        "changed_paths": paths, "baseline": baseline_path.relative_to(root).as_posix() if baseline else None,
        "metrics": metrics, "rule_results": rule_results, "findings": findings, "advisories": advisories,
        "complete": not findings,
        "evidence_label": "approved-anchor + local-path + local-file-sha256 + local-ast + baseline-delta",
        "boundary": "Scope, test-only changes, file identity, and exact AST deltas are deterministic. Semantic duplication, abstraction necessity, and behaviour preservation still require requirement-linked diff/review and validation receipts.",
    }
    folder = directory / "maintainability"
    artifact = folder / f"assessment-{len(list(folder.glob('assessment-*.json'))) + 1}.json"
    LEDGER.atomic_json(artifact, payload)
    LEDGER.append_event(root, run_id, "maintainability_assessed", {"artifact": artifact.relative_to(directory).as_posix(), "findings": len(findings), "advisories": len(advisories), "complete": payload["complete"]})
    return {**payload, "run_artifact": artifact.relative_to(root).as_posix()}


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--root", type=Path, default=Path.cwd())
    parser.add_argument("--run-id", required=True)
    parser.add_argument("--changed", action="append", default=[])
    parser.add_argument("--baseline", action="store_true", help="Capture the approved post-approval/pre-edit maintainability baseline.")
    args = parser.parse_args()
    try:
        if args.baseline:
            result = capture_baseline(args.root.resolve(), args.run_id)
        else:
            if not args.changed:
                raise ValueError("assessment requires at least one --changed path; use --baseline for pre-edit capture")
            result = assess(args.root.resolve(), args.run_id, args.changed)
        print(json.dumps(result, indent=2, sort_keys=True))
        return 0
    except (OSError, ValueError, KeyError, json.JSONDecodeError) as error:
        print(f"Maintainability harness error: {error}")
        return 2


if __name__ == "__main__":
    raise SystemExit(main())
