"""Centralized per-user visibility logic for muscles and exercises.

All endpoints that list muscles or exercises MUST call the functions in this
module instead of inlining the WHERE predicate.

Hard ownership boundary (``is_global OR created_by = me``) is now enforced
by Postgres RLS (migration 0002_rls, GYM-32).  These functions apply only the
soft-hide layer — subtracting rows the user has explicitly hidden.

``WHERE user_id`` / ``WHERE created_by`` filters in the routers are kept as
defence-in-depth; RLS is the real enforcement boundary.
"""
from typing import List

from sqlalchemy.orm import Session

from app.models.models import Exercise, Muscle, UserHiddenExercise, UserHiddenMuscle


def visible_muscles(db: Session, user_id: int) -> List[Muscle]:
    """Return muscle groups visible to *user_id*, ordered by name.

    RLS already restricts the query to rows the user owns or that are global.
    This function subtracts the soft-hide layer: global muscles the user has
    explicitly hidden are excluded.

    Private muscles created by the user are always returned (not hideable).

    Args:
        db: Active SQLAlchemy session with the RLS GUC already set for user_id.
        user_id: Telegram user id of the authenticated caller (used for the
            soft-hide subquery only; hard ownership is enforced by RLS).

    Returns:
        Ordered list of ``Muscle`` ORM objects visible to the user.
    """
    hidden_subq = (
        db.query(UserHiddenMuscle.muscle_id)
        .filter(UserHiddenMuscle.user_id == user_id)
        .subquery()
    )

    # Reason: RLS enforces the hard boundary (is_global OR created_by = me).
    # Here we only apply the soft-hide: exclude global muscles the user hid.
    # Private muscles (is_global=False, created_by=user_id) are never hideable
    # so they appear unconditionally once RLS admits them.
    return (
        db.query(Muscle)
        .filter(
            ~(
                Muscle.is_global.is_(True)
                & Muscle.id.in_(db.query(hidden_subq.c.muscle_id))
            )
        )
        .order_by(Muscle.name)
        .all()
    )


def visible_exercises_for_muscle(
    db: Session, user_id: int, muscle_id: int
) -> List[Exercise]:
    """Return exercises for *muscle_id* visible to *user_id*, ordered by name.

    RLS already restricts the query to rows the user owns or that are global.
    This function subtracts the soft-hide layer: global exercises the user has
    explicitly hidden are excluded.

    Args:
        db: Active SQLAlchemy session with the RLS GUC already set for user_id.
        user_id: Telegram user id of the authenticated caller (used for the
            soft-hide subquery only; hard ownership is enforced by RLS).
        muscle_id: Database id of the parent muscle.

    Returns:
        Ordered list of ``Exercise`` ORM objects visible to the user.
    """
    hidden_subq = (
        db.query(UserHiddenExercise.exercise_id)
        .filter(UserHiddenExercise.user_id == user_id)
        .subquery()
    )

    # Reason: RLS enforces the hard boundary (is_global OR created_by = me).
    # Here we only apply the soft-hide: exclude global exercises the user hid.
    return (
        db.query(Exercise)
        .filter(
            Exercise.muscle == muscle_id,
            ~(
                Exercise.is_global.is_(True)
                & Exercise.id.in_(db.query(hidden_subq.c.exercise_id))
            ),
        )
        .order_by(Exercise.name)
        .all()
    )
