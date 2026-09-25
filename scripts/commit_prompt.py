#!/usr/bin/env python3
"""Phase 8: commit prompt and reporting (augmentation, not gating).

At plan completion, report what the graph knows about the task's files:
coverage % of task-relevant files with symbol-level detail, related but
unread files, and — when coverage justifies a build — a concrete
Phase 3 build suggestion with depth chosen from live data (D2 pickup).

Coverage (Option C): ready_files / task_relevant_files, where a file is
"ready" when the Phase 1 cache holds both its imports and its symbols.

| Coverage | Prompt?                              |
|----------|--------------------------------------|
| 0-25%    | No - wait for more accumulation      |
| 25-40%   | Consider - only for large tasks      |
| 40%+     | Yes - build validates and gap-fills  |

Never gates anything: assessment is read-only and always exits 0.
Accepting means running the suggested build (see efficacy note in the
report); declining or silence leaves the cache untouched. A mapper commit
within the last 7 days suppresses the prompt to reduce noise.

See docs/arch/code-graphing.md §3.8.
"""

from __future__ import annotations

import argparse
import json
import sys
from datetime import datetime, timedelta, timezone
from pathlib import Path
from typing import Any

SCRIPT_DIR = Path(__file__).resolve().parent
if str(SCRIPT_DIR) not in sys.path:
    sys.path.insert(0, str(SCRIPT_DIR))

import code_graph_cache

PROMPT_THRESHOLD = 0.40
CONSIDER_THRESHOLD = 0.25
LARGE_TASK_FILES = 10
SPRAWLING_TASK_FILES = 20
RECENT_COMMIT_DAYS = 7
MAX_RELATED = 10
MAX_DISPLAY = 20


def _normalize(files: list[str]) -> list[str]:
    seen: list[str] = []
    for item in files:
        rel = str(item or "").replace("\\", "/").strip().strip("/")
        if rel and rel not in seen:
            seen.append(rel)
    return seen


def _mapper_scope(root: Path) -> tuple[list[str], datetime | None]:
    """Return (built scope, commit time) of the mapper graph section, if any.

    Reads through the unified v1/v2 container reader (Stage 0c) so mapper
    graphs inside v2 containers are visible; the old top-level "graph"
    check missed them entirely. Read-only.
    """
    for rel in (code_graph_cache.SHARED_CACHE, code_graph_cache.LOCAL_CACHE):
        container, error = code_graph_cache.read_container(root / rel)
        if error is not None:
            continue
        mapper = container["mapper_graph"]
        if not isinstance(mapper, dict) or not isinstance(mapper.get("graph"), dict):
            continue
        scope = mapper.get("scope", [])
        stamp = mapper.get("updated_at") or mapper.get("created_at")
        try:
            committed = datetime.fromisoformat(str(stamp)) if stamp else None
        except ValueError:
            committed = None
        return [str(item) for item in scope if item], committed
    return [], None


def _maybe_rel(value: str, known: set[str]) -> str | None:
    """Best-effort: map a raw import string onto a known repo-relative path."""
    candidate = str(value or "").replace("\\", "/").strip().strip("./")
    if not candidate:
        return None
    if candidate in known:
        return candidate
    dotted = candidate.replace(".", "/")
    for suffix in (".py", "/__init__.py"):
        if dotted + suffix in known:
            return dotted + suffix
    return None


def related_files(task: list[str], entries: dict[str, Any]) -> list[str]:
    """Cached files outside the task set linked by import overlap (capped)."""
    task_set = set(task)
    known = set(entries) | task_set
    task_imports: set[str] = set()
    for rel in task:
        entry = entries.get(rel, {})
        for value in entry.get("imports", []):
            mapped = _maybe_rel(str(value), known)
            task_imports.add(mapped or str(value))
    related: list[str] = []
    # Reverse direction first: task files import these cached files.
    for rel in task:
        for value in entries.get(rel, {}).get("imports", []):
            mapped = _maybe_rel(str(value), known)
            if mapped and mapped in entries and mapped not in task_set and mapped not in related:
                related.append(mapped)
    # Forward direction: cached files importing the task's neighborhood.
    for rel, entry in entries.items():
        if rel in task_set or rel in related:
            continue
        for value in entry.get("imports", []):
            mapped = _maybe_rel(str(value), known)
            if (mapped or str(value)) in task_imports or (mapped and mapped in task_set):
                related.append(rel)
                break
        if len(related) >= MAX_RELATED:
            break
    return sorted(related)


