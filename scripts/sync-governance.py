#!/usr/bin/env python3

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
START = "<!-- tailtrail-governance:start -->"
END = "<!-- tailtrail-governance:end -->"

TARGETS = (
    "AGENTS.md",
    "CLAUDE.md",
    "GEMINI.md",
    "ROADMAP.md",
    "context/guardrail-layers.md",
    "adapters/claude.md",
    "adapters/chatgpt-instructions.md",
    "adapters/copilot-instructions.md",
    "adapters/cursor.mdc",
    "adapters/gemini.md",
    ".github/copilot-instructions.md",
    ".openai/chatgpt-instructions.md",
    ".cursor/rules/tailtrail.mdc",
)

SNAPSHOT_TARGETS = (
    "demo-project-layout/tailtrail-demo-workspace/tailtrail/AGENTS.md",
    "demo-project-layout/tailtrail-demo-workspace/tailtrail/GOVERNANCE.md",
    "demo-project-layout/tailtrail-demo-workspace/.github/copilot-instructions.md",
    "demo-project-layout/tailtrail-demo-workspace/tailtrail/adapters/claude.md",
    "demo-project-layout/tailtrail-demo-workspace/tailtrail/adapters/chatgpt-instructions.md",
    "demo-project-layout/tailtrail-demo-workspace/tailtrail/adapters/copilot-instructions.md",
    "demo-project-layout/tailtrail-demo-workspace/tailtrail/adapters/cursor.mdc",
    "demo-project-layout/tailtrail-demo-workspace/tailtrail/adapters/gemini.md",
    "demo-project-layout/tailtrail-demo-workspace/tailtrail/context/guardrail-layers.md",
)


def read(relative_path: str, root: Path = ROOT) -> str:
    return (root / relative_path).read_text(encoding="utf-8")


def write(relative_path: str, body: str, root: Path = ROOT) -> None:
    (root / relative_path).write_text(body, encoding="utf-8")


def extract_block(body: str, path: str) -> str:
    start = body.find(START)
    end = body.find(END)
    if start < 0 or end < 0 or end < start:
        raise ValueError(f"{path}: missing governance sync markers")
    return body[start : end + len(END)]


def replace_block(body: str, block: str, path: str) -> str:
    start = body.find(START)
    end = body.find(END)
    if start < 0 or end < 0 or end < start:
        raise ValueError(f"{path}: missing governance sync markers")
    return body[:start] + block + body[end + len(END) :]


def canonical_block(root: Path = ROOT) -> str:
    return extract_block(read("GOVERNANCE.md", root), "GOVERNANCE.md")


def has_marker_block(body: str) -> bool:
    lines = body.splitlines()
    return any(line.strip() == START for line in lines) and any(line.strip() == END for line in lines)


def tracked_files(root: Path) -> list[Path]:
    result: list[Path] = []
    for path in root.rglob("*"):
        if not path.is_file():
            continue
        if any(part in {".git", ".tailtrail", "__pycache__", "aidlc-rules"} for part in path.parts):
            continue
        if path.name == ".DS_Store":
            continue
        result.append(path)
    return sorted(result)


def status_for(relative_path: str, role: str, canonical: str, root: Path) -> str:
    try:
        body = read(relative_path, root)
        current = extract_block(body, relative_path)
    except (OSError, ValueError):
        return "missing-marker"
    if current == canonical:
        return "ok"
    return "snapshot-drift" if role == "snapshot" else "drift"


def inventory(root: Path = ROOT) -> list[dict[str, str]]:
    canonical = canonical_block(root)
    rows: list[dict[str, str]] = [{"path": "GOVERNANCE.md", "role": "canonical", "status": "ok"}]
    registered = {"GOVERNANCE.md", *TARGETS, *SNAPSHOT_TARGETS}
    for target in TARGETS:
        rows.append({"path": target, "role": "target", "status": status_for(target, "target", canonical, root)})
    for target in SNAPSHOT_TARGETS:
        rows.append({"path": target, "role": "snapshot", "status": status_for(target, "snapshot", canonical, root)})
    for path in tracked_files(root):
        rel = path.relative_to(root).as_posix()
        if rel in registered:
            continue
        try:
            body = path.read_text(encoding="utf-8", errors="replace")
        except OSError:
            continue
        if has_marker_block(body):
            rows.append({"path": rel, "role": "unregistered", "status": "unregistered"})
    return rows


