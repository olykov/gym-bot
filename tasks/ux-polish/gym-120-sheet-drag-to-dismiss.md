---
schema_version: 1
id: GYM-120
title: "BottomSheet: drag-to-dismiss via grab handle (handle is currently decorative)"
slug: gym-120-sheet-drag-to-dismiss
status: review
priority: medium
type: feature
labels: [frontend, ux, motion, sheets]
assignee: null
model: null
reporter: oleksii
created: 2026-06-12T09:20:00Z
start_date: 2026-06-12T15:05:00Z
finish_date: null
updated: 2026-06-12T15:05:00Z
epic: ux-polish
depends_on: []
blocks: []
related: [GYM-119]
commits: []
tests: []
design_reports: ["docs/review/01-uiux-review.md"]
review_reports: []
review: {}
backlog_ref: ""
---

# GYM-120 — Sheet drag-to-dismiss

## Problem
Review doc 01 §3. The `<BottomSheet>` grab handle signals "draggable" but isn't — a broken
mobile-native expectation. Scrim/Back/Done are the only close paths.

## Solution
- Pointer-drag on the handle zone (handle + top padding strip ONLY, so it never fights the
  body's internal scroll — critical for `fixedHeight` record sheet) translates the panel;
  release past ~30% height or velocity threshold → close; otherwise spring back (180ms,
  `--ease-out-soft`).
- Scrim opacity follows drag progress.
- Reduced-motion: drag still works (it is direct manipulation, not motion), but snap-back/
  close are instant.
- No gesture library — pointer events, same style as `SetRow` swipe; use
  `setPointerCapture` from the start.
- UI work → `frontend-design-engineer` agent + `frontend-design` plugin.

## Acceptance criteria
- [ ] Dragging the handle down dismisses; mid-drag release springs back. *(implemented; needs a real-device gesture check)*
- [x] Body scroll inside the sheet never triggers dismissal. *(structural: the drag handlers live ONLY on the handle strip above the body — the body region has no drag listeners)*
- [ ] Works for both auto-height (editor/manage) and fixedHeight (record) sheets. *(one shared panel path in code; gesture itself needs a device check on both sheet kinds)*

## Comments

### 2026-06-12T09:20:00Z — task created

### 2026-06-12T15:05:00Z — implemented (agent wave 4a)

- Files: `apps/web/src/components/ui/useSheetDrag.ts` (new hook), `apps/web/src/components/ui/BottomSheet.tsx` (drag zone + style wiring).
- Choices:
  - Drag zone = grab handle + the panel's top padding strip only (a dedicated `touch-none` wrapper above the body), so the gesture can never intercept the body's internal scroll — critical for the fixedHeight record sheet.
  - Pointer events with guarded `setPointerCapture` (SetRow idiom); downward-only translate (clamped ≥ 0).
  - Dismiss on release past 30% of panel height (`CLOSE_FRACTION`) OR a downward flick ≥ 0.5 px/ms over the trailing 100ms of move samples (with a 24px minimum travel guard); otherwise spring back 180ms `var(--ease-out-soft)`.
  - Scrim opacity follows drag progress via inline style; because `.sheet-scrim`/`.sheet-panel` entrance animations use `forwards` fill (which beats inline styles), the hook pins `animation: none` inline from the first drag for the rest of the open lifetime (re-enabling would replay the slide-up).
  - Light impact haptic once per gesture when the close threshold is crossed mid-drag.
  - Reduced-motion: drag still follows the finger (direct manipulation); snap-back/close are instant (no transition). Close is the existing instant unmount via `onClose`.
  - BottomSheet stays at 281 lines (<500) with the gesture extracted to `useSheetDrag`.
- Verification: bench `tsc --noEmit`, `eslint --max-warnings 0`, `vitest run` (81 tests), `vite build` — all pass. Real-device drag feel not yet verified.
- No file overlap with GYM-122 (separate commit-safe).
- Suggested commit: `Add BottomSheet drag-to-dismiss via grab handle`
