"""Exercise endpoints — GYM-22 / GYM-26.

Covers list, create, hide/unhide, and delete for exercises, all scoped to the
authenticated user.  Isolation (visible exercises) is delegated to
``app.services.visibility``.

All routes accept EITHER a user JWT (Mini App) OR a service token +
X-Act-As-User impersonation (the Telegram bot) via ``get_principal``.
"""
import logging
from typing import List, Optional

from fastapi import APIRouter, Depends, HTTPException, Response
from sqlalchemy import exists, text
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session

from app.core.database import get_db_for_principal
from app.middleware.permissions import Principal, get_principal
from app.models import models
from app.schemas import schemas
from app.services.resolve import resolve_muscle_id
from app.services.visibility import visible_exercises_for_muscle, visible_muscles

# ---------------------------------------------------------------------------
# Tiered search SQL for GET /exercises/search (GYM-93).
#
# Candidate pool: exercises visible to the caller under RLS (global canonical
# + the caller's own customs — consistent with listExercisesByMuscle scope)
# plus alias hits from exercise_alias (global catalog, lang-aware).
#
# Tiers (highest score → lowest), one row per exercise id (DISTINCT ON keeps
# the best tier per id):
#   tier 1 (exact)  score 1.0 — name_key = app_name_key(:q) exact match
#   tier 2 (prefix) score 0.8 — name_key LIKE app_name_key(:q) || '%'
#   tier 3 (alias)  score 0.6 — exercise_alias.name_key matches exact/prefix;
#                                matches ANY alias lang (UI locale does NOT gate
#                                recall — GYM-112 fix: removed a.lang = :lang)
#   tier 4 (fuzzy)  score similarity() — pg_trgm similarity > 0.3
#
# Fuzzy threshold 0.3: the pg_trgm default, chosen for typo tolerance on
# 5–15 char exercise names while keeping false positives low.
# ---------------------------------------------------------------------------
_SEARCH_SQL = """
WITH q_key AS (
    -- Normalize the query once; re-used in every tier.
    SELECT public.app_name_key(:q) AS k
),
candidates AS (
    -- Tier 1: exact name_key match on exercises visible to this caller.
    -- score 1.0; only exercises where e.muscle = :muscle_id when scoped.
    SELECT
        e.id,
        e.name,
        e.muscle,
        m.name AS muscle_name,
        1                AS tier,
        CAST(1.0 AS float) AS score,
        'exact'          AS match_reason
    FROM exercises e
    JOIN muscles m ON m.id = e.muscle
    CROSS JOIN q_key
    WHERE e.name_key = q_key.k
      AND (CAST(:muscle_id AS int) IS NULL OR e.muscle = CAST(:muscle_id AS int))

    UNION ALL

    -- Tier 2: prefix match on name_key (excludes exact match rows).
    -- score 0.8.
    SELECT
        e.id,
        e.name,
        e.muscle,
        m.name AS muscle_name,
        2                  AS tier,
        CAST(0.8 AS float) AS score,
        'prefix'           AS match_reason
    FROM exercises e
    JOIN muscles m ON m.id = e.muscle
    CROSS JOIN q_key
    WHERE e.name_key LIKE q_key.k || '%'
      AND e.name_key <> q_key.k
      AND (CAST(:muscle_id AS int) IS NULL OR e.muscle = CAST(:muscle_id AS int))

    UNION ALL

    -- Tier 3: alias hit — matches any alias regardless of lang (GYM-112).
    -- The lang guard has been removed; aliases are alternate names a user may
    -- type in any language and UI locale must not gate recall.
    -- Joins exercise_alias on canonical_id = exercises.id; alias.name_key
    -- matches exact or prefix. score 0.6.
    SELECT
        e.id,
        e.name,
        e.muscle,
        m.name AS muscle_name,
        3                  AS tier,
        CAST(0.6 AS float) AS score,
        'alias'            AS match_reason
    FROM exercise_alias a
    JOIN exercises e ON e.id = a.canonical_id
    JOIN muscles m   ON m.id = e.muscle
    CROSS JOIN q_key
    WHERE (a.name_key = q_key.k OR a.name_key LIKE q_key.k || '%')
      AND (CAST(:muscle_id AS int) IS NULL OR e.muscle = CAST(:muscle_id AS int))

    UNION ALL

    -- Tier 4: fuzzy match via pg_trgm similarity on exercises.name_key.
    -- score = similarity value (> 0.3 threshold).
    SELECT
        e.id,
        e.name,
        e.muscle,
        m.name                          AS muscle_name,
        4                               AS tier,
        similarity(e.name_key, q_key.k) AS score,
        'fuzzy'                         AS match_reason
    FROM exercises e
    JOIN muscles m ON m.id = e.muscle
    CROSS JOIN q_key
    WHERE similarity(e.name_key, q_key.k) > 0.3
      AND (CAST(:muscle_id AS int) IS NULL OR e.muscle = CAST(:muscle_id AS int))
),
ranked AS (
    -- Keep the best tier per exercise id (DISTINCT ON keeps first row per id
    -- after ordering by tier ASC, score DESC within each id group).
    SELECT DISTINCT ON (id)
        id,
        name,
        muscle,
        muscle_name,
        match_reason,
        score
    FROM candidates
    ORDER BY id, tier ASC, score DESC
)
SELECT id, name, muscle, muscle_name, match_reason, score
FROM ranked
ORDER BY
    CASE match_reason
        WHEN 'exact'  THEN 1
        WHEN 'prefix' THEN 2
        WHEN 'alias'  THEN 3
        WHEN 'fuzzy'  THEN 4
    END,
    score DESC,
    name
LIMIT :lim
"""

