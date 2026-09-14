#!/usr/bin/env python3
"""Centralized write-access enforcement for the Sequential Worker Pipeline."""
from __future__ import annotations

import os
import functools
from pathlib import Path
from typing import Any, Callable

import navigator_scope
from pipeline_manager import PipelineManager
from pipeline_judge import PipelineJudge

class SecurityBoundaryError(Exception):
    """Raised when a write attempt violates the active pipeline stage boundaries."""
    def __init__(self, message: str):
        super().__init__(message)
        self.message = message

class WriteGuardian:
    """Intercepts file writes to ensure they align with the active pipeline badge."""
    
    def __init__(self, root: Path, run_id: str | None = None):
        self.root = root.resolve()
        self.run_id = run_id or os.environ.get("TAILTRAIL_ACTIVE_RUN_ID")
        
        if not self.run_id:
            self.permissive_mode = True
        else:
            self.permissive_mode = False
            self.manager = PipelineManager(self.root, self.run_id)
            self.judge = PipelineJudge(self.root, self.run_id)

    def is_exempt(self, path: Path) -> bool:
        """Paths that are always writable regardless of the active stage."""
        try:
            relative = path.resolve().relative_to(self.root)
        except ValueError:
            return False
            
        rel_str = relative.as_posix()
        if rel_str.startswith(".tailtrail/") or rel_str.startswith("tailtrail-meta/"):
            return True
        return False

    def validate_write(self, path: Path | str) -> None:
        """
        Verify if the current active worker has permission to edit the given path.
        Raises SecurityBoundaryError if the write is prohibited.
        """
        if isinstance(path, str):
            path = Path(path)
        
        path = path.resolve()
        
        if self.is_exempt(path):
            return

        if self.permissive_mode:
            return

        try:
            relative_path = path.relative_to(self.root).as_posix()
        except ValueError:
            # If path is outside root, it's prohibited unless it's a known external target
            raise SecurityBoundaryError(f"Write access denied: Path `{path}` is outside the project root.")

        allowed, error = self.judge.validate_write_access(relative_path)
        if not allowed:
            raise SecurityBoundaryError(error)

def guarded_write(func: Callable):
    """Decorator to enforce pipeline boundaries on file-writing functions."""
    @functools.wraps(func)
    def wrapper(*args, **kwargs):
        # Attempt to find 'root' and 'path' in arguments
        root = None
        path = None
        
        # Check positional args
        for arg in args:
            if isinstance(arg, Path) and "root" in str(arg).lower(): # Simple heuristic
                root = arg
            if isinstance(arg, (Path, str)) and any(p in str(arg).lower() for p in ["path", "destination", "file"]):
                path = arg
        
        # Check keyword args
        root = kwargs.get("root") or kwargs.get("target_root")
        path = kwargs.get("path") or kwargs.get("destination") or kwargs.get("relative_path")
        
        # If we can't find root/path, we can't guard, so we let it pass (or log a warning)
        if not root or not path:
            return func(*args, **kwargs)
        
        # Ensure root is a Path
        if isinstance(root, str): root = Path(root)
        
        guardian = WriteGuardian(root)
        guardian.validate_write(path)
        
        return func(*args, **kwargs)
    return wrapper
