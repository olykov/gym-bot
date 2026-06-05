"""GYM-76: Unit tests for the reusable name validator and schema integration.

Tests cover:
  - normalize_name: trim and internal-whitespace-collapse behaviour.
  - validate_name: length boundaries (min 1, muscle max 30, exercise max 40),
    disallowed characters, Cyrillic acceptance.
  - Schema integration: MuscleCreate, ExerciseCreate (admin), ExerciseCreateByName,
    TrainingCreate — each path exercised with valid and invalid inputs.

These are pure unit tests; no DB or Docker container is required.
"""
import pytest
from pydantic import ValidationError

from app.schemas.validators import (
    EXERCISE_NAME_MAX,
    MUSCLE_NAME_MAX,
    normalize_name,
    validate_name,
)
from app.schemas.schemas import (
    ExerciseCreate,
    ExerciseCreateByName,
    MuscleCreate,
    TrainingCreate,
)


# ---------------------------------------------------------------------------
# normalize_name
# ---------------------------------------------------------------------------

class TestNormalizeName:
    def test_trims_leading_whitespace(self):
        assert normalize_name("  Biceps") == "Biceps"

    def test_trims_trailing_whitespace(self):
        assert normalize_name("Biceps  ") == "Biceps"

    def test_collapses_internal_spaces(self):
        assert normalize_name("Bench   Press") == "Bench Press"

    def test_collapses_tabs_and_newlines(self):
        assert normalize_name("Bench\t\nPress") == "Bench Press"

    def test_whitespace_only_returns_empty(self):
        assert normalize_name("   ") == ""

    def test_already_clean_unchanged(self):
        assert normalize_name("Clean Name") == "Clean Name"

    def test_mixed_internal_and_edges(self):
        assert normalize_name("  Push  Up  ") == "Push Up"


# ---------------------------------------------------------------------------
# validate_name — core logic
# ---------------------------------------------------------------------------

class TestValidateName:
    # --- empty / whitespace-only ---

    def test_empty_string_rejected(self):
        with pytest.raises(ValueError, match="empty"):
            validate_name("", max_len=30)

    def test_whitespace_only_rejected(self):
        with pytest.raises(ValueError, match="empty"):
            validate_name("   ", max_len=30)

    # --- length bounds (muscle = 30) ---

    def test_exactly_max_muscle_accepted(self):
        name = "A" * MUSCLE_NAME_MAX          # 30 chars — exactly at limit
        result = validate_name(name, max_len=MUSCLE_NAME_MAX)
        assert result == name

    def test_max_plus_one_muscle_rejected(self):
        name = "A" * (MUSCLE_NAME_MAX + 1)    # 31 chars — one over
        with pytest.raises(ValueError, match="at most 30"):
            validate_name(name, max_len=MUSCLE_NAME_MAX)

    # --- length bounds (exercise = 40) ---

    def test_exactly_max_exercise_accepted(self):
        name = "B" * EXERCISE_NAME_MAX         # 40 chars — exactly at limit
        result = validate_name(name, max_len=EXERCISE_NAME_MAX)
        assert result == name

    def test_max_plus_one_exercise_rejected(self):
        name = "B" * (EXERCISE_NAME_MAX + 1)  # 41 chars — one over
        with pytest.raises(ValueError, match="at most 40"):
            validate_name(name, max_len=EXERCISE_NAME_MAX)

    # --- disallowed characters ---

    def test_emoji_rejected(self):
        with pytest.raises(ValueError, match="disallowed"):
            validate_name("Bench Press 💪", max_len=40)

    def test_less_than_sign_rejected(self):
        with pytest.raises(ValueError, match="disallowed"):
            validate_name("Bench<Press", max_len=40)

    def test_curly_brace_rejected(self):
        with pytest.raises(ValueError, match="disallowed"):
            validate_name("Name{test}", max_len=40)

    def test_control_char_rejected(self):
        with pytest.raises(ValueError, match="disallowed"):
            validate_name("Name\x00", max_len=40)

    def test_pipe_rejected(self):
        with pytest.raises(ValueError, match="disallowed"):
            validate_name("Name|Other", max_len=40)

    def test_hash_rejected(self):
        with pytest.raises(ValueError, match="disallowed"):
            validate_name("#Tag", max_len=40)

    # --- Cyrillic accepted ---

    def test_cyrillic_muscle_accepted(self):
        result = validate_name("Бицепс", max_len=MUSCLE_NAME_MAX)
        assert result == "Бицепс"

    def test_cyrillic_exercise_accepted(self):
        result = validate_name("Жим лёжа", max_len=EXERCISE_NAME_MAX)
        assert result == "Жим лёжа"

    def test_cyrillic_yo_and_yo_lower_accepted(self):
        result = validate_name("Жим Ёжа ёмкость", max_len=EXERCISE_NAME_MAX)
        assert result == "Жим Ёжа ёмкость"

    # --- Latin with allowed punctuation accepted ---

    def test_latin_with_punctuation_accepted(self):
        result = validate_name("Smith & Wesson (45°)", max_len=EXERCISE_NAME_MAX)
        assert result == "Smith & Wesson (45°)"

    def test_hyphen_apostrophe_accepted(self):
        result = validate_name("Leg-Press / D'Bell", max_len=EXERCISE_NAME_MAX)
        assert result == "Leg-Press / D'Bell"

    # --- normalization is returned ---

    def test_normalized_value_returned(self):
        result = validate_name("  Push   Up  ", max_len=EXERCISE_NAME_MAX)
        assert result == "Push Up"


