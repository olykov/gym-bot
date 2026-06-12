---
schema_version: 1
id: GYM-147
title: "Stray light strip at top of bottom-sheet in dark mode"
slug: gym-147-sheet-top-strip
status: done
priority: medium
type: bug-fix
labels: [frontend, ux, sheets, dark-mode]
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
related: [GYM-143]
commits: [87ca6ee]
tests: []
design_reports: []
review_reports: []
review: {}
backlog_ref: ""
---

# GYM-147 — Stray light strip at top of bottom-sheet in dark mode

## Problem
The sheet panel has `rounded-t-lg border-t border-hairline`. In dark mode the
browser anti-aliases the CSS `border-t` on the rounded corner against the dark
viewport background (not the panel surface), producing a bright white/light
sliver along the panel's top edge.

## Fix
Removed `border-t border-hairline` from the panel class. Added an `inset
box-shadow` to `.sheet-panel` in `index.css`:
`inset 0 1px 0 0 color-mix(in srgb, var(--hint) 10%, transparent)`.

An inset shadow is composited AGAINST the panel's own `bg-bg` surface, not
the viewport behind it — so the edge stays subtle in dark mode (no white
artifact). Visually identical to the hairline border in light mode.

## Files changed
- `apps/web/src/components/ui/BottomSheet.tsx` — removed `border-t border-hairline`
- `apps/web/src/index.css` — `.sheet-panel` gains `inset 0 1px 0 0 ...` box-shadow

## Acceptance
- [x] No visible bright white/light strip at the top of any sheet in dark mode (screenshot: iphone15pro-2-sheet-open-fab-hidden.png and -3-gym146-recap-headers.png)
- [x] Subtle top-edge definition still readable (inset shadow on panel bg, visible in both themes)

## Comments

### 2026-06-12T22:00:00Z — done
Panel border-top=0px confirmed by Playwright. Inset box-shadow composites against
panel surface — no bright edge artifact. Screenshots show clean dark rounded top.
Commit 87ca6ee.
