---
schema_version: 1
id: GYM-67
title: "API: implement /analytics/recent-exercises (last set per recent exercise)"
slug: gym-67-recent-exercises-api
status: review
priority: high
type: feature
labels: [phase-5, api]
assignee: null
model: null
reporter: oleksii
created: 2026-06-05T06:00:00Z
start_date: 2026-06-05T06:30:00Z
finish_date: 2026-06-04T00:00:00Z
updated: 2026-06-05T06:00:00Z
epic: phase-5
depends_on: [GYM-66]
blocks: [GYM-69]
related: [GYM-59, GYM-61]
commits: [118f064]
tests: [apps/api/tests/test_gym67_recent_exercises.py]
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

### 2026-06-04T00:00:00Z — implemented (commit 118f064)

Query (DISTINCT ON approach):
```sql
SELECT muscle_name, exercise_name, last_weight, last_reps, last_date
FROM (
    SELECT DISTINCT ON (t.exercise_id)
        m.name  AS muscle_name,
        e.name  AS exercise_name,
        t.weight AS last_weight,
        t.reps   AS last_reps,
        t.date::date AS last_date
    FROM training t
    JOIN exercises e ON e.id = t.exercise_id
    JOIN muscles   m ON m.id = t.muscle_id
    WHERE t.user_id = :uid
    ORDER BY t.exercise_id, t.date DESC
) latest
ORDER BY last_date DESC
LIMIT :lim
```

EXPLAIN result: Bitmap Index Scan on idx_training_user_exercise (user_id = 1) — no seq-scan
on training. muscles/exercises are tiny catalog tables; seq-scans there are expected.

pytest summary: 136 passed, 8 warnings in 8.88s (full suite, including 18 new GYM-67 tests).
