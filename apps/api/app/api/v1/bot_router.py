"""Bot-facing endpoints — GYM-22 / GYM-26.

Covers users, muscles, and training operations.  Exercise endpoints are in
exercises_router.py; analytics are in analytics_router.py.

All routes derive the acting user's id from ``get_principal``, which accepts
EITHER a user JWT (Mini App) OR a service token + X-Act-As-User impersonation
(the Telegram bot).  No client-supplied user_id in body or query.

Isolation logic is centralised in ``app.services.visibility``.

Training id generation: uuid4().hex (32 lower-case hex chars).  This is the
only scheme used across the API (GYM-22 unification decision).  The bot's
legacy md5-based ids in existing rows are left untouched in the DB.
"""
import logging
import uuid
from datetime import datetime
from typing import List

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session

from app.core.database import get_db_for_principal
from app.middleware.permissions import Principal, get_principal
from app.models import models
from app.schemas import schemas
from app.services.visibility import visible_muscles

logger = logging.getLogger(__name__)

router = APIRouter()


# ---------------------------------------------------------------------------
# Users — GET /users/me, PUT /users/me
# ---------------------------------------------------------------------------


@router.get("/users/me", response_model=schemas.User, tags=["users"])
def get_me(
    principal: Principal = Depends(get_principal),
    db: Session = Depends(get_db_for_principal),
) -> schemas.User:
    """Return the authenticated user's profile.

    Maps to the bot's ``get_user(user_id)``.  Returns 404 when the caller has
    a valid identity but no stored user row yet.

    Args:
        principal: Resolved identity (user_id, role) from ``get_principal``.
        db: SQLAlchemy session.

    Returns:
        The user's profile.
    """
    uid = principal["user_id"]
    user = db.query(models.User).filter(models.User.id == uid).first()
    if user is None:
        raise HTTPException(status_code=404, detail="User not found")
    return user


@router.put("/users/me", response_model=schemas.User, tags=["users"])
def upsert_me(
    body: schemas.UserRegistration,
    principal: Principal = Depends(get_principal),
    db: Session = Depends(get_db_for_principal),
) -> schemas.User:
    """Register or update the authenticated user's profile.

    Maps to the bot's ``save_any_data("users", {...})``.  Idempotent.

    Args:
        body: Profile fields supplied by the caller.
        principal: Resolved identity from ``get_principal``.
        db: SQLAlchemy session.

    Returns:
        The created or updated user profile.
    """
    uid = principal["user_id"]
    user = db.query(models.User).filter(models.User.id == uid).first()

    if user is None:
        user = models.User(id=uid, registration_date=datetime.utcnow())
        db.add(user)

    if body.first_name is not None:
        user.first_name = body.first_name
    if body.lastname is not None:
        user.lastname = body.lastname
    if body.username is not None:
        user.username = body.username
    if body.bio is not None:
        user.bio = body.bio

    user.last_interaction = datetime.utcnow()

    db.commit()
    db.refresh(user)
    return user


# ---------------------------------------------------------------------------
# Muscles — list, create, hide/unhide, delete
# ---------------------------------------------------------------------------


@router.get("/muscles", response_model=List[schemas.Muscle], tags=["muscles"])
def list_muscles(
    principal: Principal = Depends(get_principal),
    db: Session = Depends(get_db_for_principal),
) -> List[schemas.Muscle]:
    """List muscle groups visible to the authenticated user.

    Maps to ``get_all_muscles(user_id)``: global not hidden + user's private,
    ordered by name.

    Args:
        principal: Resolved identity from ``get_principal``.
        db: SQLAlchemy session.

    Returns:
        Ordered list of visible muscles.
    """
    uid = principal["user_id"]
    return visible_muscles(db, uid)


@router.post("/muscles", response_model=schemas.Muscle, tags=["muscles"])
def create_muscle(
    body: schemas.MuscleCreate,
    principal: Principal = Depends(get_principal),
    db: Session = Depends(get_db_for_principal),
) -> schemas.Muscle:
    """Add a private muscle for the authenticated user.

    Maps to ``add_muscle(name, user_id)``.  Returns existing (global or
    private) if same name already visible to the user.

    Args:
        body: Muscle name.
        principal: Resolved identity from ``get_principal``.
        db: SQLAlchemy session.

    Returns:
        Existing or newly created muscle.
    """
    uid = principal["user_id"]
    name = body.name.strip()

    existing = (
        db.query(models.Muscle)
        .filter(
            models.Muscle.name == name,
            (models.Muscle.is_global.is_(True)) | (models.Muscle.created_by == uid),
        )
        .order_by(models.Muscle.is_global.desc())
        .first()
    )
    if existing:
        return existing

    muscle = models.Muscle(name=name, is_global=False, created_by=uid)
    db.add(muscle)
    db.commit()
    db.refresh(muscle)
    return muscle


@router.put("/muscles/{muscle_id}/hidden", status_code=204, tags=["muscles"])
def hide_muscle(
    muscle_id: int,
    principal: Principal = Depends(get_principal),
    db: Session = Depends(get_db_for_principal),
) -> None:
    """Hide a global muscle for the authenticated user.

    Args:
        muscle_id: Id of the global muscle to hide.
        principal: Resolved identity from ``get_principal``.
        db: SQLAlchemy session.
    """
    uid = principal["user_id"]
    muscle = db.query(models.Muscle).filter(models.Muscle.id == muscle_id).first()
    if muscle is None:
        raise HTTPException(status_code=404, detail="Muscle not found")

    exists = (
        db.query(models.UserHiddenMuscle)
        .filter(
            models.UserHiddenMuscle.user_id == uid,
            models.UserHiddenMuscle.muscle_id == muscle_id,
        )
        .first()
    )
    if not exists:
        db.add(models.UserHiddenMuscle(user_id=uid, muscle_id=muscle_id))
        db.commit()


