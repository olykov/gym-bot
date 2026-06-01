"""baseline schema (mirrors packages/db/init.sql)

Revision ID: 0001_baseline
Revises:
Create Date: 2026-06-01 08:00:00.000000+00:00

This is the BASELINE revision: upgrade() recreates exactly the schema that
packages/db/init.sql produces today — the same tables, columns, foreign keys,
partial unique indexes, and the three GYM-4 hot-path indexes
(idx_training_user_date, idx_training_exercise_id, idx_users_username).

It represents "what production already has". Therefore:

  * EXISTING prod DB — DO NOT run this upgrade. Mark it as already at baseline:

        alembic stamp 0001_baseline

    This writes the revision into alembic_version WITHOUT executing any DDL, so
    no data is touched and nothing is re-created.

  * FRESH DB — `alembic upgrade head` builds the whole schema from scratch.

Going forward, Alembic is the canonical source of schema truth; init.sql is kept
only as the Docker container bootstrap until the cutover to `alembic upgrade`
in container start. See packages/db/README.md.
"""

from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op

# revision identifiers, used by Alembic.
revision: str = "0001_baseline"
down_revision: Union[str, Sequence[str], None] = None
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Create the current production schema (mirror of init.sql)."""
    # --- users -----------------------------------------------------------
    op.create_table(
        "users",
        # Telegram user id is supplied by the client, never DB-generated:
        # autoincrement=False keeps this BIGINT (not BIGSERIAL), matching init.sql.
        sa.Column("id", sa.BigInteger(), autoincrement=False, nullable=False),
        sa.Column("registration_date", sa.TIMESTAMP(), nullable=False),
        sa.Column("last_interaction", sa.TIMESTAMP(), nullable=True),
        sa.Column("lastname", sa.String(length=255), nullable=True),
        sa.Column("first_name", sa.String(length=255), nullable=True),
        sa.Column("phone", sa.String(length=20), nullable=True),
        sa.Column("country", sa.String(length=255), nullable=True),
        sa.Column("username", sa.String(length=255), nullable=True),
        sa.Column("bio", sa.Text(), nullable=True),
        sa.PrimaryKeyConstraint("id"),
    )

    # --- muscles ---------------------------------------------------------
    op.create_table(
        "muscles",
        sa.Column("id", sa.Integer(), autoincrement=True, nullable=False),
        sa.Column("name", sa.String(length=255), nullable=False),
        sa.Column("is_global", sa.Boolean(), server_default=sa.true(), nullable=True),
        sa.Column("created_by", sa.BigInteger(), nullable=True),
        sa.ForeignKeyConstraint(["created_by"], ["users.id"]),
        sa.PrimaryKeyConstraint("id"),
    )
    # Partial unique index: global muscles (created_by IS NULL).
    op.create_index(
        "idx_muscles_name_global",
        "muscles",
        ["name"],
        unique=True,
        postgresql_where=sa.text("created_by IS NULL"),
    )
    # Partial unique index: user-specific muscles (created_by IS NOT NULL).
    op.create_index(
        "idx_muscles_name_user",
        "muscles",
        ["name", "created_by"],
        unique=True,
        postgresql_where=sa.text("created_by IS NOT NULL"),
    )

    # --- exercises -------------------------------------------------------
    op.create_table(
        "exercises",
        sa.Column("id", sa.Integer(), autoincrement=True, nullable=False),
        sa.Column("name", sa.String(length=255), nullable=False),
        sa.Column("muscle", sa.Integer(), nullable=True),
        sa.Column("is_global", sa.Boolean(), server_default=sa.true(), nullable=True),
        sa.Column("created_by", sa.BigInteger(), nullable=True),
        sa.ForeignKeyConstraint(["created_by"], ["users.id"]),
        sa.ForeignKeyConstraint(["muscle"], ["muscles.id"]),
        sa.PrimaryKeyConstraint("id"),
    )
    # Partial unique index: global exercises (created_by IS NULL).
    op.create_index(
        "idx_exercises_global",
        "exercises",
        ["name", "muscle"],
        unique=True,
        postgresql_where=sa.text("created_by IS NULL"),
    )
    # Partial unique index: user-specific exercises (created_by IS NOT NULL).
    op.create_index(
        "idx_exercises_user",
        "exercises",
        ["name", "muscle", "created_by"],
        unique=True,
        postgresql_where=sa.text("created_by IS NOT NULL"),
    )

    # --- user_hidden_exercises ------------------------------------------
    op.create_table(
        "user_hidden_exercises",
        sa.Column("user_id", sa.BigInteger(), nullable=False),
        sa.Column("exercise_id", sa.Integer(), nullable=False),
        sa.ForeignKeyConstraint(["exercise_id"], ["exercises.id"], ondelete="CASCADE"),
        sa.ForeignKeyConstraint(["user_id"], ["users.id"]),
        sa.PrimaryKeyConstraint("user_id", "exercise_id"),
    )

    # --- user_hidden_muscles --------------------------------------------
    op.create_table(
        "user_hidden_muscles",
        sa.Column("user_id", sa.BigInteger(), nullable=False),
        sa.Column("muscle_id", sa.Integer(), nullable=False),
        sa.ForeignKeyConstraint(["muscle_id"], ["muscles.id"], ondelete="CASCADE"),
        sa.ForeignKeyConstraint(["user_id"], ["users.id"]),
        sa.PrimaryKeyConstraint("user_id", "muscle_id"),
    )

    # --- training --------------------------------------------------------
    op.create_table(
        "training",
        sa.Column("id", sa.String(length=32), nullable=False),
        sa.Column("date", sa.TIMESTAMP(), nullable=False),
        sa.Column("user_id", sa.BigInteger(), nullable=True),
        sa.Column("muscle_id", sa.Integer(), nullable=True),
        sa.Column("exercise_id", sa.Integer(), nullable=True),
        sa.Column("set", sa.Integer(), nullable=True),
        sa.Column("weight", sa.Numeric(precision=5, scale=2), nullable=True),
        sa.Column("reps", sa.Numeric(precision=5, scale=2), nullable=True),
        sa.ForeignKeyConstraint(["exercise_id"], ["exercises.id"]),
        sa.ForeignKeyConstraint(["muscle_id"], ["muscles.id"]),
        sa.ForeignKeyConstraint(["user_id"], ["users.id"]),
        sa.PrimaryKeyConstraint("id"),
    )

    # --- GYM-4 hot-path indexes -----------------------------------------
    # Every analytics query filters user_id and joins/sorts on date/exercise;
    # without these the training table is sequentially scanned each request.
    op.create_index("idx_training_user_date", "training", ["user_id", "date"])
    op.create_index("idx_training_exercise_id", "training", ["exercise_id"])
    op.create_index("idx_users_username", "users", ["username"])


def downgrade() -> None:
    """Drop the entire baseline schema (reverse order of upgrade)."""
    op.drop_index("idx_users_username", table_name="users")
    op.drop_index("idx_training_exercise_id", table_name="training")
    op.drop_index("idx_training_user_date", table_name="training")
    op.drop_table("training")

    op.drop_table("user_hidden_muscles")
    op.drop_table("user_hidden_exercises")

    op.drop_index("idx_exercises_user", table_name="exercises")
    op.drop_index("idx_exercises_global", table_name="exercises")
    op.drop_table("exercises")

    op.drop_index("idx_muscles_name_user", table_name="muscles")
    op.drop_index("idx_muscles_name_global", table_name="muscles")
    op.drop_table("muscles")

    op.drop_table("users")
