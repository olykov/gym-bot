---
schema_version: 1
id: GYM-71
title: "API: implement /analytics/log-context (completed-sets + last-session + PR)"
slug: gym-71-log-context-api
status: review
priority: high
type: feature
labels: [phase-5, api, perf]
assignee: null
model: null
reporter: oleksii
created: 2026-06-05T08:00:00Z
start_date: 2026-06-05T08:30:00Z
finish_date: 2026-06-05T10:00:00Z
updated: 2026-06-05T10:00:00Z
epic: phase-5
depends_on: [GYM-70]
blocks: [GYM-72]
related: [GYM-39, GYM-47]
commits: [c367dae]
tests: [apps/api/tests/test_gym71_log_context.py]
design_reports: []
review_reports: []
review: {}
backlog_ref: ""
---

# GYM-71 — API: log-context

## Problem
Implement the combined set-logger context in one cached, RLS-scoped read.

## Plan
`GET /analytics/log-context?muscle&exercise&date` in apps/api (analytics_router), `get_principal` auth:
- `completed_sets` — distinct set numbers on `date` for this exercise (= existing completed-sets logic).
- `last_session_sets` — the sets of the MOST RECENT PRIOR session (the latest `date::date` < today, or
  latest overall if none today) for this exercise: `[{set, weight, reps}]` ordered by set. (e.g. find
  `max(date::date)` for the exercise excluding today, return that day's sets.)
- `pr` — the personal record (= existing personal-record logic) `{weight, reps, date}` or null.
Resolve muscle/exercise by name (RLS-scoped). Sargable (idx_training_user_exercise/idx_training_user_date,
GYM-59). Cache via the analytics cache (key includes muscle/exercise/date); GYM-47 mutation invalidation
covers it. Tests: completed_sets correctness, last_session = the right prior day's sets, pr, isolation,
no-history → empty/null. `EXPLAIN` confirms index use.

## Acceptance criteria
- [x] log-context returns the 3 parts correctly per-user; sargable; cached; tests green.

## Comments

### 2026-06-05T08:00:00Z — task created
One endpoint replaces 3 Phase-B roundtrips (the §3 latency fix) + powers last-session pre-fill.

### 2026-06-05T10:00:00Z — implementation complete

**Last-session CTE query:**
```sql
WITH prior_day AS (
    SELECT MAX(date::date) AS last_date
    FROM training
    WHERE user_id     = :uid
      AND exercise_id = :eid
      AND date < :day_start
)
SELECT t.set, t.weight, t.reps
FROM training t
JOIN prior_day pd ON t.date::date = pd.last_date
WHERE t.user_id     = :uid
  AND t.exercise_id = :eid
ORDER BY t.set
```

**EXPLAIN output (100-row table, postgres:16):**
```
Sort  (cost=16.38..16.38 rows=1 width=28) (actual time=1.563..1.564 rows=1 loops=1)
  Sort Key: t.set
  ->  Nested Loop  (cost=8.32..16.37 rows=1 width=28) (actual time=1.541..1.541 rows=1 loops=1)
        Join Filter: ((t.date)::date = (max((training.date)::date)))
        ->  Index Scan using idx_training_user_exercise on training t
              Index Cond: ((user_id = 1001) AND (exercise_id = 1))
        ->  Aggregate ...
              ->  Index Scan using idx_training_user_exercise on training
                    Index Cond: ((user_id = 1001) AND (exercise_id = 1))
                    Filter: (date < '2026-05-01 00:00:00')
Planning Time: 0.358 ms  Execution Time: 1.588 ms
```
Index used: `idx_training_user_exercise` — no seq-scan on training.

**pytest summary (18 GYM-71 tests):** 18 passed in 5.75s.
Full suite: 149 passed, 5 pre-existing failures (date-boundary tests hardcoded to 2026-06-04, now failing on 2026-06-05; introduced before GYM-71).

**Files changed:**
- `apps/api/app/schemas/schemas.py` — added `LogSet`, `LogContext` schemas
- `apps/api/app/api/v1/analytics_router.py` — added `_resolve_exercise_id`, `_fetch_completed_sets`, `_fetch_last_session_sets`, `_fetch_personal_record` helpers + `get_log_context` endpoint
- `apps/api/tests/test_gym71_log_context.py` — 18 integration tests (new file)
