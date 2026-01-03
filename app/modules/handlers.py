from aiogram import Router
from aiogram.types import Message, CallbackQuery
from aiogram.filters import CommandStart, Command
from aiogram.fsm.context import FSMContext
import prettytable as pt
from datetime import datetime
import hashlib

from templates.exercise import sets, weights, reps
from .postgres import PostgresDB
from .logging import Logger
from .states import UserStates
from utils import markups
import os


def normalize_weight_format(weight_str: str) -> str:
    """Convert comma decimal to dot decimal for PostgreSQL compatibility.

    Args:
        weight_str: Weight value as string (e.g., "2,5" or "2.5")

    Returns:
        Weight value with dot decimal format (e.g., "2.5")
    """
    return weight_str.replace(',', '.') if ',' in weight_str else weight_str


db = PostgresDB(
    db_name=os.environ.get("DB_NAME"),
    user=os.environ.get("DB_USER"),
    password=os.environ.get("DB_PASSWORD"),
    host=os.environ.get("DB_HOST"),
    port=os.environ.get("DB_PORT")
)
logger = Logger(name="handlers")
router = Router()


def get_hash(*args):
    """Create a hash from multiple arguments"""
    combined = ''.join(str(arg) for arg in args)
    return hashlib.md5(combined.encode()).hexdigest()


def check_user_exists(user_id):
    return db.get_user(user_id)


def check_user_registered(msg):
    if not check_user_exists(msg.from_user.id):
        data = {
            "id": msg.from_user.id,
            "registration_date": datetime.now(),
            "last_interaction": datetime.now(),
            "lastname": f"{msg.from_user.last_name}",
            "first_name": f"{msg.from_user.first_name}",
            "username": f"{msg.from_user.username}",
            "bio": f"{msg.chat.bio}",
        }
        db.save_any_data("users", data)
    return check_user_exists(msg.from_user.id)


def format_result_message(data: dict):
    """Format training result as a table for display.

    Args:
        data: Dictionary with keys: muscle, exercise, set, weight, reps

    Returns:
        Formatted HTML string with table
    """
    table = pt.PrettyTable(['Name', 'Details'])
    table.align = 'l'

    table.add_row(['Muscle', data['muscle']])
    table.add_row(['Exercise', data['exercise']])
    table.add_row(['Set', data["set"]])
    table.add_row(['Weight', f"{data['weight']}kg"])
    table.add_row(['Reps', data["reps"]])
    table.add_row(['Recorded at', datetime.now().strftime('%d-%m-%Y %H:%M:%S')])
    return f'<pre>{table}</pre>'


def format_last_training_table(training_data, exercise_name):
    """
    Format last training history as a table for display.
    
    Args:
        training_data: List of tuples (date, set, weight, reps)
        exercise_name: Name of the exercise
    
    Returns:
        Formatted HTML string with table or message if no data
    """
    if not training_data:
        return f"📝 You haven't done {exercise_name} before.\n\n"
    
    # Group data by date to show training sessions
    from collections import defaultdict
    sessions = defaultdict(list)
    
    for date, set_num, weight, reps in training_data:
        session_date = date.strftime('%d %B %Y')
        sessions[session_date].append((set_num, weight, reps))
    
    # Create table for the most recent session
    most_recent_date = list(sessions.keys())[0]  # Already ordered by date DESC
    recent_session = sessions[most_recent_date]
    
    table = pt.PrettyTable(['Set', 'Weight (kg)', 'Reps'])
    table.align = 'l'
    
    # Sort sets by set number
    recent_session.sort(key=lambda x: x[0])
    
    for set_num, weight, reps in recent_session:
        table.add_row([f"Set {set_num}", f"{weight}kg", f"{reps}"])
    
    history_text = f"📊 Your last training for {exercise_name} ({most_recent_date}):\n\n<pre>{table}</pre>\n\n"
    return history_text


def format_personal_record(pr_data, exercise_name):
    """
    Format personal record (PR) for display.
    
    Args:
        pr_data: Tuple of (weight, reps, date) or None if no PR exists
        exercise_name: Name of the exercise
    
    Returns:
        Formatted PR string or empty string if no PR data
    """
    if not pr_data:
        return ""  # No PR data - return empty string (safe for first-time users)
    
    weight, reps, date = pr_data
    formatted_date = date.strftime('%d %B %Y')
    return f"🥇 Your PR: {weight}kg for {int(reps)} reps ({formatted_date})\n\n"


