# Enterprise Phase E1 Design — Shared Release Truth

Date: 2026-08-22

## Architecture

`release-manifest.json` is declarative policy. `scripts/release_manifest.py` is
the dependency-free reader and validator used by release, doctor, public audit,
smoke, and export paths.

```text
release-manifest.json
  ├── candidate scope and hygiene ──> check-tailtrail / release-check
  ├── approved repository URLs ─────> public-doc-audit
  ├── workflow fragments ───────────> release-check / CI
  ├── distribution policy ──────────> export-release
  └── ordered smoke commands ───────> smoke-test
```

The candidate is the current tracked file content plus explicitly reviewed
untracked additions. Explicit file/prefix exclusions remove projected official
AI-DLC runtime material and a local issue scratch file. Unrelated user-owned
untracked files are not selected. Forbidden local-state rules are checked on
existing tracked inputs, while the snapshot builder independently filters them.

## Public reference policy

The audit scans only manifest-selected text files. Repository URLs are denied
unless their normalized repository root is in the manifest allowlist. The list
contains TailTrail's public origin and the pinned/public AI-DLC, Spec Kit, and
AI Mode upstream projects already used by the repository. SSH repository URLs
are normalized before comparison and therefore remain denied unless the same
public root is explicitly approved.

## Smoke isolation

The smoke builder copies candidate files directly from the working tree into a
temporary directory, preserving current reviewed edits without copying `.git`,
IDE files, unrelated untracked files, or generated `.tailtrail` state. Manifest
preflight commands run before stateful user journeys. The temporary directory
is removed unless debugging retention is explicitly requested.

## Compatibility decisions

- Root `navigator.py` remains a compatibility surface and prepends the local
  `scripts` directory before importing shared modules.
- `aidlc-rules/` remains a projected official runtime source and is explicitly
  excluded from the public candidate; `.aidlc/` pinned bridge material remains
  governed separately.
- `issue.txt` is explicitly excluded as local diagnostic material.
- Historical roadmap statements are retained as history; active release,
  support, versioning, admin, benchmark, and CI documents name `trust.yml` and
  the shared manifest.

## Dependency and safety posture

No dependency is added or changed. JSON, regular expressions, filesystem
operations, subprocess execution, temporary directories, and copying use the
Python standard library. The implementation does not publish, install globally,
contact providers, delete unrelated user files, or claim later enterprise
phases complete.
