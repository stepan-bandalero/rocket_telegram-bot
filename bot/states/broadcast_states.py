from aiogram.fsm.state import State, StatesGroup


class BroadcastStates(StatesGroup):
    waiting_type = State()
    waiting_text = State()
    waiting_media = State()
    waiting_buttons = State()
    confirm = State()
