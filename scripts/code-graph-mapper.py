#!/usr/bin/env python3

from __future__ import annotations

import argparse
import ast
import hashlib
import json
import re
import subprocess
from datetime import datetime, timezone
from pathlib import Path
from typing import Any


SCHEMA_VERSION = "1"
SHARED_CACHE = Path("tailtrail-meta") / "code-graph-cache.json"
LOCAL_CACHE = Path(".tailtrail") / "code-graph-cache.json"

SKIP_DIRS = {
    ".git",
    ".hg",
    ".idea",
    ".svn",
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

SOURCE_EXTENSIONS = {
    ".cs",
    ".java",
    ".py",
    ".sql",
    ".tf",
    ".tfvars",
}

TEXT_EXTENSIONS = SOURCE_EXTENSIONS | {
    ".json",
    ".properties",
    ".toml",
    ".xml",
    ".yaml",
    ".yml",
}

WATCH_NAMES = {
    "pom.xml",
    "build.gradle",
    "build.gradle.kts",
    "gradle.properties",
    "requirements.txt",
    "pyproject.toml",
    "setup.py",
    "tox.ini",
    "pytest.ini",
    "sonar-project.properties",
    "package.json",
    "package-lock.json",
    "pnpm-lock.yaml",
    "yarn.lock",
    "Directory.Build.props",
    "Directory.Build.targets",
}

WATCH_SUFFIXES = {".csproj", ".sln"}
CONFIG_SUFFIXES = {".yaml", ".yml", ".json", ".properties", ".toml"}
TEST_HINTS = ("test", "tests", "spec", "specs")
PARTITION_MARKERS = WATCH_NAMES | {"Dockerfile", "Jenkinsfile", "Makefile", "go.mod", "Cargo.toml"}
RELEASE_NAMES = {
    "Jenkinsfile",
    "azure-pipelines.yml",
    "azure-pipelines.yaml",
    "buildspec.yml",
    "buildspec.yaml",
    "cloudbuild.yaml",
    "skaffold.yaml",
}
RELEASE_DIR_HINTS = {
    ".github/workflows",
    ".gitlab-ci.yml",
    "charts",
    "deploy",
    "deployment",
    "helm",
    "k8s",
    "kubernetes",
    "pipelines",
    "terraform",
}


def now_utc() -> str:
    return datetime.now(timezone.utc).isoformat()


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


def file_sha256(path: Path) -> str | None:
    if not path.is_file():
        return None
    digest = hashlib.sha256()
    try:
        with path.open("rb") as handle:
            for chunk in iter(lambda: handle.read(1024 * 1024), b""):
                digest.update(chunk)
    except OSError:
        return None
    return digest.hexdigest()


def file_metadata(path: Path) -> dict[str, Any] | None:
    digest = file_sha256(path)
    if digest is None:
        return None
    stat = path.stat()
    return {"sha256": digest, "mtime": int(stat.st_mtime), "size": stat.st_size}


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


def list_text_files(root: Path) -> list[Path]:
    files: list[Path] = []
    for path in root.rglob("*"):
        if is_skipped(path) or not path.is_file():
            continue
        if path.suffix in TEXT_EXTENSIONS or path.name in WATCH_NAMES or path.suffix in WATCH_SUFFIXES:
            files.append(path)
    return sorted(files)


def is_release_path(path: Path, root: Path) -> bool:
    rel = safe_relative(path, root) or path.as_posix()
    lowered = rel.lower()
    if path.name in RELEASE_NAMES or path.name == ".gitlab-ci.yml":
        return True
    return any(lowered == hint or lowered.startswith(f"{hint}/") or f"/{hint}/" in lowered for hint in RELEASE_DIR_HINTS)


def partition_root_for(path: Path, root: Path) -> Path:
    current = path.parent if path.is_file() else path
    best: Path | None = None
    while current.resolve() != root.resolve() and safe_relative(current, root) is not None:
        has_marker = any((current / name).is_file() for name in PARTITION_MARKERS) or any(item.suffix in WATCH_SUFFIXES for item in current.glob("*"))
        if has_marker:
            best = current
        current = current.parent
    if best is not None:
        return best
    rel = safe_relative(path, root)
    if rel:
        first = rel.split("/", 1)[0]
        candidate = root / first
        if candidate.exists():
            return candidate
    return root


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


def line_number(body: str, offset: int) -> int:
    return body.count("\n", 0, offset) + 1


def add_symbol(symbols: list[dict[str, Any]], kind: str, name: str, language: str, file: str, line: int, confidence: str) -> None:
    if not name:
        return
    symbols.append(
        {
            "kind": kind,
            "name": name,
            "language": language,
            "file": file,
            "line": line,
            "confidence": confidence,
        }
    )


def extract_python(path: Path, root: Path, body: str) -> dict[str, list[dict[str, Any]]]:
    rel = safe_relative(path, root) or path.as_posix()
    symbols: list[dict[str, Any]] = []
    endpoints: list[dict[str, Any]] = []
    hierarchy: list[dict[str, Any]] = []
    call_chains: list[dict[str, Any]] = []
    try:
        tree = ast.parse(body)
    except SyntaxError:
        tree = None

    if tree is not None:
        for node in ast.walk(tree):
            if isinstance(node, ast.ClassDef):
                add_symbol(symbols, "class", node.name, "python", rel, node.lineno, "python_ast")
                for base in node.bases:
                    base_name = getattr(base, "id", None) or getattr(base, "attr", None)
                    if base_name:
                        hierarchy.append(
                            {
                                "type": node.name,
                                "inherits": base_name,
                                "language": "python",
                                "file": rel,
                                "line": node.lineno,
                                "confidence": "python_ast",
                            }
                        )
            elif isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef)):
                add_symbol(symbols, "function", node.name, "python", rel, node.lineno, "python_ast")
                for decorator in node.decorator_list:
                    text = ast.unparse(decorator) if hasattr(ast, "unparse") else ""
                    if any(term in text.lower() for term in (".get(", ".post(", ".put(", ".delete(", ".route(")):
                        endpoints.append(
                            {
                                "route": text,
                                "method": "unknown",
                                "handler": node.name,
                                "language": "python",
                                "file": rel,
                                "line": node.lineno,
                                "framework_hint": "decorator-route",
                                "confidence": "python_ast",
                            }
                        )
                for child in ast.walk(node):
                    if isinstance(child, ast.Call):
                        callee = ""
                        if isinstance(child.func, ast.Name):
                            callee = child.func.id
                        elif isinstance(child.func, ast.Attribute):
                            callee = child.func.attr
                        if callee:
                            call_chains.append(
                                {
                                    "caller": node.name,
                                    "callee": callee,
                                    "language": "python",
                                    "file": rel,
                                    "line": getattr(child, "lineno", node.lineno),
                                    "confidence": "python_ast",
                                }
                            )

    return {"symbols": symbols, "endpoints": endpoints, "type_hierarchy": hierarchy, "call_chains": call_chains}


