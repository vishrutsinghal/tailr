# Workspace Detection

Purpose: understand the project shape before planning or editing.

## Inputs

- user request
- repository root
- visible project files
- package, build, test, and config files
- local policy files when present

## Actions

- Identify language, framework, package manager, and build system.
- Identify entry points, tests, generated areas, and dependency manifests.
- Record likely commands without running broad or destructive actions.
- Classify the work as greenfield, brownfield, or mixed.
- Choose lifecycle depth: `minimal`, `standard`, or `comprehensive`.

## Outputs

- update `aidlc-docs/aidlc-state.md`
- update `aidlc-docs/audit.md`
- update `context/project-map.md` when stable facts will be reused

## Done When

- the active project type is clear
- likely commands are known or explicitly unknown
- generated/vendor areas to avoid are identified
- lifecycle depth is justified
