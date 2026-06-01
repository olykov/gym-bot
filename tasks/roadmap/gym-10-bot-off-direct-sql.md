---
schema_version: 1
id: GYM-10
title: "Phase 3: Move bot off direct SQL to Core API client"
slug: gym-10-bot-off-direct-sql
status: done
priority: high
type: refactor
labels: [phase-3, bot]
assignee: null
model: null
reporter: oleksii
created: 2026-05-31T16:00:00Z
start_date: 2026-06-01T11:00:00Z
finish_date: 2026-06-01T14:20:00Z
updated: 2026-06-01T14:20:00Z
epic: roadmap
depends_on: [GYM-9]
blocks: []
related: [GYM-26, GYM-27, GYM-28, GYM-29, GYM-30]
commits: ["0c7c19f", "2e77855", "4f3961a", "69905b2", "5bc4da2"]
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

### 2026-06-01T12:00:00Z — code complete + e2e verified, awaiting operator deploy (status: review)
All sub-tasks done on branch phase-3/bot-off-sql: GYM-26 (API service-auth, 2e77855), GYM-27 (contract
+ async python client, 4f3961a), GYM-28 (bot off SQL + hardening, 69905b2 + 48915e4), GYM-29 (infra env,
0c7c19f). security-auditor: SAFE TO MERGE (no critical/high). Backup-seeded e2e against the real
admin_backend image + prod data via service auth: reads (PR/max-reps/top-exercises/visibility) all match
direct SQL, cross-user isolation holds, write round-trip creates a uuid training row. The bot now has NO
psycopg2/DB env; it calls the Core API over the internal network. Kept in REVIEW (not done) because it is
NOT merged/deployed — operator merges phase-3/bot-off-sql -> main (auto-deploys) when ready; rollback =
revert the merge. Operator prerequisite already met: BOT_SERVICE_TOKEN secret is set. Flip to done after
prod smoke (/start).

### 2026-06-01T14:20:00Z — merged + deployed + prod-verified (done)
Merged phase-3/bot-off-sql -> main and deployed (run 26760173094 success). Prod smoke via the bot's OWN
client (its env + service token -> prod Core API -> prod DB) caught a real bug the curl-based e2e missed:
client models rejected naive datetimes -> fixed as GYM-30 (5bc4da2), redeployed (run 26760579227 success),
re-smoked: list_muscles=9, PR 25.0/10 (date parsed), history=389 rows. The live bot now owns NO DB
connection — it calls Core API over the internal network via service auth. Only apps/api touches Postgres
now -> Phase 4 (RLS, GYM-11) is unblocked. Operator: final UX smoke in Telegram (/start -> /gym -> record
a set -> see the green PR highlight).
