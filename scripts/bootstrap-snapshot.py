#!/usr/bin/env python3

from __future__ import annotations

import argparse
import json
import shutil
import subprocess
from datetime import datetime, timezone
from hashlib import sha256
from pathlib import Path
from typing import Any


TAILTRAIL_DIR = Path(".tailtrail")
SNAPSHOT_PATH = TAILTRAIL_DIR / "bootstrap-snapshot.json"

IGNORED_DIRS = {
    ".git",
    ".hg",
    ".svn",
    ".tailtrail",
    "__pycache__",
    ".pytest_cache",
    ".mypy_cache",
    ".ruff_cache",
    ".tox",
    ".venv",
    "venv",
    "env",
    "node_modules",
    "dist",
    "build",
    "target",
    "bin",
    "obj",
    ".idea",
    ".vscode",
}

LANGUAGE_EXTENSIONS = {
    ".py": "python",
    ".java": "java",
    ".cs": "dotnet",
    ".fs": "dotnet",
    ".vb": "dotnet",
    ".js": "javascript",
    ".jsx": "javascript",
    ".ts": "typescript",
    ".tsx": "typescript",
    ".go": "go",
    ".sql": "sql",
    ".tf": "terraform",
    ".tfvars": "terraform",
    ".kt": "kotlin",
    ".kts": "kotlin",
    ".rb": "ruby",
    ".php": "php",
    ".rs": "rust",
    ".yml": "yaml",
    ".yaml": "yaml",
}

MANIFESTS = {
    "package.json": ("javascript", "npm"),
    "pnpm-lock.yaml": ("javascript", "pnpm"),
    "yarn.lock": ("javascript", "yarn"),
    "package-lock.json": ("javascript", "npm"),
    "pyproject.toml": ("python", "python"),
    "requirements.txt": ("python", "pip"),
    "requirements-dev.txt": ("python", "pip"),
    "setup.py": ("python", "setuptools"),
    "tox.ini": ("python", "tox"),
    "pytest.ini": ("python", "pytest"),
    "pom.xml": ("java", "maven"),
    "build.gradle": ("java", "gradle"),
    "build.gradle.kts": ("java", "gradle"),
    "gradlew": ("java", "gradle"),
    "go.mod": ("go", "go"),
    "Cargo.toml": ("rust", "cargo"),
    "Gemfile": ("ruby", "bundler"),
    "composer.json": ("php", "composer"),
    "terraform.tf": ("terraform", "terraform"),
    "main.tf": ("terraform", "terraform"),
}

TEST_SIGNAL_FILES = {
    "pytest.ini": "pytest",
    "tox.ini": "tox",
    "jest.config.js": "jest",
    "jest.config.ts": "jest",
    "vitest.config.js": "vitest",
    "vitest.config.ts": "vitest",
    "pom.xml": "java-test",
    "build.gradle": "gradle-test",
    "build.gradle.kts": "gradle-test",
    "go.mod": "go-test",
}

CI_PATTERNS = {
    ".github/workflows": "github-actions",
    ".gitlab-ci.yml": "gitlab-ci",
    "azure-pipelines.yml": "azure-pipelines",
    "Jenkinsfile": "jenkins",
    ".circleci/config.yml": "circleci",
    "bitbucket-pipelines.yml": "bitbucket-pipelines",
}

SCANNER_FILES = {
    "sonar-project.properties": "sonar",
    ".semgrep.yml": "semgrep",
    ".semgrep.yaml": "semgrep",
    "codeql.yml": "codeql",
    ".github/codeql/codeql-config.yml": "codeql",
    "trivy.yaml": "trivy",
    "trivy.yml": "trivy",
    ".trivyignore": "trivy",
    "grype.yaml": "grype",
    "grype.yml": "grype",
    "dependency-check-report.xml": "dependency-check",
    "pom.xml": "dependency-manifest",
    "package-lock.json": "dependency-manifest",
    "pnpm-lock.yaml": "dependency-manifest",
    "yarn.lock": "dependency-manifest",
    "requirements.txt": "dependency-manifest",
    "go.sum": "dependency-manifest",
    "Cargo.lock": "dependency-manifest",
}

