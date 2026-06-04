---
schema_version: 1
id: GYM-67
title: "API: implement /analytics/recent-exercises (last set per recent exercise)"
slug: gym-67-recent-exercises-api
status: backlog
priority: high
type: feature
labels: [phase-5, api]
assignee: null
model: null
reporter: oleksii
created: 2026-06-05T06:00:00Z
start_date: null
finish_date: null
updated: 2026-06-05T06:00:00Z
epic: phase-5
depends_on: [GYM-66]
blocks: [GYM-69]
related: [GYM-59, GYM-61]
commits: []
tests: []
design_reports: []
review_reports: []
review: {}
backlog_ref: ""
---

# GYM-67 — API: recent-exercises

## Problem
Implement the cross-muscle last-trained-exercises read with each exercise's last working set.

## Plan
`GET /analytics/recent-exercises?limit` in apps/api (mirror `get_top_exercises` style): for the caller,
the most-recently-trained distinct exercises, newest first, each with its LAST set's weight/reps/date
and muscle+exercise names. Approach: per (user, exercise_id) the latest `date` (and the weight/reps of
that latest set), ordered by that date desc, limit N. Use a window/`DISTINCT ON (exercise_id) ... ORDER
BY exercise_id, date DESC` then re-order by date, or an equivalent sargable query over
`idx_training_user_date` / `idx_training_user_exercise` (GYM-59). RLS via `get_principal`; cached
(analytics cache, invalidated by the GYM-47 training-mutation wiring). Tests: order (recency), last
set values, per-user isolation, limit cap. `EXPLAIN` confirms index use (no seq-scan).

## Acceptance criteria
- [ ] recent-exercises returns last-trained exercises with correct last weight/reps, recency order,
      per-user; sargable; tests green.

## Comments

### 2026-06-05T06:00:00Z — task created
Reuses the analytics cache + the GYM-59 composite indexes.
