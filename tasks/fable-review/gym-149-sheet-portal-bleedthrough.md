---
schema_version: 1
id: GYM-149
title: "Sheet bleeds through on device: de-emphasis opacity/transform on the sheet's own ancestor"
slug: gym-149-sheet-portal-bleedthrough
status: done
priority: critical
type: bug-fix
labels: [frontend, design, sheet, shell, miniapp, regression]
assignee: null
model: null
reporter: oleksii
created: 2026-06-12T19:20:00Z
start_date: 2026-06-12T19:20:00Z
finish_date: 2026-06-12T19:35:00Z
updated: 2026-06-12T19:35:00Z
epic: fable-review
depends_on: []
blocks: []
related: [GYM-147, GYM-148]
commits: [7ba1bf3]
tests: []
design_reports: []
review_reports: []
review: {}
backlog_ref: ""
---

# GYM-149 — Sheet bleeds through; top strip persists

## Problem (operator, on-device — regression from GYM-147/148)
Opening the History set editor on a real device: the page content behind (other
exercises/sets) bled THROUGH the sheet — text over the fields and even over the SAVE
button — and the sheet drifted/misaligned. Also the GYM-147 top "strip" was still
visible (the inset-shadow attempt read as the same strip).

## Root cause
1. `BottomSheet` rendered INLINE, so it was a DESCENDANT of `.shell-content`.
2. GYM-148 de-emphasis set `opacity: 0.82` + `transform: scale(0.97)` on
   `.shell-content`. `opacity < 1` on an ancestor makes the sheet itself
   translucent (page bleeds through); `transform` on an ancestor makes the sheet's
   `position: fixed` resolve against that ancestor (it scales/drifts instead of
   pinning to the viewport). Headless missed it because the test mock had little
   content directly behind the sheet, so 18% translucency over dark looked opaque.

## Fix
- Portal `BottomSheet` to `document.body` via `createPortal` — the sheet is now a
  sibling of `.shell-content`, fully opaque and viewport-fixed; only the page behind
  is scaled+dimmed. :root CSS vars still apply.
- Remove the `.sheet-panel` top edge entirely (no `border-t`, no inset highlight) —
  just the card drop-shadow. The grab handle alone signals the top.

## Verification (headless, dark theme, realistic iPhone + Telegram insets, content behind)
At 393×852 and 375×667, with a full day (4 exercises) behind the sheet:
- `.shell-content.contains(.sheet-panel)` === false (portaled out)
- min ancestor opacity of the sheet === 1 (not translucent)
- `elementFromPoint` at mid-sheet hits the sheet, not a background row (opaque)
- `.shell-content` still has transform + opacity 0.82 (de-emphasis intact)
- top-edge zoom: no light strip

## Comments

### 2026-06-12T19:35:00Z — fixed directly (orchestrator), prod-breaking regression
Fixed inline rather than re-delegating: prod History-edit was unusable and the root
cause was a precise CSS/React architecture bug (fixed overlay inside a transformed,
opacity-reduced ancestor). Verified with content BEHIND the sheet — the gap that let
GYM-148 ship broken.
