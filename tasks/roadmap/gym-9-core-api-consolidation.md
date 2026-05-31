---
schema_version: 1
id: GYM-9
title: "Phase 2: Core API consolidation (Alembic + OpenAPI contract)"
slug: gym-9-core-api-consolidation
status: backlog
priority: high
type: feature
labels: [phase-2, api]
assignee: null
model: null
reporter: oleksii
created: 2026-05-31T16:00:00Z
start_date: null
finish_date: null
updated: 2026-05-31T16:00:00Z
epic: roadmap
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

# GYM-9 — Phase 2: Core API consolidation (Alembic + OpenAPI contract)

## Problem
No single backend owns the DB; isolation logic is duplicated across bot and admin API.

## Plan
Adopt Alembic; publish packages/api-contract (OpenAPI + generated clients); de-duplicate visibility logic into apps/api; unify ID generation. The unlock for parallel work.

## Comments

### 2026-05-31T16:00:00Z — task created
Keystone -- everything downstream depends on this.
