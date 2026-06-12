---
schema_version: 1
id: GYM-148
title: "Content behind sheet not visibly de-emphasized (sheet lacks foreground focus)"
slug: gym-148-sheet-backdrop-defocus
status: done
priority: medium
type: feature
labels: [frontend, ux, sheets, motion]
assignee: null
model: claude-sonnet-4-6
reporter: oleksii
created: 2026-06-12T20:00:00Z
start_date: 2026-06-12T20:00:00Z
finish_date: 2026-06-12T22:00:00Z
updated: 2026-06-12T22:00:00Z
epic: fable-review
depends_on: [GYM-145]
blocks: []
related: [GYM-143, GYM-145]
commits: [ca383e1]
tests: []
design_reports: []
review_reports: []
review: {}
backlog_ref: ""
---

# GYM-148 — Content behind sheet not visibly de-emphasized

## Problem
When a bottom-sheet opens, the page behind is dimmed by the scrim
(rgba 0,0,0,0.45) but does not feel de-emphasized — the content behind still
reads at full scale and brightness, so the sheet doesn't clearly read as the
focused layer.

## Chosen technique: scale + opacity dim on `.shell-content`

**Not backdrop-filter blur.** Reason: `backdrop-filter: blur()` forces a
compositor layer on every frame and produces visible stuttering on mid-range
Android (Snapdragon 400/600 era), which is a significant portion of Telegram
users. It is also unsupported in some Telegram WebView builds.

**Instead:** when `data-sheet-open="1"` is set on `<html>` (already done by
GYM-145's `acquireSheetOpen`), the `.shell-content` wrapper (content area only
— NOT the header or nav chrome) scales to 0.97 and dims to 0.82 opacity.

- `transform: scale(0.97)` + `opacity: 0.82` are GPU-composited — zero
  layout/paint cost on both iOS and Android.
- `transform-origin: top center` — the page shrinks from the top, aligned with
  the sheet's entry point, creating a natural depth cue.
- `will-change: transform, opacity` hints the GPU layer.
- 220ms ease-out-soft transition (same cadence as the sheet slide-in).
- Scrim opacity also increased from 0.45 → 0.55 for a stronger visual separation.

**prefers-reduced-motion:** scale (motion) is removed; opacity dim is retained
(it is informational, not decorative) but instant (no transition). The sheet
panel remains at full opacity in all cases — only the BEHIND content is dimmed.

## Applied uniformly
All sheets use `<BottomSheet>` → all trigger `acquireSheetOpen` → all get the
de-emphasis. No per-sheet wiring needed.

## Files changed
- `apps/web/src/components/shell/AppShell.tsx` — added `.shell-content` class
- `apps/web/src/index.css` — de-emphasis rule + reduced-motion override
- `apps/web/src/index.css` — scrim opacity 0.45 → 0.55

## Acceptance
- [x] Page visibly scales back and dims when any sheet opens (screenshot: iphone15pro-2-sheet-open-fab-hidden.png — DASHBOARD text visibly scaled/dimmed behind sheet)
- [x] Sheet panel stays at full opacity (not dimmed — only .shell-content is targeted)
- [x] Transition smooth: 220ms ease-out-soft, GPU-composited transform+opacity
- [x] Under prefers-reduced-motion: scale=none, opacity=0.82 instant (no transition)

## Comments

### 2026-06-12T22:00:00Z — done
Playwright confirmed: .shell-content transform=applied, opacity=0.82 when sheet open.
Screenshots show visible depth separation between page and sheet at both viewports.
Commit ca383e1.
