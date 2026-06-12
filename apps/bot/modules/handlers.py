"""Aiogram handlers for the Gym Tracker bot.

All data I/O goes through the shared GymApiClient (modules.api).
No direct database access.
"""

from __future__ import annotations

from collections import defaultdict

import httpx
import prettytable as pt
from aiogram import Router
from aiogram.filters import Command, CommandStart
from aiogram.fsm.context import FSMContext
from aiogram.types import CallbackQuery, Message

from gym_api_client import models as api_models
from modules.api import api
from modules.confirmation import build_save_confirmation, normalize_weight_format
from modules.logging import Logger
from modules.states import UserStates
from templates.exercise import sets, weights, reps
from utils import markups

router = Router()
logger = Logger(name="handlers")


# ---------------------------------------------------------------------------
# Utility helpers
# ---------------------------------------------------------------------------
# normalize_weight_format / format_result_message and the GYM-137 save
# confirmation live in modules.confirmation (handlers.py is over the size
# limit — split when touched, per CLAUDE.md).


def format_last_training_table(
    training_data: list[api_models.TrainingHistoryEntry],
    exercise_name: str,
) -> str:
    """Format training history entries as a PrettyTable for the most recent session.

    Args:
        training_data: Ordered list of history entries (most-recent first).
        exercise_name: Display name for the exercise.

    Returns:
        Formatted HTML string, or a first-timer notice.
    """
    if not training_data:
        return f"You haven't done {exercise_name} before.\n\n"

    sessions: dict[str, list[tuple[int, float, float]]] = defaultdict(list)
    for entry in training_data:
        session_date = entry.date.strftime("%d %B %Y")
        sessions[session_date].append((entry.set, entry.weight, entry.reps))

    most_recent_date = list(sessions.keys())[0]
    recent_session = sorted(sessions[most_recent_date], key=lambda x: x[0])

    table = pt.PrettyTable(["Set", "Weight (kg)", "Reps"])
    table.align = "l"
    for set_num, weight, r in recent_session:
        table.add_row([f"Set {set_num}", f"{weight}kg", f"{r}"])

    return (
        f"Your last training for {exercise_name} ({most_recent_date}):\n\n"
        f"<pre>{table}</pre>\n\n"
    )


def format_personal_record(
    pr_data: api_models.PersonalRecord | None,
    exercise_name: str,
) -> str:
    """Format personal record for display.

    Args:
        pr_data: PersonalRecord model or None when no history exists.
        exercise_name: Display name (unused in output but kept for API compat).

    Returns:
        Formatted PR string, or empty string when no record exists.
    """
    if not pr_data:
        return ""
    formatted_date = pr_data.date.strftime("%d %B %Y")
    return f"Your PR: {pr_data.weight}kg for {int(pr_data.reps)} reps ({formatted_date})\n\n"


async def ensure_user(message: Message) -> bool:
    """Upsert the Telegram user in the Core API.

    Returns True when the user is known/created, False on API error.
    """
    user_id = message.from_user.id
    try:
        await api.upsert_me(
            api_models.UserRegistration(
                first_name=message.from_user.first_name,
                lastname=message.from_user.last_name,
                username=message.from_user.username,
            ),
            act_as_user=user_id,
        )
        return True
    except httpx.HTTPError as exc:
        logger.error(f"API error upserting user {user_id}: {exc}")
        await message.reply("Service unavailable. Please try again later.")
        return False


# ---------------------------------------------------------------------------
# Command handlers
# ---------------------------------------------------------------------------

@router.message(CommandStart())
async def comm_start(message: Message, state: FSMContext) -> None:
    logger.info(f"{message.from_user.id} /start called")
    if not await ensure_user(message):
        return

    await state.clear()
    await state.set_state(UserStates.selecting_muscle)

    ikm = await markups.generate_muscle_markup(message.from_user.id)
    await message.reply("Select a body part", reply_markup=ikm)


@router.message(Command("gym"))
async def gym(message: Message, state: FSMContext) -> None:
    logger.info(f"{message.from_user.id} /gym called")
    if not await ensure_user(message):
        return

    await state.clear()
    await state.set_state(UserStates.selecting_muscle)

    ikm = await markups.generate_muscle_markup(message.from_user.id)
    await message.reply("Select a body part", reply_markup=ikm)