def inventory_payload(rows: list[dict[str, str]]) -> dict[str, object]:
    summary = {"ok": 0, "drift": 0, "missing_marker": 0, "snapshot_drift": 0, "unregistered": 0}
    for row in rows:
        status = row["status"].replace("-", "_")
        if status in summary:
            summary[status] += 1
    return {
        "type": "tailtrail-governance-inventory",
        "schema_version": "1",
        "canonical": "GOVERNANCE.md",
        "targets": [row for row in rows if row["role"] == "target"],
        "snapshots": [row for row in rows if row["role"] == "snapshot"],
        "unregistered": [row for row in rows if row["role"] == "unregistered"],
        "summary": summary,
        "rows": rows,
    }


def render_inventory_markdown(rows: list[dict[str, str]]) -> str:
    payload = inventory_payload(rows)
    lines = [
        "# TailTrail Governance Inventory",
        "",
        "- Canonical source: `GOVERNANCE.md`",
        f"- Targets: {len(payload['targets'])}",
        f"- Snapshots: {len(payload['snapshots'])}",
        f"- Unregistered: {len(payload['unregistered'])}",
        "",
        "| Path | Role | Status |",
        "|---|---|---|",
    ]
    lines.extend(f"| {row['path']} | {row['role']} | {row['status']} |" for row in rows)
    return "\n".join(lines) + "\n"


def check(root: Path = ROOT, strict: bool = False) -> list[str]:
    errors: list[str] = []
    canonical = canonical_block(root)
    guardrails = read("GUARDRAILS.md", root)
    for phrase in (
        "Do not act with more certainty than the evidence supports.",
        "Do not claim tests passed unless they were run and succeeded.",
        "Token saving must not hide material facts.",
        "Do not remove or weaken safeguards",
    ):
        if phrase not in guardrails:
            errors.append(f"GUARDRAILS.md missing canonical source phrase: {phrase}")
    for target in TARGETS:
        try:
            current = extract_block(read(target, root), target)
        except ValueError as error:
            errors.append(str(error))
            continue
        if current != canonical:
            errors.append(f"{target}: governance block is not synced with GOVERNANCE.md")
    rows = inventory(root)
    for row in rows:
        if row["role"] == "unregistered":
            message = f"{row['path']}: unregistered governance marker block"
            if strict:
                errors.append(message)
            else:
                print(f"Governance sync warning: {message}", file=sys.stderr)
    return errors


def sync(root: Path = ROOT, include_snapshots: bool = False) -> None:
    canonical = canonical_block(root)
    targets = [*TARGETS, *SNAPSHOT_TARGETS] if include_snapshots else TARGETS
    for target in targets:
        write(target, replace_block(read(target, root), canonical, target), root)


def main() -> int:
    parser = argparse.ArgumentParser(description="Check or sync TailTrail repeated governance text.")
    parser.add_argument("action", choices=["check", "sync", "inventory"], help="Check drift, rewrite marked governance blocks, or print an inventory.")
    parser.add_argument("--root", type=Path, default=ROOT)
    parser.add_argument("--strict", action="store_true", help="Fail check when unregistered files carry governance markers.")
    parser.add_argument("--include-snapshots", action="store_true", help="Allow sync to rewrite demo snapshot files.")
    parser.add_argument("--format", choices=("markdown", "json"), default="markdown")
    args = parser.parse_args()
    root = args.root.resolve()

    if args.action == "sync":
        sync(root, include_snapshots=args.include_snapshots)

    if args.action == "inventory":
        rows = inventory(root)
        if args.format == "json":
            print(json.dumps(inventory_payload(rows), indent=2, sort_keys=True))
        else:
            print(render_inventory_markdown(rows), end="")
        return 0

    errors = check(root, strict=args.strict)
    if errors:
        for error in errors:
            print(f"Governance sync failed: {error}", file=sys.stderr)
        return 1

    print("Governance sync passed.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