def extract_java(path: Path, root: Path, body: str) -> dict[str, list[dict[str, Any]]]:
    rel = safe_relative(path, root) or path.as_posix()
    symbols: list[dict[str, Any]] = []
    endpoints: list[dict[str, Any]] = []
    hierarchy: list[dict[str, Any]] = []
    db_tables: list[dict[str, Any]] = []

    class_pattern = re.compile(r"\b(class|interface|enum)\s+(\w+)(?:\s+extends\s+(\w+))?(?:\s+implements\s+([\w,\s]+))?")
    method_pattern = re.compile(r"\b(?:public|private|protected|static|final|synchronized|\s)+[\w<>\[\], ?]+\s+(\w+)\s*\([^;{}]*\)\s*\{")
    route_pattern = re.compile(r"@(GetMapping|PostMapping|PutMapping|DeleteMapping|PatchMapping|RequestMapping)\s*(?:\(([^)]*)\))?")
    table_pattern = re.compile(r"@Table\s*\([^)]*name\s*=\s*\"([^\"]+)\"")

    for match in class_pattern.finditer(body):
        kind, name, extends, implements = match.group(1), match.group(2), match.group(3), match.group(4)
        line = line_number(body, match.start())
        add_symbol(symbols, kind, name, "java", rel, line, "heuristic")
        if extends:
            hierarchy.append({"type": name, "extends": extends, "language": "java", "file": rel, "line": line, "confidence": "heuristic"})
        if implements:
            for item in [part.strip() for part in implements.split(",") if part.strip()]:
                hierarchy.append({"type": name, "implements": item, "language": "java", "file": rel, "line": line, "confidence": "heuristic"})

    for match in method_pattern.finditer(body):
        add_symbol(symbols, "method", match.group(1), "java", rel, line_number(body, match.start()), "heuristic")

    for match in route_pattern.finditer(body):
        endpoints.append(
            {
                "route": (match.group(2) or "").strip() or "annotation-default",
                "method": match.group(1),
                "handler": "nearby Java method/class",
                "language": "java",
                "file": rel,
                "line": line_number(body, match.start()),
                "framework_hint": "Spring annotation",
                "confidence": "heuristic",
            }
        )

    for match in table_pattern.finditer(body):
        db_tables.append({"table": match.group(1), "source": "jpa-table-annotation", "language": "java", "file": rel, "line": line_number(body, match.start()), "confidence": "heuristic"})

    return {"symbols": symbols, "endpoints": endpoints, "type_hierarchy": hierarchy, "db_tables": db_tables}


def extract_dotnet(path: Path, root: Path, body: str) -> dict[str, list[dict[str, Any]]]:
    rel = safe_relative(path, root) or path.as_posix()
    symbols: list[dict[str, Any]] = []
    endpoints: list[dict[str, Any]] = []
    hierarchy: list[dict[str, Any]] = []
    db_tables: list[dict[str, Any]] = []

    type_pattern = re.compile(r"\b(class|interface|record|struct|enum)\s+(\w+)(?:\s*:\s*([\w,\s<>]+))?")
    method_pattern = re.compile(r"\b(?:public|private|protected|internal|static|async|virtual|override|\s)+[\w<>\[\], ?]+\s+(\w+)\s*\([^;{}]*\)\s*\{")
    route_pattern = re.compile(r"\[(HttpGet|HttpPost|HttpPut|HttpDelete|HttpPatch|Route)(?:\(([^)]*)\))?\]")
    dbset_pattern = re.compile(r"DbSet<\s*(\w+)\s*>\s+(\w+)")

    for match in type_pattern.finditer(body):
        kind, name, bases = match.group(1), match.group(2), match.group(3)
        line = line_number(body, match.start())
        add_symbol(symbols, kind, name, "dotnet", rel, line, "heuristic")
        if bases:
            for item in [part.strip() for part in bases.split(",") if part.strip()]:
                hierarchy.append({"type": name, "inherits_or_implements": item, "language": "dotnet", "file": rel, "line": line, "confidence": "heuristic"})

    for match in method_pattern.finditer(body):
        add_symbol(symbols, "method", match.group(1), "dotnet", rel, line_number(body, match.start()), "heuristic")

    for match in route_pattern.finditer(body):
        endpoints.append(
            {
                "route": (match.group(2) or "").strip() or "attribute-default",
                "method": match.group(1),
                "handler": "nearby .NET method/class",
                "language": "dotnet",
                "file": rel,
                "line": line_number(body, match.start()),
                "framework_hint": "ASP.NET attribute",
                "confidence": "heuristic",
            }
        )

    for match in dbset_pattern.finditer(body):
        db_tables.append({"table": match.group(2), "entity": match.group(1), "source": "ef-dbset", "language": "dotnet", "file": rel, "line": line_number(body, match.start()), "confidence": "heuristic"})

    return {"symbols": symbols, "endpoints": endpoints, "type_hierarchy": hierarchy, "db_tables": db_tables}


