"""Pure delta helpers for the set-saved confirmation message (GYM-137).

Mirrors the LOCKED GYM-130 delta rule from apps/web ``derive.computeDelta``:
weight is compared first; reps only break a weight tie. The ▲/▼ glyphs and
the kg/rep wording mirror the web app's delta strings (the bot's UI language
is English, matching every other bot message).
"""

from __future__ import annotations

from gym_api_client import models as api_models


def _fmt_amount(amount: float) -> str:
    """Format a delta amount without trailing zeros.

    Args:
        amount: Positive delta amount (weight in kg or rep count).

    Returns:
        "2.5" for 2.5, "2" for 2.0.
    """
    return f"{amount:g}"


def compute_delta_text(
    weight: float,
    reps: float,
    last_weight: float,
    last_reps: float,
) -> str:
    """Render the delta vs the same set of the last session as text.

    LOCKED rule (GYM-130, mirrors apps/web ``derive.computeDelta``): weight
    is compared first; reps are only the tiebreaker at equal weight.

    Args:
        weight: Just-saved set weight (kg).
        reps: Just-saved set reps.
        last_weight: Same-numbered set's weight in the last session.
        last_reps: Same-numbered set's reps in the last session.

    Returns:
        One of "▲ +2.5kg vs last session", "▼ −2.5kg vs last session",
        "▲ +2 reps vs last session", "▼ −1 rep vs last session",
        "= same as last session".
    """
    if weight > last_weight:
        return f"▲ +{_fmt_amount(weight - last_weight)}kg vs last session"
    if weight < last_weight:
        return f"▼ −{_fmt_amount(last_weight - weight)}kg vs last session"
    if reps > last_reps:
        amount = reps - last_reps
        unit = "rep" if amount == 1 else "reps"
        return f"▲ +{_fmt_amount(amount)} {unit} vs last session"
    if reps < last_reps:
        amount = last_reps - reps
        unit = "rep" if amount == 1 else "reps"
        return f"▼ −{_fmt_amount(amount)} {unit} vs last session"
    return "= same as last session"


def delta_note_for_set(
    last_session_sets: list[api_models.LogSet],
    set_number: int,
    weight: float,
    reps: float,
) -> str:
    """Build the parenthesised confirmation suffix for a just-saved set.

    Compares against the SAME set number in the last session
    (``log-context.last_session_sets``). When the last session has no set
    with that number there is nothing to beat, so no note is produced —
    honest, never fabricated.

    Args:
        last_session_sets: ``LogContext.last_session_sets`` from the API.
        set_number: Set number that was just saved.
        weight: Just-saved weight (kg).
        reps: Just-saved reps.

    Returns:
        "(▲ +2.5kg vs last session)"-style text, or "" when there is no
        matching last-session set.
    """
    last = next((s for s in last_session_sets if s.set == set_number), None)
    if last is None:
        return ""
    return f"({compute_delta_text(weight, reps, last.weight, last.reps)})"
