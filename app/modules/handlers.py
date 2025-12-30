from aiogram import Router
from aiogram.types import Message, CallbackQuery
from aiogram.filters import CommandStart, Command
import prettytable as pt
from datetime import datetime
import hashlib

from templates.exercise import sets, weights, reps
from .postgres import PostgresDB
from .logging import Logger
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
user_choices = {}

# Cache removed for user-specific exercises support


def ensure_user_context(user_id, muscle_name=None):
    """
    Ensure user context is valid and preserved.
    
    Args:
        user_id: User's Telegram ID
        muscle_name: Optional muscle name to validate/restore context
    """
    if user_id not in user_choices:
        user_choices[user_id] = {"muscle": None, "exercise": None, "set": None, "weight": None, "reps": None}
    
    if muscle_name and user_choices[user_id]["muscle"] != muscle_name:
        logger.warning(f"Restoring muscle context for user {user_id}: {muscle_name}")
        user_choices[user_id]["muscle"] = muscle_name
        user_choices[user_id]["exercise"] = None  # Reset exercise when muscle changes


def get_hash(*args):
    """Create a hash from multiple arguments"""
    combined = ''.join(str(arg) for arg in args)
    return hashlib.md5(combined.encode()).hexdigest()


def get_all_muscles():
    """Get all muscles from database with caching."""
    global _muscles_cache
    if _muscles_cache is None:
        _muscles_cache = db.get_all_muscles()
    return _muscles_cache


def get_exercises_for_muscle(muscle_name):
    """Get exercises for a muscle from database with caching."""
    if muscle_name not in _exercises_cache:
        _exercises_cache[muscle_name] = db.get_exercises_by_muscle(muscle_name)
    return _exercises_cache[muscle_name]


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


def format_result_message(results, user_id):
    table = pt.PrettyTable(['Name', 'Details'])
    table.align = 'l'

    table.add_row(['Muscle', results[user_id]['muscle']])
    table.add_row(['Exercise', results[user_id]['exercise']])
    table.add_row(['Set', results[user_id]["set"]])
    table.add_row(['Weight', f"{results[user_id]['weight']}kg"])
    table.add_row(['Reps', results[user_id]["reps"]])
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
async def comm_start(message: Message):
    logger.info(f"{message.from_user.id} /start has been called")
    user = check_user_registered(message)
    if not user:
        return
    user_choices[message.from_user.id] = {"muscle": None, "exercise": None, "set": None, "weight": None, "reps": None}
    ikm = markups.generate_muscle_markup(message.from_user.id)
    await message.reply("Select a body part", reply_markup=ikm)


@router.message(Command("gym"))
async def gym(message: Message):
    logger.info(f"{message.from_user.id} /gym has been called")
    user = check_user_registered(message)
    if not user:
        return
    user_choices[message.from_user.id] = {"muscle": None, "exercise": None, "set": None, "weight": None, "reps": None}
    ikm = markups.generate_muscle_markup(message.from_user.id)
    await message.reply("Select a body part", reply_markup=ikm)


@router.message(Command("edit"))
async def gym(message: Message):
    logger.info(f"{message.from_user.id} /edit has been called")
    user = check_user_registered(message)
    if not user:
        return
    # user_choices[message.from_user.id] = {"muscle": None, "exercise": None, "set": None, "weight": None, "reps": None}
    ikm = markups.generate_edit_markup()
    await message.reply("Edit trainings", reply_markup=ikm)


@router.callback_query(lambda c: c.data.startswith("mus_"))
async def process_muscle(callback_query: CallbackQuery):
    user_id = callback_query.from_user.id
    muscle_name = callback_query.data.replace("mus_", "")
    user_choices[user_id]["muscle"] = muscle_name
    
    if user_choices[user_id]["muscle"]:
        logger.info(f"{user_id}: {muscle_name} body part selected")
        # Removed db.add_muscle() - selecting a muscle shouldn't create it

        ikm = markups.generate_exercise_markup(muscle_name, user_id, show_all=False)
        bot = callback_query.bot
        await bot.edit_message_text(chat_id=callback_query.message.chat.id,
                                    message_id=callback_query.message.message_id,
                                    text="Select the exercise",
                                    reply_markup=ikm)
        await callback_query.answer(muscle_name)
    else:
        user_choices[user_id] = {"muscle": None, "exercise": None, "set": None, "weight": None, "reps": None}
        ikm = markups.generate_muscle_markup(user_id)
        await callback_query.message.reply("Start this one from scratch", reply_markup=ikm)
    


