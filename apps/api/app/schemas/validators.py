"""Reusable name validators for muscle and exercise names.

Canonical rules are defined in docs/validation.md (GYM-75) — this module is
the single server-side enforcement point.  The regex character class is kept
byte-for-byte identical to the ``pattern`` in packages/api-contract/openapi.yaml
so the API and the contract never diverge.

Two distinct validation strategies are provided:

- ``validate_name``: full validation for a name being **CREATED/STORED** — enforces
  normalization, max-length cap, and the allowed-character whitelist.
- ``validate_lookup_name``: lightweight validation for a name used only to **LOOK UP**
  an existing record — enforces normalization and rejects empty/whitespace-only input,
  but imposes NO max-length cap and NO character-whitelist check.

The create-vs-lookup distinction is fundamental: length and char limits only make sense
for data being stored.  A lookup field must always be able to reference records that
predate the current validation rules (e.g. a muscle whose name is 35 chars, created
before the 30-char cap was introduced).  Lookups are safe without those caps because
they use parameterised SQL and return 404 on no match rather than touching the DB.

Usage::

    from app.schemas.validators import validate_name, validate_lookup_name, MUSCLE_NAME_MAX

    # For a field being stored (CREATE path):
    class MuscleCreate(BaseModel):
        name: str

        @field_validator("name", mode="before")
        @classmethod
        def _validate_name(cls, v: object) -> str:
            return validate_name(str(v), max_len=MUSCLE_NAME_MAX)

    # For a field referencing an existing record (LOOKUP path):
    class ExerciseCreateByName(BaseModel):
        muscle_name: str

        @field_validator("muscle_name", mode="before")
        @classmethod
        def _validate_muscle_name(cls, v: object) -> str:
            return validate_lookup_name(str(v))
"""
import re

# ---------------------------------------------------------------------------
# Length limits — sourced from docs/validation.md
# ---------------------------------------------------------------------------

MUSCLE_NAME_MAX: int = 30
EXERCISE_NAME_MAX: int = 40

# ---------------------------------------------------------------------------
# Allowed-character pattern
#
# Explicit Unicode ranges instead of \p{L}/\p{N} because plain Python ``re``
# does not support Unicode property escapes, and we need the pattern to match
# the contract's ``pattern`` field exactly (which also uses explicit ranges).
#
# Breakdown:
#   A-Za-z           — ASCII Latin letters
#   0-9              — ASCII digits
#   À-ÖØ-öø-ÿ       — Latin-1 Supplement letters (excludes × U+00D7 and ÷ U+00F7)
#   А-яЁё            — Cyrillic letters (А-я = U+0410-044F, Ё = U+0401, ё = U+0451)
#   (space)          — single ASCII space (after normalization)
#   \-               — hyphen (literal, escaped at start of class)
#   '                — apostrophe
#   .                — full stop
#   ,                — comma
#   (  )             — parentheses
#   /                — slash
#   &                — ampersand
#   +                — plus
#   °                — degree sign (U+00B0)
# ---------------------------------------------------------------------------

_NAME_RE: re.Pattern[str] = re.compile(
    r"^[A-Za-z0-9À-ÖØ-öø-ÿА-яЁё \-'.,()/&+°]+$"
)


def normalize_name(s: str) -> str:
    """Trim leading/trailing whitespace and collapse internal runs to one space.

    This is the normalization step that MUST run before any length or
    character-set check.  The normalized value is what gets stored.

    Args:
        s: Raw user-supplied string.

    Returns:
        Normalized string with leading/trailing whitespace removed and internal
        whitespace runs collapsed to a single ASCII space.
    """
    return " ".join(s.split())


def validate_name(s: str, *, max_len: int) -> str:
    """Normalize and validate a muscle or exercise name.

    Runs normalization first, then enforces:
    1. Non-empty (whitespace-only → rejected).
    2. Length ≤ max_len after normalization.
    3. Allowed-character set (see module docstring / docs/validation.md).

    Raises ``ValueError`` with a descriptive message on any violation so
    Pydantic surfaces a 422 response with the field name.

    Args:
        s: Raw user-supplied string (will be normalized internally).
        max_len: Maximum allowed length after normalization.

    Returns:
        The normalized, valid name ready to be stored.

    Raises:
        ValueError: If the name is empty/whitespace-only, exceeds max_len,
            or contains disallowed characters.
    """
    normalized = normalize_name(s)

    if not normalized:
        raise ValueError("name must not be empty or whitespace-only")

    if len(normalized) > max_len:
        raise ValueError(
            f"name must be at most {max_len} characters after normalization "
            f"(got {len(normalized)})"
        )

    if not _NAME_RE.match(normalized):
        raise ValueError(
            "name contains disallowed characters; allowed: Latin letters, "
            "Cyrillic letters, digits, space, and - ' . , ( ) / & + °"
        )

    return normalized


def validate_lookup_name(s: str) -> str:
    """Normalize a name used only to look up an existing record.

    This is the lightweight counterpart to ``validate_name`` and is intentionally
    less strict.  It applies only normalization (trim + collapse) and rejects
    empty/whitespace-only input.  It does **not** enforce a max-length cap or the
    allowed-character whitelist.

    Rationale (create-vs-lookup distinction):
        Length and character constraints belong on data being **created/stored**.
        A lookup field must always be able to reference records that predate the
        current validation rules — for example a muscle whose name is 35 chars,
        created before the 30-char cap was introduced.  Forbidding such a name at
        the lookup layer would make those records permanently unreachable.
        Lookups are safe without the extra caps because they use parameterised SQL
        and return 404 on no match rather than writing anything to the DB.

    Args:
        s: Raw user-supplied string (will be normalized internally).

    Returns:
        The normalized name (leading/trailing whitespace stripped, internal
        whitespace collapsed to a single space).

    Raises:
        ValueError: If the name is empty or whitespace-only after normalization.
    """
    normalized = normalize_name(s)
    if not normalized:
        raise ValueError("name must not be empty or whitespace-only")
    return normalized
