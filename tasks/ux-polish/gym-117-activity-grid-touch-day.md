---
schema_version: 1
id: GYM-117
title: "Bug: activity grid tooltip is title-only — unreachable on touch devices"
slug: gym-117-activity-grid-touch-day
status: review
priority: high
type: bug-fix
labels: [frontend, ux, dashboard, mobile]
assignee: null
model: null
reporter: oleksii
created: 2026-06-12T09:05:00Z
start_date: 2026-06-12T14:45:00Z
finish_date: null
updated: 2026-06-12T14:45:00Z
epic: ux-polish
depends_on: []
blocks: []
related: []
commits: []
tests: ["apps/web/src/components/dashboard/activityGridModel.test.ts"]
design_reports: ["docs/review/01-uiux-review.md"]
review_reports: []
review: {}
backlog_ref: ""
---

# GYM-117 — Activity grid: tap-to-inspect a day

## Problem
Review doc 01 §1.2. `ActivityGrid` cells expose data only via `title={cellTooltip(cell)}` —
`title` never shows on touch, and the app is ~99.9% phone sessions. Users cannot see
"N sets on <date>" at all.

## Solution
- Tap a cell → select it (accent ring reuse) + a detail line under the grid:
  `12 sets · MON 02 JUN` (Sora, tabular). Tap elsewhere/again deselects.
- If the day has trainings: second tap (or a chevron in the detail line) navigates to
  `/history/:date` — the grid becomes an entry point into History.
- Keep `title` for desktop hover. Month labels along the top axis are GYM-123 (separate).
- UI work → `frontend-design-engineer` agent + `frontend-design` plugin.

## Acceptance criteria
- [ ] On touch, tapping any non-padding cell shows its sets count + date; works in dark.
      (implemented + unit-tested; the touch interaction and dark-mode ring/contrast need an
      on-device visual check)
- [x] Tap-through to `/history/:date` for days with sets.
- [x] No layout shift; reduced-motion fine; empty cells selectable but show "0 sets".

## Comments

### 2026-06-12T09:05:00Z — task created
P0 #3 from the review plan.

### 2026-06-12T14:45:00Z — implemented (agent wave 3b)
Files:
- `apps/web/src/components/dashboard/activityGridModel.ts` — new pure helper
  `cellDetailText(cell, today)` → `12 sets · MON 02 JUN` (reuses `formatDayHeading` from
  `components/history/historyWindow` so the line matches the History day heading, incl. the
  year suffix for past years).
- `apps/web/src/components/dashboard/ActivityGrid.tsx` — non-padding cells are now
  `<button>`s (aria-label = tooltip, aria-pressed; `title` kept for desktop hover). Tap →
  select + light impact haptic; tap same cell or anywhere else in the grid (rail/gaps,
  via container click + cell stopPropagation) → deselect. Selection is keyed by DATE so a
  refetch never orphans it.
- `apps/web/src/components/dashboard/activityGridModel.test.ts` — 5 new cases for
  `cellDetailText` (padding → null, singular/plural, zero sets, year suffix).

Design notes:
- Selected ring = gapped double ring `0 0 0 2px var(--bg), 0 0 0 4px var(--accent)` +
  zIndex lift; today keeps its solid 2px `--accent` ring — both stay distinguishable even
  on the same cell. Ring-only (no scale) so there is nothing to gate under reduced motion.
- Detail row is ALWAYS reserved (min-h 44px, shows a quiet "Tap a day to inspect" hint
  when nothing is selected) → zero layout shift on select, and it doubles as
  discoverability for the tap affordance.
- Days with sets: the detail line is a ≥44px `press-95` button (Sora, `.tabular`) with the
  DayCard-style hint-colored SVG chevron → `useTransitionNavigate("/history/:date",
  "forward")` + light impact haptic. Empty days: plain text `0 sets · <date>`, no
  affordance, no navigation.
- Tokens-only: ramp/ring colors via CSS vars, spacing via the sanctioned scale,
  `min-h-[44px]` matches the existing idiom (DayCard/ErrorState/BottomNav).

Verification: bench `npx tsc --noEmit` + `npm run lint` (max-warnings 0) + `npm run test`
(72 tests, 6 files, all green) + `npm run build` — all pass.

Suggested commit: `Add tap-to-inspect day selection to activity grid`
File overlap with GYM-118 (same wave): none — disjoint file sets.
