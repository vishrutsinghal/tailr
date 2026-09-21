#!/usr/bin/env python3
"""Create a small, deterministic evidence packet for host-assisted Debug Start.

The preflight reads repository text and explicitly referenced local artifacts.
It never runs project code, tests, package managers, scanners, Git, or external
providers.  Its output is advisory input for one host reasoning pass.
"""
from __future__ import annotations

import argparse
import ast
import hashlib
import html
import json
import re
import time
import tomllib
from pathlib import Path
from typing import Any
from urllib.parse import unquote, urlparse

import code_relationships
import module_resolution
import navigator_scope


SCHEMA_VERSION = "1"
PACKET_TYPE = "tailtrail-debug-preflight"
MAX_SECONDS = 15.0
MAX_FILES_SCANNED = 96
MAX_BYTES_SCANNED = 2_000_000
MAX_EVIDENCE_FILES = 6
MAX_LINES_PER_SLICE = 180
MAX_ARTIFACT_BYTES = 1_000_000
MAX_LOCAL_CALL_EXPANSIONS = 4
MAX_LOCAL_CALL_DEPTH = 2
TEXT_SUFFIXES = {
    ".py", ".js", ".jsx", ".ts", ".tsx", ".java", ".kt", ".go", ".rs",
    ".cs", ".rb", ".php", ".vue", ".svelte", ".feature", ".toml", ".ini",
    ".cfg", ".json", ".yaml", ".yml", ".txt",
}
SKIP_PARTS = {
    ".git", ".tailtrail", "tailtrail-meta", "node_modules", "vendor", "dist",
    "build", "coverage", "reports", ".venv", "venv", "__pycache__", ".idea",
}
STOP_WORDS = {
    "about", "after", "again", "also", "before", "debug", "does", "from",
    "are", "file", "have", "into", "issue", "need", "private", "report",
    "should", "that", "the", "their", "there", "these", "this", "tmp",
    "when", "where", "which", "with", "would",
}
CONFIG_NAMES = {
    "pyproject.toml", "requirements.txt", "requirements-dev.txt", "pytest.ini",
    "setup.cfg", "tox.ini", "package.json", "pom.xml", "build.gradle",
    "build.gradle.kts", "go.mod",
}


def _sha(data: bytes) -> str:
    return "sha256:" + hashlib.sha256(data).hexdigest()


def _goal_terms(goal: str, artifact_anchors: list[dict[str, str]] | None = None) -> list[str]:
    quoted = [value.strip() for value in re.findall(r"[`\"']([^`\"']{3,})[`\"']", goal)]
    words = [
        value.casefold() for value in re.findall(r"[A-Za-z][A-Za-z0-9_-]{2,}", goal)
        if value.casefold() not in STOP_WORDS
    ]
    semantic = []
    lowered = goal.casefold()
    if any(word in lowered for word in ("repeat", "duplicate", "twice")):
        semantic.extend(["duplicate", "repeated", "background", "steps"])
    if any(word in lowered for word in ("html", "report")):
        semantic.extend(["html", "results_table", "reporting"])
    anchors = [
        str(row.get("value", "")).casefold()
        for row in (artifact_anchors or [])
        if str(row.get("value", "")).strip()
    ]
    return list(dict.fromkeys([*anchors, *(value.casefold() for value in quoted), *words, *semantic]))[:36]


def _inventory(root: Path) -> list[str]:
    rows: list[str] = []
    installed_pack = (root / "tailtrail" / "scripts" / "tailtrail.py").is_file()
    for path in root.rglob("*"):
        try:
            relative = path.relative_to(root)
        except ValueError:
            continue
        if any(part in SKIP_PARTS for part in relative.parts) or (installed_pack and relative.parts[:1] == ("tailtrail",)) or not path.is_file():
            continue
        if path.suffix.casefold() in TEXT_SUFFIXES or path.name in CONFIG_NAMES:
            rows.append(relative.as_posix())
    return sorted(rows)


def _path_score(path: str, terms: list[str]) -> int:
    lowered = path.casefold()
    score = sum(8 for term in terms if term in lowered)
    if "/test" in lowered or lowered.startswith("test") or ".spec." in lowered or ".cy." in lowered:
        score += 2
    if Path(path).name in CONFIG_NAMES:
        score += 1
    return score


def _matches(text: str, path: str, terms: list[str]) -> tuple[int, list[int], list[str]]:
    lowered = text.casefold()
    path_lower = path.casefold()
    matched = [term for term in terms if term in lowered or term in path_lower]
    lines = text.splitlines()
    weighted_hits = [
        (sum(1 for term in matched if term in line.casefold()), index)
        for index, line in enumerate(lines, start=1)
        if any(term in line.casefold() for term in matched)
    ]
    line_hits = [index for _weight, index in sorted(weighted_hits, key=lambda item: (-item[0], item[1]))]
    score = len(matched) * 5 + min(len(line_hits), 8)
    if re.search(r"\b(def|class|function|const|let|export|func)\b", text):
        score += 2
    return score, line_hits, matched


def _slice(lines: list[str], hits: list[int]) -> tuple[int, int, str]:
    center = hits[0] if hits else 1
    start = max(1, center - 60)
    end = min(len(lines) or 1, start + MAX_LINES_PER_SLICE - 1)
    return start, end, "\n".join(lines[start - 1:end])


def _symbol_slice(root: Path, path: str, text: str, hits: list[int]) -> tuple[int, int, str, list[str]]:
    """Prefer the smallest owning symbol around the strongest evidence hit."""
    lines = text.splitlines()
    center = hits[0] if hits else 1
    symbols: list[str] = []
    start = max(1, center - 12)
    end = min(len(lines) or 1, center + 36)
    try:
        facts = code_relationships.extract(root / path, root, text)
    except (OSError, ValueError):
        facts = {"definitions": []}
    definitions = [
        row for row in facts.get("definitions", [])
        if isinstance(row, dict) and isinstance(row.get("line"), int)
    ]
    if Path(path).suffix.casefold() == ".py":
        try:
            tree = ast.parse(text)
        except SyntaxError:
            tree = None
        if tree is not None:
            definition_nodes = [
                node for node in ast.walk(tree)
                if isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef, ast.ClassDef))
            ]
            owners = [
                node for node in definition_nodes
                if node.lineno <= center <= int(getattr(node, "end_lineno", node.lineno))
            ]
            if owners:
                owner = min(owners, key=lambda node: int(getattr(node, "end_lineno", node.lineno)) - node.lineno)
                start = max(1, owner.lineno - 3)
                owner_end = int(getattr(owner, "end_lineno", owner.lineno))
                following = [node.lineno for node in definition_nodes if node.lineno > owner_end]
                end = min(
                    len(lines) or 1,
                    owner_end + 2,
                    (min(following) - 1) if following else len(lines) or 1,
                )
                symbols = [owner.name]
    if not symbols and definitions:
        preceding = [row for row in definitions if int(row["line"]) <= center]
        if preceding:
            owner = max(preceding, key=lambda row: int(row["line"]))
            if center - int(owner["line"]) <= 80:
                symbols = [str(owner.get("value", ""))]
                start = max(1, int(owner["line"]) - 3)
                following = [int(row["line"]) for row in definitions if int(row["line"]) > int(owner["line"])]
                end = min(len(lines) or 1, (min(following) - 1) if following else center + 36)
    if end - start + 1 > MAX_LINES_PER_SLICE:
        end = start + MAX_LINES_PER_SLICE - 1
    return start, end, "\n".join(lines[start - 1:end]), [value for value in symbols if value]


