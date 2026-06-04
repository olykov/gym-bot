---
schema_version: 1
id: GYM-59
title: "DB: composite indexes training(user_id,muscle_id) + (user_id,exercise_id)"
slug: gym-59-training-frequency-indexes
status: review
priority: low
type: chore
labels: [phase-5, db]
assignee: null
model: null
reporter: oleksii
created: 2026-06-05T01:00:00Z
start_date: 2026-06-05T01:05:00Z
finish_date: 2026-06-04T00:00:00Z
updated: 2026-06-04T00:00:00Z
epic: phase-5
depends_on: []
blocks: []
related: [GYM-12, GYM-61]
commits: [5b489c1453e91f6e4aceb50d2e35edd16a2fdfff]
tests: []
design_reports: []
review_reports: []
review: {}
backlog_ref: ""
---

# GYM-59 — Per-user frequency indexes

## Problem
The Progress pickers will sort muscles/exercises by the user's training frequency
(`GROUP BY muscle_id/exercise_id WHERE user_id`). At ~9k rows it's already instant, but composite
indexes keep it sargable at scale.

## Plan
Alembic migration `0003_*` (down_revision = `0002_rls`): create
`idx_training_user_muscle (user_id, muscle_id)` and `idx_training_user_exercise (user_id, exercise_id)`
on `training` (IF NOT EXISTS). `downgrade()` drops both. Validate `upgrade`+`downgrade` on a throwaway
postgres:16 (chain off init.sql → stamp 0001 → upgrade head). Note: operator applies on prod via
`alembic upgrade head` (the Phase 4 runbook path).

## Acceptance criteria
- [ ] Migration up/down clean; both indexes present after upgrade; chained off 0002_rls.

## Comments

### 2026-06-05T01:00:00Z — task created
Perf/scale only; the frequency ORDER BY itself works without these.

### 2026-06-04T00:00:00Z — implemented; review
Migration `packages/db/alembic/versions/0003_training_frequency_indexes.py`
(down_revision `0002_rls`): `op.create_index(..., if_not_exists=True)` for
`idx_training_user_muscle (user_id, muscle_id)` and
`idx_training_user_exercise (user_id, exercise_id)`; `downgrade()` drops both
(`if_exists=True`). Plain btree (non-CONCURRENTLY) — small table, and
CONCURRENTLY cannot run in Alembic's transaction.

Validated on a throwaway postgres:16: load init.sql → `alembic stamp
0001_baseline` → `alembic upgrade head`. After upgrade `pg_indexes` for
`training` listed `idx_training_user_exercise` and `idx_training_user_muscle`
(both `USING btree (user_id, …)`); `alembic downgrade -1` ran clean and both
indexes were gone (revision back at `0002_rls`). Container torn down.
