"""Shared name-to-id resolvers for muscles and exercises (GYM-106).

All single-muscle and single-exercise name lookups go through these two
functions.  Resolution is always by ``name_key`` (the ``app_name_key`` SQL
function) so that name variants like "bench-press", "BENCH PRESS", and
"Bench Press" resolve to the same row.

Priority (deterministic, own wins over global):
  1. Caller's OWN row (``created_by == uid``) whose ``name_key`` matches.
  2. TODO GYM-86: check user_*_override.display_name_key here (override-aware
     branch; tables 0005/0006 not yet on prod — add between own and global once
     migration 0005 is applied and GYM-86 is shipped).
  3. GLOBAL row (``created_by IS NULL``) whose ``name_key`` matches.

The ordering is achieved via a single query with ``ORDER BY (created_by IS NULL)
ASC LIMIT 1`` — this puts own rows (``created_by IS NOT NULL → FALSE → 0``)
before global rows (``created_by IS NULL → TRUE → 1``), giving a deterministic
winner without two round-trips.

RLS: the session is already GUC-wired for the calling user (``get_db_for_principal``),
so a user can never resolve an exercise invisible to them — their own rows and
visible globals are the only rows in scope.

Defence-in-depth: ``uid`` is passed explicitly so the caller's intent is clear;
the actual enforcement boundary is RLS.
"""
from typing import Optional

from sqlalchemy import func, literal
from sqlalchemy.orm import Session

from app.models.models import Exercise, Muscle


def resolve_muscle_id(db: Session, uid: int, muscle: str) -> Optional[int]:
    """Resolve a muscle name to its database id for the given user.

    Matches by ``name_key == app_name_key(muscle)`` within the rows visible
    to the user (RLS-scoped session).  The user's own row wins over a global
    row with the same key (deterministic own-first ordering via ORDER BY).

    Prerequisite cleanup site (GYM-106): replaces bare ``.name ==`` lookups in
    the exact-name sites listed in ADR 0002 LIST A.

    Args:
        db: SQLAlchemy session already GUC-wired for the calling user.
        uid: Telegram user id of the caller (used for own-first ordering).
        muscle: Muscle group name — any case/separator variant is accepted.

    Returns:
        The integer muscle id, or ``None`` when not found / not visible.
    """
    row = (
        db.query(Muscle.id)
        .filter(Muscle.name_key == func.app_name_key(muscle))
        # TODO GYM-86: insert override-display_name_key check here, between own
        # and global, once migration 0005 is applied and user_muscle_override
        # table is on prod.
        .order_by(
            # False (0) < True (1): own rows (created_by IS NOT NULL → False)
            # sort before global rows (created_by IS NULL → True).
            (Muscle.created_by == None).asc()  # noqa: E711 — SQLAlchemy IS NULL
        )
        .limit(1)
        .first()
    )
    return row[0] if row else None


def resolve_exercise_id(
    db: Session, uid: int, muscle: str, exercise: str
) -> Optional[int]:
    """Resolve muscle + exercise names to an exercise id for the given user.

    First resolves the muscle via :func:`resolve_muscle_id`, then looks up
    the exercise within that muscle.  Both steps use ``name_key`` matching
    (``app_name_key`` SQL function) and own-first-then-global deterministic
    priority.

    Used by all single-exercise name lookups: analytics endpoints, training
    creation, and log-context.  Centralises the resolution logic so variant
    names (e.g. "bench-press", "BENCH PRESS") resolve consistently everywhere.

    Args:
        db: SQLAlchemy session already GUC-wired for the calling user.
        uid: Telegram user id of the caller (used for own-first ordering).
        muscle: Muscle group name (any case/separator variant).
        exercise: Exercise name (any case/separator variant).

    Returns:
        The integer exercise id, or ``None`` when not found / not visible.
    """
    muscle_id = resolve_muscle_id(db, uid, muscle)
    if muscle_id is None:
        return None

    row = (
        db.query(Exercise.id)
        .filter(
            Exercise.muscle == muscle_id,
            Exercise.name_key == func.app_name_key(exercise),
        )
        # TODO GYM-86: insert override-display_name_key check here, between own
        # and global, once migration 0005 is applied and user_exercise_override
        # table is on prod.
        .order_by(
            # Own rows (created_by IS NOT NULL → False → 0) before global
            # (created_by IS NULL → True → 1).
            (Exercise.created_by == None).asc()  # noqa: E711 — SQLAlchemy IS NULL
        )
        .limit(1)
        .first()
    )
    return row[0] if row else None
