"""Set-saved confirmation message building (GYM-137).

Split out of handlers.py (which is over the size limit per CLAUDE.md):
the result table, the weight-format normalizer it needs, and the
last-session delta note fetched from `GET /analytics/log-context`.
"""

from __future__ import annotations

from datetime import datetime

import prettytable as pt

from modules.api import api
from modules.delta import delta_note_for_set
from modules.logging import Logger

logger = Logger(name="confirmation")


def normalize_weight_format(weight_str: str) -> str:
    """Convert comma decimal separator to dot for numeric parsing.

    Args:
        weight_str: Weight value as string, e.g. "2,5" or "2.5".

    Returns:
        Weight value with dot decimal format, e.g. "2.5".
    """
    return weight_str.replace(",", ".") if "," in weight_str else weight_str


def format_result_message(data: dict) -> str:
    """Format a single training record as an HTML-wrapped PrettyTable.

    Args:
        data: Keys: muscle, exercise, set, weight, reps.

    Returns:
        HTML <pre>-wrapped table string.
    """
    table = pt.PrettyTable(["Name", "Details"])
    table.align = "l"
    table.add_row(["Muscle", data["muscle"]])
    table.add_row(["Exercise", data["exercise"]])
    table.add_row(["Set", data["set"]])
    table.add_row(["Weight", f"{data['weight']}kg"])
    table.add_row(["Reps", data["reps"]])
    table.add_row(["Recorded at", datetime.now().strftime("%d-%m-%Y %H:%M:%S")])
    return f"<pre>{table}</pre>"


async def fetch_save_delta_note(
    user_id: int,
    muscle: str,
    exercise: str,
    set_number: int,
    weight: float,
    reps: float,
) -> str:
    """Fetch last-session context and build the save-confirmation delta note.

    GYM-137: one `GET /analytics/log-context` read (service-token +
    X-Act-As-User, same client path as every other analytics call) gives
    `last_session_sets`; the delta vs the same set number is rendered by
    the pure helper in modules.delta.

    Failure-safe: ANY error returns "" so the save confirmation is never
    blocked or broken by the analytics read.

    Args:
        user_id: Telegram user id of the saver.
        muscle: Muscle group name.
        exercise: Exercise name.
        set_number: Set number that was just saved.
        weight: Just-saved weight (kg).
        reps: Just-saved reps.

    Returns:
        "(▲ +2.5kg vs last session)"-style note, or "" when there is no
        matching last-session set or the context read fails.
    """
    try:
        ctx = await api.get_log_context(
            muscle=muscle,
            exercise=exercise,
            date=datetime.utcnow().date().isoformat(),
            act_as_user=user_id,
        )
        return delta_note_for_set(ctx.last_session_sets, set_number, weight, reps)
    except Exception as exc:  # noqa: BLE001 — never break the save UX
        logger.warning(f"{user_id}: log-context unavailable, skipping delta: {exc}")
        return ""


async def build_save_confirmation(
    user_id: int,
    muscle_name: str,
    exercise_name: str,
    set_number: str,
    weight_value: str,
    reps_value: str,
) -> str:
    """Build the set-saved confirmation text, with the GYM-137 delta note.

    Args:
        user_id: Telegram user id of the saver.
        muscle_name: Muscle group name.
        exercise_name: Exercise name.
        set_number: Set number as the FSM string value.
        weight_value: Weight as the FSM string value (comma or dot decimals).
        reps_value: Reps as the FSM string value.

    Returns:
        HTML confirmation message; the delta line is appended only when a
        matching last-session set exists and the context read succeeds.
    """
    message = format_result_message({
        "muscle": muscle_name,
        "exercise": exercise_name,
        "set": set_number,
        "weight": weight_value,
        "reps": reps_value,
    })
    note = await fetch_save_delta_note(
        user_id,
        muscle_name,
        exercise_name,
        int(set_number),
        float(normalize_weight_format(weight_value)),
        float(reps_value),
    )
    return f"{message}\n{note}" if note else message
