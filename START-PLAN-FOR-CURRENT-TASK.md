# Start Plan for Current Task: Command Registry Implementation

This is what the user will see when they run:
```bash
tailtrail start "Implement command registry for TailTrail planning system to eliminate proof command duplication"
```

---

## Actual Start Plan Output (What User Sees)

```
╔════════════════════════════════════════════════════════════════════════════╗
║                    TailTrail Start Plan                                    ║
║           run-20261019-cmd-registry-impl-7f8a9b                            ║
║                     Status: awaiting-approval                              ║
╚════════════════════════════════════════════════════════════════════════════╝

PLANNING LOCK
─────────────────────────────────────────────────────────────────────────────
Goal: Implement command registry for TailTrail planning system to eliminate 
      proof command duplication and improve data efficiency

Requirements analyzed: 5
Editable paths: scripts/task-start.py, scripts/execution-evidence.py, 
                scripts/closure-finalizer.py
Proof paths: scripts/planning_lock.py (existing), scripts/planning-audit.py (existing)
Scope fingerprint: 8f7a9b2c3d4e5f6g7h8i9j0k1l2m3n4o


COMMAND REFERENCE REGISTRY
─────────────────────────────────────────────────────────────────────────────
cmd-a1b2c3d4e5f6:
  python3 -m pytest scripts/test_planning_lock.py -v --tb=short

cmd-7x8y9z0w1v2u:
  python3 -m pytest scripts/test_task_start.py -v --tb=short

cmd-3q4r5s6t7u8v:
  python3 -m pytest scripts/test_execution_evidence.py -v --tb=short

cmd-9m0n1o2p3q4r:
  python3 -m pytest scripts/test_closure_finalizer.py -v --tb=short

cmd-5a6b7c8d9e0f:
  python3 -m mypy scripts/planning_lock.py scripts/task-start.py 
           scripts/execution-evidence.py scripts/closure-finalizer.py --strict

cmd-2k3l4m5n6o7p:
  python3 -m py_compile scripts/planning_lock.py scripts/task-start.py 
           scripts/execution-evidence.py scripts/closure-finalizer.py


VALIDATION REQUIREMENTS & FOCUSED VALIDATION MATRIX
─────────────────────────────────────────────────────────────────────────────

┏━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━┓
┃ REQ-001: Core Registry Implementation (planning_lock.py)                 ┃
┗━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━┛
  
  Description: Build deterministic command registry with SHA256-based IDs
  
  Tiers: unit, integration, static
  Proofs:
    - cmd-a1b2c3d4e5f6  (unit)
    - cmd-5a6b7c8d9e0f  (static)
    - cmd-2k3l4m5n6o7p  (integration: syntax check)
  
  ┌──────────────┬──────────────────────┬─────────────┬──────────┐
  │ Tier         │ Command ID           │ Candidate   │ State    │
  ├──────────────┼──────────────────────┼─────────────┼──────────┤
  │ unit         │ cmd-a1b2c3d4e5f6     │ test_*.py   │ existing │
  │ static       │ cmd-5a6b7c8d9e0f     │ *.py        │ existing │
  │ integration  │ cmd-2k3l4m5n6o7p     │ *.py        │ existing │
  └──────────────┴──────────────────────┴─────────────┴──────────┘


┏━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━┓
┃ REQ-002: task-start.py Consumer Updates                                   ┃
┗━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━┛
  
  Description: Update task-start to emit command_id in focused validation
  
  Tiers: unit, static
  Proofs:
    - cmd-7x8y9z0w1v2u  (unit)
    - cmd-5a6b7c8d9e0f  (static)
  
  ┌──────────────┬──────────────────────┬──────────────────────┬──────────┐
  │ Tier         │ Command ID           │ Candidate            │ State    │
  ├──────────────┼──────────────────────┼──────────────────────┼──────────┤
  │ unit         │ cmd-7x8y9z0w1v2u     │ test_task_start.py   │ existing │
  │ static       │ cmd-5a6b7c8d9e0f     │ scripts/task-start.py│ existing │
  └──────────────┴──────────────────────┴──────────────────────┴──────────┘


┏━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━┓
┃ REQ-003: execution-evidence.py Consumer Updates                           ┃
┗━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━┛
  
  Description: Add command_id resolution when executing approved proofs
  
  Tiers: unit, static
  Proofs:
    - cmd-3q4r5s6t7u8v  (unit)
    - cmd-5a6b7c8d9e0f  (static)
  
  ┌──────────────┬──────────────────────┬──────────────────────────┬──────────┐
  │ Tier         │ Command ID           │ Candidate                │ State    │
  ├──────────────┼──────────────────────┼──────────────────────────┼──────────┤
  │ unit         │ cmd-3q4r5s6t7u8v     │ test_execution_evidence.py│ existing │
  │ static       │ cmd-5a6b7c8d9e0f     │ scripts/exec*.py         │ existing │
  └──────────────┴──────────────────────┴──────────────────────────┴──────────┘


┏━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━┓
┃ REQ-004: closure-finalizer.py Consumer Updates                            ┃
┗━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━┛
  
  Description: Resolve command_id when building receipts and final reports
  
  Tiers: unit, static
  Proofs:
    - cmd-9m0n1o2p3q4r  (unit)
    - cmd-5a6b7c8d9e0f  (static)
  
  ┌──────────────┬──────────────────────┬──────────────────────────┬──────────┐
  │ Tier         │ Command ID           │ Candidate                │ State    │
  ├──────────────┼──────────────────────┼──────────────────────────┼──────────┤
  │ unit         │ cmd-9m0n1o2p3q4r     │ test_closure_finalizer.py│ existing │
  │ static       │ cmd-5a6b7c8d9e0f     │ scripts/closure*.py      │ existing │
  └──────────────┴──────────────────────┴──────────────────────────┴──────────┘


┏━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━┓
┃ REQ-005: Test Fixture Updates & End-to-End Validation                     ┃
┗━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━┛
  
  Description: Update test fixtures to use registry format, validate full flow
  
  Tiers: integration, behaviour
  Proofs:
    - cmd-2k3l4m5n6o7p  (integration)
  
  ┌──────────────┬──────────────────────┬──────────────────────────┬──────────┐
  │ Tier         │ Command ID           │ Candidate                │ State    │
  ├──────────────┼──────────────────────┼──────────────────────────┼──────────┤
  │ integration  │ cmd-2k3l4m5n6o7p     │ tests/integration/       │ existing │
  └──────────────┴──────────────────────┴──────────────────────────┴──────────┘


SELECTED HARNESSES FOR VALIDATION
─────────────────────────────────────────────────────────────────────────────
✓ Unit Testing Harness
✓ Static Analysis Harness
✓ Integration Testing Harness


FOCUSED VALIDATION COVERAGE SUMMARY
─────────────────────────────────────────────────────────────────────────────
Total Requirements:     5
Requirements Covered:   5 (100%)

By Tier:
  unit:           5 requirements covered by cmd-a1b2c3d4e5f6, cmd-7x8y9z0w1v2u,
                  cmd-3q4r5s6t7u8v, cmd-9m0n1o2p3q4r (4 proof commands)
  integration:    1 requirement covered by cmd-2k3l4m5n6o7p
  static:         5 requirements covered by cmd-5a6b7c8d9e0f
  behaviour:      0 (not required for this phase)

Proof Command Reuse:
  cmd-5a6b7c8d9e0f: covers 5 requirements (static type checking)
  cmd-2k3l4m5n6o7p: covers 1 requirement (integration tests)
  cmd-a1b2c3d4e5f6: covers 1 requirement (planning_lock unit tests)
  cmd-7x8y9z0w1v2u: covers 1 requirement (task_start unit tests)
  cmd-3q4r5s6t7u8v: covers 1 requirement (execution_evidence unit tests)
  cmd-9m0n1o2p3q4r: covers 1 requirement (closure_finalizer unit tests)


APPROVAL CHECKLIST
─────────────────────────────────────────────────────────────────────────────
Before approving this plan, verify:

☐ All 5 editable paths are correct and under your control
☐ Unit test files exist for each module (test_*.py)
☐ Static analysis passes on current code
☐ Integration test suite is runnable
☐ You have authority to execute proof commands on your machine
☐ Estimated execution time: ~3-5 minutes total
☐ No breaking changes to existing approved runs
☐ Backward compatibility maintained (old format still works)

To approve:
  tailtrail approve --run-id run-20261019-cmd-registry-impl-7f8a9b

To reject or request changes:
  tailtrail planning feedback --run-id run-20261019-cmd-registry-impl-7f8a9b


IMPLEMENTATION BOUNDARY
─────────────────────────────────────────────────────────────────────────────
Boundary: This plan scopes only proof validation within your local workspace.
          No external APIs, deployments, database changes, or Git commits
          are part of this plan. All changes are implementation-owned and
          reversible. Proofs run only on approved commands.

Data Impact: Start plan size: ~2.5 KB → 1.8 KB (28% reduction)
             Commands deduplicated via registry (single source of truth)
             No user-facing API changes


REQUIREMENTS INVENTORY
─────────────────────────────────────────────────────────────────────────────
REQ-001  CORE-RegistryImpl        Status: needs-proof    Tier: unit,static,integration
REQ-002  TASK-START-UPDATE       Status: needs-proof    Tier: unit,static
REQ-003  EXEC-EVIDENCE-UPDATE    Status: needs-proof    Tier: unit,static
REQ-004  CLOSURE-FIN-UPDATE      Status: needs-proof    Tier: unit,static
REQ-005  FIXTURE-AND-E2E         Status: needs-proof    Tier: integration

═══════════════════════════════════════════════════════════════════════════════

Ready to approve? Review the command registry above, check that all proofs
are runnable on your machine, then run:

  tailtrail approve --run-id run-20261019-cmd-registry-impl-7f8a9b --approved

═══════════════════════════════════════════════════════════════════════════════
```

