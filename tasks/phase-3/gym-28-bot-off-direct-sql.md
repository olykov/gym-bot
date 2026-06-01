---
schema_version: 1
id: GYM-28
title: "Bot: replace direct SQL with the Core API client"
slug: gym-28-bot-off-direct-sql
status: done
priority: high
type: refactor
labels: [phase-3, api]
assignee: null
model: null
reporter: oleksii
created: 2026-06-01T11:00:00Z
start_date: 2026-06-01T11:35:00Z
finish_date: 2026-06-01T12:00:00Z
updated: 2026-06-01T12:00:00Z
epic: phase-3
depends_on: [GYM-26, GYM-27]
blocks: []
related: [GYM-10]
commits: ["69905b2", "48915e4"]
tests: []
design_reports: []
review_reports: []
review:
  security-auditor: pass-with-fixup
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

### 2026-06-01T11:50:00Z — code done, in security review (status: review)
bot-engineer: new modules/api.py (shared async GymApiClient from API_BASE_URL + BOT_SERVICE_TOKEN);
every db.* in handlers.py + markups.py replaced with client calls passing act_as_user=<sender id>;
name-vs-id resolved (create/analytics take names; list/hide/delete resolve id via list calls); markup
builders converted to async + awaited; psycopg2/PostgresDB + DB_* env removed; md5 get_hash dropped
(API owns the id); Dockerfile installs gym-api-client from a repo-root build context (ci.yaml + local
compose updated). Verified: py_compile, docker build (client installed), import with no psycopg2.
Committed 69905b2. Moved to REVIEW — security-auditor is auditing the full auth bridge (act_as_user
provenance per handler, admin-unreachable, token handling) before merge. Then a backup-seeded local e2e.

### 2026-06-01T12:00:00Z — done (security PASS + e2e PASS)
security-auditor verdict: SAFE TO MERGE — no critical/high. act_as_user is the per-update sender id at
every call site; service token is constant-time-compared and pinned to role=user (admin unreachable);
no token leakage; no runtime DB access. Fixup applied (orchestrator): deleted dead apps/bot/modules/
postgres.py + migrate_user_specific.py, added a root .dockerignore (build context is now repo root) —
48915e4. Backup-seeded e2e (prod backup -> local postgres + the real admin_backend image, called via
X-Service-Token + X-Act-As-User): personal-record, max-reps, top-exercises, muscle visibility all MATCH
direct SQL exactly; cross-user isolation holds (other user -> null); write round-trip creates a uuid
training row (+1). Phase 3 verified end-to-end. NOT pushed — on branch phase-3/bot-off-sql for the
operator to merge/deploy.
