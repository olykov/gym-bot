---
schema_version: 1
id: GYM-33
title: "API: connect as app_rw, set GUC context per transaction"
slug: gym-33-api-app-role-context
status: todo
priority: high
type: feature
labels: [phase-4, api]
assignee: null
model: null
reporter: oleksii
created: 2026-06-02T00:00:00Z
start_date: null
finish_date: null
updated: 2026-06-02T00:00:00Z
epic: phase-4
depends_on: [GYM-32]
blocks: [GYM-35, GYM-36]
related: [GYM-11]
commits: []
tests: []
design_reports: []
review_reports: []
review: {}
backlog_ref: ""
---

# GYM-33 — API: connect as app_rw, set GUC context per transaction

## Problem
The API connects as a superuser (RLS-immune) and never tells the DB who the caller is. It must
run as `app_rw` and set `app.user_id` + `app.role` per request transaction.

## Plan
- Config: add `APP_DB_USER`/`APP_DB_PASSWORD`; runtime `DATABASE_URL` builds from them. Keep a
  separate `MIGRATION_DATABASE_URL` (myuser) for Alembic only.
- `contextvars.ContextVar` for `current_user_id` + `current_role`; set in `get_principal` (and
  the admin deps), reset in a `finally`.
- SQLAlchemy `after_begin` event on `SessionLocal`/engine → emit
  `SELECT set_config('app.user_id', :uid, true), set_config('app.role', :role, true)` using the
  contextvar values (empty string when unset → fail-closed).
- Simplify `app/services/visibility.py`: drop the hard ownership predicate (RLS enforces it);
  keep only the soft-hide (`user_hidden_*`) subtraction. Do NOT rip out router `WHERE user_id`
  in this task — leave as defence-in-depth.

## Acceptance criteria
- [ ] App boots and serves as `app_rw`; verified `rolbypassrls=f` for the runtime connection.
- [ ] Every request transaction sets the GUCs; no leakage across pooled connections.
- [ ] Existing bot/admin endpoints still pass a backup-seeded e2e.

## Comments

### 2026-06-02T00:00:00Z — task created
GUC names fixed by the plan: `app.user_id`, `app.role`. Role name fixed: `app_rw`.