def extract_sql(path: Path, root: Path, body: str) -> dict[str, list[dict[str, Any]]]:
    rel = safe_relative(path, root) or path.as_posix()
    symbols: list[dict[str, Any]] = []
    db_tables: list[dict[str, Any]] = []
    table_pattern = re.compile(r"\b(?:CREATE\s+TABLE|ALTER\s+TABLE|INSERT\s+INTO|UPDATE|DELETE\s+FROM|FROM|JOIN)\s+([A-Za-z_][\w.]*)", re.IGNORECASE)
    proc_pattern = re.compile(r"\bCREATE\s+(?:PROCEDURE|PROC|FUNCTION)\s+([A-Za-z_][\w.]*)", re.IGNORECASE)

    for match in table_pattern.finditer(body):
        db_tables.append({"table": match.group(1), "source": "sql-reference", "language": "sql", "file": rel, "line": line_number(body, match.start()), "confidence": "heuristic"})
    for match in proc_pattern.finditer(body):
        add_symbol(symbols, "sql-routine", match.group(1), "sql", rel, line_number(body, match.start()), "heuristic")

    return {"symbols": symbols, "db_tables": db_tables}


def extract_terraform(path: Path, root: Path, body: str) -> dict[str, list[dict[str, Any]]]:
    rel = safe_relative(path, root) or path.as_posix()
    symbols: list[dict[str, Any]] = []
    config_usage: list[dict[str, Any]] = []
    block_pattern = re.compile(r'\b(resource|data|module|variable|output|provider)\s+"([^"]+)"(?:\s+"([^"]+)")?')
    ref_pattern = re.compile(r"\b(var|module|local|data)\.([A-Za-z_][\w-]*)")

    for match in block_pattern.finditer(body):
        kind, first, second = match.group(1), match.group(2), match.group(3)
        name = f"{first}.{second}" if second else first
        add_symbol(symbols, kind, name, "terraform", rel, line_number(body, match.start()), "heuristic")
    for match in ref_pattern.finditer(body):
        config_usage.append({"key": f"{match.group(1)}.{match.group(2)}", "source": "terraform-reference", "language": "terraform", "file": rel, "line": line_number(body, match.start()), "confidence": "heuristic"})

    return {"symbols": symbols, "config_usage": config_usage}


def extract_config_usage(path: Path, root: Path, body: str) -> list[dict[str, Any]]:
    rel = safe_relative(path, root) or path.as_posix()
    if path.suffix not in CONFIG_SUFFIXES and path.name not in WATCH_NAMES:
        return []
    usage: list[dict[str, Any]] = []
    key_pattern = re.compile(r"^\s*([A-Za-z_][\w.-]{2,})\s*[:=]", re.MULTILINE)
    for match in key_pattern.finditer(body):
        usage.append({"key": match.group(1), "source": "config-key", "language": "config", "file": rel, "line": line_number(body, match.start()), "confidence": "heuristic"})
    return usage[:100]


def extract_service_edges(path: Path, root: Path, body: str) -> list[dict[str, Any]]:
    rel = safe_relative(path, root) or path.as_posix()
    edges: list[dict[str, Any]] = []
    for match in re.finditer(r"https?://([A-Za-z0-9_.:-]+)(/[A-Za-z0-9_./{}:-]*)?", body):
        edges.append(
            {
                "source_file": rel,
                "line": line_number(body, match.start()),
                "target": match.group(1),
                "path_hint": match.group(2) or "",
                "edge_type": "http-url",
                "confidence": "heuristic",
            }
        )
    for match in re.finditer(r"\b(?:service|client|base[-_.]?url|endpoint|host)\s*[:=]\s*[\"']?([A-Za-z0-9_.:-]{4,})", body, re.IGNORECASE):
        edges.append(
            {
                "source_file": rel,
                "line": line_number(body, match.start()),
                "target": match.group(1),
                "path_hint": "",
                "edge_type": "service-config",
                "confidence": "heuristic",
            }
        )
    for match in re.finditer(r"<ProjectReference\s+Include=\"([^\"]+)\"", body):
        edges.append(
            {
                "source_file": rel,
                "line": line_number(body, match.start()),
                "target": match.group(1),
                "path_hint": "",
                "edge_type": "dotnet-project-reference",
                "confidence": "heuristic",
            }
        )
    return edges[:100]


