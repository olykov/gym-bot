"""Analytics endpoints — GYM-22 / GYM-26 / GYM-39 / GYM-56 / GYM-58.

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

GYM-56:
- current_streak changed from consecutive days to consecutive Monday-start weeks (UTC).

GYM-58:
- Optional ``tz`` query param (IANA timezone name) added to get_activity, get_summary,
  get_activity.  When provided, day/week boundaries follow the user's local wall-clock
  via ``AT TIME ZONE 'UTC' AT TIME ZONE :tz`` applied only in SELECT/GROUP BY/ORDER BY
  (never in WHERE — keeps queries sargable).  Cache keys include tz to prevent collisions.
"""
import logging
from collections import defaultdict
from datetime import datetime, date, timedelta, timezone
from typing import Dict, List, Optional
from zoneinfo import ZoneInfo, ZoneInfoNotFoundError

from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy import func, text
from sqlalchemy.orm import Session

from app.core.cache import cache_get, cache_set, make_key
from app.core.database import get_db_for_principal
from app.middleware.permissions import Principal, get_principal
from app.models import models
from app.schemas import schemas
from app.services.resolve import resolve_exercise_id as _shared_resolve_exercise_id
from app.services.resolve import resolve_muscle_id as _shared_resolve_muscle_id

logger = logging.getLogger(__name__)

router = APIRouter()

# Maximum date-range span for /analytics/activity (reject absurd ranges).
_MAX_ACTIVITY_DAYS = 400


def _validate_tz(tz: Optional[str]) -> Optional[ZoneInfo]:
    """Validate and return a ZoneInfo for the given IANA timezone name.

    Args:
        tz: IANA timezone name (e.g. "Asia/Tbilisi") or None.

    Returns:
        A ``ZoneInfo`` instance when tz is provided, or ``None`` when tz is None
        (meaning UTC behaviour is preserved).

    Raises:
        HTTPException 422: When tz is not a valid IANA timezone name.
    """
    if tz is None:
        return None
    try:
        return ZoneInfo(tz)
    except (ZoneInfoNotFoundError, KeyError):
        raise HTTPException(
            status_code=422,
            detail=f"Invalid or unknown timezone: {tz!r}. Use an IANA timezone name, e.g. 'Asia/Tbilisi'.",
        )


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
            models.Muscle.name_key == func.app_name_key(muscle),
            models.Exercise.name_key == func.app_name_key(exercise),
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
            models.Muscle.name_key == func.app_name_key(muscle),
            models.Exercise.name_key == func.app_name_key(exercise),
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
            models.Muscle.name_key == func.app_name_key(muscle),
            models.Exercise.name_key == func.app_name_key(exercise),
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
            models.Muscle.name_key == func.app_name_key(muscle),
            models.Exercise.name_key == func.app_name_key(exercise),
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
    limit: int = Query(default=5, ge=1, le=200),
    principal: Principal = Depends(get_principal),
    db: Session = Depends(get_db_for_principal),
) -> List[schemas.TopExercise]:
    """Return the most frequently used exercises for a muscle.

    Maps to ``get_top_exercises_for_muscle(user, muscle, limit)``.

    The ``limit`` parameter is capped at 200 — large enough for the Progress
    picker to request all of a user's exercises for a muscle
    (``?limit=200``), while guarding against unbounded scans.  Existing bot
    callers that pass the default (5) are unaffected.

    Args:
        muscle: Muscle group name.
        limit: Maximum number of exercises to return (1–200, default 5).
        principal: Resolved identity from ``get_principal``.
        db: SQLAlchemy session.

    Returns:
        Exercises ranked by training frequency (descending), then alphabetically.
    """
    uid = principal["user_id"]

    # GYM-106: resolve muscle by name_key so variant names (e.g. "bench-press")
    # work consistently.  Returns empty list when the muscle is not found /
    # not visible — matches previous behaviour for unknown muscle names.
    muscle_id = _shared_resolve_muscle_id(db, uid, muscle)
    if muscle_id is None:
        return []

    rows = (
        db.query(models.Exercise.name, func.count().label("frequency"))
        .join(models.Training, models.Training.exercise_id == models.Exercise.id)
        .filter(
            models.Training.user_id == uid,
            models.Training.muscle_id == muscle_id,
        )
        .group_by(models.Exercise.name)
        .order_by(func.count().desc(), models.Exercise.name.asc())
        .limit(limit)
        .all()
    )

    return [schemas.TopExercise(name=r[0], frequency=r[1]) for r in rows]


