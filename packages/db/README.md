# packages/db — database schema & migrations

This package owns the database structure: the schema, its Alembic migrations, the
raw-SQL bootstrap, and (later) RLS policies. All schema evolution is a versioned
migration — never an ad-hoc `ALTER` against a live DB.

## Layout

```
packages/db/
  init.sql                         # Docker container bootstrap (fresh volume only)
  migrations/                      # legacy raw-SQL migrations (pre-Alembic; e.g. GYM-4 indexes)
  alembic.ini                      # Alembic config; URL comes from the env, not this file
  bootstrap/
    create_app_role.sql            # idempotent app_rw role creation (infra/GYM-34; not a migration)
  alembic/
    env.py                         # resolves DATABASE_URL / DB_* from the environment
    script.py.mako                 # migration template
    versions/
      0001_baseline.py             # baseline = exactly today's production schema
      0002_rls.py                  # RLS helpers, policies on the 6 base tables, GRANTs to app_rw
      0003_training_frequency_indexes.py  # per-user (user_id, muscle_id/exercise_id) indexes
      0004_name_key.py             # app_name_key() fn + generated name_key + UNIQUE + collision-rename
  requirements.txt                 # alembic + psycopg2-binary
```

## Source-of-truth status

Going forward, **Alembic is canonical** for schema truth. `init.sql` is retained
**only** as the Docker container bootstrap (it runs once on a fresh volume) until
the container is cut over to run `alembic upgrade head` on startup. Until that
cutover, any schema change must be made as an Alembic revision **and** mirrored
into `init.sql` so fresh containers stay in sync. Do not hand-edit a live DB.

The `0001_baseline` revision mirrors `init.sql` exactly: tables `users`,
`muscles`, `exercises`, `user_hidden_exercises`, `user_hidden_muscles`,
`training`; the partial unique indexes on `muscles`/`exercises`; and the three
GYM-4 hot-path indexes `idx_training_user_date`, `idx_training_exercise_id`,
`idx_users_username`.

## Configuration

`env.py` reads the connection from the environment — credentials are never
committed:

1. `DATABASE_URL` if set, otherwise
2. assembled from `DB_USER` / `DB_PASSWORD` / `DB_HOST` / `DB_PORT` / `DB_NAME`
   (the same variables `apps/api` uses).

Install the tooling and run all commands from `packages/db/`:

```bash
pip install -r packages/db/requirements.txt
cd packages/db
```

## Adopting Alembic on the EXISTING production DB (no data loss)

Production already has the baseline schema (it was built from `init.sql` plus the
GYM-4 index migration). It must NOT re-run the baseline DDL. Stamp it as already
at the baseline — this writes the `alembic_version` row and runs **no** DDL:

```bash
alembic stamp 0001_baseline
```

After stamping, future revisions apply normally with `alembic upgrade head`.

## Fresh / local DB bootstrap

Two equivalent options for an empty database:

- **Container bootstrap (current default):** the Postgres container runs
  `init.sql` on a fresh volume, then stamp it: `alembic stamp 0001_baseline`.
- **Alembic-only (canonical going forward):** `alembic upgrade head` builds the
  whole schema from the migrations, no `init.sql` needed.

## Day-to-day

```bash
alembic history          # list revisions
alembic current          # show the DB's current revision
alembic heads            # show head revision(s)
alembic upgrade head     # apply pending migrations
```

## Authoring a new migration

```bash
alembic revision -m "short description"
```

Edit the generated file's `upgrade()` / `downgrade()` with explicit,
parameterized DDL. State backward compatibility and the data-migration / rollback
plan in the docstring. Destructive changes (drop / rename / type-narrowing)
require an approved plan and a rollback note before authoring.

## Row-Level Security (RLS) — GYM-32

RLS is DB-enforced, fail-closed per-user isolation (`0002_rls.py`). The API
connects as the non-superuser role **`app_rw`** (`NOSUPERUSER NOBYPASSRLS`) and
sets two GUCs per transaction with `SET LOCAL`:

- `app.user_id` — bigint (as text); the owner key.
- `app.role`    — `'user'` or `'admin'`; admin bypasses the owner check.

Policies read context fail-closed (unset/empty → NULL → no row matches):

```sql
nullif(current_setting('app.user_id', true), '')::bigint
-- admin branch appended to every policy:
OR current_setting('app.role', true) = 'admin'
```

> RLS is ignored by superusers and `BYPASSRLS` roles. The legacy `myuser`
> superuser still bypasses RLS — keep it for migrations/ops only; the app
> **must** run as `app_rw`.

### Convention for a NEW user-owned table

Every new user-owned table gets:

1. `user_id BIGINT NOT NULL REFERENCES users(id)`,
2. a composite index leading with `user_id`, e.g. `(user_id, created_at)`, and
3. one RLS line in the migration:

```python
op.execute("SELECT enable_user_rls('your_table', 'user_id')")
```

Catalog tables (an `is_global` + `created_by` shared dictionary) use instead:

```python
op.execute("SELECT enable_catalog_rls('your_table')")
```

`enable_user_rls(table, owner_col)` and `enable_catalog_rls(table)` are
re-runnable PL/pgSQL helpers installed by `0002_rls`. They ENABLE + FORCE RLS
and create the four PERMISSIVE CRUD policies (drop-if-exists first, so safe to
re-run). `app_rw` already holds CRUD + sequence grants, and
`ALTER DEFAULT PRIVILEGES` (set in `0002_rls`) extends them to future tables —
so no extra GRANT is needed for a new table.

### Role bootstrap (infra / GYM-34)

`app_rw` is created OUTSIDE Alembic (roles are cluster-global, password is a
secret) by `bootstrap/create_app_role.sql`, idempotently, password via the psql
variable `app_pw`:

```bash
psql "$ADMIN_DATABASE_URL" -v app_pw="$APP_DB_PASSWORD" \
     -f packages/db/bootstrap/create_app_role.sql
```

Run order on a DB: bootstrap (create `app_rw`) → `alembic stamp 0001_baseline`
(existing prod) or `alembic upgrade head` (fresh) → app connects as `app_rw`.
The `0002_rls` GRANTs are guarded: if `app_rw` does not exist yet the migration
still succeeds (it raises a NOTICE and skips the grants) so dev DBs work without
the role.
