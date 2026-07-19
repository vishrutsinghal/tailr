# Cross-Repo Reference Mode

Use Cross-Repo Reference Mode when the user is working in one repo but wants a sibling or external repo used as a pattern reference.

## Purpose

This mode protects read/write boundaries in multi-repo workspaces.

It helps the agent:

- identify the target repo that may be edited
- identify reference repos that must stay read-only
- use reference repos for conventions, architecture shape, validation style, tests, config patterns, and naming
- avoid copying implementation code from reference repos
- avoid broad token-heavy sibling repo reads
- detect when the reference path is outside the active workspace and may not be readable

## User Prompt Shape

Preferred:

```text
Use TailTrail cross-repo reference.
Target: /path/to/service-a
Reference: /path/to/service-b
Goal: implement the same validation style.
Only edit the target repo.
```

Short form:

```text
Use service-b as reference for service-a. Only edit service-a.
```

Navigator should parse labeled `Target:` and `Reference:` paths when present. If it cannot parse the reference path, it should recommend the `tailtrail reference` command with a placeholder and ask the user to confirm.

## Command

```bash
python3 scripts/tailtrail.py reference --target /path/to/service-a --reference /path/to/service-b --goal "match validation style"
```

The command is local and deterministic. It does not edit code, run scanners, call models, or create a graph unless the user later runs the suggested graph command.

Use `--write-summary` only when the user wants a durable local reference summary:

```bash
python3 scripts/tailtrail.py reference \
  --target /path/to/service-a \
  --reference /path/to/service-b \
  --goal "match validation style" \
  --write-summary /path/to/service-a/.tailtrail/reference-context/service-b.md
```

## Boundaries

- Only target repo files are editable.
- Reference repos are read-only.
- Reference repos provide patterns, not source code to copy.
- Current target source always wins over reference summaries.
- If a reference repo cannot be read, ask the user to open the parent workspace or provide a compact generated summary.
- Do not bulk-load an entire sibling repo when a manifest, code graph, or focused file slice is enough.

## Relationship To Code Graph Mapper

Cross-Repo Reference Mode can recommend a graph cache for the reference repo, stored under the target repo:

```bash
python3 scripts/tailtrail.py graph map \
  --root /path/to/service-b \
  --cache /path/to/service-a/.tailtrail/reference-graphs/service-b.json
```

This keeps reference metadata near the target workflow without editing the reference repo.

The graph cache is metadata-only. It does not store source snippets and does not replace exact source inspection before editing target files.
