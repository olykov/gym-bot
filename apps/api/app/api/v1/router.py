from fastapi import APIRouter, Depends, HTTPException, Request, Header
from sqlalchemy.orm import Session
from typing import List, Optional
from pydantic import BaseModel
from app.core.database import get_db
from app.models import models
from app.schemas import schemas
from app.core.auth import verify_session_token

router = APIRouter()

def get_current_user(authorization: Optional[str] = Header(None)):
    """Dependency to get current user from JWT token"""
    if not authorization or not authorization.startswith("Bearer "):
        raise HTTPException(status_code=401, detail="Not authenticated")
    
    token = authorization.replace("Bearer ", "")
    user_data = verify_session_token(token)
    
    if not user_data:
        raise HTTPException(status_code=401, detail="Invalid or expired token")
    
    return user_data

@router.get("/muscles", response_model=List[schemas.Muscle])
def read_muscles(skip: int = 0, limit: int = 100, db: Session = Depends(get_db), current_user: dict = Depends(get_current_user)):
    muscles = db.query(models.Muscle).offset(skip).limit(limit).all()
    return muscles

@router.post("/muscles", response_model=schemas.Muscle)
def create_muscle(muscle: schemas.MuscleCreate, db: Session = Depends(get_db), current_user: dict = Depends(get_current_user)):
    db_muscle = models.Muscle(name=muscle.name)
    db.add(db_muscle)
    try:
        db.commit()
        db.refresh(db_muscle)
    except IntegrityError:
        db.rollback()
        raise HTTPException(status_code=400, detail="Muscle group with this name already exists")
    return db_muscle

@router.put("/muscles/{muscle_id}", response_model=schemas.Muscle)
def update_muscle(muscle_id: int, muscle: schemas.MuscleCreate, db: Session = Depends(get_db), current_user: dict = Depends(get_current_user)):
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

@router.get("/exercises", response_model=List[schemas.Exercise])
def read_exercises(skip: int = 0, limit: int = 100, db: Session = Depends(get_db), current_user: dict = Depends(get_current_user)):
    exercises = db.query(models.Exercise).offset(skip).limit(limit).all()
    return exercises

from sqlalchemy.exc import IntegrityError

@router.post("/exercises", response_model=schemas.Exercise)
def create_exercise(exercise: schemas.ExerciseCreate, db: Session = Depends(get_db), current_user: dict = Depends(get_current_user)):
    db_exercise = models.Exercise(name=exercise.name, muscle=exercise.muscle)
    db.add(db_exercise)
    try:
        db.commit()
        db.refresh(db_exercise)
    except IntegrityError:
        db.rollback()
        raise HTTPException(status_code=400, detail="Exercise with this name already exists for this muscle group")
    return db_exercise

@router.put("/exercises/{exercise_id}", response_model=schemas.Exercise)
def update_exercise(exercise_id: int, exercise: schemas.ExerciseCreate, db: Session = Depends(get_db), current_user: dict = Depends(get_current_user)):
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
        raise HTTPException(status_code=400, detail="Exercise with this name already exists for this muscle group")
    
    return db_exercise

@router.get("/training", response_model=List[schemas.Training])
def read_training(skip: int = 0, limit: int = 100, db: Session = Depends(get_db), current_user: dict = Depends(get_current_user)):
    training = db.query(models.Training).order_by(models.Training.date.desc()).offset(skip).limit(limit).all()
    return training


# User Training Management Endpoints

from app.templates.exercise import sets, weights, reps
import uuid
from datetime import datetime

@router.get("/static-data")
def get_static_data(current_user: dict = Depends(get_current_user)):
    """Get static data for dropdowns (sets, weights, reps)"""
    return {
        "sets": sets,
        "weights": weights,
        "reps": reps
    }

@router.get("/user/muscles")
def get_user_muscles(db: Session = Depends(get_db), current_user: dict = Depends(get_current_user)):
    """Get muscles visible to the current user"""
    # We need to use the PostgresDB class directly or add a method to the SQLAlchemy repository
    # Since the original code uses raw SQL in PostgresDB class, we should probably use that if possible,
    # OR replicate the logic in SQLAlchemy.
    # Given the project structure mixes SQLAlchemy and raw SQL (via PostgresDB class in app/modules),
    # and the user wants to use the existing logic, let's try to use the PostgresDB instance if available,
    # or replicate the query using SQLAlchemy.
    # The `db` dependency is a SQLAlchemy Session.
    # The `PostgresDB` class is instantiated in `handlers.py` and `markups.py` but not injected here.
    # However, we can use raw SQL with the SQLAlchemy session.
    
    user_id = int(current_user['sub'])
    
    # Replicating logic from PostgresDB.get_all_muscles using SQLAlchemy
    # Logic: (is_global = TRUE AND id NOT IN user_hidden_muscles) OR (created_by = user_id)
    
    # Subquery for hidden muscles
    hidden_muscles = db.query(models.UserHiddenMuscle.muscle_id).filter(models.UserHiddenMuscle.user_id == user_id)
    
    muscles = db.query(models.Muscle).filter(
        ((models.Muscle.is_global == True) & (~models.Muscle.id.in_(hidden_muscles))) |
        (models.Muscle.created_by == user_id)
    ).order_by(models.Muscle.name).all()
    
    return muscles

