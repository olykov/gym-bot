"""Pydantic schemas used by the Core API.

Covers both the existing admin CRUD shapes and the full contract defined in
packages/api-contract/openapi.yaml.  Admin shapes are preserved unchanged so
that existing endpoints keep working.
"""
import datetime as _dt
from datetime import datetime, date
from typing import List, Optional

# Alias: prevents Pydantic from confusing the field name ``date`` with the
# ``datetime.date`` type when both appear in the same class namespace.
_Date = _dt.date

from pydantic import BaseModel, ConfigDict, field_validator

from app.schemas.validators import (
    EXERCISE_NAME_MAX,
    MUSCLE_NAME_MAX,
    validate_name,
    validate_lookup_name,
)


# ---------------------------------------------------------------------------
# Shared config mixin
# ---------------------------------------------------------------------------

class _ORM(BaseModel):
    model_config = ConfigDict(from_attributes=True)


# ---------------------------------------------------------------------------
# Muscle
# ---------------------------------------------------------------------------

class MuscleBase(BaseModel):
    name: str


class MuscleCreate(MuscleBase):
    """Request body for creating/renaming a muscle (admin or user)."""

    @field_validator("name", mode="before")
    @classmethod
    def _validate_name(cls, v: object) -> str:
        """Normalize and validate the muscle name (max 30 chars)."""
        return validate_name(str(v), max_len=MUSCLE_NAME_MAX)


class MuscleRename(BaseModel):
    """Request body for PATCH /muscles/{muscle_id} (own-custom rename)."""

    name: str

    @field_validator("name", mode="before")
    @classmethod
    def _validate_name(cls, v: object) -> str:
        """Normalize and validate the new muscle name (max 30 chars)."""
        return validate_name(str(v), max_len=MUSCLE_NAME_MAX)


class Muscle(_ORM):
    """Full muscle representation as returned by the API."""

    id: int
    name: str
    is_global: Optional[bool] = None
    created_by: Optional[int] = None
    is_mine: Optional[bool] = None
    resolution: Optional[str] = None


# ---------------------------------------------------------------------------
# Exercise
# ---------------------------------------------------------------------------

class ExerciseBase(BaseModel):
    name: str
    muscle: int  # muscle id (admin-facing)


class ExerciseCreate(ExerciseBase):
    """Admin exercise creation: references muscle by id."""

    @field_validator("name", mode="before")
    @classmethod
    def _validate_name(cls, v: object) -> str:
        """Normalize and validate the exercise name (max 40 chars)."""
        return validate_name(str(v), max_len=EXERCISE_NAME_MAX)


class ExerciseCreateByName(BaseModel):
    """User-facing exercise creation: references muscle by name (mirrors bot)."""

    name: str
    muscle_name: str

    @field_validator("name", mode="before")
    @classmethod
    def _validate_name(cls, v: object) -> str:
        """Normalize and validate the exercise name (max 40 chars)."""
        return validate_name(str(v), max_len=EXERCISE_NAME_MAX)

    @field_validator("muscle_name", mode="before")
    @classmethod
    def _validate_muscle_name(cls, v: object) -> str:
        """Normalize the muscle reference name; reject empty only (no length/char cap).

        ``muscle_name`` is a LOOKUP reference, not a name being stored.  See
        ``validate_lookup_name`` docstring for the create-vs-lookup rationale.
        """
        return validate_lookup_name(str(v))


class ExerciseRename(BaseModel):
    """Request body for PATCH /exercises/{exercise_id} (own-custom rename)."""

    name: str

    @field_validator("name", mode="before")
    @classmethod
    def _validate_name(cls, v: object) -> str:
        """Normalize and validate the new exercise name (max 40 chars)."""
        return validate_name(str(v), max_len=EXERCISE_NAME_MAX)


class ExerciseMove(BaseModel):
    """Request body for PATCH /exercises/{exercise_id}/muscle (own-custom move)."""

    muscle_id: int


