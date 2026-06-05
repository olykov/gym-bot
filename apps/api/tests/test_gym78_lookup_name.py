"""GYM-78: Unit tests for the validate_lookup_name validator and the lookup fields.

Covers the exact live regression (can't add exercise into a pre-existing >30-char
muscle) and documents the create-vs-lookup validation boundary.

These are pure unit tests; no DB or Docker container is required.
"""
import pytest
from pydantic import ValidationError

from app.schemas.validators import (
    EXERCISE_NAME_MAX,
    MUSCLE_NAME_MAX,
    validate_lookup_name,
)
from app.schemas.schemas import (
    ExerciseCreate,
    ExerciseCreateByName,
    MuscleCreate,
    TrainingCreate,
)


# ---------------------------------------------------------------------------
# validate_lookup_name — unit
# ---------------------------------------------------------------------------

class TestValidateLookupName:
    def test_valid_name_returned_normalized(self):
        assert validate_lookup_name("  Bench Press  ") == "Bench Press"

    def test_internal_whitespace_collapsed(self):
        assert validate_lookup_name("Upper  Body") == "Upper Body"

    def test_empty_rejected(self):
        with pytest.raises(ValueError, match="empty"):
            validate_lookup_name("")

    def test_whitespace_only_rejected(self):
        with pytest.raises(ValueError, match="empty"):
            validate_lookup_name("   ")

    def test_long_name_over_muscle_cap_accepted(self):
        """Names beyond the 30-char creation cap are accepted for lookups."""
        long_name = "A" * (MUSCLE_NAME_MAX + 5)  # 35 chars
        assert validate_lookup_name(long_name) == long_name

    def test_long_name_over_exercise_cap_accepted(self):
        """Names beyond the 40-char creation cap are accepted for lookups."""
        long_name = "B" * (EXERCISE_NAME_MAX + 5)  # 45 chars
        assert validate_lookup_name(long_name) == long_name

    def test_disallowed_chars_accepted(self):
        """Chars that are disallowed in CREATE names are accepted for lookups."""
        assert validate_lookup_name("Name<with>angles") == "Name<with>angles"

    def test_emoji_accepted(self):
        assert validate_lookup_name("Bench 💪") == "Bench 💪"

    def test_cyrillic_accepted(self):
        assert validate_lookup_name("Грудь") == "Грудь"


# ---------------------------------------------------------------------------
# ExerciseCreateByName — the exact GYM-78 regression
# ---------------------------------------------------------------------------

class TestExerciseCreateByNameLookup:
    def test_long_muscle_name_31_chars_accepted(self):
        """REGRESSION GYM-78: muscle_name > 30 chars must succeed, not return 422.

        Operator reported: POST /api/v1/exercises returned 422 when muscle_name
        was 31+ chars because validate_name(max_len=30) was applied to a LOOKUP
        field.  After the fix, validate_lookup_name is used instead.
        """
        long_muscle = "A" * (MUSCLE_NAME_MAX + 1)  # 31 chars — over the creation cap
        e = ExerciseCreateByName(name="Squat Variation", muscle_name=long_muscle)
        assert e.muscle_name == long_muscle
        assert e.name == "Squat Variation"

    def test_long_muscle_name_50_chars_accepted(self):
        """Even very long legacy muscle names are accepted as lookup references."""
        long_muscle = "Very Long Legacy Muscle Name That Predates The Cap"  # 50 chars
        e = ExerciseCreateByName(name="New Exercise", muscle_name=long_muscle)
        assert e.muscle_name == long_muscle

    def test_muscle_name_whitespace_normalized(self):
        e = ExerciseCreateByName(name="Bench Press", muscle_name="  Upper  Chest  ")
        assert e.muscle_name == "Upper Chest"

    def test_muscle_name_empty_rejected(self):
        with pytest.raises(ValidationError) as exc_info:
            ExerciseCreateByName(name="Bench Press", muscle_name="")
        errors = exc_info.value.errors()
        assert any(e["loc"] == ("muscle_name",) for e in errors)

    def test_muscle_name_whitespace_only_rejected(self):
        with pytest.raises(ValidationError) as exc_info:
            ExerciseCreateByName(name="Bench Press", muscle_name="   ")
        errors = exc_info.value.errors()
        assert any(e["loc"] == ("muscle_name",) for e in errors)

    # --- CREATE-name caps still enforced on the exercise name field ---

    def test_exercise_name_41_chars_rejected(self):
        """The NEW exercise name is still capped at 40 chars (CREATE field)."""
        too_long = "A" * (EXERCISE_NAME_MAX + 1)  # 41 chars
        with pytest.raises(ValidationError) as exc_info:
            ExerciseCreateByName(name=too_long, muscle_name="Chest")
        errors = exc_info.value.errors()
        assert any(e["loc"] == ("name",) for e in errors)

    def test_exercise_name_exactly_40_chars_accepted(self):
        e = ExerciseCreateByName(name="A" * EXERCISE_NAME_MAX, muscle_name="Chest")
        assert len(e.name) == EXERCISE_NAME_MAX

    def test_exercise_name_disallowed_char_rejected(self):
        """The NEW exercise name still enforces the allowed-char whitelist."""
        with pytest.raises(ValidationError) as exc_info:
            ExerciseCreateByName(name="Bench#Press", muscle_name="Chest")
        errors = exc_info.value.errors()
        assert any(e["loc"] == ("name",) for e in errors)

    def test_exercise_name_emoji_rejected(self):
        with pytest.raises(ValidationError) as exc_info:
            ExerciseCreateByName(name="Curl 💪", muscle_name="Biceps")
        errors = exc_info.value.errors()
        assert any(e["loc"] == ("name",) for e in errors)


