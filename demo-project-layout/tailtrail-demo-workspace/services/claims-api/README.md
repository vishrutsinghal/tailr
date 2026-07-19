# Claims API Demo Service

This service is intentionally tiny and dependency-free.

It demonstrates:

- request validation
- a small endpoint
- focused unit tests
- one intentional validation bug
- TailTrail planning around graph, review, tests, and learning

## Intentional Bug

`validate_claim` currently allows `amount == 0`. Demo policy says amount must be greater than `0`.

This is the main bug for TailTrail to plan and fix during the demo.

## Run Tests

From `tailtrail-demo-workspace`:

```bash
python3 services/claims-api/tests/test_validation.py
```

The zero-amount regression test is marked as an expected failure so the demo repository remains runnable before the bug is fixed.

## Run Service

From `tailtrail-demo-workspace`:

```bash
python3 services/claims-api/src/claims_api/app.py
```

Then send a request:

```bash
curl -X POST http://localhost:8080/claims -d '{"claim_id":"CLM-1001","member_id":"MBR-2001","claim_type":"medical","amount":125.5}'
```

