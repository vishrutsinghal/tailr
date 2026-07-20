#!/usr/bin/env python3

from __future__ import annotations

import argparse
import json
import shutil
import subprocess
import sys
from dataclasses import dataclass
from pathlib import Path

from install_surfaces import DEFAULT_SURFACE, SURFACES


ROOT = Path(__file__).resolve().parents[1]

PROFILES = ("inspect", "generic", "codex", "codex-plugin", "copilot", "aidlc", "hooks", "full")
CODEX_PLUGIN_PAYLOAD = (
    "AGENTS.md",
    ".codex-plugin/plugin.json",
    "skills/tailtrail/SKILL.md",
    "skills/tailtrail-review/SKILL.md",
)
DEFERRED = [
    "Global Codex config writes are not implemented.",
    "Shell profile edits are not implemented.",
    "IDE setting changes are not implemented.",
    "Network install or dependency download is not implemented.",
    "Auto-enabling hooks everywhere is not implemented.",
    "Profile sprawl is intentionally deferred until real usage shows the need.",
]

LOCAL_INSTALL_GITIGNORE = [
    ".tailtrail/",
    "tailtrail/",
    ".github/copilot-instructions.md",
    ".cursor/rules/tailtrail.mdc",
    ".openai/chatgpt-instructions.md",
    "CLAUDE.md",
    "GEMINI.md",
    "AGENTS.md",
    "AIDLC.md",
    "DEPENDENCY-GATE.md",
    "GUARDRAILS.md",
    "GOVERNANCE.md",
    "TOKEN-AUTOPILOT.md",
    "TOKEN-SLICER.md",
    "TAILTRAIL-COMMANDS.md",
    "USEFUL-PROMPTS.md",
    "USER-GUIDE.md",
    "tailtrail-policy.md",
    "tailtrail-policy.example.md",
    "aidlc-docs/",
    "!tailtrail-meta/",
    "!tailtrail-meta/README.md",
    "!tailtrail-meta/code-graph-cache.json",
    "!tailtrail-meta/harness-summary.schema.json",
    "!tailtrail-meta/harness-summary.jsonl",
]


@dataclass(frozen=True)
class Step:
    action: str
    command: list[str] | None = None
    source: Path | None = None
    destination: Path | None = None
    note: str | None = None


def relative(path: Path, root: Path) -> str:
    try:
        return path.relative_to(root).as_posix()
    except ValueError:
        return path.as_posix()


def run(command: list[str], quiet: bool = False) -> int:
    result = subprocess.run(
        command,
        cwd=ROOT,
        text=True,
        check=False,
        capture_output=quiet,
    )
    if quiet and result.returncode != 0:
        sys.stderr.write(result.stderr)
        sys.stderr.write(result.stdout)
    return result.returncode


def validate_repo() -> None:
    code = run([sys.executable, str(ROOT / "scripts" / "check-tailtrail.py")], quiet=True)
    if code != 0:
        raise SystemExit(code)


def validate_codex_plugin_payload() -> None:
    missing = [path for path in CODEX_PLUGIN_PAYLOAD if not (ROOT / path).is_file()]
    if missing:
        raise SystemExit(f"TailTrail Codex plugin payload is incomplete: {', '.join(missing)}")


