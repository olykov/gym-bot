---
schema_version: 1
id: GYM-154
title: "Open sheet dims the bottom nav too; nav should stay bright (no gap) or be hidden"
slug: gym-154-nav-not-dimmed-under-sheet
status: done
start_date: 2026-06-13T00:00:00Z
finish_date: 2026-06-13T00:00:00Z
priority: medium
type: feature
labels: [frontend, design, sheet, shell, miniapp]
assignee: null
model: null
reporter: oleksii
created: 2026-06-13T14:50:00Z
updated: 2026-06-13T14:50:00Z
epic: fable-review
depends_on: []
blocks: []
related: [GYM-148, GYM-149]
commits: [a33b7ad]
tests: []
design_reports: []
review_reports: []
review: {}
backlog_ref: ""
---

# GYM-154 — Bottom nav is dimmed under an open sheet

## Problem (operator)
The GYM-148/149 sheet de-emphasis darkens the page behind an open sheet (good), but the
scrim (`.sheet-scrim absolute inset-0`, portaled at z-sheet) also covers the BOTTOM NAV
below the sheet. So an open sheet (which is NOT full-height) sits between a dimmed top and
a dimmed nav strip — it reads as "cut off top and bottom, sticking out". The nav row over
which the sheet rises looks darkened.

## Decision (operator) — start with OPTION 1
1. **Option 1 (try first):** do NOT dim the bottom nav — keep it at normal brightness while
   a sheet is open. Watch for GAPS between the nav top and the sheet bottom: a gap would
   show as a weird dark strip (the sheet's wrapper bottom = --nav-h, so the sheet bottom must
   meet the nav top flush). Must work in BOTH light and dark themes.
2. **Option 2 (fallback, if operator dislikes 1):** fully HIDE the bottom nav while a sheet
   is open.

## Plan (frontend-design + plugin)
Designer decides the cleanest mechanism: e.g. scrim height stops at the nav top (scrim covers
viewport − nav-h), or the nav renders above the scrim at full opacity. Ensure: nav not dimmed,
no dark gap/seam between nav and sheet, FAB stays hidden (GYM-145), light + dark correct.
Verify headless dark + realistic insets + content behind: measure that the nav strip is at
full brightness and the sheet bottom is flush with the nav top (no scrimmed gap).

## Comments

### 2026-06-13T14:50:00Z — filed; operator wants option 1 first, delegated to design agent

### 2026-06-13T00:00:00Z — done (a33b7ad)
Implemented Option 1. Mechanism: limit the `.sheet-scrim` bottom to `NAV_CLEAR`
(`calc(var(--nav-h) + max(env(safe-area-inset-bottom), var(--tg-safe-bottom, 0px)))`),
the same expression used by the panel wrapper. The scrim now covers only the viewport
area above the nav. The panel bottom is flush with the scrim bottom — no dark gap or
seam. GYM-145 FAB-hidden behavior unaffected. Headless Playwright verification passed
both dark and light themes: nav luminance delta 1.0 lum (dark) / 1.4 lum (light)
(threshold 15); scrim bottom=758, nav top=757, gap=-1px (flush). 205 unit tests pass.
