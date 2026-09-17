"""Make the installed `tailtrail` command resolvable without manual PATH edits.

A virtualenv install is only reachable by full path until its Scripts/bin
directory is on PATH. Every manual install hits this, so the install flow
registers it: `shutil.which` check first, Windows registry update
(HKCU Environment, no admin needed) with a restart notice, and a shell
hint on other platforms. `--no-path-register` opts out.
"""

from __future__ import annotations

import os
import shutil
import sys
from pathlib import Path
from typing import Any


def scripts_dir_for(executable: str | None = None) -> Path:
    """Directory holding the current interpreter's installed commands."""
    return Path(executable or sys.executable).resolve().parent


def command_resolvable(name: str = "tailtrail") -> bool:
    """True when the command resolves on PATH already."""
    return shutil.which(name) is not None


def new_path_value(current: str, entry: str) -> str | None:
    """Append entry to a PATH string, or None when already present.

    Comparison is case-insensitive on Windows, where the registry
    preserves the existing casing.
    """
    parts = [item for item in current.split(os.pathsep) if item]
    lowered = entry.replace("/", "\\").lower() if os.name == "nt" else entry
    for item in parts:
        candidate = item.replace("/", "\\").lower() if os.name == "nt" else item
        if candidate == lowered or candidate.rstrip("\\/") == lowered.rstrip("\\/"):
            return None
    return current + (os.pathsep if current and not current.endswith(os.pathsep) else "") + entry


def register_user_path_windows(entry: str) -> bool:
    """Append entry to the HKCU user PATH. Returns True when changed."""
    import winreg

    with winreg.OpenKey(winreg.HKEY_CURRENT_USER, "Environment", 0, winreg.KEY_READ) as key:
        try:
            current, _ = winreg.QueryValueEx(key, "Path")
        except FileNotFoundError:
            current = ""
    updated = new_path_value(str(current), entry)
    if updated is None:
        return False
    with winreg.OpenKey(winreg.HKEY_CURRENT_USER, "Environment", 0, winreg.KEY_SET_VALUE) as key:
        winreg.SetValueEx(key, "Path", 0, winreg.REG_EXPAND_SZ, updated)
    _broadcast_setting_change()
    return True


def _broadcast_setting_change() -> None:
    """Best-effort: tell new processes the environment changed."""
    try:
        import ctypes

        HWND_BROADCAST = 0xFFFF
        WM_SETTINGCHANGE = 0x001A
        SMTO_ABORTIFHUNG = 0x0002
        ctypes.windll.user32.SendMessageTimeoutW(
            HWND_BROADCAST, WM_SETTINGCHANGE, 0, "Environment", SMTO_ABORTIFHUNG, 5000, None
        )
    except Exception:
        pass


def ensure_command_on_path(entry: str | None = None) -> dict[str, Any]:
    """Register the interpreter's Scripts dir so `tailtrail` resolves.

    Never raises: failures are reported in the returned dict.
    """
    if command_resolvable():
        return {"status": "already", "entry": None, "restart_required": False, "error": None}
    scripts_dir = Path(entry) if entry else scripts_dir_for()
    if os.name == "nt":
        try:
            changed = register_user_path_windows(str(scripts_dir))
        except OSError as error:
            return {"status": "failed", "entry": str(scripts_dir),
                    "restart_required": False, "error": str(error)}
        return {"status": "added" if changed else "already",
                "entry": str(scripts_dir), "restart_required": True, "error": None}
    return {"status": "manual", "entry": scripts_dir.as_posix(), "restart_required": False,
            "error": f"add {scripts_dir.as_posix()} to PATH in your shell profile"}


def render_notice(result: dict[str, Any]) -> str:
    status = result.get("status")
    if status == "already":
        return "Command check: `tailtrail` already resolves on PATH."
    if status == "added":
        return (
            f"Command check: added `{result['entry']}` to your user PATH.\n"
            "Restart terminals and IDEs (PATH reloads per process), then run "
            "`where.exe tailtrail` to verify."
        )
    if status == "manual":
        return f"Command check: {result['error']}"
    return f"Command check: PATH registration failed: {result['error']}"
