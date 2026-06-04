"""Analytics endpoints — GYM-22 / GYM-26 / GYM-39.

All analytics reads are scoped by the authenticated user (derived from
``get_principal``), which accepts EITHER a user JWT OR service-token
impersonation.  Queries faithfully mirror the bot's postgres.py
implementations:
- get_completed_sets
- get_last_training_history
- get_personal_record
- get_max_reps_for_weight
- get_top_exercises_for_muscle

GYM-39 additions (Mini App dashboard):
- get_activity     — daily set counts for a date range, sargable on idx_training_user_date
- get_summary      — 4 headline metrics (exercises, sets, prs, current_streak)
- get_exercise_progress — per-set weight/reps series for ECharts
"""
import logging
from collections import defaultdict
from datetime import datetime, date, timedelta, timezone
from typing import Dict, List, Optional

from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy import func, text
from sqlalchemy.orm import Session

from app.core.cache import cache_get, cache_set, make_key
from app.core.database import get_db_for_principal
from app.middleware.permissions import Principal, get_principal
from app.models import models
from app.schemas import schemas

logger = logging.getLogger(__name__)

router = APIRouter()

# Maximum date-range span for /analytics/activity (reject absurd ranges).
_MAX_ACTIVITY_DAYS = 400


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
    db: Session = Depends(get_db_for_principal),
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
    db: Session = Depends(get_db_for_principal),
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
    db: Session = Depends(get_db_for_principal),
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
    db: Session = Depends(get_db_for_principal),
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
    db: Session = Depends(get_db_for_principal),
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


# ---------------------------------------------------------------------------
# GYM-39: Dashboard / Mini App analytics
# ---------------------------------------------------------------------------


@router.get(
    "/analytics/activity",
    response_model=List[schemas.ActivityDay],
    tags=["analytics"],
)
def get_activity(
    from_date: date = Query(..., alias="from"),
    to_date: date = Query(..., alias="to"),
    principal: Principal = Depends(get_principal),
    db: Session = Depends(get_db_for_principal),
) -> List[schemas.ActivityDay]:
    """Return daily set counts for a date range (activity contribution grid).

    One entry per day that has activity within [from_date, to_date].  Days with
    no training are omitted.  The range is inclusive on both ends but capped at
    400 days to prevent full-table scans on large histories.

    Sargability note: the WHERE clause uses ``date >= :from AND date < :to_exclusive``
    (i.e. a half-open range on the raw TIMESTAMP column) so that Postgres can use
    ``idx_training_user_date (user_id, date)`` without wrapping the column in a
    function.  CAST(date AS DATE) appears only in GROUP BY / SELECT, never in WHERE.

    Args:
        from_date: Inclusive start date (``from`` query parameter).
        to_date: Inclusive end date (``to`` query parameter).
        principal: Resolved identity from ``get_principal``.
        db: SQLAlchemy session.

    Returns:
        List of ActivityDay objects, one per active day, ordered by date ascending.

    Raises:
        HTTPException 400: If ``from`` > ``to`` or range exceeds 400 days.
    """
    if from_date > to_date:
        raise HTTPException(status_code=400, detail="'from' must be <= 'to'")
    span = (to_date - from_date).days + 1
    if span > _MAX_ACTIVITY_DAYS:
        raise HTTPException(
            status_code=400,
            detail=f"Date range too large ({span} days). Maximum is {_MAX_ACTIVITY_DAYS} days.",
        )

    uid = principal["user_id"]
    cache_key = make_key(uid, "activity", frm=str(from_date), to=str(to_date))
    cached = cache_get(cache_key)
    if cached is not None:
        return [schemas.ActivityDay(**item) for item in cached]

    # Half-open range: [from_date 00:00:00, to_date+1day 00:00:00)
    # Reason: idx_training_user_date is on (user_id, date); plain range predicates on
    # `date` allow Postgres to use the index without a function scan.
    # DATE_TRUNC appears only in GROUP BY / SELECT, never in WHERE.
    to_exclusive = datetime(to_date.year, to_date.month, to_date.day) + timedelta(days=1)
    from_dt = datetime(from_date.year, from_date.month, from_date.day)

    rows = db.execute(
        text("""
            SELECT
                DATE_TRUNC('day', date) AS day,
                COUNT(*)                AS sets_count
            FROM training
            WHERE user_id = :uid
              AND date >= :from_dt
              AND date  < :to_exclusive
            GROUP BY DATE_TRUNC('day', date)
            ORDER BY DATE_TRUNC('day', date)
        """),
        {"uid": uid, "from_dt": from_dt, "to_exclusive": to_exclusive},
    ).fetchall()

    # Build result — extract the calendar date from the truncated timestamp.
    result = []
    for r in rows:
        day_ts = r[0]
        day = day_ts.date() if hasattr(day_ts, "date") else day_ts
        result.append(schemas.ActivityDay(date=day, sets_count=r[1]))

    cache_set(cache_key, [{"date": str(item.date), "sets_count": item.sets_count} for item in result])
    return result