def extract_language_data(path: Path, root: Path) -> dict[str, list[dict[str, Any]]]:
    body = read_text(path)
    language = language_for(path)
    data: dict[str, list[dict[str, Any]]] = {
        "symbols": [],
        "references": [],
        "call_chains": [],
        "type_hierarchy": [],
        "endpoints": [],
        "db_tables": [],
        "config_usage": [],
        "service_edges": [],
    }
    if not body:
        return data
    if language == "python":
        extracted = extract_python(path, root, body)
    elif language == "java":
        extracted = extract_java(path, root, body)
    elif language == "dotnet":
        extracted = extract_dotnet(path, root, body)
    elif language == "sql":
        extracted = extract_sql(path, root, body)
    elif language == "terraform":
        extracted = extract_terraform(path, root, body)
    else:
        extracted = {}
    for key, values in extracted.items():
        data[key].extend(values)
    data["config_usage"].extend(extract_config_usage(path, root, body))
    data["service_edges"].extend(extract_service_edges(path, root, body))
    return data


def looks_like_test(path: Path) -> bool:
    lowered = path.as_posix().lower()
    return any(f"/{hint}" in lowered or lowered.startswith(hint) for hint in TEST_HINTS) or path.name.lower().startswith("test_") or "test" in path.stem.lower()


def tokens_for(path: Path, root: Path) -> set[str]:
    rel = safe_relative(path, root) or path.name
    stem = path.stem
    no_ext = rel[: -len(path.suffix)] if path.suffix else rel
    dotted = no_ext.replace("/", ".")
    return {item for item in {rel, path.name, stem, no_ext, dotted, stem.replace("-", "_"), stem.replace("_", "-")} if len(item) >= 3}


def find_references(root: Path, target_files: list[Path], candidates: list[Path], limit: int) -> list[dict[str, Any]]:
    refs: list[dict[str, Any]] = []
    target_tokens = {token for path in target_files for token in tokens_for(path, root)}
    lowered_tokens = {token.lower() for token in target_tokens}
    for path in candidates:
        if path in target_files or path.suffix not in TEXT_EXTENSIONS:
            continue
        body = read_text(path)
        if not body:
            continue
        lowered = body.lower()
        for token in sorted(lowered_tokens, key=len, reverse=True):
            found = lowered.find(token)
            if found >= 0:
                refs.append(
                    {
                        "target": token,
                        "referring_file": safe_relative(path, root) or path.as_posix(),
                        "line": line_number(body, found),
                        "reference_type": "text-or-import-token",
                        "confidence": "heuristic",
                    }
                )
                break
        if len(refs) >= limit:
            break
    return refs


def likely_tests_and_callers(root: Path, target_files: list[Path], candidates: list[Path], limit: int) -> tuple[list[str], list[str]]:
    tests: list[str] = []
    callers: list[str] = []
    target_tokens = {token.lower() for path in target_files for token in tokens_for(path, root)}
    for path in candidates:
        if path in target_files or path.suffix not in TEXT_EXTENSIONS:
            continue
        rel = safe_relative(path, root)
        if rel is None:
            continue
        lowered_path = rel.lower()
        body = read_text(path).lower()
        matched = any(token in lowered_path or token in body for token in target_tokens)
        if not matched:
            continue
        if looks_like_test(path):
            tests.append(rel)
        else:
            callers.append(rel)
        if len(tests) >= limit and len(callers) >= limit:
            break
    return list(dict.fromkeys(tests))[:limit], list(dict.fromkeys(callers))[:limit]


def nearby_watch_files(root: Path, target_files: list[Path], candidates: list[Path], limit: int) -> list[Path]:
    found: dict[str, Path] = {}
    for path in candidates:
        if path.name not in WATCH_NAMES and path.suffix not in WATCH_SUFFIXES:
            continue
        rel = safe_relative(path, root)
        if rel is not None:
            found[rel] = path
    for target in target_files:
        for parent in [target.parent, *target.parents]:
            if safe_relative(parent, root) is None and parent.resolve() != root.resolve():
                continue
            for name in WATCH_NAMES:
                candidate = parent / name
                rel = safe_relative(candidate, root)
                if candidate.is_file() and rel is not None:
                    found[rel] = candidate
            if parent.resolve() == root.resolve():
                break
    return [found[key] for key in sorted(found)[:limit]]


def workspace_overlays(root: Path, _target_files: list[Path], scanner_files: list[Path]) -> list[dict[str, Any]]:
    overlays: list[dict[str, Any]] = []
    for path in scanner_files:
        rel = safe_relative(path, root)
        if rel:
            overlays.append({"type": "scanner-evidence", "path": rel, "confidence": "user-provided"})
    return overlays


def read_codeowners(root: Path) -> list[tuple[str, list[str]]]:
    candidates = [root / "CODEOWNERS", root / ".github" / "CODEOWNERS", root / "docs" / "CODEOWNERS"]
    entries: list[tuple[str, list[str]]] = []
    for path in candidates:
        body = read_text(path)
        if not body:
            continue
        for raw in body.splitlines():
            line = raw.strip()
            if not line or line.startswith("#"):
                continue
            parts = line.split()
            if len(parts) >= 2:
                entries.append((parts[0], parts[1:]))
        if entries:
            break
    return entries[:200]


def owner_for(rel: str, entries: list[tuple[str, list[str]]]) -> list[str]:
    owners: list[str] = []
    for pattern, values in entries:
        normalized = pattern.lstrip("/")
        if normalized == "*" or rel.startswith(normalized.rstrip("*")) or Path(rel).match(normalized):
            owners = values
    return owners


