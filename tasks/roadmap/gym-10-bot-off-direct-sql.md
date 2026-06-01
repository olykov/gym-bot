---
schema_version: 1
id: GYM-10
title: "Phase 3: Move bot off direct SQL to Core API client"
slug: gym-10-bot-off-direct-sql
status: in_progress
priority: high
type: refactor
labels: [phase-3, bot]
assignee: null
model: null
reporter: oleksii
created: 2026-05-31T16:00:00Z
start_date: 2026-06-01T11:00:00Z
finish_date: null
updated: 2026-06-01T11:00:00Z
epic: roadmap
depends_on: [GYM-9]
blocks: []
related: [GYM-26, GYM-27, GYM-28, GYM-29]
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

### 2026-06-01T11:00:00Z — phase started (branch phase-3/bot-off-sql)
Auth decision approved: bot is a trusted first-party SERVICE -> service-token auth + scoped user
impersonation (X-Service-Token + X-Act-As-User, role=user only), behind a unified resolve_principal()
layer. No JWT_SECRET sharing; RLS-ready; upgrade path to signed service-JWT / RFC 8693 token-exchange.
Decomposed: GYM-26 (API service-auth, core-api-engineer), GYM-27 (contract auth + python client,
api-contract-guardian), GYM-28 (bot off SQL, bot-engineer), GYM-29 (infra wiring, infra-engineer),
then security-auditor review + a backup-seeded local e2e. All on the branch; NOT pushed/deployed until
the operator says (backups exist: S3 + /opt/gymbot-pg-backup-01062026.zip). BOT_SERVICE_TOKEN secret
is set. Wave 1: GYM-26 + GYM-27 + GYM-29 in parallel; GYM-28 follows.
