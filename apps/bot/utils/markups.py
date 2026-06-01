"""Inline keyboard markup builders for the Gym Tracker bot.

Functions that read remote data are async; purely static builders stay sync.
All callback_data prefixes are unchanged for FSM stability.
"""

from __future__ import annotations

import os
from datetime import datetime

import httpx
from aiogram.enums import ButtonStyle
from aiogram.types import InlineKeyboardButton, InlineKeyboardMarkup, WebAppInfo

from gym_api_client import GymApiClient, models
from modules.api import api
from modules.logging import Logger
from templates.exercise import reps, sets, weights

logger = Logger(name="markups")


# ---------------------------------------------------------------------------
# Internal helpers
# ---------------------------------------------------------------------------

async def _find_muscle_id(muscle_name: str, user_id: int) -> int | None:
    """Return the id for a named muscle visible to *user_id*, or None."""
    try:
        muscles = await api.list_muscles(act_as_user=user_id)
        for m in muscles:
            if m.name == muscle_name:
                return m.id
    except httpx.HTTPError as exc:
        logger.error(f"API error looking up muscle '{muscle_name}': {exc}")
    return None


async def _find_exercise_id(
    muscle_name: str, exercise_name: str, user_id: int
) -> int | None:
    """Return the id for a named exercise under *muscle_name* visible to *user_id*."""
    muscle_id = await _find_muscle_id(muscle_name, user_id)
    if muscle_id is None:
        return None
    try:
        exercises = await api.list_exercises_by_muscle(muscle_id, act_as_user=user_id)
        for e in exercises:
            if e.name == exercise_name:
                return e.id
    except httpx.HTTPError as exc:
        logger.error(
            f"API error looking up exercise '{exercise_name}' for muscle id {muscle_id}: {exc}"
        )
    return None


def _is_peak(button_value: object, target: object) -> bool:
    """Return True when *button_value* numerically equals *target*.

    Compares as floats so "5" matches 5.0.  Returns False on None or
    non-numeric input.
    """
    if target is None:
        return False
    try:
        return float(button_value) == float(target)  # type: ignore[arg-type]
    except (TypeError, ValueError):
        return False


# ---------------------------------------------------------------------------
# Static markup builders (no I/O)
# ---------------------------------------------------------------------------

def generate_start_markup() -> InlineKeyboardMarkup:
    web_app_url = os.environ.get("WEB_APP_URL")
    if not web_app_url:
        logger.error("WEB_APP_URL not set in environment variables")
        web_app_url = "https://google.com"
    elif not web_app_url.startswith("https://"):
        web_app_url = f"https://{web_app_url}"

    return InlineKeyboardMarkup(
        inline_keyboard=[[
            InlineKeyboardButton(
                text="Record training",
                callback_data="/gym",
                style=ButtonStyle.SUCCESS,
            ),
            InlineKeyboardButton(
                text="Edit trainings",
                web_app=WebAppInfo(url=web_app_url),
            ),
        ]]
    )


def generate_edit_markup() -> InlineKeyboardMarkup:
    return InlineKeyboardMarkup(
        inline_keyboard=[[
            InlineKeyboardButton(
                text="Edit today's training",
                callback_data="edit_today_training",
                style=ButtonStyle.PRIMARY,
            ),
            InlineKeyboardButton(text="Close", callback_data="/start"),
        ]]
    )


# ---------------------------------------------------------------------------
# Async markup builders (read remote data)
# ---------------------------------------------------------------------------

async def generate_muscle_markup(user_id: int | None = None) -> InlineKeyboardMarkup:
    """Build the muscle-selection keyboard."""
    inline_keyboard: list[list[InlineKeyboardButton]] = []
    btn_row: list[InlineKeyboardButton] = []

    try:
        muscles = await api.list_muscles(act_as_user=user_id)
        muscle_names = [m.name for m in muscles]
    except httpx.HTTPError as exc:
        logger.error(f"API error fetching muscles for user {user_id}: {exc}")
        muscle_names = []

    for muscle in muscle_names:
        btn_row.append(
            InlineKeyboardButton(text=muscle, callback_data=f"mus_{muscle}")
        )
        if len(btn_row) == 3:
            inline_keyboard.append(btn_row)
            btn_row = []

    if btn_row:
        inline_keyboard.append(btn_row)

    inline_keyboard.append(
        [InlineKeyboardButton(text="➕ Add Muscle", callback_data="add_muscle_btn")]
    )
    inline_keyboard.append(
        [InlineKeyboardButton(text="⬅️ Go back", callback_data="/start")]
    )

    return InlineKeyboardMarkup(inline_keyboard=inline_keyboard)


