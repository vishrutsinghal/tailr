#!/usr/bin/env python3

from __future__ import annotations

import argparse
from pathlib import Path


TEAM_SECTION_MARKER = "<!-- tailtrail-team-section -->"


def write_if_missing(path: Path, body: str, force: bool, written: list[str], skipped: list[str]) -> None:
    if path.exists() and not force:
        skipped.append(path.as_posix())
        return
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(body, encoding="utf-8")
    written.append(path.as_posix())


def append_agents_section(path: Path, mode: str, pack_dir: str, written: list[str], skipped: list[str]) -> None:
    section = (
        f"\n{TEAM_SECTION_MARKER}\n"
        "## TailTrail Team Usage\n\n"
        f"TailTrail team mode is `{mode}` for this project.\n\n"
        f"- TailTrail pack folder: `{pack_dir}`\n"
        "- Prefer short commands such as `Use delivery flow`, `Use risk flow`, `Use architecture review`, and `Use AIDLC review and handoff`.\n"
        "- Keep team customizations in `.tailtrail/intent-overrides.json` or `.tailtrail/learnings.md`.\n"
        "- Do not edit TailTrail-managed core files unless you intentionally plan to preserve or backup-overwrite them during update.\n"
    )
    if path.exists():
        body = path.read_text(encoding="utf-8")
        if TEAM_SECTION_MARKER in body:
            skipped.append(path.as_posix())
            return
        path.write_text(body.rstrip() + "\n" + section, encoding="utf-8")
    else:
        path.write_text("# Project Agent Guidance\n" + section, encoding="utf-8")
    written.append(path.as_posix())


def team_policy(mode: str, pack_dir: str) -> str:
    required = mode == "required"
    return (
        "# TailTrail Team Policy\n\n"
        f"- Mode: `{mode}`\n"
        f"- Pack folder: `{pack_dir}`\n"
        "- Use TailTrail for AI-assisted coding, review, dependency decisions, lifecycle work, handoff, and token discipline.\n"
        "- Keep local custom prompts in `.tailtrail/intent-overrides.json`.\n"
        "- Keep durable project facts in `.tailtrail/learnings.md`.\n"
        "- Update TailTrail with `python3 tailtrail/scripts/update-tailtrail.py --root . --dry-run` before adopting new features.\n"
        + ("- Required mode: verify the TailTrail pack exists before AI-assisted work.\n" if required else "- Optional mode: TailTrail is recommended but not enforced.\n")
    )


def check_script(pack_dir: str) -> str:
    return (
        "#!/usr/bin/env python3\n\n"
        "from pathlib import Path\n"
        "import sys\n\n"
        f"pack = Path({pack_dir!r})\n"
        "required = [pack / 'AGENTS.md', pack / 'scripts' / 'expand-intent.py', pack / 'context' / 'flow-catalog.md']\n"
        "missing = [path.as_posix() for path in required if not path.exists()]\n"
        "if missing:\n"
        "    print('TailTrail required files are missing:', ', '.join(missing), file=sys.stderr)\n"
        "    sys.exit(1)\n"
        "print('TailTrail team check passed.')\n"
    )


def main() -> int:
    parser = argparse.ArgumentParser(description="Initialize lightweight TailTrail team guidance in a target project.")
    parser.add_argument("--root", type=Path, default=Path.cwd(), help="Target project root.")
    parser.add_argument("--mode", choices=["optional", "required"], default="optional", help="Team adoption mode.")
    parser.add_argument("--pack-dir", default="tailtrail", help="TailTrail pack folder in the target project.")
    parser.add_argument("--force", action="store_true", help="Overwrite generated team policy/check files.")
    args = parser.parse_args()

    root = args.root.resolve()
    written: list[str] = []
    skipped: list[str] = []

    write_if_missing(root / ".tailtrail" / "team-policy.md", team_policy(args.mode, args.pack_dir), args.force, written, skipped)
    append_agents_section(root / "AGENTS.md", args.mode, args.pack_dir, written, skipped)

    if args.mode == "required":
        write_if_missing(root / ".tailtrail" / "check-tailtrail.py", check_script(args.pack_dir), args.force, written, skipped)

    print(f"TailTrail team mode initialized at: {root}")
    print(f"Mode: {args.mode}")
    if written:
        print("Written:")
        for path in written:
            print(f"- {path}")
    if skipped:
        print("Skipped existing files:")
        for path in skipped:
            print(f"- {path}")
    print("Next: review git diff, then commit the generated team guidance.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
