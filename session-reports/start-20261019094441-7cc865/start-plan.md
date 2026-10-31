# TailTrail Start Plan

| Field | Value |
|---|---|
| Run ID | `start-20261019094441-7cc865` |
| Approved revision | `v3` |
| State | Activated |
| Planning audit | Clean |
| Scope decision | `sha256:18912f7f8eedd155e152e92a39484e0f50275ac49f1895836375690446b62366` |

## Goal

Make `proof-update` create an explicit structured shared binding from one command to `unit`, `contract`, and `behaviour` tiers, reject loose positional command/tier lists, and permit an awaiting-approval revision to expand its saved proof boundary for required integration evidence.

## Requirements

| ID | Requirement | Kind | Status |
|---|---|---|---|
| REQ-01 | Make `proof-update` create an explicit structured shared binding from one command to unit, contract, and behaviour tiers. | Change | Approved |
| REQ-02 | Reject loose positional command and tier lists. | Constraint | Approved |

## Scope

| Role | Path | Requirements | Authority |
|---|---|---|---|
| Implementation owner | `scripts/planning-revision.py` | REQ-01, REQ-02 | Editable after approval |
| Proof | `tests/test_planning_revision.py` | REQ-01 | Test assertions only |
| Proof | `tests/test_canonical_statement_contract.py` | REQ-01, REQ-02 | Test assertions only |

## Structured Proof Binding

```json
{
  "command": "python3 -m unittest tests.test_planning_revision -v",
  "tiers": ["unit", "contract", "behaviour", "integration"]
}
```

Loose parallel command and tier lists do not grant accidental multi-tier authority.

## Proof Commands

| Command ID | Command | Requirement | Tiers |
|---|---|---|---|
| `cmd-38cc3b` | `python3 -m unittest tests.test_planning_revision -v` | REQ-01 | unit, contract, behaviour, integration |
| `cmd-1c705e` | `python3 -m unittest discover -s tests -p test_canonical_statement_contract.py -v` | REQ-02 | unit |

## Boundary Revision

| Field | Before | After |
|---|---|---|
| Allowed tiers | unit, contract, behaviour | unit, contract, behaviour, integration |
| Restart required | Yes | No |
| Audit behavior | Boundary conflict | Re-evaluate same awaiting-approval run |

## Planned Validation

| Check | Expected result |
|---|---|
| One command covers all explicitly bound tiers | Pass |
| Loose positional lists cannot imply shared authority | Pass |
| `proof-boundary-expand` does not enter requirement-add handling | Pass |
| Revised proof path remains requirement-scoped | Pass |
| Planning revision followed by planning audit becomes clean | Pass |

## Approval

Revision `v3` was explicitly approved and activated. Implementation authority remained limited to the approved owner and proof paths.