@router.message(Command("edit"))
async def edit_command(message: Message, state: FSMContext) -> None:
    logger.info(f"{message.from_user.id} /edit called")
    if not await ensure_user(message):
        return

    await state.clear()

    ikm = markups.generate_edit_markup()
    await message.reply("Edit trainings", reply_markup=ikm)


# ---------------------------------------------------------------------------
# Callback query handlers
# ---------------------------------------------------------------------------

@router.callback_query(lambda c: c.data.startswith("mus_"))
async def process_muscle(callback_query: CallbackQuery, state: FSMContext) -> None:
    user_id = callback_query.from_user.id
    muscle_name = callback_query.data.replace("mus_", "")

    await state.update_data(muscle=muscle_name)
    await state.set_state(UserStates.selecting_exercise)

    logger.info(f"{user_id}: muscle '{muscle_name}' selected")

    ikm = await markups.generate_exercise_markup(muscle_name, user_id, show_all=False)
    await callback_query.bot.edit_message_text(
        chat_id=callback_query.message.chat.id,
        message_id=callback_query.message.message_id,
        text="Select the exercise",
        reply_markup=ikm,
    )
    await callback_query.answer(muscle_name)


@router.callback_query(lambda c: c.data.startswith("ex_"))
async def process_exercise(callback_query: CallbackQuery, state: FSMContext) -> None:
    user_id = callback_query.from_user.id
    exercise_name = callback_query.data.replace("ex_", "")

    data = await state.get_data()
    muscle_name: str = data.get("muscle", "")

    await state.update_data(exercise=exercise_name)
    await state.set_state(UserStates.selecting_set)

    logger.info(f"{user_id}: exercise '{exercise_name}' selected")

    # Fetch training context for the exercise summary
    history_message = ""
    pr_message = ""
    try:
        history = await api.get_training_history(
            muscle=muscle_name, exercise=exercise_name, act_as_user=user_id
        )
        history_message = format_last_training_table(history, exercise_name)
    except httpx.HTTPError as exc:
        logger.error(f"API error fetching history for user {user_id}: {exc}")

    try:
        pr = await api.get_personal_record(
            muscle=muscle_name, exercise=exercise_name, act_as_user=user_id
        )
        pr_message = format_personal_record(pr, exercise_name)
    except httpx.HTTPError as exc:
        logger.error(f"API error fetching PR for user {user_id}: {exc}")

    message_text = history_message + pr_message + "Select set"
    ikm = await markups.generate_select_set_markup(user_id, muscle_name, exercise_name)

    await callback_query.bot.edit_message_text(
        chat_id=callback_query.message.chat.id,
        message_id=callback_query.message.message_id,
        text=message_text,
        parse_mode="HTML",
        reply_markup=ikm,
    )
    await callback_query.answer(exercise_name)


@router.callback_query(lambda c: c.data in [_set["id"] for _set in sets])
async def process_set(callback_query: CallbackQuery, state: FSMContext) -> None:
    user_id = callback_query.from_user.id
    set_number = callback_query.data

    await state.update_data(set=set_number)
    await state.set_state(UserStates.selecting_weight)

    logger.info(f"{user_id}: set {set_number} selected")

    data = await state.get_data()
    ikm = await markups.generate_enter_weight_markup(
        user_id, data.get("muscle"), data.get("exercise")
    )
    await callback_query.bot.edit_message_text(
        chat_id=callback_query.message.chat.id,
        message_id=callback_query.message.message_id,
        text=f"Enter weight for set {set_number}",
        reply_markup=ikm,
    )
    await callback_query.answer(set_number)


@router.callback_query(lambda c: c.data in [f"{w}kg" for w in weights])
async def process_weight(callback_query: CallbackQuery, state: FSMContext) -> None:
    user_id = callback_query.from_user.id
    weight_value = normalize_weight_format(callback_query.data.replace("kg", ""))

    data = await state.get_data()
    set_number = data.get("set", "?")

    await state.update_data(weight=weight_value)
    await state.set_state(UserStates.selecting_reps)

    logger.info(f"{user_id}: weight {weight_value} selected")

    ikm = await markups.generate_enter_reps_markup(
        user_id, data.get("muscle"), data.get("exercise"), weight_value
    )
    await callback_query.bot.edit_message_text(
        chat_id=callback_query.message.chat.id,
        message_id=callback_query.message.message_id,
        text=f"Set {set_number} | {weight_value}kg for <b>how many reps</b>?",
        parse_mode="HTML",
        reply_markup=ikm,
    )
    await callback_query.answer(callback_query.data)