# ---------------------------------------------------------------------------
# Schema integration: MuscleCreate
# ---------------------------------------------------------------------------

class TestMuscleCreateSchema:
    def test_valid_name_accepted(self):
        m = MuscleCreate(name="Chest")
        assert m.name == "Chest"

    def test_leading_trailing_whitespace_normalized(self):
        m = MuscleCreate(name="  Chest  ")
        assert m.name == "Chest"

    def test_internal_whitespace_collapsed(self):
        m = MuscleCreate(name="Upper  Chest")
        assert m.name == "Upper Chest"

    def test_cyrillic_accepted(self):
        m = MuscleCreate(name="Бицепс")
        assert m.name == "Бицепс"

    def test_empty_name_rejected_422(self):
        with pytest.raises(ValidationError) as exc_info:
            MuscleCreate(name="")
        errors = exc_info.value.errors()
        assert any(e["loc"] == ("name",) for e in errors)

    def test_whitespace_only_rejected_422(self):
        with pytest.raises(ValidationError) as exc_info:
            MuscleCreate(name="   ")
        errors = exc_info.value.errors()
        assert any(e["loc"] == ("name",) for e in errors)

    def test_over_max_length_rejected_422(self):
        with pytest.raises(ValidationError) as exc_info:
            MuscleCreate(name="A" * (MUSCLE_NAME_MAX + 1))
        errors = exc_info.value.errors()
        assert any(e["loc"] == ("name",) for e in errors)

    def test_exactly_max_length_accepted(self):
        m = MuscleCreate(name="A" * MUSCLE_NAME_MAX)
        assert len(m.name) == MUSCLE_NAME_MAX

    def test_disallowed_char_rejected_422(self):
        with pytest.raises(ValidationError) as exc_info:
            MuscleCreate(name="Chest<Muscle")
        errors = exc_info.value.errors()
        assert any(e["loc"] == ("name",) for e in errors)

    def test_emoji_rejected_422(self):
        with pytest.raises(ValidationError) as exc_info:
            MuscleCreate(name="Bicep 💪")
        errors = exc_info.value.errors()
        assert any(e["loc"] == ("name",) for e in errors)


# ---------------------------------------------------------------------------
# Schema integration: ExerciseCreate (admin — muscle by id)
# ---------------------------------------------------------------------------

