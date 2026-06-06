---
schema_version: 1
id: GYM-83
title: "apps/web: picker exercise tiles miss never-logged exercises (uses history-only top-exercises) — render full catalog sorted by frequency"
slug: gym-83-picker-full-exercise-catalog
status: in_progress
priority: high
type: bug-fix
labels: [phase-5, frontend, bug]
assignee: null
model: null
reporter: oleksii
created: 2026-06-06T19:30:00Z
start_date: 2026-06-06T19:30:00Z
finish_date: null
updated: 2026-06-06T19:30:00Z
epic: phase-5
depends_on: [GYM-82]
related: [GYM-72]
commits: []
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
