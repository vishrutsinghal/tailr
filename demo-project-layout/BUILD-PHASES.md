# Demo Project Build Phases

This is the phased plan for turning the layout into a working demo later.

## Phase 1: Static Demo Skeleton

Create folders, placeholder READMEs, and synthetic docs.

Deliverables:

- workspace README
- demo script
- synthetic data policy
- folder placeholders

Done when:

- the demo project can be explained without running code
- no product source is mixed into demo source

## Phase 2: One Small Service

Implement one tiny service with:

- one endpoint
- one validation function
- one config file
- one or two unit tests
- one intentional bug or quality issue

Recommended first service:

- `services/claims-api`

Done when:

- Navigator can plan a small bug fix
- Test Precision Planner can suggest test cases
- Code Graph Mapper can produce useful read order

## Phase 3: TailTrail Walkthrough

Add presenter-ready TailTrail prompts and expected outcomes for:

- install check
- Navigator repo overview
- Code Graph Mapper generation
- small bug-fix plan
- Test Precision Planner
- review and handoff
- learning capture suggestion
- value report

Done when:

- the demo can be presented without improvising prompts
- every prompt says whether it should write files or stay read-only
- the audience can see which TailTrail feature is being demonstrated

## Phase 4: Synthetic CI And Scanner Evidence

Add local fixture files for:

- Sonar-like quality issue
- SARIF issue
- Trivy or Grype vulnerability issue
- failing test log

Done when:

- CI/Sonar Intelligence can summarize local logs
- Security And Vulnerability Intelligence can summarize structured scanner output
- no live scanner, CI, or network access is required

## Phase 5: AIDLC And Handoff Story

Add lifecycle docs and a realistic change story.

Done when:

- AIDLC can create or update lifecycle artifacts
- handoff can summarize risks, validation, and review notes

## Phase 6: Learning And Value Story

Add curated demo learning fixtures and value report examples.

Done when:

- Navigator can surface advisory learning
- user can approve or ignore learning
- value report can show directional and measured examples without overstating exact ROI

## Phase 7: Multi-Service Expansion

Add second and third small services only after the one-service demo is polished.

Done when:

- cross-service graph is useful
- cross-repo/reference-style scenario is clear
- demo remains understandable in under 15 minutes

## Phase 8: Presenter Package

Create final demo materials:

- presenter script
- audience handout
- expected command outputs
- reset script
- troubleshooting guide

Done when:

- a presenter can run the demo from a fresh clone
- every claim in the demo maps to visible evidence