@router.message(CommandStart())
async def comm_start(message: Message, state: FSMContext):
    logger.info(f"{message.from_user.id} /start has been called")
    user = check_user_registered(message)
    if not user:
        return

    # Clear state and reset to muscle selection
    await state.clear()
    await state.set_state(UserStates.selecting_muscle)

    ikm = markups.generate_muscle_markup(message.from_user.id)
    await message.reply("Select a body part", reply_markup=ikm)


@router.message(Command("gym"))
async def gym(message: Message, state: FSMContext):
    logger.info(f"{message.from_user.id} /gym has been called")
    user = check_user_registered(message)
    if not user:
        return

    # Clear state and reset to muscle selection
    await state.clear()
    await state.set_state(UserStates.selecting_muscle)

    ikm = markups.generate_muscle_markup(message.from_user.id)
    await message.reply("Select a body part", reply_markup=ikm)


@router.message(Command("edit"))
async def edit_command(message: Message, state: FSMContext):
    logger.info(f"{message.from_user.id} /edit has been called")
    user = check_user_registered(message)
    if not user:
        return

    # Clear state for edit mode
    await state.clear()

    ikm = markups.generate_edit_markup()
    await message.reply("Edit trainings", reply_markup=ikm)


@router.callback_query(lambda c: c.data.startswith("mus_"))
async def process_muscle(callback_query: CallbackQuery, state: FSMContext):
    user_id = callback_query.from_user.id
    muscle_name = callback_query.data.replace("mus_", "")

    # Store muscle in FSM state and move to exercise selection
    await state.update_data(muscle=muscle_name)
    await state.set_state(UserStates.selecting_exercise)

    logger.info(f"{user_id}: {muscle_name} body part selected")

    ikm = markups.generate_exercise_markup(muscle_name, user_id, show_all=False)
    bot = callback_query.bot
    await bot.edit_message_text(
        chat_id=callback_query.message.chat.id,
        message_id=callback_query.message.message_id,
        text="Select the exercise",
        reply_markup=ikm
    )
    await callback_query.answer(muscle_name)
    


@router.callback_query(lambda c: c.data.startswith("ex_"))
async def process_exercise(callback_query: CallbackQuery, state: FSMContext):
    user_id = callback_query.from_user.id
    exercise_name = callback_query.data.replace("ex_", "")

    # Get current state data
    data = await state.get_data()
    muscle_name = data.get("muscle")

    # Store exercise in FSM state and move to set selection
    await state.update_data(exercise=exercise_name)
    await state.set_state(UserStates.selecting_set)

    logger.info(f"{user_id}: {exercise_name} exercise selected")

    # Get last training history for this exercise
    training_history = db.get_last_training_history(
        user_id,
        muscle_name,
        exercise_name
    )

    # Get personal record for this exercise
    pr_data = db.get_personal_record(
        user_id,
        muscle_name,
        exercise_name
    )

    # Format training history and PR messages
    history_message = format_last_training_table(training_history, exercise_name)
    pr_message = format_personal_record(pr_data, exercise_name)

    # Combine history, PR, and set selection message
    message_text = history_message + pr_message + "Select set"

    ikm = markups.generate_select_set_markup(
        user_id,
        muscle_name,
        exercise_name
    )
    bot = callback_query.bot
    await bot.edit_message_text(
        chat_id=callback_query.message.chat.id,
        message_id=callback_query.message.message_id,
        text=message_text,
        parse_mode="HTML",
        reply_markup=ikm
    )
    await callback_query.answer(exercise_name)


@router.callback_query(lambda c: c.data in [_set["id"] for _set in sets])
async def process_set(callback_query: CallbackQuery, state: FSMContext):
    user_id = callback_query.from_user.id
    set_number = callback_query.data

    # Store set in FSM state and move to weight selection
    await state.update_data(set=set_number)
    await state.set_state(UserStates.selecting_weight)

    logger.info(f"{user_id}: Set {set_number} selected")

    ikm = markups.generate_enter_weight_markup()
    bot = callback_query.bot
    await bot.edit_message_text(
        chat_id=callback_query.message.chat.id,
        message_id=callback_query.message.message_id,
        text=f"Enter weight for set {set_number}",
        reply_markup=ikm
    )
    await callback_query.answer(set_number)


