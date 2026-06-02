# RLS Security Review — Phase 4 (GYM-35)

- **Date:** 2026-06-02
- **Branch:** `phase-4/rls`
- **Scope:** GYM-32 (migration/policies/role), GYM-33 (API app_rw + GUC context), GYM-34 (infra/runbook)
- **Reviewer:** security-auditor (read-only)
- **VERDICT: SAFE WITH FIXUPS**

The architecture is sound: dedicated `app_rw` (NOSUPERUSER NOBYPASSRLS) runtime role, ENABLE+FORCE
RLS on all 6 tables with fail-closed `nullif(...,'')::bigint` predicates, `is_local=true` GUCs,
parameterized GUC binding, and a service path that hardcodes `role='user'`. No CRITICAL cross-tenant
leak is provable from the code, but two HIGH issues must be resolved/proven before prod.

## HIGH (blockers)

### H1 — Legacy auth deps set RLS context but never reset it
`apps/api/app/middleware/permissions.py` — `get_current_user` (and `require_admin`/`require_role`
through it) call `set_principal_context()` with NO paired `reset_principal_context()`. Relying on
"the next request overwrites it" is fragile: a future route using `get_db` without an auth dep, or
an exception path, can leave `app.role='admin'` set and leak across users on a reused worker.
- **Fix:** make `get_current_user`/`require_admin`/`require_role` yield-based with
  `finally: reset_principal_context(...)`, like `get_principal`.

### H2 — Contextvar→`after_begin` propagation across FastAPI threadpool unproven / version-fragile
`apps/api/app/core/database.py` reads the contextvars inside `after_begin`, which fires in the
endpoint-body threadpool call. Sync generator deps (`get_principal`) propagate via
`contextmanager_in_threadpool`; plain-function legacy deps may not. Unverified (no tests yet).
- **Fix:** GYM-36 must assert that for BOTH `get_principal` and the legacy `require_*` paths,
  `current_setting('app.user_id')` inside a real query equals the caller, and that admin-then-user
  on a single worker never leaks. Pin `anyio`/`starlette` in requirements.

## MEDIUM (hardening)

- **M1** — training INSERT resolves muscle/exercise by NAME (RLS-filtered, so mostly safe), but does
  not assert resolved `exercise.muscle == muscle.id`. Prefer id-based resolution via the visibility
  layer. (`bot_router.py`, `router.py` create_training paths.)
- **M2** — admin token `sub='admin'` → `int()` raises → `app.user_id=''` (fine; admin uses role
  branch). Hardcoded admin Telegram-id allowlist (`auth.py`) should be config-driven for rotation.
- **M3** — GRANT/REVOKE role name is f-string-interpolated in `0002_rls.py` (constant `app_rw`, no
  injection today). Keep `APP_ROLE` a literal; never user-derived.
- **M4** — Catalog write policy keeps global rows admin-only ONLY if every `is_global` row has
  `created_by IS NULL`. **Pre-deploy assert:** `SELECT count(*) FROM muscles WHERE is_global AND
  created_by IS NOT NULL` = 0 (and same for `exercises`).

## LOW / INFO

- L1 — admin branch is a blanket bypass; one leaked admin JWT = total access. Consider shorter admin
  TTL (currently 7 days).
- L2 — JWT `alg` pinned to HS256 (verified-good).
- L3 — `downgrade()` leaves `app_rw` LOGIN-able but with no table grants (fail-closed); revert API
  first (RUNBOOK covers this).

### Verified-good (selected)
Runtime engine uses APP_DATABASE_URL only; FORCE RLS on all 6 tables; fail-closed default `''`;
`is_local=true`; GUC bound as params; service path hardcodes `role='user'` with constant-time token
compare; bot holds only BOT_SERVICE_TOKEN (cannot mint admin JWT); no GRANT TO PUBLIC; ansible
bootstrap `no_log:true`; `visibility.py` reduced to soft-hide only.

## Required before merge to prod
1. Fix **H1** (reset legacy auth contextvars).
2. Prove **H2** + **M4** via the GYM-36 integration suite on a backup-seeded DB.