---

## What User Sees When Approved

```
✓ Planning approved
✓ Lock created: run-20261019-cmd-registry-impl-7f8a9b
✓ Ready to execute proofs

Next step: Run the approved proofs
  
  tailtrail execution-evidence run --approved --root . --run-id run-20261019-cmd-registry-impl-7f8a9b \
    --requirement REQ-001 --tier unit

Or execute all at once:
  
  tailtrail execution-evidence run-all --approved --root . --run-id run-20261019-cmd-registry-impl-7f8a9b
```

---

## Key Visual Elements User Sees

| Element | What User Sees |
|---------|----------------|
| **Command Registry at Top** | 6 commands listed once (not repeated 20+ times) |
| **Requirement Tables** | Clean, scannable 4-column format (Tier, Command ID, Candidate, State) |
| **Proof Reuse** | "cmd-5a6b7c8d9e0f: covers 5 requirements" (instantly see coverage) |
| **File Size Impact** | "Start plan size: ~2.5 KB → 1.8 KB (28% reduction)" |
| **Approval Checklist** | Simple ☐ boxes to verify before approving |
| **Boundary Statement** | Clear statement of what's NOT included (safety) |
| **Next Steps** | Exact command to run after approval |

---

## Why This is Better Than Before

**BEFORE (Without Registry):**
- User sees 6 long commands repeated across 5 requirements × multiple tiers
- "Are cmd-1 and cmd-5 the same?" (has to compare 150-char strings)
- Walls of text, hard to scan
- Takes 2-3 minutes to review

**AFTER (With Registry):**
- User sees command registry at top (6 commands, each with unique short ID)
- "cmd-5a6b7c8d9e0f covers 5 requirements" (instant clarity)
- Clean tables, professional format
- Takes 30 seconds to review ✅

