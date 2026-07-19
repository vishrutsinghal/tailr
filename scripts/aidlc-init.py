#!/usr/bin/env python3

from __future__ import annotations

import argparse
from datetime import datetime, timezone
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
TEMPLATE_DIR = ROOT / "templates"


DEPTH_ARTIFACTS = {
    "minimal": ["aidlc-state.md", "aidlc-audit.md", "change-brief.md", "diff-handoff.md", "validation-handoff.md"],
    "standard": [
        "aidlc-state.md",
        "aidlc-audit.md",
        "requirements.md",
        "workflow-plan.md",
        "implementation-plan.md",
        "diff-handoff.md",
        "validation-handoff.md",
        "stage-gate.md",
    ],
    "comprehensive": [
        "aidlc-state.md",
        "aidlc-audit.md",
        "requirements.md",
        "question-file.md",
        "workflow-plan.md",
        "implementation-plan.md",
        "diff-handoff.md",
        "validation-handoff.md",
        "operations-notes.md",
        "stage-gate.md",
    ],
}

OUTPUT_NAMES = {
    "aidlc-audit.md": "audit.md",
    "question-file.md": "questions.md",
    "stage-gate.md": "stage-gate.md",
}


def seeded_state(project: str, depth: str) -> str:
    now = datetime.now(timezone.utc).isoformat()
    return (
        "# AIDLC State\n\n"
        f"Project: {project}\n\n"
        "Owner or team:\n\n"
        f"Lifecycle depth: {depth}\n\n"
        "Current phase: Inception\n\n"
        "Current stage: Workspace Detection\n\n"
        "Status: Active\n\n"
        "Last completed step:\n\n"
        "Next step: Complete workspace detection and requirements analysis.\n\n"
        "Active approval gate:\n\n"
        "Open questions file:\n\n"
        "Current artifacts:\n\n"
        "Relevant source files:\n\n"
        "Validation command:\n\n"
        "Last validation result:\n\n"
        "Current risks:\n\n"
        f"Last updated: {now}\n"
    )


def copy_template(template_name: str, destination: Path, project: str, depth: str) -> None:
    if template_name == "aidlc-state.md":
        destination.write_text(seeded_state(project, depth), encoding="utf-8")
        return
    source = TEMPLATE_DIR / template_name
    destination.write_text(source.read_text(encoding="utf-8"), encoding="utf-8")


def main() -> int:
    parser = argparse.ArgumentParser(description="Create portable AIDLC docs for a target project.")
    parser.add_argument("--root", type=Path, default=Path.cwd(), help="Target project root.")
    parser.add_argument("--project", default=None, help="Project name for seeded state.")
    parser.add_argument("--depth", choices=sorted(DEPTH_ARTIFACTS), default="standard", help="Lifecycle depth.")
    parser.add_argument("--force", action="store_true", help="Overwrite existing generated AIDLC files.")
    args = parser.parse_args()

    target_root = args.root.resolve()
    docs_dir = target_root / "aidlc-docs"
    docs_dir.mkdir(parents=True, exist_ok=True)
    project = args.project or target_root.name

    created: list[str] = []
    skipped: list[str] = []
    for template_name in DEPTH_ARTIFACTS[args.depth]:
        output_name = OUTPUT_NAMES.get(template_name, template_name)
        destination = docs_dir / output_name
        if destination.exists() and not args.force:
            skipped.append(destination.relative_to(target_root).as_posix())
            continue
        copy_template(template_name, destination, project, args.depth)
        created.append(destination.relative_to(target_root).as_posix())

    print(f"AIDLC initialized at {docs_dir}")
    print(f"Depth: {args.depth}")
    if created:
        print("Created:")
        for path in created:
            print(f"- {path}")
    if skipped:
        print("Skipped existing files:")
        for path in skipped:
            print(f"- {path}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