# ---------------------------------------------------------------------------
# CREATE-name caps unchanged on MuscleCreate and ExerciseCreate (admin)
# ---------------------------------------------------------------------------

class TestCreateNameCapsUnchanged:
    def test_muscle_create_over_30_rejected(self):
        """MuscleCreate.name cap at 30 is unchanged after GYM-78."""
        with pytest.raises(ValidationError) as exc_info:
            MuscleCreate(name="A" * (MUSCLE_NAME_MAX + 1))
        errors = exc_info.value.errors()
        assert any(e["loc"] == ("name",) for e in errors)

    def test_muscle_create_exactly_30_accepted(self):
        m = MuscleCreate(name="A" * MUSCLE_NAME_MAX)
        assert len(m.name) == MUSCLE_NAME_MAX

    def test_exercise_create_admin_over_40_rejected(self):
        """ExerciseCreate (admin, by id).name cap at 40 is unchanged."""
        with pytest.raises(ValidationError) as exc_info:
            ExerciseCreate(name="A" * (EXERCISE_NAME_MAX + 1), muscle=1)
        errors = exc_info.value.errors()
        assert any(e["loc"] == ("name",) for e in errors)


# ---------------------------------------------------------------------------
# TrainingCreate — lookup fields work with long/odd names (pre-existing rows)
# ---------------------------------------------------------------------------

class TestTrainingCreateLookup:
    def test_long_muscle_name_accepted(self):
        """TrainingCreate.muscle_name >30 chars is accepted (lookup rule)."""
        t = TrainingCreate(
            muscle_name="A" * (MUSCLE_NAME_MAX + 5),  # 35 chars
            exercise_name="Bench Press",
            set=1, weight=100.0, reps=10.0,
        )
        assert len(t.muscle_name) == MUSCLE_NAME_MAX + 5

    def test_long_exercise_name_accepted(self):
        """TrainingCreate.exercise_name >40 chars is accepted (lookup rule)."""
        t = TrainingCreate(
            muscle_name="Chest",
            exercise_name="B" * (EXERCISE_NAME_MAX + 5),  # 45 chars
            set=1, weight=100.0, reps=10.0,
        )
        assert len(t.exercise_name) == EXERCISE_NAME_MAX + 5

    def test_empty_muscle_name_rejected(self):
        with pytest.raises(ValidationError) as exc_info:
            TrainingCreate(
                muscle_name="", exercise_name="Bench Press",
                set=1, weight=100.0, reps=10.0,
            )
        errors = exc_info.value.errors()
        assert any(e["loc"] == ("muscle_name",) for e in errors)

    def test_whitespace_only_exercise_name_rejected(self):
        with pytest.raises(ValidationError) as exc_info:
            TrainingCreate(
                muscle_name="Chest", exercise_name="   ",
                set=1, weight=100.0, reps=10.0,
            )
        errors = exc_info.value.errors()
        assert any(e["loc"] == ("exercise_name",) for e in errors)

    def test_normalization_still_applied(self):
        t = TrainingCreate(
            muscle_name="  Upper  Chest  ", exercise_name="  Bench  Press  ",
            set=1, weight=100.0, reps=10.0,
        )
        assert t.muscle_name == "Upper Chest"
        assert t.exercise_name == "Bench Press"
