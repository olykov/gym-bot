"""Pydantic schemas used by the Core API.

Covers both the existing admin CRUD shapes and the full contract defined in
packages/api-contract/openapi.yaml.  Admin shapes are preserved unchanged so
that existing endpoints keep working.
"""
from datetime import datetime, date
from typing import List, Optional

from pydantic import BaseModel, ConfigDict


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


class Muscle(_ORM):
    """Full muscle representation as returned by the API."""

    id: int
    name: str
    is_global: Optional[bool] = None
    created_by: Optional[int] = None


# ---------------------------------------------------------------------------
# Exercise
# ---------------------------------------------------------------------------

class ExerciseBase(BaseModel):
    name: str
    muscle: int  # muscle id (admin-facing)


class ExerciseCreate(ExerciseBase):
    """Admin exercise creation: references muscle by id."""


class ExerciseCreateByName(BaseModel):
    """User-facing exercise creation: references muscle by name (mirrors bot)."""

    name: str
    muscle_name: str


class Exercise(_ORM):
    """Full exercise representation."""

    id: int
    name: str
    muscle: int  # owning muscle id
    is_global: Optional[bool] = None
    created_by: Optional[int] = None


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
    bot sends today.  id, date, and user_id are assigned by the server.
    """

    muscle_name: str
    exercise_name: str
    set: int
    weight: float
    reps: float


class TrainingUpdate(BaseModel):
    """Mutable fields on a training record (weight + reps only)."""

    weight: float
    reps: float


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
        current_streak: Consecutive calendar days up to today with at least one
            training set recorded.
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