@router.callback_query(lambda c: c.data in [f"{r}_r" for r in reps])
async def process_reps(callback_query: CallbackQuery, state: FSMContext) -> None:
    user_id = callback_query.from_user.id
    reps_value = callback_query.data.replace("_r", "")

    data = await state.get_data()
    muscle_name: str = data.get("muscle", "")
    exercise_name: str = data.get("exercise", "")
    set_number: str = data.get("set", "")
    weight_value: str = data.get("weight", "")

    logger.info(f"{user_id}: {reps_value} reps selected")

    message = ""
    ikm = None

    try:
        training = await api.create_training(
            api_models.TrainingCreate(
                muscle_name=muscle_name,
                exercise_name=exercise_name,
                set=int(set_number),
                weight=float(normalize_weight_format(weight_value)),
                reps=float(reps_value),
            ),
            act_as_user=user_id,
        )
        logger.info(f"{user_id}: training {training.id} saved")

        message = await build_save_confirmation(
            user_id, muscle_name, exercise_name, set_number, weight_value, reps_value
        )
        ikm = await markups.generate_post_set_markup(user_id, muscle_name, exercise_name)

    except httpx.HTTPError as exc:
        logger.error(f"{user_id}: API error saving training: {exc}")
        message = "Error saving training. Please try again."
        ikm = await markups.generate_muscle_markup(user_id)

    await state.clear()
    await state.set_state(UserStates.selecting_muscle)

    await callback_query.bot.edit_message_text(
        chat_id=callback_query.message.chat.id,
        message_id=callback_query.message.message_id,
        text=message,
        parse_mode="HTML",
        reply_markup=ikm,
    )
    await callback_query.answer(callback_query.data)


@router.callback_query(lambda c: c.data.startswith("show_all_exercises_"))
async def process_show_all_exercises(
    callback_query: CallbackQuery, state: FSMContext
) -> None:
    """Handle 'Show All' button — preserve user context and show full exercise list."""
    user_id = callback_query.from_user.id
    muscle_name = callback_query.data.replace("show_all_exercises_", "")

    await state.update_data(muscle=muscle_name)
    logger.info(f"{user_id}: show all exercises for '{muscle_name}'")

    ikm = await markups.generate_exercise_markup(muscle_name, user_id, show_all=True)
    await callback_query.bot.edit_message_text(
        chat_id=callback_query.message.chat.id,
        message_id=callback_query.message.message_id,
        text="Select the exercise",
        reply_markup=ikm,
    )
    await callback_query.answer("Showing all exercises")


@router.callback_query(lambda c: c.data.startswith("continue_ex||"))
async def process_continue_exercise(
    callback_query: CallbackQuery, state: FSMContext
) -> None:
    """Skip muscle/exercise selection and jump to set selection for the same exercise."""
    user_id = callback_query.from_user.id

    parts = callback_query.data.replace("continue_ex||", "").split("||", 1)
    if len(parts) != 2:
        logger.error(f"Invalid continue_ex callback data: {callback_query.data}")
        await callback_query.answer("Error parsing exercise data", show_alert=True)
        return

    muscle_name, exercise_name = parts

    await state.update_data(muscle=muscle_name, exercise=exercise_name)
    await state.set_state(UserStates.selecting_set)

    logger.info(f"{user_id}: continue '{exercise_name}' for '{muscle_name}'")

    history_message = ""
    pr_message = ""
    try:
        history = await api.get_training_history(
            muscle=muscle_name, exercise=exercise_name, act_as_user=user_id
        )
        history_message = format_last_training_table(history, exercise_name)
    except httpx.HTTPError as exc:
        logger.error(f"API error fetching history for user {user_id}: {exc}")

    try:
        pr = await api.get_personal_record(
            muscle=muscle_name, exercise=exercise_name, act_as_user=user_id
        )
        pr_message = format_personal_record(pr, exercise_name)
    except httpx.HTTPError as exc:
        logger.error(f"API error fetching PR for user {user_id}: {exc}")

    message_text = history_message + pr_message + "Select set"
    ikm = await markups.generate_select_set_markup(user_id, muscle_name, exercise_name)

    await callback_query.bot.edit_message_text(
        chat_id=callback_query.message.chat.id,
        message_id=callback_query.message.message_id,
        text=message_text,
        parse_mode="HTML",
        reply_markup=ikm,
    )
    await callback_query.answer(f"Continue {exercise_name}")


