# Cache Index

Use this file to avoid rediscovering stable project facts. Cache only summaries that can be invalidated clearly.

| Key | Source | Summary | Refreshed | Invalidates when |
|---|---|---|---|---|
| project.commands | build/test docs or package scripts |  |  | command files or package manager files change |
| project.entry-points | targeted source search |  |  | routes, app bootstrap, jobs, or CLI layout change |
| project.helpers | targeted source search |  |  | shared utility folders or public helper APIs change |
| project.policy | local policy files |  |  | team policy or approval rules change |
| tool.summary | browser, MCP, API, or command output |  |  | input URL, query, command, version, or response timestamp changes |

## Cache Rules

- Prefer a one-line summary plus exact source path.
- Do not cache secrets, raw credentials, private tokens, or sensitive payloads.
- Do not let cached facts override explicit user instructions or safety rules.
- Refresh cached facts before using them for edits when the invalidation condition might have changed.
