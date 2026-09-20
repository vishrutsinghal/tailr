"""Platform-aware shell quoting for managed-command proof strings.

`shlex.quote` emits POSIX single-quote syntax, which `cmd.exe` cannot parse,
so tests that build proof commands with it fail on Windows with exit code 1
before the command runs. Use `quote` instead: POSIX behavior on POSIX hosts,
`subprocess.list2cmdline` quoting on Windows.
"""

from __future__ import annotations

import os
import shlex
import subprocess


def quote(arg: str) -> str:
    if os.name == "nt":
        return subprocess.list2cmdline([arg])
    return shlex.quote(arg)
