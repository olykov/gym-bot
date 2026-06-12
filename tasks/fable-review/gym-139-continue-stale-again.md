---
schema_version: 1
id: GYM-139
title: "Record: Continue tile still stale after logging (shows previous exercise)"
slug: gym-139-continue-stale-again
status: done
priority: high
type: bug-fix
labels: [frontend,data,record,bug,freshness]
assignee: null
model: null
reporter: oleksii
created: 2026-06-12T08:00:00Z
start_date: 2026-06-12T08:00:00Z
finish_date: 2026-06-12T00:00:00Z
updated: 2026-06-12T00:00:00Z
epic: fable-review
depends_on: []
blocks: []
related: []
commits: [4aee664]
tests:
  - "apps/web/src/components/record/usePickerData.test.ts — deriveContinueExercise (8 tests)"
design_reports: []
review_reports: []
review: {}
backlog_ref: ""
---

# GYM-139 — Record: Continue tile still stale after logging (shows previous exercise)

## Problem (operator, on-device review of the Fable batch)
- Logged 5 sets of Bench Press today, but the Continue tile still shows the PREVIOUS exercise
  (Abdominal Curl). NOTE: the GYM-115 freshness fix IS present (`useTrainingDay`: `staleTime:0` +
  `refetchOnMount:'always'`; `prefetchPickerReads` day `staleTime:0`; `useCreateTraining` invalidates
  `training.day(today)`), and `usePickerData.continueExercise` correctly derives max `training_id` from
  `day.data`. So the day query is not reflecting the just-logged sets. Likely gaps: the picker stays
  MOUNTED during logging so `refetchOnMount` never re-triggers AND the invalidation isn't forcing an
  active refetch; OR a `today`-key / timezone mismatch between the log mutation and the day query.
  Reproduce (log A then B, return to picker → Continue must be B); diagnose + fix; verify it updates live.

## Confirmed Root Cause

The issue was NOT a stale cache, a timezone mismatch, or a missing invalidation.
The GYM-115 freshness plumbing works correctly:
- `RecordSheet` keeps `useTrainingDay(today)` active throughout Phase B (it mounts it
  unconditionally, not just in Phase A), so the `invalidateQueries` in `useCreateTraining.onSettled`
  hits an active observer and triggers a real refetch.
- The day data IS fresh and includes all today's sets (including Bench Press) when the user
  returns to the picker.

**The bug is in `deriveContinueExercise` (the old inline useMemo in `usePickerData`):**

`training_id` on each `TrainingSet` is `uuid4().hex` — a 32-character hex string like
`"a3f2c1d4e5b6a7f8c9d0e1f2a3b4c5d6"`. The old derivation called `Number(s.training_id)`,
which always yields `NaN`. `Number.isFinite(NaN)` is `false`, so every set got `key = -Infinity`.
The loop never advanced `best`, `best` remained `null`, and the fallback `if (!best && exs[0])`
returned `exs[0]` — the **alphabetically first** exercise in the server response (server orders by
`e.name, t.set`). Abdominal Curl comes before Bench Press alphabetically, so it always "won".

## Fix (4aee664, branch fable-fix/continue)

**Three files changed, one test file added:**

1. `apps/web/src/components/record/usePickerData.ts`
   - Extracted `deriveContinueExercise(exercises, lastLoggedExercise)` as a pure exported function
     (testable, no React dependency).
   - Tier 1: if `lastLoggedExercise` (session override) is provided AND the exercise is in today's
     data, return it — no UUID comparison, authoritative from the mutation path.
   - Tier 2: fall back to `exs[0]` (first in server array). Unchanged from pre-bug-introduction
     behavior; correct for fresh opens where no session override exists.
   - `usePickerData` now accepts `lastLoggedExercise: ContinueExercise | null = null` as a third
     parameter and passes it to `deriveContinueExercise`.

2. `apps/web/src/components/record/RecordSheet.tsx`
   - Added `lastLoggedExercise` state (`ContinueExercise | null`, cleared on sheet close).
   - `handleSetLogged` now also calls `setLastLoggedExercise({ muscleName: entry.muscle,
     exerciseName: entry.exercise })` on each saved set.
   - Passes `lastLoggedExercise` to `<RecordPicker>`.

3. `apps/web/src/components/record/RecordPicker.tsx`
   - Added `lastLoggedExercise: ContinueExercise | null` to `RecordPickerProps`.
   - Passes it through to `usePickerData(today, selectedMuscle, lastLoggedExercise)`.

4. `apps/web/src/components/record/usePickerData.test.ts` (NEW — 8 tests)
   - Covers: null inputs, session override wins over alphabetically-first fallback, override not
     in today's data falls back gracefully, same exercise name in two muscles matches by both
     fields, uuid `training_id`s don't affect the result.

## Residual limitation (server-side, out of scope)

For **cross-session** opens (user logs via the bot then opens the Mini App), `lastLoggedExercise`
is null (no session state). The Continue tile falls back to `exs[0]` — alphabetically first —
because the API orders by `e.name, t.set` rather than by insertion time. A server-side fix would
reorder the `get_training_day` query by `MAX(t.date) DESC` per exercise group. That is core-api's
domain and out of scope for this frontend task.

## Green gate
- `npm ci` ✅
- `npm run build` ✅ (vite build + tsc)
- `npm run lint` ✅ (eslint, 0 warnings)
- `npm run test` ✅ — 193 tests pass (185 pre-existing + 8 new)