@router.get("/user/exercises")
def get_user_exercises(muscle_id: int, db: Session = Depends(get_db), current_user: dict = Depends(get_current_user)):
    """Get exercises for a specific muscle visible to the current user"""
    user_id = int(current_user['sub'])
    
    # Logic: muscle_id matches AND ((is_global = TRUE AND id NOT IN user_hidden_exercises) OR (created_by = user_id))
    
    hidden_exercises = db.query(models.UserHiddenExercise.exercise_id).filter(models.UserHiddenExercise.user_id == user_id)
    
    exercises = db.query(models.Exercise).filter(
        models.Exercise.muscle == muscle_id,
        ((models.Exercise.is_global == True) & (~models.Exercise.id.in_(hidden_exercises))) |
        (models.Exercise.created_by == user_id)
    ).order_by(models.Exercise.name).all()
    
    return exercises

class TrainingCreate(BaseModel):
    muscle_name: str
    exercise_name: str
    set_id: str # "1", "2", etc.
    weight: str
    reps: str

@router.post("/user/training")
def create_user_training(training: TrainingCreate, db: Session = Depends(get_db), current_user: dict = Depends(get_current_user)):
    """Create a new training record for the current user"""
    user_id = int(current_user['sub'])
    
    # We need to resolve muscle and exercise names to IDs
    # But wait, the PostgresDB.save_training_data takes names and does subqueries.
    # Let's use the PostgresDB logic but adapted for SQLAlchemy to keep it consistent with this router.
    
    muscle = db.query(models.Muscle).filter(models.Muscle.name == training.muscle_name).first()
    if not muscle:
        raise HTTPException(status_code=404, detail="Muscle not found")
        
    exercise = db.query(models.Exercise).filter(models.Exercise.name == training.exercise_name).first()
    if not exercise:
        raise HTTPException(status_code=404, detail="Exercise not found")
    
    # Generate ID (using uuid4 as discussed)
    new_id = uuid.uuid4().hex
    
    new_training = models.Training(
        id=new_id,
        date=datetime.now(),
        user_id=user_id,
        muscle_id=muscle.id,
        exercise_id=exercise.id,
        set=int(training.set_id),
        weight=float(training.weight),
        reps=int(training.reps)
    )
    
    db.add(new_training)
    try:
        db.commit()
        db.refresh(new_training)
        return {"success": True, "id": new_id}
    except Exception as e:
        db.rollback()
        raise HTTPException(status_code=500, detail=str(e))

class TrainingUpdate(BaseModel):
    weight: str
    reps: str

@router.put("/user/training/{training_id}")
def update_user_training(training_id: str, training: TrainingUpdate, db: Session = Depends(get_db), current_user: dict = Depends(get_current_user)):
    """Update an existing training record (weight and reps only)"""
    user_id = int(current_user['sub'])
    
    db_training = db.query(models.Training).filter(
        models.Training.id == training_id,
        models.Training.user_id == user_id
    ).first()
    
    if not db_training:
        raise HTTPException(status_code=404, detail="Training record not found or access denied")
        
    db_training.weight = float(training.weight)
    db_training.reps = int(training.reps)
    
    try:
        db.commit()
        return {"success": True}
    except Exception as e:
        db.rollback()
        raise HTTPException(status_code=500, detail=str(e))
from app.core.auth import verify_telegram_auth, verify_admin_credentials, create_session_token, verify_session_token, verify_telegram_webapp_auth


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
    """Authenticate using Telegram Web App initData"""
    print(f"[ENDPOINT] /auth/telegram/webapp called")
    
    user_data = verify_telegram_webapp_auth(auth_request.initData)
    
    if not user_data:
        raise HTTPException(status_code=401, detail="Invalid Telegram Web App data")
    
    token = create_session_token(user_data)
    
    return {
        "token": token,
        "user": user_data
    }

@router.post("/auth/telegram", response_model=AuthResponse)
async def telegram_login(request: Request):
    """Authenticate using Telegram Login Widget"""
    try:
        body = await request.json()
        print(f"[ENDPOINT] /auth/telegram called with raw data: {body}")
        auth_data = TelegramAuthRequest(**body)
    except Exception as e:
        print(f"[ENDPOINT] Error parsing request body: {e}")
        raise HTTPException(status_code=422, detail="Invalid request body")

    print(f"[ENDPOINT] /auth/telegram validated data: {auth_data.dict()}")
    
    user_data = verify_telegram_auth(auth_data.dict())
    
    if not user_data:
        print("[ENDPOINT] Authentication failed - user_data is None")
        raise HTTPException(status_code=401, detail="Invalid Telegram authentication data")
    
    print(f"[ENDPOINT] Authentication successful for user: {user_data}")
    token = create_session_token(user_data)
    print(f"[ENDPOINT] Token created, returning response")
    
    return {
        "token": token,
        "user": user_data
    }

@router.post("/auth/admin", response_model=AuthResponse)
def admin_login(credentials: AdminAuthRequest):
    """Authenticate using admin username and password"""
    user_data = verify_admin_credentials(credentials.username, credentials.password)
    
    if not user_data:
        raise HTTPException(status_code=401, detail="Invalid credentials")
    
    token = create_session_token(user_data)
    
    return {
        "token": token,
        "user": user_data
    }

@router.get("/auth/me")
def get_current_user_endpoint(current_user: dict = Depends(get_current_user)):
    """Get current user from JWT token"""
    return current_user