@router.callback_query(lambda c: c.data.startswith("ex_"))
async def process_exercise(callback_query: CallbackQuery):
    user_id = callback_query.from_user.id
    exercise_name = callback_query.data.replace("ex_", "")
    user_choices[user_id]["exercise"] = exercise_name
    
    if user_choices[user_id]["exercise"]:
        logger.info(f"{user_id}: {exercise_name} exercise selected")
        # Removed db.add_exercise() - selecting an exercise shouldn't create a duplicate
        # Only the "Add Exercise" button flow should create new exercises

        # Get last training history for this exercise
        training_history = db.get_last_training_history(
            user_id,
            user_choices[user_id]["muscle"],
            user_choices[user_id]["exercise"]
        )
        
        # Get personal record for this exercise
        pr_data = db.get_personal_record(
            user_id,
            user_choices[user_id]["muscle"],
            user_choices[user_id]["exercise"]
        )
        
        # Format training history and PR messages
        history_message = format_last_training_table(training_history, user_choices[user_id]["exercise"])
        pr_message = format_personal_record(pr_data, user_choices[user_id]["exercise"])
        
        # Combine history, PR, and set selection message
        message_text = history_message + pr_message + "Select set"

        ikm = markups.generate_select_set_markup(
            user_id,
            user_choices[user_id]["muscle"],
            user_choices[user_id]["exercise"]
        )
        bot = callback_query.bot
        await bot.edit_message_text(chat_id=callback_query.message.chat.id,
                                    message_id=callback_query.message.message_id,
                                    text=message_text,
                                    parse_mode="HTML",
                                    reply_markup=ikm)
        await callback_query.answer(exercise_name)
    else:
        user_choices[user_id] = {"muscle": None, "exercise": None, "set": None, "weight": None, "reps": None}
        ikm = markups.generate_muscle_markup(user_id)
        await callback_query.message.reply("Start this one from scratch", reply_markup=ikm)


@router.callback_query(lambda c: c.data in [_set["id"] for _set in sets])
async def process_set(callback_query: CallbackQuery):
    user_id = callback_query.from_user.id
    user_choices[user_id]["set"] = callback_query.data
    logger.info(f"{user_id}: Set {callback_query.data} selected")
    if user_choices[user_id]["set"]:
        ikm = markups.generate_enter_weight_markup()
        bot = callback_query.bot
        await bot.edit_message_text(chat_id=callback_query.message.chat.id,
                                    message_id=callback_query.message.message_id,
                                    text=f"Enter weight for set {callback_query.data}",
                                    reply_markup=ikm)
        await callback_query.answer(callback_query.data)
    else:
        user_choices[user_id] = {"muscle": None, "exercise": None, "set": None, "weight": None, "reps": None}
        ikm = markups.generate_muscle_markup(user_id)
        await callback_query.message.reply("Start this one from scratch", reply_markup=ikm)


@router.callback_query(lambda c: c.data in [f"{w}kg" for w in weights])
async def process_weight(callback_query: CallbackQuery):
    user_id = callback_query.from_user.id
    user_choices[user_id]["weight"] = normalize_weight_format(callback_query.data.replace("kg", ""))
    logger.info(f"{user_id}: Weight {user_choices[user_id]['weight']} selected")
    if user_choices[user_id]["weight"]:
        ikm = markups.generate_enter_reps_markup()
        bot = callback_query.bot
        await bot.edit_message_text(chat_id=callback_query.message.chat.id,
                                    message_id=callback_query.message.message_id,
                                    text=f"How many reps?",
                                    reply_markup=ikm)
        await callback_query.answer(callback_query.data)
    else:
        user_choices[user_id] = {"muscle": None, "exercise": None, "set": None, "weight": None, "reps": None}
        ikm = markups.generate_muscle_markup(user_id)
        await callback_query.message.reply("Start this one from scratch", reply_markup=ikm)


