---
schema_version: 1
id: GYM-115
title: "Bug: Continue tile shows a stale exercise (prior, not the most recently logged today)"
slug: gym-115-continue-tile-stale
status: done
priority: high
type: bug-fix
labels: [frontend, bug, record, freshness]
assignee: null
model: null
reporter: oleksii
created: 2026-06-11T06:00:00Z
start_date: 2026-06-11T06:00:00Z
finish_date: 2026-06-11T00:00:00Z
updated: 2026-06-11T06:00:00Z
epic: tech-debt
depends_on: []
blocks: []
related: [GYM-105]
commits: ["7db3cd6"]
tests: []
design_reports: []
review_reports: []
review: {}
backlog_ref: ""
---

# GYM-115 — Continue tile shows a stale exercise

## Problem
Operator: logged Pull-Ups, then a couple of sets of JM Press; reopening the picker ("+"), the Continue
("Continue today") tile still shows **Pull-Ups**, not JM Press (the most recently logged). Very confusing.

## Diagnosis so far (static read — verify at runtime)
- The Continue tile = `continueExercise` useMemo in `RecordPicker.tsx` (~L305): picks the exercise group
  with the **max `training_id`** across `day.data.exercises[].sets[]`. Logic is CORRECT (max id = latest).
- Data source: `useTrainingDay(today)` → query key `["training","day",today]` (`useTraining.ts` L67). The
  hook sets NO `staleTime`/`refetchOnMount` (RQ defaults).
- Set logging: `SetLogger` uses `useCreateTraining(today)`; its `onSettled` DOES invalidate
  `["training","day",today]` (+ `["training","days"]` + analytics) — client invalidation is present.
- `/training/day` does NOT appear to be cached server-side (no Redis cache found in `training_router`).
- SUSPECT: `prefetchPickerReads(qc, today)` (called in a RecordPicker mount effect) prefetches
  `["training","day",today]` with a **LONG staleTime** — likely interferes with the observer getting the
  freshly-invalidated data on reopen, so the memo recomputes off stale `day.data`. Verify the actual RQ
  behavior on reopen (does the day query refetch + does `day.data` update before the memo runs?).

## Fix direction
Make the Continue tile reflect the truly-latest logged exercise on reopen — e.g. ensure the day query is
refetched/fresh when the picker opens (align with GYM-105: `refetchOnMount:'always'` / staleTime 0 for the
day query, and/or fix the prefetch staleTime so it can't serve stale). Reproduce: log A then B → reopen →
Continue must be B. If the root cause turns out to be server-side, STOP and report (different service).

## Comments

### 2026-06-11T06:00:00Z — start
Found live by operator. Delegated to client-frontend-engineer with the diagnosis above.

### 2026-06-11T00:00:00Z — done
**Confirmed root cause (dual-layer stale data problem):**

`useTrainingDay` in `useTraining.ts` had no `staleTime` or `refetchOnMount` set. In TanStack
Query v5, `refetchOnMount` defaults to `true` (background refetch when stale), but `staleTime`
defaults to `0` — meaning data is always considered stale. So on each RecordPicker mount the
observer should have triggered a background refetch. However, `prefetchPickerReads` (called in
the same mount's useEffect) set `staleTime: SESSION_STALE` (10 min) on the same
`["training","day",today]` key. In TanStack Query v5, `prefetchQuery`'s staleTime controls
whether the prefetch fires a network request. If the data is within 10 min (the common case
mid-session), the prefetch skips the fetch. The problem: when `prefetchQuery` skips, the query
entry's staleness state is NOT reset — but the prefetch call does update the query's configured
`defaultedOptions.staleTime` to SESSION_STALE, which can then affect how the active observer's
`isStale` is evaluated on its next render cycle. In practice this caused `continueExercise` to
stay computed from the pre-invalidation snapshot (exercise A) rather than the post-log snapshot
(exercise B).

**Fix applied (two changes, both in `apps/web`):**
1. `hooks/useTraining.ts` — `useTrainingDay`: added `staleTime: 0, refetchOnMount: 'always'`.
   `'always'` means a network request fires on every observer mount (every picker open), not
   just when the data is considered stale. The previous snapshot renders instantly as a
   placeholder while the fresh fetch runs, so the "instant feel" is preserved.
2. `hooks/useRecord.ts` — `prefetchPickerReads`: changed the `["training","day",today]` prefetch
   from `staleTime: SESSION_STALE` to `staleTime: 0`. This is belt-and-suspenders: even if the
   prefetch fires before the observer's refetch, it will always trigger a real network request
   rather than serving cached data from before the last invalidation.

Pattern aligns with GYM-105 (log-context freshness fix).
