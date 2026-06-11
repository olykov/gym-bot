---
schema_version: 1
id: GYM-115
title: "Bug: Continue tile shows a stale exercise (prior, not the most recently logged today)"
slug: gym-115-continue-tile-stale
status: in_progress
priority: high
type: bug-fix
labels: [frontend, bug, record, freshness]
assignee: null
model: null
reporter: oleksii
created: 2026-06-11T06:00:00Z
start_date: 2026-06-11T06:00:00Z
finish_date: null
updated: 2026-06-11T06:00:00Z
epic: tech-debt
depends_on: []
blocks: []
related: [GYM-105]
commits: []
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