@router.get(
    "/analytics/recent-exercises",
    response_model=List[schemas.RecentExercise],
    tags=["analytics"],
)
def get_recent_exercises(
    limit: int = Query(default=8, ge=1, le=50),
    principal: Principal = Depends(get_principal),
    db: Session = Depends(get_db_for_principal),
) -> List[schemas.RecentExercise]:
    """Return the caller's most-recently-trained distinct exercises, newest first.

    Per exercise_id, picks the row with the latest ``date`` (DISTINCT ON) to
    obtain the last set's ``weight`` and ``reps``.  Those per-exercise snapshots
    are then ordered by ``last_date DESC LIMIT :limit`` so the result reads
    newest-trained first.

    Query is sargable: the ``WHERE user_id = :uid`` predicate uses
    ``idx_training_user_exercise`` or ``idx_training_user_date`` (GYM-59);
    ``DISTINCT ON (exercise_id) … ORDER BY exercise_id, date DESC`` lets
    Postgres satisfy the per-exercise latest-row requirement without a
    full-scan subquery.

    Result is cached under ``analytics:{user_id}:recent-exercises:{limit}``
    (90 s TTL).  Training-mutation invalidation clears ``analytics:{uid}:*``
    (GYM-47), so stale entries are evicted on any write.

    Args:
        limit: Maximum exercises to return (1–50, default 8).
        principal: Resolved identity from ``get_principal``.
        db: SQLAlchemy session.

    Returns:
        List of RecentExercise ordered by most recently trained, newest first.
    """
    uid = principal["user_id"]
    cache_key = make_key(uid, "recent-exercises", limit=limit)
    cached = cache_get(cache_key)
    if cached is not None:
        return [schemas.RecentExercise(**item) for item in cached]

    # DISTINCT ON picks the latest row per exercise_id; the outer query
    # re-orders by date desc and limits.  Both predicates (user_id) keep
    # Postgres using the composite index rather than a seq-scan.
    rows = db.execute(
        text("""
            SELECT muscle_name, exercise_name, last_weight, last_reps, last_date
            FROM (
                SELECT DISTINCT ON (t.exercise_id)
                    m.name  AS muscle_name,
                    e.name  AS exercise_name,
                    t.weight AS last_weight,
                    t.reps   AS last_reps,
                    t.date::date AS last_date
                FROM training t
                JOIN exercises e ON e.id = t.exercise_id
                JOIN muscles   m ON m.id = t.muscle_id
                WHERE t.user_id = :uid
                ORDER BY t.exercise_id, t.date DESC
            ) latest
            ORDER BY last_date DESC
            LIMIT :lim
        """),
        {"uid": uid, "lim": limit},
    ).fetchall()

    result = [
        schemas.RecentExercise(
            muscle_name=r[0],
            exercise_name=r[1],
            last_weight=float(r[2]),
            last_reps=float(r[3]),
            last_date=r[4] if isinstance(r[4], date) else date.fromisoformat(str(r[4])),
        )
        for r in rows
    ]
    cache_set(
        cache_key,
        [
            {
                "muscle_name": item.muscle_name,
                "exercise_name": item.exercise_name,
                "last_weight": item.last_weight,
                "last_reps": item.last_reps,
                "last_date": str(item.last_date),
            }
            for item in result
        ],
    )
    return result


