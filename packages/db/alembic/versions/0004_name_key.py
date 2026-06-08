"""normalized name_key + UNIQUE(name_key, scope) on muscles & exercises

Revision ID: 0004_name_key
Revises: 0003_training_frequency_indexes
Create Date: 2026-06-08 12:30:00.000000+00:00

GYM-84 — lexical dedup foundation (ADR 0001, layer 2a).

WHAT THIS DOES
--------------
1. Installs ONE canonical, IMMUTABLE normalization function ``app_name_key(text)``
   that computes the match key for a muscle/exercise name. This is the SINGLE
   SOURCE OF TRUTH: the DB uses it to back generated columns + unique indexes,
   and the Core API will call the SAME function for write-path lookups (GYM-85),
   guaranteeing DB <-> API agreement.

   Normalization (deterministic, IMMUTABLE):
     lower()                                  -- Postgres lower() folds Cyrillic;
                                                 full Unicode casefold not needed
     -> hyphen/underscore -> space            -- unify separators
     -> strip apostrophes . , (incidental)    -- drop incidental punctuation
     -> collapse all whitespace runs to ' '   -- one ASCII space between words
     -> btrim                                  -- final trim

   So "Bench Press", "bench-press", "bench_press", "BENCH  PRESS" all map to
   the single key "bench press". (No accent-folding: unaccent is NOT used —
   accent differences are rare in this catalog and unaccent would add an
   extension dependency + an IMMUTABLE-wrapper requirement for marginal benefit.
   Documented in docs/validation.md; can be layered in later if needed.)

2. Adds ``name_key`` to ``muscles`` and ``exercises`` as
   ``GENERATED ALWAYS AS (app_name_key(name)) STORED``. Chosen over a
   BEFORE trigger because: (a) it is auto-maintained on every INSERT/UPDATE
   with ZERO application changes (existing inserts that never mention name_key
   keep working); (b) the value cannot drift from ``name`` — Postgres recomputes
   it; (c) it is index-backable. A STORED generated column requires the
   expression to be IMMUTABLE, which ``app_name_key`` is. (A trigger would be
   the fallback only if the key needed mutable inputs — it does not.)

3. BACKFILL is automatic: a generated column is computed for every existing row
   the moment the column is added. No UPDATE needed.

4. RESOLVES EXISTING COLLISIONS before adding the unique indexes, per operator
   policy = RENAME the duplicate, KEEP BOTH rows (do NOT merge; each row keeps
   its own training history, which references ids that never change). For each
   colliding group (scoped exactly like the existing name-based uniques), the
   oldest row (lowest id) is kept as-is; every later colliding row gets a numeric
   suffix appended to its ``name`` ("(2)", "(3)", ...) until its generated
   name_key is unique within its scope. Deterministic and re-runnable.

5. Adds partial UNIQUE indexes on ``name_key`` mirroring the existing
   name-based ones, and DROPS the now-redundant name-based uniques (the
   name_key uniques subsume them — keeping both would double-reject and confuse:
   two rows differing only in punctuation/case would pass the name unique but
   fail the name_key unique, so the name unique adds nothing the key unique
   doesn't already cover). RLS posture is preserved: name_key is a plain
   readable column, indexes never bypass RLS.

BACKWARD COMPATIBILITY
----------------------
- Existing INSERT/UPDATE statements are untouched: they never reference
  name_key, and the generated column fills itself. apps/* need no change.
- Training history is untouched: it FKs exercise/muscle ids, which never change.
- Renamed duplicates: only the *display* ``name`` of colliding dupes changes
  (suffix appended); ids, FKs, and history are intact.

DOWNGRADE (one-way data caveat)
-------------------------------
downgrade() drops the name_key indexes, restores the original name-based unique
indexes, drops the name_key columns, and drops app_name_key(). It does NOT
un-rename the duplicates that upgrade() renamed: the original colliding names
are not recorded, and re-applying the old name-uniques over un-renamed dupes
would fail anyway. This is an accepted, documented one-way data effect — the
renamed rows remain valid, just with their suffixed display names.
"""