class Exercise(_ORM):
    """Full exercise representation."""

    id: int
    name: str
    muscle: int  # owning muscle id
    is_global: Optional[bool] = None
    created_by: Optional[int] = None
    is_mine: Optional[bool] = None
    resolution: Optional[str] = None


class ExerciseCandidate(BaseModel):
    """Ranked candidate returned by GET /exercises/search (GYM-93).

    Mirrors the ``ExerciseCandidate`` schema in openapi.yaml.  Identity and
    name fields mirror ``Exercise`` (``id``, ``name``, ``muscle``);
    ``muscle_name`` denormalizes the owning muscle for the dropdown.
    ``match_reason`` and ``score`` describe the ranking tier.
    """

    id: int
    name: str
    muscle: int
    muscle_name: str
    match_reason: str  # 'exact' | 'prefix' | 'alias' | 'fuzzy'
    score: float


# ---------------------------------------------------------------------------
# User
# ---------------------------------------------------------------------------

class UserBase(BaseModel):
    id: int
    first_name: Optional[str] = None
    lastname: Optional[str] = None
    username: Optional[str] = None


class User(_ORM):
    """Full user representation."""

    id: int
    first_name: Optional[str] = None
    lastname: Optional[str] = None
    username: Optional[str] = None
    bio: Optional[str] = None
    registration_date: Optional[datetime] = None
    last_interaction: Optional[datetime] = None


class UserRegistration(BaseModel):
    """Fields the caller may supply when registering/updating their profile."""

    first_name: Optional[str] = None
    lastname: Optional[str] = None
    username: Optional[str] = None
    bio: Optional[str] = None


# ---------------------------------------------------------------------------
# Training
# ---------------------------------------------------------------------------

class TrainingBase(BaseModel):
    date: datetime
    user_id: int
    muscle_id: int
    exercise_id: int
    set: int
    weight: float
    reps: float


class Training(_ORM):
    """Full training record.

    ``id`` is a uuid4 hex string (32 hex chars) assigned by the server.
    This is the unified scheme used by the whole API — see GYM-22 ID
    unification note.
    """

    id: str
    date: datetime
    user_id: int
    muscle_id: int
    exercise_id: int
    set: int
    weight: float
    reps: float

    # Nested for admin list view (optional — populated only by admin endpoints)
    muscle_group: Optional[Muscle] = None
    exercise: Optional[Exercise] = None
    user: Optional[User] = None


class TrainingCreate(BaseModel):
    """Create a training set (user-facing, mirrors bot save_training_data).

    Muscle and exercise are referenced by name so the request matches what the
    bot sends today.  id and user_id are assigned by the server.  ``date`` is
    optional: when provided the set is logged on that calendar day (at noon UTC
    for tz-safety); when omitted the server uses utcnow() (unchanged).

    Name fields use ``validate_lookup_name``: they are normalized (trim +
    whitespace-collapse) and must not be empty, but NO max-length cap and NO
    character-whitelist are applied.  This path only looks up existing rows by
    name, never creates new ones, so capping at 30/40 chars or char-checking
    would reject lookups for names that predate the current validation rules.
    See ``apps/api/app/schemas/validators.validate_lookup_name`` for the full
    create-vs-lookup rationale.
    """

    muscle_name: str
    exercise_name: str
    set: int
    weight: float
    reps: float
    date: Optional[_Date] = None

    @field_validator("muscle_name", "exercise_name", mode="before")
    @classmethod
    def _normalize_lookup_name(cls, v: object) -> str:
        """Normalize lookup reference; reject empty only (no length/char cap).

        Delegates to ``validate_lookup_name`` — see its docstring for the
        create-vs-lookup rationale.
        """
        return validate_lookup_name(str(v))


class TrainingUpdate(BaseModel):
    """Mutable fields on a training record (weight + reps only)."""

    weight: float
    reps: float