def _python_symbol_candidates(root: Path, path: str, text: str, terms: list[str]) -> list[dict[str, Any]]:
    """Return distinct top-level Python symbols that match current evidence."""
    if Path(path).suffix.casefold() != ".py":
        return []
    try:
        tree = ast.parse(text)
    except SyntaxError:
        return []
    lines = text.splitlines()
    rows: list[dict[str, Any]] = []
    for node in tree.body:
        if not isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef, ast.ClassDef)):
            continue
        start = node.lineno
        end = int(getattr(node, "end_lineno", node.lineno))
        excerpt = "\n".join(lines[start - 1:end])
        score, _hits, matched = _matches(excerpt, path, terms)
        if score > 0:
            rows.append({
                "start_line": start,
                "end_line": end,
                "excerpt": excerpt,
                "symbols": [node.name],
                "score": score,
                "matched_terms": matched,
            })
    return sorted(rows, key=lambda row: (-int(row["score"]), int(row["start_line"])))


def _definition_index(
    root: Path,
    source_text: dict[str, tuple[str, bytes]],
) -> dict[str, list[dict[str, Any]]]:
    """Index bounded symbol slices from source that preflight already read."""
    indexed: dict[str, list[dict[str, Any]]] = {}
    for path, (text, data) in source_text.items():
        if not _implementation_capable(path):
            continue
        try:
            facts = code_relationships.extract(root / path, root, text)
        except (OSError, ValueError):
            continue
        definitions = [row for row in facts.get("definitions", []) if isinstance(row, dict)]
        # The shared extractor intentionally keeps JS/TS facts small; include
        # named arrow functions as callable definitions for local expansion.
        if Path(path).suffix.casefold() in {".js", ".jsx", ".ts", ".tsx"}:
            for match in re.finditer(
                r"\b(?:export\s+)?(?:const|let)\s+([A-Za-z_$][\w$]*)[^;=]{0,300}=\s*(?:async\s*)?(?:\([^)]{0,500}\)|[A-Za-z_$][\w$]*)\s*=>",
                text,
            ):
                definitions.append({"value": match.group(1), "line": text.count("\n", 0, match.start()) + 1})
        seen: set[tuple[str, int]] = set()
        for definition in definitions:
            symbol = str(definition.get("value", ""))
            line = definition.get("line")
            if not symbol or not isinstance(line, int) or (symbol, line) in seen:
                continue
            seen.add((symbol, line))
            start, end, excerpt, symbols = _symbol_slice(root, path, text, [line])
            indexed.setdefault(symbol, []).append({
                "path": path,
                "sha256": _sha(data),
                "start_line": start,
                "end_line": end,
                "excerpt": excerpt,
                "symbols": symbols or [symbol],
            })
    return indexed


def _assignment_names(node: ast.AST) -> set[str]:
    names: set[str] = set()
    for item in ast.walk(node):
        if isinstance(item, ast.Name):
            names.add(item.id)
        elif isinstance(item, ast.Attribute):
            names.add(item.attr)
    return names


def _call_name(node: ast.Call) -> str | None:
    return node.func.id if isinstance(node.func, ast.Name) else None


def _value_controlling_calls(path: str, excerpt: str, behavior_symbols: set[str]) -> list[str]:
    """Return direct calls that obviously control an assigned or returned value."""
    calls: list[tuple[int, str]] = []
    suffix = Path(path).suffix.casefold()
    if suffix == ".py":
        try:
            tree = ast.parse(excerpt)
        except SyntaxError:
            return []
        normalized_symbols = {value.casefold().lstrip("_") for value in behavior_symbols}
        for node in ast.walk(tree):
            value: ast.AST | None = None
            priority = 0
            targets: set[str] = set()
            if isinstance(node, ast.Assign):
                value = node.value
                targets = set().union(*(_assignment_names(target) for target in node.targets))
            elif isinstance(node, ast.AnnAssign):
                value = node.value
                targets = _assignment_names(node.target)
            elif isinstance(node, ast.Return):
                value = node.value
                priority = 80
            if value is None:
                continue
            if targets:
                normalized_targets = {value.casefold().lstrip("_") for value in targets}
                if normalized_targets & normalized_symbols or any(value.endswith("steps") for value in normalized_targets):
                    priority = 100
                else:
                    continue
            direct_value = value.value if isinstance(value, ast.Await) else value
            if isinstance(direct_value, ast.Call):
                name = _call_name(direct_value)
                if name:
                    calls.append((priority, name))
    elif suffix in {".js", ".jsx", ".ts", ".tsx"}:
        normalized_symbols = {value.casefold().lstrip("_") for value in behavior_symbols}
        for match in re.finditer(
            r"\b(?:const|let|var)\s+([A-Za-z_$][\w$]*)\s*=\s*(?:await\s+)?([A-Za-z_$][\w$]*)\s*\(",
            excerpt,
        ):
            target, callee = match.group(1), match.group(2)
            normalized = target.casefold().lstrip("_")
            if normalized in normalized_symbols or normalized.endswith("steps"):
                calls.append((100, callee))
        for match in re.finditer(r"\breturn\s+(?:await\s+)?([A-Za-z_$][\w$]*)\s*\(", excerpt):
            calls.append((80, match.group(1)))
    return list(dict.fromkeys(name for _priority, name in sorted(calls, key=lambda row: (-row[0], row[1]))))


def _python_import_bindings(
    importer: str,
    text: str,
    known_paths: set[str],
) -> tuple[dict[str, tuple[str, str]], set[str]]:
    """Resolve explicit repository-local ``from ... import ...`` bindings."""
    try:
        tree = ast.parse(text)
    except SyntaxError:
        return {}, set()
    bindings: dict[str, tuple[str, str]] = {}
    local_names: set[str] = set()
    parent_parts = list(Path(importer).parent.parts)
    for node in tree.body:
        if not isinstance(node, ast.ImportFrom):
            continue
        if node.level:
            keep = max(0, len(parent_parts) - (node.level - 1))
            module_parts = [*parent_parts[:keep], *(node.module or "").split(".")]
        else:
            module_parts = (node.module or "").split(".")
        module_parts = [value for value in module_parts if value]
        variants = ["/".join(module_parts) + ".py", "/".join([*module_parts, "__init__.py"])]
        targets = [value for value in variants if value in known_paths]
        if not targets and module_parts:
            suffix = "/".join(module_parts) + ".py"
            targets = [value for value in known_paths if value.endswith("/" + suffix) or value == suffix]
        if targets:
            local_names.update(alias.asname or alias.name for alias in node.names)
        if len(targets) != 1:
            continue
        for alias in node.names:
            bindings[alias.asname or alias.name] = (targets[0], alias.name)
    return bindings, local_names


