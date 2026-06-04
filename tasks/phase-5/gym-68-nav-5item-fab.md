---
schema_version: 1
id: GYM-68
title: "apps/web: 5-item bottom nav + raised center FAB + Profile stub"
slug: gym-68-nav-5item-fab
status: backlog
priority: high
type: feature
labels: [phase-5, frontend, design]
assignee: null
model: null
reporter: oleksii
created: 2026-06-05T06:00:00Z
start_date: null
finish_date: null
updated: 2026-06-05T06:00:00Z
epic: phase-5
depends_on: [GYM-65]
blocks: [GYM-69]
related: [GYM-64]
commits: []
tests: []
design_reports: []
review_reports: []
review: {}
backlog_ref: ""
---

# GYM-68 — 5-item nav + center FAB

## Problem
Grow the bottom nav from 3 tabs to the §12.1 5-item bar with a raised center action button + a Profile
stub, without breaking the §2/§10.1 shell contract or the sliding indicator.

## Plan (frontend-design-engineer — MUST invoke the `frontend-design` plugin; obey docs/frontend-spec.md §12.1)
- `<BottomNav>`: 4 route tabs (Dashboard · Progress · History · Profile) + a center `<NavFab>` between
  index 1 and 2 (a fixed-width spacer slot; FAB absolutely positioned/raised over it). The sliding
  indicator is measured over the 4 route tabs only (ref-measured offset, not `index*100%`), skipping the
  center.
- `<NavFab>`: raised circular `--accent` button (≥56px, lifted ~16px, `--button-text` `+`, shadow token,
  `--bg` ring), `impactOccurred('medium')` on press; an `onClick` that triggers the record sheet (wire a
  prop/callback or a shared open-record handler — the sheet itself is GYM-69; here, stub the open with a
  no-op/placeholder so the nav ships independently). NOT a NavLink, no route/active state.
- `navConfig`: add the `Profile` tab (person glyph) → route `/profile` rendering `<ProfileStub>`
  (`<EmptyState>` "PROFILE / Coming soon", zero queries). Distribution stays deferred.
- Safe-area: keep the bar's bottom padding `max(env(safe-area-inset-bottom), var(--tg-safe-bottom))`;
  the `<Container>` bottom padding must add the FAB lift on top of nav height so content isn't hidden
  under the raised circle (§12.8).

## Acceptance criteria
- [ ] 5-item bar renders; FAB raised + on-brand; indicator covers only the 4 tabs; Profile stub route;
      content not hidden under the FAB; light+dark; build green; plugin invoked.

## Comments

### 2026-06-05T06:00:00Z — task created
The FAB's open-record action is fully wired in GYM-69; here it ships with a placeholder handler.
