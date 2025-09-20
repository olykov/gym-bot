from aiogram import Router
from aiogram.types import Message, CallbackQuery
from aiogram.filters import CommandStart, Command
import prettytable as pt
from datetime import datetime
import hashlib

from templates.exercise import exercise_types, sets, weights, reps
from .postgres import PostgresDB
from .sheets import GoogleSheets
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
sheets = GoogleSheets(os.environ.get("GOOGLE_SHEET_ID"), 'exercises')
logger = Logger(name="handlers")
router = Router()
user_choices = {}


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
    return f"Your PR: {weight}kg for {reps} reps ({formatted_date})\n\n"


@router.message(CommandStart())
async def comm_start(message: Message):
    logger.info(f"{message.from_user.id} /start has been called")
    user = check_user_registered(message)
    if not user:
        return
    user_choices[message.from_user.id] = {"muscle": None, "exercise": None, "set": None, "weight": None, "reps": None}
    ikm = markups.generate_start_markup()
    bot = message.bot
    await bot.edit_message_text(chat_id=message.message.chat.id,
                                message_id=message.message.message_id,
                                text="Select the action:",
                                reply_markup=ikm)
    await message.answer("Starting by /start calling")


@router.message(Command("gym"))
async def gym(message: Message):
    logger.info(f"{message.from_user.id} /gym has been called")
    user = check_user_registered(message)
    if not user:
        return
    user_choices[message.from_user.id] = {"muscle": None, "exercise": None, "set": None, "weight": None, "reps": None}
    ikm = markups.generate_muscle_markup()
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


@router.callback_query(lambda c: c.data in [ex_type["name"] for ex_type in exercise_types])
async def process_muscle(callback_query: CallbackQuery):
    user_id = callback_query.from_user.id
    user_choices[user_id]["muscle"] = callback_query.data
    if user_choices[user_id]["muscle"]:
        logger.info(f"{user_id}: {callback_query.data} body part selected")
        db.add_muscle(user_choices[user_id]["muscle"])

        ikm = markups.generate_exercise_markup(callback_query.data, user_id, show_all=False)
        bot = callback_query.bot
        await bot.edit_message_text(chat_id=callback_query.message.chat.id,
                                    message_id=callback_query.message.message_id,
                                    text="Select the exercise",
                                    reply_markup=ikm)
        await callback_query.answer(callback_query.data)
    else:
        user_choices[user_id] = {"muscle": None, "exercise": None, "set": None, "weight": None, "reps": None}
        ikm = markups.generate_muscle_markup()
        await callback_query.message.reply("Start this one from scratch", reply_markup=ikm)
    


@router.callback_query(
    lambda c: c.data in [exercise for ex_type in exercise_types for exercise in ex_type.get("exercises", [])])
async def process_exercise(callback_query: CallbackQuery):
    user_id = callback_query.from_user.id
    user_choices[user_id]["exercise"] = callback_query.data
    if user_choices[user_id]["exercise"]:
        logger.info(f"{user_id}: {callback_query.data} exercise selected")
        db.add_exercise(exercise_name=user_choices[user_id]["exercise"],
                        muscle_name=user_choices[user_id]["muscle"])

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
        await callback_query.answer(callback_query.data)
    else:
        user_choices[user_id] = {"muscle": None, "exercise": None, "set": None, "weight": None, "reps": None}
        ikm = markups.generate_muscle_markup()
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
        ikm = markups.generate_muscle_markup()
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
        ikm = markups.generate_muscle_markup()
        await callback_query.message.reply("Start this one from scratch", reply_markup=ikm)


@router.callback_query(lambda c: c.data in [f"{r}_r" for r in reps])
async def process_reps(callback_query: CallbackQuery):
    user_id = callback_query.from_user.id
    user_choices[user_id]["reps"] = callback_query.data.replace("_r", "")
    logger.info(f"{user_id}: {user_choices[user_id]['reps']} reps selected")
    if not user_choices[user_id]["reps"]:
        user_choices[user_id] = {"muscle": None, "exercise": None, "set": None, "weight": None, "reps": None}
        ikm = markups.generate_muscle_markup()
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
            user_choices[user_id]["weight"]
            #normalize_weight_format(user_choices[user_id]["weight"]),
            user_choices[user_id]["reps"]
        )

        bot = callback_query.bot

        # Check if database save was successful
        if save_to_db["success"]:
            logger.info(f"{user_id}: {save_to_db['rows']} rows saved to db")

            # Backup to Google Sheets only if DB save succeeded
            if "2107709598" == f"{user_id}":
                sheets.add_row(
                    id_hash,
                    date_now.strftime('%Y-%m-%d %H:%M:%S'),
                    user_choices[user_id]['muscle'],
                    user_choices[user_id]['exercise'],
                    user_choices[user_id]["set"],
                    user_choices[user_id]["weight"],
                    user_choices[user_id]["reps"]
                )
            else:
                logger.info(f"{user_id} is not admin, not saving to sheets")

            # Show success message with workout summary
            message = format_result_message(user_choices, user_id)
            ikm = markups.generate_muscle_markup()
        else:
            # Database save failed - show error message
            logger.error(f"{user_id}: Database save failed - {save_to_db['error']}")
            message = "❌ Error writing to database. Please try again."
            ikm = markups.generate_muscle_markup()

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


# Back buttons
@router.callback_query(lambda c: c.data == "back_to_muscles")
async def back_to_muscles(callback_query: CallbackQuery):
    user_id = callback_query.from_user.id
    user_choices[user_id]["muscle"] = None
    logger.info(f"{user_id}: Back to body parts called")

    ikm = markups.generate_muscle_markup()
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
    user_choices[user_id] = {"muscle": None, "exercise": None, "set": None, "weight": None, "reps": None}
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
    user_choices[user_id] = {"muscle": None, "exercise": None, "set": None, "weight": None, "reps": None}
    logger.info(f"{user_id}: /gym button was clicked from start menu")

    ikm = markups.generate_muscle_markup()
    bot = callback_query.bot
    await bot.edit_message_text(chat_id=callback_query.message.chat.id,
                                message_id=callback_query.message.message_id,
                                text="Select a body part",
                                reply_markup=ikm)
    await callback_query.answer("Going back to body parts")
