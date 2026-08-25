# Codex quickstart

Install the self-contained package, then project the Core adapter into the
repository you will open in Codex:

```powershell
tailtrail install --host codex --profile core --target "D:\path\to\project"
```

On macOS/Linux:

```bash
tailtrail install --host codex --profile core --target "/absolute/path/to/project"
```

Open the target project in Codex, start a new chat, then say:

```text
tailtrail start "fix the zero quantity validation defect"
```

Review the Planning Lock. Approve the run only when its scope and requirements
are correct. After implementation, Codex returns TailTrail's Completion Report.

Verify with `tailtrail doctor --host codex --target <project>`. This validates
the installed v3 contract; it does not claim a real Codex version was observed
or supported. See [HOST-ADAPTERS.md](../../HOST-ADAPTERS.md).
