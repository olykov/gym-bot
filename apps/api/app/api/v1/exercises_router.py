"""Exercise endpoints — GYM-22 / GYM-26.

Covers list, create, hide/unhide, and delete for exercises, all scoped to the
authenticated user.  Isolation (visible exercises) is delegated to
``app.services.visibility``.

All routes accept EITHER a user JWT (Mini App) OR a service token +
X-Act-As-User impersonation (the Telegram bot) via ``get_principal``.
"""
import logging
from typing import List

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session

from app.core.database import get_db_for_principal
from app.middleware.permissions import Principal, get_principal
from app.models import models
from app.schemas import schemas
from app.services.visibility import visible_exercises_for_muscle

logger = logging.getLogger(__name__)

router = APIRouter()


@router.get(
    "/muscles/{muscle_id}/exercises",
    response_model=List[schemas.Exercise],
    tags=["exercises"],
)
def list_exercises_by_muscle(
    muscle_id: int,
    principal: Principal = Depends(get_principal),
    db: Session = Depends(get_db_for_principal),
) -> List[schemas.Exercise]:
    """List exercises for a muscle visible to the authenticated user.

    Maps to ``get_exercises_by_muscle(muscle, user_id)``.

    Args:
        muscle_id: Parent muscle id.
        principal: Resolved identity from ``get_principal``.
        db: SQLAlchemy session.

    Returns:
        Ordered list of visible exercises.
    """
    uid = principal["user_id"]
    muscle = db.query(models.Muscle).filter(models.Muscle.id == muscle_id).first()
    if muscle is None:
        raise HTTPException(status_code=404, detail="Muscle not found")
    return visible_exercises_for_muscle(db, uid, muscle_id)


@router.post("/exercises", response_model=schemas.Exercise, tags=["exercises"])
def create_exercise(
    body: schemas.ExerciseCreateByName,
    principal: Principal = Depends(get_principal),
    db: Session = Depends(get_db_for_principal),
) -> schemas.Exercise:
    """Add a private exercise for the authenticated user.

    Maps to ``add_exercise(name, muscle_name, user_id)``.  Finds or creates
    the muscle by name, then finds or creates the exercise.

    Args:
        body: Exercise name and muscle name.
        principal: Resolved identity from ``get_principal``.
        db: SQLAlchemy session.

    Returns:
        Existing or newly created exercise.
    """
    uid = principal["user_id"]
    muscle_name = body.muscle_name.strip()
    exercise_name = body.name.strip()

    muscle = (
        db.query(models.Muscle)
        .filter(
            models.Muscle.name == muscle_name,
            (models.Muscle.is_global.is_(True)) | (models.Muscle.created_by == uid),
        )
        .order_by(models.Muscle.is_global.desc())
        .first()
    )
    if muscle is None:
        muscle = models.Muscle(name=muscle_name, is_global=False, created_by=uid)
        db.add(muscle)
        db.flush()

    muscle_id = muscle.id

    exercise = (
        db.query(models.Exercise)
        .filter(
            models.Exercise.name == exercise_name,
            models.Exercise.muscle == muscle_id,
            models.Exercise.created_by == uid,
        )
        .first()
    )
    if exercise is None:
        exercise = models.Exercise(
            name=exercise_name,
            muscle=muscle_id,
            is_global=False,
            created_by=uid,
        )
        db.add(exercise)

    db.commit()
    db.refresh(exercise)
    return exercise


@router.put(
    "/exercises/{exercise_id}/hidden",
    status_code=204,
    tags=["exercises"],
)
def hide_exercise(
    exercise_id: int,
    principal: Principal = Depends(get_principal),
    db: Session = Depends(get_db_for_principal),
) -> None:
    """Hide a global exercise for the authenticated user.

    Maps to ``hide_exercise(user_id, exercise_name, muscle_name)``.

    Args:
        exercise_id: Id of the global exercise to hide.
        principal: Resolved identity from ``get_principal``.
        db: SQLAlchemy session.
    """
    uid = principal["user_id"]
    exercise = (
        db.query(models.Exercise)
        .filter(
            models.Exercise.id == exercise_id,
            models.Exercise.is_global.is_(True),
        )
        .first()
    )
    if exercise is None:
        raise HTTPException(status_code=404, detail="Global exercise not found")

    exists = (
        db.query(models.UserHiddenExercise)
        .filter(
            models.UserHiddenExercise.user_id == uid,
            models.UserHiddenExercise.exercise_id == exercise_id,
        )
        .first()
    )
    if not exists:
        db.add(models.UserHiddenExercise(user_id=uid, exercise_id=exercise_id))
        db.commit()


@router.delete(
    "/exercises/{exercise_id}/hidden",
    status_code=204,
    tags=["exercises"],
)
def unhide_exercise(
    exercise_id: int,
    principal: Principal = Depends(get_principal),
    db: Session = Depends(get_db_for_principal),
) -> None:
    """Unhide a previously hidden global exercise.

    Args:
        exercise_id: Id of the exercise to unhide.
        principal: Resolved identity from ``get_principal``.
        db: SQLAlchemy session.
    """
    uid = principal["user_id"]
    row = (
        db.query(models.UserHiddenExercise)
        .filter(
            models.UserHiddenExercise.user_id == uid,
            models.UserHiddenExercise.exercise_id == exercise_id,
        )
        .first()
    )
    if row is None:
        raise HTTPException(status_code=404, detail="Hidden record not found")
    db.delete(row)
    db.commit()


@router.delete("/exercises/{exercise_id}", status_code=204, tags=["exercises"])
def delete_private_exercise(
    exercise_id: int,
    principal: Principal = Depends(get_principal),
    db: Session = Depends(get_db_for_principal),
) -> None:
    """Delete a private exercise owned by the authenticated user.

    Maps to ``delete_private_exercise(user_id, exercise_name, muscle_name)``.

    Args:
        exercise_id: Id of the private exercise to delete.
        principal: Resolved identity from ``get_principal``.
        db: SQLAlchemy session.
    """
    uid = principal["user_id"]
    exercise = (
        db.query(models.Exercise)
        .filter(
            models.Exercise.id == exercise_id,
            models.Exercise.created_by == uid,
            models.Exercise.is_global.is_(False),
        )
        .first()
    )
    if exercise is None:
        raise HTTPException(status_code=404, detail="Private exercise not found")
    db.delete(exercise)
    db.commit()
