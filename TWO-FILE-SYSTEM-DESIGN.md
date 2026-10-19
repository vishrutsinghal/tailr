# TailTrail Two-File Per Session System

## Overview

Instead of generating reports only after work is complete, TailTrail now creates **two comprehensive verbose reports per session**:

1. **Start Plan (Verbose)** - Generated before approval, shows full requirements and command registry
2. **Closure Report (Verbose)** - Generated after completion, shows all proof results and metrics

Both use the same **professional tabular format with all details**, giving users a complete and transparent view at both ends of the workflow.

---

## File Structure

Each TailTrail session creates this directory structure:

```
.tailtrail/runs/{run-id}/
│
├── start-plan-verbose-v1.md              ← REPORT FILE 1
│   ├── Executive Summary
│   ├── Command Reference Registry (all proofs)
│   ├── Validation Requirements (5 requirements with details)
│   ├── Proof Matrix (each requirement with tiers, candidates, state)
│   ├── Architecture & Behaviour Validation (per requirement)
│   ├── Validation Coverage Summary
│   ├── Token Usage Estimate
│   ├── Approval Checklist
│   └── Plan Metadata
│
├── start-report-v1.json                  ← Structured data (same content, JSON)
├── planning/
│   └── lock.json
│
├── [Approval happens here]
│
├── [Proof execution happens here]
│
└── closure-report-verbose-v1.md          ← REPORT FILE 2 (Generated at end)
    ├── Executive Summary (COMPLETE status)
    ├── Proof Execution Summary (all results)
    ├── Unit Test Results (74 assertions, all pass)
    ├── Static Analysis Results (MyPy strict mode)
    ├── Architecture Validation (design principles)
    ├── Behaviour Validation (functional correctness)
    ├── Token Usage & Efficiency Report
    ├── Changes Summary & Code Metrics
    ├── Completion Checklist (all items verified)
    ├── Improvement Metrics & Learning
    ├── Deployment & Next Steps
    └── Closure Metadata
```

---

## File 1: Start Plan (Full Verbose)

### When Generated
- **Timing:** Immediately after planning analysis, before user approval
- **Status:** `awaiting-approval`

### What It Contains

**1. Executive Summary** (2-3 lines)
```
Goal: Implement command registry for TailTrail planning system...
Scope: Implementation-owned updates to 3 consumer files...
Timeline: ~3-5 minutes total execution
Impact: 28-40% data reduction in start plans
```

**2. Command Reference Registry**
```
┏━━━━━━━━━━━━━━━━━━━┳━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━┳━━━━━━━┓
┃ Command ID         ┃ Command                             ┃ Kind  ┃
├────────────────────┼─────────────────────────────────────┼───────┤
│ cmd-a1b2c3d4e5f6   │ python3 -m pytest scripts/test...  │ proof │
│ cmd-7x8y9z0w1v2u   │ python3 -m pytest scripts/test...  │ proof │
│ cmd-5a6b7c8d9e0f   │ python3 -m mypy scripts/ --strict  │ static│
└────────────────────┴─────────────────────────────────────┴───────┘

Registry Statistics:
  Total unique commands: 6
  Data size optimization: 2500 bytes → 1800 bytes (28% reduction)
```

**3. Validation Requirements** (Per each requirement)
```
REQ-001: Core Registry Implementation
Status: needs-proof | Owner: scripts/planning_lock.py
State: required | Tiers: unit, integration, static

Description: Build deterministic command registry...

Architecture Validation:
  ✓ Backward compatible (old format still works)
  ✓ Deterministic IDs (SHA256 ensures consistency)
  ✓ No breaking changes to external APIs

Behaviour Validation:
  ✓ Registry immutable after creation
  ✓ Command resolution deterministic
  ✓ Audit layer validates registry

Proof Matrix - REQ-001 (Coverage: 100% of tiers)
┌──────────────┬──────────────────────┬──────────────┬─────────┐
│ Tier         │ Command ID           │ Candidate    │ State   │
├──────────────┼──────────────────────┼──────────────┼─────────┤
│ unit         │ cmd-a1b2c3d4e5f6     │ tests/unit/  │ existing│
│ static       │ cmd-5a6b7c8d9e0f     │ scripts/     │ existing│
│ integration  │ cmd-2k3l4m5n6o7p     │ scripts/     │ existing│
└──────────────┴──────────────────────┴──────────────┴─────────┘

Execution Profile:
  Unit tests:      ~45 seconds (4 test classes, 32 assertions)
  Static analysis: ~12 seconds (mypy strict mode)
  Integration:     ~3 seconds (py_compile check)
  Total: ~60 seconds
```

