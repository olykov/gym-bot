---
schema_version: 1
id: GYM-20
title: "Adopt Alembic + baseline migration from init.sql"
slug: gym-20-alembic-baseline
status: in_progress
priority: high
type: feature
labels: [phase-2, api]
assignee: null
model: null
reporter: oleksii
created: 2026-06-01T08:00:00Z
start_date: 2026-06-01T08:00:00Z
finish_date: null
updated: 2026-06-01T08:00:00Z
epic: phase-2
depends_on: []
blocks: []
related: [GYM-9]
commits: []
tests: []
design_reports: []
review_reports: []
review: {}
backlog_ref: ""
---

# GYM-20 — Adopt Alembic + baseline migration from init.sql

## Problem
Schema lives in packages/db/init.sql and only runs on a fresh volume; there is no migration framework, so schema evolution (indexes, RLS, future changes) is ad-hoc.

## Plan
Introduce Alembic in packages/db: configure env.py against the DATABASE_URL, capture the CURRENT schema (the tables/indexes in init.sql, including the GYM-4 indexes) as the baseline revision, and stamp existing prod as that baseline so future changes are versioned migrations. Do not change runtime data.

## Comments

### 2026-06-01T08:00:00Z — task created
Delegated to db-migration-steward. Independent of the contract work.
