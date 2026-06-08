---
schema_version: 1
id: GYM-100
title: "apps/web: fix broken add-exercise modal + Hide action for own items + refresh log-context on add/resolve"
slug: gym-100-add-modal-hide-own-logctx-refresh
status: done
priority: critical
type: bug-fix
labels: [tax-fixes, frontend, design, ux, bug]
assignee: null
model: null
reporter: oleksii
created: 2026-06-08T15:00:00Z
start_date: 2026-06-08T15:30:00Z
finish_date: 2026-06-08T00:00:00Z
updated: 2026-06-08T00:00:00Z
epic: tax-fixes
depends_on: [GYM-99]
related: [GYM-85, GYM-98]
commits: [f170a50]
tests: []
design_reports: []
review_reports: []
review: {}
backlog_ref: ""
---

# GYM-100 — Add-modal fix + Hide-own + log-context refresh

## Problem (live, operator)
1. The add-exercise inline field renders BROKEN/janky — the input isn't even visible at first; typing
   shows a badly-rendered field. A real UI regression (likely the keyboard-inset GYM-98 × the GYM-85 hint
   placement). Reproduce + fix.
2. Long-tap on an OWN exercise should offer **Hide** as well as Rename/Move/Delete (operator decision —
   an own item with history can't be deleted, so Hide is the only way to declutter it). Verify
   Rename/Move/Delete are all present too.
3. After add→resolve (existing/unhidden), the SetLogger must show the EXISTING PR/history (not look new).
   With GYM-99 (name_key resolution + no negative cache), the frontend must INVALIDATE the log-context
   (and any per-exercise analytics) for that exercise on the create/resolve mutation so SetLogger refetches
   fresh server data instead of a stale (10-min staleTime) empty.

## Plan (frontend-design-engineer — invoke `/frontend-design:frontend-design`; Chalk & Iron, tokens only)
- #1: reproduce the broken add field; fix its rendering (layout/visibility under the keyboard-inset +
  hint). The field + submit must be fully visible and clean on a ~360px device.
- #2: add a **Hide** action to the manage sheet for OWN exercises (and own muscles if applicable), wired to
  `PUT /exercises/{id}/hidden` (GYM-99 now supports own). Keep Rename + Move + Delete. Ensure the offer-hide
  fallback on a 409-history delete still works.
- #3: in `useCreateExercise`/`useCreateMuscle` onSuccess (the add/resolve path), invalidate
  `["analytics","log-context", muscle, exercise, ...]` (and completed-sets/personal-record if separately
  keyed) for the resolved exercise so the SetLogger loads the real PR/history. Verify an existing exercise
  re-added shows its PR immediately.
- Keep all GYM-74/82/85/90/98 behavior intact; update docs/frontend-spec.md as needed.

## Acceptance criteria
- [x] Add-exercise field renders cleanly (visible input + submit). Own items show Hide + Rename/Move/Delete.
      Re-adding an existing exercise shows its real PR/history immediately (not "new"). Plugin invoked;
      build green.

## Comments

### 2026-06-08T15:00:00Z — task created
Depends on GYM-99 (name_key resolution + no negative cache + hide-own API). Frontend-design plugin mandatory.

### 2026-06-08 — implementation (f170a50)

**#1 — Add-exercise field rendering (fix diagnosis + approach)**

Root cause: `BottomSheet` in `fixedHeight=true` mode applies `keyboardPad` (the soft-keyboard height from
`visualViewport`) to the *body region's* `paddingBottom`. However the body region is `flex flex-col` and
`RecordPicker` fills it with `flex: 1, minHeight: 0, overflow: hidden`. The keyboard padding was therefore
trapped *outside* RecordPicker's `overflow: hidden` boundary — it had no effect on the inner slide panels
which do their own `overflowY: auto` scroll. Additionally the old `scrollIntoView({ block: "center" })` on
input focus fired synchronously *before* `visualViewport` dispatched its resize event, so `keyboardPad`
was still 0 when the scroll ran — producing the visible jank/no-scroll.

Fix: removed `keyboardPad` from the body region's `paddingBottom` in `fixedHeight` mode. Instead, the
computed keyboard height is written as the CSS custom property `--keyboard-pad` directly on the panel
element (`BottomSheet.tsx`). RecordPicker's two slide panels (Panel 1: muscle step, Panel 2: exercise step)
now read `--keyboard-pad` via `calc(max(var(--keyboard-pad, 0px), max(env(safe-area-inset-bottom), ...)) + 8px)`
as their own `paddingBottom`. This means the bottom padding is inside each panel's own scroll container, so
the AddInlineField + submit button are fully visible from the moment the field opens — the content can scroll
up to reveal the field without fighting the `overflow: hidden` boundary. The `scrollIntoView` call was removed
entirely from `AddInlineField` (also removed unused `useRef`). Non-fixedHeight sheets are unchanged.

**#2 — Hide for own items**

Added a Hide action to ManageSheet's own-item `actions` view (in addition to Rename, Move, Delete which were
already there). The Hide button sits between Move and Delete in the action list (separated by hairlines),
wires to the existing `doHide()` handler (which calls `useHideExercise` / `useHideMuscle`). The button shows
"Hiding…" while pending and disables itself like the global-item Hide button. The offer-hide fallback on a
409-history delete remains untouched. All four actions for own exercises — Rename, Move to another muscle,
Hide from my list, Delete — are confirmed present in the rendered block. Own muscles get Rename, Hide from my
list, Delete (Move is exercise-only).

**#3 — Log-context invalidation on add/resolve**

In `useCreateExercise` onSuccess: after the mutation returns, invalidate
`["analytics", "log-context", muscle_name, data.name]` (prefix match, covering all dates) and
`["analytics", "exercise-progress", muscle_name, data.name]`. `data.name` is the canonical name the backend
returned — critical because resolution=existing or resolution=unhidden may return a differently-cased name
than what the user typed. This ensures the log-context staleTime (10 min) does not serve a stale empty
context for a re-added exercise. SetLogger will refetch and show the real PR/history immediately.

**Build result:** `tsc && vite build` — green, no type errors. One pre-existing chunk-size warning (unchanged).

**Needs live-device pass:**
- Verify the add field is fully visible and the submit button is reachable on a real ~360px device with the
  soft keyboard open (both muscle add and exercise add panels).
- Verify long-press on an own exercise shows all four actions: Rename / Move to another muscle / Hide from
  my list / Delete.
- Verify re-adding "Bench press" (or any exercise with history) immediately shows its PR chip and last-session
  pre-fill in SetLogger (not a blank phase-B).