@router.get(
    "/analytics/top-muscles",
    response_model=List[schemas.TopMuscle],
    tags=["analytics"],
)
def get_top_muscles(
    principal: Principal = Depends(get_principal),
    db: Session = Depends(get_db_for_principal),
) -> List[schemas.TopMuscle]:
    """Return muscles the caller has trained, ranked by training frequency.

    Feeds the Progress muscle picker so the most-trained muscles surface first.
    Maps to the ``GET /analytics/top-muscles`` contract (GYM-60).

    Query is sargable: the WHERE on ``user_id`` uses
    ``idx_training_user_muscle (user_id, muscle_id)`` added in GYM-59's
    migration 0003, so Postgres performs an index scan, not a sequential scan.

    Result is cached under ``analytics:{user_id}:top-muscles:`` (90 s TTL).
    Cache invalidation on training writes is already wired (GYM-47).

    Args:
        principal: Resolved identity from ``get_principal``.
        db: SQLAlchemy session.

    Returns:
        Muscles ranked by frequency descending, then alphabetically by name.
    """
    uid = principal["user_id"]
    cache_key = make_key(uid, "top-muscles")
    cached = cache_get(cache_key)
    if cached is not None:
        return [schemas.TopMuscle(**item) for item in cached]

    rows = db.execute(
        text("""
            SELECT m.name, COUNT(*) AS frequency
            FROM training t
            JOIN muscles m ON m.id = t.muscle_id
            WHERE t.user_id = :uid
            GROUP BY m.name
            ORDER BY frequency DESC, m.name ASC
        """),
        {"uid": uid},
    ).fetchall()

    result = [schemas.TopMuscle(name=r[0], frequency=r[1]) for r in rows]
    cache_set(cache_key, [{"name": item.name, "frequency": item.frequency} for item in result])
    return result


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
    tz: Optional[str] = Query(default=None),
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
    function.  The AT TIME ZONE transform appears only in GROUP BY / SELECT / ORDER BY,
    never in WHERE.

    GYM-58: When ``tz`` is supplied, day boundaries follow the user's local wall-clock
    via ``date AT TIME ZONE 'UTC' AT TIME ZONE :tz`` in SELECT/GROUP BY/ORDER BY.
    The WHERE predicate keeps the raw timestamp column for index sargability.

    Args:
        from_date: Inclusive start date (``from`` query parameter).
        to_date: Inclusive end date (``to`` query parameter).
        tz: Optional IANA timezone name (e.g. "Asia/Tbilisi"). Default None = UTC.
        principal: Resolved identity from ``get_principal``.
        db: SQLAlchemy session.

    Returns:
        List of ActivityDay objects, one per active day, ordered by date ascending.

    Raises:
        HTTPException 400: If ``from`` > ``to`` or range exceeds 400 days.
        HTTPException 422: If ``tz`` is not a valid IANA timezone name.
    """
    _validate_tz(tz)  # raises 422 on invalid tz

    if from_date > to_date:
        raise HTTPException(status_code=400, detail="'from' must be <= 'to'")
    span = (to_date - from_date).days + 1
    if span > _MAX_ACTIVITY_DAYS:
        raise HTTPException(
            status_code=400,
            detail=f"Date range too large ({span} days). Maximum is {_MAX_ACTIVITY_DAYS} days.",
        )

    uid = principal["user_id"]
    cache_key = make_key(uid, "activity", frm=str(from_date), to=str(to_date), tz=tz or "UTC")
    cached = cache_get(cache_key)
    if cached is not None:
        return [schemas.ActivityDay(**item) for item in cached]

    # Half-open range: [from_date 00:00:00, to_date+1day 00:00:00)
    # Reason: idx_training_user_date is on (user_id, date); plain range predicates on
    # `date` allow Postgres to use the index without a function scan.
    # AT TIME ZONE appears only in GROUP BY / SELECT / ORDER BY, never in WHERE.
    to_exclusive = datetime(to_date.year, to_date.month, to_date.day) + timedelta(days=1)
    from_dt = datetime(from_date.year, from_date.month, from_date.day)

    if tz is None:
        # UTC path — unchanged behaviour.
        query_params: dict = {"uid": uid, "from_dt": from_dt, "to_exclusive": to_exclusive}
        day_expr = "DATE_TRUNC('day', date)"
        sql = f"""
            SELECT
                {day_expr} AS day,
                COUNT(*)    AS sets_count
            FROM training
            WHERE user_id = :uid
              AND date >= :from_dt
              AND date  < :to_exclusive
            GROUP BY {day_expr}
            ORDER BY {day_expr}
        """
    else:
        # Timezone-aware path: convert UTC timestamp to the user's local wall-clock
        # before truncating.  The AT TIME ZONE transform stays out of WHERE.
        # Reason: 'date AT TIME ZONE UTC AT TIME ZONE tz' first interprets the naive
        # TIMESTAMP as UTC, then converts to tz, yielding the local-wall-clock value.
        query_params = {
            "uid": uid, "from_dt": from_dt, "to_exclusive": to_exclusive, "tz": tz
        }
        day_expr = "DATE_TRUNC('day', date AT TIME ZONE 'UTC' AT TIME ZONE :tz)"
        sql = f"""
            SELECT
                {day_expr} AS day,
                COUNT(*)    AS sets_count
            FROM training
            WHERE user_id = :uid
              AND date >= :from_dt
              AND date  < :to_exclusive
            GROUP BY {day_expr}
            ORDER BY {day_expr}
        """

    rows = db.execute(text(sql), query_params).fetchall()

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
    tz: Optional[str] = Query(default=None),
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
        current_streak: consecutive Monday-start weeks ending at the current
            week in the requested timezone (default UTC), each containing >=1
            training session (GYM-56, GYM-58).
            Reason: training timestamps are stored as naive UTC TIMESTAMP.
            When ``tz`` is provided, ``date_trunc('week', date AT TIME ZONE 'UTC'
            AT TIME ZONE :tz)`` groups rows by the user's local wall-clock week.
            The streak anchor (current week / today) is also derived in that
            timezone.  The current week is "forgiving": if no session has happened
            yet this week (week in progress), the chain is not broken.

    Args:
        tz: Optional IANA timezone name (e.g. "Asia/Tbilisi"). Default None = UTC.
        principal: Resolved identity from ``get_principal``.
        db: SQLAlchemy session.

    Returns:
        AnalyticsSummary with exercises, sets, prs, current_streak.

    Raises:
        HTTPException 422: If ``tz`` is not a valid IANA timezone name.
    """
    _validate_tz(tz)  # raises 422 on invalid tz

    uid = principal["user_id"]
    cache_key = make_key(uid, "summary", tz=tz or "UTC")
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

    # Streak (GYM-56 / GYM-58): bucket training rows into Monday-start ISO weeks
    # and count consecutive weeks ending at the current week, each with >=1 session.
    # When tz is provided, the AT TIME ZONE transform converts the naive UTC timestamp
    # to the user's local wall-clock before truncating — the WHERE clause stays a plain
    # user_id filter so Postgres uses idx_training_user_date; the transform appears only
    # in GROUP BY / SELECT, keeping the predicate sargable.
    if tz is None:
        # UTC path — unchanged behaviour.
        today_ref = datetime.now(timezone.utc).date()
        week_sql = """
            SELECT DATE_TRUNC('week', date)::date AS week_start
            FROM training
            WHERE user_id = :uid
            GROUP BY DATE_TRUNC('week', date)
            ORDER BY week_start DESC
        """
        week_params: dict = {"uid": uid}
    else:
        # Timezone-aware path: current date in the user's timezone for the streak anchor.
        tz_info = ZoneInfo(tz)
        today_ref = datetime.now(tz_info).date()
        week_sql = """
            SELECT DATE_TRUNC('week', date AT TIME ZONE 'UTC' AT TIME ZONE :tz)::date AS week_start
            FROM training
            WHERE user_id = :uid
            GROUP BY DATE_TRUNC('week', date AT TIME ZONE 'UTC' AT TIME ZONE :tz)
            ORDER BY week_start DESC
        """
        week_params = {"uid": uid, "tz": tz}

    active_weeks_rows = db.execute(text(week_sql), week_params).fetchall()
    streak = _compute_streak_weeks([r[0] for r in active_weeks_rows], today_ref)

    result = schemas.AnalyticsSummary(
        exercises=exercises,
        sets=sets_total,
        prs=prs,
        current_streak=streak,
    )
    cache_set(cache_key, result.model_dump())
    return result


