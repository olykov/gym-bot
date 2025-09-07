from aiogram.types import InlineKeyboardMarkup, InlineKeyboardButton
from templates.exercise import exercise_types, sets, weights, reps
from modules.postgres import PostgresDB
from modules.logging import Logger
from datetime import datetime

logger = Logger(name="markups")
db = PostgresDB(db_name="gym_bot_db", user="myuser", password="mypassword")



def generate_start_markup():
    return InlineKeyboardMarkup(
        inline_keyboard=[[
            InlineKeyboardButton(text="Record training", callback_data="/gym"),
            InlineKeyboardButton(text="Edit trainings", callback_data="/edit")
        ]]
    )


def generate_edit_markup():
    return InlineKeyboardMarkup(
        inline_keyboard=[[
            InlineKeyboardButton(text="Edit today's training", callback_data="edit_today_training"),
            InlineKeyboardButton(text="Close", callback_data="/start")
        ]]
    )


def generate_muscle_markup():
    inline_keyboard = []
    btn_row = []

    for ex_type in exercise_types:
        btn_row.append(InlineKeyboardButton(text=ex_type["name"], callback_data=ex_type["name"]))
        if len(btn_row) == 3:
            inline_keyboard.append(btn_row)
            btn_row = []

    if btn_row:
        inline_keyboard.append(btn_row)

    inline_keyboard.append([InlineKeyboardButton(text="Back", callback_data="/start")])

    return InlineKeyboardMarkup(inline_keyboard=inline_keyboard)


def generate_exercise_markup(selected_muscle, user_id=None):
    """
    Generate exercise selection markup with user's top exercises prioritized.
    
    Args:
        selected_muscle: Name of the selected muscle group
        user_id: User's Telegram ID for personalization (optional)
    
    Returns:
        InlineKeyboardMarkup with exercises reordered by user preference
    """
    inline_keyboard = []
    btn_row = []

    # Get all exercises for the selected muscle from exercise.py
    all_exercises = []
    for ex_type in exercise_types:
        if ex_type["name"] == selected_muscle:
            all_exercises = ex_type["exercises"]
            break

    # Initialize variables for ranking
    top_exercises_sorted = []
    
    # Reorder exercises based on user's training history
    if user_id and all_exercises:
        try:
            # Get user's top exercises for this muscle group
            top_exercises_data = db.get_top_exercises_for_muscle(user_id, selected_muscle, 5)
            top_exercise_names = [name for name, frequency in top_exercises_data]
            
            # Sort top exercises alphabetically
            top_exercises_sorted = sorted(top_exercise_names)
            
            # Get remaining exercises (preserve original order from exercise.py)
            remaining_exercises = [ex for ex in all_exercises if ex not in top_exercise_names]
            
            # Combine: top exercises first, then remaining
            reordered_exercises = top_exercises_sorted + remaining_exercises
            
            logger.info(f"User {user_id} top exercises for {selected_muscle}: {top_exercise_names}")
            
        except Exception as e:
            logger.error(f"Error getting top exercises for user {user_id}: {e}")
            # Fallback to original order on any error
            reordered_exercises = all_exercises
            top_exercises_sorted = []  # Reset on error
    else:
        # No user_id provided or no exercises - use original order
        reordered_exercises = all_exercises

    # Generate buttons for reordered exercises (smart prioritization without emojis)
    for ex in reordered_exercises:
        # Create button with clean exercise name for both text and callback data
        btn_row.append(InlineKeyboardButton(text=ex, callback_data=ex))
        if len(btn_row) == 1:
            inline_keyboard.append(btn_row)
            btn_row = []

    if btn_row:
        inline_keyboard.append(btn_row)

    inline_keyboard.append([InlineKeyboardButton(text="Back", callback_data="back_to_muscles")])

    return InlineKeyboardMarkup(inline_keyboard=inline_keyboard)


def generate_select_set_markup(user_id, muscle, exercise):
    inline_keyboard = []
    btn_row = []

    todays_date = datetime.now().strftime('%Y-%m-%d')
    completed_sets = db.get_completed_sets(user_id, muscle, exercise, todays_date)
    try:
        available_sets = [s for s in sets if int(s['id']) not in completed_sets]
    except:
        logger.error("Can't get available sets")
        available_sets = sets
    logger.info(completed_sets)
    logger.info(available_sets)

    # If all sets are completed, show message
    if not available_sets:
        inline_keyboard.append([InlineKeyboardButton(text="All sets completed!", callback_data="/start")])
    else:
        for _set in available_sets:
            btn_row.append(InlineKeyboardButton(text=_set["name"], callback_data=_set['id']))
            if len(btn_row) == 6:
                inline_keyboard.append(btn_row)
                btn_row = []

        if btn_row:
            inline_keyboard.append(btn_row)

    inline_keyboard.append([InlineKeyboardButton(text="Back", callback_data="back_to_exercises")])

    return InlineKeyboardMarkup(inline_keyboard=inline_keyboard)


def generate_enter_weight_markup():
    inline_keyboard = []
    btn_row = []

    for w in weights:
        btn_row.append(InlineKeyboardButton(text=f"{w}", callback_data=f"{w}kg"))
        if len(btn_row) == 7:
            inline_keyboard.append(btn_row)
            btn_row = []

    if btn_row:
        inline_keyboard.append(btn_row)

    inline_keyboard.append([InlineKeyboardButton(text="Back", callback_data="back_to_sets")])
    return InlineKeyboardMarkup(inline_keyboard=inline_keyboard)


def generate_enter_reps_markup():
    inline_keyboard = []
    btn_row = []

    for r in reps:
        btn_row.append(InlineKeyboardButton(text=f"{r}", callback_data=f"{r}_r"))
        if len(btn_row) == 8:
            inline_keyboard.append(btn_row)
            btn_row = []

    if btn_row:
        inline_keyboard.append(btn_row)

    inline_keyboard.append([InlineKeyboardButton(text="Back", callback_data="back_to_sets")])
    return InlineKeyboardMarkup(inline_keyboard=inline_keyboard)