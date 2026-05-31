---
schema_version: 1
id: GYM-4
title: "Add DB indexes on training and users hot columns"
slug: gym-4-db-indexes
status: in_progress
priority: high
type: refactor
labels: [phase-0, perf, db]
assignee: null
model: null
reporter: oleksii
created: 2026-05-31T16:00:00Z
start_date: 2026-05-31T16:30:00Z
finish_date: null
updated: 2026-05-31T16:30:00Z
epic: phase-0
depends_on: []
blocks: []
related: []
commits: ["d9ac6eb"]
tests: []
design_reports: []
review_reports: []
review: {}
backlog_ref: ""
---

# GYM-4 — Add DB indexes on training and users hot columns

## Problem
training has no index on user_id/date/exercise_id; users none on username. Every analytics query is a full scan -- the root cause that let the legacy site overload the server.

## Plan
Add indexes: training(user_id, date), training(exercise_id), users(username). Update packages/db/init.sql (fresh installs) + a migration applied to the live DB.

## Comments

### 2026-05-31T16:00:00Z — task created
Kills the full-scan root cause before the website rebuild (GYM-12).

### 2026-05-31T16:30:00Z — in progress
Added 3 indexes to packages/db/init.sql (idx_training_user_date, idx_training_exercise_id,
idx_users_username) for fresh DBs, plus an idempotent packages/db/migrations/001_add_hot_indexes.sql
for the live DB. Code ready. Remaining: apply the migration to the production DB (operator runs the
psql one-liner on the server, OR we wire an idempotent apply step into the ansible deploy) — then link
the SHA and close.