def _monday_of_week(d: date) -> date:
    """Return the Monday of the ISO week containing ``d``.

    Reason: Python's ``date.weekday()`` returns 0 for Monday, so subtracting
    ``weekday()`` days always lands on the Monday of the same week.

    Args:
        d: Any calendar date.

    Returns:
        The Monday (start) of the week containing ``d``.
    """
    return d - timedelta(days=d.weekday())


def _compute_streak_weeks(sorted_week_starts_desc: List[date], today: date) -> int:
    """Compute the current consecutive-week training streak (GYM-56).

    Definition (Monday-start ISO weeks, UTC):
    - Each week in the list has >=1 training session.
    - Find the most recent week with a session.  If it is the current week
      OR the immediately preceding week, begin counting consecutive weeks
      backwards from there.  Otherwise return 0.
    - Reason: the current week is "forgiving" — if no session has happened
      yet this week (week still in progress), the chain is not broken.
      The chain breaks only at a fully-elapsed week with zero sessions.

    Sargability note: the SQL query that produces ``sorted_week_starts_desc``
    applies date_trunc only in GROUP BY / SELECT; the WHERE is a plain
    ``user_id = :uid`` filter so Postgres uses idx_training_user_date.

    Args:
        sorted_week_starts_desc: Distinct week-start (Monday) dates that contain
            >=1 session, newest first.  Produced by the DATE_TRUNC('week', ...) query.
        today: Reference date (caller-supplied so tests can inject a known date).

    Returns:
        Streak length as a non-negative integer.  Returns 0 when no activity.
    """
    if not sorted_week_starts_desc:
        return 0

    # Normalise: psycopg2 may return datetime.date already; coerce just in case.
    weeks = [
        w if isinstance(w, date) else (w.date() if hasattr(w, "date") else w)
        for w in sorted_week_starts_desc
    ]

    current_week_start = _monday_of_week(today)
    prev_week_start = current_week_start - timedelta(weeks=1)

    most_recent = weeks[0]

    # The chain is live only if the most-recent active week is the current week
    # or the immediately preceding week (current week still in progress).
    if most_recent < prev_week_start:
        return 0

    # Walk backwards, counting consecutive weeks from most_recent.
    streak = 0
    expected = most_recent
    for w in weeks:
        if w == expected:
            streak += 1
            expected = expected - timedelta(weeks=1)
        elif w < expected:
            break  # gap — non-consecutive week
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

    # GYM-106: resolve exercise_id via shared resolver (own-first, name_key-based).
    exercise_id = _shared_resolve_exercise_id(db, uid, muscle, exercise)

    if exercise_id is None:
        empty = {"series": []}
        cache_set(cache_key, empty)
        return schemas.ExerciseProgress(series=[])

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


# ---------------------------------------------------------------------------
# GYM-71: /analytics/log-context — combined set-logger context
# ---------------------------------------------------------------------------


def _resolve_exercise_id(
    db: Session,
    muscle: str,
    exercise: str,
    uid: Optional[int] = None,
) -> Optional[int]:
    """Resolve exercise_id from muscle + exercise name via the RLS-scoped session.

    GYM-106: delegates to the shared ``resolve_exercise_id`` helper in
    ``app.services.resolve``.  That helper matches by ``name_key`` (the
    ``app_name_key`` SQL function) and applies deterministic own-first-then-global
    priority so that variant names ("bench-press", "BENCH PRESS") all resolve to
    the same row.

    The ``uid`` parameter is forwarded when supplied; when omitted (legacy call
    sites) the resolver still works correctly because RLS already scopes the
    session — the own-first ordering simply degrades to a less-discriminating
    ``LIMIT 1`` when uid is unknown, which is safe in the RLS context.

    Args:
        db: SQLAlchemy session (already GUC-wired for the calling user).
        muscle: Muscle group name (any case/separator variant).
        exercise: Exercise name (any case/separator variant).
        uid: Caller's user id (optional; used for own-first determinism).

    Returns:
        The integer exercise id, or ``None`` when not found / not visible.
    """
    return _shared_resolve_exercise_id(db, uid or 0, muscle, exercise)


