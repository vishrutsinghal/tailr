# Sample Start Plan After Registry Implementation

## Scenario
A typical Python project with:
- Requirement 1: Unit + Integration tests (same command)
- Requirement 2: Static analysis + Type checking (same command)  
- Requirement 3: Behaviour tests (different command)

---

## Before (Current Format)

```json
{
  "run_id": "run-20261019-abc123xyz",
  "status": "awaiting-approval",
  "report": {
    "navigator": {
      "requirements": [
        {
          "requirement_uid": "REQ-001",
          "display_id": "CORE-UnitTests",
          "title": "Core unit and integration tests",
          "validation_contract": {
            "tiers": ["unit", "integration"],
            "commands": [
              "python3 -m pytest tests/unit/ -v --tb=short --junitxml=reports/unit.xml"
            ],
            "checks": [
              {
                "kind": "proof",
                "command": "python3 -m pytest tests/unit/ -v --tb=short --junitxml=reports/unit.xml",
                "tiers": ["unit", "integration"],
                "candidate_paths": ["tests/unit/"]
              }
            ]
          }
        },
        {
          "requirement_uid": "REQ-002",
          "display_id": "CORE-QualityGates",
          "title": "Code quality gates",
          "validation_contract": {
            "tiers": ["static", "linting"],
            "commands": [
              "python3 -m pylint src/ --rcfile=.pylintrc",
              "python3 -m mypy src/ --strict --junit-xml=reports/types.xml"
            ],
            "checks": [
              {
                "kind": "static",
                "command": "python3 -m pylint src/ --rcfile=.pylintrc",
                "tiers": ["static"],
                "candidate_paths": ["src/"]
              },
              {
                "kind": "static",
                "command": "python3 -m mypy src/ --strict --junit-xml=reports/types.xml",
                "tiers": ["linting"],
                "candidate_paths": ["src/"]
              }
            ]
          }
        },
        {
          "requirement_uid": "REQ-003",
          "display_id": "CORE-Behaviour",
          "title": "Behaviour-driven testing",
          "validation_contract": {
            "tiers": ["behaviour"],
            "commands": [
              "python3 -m behave features/ -f json -o reports/behaviour.json"
            ],
            "checks": [
              {
                "kind": "proof",
                "command": "python3 -m behave features/ -f json -o reports/behaviour.json",
                "tiers": ["behaviour"],
                "candidate_paths": ["features/"]
              }
            ]
          }
        }
      ],
      "focused_validation": [
        {
          "requirement_id": "REQ-001",
          "tier": "unit",
          "command": "python3 -m pytest tests/unit/ -v --tb=short --junitxml=reports/unit.xml",
          "candidate": "tests/unit/",
          "candidate_state": "existing"
        },
        {
          "requirement_id": "REQ-001",
          "tier": "integration",
          "command": "python3 -m pytest tests/unit/ -v --tb=short --junitxml=reports/unit.xml",
          "candidate": "tests/unit/",
          "candidate_state": "existing"
        },
        {
          "requirement_id": "REQ-002",
          "tier": "static",
          "command": "python3 -m pylint src/ --rcfile=.pylintrc",
          "candidate": "src/",
          "candidate_state": "existing"
        },
        {
          "requirement_id": "REQ-002",
          "tier": "linting",
          "command": "python3 -m mypy src/ --strict --junit-xml=reports/types.xml",
          "candidate": "src/",
          "candidate_state": "existing"
        },
        {
          "requirement_id": "REQ-003",
          "tier": "behaviour",
          "command": "python3 -m behave features/ -f json -o reports/behaviour.json",
          "candidate": "features/",
          "candidate_state": "existing"
        }
      ]
    }
  }
}
```

**File Size:** ~2.5 KB (lots of command duplication)

---

## After (With Registry Implementation)