@router.callback_query(lambda c: c.data in [f"{r}_r" for r in reps])
async def process_reps(callback_query: CallbackQuery):
    user_id = callback_query.from_user.id
    user_choices[user_id]["reps"] = callback_query.data.replace("_r", "")
    logger.info(f"{user_id}: {user_choices[user_id]['reps']} reps selected")
    if not user_choices[user_id]["reps"]:
        user_choices[user_id] = {"muscle": None, "exercise": None, "set": None, "weight": None, "reps": None}
        ikm = markups.generate_muscle_markup(user_id)
        await callback_query.message.reply("Start this one from scratch", reply_markup=ikm)
    else:
        id_hash = get_hash(user_choices[user_id]['exercise'], 
            datetime.now().strftime('%Y-%m-%d %H:%M:%S'), 
            user_choices[user_id]["set"], 
            user_choices[user_id]["weight"], 
            user_choices[user_id]["reps"]
        )
        
        date_now = datetime.now()
        
        save_to_db = db.save_training_data(
            id_hash,
            date_now,
            user_id,
            user_choices[user_id]['muscle'],
            user_choices[user_id]['exercise'],
            user_choices[user_id]["set"],
            normalize_weight_format(user_choices[user_id]["weight"]),
            user_choices[user_id]["reps"]
        )

        bot = callback_query.bot

        # Check if database save was successful
        if save_to_db["success"]:
            logger.info(f"{user_id}: {save_to_db['rows']} rows saved to db")

            # Show success message with workout summary
            message = format_result_message(user_choices, user_id)
            ikm = markups.generate_muscle_markup(user_id)
        else:
            # Database save failed - show error message
            logger.error(f"{user_id}: Database save failed - {save_to_db['error']}")
            message = "❌ Error writing to database. Please try again."
            ikm = markups.generate_muscle_markup(user_id)

        await bot.edit_message_text(chat_id=callback_query.message.chat.id,
                                    message_id=callback_query.message.message_id,
                                    text=message,
                                    parse_mode="HTML",
                                    reply_markup=ikm)
        await callback_query.answer(callback_query.data)


@router.callback_query(lambda c: c.data.startswith("show_all_exercises_"))
async def process_show_all_exercises(callback_query: CallbackQuery):
    """
    Handle 'Show All' button click - preserve user context and show full exercise list.
    """
    user_id = callback_query.from_user.id
    
    # Extract muscle name from callback data
    muscle_name = callback_query.data.replace("show_all_exercises_", "")
    
    # CRITICAL: Ensure user context is preserved
    ensure_user_context(user_id, muscle_name)
    
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


@router.callback_query(lambda c: c.data == "add_muscle_btn")
async def process_add_muscle_btn(callback_query: CallbackQuery):
    user_id = callback_query.from_user.id
    user_choices[user_id]["action"] = "waiting_muscle_name"
    
    await callback_query.message.answer("Please enter the name of the new muscle group:")
    await callback_query.answer()


@router.callback_query(lambda c: c.data == "add_exercise_btn")
async def process_add_exercise_btn(callback_query: CallbackQuery):
    user_id = callback_query.from_user.id
    user_choices[user_id]["action"] = "waiting_exercise_name"
    
    await callback_query.message.answer(f"Please enter the name of the new exercise for {user_choices[user_id]['muscle']}:")
    await callback_query.answer()


@router.callback_query(lambda c: c.data == "delete_exercise_btn")
async def process_delete_exercise_btn(callback_query: CallbackQuery):
    user_id = callback_query.from_user.id
    muscle_name = user_choices[user_id]["muscle"]
    
    ikm = markups.generate_delete_exercise_markup(muscle_name, user_id)
    
    await callback_query.message.edit_text(
        "Select an exercise to delete (or hide):",
        reply_markup=ikm
    )
    await callback_query.answer()


@router.callback_query(lambda c: c.data.startswith("del_ex_"))
async def process_delete_exercise_callback(callback_query: CallbackQuery):
    user_id = callback_query.from_user.id
    exercise_name = callback_query.data.replace("del_ex_", "")
    muscle_name = user_choices[user_id]["muscle"]
    
    # Try to hide (if global) or delete (if private)
    # We can try both or check first. DB methods handle logic.
    # Actually, we need to know if it's global or private to call the right method?
    # Or we can just try hide, if it fails (because it's private?), try delete?
    # Better: DB methods should be distinct.
    # Let's try hide first. If it returns False, maybe it's private.
    
    # Actually, let's just try to hide it. If it's global, it will work.
    # If it's private, hide_exercise will fail (query checks is_global=TRUE).
    # Then we try delete_private_exercise.
    
    success = db.hide_exercise(user_id, exercise_name, muscle_name)
    if not success:
        success = db.delete_private_exercise(user_id, exercise_name, muscle_name)
        
    if success:
        await callback_query.answer(f"Exercise '{exercise_name}' deleted.")
        # Refresh list
        ikm = markups.generate_exercise_markup(muscle_name, user_id, show_all=False)
        await callback_query.message.edit_text(
            "Select the exercise",
            reply_markup=ikm
        )
    else:
        await callback_query.answer("Failed to delete exercise.", show_alert=True)


