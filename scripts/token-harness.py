#!/usr/bin/env python3

from __future__ import annotations

import argparse
import json
import re
import subprocess
import sys
from pathlib import Path
from typing import Any


SOURCE_EXTENSIONS = {
    ".cs",
    ".fs",
    ".go",
    ".java",
    ".js",
    ".jsx",
    ".kt",
    ".kts",
    ".php",
    ".py",
    ".rb",
    ".rs",
    ".sql",
    ".tf",
    ".tfvars",
    ".ts",
    ".tsx",
    ".vb",
}

CONFIG_EXTENSIONS = {".ini", ".properties", ".toml", ".yaml", ".yml"}
DOC_EXTENSIONS = {".adoc", ".md", ".rst", ".txt"}
JSON_EXTENSIONS = {".json", ".jsonl", ".sarif"}

DEPENDENCY_MANIFESTS = {
    "build.gradle",
    "build.gradle.kts",
    "cargo.lock",
    "cargo.toml",
    "composer.json",
    "go.mod",
    "go.sum",
    "gemfile",
    "gemfile.lock",
    "package-lock.json",
    "package.json",
    "pnpm-lock.yaml",
    "pom.xml",
    "poetry.lock",
    "requirements-dev.txt",
    "requirements.txt",
    "setup.py",
    "yarn.lock",
}

SECURITY_POLICY_NAMES = {
    "code_of_conduct.md",
    "dependency-gate.md",
    "guardrails.md",
    "security.md",
    "tailtrail-policy.md",
}

SCANNER_NAMES = {
    "dependency-check-report.xml",
    "grype.json",
    "sarif",
    "sonar-report.json",
    "trivy.json",
}

SCANNER_KEYS = {
    "artifacts",
    "cve",
    "ghsa",
    "level",
    "locations",
    "matches",
    "package",
    "physicalLocation",
    "results",
    "ruleId",
    "runs",
    "severity",
    "vulnerability",
}

LOG_PATTERNS = (
    re.compile(r"\b(error|exception|failed|failure|traceback|stack trace)\b", re.IGNORECASE),
    re.compile(r"^\s*at\s+[\w.$<>]+\(", re.MULTILINE),
    re.compile(r"^\d{4}-\d{2}-\d{2}[T\s]\d{2}:\d{2}:\d{2}", re.MULTILINE),
)


def read_text(path: Path | None, inline_text: str | None, max_bytes: int = 512_000) -> tuple[str, int, bool]:
    if inline_text is not None:
        encoded = inline_text.encode("utf-8", errors="replace")
        return inline_text, len(encoded), False
    if path is None:
        return "", 0, False
    try:
        data = path.read_bytes()
    except OSError as error:
        raise SystemExit(f"Unable to read {path}: {error}") from error
    truncated = len(data) > max_bytes
    sample = data[:max_bytes].decode("utf-8", errors="replace")
    return sample, len(data), truncated


def normalize_label(label: str | None) -> str:
    if not label:
        return ""
    return label.strip().lower().replace("_", "-").replace(" ", "-")


def looks_like_diff(text: str) -> bool:
    return "diff --git " in text or bool(re.search(r"(?m)^@@ .+ @@|^\+\+\+ .+|^--- .+", text))


def load_json(text: str) -> Any | None:
    stripped = text.strip()
    if not stripped or stripped[0] not in "[{":
        return None
    try:
        return json.loads(stripped)
    except json.JSONDecodeError:
        return None


def json_has_scanner_shape(value: Any) -> bool:
    if isinstance(value, dict):
        keys = set(value)
        if keys & SCANNER_KEYS:
            return True
        return any(json_has_scanner_shape(child) for child in value.values())
    if isinstance(value, list):
        return any(json_has_scanner_shape(item) for item in value[:20])
    return False


def looks_like_log(text: str) -> bool:
    if not text.strip():
        return False
    return any(pattern.search(text) for pattern in LOG_PATTERNS)


