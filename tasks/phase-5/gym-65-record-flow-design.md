---
schema_version: 1
id: GYM-65
title: "Design: spec §12 — 5-item nav + center FAB + smooth record-training flow (ultrathink, plugin)"
slug: gym-65-record-flow-design
status: in_progress
priority: high
type: research
labels: [phase-5, frontend, design]
assignee: null
model: null
reporter: oleksii
created: 2026-06-05T04:00:00Z
start_date: 2026-06-05T04:00:00Z
finish_date: null
updated: 2026-06-05T04:00:00Z
epic: phase-5
depends_on: [GYM-64]
blocks: []
related: [GYM-12]
commits: []
tests: []
design_reports: []
review_reports: []
review: {}
backlog_ref: ""
---

# GYM-65 — Record-flow design (spec §12)

## Problem
Need a concrete, buildable design for: (a) the 5-item bottom nav with a raised center "+", and (b) a
super-smooth record-training flow — proposed via the frontend-design plugin before any build.

## Plan
Design-agent (frontend-design plugin, ultrathink) appends `docs/frontend-spec.md` §12 "Record training":
- **Nav:** Dashboard · Progress · [+] · History · Profile (stub). Center = elevated `--accent` circular
  CTA (distinct shape), opens the record sheet (not a route); sliding indicator skips the center; fits
  §2/§9 shell + safe areas. Profile = stub route/empty-state.
- **Record flow (smooth):** recents/frequent exercises first (1-tap) + muscle browse fallback + add
  inline; in-context set logging with weight/reps PRE-FILLED (last set / PR), auto next set#, big
  steppers + in-sheet sticky Save (§11.4), Save→haptic→auto-advance→repeat; PR-beat celebration.
- States/empty/error/reduced-motion; reuse §11 BottomSheet/Stepper primitives; note API additions
  (recent-exercises, last-set pre-fill) vs MVP-with-existing.
- Orchestrator reviews + shows the operator before build.

## Acceptance criteria
- [ ] §12 appended (nav + record flow), concrete + buildable; plugin invoked; API needs flagged.

## Comments

### 2026-06-05T04:00:00Z — task created
Proposal only — no app code. Operator approves the UX before the build wave.
