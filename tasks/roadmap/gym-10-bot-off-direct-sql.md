---
schema_version: 1
id: GYM-10
title: "Phase 3: Move bot off direct SQL to Core API client"
slug: gym-10-bot-off-direct-sql
status: backlog
priority: high
type: refactor
labels: [phase-3, bot]
assignee: null
model: null
reporter: oleksii
created: 2026-05-31T16:00:00Z
start_date: null
finish_date: null
updated: 2026-05-31T16:00:00Z
epic: roadmap
depends_on: [GYM-9]
blocks: []
related: []
commits: []
tests: []
design_reports: []
review_reports: []
review: {}
backlog_ref: ""
---

# GYM-10 — Phase 3: Move bot off direct SQL to Core API client

## Problem
apps/bot imports PostgresDB and runs blocking SQL on the event loop; keyboards read the DB directly.

## Plan
Replace db.* calls with the generated API client; remove psycopg2 from the bot; bot needs only an API base URL + token.

## Comments

### 2026-05-31T16:00:00Z — task created
After this, only apps/api touches Postgres.
