#!/usr/bin/env python3

from __future__ import annotations

import argparse
import hashlib
import json
import shutil
from datetime import datetime, timezone
from pathlib import Path

from install_surfaces import DEFAULT_SURFACE, SURFACES, resolve


ROOT = Path(__file__).resolve().parents[1]

COPILOT_SOURCE = ROOT / "adapters" / "copilot-instructions.md"

PACK_FILES = [
    ".cursor/rules/tailtrail.mdc",
    ".github/copilot-instructions.md",
    ".openai/chatgpt-instructions.md",
    "AGENTS.md",
    "AIDLC.md",
    "CLAUDE.md",
    "DEPENDENCY-GATE.md",
    "EVALUATION-HARNESS.md",
    "GEMINI.md",
    "GUARDRAILS.md",
    "GOVERNANCE.md",
    "MCP-SERVER.md",
    "QUICKSTART.md",
    "README.md",
    "ROADMAP.md",
    "TOKEN-AUTOPILOT.md",
    "TOKEN-SLICER.md",
    "TAILTRAIL-COMMANDS.md",
    "tailtrail-registry.json",
    "tailtrail-registry.schema.json",
    "context/TailTrail.map.md",
    "context/guardrail-layers.md",
    "context/intent-aliases.md",
    "context/slices.md",
    "context/token-router.md",
    "pyproject.toml",
    "tailtrail-policy.example.md",
    "tailtrail_cli.py",
    "templates/intent-overrides.json",
    "USEFUL-PROMPTS.md",
    "USER-GUIDE.md",
]

PACK_DIRS = [
    "adapters",
    "aidlc",
    "assets",
    "benchmarks",
    "context",
    "hooks",
    "templates",
    "schemas",
]

PACK_SCRIPTS = [
    "scripts/aidlc-check.py",
    "scripts/aidlc-init.py",
    "scripts/analyze-benchmark.py",
    "scripts/benchmark-tailtrail.py",
    "scripts/bootstrap-snapshot.py",
    "scripts/check-tailtrail.py",
    "scripts/ci-summary.py",
    "scripts/code-graph-mapper.py",
    "scripts/context-receipt.py",
    "scripts/context_receipt.py",
    "scripts/cross-repo-reference.py",
    "scripts/efficacy-benchmark.py",
    "scripts/efficacy-run.py",
    "scripts/evaluation-audit.py",
    "scripts/evaluation-harness.py",
    "scripts/expand-intent.py",
    "scripts/graph-learning.py",
    "scripts/guardrail-precision.py",
    "scripts/guardrail-check.py",
    "scripts/install-copilot.py",
    "scripts/install-launcher.py",
    "scripts/install-local.py",
    "scripts/install_surfaces.py",
    "scripts/learning-agent.py",
    "scripts/learning-refresh.py",
    "scripts/learnings.py",
    "scripts/meta-harness-analyze.py",
    "scripts/meta-harness-propose.py",
    "scripts/mcp-server.py",
    "scripts/navigator.py",
    "scripts/navigator_core.py",
    "scripts/navigator_render.py",
    "scripts/policy-check.py",
    "scripts/prompt-profile.py",
    "scripts/prompt_profile.py",
    "scripts/quality-loop.py",
    "scripts/quality-run.py",
    "scripts/quality-scan.py",
    "scripts/review-graph.py",
    "scripts/route-context.py",
    "scripts/sonar-summary.py",
    "scripts/sync-adapters.py",
    "scripts/tailtrail.py",
    "scripts/tailtrail-registry.py",
    "scripts/registry-drift.py",
    "scripts/tailtrail-report.py",
    "scripts/sync-governance.py",
    "scripts/task-start.py",
    "scripts/task-next.py",
    "scripts/token-auto.py",
    "scripts/token-budget-coach.py",
    "scripts/token_budget_coach.py",
    "scripts/token-harness.py",
    "scripts/token-harness-ledger.py",
    "scripts/token-harness-proof.py",
    "scripts/token-harness-bridge.py",
    "scripts/token-harness-reduce.py",
    "scripts/token-savings.py",
    "scripts/update-copilot.py",
    "scripts/team-init.py",
    "scripts/update-tailtrail.py",
    "scripts/validation-summary.py",
    "scripts/vulnerability-run.py",
    "scripts/vulnerability-scan.py",
    "scripts/vulnerability-summary.py",
]