```json
{
  "run_id": "run-20261019-abc123xyz",
  "status": "awaiting-approval",
  "report": {
    "navigator": {
      "command_registry": {
        "cmd-a1b2c3d4e5f6": {
          "command": "python3 -m pytest tests/unit/ -v --tb=short --junitxml=reports/unit.xml",
          "kind": "proof"
        },
        "cmd-7x8y9z0w1v2": {
          "command": "python3 -m pylint src/ --rcfile=.pylintrc",
          "kind": "static"
        },
        "cmd-3q4r5s6t7u8v": {
          "command": "python3 -m mypy src/ --strict --junit-xml=reports/types.xml",
          "kind": "static"
        },
        "cmd-9m0n1o2p3q4r": {
          "command": "python3 -m behave features/ -f json -o reports/behaviour.json",
          "kind": "proof"
        }
      },
      "requirements": [
        {
          "requirement_uid": "REQ-001",
          "display_id": "CORE-UnitTests",
          "title": "Core unit and integration tests",
          "validation_contract": {
            "tiers": ["unit", "integration"],
            "commands": [
              "python3 -m pytest tests/unit/ -v --tb=short --junitxml=reports/unit.xml"
            ],
            "checks": [
              {
                "kind": "proof",
                "command_id": "cmd-a1b2c3d4e5f6",
                "tiers": ["unit", "integration"],
                "candidate_paths": ["tests/unit/"]
              }
            ],
            "command_registry": {
              "cmd-a1b2c3d4e5f6": {
                "command": "python3 -m pytest tests/unit/ -v --tb=short --junitxml=reports/unit.xml",
                "kind": "proof"
              }
            }
          }
        },
        {
          "requirement_uid": "REQ-002",
          "display_id": "CORE-QualityGates",
          "title": "Code quality gates",
          "validation_contract": {
            "tiers": ["static", "linting"],
            "commands": [
              "python3 -m pylint src/ --rcfile=.pylintrc",
              "python3 -m mypy src/ --strict --junit-xml=reports/types.xml"
            ],
            "checks": [
              {
                "kind": "static",
                "command_id": "cmd-7x8y9z0w1v2",
                "tiers": ["static"],
                "candidate_paths": ["src/"]
              },
              {
                "kind": "static",
                "command_id": "cmd-3q4r5s6t7u8v",
                "tiers": ["linting"],
                "candidate_paths": ["src/"]
              }
            ],
            "command_registry": {
              "cmd-7x8y9z0w1v2": {
                "command": "python3 -m pylint src/ --rcfile=.pylintrc",
                "kind": "static"
              },
              "cmd-3q4r5s6t7u8v": {
                "command": "python3 -m mypy src/ --strict --junit-xml=reports/types.xml",
                "kind": "static"
              }
            }
          }
        },
        {
          "requirement_uid": "REQ-003",
          "display_id": "CORE-Behaviour",
          "title": "Behaviour-driven testing",
          "validation_contract": {
            "tiers": ["behaviour"],
            "commands": [
              "python3 -m behave features/ -f json -o reports/behaviour.json"
            ],
            "checks": [
              {
                "kind": "proof",
                "command_id": "cmd-9m0n1o2p3q4r",
                "tiers": ["behaviour"],
                "candidate_paths": ["features/"]
              }
            ],
            "command_registry": {
              "cmd-9m0n1o2p3q4r": {
                "command": "python3 -m behave features/ -f json -o reports/behaviour.json",
                "kind": "proof"
              }
            }
          }
        }
      ],
      "focused_validation": [
        {
          "requirement_id": "REQ-001",
          "tier": "unit",
          "command_id": "cmd-a1b2c3d4e5f6",
          "candidate": "tests/unit/",
          "candidate_state": "existing"
        },
        {
          "requirement_id": "REQ-001",
          "tier": "integration",
          "command_id": "cmd-a1b2c3d4e5f6",
          "candidate": "tests/unit/",
          "candidate_state": "existing"
        },
        {
          "requirement_id": "REQ-002",
          "tier": "static",
          "command_id": "cmd-7x8y9z0w1v2",
          "candidate": "src/",
          "candidate_state": "existing"
        },
        {
          "requirement_id": "REQ-002",
          "tier": "linting",
          "command_id": "cmd-3q4r5s6t7u8v",
          "candidate": "src/",
          "candidate_state": "existing"
        },
        {
          "requirement_id": "REQ-003",
          "tier": "behaviour",
          "command_id": "cmd-9m0n1o2p3q4r",
          "candidate": "features/",
          "candidate_state": "existing"
        }
      ]
    }
  }
}
```

**File Size:** ~1.8 KB (28% smaller due to IDs replacing long commands)

---

## Human-Readable Comparison

### Before (Terminal Output)

