from aiogram.fsm.state import State, StatesGroup


class CreateLottery(StatesGroup):
    title = State()
    description = State()
    type = State()
    ticket_price_stars = State()
    prize_gift_id = State()
    winners_count = State()
    results_date = State()
    max_tickets_per_user = State()
    max_total_tickets = State()
    confirm = State()