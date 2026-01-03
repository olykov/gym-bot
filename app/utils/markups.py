from aiogram.types import InlineKeyboardMarkup, InlineKeyboardButton, WebAppInfo
from templates.exercise import sets, weights, reps
from modules.postgres import PostgresDB
from modules.logging import Logger
from datetime import datetime
import os

logger = Logger(name="markups")
db = PostgresDB(
    db_name=os.environ.get("DB_NAME"),
    user=os.environ.get("DB_USER"),
    password=os.environ.get("DB_PASSWORD"),
    host=os.environ.get("DB_HOST"),
    port=os.environ.get("DB_PORT")
)

def determine_exercise_display_mode(user_id, muscle_name):
    """
    Determine whether to show compact (top N) or full exercise list.
    
    Args:
        user_id: User's Telegram ID
        muscle_name: Selected muscle group name
        
    Returns:
        tuple: (show_compact: bool, top_exercises: list)
    """
    if not user_id:
        return False, []  # Show all for users without ID
    
    try:
        top_exercises = db.get_top_exercises_for_muscle(user_id, muscle_name, 5)
        
        if len(top_exercises) == 0:
            return False, []  # No training history - show all
        
        return True, top_exercises  # Show compact with these exercises
    except Exception as e:
        logger.error(f"Error determining display mode for user {user_id}: {e}")
        return False, []  # Fallback to show all on error



def generate_start_markup():
    web_app_url = os.environ.get("WEB_APP_URL")
    if not web_app_url:
        logger.error("WEB_APP_URL not set in environment variables")
        # Fallback to avoid crash, but button won't work as expected
        web_app_url = "https://google.com"
    elif not web_app_url.startswith("https://"):
        web_app_url = f"https://{web_app_url}"

    return InlineKeyboardMarkup(
        inline_keyboard=[[
            InlineKeyboardButton(text="Record training", callback_data="/gym"),
            InlineKeyboardButton(text="Edit trainings", web_app=WebAppInfo(url=web_app_url))
        ]]
    )


def generate_edit_markup():
    return InlineKeyboardMarkup(
        inline_keyboard=[[
            InlineKeyboardButton(text="Edit today's training", callback_data="edit_today_training"),
            InlineKeyboardButton(text="Close", callback_data="/start")
        ]]
    )


def generate_muscle_markup(user_id=None):
    inline_keyboard = []
    btn_row = []

    # Get muscles from database
    muscles = db.get_all_muscles(user_id)

    for muscle in muscles:
        btn_row.append(InlineKeyboardButton(text=muscle, callback_data=f"mus_{muscle}"))
        if len(btn_row) == 3:
            inline_keyboard.append(btn_row)
            btn_row = []

    if btn_row:
        inline_keyboard.append(btn_row)

    # Add "Add Muscle" button
    inline_keyboard.append([InlineKeyboardButton(text="➕ Add Muscle", callback_data="add_muscle_btn")])
    inline_keyboard.append([InlineKeyboardButton(text="⬅️ Go back", callback_data="/start")])

    return InlineKeyboardMarkup(inline_keyboard=inline_keyboard)


def generate_post_set_markup(user_id, muscle_name, exercise_name, current_date=None):
    """
    Generate markup after completing a set.
    Shows 'Continue {exercise}' if sets remain, otherwise returns to muscle selection.

    Args:
        user_id: User's Telegram ID
        muscle_name: Selected muscle group name
        exercise_name: Selected exercise name
        current_date: Date string (YYYY-MM-DD format), defaults to today

    Returns:
        InlineKeyboardMarkup with appropriate buttons based on remaining sets
    """
    if current_date is None:
        current_date = datetime.now().strftime('%Y-%m-%d')

    try:
        # Check how many sets are completed
        completed_sets = db.get_completed_sets(user_id, muscle_name, exercise_name, current_date)
        total_sets = len(sets)  # From templates/exercise.py (currently 6 sets)

        # Scenario 1: Sets remaining → Show "Continue" + "New Exercise"
        if len(completed_sets) < total_sets:
            inline_keyboard = [
                [InlineKeyboardButton(
                    text=f"Continue {exercise_name}",
                    callback_data=f"continue_ex||{muscle_name}||{exercise_name}"
                )],
                [InlineKeyboardButton(
                    text="New Exercise",
                    callback_data="back_to_muscles"
                )]
            ]
            return InlineKeyboardMarkup(inline_keyboard=inline_keyboard)

        # Scenario 2: All sets completed → Return to muscle selection
        else:
            return generate_muscle_markup(user_id)

    except Exception as e:
        logger.error(f"Error generating post-set markup: {e}")
        # Fallback to muscle selection if we can't determine remaining sets
        return generate_muscle_markup(user_id)