def partition_map(root: Path, scope_paths: list[Path], candidates: list[Path], limit: int) -> list[dict[str, Any]]:
    partitions: dict[str, dict[str, Any]] = {}
    for path in candidates:
        partition_root = partition_root_for(path, root)
        rel_root = safe_relative(partition_root, root) or "."
        rel_file = safe_relative(path, root)
        if rel_file is None:
            continue
        item = partitions.setdefault(
            rel_root,
            {
                "partition": rel_root,
                "files": 0,
                "languages": {},
                "manifests": [],
                "tests": [],
                "release_paths": [],
                "in_scope": False,
            },
        )
        item["files"] += 1
        language = language_for(path)
        if language:
            item["languages"][language] = item["languages"].get(language, 0) + 1
        if path.name in WATCH_NAMES or path.suffix in WATCH_SUFFIXES:
            item["manifests"].append(rel_file)
        if looks_like_test(path):
            item["tests"].append(rel_file)
        if is_release_path(path, root):
            item["release_paths"].append(rel_file)
    scope_roots = {safe_relative(partition_root_for(path, root), root) or "." for path in scope_paths}
    for key, item in partitions.items():
        item["in_scope"] = key in scope_roots
        item["manifests"] = item["manifests"][:10]
        item["tests"] = item["tests"][:10]
        item["release_paths"] = item["release_paths"][:10]
    return sorted(partitions.values(), key=lambda item: (not item["in_scope"], item["partition"]))[:limit]


def owner_test_release_map(root: Path, scope_paths: list[Path], candidates: list[Path], likely_tests: list[str], limit: int) -> dict[str, Any]:
    codeowners = read_codeowners(root)
    release_paths = [safe_relative(path, root) for path in candidates if is_release_path(path, root) and safe_relative(path, root)]
    mappings: list[dict[str, Any]] = []
    for path in scope_paths:
        rel = safe_relative(path, root)
        if rel is None:
            continue
        partition = safe_relative(partition_root_for(path, root), root) or "."
        partition_tests = [item for item in likely_tests if item.startswith(partition.rstrip("/") + "/") or partition == "."]
        partition_release = [item for item in release_paths if item.startswith(partition.rstrip("/") + "/") or partition == "."]
        mappings.append(
            {
                "file": rel,
                "partition": partition,
                "owners": owner_for(rel, codeowners),
                "likely_tests": partition_tests[:limit],
                "release_paths": partition_release[:limit],
                "confidence": "heuristic",
            }
        )
    return {
        "codeowners_found": bool(codeowners),
        "mappings": mappings[:limit],
        "release_paths": list(dict.fromkeys(release_paths))[:limit],
    }


def endpoint_service_table_flows(graph_data: dict[str, list[dict[str, Any]]], limit: int) -> list[dict[str, Any]]:
    flows: list[dict[str, Any]] = []
    calls_by_file: dict[str, list[dict[str, Any]]] = {}
    tables_by_file: dict[str, list[dict[str, Any]]] = {}
    config_by_file: dict[str, list[dict[str, Any]]] = {}
    services_by_file: dict[str, list[dict[str, Any]]] = {}
    for item in graph_data["call_chains"]:
        calls_by_file.setdefault(str(item.get("file", "")), []).append(item)
    for item in graph_data["db_tables"]:
        tables_by_file.setdefault(str(item.get("file", "")), []).append(item)
    for item in graph_data["config_usage"]:
        config_by_file.setdefault(str(item.get("file", "")), []).append(item)
    for item in graph_data.get("service_edges", []):
        services_by_file.setdefault(str(item.get("source_file", "")), []).append(item)
    for endpoint in graph_data["endpoints"]:
        file = str(endpoint.get("file", ""))
        flows.append(
            {
                "endpoint": endpoint.get("route", "unknown"),
                "method": endpoint.get("method", "unknown"),
                "handler": endpoint.get("handler", "unknown"),
                "file": file,
                "line": endpoint.get("line", "?"),
                "service_call_hints": [item.get("callee") for item in calls_by_file.get(file, [])[:10]],
                "external_service_hints": [item.get("target") for item in services_by_file.get(file, [])[:10]],
                "db_table_hints": [item.get("table") for item in tables_by_file.get(file, [])[:10]],
                "config_hints": [item.get("key") for item in config_by_file.get(file, [])[:10]],
                "confidence": "heuristic",
            }
        )
    if not flows:
        for table in graph_data["db_tables"][:limit]:
            file = str(table.get("file", ""))
            flows.append(
                {
                    "endpoint": "none detected",
                    "method": "database-touchpoint",
                    "handler": table.get("source", "unknown"),
                    "file": file,
                    "line": table.get("line", "?"),
                    "service_call_hints": [item.get("callee") for item in calls_by_file.get(file, [])[:10]],
                    "external_service_hints": [item.get("target") for item in services_by_file.get(file, [])[:10]],
                    "db_table_hints": [table.get("table")],
                    "config_hints": [item.get("key") for item in config_by_file.get(file, [])[:10]],
                    "confidence": "heuristic",
                }
            )
    return flows[:limit]


def language_profiles(paths: list[Path]) -> dict[str, dict[str, Any]]:
    profiles: dict[str, dict[str, Any]] = {}
    for path in paths:
        language = language_for(path)
        if not language:
            continue
        profile = profiles.setdefault(language, {"level": 1, "files": 0})
        profile["files"] += 1
        if language == "python":
            profile["level"] = max(profile["level"], 2)
    return profiles


def confidence_for(symbols: list[dict[str, Any]], refs: list[dict[str, Any]], tests: list[str], callers: list[str]) -> str:
    score = 0
    if symbols:
        score += 1
    if refs:
        score += 1
    if tests:
        score += 1
    if callers:
        score += 1
    if score >= 3:
        return "high"
    if score >= 1:
        return "medium"
    return "low"