@router.callback_query(lambda c: c.data in [f"{w}kg" for w in weights])
async def process_weight(callback_query: CallbackQuery, state: FSMContext):
    user_id = callback_query.from_user.id
    weight_value = normalize_weight_format(callback_query.data.replace("kg", ""))

    # Get current state data for set number
    data = await state.get_data()
    set_number = data.get("set", "?")

    # Store weight in FSM state and move to reps selection
    await state.update_data(weight=weight_value)
    await state.set_state(UserStates.selecting_reps)

    logger.info(f"{user_id}: Weight {weight_value} selected")

    ikm = markups.generate_enter_reps_markup()
    bot = callback_query.bot
    await bot.edit_message_text(
        chat_id=callback_query.message.chat.id,
        message_id=callback_query.message.message_id,
        text=f"Set {set_number} | {weight_value}kg for <b>how many reps</b>?",
        parse_mode="HTML",
        reply_markup=ikm
    )
    await callback_query.answer(callback_query.data)


@router.callback_query(lambda c: c.data in [f"{r}_r" for r in reps])
async def process_reps(callback_query: CallbackQuery, state: FSMContext):
    user_id = callback_query.from_user.id
    reps_value = callback_query.data.replace("_r", "")

    # Get all state data
    data = await state.get_data()
    muscle_name = data.get("muscle")
    exercise_name = data.get("exercise")
    set_number = data.get("set")
    weight_value = data.get("weight")

    logger.info(f"{user_id}: {reps_value} reps selected")

    # Generate unique ID for this training record
    id_hash = get_hash(
        exercise_name,
        datetime.now().strftime('%Y-%m-%d %H:%M:%S'),
        set_number,
        weight_value,
        reps_value
    )

    date_now = datetime.now()

    # Save training data to database
    save_to_db = db.save_training_data(
        id_hash,
        date_now,
        user_id,
        muscle_name,
        exercise_name,
        set_number,
        normalize_weight_format(weight_value),
        reps_value
    )

    bot = callback_query.bot

    # Check if database save was successful
    if save_to_db["success"]:
        logger.info(f"{user_id}: {save_to_db['rows']} rows saved to db")

        # Show success message with workout summary
        message = format_result_message({
            "muscle": muscle_name,
            "exercise": exercise_name,
            "set": set_number,
            "weight": weight_value,
            "reps": reps_value
        })
        # Use new post-set markup that shows "Continue" or returns to muscle selection
        ikm = markups.generate_post_set_markup(user_id, muscle_name, exercise_name)
    else:
        # Database save failed - show error message
        logger.error(f"{user_id}: Database save failed - {save_to_db['error']}")
        message = "❌ Error writing to database. Please try again."
        ikm = markups.generate_muscle_markup(user_id)

    # Clear state and reset to muscle selection
    await state.clear()
    await state.set_state(UserStates.selecting_muscle)

    await bot.edit_message_text(
        chat_id=callback_query.message.chat.id,
        message_id=callback_query.message.message_id,
        text=message,
        parse_mode="HTML",
        reply_markup=ikm
    )
    await callback_query.answer(callback_query.data)


@router.callback_query(lambda c: c.data.startswith("show_all_exercises_"))
async def process_show_all_exercises(callback_query: CallbackQuery, state: FSMContext):
    """Handle 'Show All' button click - preserve user context and show full exercise list."""
    user_id = callback_query.from_user.id

    # Extract muscle name from callback data
    muscle_name = callback_query.data.replace("show_all_exercises_", "")

    # Ensure muscle is in state (restore if needed)
    await state.update_data(muscle=muscle_name)

    logger.info(f"{user_id}: Show all exercises requested for {muscle_name}")

    # Generate full exercise list with prioritization
    ikm = markups.generate_exercise_markup(muscle_name, user_id, show_all=True)

    bot = callback_query.bot
    await bot.edit_message_text(
        chat_id=callback_query.message.chat.id,
        message_id=callback_query.message.message_id,
        text="Select the exercise",
        reply_markup=ikm
    )
    await callback_query.answer("Showing all exercises")