MANIFEST_NAME = ".tailtrail-install.json"

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


def copy_file(source: Path, destination: Path, force: bool, written: list[str], skipped: list[str]) -> None:
    if destination.exists() and not force:
        skipped.append(destination.as_posix())
        return
    destination.parent.mkdir(parents=True, exist_ok=True)
    shutil.copy2(source, destination)
    written.append(destination.as_posix())


def pack_ignore(directory: str, names: list[str]) -> set[str]:
    ignored = {"__pycache__", ".DS_Store"}.intersection(names)
    if Path(directory).name == "results" and "benchmarks" in Path(directory).parts:
        ignored.update(name for name in names if name.endswith(".md"))
    return ignored


def copy_dir(source: Path, destination: Path, force: bool, written: list[str], skipped: list[str]) -> None:
    if destination.exists() and not force:
        skipped.append(destination.as_posix())
        return
    if destination.exists():
        shutil.rmtree(destination)
    shutil.copytree(source, destination, ignore=pack_ignore)
    written.append(destination.as_posix())


def pack_entries_for(pack_files: list[str] | tuple[str, ...], pack_dirs: list[str] | tuple[str, ...], pack_scripts: list[str] | tuple[str, ...]) -> list[str]:
    entries: list[str] = []
    entries.extend(pack_files)
    for relative_dir in pack_dirs:
        source_dir = ROOT / relative_dir
        for path in sorted(source_dir.rglob("*")):
            if path.is_file() and "__pycache__" not in path.parts and path.name != ".DS_Store":
                if relative_dir == "benchmarks" and "results" in path.parts and path.suffix == ".md":
                    continue
                entries.append(path.relative_to(ROOT).as_posix())
    entries.extend(pack_scripts)
    return sorted(entries)


def pack_entries() -> list[str]:
    return pack_entries_for(PACK_FILES, PACK_DIRS, PACK_SCRIPTS)


