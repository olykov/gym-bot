from aiogram.types import InlineKeyboardMarkup, InlineKeyboardButton
from templates.exercise import exercise_types, sets, weights, reps


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


def generate_select_set_markup():
    inline_keyboard = []
    btn_row = []

    for _set in sets:
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