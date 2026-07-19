# TailTrail Hooks

Hooks are optional. They are not enabled by the plugin manifest by default.

Use hooks only in hosts that can safely inject small text into a session. Hooks should reduce repeated prompt typing; they should not inject full TailTrail docs, raw logs, source files, or cached state.

## `tailtrail-lifecycle-hook.py`

This hook reduces repeated prompt typing by combining two backend decisions:

- `scripts/expand-intent.py` expands short commands such as `use AIDLC and review`.
- `scripts/token-auto.py` decides whether context routing is worth using.

Examples:

```bash
python3 hooks/tailtrail-lifecycle-hook.py --startup
python3 hooks/tailtrail-lifecycle-hook.py use AIDLC and review
python3 hooks/tailtrail-lifecycle-hook.py use CI Sonar
python3 hooks/tailtrail-lifecycle-hook.py "review this diff for dependency risk"
```

For a startup hook, it prints a short list of available commands. For a prompt hook, it prints the expanded workflow, run order, load list, avoid list, validation notes, and token route when useful.

Default state:

```text
.tailtrail/lifecycle-hook-state.json
```

Use `--no-state` for one-off validation or host integrations that already track state.

## `token-router-hook.py`

This hook prints a compact context injection for hosts that support prompt or startup hooks.

Example:

```bash
python3 hooks/token-router-hook.py review
python3 hooks/token-router-hook.py auto review this diff for extra dependencies
```

The hook calls `scripts/route-context.py`, prints only the selected route, and updates `.tailtrail/token-router-state.json` unless `--no-state` is passed.

Use this hook only where the host can inject small text safely. Do not configure it to inject full TailTrail docs, raw logs, source files, or cached state.

## `token-autopilot-hook.py`

This hook decides whether token routing is useful before printing context guidance.

Example:

```bash
python3 hooks/token-autopilot-hook.py rename this variable
python3 hooks/token-autopilot-hook.py review this diff for dependency risk
```

## `learning-capture-hook.py`

This hook suggests a Learning Agent V2 capture command from a compact post-task summary.

```bash
python3 hooks/learning-capture-hook.py "Fixed Sonar complexity in PaymentValidator" --candidate "Extract named guard methods while preserving validation order."
python3 hooks/learning-capture-hook.py "Fixed Sonar complexity in PaymentValidator" --candidate "Extract named guard methods while preserving validation order." --approved
```

Default behavior is suggestion only. It writes a learning event only when `--approved` is passed. Keep this hook attached to post-task or post-approval flows, not every raw user prompt.

The hook must not capture raw prompts, full assistant responses, source snippets, raw logs, secrets, credentials, PII, PHI, or customer data. If the task is tiny, vague, or not reusable, it should skip capture.

For tiny low-risk prompts, it returns a skip decision and avoids loading TailTrail docs. For non-trivial prompts, it prints one route, one slice, load items, avoid items, and exactness risk.