**4. Coverage Summary**
```
Total Requirements:  5
Requirements Covered: 5 (100%)

By Tier:
  unit:        5 requirements (4 dedicated + 1 shared)
  static:      5 requirements (1 shared command)
  integration: 1 requirement
  
Proof Command Reuse:
  cmd-5a6b7c8d9e0f: covers 5 requirements (static type checking)
  cmd-a1b2c3d4e5f6: covers 1 requirement (unit tests)
  [etc...]
```

**5. Token Usage Estimate**
```
Phase Breakdown:
  Planning Lock Creation:    ~2,800 tokens
  Command Registry Building: ~1,200 tokens
  Focused Validation Matrix: ~3,400 tokens
  Proof Execution (5 phases): ~18,500 tokens
  Closure & Reporting:       ~2,000 tokens

Total Estimated Tokens: ~30,000 (conservative)
Estimated Cost (GPT-4): ~$0.90 USD
Estimated Time: ~3-5 minutes wall time
```

**6. Approval Checklist**
```
Source & Authority:
  ☐ All 5 requirements scoped correctly
  ☐ Read/write authority on all files
  ☐ Test files exist and runnable

Proof Readiness:
  ☐ Unit test files exist
  ☐ Pytest installed
  ☐ Mypy installed with strict mode
  ☐ All dependencies installed
  ☐ No current test failures
```

### User Benefits

✅ **See complete picture before approval**
- All requirements documented
- All commands visible
- All proofs specified
- Token cost estimated

✅ **Professional presentation**
- Clean tables and sections
- Architecture & behaviour validation listed per requirement
- Execution profiles shown
- Coverage statistics clear

✅ **No surprises**
- User knows what will execute
- User knows estimated time and cost
- User knows what will be tested

---

## File 2: Closure Report (Full Verbose)

### When Generated
- **Timing:** After ALL proofs complete and closure finalized
- **Status:** `complete` or `failed`

### What It Contains

**1. Executive Summary**
```
Goal Status: ✅ COMPLETE

Successfully implemented command registry...
  ✓ 28% reduction in start plan data size
  ✓ Single-source-of-truth for proof commands
  ✓ Full backward compatibility
  ✓ Improved readability
  ✓ All 5 requirements validated and closed

Overall Result: PASS (100% requirements, all proofs successful)

Execution Timeline:
  Start Plan Created:      2026-10-19 14:32:15 UTC (+0s)
  Plan Approved:           2026-10-19 14:33:02 UTC (+47s)
  Proof Execution Started: 2026-10-19 14:33:15 UTC (+60s)
  All Proofs Complete:     2026-10-19 14:38:30 UTC (+375s)
  Closure Finalized:       2026-10-19 14:38:47 UTC (+392s)

Elapsed Wall Time: 6 minutes, 32 seconds (planned: 3-5 minutes)
```

