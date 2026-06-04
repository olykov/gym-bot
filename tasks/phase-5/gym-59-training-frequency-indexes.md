---
schema_version: 1
id: GYM-59
title: "DB: composite indexes training(user_id,muscle_id) + (user_id,exercise_id)"
slug: gym-59-training-frequency-indexes
status: backlog
priority: low
type: chore
labels: [phase-5, db]
assignee: null
model: null
reporter: oleksii
created: 2026-06-05T01:00:00Z
start_date: null
finish_date: null
updated: 2026-06-05T01:00:00Z
epic: phase-5
depends_on: []
blocks: []
related: [GYM-12, GYM-61]
commits: []
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
