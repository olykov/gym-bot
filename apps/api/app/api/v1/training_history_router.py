"""Training history endpoints — GYM-47.

Implements:
  GET  /training/days        — day-grouped summary, reverse-chronological
  GET  /training/day/{date}  — full exercise/set detail for one day
  DELETE /training/{id}      — delete caller's own set

All routes use ``get_principal`` + ``get_db_for_principal`` (RLS-scoped to
the authenticated caller, fail-closed).

Cache invalidation: every mutation calls ``cache.invalidate_user(uid)`` to
purge stale analytics:{user_id}:* keys so Dashboard/Progress numbers stay
current after edits.  Graceful if Redis is down.
"""
import logging
from collections import defaultdict
from datetime import date, datetime, timedelta
from typing import Dict, List, Optional

from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy import text
from sqlalchemy.orm import Session

from app.core.cache import invalidate_user
from app.core.database import get_db_for_principal
from app.middleware.permissions import Principal, get_principal
from app.models import models
from app.schemas import schemas

logger = logging.getLogger(__name__)

router = APIRouter()

_DEFAULT_WINDOW_DAYS = 180


@router.get(
    "/training/days",
    response_model=List[schemas.TrainingDay],
    tags=["training"],
)
def list_training_days(
    from_date: Optional[date] = Query(None, alias="from"),
    to_date: Optional[date] = Query(None, alias="to"),
    principal: Principal = Depends(get_principal),
    db: Session = Depends(get_db_for_principal),
) -> List[schemas.TrainingDay]:
    """List the caller's training days, grouped and reverse-chronological.

    Returns one entry per calendar day the caller trained within the optional
    ``from``/``to`` window (inclusive).  When omitted the window defaults to
    the last 180 days.  The WHERE clause is sargable — it filters on the raw
    ``date`` column which is covered by ``idx_training_user_date``.

    Args:
        from_date: Inclusive start date; defaults to today minus 180 days.
        to_date: Inclusive end date; defaults to today.
        principal: Resolved identity from ``get_principal``.
        db: SQLAlchemy session.

    Returns:
        List of ``TrainingDay`` summaries, newest first.
    """
    uid = principal["user_id"]
    today = date.today()
    date_from = from_date or (today - timedelta(days=_DEFAULT_WINDOW_DAYS))
    date_to = to_date or today

    # Sargable: compare the datetime column against datetime boundaries so
    # idx_training_user_date (user_id, date) is used without a function on date.
    # Reason: CAST(date AS date) in WHERE would disable index use; comparing the
    # raw timestamp column to [date_from 00:00:00, date_to+1 00:00:00) is index-safe.
    dt_from = datetime(date_from.year, date_from.month, date_from.day)
    dt_to = datetime(date_to.year, date_to.month, date_to.day) + timedelta(days=1)

    rows = db.execute(
        text("""
            SELECT
                t.date::date                      AS day,
                ARRAY_AGG(DISTINCT m.name)        AS muscles,
                COUNT(DISTINCT t.exercise_id)     AS exercises_count,
                COUNT(*)                          AS sets_count
            FROM training t
            JOIN muscles m ON m.id = t.muscle_id
            WHERE t.user_id = :uid
              AND t.date >= :dt_from
              AND t.date  < :dt_to
            GROUP BY t.date::date
            ORDER BY t.date::date DESC
        """),
        {"uid": uid, "dt_from": dt_from, "dt_to": dt_to},
    ).fetchall()

    return [
        schemas.TrainingDay(
            date=row.day,
            muscles=sorted(row.muscles),
            exercises_count=row.exercises_count,
            sets_count=row.sets_count,
        )
        for row in rows
    ]


@router.get(
    "/training/day/{day_date}",
    response_model=schemas.TrainingDayDetail,
    tags=["training"],
)
def get_training_day(
    day_date: date,
    principal: Principal = Depends(get_principal),
    db: Session = Depends(get_db_for_principal),
) -> schemas.TrainingDayDetail:
    """Return the caller's full training detail for a single calendar day.

    All sets recorded on the given day are returned, grouped by exercise with
    muscle and exercise names denormalized.  Returns an empty exercises list
    for a day with no training — never a 404 for the empty case.

    Args:
        day_date: Calendar date to fetch.
        principal: Resolved identity from ``get_principal``.
        db: SQLAlchemy session.

    Returns:
        ``TrainingDayDetail`` with exercises grouped by exercise_id, each
        containing its ordered list of sets.
    """
    uid = principal["user_id"]
    dt_from = datetime(day_date.year, day_date.month, day_date.day)
    dt_to = dt_from + timedelta(days=1)

    rows = db.execute(
        text("""
            SELECT
                t.id           AS training_id,
                t.set,
                t.weight,
                t.reps,
                t.exercise_id,
                e.name         AS exercise_name,
                m.name         AS muscle_name
            FROM training t
            JOIN exercises e ON e.id = t.exercise_id
            JOIN muscles   m ON m.id = t.muscle_id
            WHERE t.user_id = :uid
              AND t.date >= :dt_from
              AND t.date  < :dt_to
            ORDER BY e.name, t.set
        """),
        {"uid": uid, "dt_from": dt_from, "dt_to": dt_to},
    ).fetchall()

    # Group by exercise_id preserving order of first appearance.
    exercise_map: Dict[int, schemas.TrainingDayExercise] = {}
    for row in rows:
        eid = row.exercise_id
        if eid not in exercise_map:
            exercise_map[eid] = schemas.TrainingDayExercise(
                exercise_id=eid,
                exercise_name=row.exercise_name,
                muscle_name=row.muscle_name,
                sets=[],
            )
        exercise_map[eid].sets.append(
            schemas.TrainingSet(
                training_id=row.training_id,
                set=row.set,
                weight=float(row.weight),
                reps=float(row.reps),
            )
        )

    return schemas.TrainingDayDetail(
        date=day_date,
        exercises=list(exercise_map.values()),
    )


@router.delete(
    "/training/{training_id}",
    status_code=204,
    tags=["training"],
)
def delete_training(
    training_id: str,
    principal: Principal = Depends(get_principal),
    db: Session = Depends(get_db_for_principal),
) -> None:
    """Delete a training set owned by the authenticated user.

    Only the caller's own record is deleted.  Because RLS scopes to the
    caller, a cross-user ``training_id`` is invisible and treated as 404 —
    no cross-user deletion is ever possible.

    Args:
        training_id: Server-assigned id of the training set to delete.
        principal: Resolved identity from ``get_principal``.
        db: SQLAlchemy session.

    Raises:
        HTTPException 404: When the row does not exist or belongs to another user.
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

    db.delete(training)
    try:
        db.commit()
    except Exception as exc:
        db.rollback()
        logger.error("Error deleting training record: %s", exc, exc_info=True)
        raise HTTPException(status_code=500, detail="Failed to delete training record")

    invalidate_user(uid)
