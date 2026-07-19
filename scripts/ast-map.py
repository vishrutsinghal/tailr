#!/usr/bin/env python3

from __future__ import annotations

import argparse
import ast
import json
import shutil
import re
import subprocess
from dataclasses import dataclass
from datetime import datetime, timezone
from pathlib import Path
from typing import Any


SKIP_DIRS = {
    ".git",
    ".tailtrail",
    "__pycache__",
    "aidlc-rules",
    "node_modules",
    "vendor",
    "dist",
    "build",
    "target",
    "coverage",
    ".next",
    ".nuxt",
    ".venv",
    "venv",
    "bin",
    "obj",
}

SOURCE_EXTENSIONS = {".py", ".java", ".cs", ".sql", ".tf", ".tfvars"}
TEXT_EXTENSIONS = SOURCE_EXTENSIONS | {".json", ".yaml", ".yml", ".xml", ".properties", ".toml", ".gradle"}
TEST_HINTS = ("test", "tests", "spec", "specs")
POLICY_NAME = "tailtrail-policy.md"
DEFAULT_PROVIDER_OUTPUT_PREFIX = "tailtrail-meta/providers/"
EVIDENCE_LABELS = ("heuristic", "local-ast", "provider-backed", "measured/validated")


@dataclass(frozen=True)
class Symbol:
    name: str
    kind: str
    language: str
    file: str
    line: int
    container: str
    confidence: str

    def as_dict(self) -> dict[str, Any]:
        value = self.__dict__.copy()
        value["evidence_label"] = evidence_label_for_confidence(self.confidence)
        return value


def now_utc() -> str:
    return datetime.now(timezone.utc).replace(microsecond=0).isoformat()


def safe_relative(path: Path, root: Path) -> str | None:
    try:
        return path.resolve().relative_to(root.resolve()).as_posix()
    except ValueError:
        return None


def is_skipped(path: Path) -> bool:
    return any(part in SKIP_DIRS for part in path.parts)


def read_text(path: Path) -> str:
    try:
        return path.read_text(encoding="utf-8")
    except (OSError, UnicodeDecodeError):
        return ""


def evidence_label_for_confidence(confidence: Any) -> str:
    text = str(confidence or "").lower()
    if text in {"provider-backed", "provider_backed"} or "provider" in text:
        return "provider-backed"
    if text in {"python_ast", "local-ast", "local_ast"} or "ast" in text:
        return "local-ast"
    if text in {"measured/validated", "measured", "validated", "scanner-validated", "test-validated"}:
        return "measured/validated"
    return "heuristic"


def add_evidence_label(item: dict[str, Any]) -> dict[str, Any]:
    if "evidence_label" not in item:
        item["evidence_label"] = evidence_label_for_confidence(item.get("confidence"))
    return item


def label_facts(value: Any) -> Any:
    if isinstance(value, dict):
        if "confidence" in value or "provider" in value:
            add_evidence_label(value)
        for nested in value.values():
            label_facts(nested)
    elif isinstance(value, list):
        for item in value:
            label_facts(item)
    return value


def evidence_summary(report: dict[str, Any]) -> dict[str, int]:
    counts = {label: 0 for label in EVIDENCE_LABELS}

    def visit(value: Any) -> None:
        if isinstance(value, dict):
            label = value.get("evidence_label")
            if isinstance(label, str) and label in counts:
                counts[label] += 1
            for nested in value.values():
                visit(nested)
        elif isinstance(value, list):
            for item in value:
                visit(item)

    for key in ("symbols", "references", "call_hints", "type_hierarchy", "endpoints", "db_tables", "config_usage", "imports", "changed_symbol_impact", "semantic"):
        visit(report.get(key))
    return counts


def line_number(body: str, offset: int) -> int:
    return body.count("\n", 0, offset) + 1


def language_for(path: Path) -> str | None:
    if path.suffix == ".py":
        return "python"
    if path.suffix == ".java":
        return "java"
    if path.suffix == ".cs":
        return "dotnet"
    if path.suffix == ".sql":
        return "sql"
    if path.suffix in {".tf", ".tfvars"}:
        return "terraform"
    return None


def git_changed(root: Path) -> list[str]:
    result = subprocess.run(["git", "diff", "--name-only", "HEAD"], cwd=root, text=True, capture_output=True, check=False)
    if result.returncode != 0:
        return []
    return [line.strip() for line in result.stdout.splitlines() if line.strip()]


def normalize_paths(root: Path, values: list[str]) -> list[Path]:
    paths: list[Path] = []
    for value in values:
        path = (root / value).resolve()
        if path.is_file() and safe_relative(path, root) is not None and not is_skipped(path):
            paths.append(path)
    return sorted(set(paths))


def list_text_files(root: Path, limit: int) -> list[Path]:
    files: list[Path] = []
    for path in root.rglob("*"):
        if len(files) >= limit:
            break
        if is_skipped(path) or not path.is_file():
            continue
        if path.suffix in TEXT_EXTENSIONS:
            files.append(path)
    return sorted(files)


def looks_like_test(path: Path) -> bool:
    lowered = path.as_posix().lower()
    return any(f"/{hint}" in lowered or lowered.startswith(hint) for hint in TEST_HINTS) or path.name.lower().startswith("test_") or "test" in path.stem.lower()


def add(symbols: list[Symbol], name: str, kind: str, language: str, file: str, line: int, container: str = "", confidence: str = "heuristic") -> None:
    if name:
        symbols.append(Symbol(name=name, kind=kind, language=language, file=file, line=line, container=container, confidence=confidence))


def extract_imports(path: Path, root: Path, body: str, language: str) -> list[dict[str, Any]]:
    rel = safe_relative(path, root) or path.as_posix()
    imports: list[dict[str, Any]] = []
    if language == "python":
        for match in re.finditer(r"^\s*(?:from\s+([\w.]+)\s+import\s+([\w.*, ]+)|import\s+([\w., ]+))", body, re.MULTILINE):
            module = match.group(1) or match.group(3) or ""
            names = match.group(2) or ""
            imports.append({"module": module.strip(), "names": names.strip(), "language": language, "file": rel, "line": line_number(body, match.start()), "confidence": "heuristic"})
    elif language == "java":
        for match in re.finditer(r"^\s*import\s+([\w.*]+)\s*;", body, re.MULTILINE):
            imports.append({"module": match.group(1), "names": "", "language": language, "file": rel, "line": line_number(body, match.start()), "confidence": "heuristic"})
    elif language == "dotnet":
        for match in re.finditer(r"^\s*using\s+([\w.]+)\s*;", body, re.MULTILINE):
            imports.append({"module": match.group(1), "names": "", "language": language, "file": rel, "line": line_number(body, match.start()), "confidence": "heuristic"})
    elif language == "terraform":
        for match in re.finditer(r'\b(source|providers?)\s*=\s*"([^"]+)"', body):
            imports.append({"module": match.group(2), "names": match.group(1), "language": language, "file": rel, "line": line_number(body, match.start()), "confidence": "heuristic"})
    return imports