def _javascript_import_bindings(
    root: Path,
    importer: str,
    text: str,
    resolver: module_resolution.RepositoryModuleResolver,
) -> tuple[dict[str, tuple[str, str]], set[str]]:
    bindings: dict[str, tuple[str, str]] = {}
    local_names: set[str] = set()
    for match in re.finditer(r"\bimport\s*\{([^}]{1,1000})\}\s*from\s*['\"]([^'\"]+)['\"]", text):
        resolution = resolver.resolve(importer, match.group(2), "import")
        parsed_names = []
        for raw in match.group(1).split(","):
            value = re.sub(r"^\s*type\s+", "", raw.strip())
            pieces = re.split(r"\s+as\s+", value)
            if pieces and re.fullmatch(r"[A-Za-z_$][\w$]*", pieces[-1]):
                parsed_names.append((pieces[-1], pieces[0]))
        if match.group(2).startswith(".") or resolution.candidates:
            local_names.update(local for local, _original in parsed_names)
        if resolution.state != "resolved" or len(resolution.candidates) != 1:
            continue
        for local, original in parsed_names:
            bindings[local] = (resolution.candidates[0], original)
    for match in re.finditer(r"\bimport\s+([A-Za-z_$][\w$]*)\s+from\s*['\"]([^'\"]+)['\"]", text):
        resolution = resolver.resolve(importer, match.group(2), "import")
        if match.group(2).startswith(".") or resolution.candidates:
            local_names.add(match.group(1))
        if resolution.state == "resolved" and len(resolution.candidates) == 1:
            bindings[match.group(1)] = (resolution.candidates[0], match.group(1))
    return bindings, local_names


def _intrinsic_producer(excerpt: str) -> bool:
    lowered = excerpt.casefold()
    return bool(
        re.search(r"\.(?:append|extend|add|update|push)\s*\(", lowered)
        or re.search(r"\b(?:background|scenario)\.steps\b", lowered)
        or re.search(r"\breturn\s+(?:\[|\{|\(|list\s*\(|dict\s*\(|set\s*\()", lowered)
    )


def _demote_forwarding_producer(row: dict[str, Any]) -> None:
    # This helper is called only after a direct assigned/returned local call is
    # found. For that traced value the caller is a transfer/decision node, even
    # when its bounded slice also contains producer-like syntax.
    if "data-producer" not in row.get("behavior_roles", []):
        return
    row["behavior_roles"] = [value for value in row["behavior_roles"] if value != "data-producer"]
    if "data-transfer" not in row["behavior_roles"]:
        row["behavior_roles"].append("data-transfer")


def _expand_repository_local_calls(
    root: Path,
    candidates: list[dict[str, Any]],
    source_text: dict[str, tuple[str, bytes]],
    inventory: list[str],
    artifact_anchors: list[dict[str, str]],
) -> list[str]:
    """Expand obvious value-controlling calls within the existing read budget."""
    definitions = _definition_index(root, source_text)
    known_paths = set(inventory)
    resolver = module_resolution.RepositoryModuleResolver(root, known_paths)
    behavior_symbols = {
        str(row.get("value", ""))
        for row in artifact_anchors
        if row.get("kind") == "behavior-symbol"
    }
    relevant_candidates = [
        row for row in candidates
        if row.get("role") == "implementation-owner"
        and any(symbol.casefold() in row.get("excerpt", "").casefold() for symbol in behavior_symbols)
    ]
    queue_seeds = relevant_candidates or [
        row for row in sorted(candidates, key=lambda item: (-int(item.get("score", 0)), item["path"]))
        if row.get("role") == "implementation-owner"
    ][:3]
    queue = [
        (row, 0)
        for row in queue_seeds
    ]
    expanded = 0
    unresolved: list[str] = []
    visited: set[tuple[str, tuple[str, ...]]] = set()
    while queue and expanded < MAX_LOCAL_CALL_EXPANSIONS:
        caller, depth = queue.pop(0)
        caller_key = (caller["path"], tuple(caller.get("symbols", [])))
        if caller_key in visited or depth >= MAX_LOCAL_CALL_DEPTH:
            continue
        visited.add(caller_key)
        calls = _value_controlling_calls(caller["path"], caller["excerpt"], behavior_symbols)
        if not calls:
            continue
        text = source_text.get(caller["path"], ("", b""))[0]
        suffix = Path(caller["path"]).suffix.casefold()
        bindings, imported_local_names = (
            _python_import_bindings(caller["path"], text, known_paths)
            if suffix == ".py"
            else _javascript_import_bindings(root, caller["path"], text, resolver)
            if suffix in {".js", ".jsx", ".ts", ".tsx"}
            else ({}, set())
        )
        for call in calls:
            same_file = [row for row in definitions.get(call, []) if row["path"] == caller["path"]]
            target_path, target_symbol = bindings.get(call, (caller["path"], call))
            resolved = same_file if len(same_file) == 1 else [
                row for row in definitions.get(target_symbol, []) if row["path"] == target_path
            ]
            if len(resolved) != 1:
                if call in imported_local_names or len(same_file) > 1:
                    for matching_caller in candidates:
                        if matching_caller["path"] == caller["path"] and matching_caller.get("symbols") == caller.get("symbols"):
                            _demote_forwarding_producer(matching_caller)
                    unresolved.append(f"Local call `{call}` from `{caller['path']}` was not uniquely resolved within the bounded source set.")
                continue
            callee = resolved[0]
            existing = next((
                row for row in candidates
                if row["path"] == callee["path"] and tuple(row.get("symbols", [])) == tuple(callee["symbols"])
            ), None)
            roles = _behavior_roles(callee["path"], callee["excerpt"], "inspection", artifact_anchors)
            if roles == ["candidate-only"]:
                roles = ["data-producer" if _intrinsic_producer(callee["excerpt"]) else "data-transfer"]
            elif _intrinsic_producer(callee["excerpt"]) and "data-producer" not in roles:
                roles.append("data-producer")
            relation = {
                "path": caller["path"],
                "symbols": list(caller.get("symbols", [])),
                "callee": call,
            }
            if existing is None:
                existing = {
                    **callee,
                    "role": "implementation-owner",
                    "kind": "source-read",
                    "score": max(100, int(caller.get("score", 0)) + 1),
                    "matched_terms": [call],
                    "behavior_roles": roles,
                    "reason": "bounded repository-local call expansion",
                    "local_call_from": relation,
                }
                candidates.append(existing)
            else:
                existing["role"] = "implementation-owner"
                existing["score"] = max(100, int(existing.get("score", 0)))
                existing["behavior_roles"] = list(dict.fromkeys([*existing.get("behavior_roles", []), *roles]))
                existing["reason"] = "bounded repository-local call expansion"
                existing["local_call_from"] = relation
            for matching_caller in candidates:
                if matching_caller["path"] == caller["path"] and matching_caller.get("symbols") == caller.get("symbols"):
                    _demote_forwarding_producer(matching_caller)
            expanded += 1
            queue.append((existing, depth + 1))
            if expanded >= MAX_LOCAL_CALL_EXPANSIONS:
                break
    if queue and expanded >= MAX_LOCAL_CALL_EXPANSIONS:
        unresolved.append("The bounded repository-local call expansion limit was reached before every controlling call was examined.")
    return list(dict.fromkeys(unresolved))


def _role(path: str) -> tuple[str, str]:
    lowered = path.casefold()
    name = Path(path).name.casefold()
    if name.startswith("test_") or name.endswith("_test.py") or any(marker in name for marker in (".spec.", ".cy.", ".test.")):
        return "proof", "test-read"
    if Path(path).name in CONFIG_NAMES:
        return "configuration", "configuration-read"
    return "inspection", "source-read"


