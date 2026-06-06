---
schema_version: 1
id: GYM-83
title: "apps/web: picker exercise tiles miss never-logged exercises (uses history-only top-exercises) — render full catalog sorted by frequency"
slug: gym-83-picker-full-exercise-catalog
status: done
priority: high
type: bug-fix
labels: [phase-5, frontend, bug]
assignee: null
model: null
reporter: oleksii
created: 2026-06-06T19:30:00Z
start_date: 2026-06-06T19:30:00Z
finish_date: 2026-06-06T20:30:00Z
updated: 2026-06-06T20:30:00Z
epic: phase-5
depends_on: [GYM-82]
related: [GYM-72]
commits: [35e3036]
tests: []
design_reports: []
review_reports: []
review: {}
backlog_ref: ""
---

# GYM-83 — Picker exercise tiles miss never-logged exercises

## Problem (live, operator)
For Chest the bot shows 15 exercises, the Mini App shows 14. The missing one
("Bench press incline-delete1") exists in the catalog but has NEVER been logged, so it doesn't appear.

## Root cause (diagnosed — NOT a hardcode)
The picker renders exercise TILES from `useTopExercises` = `GET /analytics/top-exercises`, whose query
does an **INNER JOIN on `training`** (`analytics_router.py:274`) → it only returns exercises with at least
one logged set (frequency > 0). Never-logged exercises are invisible. The bot lists the FULL catalog
(`visible_exercises_for_muscle`). Muscles aren't affected — the picker already unions `useMuscles` (the
full muscle catalog) with `top-muscles`. Only the exercise list is history-only.

The full catalog is ALREADY fetched in the picker (`fullExercises = useExercises(selectedMuscleId)` →
`GET /muscles/{id}/exercises`, carrying `id` + `is_mine`) but is used only for the manage-sheet lookup,
not for the displayed tiles.

## Plan (frontend-design-engineer — invoke `/frontend-design:frontend-design`; tile DESIGN does NOT change, keep Chalk & Iron exactly; no new lib)
- Render the exercise tiles from the **full catalog** (`useExercises(selectedMuscleId)` → Exercise[] with
  id + is_mine), NOT from `top-exercises`.
- Preserve the current ordering UX: sort the catalog by training **frequency** (descending) using the
  `top-exercises` frequency data, then alphabetically for the rest (so trained exercises stay on top, as
  today). Keep the top-N + "Show all" expand (§12.9) and the add-inline `+ Exercise`.
- Bonus cleanup: since every tile now comes from `useExercises`, each already has `id` + `is_mine` — drop
  the name→id/is_mine lookup hack used by the manage-sheet (wire id/is_mine straight from the tile's
  Exercise). Keep the manage-sheet (GYM-82), slide-nav, fixed height, prefetch, etc. fully intact.
- Prefetch: on muscle pick, ensure `/muscles/{id}/exercises` is warmed (it already is for the manage
  lookup); keep `top-exercises` prefetch for the frequency sort (or fetch both). No new endpoint.
- Loading/empty/error states unchanged in look. Never-logged exercises now appear in the picker.

## Acceptance criteria
- [ ] The picker shows ALL exercises in a muscle (catalog parity with the bot), including never-logged
      ones; ordering still puts frequently-trained exercises first; tile design unchanged; manage-sheet
      id/is_mine still correct; `npm run build` green.

## Comments

### 2026-06-06T19:30:00Z — task created
Diagnosed from prod (Chest 15 bot vs 14 app). top-exercises is history-only (INNER JOIN training); the
picker should browse the full catalog (already fetched) sorted by frequency.

### 2026-06-06T20:30:00Z — implemented (35e3036)

**Data-source swap**: `exerciseList` in `RecordPicker` now derives from `useExercises(selectedMuscleId)`
(`GET /muscles/{id}/exercises`, returns `Exercise[]` for the full catalog) instead of
`useTopExercises(selectedMuscle)` (`GET /analytics/top-exercises`, INNER JOIN training, history-only).
Never-logged exercises now appear in the picker tile grid, matching the bot's catalog.

**Frequency-sort**: a `frequencyMap: Map<string, number>` is built from `useTopExercises` data (which
is still fetched for this purpose). The full catalog is sorted by frequency descending, then
alphabetically — so trained exercises stay on top exactly as before; never-logged exercises appear at
the bottom in alpha order.

**Loading/error state**: loading/error for the exercise panel now derives from `fullExercises.isLoading`
and `fullExercises.isError` (was `exercises.*`). The tile key is now `ex.id` (stable numeric key)
instead of `ex.name`.

**Manage-sheet cleanup**: `openExerciseManage` previously looked up the exercise by name from
`exerciseByName` Map (name→Exercise). Now it receives the `Exercise` object directly from the tile
iteration (the tiles are `Exercise[]`, so `id` + `is_mine` are always present). The `exerciseByName`
Map and its `useMemo` are removed.

**Prefetch update** (`useRecord.ts`): `prefetchMuscleExercises` now accepts an additional
`muscleId: number | null` parameter and also warms `["muscles", muscleId, "exercises"]` on muscle
pick, so the full catalog is hot before the exercise panel slides in. `fetchExercises` is imported.
`useCreateExercise` already invalidates `["muscles"]` (prefix match) so the full catalog key is
covered on exercise creation.

**Build**: `npm run build` (tsc + vite) green. No type errors.

**Needs live-device pass**: verify Chest shows all 15 exercises (including never-trained ones), that
frequency ordering is preserved for trained exercises, and that long-press → manage-sheet still
correctly identifies the exercise id/is_mine for rename/delete/hide actions.