def extract_python(path: Path, root: Path, body: str) -> dict[str, Any]:
    rel = safe_relative(path, root) or path.as_posix()
    symbols: list[Symbol] = []
    calls: list[dict[str, Any]] = []
    hierarchy: list[dict[str, Any]] = []
    endpoints: list[dict[str, Any]] = []
    try:
        tree = ast.parse(body)
    except SyntaxError:
        return {"symbols": [], "calls": [], "hierarchy": [], "endpoints": [], "errors": ["python syntax error"]}

    class Parent(ast.NodeVisitor):
        def __init__(self) -> None:
            self.stack: list[str] = []

        def visit_ClassDef(self, node: ast.ClassDef) -> Any:
            container = ".".join(self.stack)
            add(symbols, node.name, "class", "python", rel, node.lineno, container, "python_ast")
            for base in node.bases:
                base_name = getattr(base, "id", None) or getattr(base, "attr", None) or ast.unparse(base)
                if base_name:
                    hierarchy.append({"type": node.name, "inherits": base_name, "language": "python", "file": rel, "line": node.lineno, "confidence": "python_ast"})
            self.stack.append(node.name)
            self.generic_visit(node)
            self.stack.pop()

        def visit_FunctionDef(self, node: ast.FunctionDef) -> Any:
            self._function(node, "function")

        def visit_AsyncFunctionDef(self, node: ast.AsyncFunctionDef) -> Any:
            self._function(node, "async-function")

        def _function(self, node: ast.FunctionDef | ast.AsyncFunctionDef, kind: str) -> None:
            container = ".".join(self.stack)
            add(symbols, node.name, kind, "python", rel, node.lineno, container, "python_ast")
            for decorator in node.decorator_list:
                text = ast.unparse(decorator) if hasattr(ast, "unparse") else ""
                if any(term in text.lower() for term in (".get(", ".post(", ".put(", ".delete(", ".route(")):
                    endpoints.append({"route": text, "method": "unknown", "handler": ".".join([*self.stack, node.name]), "language": "python", "file": rel, "line": node.lineno, "confidence": "python_ast"})
            self.stack.append(node.name)
            self.generic_visit(node)
            self.stack.pop()

        def visit_Call(self, node: ast.Call) -> Any:
            callee = ""
            if isinstance(node.func, ast.Name):
                callee = node.func.id
            elif isinstance(node.func, ast.Attribute):
                callee = node.func.attr
            if callee:
                calls.append({"caller": ".".join(self.stack) or "module", "callee": callee, "language": "python", "file": rel, "line": getattr(node, "lineno", 1), "confidence": "python_ast"})
            self.generic_visit(node)

    Parent().visit(tree)
    return {"symbols": [item.as_dict() for item in symbols], "calls": calls, "hierarchy": hierarchy, "endpoints": endpoints, "errors": []}


def extract_java(path: Path, root: Path, body: str) -> dict[str, Any]:
    rel = safe_relative(path, root) or path.as_posix()
    symbols: list[Symbol] = []
    calls: list[dict[str, Any]] = []
    hierarchy: list[dict[str, Any]] = []
    endpoints: list[dict[str, Any]] = []
    db_tables: list[dict[str, Any]] = []
    class_pattern = re.compile(r"\b(class|interface|enum)\s+(\w+)(?:\s+extends\s+(\w+))?(?:\s+implements\s+([\w,\s]+))?")
    method_pattern = re.compile(r"\b(?:public|private|protected|static|final|synchronized|\s)+[\w<>\[\], ?]+\s+(\w+)\s*\([^;{}]*\)\s*\{")
    call_pattern = re.compile(r"\b([A-Za-z_]\w*)\s*\(")
    route_pattern = re.compile(r"@(GetMapping|PostMapping|PutMapping|DeleteMapping|PatchMapping|RequestMapping)\s*(?:\(([^)]*)\))?")
    table_pattern = re.compile(r"@Table\s*\([^)]*name\s*=\s*\"([^\"]+)\"")
    current_type = ""
    for match in class_pattern.finditer(body):
        kind, name, extends, implements = match.group(1), match.group(2), match.group(3), match.group(4)
        current_type = name
        line = line_number(body, match.start())
        add(symbols, name, kind, "java", rel, line, "", "heuristic")
        if extends:
            hierarchy.append({"type": name, "extends": extends, "language": "java", "file": rel, "line": line, "confidence": "heuristic"})
        if implements:
            for item in [part.strip() for part in implements.split(",") if part.strip()]:
                hierarchy.append({"type": name, "implements": item, "language": "java", "file": rel, "line": line, "confidence": "heuristic"})
    for match in method_pattern.finditer(body):
        method = match.group(1)
        line = line_number(body, match.start())
        add(symbols, method, "method", "java", rel, line, current_type, "heuristic")
        window = body[match.end() : match.end() + 1200]
        for call in call_pattern.finditer(window):
            callee = call.group(1)
            if callee not in {"if", "for", "while", "switch", "catch", "return", "new"}:
                calls.append({"caller": f"{current_type}.{method}" if current_type else method, "callee": callee, "language": "java", "file": rel, "line": line_number(body, match.end() + call.start()), "confidence": "heuristic"})
    for match in route_pattern.finditer(body):
        endpoints.append({"route": (match.group(2) or "").strip() or "annotation-default", "method": match.group(1), "handler": current_type or "nearby Java handler", "language": "java", "file": rel, "line": line_number(body, match.start()), "confidence": "heuristic"})
    for match in table_pattern.finditer(body):
        db_tables.append({"table": match.group(1), "source": "jpa-table-annotation", "language": "java", "file": rel, "line": line_number(body, match.start()), "confidence": "heuristic"})
    return {"symbols": [item.as_dict() for item in symbols], "calls": calls[:200], "hierarchy": hierarchy, "endpoints": endpoints, "db_tables": db_tables, "errors": []}


