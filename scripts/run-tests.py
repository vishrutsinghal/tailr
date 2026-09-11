#!/usr/bin/env python3
"""Run Python unittest suites concurrently without adding a dependency.

The runner keeps repository-state observers in a serial preflight, then runs
each remaining test module in an isolated Python subprocess with a bounded
worker pool. This avoids sharing interpreter state and prevents package-build
tests from racing enterprise/readiness checks that inspect the worktree.
"""

from __future__ import annotations

import argparse
import concurrent.futures
import json
import os
import re
import subprocess
import sys
import threading
import time
from dataclasses import dataclass
from pathlib import Path
from typing import Iterable


DEFAULT_MAX_JOBS = 4
SUMMARY_PATTERN = re.compile(r"Ran (\d+) tests? in ([0-9.]+)s")
MODULE_NAME_PATTERN = re.compile(r"^[A-Za-z_][A-Za-z0-9_]*$")

# These modules inspect Git/untracked/package governance state. Run them before
# package tests can create a shared checkout-level build directory.
PREFLIGHT_BASENAMES = {
    "test_enterprise_readiness",
    "test_product_maintainability",
    "test_product_maturity",
    "test_registry_drift",
    "test_tailtrail_registry",
}

_ACTIVE_LOCK = threading.Lock()
_ACTIVE_PROCESSES: set[subprocess.Popen[str]] = set()


@dataclass(frozen=True)
class TestResult:
    label: str
    modules: tuple[str, ...]
    returncode: int
    tests: int
    reported_seconds: float
    elapsed_seconds: float
    stdout: str
    stderr: str
    timed_out: bool

    @property
    def passed(self) -> bool:
        return self.returncode == 0 and not self.timed_out

    def public(self, include_output: bool = False) -> dict[str, object]:
        row: dict[str, object] = {
            "label": self.label,
            "modules": list(self.modules),
            "status": "passed" if self.passed else "failed",
            "returncode": self.returncode,
            "tests": self.tests,
            "reported_seconds": round(self.reported_seconds, 3),
            "elapsed_seconds": round(self.elapsed_seconds, 3),
            "timed_out": self.timed_out,
        }
        if include_output or not self.passed:
            row["stdout"] = self.stdout
            row["stderr"] = self.stderr
        return row


def _module_for(root: Path, path: Path) -> str:
    relative = path.resolve().relative_to(root.resolve()).with_suffix("")
    if not all(MODULE_NAME_PATTERN.match(part) for part in relative.parts):
        raise ValueError(f"test path cannot be imported as a unittest module: {relative.as_posix()}")
    return ".".join(relative.parts)


def discover_modules(root: Path, start_directory: str, pattern: str) -> list[str]:
    start = (root / start_directory).resolve()
    try:
        start.relative_to(root.resolve())
    except ValueError as error:
        raise ValueError("start directory must remain inside the test root") from error
    if not start.is_dir():
        raise ValueError(f"test start directory does not exist: {start}")
    modules = [
        _module_for(root, path)
        for path in sorted(start.glob(pattern))
        if path.is_file()
    ]
    if not modules:
        raise ValueError(f"no tests matched {start_directory}/{pattern}")
    return modules


def _names(values: Iterable[str]) -> set[str]:
    names: set[str] = set()
    for raw in values:
        for value in raw.split(","):
            value = value.strip()
            if value:
                names.add(value)
    return names


def select_modules(modules: Iterable[str], includes: Iterable[str], excludes: Iterable[str]) -> list[str]:
    include = _names(includes)
    exclude = _names(excludes)

    def matches(module: str, values: set[str]) -> bool:
        basename = module.rsplit(".", 1)[-1]
        return module in values or basename in values

    selected = [
        module
        for module in modules
        if (not include or matches(module, include)) and not matches(module, exclude)
    ]
    if include:
        found = {
            value
            for value in include
            if any(value in {module, module.rsplit(".", 1)[-1]} for module in modules)
        }
        missing = sorted(include - found)
        if missing:
            raise ValueError("unknown included test module(s): " + ", ".join(missing))
    if not selected:
        raise ValueError("test selection is empty")
    return selected


def split_phases(modules: Iterable[str]) -> tuple[list[str], list[str]]:
    preflight: list[str] = []
    parallel: list[str] = []
    for module in modules:
        target = preflight if module.rsplit(".", 1)[-1] in PREFLIGHT_BASENAMES else parallel
        target.append(module)
    return preflight, parallel


