---
schema_version: 1
id: GYM-62
title: "apps/web: Progress pickers by frequency + open on top exercise's By Weight chart"
slug: gym-62-progress-default-frequency
status: done
priority: medium
type: feature
labels: [phase-5, frontend, design]
assignee: null
model: null
reporter: oleksii
created: 2026-06-05T01:00:00Z
start_date: 2026-06-05T02:00:00Z
finish_date: 2026-06-04T00:00:00Z
updated: 2026-06-04T00:00:00Z
epic: phase-5
depends_on: [GYM-60, GYM-61]
blocks: []
related: [GYM-12]
commits: [41ba9f0f758761d6c10a932d7b7c1e3e49a806f5]
tests: []
design_reports: []
review_reports: []
review: {}
backlog_ref: ""
---

# GYM-62 — Progress: frequency pickers + non-empty default

## Problem
Progress opens on an empty pick-screen and the pickers are alphabetical. Operator wants them ordered
by HIS training frequency and the page to open straight on the By Weight chart of his most-frequent
exercise.

## Plan (frontend-design-engineer — MUST invoke the `frontend-design` plugin; obey docs/frontend-spec.md)
- Muscle picker → `GET /analytics/top-muscles` (frequency desc). Exercise picker →
  `GET /analytics/top-exercises?muscle=&limit=<all>` (frequency desc). Replace the alphabetical
  list-endpoint calls in Progress.
- **Default on mount:** auto-select `top-muscles[0]` → load its exercises → auto-select
  `top-exercises[0]` → render the **By Weight** chart immediately (no empty pick-screen). Most-frequent
  exercise in the most-frequent muscle ≈ the user's top exercise.
- **Empty state:** a brand-new user with no trainings (empty top-muscles) keeps the existing
  `<EmptyState>` ("log a set in the bot…"), no auto-select, no extra queries.
- Keep the By Weight | By Set toggle (GYM-57) and the design consistent; tokens only.

## Acceptance criteria
- [ ] Progress opens on the By Weight chart of the most-frequent exercise; pickers ordered by my
      frequency; new-user empty state intact. Build green; plugin invoked.

## Comments

### 2026-06-05T01:00:00Z — task created
Mostly wiring to the new endpoints + the auto-select-on-mount default.

### 2026-06-04T00:00:00Z — implemented (status → review)
Invoked the `frontend-design` plugin before the UI pass (confirmed). Stayed inside the committed
Chalk & Iron direction — this is a data-rewiring task, no new aesthetic was re-picked.

What I wired (`apps/web/` only, commit `41ba9f0`):
- `api/analytics.ts`: added `fetchTopMuscles()` → `GET /analytics/top-muscles` and
  `fetchTopExercises(muscle, limit)` → `GET /analytics/top-exercises?muscle&limit=200`, typed via
  `Schemas["TopMuscle"|"TopExercise"]` from `@api-contract`.
- `hooks/useAnalytics.ts`: added `useTopMuscles()` and `useTopExercises(muscle)` (TanStack Query,
  cached, `staleTime: 5m`; exercises query disabled until a muscle name exists). `limit=200` sentinel
  pulls ALL of a muscle's exercises. Both render the endpoint's frequency order verbatim — no client
  re-sort.
- `pages/Progress.tsx`: muscle picker ← top-muscles, exercise picker ← top-exercises. Pickers are
  name-keyed (the progress endpoint takes names); the chip `id` is the position in the frequency row.

Auto-select-on-mount logic (non-empty default): a `didDefaultMuscle` ref auto-picks `top-muscles[0]`
once, only while `muscle` is null. Then a `defaultedExerciseFor` ref (keyed by muscle name) auto-picks
`top-exercises[0]` once that muscle's row loads, only while `exercise` is null — so the page opens
straight on the By Weight chart of the most-frequent exercise. Manual picks are never clobbered (the
guards bail when a selection already exists); `pickMuscle` resets the exercise default ref so the new
muscle's top exercise auto-selects, while a manual exercise pick stands. While auto-select is in
flight `ChartArea` shows `SkeletonChart`, never a blank pick-screen.

Empty-state handling: a brand-new user → `top-muscles` is `[]` → an early return renders the existing
`<EmptyState>` ("No trainings yet"), the exercise/progress queries stay disabled, and both effects
no-op on the empty array (no auto-select, no extra queries). The By Weight | By Set toggle (GYM-57)
is untouched (default By Weight).

Build: `cd apps/web && npm run build` (tsc + vite) PASSES — 0 type errors, 716 modules, built in
~2.85s (the >500 kB chunk note is the pre-existing vendor-bundle warning, not new).

Needs a live device pass: confirm on a real Telegram client that the chart paints immediately on
open (top muscle → top exercise) with no empty flash, that manual chip taps switch muscle/exercise
without the auto-select re-firing, and light+dark + reduced-motion chip/skeleton rendering.