**2. Proof Execution Summary**
```
┏━━━━━━━━━┳━━━━━━━━━━━━┳━━━━━━━━━━━━━━━━━━┳━━━━━━━━┳━━━━━━━━━┳━━━━━━━┓
┃ Req ID  ┃ Description┃ Tiers            ┃ Time   ┃ Status  ┃ Exit  ┃
├─────────┼────────────┼──────────────────┼────────┼─────────┼───────┤
│ REQ-001 │ Registry   │ unit             │ 45s    │ ✅ PASS │ 0     │
│         │ Impl       │ static           │ 12s    │ ✅ PASS │ 0     │
│         │            │ integration      │ 3s     │ ✅ PASS │ 0     │
│ REQ-002 │ task-start │ unit             │ 15s    │ ✅ PASS │ 0     │
│         │            │ static           │ 3s     │ ✅ PASS │ 0     │
│ REQ-003 │ exec-evid  │ unit             │ 10s    │ ✅ PASS │ 0     │
│         │            │ static           │ 3s     │ ✅ PASS │ 0     │
│ REQ-004 │ closure    │ unit             │ 10s    │ ✅ PASS │ 0     │
│         │            │ static           │ 3s     │ ✅ PASS │ 0     │
│ REQ-005 │ Fixtures   │ integration      │ 25s    │ ✅ PASS │ 0     │
├─────────┼────────────┼──────────────────┼────────┼─────────┼───────┤
│ OVERALL │ All Reqs   │ 5 requirements   │ 129s   │ ✅ PASS │ 0     │
└─────────┴────────────┴──────────────────┴────────┴─────────┴───────┘

Total Proof Execution Time: 129 seconds (2 min 9 sec)
Proof Execution Efficiency: 103% of planned (target: 3-5 min, actual: 2m 9s)
```

**3. Unit Test Results** (For each requirement)
```
REQ-001: Core Registry Implementation - Unit Tests
────────────────────────────────────────────────
  Test File: scripts/test_planning_lock.py
  Command: cmd-a1b2c3d4e5f6
  Duration: 45 seconds
  Status: ✅ PASS

  Test Results:
    ├── test_command_id_generation
    │   ├── ✓ Deterministic SHA256 hashing
    │   ├── ✓ Cmd- prefix generation
    │   └── ✓ Hash length validation
    │
    ├── test_registry_building
    │   ├── ✓ Registry dict structure
    │   ├── ✓ Command metadata storage
    │   ├── ✓ Deduplication across tiers
    │   └── ✓ Immutability after creation
    │
    ├── test_projection_with_registry
    │   ├── ✓ Registry included in projection
    │   ├── ✓ Checks use command_id
    │   ├── ✓ Focused validation uses command_id
    │   └── ✓ Fingerprint includes registry
    │
    └── test_backward_compatibility
        ├── ✓ Old format still loads
        ├── ✓ Mixed formats coexist
        └── ✓ Fallback graceful

  Assertions: 32 total
  Coverage: 94% (planning_lock.py)
```

**4. Static Analysis Results**
```
MyPy Type Checking (Strict Mode)
──────────────────────────────────

  Command: cmd-5a6b7c8d9e0f
  Files Checked:
    ✓ scripts/planning_lock.py      - No errors
    ✓ scripts/task-start.py         - No errors
    ✓ scripts/execution-evidence.py - No errors
    ✓ scripts/closure-finalizer.py  - No errors

  Type Safety Report:
    Total lines analyzed:    8,247
    Lines with type hints:   7,891 (95.7%)
    Type errors:             0
    Type warnings:           0
    Any types:               0 (none allowed)

  Status: ✅ PASS (strict mode, 0 errors)
```

**5. Architecture Validation**
```
Design Principles Validation
─────────────────────────────

✅ Single Source of Truth (SSoT)
   ✓ Command registry built once in effective_plan_projection()
   ✓ All references use command_id (not embedded strings)
   ✓ Registry immutable after creation
   ✓ Validation layer ensures consistency

✅ Backward Compatibility
   ✓ Code handles both command and command_id fields
   ✓ Fallback to embedded commands when ID not found
   ✓ Mixed format transitions supported
   ✓ No breaking changes to public APIs

✅ Data Efficiency
   Before Registry: 2,500 bytes
   After Registry:  1,800 bytes
   Reduction:       28% ✅ (target: 25%+)

✅ Deterministic & Reproducible
   ✓ SHA256 hashing is deterministic
   ✓ Registry IDs stable across runs
   ✓ Fingerprints match for identical plans

✅ Layered Validation
   ✓ Layer 1 (planning_lock): Registry built correctly
   ✓ Layer 2 (planning-audit): Registry matches checks
   ✓ Layer 3 (execution-evidence): Commands resolve
   ✓ Layer 4 (closure-finalizer): Receipts linked

Architecture Assessment: ✅ PASS
```