def default_jobs() -> int:
    configured = os.environ.get("TAILTRAIL_TEST_JOBS", "").strip()
    if configured:
        try:
            jobs = int(configured)
        except ValueError as error:
            raise ValueError("TAILTRAIL_TEST_JOBS must be a positive integer") from error
        if jobs < 1:
            raise ValueError("TAILTRAIL_TEST_JOBS must be a positive integer")
        return jobs
    return max(1, min(DEFAULT_MAX_JOBS, os.cpu_count() or 1))


def _summary(stdout: str, stderr: str) -> tuple[int, float]:
    matches = SUMMARY_PATTERN.findall(stderr + "\n" + stdout)
    if not matches:
        return 0, 0.0
    tests, seconds = matches[-1]
    return int(tests), float(seconds)


def run_batch(
    root: Path,
    label: str,
    modules: Iterable[str],
    *,
    verbose: bool,
    timeout: float,
) -> TestResult:
    selected = tuple(modules)
    command = [sys.executable, "-m", "unittest"]
    if verbose:
        command.append("-v")
    command.extend(selected)
    environment = dict(os.environ)
    environment.setdefault("PYTHONHASHSEED", "0")
    started = time.monotonic()
    process = subprocess.Popen(
        command,
        cwd=root,
        env=environment,
        text=True,
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
    )
    with _ACTIVE_LOCK:
        _ACTIVE_PROCESSES.add(process)
    timed_out = False
    try:
        try:
            stdout, stderr = process.communicate(timeout=timeout if timeout > 0 else None)
        except subprocess.TimeoutExpired:
            timed_out = True
            process.kill()
            stdout, stderr = process.communicate()
    finally:
        with _ACTIVE_LOCK:
            _ACTIVE_PROCESSES.discard(process)
    elapsed = time.monotonic() - started
    tests, reported = _summary(stdout, stderr)
    return TestResult(
        label=label,
        modules=selected,
        returncode=124 if timed_out else int(process.returncode or 0),
        tests=tests,
        reported_seconds=reported,
        elapsed_seconds=elapsed,
        stdout=stdout,
        stderr=stderr,
        timed_out=timed_out,
    )


def terminate_active() -> None:
    with _ACTIVE_LOCK:
        processes = list(_ACTIVE_PROCESSES)
    for process in processes:
        try:
            process.terminate()
        except OSError:
            pass


def _failure_text(result: TestResult) -> str:
    parts = [
        f"\n--- FAILED: {result.label} ---",
        f"Modules: {', '.join(result.modules)}",
        f"Exit code: {result.returncode}" + (" (timeout)" if result.timed_out else ""),
    ]
    if result.stdout:
        parts.extend(["stdout:", result.stdout.rstrip()])
    if result.stderr:
        parts.extend(["stderr:", result.stderr.rstrip()])
    return "\n".join(parts)


def execute(
    root: Path,
    modules: list[str],
    *,
    jobs: int,
    serial: bool,
    verbose: bool,
    quiet: bool,
    timeout: float,
) -> tuple[list[TestResult], float]:
    started = time.monotonic()
    if serial or jobs == 1:
        result = run_batch(root, "serial-suite", modules, verbose=verbose, timeout=timeout)
        if not quiet and not result.passed:
            print(_failure_text(result))
        return [result], time.monotonic() - started

    preflight, parallel = split_phases(modules)
    results: list[TestResult] = []
    if preflight:
        result = run_batch(root, "repository-state-preflight", preflight, verbose=verbose, timeout=timeout)
        results.append(result)
        if not quiet:
            state = "PASS" if result.passed else "FAIL"
            print(f"[preflight] {state} {len(preflight)} modules / {result.tests} tests ({result.elapsed_seconds:.2f}s)", flush=True)
        if not result.passed:
            if not quiet:
                print(_failure_text(result))
            return results, time.monotonic() - started

    if not parallel:
        return results, time.monotonic() - started

    completed = 0
    worker_count = min(jobs, len(parallel))
    with concurrent.futures.ThreadPoolExecutor(max_workers=worker_count, thread_name_prefix="tailtrail-tests") as executor:
        futures = {
            executor.submit(run_batch, root, module, [module], verbose=verbose, timeout=timeout): module
            for module in parallel
        }
        try:
            for future in concurrent.futures.as_completed(futures):
                result = future.result()
                results.append(result)
                completed += 1
                if not quiet:
                    state = "PASS" if result.passed else "FAIL"
                    print(
                        f"[{completed}/{len(parallel)}] {state} {result.label} "
                        f"({result.tests} tests, {result.elapsed_seconds:.2f}s)",
                        flush=True,
                    )
                    if not result.passed:
                        print(_failure_text(result), flush=True)
        except KeyboardInterrupt:
            terminate_active()
            for future in futures:
                future.cancel()
            raise
    return results, time.monotonic() - started


