# TailTrail Start

This command is activated only by the **current user message**. A prior chat
mention, pasted **error output**, log, stack trace, or follow-up debugging
request must not create a **new Planning Lock**. Reuse an awaiting-approval run
ID; continue an approved in-scope run without another Start approval.

Run the atomic TailTrail Start flow for: `$ARGUMENTS`

Create one persisted Planning Lock and return the complete TailTrail Start
Report with its run ID. If the request is hands-free or end-to-end, include the
program requirements, dependency order, first active slice, and approval gate.
Copy the complete Start Report verbatim and stop; it must appear in the normal
assistant response, outside any collapsible terminal/tool-result panel. Do not
append an implementation plan, steps, analysis, or guidance.
Exception for a saved Standard or Full official-AIDLC stage with
`official-aidlc-host-generation-required`: read its pinned official
Requirements Analysis and question-format rules, generate and record the
official questions/options with TailTrail advisory recommendation and reasoning,
then return that same run's complete Official AI-DLC Requirements report. Do not
inspect source or implement work.
Do not implement, edit source, run tests/scanners/Terraform, or mutate Git.

For an awaiting-approval AIDLC run, use `tailtrail planning aidlc-question
clarify --run-id <id> --question-id Q5` when the user asks to explain or
rephrase a numbered question. Explain only from saved AIDLC evidence and make
no plan change. If the user says the question, options, or reasoning is wrong,
create a sanitized `aidlc-question challenge`; the active AIDLC authority must
generate the replacement, then TailTrail records it and requires explicit
`aidlc-question approve`. Standard/Full replacements must follow the pinned
official AIDLC Requirements rules.