def sha256(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def install_timestamp() -> str:
    return datetime.now(timezone.utc).strftime("%Y-%m-%dT00:00:00+00:00")


def write_manifest(
    pack_root: Path,
    pack_dir: Path,
    written: list[str],
    surface: str,
    pack_files: list[str] | tuple[str, ...],
    pack_dirs: list[str] | tuple[str, ...],
    pack_scripts: list[str] | tuple[str, ...],
    upgraded: bool = False,
) -> None:
    if pack_dir.as_posix() == ".":
        location = "repository root"
    else:
        location = pack_dir.as_posix()
    files = {
        relative_path: {
            "sha256": sha256(ROOT / relative_path),
        }
        for relative_path in pack_entries_for(pack_files, pack_dirs, pack_scripts)
    }
    files[".github/copilot-instructions.md"] = {
        "sha256": hashlib.sha256(copilot_body(pack_dir).encode("utf-8")).hexdigest(),
    }
    manifest = {
        "version": 1,
        "tool": "tailtrail",
        "surface": surface,
        "pack_dir": pack_dir.as_posix(),
        "pack_location": location,
        "updated_at": install_timestamp(),
        "files": files,
        "customization": {
            "preferred_override_files": [
                ".tailtrail/intent-overrides.json",
                f"{pack_dir.as_posix()}/intent-overrides.json" if pack_dir.as_posix() != "." else "intent-overrides.json",
            ],
            "note": "Customize TailTrail through override files instead of editing managed core files.",
        },
    }
    if upgraded:
        manifest["upgraded_at"] = datetime.now(timezone.utc).isoformat()
    destination = pack_root / MANIFEST_NAME
    destination.write_text(json.dumps(manifest, indent=2) + "\n", encoding="utf-8")
    written.append(destination.as_posix())


def validate_pack_dir(pack_dir: str) -> Path:
    path = Path(pack_dir)
    if path.is_absolute():
        raise SystemExit("--pack-dir must be relative to the target project root")
    if any(part == ".." for part in path.parts):
        raise SystemExit("--pack-dir must not contain '..'")
    return path


def copilot_body(pack_dir: Path | None) -> str:
    body = COPILOT_SOURCE.read_text(encoding="utf-8")
    if pack_dir is None:
        return body

    pack_label = pack_dir.as_posix()
    if pack_label == ".":
        pack_label = "repository root"
        prefix = ""
        script_prefix = "scripts"
    else:
        prefix = f"{pack_dir.as_posix()}/"
        script_prefix = f"{pack_dir.as_posix()}/scripts"

    return (
        body
        + "\n\n"
        + "## Installed TailTrail Pack Location\n\n"
        + f"TailTrail support files are installed under `{pack_label}`.\n\n"
        + "When using TailTrail support files, resolve them from this location:\n\n"
        + f"- `{prefix}AGENTS.md`\n"
        + f"- `{prefix}AIDLC.md`\n"
        + f"- `{prefix}DEPENDENCY-GATE.md`\n"
        + f"- `{prefix}GUARDRAILS.md`\n"
        + f"- `{prefix}GOVERNANCE.md`\n"
        + f"- `{prefix}tailtrail-policy.example.md`\n"
        + f"- `{prefix}context/flow-catalog.md`\n"
        + f"- `{prefix}context/guardrail-layers.md`\n"
        + f"- `{prefix}context/intent-aliases.md`\n"
        + f"- `{prefix}context/navigator.md`\n"
        + f"- `{prefix}context/code-graph-mapper.md`\n"
        + f"- `{prefix}context/review-lenses.md`\n"
        + f"- `{prefix}context/TailTrail.map.md`\n"
        + f"- `{prefix}context/slices.md`\n"
        + f"- `{prefix}TAILTRAIL-COMMANDS.md`\n"
        + f"- `{prefix}USEFUL-PROMPTS.md`\n"
        + f"- `{prefix}hooks/`\n"
        + f"- `{prefix}benchmarks/`\n"
        + f"- `{prefix}aidlc/stages/`\n"
        + f"- `{prefix}templates/`\n\n"
        + "When scripts are needed, use:\n\n"
        + f"- `python3 {script_prefix}/tailtrail.py help`\n"
        + f"- `python3 {script_prefix}/tailtrail.py do \"fix Sonar issue and prepare PR\"`\n"
        + f"- `python3 {script_prefix}/tailtrail.py \"fix Sonar issue and prepare PR\"`\n"
        + f"- `python3 {script_prefix}/tailtrail.py guide \"fix Sonar issue and prepare PR\"`\n"
        + f"- `python3 {script_prefix}/navigator.py \"fix Sonar issue and prepare PR\"`\n"
        + f"- `python3 {script_prefix}/tailtrail.py graph --changed path/to/file`\n"
        + f"- `python3 {script_prefix}/tailtrail.py graph map --changed path/to/file`\n"
        + f"- `python3 {script_prefix}/tailtrail.py graph status --changed path/to/file`\n"
        + f"- `python3 {script_prefix}/tailtrail.py ci summarize --file ci.log`\n"
        + f"- `python3 {script_prefix}/tailtrail.py sonar summarize --file sonar.log`\n"
        + f"- `python3 {script_prefix}/tailtrail.py validation summarize --ci ci.log --sonar sonar.log`\n"
        + f"- `python3 {script_prefix}/tailtrail.py quality scan --changed path/to/file`\n"
        + f"- `python3 {script_prefix}/tailtrail.py quality run --approved --command \"npm run lint\"`\n"
        + f"- `python3 {script_prefix}/tailtrail.py quality-loop review --month 2026-07`\n"
        + f"- `python3 {script_prefix}/tailtrail.py report --month 2026-07`\n"
        + f"- `python3 {script_prefix}/tailtrail.py report value --month 2026-07`\n"
        + f"- `python3 {script_prefix}/tailtrail.py policy check --root .`\n"
        + f"- `python3 {script_prefix}/tailtrail.py governance check`\n"
        + f"- `python3 {script_prefix}/tailtrail.py vulnerability scan --changed package.json`\n"
        + f"- `python3 {script_prefix}/tailtrail.py vulnerability summarize --file audit.log`\n"
        + f"- `python3 {script_prefix}/tailtrail.py vulnerability run --approved --command \"npm audit\"`\n"
        + f"- `python3 {script_prefix}/expand-intent.py \"use AIDLC and review\"`\n"
        + f"- `python3 {script_prefix}/install-local.py --inspect`\n"
        + f"- `python3 {script_prefix}/benchmark-tailtrail.py`\n"
        + f"- `python3 {script_prefix}/analyze-benchmark.py {prefix}benchmarks/results/latest.json`\n"
        + f"- `python3 {script_prefix}/team-init.py --root . --mode optional`\n"
        + f"- `python3 {script_prefix}/learnings.py init --root .`\n"
        + f"- `python3 {script_prefix}/learning-agent.py search --tags sonar,java --limit 3`\n"
        + f"- `python3 {script_prefix}/learning-refresh.py recommend --root .`\n"
        + f"- `python3 {script_prefix}/graph-learning.py search --changed path/to/file --tags sonar,java`\n"
        + f"- `python3 {prefix}hooks/learning-capture-hook.py \"Fixed validator complexity\" --candidate \"Extract named guard methods while preserving validation order.\"`\n"
        + f"- `python3 {script_prefix}/review-graph.py --changed path/to/file`\n"
        + f"- `python3 {script_prefix}/code-graph-mapper.py map --changed path/to/file`\n"
        + f"- `python3 {script_prefix}/token-auto.py \"review this diff\"`\n"
        + f"- `python3 {script_prefix}/token-savings.py estimate --used {prefix}context/slices.md --avoided {prefix}ROADMAP.md {prefix}USER-GUIDE.md`\n"
        + f"- `python3 {script_prefix}/tailtrail.py token-harness bridge plan --path build.log`\n"
        + f"- `python3 {script_prefix}/tailtrail.py token-harness bridge validate-output --input /tmp/bridge-input.json --output /tmp/bridge-output.json`\n"
        + f"- `python3 {script_prefix}/route-context.py review`\n"
        + f"- `python3 {script_prefix}/aidlc-init.py --root . --depth standard`\n"
        + f"- `python3 {script_prefix}/aidlc-check.py --root .`\n"
        + f"- `python3 {prefix}hooks/tailtrail-lifecycle-hook.py \"use AIDLC and review\"`\n"
    )


def write_copilot(destination: Path, pack_dir: Path | None, force: bool, written: list[str], skipped: list[str]) -> None:
    if destination.exists() and not force:
        skipped.append(destination.as_posix())
        return
    destination.parent.mkdir(parents=True, exist_ok=True)
    destination.write_text(copilot_body(pack_dir), encoding="utf-8")
    written.append(destination.as_posix())


def gitignore_covers(pattern: str, lines: list[str]) -> bool:
    if pattern in lines:
        return True
    if pattern == ".tailtrail/" and any(line in {".tailtrail/", ".tailtrail"} for line in lines):
        return True
    if pattern == "tailtrail/" and any(line in {"tailtrail/", "tailtrail"} for line in lines):
        return True
    return False


def write_gitignore(target_root: Path, pack_dir: Path | None, written: list[str], skipped: list[str]) -> None:
    gitignore = target_root / ".gitignore"
    existing = gitignore.read_text(encoding="utf-8").splitlines() if gitignore.exists() else []
    existing_stripped = [line.strip() for line in existing if line.strip() and not line.lstrip().startswith("#")]
    entries = list(LOCAL_INSTALL_GITIGNORE)
    if pack_dir is not None and pack_dir.as_posix() not in {"tailtrail", "."}:
        entries.append(f"{pack_dir.as_posix().rstrip('/')}/")
    missing = [entry for entry in entries if not gitignore_covers(entry, existing_stripped)]
    if not missing:
        skipped.append(gitignore.as_posix())
        return
    section = [
        "",
        "# TailTrail local install/runtime files",
        "# Keep TailTrail setup files local. Commit only reviewed tailtrail-meta/ metadata.",
        *missing,
    ]
    gitignore.parent.mkdir(parents=True, exist_ok=True)
    gitignore.write_text("\n".join([*existing, *section]).rstrip() + "\n", encoding="utf-8")
    written.append(gitignore.as_posix())


def read_manifest(pack_root: Path) -> dict[str, object] | None:
    path = pack_root / MANIFEST_NAME
    if not path.exists():
        return None
    try:
        value = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError) as error:
        raise SystemExit(f"Unable to read install manifest {path}: {error}") from error
    if not isinstance(value, dict):
        raise SystemExit(f"Install manifest {path} must contain a JSON object")
    return value