def looks_like_source(text: str) -> bool:
    source_patterns = (
        r"\b(def|class|import|from)\s+\w+",
        r"\b(public|private|protected|class|interface|using|namespace)\b",
        r"\b(function|const|let|var|import|export)\b",
        r"\bSELECT\b.+\bFROM\b",
        r"\bresource\s+\"[\w_]+\"\s+\"[\w_-]+\"",
    )
    return any(re.search(pattern, text, re.IGNORECASE | re.DOTALL) for pattern in source_patterns)


def detect_content_type(path: Path | None, text: str, label: str | None) -> tuple[str, str]:
    normalized = normalize_label(label)
    if normalized in {
        "source",
        "diff",
        "config",
        "security-policy",
        "dependency-manifest",
        "json",
        "tool-output",
        "log",
        "scanner-output",
        "documentation",
        "learning-history",
        "unknown",
    }:
        return normalized, "high"

    name = path.name.lower() if path else ""
    suffix = path.suffix.lower() if path else ""
    path_text = path.as_posix().lower() if path else ""

    if suffix in SOURCE_EXTENSIONS:
        return "source", "high"
    if looks_like_diff(text) or suffix in {".diff", ".patch"}:
        return "diff", "high"
    if name in SECURITY_POLICY_NAMES or "security" in path_text or "guardrail" in path_text:
        return "security-policy", "high"
    if name in DEPENDENCY_MANIFESTS or name.endswith(".csproj") or name.endswith(".fsproj") or name.endswith(".vbproj"):
        return "dependency-manifest", "high"
    if name in SCANNER_NAMES or suffix == ".sarif":
        return "scanner-output", "high"

    parsed = load_json(text)
    if parsed is not None:
        if json_has_scanner_shape(parsed):
            return "scanner-output", "high"
        return "json", "high"

    if suffix in CONFIG_EXTENSIONS:
        return "config", "medium"
    if suffix in JSON_EXTENSIONS:
        return "json", "medium"
    if suffix in DOC_EXTENSIONS or "/docs/" in path_text or name.startswith("readme"):
        return "documentation", "medium"
    if "learning" in path_text or "learnings" in path_text:
        return "learning-history", "medium"
    if looks_like_log(text):
        return "log", "medium"
    if looks_like_source(text):
        return "source", "low"
    return "unknown", "low"


def classify_exactness(content_type: str, size_bytes: int, text: str) -> tuple[str, str]:
    if size_bytes <= 280 and content_type == "unknown":
        return "skip-reduction", "Content is tiny or ambiguous; routing overhead is not justified."
    if content_type in {"source", "diff", "config", "security-policy", "dependency-manifest"}:
        return "must-be-exact", "This content affects implementation correctness, policy, configuration, dependencies, or review evidence."
    if content_type in {"json", "tool-output", "scanner-output"}:
        return "structure-exact", "Structured fields, IDs, paths, severities, and relationships must be preserved."
    if content_type == "documentation":
        return "summary-safe", "Documentation can be sliced or summarized if named facts and sections remain retrievable."
    if content_type == "learning-history":
        return "summary-safe", "Learning history should use curated summaries rather than raw history."
    if content_type == "log":
        return "reduce-safe", "Repetitive log output can later be reduced around failures and command boundaries."
    return "skip-reduction", "Content type is unknown; leave it exact until a safer route is available."


