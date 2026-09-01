# Codex quickstart

Install the self-contained package, then project the Core adapter into the
repository you will open in Codex:

```powershell
tailtrail setup --host codex --profile core --target "D:\path\to\project"
```

On macOS/Linux:

```bash
tailtrail setup --host codex --profile core --target "/absolute/path/to/project"
```

Start a new Codex task so the installed guidance is loaded. If it remains
stale, close and reopen the project before starting another task. Then say:

```text
tailtrail start "fix the zero quantity validation defect"
```

Review the Planning Lock. Approve the run only when its scope and requirements
are correct. After implementation, Codex returns TailTrail's Completion Report.

Verify with `tailtrail doctor --host codex --target <project>`. This validates
the installed v3 contract; it does not claim a real Codex version was observed
or supported. See [HOST-ADAPTERS.md](../../HOST-ADAPTERS.md).
