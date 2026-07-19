Use `python3 scripts/tailtrail.py start "fix Sonar issue before PR" --changed src/service/Foo.java` as the first command for this non-trivial task.

The Start report should show:

- selected features
- skipped features
- likely impacted files
- load and avoid guidance
- suggested commands
- scan approval when broad Sonar, quality, vulnerability, audit, build, or test commands are proposed
- guarded learning quality when learnings are surfaced
- a decision menu with review, approve, edit, scan approval, learning approval, and leaner workflow options

The command is advisory and approval-first. It does not edit files, run implementation, run scanners, capture learnings, or write quality events. The user should review the plan, edit it if needed, and approve implementation only after the selected features, files, commands, scan choices, learning choices, and validation look right.

