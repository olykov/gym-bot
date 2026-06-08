"""Legacy admin and auth router (GYM-23 hardened).

Two routers are exported:

``router``
    Auth endpoints (/auth/*) and /static-data.  Mounted at /api/v1 — paths
    are unchanged from before GYM-23.

``admin_router``
    Admin-gated catalog management endpoints.  Mounted at /api/v1/admin — all
    require_admin dependency enforced.  Exact path mapping (GYM-23):

    GET  /admin/muscles
    POST /admin/muscles
    PUT  /admin/muscles/{muscle_id}
    GET  /admin/exercises
    POST /admin/exercises
    PUT  /admin/exercises/{exercise_id}
    GET  /admin/training
"""
from fastapi import APIRouter, Depends, HTTPException, Request
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session
from typing import List
from pydantic import BaseModel
from app.core.database import get_db_for_admin, get_db_for_user
from app.models import models
from app.schemas import schemas
from app.middleware.permissions import get_current_user, require_admin
from app.templates.exercise import sets, weights, reps
from app.core.auth import (
    verify_telegram_auth,
    verify_admin_credentials,
    create_session_token,
    verify_telegram_webapp_auth,
)
from app.services.resolve import resolve_muscle_id, resolve_exercise_id

# ---------------------------------------------------------------------------
# Auth / static-data router — paths UNCHANGED from pre-GYM-23
# ---------------------------------------------------------------------------

router = APIRouter()


@router.get("/static-data")
def get_static_data(current_user: dict = Depends(get_current_user)):
    """Get static data for dropdowns (sets, weights, reps).

    Args:
        current_user: Authenticated user from JWT.

    Returns:
        Dict with sets, weights, and reps option lists.
    """
    return {
        "sets": sets,
        "weights": weights,
        "reps": reps,
    }


class TelegramAuthRequest(BaseModel):
    id: int
    first_name: str
    last_name: str = ""
    username: str = ""
    photo_url: str = ""
    auth_date: int
    hash: str


class AdminAuthRequest(BaseModel):
    username: str
    password: str


class AuthResponse(BaseModel):
    token: str
    user: dict


class TelegramWebAppAuthRequest(BaseModel):
    initData: str


@router.post("/auth/telegram/webapp", response_model=AuthResponse)
def telegram_webapp_login(auth_request: TelegramWebAppAuthRequest):
    """Authenticate using Telegram Web App initData.

    Args:
        auth_request: Contains the raw initData string from Telegram WebApp.

    Returns:
        JWT token and decoded user data.
    """
    user_data = verify_telegram_webapp_auth(auth_request.initData)

    if not user_data:
        raise HTTPException(status_code=401, detail="Invalid Telegram Web App data")

    token = create_session_token(user_data)

    return {
        "token": token,
        "user": user_data,
    }


@router.post("/auth/telegram", response_model=AuthResponse)
async def telegram_login(request: Request):
    """Authenticate using Telegram Login Widget.

    Args:
        request: Raw request whose body contains Telegram auth fields.

    Returns:
        JWT token and decoded user data.
    """
    try:
        body = await request.json()
        auth_data = TelegramAuthRequest(**body)
    except Exception as exc:
        raise HTTPException(status_code=422, detail="Invalid request body") from exc

    user_data = verify_telegram_auth(auth_data.dict())

    if not user_data:
        raise HTTPException(status_code=401, detail="Invalid Telegram authentication data")

    token = create_session_token(user_data)

    return {
        "token": token,
        "user": user_data,
    }


@router.post("/auth/admin", response_model=AuthResponse)
def admin_login(credentials: AdminAuthRequest):
    """Authenticate using admin username and password.

    Args:
        credentials: Admin username and password.

    Returns:
        JWT token and decoded user data.
    """
    user_data = verify_admin_credentials(credentials.username, credentials.password)

    if not user_data:
        raise HTTPException(status_code=401, detail="Invalid credentials")

    token = create_session_token(user_data)

    return {
        "token": token,
        "user": user_data,
    }


@router.get("/auth/me")
def get_current_user_endpoint(current_user: dict = Depends(get_current_user)):
    """Get current user from JWT token.

    Args:
        current_user: Authenticated user injected by dependency.

    Returns:
        Decoded JWT claims for the caller.
    """
    return current_user


# ---------------------------------------------------------------------------
# Legacy user training endpoints — kept on /user/* prefix in main.py mount
# ---------------------------------------------------------------------------

import uuid
from datetime import datetime


class TrainingCreate(BaseModel):
    muscle_name: str
    exercise_name: str
    set_id: str  # "1", "2", etc.
    weight: str
    reps: str


