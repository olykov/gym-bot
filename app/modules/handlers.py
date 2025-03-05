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

db = PostgresDB(db_name="gym_bot_db", user="myuser", password="mypassword")
sheets = GoogleSheets(os.environ.get("GOOGLE_SHEET_ID"), 'exercises')
logger = Logger(name="handlers")
router = Router()
user_choices = {}


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
    logger.info(f"{user_id}: {callback_query.data} body part selected")
    db.add_muscle(user_choices[user_id]["muscle"])

    ikm = markups.generate_exercise_markup(callback_query.data)
    bot = callback_query.bot
    await bot.edit_message_text(chat_id=callback_query.message.chat.id,
                                message_id=callback_query.message.message_id,
                                text="Select the exercise",
                                reply_markup=ikm)
    await callback_query.answer(callback_query.data)


@router.callback_query(
    lambda c: c.data in [exercise for ex_type in exercise_types for exercise in ex_type.get("exercises", [])])
async def process_exercise(callback_query: CallbackQuery):
    user_id = callback_query.from_user.id
    user_choices[user_id]["exercise"] = callback_query.data
    logger.info(f"{user_id}: {callback_query.data} exercise selected")
    db.add_exercise(exercise_name=user_choices[user_id]["exercise"],
                    muscle_name=user_choices[user_id]["muscle"])

    ikm = markups.generate_select_set_markup()
    bot = callback_query.bot
    await bot.edit_message_text(chat_id=callback_query.message.chat.id,
                                message_id=callback_query.message.message_id,
                                text="Select set",
                                reply_markup=ikm)
    await callback_query.answer(callback_query.data)


@router.callback_query(lambda c: c.data in [_set["id"] for _set in sets])
async def process_set(callback_query: CallbackQuery):
    user_id = callback_query.from_user.id
    user_choices[user_id]["set"] = callback_query.data
    logger.info(f"{user_id}: Set {callback_query.data} selected")

    ikm = markups.generate_enter_weight_markup()
    bot = callback_query.bot
    await bot.edit_message_text(chat_id=callback_query.message.chat.id,
                                message_id=callback_query.message.message_id,
                                text=f"Enter weight for set {callback_query.data}",
                                reply_markup=ikm)
    await callback_query.answer(callback_query.data)


@router.callback_query(lambda c: c.data in [f"{w}kg" for w in weights])
async def process_weight(callback_query: CallbackQuery):
    user_id = callback_query.from_user.id
    user_choices[user_id]["weight"] = callback_query.data.replace("kg", "")
    logger.info(f"{user_id}: Weight {user_choices[user_id]['weight']} selected")

    ikm = markups.generate_enter_reps_markup()
    bot = callback_query.bot
    await bot.edit_message_text(chat_id=callback_query.message.chat.id,
                                message_id=callback_query.message.message_id,
                                text=f"How many reps?",
                                reply_markup=ikm)
    await callback_query.answer(callback_query.data)


@router.callback_query(lambda c: c.data in [f"{r}_r" for r in reps])
async def process_reps(callback_query: CallbackQuery):
    user_id = callback_query.from_user.id
    user_choices[user_id]["reps"] = callback_query.data.replace("_r", "")
    logger.info(f"{user_id}: {user_choices[user_id]['reps']} reps selected")

    id_hash = get_hash(user_choices[user_id]['exercise'], 
                      datetime.now().strftime('%Y-%m-%d'), 
                      user_choices[user_id]["set"], 
                      user_choices[user_id]["weight"], 
                      user_choices[user_id]["reps"])
    
    date_now = datetime.now()
    
    save_to_db = db.save_training_data(
        id_hash,
        date_now,
        user_id,
        user_choices[user_id]['muscle'],
        user_choices[user_id]['exercise'],
        user_choices[user_id]["set"],
        user_choices[user_id]["weight"],
        user_choices[user_id]["reps"]
    )
    logger.info(f"{user_id}: {save_to_db} rows saved to db")

    # Backup
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

    message = format_result_message(user_choices, user_id)
    ikm = markups.generate_muscle_markup()
    bot = callback_query.bot
    await bot.edit_message_text(chat_id=callback_query.message.chat.id,
                                message_id=callback_query.message.message_id,
                                text=message,
                                parse_mode="HTML",
                                reply_markup=ikm)
    await callback_query.answer(callback_query.data)


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

    ikm = markups.generate_exercise_markup(user_choices[user_id]["muscle"])
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

    ikm = markups.generate_select_set_markup()
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