def extract_dotnet(path: Path, root: Path, body: str) -> dict[str, Any]:
    rel = safe_relative(path, root) or path.as_posix()
    symbols: list[Symbol] = []
    calls: list[dict[str, Any]] = []
    hierarchy: list[dict[str, Any]] = []
    endpoints: list[dict[str, Any]] = []
    db_tables: list[dict[str, Any]] = []
    type_pattern = re.compile(r"\b(class|interface|record|struct|enum)\s+(\w+)(?:\s*:\s*([\w,\s<>]+))?")
    method_pattern = re.compile(r"\b(?:public|private|protected|internal|static|async|virtual|override|\s)+[\w<>\[\], ?]+\s+(\w+)\s*\([^;{}]*\)\s*\{")
    call_pattern = re.compile(r"\b([A-Za-z_]\w*)\s*\(")
    route_pattern = re.compile(r"\[(HttpGet|HttpPost|HttpPut|HttpDelete|HttpPatch|Route)(?:\(([^)]*)\))?\]")
    dbset_pattern = re.compile(r"DbSet<\s*(\w+)\s*>\s+(\w+)")
    current_type = ""
    for match in type_pattern.finditer(body):
        kind, name, bases = match.group(1), match.group(2), match.group(3)
        current_type = name
        line = line_number(body, match.start())
        add(symbols, name, kind, "dotnet", rel, line, "", "heuristic")
        if bases:
            for item in [part.strip() for part in bases.split(",") if part.strip()]:
                hierarchy.append({"type": name, "inherits_or_implements": item, "language": "dotnet", "file": rel, "line": line, "confidence": "heuristic"})
    for match in method_pattern.finditer(body):
        method = match.group(1)
        line = line_number(body, match.start())
        add(symbols, method, "method", "dotnet", rel, line, current_type, "heuristic")
        window = body[match.end() : match.end() + 1200]
        for call in call_pattern.finditer(window):
            callee = call.group(1)
            if callee not in {"if", "for", "while", "switch", "catch", "return", "new"}:
                calls.append({"caller": f"{current_type}.{method}" if current_type else method, "callee": callee, "language": "dotnet", "file": rel, "line": line_number(body, match.end() + call.start()), "confidence": "heuristic"})
    for match in route_pattern.finditer(body):
        endpoints.append({"route": (match.group(2) or "").strip() or "attribute-default", "method": match.group(1), "handler": current_type or "nearby .NET handler", "language": "dotnet", "file": rel, "line": line_number(body, match.start()), "confidence": "heuristic"})
    for match in dbset_pattern.finditer(body):
        db_tables.append({"table": match.group(2), "entity": match.group(1), "source": "ef-dbset", "language": "dotnet", "file": rel, "line": line_number(body, match.start()), "confidence": "heuristic"})
    return {"symbols": [item.as_dict() for item in symbols], "calls": calls[:200], "hierarchy": hierarchy, "endpoints": endpoints, "db_tables": db_tables, "errors": []}


def extract_sql(path: Path, root: Path, body: str) -> dict[str, Any]:
    rel = safe_relative(path, root) or path.as_posix()
    symbols: list[Symbol] = []
    db_tables: list[dict[str, Any]] = []
    for match in re.finditer(r"\bCREATE\s+(?:PROCEDURE|PROC|FUNCTION)\s+([A-Za-z_][\w.]*)", body, re.IGNORECASE):
        add(symbols, match.group(1), "sql-routine", "sql", rel, line_number(body, match.start()), "", "heuristic")
    for match in re.finditer(r"\b(?:CREATE\s+TABLE|ALTER\s+TABLE|INSERT\s+INTO|UPDATE|DELETE\s+FROM|FROM|JOIN)\s+([A-Za-z_][\w.]*)", body, re.IGNORECASE):
        db_tables.append({"table": match.group(1), "source": "sql-reference", "language": "sql", "file": rel, "line": line_number(body, match.start()), "confidence": "heuristic"})
    return {"symbols": [item.as_dict() for item in symbols], "db_tables": db_tables, "errors": []}


def extract_terraform(path: Path, root: Path, body: str) -> dict[str, Any]:
    rel = safe_relative(path, root) or path.as_posix()
    symbols: list[Symbol] = []
    config: list[dict[str, Any]] = []
    for match in re.finditer(r'\b(resource|data|module|variable|output|provider)\s+"([^"]+)"(?:\s+"([^"]+)")?', body):
        kind, first, second = match.group(1), match.group(2), match.group(3)
        add(symbols, f"{first}.{second}" if second else first, kind, "terraform", rel, line_number(body, match.start()), "", "heuristic")
    for match in re.finditer(r"\b(var|module|local|data)\.([A-Za-z_][\w-]*)", body):
        config.append({"key": f"{match.group(1)}.{match.group(2)}", "source": "terraform-reference", "language": "terraform", "file": rel, "line": line_number(body, match.start()), "confidence": "heuristic"})
    return {"symbols": [item.as_dict() for item in symbols], "config_usage": config, "errors": []}


def extract_file(path: Path, root: Path) -> dict[str, Any]:
    body = read_text(path)
    language = language_for(path)
    base: dict[str, Any] = {"symbols": [], "calls": [], "hierarchy": [], "endpoints": [], "db_tables": [], "config_usage": [], "imports": [], "errors": []}
    if not body or not language:
        return base
    base["imports"].extend(extract_imports(path, root, body, language))
    if language == "python":
        data = extract_python(path, root, body)
    elif language == "java":
        data = extract_java(path, root, body)
    elif language == "dotnet":
        data = extract_dotnet(path, root, body)
    elif language == "sql":
        data = extract_sql(path, root, body)
    elif language == "terraform":
        data = extract_terraform(path, root, body)
    else:
        data = {}
    for key, value in data.items():
        if key in base and isinstance(value, list):
            base[key].extend(value)
    if path.suffix in {".json", ".yaml", ".yml", ".properties", ".toml"}:
        for match in re.finditer(r"^\s*([A-Za-z_][\w.-]{2,})\s*[:=]", body, re.MULTILINE):
            base["config_usage"].append({"key": match.group(1), "source": "config-key", "language": "config", "file": safe_relative(path, root) or path.as_posix(), "line": line_number(body, match.start()), "confidence": "heuristic"})
    return base


