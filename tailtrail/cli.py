"""Stable installed TailTrail console entry point."""

from __future__ import annotations

import json
import os
import sys
from contextlib import redirect_stdout
from io import StringIO
from pathlib import Path
from typing import Sequence

from .api import ExitCode, package_status
from .errors import PackageResourceError, TailTrailError, UnsupportedPythonError
from .kernel import prepare_dispatch, python_compatibility


def _json_requested(args: Sequence[str]) -> bool:
    return "--json" in args or "--format=json" in args or any(
        value == "--format" and index + 1 < len(args) and args[index + 1] == "json"
        for index, value in enumerate(args)
    )


def _emit_error(error: TailTrailError, json_output: bool) -> int:
    code = ExitCode.UNAVAILABLE if isinstance(error, (PackageResourceError, UnsupportedPythonError)) else ExitCode.INTERNAL_ERROR
    if json_output:
        print(json.dumps({"type": "tailtrail-error", "error": error.__class__.__name__, "message": str(error), "exit_code": int(code)}, sort_keys=True))
    else:
        print(f"TailTrail unavailable: {error}", file=sys.stderr)
    return int(code)


def _dispatch(dispatcher: object, args: list[str], json_output: bool) -> int:
    previous = sys.argv
    previous_capture = os.environ.get("TAILTRAIL_JSON_ENVELOPE_CAPTURE")
    sys.argv = [(getattr(dispatcher, "__file__", None) or "tailtrail"), *args]
    try:
        if not json_output:
            return int(dispatcher.main())  # type: ignore[attr-defined]
        output = StringIO()
        os.environ["TAILTRAIL_JSON_ENVELOPE_CAPTURE"] = "1"
        with redirect_stdout(output):
            code = int(dispatcher.main())  # type: ignore[attr-defined]
        text = output.getvalue().strip()
        try:
            json.loads(text)
        except json.JSONDecodeError:
            print(json.dumps({"type": "tailtrail-command-result", "ok": code == 0, "exit_code": code, "output": text}, sort_keys=True))
        else:
            print(text)
        return code
    finally:
        sys.argv = previous
        if previous_capture is None:
            os.environ.pop("TAILTRAIL_JSON_ENVELOPE_CAPTURE", None)
        else:
            os.environ["TAILTRAIL_JSON_ENVELOPE_CAPTURE"] = previous_capture


def _package_command(args: list[str], json_output: bool, runtime_root: Path) -> int | None:
    from . import __version__

    command = args[0] if args else ""
    if command in {"--version", "version"}:
        supported, compatibility = python_compatibility()
        payload = {"type": "tailtrail-version", "version": __version__, "python_supported": supported, "compatibility": compatibility}
        print(json.dumps(payload, sort_keys=True) if json_output else f"TailTrail {__version__}")
        return int(ExitCode.OK)
    if command == "package-info":
        if runtime_root == Path(__file__).resolve().parent:
            status = package_status()
            payload = {"type": "tailtrail-package-status", "version": status.version, "mode": "installed-package", "root": status.root.as_posix(), "valid": status.valid, "issues": list(status.issues)}
        else:
            valid = (runtime_root / "package-manifest.json").is_file()
            payload = {"type": "tailtrail-package-status", "version": __version__, "mode": "source-compatibility", "root": runtime_root.as_posix(), "valid": valid, "issues": [] if valid else ["missing source package manifest"]}
        if json_output:
            print(json.dumps(payload, sort_keys=True))
        else:
            print(f"TailTrail package {'passed' if payload['valid'] else 'failed'}.")
            print(f"Version: {payload['version']}")
            print(f"Mode: {payload['mode']}")
            print(f"Package root: {payload['root']}")
            for issue in payload["issues"]:
                print(f"- {issue}")
        return int(ExitCode.OK if payload["valid"] else ExitCode.VALIDATION_FAILED)
    if command == "hello" and json_output:
        if runtime_root == Path(__file__).resolve().parent:
            status = package_status()
            valid, mode, issues = status.valid, "installed-package", list(status.issues)
        else:
            valid, mode, issues = (runtime_root / "package-manifest.json").is_file(), "source-compatibility", []
        print(json.dumps({"type": "tailtrail-hello", "version": __version__, "mode": mode, "installed": valid, "issues": issues}, sort_keys=True))
        return int(ExitCode.OK if valid else ExitCode.VALIDATION_FAILED)
    return None


def main(argv: Sequence[str] | None = None) -> int:
    args = list(sys.argv[1:] if argv is None else argv)
    json_output = _json_requested(args)
    try:
        root = prepare_dispatch()
        handled = _package_command(args, json_output, root)
        if handled is not None:
            return handled
        if root == Path(__file__).resolve().parent:
            from .scripts import tailtrail as dispatcher
        else:
            from scripts import tailtrail as dispatcher

        os.environ["TAILTRAIL_COMMAND_NAME"] = "tailtrail"
        return _dispatch(dispatcher, args, json_output)
    except TailTrailError as error:
        return _emit_error(error, json_output)


if __name__ == "__main__":
    raise SystemExit(main())
