#!/usr/bin/env python3
"""Dependency-free static relationship extraction shared by graph consumers.

The extractor parses text only.  It never imports project modules, executes
project code, expands a shell command, or persists source bodies.
"""

from __future__ import annotations

import ast
import re
from pathlib import Path
from typing import Any


LANGUAGE_BY_SUFFIX = {
    ".py": "python",
    ".js": "javascript",
    ".jsx": "javascript",
    ".mjs": "javascript",
    ".cjs": "javascript",
    ".ts": "typescript",
    ".tsx": "typescript",
    ".java": "java",
    ".cs": "csharp",
    ".go": "go",
    ".tf": "terraform",
}

CONFIGURATION_SUFFIXES = {".cfg", ".conf", ".ini", ".json", ".properties", ".toml", ".yaml", ".yml"}

# Phase 9 capability registry: the single declared contract for what each
# language's extractor provides. Level 2 = full local structure
# (definitions + imports + relationships); level 1 = partial (regex
# subset). Consumers (e.g. the mapper's language_profiles) derive levels
# from here instead of hardcoding per-language carve-outs. Richer
# techniques (dynamic analysis, type resolution) stay opt-in passes
# outside this table — see docs/arch/code-graphing.md §3.9.
#
# Uniform behavior-row contract (language-neutral): every language emits
# only these `behavior` row kinds, and downstream consumers
# (behavior chains, ownership evidence, module resolution) must branch on
# row kinds, never on file suffixes or languages. `value` is always a
# static identifier (never an expression); `detail` carries the linked
# name (callee, module, setter) or a short sanitized token list.
# `scope` names the enclosing function or "module".
BEHAVIOR_ROW_KINDS = {
    # Local name bound to an imported module symbol.
    # value=local name, detail=module reference.
    # Consumers: behavior chains (call origin), module resolution.
    "import-binding": ["navigator_scope._bounded_behavior_chain"],
    # A call to a static name. value=callee name.
    # Consumers: behavior chains (call step), caller edges.
    "call": ["navigator_scope._bounded_behavior_chain"],
    # An assignment capturing a call result. value=assigned name,
    # detail=callee name. Consumers: behavior chains (returned-value flow).
    "call-result": ["navigator_scope._bounded_behavior_chain"],
    # A returned identifier. value=name.
    # Consumers: behavior chains (returned-value flow).
    "return": ["navigator_scope._bounded_behavior_chain"],
    # An error raised/thrown with a static type. value=error type.
    # Consumers: backend validation evidence (rejection behavior).
    "raise": ["navigator_scope behavior evidence"],
    # An assertion on a name. value=asserted name.
    # Consumers: backend validation evidence (guard behavior).
    "assert": ["navigator_scope behavior evidence"],
    # Framework state binding. value=state name, detail=setter name.
    # Consumers: behavior chains (state flow), UI evidence.
    "state-binding": ["navigator_scope._bounded_behavior_chain"],
    # A write through a state setter. value=state name,
    # detail=identifier list or "static-value".
    # Consumers: behavior chains (state flow), UI evidence.
    "state-write": ["navigator_scope._bounded_behavior_chain"],
    # A tracked value used in a render/output position. value=name.
    # Consumers: behavior chains (render flow), UI evidence.
    "render-use": ["navigator_scope._bounded_behavior_chain"],
    # An error caught into a name. value=name.
    # Consumers: behavior chains (error flow).
    "catch-binding": ["navigator_scope._bounded_behavior_chain"],
}
LANGUAGE_SUPPORT: dict[str, dict[str, Any]] = {
    "python": {"level": 2, "parser": "ast",
               "techniques": ["definitions", "imports", "loaders", "registrations"]},
    "terraform": {"level": 2, "parser": "structured-regex",
                  "techniques": ["definitions", "imports", "references"]},
    "javascript": {"level": 1, "parser": "regex",
                   "techniques": ["definitions", "imports", "registrations", "behavior"]},
    "typescript": {"level": 1, "parser": "regex",
                   "techniques": ["definitions", "imports", "registrations", "behavior"]},
    "java": {"level": 1, "parser": "regex",
             "techniques": ["definitions", "imports", "registrations"]},
    "csharp": {"level": 1, "parser": "regex",
               "techniques": ["definitions", "imports", "registrations"]},
    "go": {"level": 1, "parser": "regex",
           "techniques": ["definitions", "imports", "registrations"]},
}