def references_for(symbols: list[dict[str, Any]], candidates: list[Path], root: Path, limit: int) -> list[dict[str, Any]]:
    names = sorted({str(item.get("name", "")) for item in symbols if len(str(item.get("name", ""))) >= 4}, key=len, reverse=True)
    refs: list[dict[str, Any]] = []
    if not names:
        return refs
    for path in candidates:
        if path.suffix not in TEXT_EXTENSIONS:
            continue
        body = read_text(path)
        if not body:
            continue
        for name in names:
            match = re.search(rf"\b{re.escape(name)}\b", body)
            if match:
                refs.append({"symbol": name, "file": safe_relative(path, root) or path.as_posix(), "line": line_number(body, match.start()), "reference_type": "symbol-name", "confidence": "heuristic"})
                break
        if len(refs) >= limit:
            break
    return refs


def likely_tests(symbols: list[dict[str, Any]], candidates: list[Path], root: Path, limit: int) -> list[str]:
    names = {str(item.get("name", "")).lower() for item in symbols if len(str(item.get("name", ""))) >= 4}
    tests: list[str] = []
    for path in candidates:
        if not looks_like_test(path):
            continue
        rel = safe_relative(path, root)
        body = read_text(path).lower()
        if rel and any(name in rel.lower() or name in body for name in names):
            tests.append(rel)
        if len(tests) >= limit:
            break
    return list(dict.fromkeys(tests))


def impact(symbols: list[dict[str, Any]], refs: list[dict[str, Any]], tests: list[str]) -> list[dict[str, Any]]:
    by_symbol: dict[str, dict[str, Any]] = {}
    for symbol in symbols:
        name = str(symbol.get("name", ""))
        if not name:
            continue
        by_symbol[name] = {
            "symbol": name,
            "definition": f"{symbol.get('file')}:{symbol.get('line')}",
            "references": [],
            "likely_tests": tests[:5],
            "risk": "review current source before editing",
            "confidence": symbol.get("confidence", "heuristic"),
            "evidence_label": evidence_label_for_confidence(symbol.get("confidence", "heuristic")),
        }
    for ref in refs:
        name = str(ref.get("symbol", ""))
        if name in by_symbol:
            by_symbol[name]["references"].append(f"{ref.get('file')}:{ref.get('line')}")
    return list(by_symbol.values())[:50]


def find_solution_files(root: Path, limit: int = 5, visit_limit: int = 1000) -> list[str]:
    found: list[str] = []
    stack = [root]
    visited = 0
    while stack and len(found) < limit and visited < visit_limit:
        current = stack.pop()
        visited += 1
        if is_skipped(current):
            continue
        try:
            children = sorted(current.iterdir(), key=lambda item: item.name)
        except OSError:
            continue
        for child in children:
            if is_skipped(child):
                continue
            if child.is_dir():
                stack.append(child)
            elif child.suffix == ".sln":
                rel = safe_relative(child, root)
                if rel:
                    found.append(rel)
                    if len(found) >= limit:
                        break
    return found


def provider_status(root: Path, provider_outputs: list[dict[str, Any]] | None = None) -> dict[str, Any]:
    scip_files = [".scip/index.scip", "index.scip", "target/semanticdb"]
    solution_files = find_solution_files(root)
    used_providers = {str(item.get("provider", "")).lower() for item in provider_outputs or []}
    providers = {
        "language_server": {
            "available": any(shutil.which(name) for name in ("pyright-langserver", "jdtls", "typescript-language-server", "clangd")),
            "detected_commands": [name for name in ("pyright-langserver", "jdtls", "typescript-language-server", "clangd") if shutil.which(name)],
            "used": any(provider in used_providers for provider in ("language_server", "lsp", "jdt", "jdtls", "pyright")),
            "reason": "used only when approved local provider output is supplied; TailTrail does not start language servers automatically",
        },
        "scip": {
            "available": any((root / item).exists() for item in scip_files) or shutil.which("scip") is not None,
            "detected_indexes": [item for item in scip_files if (root / item).exists()],
            "command_available": shutil.which("scip") is not None,
            "used": "scip" in used_providers,
            "reason": "used only when approved local SCIP-derived JSON output is supplied",
        },
        "roslyn": {
            "available": shutil.which("dotnet") is not None and bool(solution_files),
            "detected_commands": ["dotnet"] if shutil.which("dotnet") else [],
            "solution_files": solution_files,
            "used": "roslyn" in used_providers,
            "reason": "used only when approved local Roslyn-derived JSON output is supplied; TailTrail does not execute dotnet analyzers automatically",
        },
        "tree_sitter": {
            "available": shutil.which("tree-sitter") is not None,
            "detected_commands": ["tree-sitter"] if shutil.which("tree-sitter") else [],
            "used": any(provider in used_providers for provider in ("tree_sitter", "tree-sitter")),
            "reason": "used only when approved parser output is supplied; no parser package dependency is bundled",
        },
        "repo_owned_extractor": {
            "available": True,
            "detected_commands": [],
            "used": "repo_owned_extractor" in used_providers,
            "reason": "generic adapter for approved repo-owned SQL, Terraform, Java, .NET, or Python metadata exports",
        },
    }
    return providers


def symbol_index(symbols: list[dict[str, Any]]) -> dict[str, list[dict[str, Any]]]:
    index: dict[str, list[dict[str, Any]]] = {}
    for item in symbols:
        name = str(item.get("name", ""))
        if not name:
            continue
        index.setdefault(name, []).append(
            {
                "kind": item.get("kind", "unknown"),
                "language": item.get("language", "unknown"),
                "file": item.get("file", "unknown"),
                "line": item.get("line", 0),
                "container": item.get("container", ""),
                "confidence": item.get("confidence", "heuristic"),
            }
        )
    return dict(sorted(index.items())[:100])


