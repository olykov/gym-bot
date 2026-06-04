---
schema_version: 1
id: GYM-47
title: "API: training day-list/day-detail/DELETE + analytics cache invalidation"
slug: gym-47-training-history-api
status: done
priority: medium
type: feature
labels: [phase-5, api]
assignee: null
model: null
reporter: oleksii
created: 2026-06-04T18:00:00Z
start_date: 2026-06-04T19:15:00Z
finish_date: 2026-06-04T20:30:00Z
updated: 2026-06-04T20:30:00Z
epic: phase-5
depends_on: [GYM-46]
blocks: [GYM-49]
related: [GYM-12, GYM-39]
commits: [2032ee9]
tests: [apps/api/tests/test_training_history.py]
design_reports: []
review_reports: []
review: {}
backlog_ref: ""
---

# GYM-47 — API: training history + edit + cache invalidation

## Problem
Implement the day-grouped reads and the delete, and stop the analytics Redis cache from going stale
after an edit.

## Plan
- `GET /training/days` — sargable group by `date::date` over `idx_training_user_date`; muscles/counts
  per day; bounded window + pagination. RLS via `get_principal`.
- `GET /training/day/{date}` — that day's rows joined to exercise/muscle NAMES, grouped by exercise
  then set. RLS-scoped.
- `DELETE /training/{training_id}` — delete the caller's row (RLS makes cross-user a no-op; return
  404 if not visible/own). 
- **Cache invalidation:** add to the cache util a `invalidate_user(user_id)` that deletes
  `analytics:{user_id}:*`, and call it in `POST /training`, `PUT /training/{id}`, and
  `DELETE /training/{id}` so Dashboard/Progress reflect edits immediately (not after the 90s TTL).
  Graceful if Redis down.
- Validate weight/reps on write (> 0, sane bounds). Tests for read shapes, delete, isolation, and
  that a mutation busts the cache.

## Acceptance criteria
- [x] day-list/day-detail correct + sargable (no seq-scan); DELETE works + RLS-isolated.
- [x] any training mutation invalidates that user's analytics cache; tests green.

## Comments

### 2026-06-04T18:00:00Z — task created
Cache invalidation must cover ALL training mutations — single util, no misses.

### 2026-06-04T20:30:00Z — implementation complete

**Endpoints implemented** (commit 2032ee9):
- `GET /training/days` — day-grouped summary, reverse-chronological, default 180-day window.
  Muscles as NAMES (joined), `exercises_count` = COUNT(DISTINCT exercise_id), `sets_count` = COUNT(*).
  Extracted to `apps/api/app/api/v1/training_history_router.py` (227 lines).
- `GET /training/day/{date}` — full exercise+set detail for one calendar day; exercises grouped by
  `exercise_id` with denormalized `exercise_name`/`muscle_name`; sets ordered by set number.
  Empty day → `{date, exercises: []}` (never 404).
- `DELETE /training/{training_id}` — 204 on success; 404 when row not visible (RLS) or unknown.

**Cache invalidation** — `cache.invalidate_user(user_id)` added to `apps/api/app/core/cache.py`:
  uses SCAN+DEL on pattern `analytics:{user_id}:*`; graceful if Redis down (catches all exceptions).
  Called at end of POST /training, PUT /training/{id}, DELETE /training/{id}.

**EXPLAIN (day-list query on postgres:16 with idx_training_user_date)**:
```
GroupAggregate  (cost=16.46..16.49 rows=1 width=52) (actual time=0.052..0.060 rows=10 loops=1)
  Group Key: ((t.date)::date)
  ->  Sort  (cost=16.46..16.46 rows=1 width=524) (actual time=0.033..0.034 rows=10 loops=1)
        Sort Key: ((t.date)::date) DESC, m.name
        ->  Nested Loop  (actual time=0.013..0.020 rows=10 loops=1)
              ->  Index Scan using idx_training_user_date on training t
                    Index Cond: (user_id = 1 AND date >= '...' AND date < '...')
              ->  Index Scan using muscles_pkey on muscles m
                    Index Cond: (id = t.muscle_id)
Planning Time: 0.298 ms  Execution Time: 0.093 ms
```
Index used: `idx_training_user_date` (no seq-scan). Sargable confirmed.

**pytest summary** (`pytest tests/ -q`):
```
95 passed, 8 warnings in 8.30s
```
All 95 tests green, including 33 new tests in `test_training_history.py`.
