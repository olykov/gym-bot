---
schema_version: 1
id: GYM-40
title: "Infra: REDIS_URL for admin_backend"
slug: gym-40-api-redis-wiring
status: review
priority: medium
type: chore
labels: [phase-5, infra]
assignee: null
model: null
reporter: oleksii
created: 2026-06-04T09:00:00Z
start_date: 2026-06-04T10:00:00Z
finish_date: 2026-06-04T00:00:00Z
updated: 2026-06-04T09:00:00Z
epic: phase-5
depends_on: []
blocks: [GYM-39]
related: [GYM-12]
commits: [5bec2e7]
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
- [x] `REDIS_URL` present for admin_backend; compose config valid; bot FSM unaffected (separate db index).

## Comments

### 2026-06-04T09:00:00Z — task created
Reuse gymbot_redis; do not stand up a second redis.

### 2026-06-04 — implemented (5bec2e7)
Wired REDIS_URL=redis://:${REDIS_PASSWORD}@gymbot_redis:6379/1 into admin_backend in both
docker-compose.yaml and docker-compose.local.yaml. Added the same REDIS_URL line to the ansible
deploy.yaml .env render (literal value with db index /1, derived from REDIS_PASSWORD secret at
deploy time — no new GitHub secret required).
Bot FSM uses db index /0 (hardcoded in apps/bot/main_webhook.py line 36); API gets /1 — no key
clash possible. Both compose files validated cleanly: docker compose config returned exit 0.