@router.callback_query(lambda c: c.data.startswith("continue_ex||"))
async def process_continue_exercise(callback_query: CallbackQuery, state: FSMContext):
    """
    Handle 'Continue {exercise}' button click.
    Skip muscle/exercise selection and jump directly to set selection.
    """
    user_id = callback_query.from_user.id

    # Parse callback data: "continue_ex||{muscle}||{exercise}"
    data_parts = callback_query.data.replace("continue_ex||", "").split("||", 1)
    if len(data_parts) != 2:
        logger.error(f"Invalid callback data format: {callback_query.data}")
        await callback_query.answer("Error parsing exercise data", show_alert=True)
        return

    muscle_name, exercise_name = data_parts

    # Restore muscle/exercise context in FSM state
    await state.update_data(muscle=muscle_name, exercise=exercise_name)
    await state.set_state(UserStates.selecting_set)

    logger.info(f"{user_id}: Continue {exercise_name} for {muscle_name}")

    # Get last training history for this exercise
    training_history = db.get_last_training_history(
        user_id,
        muscle_name,
        exercise_name
    )

    # Get personal record for this exercise
    pr_data = db.get_personal_record(
        user_id,
        muscle_name,
        exercise_name
    )

    # Format training history and PR messages
    history_message = format_last_training_table(training_history, exercise_name)
    pr_message = format_personal_record(pr_data, exercise_name)

    # Combine history, PR, and set selection message
    message_text = history_message + pr_message + "Select set"

    # Generate set selection markup (filters completed sets automatically)
    ikm = markups.generate_select_set_markup(user_id, muscle_name, exercise_name)

    bot = callback_query.bot
    await bot.edit_message_text(
        chat_id=callback_query.message.chat.id,
        message_id=callback_query.message.message_id,
        text=message_text,
        parse_mode="HTML",
        reply_markup=ikm
    )
    await callback_query.answer(f"Continue {exercise_name}")


@router.callback_query(lambda c: c.data == "add_muscle_btn")
async def process_add_muscle_btn(callback_query: CallbackQuery, state: FSMContext):
    # Set FSM state to waiting for muscle name
    await state.set_state(UserStates.waiting_muscle_name)

    await callback_query.message.answer("Please enter the name of the new muscle group:")
    await callback_query.answer()


@router.callback_query(lambda c: c.data == "add_exercise_btn")
async def process_add_exercise_btn(callback_query: CallbackQuery, state: FSMContext):
    # Get current muscle from state
    data = await state.get_data()
    muscle_name = data.get("muscle")

    # Set FSM state to waiting for exercise name
    await state.set_state(UserStates.waiting_exercise_name)

    await callback_query.message.answer(f"Please enter the name of the new exercise for {muscle_name}:")
    await callback_query.answer()


@router.callback_query(lambda c: c.data == "delete_exercise_btn")
async def process_delete_exercise_btn(callback_query: CallbackQuery, state: FSMContext):
    user_id = callback_query.from_user.id

    # Get current muscle from state
    data = await state.get_data()
    muscle_name = data.get("muscle")

    # Set FSM state to deleting exercise
    await state.set_state(UserStates.deleting_exercise)

    ikm = markups.generate_delete_exercise_markup(muscle_name, user_id)

    await callback_query.message.edit_text(
        "Select an exercise to delete (or hide):",
        reply_markup=ikm
    )
    await callback_query.answer()


@router.callback_query(lambda c: c.data.startswith("del_ex_"))
async def process_delete_exercise_callback(callback_query: CallbackQuery, state: FSMContext):
    user_id = callback_query.from_user.id
    exercise_name = callback_query.data.replace("del_ex_", "")

    # Get current muscle from state
    data = await state.get_data()
    muscle_name = data.get("muscle")

    # Try to hide (if global) or delete (if private)
    success = db.hide_exercise(user_id, exercise_name, muscle_name)
    if not success:
        success = db.delete_private_exercise(user_id, exercise_name, muscle_name)

    if success:
        await callback_query.answer(f"Exercise '{exercise_name}' deleted.")
        # Refresh list and return to exercise selection state
        await state.set_state(UserStates.selecting_exercise)
        ikm = markups.generate_exercise_markup(muscle_name, user_id, show_all=False)
        await callback_query.message.edit_text(
            "Select the exercise",
            reply_markup=ikm
        )
    else:
        await callback_query.answer("Failed to delete exercise.", show_alert=True)


@router.message(lambda message: message.text and not message.text.startswith("/"))
async def process_text_input(message: Message, state: FSMContext):
    user_id = message.from_user.id
    user = check_user_registered(message)
    if not user:
        return

    # Get current FSM state
    current_state = await state.get_state()

    if current_state == UserStates.waiting_muscle_name:
        muscle_name = message.text.strip()
        if muscle_name:
            db.add_muscle(muscle_name, user_id)
            await message.answer(f"Muscle '{muscle_name}' added!")

            # Reset to muscle selection state
            await state.set_state(UserStates.selecting_muscle)

            # Show muscle list again
            ikm = markups.generate_muscle_markup(user_id)
            await message.answer("Select a body part", reply_markup=ikm)
        else:
            await message.answer("Invalid name.")

    elif current_state == UserStates.waiting_exercise_name:
        exercise_name = message.text.strip()

        # Get muscle from state
        data = await state.get_data()
        muscle_name = data.get("muscle")

        if exercise_name and muscle_name:
            db.add_exercise(exercise_name, muscle_name, user_id)
            await message.answer(f"Exercise '{exercise_name}' added to {muscle_name}!")

            # Return to exercise selection state
            await state.set_state(UserStates.selecting_exercise)

            # Show exercise list again
            ikm = markups.generate_exercise_markup(muscle_name, user_id, show_all=False)
            await message.answer("Select the exercise", reply_markup=ikm)
        else:
            await message.answer("Invalid name or muscle context lost.")
            # Reset to muscle selection
            await state.clear()
            await state.set_state(UserStates.selecting_muscle)
            ikm = markups.generate_muscle_markup(user_id)
            await message.answer("Start again", reply_markup=ikm)