def _fetch_completed_sets(
    db: Session,
    uid: int,
    exercise_id: int,
    target_date: date,
) -> List[int]:
    """Return distinct set numbers logged on ``target_date`` for a user/exercise.

    Uses a half-open range on the raw TIMESTAMP column so the predicate hits
    ``idx_training_user_exercise (user_id, exercise_id)``.

    Args:
        db: SQLAlchemy session.
        uid: User id (defence-in-depth; RLS already scopes the session).
        exercise_id: Exercise id (already resolved via RLS-scoped lookup).
        target_date: Calendar date to query.

    Returns:
        Sorted list of distinct set integers.
    """
    rows = db.execute(
        text("""
            SELECT DISTINCT "set"
            FROM training
            WHERE user_id     = :uid
              AND exercise_id = :eid
              AND date >= :day_start
              AND date  < :day_end
            ORDER BY "set"
        """),
        {
            "uid": uid,
            "eid": exercise_id,
            "day_start": datetime.combine(target_date, datetime.min.time()),
            "day_end": datetime.combine(target_date, datetime.max.time()),
        },
    ).fetchall()
    return [r[0] for r in rows]


def _fetch_last_session_sets(
    db: Session,
    uid: int,
    exercise_id: int,
    target_date: date,
) -> List[schemas.LogSet]:
    """Return sets from the most recent session strictly before ``target_date``.

    Uses a CTE to find ``max(date::date)`` < target_date for (user, exercise),
    then selects all rows on that day ordered by set.  Sargable: the WHERE
    predicates on ``user_id`` and ``exercise_id`` use
    ``idx_training_user_exercise (user_id, exercise_id)``; the date upper-bound
    keeps an index-range scan.  ``date::date`` appears only in the subquery
    GROUP BY, never in a top-level WHERE, so the outer filter stays a plain
    range on the timestamp column.

    Args:
        db: SQLAlchemy session.
        uid: User id.
        exercise_id: Exercise id.
        target_date: The session date; only rows strictly before this date are
            considered.

    Returns:
        Ordered list of LogSet (set, weight, reps), or empty list when no
        prior session exists.
    """
    rows = db.execute(
        text("""
            WITH prior_day AS (
                SELECT MAX(date::date) AS last_date
                FROM training
                WHERE user_id     = :uid
                  AND exercise_id = :eid
                  AND date < :day_start
            )
            SELECT t."set", t.weight, t.reps
            FROM training t
            JOIN prior_day pd ON t.date::date = pd.last_date
            WHERE t.user_id     = :uid
              AND t.exercise_id = :eid
            ORDER BY t."set"
        """),
        {
            "uid": uid,
            "eid": exercise_id,
            "day_start": datetime.combine(target_date, datetime.min.time()),
        },
    ).fetchall()
    return [schemas.LogSet(set=r[0], weight=float(r[1]), reps=float(r[2])) for r in rows]


def _fetch_personal_record(
    db: Session,
    uid: int,
    exercise_id: int,
) -> Optional[schemas.PersonalRecord]:
    """Return the personal record (max weight) for a user/exercise.

    Mirrors ``get_personal_record`` but takes a pre-resolved exercise_id to
    avoid a redundant name-lookup join.

    Args:
        db: SQLAlchemy session.
        uid: User id.
        exercise_id: Exercise id.

    Returns:
        PersonalRecord or None when no training rows exist.
    """
    row = db.execute(
        text("""
            SELECT weight, reps, date
            FROM training
            WHERE user_id     = :uid
              AND exercise_id = :eid
            ORDER BY weight DESC, reps DESC, date DESC
            LIMIT 1
        """),
        {"uid": uid, "eid": exercise_id},
    ).fetchone()
    if row is None:
        return None
    return schemas.PersonalRecord(weight=float(row[0]), reps=float(row[1]), date=row[2])