def _behavior_roles(path: str, excerpt: str, repository_role: str, anchors: list[dict[str, str]]) -> list[str]:
    if repository_role == "proof":
        return ["proof"]
    if repository_role == "configuration":
        return ["configuration"]
    lowered = excerpt.casefold()
    roles: list[str] = []
    if (
        any(value in lowered for value in ("html", "render", "results_table", "template", "serialize", "<li", "cells.insert"))
        and any(value in lowered for value in ("return", "insert", "write", "append", "join"))
    ):
        roles.append("output-renderer")
    if any(value in lowered for value in ("getattr(", "setattr(", "report.", "feature_steps", "_bdd_steps")):
        roles.append("data-transfer")
    behavior_symbols = {
        str(row.get("value", "")).casefold()
        for row in anchors
        if row.get("kind") == "behavior-symbol"
    }
    produces_behavior_value = False
    for symbol in behavior_symbols:
        patterns = [
            rf"\b{re.escape(symbol)}\.(?:append|extend)\s*\(",
            rf"setattr\([^\n]{{0,160}}['\"]{re.escape(symbol)}['\"]",
        ]
        if symbol.startswith("_"):
            patterns.append(rf"\.{re.escape(symbol)}\s*=")
        if any(re.search(pattern, lowered) for pattern in patterns):
            produces_behavior_value = True
            break
    if produces_behavior_value or any(value in lowered for value in ("feature.background.steps", "scenario.steps")):
        roles.append("data-producer")
    exact_anchor = any(
        row.get("kind") == "artifact-label" and str(row.get("value", "")).casefold() in lowered
        for row in anchors
    )
    if exact_anchor and Path(path).suffix.casefold() in {".feature", ".json", ".yaml", ".yml"}:
        roles.append("data-producer")
    return list(dict.fromkeys(roles)) or ["candidate-only"]


def _implementation_capable(path: str) -> bool:
    return Path(path).suffix.casefold() in {".py", ".js", ".jsx", ".ts", ".tsx", ".java", ".kt", ".go", ".rs", ".cs", ".rb", ".php", ".vue", ".svelte"}


def _focused_command(root: Path, path: str) -> str | None:
    lowered = path.casefold()
    if path.endswith(".py") and ("/test" in lowered or Path(path).name.startswith("test_")):
        return f"pytest {path} -q"
    if any(marker in lowered for marker in (".cy.", ".spec.", ".test.")):
        package = root / "package.json"
        try:
            scripts = json.loads(package.read_text(encoding="utf-8")).get("scripts", {})
        except (OSError, json.JSONDecodeError, AttributeError):
            scripts = {}
        if ".cy." in lowered:
            for name, value in scripts.items():
                if "cypress" in str(value).casefold() and "component" in str(value).casefold():
                    return f'npm run {name} -- --spec "{path}"'
        if scripts.get("test"):
            return f'npm test -- "{path}"'
    if path.endswith("_test.go"):
        return f"go test ./{Path(path).parent.as_posix()}"
    return None


def _dependency_specs(path: str, text: str) -> list[tuple[str, str]]:
    rows: list[tuple[str, str]] = []
    if Path(path).name.startswith("requirements"):
        for raw in text.splitlines():
            line = raw.strip()
            match = re.match(r"([A-Za-z0-9_.-]+)\s*(.*)$", line)
            if line and not line.startswith("#") and match:
                rows.append((match.group(1).casefold().replace("_", "-"), match.group(2).strip() or "unbounded"))
    elif Path(path).name == "pyproject.toml":
        try:
            dependencies = tomllib.loads(text).get("project", {}).get("dependencies", [])
        except (tomllib.TOMLDecodeError, AttributeError):
            dependencies = []
        for value in dependencies:
            match = re.match(r"([A-Za-z0-9_.-]+)\s*(.*)$", str(value).strip())
            if match:
                rows.append((match.group(1).casefold().replace("_", "-"), match.group(2).strip() or "unbounded"))
    return rows


def _version_tuple(value: str) -> tuple[int, ...]:
    return tuple(int(part) for part in re.findall(r"\d+", value)[:4])


def _spec_status(values: list[tuple[str, str]]) -> str:
    lowers: list[tuple[int, ...]] = []
    uppers: list[tuple[int, ...]] = []
    exact: list[tuple[int, ...]] = []
    for _path, spec in values:
        exact.extend(_version_tuple(value) for value in re.findall(r"==\s*([0-9.]+)", spec))
        lowers.extend(_version_tuple(value) for value in re.findall(r">=?\s*([0-9.]+)", spec))
        uppers.extend(_version_tuple(value) for value in re.findall(r"<\s*([0-9.]+)", spec))
    if exact:
        lowers.extend(exact)
        uppers.extend(tuple([*value[:-1], value[-1] + 1]) for value in exact)
    if lowers and uppers and max(lowers) >= min(uppers):
        return "incompatible-declarations"
    return "different-declarations"


def _artifact_paths(root: Path, goal: str) -> list[Path]:
    """Resolve explicit filesystem and local IDE report URLs without fetching."""
    values = re.findall(r"(?:file|https?)://[^\s)>'\"]+", goal, re.IGNORECASE)
    result: list[Path] = []
    for value in values[:4]:
        parsed = urlparse(value.rstrip(".,"))
        if parsed.scheme.casefold() == "file":
            # urlparse puts a Windows drive letter ("file://C:/path") into
            # netloc, leaving a drive-relative path that resolves against the
            # current drive. Reattach the drive so temp-dir artifacts on one
            # drive resolve while the host runs on another.
            if re.fullmatch(r"[A-Za-z]:", parsed.netloc or ""):
                candidates = [Path(f"{parsed.netloc}{unquote(parsed.path)}")]
            else:
                candidates = [Path(unquote(parsed.path))]
        elif (parsed.hostname or "").casefold() in {"localhost", "127.0.0.1", "::1"}:
            url_path = Path(unquote(parsed.path))
            parts = list(url_path.parts)
            candidates = []
            if root.name in parts:
                index = parts.index(root.name)
                candidates.append(root.joinpath(*parts[index + 1:]))
            else:
                candidates.append(root / str(url_path).lstrip("/"))
            repository_root = root.resolve()
            candidates = [
                candidate
                for candidate in candidates
                if candidate.resolve().is_relative_to(repository_root)
            ]
            if not candidates:
                continue
        else:
            continue
        selected = next((path for path in candidates if path.is_file()), candidates[0])
        if selected not in result:
            result.append(selected)
    return result


