"""
Centralized per-user visibility logic for muscles and exercises.

All endpoints that list muscles or exercises MUST call the functions in this
module instead of inlining the WHERE predicate.  This is the single place that
encodes the visibility rule:

    visible = (global AND NOT hidden-by-user) OR (owned-by-user)
"""
from typing import List

from sqlalchemy.orm import Session

from app.models.models import Exercise, Muscle, UserHiddenExercise, UserHiddenMuscle


def visible_muscles(db: Session, user_id: int) -> List[Muscle]:
    """Return muscle groups visible to *user_id*, ordered by name.

    Visibility rule (mirrors ``get_all_muscles`` in the bot):
    - Global muscles that the user has NOT hidden.
    - Private muscles created by the user.

    Args:
        db: Active SQLAlchemy session.
        user_id: Telegram user id of the authenticated caller.

    Returns:
        Ordered list of ``Muscle`` ORM objects.
    """
    hidden_subq = (
        db.query(UserHiddenMuscle.muscle_id)
        .filter(UserHiddenMuscle.user_id == user_id)
        .subquery()
    )

    return (
        db.query(Muscle)
        .filter(
            (
                (Muscle.is_global.is_(True))
                & (Muscle.id.not_in(db.query(hidden_subq.c.muscle_id)))
            )
            | (Muscle.created_by == user_id)
        )
        .order_by(Muscle.name)
        .all()
    )


def visible_exercises_for_muscle(
    db: Session, user_id: int, muscle_id: int
) -> List[Exercise]:
    """Return exercises for *muscle_id* visible to *user_id*, ordered by name.

    Visibility rule (mirrors ``get_exercises_by_muscle`` in the bot):
    - Global exercises under the muscle that the user has NOT hidden.
    - Private exercises under the muscle created by the user.

    Args:
        db: Active SQLAlchemy session.
        user_id: Telegram user id of the authenticated caller.
        muscle_id: Database id of the parent muscle.

    Returns:
        Ordered list of ``Exercise`` ORM objects.
    """
    hidden_subq = (
        db.query(UserHiddenExercise.exercise_id)
        .filter(UserHiddenExercise.user_id == user_id)
        .subquery()
    )

    return (
        db.query(Exercise)
        .filter(
            Exercise.muscle == muscle_id,
            (
                (
                    (Exercise.is_global.is_(True))
                    & (Exercise.id.not_in(db.query(hidden_subq.c.exercise_id)))
                )
                | (Exercise.created_by == user_id)
            ),
        )
        .order_by(Exercise.name)
        .all()
    )