@router.delete("/muscles/{muscle_id}/hidden", status_code=204, tags=["muscles"])
def unhide_muscle(
    muscle_id: int,
    principal: Principal = Depends(get_principal),
    db: Session = Depends(get_db_for_principal),
) -> None:
    """Unhide a previously hidden global muscle.

    Args:
        muscle_id: Id of the muscle to unhide.
        principal: Resolved identity from ``get_principal``.
        db: SQLAlchemy session.
    """
    uid = principal["user_id"]
    row = (
        db.query(models.UserHiddenMuscle)
        .filter(
            models.UserHiddenMuscle.user_id == uid,
            models.UserHiddenMuscle.muscle_id == muscle_id,
        )
        .first()
    )
    if row is None:
        raise HTTPException(status_code=404, detail="Hidden record not found")
    db.delete(row)
    db.commit()


@router.delete("/muscles/{muscle_id}", status_code=204, tags=["muscles"])
def delete_private_muscle(
    muscle_id: int,
    principal: Principal = Depends(get_principal),
    db: Session = Depends(get_db_for_principal),
) -> None:
    """Delete a private muscle owned by the authenticated user.

    Args:
        muscle_id: Id of the private muscle to delete.
        principal: Resolved identity from ``get_principal``.
        db: SQLAlchemy session.
    """
    uid = principal["user_id"]
    muscle = (
        db.query(models.Muscle)
        .filter(
            models.Muscle.id == muscle_id,
            models.Muscle.created_by == uid,
            models.Muscle.is_global.is_(False),
        )
        .first()
    )
    if muscle is None:
        raise HTTPException(status_code=404, detail="Private muscle not found")
    db.delete(muscle)
    db.commit()


# ---------------------------------------------------------------------------
# Training — list, create, update
# ---------------------------------------------------------------------------


@router.get("/training", response_model=List[schemas.Training], tags=["training"])
def list_training(
    skip: int = 0,
    limit: int = 100,
    principal: Principal = Depends(get_principal),
    db: Session = Depends(get_db_for_principal),
) -> List[schemas.Training]:
    """List the authenticated user's training records, newest first.

    Args:
        skip: Pagination offset.
        limit: Maximum records to return.
        principal: Resolved identity from ``get_principal``.
        db: SQLAlchemy session.

    Returns:
        Training records for the caller.
    """
    uid = principal["user_id"]
    return (
        db.query(models.Training)
        .filter(models.Training.user_id == uid)
        .order_by(models.Training.date.desc())
        .offset(skip)
        .limit(limit)
        .all()
    )


@router.post(
    "/training",
    response_model=schemas.Training,
    status_code=201,
    tags=["training"],
)
def create_training(
    body: schemas.TrainingCreate,
    principal: Principal = Depends(get_principal),
    db: Session = Depends(get_db_for_principal),
) -> schemas.Training:
    """Record a training set for the authenticated user.

    Maps to ``save_training_data(...)``.  Resolves muscle and exercise by name.
    Assigns a uuid4 hex id — the unified scheme for the whole API.

    Args:
        body: Set details (muscle_name, exercise_name, set, weight, reps).
        principal: Resolved identity from ``get_principal``.
        db: SQLAlchemy session.

    Returns:
        The created training record.
    """
    uid = principal["user_id"]

    muscle = (
        db.query(models.Muscle)
        .filter(models.Muscle.name == body.muscle_name)
        .first()
    )
    if muscle is None:
        raise HTTPException(status_code=404, detail="Muscle not found")

    exercise = (
        db.query(models.Exercise)
        .filter(models.Exercise.name == body.exercise_name)
        .first()
    )
    if exercise is None:
        raise HTTPException(status_code=404, detail="Exercise not found")

    training = models.Training(
        id=uuid.uuid4().hex,
        date=datetime.utcnow(),
        user_id=uid,
        muscle_id=muscle.id,
        exercise_id=exercise.id,
        set=body.set,
        weight=body.weight,
        reps=body.reps,
    )
    db.add(training)
    try:
        db.commit()
        db.refresh(training)
    except Exception as exc:
        db.rollback()
        logger.error("Error creating training record: %s", exc, exc_info=True)
        raise HTTPException(status_code=500, detail="Failed to save training record")

    return training


@router.put(
    "/training/{training_id}",
    response_model=schemas.Training,
    tags=["training"],
)
def update_training(
    training_id: str,
    body: schemas.TrainingUpdate,
    principal: Principal = Depends(get_principal),
    db: Session = Depends(get_db_for_principal),
) -> schemas.Training:
    """Update weight and reps of an existing training record.

    Maps to ``update_training_data(training_id, user_id, weight, reps)``.
    Only the caller's own record can be updated.

    Args:
        training_id: Server-assigned training id.
        body: New weight and reps values.
        principal: Resolved identity from ``get_principal``.
        db: SQLAlchemy session.

    Returns:
        The updated training record.
    """
    uid = principal["user_id"]
    training = (
        db.query(models.Training)
        .filter(
            models.Training.id == training_id,
            models.Training.user_id == uid,
        )
        .first()
    )
    if training is None:
        raise HTTPException(
            status_code=404, detail="Training record not found or access denied"
        )

    training.weight = body.weight
    training.reps = body.reps

    try:
        db.commit()
        db.refresh(training)
    except Exception as exc:
        db.rollback()
        logger.error("Error updating training record: %s", exc, exc_info=True)
        raise HTTPException(status_code=500, detail="Failed to update training record")

    return training
