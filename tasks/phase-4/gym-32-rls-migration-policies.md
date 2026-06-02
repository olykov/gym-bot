---
schema_version: 1
id: GYM-32
title: "DB: 0002_rls migration — helpers, policies, GRANTs, role bootstrap"
slug: gym-32-rls-migration-policies
status: todo
priority: high
type: feature
labels: [phase-4, db]
assignee: null
model: null
reporter: oleksii
created: 2026-06-02T00:00:00Z
start_date: null
finish_date: null
updated: 2026-06-02T00:00:00Z
epic: phase-4
depends_on: []
blocks: [GYM-33, GYM-35, GYM-36]
related: [GYM-11]
commits: []
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