@router.callback_query(lambda c: c.data == "add_muscle_btn")
async def process_add_muscle_btn(
    callback_query: CallbackQuery, state: FSMContext
) -> None:
    await state.set_state(UserStates.waiting_muscle_name)
    await callback_query.message.answer("Please enter the name of the new muscle group:")
    await callback_query.answer()


@router.callback_query(lambda c: c.data == "add_exercise_btn")
async def process_add_exercise_btn(
    callback_query: CallbackQuery, state: FSMContext
) -> None:
    data = await state.get_data()
    muscle_name = data.get("muscle")
    await state.set_state(UserStates.waiting_exercise_name)
    await callback_query.message.answer(
        f"Please enter the name of the new exercise for {muscle_name}:"
    )
    await callback_query.answer()


@router.callback_query(lambda c: c.data == "delete_exercise_btn")
async def process_delete_exercise_btn(
    callback_query: CallbackQuery, state: FSMContext
) -> None:
    user_id = callback_query.from_user.id
    data = await state.get_data()
    muscle_name = data.get("muscle")

    await state.set_state(UserStates.deleting_exercise)

    ikm = await markups.generate_delete_exercise_markup(muscle_name, user_id)
    await callback_query.message.edit_text(
        "Select an exercise to delete (or hide):",
        reply_markup=ikm,
    )
    await callback_query.answer()


@router.callback_query(lambda c: c.data.startswith("del_ex_"))
async def process_delete_exercise_callback(
    callback_query: CallbackQuery, state: FSMContext
) -> None:
    user_id = callback_query.from_user.id
    exercise_name = callback_query.data.replace("del_ex_", "")

    data = await state.get_data()
    muscle_name: str = data.get("muscle", "")

    # Resolve exercise_id — needed by the API (id-based endpoints)
    from utils.markups import _find_exercise_id  # local import to avoid circular ref

    exercise_id = await _find_exercise_id(muscle_name, exercise_name, user_id)
    success = False

    if exercise_id is not None:
        # Try hide first (global exercise), then hard-delete (private exercise)
        try:
            await api.hide_exercise(exercise_id, act_as_user=user_id)
            success = True
        except httpx.HTTPStatusError as exc:
            if exc.response.status_code in (403, 404):
                # Not a global exercise — try deleting private copy
                try:
                    await api.delete_private_exercise(exercise_id, act_as_user=user_id)
                    success = True
                except httpx.HTTPError as inner_exc:
                    logger.error(
                        f"API error deleting private exercise {exercise_id}: {inner_exc}"
                    )
            else:
                logger.error(
                    f"API error hiding exercise {exercise_id}: {exc}"
                )
        except httpx.HTTPError as exc:
            logger.error(f"API error hiding exercise {exercise_id}: {exc}")
    else:
        logger.error(
            f"Could not resolve exercise id for '{exercise_name}' in '{muscle_name}'"
        )

    if success:
        await callback_query.answer(f"Exercise '{exercise_name}' deleted.")
        await state.set_state(UserStates.selecting_exercise)
        ikm = await markups.generate_exercise_markup(muscle_name, user_id, show_all=False)
        await callback_query.message.edit_text("Select the exercise", reply_markup=ikm)
    else:
        await callback_query.answer("Failed to delete exercise.", show_alert=True)


@router.message(lambda message: message.text and not message.text.startswith("/"))
async def process_text_input(message: Message, state: FSMContext) -> None:
    user_id = message.from_user.id
    if not await ensure_user(message):
        return

    current_state = await state.get_state()

    if current_state == UserStates.waiting_muscle_name:
        muscle_name = message.text.strip()
        if muscle_name:
            try:
                await api.create_muscle(
                    api_models.MuscleCreate(name=muscle_name),
                    act_as_user=user_id,
                )
                await message.answer(f"Muscle '{muscle_name}' added!")
            except httpx.HTTPError as exc:
                logger.error(f"API error creating muscle for user {user_id}: {exc}")
                await message.answer("Error creating muscle. Please try again.")

            await state.set_state(UserStates.selecting_muscle)
            ikm = await markups.generate_muscle_markup(user_id)
            await message.answer("Select a body part", reply_markup=ikm)
        else:
            await message.answer("Invalid name.")

    elif current_state == UserStates.waiting_exercise_name:
        exercise_name = message.text.strip()
        data = await state.get_data()
        muscle_name = data.get("muscle")

        if exercise_name and muscle_name:
            try:
                await api.create_exercise(
                    api_models.ExerciseCreate(
                        name=exercise_name, muscle_name=muscle_name
                    ),
                    act_as_user=user_id,
                )
                await message.answer(f"Exercise '{exercise_name}' added to {muscle_name}!")
            except httpx.HTTPError as exc:
                logger.error(f"API error creating exercise for user {user_id}: {exc}")
                await message.answer("Error creating exercise. Please try again.")

            await state.set_state(UserStates.selecting_exercise)
            ikm = await markups.generate_exercise_markup(muscle_name, user_id, show_all=False)
            await message.answer("Select the exercise", reply_markup=ikm)
        else:
            await message.answer("Invalid name or muscle context lost.")
            await state.clear()
            await state.set_state(UserStates.selecting_muscle)
            ikm = await markups.generate_muscle_markup(user_id)
            await message.answer("Start again", reply_markup=ikm)