def reference_edges(symbols: list[dict[str, Any]], refs: list[dict[str, Any]], calls: list[dict[str, Any]]) -> list[dict[str, Any]]:
    definitions = {str(item.get("name", "")): item for item in symbols}
    edges: list[dict[str, Any]] = []
    for ref in refs:
        symbol = str(ref.get("symbol", ""))
        definition = definitions.get(symbol, {})
        edges.append(
            {
                "from": f"{ref.get('file')}:{ref.get('line')}",
                "to": f"{definition.get('file', 'unknown')}:{definition.get('line', '?')}",
                "symbol": symbol,
                "edge_type": "text-reference",
                "confidence": ref.get("confidence", "heuristic"),
            }
        )
    for call in calls[:100]:
        edges.append(
            {
                "from": f"{call.get('file')}:{call.get('line')}",
                "to": str(call.get("callee", "unknown")),
                "symbol": str(call.get("callee", "unknown")),
                "edge_type": "call-hint",
                "confidence": call.get("confidence", "heuristic"),
            }
        )
    return edges[:200]


def import_edges(imports: list[dict[str, Any]]) -> list[dict[str, Any]]:
    return [
        {
            "from": f"{item.get('file')}:{item.get('line')}",
            "to": item.get("module", "unknown"),
            "edge_type": "import-or-module-use",
            "language": item.get("language", "unknown"),
            "confidence": item.get("confidence", "heuristic"),
        }
        for item in imports[:200]
    ]


def endpoint_handler_links(endpoints: list[dict[str, Any]], calls: list[dict[str, Any]], config: list[dict[str, Any]]) -> list[dict[str, Any]]:
    links: list[dict[str, Any]] = []
    for endpoint in endpoints:
        handler = str(endpoint.get("handler", ""))
        related_calls = [item for item in calls if handler and handler.split(".")[-1] in str(item.get("caller", ""))][:10]
        related_config = [item for item in config if item.get("file") == endpoint.get("file")][:10]
        links.append(
            {
                "route": endpoint.get("route", "unknown"),
                "method": endpoint.get("method", "unknown"),
                "handler": handler or "nearby handler",
                "file": endpoint.get("file", "unknown"),
                "line": endpoint.get("line", "?"),
                "call_hints": related_calls,
                "config_hints": related_config,
                "confidence": endpoint.get("confidence", "heuristic"),
            }
        )
    return links[:50]


def data_flow_lite(endpoints: list[dict[str, Any]], calls: list[dict[str, Any]], db_tables: list[dict[str, Any]], config: list[dict[str, Any]]) -> list[dict[str, Any]]:
    flows: list[dict[str, Any]] = []
    for endpoint in endpoints:
        endpoint_file = endpoint.get("file")
        local_calls = [item for item in calls if item.get("file") == endpoint_file][:8]
        local_tables = [item for item in db_tables if item.get("file") == endpoint_file][:8]
        local_config = [item for item in config if item.get("file") == endpoint_file][:8]
        flows.append(
            {
                "entry": f"{endpoint.get('method', 'unknown')} {endpoint.get('route', 'unknown')}",
                "handler": endpoint.get("handler", "nearby handler"),
                "file": endpoint_file,
                "line": endpoint.get("line", "?"),
                "service_call_hints": [item.get("callee") for item in local_calls],
                "db_table_hints": [item.get("table") for item in local_tables],
                "config_hints": [item.get("key") for item in local_config],
                "confidence": "heuristic",
            }
        )
    if not flows and db_tables:
        for table in db_tables[:25]:
            flows.append(
                {
                    "entry": "database-touchpoint",
                    "handler": table.get("source", "unknown"),
                    "file": table.get("file", "unknown"),
                    "line": table.get("line", "?"),
                    "service_call_hints": [],
                    "db_table_hints": [table.get("table")],
                    "config_hints": [],
                    "confidence": "heuristic",
                }
            )
    return flows[:50]


def infer_provider_name(path: Path, payload: dict[str, Any]) -> str:
    explicit = str(payload.get("provider") or payload.get("engine") or "").strip().lower()
    if explicit:
        return explicit.replace("-", "_")
    lowered = path.name.lower()
    for marker, name in {
        "roslyn": "roslyn",
        "jdt": "jdt",
        "jdtls": "jdt",
        "pyright": "pyright",
        "lsp": "language_server",
        "scip": "scip",
        "terraform": "repo_owned_extractor",
        "sql": "repo_owned_extractor",
    }.items():
        if marker in lowered:
            return name
    return "repo_owned_extractor"


def normalized_file(value: Any, root: Path) -> str:
    text = str(value or "").strip()
    if not text:
        return "unknown"
    path = Path(text)
    if path.is_absolute():
        rel = safe_relative(path, root)
        return rel or "outside-root"
    clean = Path(text)
    if ".." in clean.parts:
        return "outside-root"
    return clean.as_posix()


def policy_text(root: Path) -> str:
    path = root / POLICY_NAME
    if not path.is_file():
        return ""
    return read_text(path)


def semantic_v3_policy_enabled(root: Path) -> bool:
    body = policy_text(root).lower()
    enabled_markers = (
        "provider_backed_semantic_ingestion: enabled",
        "provider-backed-semantic-ingestion: enabled",
        "semantic_v3_provider_ingestion: enabled",
        "semantic-v3-provider-ingestion: enabled",
    )
    return any(marker in body for marker in enabled_markers)


def allowed_provider_prefixes(root: Path) -> list[str]:
    body = policy_text(root)
    prefixes = [DEFAULT_PROVIDER_OUTPUT_PREFIX]
    capture = False
    for raw in body.splitlines():
        stripped = raw.strip()
        lowered = stripped.lower()
        if lowered.startswith("allowed_provider_outputs:"):
            capture = True
            continue
        if capture:
            if stripped.startswith("- "):
                value = stripped[2:].strip().strip("`\"'")
                if value:
                    prefixes.append(value.rstrip("/") + "/")
            elif stripped and not raw.startswith((" ", "\t")):
                break
    return list(dict.fromkeys(prefixes))


def provider_path_allowed(root: Path, path: Path, prefixes: list[str]) -> bool:
    rel = safe_relative(path, root)
    if rel is None:
        return False
    return any(rel == prefix.rstrip("/") or rel.startswith(prefix) for prefix in prefixes)