```
┌────────────────────────────────────────────────────────────────────────┐
│ TailTrail Start Plan - run-20261019-abc123xyz                          │
│ Status: Awaiting Approval                                              │
└────────────────────────────────────────────────────────────────────────┘

REQUIREMENT 1: CORE-UnitTests
  Title: Core unit and integration tests
  Validation Tiers: unit, integration
  Proof Command: python3 -m pytest tests/unit/ -v --tb=short --junitxml=reports/unit.xml
  Focused Validation Matrix:
    - Tier: unit
      Command: python3 -m pytest tests/unit/ -v --tb=short --junitxml=reports/unit.xml
      Candidate: tests/unit/ (existing)
    
    - Tier: integration
      Command: python3 -m pytest tests/unit/ -v --tb=short --junitxml=reports/unit.xml
      Candidate: tests/unit/ (existing)

REQUIREMENT 2: CORE-QualityGates
  Title: Code quality gates
  Validation Tiers: static, linting
  Proof Commands:
    1. python3 -m pylint src/ --rcfile=.pylintrc
    2. python3 -m mypy src/ --strict --junit-xml=reports/types.xml
  Focused Validation Matrix:
    - Tier: static
      Command: python3 -m pylint src/ --rcfile=.pylintrc
      Candidate: src/ (existing)
    
    - Tier: linting
      Command: python3 -m mypy src/ --strict --junit-xml=reports/types.xml
      Candidate: src/ (existing)

REQUIREMENT 3: CORE-Behaviour
  Title: Behaviour-driven testing
  Validation Tiers: behaviour
  Proof Command: python3 -m behave features/ -f json -o reports/behaviour.json
  Focused Validation Matrix:
    - Tier: behaviour
      Command: python3 -m behave features/ -f json -o reports/behaviour.json
      Candidate: features/ (existing)

[VERY LONG, LOTS OF COMMAND DUPLICATION]
```

---

### After (Terminal Output)

```
┌────────────────────────────────────────────────────────────────────────┐
│ TailTrail Start Plan - run-20261019-abc123xyz                          │
│ Status: Awaiting Approval                                              │
└────────────────────────────────────────────────────────────────────────┘

COMMAND REFERENCE REGISTRY
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
  cmd-a1b2c3d4e5f6:
    python3 -m pytest tests/unit/ -v --tb=short --junitxml=reports/unit.xml
  
  cmd-7x8y9z0w1v2:
    python3 -m pylint src/ --rcfile=.pylintrc
  
  cmd-3q4r5s6t7u8v:
    python3 -m mypy src/ --strict --junit-xml=reports/types.xml
  
  cmd-9m0n1o2p3q4r:
    python3 -m behave features/ -f json -o reports/behaviour.json


VALIDATION REQUIREMENTS
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

REQUIREMENT 1: CORE-UnitTests
  Title: Core unit and integration tests
  Tiers: unit, integration
  Proof: cmd-a1b2c3d4e5f6
  
  Focused Validation:
    Tier        │ Command ID       │ Candidate       │ State
    ────────────┼──────────────────┼─────────────────┼──────────
    unit        │ cmd-a1b2c3d4e5f6 │ tests/unit/     │ existing
    integration │ cmd-a1b2c3d4e5f6 │ tests/unit/     │ existing


REQUIREMENT 2: CORE-QualityGates
  Title: Code quality gates
  Tiers: static, linting
  Proofs: cmd-7x8y9z0w1v2, cmd-3q4r5s6t7u8v
  
  Focused Validation:
    Tier    │ Command ID       │ Candidate │ State
    ────────┼──────────────────┼───────────┼──────────
    static  │ cmd-7x8y9z0w1v2  │ src/      │ existing
    linting │ cmd-3q4r5s6t7u8v │ src/      │ existing


REQUIREMENT 3: CORE-Behaviour
  Title: Behaviour-driven testing
  Tiers: behaviour
  Proof: cmd-9m0n1o2p3q4r
  
  Focused Validation:
    Tier      │ Command ID       │ Candidate │ State
    ──────────┼──────────────────┼───────────┼──────────
    behaviour │ cmd-9m0n1o2p3q4r │ features/ │ existing
```

---

## Key Visual Improvements

| Aspect | Before | After |
|--------|--------|-------|
| **Command visibility** | ❌ Scattered throughout | ✅ Centralized registry at top |
| **Duplicate detection** | ❌ "Are these the same?" | ✅ Instant (same ID = same command) |
| **Table width** | ❌ Very wide (~100+ chars) | ✅ Compact (~40 chars) |
| **Scrolling** | ❌ Lots of horizontal scroll | ✅ Clean, readable |
| **Command lookup** | ❌ Copy/paste searching | ✅ Look up by ID in registry |
| **JSON file size** | ❌ 2.5 KB | ✅ 1.8 KB (28% smaller) |
| **Professional appearance** | ❌ Cluttered | ✅ Clean, organized |

---

## User Approval Flow

### Before
User gets a wall of text with long commands repeated everywhere, hard to review.

### After
User sees:
1. **Command registry** at top (what tests will run)
2. **Compact requirement table** (which tests cover which tiers)
3. **Easy to approve** (clear what's being tested)

Much faster approval process! ✅

