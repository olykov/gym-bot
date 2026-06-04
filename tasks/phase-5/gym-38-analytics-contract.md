---
schema_version: 1
id: GYM-38
title: "Contract: 3 analytics endpoints in OpenAPI + regen clients"
slug: gym-38-analytics-contract
status: backlog
priority: medium
type: feature
labels: [phase-5, api-contract]
assignee: null
model: null
reporter: oleksii
created: 2026-06-04T09:00:00Z
start_date: null
finish_date: null
updated: 2026-06-04T09:00:00Z
epic: phase-5
depends_on: []
blocks: [GYM-39, GYM-41, GYM-42]
related: [GYM-12]
commits: []
tests: []
design_reports: []
review_reports: []
review: {}
backlog_ref: ""
---

# GYM-38 — Contract: analytics endpoints + regen clients

## Problem
The Mini App MVP needs activity-grid, summary, and exercise-progress data that the contract does not
yet define.

## Plan
Add to `packages/api-contract/openapi.yaml`, under the bot/user-facing (get_principal) auth:
- `GET /analytics/activity?from&to` → `[{ date, sets_count }]`
- `GET /analytics/summary` → `{ exercises, sets, prs, current_streak }`
- `GET /analytics/exercise-progress?muscle&exercise` → series shaped for ECharts (per-set weight/reps over time)
Regenerate BOTH clients (python + typescript). Keep naive-datetime tolerance (GYM-30).

## Acceptance criteria
- [ ] 3 endpoints in the spec; both clients regenerated and compile.

## Comments

### 2026-06-04T09:00:00Z — task created
Schemas must be exact — frontend (GYM-41/42) and API (GYM-39) both build on them.
