# TailTrail Demo Policy

This policy is active for the demo workspace.

## Dependency Rules

- Do not add external dependencies for the claims API.
- Prefer Python standard library behavior.
- Any proposed dependency must include a reason and a no-dependency alternative.

## Validation Rules

- Run or name `python3 services/claims-api/tests/test_validation.py` for validation changes.
- Do not claim tests passed unless the command was run and evidence is available.
- Preserve validation for required member id, supported claim type, and positive amount.

## Learning Rules

- Learning capture is approval-first.
- Capture only reusable patterns, not raw prompts or personal feedback.
- Low-confidence or disputed changes should not be recorded as reusable learning.

## Graph Rules

- Use Code Graph Mapper before broad source reads for meaningful code changes.
- A fresh graph cache is advisory; exact source still wins.

