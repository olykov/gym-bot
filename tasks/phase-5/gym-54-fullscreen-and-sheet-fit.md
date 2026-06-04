---
schema_version: 1
id: GYM-54
title: "apps/web: Telegram fullscreen mode + bottom-sheet fit (no clipping)"
slug: gym-54-fullscreen-and-sheet-fit
status: in_progress
priority: high
type: bug-fix
labels: [phase-5, frontend, design]
assignee: null
model: null
reporter: oleksii
created: 2026-06-04T23:45:00Z
start_date: 2026-06-04T23:45:00Z
finish_date: null
updated: 2026-06-04T23:45:00Z
epic: phase-5
depends_on: [GYM-53]
blocks: []
related: [GYM-12, GYM-41]
commits: []
tests: []
design_reports: []
review_reports: []
review: {}
backlog_ref: ""
---

# GYM-54 — Fullscreen mode + bottom-sheet fit

## Problem
Operator-reported on the live Mini App:
1. **Wants fullscreen, gets fullsize.** The app only calls `WebApp.expand()` (full height, Telegram
   header still shown). The operator wants true **fullscreen mode** (Bot API 8.0
   `requestFullscreen()`). Current `@twa-dev/sdk` is `^7.10.0` (Bot API 7.x) — no fullscreen API.
2. **Set-editor sheet clips.** The bottom-sheet's lower content (the Reps stepper field/buttons) is
   cut off at the bottom — the Telegram native **MainButton (SAVE)** overlays the viewport bottom and
   the sheet has no max-height/scroll. The MainButton has now caused two layout bugs (GYM-53 #1 + this).

## Plan (frontend-design-engineer — MUST invoke the `frontend-design` plugin; obey docs/frontend-spec.md)
1. **Fullscreen:** bump `@twa-dev/sdk` to `^8.x` (same allowed lib, needed for Bot API 8.0). On boot,
   `requestFullscreen()` with a **graceful fallback** to `expand()` (desktop/old clients reject it).
   Handle `fullscreenChanged`. Wire Telegram **`contentSafeAreaInset` + `safeAreaInset`** (Bot API 8.0)
   → CSS vars; the fixed header + content must clear the Telegram controls that overlay the top in
   fullscreen (subscribe to `safeAreaChanged`/`contentSafeAreaChanged`). Update `docs/frontend-spec.md`
   §4 with the fullscreen + safe-area handling.
2. **Sheet fit:** give `<BottomSheet>` a `max-height` (viewport − top inset) with internal
   `overflow-y:auto` so content NEVER clips; and **resolve the MainButton conflict by moving Save INTO
   the sheet** — a sticky in-sheet "SAVE" button (token-only, accent per §9.3) above the safe-area,
   drop the native `MainButton` for the editor. Keep the header Delete + two-step confirm (GYM-53).
   Update `docs/frontend-spec.md` §11.4 to reflect in-sheet Save (the native MainButton + bottom-sheet
   combination clips on real devices).

## Acceptance criteria
- [ ] App opens in fullscreen (fallback clean where unsupported); header/content clear the Telegram
      controls (no overlap) in fullscreen, light+dark.
- [ ] Set editor fully visible (Weight + Reps + Save + Delete), nothing clipped; sheet scrolls if tall.
- [ ] Build green; plugin invoked.

## Comments

### 2026-06-04T23:45:00Z — operator-reported, in progress
Fullscreen = Bot API 8.0 (SDK bump). The MainButton-in-bottom-sheet pattern is the root of the
clipping — moving Save in-sheet makes the sheet self-contained and predictable.