def build_graph(root: Path, changed_values: list[str], mode: str, scanner_values: list[str], limit: int) -> dict[str, Any]:
    changed_paths = normalize_paths(root, changed_values or git_changed(root))
    scanner_paths = normalize_paths(root, scanner_values)
    candidates = list_text_files(root)
    scope_paths = changed_paths or scanner_paths
    if not scope_paths:
        scope_paths = [path for path in candidates if language_for(path)][:limit]

    watch_paths = nearby_watch_files(root, scope_paths, candidates, limit=30)
    extraction_paths = list(dict.fromkeys([*scope_paths, *watch_paths, *scanner_paths]))

    graph_data: dict[str, list[dict[str, Any]]] = {
        "symbols": [],
        "references": [],
        "call_chains": [],
        "type_hierarchy": [],
        "endpoints": [],
        "db_tables": [],
        "config_usage": [],
        "service_edges": [],
    }
    for path in extraction_paths:
        extracted = extract_language_data(path, root)
        for key, values in extracted.items():
            graph_data[key].extend(values)

    graph_data["references"].extend(find_references(root, scope_paths, candidates, limit=limit * 4))
    likely_tests, likely_callers = likely_tests_and_callers(root, scope_paths, candidates, limit=limit)
    suggested_read_order = list(
        dict.fromkeys(
            [
                *[safe_relative(path, root) for path in scope_paths if safe_relative(path, root)],
                *likely_tests[:5],
                *likely_callers[:5],
                *[safe_relative(path, root) for path in watch_paths[:8] if safe_relative(path, root)],
            ]
        )
    )

    source_files = {}
    for path in list(dict.fromkeys([*scope_paths, *[root / item for item in likely_tests[:5]], *[root / item for item in likely_callers[:5]]])):
        rel = safe_relative(path, root)
        meta = file_metadata(path)
        if rel and meta:
            source_files[rel] = meta

    watch_files = {}
    for path in watch_paths:
        rel = safe_relative(path, root)
        meta = file_metadata(path)
        if rel and meta:
            watch_files[rel] = {**meta, "reason": "nearby dependency/build/config manifest"}

    scanner_evidence = {}
    for path in scanner_paths:
        rel = safe_relative(path, root)
        meta = file_metadata(path)
        if rel and meta:
            scanner_evidence[rel] = {**meta, "reason": "scanner evidence provided for graph scope"}

    scope = [safe_relative(path, root) for path in scope_paths if safe_relative(path, root)]
    confidence = confidence_for(graph_data["symbols"], graph_data["references"], likely_tests, likely_callers)
    cache_key_seed = json.dumps({"root": root.as_posix(), "scope": scope, "graph_mode": mode, "schema_version": SCHEMA_VERSION}, sort_keys=True)

    return {
        "schema_version": SCHEMA_VERSION,
        "created_at": now_utc(),
        "updated_at": now_utc(),
        "tailtrail_version": "local",
        "root": root.as_posix(),
        "cache_key": hashlib.sha256(cache_key_seed.encode("utf-8")).hexdigest(),
        "graph_mode": mode,
        "scope": scope,
        "task_tags": sorted(set(mode.replace("-", " ").replace("_", " ").split())),
        "language_profiles": language_profiles(extraction_paths),
        "source_files": source_files,
        "watch_files": watch_files,
        "scanner_evidence": scanner_evidence,
        "graph": {
            "changed_files": scope,
            "symbols": graph_data["symbols"][: limit * 20],
            "references": graph_data["references"][: limit * 20],
            "call_chains": graph_data["call_chains"][: limit * 20],
            "type_hierarchy": graph_data["type_hierarchy"][: limit * 20],
            "endpoints": graph_data["endpoints"][: limit * 10],
            "db_tables": graph_data["db_tables"][: limit * 20],
            "config_usage": graph_data["config_usage"][: limit * 20],
            "service_edges": graph_data["service_edges"][: limit * 20],
            "partitions": partition_map(root, scope_paths, candidates, limit=limit),
            "endpoint_service_table_flows": endpoint_service_table_flows(graph_data, limit=limit),
            "owner_test_release_map": owner_test_release_map(root, scope_paths, candidates, likely_tests, limit=limit),
            "workspace_overlays": workspace_overlays(root, scope_paths, scanner_paths),
            "likely_callers": likely_callers,
            "likely_tests": likely_tests,
            "nearby_manifests": [safe_relative(path, root) for path in watch_paths if safe_relative(path, root)],
            "risk_tags": risk_tags(scope, graph_data, watch_files, scanner_evidence),
            "confidence": confidence,
            "suggested_read_order": suggested_read_order[: limit * 3],
        },
        "freshness": {
            "status": "fresh",
            "checked_at": now_utc(),
            "reasons": [],
        },
    }


def risk_tags(scope: list[str], graph_data: dict[str, list[dict[str, Any]]], watch_files: dict[str, Any], scanner_evidence: dict[str, Any]) -> list[str]:
    tags: set[str] = set()
    text = " ".join(scope).lower()
    for term, tag in {
        "auth": "auth/security",
        "security": "security",
        "token": "secret/token",
        "password": "secret/password",
        "payment": "payment",
        "migration": "data migration",
        "sonar": "sonar/quality",
        "pipeline": "pipeline",
        "workflow": "pipeline",
    }.items():
        if term in text:
            tags.add(tag)
    if graph_data["endpoints"]:
        tags.add("endpoint")
    if graph_data["db_tables"]:
        tags.add("database")
    if graph_data["config_usage"]:
        tags.add("config")
    if watch_files:
        tags.add("manifest/config")
    if scanner_evidence:
        tags.add("scanner evidence")
    return sorted(tags)


