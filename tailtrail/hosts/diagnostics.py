"""Host-aware installed-product diagnostics with truthful qualification states."""

from __future__ import annotations

import shutil
import subprocess
from pathlib import Path
from typing import Any, Callable, Sequence

from .contracts import adapter_version, contract


Runner = Callable[[Sequence[str]], tuple[int, str]]


def _run(command: Sequence[str]) -> tuple[int, str]:
    executable = shutil.which(command[0])
    if executable is None:
        return 127, ""
    result = subprocess.run([executable, *command[1:]], text=True, capture_output=True, check=False, timeout=5)
    return result.returncode, (result.stdout or result.stderr).strip().splitlines()[0] if (result.stdout or result.stderr).strip() else ""


def detect_version(host: str, *, root: Path | None = None, runner: Runner | None = None) -> dict[str, Any]:
    detection = contract(host, root)["version_detection"]
    if detection["kind"] == "host-reported":
        return {"state": "host-reported-required", "version": None, "method": "host-reported", "qualified": False, "limitation": detection["limitation"]}
    command = tuple(detection["command"])
    code, output = (runner or _run)(command)
    return {
        "state": "detected" if code == 0 and output else "not-detected",
        "version": output or None,
        "method": "command",
        "command": list(command),
        "qualified": bool(output and output in detection["qualified_versions"]),
        "limitation": detection["limitation"],
    }


def diagnose(target: Path, host: str, *, manifest: dict[str, Any] | None, root: Path | None = None, runner: Runner | None = None) -> dict[str, Any]:
    target = target.resolve()
    entry = contract(host, root)
    required = [item["destination"] for item in entry["core_files"]]
    missing = [relative for relative in required if not (target / relative).is_file()]
    marker_failures: list[str] = []
    for relative, markers in entry["composition_markers"].items():
        path = target / relative
        if not path.is_file():
            continue
        body = path.read_text(encoding="utf-8")
        marker_failures.extend(f"{relative}: missing composition marker `{marker}`" for marker in markers if marker not in body)
    manifest_files = set((manifest or {}).get("files", {})) if isinstance((manifest or {}).get("files", {}), dict) else set()
    unexpected_core = sorted(manifest_files - set(required)) if (manifest or {}).get("profile") == "core" else []
    manifest_adapter = (manifest or {}).get("adapter_version")
    current_adapter = adapter_version(root)
    issues = [*(f"missing required host file: {item}" for item in missing), *marker_failures]
    if manifest is not None and manifest_adapter != current_adapter:
        issues.append(f"adapter contract mismatch: installed {manifest_adapter or 'unrecorded'}, current {current_adapter}")
    if unexpected_core:
        issues.append("Core manifest contains undeclared host files: " + ", ".join(unexpected_core))
    return {
        "schema_version": "1",
        "type": "tailtrail-host-diagnostic",
        "host": host,
        "adapter_version": current_adapter,
        "qualification": entry["qualification"],
        "supported": False,
        "installation": "passed" if manifest is not None and not issues else ("not-installed" if manifest is None else "failed"),
        "required_files": required,
        "missing_files": missing,
        "composition": "passed" if not marker_failures else "failed",
        "issues": issues,
        "first_action": dict(entry["first_action"]),
        "reload": dict(entry["reload"]),
        "version_detection": detect_version(host, root=root, runner=runner),
        "capabilities": dict(entry["capabilities"]),
        "runtime_status": entry["runtime_status"],
        "receipt_preparation": f"tailtrail adapters runtime prepare --host {host} --root {target.as_posix()}",
        "boundary": "Contract-tested is local evidence only. Runtime-observed requires six fresh host receipts; supported additionally requires E5 and E10 release gates.",
    }
