---
schema_version: 1
id: GYM-32
title: "DB: 0002_rls migration — helpers, policies, GRANTs, role bootstrap"
slug: gym-32-rls-migration-policies
status: review
priority: high
type: feature
labels: [phase-4, db]
assignee: null
model: null
reporter: oleksii
created: 2026-06-02T00:00:00Z
start_date: 2026-06-02T00:05:00Z
finish_date: 2026-06-02T01:30:00Z
updated: 2026-06-02T01:30:00Z
epic: phase-4
depends_on: []
blocks: [GYM-33, GYM-35, GYM-36]
related: [GYM-11]
commits: [aaf8f67]
tests: []
design_reports: []
review_reports: []
review: {}
backlog_ref: ""
---

# GYM-32 — DB: 0002_rls migration — helpers, policies, GRANTs, role bootstrap

## Problem
RLS must be enabled and forced on all user-owned tables, with reusable helpers so future tables
are isolated in one line, and GRANTed to a non-superuser `app_rw` role the API will use.

## Plan
- Alembic `0002_rls` (depends on `0001_baseline`):
  - PL/pgSQL helper `enable_user_rls(tbl, owner_col)` — ENABLE+FORCE RLS + 4 policies keyed on
    `owner_col = nullif(current_setting('app.user_id', true),'')::bigint OR current_setting('app.role',true)='admin'`.
  - PL/pgSQL helper `enable_catalog_rls(tbl)` — SELECT `is_global OR created_by = me OR admin`;
    write policies `created_by = me OR admin` (global rows admin-only).
  - Apply: `users`(owner col `id`), `training`(`user_id`), `user_hidden_muscles`(`user_id`),
    `user_hidden_exercises`(`user_id`) via user-helper; `muscles`/`exercises` via catalog-helper.
  - `GRANT SELECT, INSERT, UPDATE, DELETE ON ALL TABLES` + `GRANT USAGE, SELECT ON ALL SEQUENCES`
    to `app_rw`. `downgrade()` symmetric (DROP POLICY, NO FORCE, DISABLE, REVOKE, DROP helpers).
- Role bootstrap SQL (idempotent `DO $$ ... IF NOT EXISTS`) for `app_rw` — delivered as a script
  for infra (GYM-34) to run with the password from a secret; NOT in the versioned migration.

## Acceptance criteria
- [ ] `alembic upgrade head` then `downgrade` clean on a backup-seeded local DB.
- [ ] All 6 tables show `rowsecurity=t` and `forcerowsecurity=t`.
- [ ] Helpers exist and are used; adding a demo table needs one `SELECT enable_user_rls(...)` line.

## Comments

### 2026-06-02T00:00:00Z — task created
Owner column differs: `users.id` is the owner key (telegram id), others use `user_id`.

### 2026-06-02T01:30:00Z — built + validated (commit aaf8f67), status review
Delivered (paths under packages/db, no app/api or infra touched):
- `alembic/versions/0002_rls.py` (down_revision `0001_baseline`). Two re-runnable
  PL/pgSQL helpers in `public`: `enable_user_rls(p_table regclass, p_owner_col text)`
  and `enable_catalog_rls(p_table regclass)` — ENABLE+FORCE RLS + 4 PERMISSIVE CRUD
  policies, each DROP POLICY IF EXISTS first (idempotent), built with format()/quote_ident.
  Applied to users(`id`), training/user_hidden_muscles/user_hidden_exercises(`user_id`)
  via user-helper; muscles/exercises via catalog-helper. GRANT CRUD on all tables +
  USAGE/SELECT on all sequences to `app_rw` + ALTER DEFAULT PRIVILEGES, all guarded by
  a pg_roles existence check so a dev DB without the role still upgrades (raises NOTICE).
  downgrade() symmetric: REVOKE, DROP POLICY, NO FORCE + DISABLE RLS, DROP both helpers.
- `bootstrap/create_app_role.sql` — idempotent role creation (LOGIN NOSUPERUSER
  NOBYPASSRLS NOCREATEDB NOCREATEROLE), password via psql var `app_pw` (passed through a
  session GUC into format(%L) because psql does not substitute inside $$ bodies);
  ALTER ROLE ... PASSWORD on every run to rotate. Header documents the infra invocation.
- `README.md` — RLS section: GUC names, fail-closed template, one-line convention for new
  user-owned tables (`user_id BIGINT NOT NULL REFERENCES users(id)` + `(user_id, ...)`
  index + `SELECT enable_user_rls('tbl','user_id')`), catalog tables, bootstrap run order.

Fixed names confirmed in use: role `app_rw`; GUCs `app.user_id` (bigint-as-text) and
`app.role` ('user'|'admin'); read `nullif(current_setting('app.user_id', true), '')::bigint`;
admin branch `OR current_setting('app.role', true) = 'admin'`.

Validation on a throwaway postgres:16 (init.sql → bootstrap → stamp 0001 → upgrade head):
- All 6 tables `relrowsecurity=t, relforcerowsecurity=t`; 4 policies each; helpers present.
- `app_rw` = rolsuper=f, rolbypassrls=f, rolcanlogin=t.
- Isolation as `app_rw`: no context → training=0, users=0 (fail-closed); user 1 → training=2,
  muscles=2 (global+own), hidden=1; user 2 → training=1, muscles=2, hidden=0; admin → all
  (training=3, muscles=3). Cross-user INSERT rejected by WITH CHECK; UPDATE of a global muscle
  (created_by NULL) affects 0 rows; own INSERT succeeds.
- Helper re-runnable (second call keeps 4 policies). GRANT guard verified: upgrade succeeds on
  a DB with no `app_rw` and still applies RLS to all 6 tables.
- `alembic downgrade -1` clean: all tables f/f, 0 policies, 0 helpers, 0 app_rw grants.
NOT pushed; container/venv torn down.
