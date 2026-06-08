---
schema_version: 1
id: GYM-84
title: "DB: normalized name_key + UNIQUE(name_key, scope) on muscles & exercises + backfill"
slug: gym-84-name-key-dedup
status: done
priority: high
type: feature
labels: [taxonomy, db, validation]
assignee: null
model: null
reporter: oleksii
created: 2026-06-08T08:00:00Z
start_date: 2026-06-08T12:30:00Z
finish_date: 2026-06-08T11:25:30Z
updated: 2026-06-08T11:25:30Z
epic: tax-foundation
depends_on: []
blocks: [GYM-85, GYM-86, GYM-87]
related: []
commits: [af427f4]
tests: []
design_reports: []
review_reports: []
review: {}
backlog_ref: ""
---

# GYM-84 — Normalized name_key + uniqueness

## Problem
"Bench Press", "bench-press", "bench_press", "BENCH  PRESS" must be treated as one name. Today nothing
enforces this, so lexical duplicates can accrue. See ADR 0001 (docs/adr/0001-exercise-taxonomy.md).

## Scope (layers)
- DB (Alembic migration, packages/db): add a `name_key` column to `muscles` and `exercises`, computed as
  casefold (NOT lower — Turkish/Cyrillic safe) + trim + collapse whitespace + unify hyphen/underscore/space
  + strip incidental punctuation. UNIQUE index on the appropriate scope: `(name_key, created_by)` for user
  rows and `(name_key)` for global/canonical (mirroring the existing partial unique indexes).
- Backfill `name_key` for all existing rows; resolve any existing collisions before adding the constraint.
- Document the exact normalization in docs/validation.md (extend the Name rules).

## Key decisions (operator)
- name_key is the dedup key; display name stays as typed.
- Normalization must be identical wherever it runs (DB backfill + API write path, GYM-85).

## Acceptance
- [x] name_key present + UNIQUE on muscles & exercises; existing rows backfilled; collisions resolved;
      migration applies cleanly; normalization documented.

## Comments

### 2026-06-08 — Implemented (commit af427f4)

**Migration:** `packages/db/alembic/versions/0004_name_key.py` (down_revision = 0003), mirrored in
`packages/db/init.sql`. Docs in `docs/validation.md`.

**Canonical function (`app_name_key`) — SINGLE SOURCE OF TRUTH:**
```sql
CREATE OR REPLACE FUNCTION public.app_name_key(p_name text)
RETURNS text LANGUAGE sql IMMUTABLE STRICT PARALLEL SAFE AS $fn$
    SELECT btrim(
        regexp_replace(
            translate(
                translate(lower(p_name), '-_', '  '),  -- lower + unify '-'/'_' -> space
                E'\'`.,', ''                            -- strip ' ` . ,
            ),
            '\s+', ' ', 'g'                             -- collapse whitespace
        )
    )                                                  -- btrim = final trim
$fn$;
```
`lower()` (Cyrillic-safe), NOT full casefold — operator decision. No `unaccent` (documented:
avoids an extension dependency for marginal benefit; can layer in later via one fn change).
Verified: `Bench Press`/`bench-press`/`bench_press`/`BENCH  PRESS` -> `bench press`;
`O'Brien's Curl...` -> `obriens curl`; `Жим  Лёжа` -> `жим лёжа`; `Push-Up, v2.0` -> `push up v20`.

**Generated vs trigger:** chose `name_key TEXT GENERATED ALWAYS AS (app_name_key(name)) STORED`
on both tables. Auto-maintained on every INSERT/UPDATE with ZERO app changes; cannot drift from
`name`; index-backable. STORED requires an IMMUTABLE expr, which `app_name_key` is — so no trigger
fallback needed. Backfill is automatic (generated column computes for all existing rows on ADD).

**Collision resolution (operator policy = rename dupe, keep BOTH):** PL/pgSQL `DO` block, run
BEFORE the unique indexes. Per scope (mirrors existing uniques: muscles global `(name_key)` / user
`(name_key, created_by)`; exercises global `(name_key, muscle)` / user `(name_key, muscle,
created_by)`), keeps the lowest-id row, appends ` (2)`, ` (3)`, ... to the `name` of each later
colliding row until its generated key is unique within scope. Deterministic + re-runnable. No
merge, no delete — training history references ids, which never change. Dry-run (seeded
Chest/chest/CHEST, Back/back, Bench Press/bench-press/bench_press/BENCH  PRESS on one muscle + a
same-name `Bench Press` on a DIFFERENT muscle, Squat/squat): keepers untouched; dupes became
`chest (2)`, `CHEST (3)`, `back (2)`, `bench-press (2)`, `bench_press (3)`, `BENCH  PRESS (4)`,
`squat (2)`; the other-muscle `Bench Press` correctly NOT renamed; 6 muscles / 7 exercises all
survived; training rows t1->ex 11, t2->ex 21 intact; post-migration a re-inserted `Bench-Press`
on the same muscle is rejected by the unique index; zero remaining collisions in any scope.

**Old uniques dropped:** YES — `idx_muscles_name_global/_user`, `idx_exercises_global/_user`
dropped; `name_key` uniques subsume them (a name-unique would reject nothing the key-unique
doesn't already cover). downgrade() restores them.

**Idempotency:** `CREATE OR REPLACE` fn, `ADD COLUMN IF NOT EXISTS`, `CREATE INDEX IF NOT EXISTS`,
`DROP INDEX IF EXISTS`. Required because the apps/api test harness loads `init.sql` (now carrying
name_key) THEN runs `alembic upgrade head` — 0004 must no-op the already-present column/indexes.

**Test results (Postgres 16 in Docker):**
- Alembic-only fresh: `upgrade head` (0001->0004) clean.
- `downgrade -1` then `upgrade head` again: clean (full reversible cycle).
- Conftest path (init.sql + `stamp 0001_baseline` + `upgrade head`): clean, no dup-column error,
  2 name_key cols + 4 key indexes present.
- Collision dry-run: see above — all dupes renamed, all rows survive, history intact, unique holds.
- apps/api suite (`python3 -m pytest tests/ -q`): **278 passed, 0 failed** (13 pre-existing
  deprecation warnings unrelated to this change).

**Downgrade caveat (one-way):** downgrade drops the key indexes, restores the name-based uniques,
drops the name_key columns, and drops `app_name_key()`. It does NOT un-rename the duplicates that
upgrade renamed (the original colliding names are not recorded). Accepted/documented — renamed rows
remain valid with their suffixed display names.

### 2026-06-08 — prod application is MANUAL (operator decision)
Deploy does NOT auto-apply Alembic migrations (ansible only mounts init.sql [fresh-volume only] +
runs create_app_role.sql). Operator chose manual application per packages/db/RUNBOOK.md. This migration
(0004) must be applied to prod by hand (`alembic upgrade head` as the DB superuser/DB_USER against the
prod DB) BEFORE GYM-85 (API uses app_name_key on prod) ships. Code is on main; prod schema apply pending.
