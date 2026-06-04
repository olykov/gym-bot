---
schema_version: 1
id: GYM-39
title: "API: analytics endpoints (sargable, RLS) + Redis cache"
slug: gym-39-analytics-api-redis
status: backlog
priority: medium
type: feature
labels: [phase-5, api]
assignee: null
model: null
reporter: oleksii
created: 2026-06-04T09:00:00Z
start_date: null
finish_date: null
updated: 2026-06-04T09:00:00Z
epic: phase-5
depends_on: [GYM-38, GYM-40]
blocks: [GYM-42]
related: [GYM-12]
commits: []
tests: []
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
- [ ] 3 endpoints return correct per-user data; cross-user = 0 (RLS).
- [ ] Cache hit path verified; `EXPLAIN` shows index usage (no seq-scan on training).

## Comments

### 2026-06-04T09:00:00Z — task created
Sargable + cached is the whole point of Phase 5.