logger = logging.getLogger(__name__)

router = APIRouter()


@router.get(
    "/exercises/search",
    response_model=List[schemas.ExerciseCandidate],
    tags=["exercises"],
)
def search_exercises(
    q: str,
    muscle_id: Optional[int] = None,
    lang: Optional[str] = None,
    limit: int = 8,
    principal: Principal = Depends(get_principal),
    db: Session = Depends(get_db_for_principal),
) -> List[schemas.ExerciseCandidate]:
    """Search canonical exercise candidates with tiered ranking (GYM-93).

    Ranks candidates from exercises visible to the caller under RLS plus alias
    hits from ``exercise_alias``.  Returns up to ``limit`` results, best first.

    Tiers (highest to lowest priority):
        ``exact``  — ``exercises.name_key = app_name_key(:q)``; score 1.0.
        ``prefix`` — ``exercises.name_key LIKE app_name_key(:q) || '%'``; score 0.8.
        ``alias``  — hit in ``exercise_alias`` (any lang; UI locale does not gate recall); score 0.6.
        ``fuzzy``  — ``similarity(exercises.name_key, app_name_key(:q)) > 0.3``; score = similarity.

    One result row per exercise id (best tier kept).  Empty result set = ``[]``
    (no 404).  ``muscle_id`` scopes the search to a single muscle when provided.

    Args:
        q: Search query (user's typed text; minLength 1 enforced by FastAPI).
        muscle_id: Optional muscle scope; omit to search the whole catalog.
        lang: Optional ISO-639-1 locale; accepted for backward compatibility but no
            longer filters alias matches (GYM-112). Reserved for future ranking/display.
        limit: Maximum results to return (default 8, max 20).
        principal: Resolved identity from ``get_principal``.
        db: SQLAlchemy session with RLS GUC context pre-set.

    Returns:
        Ordered list of ``ExerciseCandidate`` items, best match first (may be empty).

    Raises:
        HTTPException: 400 when ``q`` is empty (minLength guard).
        HTTPException: 401 when the caller is not authenticated.
    """
    if not q or not q.strip():
        raise HTTPException(status_code=400, detail="q must not be empty")

    # Clamp limit to contract bounds (1..20).
    limit = max(1, min(20, limit))

    # Note: `lang` param is accepted (backward compat / future ranking) but is no
    # longer passed to the SQL — the alias tier now matches regardless of lang
    # (GYM-112).
    rows = db.execute(
        text(_SEARCH_SQL),
        {
            "q": q,
            "muscle_id": muscle_id,
            "lim": limit,
        },
    ).fetchall()

    return [
        schemas.ExerciseCandidate(
            id=row[0],
            name=row[1],
            muscle=row[2],
            muscle_name=row[3],
            match_reason=row[4],
            score=float(row[5]),
        )
        for row in rows
    ]


