---
schema_version: 1
id: GYM-139
title: "Record: Continue tile still stale after logging (shows previous exercise)"
slug: gym-139-continue-stale-again
status: in_progress
priority: high
type: bug-fix
labels: [frontend,data,record,bug,freshness]
assignee: null
model: null
reporter: oleksii
created: 2026-06-12T08:00:00Z
start_date: 2026-06-12T08:00:00Z
finish_date: null
updated: 2026-06-12T08:00:00Z
epic: fable-review
depends_on: []
blocks: []
related: []
commits: []
tests: []
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
