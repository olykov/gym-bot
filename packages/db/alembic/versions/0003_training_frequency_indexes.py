"""per-user frequency indexes on training

Revision ID: 0003_training_frequency_indexes
Revises: 0002_rls
Create Date: 2026-06-04 00:00:00.000000+00:00

GYM-59 — Phase 5 per-user frequency indexes.

The Progress pickers sort muscles/exercises by the user's training frequency
(`GROUP BY muscle_id/exercise_id WHERE user_id = %s`). At ~9k rows the scan is
already instant, but two composite indexes keep the per-user aggregation
sargable as the table grows:

  * idx_training_user_muscle   on training (user_id, muscle_id)
  * idx_training_user_exercise on training (user_id, exercise_id)

Both are created IF NOT EXISTS so the migration is idempotent and a no-op if
the indexes were ever added ad-hoc. Plain (non-CONCURRENTLY) indexes: the table
is small and CONCURRENTLY cannot run inside Alembic's migration transaction.

Backward compatibility: index-only, no schema/data change. downgrade() drops
both indexes (IF EXISTS), fully reversing upgrade().
"""

from typing import Sequence, Union

from alembic import op

# revision identifiers, used by Alembic.
revision: str = "0003_training_frequency_indexes"
down_revision: Union[str, Sequence[str], None] = "0002_rls"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Create the two composite per-user frequency indexes (idempotent)."""
    op.create_index(
        "idx_training_user_muscle",
        "training",
        ["user_id", "muscle_id"],
        if_not_exists=True,
    )
    op.create_index(
        "idx_training_user_exercise",
        "training",
        ["user_id", "exercise_id"],
        if_not_exists=True,
    )


def downgrade() -> None:
    """Drop both composite indexes (IF EXISTS), reversing upgrade()."""
    op.drop_index(
        "idx_training_user_exercise",
        table_name="training",
        if_exists=True,
    )
    op.drop_index(
        "idx_training_user_muscle",
        table_name="training",
        if_exists=True,
    )