@router.get(
    "/exercises/hidden",
    response_model=List[schemas.Exercise],
    tags=["exercises"],
)
def list_hidden_exercises(
    muscle: str,
    principal: Principal = Depends(get_principal),
    db: Session = Depends(get_db_for_principal),
) -> List[schemas.Exercise]:
    """List exercises the authenticated user has hidden within a muscle (GYM-102).

    Resolves the muscle by NAME_KEY using ``app_name_key(:muscle)`` (consistent
    with GYM-99 analytics resolution).  Returns the exercises the caller has
    explicitly hidden under that muscle, ordered by name.  Returns an empty
    array when nothing is hidden — NOT a 404.

    ``is_mine`` is set to True only for the user's own private exercises.
    ``resolution`` is null (read endpoint, not a create/resolve path).

    Args:
        muscle: Muscle name (resolved via ``app_name_key``; case/dash/space-insensitive).
        principal: Resolved identity from ``get_principal``.
        db: SQLAlchemy session.

    Returns:
        Ordered list of hidden exercises (may be empty).

    Raises:
        HTTPException: 404 when the muscle name does not resolve to any known muscle.
    """
    uid = principal["user_id"]

    # Resolve the muscle by name_key so variant casing/spacing/dashes all work.
    muscle_row = db.execute(
        text(
            "SELECT id FROM muscles "
            "WHERE name_key = app_name_key(:muscle) "
            "LIMIT 1"
        ),
        {"muscle": muscle},
    ).fetchone()
    if muscle_row is None:
        raise HTTPException(status_code=404, detail="Muscle not found")
    muscle_id = muscle_row[0]

    hidden_ids_subq = (
        db.query(models.UserHiddenExercise.exercise_id)
        .filter(models.UserHiddenExercise.user_id == uid)
        .subquery()
    )
    exercises = (
        db.query(models.Exercise)
        .filter(
            models.Exercise.muscle == muscle_id,
            models.Exercise.id.in_(db.query(hidden_ids_subq.c.exercise_id)),
        )
        .order_by(models.Exercise.name)
        .all()
    )
    for ex in exercises:
        ex.is_mine = bool(ex.created_by == uid and not ex.is_global)
    return exercises


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
    exercises = visible_exercises_for_muscle(db, uid, muscle_id)
    for ex in exercises:
        ex.is_mine = bool(ex.created_by == uid and not ex.is_global)
    return exercises


