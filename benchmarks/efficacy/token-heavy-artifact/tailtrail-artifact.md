# TailTrail Output

Token Harness route:

- Content type: `log`
- Exactness: `reduce-safe`
- Strategy: `failure-focused-summary`
- Preserve: command boundaries, exit codes, first failure, stack traces, retrieval pointer

Structured reducer output:

- First failure: `ERROR module payment failed`
- Exit code: `1`
- Repeated error group: `Timeout waiting for test database`
- Retrieval: `cat "build.log"`

Token Harness Bridge plan:

- Status: `disabled`
- Reason: no local policy enabled runtime compression bridge
- Fallback: exact pass-through or internal structured reducer

Proof boundary: estimated/local evidence only unless measured model/API telemetry is supplied.
