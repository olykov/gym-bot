---
schema_version: 1
id: GYM-11
title: "Phase 4: Postgres Row-Level Security"
slug: gym-11-postgres-rls
status: review
priority: high
type: feature
labels: [phase-4, security, db]
assignee: null
model: null
reporter: oleksii
created: 2026-05-31T16:00:00Z
start_date: 2026-06-02T00:00:00Z
finish_date: null
updated: 2026-06-02T04:00:00Z
epic: roadmap
depends_on: [GYM-10]
blocks: []
related: [GYM-32, GYM-33, GYM-34, GYM-35, GYM-36, GYM-37, GYM-13]
commits: []
tests:
  - apps/api/tests/conftest.py
  - apps/api/tests/test_rls_isolation.py
design_reports: []
review_reports: []
review: {}
backlog_ref: ""
---

# GYM-11 — Phase 4: Postgres Row-Level Security

## Problem
Per-user isolation is hand-written `WHERE user_id` duplicated across the API; a forgotten
predicate leaks data silently. There is NO database-enforced isolation. Critically, the API
connects as `myuser` which is `rolsuper=t, rolbypassrls=t` — a superuser that ignores RLS
entirely (even `FORCE ROW LEVEL SECURITY` does not apply to a superuser). So enabling RLS is
meaningless until the app runs under a dedicated unprivileged role. This is the core of the task.

## Goal
DB-enforced, fail-closed per-user isolation that scales to a full gym platform (future tables:
splits, plans, progress, calorie tracking, entitlements). Establish a reusable convention so a
new user-owned table is isolated in one migration line.

## Approved plan (2026-06-02)

### Key decisions
- **R1** — Dedicated role `app_rw` (`NOSUPERUSER NOBYPASSRLS LOGIN`); API connects as it.
  `myuser` (superuser) kept for migrations/ops only.
- **R2** — Request context via GUCs `app.user_id` + `app.role`, set per-transaction with
  `set_config(key, value, true)` (local) in a SQLAlchemy `after_begin` event reading a
  `contextvars` value populated by the auth layer. Pool-safe, auto-resets at tx end.
- **R3** — Admin access via GUC flag: policies add `OR current_setting('app.role', true) = 'admin'`.
  The API is the trust boundary; service-token (bot) ALWAYS resolves role `user`, never admin.
- **R4** — Soft-hide (`user_hidden_*`) stays app-level in `visibility.py`; RLS enforces only the
  hard boundary `is_global OR created_by = me`.
- **R5** — Subscriptions / token limits are NOT RLS. Designed here, table creation + enforcement
  deferred to GYM-13. Their rows will be user-owned and covered by the same RLS convention.
- **R6** — `app_rw` role created by an idempotent bootstrap (ansible/init, password from secret),
  NOT in the versioned migration. The migration does only ENABLE/FORCE RLS + policies + GRANTs.

### Policy model
| Table | Type | SELECT | INSERT/UPDATE/DELETE |
|---|---|---|---|
| `users` | self | `id = app.user_id` (or admin) | `id = app.user_id` |
| `training` | owned | `user_id = app.user_id` | `user_id = app.user_id` |
| `user_hidden_muscles` / `user_hidden_exercises` | owned | `user_id = app.user_id` | `user_id = app.user_id` |
| `muscles` / `exercises` | catalog | `is_global OR created_by = app.user_id` | `created_by = app.user_id` (global = admin-only) |

GUC read template (fail-closed, empty-string safe):
`nullif(current_setting('app.user_id', true), '')::bigint`; admin branch:
`OR current_setting('app.role', true) = 'admin'`.

### Foundation for future tables
Reusable PL/pgSQL helpers `enable_user_rls('table')` and `enable_catalog_rls('table')` that
ENABLE+FORCE RLS and create the 4 standard policies. New user-owned table → one line in a
migration. Convention documented in docs/ARCHITECTURE.md + packages/db/README:
`user_id BIGINT NOT NULL REFERENCES users(id)` + index `(user_id, <hot_col>)` + the helper.

### Acceptance criteria
- [x] API connects as `app_rw` (`rolsuper=f, rolbypassrls=f`); `myuser` not used at runtime.
- [x] All 6 tables: ENABLE + FORCE RLS + policies on SELECT/INSERT/UPDATE/DELETE.
- [x] Integration test: user A sees/changes 0 rows of user B (training, custom muscles/exercises,
      hidden, profile).
