---
schema_version: 1
id: GYM-9
title: "Phase 2: Core API consolidation (Alembic + OpenAPI contract)"
slug: gym-9-core-api-consolidation
status: in_progress
priority: high
type: feature
labels: [phase-2, api]
assignee: null
model: null
reporter: oleksii
created: 2026-05-31T16:00:00Z
start_date: 2026-06-01T08:00:00Z
finish_date: null
updated: 2026-06-01T08:00:00Z
epic: roadmap
depends_on: []
blocks: []
related: [GYM-20, GYM-21, GYM-22]
commits: []
tests: []
design_reports: []
review_reports: []
review: {}
backlog_ref: ""
---

# GYM-9 — Phase 2: Core API consolidation (Alembic + OpenAPI contract)

## Problem
No single backend owns the DB; isolation logic is duplicated across bot and admin API.

## Plan
Adopt Alembic; publish packages/api-contract (OpenAPI + generated clients); de-duplicate visibility logic into apps/api; unify ID generation. The unlock for parallel work.

## Comments

### 2026-05-31T16:00:00Z — task created
Keystone -- everything downstream depends on this.

### 2026-06-01T08:00:00Z — phase started, decomposed
Backups confirmed (S3 backup.tar + /opt/gymbot-pg-backup-01062026.zip on prod), so the gate is clear.
Decomposed into GYM-20 (Alembic baseline, db-migration-steward), GYM-21 (OpenAPI contract + clients,
api-contract-guardian), GYM-22 (apps/api endpoints + de-dup isolation + unify ID, core-api-engineer).
Phase 2 is ADDITIVE — the live bot stays on direct SQL until Phase 3 (GYM-10), so prod is not affected.
Wave 1 (GYM-20 + GYM-21) launched in parallel; GYM-22 follows the contract.
