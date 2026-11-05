#!/usr/bin/env python3
"""Project one frozen bundled-v2 AIDLC identity into supported host surfaces.

Phase 4 consumes an immutable active-run binding. Codex receives a verified
copy because its upstream workflow expects ``.aidlc/aidlc-rules``; Copilot and
Claude receive project-relative references to the same content-addressed pack.
Every operation is offline, receipt-bound, idempotent, and completely checked
by the read-only status route.

The pre-v2 Codex-only entry point remains available when no ``run_id`` is
provided so existing Standard/legacy installations keep bounded compatibility.
"""
from __future__ import annotations

import argparse
import hashlib
import importlib.util
import json
import os
import shutil
import sys
import tempfile
import uuid
from datetime import datetime, timezone
from pathlib import Path, PurePosixPath
from typing import Any


ROOT = Path(__file__).resolve().parents[1]
if ROOT.as_posix() not in sys.path:
    sys.path.insert(0, ROOT.as_posix())

from tailtrail import aidlc_bundle


# Legacy schema-v1 Codex layout.
PACK = Path(".tailtrail") / "official-aidlc"
CORE = PACK / "aws-aidlc-rules" / "core-workflow.md"
DETAILS = PACK / "aws-aidlc-rule-details"
PROJECTED_ROOT = Path(".aidlc") / "aidlc-rules"
PROJECTED_CORE = PROJECTED_ROOT / "aws-aidlc-rules" / "core-workflow.md"
PROJECTED_DETAILS = PROJECTED_ROOT / "aws-aidlc-rule-details"
START = "<!-- tailtrail-official-aidlc:codex:start -->"
END = "<!-- tailtrail-official-aidlc:codex:end -->"

ADAPTER_VERSION = "1"
HOSTS: dict[str, dict[str, Any]] = {
    "codex": {
        "mode": "copy",
        "instruction": "AGENTS.md",
        "projection_root": PROJECTED_ROOT.as_posix(),
        "reload": {"state": "reload-required", "reason": "Reload project instructions after the managed AGENTS.md block changes."},
    },
    "copilot": {
        "mode": "reference",
        "instruction": ".github/copilot-instructions.md",
        "reload": {"state": "reload-required", "reason": "Reload the repository instruction context after the managed Copilot block changes."},
    },
    "claude": {
        "mode": "reference",
        "instruction": "CLAUDE.md",
        "reload": {"state": "restart-required", "reason": "Start a new Claude Code session after the managed CLAUDE.md block changes."},
    },
}


def _load(relative: str, name: str) -> Any:
    spec = importlib.util.spec_from_file_location(name, ROOT / relative)
    if spec is None or spec.loader is None:
        raise RuntimeError(f"Unable to load {relative}")
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


DETECT = _load("scripts/aidlc-official-detect.py", "official_aidlc_host_detect")


def _canonical(value: Any) -> bytes:
    return json.dumps(value, sort_keys=True, separators=(",", ":"), ensure_ascii=False).encode("utf-8")


def _fingerprint(value: Any) -> str:
    return "sha256:" + hashlib.sha256(_canonical(value)).hexdigest()