- [x] No-context request returns 0 rows (fail-closed proven by test).
- [x] Admin JWT sees all; service token never admin.
- [x] Catalog: user sees `is_global`, can only modify own (`created_by = me`).
- [x] `enable_user_rls()` / `enable_catalog_rls()` exist; a demo table is covered by one line.
- [~] Validated on a backup-seeded copy of prod before deploy; rollback exists. (validated on
      ephemeral seeded DB + rollback documented; live prod-backup validation = operator cutover step)

### Prod facts (grounding, 2026-06-02)
App role `myuser` = `rolsuper=t, rolbypassrls=t`. Tables: `user_id` on training + hidden_*;
`created_by`+`is_global` on muscles/exercises; `users` keyed by telegram id. Data: 9 users,
9287 training rows, 2 custom muscles, 11 custom exercises, 3 hidden exercises, 0 orphan FKs.

### Decomposition
- **GYM-32** (db-migration-steward) — `0002_rls` migration, helpers, policies, GRANTs; role bootstrap SQL.
- **GYM-33** (core-api-engineer) — `app_rw` connection, contextvar + `after_begin`, set-context in auth, simplify `visibility.py`.
- **GYM-34** (infra-engineer) — `APP_DB_*` env/secrets, role creation in deploy, `alembic stamp` runbook.
- **GYM-35** (security-auditor) — isolation review (read-only).
- **GYM-36** (tests) — cross-tenant integration suite on backup-seeded DB.

### Operator prerequisites (not deployed until operator says)
- Prod, once: `cd packages/db && alembic stamp 0001_baseline` before `0002_rls`.
- Set `APP_DB_PASSWORD` secret; create `app_rw` role on prod via bootstrap.

## Comments

### 2026-05-31T16:00:00Z — task created
Requires the single-owner API (GYM-9/10) first.

### 2026-06-02T00:00:00Z — plan approved, phase started (branch phase-4/rls)
Ultrathink plan approved verbatim. Central finding: the runtime DB role is a superuser, so the
role swap to `app_rw` is the crux, not the policies. Decomposed into GYM-32..36; orchestrating
project subagents in background on branch phase-4/rls. NOT pushed/deployed until operator signs
off (backups exist: S3 + /opt/gymbot-pg-backup-01062026.zip). Built and validated on a
backup-seeded local DB first.

### 2026-06-02T04:00:00Z — code complete + validated, status review (awaiting operator cutover)
All sub-tasks done on branch phase-4/rls: GYM-32 (0002_rls migration + helpers + app_rw bootstrap,
aaf8f67), GYM-33 (API as app_rw + GUC context, fc31469), GYM-34 (infra env/role/runbook, 26d0faf),
GYM-35 (security review SAFE WITH FIXUPS, 666bf8e), GYM-36 (32 isolation tests, 380ecdd), GYM-37
(security fixups, 594978a). Critical catch: the contextvar+after_begin approach was BROKEN for the
app's SYNC endpoints — FastAPI runs deps and the endpoint body in separate threadpool contextvar
copies, so the GUC never reached the endpoint's session → would have shipped a fail-closed app
(0 rows for every user). Fixed by sourcing the GUC from `session.info` (shared on the Session
object), proven by 15 HTTP-level TestClient tests. Full suite: 47 passed (32 session-level + 15
HTTP-level), re-run independently. Acceptance criteria all met EXCEPT the final one — validation on
an actual prod-backup copy and the live cutover — which is the operator step.

Kept in REVIEW (not done): NOT merged/deployed. Operator cutover (see packages/db/RUNBOOK.md):
(1) set APP_DB_PASSWORD secret; (2) merge phase-4/rls -> main (deploy creates app_rw, idempotent);
(3) ONE-TIME on prod: `cd packages/db && alembic stamp 0001_baseline`; (4) pre-deploy data guard:
assert 0 rows `is_global AND created_by IS NOT NULL` in muscles/exercises; (5) `alembic upgrade head`
(as myuser); (6) Telegram smoke. Rollback: `alembic downgrade -1` + revert API to myuser. Flip to
done after prod smoke confirms per-user isolation live.