def support_for(language: str) -> dict[str, Any] | None:
    """Return the registry entry for a language, or None when unlisted."""
    return LANGUAGE_SUPPORT.get(str(language or "").lower())


def support_level(language: str) -> int | None:
    """Return the support level for a language, or None when unlisted."""
    entry = support_for(language)
    return int(entry["level"]) if entry else None


def _line(text: str, offset: int) -> int:
    return text.count("\n", 0, offset) + 1


def _row(kind: str, value: str, line: int, *, detail: str = "") -> dict[str, Any]:
    row: dict[str, Any] = {"kind": kind, "value": value, "line": line}
    if detail:
        row["detail"] = detail
    return row


def _matching_javascript_brace(text: str, opening: int) -> int | None:
    """Return the matching brace without evaluating JavaScript/TypeScript."""
    depth = 0
    quote = ""
    escaped = False
    line_comment = False
    block_comment = False
    index = opening
    while index < len(text):
        char = text[index]
        following = text[index + 1] if index + 1 < len(text) else ""
        if line_comment:
            if char == "\n":
                line_comment = False
            index += 1
            continue
        if block_comment:
            if char == "*" and following == "/":
                block_comment = False
                index += 2
            else:
                index += 1
            continue
        if quote:
            if escaped:
                escaped = False
            elif char == "\\":
                escaped = True
            elif char == quote:
                quote = ""
            index += 1
            continue
        if char == "/" and following == "/":
            line_comment = True
            index += 2
            continue
        if char == "/" and following == "*":
            block_comment = True
            index += 2
            continue
        if char in {"'", '"', "`"}:
            quote = char
        elif char == "{":
            depth += 1
        elif char == "}":
            depth -= 1
            if depth == 0:
                return index
        index += 1
    return None


def _javascript_function_scopes(text: str) -> list[tuple[int, int, str]]:
    """Extract bounded named function ranges for behavior-fact grouping."""
    scopes: list[tuple[int, int, str]] = []
    patterns = (
        r"\b(?:export\s+)?(?:default\s+)?(?:async\s+)?function\s+([A-Za-z_$][\w$]*)[^{};]{0,500}\{",
        r"\b(?:export\s+)?(?:const|let)\s+([A-Za-z_$][\w$]*)[^;=]{0,300}=\s*(?:async\s*)?(?:\([^)]{0,500}\)|[A-Za-z_$][\w$]*)\s*=>\s*\{",
    )
    for pattern in patterns:
        for match in re.finditer(pattern, text):
            opening = text.find("{", match.start(), match.end())
            closing = _matching_javascript_brace(text, opening) if opening >= 0 else None
            if closing is not None:
                scopes.append((_line(text, opening), _line(text, closing), match.group(1)))
    return sorted(set(scopes), key=lambda row: (row[0], -row[1], row[2]))


def _behavior_scope(line: int, scopes: list[tuple[int, int, str]]) -> str:
    containing = [row for row in scopes if row[0] <= line <= row[1]]
    if not containing:
        return "module"
    # The outer named function is the UI ownership boundary; nested handlers
    # may write state later rendered by that component.
    return max(containing, key=lambda row: (row[1] - row[0], -row[0]))[2]