def cache_path(root: Path, override: Path | None) -> Path:
    if override:
        return override if override.is_absolute() else root / override
    return root / SHARED_CACHE


def load_cache(path: Path) -> tuple[dict[str, Any] | None, str | None]:
    if not path.exists():
        return None, "missing"
    try:
        data = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError) as error:
        return None, f"invalid: {error}"
    if not isinstance(data, dict):
        return None, "invalid: cache root is not an object"
    return data, None


def status_for(root: Path, cache: dict[str, Any] | None, changed_values: list[str]) -> dict[str, Any]:
    if cache is None:
        return {"status": "missing", "reasons": ["No Code Graph Mapper cache exists."], "scope": changed_values}
    reasons: list[str] = []
    invalid: list[str] = []
    if cache.get("schema_version") != SCHEMA_VERSION:
        invalid.append("Cache schema version is unsupported.")
    cache_root = cache.get("root")
    if cache_root and Path(str(cache_root)).resolve() != root.resolve():
        invalid.append("Cache root does not match current project root.")

    target_scope = set(changed_values)
    cached_scope = {str(item) for item in cache.get("scope", []) if item}
    if target_scope and not target_scope.issubset(cached_scope) and not target_scope.intersection(cached_scope):
        reasons.append("Cache exists, but requested files are outside the cached scope.")

    for group in ("source_files", "watch_files", "scanner_evidence"):
        values = cache.get(group, {})
        if not isinstance(values, dict):
            invalid.append(f"{group} is not an object.")
            continue
        for rel, metadata in values.items():
            if not isinstance(metadata, dict):
                invalid.append(f"{group}.{rel} metadata is not an object.")
                continue
            expected = metadata.get("sha256")
            if not isinstance(expected, str) or not expected:
                invalid.append(f"{group}.{rel} has no usable sha256.")
                continue
            actual = file_sha256(root / rel)
            if actual is None:
                reasons.append(f"{rel} is missing.")
            elif actual != expected:
                reasons.append(f"{rel} changed after the graph was created.")

    if invalid:
        return {"status": "invalid", "reasons": invalid, "scope": list(cached_scope)}
    if reasons:
        return {"status": "stale", "reasons": reasons, "scope": list(cached_scope)}
    return {"status": "fresh", "reasons": ["Cached graph scope and watched file hashes still match."], "scope": list(cached_scope)}


def write_cache(path: Path, data: dict[str, Any]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(data, indent=2) + "\n", encoding="utf-8")


def markdown_report(data: dict[str, Any], status: dict[str, Any] | None = None, path: Path | None = None) -> str:
    graph = data.get("graph", {}) if isinstance(data.get("graph"), dict) else {}
    lines = [
        "# TailTrail Code Graph Mapper",
        "",
        "This is a compact metadata graph, not a complete semantic proof. Read exact source before editing.",
        "",
        "## Cache",
        "",
    ]
    if path:
        lines.append(f"- Path: `{path.as_posix()}`")
    lines.extend(
        [
            f"- Status: `{(status or data.get('freshness', {})).get('status', 'fresh')}`",
            f"- Mode: `{data.get('graph_mode', 'unspecified')}`",
            f"- Confidence: `{graph.get('confidence', 'unknown')}`",
            "",
            "## Scope",
            "",
        ]
    )
    scope = data.get("scope", [])
    lines.extend(f"- `{item}`" for item in scope) if scope else lines.append("- none")

    lines.extend(["", "## Suggested Read Order", ""])
    read_order = graph.get("suggested_read_order", [])
    lines.extend(f"- `{item}`" for item in read_order) if read_order else lines.append("- none")

    lines.extend(["", "## Language Profiles", ""])
    profiles = data.get("language_profiles", {})
    if profiles:
        for name, profile in sorted(profiles.items()):
            lines.append(f"- `{name}`: level `{profile.get('level')}`, files `{profile.get('files')}`")
    else:
        lines.append("- none")

    for title, key, label in (
        ("Symbols", "symbols", "name"),
        ("References", "references", "target"),
        ("Call Chain Hints", "call_chains", "callee"),
        ("Type Hierarchy Hints", "type_hierarchy", "type"),
        ("Endpoint Hints", "endpoints", "route"),
        ("DB Table Hints", "db_tables", "table"),
        ("Config Usage Hints", "config_usage", "key"),
        ("External Service Hints", "service_edges", "target"),
    ):
        lines.extend(["", f"## {title}", ""])
        values = graph.get(key, [])
        if not values:
            lines.append("- none detected")
            continue
        for item in values[:20]:
            file = item.get("file") or item.get("referring_file") or "unknown"
            line = item.get("line", "?")
            value = item.get(label, item.get("name", "unknown"))
            confidence = item.get("confidence", "heuristic")
            lines.append(f"- `{value}` in `{file}:{line}` ({confidence})")

    lines.extend(["", "## Partitions", ""])
    partitions = graph.get("partitions", [])
    if partitions:
        for item in partitions[:20]:
            marker = "in scope" if item.get("in_scope") else "nearby"
            languages = ", ".join(f"{key}:{value}" for key, value in sorted(item.get("languages", {}).items())) or "none"
            lines.append(f"- `{item.get('partition')}` ({marker}); files `{item.get('files')}`; languages `{languages}`")
    else:
        lines.append("- none detected")

    lines.extend(["", "## Endpoint To Service To Table Flows", ""])
    flows = graph.get("endpoint_service_table_flows", [])
    if flows:
        for item in flows[:20]:
            services = ", ".join(str(value) for value in item.get("external_service_hints", []) if value) or "none"
            tables = ", ".join(str(value) for value in item.get("db_table_hints", []) if value) or "none"
            calls = ", ".join(str(value) for value in item.get("service_call_hints", []) if value) or "none"
            lines.append(f"- `{item.get('method')} {item.get('endpoint')}` in `{item.get('file')}:{item.get('line')}`; calls `{calls}`; services `{services}`; tables `{tables}`")
    else:
        lines.append("- none detected")

    lines.extend(["", "## Owner / Test / Release Path Mapping", ""])
    owner_map = graph.get("owner_test_release_map", {})
    mappings = owner_map.get("mappings", []) if isinstance(owner_map, dict) else []
    if mappings:
        for item in mappings[:20]:
            owners = ", ".join(item.get("owners", [])) or "none detected"
            tests = ", ".join(item.get("likely_tests", [])) or "none detected"
            releases = ", ".join(item.get("release_paths", [])) or "none detected"
            lines.append(f"- `{item.get('file')}`; owners `{owners}`; tests `{tests}`; release paths `{releases}`")
    else:
        lines.append("- none detected")

    lines.extend(["", "## Freshness Reasons", ""])
    reasons = (status or data.get("freshness", {})).get("reasons", [])
    lines.extend(f"- {reason}" for reason in reasons) if reasons else lines.append("- none")

    lines.extend(["", "## Boundaries", ""])
    lines.extend(
        [
            "- Metadata only; no source snippets are stored.",
            "- No scanner commands are executed.",
            "- No vector database, graph database, background service, or model call is used.",
            "- Advanced graph fields use explainable local signals; read exact source before editing.",
        ]
    )
    return "\n".join(lines) + "\n"