def manifest_files(manifest: dict[str, object] | None) -> dict[str, dict[str, str]]:
    raw = manifest.get("files") if isinstance(manifest, dict) else {}
    if not isinstance(raw, dict):
        return {}
    result: dict[str, dict[str, str]] = {}
    for key, value in raw.items():
        if isinstance(key, str) and isinstance(value, dict):
            sha_value = value.get("sha256")
            if isinstance(sha_value, str):
                result[key] = {"sha256": sha_value}
    return result


def installed_surface(manifest: dict[str, object] | None) -> str:
    value = manifest.get("surface") if isinstance(manifest, dict) else None
    return value if isinstance(value, str) else "unknown"


def source_hash(relative_path: str, pack_dir: Path) -> str:
    if relative_path == ".github/copilot-instructions.md":
        return hashlib.sha256(copilot_body(pack_dir).encode("utf-8")).hexdigest()
    return sha256(ROOT / relative_path)


def write_entry(relative_path: str, destination: Path, pack_dir: Path) -> None:
    destination.parent.mkdir(parents=True, exist_ok=True)
    if relative_path == ".github/copilot-instructions.md":
        destination.write_text(copilot_body(pack_dir), encoding="utf-8")
    else:
        shutil.copy2(ROOT / relative_path, destination)


def can_upgrade_entry(destination: Path, relative_path: str, previous_files: dict[str, dict[str, str]]) -> tuple[bool, str | None]:
    if not destination.exists():
        return True, None
    previous = previous_files.get(relative_path, {})
    previous_hash = previous.get("sha256")
    if previous_hash and destination.is_file() and sha256(destination) == previous_hash:
        return True, None
    return False, f"{destination.as_posix()} exists and differs from the previous TailTrail-managed hash"