@router.get(
    "/analytics/log-context",
    response_model=schemas.LogContext,
    tags=["analytics"],
)
def get_log_context(
    muscle: str,
    exercise: str,
    date: date,
    principal: Principal = Depends(get_principal),
    db: Session = Depends(get_db_for_principal),
) -> schemas.LogContext:
    """Return the combined set-logger context for a user/exercise/date.

    One cached read replaces three separate round-trips (completed-sets +
    last-session + personal-record).  Resolves muscle and exercise by name
    through the RLS-scoped session so the user cannot probe exercises that
    are invisible to them.  Sargable queries use
    ``idx_training_user_exercise (user_id, exercise_id)`` (GYM-59).

    Args:
        muscle: Muscle group name.
        exercise: Exercise name.
        date: Calendar date for the current log session.
        principal: Resolved identity from ``get_principal``.
        db: SQLAlchemy session (GUC-wired for the calling user).

    Returns:
        LogContext with completed_sets, last_session_sets, and pr.
    """
    uid = principal["user_id"]
    cache_key = make_key(uid, "log-context", muscle=muscle, exercise=exercise, date=str(date))
    cached = cache_get(cache_key)
    if cached is not None:
        pr_raw = cached.get("pr")
        return schemas.LogContext(
            completed_sets=cached["completed_sets"],
            last_session_sets=[schemas.LogSet(**s) for s in cached["last_session_sets"]],
            pr=schemas.PersonalRecord(**pr_raw) if pr_raw else None,
        )

    exercise_id = _resolve_exercise_id(db, muscle, exercise, uid)
    if exercise_id is None:
        # Reason: do NOT cache a resolution miss — caching an empty result here
        # would poison the key for the full TTL and mask future history once the
        # exercise becomes visible (e.g. after unhide or a race with creation).
        # A miss is cheap: it's a single indexed key lookup; letting it fall
        # through to the DB every time is correct and safe. (GYM-99)
        return schemas.LogContext(completed_sets=[], last_session_sets=[], pr=None)

    completed = _fetch_completed_sets(db, uid, exercise_id, date)
    last_sets = _fetch_last_session_sets(db, uid, exercise_id, date)
    pr = _fetch_personal_record(db, uid, exercise_id)

    result = schemas.LogContext(completed_sets=completed, last_session_sets=last_sets, pr=pr)

    pr_dict = {"weight": pr.weight, "reps": pr.reps, "date": str(pr.date)} if pr else None
    cache_set(
        cache_key,
        {
            "completed_sets": completed,
            "last_session_sets": [{"set": s.set, "weight": s.weight, "reps": s.reps}
                                  for s in last_sets],
            "pr": pr_dict,
        },
    )
    return result


# ---------------------------------------------------------------------------
# GYM-134: /analytics/exercise-trend — session volume delta + e1RM trend
# ---------------------------------------------------------------------------


def _fetch_last_two_session_volumes(
    db: Session,
    uid: int,
    exercise_id: int,
) -> List[schemas.SessionVolume]:
    """Return the two most recent sessions (calendar days) with total volume.

    Volume = SUM(weight * reps) over all sets logged on the day.  Sargable:
    the WHERE predicates on ``user_id``/``exercise_id`` use
    ``idx_training_user_exercise (user_id, exercise_id)``; ``date::date``
    appears only in GROUP BY / SELECT / ORDER BY, never in WHERE.

    Args:
        db: SQLAlchemy session.
        uid: User id (defence-in-depth; RLS already scopes the session).
        exercise_id: Exercise id (already resolved via RLS-scoped lookup).

    Returns:
        Up to two SessionVolume entries, most recent first.  Empty list when
        the exercise has no training history.
    """
    rows = db.execute(
        text("""
            SELECT date::date AS day, SUM(weight * reps) AS volume
            FROM training
            WHERE user_id     = :uid
              AND exercise_id = :eid
            GROUP BY date::date
            ORDER BY day DESC
            LIMIT 2
        """),
        {"uid": uid, "eid": exercise_id},
    ).fetchall()
    return [
        schemas.SessionVolume(
            date=r[0] if isinstance(r[0], date) else date.fromisoformat(str(r[0])),
            volume=float(r[1]),
        )
        for r in rows
    ]


def _fetch_e1rm_trend(
    db: Session,
    uid: int,
    exercise_id: int,
    window_start: datetime,
) -> List[schemas.E1rmPoint]:
    """Return per-session max Epley e1RM points within the trailing window.

    e1RM (Epley) = weight * (1 + reps/30); per session (calendar day) the
    maximum across the day's sets is taken — done directly in SQL via
    ``MAX(weight * (1 + reps / 30.0))``.  Sargable: WHERE uses plain
    predicates on ``user_id``/``exercise_id`` plus a raw timestamp range
    (``date >= :window_start``) so ``idx_training_user_exercise`` applies;
    ``date::date`` appears only in GROUP BY / SELECT / ORDER BY.

    Args:
        db: SQLAlchemy session.
        uid: User id.
        exercise_id: Exercise id.
        window_start: Inclusive lower bound of the trailing window (UTC).

    Returns:
        E1rmPoint entries ordered by date ascending; empty when no sessions
        fall within the window.
    """
    rows = db.execute(
        text("""
            SELECT date::date AS day, MAX(weight * (1 + reps / 30.0)) AS e1rm
            FROM training
            WHERE user_id     = :uid
              AND exercise_id = :eid
              AND date >= :window_start
            GROUP BY date::date
            ORDER BY day ASC
        """),
        {"uid": uid, "eid": exercise_id, "window_start": window_start},
    ).fetchall()
    return [
        schemas.E1rmPoint(
            date=r[0] if isinstance(r[0], date) else date.fromisoformat(str(r[0])),
            e1rm=float(r[1]),
        )
        for r in rows
    ]


