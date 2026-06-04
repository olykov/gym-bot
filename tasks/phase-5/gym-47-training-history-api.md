---
schema_version: 1
id: GYM-47
title: "API: training day-list/day-detail/DELETE + analytics cache invalidation"
slug: gym-47-training-history-api
status: backlog
priority: medium
type: feature
labels: [phase-5, api]
assignee: null
model: null
reporter: oleksii
created: 2026-06-04T18:00:00Z
start_date: null
finish_date: null
updated: 2026-06-04T18:00:00Z
epic: phase-5
depends_on: [GYM-46]
blocks: [GYM-49]
related: [GYM-12, GYM-39]
commits: []
tests: []
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
- [ ] day-list/day-detail correct + sargable (no seq-scan); DELETE works + RLS-isolated.
- [ ] any training mutation invalidates that user's analytics cache; tests green.

## Comments

### 2026-06-04T18:00:00Z — task created
Cache invalidation must cover ALL training mutations — single util, no misses.