def _digest(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as stream:
        for chunk in iter(lambda: stream.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def _safe_root(root: Path) -> Path:
    requested = Path(root)
    if requested.is_symlink() or not requested.exists() or not requested.is_dir():
        raise ValueError(f"host projection root must be an existing non-symlink directory: {requested}")
    resolved = requested.resolve()
    if resolved == Path(resolved.anchor):
        raise ValueError("host projection into a filesystem root is forbidden")
    return resolved


def _safe_relative(value: Any) -> str:
    if not isinstance(value, str) or not value or "\\" in value or "\x00" in value:
        raise ValueError("host projection path must be one safe repository-relative POSIX path")
    path = PurePosixPath(value)
    if path.is_absolute() or any(part in {"", ".", ".."} for part in path.parts):
        raise ValueError(f"unsafe host projection path: {value}")
    return path.as_posix()


def _managed_path(root: Path, relative: str, *, create_parents: bool = False) -> Path:
    """Resolve one repository-relative path without following unsafe ancestors."""
    safe = _safe_relative(relative)
    parts = PurePosixPath(safe).parts
    cursor = root
    for part in parts[:-1]:
        cursor = cursor / part
        if cursor.exists() or cursor.is_symlink():
            if cursor.is_symlink() or not cursor.is_dir():
                raise ValueError(f"host projection path has an unsafe ancestor: {safe}")
        elif create_parents:
            cursor.mkdir()
    return root / safe


def _markers(host: str) -> tuple[str, str]:
    return (
        f"<!-- tailtrail-official-aidlc:{host}:start -->",
        f"<!-- tailtrail-official-aidlc:{host}:end -->",
    )


def _atomic_text(path: Path, content: str) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with tempfile.NamedTemporaryFile("w", encoding="utf-8", delete=False, dir=path.parent, newline="") as handle:
        handle.write(content)
        handle.flush()
        os.fsync(handle.fileno())
        temporary = Path(handle.name)
    try:
        os.replace(temporary, path)
    finally:
        if temporary.exists():
            temporary.unlink()


def _atomic_json(path: Path, payload: dict[str, Any]) -> None:
    _atomic_text(path, json.dumps(payload, indent=2, sort_keys=True) + "\n")


def _replace_managed_block(content: str, block: str, host: str = "codex") -> str:
    start, end = _markers(host)
    has_start, has_end = start in content, end in content
    if has_start != has_end:
        raise ValueError(f"{HOSTS[host]['instruction']} has an incomplete TailTrail official AI-DLC managed block")
    if has_start:
        before, after = content.split(start, 1)
        _, suffix = after.split(end, 1)
        return before.rstrip() + "\n\n" + block + suffix.lstrip("\r\n")
    return content.rstrip() + "\n\n" + block


def _legacy_block(manifest: dict[str, Any]) -> str:
    official = manifest["official"]
    return "\n".join((
        START,
        "## Official AI-DLC Standard/Full bridge (TailTrail managed)",
        "",
        "This project has a pinned, integrity-verified official AI-DLC pack.",
        "Apply it only for an explicit approved TailTrail `--aidlc standard` or `--aidlc full` run.",
        f"- Source: `{official['source']}`",
        f"- Revision: `{official['revision']}`",
        f"- Exact core rule: `{PROJECTED_CORE.as_posix()}`",
        f"- Rule details root: `{PROJECTED_DETAILS.as_posix()}`",
        END,
    )) + "\n"


def _copy_projection(root: Path) -> list[str]:
    source_core, source_details = root / CORE, root / DETAILS
    target_core, target_details = root / PROJECTED_CORE, root / PROJECTED_DETAILS
    if target_core.exists() or target_details.exists():
        raise ValueError("official AI-DLC host projection already exists; validate it or remove it explicitly before reinstalling")
    target_core.parent.mkdir(parents=True, exist_ok=True)
    shutil.copy2(source_core, target_core)
    shutil.copytree(source_details, target_details)
    return [PROJECTED_CORE.as_posix(), PROJECTED_DETAILS.as_posix()]


def _manifest(root: Path) -> dict[str, Any]:
    result = DETECT.status(root)
    if result.get("state") != "compatible":
        raise ValueError("a compatible pinned official AI-DLC pack is required; run `tailtrail aidlc official status --root .` first")
    return json.loads((root / str(result["manifest"])).read_text(encoding="utf-8"))


def _legacy_install(root: Path, host: str) -> dict[str, Any]:
    if host != "codex":
        raise ValueError("legacy host projection supports Codex only; bundled-v2 Copilot and Claude projections require --run-id")
    manifest = _manifest(root)
    agents = root / "AGENTS.md"
    if not agents.is_file() or agents.is_symlink():
        raise ValueError("Codex host projection requires a safe existing AGENTS.md")
    original = agents.read_text(encoding="utf-8")
    if START in original:
        return _legacy_status(root, host)
    projected = _copy_projection(root)
    _atomic_text(agents, _replace_managed_block(original, _legacy_block(manifest)))
    return {**_legacy_status(root, host), "state": "installed", "projected": projected}


def _legacy_status(root: Path, host: str) -> dict[str, Any]:
    compatibility = DETECT.status(root)
    agents = root / "AGENTS.md"
    core, details = root / PROJECTED_CORE, root / PROJECTED_DETAILS
    text = agents.read_text(encoding="utf-8") if agents.is_file() and not agents.is_symlink() else ""
    block_present = START in text and END in text
    source_core = root / CORE
    projection_matches = core.is_file() and source_core.is_file() and _digest(core) == _digest(source_core)
    details_present = details.is_dir() and not details.is_symlink()
    state = "installed" if compatibility.get("state") == "compatible" and block_present and projection_matches and details_present else "not-installed"
    return {
        "type": "tailtrail-official-aidlc-host-projection",
        "schema_version": "1",
        "host": host,
        "state": state,
        "compatible_pack": compatibility.get("state") == "compatible",
        "managed_block": block_present,
        "projected_core": PROJECTED_CORE.as_posix(),
        "projected_core_matches_pinned_pack": projection_matches,
        "projected_rule_details": PROJECTED_DETAILS.as_posix(),
        "projected_rule_details_present": details_present,
        "boundary": "Bounded legacy Codex compatibility only; bundled-v2 host conformance requires a frozen run binding.",
    }


def _receipt_path(root: Path, run_id: str, host: str) -> Path:
    run_key = hashlib.sha256(run_id.encode("utf-8")).hexdigest()
    return _managed_path(root, f".tailtrail/official-aidlc/host-projections/{run_key}/{host}/receipt.json")


def _read_json(path: Path, label: str) -> dict[str, Any]:
    if path.is_symlink() or not path.is_file():
        raise ValueError(f"{label} is missing, unsafe, or not a regular file: {path}")
    try:
        value = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, UnicodeError, json.JSONDecodeError) as error:
        raise ValueError(f"{label} is unreadable: {error}") from error
    if not isinstance(value, dict):
        raise ValueError(f"{label} must contain a JSON object")
    return value


def _frozen_identity(root: Path, run_id: str) -> dict[str, Any]:
    binding = aidlc_bundle.resolve_bound_run(root, run_id)
    if binding.get("state") != "ready" or binding.get("selector_consulted") is not False or binding.get("network_used") is not False:
        issues = "; ".join(str(row.get("detail")) for row in binding.get("issues", []) if isinstance(row, dict))
        raise ValueError("host projection requires one ready frozen bundled-v2 run binding" + (f": {issues}" if issues else ""))
    pack_path = _safe_relative(binding.get("pack_path"))
    pack = root / pack_path
    projection = _read_json(pack / "projection-receipt.json", "project projection receipt")
    if projection.get("projection_fingerprint") != binding.get("projection_fingerprint"):
        raise ValueError("frozen run binding and project projection fingerprints disagree")
    rows = projection.get("inventory")
    if not isinstance(rows, list) or not rows:
        raise ValueError("project projection has no complete inventory")
    inventory: dict[str, str] = {}
    for row in rows:
        if not isinstance(row, dict):
            raise ValueError("project projection inventory is malformed")
        relative = _safe_relative(row.get("path"))
        digest = row.get("sha256")
        if not isinstance(digest, str) or len(digest) != 64 or any(character not in "0123456789abcdef" for character in digest) or relative in inventory:
            raise ValueError("project projection inventory is malformed or duplicated")
        inventory[relative] = digest
    required = ("source_manifest_fingerprint", "official_source", "official_revision", "official_commit", "trust_posture", "pack_fingerprint")
    if any(not isinstance(projection.get(field), str) or not projection[field] for field in required):
        raise ValueError("project projection identity is incomplete")
    return {"binding": binding, "projection": projection, "pack": pack, "pack_path": pack_path, "inventory": inventory}


def _host_block(host: str, run_id: str, identity: dict[str, Any], projection_root: str) -> str:
    projection = identity["projection"]
    start, end = _markers(host)
    core = f"{projection_root}/aws-aidlc-rules/core-workflow.md"
    details = f"{projection_root}/aws-aidlc-rule-details"
    return "\n".join((
        start,
        "## Official AI-DLC Full bridge (TailTrail managed)",
        "",
        "Use this exact immutable official pack only for the named active TailTrail Full run.",
        "Do not download, substitute, rediscover, or silently downgrade these rules.",
        f"- Frozen run: `{run_id}`",
        f"- Official source: `{projection['official_source']}`",
        f"- Official revision: `{projection['official_revision']}`",
        f"- Official commit: `{projection['official_commit']}`",
        f"- Project pack: `{identity['pack_path']}`",
        f"- Project projection: `{projection['projection_fingerprint']}`",
        f"- Exact core rule: `{core}`",
        f"- Rule details root: `{details}`",
        "",
        "Read the exact core rule, active stage rules, and saved Question Orchestrator context.",
        "TailTrail retains approval, scope, evidence, drift, recovery, and closure authority.",
        end,
    )) + "\n"


def _expected_mappings(identity: dict[str, Any], projection_root: str) -> list[dict[str, str]]:
    pack_path = identity["pack_path"]
    copied = projection_root != pack_path
    return [
        {
            "source_path": f"{pack_path}/{path}",
            "destination_path": f"{projection_root}/{path}" if copied else f"{pack_path}/{path}",
            "source_sha256": digest,
            "destination_sha256": digest,
        }
        for path, digest in sorted(identity["inventory"].items())
    ]


def _copy_inventory(root: Path, identity: dict[str, Any], projection_root: str) -> Path:
    destination = _managed_path(root, projection_root, create_parents=True)
    if destination.exists() or destination.is_symlink():
        raise ValueError("Codex projection destination already exists without a matching immutable host receipt")
    destination.parent.mkdir(parents=True, exist_ok=True)
    staging = destination.parent / f".tailtrail-aidlc-staging-{uuid.uuid4().hex}"
    staging.mkdir()
    try:
        for relative, digest in sorted(identity["inventory"].items()):
            source = identity["pack"] / relative
            if source.is_symlink() or not source.is_file() or _digest(source) != digest:
                raise ValueError(f"frozen project pack changed before host projection: {relative}")
            target = staging / relative
            target.parent.mkdir(parents=True, exist_ok=True)
            shutil.copy2(source, target)
            if _digest(target) != digest:
                raise ValueError(f"copied host projection failed verification: {relative}")
        os.replace(staging, destination)
        return destination
    finally:
        if staging.exists() and not staging.is_symlink():
            shutil.rmtree(staging)


def _receipt_payload(host: str, run_id: str, identity: dict[str, Any], instruction_block: str) -> dict[str, Any]:
    config = HOSTS[host]
    projection = identity["projection"]
    projection_root = str(config.get("projection_root") or identity["pack_path"])
    core = {
        "schema_version": "1",
        "type": "tailtrail-official-aidlc-host-projection-receipt",
        "created_at": datetime.now(timezone.utc).isoformat(),
        "run_id": run_id,
        "host": {"identity": host, "adapter_name": "tailtrail-official-aidlc-host", "adapter_version": ADAPTER_VERSION},
        "projection_mode": config["mode"],
        "origin": {
            "run_resolution_fingerprint": identity["binding"]["binding_fingerprint"],
            "project_projection_fingerprint": projection["projection_fingerprint"],
            "project_pack_fingerprint": projection["pack_fingerprint"],
            "bundle_manifest_fingerprint": projection["source_manifest_fingerprint"],
        },
        "official_identity": {"source": projection["official_source"], "revision": projection["official_revision"], "commit": projection["official_commit"]},
        "trust_posture": projection["trust_posture"],
        "projection_root": projection_root,
        "mappings": _expected_mappings(identity, projection_root),
        "instruction_block": {"path": config["instruction"], "fingerprint": "sha256:" + hashlib.sha256(instruction_block.encode("utf-8")).hexdigest()},
        "reload_posture": config["reload"],
        "qualification": {"state": "qualified", "checks": ["frozen-run-binding", "complete-inventory", "instruction-block", "offline-boundary"]},
        "boundary": "One immutable offline host projection. Host-specific layout does not change official or project-pack identity.",
    }
    core["receipt_id"] = "host-projection-" + hashlib.sha256(_canonical(core)).hexdigest()[:16]
    return {**core, "receipt_fingerprint": _fingerprint(core)}


def _receipt_valid(receipt: dict[str, Any]) -> bool:
    sealed = dict(receipt)
    fingerprint = sealed.pop("receipt_fingerprint", None)
    return isinstance(fingerprint, str) and fingerprint == _fingerprint(sealed)


def _inventory_issues(root: Path, projection_root: str, expected: dict[str, str]) -> list[str]:
    base = root / projection_root
    if base.is_symlink() or not base.is_dir():
        return [f"copied projection root is missing or unsafe: {projection_root}"]
    actual: dict[str, str] = {}
    issues: list[str] = []
    for path in sorted(base.rglob("*")):
        relative = path.relative_to(base).as_posix()
        if path.is_symlink():
            issues.append(f"copied projection contains a symbolic link: {relative}")
        elif path.is_dir():
            continue
        elif not path.is_file():
            issues.append(f"copied projection contains a non-regular file: {relative}")
        else:
            actual[relative] = _digest(path)
    for path in sorted(set(expected) - set(actual)):
        issues.append(f"copied projection file is missing: {path}")
    for path in sorted(set(actual) - set(expected)):
        issues.append(f"copied projection has an additional file: {path}")
    for path in sorted(set(actual) & set(expected)):
        if actual[path] != expected[path]:
            issues.append(f"copied projection hash mismatch: {path}")
    return issues


def _instruction_issues(root: Path, host: str, expected_block: str) -> list[str]:
    try:
        path = _managed_path(root, HOSTS[host]["instruction"])
    except ValueError as error:
        return [str(error)]
    if path.is_symlink() or not path.is_file():
        return [f"host instruction file is missing or unsafe: {HOSTS[host]['instruction']}"]
    content = path.read_text(encoding="utf-8")
    start, end = _markers(host)
    if content.count(start) != 1 or content.count(end) != 1:
        return ["host instruction block is missing, duplicated, or incomplete"]
    actual = start + content.split(start, 1)[1].split(end, 1)[0] + end + "\n"
    return [] if actual == expected_block else ["host instruction block differs from the frozen projection receipt"]


def conformance(root: Path, host: str, run_id: str) -> dict[str, Any]:
    root = _safe_root(root)
    if host not in HOSTS:
        raise ValueError(f"unsupported host: {host}")
    try:
        identity = _frozen_identity(root, run_id)
        config = HOSTS[host]
        projection_root = str(config.get("projection_root") or identity["pack_path"])
        expected_block = _host_block(host, run_id, identity, projection_root)
        receipt_path = _receipt_path(root, run_id, host)
        if not receipt_path.exists():
            return {"schema_version": "1", "type": "tailtrail-official-aidlc-host-conformance", "host": host, "run_id": run_id, "state": "not-installed", "projection_mode": config["mode"], "network_used": False, "issues": ["host projection receipt is missing"]}
        receipt = _read_json(receipt_path, "host projection receipt")
        expected_origin = {
            "run_resolution_fingerprint": identity["binding"]["binding_fingerprint"],
            "project_projection_fingerprint": identity["projection"]["projection_fingerprint"],
            "project_pack_fingerprint": identity["projection"]["pack_fingerprint"],
            "bundle_manifest_fingerprint": identity["projection"]["source_manifest_fingerprint"],
        }
        issues: list[str] = []
        if not _receipt_valid(receipt):
            issues.append("host projection receipt failed its integrity seal")
        if receipt.get("run_id") != run_id or (receipt.get("host") or {}).get("identity") != host:
            issues.append("host projection receipt identity does not match the request")
        if receipt.get("projection_mode") != config["mode"] or receipt.get("origin") != expected_origin:
            issues.append("host projection receipt mode or frozen origin does not match")
        if receipt.get("projection_root") != projection_root or receipt.get("mappings") != _expected_mappings(identity, projection_root):
            issues.append("host projection receipt inventory mapping is incomplete or altered")
        issues.extend(_instruction_issues(root, host, expected_block))
        if config["mode"] == "copy":
            issues.extend(_inventory_issues(root, projection_root, identity["inventory"]))
        else:
            for relative, digest in sorted(identity["inventory"].items()):
                source = identity["pack"] / relative
                if source.is_symlink() or not source.is_file() or _digest(source) != digest:
                    issues.append(f"referenced project-pack file is missing, unsafe, or altered: {relative}")
        return {
            "schema_version": "1",
            "type": "tailtrail-official-aidlc-host-conformance",
            "host": host,
            "run_id": run_id,
            "state": "installed" if not issues else "blocked",
            "projection_mode": config["mode"],
            "network_used": False,
            "official_identity": receipt.get("official_identity"),
            "origin": receipt.get("origin"),
            "trust_posture": receipt.get("trust_posture"),
            "projection_root": projection_root,
            "receipt": receipt_path.relative_to(root).as_posix(),
            "receipt_fingerprint": receipt.get("receipt_fingerprint"),
            "reload_posture": receipt.get("reload_posture"),
            "qualification": "qualified" if not issues else "blocked",
            "issues": issues,
            "boundary": "Read-only complete host conformance; no provisioning, repair, selector lookup, or network operation was performed.",
        }
    except (OSError, UnicodeError, ValueError, json.JSONDecodeError) as error:
        return {"schema_version": "1", "type": "tailtrail-official-aidlc-host-conformance", "host": host, "run_id": run_id, "state": "blocked", "projection_mode": HOSTS[host]["mode"], "network_used": False, "issues": [str(error)], "boundary": "Read-only conformance failed closed without changing project state."}


def project(root: Path, host: str, run_id: str) -> dict[str, Any]:
    root = _safe_root(root)
    if host not in HOSTS:
        raise ValueError(f"unsupported host: {host}")
    identity = _frozen_identity(root, run_id)
    config = HOSTS[host]
    projection_root = str(config.get("projection_root") or identity["pack_path"])
    instruction = _managed_path(root, config["instruction"])
    if instruction.is_symlink() or not instruction.is_file():
        raise ValueError(f"{host} host projection requires a safe existing {config['instruction']}")
    receipt_path = _receipt_path(root, run_id, host)
    if receipt_path.exists():
        result = conformance(root, host, run_id)
        if result.get("state") != "installed":
            raise ValueError("existing host projection is not conformant; explicit repair is required")
        return {**result, "status": "reused"}
    original = instruction.read_text(encoding="utf-8")
    block = _host_block(host, run_id, identity, projection_root)
    updated = _replace_managed_block(original, block, host)
    created_copy: Path | None = None
    instruction_changed = False
    try:
        if config["mode"] == "copy":
            created_copy = _copy_inventory(root, identity, projection_root)
        _atomic_text(instruction, updated)
        instruction_changed = updated != original
        receipt = _receipt_payload(host, run_id, identity, block)
        _managed_path(root, receipt_path.relative_to(root).as_posix(), create_parents=True)
        _atomic_json(receipt_path, receipt)
        result = conformance(root, host, run_id)
        if result.get("state") != "installed":
            raise ValueError("new host projection failed complete conformance: " + "; ".join(result.get("issues", [])))
        return {**result, "status": "created"}
    except Exception:
        if receipt_path.exists() and not receipt_path.is_symlink():
            receipt_path.unlink()
        if instruction_changed:
            _atomic_text(instruction, original)
        if created_copy is not None and created_copy.exists() and not created_copy.is_symlink():
            shutil.rmtree(created_copy)
        raise


def install(root: Path, host: str = "codex", run_id: str | None = None) -> dict[str, Any]:
    root = _safe_root(root)
    return project(root, host, run_id) if run_id else _legacy_install(root, host)


def status(root: Path, host: str = "codex", run_id: str | None = None) -> dict[str, Any]:
    root = _safe_root(root)
    return conformance(root, host, run_id) if run_id else _legacy_status(root, host)


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    sub = parser.add_subparsers(dest="action", required=True)
    for action in ("install", "status"):
        command = sub.add_parser(action)
        command.add_argument("--root", type=Path, default=Path.cwd())
        command.add_argument("--host", choices=tuple(HOSTS), default="codex")
        command.add_argument("--run-id")
    args = parser.parse_args()
    try:
        result = install(args.root, args.host, args.run_id) if args.action == "install" else status(args.root, args.host, args.run_id)
    except (OSError, ValueError, json.JSONDecodeError) as error:
        print(f"Official AI-DLC host projection error: {error}")
        return 2
    print(json.dumps(result, indent=2, sort_keys=True))
    return 0 if result["state"] == "installed" else 1


if __name__ == "__main__":
    raise SystemExit(main())