def _trend_to_cache(trend: schemas.ExerciseTrend) -> dict:
    """Serialize an ExerciseTrend for the JSON cache (dates as ISO strings).

    Args:
        trend: Computed trend payload.

    Returns:
        JSON-serialisable dict mirroring the contract shape.
    """
    def _session(s: Optional[schemas.SessionVolume]) -> Optional[dict]:
        return {"date": str(s.date), "volume": s.volume} if s else None

    return {
        "last_session": _session(trend.last_session),
        "prev_session": _session(trend.prev_session),
        "e1rm_trend": [{"date": str(p.date), "e1rm": p.e1rm} for p in trend.e1rm_trend],
    }


def _trend_from_cache(cached: dict) -> schemas.ExerciseTrend:
    """Rebuild an ExerciseTrend from its cached JSON dict.

    Args:
        cached: Dict previously produced by ``_trend_to_cache``.

    Returns:
        ExerciseTrend instance.
    """
    last_raw = cached.get("last_session")
    prev_raw = cached.get("prev_session")
    return schemas.ExerciseTrend(
        last_session=schemas.SessionVolume(**last_raw) if last_raw else None,
        prev_session=schemas.SessionVolume(**prev_raw) if prev_raw else None,
        e1rm_trend=[schemas.E1rmPoint(**p) for p in cached.get("e1rm_trend", [])],
    )


@router.get(
    "/analytics/exercise-trend",
    response_model=schemas.ExerciseTrend,
    tags=["analytics"],
)
def get_exercise_trend(
    muscle: str,
    exercise: str,
    weeks: int = Query(default=8, ge=1, le=52),
    principal: Principal = Depends(get_principal),
    db: Session = Depends(get_db_for_principal),
) -> schemas.ExerciseTrend:
    """Return session volume delta inputs + e1RM trend for an exercise (GYM-134).

    One small read powering the SetLogger sparkline and the session-vs-session
    volume delta: the two most recent sessions' volumes (Σ weight×reps per
    calendar day) and a per-session max Epley e1RM series over the trailing
    ``weeks`` window.  Resolves muscle/exercise by name through the RLS-scoped
    session (GYM-71 pattern) so a user cannot probe invisible exercises.

    Cached under ``analytics:{uid}:exercise-trend:...`` (90 s TTL); training
    mutations purge ``analytics:{uid}:*`` (GYM-47), which covers this key
    family automatically.

    Args:
        muscle: Muscle group name.
        exercise: Exercise name.
        weeks: Trailing window for the e1RM trend in weeks (1–52, default 8).
        principal: Resolved identity from ``get_principal``.
        db: SQLAlchemy session (GUC-wired for the calling user).

    Returns:
        ExerciseTrend with last_session, prev_session, and e1rm_trend.
    """
    uid = principal["user_id"]
    cache_key = make_key(uid, "exercise-trend", muscle=muscle, exercise=exercise, weeks=weeks)
    cached = cache_get(cache_key)
    if cached is not None:
        return _trend_from_cache(cached)

    exercise_id = _resolve_exercise_id(db, muscle, exercise, uid)
    if exercise_id is None:
        # Reason: do NOT cache a resolution miss — caching would poison the key
        # for the full TTL and mask history once the exercise becomes visible
        # (GYM-99 discipline, mirrors log-context).
        return schemas.ExerciseTrend(last_session=None, prev_session=None, e1rm_trend=[])

    sessions = _fetch_last_two_session_volumes(db, uid, exercise_id)
    window_start = datetime.utcnow() - timedelta(weeks=weeks)
    trend = _fetch_e1rm_trend(db, uid, exercise_id, window_start)

    result = schemas.ExerciseTrend(
        last_session=sessions[0] if sessions else None,
        prev_session=sessions[1] if len(sessions) > 1 else None,
        e1rm_trend=trend,
    )
    cache_set(cache_key, _trend_to_cache(result))
    return result


# ---------------------------------------------------------------------------
# GYM-136: /analytics/week-compare — this-week vs last-week totals
# ---------------------------------------------------------------------------


