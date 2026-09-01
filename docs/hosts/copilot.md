# GitHub Copilot quickstart

Install the self-contained package, then project the Core adapter into the
target repository:

```powershell
tailtrail setup --host copilot --profile core --target "D:\path\to\project"
```

On macOS/Linux:

```bash
tailtrail setup --host copilot --profile core --target "/absolute/path/to/project"
```

Open the target repository and start a new Copilot Chat. If repository
instructions remain stale, reload the IDE window and start another chat. Use:

```text
/tailtrail-start "fix the zero quantity validation defect"
```

`tailtrail start "..."` also works. TailTrail must return a Planning Lock
before implementation; approve it in the same chat when you are ready.

Verify with `tailtrail doctor --host copilot --target <project>`. Copilot
instruction loading is host-assisted; CI remains authoritative for enforceable
repository policy. See [HOST-ADAPTERS.md](../../HOST-ADAPTERS.md).