def command_map(args: argparse.Namespace) -> int:
    root = args.root.resolve()
    data = build_graph(root, args.changed, args.mode, args.scanner_evidence, max(args.limit, 1))
    path = cache_path(root, args.cache)
    write_cache(path, data)
    status = status_for(root, data, args.changed)
    if args.format == "json":
        print(json.dumps({"cache_path": path.as_posix(), "status": status, "cache": data}, indent=2))
    else:
        print(markdown_report(data, status, path), end="")
    return 0


def command_status(args: argparse.Namespace) -> int:
    root = args.root.resolve()
    path = cache_path(root, args.cache)
    cache, error = load_cache(path)
    if cache is None:
        status = {"status": "missing" if error == "missing" else "invalid", "reasons": [error or "missing"], "scope": args.changed}
        data = {"graph_mode": args.mode, "scope": args.changed, "language_profiles": {}, "graph": {"confidence": "unknown", "suggested_read_order": []}, "freshness": status}
    else:
        status = status_for(root, cache, args.changed)
        data = cache
    if args.format == "json":
        print(json.dumps({"cache_path": path.as_posix(), "status": status, "cache": data if cache else None}, indent=2))
    else:
        print(markdown_report(data, status, path), end="")
    return 0 if status["status"] == "fresh" else 1


def command_refresh(args: argparse.Namespace) -> int:
    root = args.root.resolve()
    path = cache_path(root, args.cache)
    previous, _ = load_cache(path)
    previous_status = status_for(root, previous, args.changed) if previous else {"status": "missing", "reasons": ["No previous cache."], "scope": args.changed}
    data = build_graph(root, args.changed, args.mode, args.scanner_evidence, max(args.limit, 1))
    data["refresh"] = {"previous_status": previous_status["status"], "previous_reasons": previous_status["reasons"]}
    write_cache(path, data)
    status = status_for(root, data, args.changed)
    if args.format == "json":
        print(json.dumps({"cache_path": path.as_posix(), "previous_status": previous_status, "status": status, "cache": data}, indent=2))
    else:
        print(markdown_report(data, status, path), end="")
    return 0


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description="Create and check TailTrail Code Graph Mapper cache.")
    subparsers = parser.add_subparsers(dest="command", required=True)
    for name in ("map", "status", "refresh"):
        sub = subparsers.add_parser(name, help=f"{name} Code Graph Mapper cache.")
        sub.add_argument("--root", type=Path, default=Path.cwd(), help="Project root.")
        sub.add_argument("--changed", action="append", default=[], help="Changed or target file. Repeat for multiple files.")
        sub.add_argument("--scanner-evidence", action="append", default=[], help="Local scanner report/log file to hash and link.")
        sub.add_argument("--mode", default="sonar-vulnerability-review", help="Graph mode or task class.")
        sub.add_argument("--cache", type=Path, default=None, help="Override cache path. Defaults to tailtrail-meta/code-graph-cache.json.")
        sub.add_argument("--format", choices=["markdown", "json"], default="markdown", help="Output format.")
        sub.add_argument("--limit", type=int, default=20, help="Maximum extraction/read-order breadth.")
    return parser


def main() -> int:
    parser = build_parser()
    args = parser.parse_args()
    if args.command == "map":
        return command_map(args)
    if args.command == "status":
        return command_status(args)
    if args.command == "refresh":
        return command_refresh(args)
    parser.error("unknown command")
    return 2


if __name__ == "__main__":
    raise SystemExit(main())