class TestExerciseCreateSchema:
    def test_valid_name_accepted(self):
        e = ExerciseCreate(name="Bench Press", muscle=1)
        assert e.name == "Bench Press"

    def test_normalization_applied(self):
        e = ExerciseCreate(name="  Bench  Press  ", muscle=1)
        assert e.name == "Bench Press"

    def test_cyrillic_accepted(self):
        e = ExerciseCreate(name="Жим лёжа", muscle=1)
        assert e.name == "Жим лёжа"

    def test_empty_name_rejected_422(self):
        with pytest.raises(ValidationError) as exc_info:
            ExerciseCreate(name="", muscle=1)
        errors = exc_info.value.errors()
        assert any(e["loc"] == ("name",) for e in errors)

    def test_over_max_length_rejected_422(self):
        with pytest.raises(ValidationError) as exc_info:
            ExerciseCreate(name="A" * (EXERCISE_NAME_MAX + 1), muscle=1)
        errors = exc_info.value.errors()
        assert any(e["loc"] == ("name",) for e in errors)

    def test_exactly_max_length_accepted(self):
        e = ExerciseCreate(name="A" * EXERCISE_NAME_MAX, muscle=1)
        assert len(e.name) == EXERCISE_NAME_MAX

    def test_disallowed_char_rejected_422(self):
        with pytest.raises(ValidationError) as exc_info:
            ExerciseCreate(name="Bench|Press", muscle=1)
        errors = exc_info.value.errors()
        assert any(e["loc"] == ("name",) for e in errors)

    def test_emoji_rejected_422(self):
        with pytest.raises(ValidationError) as exc_info:
            ExerciseCreate(name="Curl 💪", muscle=1)
        errors = exc_info.value.errors()
        assert any(e["loc"] == ("name",) for e in errors)


# ---------------------------------------------------------------------------
# Schema integration: ExerciseCreateByName (user-facing — both fields)
# ---------------------------------------------------------------------------

class TestExerciseCreateByNameSchema:
    def test_valid_both_fields(self):
        e = ExerciseCreateByName(name="Bench Press", muscle_name="Chest")
        assert e.name == "Bench Press"
        assert e.muscle_name == "Chest"

    def test_normalization_both_fields(self):
        e = ExerciseCreateByName(name="  Bench  Press  ", muscle_name="  Upper  Chest  ")
        assert e.name == "Bench Press"
        assert e.muscle_name == "Upper Chest"

    def test_cyrillic_both_fields(self):
        e = ExerciseCreateByName(name="Жим лёжа", muscle_name="Грудь")
        assert e.name == "Жим лёжа"
        assert e.muscle_name == "Грудь"

    def test_empty_exercise_name_rejected(self):
        with pytest.raises(ValidationError) as exc_info:
            ExerciseCreateByName(name="", muscle_name="Chest")
        errors = exc_info.value.errors()
        assert any(e["loc"] == ("name",) for e in errors)

    def test_empty_muscle_name_rejected(self):
        with pytest.raises(ValidationError) as exc_info:
            ExerciseCreateByName(name="Bench Press", muscle_name="")
        errors = exc_info.value.errors()
        assert any(e["loc"] == ("muscle_name",) for e in errors)

    def test_exercise_name_over_max_rejected(self):
        with pytest.raises(ValidationError) as exc_info:
            ExerciseCreateByName(name="A" * (EXERCISE_NAME_MAX + 1), muscle_name="Chest")
        errors = exc_info.value.errors()
        assert any(e["loc"] == ("name",) for e in errors)

    def test_muscle_name_over_max_rejected(self):
        with pytest.raises(ValidationError) as exc_info:
            ExerciseCreateByName(name="Bench Press", muscle_name="A" * (MUSCLE_NAME_MAX + 1))
        errors = exc_info.value.errors()
        assert any(e["loc"] == ("muscle_name",) for e in errors)

    def test_exercise_name_exactly_max_accepted(self):
        e = ExerciseCreateByName(name="A" * EXERCISE_NAME_MAX, muscle_name="Chest")
        assert len(e.name) == EXERCISE_NAME_MAX

    def test_muscle_name_exactly_max_accepted(self):
        e = ExerciseCreateByName(name="Bench Press", muscle_name="A" * MUSCLE_NAME_MAX)
        assert len(e.muscle_name) == MUSCLE_NAME_MAX

    def test_disallowed_char_in_exercise_rejected(self):
        with pytest.raises(ValidationError) as exc_info:
            ExerciseCreateByName(name="Bench#Press", muscle_name="Chest")
        errors = exc_info.value.errors()
        assert any(e["loc"] == ("name",) for e in errors)

    def test_disallowed_char_in_muscle_rejected(self):
        with pytest.raises(ValidationError) as exc_info:
            ExerciseCreateByName(name="Bench Press", muscle_name="Ch<est")
        errors = exc_info.value.errors()
        assert any(e["loc"] == ("muscle_name",) for e in errors)

    def test_emoji_in_exercise_rejected(self):
        with pytest.raises(ValidationError) as exc_info:
            ExerciseCreateByName(name="Curl 🏋️", muscle_name="Biceps")
        errors = exc_info.value.errors()
        assert any(e["loc"] == ("name",) for e in errors)