from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op

# revision identifiers, used by Alembic.
revision: str = "0004_name_key"
down_revision: Union[str, Sequence[str], None] = "0003_training_frequency_indexes"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


# ---------------------------------------------------------------------------
# 1. Canonical normalization function (SINGLE SOURCE OF TRUTH).
#
# IMMUTABLE + deterministic so it can back a STORED generated column and an
# index, and so the API (GYM-85) can rely on identical output. The body is a
# pure expression chain; STRICT returns NULL on NULL input (never the case for
# NOT NULL name, but correct by construction).
#
# Order matters:
#   1. lower()                              case-fold (Cyrillic-aware)
#   2. translate('-_' -> ' ')              unify separators to space
#   3. translate("'`.," -> '')             strip incidental punctuation
#   4. regexp_replace('\s+' -> ' ')        collapse whitespace runs
#   5. btrim                                final trim
# ---------------------------------------------------------------------------
_CREATE_FN = r"""
CREATE OR REPLACE FUNCTION public.app_name_key(p_name text)
RETURNS text
LANGUAGE sql
IMMUTABLE
STRICT
PARALLEL SAFE
AS $fn$
    SELECT btrim(
        regexp_replace(
            translate(
                translate(lower(p_name), '-_', '  '),
                E'\'`.,', ''
            ),
            '\s+', ' ', 'g'
        )
    )
$fn$;
"""

_DROP_FN = "DROP FUNCTION IF EXISTS public.app_name_key(text)"


