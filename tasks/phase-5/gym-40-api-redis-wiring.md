---
schema_version: 1
id: GYM-40
title: "Infra: REDIS_URL for admin_backend"
slug: gym-40-api-redis-wiring
status: backlog
priority: medium
type: chore
labels: [phase-5, infra]
assignee: null
model: null
reporter: oleksii
created: 2026-06-04T09:00:00Z
start_date: null
finish_date: null
updated: 2026-06-04T09:00:00Z
epic: phase-5
depends_on: []
blocks: [GYM-39]
related: [GYM-12]
commits: []
tests: []
design_reports: []
review_reports: []
review: {}
backlog_ref: ""
---

# GYM-40 — Infra: REDIS_URL for admin_backend

## Problem
The API needs Redis for the analytics cache. Redis already runs in the stack (the bot uses it for
FSM); the API just needs the connection wired.

## Plan
Add `REDIS_URL` to the `admin_backend` env in both compose files and the ansible `.env` render,
pointing at the existing `gymbot_redis` service (own DB index to avoid clashing with the bot FSM).
No new service. Validate `docker compose config`.

## Acceptance criteria
- [ ] `REDIS_URL` present for admin_backend; compose config valid; bot FSM unaffected (separate db index).

## Comments

### 2026-06-04T09:00:00Z — task created
Reuse gymbot_redis; do not stand up a second redis.
