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


def generate_exercise_markup(selected_muscle):
    inline_keyboard = []
    btn_row = []

    for ex_type in exercise_types:
        if ex_type["name"] == selected_muscle:
            for ex in ex_type["exercises"]:
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
    available_sets = [s for s in sets if s['id'] not in completed_sets]
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