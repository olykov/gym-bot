---
schema_version: 1
id: GYM-68
title: "apps/web: 5-item bottom nav + raised center FAB + Profile stub"
slug: gym-68-nav-5item-fab
status: review
priority: high
type: feature
labels: [phase-5, frontend, design]
assignee: null
model: null
reporter: oleksii
created: 2026-06-05T06:00:00Z
start_date: 2026-06-05T06:30:00Z
finish_date: 2026-06-04T00:00:00Z
updated: 2026-06-04T00:00:00Z
epic: phase-5
depends_on: [GYM-65]
blocks: [GYM-69]
related: [GYM-64]
commits: [9f9e573d32373623d37883a774c17d934e694c9e]
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

### 2026-06-04 — implemented (commit 9f9e573)
Built the §12.1 5-item bar. Invoked the `frontend-design` plugin before the UI work (applied
"Chalk & Iron" + §12.1/§12.9 — `--accent` FAB, one accent, tokens only).

**Nav structure.** `<BottomNav>` is a 5-slot flex row: route tabs Dashboard · Progress in visual
order, then a fixed-width center SPACER (`CENTER_SLOT_PX = FAB_SIZE + 24` = 80px, giving ≥12px gap
each side so the 56px circle + 1px ring clears the adjacent ≥44px tabs, §12.8), then History ·
Profile. The center holds the absolutely-positioned `<NavFab>`. `navConfig` now lists the four route
tabs (added `Profile` with a head+shoulders person glyph → `/profile`); the `+` is NOT a `NavTab`.
Distribution stays deferred. `/profile` route renders `<Profile>` (a single `<EmptyState>` "PROFILE /
Coming soon", zero queries) inside the shared `<AppShell>`.

**Indicator (ref-measured).** Replaced the `width=100/tabCount` + `translateX=index*100%` math (which
breaks with the non-uniform center slot) with a measured offset: each route tab carries a ref, and a
`useLayoutEffect` measures the active tab's `getBoundingClientRect()` left edge + width relative to the
flex row, then sets the indicator's `left`/`width` directly (transition-all, 180ms, reduced-motion
gated). Recomputes on route change + window resize, plus a first-mount rAF pass after fonts settle.
The center spacer carries no ref, so a center tap never moves the indicator.

**FAB left pluggable for GYM-69.** `<NavFab>` takes an optional `onRecord?: () => void` passed through
from `<BottomNav onRecord>`. On press it fires `hapticImpact("medium")` then calls `onRecord` if
provided, else a `console.debug` placeholder. It is a `<button>` (action), not a `NavLink` — no route
or active state. GYM-69 wires the real record-sheet open by passing `onRecord` down from the shell;
no change to NavFab/BottomNav internals needed.

**Safe-area (§12.8).** Added a `--fab-lift: 16px` token (kept in sync with `FAB_LIFT` in NavFab); the
FAB lifts upward via `top: -16px`. `<Container>` bottom padding now adds `+ var(--fab-lift)` on top of
`--nav-h` so nothing interactive at the content bottom hides under the raised circle. The bar's own
bottom inset `max(env(safe-area-inset-bottom), --tg-safe-bottom)` is unchanged (FAB lifts into
content, never down into the home indicator).

**Build:** `cd apps/web && npm run build` (tsc + vite) PASSES — 718 modules, no TS errors (only the
pre-existing >500kB chunk-size advisory, unrelated).

**Self-review:** 5 slots render; indicator covers only the 4 tabs (ref-measured); FAB raised +
`--accent` + medium haptic + placeholder `onClick`; `/profile` stub route; content cleared below the
FAB; tokens adapt light+dark. **Needs a live device pass:** verify the medium haptic and the FAB
lift/clearance on a real notched device + Telegram fullscreen inset, and the indicator alignment after
the web-font swap on-device.