def enforce_v3_gate(root: Path, depth: str, provider_output_values: list[str], approved: bool) -> None:
    if depth != "v3":
        return
    policy_enabled = semantic_v3_policy_enabled(root)
    if not provider_output_values:
        raise SystemExit("Semantic V3 provider ingestion requires at least one explicit --provider-output JSON file.")
    if not approved and not policy_enabled:
        raise SystemExit(
            "Semantic V3 provider ingestion requires explicit approval or local policy enablement. "
            "Use --approved after reviewing provider-output paths, or set provider_backed_semantic_ingestion: enabled in tailtrail-policy.md."
        )
    prefixes = allowed_provider_prefixes(root)
    for value in provider_output_values:
        path = (root / value).resolve()
        if path.suffix.lower() != ".json":
            raise SystemExit(f"Semantic V3 provider output must be JSON: {value}")
        if not provider_path_allowed(root, path, prefixes):
            allowed = ", ".join(prefixes)
            raise SystemExit(f"Semantic V3 provider output must be inside an allowed repo path ({allowed}): {value}")


def file_field(item: dict[str, Any]) -> Any:
    for key in ("file", "source_file", "document", "uri"):
        if item.get(key):
            return item.get(key)
    candidate = item.get("path")
    if candidate and (Path(str(candidate)).suffix or "/" in str(candidate).strip().lstrip("/")):
        return candidate
    return ""


def line_value(value: Any) -> int:
    try:
        line = int(value)
    except (TypeError, ValueError):
        return 0
    return max(line, 0)


def provider_items(payload: dict[str, Any], *keys: str) -> list[dict[str, Any]]:
    for key in keys:
        value = payload.get(key)
        if isinstance(value, list):
            return [item for item in value if isinstance(item, dict)]
    graph = payload.get("graph")
    if isinstance(graph, dict):
        for key in keys:
            value = graph.get(key)
            if isinstance(value, list):
                return [item for item in value if isinstance(item, dict)]
    semantic = payload.get("semantic")
    if isinstance(semantic, dict):
        for key in keys:
            value = semantic.get(key)
            if isinstance(value, list):
                return [item for item in value if isinstance(item, dict)]
    return []


def normalize_provider_output(path: Path, root: Path, limit: int) -> dict[str, Any]:
    try:
        payload = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError) as error:
        return {"path": path.as_posix(), "provider": "unknown", "error": str(error), "symbols": [], "references": [], "calls": [], "hierarchy": [], "endpoints": [], "db_tables": [], "config_usage": [], "imports": []}
    if not isinstance(payload, dict):
        return {"path": path.as_posix(), "provider": "unknown", "error": "provider output root is not an object", "symbols": [], "references": [], "calls": [], "hierarchy": [], "endpoints": [], "db_tables": [], "config_usage": [], "imports": []}

    provider = infer_provider_name(path, payload)
    language = str(payload.get("language") or "unknown").lower()

    def common(item: dict[str, Any]) -> dict[str, Any]:
        return {
            "language": str(item.get("language") or language or "unknown").lower(),
            "file": normalized_file(file_field(item), root),
            "line": line_value(item.get("line") or item.get("start_line") or item.get("range_start")),
            "confidence": "provider-backed",
            "provider": provider,
        }

    symbols = [
        {
            **common(item),
            "name": str(item.get("name") or item.get("symbol") or item.get("display_name") or ""),
            "kind": str(item.get("kind") or item.get("symbol_kind") or "symbol"),
            "container": str(item.get("container") or item.get("scope") or ""),
        }
        for item in provider_items(payload, "symbols", "definitions")
    ][: limit * 20]
    references = [
        {
            **common(item),
            "symbol": str(item.get("symbol") or item.get("name") or item.get("target") or ""),
            "reference_type": str(item.get("reference_type") or item.get("kind") or "provider-reference"),
        }
        for item in provider_items(payload, "references", "reference_edges")
    ][: limit * 20]
    calls = [
        {
            **common(item),
            "caller": str(item.get("caller") or item.get("from") or ""),
            "callee": str(item.get("callee") or item.get("to") or item.get("target") or ""),
        }
        for item in provider_items(payload, "calls", "call_hints", "call_chains")
    ][: limit * 20]
    hierarchy = [
        {
            **common(item),
            "type": str(item.get("type") or item.get("child") or item.get("name") or ""),
            "inherits_or_implements": str(item.get("inherits_or_implements") or item.get("inherits") or item.get("extends") or item.get("parent") or ""),
        }
        for item in provider_items(payload, "hierarchy", "type_hierarchy")
    ][: limit * 10]
    endpoints = [
        {
            **common(item),
            "route": str(item.get("route") or item.get("path") or item.get("endpoint") or ""),
            "method": str(item.get("method") or item.get("http_method") or "unknown"),
            "handler": str(item.get("handler") or item.get("symbol") or ""),
        }
        for item in provider_items(payload, "endpoints", "routes")
    ][: limit * 10]
    db_tables = [
        {
            **common(item),
            "table": str(item.get("table") or item.get("name") or item.get("target") or ""),
            "source": str(item.get("source") or "provider-table"),
        }
        for item in provider_items(payload, "db_tables", "tables", "sql_tables")
    ][: limit * 10]
    config_usage = [
        {
            **common(item),
            "key": str(item.get("key") or item.get("name") or item.get("address") or ""),
            "source": str(item.get("source") or "provider-config"),
        }
        for item in provider_items(payload, "config_usage", "terraform_resources", "resources")
    ][: limit * 10]
    imports = [
        {
            **common(item),
            "module": str(item.get("module") or item.get("to") or item.get("target") or ""),
            "names": str(item.get("names") or ""),
        }
        for item in provider_items(payload, "imports", "import_edges", "module_edges")
    ][: limit * 20]

    return {
        "path": path.as_posix(),
        "provider": provider,
        "error": "",
        "symbols": [item for item in symbols if item["name"]],
        "references": [item for item in references if item["symbol"]],
        "calls": [item for item in calls if item["callee"] or item["caller"]],
        "hierarchy": [item for item in hierarchy if item["type"]],
        "endpoints": [item for item in endpoints if item["route"] or item["handler"]],
        "db_tables": [item for item in db_tables if item["table"]],
        "config_usage": [item for item in config_usage if item["key"]],
        "imports": [item for item in imports if item["module"]],
    }


