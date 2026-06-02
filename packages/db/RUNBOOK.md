# packages/db — Operator Runbook

This document covers the prod cutover for Phase 4 RLS (GYM-11/GYM-34):
the one-time `alembic stamp`, the `app_rw` role bootstrap, and the full
rollback procedure.

---

## Required GitHub Actions secret

| Secret name      | Where set                          | Notes                                  |
|------------------|------------------------------------|----------------------------------------|
| `APP_DB_PASSWORD`| GitHub repo → Settings → Secrets  | Password for the `app_rw` runtime role. Never hardcoded or committed. |

The other DB secrets (`DB_USER`, `DB_PASSWORD`, `DB_NAME`) continue to be used
for the Postgres container and Alembic operations. `APP_DB_USER` defaults to
`app_rw` and does not need a secret unless you want to override the role name.

---

## Prod cutover ORDER

Perform steps a–e exactly in this sequence. Do not deploy the API with
`APP_DB_PASSWORD` set until step (b) is complete, or the API will fail to start.

### (a) Set the APP_DB_PASSWORD secret

In the GitHub repository:
- Settings → Secrets and variables → Actions → New repository secret
- Name: `APP_DB_PASSWORD`
- Value: a strong random password (e.g. `openssl rand -base64 32`)

This secret is picked up by the CI deploy job and written to `.env` on the host
by Ansible. It is never written to any source file.

### (b) Deploy creates the app_rw role

The next push to `main` (or a re-run of the deploy workflow) will:
1. Copy `packages/db/bootstrap/create_app_role.sql` to the host.
2. After the stack is up, run:
   ```
   docker exec -i gymbot_db psql -U "$DB_USER" -d "$DB_NAME" \
     -v app_pw="$APP_DB_PASSWORD" < create_app_role.sql
   ```
   This creates `app_rw LOGIN NOSUPERUSER NOBYPASSRLS` if absent, then rotates
   its password. It is **idempotent** — safe on every deploy, including after a
   password rotation.

Verify the role exists:
```sql
-- on the host:
docker exec -it gymbot_db psql -U "$DB_USER" -d "$DB_NAME" \
  -c "\du app_rw"
```

### (c) One-time alembic stamp on prod (before first 0002_rls migration)

This step is required only once, on a live prod DB that has never run Alembic.
If the `alembic_version` table already contains `0001_baseline`, skip to step (d).

SSH into the prod host (or run from a machine that can reach the DB):
```bash
cd packages/db
DATABASE_URL="postgresql://myuser:$DB_PASSWORD@$DB_HOST:$DB_PORT/$DB_NAME" \
  alembic stamp 0001_baseline
```

`stamp` writes the revision ID into `alembic_version` WITHOUT running any SQL.
It tells Alembic "the schema is already at this revision" so it will only run
migrations that come after it (i.e. `0002_rls`).

**Alembic always runs as `myuser` (superuser/owner).** Never run migrations as
`app_rw` — it lacks DDL privileges. The env var to pass is `DATABASE_URL`, which
must point to the `myuser`/`DB_PASSWORD` credentials.

### (c2) Pre-cutover data integrity check (M4)

Before applying the RLS migration, assert that no global catalog row has a
non-null ``created_by`` (a violation would break the catalog write policy):

```sql
-- Run as myuser against the prod DB before step (d).
SELECT COUNT(*) FROM muscles  WHERE is_global AND created_by IS NOT NULL;
SELECT COUNT(*) FROM exercises WHERE is_global AND created_by IS NOT NULL;
-- Both counts must be 0.  If not, fix the data before proceeding.
```

This check is also automated in ``apps/api/tests/test_rls_endpoints.py``
(``TestCatalogM4DataGuard``).

### (d) Apply the RLS migration

```bash
cd packages/db
DATABASE_URL="postgresql://myuser:$DB_PASSWORD@$DB_HOST:$DB_PORT/$DB_NAME" \
  alembic upgrade head
```

This runs `0002_rls`, which:
- Creates PL/pgSQL helpers `enable_user_rls()` and `enable_catalog_rls()`.
- ENABLEs and FORCEs RLS on `users`, `training`, `user_hidden_muscles`,
  `user_hidden_exercises`, `muscles`, `exercises`.
- Creates per-table SELECT/INSERT/UPDATE/DELETE policies keyed on `app.user_id`
  and `app.role` GUCs.
- GRANTs table/sequence privileges to `app_rw`.

Verify:
```sql
SELECT tablename, rowsecurity, forcerowsecurity
FROM pg_tables
WHERE schemaname = 'public'
  AND tablename IN (
    'users','training','user_hidden_muscles',
    'user_hidden_exercises','muscles','exercises'
  );
-- rowsecurity and forcerowsecurity should both be true for all 6 tables.
```

### (e) RLS takes effect

The API (already deployed) reads `APP_DB_PASSWORD` from its environment and
connects as `app_rw`. Because `app_rw` is `NOSUPERUSER NOBYPASSRLS`, Postgres
enforces the policies created in step (d).

The API's `after_begin` hook sets `app.user_id` and `app.role` per transaction
(see `apps/api/app/db/session.py`). Without these GUCs, all queries return 0
rows (fail-closed).

---

## Rollback procedure

### Fast rollback (revert to myuser, no schema change)

If you need to revert the API to the superuser connection immediately (e.g. an
`app_rw` misconfiguration blocks the API from starting):

1. Remove `APP_DB_PASSWORD` from GitHub Actions secrets (or set it to a dummy
   value so the API can start).
2. On the host, edit `/opt/gym-bot/.env` and remove the `APP_DB_PASSWORD` line,
   then restart the API container:
   ```bash
   docker compose -f /opt/gym-bot/docker-compose.yml restart admin_backend
   ```
   The API will fall back to `DB_USER`/`DB_PASSWORD` (`myuser`) because
   `APP_DB_USER` defaults to `app_rw` but pydantic-settings will raise on
   missing `APP_DB_PASSWORD` — so you must also revert the code to remove the
   `APP_DB_PASSWORD` requirement, OR temporarily set a dummy value and accept
   that RLS is not enforced.

   The cleaner path: revert the GYM-33 commits and redeploy without `APP_DB_*`.

### Schema rollback (drop RLS policies)

```bash
cd packages/db
DATABASE_URL="postgresql://myuser:$DB_PASSWORD@$DB_HOST:$DB_PORT/$DB_NAME" \
  alembic downgrade -1
```

`downgrade -1` applies `0002_rls`'s `downgrade()` function, which:
- DROPs all per-table policies.
- DISABLEs RLS on the 6 tables.
- REVOKEs GRANTs from `app_rw`.
- DROPs the helper functions.

After downgrade, the DB is back to the `0001_baseline` state. The `app_rw` role
still exists (it is not created by the migration) but has no table access until
the next `upgrade head`.

To remove the role entirely (optional, only if you also revert the API):
```sql
REVOKE USAGE ON SCHEMA public FROM app_rw;
DROP ROLE IF EXISTS app_rw;
```

---

## Notes

- The `gymbot_db` Postgres container (`myuser`) remains the OWNER of all tables.
  `app_rw` only receives the GRANTs listed in `0002_rls`.
- Alembic must always connect as `myuser` (the owner), not `app_rw`.
- The `create_app_role.sql` bootstrap is re-run on every deploy and is safe for
  password rotation: just update the `APP_DB_PASSWORD` secret and redeploy.
- `no_log: true` is set on the Ansible bootstrap task so the password never
  appears in GitHub Actions logs.