@router.get(
    "/analytics/summary",
    response_model=schemas.AnalyticsSummary,
    tags=["analytics"],
)
def get_analytics_summary(
    principal: Principal = Depends(get_principal),
    db: Session = Depends(get_db_for_principal),
) -> schemas.AnalyticsSummary:
    """Return headline dashboard metrics for the caller.

    Metrics:
        exercises: count(distinct exercise_id) — distinct exercises ever logged.
        sets: count(*) — total training rows (one row = one set).
        prs: count of all-time PR events — training rows where the logged weight
            strictly exceeds the running max weight seen previously for the same
            (user_id, exercise_id), ordered chronologically by (date, set).
            Reason: the previous definition (prs = count(distinct exercise_id))
            made prs always equal to exercises, which rendered as two identical
            numbers on the 2×2 dashboard and looked like a bug (GYM-44).
            The new definition counts genuinely new personal-record moments: the
            first set of any exercise always counts (prev_max IS NULL), and
            subsequent sets count only when weight is strictly greater than every
            prior set for that exercise.  This produces a meaningfully different
            metric (prs <= sets, and typically prs < exercises for exercisers who
            have been training consistently with progressive overload).
        current_streak: consecutive calendar days up to today (UTC) with >=1 set.
            Reason: training timestamps are stored in UTC (Postgres TIMESTAMP WITHOUT
            TIME ZONE, inserted as NOW() which the server interprets as UTC).  Using
            UTC for streak calculation is consistent with the stored data.  A Georgia
            (+4) timezone offset could be added later but would require either storing
            TZ-aware timestamps or accepting an offset parameter — out of scope here.

    Args:
        principal: Resolved identity from ``get_principal``.
        db: SQLAlchemy session.

    Returns:
        AnalyticsSummary with exercises, sets, prs, current_streak.
    """
    uid = principal["user_id"]
    cache_key = make_key(uid, "summary")
    cached = cache_get(cache_key)
    if cached is not None:
        return schemas.AnalyticsSummary(**cached)

    # Aggregate query for exercises and sets.
    agg = db.execute(
        text("""
            SELECT
                COUNT(DISTINCT exercise_id) AS exercises,
                COUNT(*)                    AS sets
            FROM training
            WHERE user_id = :uid
        """),
        {"uid": uid},
    ).fetchone()

    exercises = int(agg[0]) if agg else 0
    sets_total = int(agg[1]) if agg else 0

    # PR event query: count rows where weight exceeds the running max for that
    # (exercise_id) up to (but not including) the current row, ordered by date
    # then set.  The first set for each exercise has prev_max IS NULL and always
    # counts as a PR.
    # Reason: uses a window function over the RLS-scoped training rows; no
    # per-row subquery so it remains sargable — Postgres evaluates the window
    # over the index-filtered partition without an additional sequential scan.
    pr_row = db.execute(
        text("""
            WITH windowed AS (
                SELECT
                    weight,
                    max(weight) OVER (
                        PARTITION BY exercise_id
                        ORDER BY date, "set"
                        ROWS BETWEEN UNBOUNDED PRECEDING AND 1 PRECEDING
                    ) AS prev_max
                FROM training
                WHERE user_id = :uid
            )
            SELECT COUNT(*) FROM windowed
            WHERE prev_max IS NULL OR weight > prev_max
        """),
        {"uid": uid},
    ).fetchone()

    prs = int(pr_row[0]) if pr_row else 0

    # Streak: fetch all distinct active dates ordered DESC, count consecutive run
    # ending at today (UTC).
    today_utc = datetime.now(timezone.utc).date()

    active_dates_rows = db.execute(
        text("""
            SELECT DISTINCT DATE(date) AS d
            FROM training
            WHERE user_id = :uid
            ORDER BY d DESC
        """),
        {"uid": uid},
    ).fetchall()

    streak = _compute_streak([r[0] for r in active_dates_rows], today_utc)

    result = schemas.AnalyticsSummary(
        exercises=exercises,
        sets=sets_total,
        prs=prs,
        current_streak=streak,
    )
    cache_set(cache_key, result.model_dump())
    return result


