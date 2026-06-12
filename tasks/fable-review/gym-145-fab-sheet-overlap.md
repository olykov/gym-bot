---
schema_version: 1
id: GYM-145
title: "FAB pokes through scrim when any bottom-sheet is open"
slug: gym-145-fab-sheet-overlap
status: done
priority: high
type: bug-fix
labels: [frontend, ux, sheets, nav]
assignee: null
model: claude-sonnet-4-6
reporter: oleksii
created: 2026-06-12T20:00:00Z
start_date: 2026-06-12T20:00:00Z
finish_date: 2026-06-12T22:00:00Z
updated: 2026-06-12T22:00:00Z
epic: fable-review
depends_on: []
blocks: []
related: [GYM-143, GYM-148]
commits: [ca383e1]
tests: []
design_reports: []
review_reports: []
review: {}
backlog_ref: ""
---

# GYM-145 — FAB pokes through scrim when any bottom-sheet is open

## Problem
The center NavFab (`+` circle) protrudes 16px above the BottomNav bar
(`FAB_LIFT = 16px`). When a bottom-sheet opens with `bottom: NAV_CLEAR`, the
panel's lowest pixel sits at the nav's top edge. The FAB's upper half is in the
same visual region (16px above nav-top), and even with the scrim at z=30 the
FAB's orange circle remains partially visible because the scrim is semi-transparent
(rgba 0,0,0,0.45).

## Fix
Module-level ref-count in `BottomSheet.tsx` (`acquireSheetOpen`): when count > 0,
sets `data-sheet-open="1"` on `<html>`; clears when count drops to 0. Handles
nested sheets correctly. CSS rule `[data-sheet-open] .fab-btn { visibility:hidden }`
suppresses the FAB. `visibility:hidden` keeps the layout slot (no reflow on the
BottomNav) while making it non-interactive and non-visible.

## Files changed
- `apps/web/src/components/ui/BottomSheet.tsx` — `acquireSheetOpen` counter + useEffect
- `apps/web/src/components/shell/NavFab.tsx` — added `.fab-btn` class
- `apps/web/src/index.css` — CSS rule for `[data-sheet-open] .fab-btn`

## Acceptance
- [x] FAB not visible when the record sheet is open (screenshot: iphone15pro-2-sheet-open-fab-hidden.png)
- [x] FAB not visible when any history set-editor or move-sheet is open (same acquireSheetOpen)
- [x] FAB returns immediately when the sheet closes (verified: data-sheet-open cleared)
- [x] Nested sheets: FAB stays hidden while either sheet is open (ref-count handles this)

## Comments

### 2026-06-12T22:00:00Z — done
Implemented and verified. Green gate: lint 0 warnings, 198 tests pass, Vite build clean.
Headless Playwright at 393x852 and 375x667: FAB visibility:hidden while sheet open,
visible again after close. Commit ca383e1.