def plan_upgrade(pack_root: Path, pack_dir: Path) -> tuple[dict[str, object], list[str], list[str]]:
    manifest = read_manifest(pack_root)
    if manifest is None:
        raise SystemExit(f"No TailTrail install manifest found at {pack_root / MANIFEST_NAME}")
    current_surface = installed_surface(manifest)
    if current_surface == "extended":
        return manifest, [], []
    if current_surface != "core":
        raise SystemExit(f"Cannot upgrade unknown installed surface: {current_surface}")
    core_files, core_dirs, core_scripts = resolve("core", PACK_FILES, PACK_DIRS, PACK_SCRIPTS)
    extended_files, extended_dirs, extended_scripts = resolve("extended", PACK_FILES, PACK_DIRS, PACK_SCRIPTS)
    core_entries = set(pack_entries_for(core_files, core_dirs, core_scripts))
    extended_entries = set(pack_entries_for(extended_files, extended_dirs, extended_scripts))
    to_add = sorted(extended_entries - core_entries)
    previous_files = manifest_files(manifest)
    blocked: list[str] = []
    for relative_path in to_add:
        ok, reason = can_upgrade_entry(pack_root / relative_path, relative_path, previous_files)
        if not ok and reason:
            blocked.append(reason)
    return manifest, to_add, blocked


def status(pack_root: Path, pack_dir: Path) -> int:
    manifest = read_manifest(pack_root)
    if manifest is None:
        print(f"manifest: missing ({pack_root / MANIFEST_NAME})")
        print("surface: unknown")
        return 1
    surface = installed_surface(manifest)
    print(f"manifest: {pack_root / MANIFEST_NAME}")
    print(f"surface: {surface}")
    if surface == "core":
        _, to_add, blocked = plan_upgrade(pack_root, pack_dir)
        print(f"upgrade_adds: {len(to_add)} files")
        if to_add:
            print("upgrade_examples:")
            for item in to_add[:10]:
                print(f"- {item}")
        if blocked:
            print("upgrade_blockers:")
            for item in blocked:
                print(f"- {item}")
    elif surface == "extended":
        print("upgrade_adds: 0 files")
        print("already extended")
    else:
        print("upgrade_adds: unknown")
    return 0


def upgrade_to_extended(pack_root: Path, pack_dir: Path, force: bool, written: list[str], skipped: list[str]) -> int:
    manifest, to_add, blocked = plan_upgrade(pack_root, pack_dir)
    if installed_surface(manifest) == "extended":
        print("TailTrail install is already extended.")
        return 0
    if blocked and not force:
        print("TailTrail upgrade blocked to avoid overwriting user changes.")
        for item in blocked:
            print(f"- {item}")
        print("Use --force only after reviewing the listed files.")
        return 1
    for relative_path in to_add:
        write_entry(relative_path, pack_root / relative_path, pack_dir)
        written.append((pack_root / relative_path).as_posix())
    extended_files, extended_dirs, extended_scripts = resolve("extended", PACK_FILES, PACK_DIRS, PACK_SCRIPTS)
    write_manifest(pack_root, pack_dir, written, "extended", extended_files, extended_dirs, extended_scripts, upgraded=True)
    if not to_add:
        skipped.append("No files needed to be added.")
    return 0