def inspect_payload() -> dict[str, object]:
    return {
        "tool": "TailTrail",
        "root": ROOT.as_posix(),
        "profiles": list(PROFILES),
        "surfaces": list(SURFACES),
        "default_surface": DEFAULT_SURFACE,
        "capabilities": [
            "Codex plugin source",
            "Codex project guidance installer",
            "portable AGENTS.md guidance",
            "GitHub Copilot managed pack",
            "optional `tailtrail` launcher command",
            "AIDLC lifecycle initializer",
            "optional lifecycle/token hooks",
            "team guidance initializer",
            "safe pack updater",
        ],
        "recommended_start": [
            "python3 scripts/install-local.py --inspect",
            "python3 scripts/tailtrail.py install launcher --dry-run",
            "python3 scripts/tailtrail.py install launcher",
            "python3 scripts/tailtrail.py install codex --target /path/to/project --dry-run",
            "python3 scripts/tailtrail.py install codex --target /path/to/project",
            "python3 scripts/tailtrail.py install codex-plugin --target /path/to/project --dry-run",
            "python3 scripts/tailtrail.py install codex-plugin --target /path/to/project",
            "python3 scripts/install-local.py --target /path/to/project --profile full --dry-run",
            "python3 scripts/install-local.py --target /path/to/project --profile full",
        ],
        "not_implemented_yet": DEFERRED,
    }


def print_inspect() -> None:
    payload = inspect_payload()
    print("# TailTrail Local Installer")
    print()
    print(f"Root: `{payload['root']}`")
    print()
    print("Profiles:")
    for profile in payload["profiles"]:
        print(f"- `{profile}`")
    print()
    print("Capabilities:")
    for capability in payload["capabilities"]:
        print(f"- {capability}")
    print()
    print("Recommended start:")
    for command in payload["recommended_start"]:
        print(f"- `{command}`")
    print()
    print("Not implemented yet:")
    for item in payload["not_implemented_yet"]:
        print(f"- {item}")


def generic_steps(target: Path, force: bool) -> list[Step]:
    destination = target / "AGENTS.md"
    if destination.exists() and not force:
        return [Step("skip", source=ROOT / "AGENTS.md", destination=destination, note="AGENTS.md already exists; use --force to overwrite.")]
    return [Step("copy", source=ROOT / "AGENTS.md", destination=destination)]


def codex_steps(target: Path, force: bool) -> list[Step]:
    destination = target / "AGENTS.md"
    if destination.exists() and not force:
        return [Step("skip", source=ROOT / "AGENTS.md", destination=destination, note="AGENTS.md already exists; preserve its project guidance or use --force to overwrite.")]
    return [Step("copy", source=ROOT / "AGENTS.md", destination=destination, note="Install TailTrail project guidance for Codex.")]


def codex_plugin_steps(target: Path, force: bool) -> list[Step]:
    steps: list[Step] = []
    agents_destination = target / "AGENTS.md"
    if agents_destination.exists() and not force:
        steps.append(Step("skip", source=ROOT / "AGENTS.md", destination=agents_destination, note="AGENTS.md already exists; preserve its project guidance or use --force to overwrite."))
    else:
        steps.append(Step("copy", source=ROOT / "AGENTS.md", destination=agents_destination, note="Install TailTrail project guidance for Codex."))

    plugin_destination = target / ".codex-plugin"
    if plugin_destination.exists() and not force:
        steps.append(Step("skip", source=ROOT / ".codex-plugin" / "plugin.json", destination=plugin_destination, note="Codex plugin source already exists; use --force to overwrite."))
    else:
        steps.append(Step("copytree", source=ROOT / ".codex-plugin", destination=plugin_destination, note="Install TailTrail Codex plugin manifest and local skills."))

    skills_destination = target / "skills"
    if skills_destination.exists() and not force:
        steps.append(Step("skip", source=ROOT / "skills", destination=skills_destination, note="Skills directory already exists; use --force to merge/overwrite."))
    else:
        steps.append(Step("copytree", source=ROOT / "skills", destination=skills_destination, note="Install TailTrail Codex plugin skill sources."))

    return steps


def copilot_steps(target: Path, pack_dir: str, force: bool, surface: str) -> list[Step]:
    command = [
        sys.executable,
        str(ROOT / "scripts" / "install-copilot.py"),
        "--root",
        target.as_posix(),
        "--with-tailtrail-pack",
        "--pack-dir",
        pack_dir,
        "--surface",
        surface,
    ]
    if force:
        command.append("--force")
    return [Step("run", command=command, note="Install GitHub Copilot instructions and managed TailTrail pack.")]


