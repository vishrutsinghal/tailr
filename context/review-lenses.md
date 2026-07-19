# TailTrail Review Lenses

Review lenses are focused perspectives for TailTrail Review. They keep reviews sharper than a generic checklist.

Use one lens when a specific risk dominates. Use two only when the change clearly crosses both areas.

## Lenses

| Lens | Short Prompt | Focus |
|---|---|---|
| `architecture` | `Use architecture review.` | Boundaries, data flow, coupling, shared abstractions, migration paths, and blast radius. |
| `security` | `Use security review.` | Auth, authorization, secrets, input handling, escaping, dependency risk, privacy, and auditability. |
| `qa` | `Use QA review.` | User flows, regression paths, test coverage, manual checks, fixtures, and validation evidence. |
| `maintainability` | `Use maintainability review.` | Simplicity, duplication, naming, unnecessary abstractions, readability, and future ownership. |
| `dependency` | `Use dependency review.` | New packages, version changes, license/security/supply-chain risk, and standard-library alternatives. |

## Lens Rules

- Lead with concrete findings, not broad commentary.
- Reference exact files, diffs, or behaviors.
- Do not weaken existing safeguards to make code shorter.
- Prefer one focused validation gap over a long generic test wish list.
- If a lens finds release or ownership risk, create a handoff note.