# ---------------------------------------------------------------------------
# 4. Collision resolution (rename duplicates, keep both).
#
# Done in PL/pgSQL so the rename loop is deterministic and re-runnable. For each
# scope we walk colliding groups ordered by id; the FIRST row in a group is the
# keeper, every later row gets " (n)" appended to name until its generated
# name_key is unique within the scope. We bump n until app_name_key(candidate)
# is free — this also handles the (rare) case where the suffixed name itself
# collides with another existing row.
#
# Scopes mirror the existing uniques exactly:
#   muscles  : global -> key (created_by IS NULL); user -> (key, created_by)
#   exercises: global -> (key, muscle) (created_by IS NULL);
#              user   -> (key, muscle, created_by)
# ---------------------------------------------------------------------------
_RESOLVE_COLLISIONS = r"""
DO $resolve$
DECLARE
    r          RECORD;
    v_n        int;
    v_newname  text;
BEGIN
    -- ===== muscles: GLOBAL scope (created_by IS NULL), key = name_key =====
    FOR r IN
        SELECT m.id
        FROM muscles m
        WHERE m.created_by IS NULL
          AND EXISTS (
              SELECT 1 FROM muscles k
              WHERE k.created_by IS NULL
                AND k.name_key = m.name_key
                AND k.id < m.id
          )
        ORDER BY m.id
    LOOP
        v_n := 2;
        LOOP
            v_newname := (SELECT name FROM muscles WHERE id = r.id) || ' (' || v_n || ')';
            EXIT WHEN NOT EXISTS (
                SELECT 1 FROM muscles k
                WHERE k.created_by IS NULL
                  AND k.id <> r.id
                  AND k.name_key = public.app_name_key(v_newname)
            );
            v_n := v_n + 1;
        END LOOP;
        UPDATE muscles SET name = v_newname WHERE id = r.id;
    END LOOP;

    -- ===== muscles: USER scope (created_by IS NOT NULL), key = (name_key, created_by) =====
    FOR r IN
        SELECT m.id
        FROM muscles m
        WHERE m.created_by IS NOT NULL
          AND EXISTS (
              SELECT 1 FROM muscles k
              WHERE k.created_by = m.created_by
                AND k.name_key = m.name_key
                AND k.id < m.id
          )
        ORDER BY m.id
    LOOP
        v_n := 2;
        LOOP
            v_newname := (SELECT name FROM muscles WHERE id = r.id) || ' (' || v_n || ')';
            EXIT WHEN NOT EXISTS (
                SELECT 1 FROM muscles k
                WHERE k.created_by = (SELECT created_by FROM muscles WHERE id = r.id)
                  AND k.id <> r.id
                  AND k.name_key = public.app_name_key(v_newname)
            );
            v_n := v_n + 1;
        END LOOP;
        UPDATE muscles SET name = v_newname WHERE id = r.id;
    END LOOP;

    -- ===== exercises: GLOBAL scope (created_by IS NULL), key = (name_key, muscle) =====
    FOR r IN
        SELECT e.id
        FROM exercises e
        WHERE e.created_by IS NULL
          AND EXISTS (
              SELECT 1 FROM exercises k
              WHERE k.created_by IS NULL
                AND k.name_key = e.name_key
                AND k.muscle IS NOT DISTINCT FROM e.muscle
                AND k.id < e.id
          )
        ORDER BY e.id
    LOOP
        v_n := 2;
        LOOP
            v_newname := (SELECT name FROM exercises WHERE id = r.id) || ' (' || v_n || ')';
            EXIT WHEN NOT EXISTS (
                SELECT 1 FROM exercises k
                WHERE k.created_by IS NULL
                  AND k.id <> r.id
                  AND k.muscle IS NOT DISTINCT FROM (SELECT muscle FROM exercises WHERE id = r.id)
                  AND k.name_key = public.app_name_key(v_newname)
            );
            v_n := v_n + 1;
        END LOOP;
        UPDATE exercises SET name = v_newname WHERE id = r.id;
    END LOOP;

    -- ===== exercises: USER scope, key = (name_key, muscle, created_by) =====
    FOR r IN
        SELECT e.id
        FROM exercises e
        WHERE e.created_by IS NOT NULL
          AND EXISTS (
              SELECT 1 FROM exercises k
              WHERE k.created_by = e.created_by
                AND k.name_key = e.name_key
                AND k.muscle IS NOT DISTINCT FROM e.muscle
                AND k.id < e.id
          )
        ORDER BY e.id
    LOOP
        v_n := 2;
        LOOP
            v_newname := (SELECT name FROM exercises WHERE id = r.id) || ' (' || v_n || ')';
            EXIT WHEN NOT EXISTS (
                SELECT 1 FROM exercises k
                WHERE k.created_by = (SELECT created_by FROM exercises WHERE id = r.id)
                  AND k.id <> r.id
                  AND k.muscle IS NOT DISTINCT FROM (SELECT muscle FROM exercises WHERE id = r.id)
                  AND k.name_key = public.app_name_key(v_newname)
            );
            v_n := v_n + 1;
        END LOOP;
        UPDATE exercises SET name = v_newname WHERE id = r.id;
    END LOOP;
END
$resolve$;
"""