**6. Behaviour Validation**
```
Functional Behaviour Verification
───────────────────────────────────

✅ Requirement Generation
   Same requirements generated? YES ✓
   Same tiers covered? YES ✓

✅ Proof Execution
   Same commands execute? YES ✓
   Same results? YES ✓

✅ Data Integrity
   Audit passes? YES ✓
   Fingerprints match? YES ✓

✅ Multi-Tier Coverage
   Single command not duplicated? YES ✓
   All tiers linked to same ID? YES ✓

✅ Backward Compatibility
   Old plans work? YES ✓
   Mixed format works? YES ✓
   Graceful fallback? YES ✓

Behaviour Assessment: ✅ PASS
```

**7. Token Usage & Efficiency**
```
Token Consumption Breakdown:
  ┌─────────────────────────┬──────────┬──────────┬──────────┐
  │ Phase                   │ Planned  │ Actual   │ Variance │
  ├─────────────────────────┼──────────┼──────────┼──────────┤
  │ Planning Lock Creation  │ 2,800    │ 2,650    │ -5%      │
  │ Registry Building       │ 1,200    │ 1,100    │ -8%      │
  │ Audit Validation        │ 2,100    │ 1,950    │ -7%      │
  │ REQ-001 Execution       │ 4,200    │ 3,980    │ -5%      │
  │ REQ-002 Execution       │ 3,100    │ 2,900    │ -6%      │
  │ REQ-003 Execution       │ 3,400    │ 3,200    │ -6%      │
  │ REQ-004 Execution       │ 3,500    │ 3,150    │ -10%     │
  │ REQ-005 Execution       │ 4,300    │ 3,950    │ -8%      │
  │ Closure & Reporting     │ 2,000    │ 1,850    │ -7%      │
  ├─────────────────────────┼──────────┼──────────┼──────────┤
  │ TOTAL ESTIMATE          │ 30,000   │ 25,730   │ -14%     │
  └─────────────────────────┴──────────┴──────────┴──────────┘

Cost Analysis (GPT-4):
  Estimated Cost:  $0.90 USD
  Actual Cost:     $0.77 USD
  Savings:         $0.13 USD (-14%)
```

**8. Code Metrics**
```
Source Code Changes Summary:
  ┌────────────────────────────┬─────────┐
  │ Metric                     │ Value   │
  ├────────────────────────────┼─────────┤
  │ Total lines added          │ 196     │
  │ Total lines modified       │ 70      │
  │ Net change                 │ +266    │
  │ Files changed              │ 4       │
  │ New functions              │ 2       │
  │ Modified functions         │ 7       │
  │ Breaking changes           │ 0       │
  │ Backward compatible        │ YES ✓   │
  ├────────────────────────────┼─────────┤
  │ Data Efficiency            │         │
  │ Start plan size reduction  │ 28%     │
  │ Registry deduplication     │ 6:1     │
  │ Memory savings per plan    │ 24 KB   │
  └────────────────────────────┴─────────┘
```

**9. Completion Checklist** (All items verified)
```
Requirements Completion:
  ☑ REQ-001 - COMPLETE (all tiers)
  ☑ REQ-002 - COMPLETE (all functions)
  ☑ REQ-003 - COMPLETE (resolution added)
  ☑ REQ-004 - COMPLETE (display logic)
  ☑ REQ-005 - COMPLETE (fixtures updated)

Validation Gates Passed:
  ☑ Unit Tests (74 assertions) - ALL PASS
  ☑ Static Analysis (Mypy) - 0 ERRORS
  ☑ Architecture Validation - PASS
  ☑ Behaviour Validation - PASS
  ☑ Backward Compatibility - VERIFIED
  ☑ Type Safety - 95%+ coverage
  ☑ Data Integrity - VERIFIED
  ☑ Integration Tests (E2E) - PASS
```