# ---------------------------------------------------------------------------
# Back-button handlers
# ---------------------------------------------------------------------------

@router.callback_query(lambda c: c.data == "back_to_muscles")
async def back_to_muscles(callback_query: CallbackQuery, state: FSMContext) -> None:
    user_id = callback_query.from_user.id

    await state.clear()
    await state.set_state(UserStates.selecting_muscle)

    logger.info(f"{user_id}: back to body parts")

    ikm = await markups.generate_muscle_markup(user_id)
    await callback_query.bot.edit_message_text(
        chat_id=callback_query.message.chat.id,
        message_id=callback_query.message.message_id,
        text="Select a body part",
        reply_markup=ikm,
    )
    await callback_query.answer("Going back to body parts")


@router.callback_query(lambda c: c.data == "back_to_exercises")
async def back_to_exercises(callback_query: CallbackQuery, state: FSMContext) -> None:
    user_id = callback_query.from_user.id

    data = await state.get_data()
    muscle_name = data.get("muscle")

    await state.update_data(exercise=None, set=None, weight=None, reps=None)
    await state.set_state(UserStates.selecting_exercise)

    logger.info(f"{user_id}: back to exercises")

    ikm = await markups.generate_exercise_markup(muscle_name, user_id, show_all=False)
    await callback_query.bot.edit_message_text(
        chat_id=callback_query.message.chat.id,
        message_id=callback_query.message.message_id,
        text="Select the exercise",
        reply_markup=ikm,
    )
    await callback_query.answer("Going back to exercises")


@router.callback_query(lambda c: c.data == "back_to_sets")
async def back_to_sets(callback_query: CallbackQuery, state: FSMContext) -> None:
    user_id = callback_query.from_user.id

    data = await state.get_data()
    muscle_name = data.get("muscle")
    exercise_name = data.get("exercise")

    await state.update_data(set=None, weight=None, reps=None)
    await state.set_state(UserStates.selecting_set)

    logger.info(f"{user_id}: back to sets")

    ikm = await markups.generate_select_set_markup(user_id, muscle_name, exercise_name)
    await callback_query.bot.edit_message_text(
        chat_id=callback_query.message.chat.id,
        message_id=callback_query.message.message_id,
        text="Select set",
        reply_markup=ikm,
    )
    await callback_query.answer("Going back to sets")


@router.callback_query(lambda c: c.data == "/start")
async def start_callback(callback_query: CallbackQuery, state: FSMContext) -> None:
    user_id = callback_query.from_user.id

    await state.clear()
    logger.info(f"{user_id}: exit training editing")

    ikm = markups.generate_start_markup()
    await callback_query.bot.edit_message_text(
        chat_id=callback_query.message.chat.id,
        message_id=callback_query.message.message_id,
        text="Select the action:",
        reply_markup=ikm,
    )
    await callback_query.answer("Starting from scratch")


@router.callback_query(lambda c: c.data == "/gym")
async def gym_callback(callback_query: CallbackQuery, state: FSMContext) -> None:
    user_id = callback_query.from_user.id

    await state.clear()
    await state.set_state(UserStates.selecting_muscle)

    logger.info(f"{user_id}: /gym button from start menu")

    ikm = await markups.generate_muscle_markup(user_id)
    await callback_query.bot.edit_message_text(
        chat_id=callback_query.message.chat.id,
        message_id=callback_query.message.message_id,
        text="Select a body part",
        reply_markup=ikm,
    )
    await callback_query.answer("Going back to body parts")