def load_provider_outputs(root: Path, values: list[str], limit: int) -> list[dict[str, Any]]:
    outputs: list[dict[str, Any]] = []
    for value in values:
        path = (root / value).resolve()
        if safe_relative(path, root) is None or not path.is_file() or is_skipped(path):
            outputs.append({"path": value, "provider": "unknown", "error": "provider output is missing or outside the project root", "symbols": [], "references": [], "calls": [], "hierarchy": [], "endpoints": [], "db_tables": [], "config_usage": [], "imports": []})
            continue
        outputs.append(normalize_provider_output(path, root, limit))
    return outputs


def merge_provider_data(data: dict[str, list[dict[str, Any]]], provider_outputs: list[dict[str, Any]]) -> dict[str, list[dict[str, Any]]]:
    merged = {key: list(value) for key, value in data.items()}
    mapping = {
        "symbols": "symbols",
        "references": "references",
        "calls": "calls",
        "hierarchy": "hierarchy",
        "endpoints": "endpoints",
        "db_tables": "db_tables",
        "config_usage": "config_usage",
        "imports": "imports",
    }
    for output in provider_outputs:
        for provider_key, data_key in mapping.items():
            merged.setdefault(data_key, []).extend(output.get(provider_key, []))
    return merged


def build_semantic_layer(root: Path, data: dict[str, list[dict[str, Any]]], refs: list[dict[str, Any]], tests: list[str], provider_outputs: list[dict[str, Any]] | None = None, engine: str = "tailtrail-semantic-v2") -> dict[str, Any]:
    edges = reference_edges(data["symbols"], refs, data["calls"])
    imports = data.get("imports", [])
    provider_outputs = provider_outputs or []
    return {
        "engine": engine,
        "provider_status": provider_status(root, provider_outputs),
        "provider_outputs": [
            {
                "path": item.get("path"),
                "provider": item.get("provider"),
                "error": item.get("error", ""),
                "symbols": len(item.get("symbols", [])),
                "references": len(item.get("references", [])),
                "calls": len(item.get("calls", [])),
                "hierarchy": len(item.get("hierarchy", [])),
                "endpoints": len(item.get("endpoints", [])),
                "db_tables": len(item.get("db_tables", [])),
                "config_usage": len(item.get("config_usage", [])),
                "imports": len(item.get("imports", [])),
            }
            for item in provider_outputs
        ],
        "symbol_index": symbol_index(data["symbols"]),
        "import_edges": import_edges(imports),
        "reference_edges": edges,
        "endpoint_handler_links": endpoint_handler_links(data["endpoints"], data["calls"], data["config_usage"]),
        "data_flow_lite": data_flow_lite(data["endpoints"], data["calls"], data["db_tables"], data["config_usage"]),
        "test_coverage_hints": [{"test": item, "reason": "name or symbol proximity", "confidence": "heuristic"} for item in tests],
        "quality_notes": [
            f"{engine} enriches AST V1 with local semantic edges and approved provider outputs, but remains metadata-only.",
            "Language-server/JDT, Roslyn, SCIP, SQL, Terraform, and repo-owned providers are ingested only from supplied local JSON outputs.",
            "TailTrail does not start providers, install dependencies, call the network, or treat provider output as a correctness proof.",
            "Use provider output only when local policy approves it and exact source validation follows.",
        ],
    }


def build(root: Path, changed_values: list[str], depth: str, limit: int, provider_output_values: list[str] | None = None, approved: bool = False) -> dict[str, Any]:
    provider_output_values = provider_output_values or []
    enforce_v3_gate(root, depth, provider_output_values, approved)
    changed = normalize_paths(root, changed_values or git_changed(root))
    candidates = list_text_files(root, max(limit * 100, 200))
    scope = changed or [path for path in candidates if language_for(path)][:limit]
    data = {"symbols": [], "calls": [], "hierarchy": [], "endpoints": [], "db_tables": [], "config_usage": [], "imports": [], "errors": []}
    for path in scope:
        extracted = extract_file(path, root)
        for key in data:
            data[key].extend(extracted.get(key, []))
    refs: list[dict[str, Any]] = []
    tests: list[str] = []
    changed_impact: list[dict[str, Any]] = []
    if depth in {"v1", "v2", "v3"}:
        refs = references_for(data["symbols"], candidates, root, limit * 10)
        tests = likely_tests(data["symbols"], candidates, root, limit)
        changed_impact = impact(data["symbols"], refs, tests)
    provider_outputs = load_provider_outputs(root, provider_output_values, limit) if depth == "v3" else []
    semantic_data = merge_provider_data(data, provider_outputs) if depth == "v3" else data
    if depth == "v3":
        refs = [*refs, *semantic_data.get("references", [])]
        tests = likely_tests(semantic_data["symbols"], candidates, root, limit)
        changed_impact = impact(semantic_data["symbols"], refs, tests)
    semantic_layer = build_semantic_layer(
        root,
        semantic_data,
        refs,
        tests,
        provider_outputs,
        "tailtrail-semantic-v3",
    ) if depth == "v3" else build_semantic_layer(root, data, refs, tests) if depth == "v2" else {}
    visible_data = semantic_data if depth == "v3" else data
    report = {
        "type": "tailtrail-ast-map",
        "schema_version": "1",
        "created_at": now_utc(),
        "root": root.as_posix(),
        "depth": depth,
        "scope": [safe_relative(path, root) for path in scope if safe_relative(path, root)],
        "language_profiles": language_profiles(scope),
        "symbols": visible_data["symbols"][: limit * 20],
        "references": refs,
        "call_hints": visible_data["calls"][: limit * 20] if depth in {"v1", "v2", "v3"} else [],
        "type_hierarchy": visible_data["hierarchy"][: limit * 10] if depth in {"v1", "v2", "v3"} else [],
        "endpoints": visible_data["endpoints"][: limit * 10] if depth in {"v1", "v2", "v3"} else [],
        "db_tables": visible_data["db_tables"][: limit * 10] if depth in {"v1", "v2", "v3"} else [],
        "config_usage": visible_data["config_usage"][: limit * 10] if depth in {"v1", "v2", "v3"} else [],
        "imports": visible_data["imports"][: limit * 20] if depth in {"v2", "v3"} else [],
        "likely_tests": tests,
        "changed_symbol_impact": changed_impact,
        "semantic": semantic_layer,
        "errors": data["errors"],
        "boundaries": [
            "AST maps are structured metadata, not a correctness proof.",
            "No source snippets, model calls, scanner execution, network calls, vector DB, or background service are used.",
            "Read exact current source, tests, CI, scanner evidence, policy, and guardrails before editing.",
        ],
        "deferred": [
            "automatic language-server startup",
            "direct binary SCIP index ingestion",
            "direct Roslyn analyzer execution",
            "tree-sitter or parser dependency bundling",
            "cross-repo service graph",
            "graph database or vector database",
        ],
    }
    label_facts(report)
    report["evidence_summary"] = evidence_summary(report)
    return report