async def generate_post_set_markup(
    user_id: int,
    muscle_name: str,
    exercise_name: str,
    current_date: str | None = None,
) -> InlineKeyboardMarkup:
    """Build the post-set keyboard: continue same exercise, or pick a new one."""
    if current_date is None:
        current_date = datetime.now().strftime("%Y-%m-%d")

    try:
        result = await api.get_completed_sets(
            muscle=muscle_name,
            exercise=exercise_name,
            date=current_date,
            act_as_user=user_id,
        )
        completed_sets = result.sets
        total_sets = len(sets)

        if len(completed_sets) < total_sets:
            return InlineKeyboardMarkup(
                inline_keyboard=[
                    [
                        InlineKeyboardButton(
                            text=f"Continue {exercise_name}",
                            callback_data=f"continue_ex||{muscle_name}||{exercise_name}",
                            style=ButtonStyle.SUCCESS,
                        )
                    ],
                    [
                        InlineKeyboardButton(
                            text="New Exercise",
                            callback_data="back_to_muscles",
                        )
                    ],
                ]
            )
        # All sets done — fall through to muscle list
    except httpx.HTTPError as exc:
        logger.error(f"API error fetching completed sets for user {user_id}: {exc}")

    return await generate_muscle_markup(user_id)


async def _build_exercise_buttons(
    exercises_to_show: list[str],
) -> list[list[InlineKeyboardButton]]:
    rows: list[list[InlineKeyboardButton]] = []
    btn_row: list[InlineKeyboardButton] = []
    for ex in exercises_to_show:
        btn_row.append(
            InlineKeyboardButton(text=ex, callback_data=f"ex_{ex}")
        )
        if len(btn_row) == 1:
            rows.append(btn_row)
            btn_row = []
    if btn_row:
        rows.append(btn_row)
    return rows


async def generate_exercise_markup(
    selected_muscle: str,
    user_id: int | None = None,
    show_all: bool = False,
) -> InlineKeyboardMarkup:
    """Build the exercise-selection keyboard (compact or full)."""
    # Resolve muscle id from name
    muscle_id: int | None = None
    if user_id:
        muscle_id = await _find_muscle_id(selected_muscle, user_id)

    all_exercises: list[str] = []
    if muscle_id is not None:
        try:
            raw = await api.list_exercises_by_muscle(muscle_id, act_as_user=user_id)
            all_exercises = [e.name for e in raw]
        except httpx.HTTPError as exc:
            logger.error(
                f"API error fetching exercises for muscle '{selected_muscle}': {exc}"
            )

    # Determine display list
    if show_all:
        exercises_to_show = await _prioritized_exercises(
            all_exercises, selected_muscle, user_id
        )
        bottom_buttons = [
            InlineKeyboardButton(text="⬅️ Go back", callback_data="back_to_muscles")
        ]
    else:
        top_items = await _get_top_exercise_names(selected_muscle, user_id)
        if top_items:
            exercises_to_show = sorted(top_items)
            bottom_buttons = [
                InlineKeyboardButton(
                    text="Show All",
                    callback_data=f"show_all_exercises_{selected_muscle}",
                ),
                InlineKeyboardButton(
                    text="⬅️ Go back", callback_data="back_to_muscles"
                ),
            ]
        else:
            exercises_to_show = all_exercises
            bottom_buttons = [
                InlineKeyboardButton(text="⬅️ Go back", callback_data="back_to_muscles")
            ]

    inline_keyboard = await _build_exercise_buttons(exercises_to_show)

    inline_keyboard.append([
        InlineKeyboardButton(text="➕ Add Exercise", callback_data="add_exercise_btn"),
        InlineKeyboardButton(
            text="❌ Delete Exercise",
            callback_data="delete_exercise_btn",
            style=ButtonStyle.DANGER,
        ),
    ])
    inline_keyboard.append(bottom_buttons)

    return InlineKeyboardMarkup(inline_keyboard=inline_keyboard)


async def _get_top_exercise_names(
    muscle_name: str, user_id: int | None
) -> list[str]:
    """Return up to 5 top exercise names for the user, empty list on error/no data."""
    if not user_id:
        return []
    try:
        top = await api.get_top_exercises(
            muscle=muscle_name, limit=5, act_as_user=user_id
        )
        return [t.name for t in top]
    except httpx.HTTPError as exc:
        logger.error(
            f"API error fetching top exercises for muscle '{muscle_name}': {exc}"
        )
        return []


async def _prioritized_exercises(
    all_exercises: list[str],
    muscle_name: str,
    user_id: int | None,
) -> list[str]:
    """Return exercises sorted: top ones alphabetically first, then the rest."""
    if user_id and all_exercises:
        top_names = await _get_top_exercise_names(muscle_name, user_id)
        top_set = set(top_names)
        top_sorted = sorted(top_names)
        remaining = [ex for ex in all_exercises if ex not in top_set]
        return top_sorted + remaining
    return all_exercises


