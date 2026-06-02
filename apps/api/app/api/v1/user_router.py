from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session
from typing import List
from app.core.database import get_db_for_user
from app.models import models
from app.schemas import schemas
from app.middleware.permissions import require_user

router = APIRouter()


@router.get("/training", response_model=List[schemas.Training])
def get_user_training(
    skip: int = 0,
    limit: int = 100,
    user_data: dict = Depends(require_user),
    db: Session = Depends(get_db_for_user),
):
    """Get training data for the authenticated user only.

    Args:
        skip: Pagination offset.
        limit: Maximum records to return.
        user_data: JWT claims injected by require_user.
        db: SQLAlchemy session.

    Returns:
        Training records for the authenticated user, newest first.
    """
    # Cast sub to int so the comparison matches the BigInteger Training.user_id column.
    user_id = int(user_data["sub"])

    training = (
        db.query(models.Training)
        .filter(models.Training.user_id == user_id)
        .order_by(models.Training.date.desc())
        .offset(skip)
        .limit(limit)
        .all()
    )

    return training