class TrainingMove(BaseModel):
    """Request body for PATCH /training/{training_id}/move (GYM-51).

    All fields are optional; at least one of {date, (muscle_name +
    exercise_name)} must be supplied.  If either muscle_name or exercise_name
    is given, both are required (they move together).

    Name fields use ``validate_lookup_name``: normalized (trim +
    whitespace-collapse), must not be empty, no max-length cap.
    """

    date: Optional[_Date] = None
    muscle_name: Optional[str] = None
    exercise_name: Optional[str] = None

    @field_validator("muscle_name", "exercise_name", mode="before")
    @classmethod
    def _normalize_lookup_name(cls, v: object) -> str:
        """Normalize lookup reference; reject empty only (no length/char cap)."""
        if v is None:
            return v  # type: ignore[return-value]
        return validate_lookup_name(str(v))


# ---------------------------------------------------------------------------
# Training history — GYM-47
# ---------------------------------------------------------------------------

class TrainingSet(BaseModel):
    """A single recorded set within a training day's exercise.

    Matches ``TrainingSet`` in packages/api-contract/openapi.yaml.
    """

    training_id: str
    set: int
    weight: float
    reps: float


class TrainingDayExercise(BaseModel):
    """One exercise trained on a day, with denormalized names and its sets.

    Matches ``TrainingDayExercise`` in the OpenAPI contract.
    """

    exercise_id: int
    exercise_name: str
    muscle_name: str
    sets: List["TrainingSet"]


class TrainingDay(BaseModel):
    """One day the caller trained, summarised for the History list.

    Matches ``TrainingDay`` in the OpenAPI contract.
    ``date`` is a calendar date (not a timestamp).

    ``has_pr`` (GYM-136) is True when the day holds the caller's CURRENT
    all-time max-weight set of at least one exercise ("current max" semantic:
    a later heavier set moves the marker to its own day; ties mark every
    tying day).
    """

    date: date
    muscles: List[str]
    exercises_count: int
    sets_count: int
    has_pr: bool


class TrainingDayDetail(BaseModel):
    """Full detail of the caller's training on a single day.

    Matches ``TrainingDayDetail`` in the OpenAPI contract.
    ``exercises`` is empty when no rows exist for the date.
    """

    date: date
    exercises: List[TrainingDayExercise]


# ---------------------------------------------------------------------------
# Analytics
# ---------------------------------------------------------------------------

class CompletedSets(BaseModel):
    """Distinct set numbers already recorded for an exercise on a date."""

    sets: List[int]


class TrainingHistoryEntry(BaseModel):
    """Single row from get_last_training_history."""

    date: datetime
    set: int
    weight: float
    reps: float


class PersonalRecord(BaseModel):
    """Max-weight personal record for an exercise."""

    weight: float
    reps: float
    date: datetime


class MaxReps(BaseModel):
    """Max reps at a given weight (null when no history)."""

    max_reps: Optional[float] = None


class TopExercise(BaseModel):
    """Exercise ranked by training frequency for a muscle."""

    name: str
    frequency: int


class TopMuscle(BaseModel):
    """Muscle ranked by training frequency for the caller (GYM-60 contract).

    Matches ``TopMuscle`` in packages/api-contract/openapi.yaml.
    """

    name: str
    frequency: int


# ---------------------------------------------------------------------------
# Analytics (GYM-39) — dashboard / Mini App
# ---------------------------------------------------------------------------

class ActivityDay(BaseModel):
    """Sets recorded on a single day within the requested range.

    Matches the ``ActivityDay`` schema in packages/api-contract/openapi.yaml.
    ``date`` is a calendar date (not a timestamp).
    """

    date: date
    sets_count: int


class AnalyticsSummary(BaseModel):
    """Headline dashboard metrics for the caller.

    Matches ``AnalyticsSummary`` in the OpenAPI contract.

    Attributes:
        exercises: Distinct exercises ever logged by this user.
        sets: Total sets recorded by this user.
        prs: Number of exercises for which a max-weight personal record exists.
        current_streak: Consecutive Monday-start weeks (UTC) ending at the
            current week, each containing >=1 training session (GYM-56).
    """

    exercises: int
    sets: int
    prs: int
    current_streak: int