class TrainingUpdate(BaseModel):
    weight: str
    reps: str


@router.get("/user/muscles")
def get_user_muscles(
    db: Session = Depends(get_db_for_user),
    current_user: dict = Depends(get_current_user),
):
    """Get muscles visible to the current user (legacy path).

    Args:
        db: SQLAlchemy session.
        current_user: JWT claims.

    Returns:
        List of visible muscle groups.
    """
    from app.services.visibility import visible_muscles

    user_id = int(current_user["sub"])
    return visible_muscles(db, user_id)


@router.get("/user/exercises")
def get_user_exercises(
    muscle_id: int,
    db: Session = Depends(get_db_for_user),
    current_user: dict = Depends(get_current_user),
):
    """Get exercises for a muscle visible to the current user (legacy path).

    Args:
        muscle_id: Muscle group id to filter by.
        db: SQLAlchemy session.
        current_user: JWT claims.

    Returns:
        List of visible exercises for the given muscle.
    """
    from app.services.visibility import visible_exercises_for_muscle

    user_id = int(current_user["sub"])
    return visible_exercises_for_muscle(db, user_id, muscle_id)


@router.post("/user/training")
def create_user_training(
    training: TrainingCreate,
    db: Session = Depends(get_db_for_user),
    current_user: dict = Depends(get_current_user),
):
    """Create a new training record for the current user.

    Args:
        training: Training set details (muscle, exercise, set, weight, reps).
        db: SQLAlchemy session.
        current_user: JWT claims.

    Returns:
        Dict with success flag and the new training id.
    """
    user_id = int(current_user["sub"])

    # GYM-106: resolve by name_key (own-first-then-global, variant-name aware).
    muscle_id = resolve_muscle_id(db, user_id, training.muscle_name)
    if not muscle_id:
        raise HTTPException(status_code=404, detail="Muscle not found")

    exercise_id = resolve_exercise_id(db, user_id, training.muscle_name, training.exercise_name)
    if not exercise_id:
        raise HTTPException(status_code=404, detail="Exercise not found")

    new_id = uuid.uuid4().hex

    new_training = models.Training(
        id=new_id,
        date=datetime.now(),
        user_id=user_id,
        muscle_id=muscle_id,
        exercise_id=exercise_id,
        set=int(training.set_id),
        weight=float(training.weight),
        reps=int(training.reps),
    )

    db.add(new_training)
    try:
        db.commit()
        db.refresh(new_training)
        return {"success": True, "id": new_id}
    except Exception as exc:
        db.rollback()
        raise HTTPException(status_code=500, detail=str(exc)) from exc


@router.put("/user/training/{training_id}")
def update_user_training(
    training_id: str,
    training: TrainingUpdate,
    db: Session = Depends(get_db_for_user),
    current_user: dict = Depends(get_current_user),
):
    """Update weight and reps of an existing training record.

    Args:
        training_id: The training record id.
        training: New weight and reps values.
        db: SQLAlchemy session.
        current_user: JWT claims.

    Returns:
        Dict with success flag.
    """
    user_id = int(current_user["sub"])

    db_training = db.query(models.Training).filter(
        models.Training.id == training_id,
        models.Training.user_id == user_id,
    ).first()

    if not db_training:
        raise HTTPException(status_code=404, detail="Training record not found or access denied")

    db_training.weight = float(training.weight)
    db_training.reps = int(training.reps)

    try:
        db.commit()
        return {"success": True}
    except Exception as exc:
        db.rollback()
        raise HTTPException(status_code=500, detail=str(exc)) from exc


# ---------------------------------------------------------------------------
# Admin catalog router — mounted at /api/v1/admin in main.py (GYM-23)
# ---------------------------------------------------------------------------

admin_router = APIRouter(tags=["admin"])


@admin_router.get("/muscles", response_model=List[schemas.Muscle])
def admin_read_muscles(
    skip: int = 0,
    limit: int = 100,
    db: Session = Depends(get_db_for_admin),
    current_user: dict = Depends(require_admin),
):
    """List all muscle groups (admin only).

    Args:
        skip: Pagination offset.
        limit: Maximum records to return.
        db: SQLAlchemy session.
        current_user: Admin user from require_admin dependency.

    Returns:
        List of all muscle groups.
    """
    return db.query(models.Muscle).offset(skip).limit(limit).all()