@router.message(lambda message: message.text and not message.text.startswith("/"))
async def process_text_input(message: Message):
    user_id = message.from_user.id
    user = check_user_registered(message)
    if not user:
        return

    if user_id not in user_choices:
        ensure_user_context(user_id)
        
    action = user_choices[user_id].get("action")
    
    if action == "waiting_muscle_name":
        muscle_name = message.text.strip()
        if muscle_name:
            db.add_muscle(muscle_name, user_id)
            user_choices[user_id]["action"] = None
            await message.answer(f"Muscle '{muscle_name}' added!")
            
            # Show muscle list again
            ikm = markups.generate_muscle_markup(user_id)
            await message.answer("Select a body part", reply_markup=ikm)
        else:
            await message.answer("Invalid name.")
            
    elif action == "waiting_exercise_name":
        exercise_name = message.text.strip()
        muscle_name = user_choices[user_id].get("muscle")
        
        if exercise_name and muscle_name:
            db.add_exercise(exercise_name, muscle_name, user_id)
            user_choices[user_id]["action"] = None
            await message.answer(f"Exercise '{exercise_name}' added to {muscle_name}!")
            
            # Show exercise list again
            ikm = markups.generate_exercise_markup(muscle_name, user_id, show_all=False)
            await message.answer("Select the exercise", reply_markup=ikm)
        else:
            await message.answer("Invalid name or muscle context lost.")
            user_choices[user_id]["action"] = None
            ikm = markups.generate_muscle_markup(user_id)
            await message.answer("Start again", reply_markup=ikm)


# Back buttons
@router.callback_query(lambda c: c.data == "back_to_muscles")
async def back_to_muscles(callback_query: CallbackQuery):
    user_id = callback_query.from_user.id
    user_choices[user_id]["muscle"] = None
    user_choices[user_id]["action"] = None # Reset action
    logger.info(f"{user_id}: Back to body parts called")

    ikm = markups.generate_muscle_markup(user_id)
    bot = callback_query.bot
    await bot.edit_message_text(chat_id=callback_query.message.chat.id,
                                message_id=callback_query.message.message_id,
                                text="Select a body part",
                                reply_markup=ikm)
    await callback_query.answer("Going back to body parts")


@router.callback_query(lambda c: c.data == "back_to_exercises")
async def back_to_exercises(callback_query: CallbackQuery):
    user_id = callback_query.from_user.id
    user_choices[user_id]["exercise"] = None
    user_choices[user_id]["action"] = None # Reset action
    logger.info(f"{user_id}: Back to exercises called")

    ikm = markups.generate_exercise_markup(user_choices[user_id]["muscle"], user_id, show_all=False)
    bot = callback_query.bot
    await bot.edit_message_text(chat_id=callback_query.message.chat.id,
                                message_id=callback_query.message.message_id,
                                text="Select the exercise",
                                reply_markup=ikm)
    await callback_query.answer("Going back to exercises")


@router.callback_query(lambda c: c.data == "back_to_sets")
async def back_to_sets(callback_query: CallbackQuery):
    user_id = callback_query.from_user.id
    user_choices[user_id]["set"] = None
    logger.info(f"{user_id}: Back to sets called")

    ikm = markups.generate_select_set_markup(
        user_id,
        user_choices[user_id]["muscle"],
        user_choices[user_id]["exercise"]
    )
    bot = callback_query.bot
    await bot.edit_message_text(chat_id=callback_query.message.chat.id,
                                message_id=callback_query.message.message_id,
                                text="Select set",
                                reply_markup=ikm)
    await callback_query.answer("Going back to sets")


# duplicating
@router.callback_query(lambda c: c.data == "/start")
async def start_callback(callback_query: CallbackQuery):
    user_id = callback_query.from_user.id
    user_choices[user_id] = {"muscle": None, "exercise": None, "set": None, "weight": None, "reps": None, "action": None}
    logger.info(f"{user_id}: Exit 'training editing' button was clicked")
    ikm = markups.generate_start_markup()
    bot = callback_query.bot
    await bot.edit_message_text(chat_id=callback_query.message.chat.id,
                                message_id=callback_query.message.message_id,
                                text="Select the action:",
                                reply_markup=ikm)
    await callback_query.answer("Starting from scratch")


# duplicating
@router.callback_query(lambda c: c.data == "/gym")
async def gym_callback(callback_query: CallbackQuery):
    user_id = callback_query.from_user.id
    user_choices[user_id] = {"muscle": None, "exercise": None, "set": None, "weight": None, "reps": None, "action": None}
    logger.info(f"{user_id}: /gym button was clicked from start menu")

    ikm = markups.generate_muscle_markup(user_id)
    bot = callback_query.bot
    await bot.edit_message_text(chat_id=callback_query.message.chat.id,
                                message_id=callback_query.message.message_id,
                                text="Select a body part",
                                reply_markup=ikm)
    await callback_query.answer("Going back to body parts")
