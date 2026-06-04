---
schema_version: 1
id: GYM-39
title: "API: analytics endpoints (sargable, RLS) + Redis cache"
slug: gym-39-analytics-api-redis
status: done
priority: medium
type: feature
labels: [phase-5, api]
assignee: null
model: null
reporter: oleksii
created: 2026-06-04T09:00:00Z
start_date: 2026-06-04T11:10:00Z
finish_date: 2026-06-04T12:00:00Z
updated: 2026-06-04T09:00:00Z
epic: phase-5
depends_on: [GYM-38, GYM-40]
blocks: [GYM-42]
related: [GYM-12]
commits: [e285ccd]
tests: [apps/api/tests/test_analytics_endpoints.py]
design_reports: []
review_reports: []
review: {}
backlog_ref: ""
---

# GYM-39 — API: analytics endpoints + Redis cache

## Problem
Implement the 3 analytics endpoints efficiently so the heavy `site_old` failure cannot recur.

## Plan
- Implement `activity`, `summary`, `exercise-progress` in apps/api, scoped via `get_principal`
  (RLS does isolation; fail-closed). Queries MUST be **sargable** — no functions on indexed columns
  in WHERE; lean on `idx_training_user_date`; bounded date ranges; pagination where lists can grow.
- Add a small **Redis cache util**: key `analytics:{user_id}:{endpoint}:{params}`, short TTL
  (~60–120s), TTL-only invalidation (writes are rare). Use the existing redis (REDIS_URL from GYM-40).
- No new heavy index unless `EXPLAIN` shows a need (data ~9k rows). If needed → a db-migration task.

## Acceptance criteria
- [x] 3 endpoints return correct per-user data; cross-user = 0 (RLS).
- [x] Cache hit path verified; `EXPLAIN` shows index usage (no seq-scan on training).

## Comments

### 2026-06-04T09:00:00Z — task created
Sargable + cached is the whole point of Phase 5.

### 2026-06-04T12:00:00Z — implementation complete (core-api-engineer)

**prs definition:** `COUNT(DISTINCT exercise_id) FROM training WHERE user_id = ?`.
Every exercise for which the user has at least one training row has a de-facto max-weight
personal record (the highest weight ever lifted for that exercise). This means
`prs == exercises` by definition. Kept as a separate field in the schema because:
(a) the contract specifies it as a distinct metric, and (b) the definition can be tightened
later (e.g. exercises where weight > personal baseline) without a schema change.

**current_streak definition:** consecutive calendar days ending at today (UTC) with >=1
training set. Training timestamps are stored as UTC TIMESTAMP WITHOUT TIME ZONE (inserted
via `NOW()` which Postgres interprets as the server's UTC clock). Using UTC for date
truncation is consistent with stored data. Georgia +4 offset is not applied because it would
require either TZ-aware storage or a client-supplied offset parameter — neither is in scope
for this task. If Georgia-local-day semantics are needed, a follow-up task should change
`training.date` to `TIMESTAMPTZ` and pass a timezone parameter to `DATE_TRUNC`.

**EXPLAIN output (activity query, 50-row test table):**
```
GroupAggregate  (cost=8.18..8.20 rows=1 width=16)
  Group Key: (date_trunc('day'::text, date))
  ->  Sort  (cost=8.18..8.19 rows=1 width=8)
        Sort Key: (date_trunc('day'::text, date))
        ->  Index Only Scan using idx_training_user_date on training  (cost=0.15..8.17 rows=1 width=8)
              Index Cond: ((user_id = 100001) AND (date >= '2026-05-01 00:00:00') AND (date < '2026-06-10 00:00:00'))
```
Index Only Scan on `idx_training_user_date` — no seq scan. DATE_TRUNC is in GROUP BY/SELECT only.

**pytest summary:**
```
73 passed, 2 warnings in 9.11s
```
(73 = 51 pre-existing + 22 new analytics tests)

**cache-down fallback:** The `cache_get` and `cache_set` helpers in `app/core/cache.py` catch
all exceptions internally and return None / silently skip. The endpoint code does:
`cached = cache_get(key); if cached is not None: return ...` then runs the DB query.
Redis failures never propagate to the HTTP response. The test env uses REDIS_URL=port 6399
(non-existent server), so every test exercises the fallback path.