def parser() -> argparse.ArgumentParser:
    item = argparse.ArgumentParser(description="Run unittest modules with bounded cross-platform parallelism.")
    item.add_argument("--root", type=Path, default=Path.cwd(), help="Repository root containing the test directory.")
    item.add_argument("--start-directory", default="tests", help="Repository-relative test directory (default: tests).")
    item.add_argument("--pattern", default="test_*.py", help="Test filename pattern (default: test_*.py).")
    item.add_argument("--jobs", type=int, help="Worker count; defaults to TAILTRAIL_TEST_JOBS or min(CPU, 4).")
    item.add_argument("--serial", action="store_true", help="Run one conventional unittest subprocess for debugging.")
    item.add_argument("--include", action="append", default=[], help="Comma-separated module names or basenames to include.")
    item.add_argument("--exclude", action="append", default=[], help="Comma-separated module names or basenames to exclude.")
    item.add_argument("--timeout", type=float, default=0.0, help="Optional per-module timeout in seconds; zero disables it.")
    item.add_argument("--verbose", action="store_true", help="Pass -v to unittest subprocesses.")
    item.add_argument("--quiet", action="store_true", help="Suppress per-module progress; failures remain in the final report.")
    item.add_argument("--list", action="store_true", help="List selected modules without executing them.")
    item.add_argument("--format", choices=("text", "json"), default="text")
    return item


def main(argv: list[str] | None = None) -> int:
    args = parser().parse_args(argv)
    try:
        root = args.root.resolve()
        jobs = args.jobs if args.jobs is not None else default_jobs()
        if jobs < 1:
            raise ValueError("--jobs must be at least 1")
        if args.timeout < 0:
            raise ValueError("--timeout cannot be negative")
        discovered = discover_modules(root, args.start_directory, args.pattern)
        modules = select_modules(discovered, args.include, args.exclude)
    except (OSError, ValueError) as error:
        if args.format == "json":
            print(json.dumps({"type": "tailtrail-parallel-test-result", "status": "invalid", "error": str(error)}, indent=2, sort_keys=True))
        else:
            print(f"TailTrail test runner error: {error}", file=sys.stderr)
        return 2

    if args.list:
        if args.format == "json":
            print(json.dumps({"type": "tailtrail-parallel-test-selection", "modules": modules}, indent=2, sort_keys=True))
        else:
            print("\n".join(modules))
        return 0

    try:
        results, elapsed = execute(
            root,
            modules,
            jobs=jobs,
            serial=args.serial,
            verbose=args.verbose,
            quiet=args.quiet or args.format == "json",
            timeout=args.timeout,
        )
    except KeyboardInterrupt:
        if args.format == "json":
            print(json.dumps({"type": "tailtrail-parallel-test-result", "status": "interrupted"}, indent=2, sort_keys=True))
        else:
            print("\nTailTrail test run interrupted; active workers were terminated.", file=sys.stderr)
        return 130

    failures = [result for result in results if not result.passed]
    payload = {
        "schema_version": "1",
        "type": "tailtrail-parallel-test-result",
        "status": "passed" if not failures else "failed",
        "root": root.as_posix(),
        "jobs": 1 if args.serial else min(jobs, len(modules)),
        "serial": bool(args.serial),
        "module_count": len(modules),
        "tests": sum(result.tests for result in results),
        "elapsed_seconds": round(elapsed, 3),
        "preflight_modules": split_phases(modules)[0] if not args.serial else [],
        "failures": [result.public(include_output=True) for result in sorted(failures, key=lambda row: row.label)],
        "results": [result.public() for result in sorted(results, key=lambda row: row.label)],
    }
    if args.format == "json":
        print(json.dumps(payload, indent=2, sort_keys=True))
    else:
        print("\nTailTrail test summary")
        print(f"- Status: {payload['status']}")
        print(f"- Modules: {payload['module_count']}")
        print(f"- Tests: {payload['tests']}")
        print(f"- Workers: {payload['jobs']}")
        print(f"- Elapsed: {payload['elapsed_seconds']:.3f}s")
        if failures and args.quiet:
            for result in sorted(failures, key=lambda row: row.label):
                print(_failure_text(result))
    return 0 if not failures else 1


if __name__ == "__main__":
    raise SystemExit(main())
