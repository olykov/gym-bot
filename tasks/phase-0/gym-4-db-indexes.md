---
schema_version: 1
id: GYM-4
title: "Add DB indexes on training and users hot columns"
slug: gym-4-db-indexes
status: backlog
priority: high
type: refactor
labels: [phase-0, perf, db]
assignee: null
model: null
reporter: oleksii
created: 2026-05-31T16:00:00Z
start_date: null
finish_date: null
updated: 2026-05-31T16:00:00Z
epic: phase-0
depends_on: []
blocks: []
related: []
commits: []
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
