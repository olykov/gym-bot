"""Training history endpoints — GYM-47 / GYM-58 / GYM-51 / GYM-155 / GYM-153.

Implements:
  GET  /training/days              — day-grouped summary, reverse-chronological
  GET  /training/day/{date}        — full exercise/set detail for one day
  DELETE /training/{id}            — delete caller's own set
  PATCH /training/{id}/move        — move set to another date and/or exercise (GYM-51)

All routes use ``get_principal`` + ``get_db_for_principal`` (RLS-scoped to
the authenticated caller, fail-closed).

Cache invalidation: every mutation calls ``cache.invalidate_user(uid)`` to
purge stale analytics:{user_id}:* keys so Dashboard/Progress numbers stay
current after edits.  Graceful if Redis is down.

GYM-58: Optional ``tz`` query param added to ``list_training_days``.  When
provided, the ``t.date::date`` grouping is replaced by
``(t.date AT TIME ZONE 'UTC' AT TIME ZONE :tz)::date`` in SELECT/GROUP BY/
ORDER BY only — the WHERE filter keeps the raw column for sargability.

GYM-51: PATCH move stores date at noon UTC so the set lands on the intended
calendar day in every ±12h timezone.

GYM-155: PR flags use temporal window-function semantics ("was a PR when
logged") instead of the old all-time-max-weight comparison.  A set is_pr when,
comparing to all EARLIER sets for the same exercise (ordered by date, set):
  1. It is the user's first ever set of that exercise (no prior rows), OR
  2. Its weight is strictly greater than every prior weight, OR
  3. The exact weight was lifted before AND its reps strictly exceed the best
     prior reps at that weight.
has_pr (day level) = OR of is_pr over the day's sets.
This fixes constant-weight / bodyweight exercises that previously flagged every
set as PR because weight == all-time max_weight for every set.

GYM-153: pr_kind is derived alongside is_pr in GET /training/day/{date}.
  'weight' — first-ever set or strictly greater weight (weight branch first,
             so first-ever set always yields 'weight', not 'reps').
  'reps'   — same weight lifted before, strictly more reps.
  NULL     — not a PR.
Invariant: pr_kind IS NOT NULL exactly when is_pr is true.

GYM-156: Optional ``tz`` query param added to ``get_training_day`` (mirrors
``list_training_days``).  When provided, the UTC day window [dt_from, dt_to)
is computed from the LOCAL midnight boundaries of ``day_date`` in ``tz`` using
``zoneinfo.ZoneInfo``.  Without ``tz`` the existing UTC behaviour is preserved
(back-compat).  Same ``_validate_tz`` helper and same Query metadata as
``list_training_days``.
"""
import logging
from collections import defaultdict
from datetime import date, datetime, time, timedelta
from typing import Dict, List, Optional
from zoneinfo import ZoneInfo, ZoneInfoNotFoundError

from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy import text
from sqlalchemy.orm import Session

from app.services.resolve import resolve_exercise_id

from app.core.cache import invalidate_user
from app.core.database import get_db_for_principal
from app.middleware.permissions import Principal, get_principal
from app.models import models
from app.schemas import schemas

logger = logging.getLogger(__name__)

router = APIRouter()

_DEFAULT_WINDOW_DAYS = 180


def _validate_tz(tz: Optional[str]) -> None:
    """Raise HTTP 422 when tz is not a valid IANA timezone name.

    Args:
        tz: IANA timezone name or None (None is always valid — UTC behaviour).

    Raises:
        HTTPException 422: When tz is supplied but not a recognised IANA zone.
    """
    if tz is None:
        return
    try:
        ZoneInfo(tz)
    except (ZoneInfoNotFoundError, KeyError):
        raise HTTPException(
            status_code=422,
            detail=f"Invalid or unknown timezone: {tz!r}. Use an IANA timezone name, e.g. 'Asia/Tbilisi'.",
        )