async def generate_delete_exercise_markup(
    selected_muscle: str, user_id: int | None = None
) -> InlineKeyboardMarkup:
    """Build the exercise-deletion keyboard."""
    inline_keyboard: list[list[InlineKeyboardButton]] = []
    btn_row: list[InlineKeyboardButton] = []

    muscle_id: int | None = None
    if user_id:
        muscle_id = await _find_muscle_id(selected_muscle, user_id)

    all_exercises: list[str] = []
    if muscle_id is not None:
        try:
            raw = await api.list_exercises_by_muscle(muscle_id, act_as_user=user_id)
            all_exercises = [e.name for e in raw]
        except httpx.HTTPError as exc:
            logger.error(
                f"API error fetching exercises for delete markup '{selected_muscle}': {exc}"
            )

    for ex in all_exercises:
        btn_row.append(
            InlineKeyboardButton(
                text=f"❌ {ex}",
                callback_data=f"del_ex_{ex}",
                style=ButtonStyle.DANGER,
            )
        )
        if len(btn_row) == 1:
            inline_keyboard.append(btn_row)
            btn_row = []

    if btn_row:
        inline_keyboard.append(btn_row)

    inline_keyboard.append(
        [InlineKeyboardButton(text="⬅️ Cancel", callback_data="back_to_exercises")]
    )

    return InlineKeyboardMarkup(inline_keyboard=inline_keyboard)


async def generate_select_set_markup(
    user_id: int, muscle: str, exercise: str
) -> InlineKeyboardMarkup:
    """Build the set-selection keyboard, graying out already-completed sets."""
    inline_keyboard: list[list[InlineKeyboardButton]] = []
    btn_row: list[InlineKeyboardButton] = []

    todays_date = datetime.now().strftime("%Y-%m-%d")
    completed_set_ids: list[int] = []
    try:
        result = await api.get_completed_sets(
            muscle=muscle,
            exercise=exercise,
            date=todays_date,
            act_as_user=user_id,
        )
        completed_set_ids = result.sets
    except httpx.HTTPError as exc:
        logger.error(f"API error fetching completed sets for user {user_id}: {exc}")

    try:
        available_sets = [s for s in sets if int(s["id"]) not in completed_set_ids]
    except Exception:
        logger.error("Can't determine available sets")
        available_sets = sets

    if not available_sets:
        inline_keyboard.append([
            InlineKeyboardButton(
                text="All sets completed!",
                callback_data="/start",
                style=ButtonStyle.SUCCESS,
            )
        ])
    else:
        for _set in available_sets:
            btn_row.append(
                InlineKeyboardButton(text=_set["name"], callback_data=_set["id"])
            )
            if len(btn_row) == 6:
                inline_keyboard.append(btn_row)
                btn_row = []
        if btn_row:
            inline_keyboard.append(btn_row)

    inline_keyboard.append(
        [InlineKeyboardButton(text="⬅️ Go back", callback_data="back_to_exercises")]
    )

    return InlineKeyboardMarkup(inline_keyboard=inline_keyboard)


async def generate_enter_weight_markup(
    user_id: int | None = None,
    muscle: str | None = None,
    exercise: str | None = None,
) -> InlineKeyboardMarkup:
    """Build weight-selection keyboard, highlighting the PR weight in green."""
    inline_keyboard: list[list[InlineKeyboardButton]] = []
    btn_row: list[InlineKeyboardButton] = []

    pr_weight: float | None = None
    if user_id and muscle and exercise:
        try:
            record = await api.get_personal_record(
                muscle=muscle, exercise=exercise, act_as_user=user_id
            )
            if record:
                pr_weight = record.weight
        except httpx.HTTPError as exc:
            logger.error(f"API error fetching PR weight for user {user_id}: {exc}")

    for w in weights:
        style = ButtonStyle.SUCCESS if _is_peak(w, pr_weight) else None
        btn_row.append(
            InlineKeyboardButton(text=f"{w}", callback_data=f"{w}kg", style=style)
        )
        if len(btn_row) == 7:
            inline_keyboard.append(btn_row)
            btn_row = []

    if btn_row:
        inline_keyboard.append(btn_row)

    inline_keyboard.append(
        [InlineKeyboardButton(text="⬅️ Go back", callback_data="back_to_sets")]
    )
    return InlineKeyboardMarkup(inline_keyboard=inline_keyboard)


async def generate_enter_reps_markup(
    user_id: int | None = None,
    muscle: str | None = None,
    exercise: str | None = None,
    weight: str | None = None,
) -> InlineKeyboardMarkup:
    """Build reps-selection keyboard, highlighting the max-reps-at-weight in green."""
    inline_keyboard: list[list[InlineKeyboardButton]] = []
    btn_row: list[InlineKeyboardButton] = []

    max_reps: float | None = None
    if user_id and muscle and exercise and weight is not None:
        try:
            result = await api.get_max_reps_for_weight(
                muscle=muscle,
                exercise=exercise,
                weight=float(weight),
                act_as_user=user_id,
            )
            max_reps = result.max_reps
        except httpx.HTTPError as exc:
            logger.error(f"API error fetching max reps for user {user_id}: {exc}")

    for r in reps:
        style = ButtonStyle.SUCCESS if _is_peak(r, max_reps) else None
        btn_row.append(
            InlineKeyboardButton(text=f"{r}", callback_data=f"{r}_r", style=style)
        )
        if len(btn_row) == 8:
            inline_keyboard.append(btn_row)
            btn_row = []

    if btn_row:
        inline_keyboard.append(btn_row)

    inline_keyboard.append(
        [InlineKeyboardButton(text="⬅️ Go back", callback_data="back_to_sets")]
    )
    return InlineKeyboardMarkup(inline_keyboard=inline_keyboard)