def generate_exercise_markup(selected_muscle, user_id=None, show_all=False):
    """
    Generate exercise selection markup with smart compact/full display.
    """
    inline_keyboard = []
    btn_row = []

    # Get all exercises for the selected muscle from database
    all_exercises = db.get_exercises_by_muscle(selected_muscle, user_id)

    # Determine what exercises to show based on mode
    if show_all:
        # Show all exercises with smart prioritization (existing behavior)
        if user_id and all_exercises:
            try:
                # Get user's top exercises for prioritization
                top_exercises_data = db.get_top_exercises_for_muscle(user_id, selected_muscle, 5)
                top_exercise_names = [name for name, frequency in top_exercises_data]
                
                # Sort top exercises alphabetically
                top_exercises_sorted = sorted(top_exercise_names)
                
                # Get remaining exercises (preserve original order from exercise.py)
                remaining_exercises = [ex for ex in all_exercises if ex not in top_exercise_names]
                
                # Combine: top exercises first, then remaining
                exercises_to_show = top_exercises_sorted + remaining_exercises
                
                logger.info(f"User {user_id} showing all exercises for {selected_muscle} with prioritization")
                
            except Exception as e:
                logger.error(f"Error getting top exercises for user {user_id}: {e}")
                exercises_to_show = all_exercises
        else:
            exercises_to_show = all_exercises

        # Bottom buttons for "show all" mode
        bottom_buttons = [InlineKeyboardButton(text="⬅️ Go back", callback_data="back_to_muscles")]

    else:
        # Smart compact view - show only top exercises or all if no history
        show_compact, top_exercises_data = determine_exercise_display_mode(user_id, selected_muscle)
        
        if show_compact:
            # Show only top exercises (1-5 depending on user history)
            top_exercise_names = [name for name, frequency in top_exercises_data]
            exercises_to_show = sorted(top_exercise_names)  # Alphabetical order
            
            logger.info(f"User {user_id} compact view for {selected_muscle}: {len(exercises_to_show)} exercises")
            
            # Bottom buttons for compact mode
            bottom_buttons = [
                InlineKeyboardButton(text="Show All", callback_data=f"show_all_exercises_{selected_muscle}"),
                InlineKeyboardButton(text="⬅️ Go back", callback_data="back_to_muscles")
            ]
        else:
            # No training history - show all exercises (current behavior for new users)
            exercises_to_show = all_exercises
            bottom_buttons = [InlineKeyboardButton(text="⬅️ Go back", callback_data="back_to_muscles")]

    # Generate buttons for exercises
    for ex in exercises_to_show:
        btn_row.append(InlineKeyboardButton(text=ex, callback_data=f"ex_{ex}"))
        if len(btn_row) == 1:
            inline_keyboard.append(btn_row)
            btn_row = []

    if btn_row:
        inline_keyboard.append(btn_row)

    # Add "Add/Delete Exercise" buttons
    inline_keyboard.append([
        InlineKeyboardButton(text="➕ Add Exercise", callback_data="add_exercise_btn"),
        InlineKeyboardButton(text="❌ Delete Exercise", callback_data="delete_exercise_btn")
    ])

    # Add bottom buttons
    inline_keyboard.append(bottom_buttons)

    return InlineKeyboardMarkup(inline_keyboard=inline_keyboard)


def generate_delete_exercise_markup(selected_muscle, user_id=None):
    """
    Generate markup for deleting exercises.
    """
    inline_keyboard = []
    btn_row = []

    # Get all exercises for the selected muscle
    all_exercises = db.get_exercises_by_muscle(selected_muscle, user_id)

    for ex in all_exercises:
        # Use del_ex_ prefix for deletion callbacks
        btn_row.append(InlineKeyboardButton(text=f"❌ {ex}", callback_data=f"del_ex_{ex}"))
        if len(btn_row) == 1:
            inline_keyboard.append(btn_row)
            btn_row = []

    if btn_row:
        inline_keyboard.append(btn_row)

    inline_keyboard.append([InlineKeyboardButton(text="⬅️ Cancel", callback_data="back_to_exercises")])

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

    inline_keyboard.append([InlineKeyboardButton(text="⬅️ Go back", callback_data="back_to_exercises")])

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

    inline_keyboard.append([InlineKeyboardButton(text="⬅️ Go back", callback_data="back_to_sets")])
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

    inline_keyboard.append([InlineKeyboardButton(text="⬅️ Go back", callback_data="back_to_sets")])
    return InlineKeyboardMarkup(inline_keyboard=inline_keyboard)