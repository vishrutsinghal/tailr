# TailTrail Navigator Plan

Navigator selected a compact read-only repo overview path.

## Goal

- tell me important features of this repo

## Mode

- Repo Overview / Discovery
- No implementation until approval.
- No scans, tests, builds, learning capture, AIDLC, review, or handoff unless you ask for them.

## Plan

1. Inspect README and top-level project structure.
2. Identify language, framework, entry points, tests, and major modules.
3. Summarize important repo features and how they fit together.
4. Offer Code Graph Mapper as an approved deeper discovery step when a reusable graph cache is useful.
5. Ask before running scans, tests, builds, or writing files.

## Load

- exact user request
- README or project docs when present
- fresh `.tailtrail/bootstrap-snapshot.json` when present
- build and dependency manifests
- top-level source, test, config, and CI folders
- entry points and main modules only after the structure is known

## Avoid

- editing files
- AIDLC lifecycle docs unless user asks for lifecycle planning
- review, handoff, scanner, or vulnerability routes unless the user asks for change work
- full source tree reads before identifying the main modules

## Bootstrap Snapshot

- Status: `missing`
- Path: `.tailtrail/bootstrap-snapshot.json`
- Reason: snapshot file is missing
- Recommended action: Run `tailtrail bootstrap snapshot --write-result` or `tailtrail bootstrap refresh` before broad Navigator planning.
- Command: `tailtrail bootstrap snapshot --root "<ROOT>" --write-result`

## Optional Deeper Discovery

- Feature: Code Graph Mapper
- Default: not run
- Creates: `<ROOT>/tailtrail-meta/code-graph-cache.json`
- Why: Repo overview starts with low-cost docs and structure. Run this only when you want a reusable module/symbol/read-order map.
- Command: `tailtrail graph map --root "<ROOT>"`
- Use when:
  - README or docs are missing or weak
  - the repo is large
  - you want module, endpoint, test, config, or dependency relationships
  - you expect follow-up implementation, review, Sonar, vulnerability, or handoff work

## Approval

- Approve to inspect the repo and answer the overview question.
- You can ask for a compact or detailed summary before approval.

## Notes

- Navigator selected a read-only discovery path.
- It does not edit files, run implementation, record learnings, run scanners, or create graph cache files by itself.
- Bootstrap Snapshot writes only `.tailtrail/bootstrap-snapshot.json` when the snapshot command is explicitly approved.
- If you approve, the next step is to inspect the target repo and answer the repo overview question.