def _compute_streak(sorted_dates_desc: List[date], today: date) -> int:
    """Compute the current consecutive-day training streak ending at today.

    A streak is the number of consecutive calendar days ending on today (or
    yesterday if today has no activity yet) with at least one training set.

    Args:
        sorted_dates_desc: Distinct active dates, newest first.
        today: The reference date (caller supplies so it can be injected in tests).

    Returns:
        Streak length as a non-negative integer.  Returns 0 when no activity.
    """
    if not sorted_dates_desc:
        return 0

    # Convert to Python date objects if needed (psycopg2 may return datetime.date).
    dates = [d if isinstance(d, date) else d.date() for d in sorted_dates_desc]

    # Streak starts only if today or yesterday has activity.
    if dates[0] < today - timedelta(days=1):
        return 0

    streak = 0
    expected = dates[0]  # start from the most-recent active date
    for d in dates:
        if d == expected:
            streak += 1
            expected = expected - timedelta(days=1)
        elif d < expected:
            break  # gap found
    return streak


@router.get(
    "/analytics/exercise-progress",
    response_model=schemas.ExerciseProgress,
    tags=["analytics"],
)
def get_exercise_progress(
    muscle: str,
    exercise: str,
    principal: Principal = Depends(get_principal),
    db: Session = Depends(get_db_for_principal),
) -> schemas.ExerciseProgress:
    """Return per-set weight/reps progress series for an exercise.

    Resolves the exercise by name through the visibility-scoped query (so RLS
    applies — a user cannot probe exercises they cannot see).  Groups the
    user's training rows by set number; within each set, points are ordered
    by date ascending, suitable for ECharts line series.

    Returns ``{ series: [] }`` when the exercise has no training history.

    Args:
        muscle: Muscle group name (used for scoped exercise lookup).
        exercise: Exercise name.
        principal: Resolved identity from ``get_principal``.
        db: SQLAlchemy session.

    Returns:
        ExerciseProgress with one ExerciseSetSeries per distinct set number.
    """
    uid = principal["user_id"]
    cache_key = make_key(uid, "exercise_progress", muscle=muscle, exercise=exercise)
    cached = cache_get(cache_key)
    if cached is not None:
        return schemas.ExerciseProgress(**cached)

    # Resolve exercise_id through the RLS-scoped exercises table so the user
    # cannot enumerate exercises they cannot see.
    ex_row = (
        db.query(models.Exercise.id)
        .join(models.Muscle, models.Exercise.muscle == models.Muscle.id)
        .filter(
            models.Muscle.name == muscle,
            models.Exercise.name == exercise,
        )
        .first()
    )

    if ex_row is None:
        empty = {"series": []}
        cache_set(cache_key, empty)
        return schemas.ExerciseProgress(series=[])

    exercise_id = ex_row[0]

    rows = db.execute(
        text("""
            SELECT
                set,
                DATE(date)  AS day,
                weight,
                reps
            FROM training
            WHERE user_id     = :uid
              AND exercise_id = :eid
            ORDER BY set ASC, date ASC
        """),
        {"uid": uid, "eid": exercise_id},
    ).fetchall()

    # Group by set number.
    series_map: Dict[int, List[schemas.ExercisePoint]] = defaultdict(list)
    for r in rows:
        set_num = r[0]
        day_raw = r[1]
        day = day_raw if isinstance(day_raw, date) else date.fromisoformat(str(day_raw))
        series_map[set_num].append(
            schemas.ExercisePoint(date=day, weight=float(r[2]), reps=float(r[3]))
        )

    series = [
        schemas.ExerciseSetSeries(set=s, points=pts)
        for s, pts in sorted(series_map.items())
    ]

    result = schemas.ExerciseProgress(series=series)

    # Serialize for cache — dates as ISO strings.
    cache_set(
        cache_key,
        {
            "series": [
                {
                    "set": s.set,
                    "points": [
                        {"date": str(p.date), "weight": p.weight, "reps": p.reps}
                        for p in s.points
                    ],
                }
                for s in series
            ]
        },
    )
    return result