# Back buttons
@router.callback_query(lambda c: c.data == "back_to_muscles")
async def back_to_muscles(callback_query: CallbackQuery, state: FSMContext):
    user_id = callback_query.from_user.id

    # Clear state and reset to muscle selection
    await state.clear()
    await state.set_state(UserStates.selecting_muscle)

    logger.info(f"{user_id}: Back to body parts called")

    ikm = markups.generate_muscle_markup(user_id)
    bot = callback_query.bot
    await bot.edit_message_text(
        chat_id=callback_query.message.chat.id,
        message_id=callback_query.message.message_id,
        text="Select a body part",
        reply_markup=ikm
    )
    await callback_query.answer("Going back to body parts")


@router.callback_query(lambda c: c.data == "back_to_exercises")
async def back_to_exercises(callback_query: CallbackQuery, state: FSMContext):
    user_id = callback_query.from_user.id

    # Get current muscle from state
    data = await state.get_data()
    muscle_name = data.get("muscle")

    # Clear exercise, set, weight, reps but keep muscle
    await state.update_data(exercise=None, set=None, weight=None, reps=None)
    await state.set_state(UserStates.selecting_exercise)

    logger.info(f"{user_id}: Back to exercises called")

    ikm = markups.generate_exercise_markup(muscle_name, user_id, show_all=False)
    bot = callback_query.bot
    await bot.edit_message_text(
        chat_id=callback_query.message.chat.id,
        message_id=callback_query.message.message_id,
        text="Select the exercise",
        reply_markup=ikm
    )
    await callback_query.answer("Going back to exercises")


@router.callback_query(lambda c: c.data == "back_to_sets")
async def back_to_sets(callback_query: CallbackQuery, state: FSMContext):
    user_id = callback_query.from_user.id

    # Get current muscle and exercise from state
    data = await state.get_data()
    muscle_name = data.get("muscle")
    exercise_name = data.get("exercise")

    # Clear set, weight, reps but keep muscle and exercise
    await state.update_data(set=None, weight=None, reps=None)
    await state.set_state(UserStates.selecting_set)

    logger.info(f"{user_id}: Back to sets called")

    ikm = markups.generate_select_set_markup(
        user_id,
        muscle_name,
        exercise_name
    )
    bot = callback_query.bot
    await bot.edit_message_text(
        chat_id=callback_query.message.chat.id,
        message_id=callback_query.message.message_id,
        text="Select set",
        reply_markup=ikm
    )
    await callback_query.answer("Going back to sets")


# duplicating
@router.callback_query(lambda c: c.data == "/start")
async def start_callback(callback_query: CallbackQuery, state: FSMContext):
    user_id = callback_query.from_user.id

    # Clear all state
    await state.clear()

    logger.info(f"{user_id}: Exit 'training editing' button was clicked")

    ikm = markups.generate_start_markup()
    bot = callback_query.bot
    await bot.edit_message_text(
        chat_id=callback_query.message.chat.id,
        message_id=callback_query.message.message_id,
        text="Select the action:",
        reply_markup=ikm
    )
    await callback_query.answer("Starting from scratch")


# duplicating
@router.callback_query(lambda c: c.data == "/gym")
async def gym_callback(callback_query: CallbackQuery, state: FSMContext):
    user_id = callback_query.from_user.id

    # Clear state and reset to muscle selection
    await state.clear()
    await state.set_state(UserStates.selecting_muscle)

    logger.info(f"{user_id}: /gym button was clicked from start menu")

    ikm = markups.generate_muscle_markup(user_id)
    bot = callback_query.bot
    await bot.edit_message_text(
        chat_id=callback_query.message.chat.id,
        message_id=callback_query.message.message_id,
        text="Select a body part",
        reply_markup=ikm
    )
    await callback_query.answer("Going back to body parts")