def _static_loader_path(node: ast.AST) -> str | None:
    """Resolve a literal Path ``/`` chain without evaluating project code."""
    if isinstance(node, ast.Constant) and isinstance(node.value, str):
        return node.value
    if isinstance(node, ast.Name):
        return "" if node.id in {"ROOT", "SCRIPTS"} else None
    if isinstance(node, ast.BinOp) and isinstance(node.op, ast.Div):
        left = _static_loader_path(node.left)
        right = _static_loader_path(node.right)
        if left is None or right is None:
            return None
        return "/".join(part.strip("/") for part in (left, right) if part.strip("/"))
    return None


def _python(text: str) -> dict[str, list[dict[str, Any]]]:
    definitions: list[dict[str, Any]] = []
    imports: list[dict[str, Any]] = []
    loaders: list[dict[str, Any]] = []
    registrations: list[dict[str, Any]] = []
    try:
        tree = ast.parse(text)
    except SyntaxError:
        return {
            "definitions": [], "imports": [], "loaders": [],
            "registrations": [], "references": [], "behavior": [],
        }
    for node in ast.walk(tree):
        if isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef, ast.ClassDef)):
            definitions.append(_row(type(node).__name__.lower(), node.name, node.lineno))
        elif isinstance(node, ast.Import):
            for alias in node.names:
                imports.append(_row("import", alias.name, node.lineno))
        elif isinstance(node, ast.ImportFrom):
            prefix = "." * node.level
            imports.append(_row("import", prefix + (node.module or ""), node.lineno))
        elif isinstance(node, ast.Call):
            name = ""
            if isinstance(node.func, ast.Name):
                name = node.func.id
            elif isinstance(node.func, ast.Attribute):
                name = node.func.attr
            if name in {"load", "load_module", "spec_from_file_location"} and len(node.args) >= 2:
                loader_path = _static_loader_path(node.args[1])
                if loader_path:
                    loaders.append(_row("loader", loader_path, getattr(node, "lineno", 1), detail=name))
            elif name.lower() in {"add_route", "include", "register", "register_blueprint", "use"}:
                value = ""
                if node.args:
                    first = node.args[0]
                    if isinstance(first, ast.Constant) and isinstance(first.value, str):
                        value = first.value
                    elif isinstance(first, ast.Name):
                        value = first.id
                    elif isinstance(first, ast.Attribute):
                        value = first.attr
                if value:
                    registrations.append(_row("registration", value, getattr(node, "lineno", 1), detail=name))
    return {
        "definitions": sorted(definitions, key=lambda item: (item["line"], item["value"])),
        "imports": sorted(imports, key=lambda item: (item["line"], item["value"])),
        "loaders": sorted(loaders, key=lambda item: (item["line"], item["value"])),
        "registrations": sorted(registrations, key=lambda item: (item["line"], item["value"])),
        "references": [],
        "behavior": [],
    }