TAILTRAIL_ARTIFACTS = {
    "policy": "tailtrail-policy.md",
    "aidlc_docs": "aidlc-docs/aidlc-state.md",
    "learnings": ".tailtrail/learnings.md",
    "learning_index": ".tailtrail/learning-index.md",
    "code_graph_shared": "tailtrail-meta/code-graph-cache.json",
    "code_graph_local": ".tailtrail/code-graph-cache.json",
    "harness_summary_shared": "tailtrail-meta/harness-summary.jsonl",
    "harness_review_local": ".tailtrail/harness-review.md",
}

COMMANDS = (
    "git",
    "python3",
    "node",
    "npm",
    "yarn",
    "pnpm",
    "java",
    "mvn",
    "gradle",
    "dotnet",
    "go",
    "terraform",
    "pytest",
    "ruff",
    "sonar-scanner",
    "trivy",
    "grype",
)


def now() -> str:
    return datetime.now(timezone.utc).replace(microsecond=0).isoformat()


def is_ignored_dir(path: Path) -> bool:
    return path.name in IGNORED_DIRS


def relative(path: Path, root: Path) -> str:
    return path.relative_to(root).as_posix()


def git_root_kind(root: Path) -> str:
    result = subprocess.run(["git", "rev-parse", "--is-inside-work-tree"], cwd=root, text=True, capture_output=True, check=False)
    return "git" if result.returncode == 0 and result.stdout.strip() == "true" else "directory"


def cheap_walk(root: Path, max_files: int = 2500) -> tuple[dict[str, int], dict[str, int], list[str], int]:
    language_counts: dict[str, int] = {}
    extension_counts: dict[str, int] = {}
    top_dirs: set[str] = set()
    scanned = 0
    stack = [root]
    while stack and scanned < max_files:
        current = stack.pop()
        try:
            entries = sorted(current.iterdir(), key=lambda item: item.name)
        except OSError:
            continue
        for entry in entries:
            if entry.is_dir():
                if is_ignored_dir(entry):
                    continue
                if entry.parent == root:
                    top_dirs.add(entry.name)
                stack.append(entry)
                continue
            if not entry.is_file():
                continue
            scanned += 1
            suffix = entry.suffix.lower()
            if suffix:
                extension_counts[suffix] = extension_counts.get(suffix, 0) + 1
            language = LANGUAGE_EXTENSIONS.get(suffix)
            if language:
                language_counts[language] = language_counts.get(language, 0) + 1
            if scanned >= max_files:
                break
    return language_counts, extension_counts, sorted(top_dirs), scanned


def existing_paths(root: Path, mapping: dict[str, str] | dict[str, tuple[str, str]]) -> list[str]:
    paths: list[str] = []
    for item in mapping:
        if (root / item).exists():
            paths.append(item)
    return sorted(paths)


def find_solution_files(root: Path) -> list[str]:
    names: list[str] = []
    for pattern in ("*.sln", "*.csproj", "*.fsproj", "*.vbproj"):
        names.extend(relative(path, root) for path in root.glob(pattern) if path.is_file())
    return sorted(names)[:25]


def detect_languages(root: Path, language_counts: dict[str, int], manifests: list[str], solution_files: list[str]) -> list[str]:
    languages = set(language_counts)
    for manifest in manifests:
        language, _tool = MANIFESTS.get(manifest, ("", ""))
        if language:
            languages.add(language)
    if solution_files:
        languages.add("dotnet")
    return sorted(languages)


def detect_package_managers(manifests: list[str], solution_files: list[str]) -> list[str]:
    managers = {MANIFESTS[item][1] for item in manifests if item in MANIFESTS and MANIFESTS[item][1]}
    if solution_files:
        managers.add("dotnet")
    return sorted(managers)