def _inspect_artifact(path: Path) -> dict[str, Any]:
    row: dict[str, Any] = {"path": path.as_posix(), "status": "unavailable", "observations": []}
    try:
        size = path.stat().st_size
        if size > MAX_ARTIFACT_BYTES:
            row.update({"status": "skipped-too-large", "size_bytes": size})
            return row
        data = path.read_bytes()
    except OSError as exc:
        row["reason"] = exc.__class__.__name__
        return row
    text = data.decode("utf-8", errors="replace")
    row.update({"status": "inspected", "size_bytes": len(data), "sha256": _sha(data)})
    blob = re.search(r"data-jsonblob=[\"']([^\"']+)", text)
    parsed: Any = None
    if blob:
        try:
            parsed = json.loads(html.unescape(blob.group(1)))
        except json.JSONDecodeError:
            pass
    source = html.unescape(json.dumps(parsed, ensure_ascii=False) if parsed is not None else text)
    repeated: list[str] = []
    step_lists = re.findall(r"<ol[^>]*class=[^>]*feature-steps-list[^>]*>(.*?)</ol>", source, re.I | re.S)
    for block in step_lists:
        labels = re.findall(r"<strong>([^<]{1,160})</strong>", block)
        normalized = [html.unescape(re.sub(r"\s+", " ", value)).strip() for value in labels]
        for start in range(len(normalized)):
            for width in range(2, min(12, (len(normalized) - start) // 2) + 1):
                if normalized[start:start + width] == normalized[start + width:start + width * 2] and width > len(repeated):
                    repeated = normalized[start:start + width]
    if repeated:
        row["observations"].append({"type": "adjacent-repeated-prefix", "count": len(repeated), "labels": repeated})
    versions: dict[str, str] = {}
    if isinstance(parsed, dict) and isinstance(parsed.get("environment"), dict):
        environment = parsed["environment"]
        if environment.get("Python"):
            versions["Python"] = str(environment["Python"])
        packages = environment.get("Packages", {})
        plugins = environment.get("Plugins", {})
        if isinstance(packages, dict) and packages.get("pytest"):
            versions["pytest"] = str(packages["pytest"])
        if isinstance(plugins, dict) and plugins.get("bdd"):
            versions["pytest-bdd"] = str(plugins["bdd"])
    if not versions:
        versions = dict(re.findall(r"[\"'](pytest(?:-bdd)?|python)[\"']\s*[:,]\s*[\"']([^\"']+)", source, re.I))
    if versions:
        row["environment"] = versions
    return row


def _artifact_anchors(artifacts: list[dict[str, Any]]) -> list[dict[str, str]]:
    """Extract public search anchors from inspected evidence before repository discovery."""
    anchors: list[dict[str, str]] = []
    for artifact in artifacts:
        if artifact.get("status") != "inspected":
            continue
        source = str(artifact.get("path", ""))
        for observation in artifact.get("observations", []):
            if not isinstance(observation, dict):
                continue
            if observation.get("type") == "adjacent-repeated-prefix":
                anchors.extend({"kind": "artifact-label", "value": str(label), "source": source} for label in observation.get("labels", []))
                anchors.extend(
                    {"kind": "behavior-symbol", "value": value, "source": source}
                    for value in ("feature_steps", "_bdd_steps", "results_table")
                )
        for name in (artifact.get("environment") or {}):
            anchors.append({"kind": "environment", "value": str(name), "source": source})
    unique: list[dict[str, str]] = []
    seen: set[tuple[str, str]] = set()
    for row in anchors:
        key = (row["kind"], row["value"].casefold())
        if row["value"].strip() and key not in seen:
            seen.add(key)
            unique.append(row)
    return unique


def _behavior_graph_topology(nodes: list[dict[str, Any]], edges: list[dict[str, str]]) -> dict[str, Any]:
    behavior = {
        row["id"]: row for row in nodes
        if row["role"] in {"observed-output", "output-renderer", "data-transfer", "data-producer"}
    }
    flow = [row for row in edges if row["relationship"] != "exercises" and row["from"] in behavior and row["to"] in behavior]
    outgoing = {node_id: [] for node_id in behavior}
    incoming = {node_id: [] for node_id in behavior}
    undirected = {node_id: set() for node_id in behavior}
    for edge in flow:
        outgoing[edge["from"]].append(edge["to"])
        incoming[edge["to"]].append(edge["from"])
        undirected[edge["from"]].add(edge["to"])
        undirected[edge["to"]].add(edge["from"])
    observed = [node_id for node_id, row in behavior.items() if row["role"] == "observed-output"]
    entries = observed or [node_id for node_id in behavior if not incoming[node_id]]
    terminals = sorted(node_id for node_id in behavior if not outgoing[node_id])
    branches = sorted(node_id for node_id in behavior if len(outgoing[node_id]) > 1)
    merges = sorted(node_id for node_id in behavior if len(incoming[node_id]) > 1)
    unseen = set(behavior)
    components = 0
    while unseen:
        components += 1
        pending = [next(iter(unseen))]
        while pending:
            node_id = pending.pop()
            if node_id in unseen:
                unseen.remove(node_id)
                pending.extend(undirected[node_id] & unseen)
    indegree = {node_id: len(incoming[node_id]) for node_id in behavior}
    pending = [node_id for node_id, count in indegree.items() if count == 0]
    visited = 0
    while pending:
        node_id = pending.pop()
        visited += 1
        for target in outgoing[node_id]:
            indegree[target] -= 1
            if indegree[target] == 0:
                pending.append(target)
    cyclic = visited != len(behavior)
    path_count = 0
    capped = False

    def count_paths(node_id: str, active: set[str]) -> None:
        nonlocal path_count, capped
        if capped or node_id in active:
            return
        if not outgoing[node_id]:
            path_count += 1
            capped = path_count >= 64
            return
        for target in outgoing[node_id]:
            count_paths(target, active | {node_id})

    for entry in entries:
        count_paths(entry, set())
    shape = (
        "cyclic" if cyclic else "disconnected" if components > 1
        else "branching-and-converging" if branches and merges
        else "branching" if branches else "converging" if merges else "linear"
    )
    return {
        "shape": shape,
        "entry_node_ids": sorted(entries),
        "terminal_node_ids": terminals,
        "branch_node_ids": branches,
        "merge_node_ids": merges,
        "component_count": components,
        "cyclic": cyclic,
        "path_count": path_count,
        "path_count_capped": capped,
    }


def _behavior_trace(
    artifacts: list[dict[str, Any]],
    evidence: list[dict[str, Any]],
    unresolved_local_calls: list[str] | None = None,
) -> dict[str, Any]:
    """Build a public output-to-producer graph without claiming root cause."""
    nodes: list[dict[str, Any]] = []
    edges: list[dict[str, str]] = []
    artifact_node: str | None = None
    inspected = next((row for row in artifacts if row.get("status") == "inspected"), None)
    if inspected:
        artifact_node = "TRACE-N1"
        nodes.append({
            "id": artifact_node,
            "role": "observed-output",
            "path": str(inspected.get("path", "")),
            "evidence_id": None,
        })
    role_nodes: dict[str, list[str]] = {}
    evidence_by_id = {str(row.get("id")): row for row in evidence}
    for row in evidence:
        roles = set(row.get("behavior_roles", []))
        behavior_role = (
            "proof" if "proof" in roles
            else "output-renderer" if "output-renderer" in roles
            else "data-producer" if "data-producer" in roles
            else "data-transfer" if "data-transfer" in roles
            else None
        )
        if behavior_role is None:
            continue
        node_id = f"TRACE-N{len(nodes) + 1}"
        nodes.append({
            "id": node_id,
            "role": behavior_role,
            "repository_role": row.get("suggested_role"),
            "path": row["path"],
            "symbols": list(row.get("symbols", [])),
            "evidence_id": row["id"],
        })
        role_nodes.setdefault(behavior_role, []).append(node_id)

    node_by_id = {row["id"]: row for row in nodes}

    def tokens(node_id: str) -> set[str]:
        evidence_row = evidence_by_id.get(str(node_by_id[node_id].get("evidence_id")), {})
        return {
            value.casefold()
            for value in re.findall(r"\b[A-Za-z_][A-Za-z0-9_]*steps\b", str(evidence_row.get("excerpt", "")), re.IGNORECASE)
        }

    def best_related(current: str, candidates: list[str]) -> str | None:
        ranked = sorted(
            ((len(tokens(current) & tokens(candidate)), candidate) for candidate in candidates),
            key=lambda row: (-row[0], row[1]),
        )
        return ranked[0][1] if ranked and ranked[0][0] > 0 else None

    edge_index = 1
    renderer = next(iter(role_nodes.get("output-renderer", [])), None)
    transfers = list(role_nodes.get("data-transfer", []))
    owner_producers = [value for value in role_nodes.get("data-producer", []) if node_by_id[value].get("repository_role") == "implementation-owner"]
    if artifact_node and renderer:
        edges.append({"id": f"TRACE-E{edge_index}", "from": artifact_node, "to": renderer, "relationship": "rendered-by"})
        edge_index += 1
    current = renderer
    chain = [renderer] if renderer else []
    remaining = list(transfers)
    while current and remaining:
        following = best_related(current, remaining)
        if following is None:
            break
        edges.append({
            "id": f"TRACE-E{edge_index}",
            "from": current,
            "to": following,
            "relationship": "reads-from" if current == renderer else "receives-from",
        })
        edge_index += 1
        chain.append(following)
        remaining.remove(following)
        current = following

    connected_producers: list[str] = []
    for candidate in owner_producers:
        evidence_row = evidence_by_id.get(str(node_by_id[candidate].get("evidence_id")), {})
        relation = evidence_row.get("local_call_from") if isinstance(evidence_row.get("local_call_from"), dict) else {}
        caller_symbols = set(relation.get("symbols", []))
        caller_node = next((
            node_id for node_id in chain
            if node_by_id[node_id].get("path") == relation.get("path")
            and caller_symbols.intersection(node_by_id[node_id].get("symbols", []))
        ), None)
        if caller_node and caller_node != candidate:
            relationship = "reads-from" if node_by_id[caller_node].get("role") == "output-renderer" else "receives-from"
            edges.append({"id": f"TRACE-E{edge_index}", "from": caller_node, "to": candidate, "relationship": relationship})
            edge_index += 1
            connected_producers.append(candidate)
    if not connected_producers and current:
        producer = best_related(current, owner_producers)
        if producer is None and len(owner_producers) == 1:
            producer = owner_producers[0]
        if producer and current != producer:
            relationship = "reads-from" if node_by_id[current].get("role") == "output-renderer" else "receives-from"
            edges.append({"id": f"TRACE-E{edge_index}", "from": current, "to": producer, "relationship": relationship})
            connected_producers.append(producer)
            edge_index += 1
    for producer in connected_producers:
        if producer not in chain:
            chain.append(producer)
    proof = next(iter(role_nodes.get("proof", [])), None)
    proof_target = renderer or next(iter(connected_producers), None) or next(iter(transfers), None)
    if proof and proof_target:
        edges.append({"id": f"TRACE-E{edge_index}", "from": proof, "to": proof_target, "relationship": "exercises"})
    divergence = [value for value in owner_producers] or [
        row["id"] for row in nodes
        if row.get("repository_role") == "implementation-owner" and row.get("role") in {"data-transfer", "output-renderer"}
    ]
    topology = _behavior_graph_topology(nodes, edges)
    terminal_roles = {
        node_by_id[node_id].get("role")
        for node_id in topology["terminal_node_ids"]
    }
    resolved = bool(
        artifact_node
        and renderer
        and connected_producers
        and not unresolved_local_calls
        and topology["component_count"] == 1
        and not topology["cyclic"]
        and terminal_roles == {"data-producer"}
    )
    return {
        "direction": "observed-output-to-producer",
        "state": "resolved-to-producer" if resolved else "partial",
        "nodes": nodes,
        "edges": edges,
        "divergence_candidates": divergence,
        "topology": topology,
        "boundary": "This behavior graph identifies evidence-backed roles, branches, merges, and possible divergence points; it does not prove root cause or grant correction authority.",
    }


def _safe_fallback(
    behavior_trace: dict[str, Any],
    artifacts: list[dict[str, Any]],
    commands: list[dict[str, Any]],
) -> dict[str, Any]:
    """Choose the fail-safe next route without inventing correction scope."""
    trace_partial = behavior_trace.get("state") != "resolved-to-producer"
    reproduction_sources = []
    if artifacts:
        reproduction_sources.append("supplied-artifact")
    if commands:
        reproduction_sources.append("focused-proof-command")
    if not trace_partial:
        state = "not-needed"
        trigger = "trace-resolved"
        user_input = "not-required"
        next_action = "Prepare the bounded reproduction after Planning Lock approval."
    elif reproduction_sources:
        state = "continue-approved-debug-investigation"
        trigger = "local-helper-unresolved"
        user_input = "not-required"
        next_action = "Preserve the partial trace and continue to the approved reproduction; do not infer correction scope."
    else:
        state = "awaiting-reproduction-input"
        trigger = "reproduction-and-external-context-unavailable"
        user_input = "required"
        next_action = "Ask only for the smallest reproduction command, artifact, or external observation needed to continue."
    return {
        "state": state,
        "trigger": trigger,
        "trace_state": behavior_trace.get("state", "partial"),
        "correction_scope": "blocked",
        "user_input": user_input,
        "reproduction_sources": reproduction_sources,
        "next_action": next_action,
        "boundary": "A partial preflight trace is orientation evidence only. It cannot select correction scope or justify a source edit.",
    }


def build(root: Path, goal: str, host: str) -> dict[str, Any]:
    started = time.monotonic()
    root = root.resolve()
    # Evidence comes first: repository discovery is framed by what the user
    # actually supplied, not by broad filename or goal-word matching alone.
    artifacts = [_inspect_artifact(path) for path in _artifact_paths(root, goal)]
    artifact_anchors = _artifact_anchors(artifacts)
    terms = _goal_terms(goal, artifact_anchors)
    inventory = _inventory(root)
    ordered = sorted(inventory, key=lambda path: (-_path_score(path, terms), path))
    candidates: list[dict[str, Any]] = []
    config_text: dict[str, str] = {}
    source_text: dict[str, tuple[str, bytes]] = {}
    files_scanned = 0
    bytes_scanned = 0
    termination = "inventory-exhausted"
    for path in ordered:
        if files_scanned >= MAX_FILES_SCANNED:
            termination = "file-scan-budget-reached"
            break
        if time.monotonic() - started > MAX_SECONDS:
            termination = "time-budget-reached"
            break
        target = root / path
        try:
            data = target.read_bytes()
        except OSError:
            continue
        if bytes_scanned + len(data) > MAX_BYTES_SCANNED:
            termination = "byte-scan-budget-reached"
            break
        files_scanned += 1
        bytes_scanned += len(data)
        text = data.decode("utf-8", errors="ignore")
        source_text[path] = (text, data)
        if Path(path).name in CONFIG_NAMES:
            config_text[path] = text
        score, hits, matched = _matches(text, path, terms)
        if score <= 0 and Path(path).name not in CONFIG_NAMES:
            continue
        start, end, excerpt, symbols = _symbol_slice(root, path, text, hits)
        slice_score, _slice_hits, slice_matched = _matches(excerpt, path, terms)
        if symbols:
            score, matched = slice_score, slice_matched
        role, kind = _role(path)
        behavior_roles = _behavior_roles(path, excerpt, role, artifact_anchors)
        if role == "inspection" and _implementation_capable(path) and any(value in behavior_roles for value in ("output-renderer", "data-transfer", "data-producer")):
            role = "implementation-owner"
        if role == "configuration" and (Path(path).name == "pyproject.toml" or Path(path).name.startswith("requirements")):
            score += 20
        candidates.append({
            "path": path, "sha256": _sha(data), "role": role, "kind": kind,
            "score": score, "matched_terms": matched, "start_line": start,
            "end_line": end, "excerpt": excerpt, "symbols": symbols,
            "behavior_roles": behavior_roles,
        })
        if role not in {"proof", "configuration"}:
            for symbol_row in _python_symbol_candidates(root, path, text, terms):
                if symbol_row["symbols"] == symbols:
                    continue
                symbol_roles = _behavior_roles(path, str(symbol_row["excerpt"]), "inspection", artifact_anchors)
                symbol_role = "implementation-owner" if _implementation_capable(path) and set(symbol_roles).intersection({"output-renderer", "data-transfer", "data-producer"}) else "inspection"
                candidates.append({
                    "path": path,
                    "sha256": _sha(data),
                    "role": symbol_role,
                    "kind": "source-read",
                    "score": int(symbol_row["score"]),
                    "matched_terms": symbol_row["matched_terms"],
                    "start_line": symbol_row["start_line"],
                    "end_line": symbol_row["end_line"],
                    "excerpt": symbol_row["excerpt"],
                    "symbols": symbol_row["symbols"],
                    "behavior_roles": symbol_roles,
                })

    local_call_unresolved = _expand_repository_local_calls(
        root,
        candidates,
        source_text,
        inventory,
        artifact_anchors,
    )

    # Follow concrete values seen at the renderer/transfer boundary back to
    # assignments or collection mutations in the already-read source. This is
    # a relationship pass over current evidence, not another repository scan.
    artifact_behavior_symbols = {
        str(row.get("value", ""))
        for row in artifact_anchors
        if row.get("kind") == "behavior-symbol"
    }
    trace_tokens = list(dict.fromkeys([
        *artifact_behavior_symbols,
        *(
            value
            for row in candidates
            if set(row["behavior_roles"]).intersection({"output-renderer", "data-transfer"})
            for value in re.findall(r"\b[A-Za-z_][A-Za-z0-9_]*_steps\b", row["excerpt"])
            if value.casefold() not in {"rendered_steps"}
        ),
    ]))[:12]
    traced_keys = {(row["path"], row["start_line"], row["end_line"]) for row in candidates}
    traced_symbol_keys = {
        (row["path"], tuple(row.get("symbols", [])))
        for row in candidates
        if row.get("symbols")
    }
    for token in trace_tokens:
        producer_patterns = [
            rf"setattr\([^\n]{{0,160}}['\"]{re.escape(token)}['\"]",
            rf"\b{re.escape(token)}\.(?:append|extend)\s*\(",
        ]
        if token.startswith("_"):
            producer_patterns.append(rf"\.{re.escape(token)}\s*=")
        token_pattern = re.compile("(?:" + "|".join(producer_patterns) + ")", re.IGNORECASE)
        for path, (text, data) in source_text.items():
            if not _implementation_capable(path):
                continue
            match = token_pattern.search(text)
            if not match:
                continue
            line = text.count("\n", 0, match.start()) + 1
            start, end, excerpt, symbols = _symbol_slice(root, path, text, [line])
            key = (path, start, end)
            symbol_key = (path, tuple(symbols))
            if key in traced_keys or (symbols and symbol_key in traced_symbol_keys):
                continue
            traced_keys.add(key)
            if symbols:
                traced_symbol_keys.add(symbol_key)
            repository_role, kind = _role(path)
            behavior_roles = _behavior_roles(path, excerpt, repository_role, artifact_anchors)
            if "data-producer" not in behavior_roles:
                behavior_roles = [*behavior_roles, "data-producer"]
            candidates.append({
                "path": path,
                "sha256": _sha(data),
                "role": "implementation-owner",
                "kind": kind,
                "score": 100,
                "matched_terms": [token],
                "start_line": start,
                "end_line": end,
                "excerpt": excerpt,
                "symbols": symbols,
                "behavior_roles": list(dict.fromkeys(behavior_roles)),
            })

    # Tests coupled by a production module stem outrank unrelated lexical test hits.
    primary_owners = sorted(
        (row for row in candidates if row["role"] == "implementation-owner" and row["score"] > 0),
        key=lambda row: (-row["score"], row["path"]),
    )[:1]
    production_stems = {Path(row["path"]).stem.casefold().removesuffix("_reporting") for row in primary_owners}
    for row in candidates:
        if row["role"] == "proof" and any(
            stem and (stem in row["path"].casefold() or stem in row["excerpt"].casefold())
            for stem in production_stems
        ):
            row["score"] += 30
    selected: list[dict[str, Any]] = []
    selected_keys: set[tuple[Any, ...]] = set()
    for role in ("implementation-owner", "proof", "configuration", "inspection"):
        role_candidates = [item for item in candidates if item["role"] == role]
        if role == "implementation-owner":
            ordered_role_candidates: list[dict[str, Any]] = []
            for behavior_role in ("output-renderer", "data-transfer", "data-producer"):
                matching = sorted(
                    (item for item in role_candidates if behavior_role in item["behavior_roles"]),
                    key=lambda item: (
                        -sum(1 for term in item.get("matched_terms", []) if term in artifact_behavior_symbols),
                        -item["score"],
                        item["path"],
                        item["start_line"],
                    ),
                )
                if matching and matching[0] not in ordered_role_candidates:
                    ordered_role_candidates.append(matching[0])
            ordered_role_candidates.extend(
                row for row in sorted(
                    role_candidates,
                    key=lambda item: (
                        -sum(
                            1 for term in item.get("matched_terms", [])
                            if term in artifact_behavior_symbols
                        ),
                        0 if item.get("local_call_from") else 1,
                        -item["score"],
                        item["path"],
                        item["start_line"],
                    ),
                )
                if row not in ordered_role_candidates
            )
        else:
            ordered_role_candidates = sorted(role_candidates, key=lambda item: (-item["score"], item["path"], item["start_line"]))
        for row in ordered_role_candidates:
            if row["score"] <= 0 and role != "configuration":
                continue
            key = (
                row["path"],
                tuple(row.get("symbols", [])),
            ) if row.get("symbols") else (row["path"], row["start_line"], row["end_line"])
            if key not in selected_keys:
                selected.append(row)
                selected_keys.add(key)
            role_limit = 4 if role == "implementation-owner" else 2 if role == "configuration" else 1
            if len([item for item in selected if item["role"] == role]) >= role_limit:
                break
    selected = selected[:MAX_EVIDENCE_FILES]
    evidence = []
    commands = []
    for index, row in enumerate(selected, start=1):
        command = _focused_command(root, row["path"]) if row["role"] == "proof" else None
        if command:
            commands.append({"path": row["path"], "command": command, "tier": "regression"})
        evidence.append({
            "id": f"PF-E{index}", "path": row["path"], "sha256": row["sha256"],
            "suggested_role": row["role"], "kind": row["kind"],
            "start_line": row["start_line"], "end_line": row["end_line"],
            "symbols": row["symbols"], "behavior_roles": row["behavior_roles"],
            "matched_terms": row["matched_terms"],
            "reason": row.get("reason", "artifact-framed query and static behavior-role match"),
            "excerpt": row["excerpt"],
            **({"local_call_from": row["local_call_from"]} if row.get("local_call_from") else {}),
            **({"command": command} if command else {}),
        })

    specs: dict[str, list[tuple[str, str]]] = {}
    for path, text in config_text.items():
        for name, spec in _dependency_specs(path, text):
            specs.setdefault(name, []).append((path, spec))
    config_findings = [
        {"dependency": name, "declarations": [{"path": path, "specifier": spec} for path, spec in values], "status": _spec_status(values)}
        for name, values in sorted(specs.items())
        if len({spec for _path, spec in values}) > 1
    ]
    observed_repeat = next((obs for item in artifacts for obs in item.get("observations", []) if obs.get("type") == "adjacent-repeated-prefix"), None)
    requirement_observations = []
    if observed_repeat:
        requirement_observations.append(
            f"The supplied artifact contains {observed_repeat['count']} adjacent step labels repeated twice."
        )
    behavior_trace = _behavior_trace(artifacts, evidence, local_call_unresolved)
    safe_fallback = _safe_fallback(behavior_trace, artifacts, commands)
    unresolved = list(local_call_unresolved) if evidence else ["No current-source evidence matched the artifact-framed debug query."]
    if behavior_trace["state"] != "resolved-to-producer":
        unresolved.append("The backward behavior trace did not yet reach a supported data producer.")
    reuse_key = _sha(json.dumps({
        "root": root.as_posix(),
        "goal_fingerprint": _sha(goal.encode("utf-8")),
        "artifacts": [(row.get("path"), row.get("sha256")) for row in artifacts],
        "evidence": [(row["path"], row["sha256"], row["start_line"], row["end_line"]) for row in evidence],
    }, sort_keys=True, separators=(",", ":")).encode("utf-8"))
    elapsed_ms = round((time.monotonic() - started) * 1000)
    packet = {
        "schema_version": SCHEMA_VERSION,
        "type": PACKET_TYPE,
        "root": root.as_posix(),
        "host": host,
        "goal_fingerprint": _sha(goal.encode("utf-8")),
        "status": "complete" if evidence and not local_call_unresolved else "partial",
        "requirement_observations": requirement_observations,
        "artifacts": artifacts,
        "artifact_anchors": artifact_anchors,
        "evidence": evidence,
        "behavior_trace": behavior_trace,
        "safe_fallback": safe_fallback,
        "reuse_key": reuse_key,
        "configuration_findings": config_findings,
        "suggested_test_commands": commands,
        "unresolved": unresolved,
        "metrics": {
            "elapsed_ms": elapsed_ms, "files_considered": len(inventory),
            "files_read": files_scanned, "evidence_files": len(evidence),
            "bytes_read": bytes_scanned, "estimated_tokens": (sum(len(row["excerpt"]) for row in evidence) + 3) // 4,
            "file_scan_limit": MAX_FILES_SCANNED, "byte_scan_limit": MAX_BYTES_SCANNED,
            "evidence_file_limit": MAX_EVIDENCE_FILES, "line_slice_limit": MAX_LINES_PER_SLICE,
            "termination_reason": termination,
        },
        "host_contract": {
            "max_reasoning_passes": 1,
            "instruction": "Use only this artifact-first packet for one reasoning pass. Return the closed tailtrail-host-debug-diagnosis proposal with validated evidence, trace, finding, and test IDs. Preserve a partial trace, block correction scope, and continue to approved reproduction whenever the packet contains a reproduction source; request user evidence only when reproduction and external context are both unavailable. Do not return unrestricted reasoning, rescan, claim root cause, or request execution authority.",
        },
    }
    packet["packet_fingerprint"] = _sha(json.dumps(packet, sort_keys=True, separators=(",", ":")).encode("utf-8"))
    return packet


def render_markdown(packet: dict[str, Any]) -> str:
    metrics = packet["metrics"]
    lines = [
        "# TailTrail Debug Preflight", "",
        f"Status: **{packet['status']}**", "",
        f"- Packet: `{packet['packet_fingerprint']}`",
        f"- Reuse key: `{packet['reuse_key']}`",
        f"- Bounded scan: {metrics['files_read']} file(s), {metrics['evidence_files']} evidence slice(s), {metrics['elapsed_ms']} ms.",
        f"- Focused context estimate: approximately {metrics['estimated_tokens']} tokens.",
        f"- Stop reason: `{metrics['termination_reason']}`.", "",
        "## Evidence packet", "",
    ]
    for row in packet["evidence"]:
        roles = ", ".join(row.get("behavior_roles", []))
        lines.append(f"- `{row['path']}:{row['start_line']}` — {row['suggested_role']} ({roles}); {row['reason']}.")
    trace = packet.get("behavior_trace", {})
    if trace.get("nodes"):
        topology = trace.get("topology") or {}
        lines.extend(["", "## Backward behavior graph", ""])
        lines.append(
            f"- State: `{trace.get('state')}`; shape: `{topology.get('shape', 'unavailable')}`; "
            f"paths: `{topology.get('path_count', 0)}`; direction: `{trace.get('direction')}`."
        )
        for edge in trace.get("edges", []):
            lines.append(f"- `{edge['from']}` → `{edge['to']}`: {edge['relationship']}.")
    if packet["suggested_test_commands"]:
        lines.extend(["", "## Focused proof", ""])
        lines.extend(f"- `{row['command']}`" for row in packet["suggested_test_commands"])
    fallback = packet.get("safe_fallback", {})
    if fallback.get("state") != "not-needed":
        lines.extend(["", "## Safe fallback", ""])
        lines.append(f"- Route: `{fallback.get('state')}`; trace: `{fallback.get('trace_state')}`; correction scope: `{fallback.get('correction_scope')}`.")
        lines.append(f"- User input: `{fallback.get('user_input')}`. {fallback.get('next_action')}")
    lines.extend(["", "Host reasoning is limited to one pass over this packet; no project command was run."])
    return "\n".join(lines) + "\n"


def main() -> int:
    parser = argparse.ArgumentParser(description="Create a bounded Debug Start evidence packet")
    parser.add_argument("--root", default=".")
    parser.add_argument("--goal", required=True)
    parser.add_argument("--host", required=True, choices=("codex", "copilot", "claude"))
    parser.add_argument("--format", choices=("json", "markdown"), default="json")
    args = parser.parse_args()
    packet = build(Path(args.root), args.goal, args.host)
    print(json.dumps(packet, indent=2) if args.format == "json" else render_markdown(packet), end="" if args.format == "markdown" else "\n")
    return 0 if packet.get("safe_fallback", {}).get("state") != "awaiting-reproduction-input" else 2


if __name__ == "__main__":
    raise SystemExit(main())
