#!/usr/bin/env python3
"""Platform-aware shell quoting for TailTrail-suggested commands.

`shlex.quote` emits POSIX single-quote syntax, which `cmd.exe` and
PowerShell cannot parse. Any command string TailTrail shows a host for
copy-paste (intake continuations, corrective errors, proof commands) must
use `quote` instead: POSIX behavior on POSIX hosts, `list2cmdline`
quoting on Windows (`os.name == "nt"`, matching the installer convention).
"""

from __future__ import annotations

import os
import shlex
import subprocess


def quote(arg: str) -> str:
    """Quote one shell argument for the current platform's command parser."""
    if os.name == "nt":
        return subprocess.list2cmdline([arg])
    return shlex.quote(arg)
