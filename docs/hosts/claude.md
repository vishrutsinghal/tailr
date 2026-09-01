# Claude quickstart

Install the self-contained package, then project the Core adapter into the
target repository:

```powershell
tailtrail setup --host claude --profile core --target "D:\path\to\project"
```

On macOS/Linux:

```bash
tailtrail setup --host claude --profile core --target "/absolute/path/to/project"
```

Exit any existing Claude Code session and start a new session in the target
project. If it remains stale, restart Claude Code before reopening the project.
Then run:

```text
/tailtrail-start fix the zero quantity validation defect
```

Review the plan first. Approving its active run allows the scoped work to begin;
the final response is TailTrail's Completion Report.

Verify with `tailtrail doctor --host claude --target <project>`. Doctor requires
both `CLAUDE.md` and `.claude/commands/tailtrail-start.md`; a generic or partial
Claude file cannot pass. See [HOST-ADAPTERS.md](../../HOST-ADAPTERS.md).
