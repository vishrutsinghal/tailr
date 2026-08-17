# Codex quickstart

From the TailTrail source checkout, install into the project you will open in
Codex:

```powershell
py -3 scripts\tailtrail.py install codex-plugin --target "D:\path\to\project"
```

On macOS/Linux:

```bash
python3 scripts/tailtrail.py install codex-plugin --target "/absolute/path/to/project"
```

Open the target project in Codex, start a new chat, then say:

```text
tailtrail start "fix the zero quantity validation defect"
```

Review the Planning Lock. Approve the run only when its scope and requirements
are correct. After implementation, Codex returns TailTrail's Completion Report.

Verify or refresh the install with [INSTALL.md](../../INSTALL.md).