def upgrade() -> None:
    """Install app_name_key, add generated name_key, resolve collisions, swap uniques.

    Idempotent throughout (CREATE OR REPLACE / ADD COLUMN IF NOT EXISTS /
    CREATE INDEX IF NOT EXISTS / DROP INDEX IF EXISTS) so it is a safe no-op
    when the schema was already bootstrapped from init.sql (which mirrors this
    migration), and re-runnable after a partial failure. The test harness
    loads init.sql then runs `alembic upgrade head`, so this MUST tolerate the
    name_key column / indexes already existing.
    """
    # 1. Canonical normalization function (must exist before the generated column).
    op.execute(_CREATE_FN)

    # 2. Generated, auto-backfilled name_key columns.
    #    GENERATED ALWAYS AS (...) STORED computes the value for every existing
    #    row immediately (= backfill) and on every future INSERT/UPDATE.
    op.execute(
        "ALTER TABLE muscles "
        "ADD COLUMN IF NOT EXISTS name_key text "
        "GENERATED ALWAYS AS (public.app_name_key(name)) STORED"
    )
    op.execute(
        "ALTER TABLE exercises "
        "ADD COLUMN IF NOT EXISTS name_key text "
        "GENERATED ALWAYS AS (public.app_name_key(name)) STORED"
    )

    # 4. Resolve existing collisions (rename dupes, keep both) BEFORE the unique
    #    indexes are created, or index creation would fail on the duplicates.
    op.execute(_RESOLVE_COLLISIONS)

    # 5a. New partial UNIQUE indexes on name_key, mirroring the name-based ones.
    op.create_index(
        "idx_muscles_name_key_global",
        "muscles",
        ["name_key"],
        unique=True,
        postgresql_where=sa.text("created_by IS NULL"),
        if_not_exists=True,
    )
    op.create_index(
        "idx_muscles_name_key_user",
        "muscles",
        ["name_key", "created_by"],
        unique=True,
        postgresql_where=sa.text("created_by IS NOT NULL"),
        if_not_exists=True,
    )
    op.create_index(
        "idx_exercises_name_key_global",
        "exercises",
        ["name_key", "muscle"],
        unique=True,
        postgresql_where=sa.text("created_by IS NULL"),
        if_not_exists=True,
    )
    op.create_index(
        "idx_exercises_name_key_user",
        "exercises",
        ["name_key", "muscle", "created_by"],
        unique=True,
        postgresql_where=sa.text("created_by IS NOT NULL"),
        if_not_exists=True,
    )

    # 5b. Drop the now-redundant name-based uniques (subsumed by name_key uniques).
    op.drop_index("idx_muscles_name_global", table_name="muscles", if_exists=True)
    op.drop_index("idx_muscles_name_user", table_name="muscles", if_exists=True)
    op.drop_index("idx_exercises_global", table_name="exercises", if_exists=True)
    op.drop_index("idx_exercises_user", table_name="exercises", if_exists=True)


def downgrade() -> None:
    """Reverse upgrade(): restore name uniques, drop name_key columns + function.

    NOTE: renamed duplicates are NOT un-renamed (one-way data effect, documented
    in the module docstring).
    """
    # Restore the original name-based partial unique indexes first. This is safe
    # only because upgrade() renamed colliding rows so their *names* are now
    # unique within scope — the original name-uniques hold over the post-rename
    # data.
    op.create_index(
        "idx_muscles_name_global",
        "muscles",
        ["name"],
        unique=True,
        postgresql_where=sa.text("created_by IS NULL"),
    )
    op.create_index(
        "idx_muscles_name_user",
        "muscles",
        ["name", "created_by"],
        unique=True,
        postgresql_where=sa.text("created_by IS NOT NULL"),
    )
    op.create_index(
        "idx_exercises_global",
        "exercises",
        ["name", "muscle"],
        unique=True,
        postgresql_where=sa.text("created_by IS NULL"),
    )
    op.create_index(
        "idx_exercises_user",
        "exercises",
        ["name", "muscle", "created_by"],
        unique=True,
        postgresql_where=sa.text("created_by IS NOT NULL"),
    )

    # Drop the name_key uniques.
    op.drop_index("idx_exercises_name_key_user", table_name="exercises")
    op.drop_index("idx_exercises_name_key_global", table_name="exercises")
    op.drop_index("idx_muscles_name_key_user", table_name="muscles")
    op.drop_index("idx_muscles_name_key_global", table_name="muscles")

    # Drop the generated columns (this also removes their dependency on the fn).
    op.execute("ALTER TABLE exercises DROP COLUMN name_key")
    op.execute("ALTER TABLE muscles DROP COLUMN name_key")

    # Drop the canonical function last (nothing depends on it now).
    op.execute(_DROP_FN)
