"""Closed, package-owned host adapter contract loader."""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any


HOSTS = ("codex", "copilot", "claude")
PRECEDENCE = ["host safety", "user request", "official stage rules", "tailtrail assurance rules"]


def package_root() -> Path:
    root = Path(__file__).resolve().parents[1]
    return root if (root / "package-manifest.json").is_file() else root.parent


def contracts(root: Path | None = None) -> dict[str, Any]:
    base = (root or package_root()).resolve()
    payload = json.loads((base / "adapters" / "host-compatibility-v1.json").read_text(encoding="utf-8"))
    if payload.get("schema_version") != "1" or payload.get("type") != "tailtrail-host-adapter-compatibility":
        raise ValueError("host adapter contract is incompatible")
    if payload.get("adapter_version") != "v3" or payload.get("precedence") != PRECEDENCE:
        raise ValueError("host adapter version or precedence is incompatible")
    entries = payload.get("hosts")
    if not isinstance(entries, list) or tuple(item.get("id") for item in entries if isinstance(item, dict)) != HOSTS:
        raise ValueError("host adapter contract must define codex, copilot, and claude exactly once")
    for entry in entries:
        _validate_entry(entry)
    return payload


def _safe_path(value: object, field: str) -> str:
    if not isinstance(value, str):
        raise ValueError(f"{field} must be a relative path")
    path = Path(value)
    if path.is_absolute() or not path.parts or any(part in {"", ".", ".."} for part in path.parts):
        raise ValueError(f"{field} must be a safe relative path")
    return path.as_posix()


def _validate_entry(entry: dict[str, Any]) -> None:
    host = entry.get("id")
    if host not in HOSTS or entry.get("owner") != "tailtrail-hosts":
        raise ValueError("host adapter identity or owner is invalid")
    if entry.get("qualification") not in {"instruction-compatible", "contract-tested", "runtime-observed", "supported", "unknown", "not-validated"}:
        raise ValueError(f"{host}: invalid qualification")
    if entry.get("supported") is not False:
        raise ValueError(f"{host}: E4 contract cannot claim release support")
    files = entry.get("core_files")
    if not isinstance(files, list) or not files:
        raise ValueError(f"{host}: core_files must be non-empty")
    destinations: set[str] = set()
    for item in files:
        if not isinstance(item, dict) or set(item) != {"source", "destination"}:
            raise ValueError(f"{host}: invalid core file entry")
        _safe_path(item["source"], f"{host}.source")
        destination = _safe_path(item["destination"], f"{host}.destination")
        if destination in destinations:
            raise ValueError(f"{host}: duplicate destination {destination}")
        destinations.add(destination)
    markers = entry.get("composition_markers")
    if not isinstance(markers, dict) or not markers or not set(markers).issubset(destinations):
        raise ValueError(f"{host}: composition markers must target Core files")
    for path, values in markers.items():
        _safe_path(path, f"{host}.composition_markers")
        if not isinstance(values, list) or not values or not all(isinstance(value, str) and value for value in values):
            raise ValueError(f"{host}: composition markers must be non-empty strings")
    action = entry.get("first_action")
    if not isinstance(action, dict) or set(action) != {"surface", "invocation", "result"} or not all(isinstance(value, str) and value for value in action.values()):
        raise ValueError(f"{host}: first action is invalid")
    detection = entry.get("version_detection")
    if not isinstance(detection, dict) or detection.get("kind") not in {"command", "host-reported"}:
        raise ValueError(f"{host}: version detection is invalid")
    command = detection.get("command")
    if detection["kind"] == "command" and (not isinstance(command, list) or not command):
        raise ValueError(f"{host}: command version detection needs a command")
    if detection["kind"] == "host-reported" and command != []:
        raise ValueError(f"{host}: host-reported version detection must not execute a command")
    capabilities = entry.get("capabilities")
    if not isinstance(capabilities, dict) or any(capabilities.get(name) != "approval-required" for name in ("global_settings", "network_activity", "account_changes")):
        raise ValueError(f"{host}: external changes must remain approval-required")
    migration = entry.get("migration")
    if not isinstance(migration, dict) or migration.get("strategy") != "transactional-replace-owned-files" or migration.get("rollback") != "E3 transaction backup":
        raise ValueError(f"{host}: migration must use the E3 transaction lifecycle")


def adapter_version(root: Path | None = None) -> str:
    return str(contracts(root)["adapter_version"])


def contract(host: str, root: Path | None = None) -> dict[str, Any]:
    if host not in HOSTS:
        raise ValueError(f"unsupported host: {host}")
    return next(item for item in contracts(root)["hosts"] if item["id"] == host)


def core_files(host: str, root: Path | None = None) -> tuple[tuple[str, str], ...]:
    entry = contract(host, root)
    return tuple((str(item["source"]), str(item["destination"])) for item in entry["core_files"])


def first_action(host: str, root: Path | None = None) -> dict[str, str]:
    return dict(contract(host, root)["first_action"])