@router.post("/exercises", response_model=schemas.Exercise, tags=["exercises"])
def create_exercise(
    body: schemas.ExerciseCreateByName,
    http_response: Response,
    principal: Principal = Depends(get_principal),
    db: Session = Depends(get_db_for_principal),
) -> schemas.Exercise:
    """Add a private exercise for the authenticated user (find-or-create-or-unhide).

    Finds or creates the muscle by name first (name lookup, not key-based),
    then applies key-based resolution for the exercise (GYM-85):

    Resolution precedence (scoped to the resolved muscle):

    1. Key matches caller's OWN exercise (``created_by == uid``) → return it,
       ``resolution=existing``, HTTP 200.
    2. Key matches a GLOBAL exercise NOT hidden for the caller → return it,
       ``resolution=existing``, HTTP 200.
    3. Key matches a GLOBAL exercise that IS hidden → silently remove the
       ``UserHiddenExercise`` row → return it, ``resolution=unhidden``,
       HTTP 200.
    4. No key match → create a new private row, ``resolution=created``,
       HTTP 201.

    Args:
        body: Exercise name and muscle name.
        http_response: FastAPI ``Response`` injected to set the status code.
        principal: Resolved identity from ``get_principal``.
        db: SQLAlchemy session.

    Returns:
        Existing, unhidden, or newly created exercise.
    """
    uid = principal["user_id"]
    muscle_name = body.muscle_name.strip()
    exercise_name = body.name  # already normalized by the validator

    # GYM-106: resolve the owning muscle by name_key (own-first-then-global,
    # variant-name aware) rather than exact name.  If no visible muscle matches
    # the key, fall back to creating a new own muscle with the supplied display
    # name (preserving the GYM-85 create-or-resolve behaviour).
    muscle_id = resolve_muscle_id(db, uid, muscle_name)
    if muscle_id is None:
        new_muscle = models.Muscle(name=muscle_name, is_global=False, created_by=uid)
        db.add(new_muscle)
        db.flush()
        muscle_id = new_muscle.id

    # 1. Own exercise: same key + same muscle + same user.
    own = db.execute(
        text(
            "SELECT id FROM exercises "
            "WHERE created_by = :uid "
            "  AND muscle = :mid "
            "  AND name_key = app_name_key(:name) "
            "LIMIT 1"
        ),
        {"uid": uid, "mid": muscle_id, "name": exercise_name},
    ).fetchone()
    if own:
        exercise = (
            db.query(models.Exercise).filter(models.Exercise.id == own[0]).first()
        )
        if exercise:
            db.commit()  # flush any muscle creation above
            exercise.is_mine = True
            exercise.resolution = "existing"
            http_response.status_code = 200
            return exercise

    # 2 & 3. Global exercise with same key under the same muscle.
    global_row = db.execute(
        text(
            "SELECT id FROM exercises "
            "WHERE created_by IS NULL "
            "  AND muscle = :mid "
            "  AND name_key = app_name_key(:name) "
            "LIMIT 1"
        ),
        {"mid": muscle_id, "name": exercise_name},
    ).fetchone()
    if global_row:
        global_id = global_row[0]
        hidden_row = (
            db.query(models.UserHiddenExercise)
            .filter(
                models.UserHiddenExercise.user_id == uid,
                models.UserHiddenExercise.exercise_id == global_id,
            )
            .first()
        )
        exercise = (
            db.query(models.Exercise).filter(models.Exercise.id == global_id).first()
        )
        if hidden_row:
            # Resolution 3: silently unhide.
            db.delete(hidden_row)
            db.commit()
            db.refresh(exercise)
            exercise.is_mine = False
            exercise.resolution = "unhidden"
            http_response.status_code = 200
            return exercise
        else:
            # Resolution 2: already visible global.
            db.commit()  # flush any muscle creation above
            exercise.is_mine = False
            exercise.resolution = "existing"
            http_response.status_code = 200
            return exercise

    # 4. Create a new private exercise.
    exercise = models.Exercise(
        name=exercise_name,
        muscle=muscle_id,
        is_global=False,
        created_by=uid,
    )
    db.add(exercise)
    db.commit()
    db.refresh(exercise)
    exercise.is_mine = True
    exercise.resolution = "created"
    http_response.status_code = 201
    return exercise


@router.patch(
    "/exercises/{exercise_id}",
    response_model=schemas.Exercise,
    tags=["exercises"],
)
def rename_exercise(
    exercise_id: int,
    body: schemas.ExerciseRename,
    principal: Principal = Depends(get_principal),
    db: Session = Depends(get_db_for_principal),
) -> schemas.Exercise:
    """Rename a private exercise owned by the authenticated user.

    Only the caller's own custom (non-global) exercise may be renamed.
    Returns 403 when the target is a global item, 404 when not found.
    Returns 409 when the new name duplicates another of the caller's exercises
    under the same muscle.

    Args:
        exercise_id: Id of the private exercise to rename.
        body: New name (validated + normalized by ExerciseRename).
        principal: Resolved identity from ``get_principal``.
        db: SQLAlchemy session.

    Returns:
        The updated Exercise record.
    """
    uid = principal["user_id"]
    new_name = body.name

    # Resolve the row first to distinguish 403 from 404.
    exercise = db.query(models.Exercise).filter(models.Exercise.id == exercise_id).first()
    if exercise is None:
        raise HTTPException(status_code=404, detail="Exercise not found")
    if exercise.is_global or exercise.created_by != uid:
        raise HTTPException(
            status_code=403,
            detail="Cannot rename a global or unowned exercise",
        )

    # Key-based pre-check: reject if the new key collides with another visible
    # item under the same muscle for the caller (own rows only; renaming to
    # own current key is a no-op — id != exercise_id filters it out).
    key_dup = db.execute(
        text(
            "SELECT id FROM exercises "
            "WHERE created_by = :uid "
            "  AND muscle = :mid "
            "  AND name_key = app_name_key(:new_name) "
            "  AND id <> :eid "
            "LIMIT 1"
        ),
        {
            "uid": uid,
            "mid": exercise.muscle,
            "new_name": new_name,
            "eid": exercise_id,
        },
    ).fetchone()
    if key_dup:
        raise HTTPException(
            status_code=409,
            detail=f"You already have an exercise named '{new_name}' under that muscle",
        )

    exercise.name = new_name
    try:
        db.commit()
        db.refresh(exercise)
    except IntegrityError:
        db.rollback()
        raise HTTPException(
            status_code=409,
            detail=f"You already have an exercise named '{new_name}' under that muscle",
        )

    exercise.is_mine = True
    return exercise


