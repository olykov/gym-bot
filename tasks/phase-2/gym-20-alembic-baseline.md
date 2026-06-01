---
schema_version: 1
id: GYM-20
title: "Adopt Alembic + baseline migration from init.sql"
slug: gym-20-alembic-baseline
status: done
priority: high
type: feature
labels: [phase-2, api]
assignee: null
model: null
reporter: oleksii
created: 2026-06-01T08:00:00Z
start_date: 2026-06-01T08:00:00Z
finish_date: 2026-06-01T08:40:00Z
updated: 2026-06-01T08:40:00Z
epic: phase-2
depends_on: []
blocks: []
related: [GYM-9]
commits: ["b81b2a6"]
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

### 2026-06-01T08:40:00Z — done
db-migration-steward delivered Alembic under packages/db: alembic.ini + env.py (reads DB env, no
committed creds) + baseline revision 0001_baseline mirroring init.sql exactly (all tables, FKs,
partial unique indexes, GYM-4 indexes; users.id rendered BIGINT not BIGSERIAL). packages/db/requirements.txt
(alembic 1.18.4) + README with adoption docs. Verified via offline-SQL round-trip vs init.sql.
Committed b81b2a6. Operator follow-up (one-liner, no data change, before the first real migration e.g.
GYM-11 RLS): `cd packages/db && alembic stamp 0001_baseline` on prod. init.sql kept as container
bootstrap until cutover.