def language_profiles(paths: list[Path]) -> dict[str, dict[str, int]]:
    profiles: dict[str, dict[str, int]] = {}
    for path in paths:
        language = language_for(path)
        if not language:
            continue
        profile = profiles.setdefault(language, {"files": 0})
        profile["files"] += 1
    return profiles


def markdown(report: dict[str, Any]) -> str:
    lines = [
        "# TailTrail AST Map",
        "",
        f"- Depth: `{report['depth']}`",
        f"- Root: `{report['root']}`",
        "",
        "## Scope",
        "",
    ]
    lines.extend(f"- `{item}`" for item in report["scope"] or ["none"])
    lines.extend(["", "## Evidence Summary", ""])
    summary = report.get("evidence_summary", {})
    if summary:
        for label in EVIDENCE_LABELS:
            lines.append(f"- `{label}`: `{summary.get(label, 0)}`")
    else:
        lines.append("- none")
    lines.extend(["", "## Symbols", ""])
    for item in report["symbols"][:30] or [{"name": "none detected", "file": "", "line": ""}]:
        suffix = f" in `{item.get('file')}:{item.get('line')}`" if item.get("file") else ""
        evidence = item.get("evidence_label") or evidence_label_for_confidence(item.get("confidence"))
        lines.append(f"- `{item.get('name')}` ({item.get('kind', 'unknown')}){suffix} [{evidence}]")
    for title, key, label in (
        ("References", "references", "symbol"),
        ("Call Hints", "call_hints", "callee"),
        ("Type Hierarchy", "type_hierarchy", "type"),
        ("Endpoint Hints", "endpoints", "route"),
        ("DB Table Hints", "db_tables", "table"),
        ("Config Usage", "config_usage", "key"),
        ("Imports / Module Uses", "imports", "module"),
    ):
        lines.extend(["", f"## {title}", ""])
        values = report.get(key, [])
        if not values:
            lines.append("- none")
            continue
        for item in values[:20]:
            file = item.get("file", "unknown")
            line = item.get("line", "?")
            evidence = item.get("evidence_label") or evidence_label_for_confidence(item.get("confidence"))
            lines.append(f"- `{item.get(label, 'unknown')}` in `{file}:{line}` [{evidence}]")
    lines.extend(["", "## Likely Tests", ""])
    lines.extend(f"- `{item}`" for item in report["likely_tests"] or ["none"])
    lines.extend(["", "## Changed Symbol Impact", ""])
    for item in report["changed_symbol_impact"][:20]:
        lines.append(f"- `{item['symbol']}` defined at `{item['definition']}`; references: `{len(item['references'])}`; likely tests: `{len(item['likely_tests'])}`")
    if not report["changed_symbol_impact"]:
        lines.append("- none")
    semantic = report.get("semantic", {})
    if semantic:
        engine = str(semantic.get("engine", "unknown"))
        heading = "Semantic V3" if engine.endswith("v3") else "Semantic V2"
        lines.extend(["", f"## {heading}", ""])
        lines.append(f"- Engine: `{engine}`")
        lines.append(f"- Symbol index entries: `{len(semantic.get('symbol_index', {}))}`")
        lines.append(f"- Import edges: `{len(semantic.get('import_edges', []))}`")
        lines.append(f"- Reference edges: `{len(semantic.get('reference_edges', []))}`")
        lines.append(f"- Endpoint handler links: `{len(semantic.get('endpoint_handler_links', []))}`")
        lines.append(f"- Data-flow-lite hints: `{len(semantic.get('data_flow_lite', []))}`")
        provider_outputs = semantic.get("provider_outputs", [])
        if provider_outputs:
            lines.extend(["", "## Provider Outputs", ""])
            for item in provider_outputs:
                error = f"; error `{item.get('error')}`" if item.get("error") else ""
                lines.append(f"- `{item.get('provider')}` from `{item.get('path')}`; symbols `{item.get('symbols')}`; references `{item.get('references')}`; calls `{item.get('calls')}`{error}")
        lines.extend(["", "## Optional Provider Readiness", ""])
        for name, provider in semantic.get("provider_status", {}).items():
            status = "available" if provider.get("available") else "not detected"
            lines.append(f"- `{name}`: {status}; used: `{provider.get('used', False)}`")
        lines.extend(["", "## Data-Flow-Lite", ""])
        flows = semantic.get("data_flow_lite", [])
        if flows:
            for item in flows[:20]:
                lines.append(f"- `{item.get('entry')}` -> `{item.get('handler')}` in `{item.get('file')}:{item.get('line')}`")
        else:
            lines.append("- none")
    lines.extend(["", "## Boundaries", ""])
    lines.extend(f"- {item}" for item in report["boundaries"])
    lines.extend(["", "## Deferred", ""])
    lines.extend(f"- {item}" for item in report["deferred"])
    return "\n".join(lines) + "\n"


def main() -> int:
    parser = argparse.ArgumentParser(description="Create a dependency-free TailTrail AST Lite, AST V1, Semantic V2, or opt-in Semantic V3 map.")
    parser.add_argument("--root", type=Path, default=Path.cwd())
    parser.add_argument("--changed", action="append", default=[], help="Changed or target file. Repeat for multiple files.")
    parser.add_argument("--depth", choices=("lite", "v1", "v2", "v3"), default="v1")
    parser.add_argument("--provider-output", action="append", default=[], help="Approved local provider JSON output to ingest for Semantic V3. Repeat for multiple files.")
    parser.add_argument("--approved", action="store_true", help="Approve Semantic V3 provider-output ingestion for this run.")
    parser.add_argument("--format", choices=("markdown", "json"), default="markdown")
    parser.add_argument("--limit", type=int, default=20)
    args = parser.parse_args()
    report = build(args.root.resolve(), args.changed, args.depth, max(args.limit, 1), args.provider_output, args.approved)
    if args.format == "json":
        print(json.dumps(report, indent=2, sort_keys=True))
    else:
        print(markdown(report), end="")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
