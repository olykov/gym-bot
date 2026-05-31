from aiogram.fsm.state import State, StatesGroup


class UserStates(StatesGroup):
    """FSM states for user conversation flow."""
    # Main conversation flow
    selecting_muscle = State()
    selecting_exercise = State()
    selecting_set = State()
    selecting_weight = State()
    selecting_reps = State()

    # Edit flow
    waiting_muscle_name = State()
    waiting_exercise_name = State()
    deleting_exercise = State()
