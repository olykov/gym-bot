---
schema_version: 1
id: GYM-29
title: "Infra: wire BOT_SERVICE_TOKEN + API_BASE_URL; build context for shared client"
slug: gym-29-infra-wire-bot-service-auth
status: done
priority: high
type: chore
labels: [phase-3, api]
assignee: null
model: null
reporter: oleksii
created: 2026-06-01T11:00:00Z
start_date: 2026-06-01T11:00:00Z
finish_date: 2026-06-01T11:20:00Z
updated: 2026-06-01T11:20:00Z
epic: phase-3
depends_on: []
blocks: []
related: [GYM-10, GYM-28]
commits: ["0c7c19f"]
tests: []
design_reports: []
review_reports: []
review: {}
backlog_ref: ""
---

# GYM-29 — Infra: wire BOT_SERVICE_TOKEN + API_BASE_URL; build context for shared client

## Problem
The bot needs new env (BOT_SERVICE_TOKEN, API_BASE_URL) and must stop receiving DB_*; the API needs BOT_SERVICE_TOKEN; the bot's Docker build must be able to install the shared api-contract Python client.

## Plan
Wire BOT_SERVICE_TOKEN through ci.yaml + ansible .env + compose for BOTH the bot and admin_backend. Add API_BASE_URL=http://admin_backend:8000/api/v1 to the bot's env and REMOVE DB_USER/DB_PASSWORD/DB_HOST/DB_NAME/DB_PORT from the bot service. Make the bot Docker build able to install packages/api-contract's Python client (expand build context to repo root with -f apps/bot/Dockerfile, or an agreed alternative). Keep prod and local compose consistent. Do not break the API or admin services.

## Comments

### 2026-06-01T11:00:00Z — task created
Can be prepared in parallel with the API/contract work; coordinate the client-packaging choice with GYM-27/GYM-28.

### 2026-06-01T11:20:00Z — done (env scope)
infra-engineer wired BOT_SERVICE_TOKEN through ci.yaml + ansible .env + both compose files; added
API_BASE_URL=http://admin_backend:8000/api/v1 to the bot; removed all DB_* (+ DATABASE_URL) from the
bot service; bot depends_on admin_backend; admin_backend also gets BOT_SERVICE_TOKEN to validate.
Compose config valid on both files. Committed 0c7c19f. The Docker build-context change for the shared
api-contract client was intentionally deferred to GYM-28 (bot-engineer owns apps/bot/Dockerfile).
