---
schema_version: 1
id: GYM-61
title: "API: implement top-muscles (frequency); top-exercises returns all for a muscle"
slug: gym-61-top-muscles-api
status: review
priority: medium
type: feature
labels: [phase-5, api]
assignee: null
model: null
reporter: oleksii
created: 2026-06-05T01:00:00Z
start_date: 2026-06-05T01:30:00Z
finish_date: 2026-06-04T00:00:00Z
updated: 2026-06-05T01:00:00Z
epic: phase-5
depends_on: [GYM-60]
blocks: [GYM-62]
related: [GYM-12, GYM-59]
commits: [c3ed107]
tests: [apps/api/tests/test_gym61_top_muscles.py]
design_reports: []
review_reports: []
review: {}
backlog_ref: ""
---

# GYM-61 — API: top-muscles + all-exercises

## Problem
Implement the frequency-sorted muscle list; confirm exercises can be returned in full (not top-5).

## Plan
- `GET /analytics/top-muscles` in apps/api (mirror `get_top_exercises`): for the caller,
  `SELECT m.name, count(*) freq FROM training t JOIN muscles m ON m.id=t.muscle_id WHERE t.user_id=:uid
  GROUP BY m.name ORDER BY freq DESC`. RLS-scoped via `get_principal`; cached (analytics cache);
  sargable (uses idx_training_user_muscle from GYM-59, or the user_id index).
- `GET /analytics/top-exercises`: confirm a large/absent `limit` returns ALL the user's exercises for
  the muscle frequency-sorted (the Progress picker passes a high limit). Adjust if it hard-caps.
- Tests: top-muscles order + counts + isolation; top-exercises returns all for a muscle.

## Acceptance criteria
- [x] top-muscles correct (frequency desc, per-user); top-exercises can return all; tests green; sargable.

## Comments

### 2026-06-05T01:00:00Z — task created
Cache key per user; reuse the analytics cache + invalidation already wired.

### 2026-06-04T00:00:00Z — implementation complete (c3ed107)

**top-muscles query** (analytics_router.py `get_top_muscles`):
```sql
SELECT m.name, COUNT(*) AS frequency
FROM training t
JOIN muscles m ON m.id = t.muscle_id
WHERE t.user_id = :uid
GROUP BY m.name
ORDER BY frequency DESC, m.name ASC
```

**EXPLAIN ANALYZE** (Postgres 16, 8 rows for user_id=1):
```
Sort (actual time=0.867..0.869 rows=3)
  Sort Key: (count(*)) DESC, m.name
  -> GroupAggregate (actual rows=3)
       -> Sort (actual rows=8)
            -> Hash Join
                 Hash Cond: (m.id = t.muscle_id)
                 -> Seq Scan on muscles m (rows=3)
                 -> Hash
                      -> Bitmap Heap Scan on training t
                           Recheck Cond: (user_id = 1)
                           -> Bitmap Index Scan on idx_training_user_exercise
                                Index Cond: (user_id = 1)
Planning Time: 1.291 ms  Execution Time: 0.954 ms
```
Index used: `idx_training_user_exercise (user_id, exercise_id)` — one of the two GYM-59 indexes,
both of which cover `user_id` as the leading key. The WHERE predicate is sargable (no function
wrapping on `user_id`).

**top-exercises limit**: was unbounded (default=5, no cap). Changed to
`Query(default=5, ge=1, le=200)`. Existing bot callers (limit=5) unaffected; Progress picker
can pass limit=200 to get all exercises. Requests above 200 get 422.

**pytest summary**: `118 passed, 8 warnings in 6.86s` (all tests, including 15 new GYM-61 tests).
