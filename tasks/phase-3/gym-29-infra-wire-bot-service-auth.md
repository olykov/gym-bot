---
schema_version: 1
id: GYM-29
title: "Infra: wire BOT_SERVICE_TOKEN + API_BASE_URL; build context for shared client"
slug: gym-29-infra-wire-bot-service-auth
status: in_progress
priority: high
type: chore
labels: [phase-3, api]
assignee: null
model: null
reporter: oleksii
created: 2026-06-01T11:00:00Z
start_date: 2026-06-01T11:00:00Z
finish_date: null
updated: 2026-06-01T11:00:00Z
epic: phase-3
depends_on: []
blocks: []
related: [GYM-10]
commits: []
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