def aidlc_steps(target: Path, depth: str, force: bool) -> list[Step]:
    command = [
        sys.executable,
        str(ROOT / "scripts" / "aidlc-init.py"),
        "--root",
        target.as_posix(),
        "--depth",
        depth,
    ]
    if force:
        command.append("--force")
    return [Step("run", command=command, note=f"Initialize AIDLC docs at {depth} depth.")]


def hooks_steps(target: Path, pack_dir: str) -> list[Step]:
    hook = target / pack_dir / "hooks" / "tailtrail-lifecycle-hook.py"
    return [
        Step("info", note="Hooks are opt-in. Wire these commands only in hook-capable hosts."),
        Step("info", note=f"Startup: python3 {relative(hook, target)} --startup --no-state"),
        Step("info", note=f"Prompt: python3 {relative(hook, target)} \"use AIDLC and review\" --no-state"),
        Step("info", note=f"CI/Sonar: python3 {relative(hook, target)} \"use CI Sonar\" --no-state"),
    ]


def team_steps(target: Path, pack_dir: str, team_mode: str, force: bool) -> list[Step]:
    command = [
        sys.executable,
        str(ROOT / "scripts" / "team-init.py"),
        "--root",
        target.as_posix(),
        "--mode",
        team_mode,
        "--pack-dir",
        pack_dir,
    ]
    if force:
        command.append("--force")
    return [Step("run", command=command, note=f"Initialize {team_mode} team guidance.")]


def steps_for(profile: str, target: Path, pack_dir: str, depth: str, team_mode: str, force: bool, surface: str) -> list[Step]:
    if profile == "inspect":
        return []
    if profile == "generic":
        return generic_steps(target, force)
    if profile == "codex":
        return codex_steps(target, force)
    if profile == "codex-plugin":
        return codex_plugin_steps(target, force)
    if profile == "copilot":
        return copilot_steps(target, pack_dir, force, surface)
    if profile == "aidlc":
        return aidlc_steps(target, depth, force)
    if profile == "hooks":
        return hooks_steps(target, pack_dir)
    if profile == "full":
        return [
            *copilot_steps(target, pack_dir, force, surface),
            *aidlc_steps(target, depth, force),
            *team_steps(target, pack_dir, team_mode, force),
            *hooks_steps(target, pack_dir),
        ]
    raise SystemExit(f"Unknown profile: {profile}")


def gitignore_covers(pattern: str, lines: list[str]) -> bool:
    if pattern in lines:
        return True
    if pattern == ".tailtrail/" and any(line in {".tailtrail/", ".tailtrail"} for line in lines):
        return True
    if pattern == "tailtrail/" and any(line in {"tailtrail/", "tailtrail"} for line in lines):
        return True
    return False


def write_local_gitignore(target: Path) -> bool:
    gitignore = target / ".gitignore"
    existing = gitignore.read_text(encoding="utf-8").splitlines() if gitignore.exists() else []
    active = [line.strip() for line in existing if line.strip() and not line.lstrip().startswith("#")]
    missing = [entry for entry in LOCAL_INSTALL_GITIGNORE if not gitignore_covers(entry, active)]
    if not missing:
        return False
    section = [
        "",
        "# TailTrail local install/runtime files",
        "# Keep TailTrail setup files local. Commit only reviewed tailtrail-meta/ metadata.",
        *missing,
    ]
    gitignore.write_text("\n".join([*existing, *section]).rstrip() + "\n", encoding="utf-8")
    return True


