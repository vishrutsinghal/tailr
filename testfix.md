What was done — complete summary
Root cause of your reported problem
The Planning Lock was being created correctly (tool was firing). The bug was that after creating the lock, Copilot appended its own generic implementation plan because the instruction said "return the complete Start Report" — which is ambiguous. It doesn't say stop. So every adapter obeyed the letter of the rule and then added its own content.
 
All changes applied
1. scripts/mcp-server.py — code fix
harness_control_check was declared out of order in tool_definitions() (between two read-only tools), causing doctor to self-report as failed. A failing doctor makes the MCP integration look broken to the host.
Fixed by moving it into the correct position after planning_lock_show (last read-only) and before source_patch_apply (first controlled).
Result: doctor passes, all 19 tests green.
2. .github/prompts/tailtrail-start.prompt.md — explicit stop rule
Rewrote to say: MCP first, CLI fallback, then "Return the tool or CLI output exactly as produced. Do not add your own implementation plan, steps, analysis, or guidance after it."
3. All 9 adapter/instruction files — verbatim-stop rule added to Planning Lock bullet
File
Change
.github/copilot-instructions.md
Planning Lock now has bold stop rule
adapters/copilot-instructions.md
Same (source for reinstalls)
adapters/claude.md
Same
adapters/chatgpt-instructions.md
Same
adapters/gemini.md
Same
adapters/cursor.mdc
Same
CLAUDE.md
Same
GEMINI.md
Same
AGENTS.md
Same
skills/tailtrail-start/SKILL.md
Added bold stop rule + MCP-first ordering
4. Documentation consistency fixes (earlier)
tailtrail-mcp.md — reconciled shipped vs planned status, broken link fixed
META-HARNESS-IMPLEMENTATION.md — duplicate command removed
testing-confidence.md — baseline rating annotated
5. TAILTRAIL-MCP-START-REVIEW.md — created
Full investigation, root-cause analysis, all changes, findings F1–F8, and 5-phase implementation plan for remaining improvements.
 
To test right now
Use /tailtrail-start <your task> in Copilot. You should now see only the TailTrail Start Report — Planning Lock ID, selected controls, guided delivery sequence, approval gate — with nothing appended after it. If you still see extra content, the Copilot session needs to reload the updated .github/copilot-instructions.md (close and reopen the chat).
