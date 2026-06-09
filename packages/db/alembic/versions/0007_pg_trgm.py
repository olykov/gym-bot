"""enable pg_trgm + GIN trigram indexes for exercise search (GYM-93)

Revision ID: 0007_pg_trgm
Revises: 0006_canonical_alias
Create Date: 2026-06-10 00:00:00.000000+00:00

GYM-93 — fuzzy candidate search over exercise names and aliases.

WHAT THIS DOES
--------------
1. ``CREATE EXTENSION IF NOT EXISTS pg_trgm``
   Enables the pg_trgm module (requires superuser, which is how Alembic runs).
   Idempotent: ``IF NOT EXISTS`` makes this a no-op on repeat runs.

2. GIN trigram index on ``exercises (name_key)``
   Backs ``similarity(exercises.name_key, app_name_key(:q))`` comparisons and
   the ``LIKE`` prefix tier in GET /exercises/search (GYM-93).  GIN is the
   right index type for full-text similarity on trigrams (vs. GiST which is
   better for nearest-neighbour in high-cardinality sets).

3. GIN trigram index on ``exercise_alias (name_key)``
   Same purpose for the alias tier: alias-name lookup by similarity and LIKE.

FUZZY THRESHOLD
---------------
The endpoint uses ``similarity(...) > 0.3`` as the fuzzy tier threshold.
0.3 is the pg_trgm default and provides reasonable typo tolerance (a
transposition or single wrong character in a 5-char word typically gives
~0.4–0.5 similarity), while keeping false positives low for a fitness catalog
where exercise names are fairly distinct.

BACKWARD COMPATIBILITY
----------------------
Additive only.  Indexes are created IF NOT EXISTS and do not affect any
existing query paths.  The extension is safe to enable globally — it adds
functions and operators but no schema changes.  init.sql should also be
updated to mirror these indexes for fresh container bootstraps (the harness
loads init.sql then upgrades, so idempotency is preserved).

DOWNGRADE
---------
Drops the two GIN indexes and disables pg_trgm (DROP EXTENSION).  Dropping
the extension is only safe because it was added here; if some other migration
later adds pg_trgm dependencies, this downgrade would fail — acceptable since
this is a one-way capability addition.
"""

from typing import Sequence, Union

from alembic import op

# revision identifiers, used by Alembic.
revision: str = "0007_pg_trgm"
down_revision: Union[str, Sequence[str], None] = "0006_canonical_alias"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Enable pg_trgm and add GIN trigram indexes for exercise search.

    Idempotent (CREATE IF NOT EXISTS everywhere) so it is a safe no-op
    when bootstrapped from init.sql first.
    """
    # 1. Enable the pg_trgm extension (superuser required; Alembic runs as myuser).
    op.execute("CREATE EXTENSION IF NOT EXISTS pg_trgm")

    # 2. GIN trigram index on exercises.name_key for similarity + LIKE queries.
    op.execute(
        "CREATE INDEX IF NOT EXISTS idx_exercises_name_key_trgm "
        "ON exercises USING gin (name_key gin_trgm_ops)"
    )

    # 3. GIN trigram index on exercise_alias.name_key for alias-tier search.
    op.execute(
        "CREATE INDEX IF NOT EXISTS idx_exercise_alias_name_key_trgm "
        "ON exercise_alias USING gin (name_key gin_trgm_ops)"
    )


def downgrade() -> None:
    """Drop the GIN trigram indexes and remove pg_trgm."""
    op.execute("DROP INDEX IF EXISTS idx_exercise_alias_name_key_trgm")
    op.execute("DROP INDEX IF EXISTS idx_exercises_name_key_trgm")
    op.execute("DROP EXTENSION IF EXISTS pg_trgm")