@router.patch(
    "/exercises/{exercise_id}/muscle",
    response_model=schemas.Exercise,
    tags=["exercises"],
)
def move_exercise(
    exercise_id: int,
    body: schemas.ExerciseMove,
    principal: Principal = Depends(get_principal),
    db: Session = Depends(get_db_for_principal),
) -> schemas.Exercise:
    """Move a private exercise to a different muscle (GYM-90).

    Only the caller's own custom (non-global) exercise may be moved.
    Returns 403 when the target is a global item or owned by another user.
    Returns 404 when the exercise does not exist, or when the target muscle
    does not exist or is not visible to the caller.
    Returns 409 when the caller already has an exercise with the same name
    under the target muscle (unique ``(name, muscle, created_by)`` index).

    Args:
        exercise_id: Id of the private exercise to move.
        body: Target ``muscle_id``.
        principal: Resolved identity from ``get_principal``.
        db: SQLAlchemy session.

    Returns:
        The updated Exercise record with ``is_mine=True``.
    """
    uid = principal["user_id"]
    target_muscle_id = body.muscle_id

    # Resolve the exercise first — distinguish 403 (global/unowned) from 404.
    exercise = db.query(models.Exercise).filter(models.Exercise.id == exercise_id).first()
    if exercise is None:
        raise HTTPException(status_code=404, detail="Exercise not found")
    if exercise.is_global or exercise.created_by != uid:
        raise HTTPException(
            status_code=403,
            detail="Cannot move a global or unowned exercise",
        )

    # Target muscle must exist AND be visible to the caller (global or own).
    visible = visible_muscles(db, uid)
    target_muscle = next((m for m in visible if m.id == target_muscle_id), None)
    if target_muscle is None:
        raise HTTPException(status_code=404, detail="Target muscle not found")

    # Pre-check: caller already has an exercise with the same name in target muscle.
    dup = (
        db.query(models.Exercise)
        .filter(
            models.Exercise.name == exercise.name,
            models.Exercise.created_by == uid,
            models.Exercise.is_global.is_(False),
            models.Exercise.muscle == target_muscle_id,
            models.Exercise.id != exercise_id,
        )
        .first()
    )
    if dup:
        raise HTTPException(
            status_code=409,
            detail=(
                f"You already have an exercise named '{exercise.name}' "
                f"under that muscle"
            ),
        )

    exercise.muscle = target_muscle_id
    try:
        db.commit()
        db.refresh(exercise)
    except IntegrityError:
        db.rollback()
        raise HTTPException(
            status_code=409,
            detail=(
                f"You already have an exercise named '{exercise.name}' "
                f"under that muscle"
            ),
        )

    exercise.is_mine = True
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
    """Hide a global or own exercise for the authenticated user.

    Allows hiding any exercise visible to the caller — global exercises AND
    exercises the caller created themselves.  This is needed for own exercises
    that have logged history (the delete-guard blocks hard-delete, so Hide is
    the only way to remove them from pickers).  (GYM-99)

    Args:
        exercise_id: Id of the exercise to hide (global or own).
        principal: Resolved identity from ``get_principal``.
        db: SQLAlchemy session.
    """
    uid = principal["user_id"]
    # Reason: accept global exercises OR the caller's own private exercises;
    # RLS already ensures we can only see exercises visible to this user.
    exercise = (
        db.query(models.Exercise)
        .filter(
            models.Exercise.id == exercise_id,
        )
        .first()
    )
    if exercise is None:
        raise HTTPException(status_code=404, detail="Exercise not found")

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

    # D2 delete-guard: block hard-delete when training history references this
    # exercise — history must never be silently destroyed.
    history_exists = db.query(
        exists().where(models.Training.exercise_id == exercise_id)
    ).scalar()
    if history_exists:
        raise HTTPException(
            status_code=409,
            detail="exercise has logged history; hide it instead",
        )

    db.delete(exercise)
    db.commit()