def detect_test_signals(root: Path, manifests: list[str], top_dirs: list[str]) -> list[str]:
    signals = {TEST_SIGNAL_FILES[item] for item in manifests if item in TEST_SIGNAL_FILES}
    if any(name.lower() in {"test", "tests", "__tests__", "spec", "specs"} for name in top_dirs):
        signals.add("test-directory")
    if any(root.glob("**/pytest.ini")):
        signals.add("pytest")
    return sorted(signals)


def detect_ci_signals(root: Path) -> list[str]:
    signals: set[str] = set()
    for path, label in CI_PATTERNS.items():
        if (root / path).exists():
            signals.add(label)
    return sorted(signals)


def detect_scanner_signals(root: Path, manifests: list[str]) -> list[str]:
    signals = {SCANNER_FILES[item] for item in manifests if item in SCANNER_FILES}
    for path, label in SCANNER_FILES.items():
        if (root / path).exists():
            signals.add(label)
    if any(root.glob("*.sarif")) or any(root.glob("**/*.sarif")):
        signals.add("sarif")
    return sorted(signals)


def artifact_status(root: Path) -> dict[str, str]:
    status: dict[str, str] = {}
    for key, path in TAILTRAIL_ARTIFACTS.items():
        status[key] = "present" if (root / path).exists() else "missing"
    return status


def command_availability() -> dict[str, bool]:
    return {command: shutil.which(command) is not None for command in COMMANDS}


def signal_files(root: Path, manifests: list[str], solution_files: list[str]) -> list[dict[str, Any]]:
    candidates = set(manifests) | set(solution_files) | set(CI_PATTERNS) | set(SCANNER_FILES) | set(TAILTRAIL_ARTIFACTS.values())
    rows: list[dict[str, Any]] = []
    for item in sorted(candidates):
        path = root / item
        if not path.exists() or not path.is_file():
            continue
        try:
            stat = path.stat()
        except OSError:
            continue
        rows.append({"path": item, "size": stat.st_size, "mtime": int(stat.st_mtime)})
    return rows


def fingerprint(rows: list[dict[str, Any]], top_dirs: list[str]) -> str:
    payload = {"signal_files": rows, "top_dirs": top_dirs}
    encoded = json.dumps(payload, sort_keys=True, separators=(",", ":")).encode("utf-8")
    return sha256(encoded).hexdigest()


def first_reads(root: Path, manifests: list[str], ci_signals: list[str], scanner_signals: list[str]) -> list[str]:
    reads: list[str] = []
    seen_lower: set[str] = set()
    for candidate in ("README.md", "readme.md", "docs/README.md", "AGENTS.md", "tailtrail-policy.md"):
        if candidate.lower() not in seen_lower and (root / candidate).is_file():
            reads.append(candidate)
            seen_lower.add(candidate.lower())
    reads.extend(manifests[:8])
    if ci_signals and (root / ".github/workflows").exists():
        reads.append(".github/workflows")
    if scanner_signals and (root / "sonar-project.properties").exists():
        reads.append("sonar-project.properties")
    if (root / "tailtrail-meta" / "code-graph-cache.json").is_file():
        reads.append("tailtrail-meta/code-graph-cache.json")
    return list(dict.fromkeys(reads))[:12]