def recommend_strategy(content_type: str, exactness_class: str, task: str | None) -> dict[str, Any]:
    lowered_task = (task or "").lower()
    if exactness_class == "must-be-exact":
        name = "graph-first" if content_type == "source" and any(term in lowered_task for term in ("broad", "review", "sonar", "security", "refactor")) else "exact-pass-through"
        reason = (
            "Use Code Graph Mapper first for broad source understanding, then inspect exact source before edits."
            if name == "graph-first"
            else f"{content_type} content must remain exact."
        )
        return {
            "name": name,
            "reason": reason,
            "allowed_reductions": ["graph metadata first"] if name == "graph-first" else [],
            "blocked_reductions": ["summarize", "compress", "drop-lines", "paraphrase"],
        }
    if exactness_class == "structure-exact":
        name = "scanner-focused-summary" if content_type == "scanner-output" else "structure-summary"
        return {
            "name": name,
            "reason": "Later reducers may summarize structure only if keys, IDs, paths, counts, severities, and hierarchy remain intact.",
            "allowed_reductions": ["collapse repeated fields", "summarize non-critical values"],
            "blocked_reductions": ["drop IDs", "drop paths", "drop severities", "drop versions", "rewrite structure"],
        }
    if content_type == "log":
        return {
            "name": "failure-focused-summary",
            "reason": "Later reducers may focus on first failure, repeated errors, stack frames, and command boundaries.",
            "allowed_reductions": ["deduplicate repeated lines", "keep first and last relevant failures"],
            "blocked_reductions": ["drop exit codes", "drop command names", "drop first failure"],
        }
    if content_type == "documentation":
        return {
            "name": "doc-section-slice",
            "reason": "Documentation can be sliced by heading or relevant section while preserving named requirements.",
            "allowed_reductions": ["section slicing", "short summary with retrieval pointer"],
            "blocked_reductions": ["drop requirements", "drop policy statements", "drop exact commands"],
        }
    if content_type == "learning-history":
        return {
            "name": "learning-summary",
            "reason": "Use high-confidence curated learning summaries instead of raw learning history.",
            "allowed_reductions": ["load high-confidence summaries only"],
            "blocked_reductions": ["load raw learning history by default", "use low-confidence learnings as facts"],
        }
    return {
        "name": "skip-reduction",
        "reason": "No safe or useful reduction route was selected.",
        "allowed_reductions": [],
        "blocked_reductions": ["summarize", "compress", "drop-lines"],
    }


def preserve_list(content_type: str, exactness_class: str) -> list[str]:
    common = ["source path or input label", "retrieval pointer"]
    if content_type == "source" and exactness_class == "structure-exact":
        return [*common, "imports", "class names", "function and method names", "line numbers", "body omission marker"]
    if exactness_class == "must-be-exact":
        return [*common, "line numbers", "exact text", "commands", "IDs", "hashes", "versions"]
    if content_type == "scanner-output":
        return [*common, "rule IDs", "severity", "file paths", "line numbers", "package names", "installed and fixed versions"]
    if exactness_class == "structure-exact":
        return [*common, "JSON keys", "array/object hierarchy", "IDs", "counts", "paths"]
    if content_type == "log":
        return [*common, "command boundaries", "exit codes", "first failure", "stack traces", "repeated error groups"]
    if content_type == "documentation":
        return [*common, "headings", "requirements", "policy statements", "exact commands"]
    if content_type == "learning-history":
        return [*common, "learning IDs", "confidence score", "validation outcome", "staleness or suppression status"]
    return common


def retrieval_command(path: Path | None) -> str:
    if path is None:
        return "provided inline text"
    return f"cat {json.dumps(path.as_posix())}"


def build_route(path: Path | None, text: str | None, label: str | None, task: str | None) -> dict[str, Any]:
    sample, size_bytes, truncated = read_text(path, text)
    content_type, confidence = detect_content_type(path, sample, label)
    exactness, exactness_reason = classify_exactness(content_type, size_bytes, sample)
    strategy = recommend_strategy(content_type, exactness, task)
    return {
        "schema_version": "1",
        "type": "tailtrail-token-harness-route",
        "input": {
            "path": path.as_posix() if path else "",
            "label": label or "",
            "size_bytes": size_bytes,
            "sample_truncated": truncated,
        },
        "classification": {
            "content_type": content_type,
            "exactness_class": exactness,
            "confidence": confidence,
            "reason": exactness_reason,
        },
        "strategy": strategy,
        "preserve": preserve_list(content_type, exactness),
        "retrieval": {
            "required": exactness != "skip-reduction",
            "command": retrieval_command(path),
        },
        "notes": [
            "TH-1 does not transform content.",
            "No token savings claim is produced.",
            "Use reducer, receipt, ledger, and proof commands only when their approval and evidence rules are satisfied.",
        ],
    }