**10. Improvement Metrics**
```
Performance Improvements:
  Start plan generation time: 2.1s → 1.8s (-14%)
  Audit validation time: 1.8s → 1.5s (-17%)
  User review time: ~3m → ~1m (-67%)
  Overall plan-to-closure: 6m 32s (within target)

User Experience Improvements:
  ✅ Start plan readability - Significantly improved
  ✅ Duplicate detection - Instant (visual ID matching)
  ✅ Terminal output - Reduced width (compact tables)
  ✅ Approval speed - Faster (-67%)
  ✅ Report clarity - Cleaner separation of concerns
```

**11. Deployment & Next Steps**
```
Changes Ready for:
  ✅ Merge to main branch
  ✅ Release in next version
  ✅ Production deployment
  ✅ User rollout

Rollout Checklist:
  ☑ Code review completed
  ☑ All tests passing
  ☑ Type safety verified
  ☑ Backward compatibility confirmed
  ☑ Performance validated
  ☑ Documentation updated
  ☑ No deployment blockers
```

### User Benefits

✅ **Complete transparency of what happened**
- Every proof result visible
- Every test assertion listed
- Every architecture principle validated
- Every behaviour aspect verified

✅ **Professional accountability**
- Token usage exactly tracked
- Code metrics precise
- Architecture validated
- Quality metrics clear

✅ **Ready for approval/deployment**
- All checklists completed
- Next steps clear
- No surprises or gaps
- Complete audit trail

---

## Key Differences from Previous System

| Aspect | Before | After (Two-File System) |
|--------|--------|------------------------|
| **Start Report** | Generated only if verbose mode | Always generated (full verbose) |
| **Closure Report** | Generated at end only | Generated at end (full verbose) |
| **User Visibility** | Limited to summary | Full details at both ends |
| **Decision Support** | Minimal (limited info) | Complete (command registry + full architecture) |
| **Audit Trail** | Basic | Comprehensive (every detail tracked) |
| **Professional Appeal** | Minimal | Professional (tables, metrics, validation) |
| **Token Cost** | Hidden | Visible (estimated and actual) |
| **Architecture Details** | Not shown | Shown per requirement |
| **Behaviour Validation** | Not shown | Shown per requirement |
| **Code Metrics** | Not tracked | Comprehensive (lines, functions, coverage) |

---

## File Naming Convention

```
{report-type}-verbose-{schema-version}.md

Examples:
  start-plan-verbose-v1.md      ← Start report
  closure-report-verbose-v1.md  ← Closure report
  
Structured counterparts (JSON):
  start-report-v1.json          ← Machine-readable start data
  completion-report-v1.json     ← Machine-readable closure data
```

---

## Storage & Access

### During Session (Before Approval)
User can read start-plan-verbose file:
```bash
cat .tailtrail/runs/run-20261019/start-plan-verbose-v1.md
```

### After Completion
Both files available:
```bash
# View what was planned
cat .tailtrail/runs/run-20261019/start-plan-verbose-v1.md

# View what was completed
cat .tailtrail/runs/run-20261019/closure-report-verbose-v1.md
```

### For Sharing/Review
HTML or PDF versions can be generated:
```bash
tailtrail report export --run-id run-20261019 --format html
tailtrail report export --run-id run-20261019 --format pdf
```

---

## Summary

This **two-file per session system** provides:

✅ **Transparency** - Complete visibility at start and end  
✅ **Accountability** - Every metric tracked and documented  
✅ **Professional** - Tabular format with all details  
✅ **User-Friendly** - Clean sections and checklists  
✅ **Audit-Ready** - Complete trail for compliance  
✅ **Decision Support** - Everything needed to approve/reject  

Users get a **start-to-finish narrative** of their work with professional metrics at both ends!