def _week_compare_bounds(tz: Optional[str]) -> tuple[date, date, datetime, datetime]:
    """Compute the Monday anchors and the UTC range for the 2-week window.

    Weeks are Monday-start calendar weeks in the user's timezone (UTC when
    ``tz`` is None).  The returned range covers [last Monday 00:00 local,
    next Monday 00:00 local) expressed as naive-UTC datetimes — the training
    ``date`` column stores naive UTC, so comparing against these bounds keeps
    the WHERE clause sargable on ``idx_training_user_date``.

    Args:
        tz: Validated IANA timezone name, or None for UTC behaviour.

    Returns:
        Tuple of (last_monday, this_monday, range_start_utc, range_end_utc).
    """
    if tz is None:
        today_ref = datetime.now(timezone.utc).date()
        this_monday = _monday_of_week(today_ref)
        last_monday = this_monday - timedelta(weeks=1)
        next_monday = this_monday + timedelta(weeks=1)
        range_start = datetime(last_monday.year, last_monday.month, last_monday.day)
        range_end = datetime(next_monday.year, next_monday.month, next_monday.day)
        return last_monday, this_monday, range_start, range_end

    tz_info = ZoneInfo(tz)
    today_ref = datetime.now(tz_info).date()
    this_monday = _monday_of_week(today_ref)
    last_monday = this_monday - timedelta(weeks=1)
    next_monday = this_monday + timedelta(weeks=1)

    def _local_midnight_as_utc(d: date) -> datetime:
        # Local wall-clock midnight converted to the naive-UTC instant stored
        # in the training table.
        local = datetime(d.year, d.month, d.day, tzinfo=tz_info)
        return local.astimezone(timezone.utc).replace(tzinfo=None)

    return (
        last_monday,
        this_monday,
        _local_midnight_as_utc(last_monday),
        _local_midnight_as_utc(next_monday),
    )


def _fetch_week_buckets(
    db: Session,
    uid: int,
    range_start: datetime,
    range_end: datetime,
    tz: Optional[str],
) -> Dict[date, schemas.WeekStats]:
    """Aggregate sets/volume per Monday-start week within the bounded range.

    One grouped query over the 2-week range.  Sargable: the WHERE clause is a
    plain ``user_id`` filter plus a raw timestamp range, so Postgres uses
    ``idx_training_user_date``; the AT TIME ZONE transform appears only in
    SELECT / GROUP BY (GYM-58 discipline, mirrors summary/streak).

    Args:
        db: SQLAlchemy session.
        uid: User id (defence-in-depth; RLS already scopes the session).
        range_start: Inclusive naive-UTC lower bound (last Monday local 00:00).
        range_end: Exclusive naive-UTC upper bound (next Monday local 00:00).
        tz: Validated IANA timezone name, or None for UTC grouping.

    Returns:
        Mapping of week-start Monday date to WeekStats.
    """
    if tz is None:
        week_expr = "DATE_TRUNC('week', date)"
        params: dict = {"uid": uid, "range_start": range_start, "range_end": range_end}
    else:
        week_expr = "DATE_TRUNC('week', date AT TIME ZONE 'UTC' AT TIME ZONE :tz)"
        params = {
            "uid": uid, "range_start": range_start, "range_end": range_end, "tz": tz
        }

    rows = db.execute(
        text(f"""
            SELECT
                {week_expr}::date    AS week_start,
                COUNT(*)             AS sets,
                SUM(weight * reps)   AS volume
            FROM training
            WHERE user_id = :uid
              AND date >= :range_start
              AND date  < :range_end
            GROUP BY {week_expr}
        """),
        params,
    ).fetchall()

    buckets: Dict[date, schemas.WeekStats] = {}
    for r in rows:
        week_start = r[0] if isinstance(r[0], date) else date.fromisoformat(str(r[0]))
        buckets[week_start] = schemas.WeekStats(
            sets=int(r[1]), volume=float(r[2] or 0.0)
        )
    return buckets


@router.get(
    "/analytics/week-compare",
    response_model=schemas.WeekCompare,
    tags=["analytics"],
)
def get_week_compare(
    tz: Optional[str] = Query(default=None),
    principal: Principal = Depends(get_principal),
    db: Session = Depends(get_db_for_principal),
) -> schemas.WeekCompare:
    """Return this-week vs last-week sets/volume totals (GYM-136).

    Weeks are Monday-start calendar weeks computed in the requested timezone
    (default UTC, mirroring the summary endpoint's tz convention): ``this_week``
    is the week containing today, ``last_week`` the week immediately before.
    A week with no training carries zeros.

    Cached under ``analytics:{uid}:week-compare:{tz}`` (90 s TTL); training
    mutations purge ``analytics:{uid}:*`` (GYM-47), which covers this key.

    Args:
        tz: Optional IANA timezone name (e.g. "Asia/Tbilisi"). Default None = UTC.
        principal: Resolved identity from ``get_principal``.
        db: SQLAlchemy session.

    Returns:
        WeekCompare with this_week and last_week totals.

    Raises:
        HTTPException 422: If ``tz`` is not a valid IANA timezone name.
    """
    _validate_tz(tz)  # raises 422 on invalid tz

    uid = principal["user_id"]
    cache_key = make_key(uid, "week-compare", tz=tz or "UTC")
    cached = cache_get(cache_key)
    if cached is not None:
        return schemas.WeekCompare(**cached)

    last_monday, this_monday, range_start, range_end = _week_compare_bounds(tz)
    buckets = _fetch_week_buckets(db, uid, range_start, range_end, tz)

    empty = schemas.WeekStats(sets=0, volume=0.0)
    result = schemas.WeekCompare(
        this_week=buckets.get(this_monday, empty),
        last_week=buckets.get(last_monday, empty),
    )
    cache_set(cache_key, result.model_dump())
    return result