def print_plan(profile: str, surface: str, target: Path, steps: list[Step], dry_run: bool) -> None:
    print("TailTrail local installer")
    print(f"Profile: {profile} (assistant/install context)")
    print(f"Surface: {surface} (file breadth)")
    print(f"Target: {target}")
    print(f"Mode: {'dry-run' if dry_run else 'apply'}")
    if not steps:
        print("No target changes for this profile.")
        return
    print("Plan:")
    for step in steps:
        if step.action == "copy":
            print(f"- copy {step.source} -> {step.destination}")
        elif step.action == "copytree":
            print(f"- copy tree {step.source} -> {step.destination}")
        elif step.action == "run":
            print(f"- run {' '.join(step.command or [])}")
        elif step.action == "skip":
            print(f"- skip {step.destination}: {step.note}")
        else:
            print(f"- {step.note}")
    print("- ensure .gitignore keeps TailTrail setup/runtime local and allows reviewed tailtrail-meta/ metadata")


def apply_steps(target: Path, steps: list[Step], dry_run: bool) -> int:
    if dry_run:
        return 0
    for step in steps:
        if step.action in {"info", "skip"}:
            continue
        if step.action == "copy":
            if step.source is None or step.destination is None:
                raise SystemExit("copy step missing source or destination")
            step.destination.parent.mkdir(parents=True, exist_ok=True)
            shutil.copy2(step.source, step.destination)
            print(f"Copied: {relative(step.destination, target)}")
        elif step.action == "copytree":
            if step.source is None or step.destination is None:
                raise SystemExit("copytree step missing source or destination")
            if step.destination.exists():
                if not step.destination.is_dir():
                    raise SystemExit(f"Destination exists and is not a directory: {step.destination}")
                shutil.copytree(step.source, step.destination, dirs_exist_ok=True)
            else:
                shutil.copytree(step.source, step.destination)
            print(f"Copied tree: {relative(step.destination, target)}")
        elif step.action == "run":
            if step.command is None:
                raise SystemExit("run step missing command")
            code = run(step.command)
            if code != 0:
                return code
    if write_local_gitignore(target):
        print("Updated: .gitignore")
    return 0


def main() -> int:
    parser = argparse.ArgumentParser(description="Inspect or install TailTrail into a local project without global writes.")
    parser.add_argument("--inspect", action="store_true", help="Validate this repo and print capabilities.")
    parser.add_argument("--target", type=Path, help="Target project root for install profiles.")
    parser.add_argument("--profile", choices=PROFILES, default="inspect", help="Install profile.")
    parser.add_argument("--surface", choices=SURFACES, default=DEFAULT_SURFACE, help="Surface-area profile for managed packs: core is first-run minimal, extended is the full pack.")
    parser.add_argument("--pack-dir", default="tailtrail", help="Managed TailTrail pack folder for Copilot/full profiles.")
    parser.add_argument("--depth", choices=["minimal", "standard", "comprehensive"], default="standard", help="AIDLC depth.")
    parser.add_argument("--team-mode", choices=["optional", "required"], default="optional", help="Team guidance mode for full profile.")
    parser.add_argument("--dry-run", action="store_true", help="Print the plan without writing target files.")
    parser.add_argument("--force", action="store_true", help="Overwrite profile-managed files when supported.")
    parser.add_argument("--format", choices=["markdown", "json"], default="markdown", help="Output format for inspect mode.")
    args = parser.parse_args()

    profile = "inspect" if args.inspect else args.profile
    if profile in {"codex", "codex-plugin"}:
        validate_codex_plugin_payload()
    else:
        validate_repo()
    if profile == "inspect":
        if args.format == "json":
            print(json.dumps(inspect_payload(), indent=2))
        else:
            print_inspect()
        return 0

    if args.target is None:
        raise SystemExit("--target is required for install profiles")

    target = args.target.resolve()
    steps = steps_for(profile, target, args.pack_dir, args.depth, args.team_mode, args.force, args.surface)
    print_plan(profile, args.surface, target, steps, args.dry_run)
    sys.stdout.flush()
    code = apply_steps(target, steps, args.dry_run)
    if code == 0:
        print("Done. Review target project changes before committing.")
    return code


if __name__ == "__main__":
    raise SystemExit(main())
