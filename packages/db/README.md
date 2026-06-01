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
  alembic/
    env.py                         # resolves DATABASE_URL / DB_* from the environment
    script.py.mako                 # migration template
    versions/
      0001_baseline.py             # baseline = exactly today's production schema
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