class ExercisePoint(BaseModel):
    """A single recorded point of weight and reps on a date.

    Matches ``ExercisePoint`` in the OpenAPI contract.
    ``date`` is a calendar date (not a timestamp).
    """

    date: date
    weight: float
    reps: float


class ExerciseSetSeries(BaseModel):
    """Progress series for one set number.

    Matches ``ExerciseSetSeries`` in the OpenAPI contract.
    """

    set: int
    points: List[ExercisePoint]


class ExerciseProgress(BaseModel):
    """Per-set progress series for an exercise, shaped for ECharts.

    Matches ``ExerciseProgress`` in the OpenAPI contract.
    Empty when no history exists for the exercise.
    """

    series: List[ExerciseSetSeries]


class RecentExercise(BaseModel):
    """A distinct exercise the caller trained recently, with last-set metadata.

    Matches ``RecentExercise`` in packages/api-contract/openapi.yaml (GYM-66).
    ``last_date`` is a calendar date (not a timestamp).
    """

    muscle_name: str
    exercise_name: str
    last_weight: float
    last_reps: float
    last_date: date


# ---------------------------------------------------------------------------
# Log-context (GYM-71) — combined set-logger payload
# ---------------------------------------------------------------------------

class LogSet(BaseModel):
    """A single set from a prior session, for set-logger pre-fill.

    Matches ``LogSet`` in packages/api-contract/openapi.yaml.
    """

    set: int
    weight: float
    reps: float


class LogContext(BaseModel):
    """Combined set-logger context: completed sets, last-session sets, and PR.

    Matches ``LogContext`` in packages/api-contract/openapi.yaml (GYM-70).

    Attributes:
        completed_sets: Set numbers already logged on ``date`` for this exercise.
        last_session_sets: Sets from the most recent prior session, ordered by set.
        pr: Personal record (max weight), or null when no history exists.
    """

    completed_sets: List[int]
    last_session_sets: List[LogSet]
    pr: Optional[PersonalRecord] = None


# ---------------------------------------------------------------------------
# Exercise trend (GYM-134) — session volume delta + e1RM trend series
# ---------------------------------------------------------------------------

class SessionVolume(BaseModel):
    """One training session (calendar day) with its total volume.

    Matches ``SessionVolume`` in packages/api-contract/openapi.yaml.
    ``volume`` is the sum of weight x reps across all sets of the session.
    """

    date: date
    volume: float


class E1rmPoint(BaseModel):
    """Per-session maximum estimated one-rep max (Epley).

    Matches ``E1rmPoint`` in the OpenAPI contract.
    ``e1rm`` is max(weight * (1 + reps/30)) across the session's sets.
    """

    date: date
    e1rm: float


class ExerciseTrend(BaseModel):
    """Session-vs-session volume delta inputs plus a per-session e1RM trend.

    Matches ``ExerciseTrend`` in the OpenAPI contract (GYM-134).

    Attributes:
        last_session: The most recent session, or null when no history exists.
        prev_session: The session before the most recent one, or null.
        e1rm_trend: Per-session max-e1RM points within the window, date ascending.
    """

    last_session: Optional[SessionVolume] = None
    prev_session: Optional[SessionVolume] = None
    e1rm_trend: List[E1rmPoint]


# ---------------------------------------------------------------------------
# Week comparison (GYM-136) — this-week vs last-week dashboard card
# ---------------------------------------------------------------------------

class WeekStats(BaseModel):
    """Training totals for one Monday-start calendar week.

    Matches ``WeekStats`` in packages/api-contract/openapi.yaml (GYM-136).
    ``volume`` is the sum of weight x reps across the week's sets.
    """

    sets: int
    volume: float


class WeekCompare(BaseModel):
    """This-week vs last-week totals for the Dashboard comparison card.

    Matches ``WeekCompare`` in the OpenAPI contract (GYM-136).  Weeks are
    Monday-start calendar weeks in the requested timezone (UTC when omitted);
    a week with no training carries zeros.
    """

    this_week: WeekStats
    last_week: WeekStats