def build_snapshot(root: Path) -> dict[str, Any]:
    root = root.resolve()
    language_counts, extension_counts, top_dirs, scanned = cheap_walk(root)
    manifests = existing_paths(root, MANIFESTS)
    solution_files = find_solution_files(root)
    languages = detect_languages(root, language_counts, manifests, solution_files)
    package_managers = detect_package_managers(manifests, solution_files)
    test_signals = detect_test_signals(root, manifests, top_dirs)
    ci_signals = detect_ci_signals(root)
    scanner_signals = detect_scanner_signals(root, manifests)
    artifacts = artifact_status(root)
    signals = signal_files(root, manifests, solution_files)
    root_fingerprint = fingerprint(signals, top_dirs)
    return {
        "schema_version": "1",
        "type": "tailtrail-bootstrap-snapshot",
        "created_at": now(),
        "root_kind": git_root_kind(root),
        "root_fingerprint": root_fingerprint,
        "freshness": {"status": "fresh", "reason": "snapshot was just created"},
        "scan_limits": {
            "max_files": 2500,
            "files_scanned": scanned,
            "source_bodies_read": False,
            "project_code_executed": False,
        },
        "languages": languages,
        "language_counts": dict(sorted(language_counts.items())),
        "extension_counts": dict(sorted(extension_counts.items(), key=lambda item: (-item[1], item[0]))[:20]),
        "top_level_dirs": top_dirs[:40],
        "manifests": manifests,
        "solution_files": solution_files,
        "package_managers": package_managers,
        "test_signals": test_signals,
        "ci_signals": ci_signals,
        "scanner_signals": scanner_signals,
        "tailtrail_artifacts": artifacts,
        "available_commands": command_availability(),
        "recommended_first_reads": first_reads(root, manifests, ci_signals, scanner_signals),
        "avoid_first_reads": [
            "full source tree",
            "large generated folders",
            "raw logs",
            "dependency caches",
            "environment variables",
            "private credentials",
        ],
        "signal_files": signals,
        "privacy": "Local snapshot only. Contains filenames, counts, tool signals, and TailTrail artifact presence. It does not include source bodies, raw prompts, logs, secrets, environment values, or user identity.",
    }


def load_snapshot(root: Path) -> dict[str, Any] | None:
    path = root / SNAPSHOT_PATH
    if not path.exists():
        return None
    try:
        value = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError):
        return None
    return value if isinstance(value, dict) else None


def snapshot_status(root: Path) -> dict[str, Any]:
    root = root.resolve()
    path = root / SNAPSHOT_PATH
    existing = load_snapshot(root)
    current = build_snapshot(root)
    if existing is None:
        return {
            "schema_version": "1",
            "type": "tailtrail-bootstrap-status",
            "path": SNAPSHOT_PATH.as_posix(),
            "exists": path.exists(),
            "status": "missing" if not path.exists() else "invalid",
            "reason": "snapshot file is missing" if not path.exists() else "snapshot file is invalid JSON or not an object",
            "recommended_action": "Run `tailtrail bootstrap snapshot --write-result` or `tailtrail bootstrap refresh` before broad Navigator planning.",
            "current_fingerprint": current["root_fingerprint"],
            "snapshot": None,
        }
    previous = str(existing.get("root_fingerprint", ""))
    current_fingerprint = str(current["root_fingerprint"])
    if previous == current_fingerprint:
        status = "fresh"
        reason = "shape signals match current workspace"
        action = "Reuse snapshot for Navigator planning."
    else:
        status = "stale"
        reason = "manifests, CI/scanner files, TailTrail artifacts, or top-level project shape changed"
        action = "Run `tailtrail bootstrap refresh` before relying on this snapshot."
    return {
        "schema_version": "1",
        "type": "tailtrail-bootstrap-status",
        "path": SNAPSHOT_PATH.as_posix(),
        "exists": True,
        "status": status,
        "reason": reason,
        "recommended_action": action,
        "created_at": existing.get("created_at"),
        "languages": existing.get("languages", []),
        "manifests": existing.get("manifests", []),
        "test_signals": existing.get("test_signals", []),
        "ci_signals": existing.get("ci_signals", []),
        "scanner_signals": existing.get("scanner_signals", []),
        "previous_fingerprint": previous,
        "current_fingerprint": current_fingerprint,
        "snapshot": existing,
    }