def _regex_facts(text: str, language: str) -> dict[str, list[dict[str, Any]]]:
    definitions: list[dict[str, Any]] = []
    imports: list[dict[str, Any]] = []
    loaders: list[dict[str, Any]] = []
    registrations: list[dict[str, Any]] = []
    behavior: list[dict[str, Any]] = []
    if language in {"javascript", "typescript"}:
        for pattern in (
            r"^\s*import(?:[\s\S]*?\sfrom\s*)?['\"]([^'\"]+)['\"]",
            r"\brequire\(\s*['\"]([^'\"]+)['\"]\s*\)",
            r"\bimport\(\s*['\"]([^'\"]+)['\"]\s*\)",
        ):
            for match in re.finditer(pattern, text, re.MULTILINE):
                imports.append(_row("import", match.group(1), _line(text, match.start())))
        seen_definitions: set[tuple[str, int]] = set()

        def _define(value: str, offset: int) -> None:
            key = (value, _line(text, offset))
            if key not in seen_definitions:
                seen_definitions.add(key)
                definitions.append(_row("definition", value, key[1]))

        for match in re.finditer(
            r"(?:^|[^\w$])(?:export\s+(?:default\s+)?)?(?:async\s+)?"
            r"(?:class|function|interface|type|enum)\s+([A-Za-z_$][\w$]*)",
            text,
        ):
            _define(match.group(1), match.start(1))
        for match in re.finditer(
            r"(?:^|[^\w$])(?:export\s+)?(?:const|let|var)\s+([A-Za-z_$][\w$]*)"
            r"\s*=\s*(?:async\s*)?(?:\([^)]*\)|[A-Za-z_$][\w$]*)\s*=>",
            text,
        ):
            _define(match.group(1), match.start(1))
        for match in re.finditer(r"\b(?:register|use|route)\(\s*['\"]?([A-Za-z0-9_./:-]+)", text):
            registrations.append(_row("registration", match.group(1), _line(text, match.start())))
        behavior.extend(_javascript_typescript_behavior(text))
    elif language == "java":
        for match in re.finditer(r"^\s*package\s+([\w.]+)\s*;", text, re.MULTILINE):
            registrations.append(_row("package", match.group(1), _line(text, match.start())))
        for match in re.finditer(r"^\s*import\s+(?:static\s+)?([\w.*]+)\s*;", text, re.MULTILINE):
            imports.append(_row("import", match.group(1), _line(text, match.start())))
        for match in re.finditer(r"\b(?:class|interface|record|enum)\s+([A-Za-z_]\w*)", text):
            definitions.append(_row("definition", match.group(1), _line(text, match.start())))
    elif language == "csharp":
        for match in re.finditer(r"^\s*namespace\s+([\w.]+)\s*[;{]", text, re.MULTILINE):
            registrations.append(_row("namespace", match.group(1), _line(text, match.start())))
        for match in re.finditer(r"^\s*using\s+(?:static\s+)?([\w.]+)\s*;", text, re.MULTILINE):
            imports.append(_row("import", match.group(1), _line(text, match.start())))
        for match in re.finditer(r"\b(?:class|interface|record|struct|enum)\s+([A-Za-z_]\w*)", text):
            definitions.append(_row("definition", match.group(1), _line(text, match.start())))
    elif language == "go":
        for match in re.finditer(r"^\s*package\s+([A-Za-z_]\w*)", text, re.MULTILINE):
            registrations.append(_row("package", match.group(1), _line(text, match.start())))
        for match in re.finditer(r"^\s*import\s+(?:[A-Za-z_.]\w*\s+)?\"([^\"]+)\"", text, re.MULTILINE):
            imports.append(_row("import", match.group(1), _line(text, match.start())))
        for block in re.finditer(r"\bimport\s*\((.*?)\)", text, re.DOTALL):
            for match in re.finditer(r"(?:[A-Za-z_.]\w*\s+)?\"([^\"]+)\"", block.group(1)):
                imports.append(_row("import", match.group(1), _line(text, block.start() + match.start())))
        for match in re.finditer(r"^\s*(?:func|type)\s+(?:\([^)]*\)\s*)?([A-Za-z_]\w*)", text, re.MULTILINE):
            definitions.append(_row("definition", match.group(1), _line(text, match.start())))
    return {
        "definitions": sorted(definitions, key=lambda item: (item["line"], item["value"])),
        "imports": sorted(imports, key=lambda item: (item["line"], item["value"])),
        "loaders": sorted(loaders, key=lambda item: (item["line"], item["value"])),
        "registrations": sorted(registrations, key=lambda item: (item["line"], item["value"])),
        "references": [],
        "behavior": sorted(behavior, key=lambda item: (item["line"], item["kind"], item["value"])),
    }


