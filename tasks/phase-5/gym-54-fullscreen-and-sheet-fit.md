---
schema_version: 1
id: GYM-54
title: "apps/web: Telegram fullscreen mode + bottom-sheet fit (no clipping)"
slug: gym-54-fullscreen-and-sheet-fit
status: review
priority: high
type: bug-fix
labels: [phase-5, frontend, design]
assignee: null
model: null
reporter: oleksii
created: 2026-06-04T23:45:00Z
start_date: 2026-06-04T23:45:00Z
finish_date: 2026-06-04T23:59:00Z
updated: 2026-06-04T23:59:00Z
epic: phase-5
depends_on: [GYM-53]
blocks: []
related: [GYM-12, GYM-41]
commits: [d9ed262e4ddcc6a9e31471059f393e046edba73a]
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

### 2026-06-04T23:59:00Z — implemented (commit d9ed262), status → review
`frontend-design` plugin invoked before the UI/layout work (HARD RULE); applied "Chalk & Iron" +
`docs/frontend-spec.md` (no re-pick), tokens-only.

**Fullscreen wiring (`telegram/webapp.ts`).** Bumped `@twa-dev/sdk` `^7.10.0` → `^8.0.0`
(resolved 8.0.2, Bot API 8.0); `npm install` clean. On boot, after `ready()`, a new
`requestFullscreenWithFallback()` guards on `WebApp.isVersionAtLeast('8.0')` + presence of
`requestFullscreen`, calls it in try/catch, and falls back to `WebApp.expand()` on
desktop / old clients / any throw. Subscribed to `fullscreenChanged`, `safeAreaChanged`,
`contentSafeAreaChanged` (plus existing theme/viewport). Removed the unused `mainButton`
wrapper export (no longer referenced anywhere).

**Safe-area approach.** New `syncSafeAreaVars()` reads `WebApp.contentSafeAreaInset` (clearance
under Telegram's overlaid close/menu controls in fullscreen) + `WebApp.safeAreaInset` (device
notch / home-indicator), defensively coerces each field, and writes CSS vars:
`--tg-content-top/bottom` (device+content inset = header/footer clearance) and
`--tg-safe-top/bottom/left/right` (device only). Shell chrome now pads with
`max(env(safe-area-inset-*), var(--tg-*))`: `AppHeader` top, `Container` top (incl. header height)
+ bottom, `BottomNav` bottom. Vars default to `0px` outside Telegram so `max()` degrades to plain
`env()` (fullsize / browser unaffected). This is what keeps the fixed header BELOW the Telegram
close button in fullscreen.

**Sheet + Save change.** `<BottomSheet>` panel is now a flex column capped at
`calc(100dvh − max(env(safe-area-inset-top), --tg-content-top) − 24px)` with an
`overflow-y:auto` body → a tall sheet scrolls internally, never clips. Dropped the native
MainButton for the editor entirely; `SetEditor` SAVE is a sticky in-sheet button
(`position:sticky; bottom:0`, `--accent` fill, `--button-text`, ≥48px, disabled when
unchanged/invalid — same validity logic). Header Delete + two-step confirm (GYM-53) untouched;
haptics kept (success on save, warning on delete-confirm). Updated `frontend-spec.md` §4
(fullscreen + content-safe-area handling) and §11.4 (in-sheet sticky Save; noted the native
MainButton + bottom-sheet clips on real devices).

**Build:** `npm install && npm run build` (tsc + vite) green — 715 modules, no TS errors. The
only warning is the pre-existing ECharts chunk-size note (unrelated).

**Needs a real Telegram device pass (honest):** fullscreen + the exact Telegram-control clearance
are device/client-specific and can't be exercised in CI/browser (the SDK no-ops `requestFullscreen`
and reports zero insets off-device). The wiring handles it by driving header/shell/nav padding off
the *live* `contentSafeAreaInset`/`safeAreaInset` and re-reading on `fullscreenChanged` /
`safeAreaChanged` / `contentSafeAreaChanged`, so whatever insets the real client reports are applied
reactively; the `max(env(), var(--tg-*))` fallback guarantees fullsize/browser stay correct. Verify
on a real client: (1) header sits clear of the Telegram close/menu in fullscreen, light+dark;
(2) the set-editor sheet shows Weight + Reps + sticky Save + header Delete with nothing clipped and
scrolls internally on a short viewport.