# ---------------------------------------------------------------------------
# Schema integration: TrainingCreate
# (lookup-only path: normalize + char-check, no max_len enforcement)
# ---------------------------------------------------------------------------

class TestTrainingCreateSchema:
    def test_valid_fields_accepted(self):
        t = TrainingCreate(
            muscle_name="Chest", exercise_name="Bench Press",
            set=1, weight=100.0, reps=10.0,
        )
        assert t.muscle_name == "Chest"
        assert t.exercise_name == "Bench Press"

    def test_normalization_applied_to_both(self):
        t = TrainingCreate(
            muscle_name="  Upper  Chest  ", exercise_name="  Bench  Press  ",
            set=1, weight=100.0, reps=10.0,
        )
        assert t.muscle_name == "Upper Chest"
        assert t.exercise_name == "Bench Press"

    def test_cyrillic_accepted(self):
        t = TrainingCreate(
            muscle_name="Грудь", exercise_name="Жим лёжа",
            set=1, weight=80.0, reps=8.0,
        )
        assert t.muscle_name == "Грудь"
        assert t.exercise_name == "Жим лёжа"

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

    def test_disallowed_char_in_muscle_name_rejected(self):
        with pytest.raises(ValidationError) as exc_info:
            TrainingCreate(
                muscle_name="Chest<>", exercise_name="Bench Press",
                set=1, weight=100.0, reps=10.0,
            )
        errors = exc_info.value.errors()
        assert any(e["loc"] == ("muscle_name",) for e in errors)

    def test_emoji_in_exercise_name_rejected(self):
        with pytest.raises(ValidationError) as exc_info:
            TrainingCreate(
                muscle_name="Chest", exercise_name="Bench 💪",
                set=1, weight=100.0, reps=10.0,
            )
        errors = exc_info.value.errors()
        assert any(e["loc"] == ("exercise_name",) for e in errors)

    def test_long_name_over_40_accepted_for_lookup(self):
        """Names exceeding the exercise max are allowed here (lookup-only path).

        TrainingCreate only resolves existing rows by name; it never creates
        new muscles or exercises, so rejecting names > 40 chars would break
        lookups for names that existed before GYM-76 validation was enforced.
        """
        long_name = "A" * (EXERCISE_NAME_MAX + 1)  # 41 chars
        t = TrainingCreate(
            muscle_name="Chest", exercise_name=long_name,
            set=1, weight=100.0, reps=10.0,
        )
        assert t.exercise_name == long_name
