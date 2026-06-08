"""per-user rename overrides: user_exercise_override + user_muscle_override

Revision ID: 0005_user_overrides
Revises: 0004_name_key
Create Date: 2026-06-08 21:00:00.000000+00:00

GYM-86 — per-user RENAME overrides (ADR 0001, "reference + overrides").

WHAT THIS DOES
--------------
Adds the per-user override seam so a user can rename a CANONICAL exercise/muscle
to their own display name WITHOUT mutating the shared catalog row and WITHOUT
losing the canonical identity (the override references the canonical id; the
link persists, so ratings/PRs still aggregate by canonical id). This revision is
SCHEMA ONLY — no resolution/read logic changes (that is the API layer, GYM-89).

Two new user-owned tables, one per reference dimension:

  user_exercise_override
    user_id          BIGINT  NOT NULL  REFERENCES users(id)
                                       -- matches user_hidden_exercises.user_id
    exercise_id      INT     NOT NULL  REFERENCES exercises(id) ON DELETE CASCADE
    display_name     TEXT    NOT NULL  -- the user's personal name for this row
    display_name_key TEXT GENERATED ALWAYS AS (app_name_key(display_name)) STORED
                                       -- normalized key, reusing the GYM-84 fn,
                                       -- for name -> id resolution lookups
    PRIMARY KEY (user_id, exercise_id) -- one override per user per exercise
    INDEX (user_id, display_name_key)  -- name -> id resolution within a user

  user_muscle_override
    same shape against muscles(muscle_id -> muscles.id ON DELETE CASCADE),
    PK (user_id, muscle_id), INDEX (user_id, display_name_key).

WHY a generated key column
--------------------------
``display_name_key`` is ``GENERATED ALWAYS AS (app_name_key(display_name))
STORED`` — identical pattern to the muscles/exercises ``name_key`` added in
0004. It cannot drift from ``display_name`` (Postgres recomputes it), it is
auto-backfilled, and it is index-backable so the API can resolve a typed name
back to the overridden exercise/muscle id for a given user. NOT unique: a user
may legitimately rename two different canonical rows to keys that collide; the
add/rename dedup policy lives in the API (GYM-89), not as a hard DB unique here.

RLS POSTURE (user-owned, per-row isolation)
-------------------------------------------
Both tables are USER-OWNED (every row belongs to exactly one ``user_id``), so
they get the SAME RLS posture as ``user_hidden_exercises`` /
``user_hidden_muscles``: ``enable_user_rls(table, 'user_id')`` — ENABLE + FORCE
RLS + the four fail-closed CRUD policies keyed on the ``app.user_id`` GUC under
role ``app_rw`` (admin branch bypasses). ``app_rw`` already holds CRUD + sequence
grants via the ``ALTER DEFAULT PRIVILEGES`` set in 0002_rls, so no extra GRANT is
needed for these tables.

BACKWARD COMPATIBILITY
----------------------
Purely additive: two brand-new tables, no change to existing tables/columns/data.
Existing inserts/queries are untouched. Mirrored into init.sql for fresh
container bootstraps.

IDEMPOTENCY / TEST HARNESS
--------------------------
The test harness loads init.sql (which mirrors these tables) THEN runs
``alembic upgrade head``, so upgrade() MUST tolerate the tables/indexes already
existing — every statement uses IF NOT EXISTS, and enable_user_rls is itself
re-runnable (drop-if-exists per policy).

DOWNGRADE
---------
Fully reversible: disable + un-force RLS, drop the four policies on each table,
then drop both tables (which drops their generated columns and indexes). No data
migration is involved (the tables are new).
"""

from typing import Sequence, Union

from alembic import op

# revision identifiers, used by Alembic.
revision: str = "0005_user_overrides"
down_revision: Union[str, Sequence[str], None] = "0004_name_key"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


# Policy names created by enable_user_rls() — used by downgrade() to drop them.
_USER_POLICIES = (
    "rls_user_select",
    "rls_user_insert",
    "rls_user_update",
    "rls_user_delete",
)

_OVERRIDE_TABLES = ("user_exercise_override", "user_muscle_override")


_CREATE_EXERCISE_OVERRIDE = r"""
CREATE TABLE IF NOT EXISTS user_exercise_override (
    user_id          BIGINT NOT NULL REFERENCES users(id),
    exercise_id      INT    NOT NULL REFERENCES exercises(id) ON DELETE CASCADE,
    display_name     TEXT   NOT NULL,
    display_name_key TEXT GENERATED ALWAYS AS (public.app_name_key(display_name)) STORED,
    PRIMARY KEY (user_id, exercise_id)
);
"""

_CREATE_MUSCLE_OVERRIDE = r"""
CREATE TABLE IF NOT EXISTS user_muscle_override (
    user_id          BIGINT NOT NULL REFERENCES users(id),
    muscle_id        INT    NOT NULL REFERENCES muscles(id) ON DELETE CASCADE,
    display_name     TEXT   NOT NULL,
    display_name_key TEXT GENERATED ALWAYS AS (public.app_name_key(display_name)) STORED,
    PRIMARY KEY (user_id, muscle_id)
);
"""


def upgrade() -> None:
    """Create the two user-owned override tables, resolution indexes, and RLS.

    Idempotent (IF NOT EXISTS everywhere; enable_user_rls is re-runnable) so it
    is a safe no-op when the schema was already bootstrapped from init.sql.
    """
    # 1. Tables (with the generated display_name_key column).
    op.execute(_CREATE_EXERCISE_OVERRIDE)
    op.execute(_CREATE_MUSCLE_OVERRIDE)

    # 2. (user_id, display_name_key) indexes for name -> id resolution lookups.
    op.execute(
        "CREATE INDEX IF NOT EXISTS idx_user_exercise_override_name_key "
        "ON user_exercise_override (user_id, display_name_key)"
    )
    op.execute(
        "CREATE INDEX IF NOT EXISTS idx_user_muscle_override_name_key "
        "ON user_muscle_override (user_id, display_name_key)"
    )

    # 3. User-owned RLS — same posture as user_hidden_*.
    op.execute("SELECT public.enable_user_rls('user_exercise_override', 'user_id')")
    op.execute("SELECT public.enable_user_rls('user_muscle_override', 'user_id')")


def downgrade() -> None:
    """Fully reverse upgrade(): drop policies, disable RLS, drop both tables."""
    for table in _OVERRIDE_TABLES:
        for policy in _USER_POLICIES:
            op.execute(f"DROP POLICY IF EXISTS {policy} ON {table}")
        op.execute(f"ALTER TABLE IF EXISTS {table} NO FORCE ROW LEVEL SECURITY")
        op.execute(f"ALTER TABLE IF EXISTS {table} DISABLE ROW LEVEL SECURITY")
        op.execute(f"DROP TABLE IF EXISTS {table}")