def assess(root: Path | str, task_files: list[str]) -> dict[str, Any]:
    """Assess commit readiness for task-relevant files. Read-only."""
    root_path = Path(root)
    task = _normalize(task_files)
    cache_path = code_graph_cache.find_cache(root_path)
    entries: dict[str, Any] = {}
    if cache_path is not None:
        data, _ = code_graph_cache.load(cache_path)
        entries = data.get("files", {})
    ready = [
        rel for rel in task
        if entries.get(rel, {}).get("symbols") and entries.get(rel, {}).get("imports")
    ]
    coverage = len(ready) / len(task) if task else 0.0
    mapper_scope, committed_at = _mapper_scope(root_path)
    recent_commit = (
        committed_at is not None
        and committed_at > datetime.now(timezone.utc) - timedelta(days=RECENT_COMMIT_DAYS)
    )
    if not task:
        decision, reason = "no", "no task-relevant files supplied"
    elif recent_commit:
        decision, reason = "no", f"mapper commit within the last {RECENT_COMMIT_DAYS} days"
    elif coverage >= PROMPT_THRESHOLD:
        decision, reason = "yes", f"coverage {coverage:.0%} >= {PROMPT_THRESHOLD:.0%}"
    elif coverage >= CONSIDER_THRESHOLD and len(task) >= LARGE_TASK_FILES:
        decision, reason = "consider", f"coverage {coverage:.0%} on a large task ({len(task)} files)"
    elif coverage >= CONSIDER_THRESHOLD:
        decision, reason = "no", f"coverage {coverage:.0%} below prompt threshold for a small task"
    else:
        decision, reason = "no", f"coverage {coverage:.0%} - wait for more accumulation"
    gap = [rel for rel in task if rel not in set(mapper_scope)]
    depth = "shallow" if len(task) >= SPRAWLING_TASK_FILES else "medium"
    return {
        "task_files": len(task),
        "ready_files": len(ready),
        "coverage": round(coverage, 4),
        "decision": decision,
        "reason": reason,
        "ready": sorted(ready),
        "not_ready": sorted(set(task) - set(ready)),
        "related_unread": related_files(task, entries),
        "mapper_scope_files": len(mapper_scope),
        "recent_commit": recent_commit,
        "suggested_depth": depth if decision in ("yes", "consider") else None,
        "suggested_scope": gap if decision in ("yes", "consider") else [],
    }


def _suggest_command(root: Path, report: dict[str, Any]) -> str | None:
    if report["decision"] not in ("yes", "consider"):
        return None
    scope = report["suggested_scope"] or report["not_ready"]
    parts = " ".join(f"--changed {rel}" for rel in scope[:MAX_DISPLAY])
    suffix = " ..." if len(scope) > MAX_DISPLAY else ""
    return (
        f"python scripts/graph_builder.py --root {root.as_posix()} "
        f"{parts}{suffix} --depth {report['suggested_depth']}"
    )


def _render(root: Path, report: dict[str, Any]) -> str:
    lines = [
        "# TailTrail Commit Coverage",
        "",
        f"- Task files: `{report['task_files']}`",
        f"- Ready: `{report['ready_files']}` (`{report['coverage']:.0%}`)",
        f"- Decision: `{report['decision']}` ({report['reason']})",
        f"- Mapper scope files: `{report['mapper_scope_files']}`",
    ]
    if report["not_ready"]:
        lines.append(f"- Not ready: `{', '.join(report['not_ready'][:MAX_DISPLAY])}`")
    if report["related_unread"]:
        lines.append(f"- Related unread: `{', '.join(report['related_unread'])}`")
    command = _suggest_command(root, report)
    if command:
        lines.extend(["", "## Suggested build", "", f"`{command}`"])
        lines.append("- Accept by running it; decline/silence leaves the cache untouched.")
    return "\n".join(lines) + "\n"


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description="Commit coverage prompt (Phase 8, read-only).")
    parser.add_argument("--root", type=Path, default=Path.cwd(), help="Project root.")
    parser.add_argument("--file", action="append", default=[], help="Task-relevant file. Repeatable.")
    parser.add_argument("--format", choices=("text", "json"), default="text", help="Output format.")
    return parser


def main(argv: list[str] | None = None) -> int:
    args = build_parser().parse_args(argv)
    report = assess(args.root, args.file)
    if args.format == "json":
        payload = dict(report)
        payload["suggested_command"] = _suggest_command(Path(args.root), report)
        print(json.dumps(payload, indent=2, sort_keys=True))
    else:
        print(_render(Path(args.root), report), end="")
    return 0


if __name__ == "__main__":
    raise SystemExit(main(sys.argv[1:]))