def write_snapshot(root: Path, snapshot: dict[str, Any]) -> Path:
    path = root / SNAPSHOT_PATH
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(snapshot, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    return path


def render_status(status: dict[str, Any]) -> str:
    lines = [
        "# TailTrail Bootstrap Snapshot Status",
        "",
        f"- Path: `{status['path']}`",
        f"- Exists: `{str(status['exists']).lower()}`",
        f"- Status: `{status['status']}`",
        f"- Reason: {status['reason']}",
        f"- Recommended action: {status['recommended_action']}",
    ]
    if status.get("languages"):
        lines.append("- Languages: " + ", ".join(f"`{item}`" for item in status["languages"]))
    if status.get("manifests"):
        lines.append("- Manifests: " + ", ".join(f"`{item}`" for item in status["manifests"][:8]))
    if status.get("test_signals"):
        lines.append("- Test signals: " + ", ".join(f"`{item}`" for item in status["test_signals"]))
    if status.get("ci_signals"):
        lines.append("- CI signals: " + ", ".join(f"`{item}`" for item in status["ci_signals"]))
    if status.get("scanner_signals"):
        lines.append("- Scanner signals: " + ", ".join(f"`{item}`" for item in status["scanner_signals"]))
    return "\n".join(lines) + "\n"


def render_snapshot(snapshot: dict[str, Any], written: Path | None = None) -> str:
    lines = [
        "# TailTrail Bootstrap Snapshot",
        "",
        "- Scope: safe repo/runtime facts only",
        "- Source bodies read: `false`",
        "- Project code executed: `false`",
    ]
    if written:
        lines.append(f"- Written: `{written.as_posix()}`")
    lines.extend(
        [
            f"- Root kind: `{snapshot['root_kind']}`",
            "- Languages: " + (", ".join(f"`{item}`" for item in snapshot["languages"]) if snapshot["languages"] else "`unknown`"),
            "- Package managers: " + (", ".join(f"`{item}`" for item in snapshot["package_managers"]) if snapshot["package_managers"] else "`none detected`"),
            "- Test signals: " + (", ".join(f"`{item}`" for item in snapshot["test_signals"]) if snapshot["test_signals"] else "`none detected`"),
            "- CI signals: " + (", ".join(f"`{item}`" for item in snapshot["ci_signals"]) if snapshot["ci_signals"] else "`none detected`"),
            "- Scanner signals: " + (", ".join(f"`{item}`" for item in snapshot["scanner_signals"]) if snapshot["scanner_signals"] else "`none detected`"),
            "",
            "## Recommended First Reads",
            "",
        ]
    )
    if snapshot["recommended_first_reads"]:
        lines.extend(f"- `{item}`" for item in snapshot["recommended_first_reads"])
    else:
        lines.append("- No obvious docs or manifests detected.")
    lines.extend(["", "## Avoid First Reads", ""])
    lines.extend(f"- {item}" for item in snapshot["avoid_first_reads"])
    return "\n".join(lines) + "\n"


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description="Create or inspect a safe pre-task TailTrail bootstrap snapshot.")
    subparsers = parser.add_subparsers(dest="command", required=True)
    for command in ("snapshot", "refresh"):
        sub = subparsers.add_parser(command, help=f"Run bootstrap {command}.")
        sub.add_argument("--root", type=Path, default=Path("."), help="Target repo root.")
        sub.add_argument("--format", choices=("markdown", "json"), default="markdown")
        sub.add_argument("--write-result", action="store_true", help="Write .tailtrail/bootstrap-snapshot.json.")
    status = subparsers.add_parser("status", help="Check bootstrap snapshot freshness.")
    status.add_argument("--root", type=Path, default=Path("."), help="Target repo root.")
    status.add_argument("--format", choices=("markdown", "json"), default="markdown")
    return parser


def main() -> int:
    parser = build_parser()
    args = parser.parse_args()
    root = args.root.resolve()
    if args.command == "status":
        status = snapshot_status(root)
        if args.format == "json":
            print(json.dumps(status, indent=2, sort_keys=True))
        else:
            print(render_status(status), end="")
        return 0

    snapshot = build_snapshot(root)
    write_result = args.write_result or args.command == "refresh"
    written = write_snapshot(root, snapshot) if write_result else None
    if args.format == "json":
        print(json.dumps(snapshot, indent=2, sort_keys=True))
    else:
        print(render_snapshot(snapshot, written), end="")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
