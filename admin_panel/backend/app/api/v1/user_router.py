from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session
from typing import List
from app.core.database import get_db
from app.models import models
from app.schemas import schemas
from app.middleware.permissions import require_user

router = APIRouter()


@router.get("/training", response_model=List[schemas.Training])
def get_user_training(
    skip: int = 0,
    limit: int = 100,
    user_data: dict = Depends(require_user),
    db: Session = Depends(get_db)
):
    """Get training data for the authenticated user only"""
    user_id = user_data.get("sub")  # "sub" contains the user ID from JWT
    
    training = db.query(models.Training)\
        .filter(models.Training.user_id == user_id)\
        .order_by(models.Training.date.desc())\
        .offset(skip)\
        .limit(limit)\
        .all()
    
    return training