def main() -> int:
    parser = argparse.ArgumentParser(description="Install TailTrail GitHub Copilot support into a target project.")
    parser.add_argument("--root", type=Path, default=Path.cwd(), help="Target project root.")
    parser.add_argument("--target", type=Path, help="Alias for --root that installs a managed pack at the target root.")
    parser.add_argument("--with-tailtrail-pack", action="store_true", help="Copy TailTrail support docs, templates, context, AIDLC, and scripts.")
    parser.add_argument("--pack-only", action="store_true", help="Install the managed TailTrail pack without writing Copilot instructions.")
    parser.add_argument("--pack-dir", default="tailtrail", help="Folder for TailTrail support files when --with-tailtrail-pack is used. Use '.' for root layout.")
    parser.add_argument("--surface", choices=SURFACES, default=DEFAULT_SURFACE, help="Surface-area profile: core is first-run minimal, extended is the full pack.")
    parser.add_argument("--upgrade", action="store_true", help="Upgrade an existing Core install to Extended without deleting files.")
    parser.add_argument("--status", action="store_true", help="Report installed surface and what an upgrade would add.")
    parser.add_argument("--no-gitignore", action="store_true", help="Do not add TailTrail local-install ignore entries to .gitignore.")
    parser.add_argument("--force", action="store_true", help="Overwrite existing target files.")
    args = parser.parse_args()

    target_was_used = args.target is not None
    target_root = (args.target or args.root).resolve()
    with_tailtrail_pack = args.with_tailtrail_pack or target_was_used or args.upgrade or args.status
    pack_dir_value = "." if target_was_used and args.pack_dir == "tailtrail" else args.pack_dir
    pack_dir = validate_pack_dir(pack_dir_value) if with_tailtrail_pack else None
    pack_root = target_root / pack_dir if pack_dir is not None else target_root
    written: list[str] = []
    skipped: list[str] = []

    if args.status:
        if pack_dir is None:
            raise SystemExit("--status requires a managed pack target")
        return status(pack_root, pack_dir)

    if args.upgrade:
        if pack_dir is None:
            raise SystemExit("--upgrade requires a managed pack target")
        code = upgrade_to_extended(pack_root, pack_dir, args.force, written, skipped)
        if written:
            print("Written:")
            for path in written:
                print(f"- {path}")
        if skipped:
            print("Skipped:")
            for path in skipped:
                print(f"- {path}")
        return code

    if not args.pack_only:
        write_copilot(
            target_root / ".github" / "copilot-instructions.md",
            pack_dir,
            args.force,
            written,
            skipped,
        )

    if with_tailtrail_pack:
        pack_files, pack_dirs, pack_scripts = resolve(args.surface, PACK_FILES, PACK_DIRS, PACK_SCRIPTS)
        for relative_path in pack_files:
            if relative_path == ".github/copilot-instructions.md":
                continue
            copy_file(ROOT / relative_path, pack_root / relative_path, args.force, written, skipped)
        for relative_path in pack_dirs:
            copy_dir(ROOT / relative_path, pack_root / relative_path, args.force, written, skipped)
        for relative_path in pack_scripts:
            copy_file(ROOT / relative_path, pack_root / relative_path, args.force, written, skipped)
        write_manifest(pack_root, pack_dir, written, args.surface, pack_files, pack_dirs, pack_scripts)

    if not args.no_gitignore:
        write_gitignore(target_root, pack_dir, written, skipped)

    setup_name = "TailTrail managed pack" if args.pack_only else "TailTrail Copilot setup"
    print(f"{setup_name} target: {target_root}")
    if pack_dir is not None:
        print(f"TailTrail pack folder: {(target_root / pack_dir).resolve()}")
        print(f"TailTrail surface: {args.surface}")
    if written:
        print("Written:")
        for path in written:
            print(f"- {path}")
    if skipped:
        print("Skipped existing files:")
        for path in skipped:
            print(f"- {path}")
    if pack_dir is not None and args.surface == "core":
        print("Core installed. Run 'tailtrail install upgrade-to-extended' when ready.")
    print("Next: review target changes. Do not commit TailTrail install/runtime files; commit only intentional tailtrail-meta/ metadata.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