def render_markdown(route: dict[str, Any]) -> str:
    classification = route["classification"]
    strategy = route["strategy"]
    lines = [
        "# TailTrail Token Harness Route",
        "",
        f"- Content type: `{classification['content_type']}`",
        f"- Exactness: `{classification['exactness_class']}`",
        f"- Strategy: `{strategy['name']}`",
        f"- Confidence: `{classification['confidence']}`",
        f"- Reason: {strategy['reason']}",
        "",
        "## Preserve",
        "",
    ]
    lines.extend(f"- {item}" for item in route["preserve"])
    lines.extend(["", "## Blocked Reductions", ""])
    blocked = strategy.get("blocked_reductions", [])
    lines.extend(f"- {item}" for item in blocked) if blocked else lines.append("- none")
    lines.extend(["", "## Retrieval", "", f"- `{route['retrieval']['command']}`"])
    lines.extend(["", "## Notes", ""])
    lines.extend(f"- {item}" for item in route["notes"])
    return "\n".join(lines) + "\n"


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description="Route context through the TailTrail Token Harness exactness gate.")
    subparsers = parser.add_subparsers(dest="command", required=True)
    route = subparsers.add_parser("route", help="Classify content and recommend a safe token strategy.")
    source = route.add_mutually_exclusive_group(required=True)
    source.add_argument("--path", type=Path, help="File or artifact path to classify.")
    source.add_argument("--text", help="Inline text to classify.")
    route.add_argument("--label", help="Optional content label override, such as scanner-output or source.")
    route.add_argument("--task", help="Optional task goal to tune strategy selection.")
    route.add_argument("--format", choices=("markdown", "json"), default="markdown")
    ledger = subparsers.add_parser("ledger", help="Append, summarize, or validate the Token Harness ledger.")
    ledger.add_argument("ledger_args", nargs=argparse.REMAINDER)
    reduce = subparsers.add_parser("reduce", help="Run exactness-preserving structured reducers.")
    reduce.add_argument("reduce_args", nargs=argparse.REMAINDER)
    proof = subparsers.add_parser("proof", help="Produce proof reports or holdout decisions.")
    proof.add_argument("proof_args", nargs=argparse.REMAINDER)
    bridge = subparsers.add_parser("bridge", help="Run optional policy-gated runtime compression bridge commands.")
    bridge.add_argument("bridge_args", nargs=argparse.REMAINDER)
    return parser


def main() -> int:
    if len(sys.argv) > 1 and sys.argv[1] == "bridge":
        script = Path(__file__).resolve().with_name("token-harness-bridge.py")
        return subprocess.run([sys.executable, script.as_posix(), *sys.argv[2:]], check=False).returncode
    if len(sys.argv) > 1 and sys.argv[1] == "ledger":
        script = Path(__file__).resolve().with_name("token-harness-ledger.py")
        return subprocess.run([sys.executable, script.as_posix(), *sys.argv[2:]], check=False).returncode
    if len(sys.argv) > 1 and sys.argv[1] == "reduce":
        script = Path(__file__).resolve().with_name("token-harness-reduce.py")
        return subprocess.run([sys.executable, script.as_posix(), *sys.argv[2:]], check=False).returncode
    if len(sys.argv) > 1 and sys.argv[1] == "proof":
        script = Path(__file__).resolve().with_name("token-harness-proof.py")
        return subprocess.run([sys.executable, script.as_posix(), *sys.argv[2:]], check=False).returncode
    parser = build_parser()
    args = parser.parse_args()
    route = build_route(args.path, args.text, args.label, args.task)
    if args.format == "json":
        print(json.dumps(route, indent=2, sort_keys=True))
    else:
        print(render_markdown(route), end="")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
