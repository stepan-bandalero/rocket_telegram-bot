# bot/states/broadcast.py (упрощенная)
from aiogram.fsm.state import State, StatesGroup


class BroadcastStates(StatesGroup):
    editing_text = State()
    editing_media = State()
    editing_buttons = State()