@admin_router.post("/muscles", response_model=schemas.Muscle)
def admin_create_muscle(
    muscle: schemas.MuscleCreate,
    db: Session = Depends(get_db_for_admin),
    current_user: dict = Depends(require_admin),
):
    """Create a new muscle group (admin only).

    Args:
        muscle: Muscle name.
        db: SQLAlchemy session.
        current_user: Admin user from require_admin dependency.

    Returns:
        Newly created muscle group.
    """
    db_muscle = models.Muscle(name=muscle.name)
    db.add(db_muscle)
    try:
        db.commit()
        db.refresh(db_muscle)
    except IntegrityError:
        db.rollback()
        raise HTTPException(status_code=400, detail="Muscle group with this name already exists")
    return db_muscle


@admin_router.put("/muscles/{muscle_id}", response_model=schemas.Muscle)
def admin_update_muscle(
    muscle_id: int,
    muscle: schemas.MuscleCreate,
    db: Session = Depends(get_db_for_admin),
    current_user: dict = Depends(require_admin),
):
    """Update an existing muscle group (admin only).

    Args:
        muscle_id: Id of the muscle to update.
        muscle: New name.
        db: SQLAlchemy session.
        current_user: Admin user from require_admin dependency.

    Returns:
        Updated muscle group.
    """
    db_muscle = db.query(models.Muscle).filter(models.Muscle.id == muscle_id).first()
    if not db_muscle:
        raise HTTPException(status_code=404, detail="Muscle group not found")

    db_muscle.name = muscle.name

    try:
        db.commit()
        db.refresh(db_muscle)
    except IntegrityError:
        db.rollback()
        raise HTTPException(status_code=400, detail="Muscle group with this name already exists")

    return db_muscle


@admin_router.get("/exercises", response_model=List[schemas.Exercise])
def admin_read_exercises(
    skip: int = 0,
    limit: int = 100,
    db: Session = Depends(get_db_for_admin),
    current_user: dict = Depends(require_admin),
):
    """List all exercises (admin only).

    Args:
        skip: Pagination offset.
        limit: Maximum records to return.
        db: SQLAlchemy session.
        current_user: Admin user from require_admin dependency.

    Returns:
        List of all exercises.
    """
    return db.query(models.Exercise).offset(skip).limit(limit).all()


@admin_router.post("/exercises", response_model=schemas.Exercise)
def admin_create_exercise(
    exercise: schemas.ExerciseCreate,
    db: Session = Depends(get_db_for_admin),
    current_user: dict = Depends(require_admin),
):
    """Create a new exercise (admin only).

    Args:
        exercise: Exercise name and associated muscle.
        db: SQLAlchemy session.
        current_user: Admin user from require_admin dependency.

    Returns:
        Newly created exercise.
    """
    db_exercise = models.Exercise(name=exercise.name, muscle=exercise.muscle)
    db.add(db_exercise)
    try:
        db.commit()
        db.refresh(db_exercise)
    except IntegrityError:
        db.rollback()
        raise HTTPException(
            status_code=400,
            detail="Exercise with this name already exists for this muscle group",
        )
    return db_exercise


@admin_router.put("/exercises/{exercise_id}", response_model=schemas.Exercise)
def admin_update_exercise(
    exercise_id: int,
    exercise: schemas.ExerciseCreate,
    db: Session = Depends(get_db_for_admin),
    current_user: dict = Depends(require_admin),
):
    """Update an existing exercise (admin only).

    Args:
        exercise_id: Id of the exercise to update.
        exercise: New name and muscle.
        db: SQLAlchemy session.
        current_user: Admin user from require_admin dependency.

    Returns:
        Updated exercise.
    """
    db_exercise = db.query(models.Exercise).filter(models.Exercise.id == exercise_id).first()
    if not db_exercise:
        raise HTTPException(status_code=404, detail="Exercise not found")

    db_exercise.name = exercise.name
    db_exercise.muscle = exercise.muscle

    try:
        db.commit()
        db.refresh(db_exercise)
    except IntegrityError:
        db.rollback()
        raise HTTPException(
            status_code=400,
            detail="Exercise with this name already exists for this muscle group",
        )

    return db_exercise


@admin_router.get("/training", response_model=List[schemas.Training])
def admin_read_training(
    skip: int = 0,
    limit: int = 100,
    db: Session = Depends(get_db_for_admin),
    current_user: dict = Depends(require_admin),
):
    """List all training records across all users (admin only).

    Args:
        skip: Pagination offset.
        limit: Maximum records to return.
        db: SQLAlchemy session.
        current_user: Admin user from require_admin dependency.

    Returns:
        List of training records ordered newest first.
    """
    return (
        db.query(models.Training)
        .order_by(models.Training.date.desc())
        .offset(skip)
        .limit(limit)
        .all()
    )
