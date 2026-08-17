# GitHub Copilot quickstart

From the TailTrail source checkout, install the Copilot profile into the target
project:

```powershell
py -3 scripts\tailtrail.py install local --target "D:\path\to\project" --profile copilot
```

On macOS/Linux:

```bash
python3 scripts/tailtrail.py install local --target "/absolute/path/to/project" --profile copilot
```

Open the target repository in Copilot and start a new chat. Use:

```text
/tailtrail-start "fix the zero quantity validation defect"
```

`tailtrail start "..."` also works. TailTrail must return a Planning Lock
before implementation; approve it in the same chat when you are ready.

Verify or update the install with [INSTALL.md](../../INSTALL.md).