def _terraform(text: str) -> dict[str, list[dict[str, Any]]]:
    """Extract bounded HCL/Terraform definitions and references.

    Recognizes `resource`/`data` blocks (defined as `TYPE.NAME`), and
    `module`/`variable`/`output` blocks (defined as `NAME`). Module `source`
    attributes are treated as imports; `var.`/`local.`/`module.`/`data.`
    lookups are treated as references. This is regex-based, bounded static
    text parsing; it does not evaluate HCL expressions.
    """
    definitions: list[dict[str, Any]] = []
    imports: list[dict[str, Any]] = []
    references: list[dict[str, Any]] = []
    for match in re.finditer(
        r'^\s*(?:resource|data)\s+"([A-Za-z0-9_]+)"\s+"([A-Za-z0-9_]+)"\s*\{',
        text,
        re.MULTILINE,
    ):
        value = f"{match.group(1)}.{match.group(2)}"
        definitions.append(_row("definition", value, _line(text, match.start())))
    for match in re.finditer(
        r'^\s*(?:module|variable|output)\s+"([A-Za-z0-9_]+)"\s*\{',
        text,
        re.MULTILINE,
    ):
        definitions.append(_row("definition", match.group(1), _line(text, match.start())))
    for match in re.finditer(r'\bsource\s*=\s*"([^"]+)"', text):
        imports.append(_row("import", match.group(1), _line(text, match.start())))
    for match in re.finditer(r'\b(?:var|local|module|data)\.([A-Za-z0-9_.]+)', text):
        references.append(_row("reference", match.group(1), _line(text, match.start())))
    return {
        "definitions": sorted(definitions, key=lambda item: (item["line"], item["value"])),
        "imports": sorted(imports, key=lambda item: (item["line"], item["value"])),
        "loaders": [],
        "registrations": [],
        "references": sorted(references, key=lambda item: (item["line"], item["value"])),
        "behavior": [],
    }


def _javascript_typescript_behavior(text: str) -> list[dict[str, Any]]:
    """Extract bounded, sanitized intra-file UI-flow facts.

    This intentionally recognizes only static identifiers and short structural
    relationships. It does not retain expressions or attempt to execute or
    fully parse TypeScript/JSX.
    """
    rows: list[dict[str, Any]] = []
    import_bindings: list[tuple[str, str, int]] = []
    for match in re.finditer(
        r"\bimport\s*\{([^}]{1,1000})\}\s*from\s*['\"]([^'\"]+)['\"]",
        text,
        re.MULTILINE,
    ):
        for raw in match.group(1).split(","):
            value = re.sub(r"^\s*type\s+", "", raw.strip())
            if not value:
                continue
            pieces = re.split(r"\s+as\s+", value)
            local = pieces[-1].strip()
            if re.fullmatch(r"[A-Za-z_$][\w$]*", local):
                import_bindings.append((local, match.group(2), _line(text, match.start())))
    for match in re.finditer(
        r"\bimport\s+([A-Za-z_$][\w$]*)\s+from\s*['\"]([^'\"]+)['\"]",
        text,
        re.MULTILINE,
    ):
        import_bindings.append((match.group(1), match.group(2), _line(text, match.start())))
    for local, reference, line in import_bindings:
        rows.append(_row("import-binding", local, line, detail=reference))

    for match in re.finditer(r"(?<![.\w$])([A-Za-z_$][\w$]*)\s*\(", text):
        name = match.group(1)
        if name in {"async", "catch", "for", "if", "switch", "while"}:
            continue
        prefix = text[max(0, match.start() - 24):match.start()]
        if re.search(r"\b(?:function|class|interface|type|enum)\s*$", prefix):
            continue
        rows.append(_row("call", name, _line(text, match.start())))

    for match in re.finditer(
        r"\b(?:const|let|var)\s+([A-Za-z_$][\w$]*)\s*=\s*(?:await\s+)?([A-Za-z_$][\w$]*)\s*\(",
        text,
    ):
        if match.group(2) != "async":
            rows.append(_row("call-result", match.group(1), _line(text, match.start()), detail=match.group(2)))

    for match in re.finditer(r"\bcatch\s*\(\s*([A-Za-z_$][\w$]*)\s*\)", text):
        rows.append(_row("catch-binding", match.group(1), _line(text, match.start())))

    state_by_setter: dict[str, str] = {}
    for match in re.finditer(
        r"\b(?:const|let)\s*\[\s*([A-Za-z_$][\w$]*)\s*,\s*([A-Za-z_$][\w$]*)\s*\]\s*=\s*(?:[A-Za-z_$][\w$]*\.)?useState(?:<[^;=]{0,200}>)?\s*\(",
        text,
    ):
        state, setter = match.group(1), match.group(2)
        state_by_setter[setter] = state
        rows.append(_row("state-binding", state, _line(text, match.start()), detail=setter))
    for setter, state in state_by_setter.items():
        pattern = rf"\b{re.escape(setter)}\s*\(([^;\n]{{0,500}})\)"
        for match in re.finditer(pattern, text):
            expression = re.sub(
                r"'(?:\\.|[^'\\])*'|\"(?:\\.|[^\"\\])*\"|`(?:\\.|[^`\\])*`",
                "",
                match.group(1),
            )
            identifiers = sorted(dict.fromkeys(
                value
                for value in re.findall(r"[A-Za-z_$][\w$]*", expression)
                if value not in {"Error", "false", "instanceof", "null", "true", "undefined"}
            ))[:12]
            rows.append(_row(
                "state-write",
                state,
                _line(text, match.start()),
                detail=",".join(identifiers) if identifiers else "static-value",
            ))

    rendered_names: set[tuple[str, int]] = set()
    tracked_values = {
        row["value"]
        for row in rows
        if row["kind"] in {"state-binding", "call-result", "catch-binding"}
    }
    # JSX commonly nests braces (for example ``{error && <aside>{error}</aside>}``),
    # so a balanced-JSX parser would be disproportionate here. Bound the scan
    # to a short return region that contains markup and retain only the tracked
    # identifier and line number.
    for return_match in re.finditer(r"\breturn\b", text):
        region = text[return_match.start():return_match.start() + 4_096]
        if not re.search(r"<[/]?[A-Za-z][^>]*>", region):
            continue
        for value in tracked_values:
            value_match = re.search(rf"\b{re.escape(value)}\b", region)
            if value_match:
                key = (value, _line(text, return_match.start() + value_match.start()))
                if key not in rendered_names:
                    rendered_names.add(key)
                    rows.append(_row("render-use", value, key[1]))
    scopes = _javascript_function_scopes(text)
    for row in rows:
        if row["kind"] != "import-binding":
            row["scope"] = _behavior_scope(int(row["line"]), scopes)
    return rows