@router.get(
    "/training/days",
    response_model=List[schemas.TrainingDay],
    tags=["training"],
)
def list_training_days(
    from_date: Optional[date] = Query(None, alias="from"),
    to_date: Optional[date] = Query(None, alias="to"),
    tz: Optional[str] = Query(default=None),
    principal: Principal = Depends(get_principal),
    db: Session = Depends(get_db_for_principal),
) -> List[schemas.TrainingDay]:
    """List the caller's training days, grouped and reverse-chronological.

    Returns one entry per calendar day the caller trained within the optional
    ``from``/``to`` window (inclusive).  When omitted the window defaults to
    the last 180 days.  The WHERE clause is sargable — it filters on the raw
    ``date`` column which is covered by ``idx_training_user_date``.

    GYM-58: When ``tz`` is provided, day boundaries follow the user's local
    wall-clock.  The day expression ``t.date::date`` is replaced by
    ``(t.date AT TIME ZONE 'UTC' AT TIME ZONE :tz)::date`` in SELECT/GROUP BY/
    ORDER BY only.  The WHERE keeps the raw timestamp column.

    GYM-155: has_pr uses temporal PR semantics — a day has_pr=True when it
    contains at least one set that was a personal record at the moment it was
    logged (weight PR or reps-at-weight PR vs all prior sets of the exercise,
    ordered by date then set number).  Constant-weight exercises no longer mark
    every day as has_pr.

    Args:
        from_date: Inclusive start date; defaults to today minus 180 days.
        to_date: Inclusive end date; defaults to today.
        tz: Optional IANA timezone name (e.g. "Asia/Tbilisi"). Default None = UTC.
        principal: Resolved identity from ``get_principal``.
        db: SQLAlchemy session.

    Returns:
        List of ``TrainingDay`` summaries, newest first.

    Raises:
        HTTPException 422: If ``tz`` is not a valid IANA timezone name.
    """
    _validate_tz(tz)  # raises 422 on invalid tz

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

    if tz is None:
        # UTC path — unchanged behaviour.
        # Reason: the outer query references pr_flags pf, so the column
        # alias is pf.date (not t.date which was used in the old single-table query).
        day_expr = "pf.date::date"
        query_params: dict = {"uid": uid, "dt_from": dt_from, "dt_to": dt_to}
    else:
        # Timezone-aware path: convert the naive UTC timestamp to the user's local
        # wall-clock before casting to date.  The AT TIME ZONE transform stays out
        # of the WHERE clause so the index on (user_id, date) is still used.
        day_expr = "(pf.date AT TIME ZONE 'UTC' AT TIME ZONE :tz)::date"
        query_params = {"uid": uid, "dt_from": dt_from, "dt_to": dt_to, "tz": tz}

    # GYM-155: Temporal PR detection via window functions.
    #
    # Step 1 (all_sets CTE): pull the user's FULL history (not just the window)
    # for every exercise present in the requested window.  This ensures the
    # "prior" comparison is correct for any set inside the window even when
    # earlier sets fall outside the window date range.
    #
    # Step 2 (pr_flags CTE): compute two running-max window functions per set,
    # ordered by (date, set) — the canonical insertion order:
    #   prior_max_w         — max weight seen BEFORE this set for the exercise.
    #   prior_max_reps_at_w — max reps seen BEFORE this set at this exact weight.
    # The ROWS BETWEEN UNBOUNDED PRECEDING AND 1 PRECEDING frame excludes the
    # current row so "prior" is strictly earlier.
    #
    # Step 3: is_pr logic (Option A, no e1RM):
    #   - prior_max_w IS NULL              → first ever set of this exercise = PR
    #   - weight > prior_max_w             → strict weight PR
    #   - prior_max_reps_at_w IS NOT NULL  → weight was lifted before (not first
    #     time at this weight) AND reps > prior_max_reps_at_w → reps-at-weight PR
    #
    # Step 4: filter pr_flags to the requested window, then GROUP BY day and OR
    # the is_pr flags for has_pr.
    sql = f"""
        WITH window_exercises AS (
            -- Distinct exercises the user trained in the requested window.
            -- Used to scope the full-history scan to only relevant exercises.
            SELECT DISTINCT exercise_id
            FROM training
            WHERE user_id = :uid
              AND date >= :dt_from
              AND date  < :dt_to
        ),
        all_sets AS (
            -- Full history for those exercises (needed for correct "prior" context).
            SELECT t.id, t.date, t.set, t.exercise_id, t.muscle_id,
                   t.weight, t.reps
            FROM training t
            JOIN window_exercises we ON we.exercise_id = t.exercise_id
            WHERE t.user_id = :uid
        ),
        pr_flags AS (
            SELECT
                id, date, exercise_id, muscle_id, weight, reps,
                -- Running max weight of all EARLIER sets for this exercise.
                MAX(weight) OVER (
                    PARTITION BY exercise_id
                    ORDER BY date, set
                    ROWS BETWEEN UNBOUNDED PRECEDING AND 1 PRECEDING
                ) AS prior_max_w,
                -- Running max reps of all EARLIER sets at the same weight.
                MAX(reps) OVER (
                    PARTITION BY exercise_id, weight
                    ORDER BY date, set
                    ROWS BETWEEN UNBOUNDED PRECEDING AND 1 PRECEDING
                ) AS prior_max_reps_at_w
            FROM all_sets
        )
        SELECT
            {day_expr}                AS day,
            ARRAY_AGG(DISTINCT m.name) AS muscles,
            COUNT(DISTINCT pf.exercise_id) AS exercises_count,
            COUNT(*)                   AS sets_count,
            BOOL_OR(
                pf.prior_max_w IS NULL
                OR pf.weight > pf.prior_max_w
                OR (
                    pf.prior_max_reps_at_w IS NOT NULL
                    AND pf.reps > pf.prior_max_reps_at_w
                )
            )                          AS has_pr
        FROM pr_flags pf
        JOIN muscles m ON m.id = pf.muscle_id
        WHERE pf.date >= :dt_from
          AND pf.date  < :dt_to
        GROUP BY {day_expr}
        ORDER BY {day_expr} DESC
    """

    rows = db.execute(text(sql), query_params).fetchall()

    return [
        schemas.TrainingDay(
            date=row.day,
            muscles=sorted(row.muscles),
            exercises_count=row.exercises_count,
            sets_count=row.sets_count,
            has_pr=bool(row.has_pr),
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
    tz: Optional[str] = Query(default=None),
    principal: Principal = Depends(get_principal),
    db: Session = Depends(get_db_for_principal),
) -> schemas.TrainingDayDetail:
    """Return the caller's full training detail for a single calendar day.

    All sets recorded on the given day are returned, grouped by exercise with
    muscle and exercise names denormalized.  Returns an empty exercises list
    for a day with no training — never a 404 for the empty case.

    GYM-155: each set carries ``is_pr`` using temporal PR semantics — True
    when the set was a personal record at the moment it was logged (weight PR
    or reps-at-weight PR vs all prior sets of that exercise, ordered by date
    then set number).  Constant-weight / bodyweight exercises are handled
    correctly: only the first set of the exercise and any new reps-at-weight
    records flag is_pr=True.

    GYM-153: each set also carries ``pr_kind`` — ``'weight'`` for a strict
    weight PR or the first-ever set of the exercise; ``'reps'`` for a strict
    reps-at-weight PR; ``None`` when is_pr is false.  Derived from the same
    window-function expressions as is_pr so they can never disagree.

    GYM-142 (variant A): exercise groups are ordered by recency — the most
    recently logged exercise first (DESC by MAX(t.date) within the day).
    Sets within an exercise remain in ascending set-number order.  The recency
    signal is the ``date`` TIMESTAMP column (set to server UTC at insert time).

    GYM-156: When ``tz`` is provided, the day window is computed from the LOCAL
    midnight boundaries of ``day_date`` in ``tz``.  The LOCAL midnight is
    converted to UTC so the WHERE filter stays on the raw ``date`` column
    (sargable).  Without ``tz`` the existing UTC behaviour is unchanged.
    Adding 1 day to the tz-aware local midnight before converting to UTC
    handles DST correctly (next LOCAL midnight, not +86400 seconds).

    Args:
        day_date: Calendar date to fetch.
        tz: Optional IANA timezone name (e.g. "Asia/Tbilisi"). Default None = UTC.
        principal: Resolved identity from ``get_principal``.
        db: SQLAlchemy session.

    Returns:
        ``TrainingDayDetail`` with exercises grouped by exercise_id, ordered
        most-recently-logged first, each with its ascending set list.

    Raises:
        HTTPException 422: If ``tz`` is not a valid IANA timezone name.
    """
    _validate_tz(tz)  # raises 422 on invalid tz
    uid = principal["user_id"]
    if tz is None:
        # UTC path — unchanged back-compat behaviour.
        dt_from = datetime(day_date.year, day_date.month, day_date.day)
        dt_to = dt_from + timedelta(days=1)
    else:
        # Timezone-aware path: compute LOCAL midnight boundaries then convert to UTC.
        # Adding timedelta(days=1) to the tz-aware local midnight gives the next
        # LOCAL midnight (DST-correct), which we then strip back to a naive UTC.
        local_midnight = datetime(
            day_date.year, day_date.month, day_date.day, tzinfo=ZoneInfo(tz)
        )
        dt_from = local_midnight.astimezone(ZoneInfo("UTC")).replace(tzinfo=None)
        dt_to = (local_midnight + timedelta(days=1)).astimezone(
            ZoneInfo("UTC")
        ).replace(tzinfo=None)

    # GYM-155: Temporal PR detection via window functions (same logic as
    # list_training_days — see that docstring for full derivation).
    #
    # all_sets: full history for every exercise the user did on this day so
    # the window functions have correct "prior" context even when earlier sets
    # fall on other days.
    #
    # pr_flags: running-max window functions partitioned by exercise (and by
    # exercise+weight for the reps dimension).  ROWS BETWEEN UNBOUNDED
    # PRECEDING AND 1 PRECEDING excludes the current row — strictly prior.
    #
    # GYM-142: ex_recency provides the latest timestamp per exercise within
    # the day so the outer ORDER BY places the most-recently-logged exercise
    # first while sets within each exercise remain ascending by set number.
    rows = db.execute(
        text("""
            WITH day_exercises AS (
                SELECT DISTINCT exercise_id
                FROM training
                WHERE user_id = :uid
                  AND date >= :dt_from
                  AND date  < :dt_to
            ),
            all_sets AS (
                SELECT t.id, t.date, t.set, t.exercise_id, t.muscle_id,
                       t.weight, t.reps
                FROM training t
                JOIN day_exercises de ON de.exercise_id = t.exercise_id
                WHERE t.user_id = :uid
            ),
            pr_flags AS (
                SELECT
                    id, date, set, exercise_id, muscle_id, weight, reps,
                    MAX(weight) OVER (
                        PARTITION BY exercise_id
                        ORDER BY date, set
                        ROWS BETWEEN UNBOUNDED PRECEDING AND 1 PRECEDING
                    ) AS prior_max_w,
                    MAX(reps) OVER (
                        PARTITION BY exercise_id, weight
                        ORDER BY date, set
                        ROWS BETWEEN UNBOUNDED PRECEDING AND 1 PRECEDING
                    ) AS prior_max_reps_at_w
                FROM all_sets
            ),
            ex_recency AS (
                SELECT exercise_id, MAX(date) AS last_logged
                FROM training
                WHERE user_id = :uid
                  AND date >= :dt_from
                  AND date  < :dt_to
                GROUP BY exercise_id
            )
            SELECT
                pf.id                   AS training_id,
                pf.set,
                pf.weight,
                pf.reps,
                pf.exercise_id,
                e.name                  AS exercise_name,
                m.name                  AS muscle_name,
                (
                    pf.prior_max_w IS NULL
                    OR pf.weight > pf.prior_max_w
                    OR (
                        pf.prior_max_reps_at_w IS NOT NULL
                        AND pf.reps > pf.prior_max_reps_at_w
                    )
                )                       AS is_pr,
                -- GYM-153: weight branch is checked first so the first-ever
                -- set (prior_max_w IS NULL) always yields 'weight', guaranteeing
                -- mutual exclusivity with the 'reps' branch.
                -- Invariant: pr_kind IS NOT NULL exactly when is_pr is true.
                CASE
                    WHEN (pf.prior_max_w IS NULL OR pf.weight > pf.prior_max_w)
                        THEN 'weight'
                    WHEN (
                        pf.prior_max_reps_at_w IS NOT NULL
                        AND pf.reps > pf.prior_max_reps_at_w
                    )
                        THEN 'reps'
                    ELSE NULL
                END                     AS pr_kind
            FROM pr_flags pf
            JOIN exercises  e  ON e.id  = pf.exercise_id
            JOIN muscles    m  ON m.id  = pf.muscle_id
            JOIN ex_recency er ON er.exercise_id = pf.exercise_id
            WHERE pf.date >= :dt_from
              AND pf.date  < :dt_to
            ORDER BY er.last_logged DESC, pf.set ASC
        """),
        {"uid": uid, "dt_from": dt_from, "dt_to": dt_to},
    ).fetchall()

    # Group by exercise_id preserving order of first appearance (recency order
    # comes from the SQL ORDER BY er.last_logged DESC).
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
                is_pr=bool(row.is_pr),
                pr_kind=row.pr_kind,
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


# ---------------------------------------------------------------------------
# PATCH /training/{training_id}/move  — GYM-51
# ---------------------------------------------------------------------------

@router.patch(
    "/training/{training_id}/move",
    response_model=schemas.Training,
    tags=["training"],
)
def move_training(
    training_id: str,
    body: schemas.TrainingMove,
    principal: Principal = Depends(get_principal),
    db: Session = Depends(get_db_for_principal),
) -> schemas.Training:
    """Move a training set to another date and/or exercise.

    At least one of {date, (muscle_name + exercise_name)} must be supplied.
    muscle_name and exercise_name must always appear together — they move the
    set to a different exercise under the named muscle.

    Date storage: noon UTC of the target calendar day, so the set lands on the
    intended day in every real-world timezone (±12h safe).

    Returns 409 when the move would create a duplicate (same user + resulting
    date day + resulting exercise_id + same set number already exists in a
    DIFFERENT row).

    Args:
        training_id: Server-assigned id of the training set to move.
        body: Fields to change (date, muscle_name+exercise_name, or both).
        principal: Resolved identity from ``get_principal``.
        db: SQLAlchemy session.

    Returns:
        The updated training record.

    Raises:
        HTTPException 404: Row not found or not owned by caller.
        HTTPException 422: Empty body; or only one of muscle_name/exercise_name;
                           or target exercise not resolvable.
        HTTPException 409: Move would collide with an existing set at the same
                           day + exercise + set-number.
    """
    uid = principal["user_id"]

    # --- body validation ---
    has_date = body.date is not None
    has_muscle = body.muscle_name is not None
    has_exercise = body.exercise_name is not None

    if not has_date and not has_muscle and not has_exercise:
        raise HTTPException(
            status_code=422,
            detail="Body must contain at least one of: date, or muscle_name + exercise_name.",
        )

    if has_muscle != has_exercise:
        raise HTTPException(
            status_code=422,
            detail="muscle_name and exercise_name must both be provided together.",
        )

    # --- fetch own row (RLS already scopes to uid) ---
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

    # --- compute target values ---
    if has_date:
        # Store at noon UTC: safe for ±12h offsets.
        target_date = datetime.combine(body.date, time(12, 0))
    else:
        target_date = training.date

    if has_muscle:
        # resolve_exercise_id: own-first-then-global, name_key matching.
        target_exercise_id = resolve_exercise_id(
            db, uid, body.muscle_name, body.exercise_name
        )
        if target_exercise_id is None:
            raise HTTPException(
                status_code=422,
                detail=(
                    f"Exercise '{body.exercise_name}' under muscle '{body.muscle_name}' "
                    "not found or not visible to you."
                ),
            )
        # Fetch the muscle_id for the resolved exercise.
        row = db.execute(
            text("SELECT muscle FROM exercises WHERE id = :eid"),
            {"eid": target_exercise_id},
        ).fetchone()
        target_muscle_id = row[0] if row else training.muscle_id
    else:
        target_exercise_id = training.exercise_id
        target_muscle_id = training.muscle_id

    # --- collision check (409): same user + same day + same exercise + same set# ---
    # Day boundaries for the target date (one calendar day).
    target_day_start = datetime(target_date.year, target_date.month, target_date.day)
    target_day_end = target_day_start + timedelta(days=1)

    collision = (
        db.query(models.Training)
        .filter(
            models.Training.user_id == uid,
            models.Training.exercise_id == target_exercise_id,
            models.Training.set == training.set,
            models.Training.date >= target_day_start,
            models.Training.date < target_day_end,
            models.Training.id != training_id,  # exclude the row being moved
        )
        .first()
    )
    if collision is not None:
        raise HTTPException(
            status_code=409,
            detail=(
                f"Set {training.set} already exists for exercise_id={target_exercise_id} "
                f"on {target_date.date()} — move would create a duplicate."
            ),
        )

    # --- apply changes ---
    training.date = target_date
    training.exercise_id = target_exercise_id
    training.muscle_id = target_muscle_id

    try:
        db.commit()
        db.refresh(training)
    except Exception as exc:
        db.rollback()
        logger.error("Error moving training record: %s", exc, exc_info=True)
        raise HTTPException(status_code=500, detail="Failed to move training record")

    # Purge analytics cache for both the source and target day.
    invalidate_user(uid)
    return training
