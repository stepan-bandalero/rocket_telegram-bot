# bot/states/broadcast.py (упрощенная)
from aiogram.fsm.state import State, StatesGroup


class BroadcastStates(StatesGroup):
    editing_text = State()
    editing_media = State()
    waiting_forward = State()

    adding_button_text = State()
    adding_button_url = State()
    adding_button_page = State()
    adding_button_case = State()
    adding_button_style = State()
    adding_button_emoji = State()
    adding_button_confirm = State()