def _configuration(text: str) -> dict[str, list[dict[str, Any]]]:
    """Extract conservative path/module value tokens from configuration text."""
    references: list[dict[str, Any]] = []
    seen: set[tuple[str, int]] = set()
    for match in re.finditer(r"(?<![A-Za-z0-9_])([A-Za-z0-9_@.-]+(?:[/\\.][A-Za-z0-9_@.-]+)+)(?![A-Za-z0-9_])", text):
        value = match.group(1).replace("\\", "/").strip("./")
        row_key = (value, _line(text, match.start()))
        if len(value) < 3 or row_key in seen:
            continue
        seen.add(row_key)
        references.append(_row("configuration-reference", value, row_key[1]))
    return {
        "definitions": [],
        "imports": [],
        "loaders": [],
        "registrations": [],
        "references": sorted(references, key=lambda item: (item["line"], item["value"])),
        "behavior": [],
    }


def extract(path: Path, root: Path, text: str) -> dict[str, Any]:
    """Return sanitized definitions and relationships for one local file."""
    language = LANGUAGE_BY_SUFFIX.get(path.suffix.lower(), "unknown")
    if language == "python":
        facts = _python(text)
    elif language == "terraform":
        facts = _terraform(text)
    elif language != "unknown":
        facts = _regex_facts(text, language)
    elif path.suffix.lower() in CONFIGURATION_SUFFIXES:
        facts = _configuration(text)
    else:
        facts = _regex_facts(text, language)
    return {
        "path": path.resolve().relative_to(root.resolve()).as_posix(),
        "language": language,
        **facts,
    }
