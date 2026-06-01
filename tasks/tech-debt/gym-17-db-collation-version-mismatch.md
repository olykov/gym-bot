---
schema_version: 1
id: GYM-17
title: "Postgres collation version mismatch on prod DB (glibc 2.36 vs 2.41)"
slug: gym-17-db-collation-version-mismatch
status: review
priority: medium
type: chore
labels: [tech-debt, db]
assignee: null
model: null
reporter: oleksii
created: 2026-05-31T17:00:00Z
start_date: 2026-06-01T17:55:00Z
finish_date: null
updated: 2026-06-01T17:58:00Z
epic: tech-debt
depends_on: []
blocks: []
related: [GYM-4]
commits: []
tests: []
design_reports: []
review_reports: []
review: {}
backlog_ref: ""
---

# GYM-17 — Postgres collation version mismatch on prod DB

## Problem
Running psql on prod (during GYM-4) emitted:
`WARNING: database "gym_bot_db" has a collation version mismatch ... created using collation version
2.36, but the operating system provides version 2.41`.
The DB volume was created against an older glibc than the host now provides. Collation-sensitive
text indexes (e.g. users.username, the muscles/exercises name unique indexes) can, in rare cases,
return wrong ordering / mismatches until reindexed. Not urgent, but real.

## Plan
On the prod DB, once, during a low-traffic window:
- `REINDEX DATABASE gym_bot_db;` (or REINDEX the collation-sensitive text indexes), then
- `ALTER DATABASE gym_bot_db REFRESH COLLATION VERSION;`
Alternatively, pin the Postgres image/base so the glibc version stays stable across host changes.

## Acceptance criteria
- [x] Collation warning no longer emitted by psql on prod
- [x] Text indexes reindexed

## Comments

### 2026-05-31T17:00:00Z — task created
Discovered while applying GYM-4 indexes. Logged per "discovered tangent -> new backlog task".

### 2026-06-01T17:58:00Z — operator ran the fix on prod (review)
Operator executed on prod `gymbot_db` (postgres:16):
`REINDEX DATABASE gym_bot_db;` then `ALTER DATABASE gym_bot_db REFRESH COLLATION VERSION;`
→ `NOTICE: changing version from 2.36 to 2.41` / `ALTER DATABASE`. A fresh `psql` connect (`\q`)
afterwards emitted no collation warning — mismatch resolved. Ops-only change (no source code);
this closure commit is the linked evidence.
