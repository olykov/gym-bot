---
schema_version: 1
id: GYM-33
title: "API: connect as app_rw, set GUC context per transaction"
slug: gym-33-api-app-role-context
status: review
priority: high
type: feature
labels: [phase-4, api]
assignee: null
model: null
reporter: oleksii
created: 2026-06-02T00:00:00Z
start_date: 2026-06-02T01:35:00Z
finish_date: 2026-06-02T03:00:00Z
updated: 2026-06-02T03:00:00Z
epic: phase-4
depends_on: [GYM-32]
blocks: [GYM-35, GYM-36]
related: [GYM-11]
commits: [fc31469]
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

### 2026-06-02T03:00:00Z — implementation complete (commit fc31469)

**Files changed (apps/api/ only):**
- `app/core/db_context.py` (new): `current_user_id` / `current_role` `ContextVar[str]` with
  default `''`; `set_principal_context(user_id, role)` returns reset tokens;
  `reset_principal_context(uid_token, role_token)` restores prior state.
- `app/core/config.py`: added `APP_DB_USER` (default `'app_rw'`) and `APP_DB_PASSWORD`
  (required, wired into `must_not_be_empty` validator). Added `APP_DATABASE_URL` property
  (app_rw credentials). `DATABASE_URL` (myuser) retained as migration/ops URL.
- `app/core/database.py`: runtime `engine` now uses `APP_DATABASE_URL`. Added
  `@event.listens_for(SessionLocal, 'after_begin')` handler that calls
  `connection.execute(text("SELECT set_config('app.user_id', :uid, true), ..."))` reading
  the contextvars. `is_local=true` (3rd arg) means GUCs auto-reset at transaction end.
- `app/middleware/permissions.py`: `get_principal` converted to yield dependency — calls
  `set_principal_context` before yielding, `reset_principal_context` in `finally`. Legacy
  deps (`get_current_user`, `require_admin`) also call `set_principal_context` so the GUC
  is set for the transaction that fires `after_begin`.
- `app/services/visibility.py`: dropped hard `(is_global AND NOT hidden) OR created_by=me`
  predicate — RLS enforces the ownership boundary. Kept only the soft-hide NOT IN subquery.
  Routers' `WHERE user_id` filters left in place as defence-in-depth.

**SQLAlchemy event used:** `Session after_begin` (not engine-level). Fires at the start of
every DBAPI transaction for both reads and writes, and re-fires after each commit+new-begin
within the same session. The DBAPI connection passed to the handler lets us emit raw SQL
without going through the ORM.

**Validation (local throwaway Postgres 16, 0002_rls migration applied, app_rw created):**
- user 1001 with GUC set → sees 1 row (aaa111) ✅
- user 1002 with GUC set → sees 1 row (bbb222) ✅
- no-principal context (GUC='') → sees 0 rows (fail-closed) ✅
- admin GUC (role='admin') → sees 2 rows (both users) ✅
- app_rw: rolsuper=False, rolbypassrls=False ✅
