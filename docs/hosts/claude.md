# Claude quickstart

From the TailTrail source checkout, install the Claude profile into the target
project:

```powershell
py -3 scripts\tailtrail.py install local --target "D:\path\to\project" --profile claude
```

On macOS/Linux:

```bash
python3 scripts/tailtrail.py install local --target "/absolute/path/to/project" --profile claude
```

Start a new Claude chat in the target project, then ask:

```text
tailtrail start "fix the zero quantity validation defect"
```

Review the plan first. Approving its active run allows the scoped work to begin;
the final response is TailTrail's Completion Report.

Verify or update the install with [INSTALL.md](../../INSTALL.md).
