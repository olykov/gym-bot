"""Analytics endpoints — GYM-22 / GYM-26.

All analytics reads are scoped by the authenticated user (derived from
``get_principal``), which accepts EITHER a user JWT OR service-token
impersonation.  Queries faithfully mirror the bot's postgres.py
implementations:
- get_completed_sets
- get_last_training_history
- get_personal_record
- get_max_reps_for_weight
- get_top_exercises_for_muscle
"""
import logging
from datetime import datetime, date
from typing import List, Optional

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy import func
from sqlalchemy.orm import Session

from app.core.database import get_db
from app.middleware.permissions import Principal, get_principal
from app.models import models
from app.schemas import schemas

logger = logging.getLogger(__name__)

router = APIRouter()


@router.get(
    "/analytics/completed-sets",
    response_model=schemas.CompletedSets,
    tags=["analytics"],
)
def get_completed_sets(
    muscle: str,
    exercise: str,
    date: date,
    principal: Principal = Depends(get_principal),
    db: Session = Depends(get_db),
) -> schemas.CompletedSets:
    """Return set numbers already recorded for an exercise on a given date.

    Maps to ``get_completed_sets(user, muscle, exercise, date)``.

    Args:
        muscle: Muscle group name.
        exercise: Exercise name.
        date: Calendar date (YYYY-MM-DD).
        principal: Resolved identity from ``get_principal``.
        db: SQLAlchemy session.

    Returns:
        Distinct completed set numbers.
    """
    uid = principal["user_id"]

    rows = (
        db.query(models.Training.set)
        .join(models.Muscle, models.Training.muscle_id == models.Muscle.id)
        .join(models.Exercise, models.Training.exercise_id == models.Exercise.id)
        .filter(
            models.Training.user_id == uid,
            models.Muscle.name == muscle,
            models.Exercise.name == exercise,
            models.Training.date >= datetime.combine(date, datetime.min.time()),
            models.Training.date < datetime.combine(date, datetime.max.time()),
        )
        .distinct()
        .all()
    )

    return schemas.CompletedSets(sets=[r[0] for r in rows])


@router.get(
    "/analytics/history",
    response_model=List[schemas.TrainingHistoryEntry],
    tags=["analytics"],
)
def get_training_history(
    muscle: str,
    exercise: str,
    principal: Principal = Depends(get_principal),
    db: Session = Depends(get_db),
) -> List[schemas.TrainingHistoryEntry]:
    """Return training history for an exercise, excluding today.

    Maps to ``get_last_training_history(user, muscle, exercise)``.

    Args:
        muscle: Muscle group name.
        exercise: Exercise name.
        principal: Resolved identity from ``get_principal``.
        db: SQLAlchemy session.

    Returns:
        History entries ordered newest date first, then set ascending.
    """
    uid = principal["user_id"]
    today = datetime.utcnow().date()

    rows = (
        db.query(
            models.Training.date,
            models.Training.set,
            models.Training.weight,
            models.Training.reps,
        )
        .join(models.Muscle, models.Training.muscle_id == models.Muscle.id)
        .join(models.Exercise, models.Training.exercise_id == models.Exercise.id)
        .filter(
            models.Training.user_id == uid,
            models.Muscle.name == muscle,
            models.Exercise.name == exercise,
            models.Training.date < datetime.combine(today, datetime.min.time()),
        )
        .order_by(models.Training.date.desc(), models.Training.set.asc())
        .all()
    )

    return [
        schemas.TrainingHistoryEntry(
            date=r[0], set=r[1], weight=float(r[2]), reps=float(r[3])
        )
        for r in rows
    ]


@router.get(
    "/analytics/personal-record",
    response_model=Optional[schemas.PersonalRecord],
    tags=["analytics"],
)
def get_personal_record(
    muscle: str,
    exercise: str,
    principal: Principal = Depends(get_principal),
    db: Session = Depends(get_db),
) -> Optional[schemas.PersonalRecord]:
    """Return the personal record (max weight) for an exercise.

    Maps to ``get_personal_record(user, muscle, exercise)``.

    Args:
        muscle: Muscle group name.
        exercise: Exercise name.
        principal: Resolved identity from ``get_principal``.
        db: SQLAlchemy session.

    Returns:
        PersonalRecord or None when no history exists.
    """
    uid = principal["user_id"]

    row = (
        db.query(
            models.Training.weight,
            models.Training.reps,
            models.Training.date,
        )
        .join(models.Muscle, models.Training.muscle_id == models.Muscle.id)
        .join(models.Exercise, models.Training.exercise_id == models.Exercise.id)
        .filter(
            models.Training.user_id == uid,
            models.Muscle.name == muscle,
            models.Exercise.name == exercise,
        )
        .order_by(
            models.Training.weight.desc(),
            models.Training.reps.desc(),
            models.Training.date.desc(),
        )
        .first()
    )

    if row is None:
        return None

    return schemas.PersonalRecord(weight=float(row[0]), reps=float(row[1]), date=row[2])


@router.get(
    "/analytics/max-reps",
    response_model=schemas.MaxReps,
    tags=["analytics"],
)
def get_max_reps_for_weight(
    muscle: str,
    exercise: str,
    weight: float,
    principal: Principal = Depends(get_principal),
    db: Session = Depends(get_db),
) -> schemas.MaxReps:
    """Return the maximum reps ever performed at a given weight.

    Maps to ``get_max_reps_for_weight(user, muscle, exercise, weight)``.

    Args:
        muscle: Muscle group name.
        exercise: Exercise name.
        weight: Weight value to filter by.
        principal: Resolved identity from ``get_principal``.
        db: SQLAlchemy session.

    Returns:
        MaxReps (max_reps may be null when no history at that weight).
    """
    uid = principal["user_id"]

    result = (
        db.query(func.max(models.Training.reps))
        .join(models.Muscle, models.Training.muscle_id == models.Muscle.id)
        .join(models.Exercise, models.Training.exercise_id == models.Exercise.id)
        .filter(
            models.Training.user_id == uid,
            models.Muscle.name == muscle,
            models.Exercise.name == exercise,
            models.Training.weight == weight,
        )
        .scalar()
    )

    return schemas.MaxReps(max_reps=float(result) if result is not None else None)


@router.get(
    "/analytics/top-exercises",
    response_model=List[schemas.TopExercise],
    tags=["analytics"],
)
def get_top_exercises(
    muscle: str,
    limit: int = 5,
    principal: Principal = Depends(get_principal),
    db: Session = Depends(get_db),
) -> List[schemas.TopExercise]:
    """Return the most frequently used exercises for a muscle.

    Maps to ``get_top_exercises_for_muscle(user, muscle, limit)``.

    Args:
        muscle: Muscle group name.
        limit: Maximum number of exercises to return.
        principal: Resolved identity from ``get_principal``.
        db: SQLAlchemy session.

    Returns:
        Exercises ranked by training frequency (descending), then alphabetically.
    """
    uid = principal["user_id"]

    rows = (
        db.query(models.Exercise.name, func.count().label("frequency"))
        .join(models.Training, models.Training.exercise_id == models.Exercise.id)
        .join(models.Muscle, models.Training.muscle_id == models.Muscle.id)
        .filter(
            models.Training.user_id == uid,
            models.Muscle.name == muscle,
        )
        .group_by(models.Exercise.name)
        .order_by(func.count().desc(), models.Exercise.name.asc())
        .limit(limit)
        .all()
    )

    return [schemas.TopExercise(name=r[0], frequency=r[1]) for r in rows]
