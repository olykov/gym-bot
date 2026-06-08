"""canonical link (exercises.canonical_id) + exercise_alias catalog table

Revision ID: 0006_canonical_alias
Revises: 0005_user_overrides
Create Date: 2026-06-08 21:15:00.000000+00:00

GYM-87 — canonical catalog link + alias/synonym store (ADR 0001, layer 2b).

WHAT THIS DOES
--------------
1. ``exercises.canonical_id``
   INT NULL REFERENCES exercises(id) ON DELETE SET NULL  (self-reference)
   Links a user-custom exercise to the canonical exercise it represents. NULL
   for canonical rows themselves AND for unlinked customs. ON DELETE SET NULL so
   removing a canonical row degrades its linked customs back to "unlinked"
   (they keep all their own training history; only the optional canonical
   pointer clears). Indexed (``idx_exercises_canonical_id``) so "all rows linked
   to canonical X" (needed for merge GYM-88 and cross-user aggregation) is fast.

2. ``exercise_alias`` — the synonym/translation store (CATALOG, shared):
     id           SERIAL PRIMARY KEY
     canonical_id INT  NOT NULL REFERENCES exercises(id) ON DELETE CASCADE
     alias_name   TEXT NOT NULL
     name_key     TEXT GENERATED ALWAYS AS (app_name_key(alias_name)) STORED
     lang         TEXT NULL          -- optional ISO language tag of the alias
     UNIQUE (canonical_id, name_key) -- no duplicate alias keys per canonical
     INDEX (name_key)                -- alias-based resolution: key -> canonical

   Many aliases per canonical, including translations. ``name_key`` reuses the
   GYM-84 ``app_name_key`` normalization so an alias lookup uses the SAME key the
   catalog/override lookups use. ON DELETE CASCADE: deleting a canonical exercise
   drops its aliases (they are meaningless without it).

This revision is SCHEMA ONLY. It does NOT seed aliases (that is GYM-92) and does
NOT change any resolution logic (the API still resolves exactly as before; the
alias path is wired later, GYM-89).

RLS POSTURE
-----------
``exercise_alias`` is a CATALOG table (shared reference data, read by everyone,
written by admin), so it gets ``enable_catalog_rls('exercise_alias')`` — the same
read-all / owner-or-admin-write posture as ``exercises`` / ``muscles``. NOTE: the
catalog read/write policy template references ``is_global`` and ``created_by``;
exercise_alias has neither, so it carries the two columns purely to satisfy the
shared policy shape:
  - ``is_global BOOLEAN NOT NULL DEFAULT TRUE``  -> rows are world-readable
  - ``created_by BIGINT NULL REFERENCES users(id)`` -> NULL ⇒ admin-only writes
This keeps aliases a globally-readable, admin-curated dictionary (consistent with
how global catalog rows behave) without inventing a bespoke policy.

``exercises.canonical_id`` is a new column on the already-catalog-RLS'd
``exercises`` table; existing policies cover it (RLS is per-row, not per-column),
so no policy change is needed.

BACKWARD COMPATIBILITY
----------------------
Additive only. ``canonical_id`` is nullable with no default, so every existing
exercise row stays valid and unlinked; existing inserts/queries are untouched.
``exercise_alias`` is a brand-new table. Mirrored into init.sql for fresh
container bootstraps.

IDEMPOTENCY / TEST HARNESS
--------------------------
init.sql mirrors this, and the harness loads init.sql THEN upgrades, so upgrade()
tolerates the column/table/indexes already existing (ADD COLUMN IF NOT EXISTS,
CREATE TABLE/INDEX IF NOT EXISTS, enable_catalog_rls is re-runnable).

DOWNGRADE
---------
Fully reversible: disable + un-force RLS and drop the four catalog policies on
exercise_alias, drop the table, then drop the canonical_id index and column. No
data migration (column/table are new; dropping canonical_id only removes the
optional pointer, training history is untouched).
"""

from typing import Sequence, Union

from alembic import op

# revision identifiers, used by Alembic.
revision: str = "0006_canonical_alias"
down_revision: Union[str, Sequence[str], None] = "0005_user_overrides"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


# Policy names created by enable_catalog_rls() — used by downgrade() to drop them.
_CATALOG_POLICIES = (
    "rls_catalog_select",
    "rls_catalog_insert",
    "rls_catalog_update",
    "rls_catalog_delete",
)


_CREATE_ALIAS = r"""
CREATE TABLE IF NOT EXISTS exercise_alias (
    id           SERIAL PRIMARY KEY,
    canonical_id INT  NOT NULL REFERENCES exercises(id) ON DELETE CASCADE,
    alias_name   TEXT NOT NULL,
    name_key     TEXT GENERATED ALWAYS AS (public.app_name_key(alias_name)) STORED,
    lang         TEXT,
    -- Catalog-RLS shape columns (see module docstring): aliases are a global,
    -- admin-curated dictionary, so is_global defaults TRUE and created_by is NULL.
    is_global    BOOLEAN NOT NULL DEFAULT TRUE,
    created_by   BIGINT REFERENCES users(id),
    UNIQUE (canonical_id, name_key)
);
"""


def upgrade() -> None:
    """Add exercises.canonical_id (+ index) and the exercise_alias catalog table.

    Idempotent (IF NOT EXISTS everywhere; enable_catalog_rls re-runnable) so it
    is a safe no-op when bootstrapped from init.sql first.
    """
    # 1. Self-referencing canonical link on exercises (nullable, SET NULL).
    op.execute(
        "ALTER TABLE exercises "
        "ADD COLUMN IF NOT EXISTS canonical_id INT "
        "REFERENCES exercises(id) ON DELETE SET NULL"
    )
    op.execute(
        "CREATE INDEX IF NOT EXISTS idx_exercises_canonical_id "
        "ON exercises (canonical_id)"
    )

    # 2. Alias / synonym catalog table (with generated name_key).
    op.execute(_CREATE_ALIAS)
    op.execute(
        "CREATE INDEX IF NOT EXISTS idx_exercise_alias_name_key "
        "ON exercise_alias (name_key)"
    )

    # 3. Catalog RLS — same posture as exercises / muscles.
    op.execute("SELECT public.enable_catalog_rls('exercise_alias')")


def downgrade() -> None:
    """Fully reverse upgrade(): drop alias table + policies, then canonical_id."""
    # 1. exercise_alias: drop policies, disable RLS, drop table (+ its indexes).
    for policy in _CATALOG_POLICIES:
        op.execute(f"DROP POLICY IF EXISTS {policy} ON exercise_alias")
    op.execute("ALTER TABLE IF EXISTS exercise_alias NO FORCE ROW LEVEL SECURITY")
    op.execute("ALTER TABLE IF EXISTS exercise_alias DISABLE ROW LEVEL SECURITY")
    op.execute("DROP TABLE IF EXISTS exercise_alias")

    # 2. exercises.canonical_id: drop index then column.
    op.execute("DROP INDEX IF EXISTS idx_exercises_canonical_id")
    op.execute("ALTER TABLE exercises DROP COLUMN IF EXISTS canonical_id")
