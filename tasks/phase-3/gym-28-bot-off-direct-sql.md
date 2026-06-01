---
schema_version: 1
id: GYM-28
title: "Bot: replace direct SQL with the Core API client"
slug: gym-28-bot-off-direct-sql
status: in_progress
priority: high
type: refactor
labels: [phase-3, api]
assignee: null
model: null
reporter: oleksii
created: 2026-06-01T11:00:00Z
start_date: 2026-06-01T11:35:00Z
finish_date: null
updated: 2026-06-01T11:35:00Z
epic: phase-3
depends_on: [GYM-26, GYM-27]
blocks: []
related: [GYM-10]
commits: []
tests: []
design_reports: []
review_reports: []
review: {}
backlog_ref: ""
---

# GYM-28 — Bot: replace direct SQL with the Core API client

## Problem
apps/bot imports PostgresDB and runs blocking psycopg2 SQL (incl. DB-driven keyboard rendering). It must stop owning the DB.

## Plan
Add an API client wrapper in apps/bot that uses the GYM-27 client and injects X-Service-Token + X-Act-As-User (acting user_id) per call, base URL http://admin_backend:8000/api/v1. Replace every db.* call in handlers.py and markups.py with API calls; remove PostgresDB/psycopg2 and the DB_* env needs; drop the md5 get_hash (the API owns the training id). Graceful error handling when the API is unreachable. This finally makes the bot async at the data layer (closes HP-1).

## Comments

### 2026-06-01T11:00:00Z — task created
Wave 2 — after GYM-26 (auth) and GYM-27 (client).
