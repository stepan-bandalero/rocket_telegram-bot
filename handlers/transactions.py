from aiogram import F, Router
from aiogram.types import Message, InlineKeyboardMarkup, InlineKeyboardButton, CallbackQuery
from sqlalchemy import func, select, desc
from sqlalchemy.ext.asyncio import AsyncSession
from datetime import datetime, timezone, timedelta

from config import settings
from db import SessionLocal
from models.user_transaction import UserTransaction

router = Router()

PAGE_SIZE = 8  # транзакций на странице
MSK = timezone(timedelta(hours=3))

# --- Запрос страницы транзакций ---
async def get_transactions_page(session: AsyncSession, page: int):
    offset = (page - 1) * PAGE_SIZE

    stmt = (
        select(UserTransaction)
        .order_by(desc(UserTransaction.created_at))
        .offset(offset)
        .limit(PAGE_SIZE)
    )

    result = await session.execute(stmt)
    transactions = result.scalars().all()

    total_stmt = select(func.count(UserTransaction.id))
    total_result = await session.execute(total_stmt)
    total_count = total_result.scalar_one()

    return transactions, total_count


# --- Формирование клавиатуры ---
def build_transactions_keyboard(current_page: int, total_pages: int) -> InlineKeyboardMarkup:
    buttons = []

    if current_page > 2:
        buttons.append(InlineKeyboardButton(text="⏪ 1", callback_data=f"tx_page:1"))
    if current_page > 1:
        buttons.append(InlineKeyboardButton(text="◀️ Назад", callback_data=f"tx_page:{current_page - 1}"))

    buttons.append(InlineKeyboardButton(text=f"{current_page}/{total_pages}", callback_data="current_page_tx"))

    if current_page < total_pages:
        buttons.append(InlineKeyboardButton(text="Вперёд ▶️", callback_data=f"tx_page:{current_page + 1}"))
    if current_page < total_pages - 1:
        buttons.append(InlineKeyboardButton(text=f"{total_pages} ⏩", callback_data=f"tx_page:{total_pages}"))

    keyboard = []

    if len(buttons) <= 3:
        keyboard.append(buttons)
    elif len(buttons) == 4:
        keyboard.append(buttons[:2])
        keyboard.append(buttons[2:])
    else:
        keyboard.append(buttons[:2])
        keyboard.append([buttons[2]])
        keyboard.append(buttons[3:])

    return InlineKeyboardMarkup(inline_keyboard=keyboard)


# --- Форматирование строки транзакции ---
def format_transaction_line(index: int, tx: UserTransaction) -> str:
    # Форматируем дату
    dt = tx.created_at
    if dt.tzinfo is None:
        dt = dt.replace(tzinfo=timezone.utc)
    formatted_time = dt.astimezone(MSK).strftime("%d.%m.%Y %H:%M:%S MSK")

    # Тип операции
    type_label = "💰 Пополнение" if tx.type == "deposit" else "📤 Списание"
    currency_icon = "🎁 Gift" if tx.currency == "gift" else "💎 TON"

    # Сумма (делим на 2 и округляем до 2 знаков)
    amount_val = round(tx.amount / 100, 2)  # если amount хранится в сотнях
    amount_str = f"{amount_val:.2f}"

    return (
        f"<b>#{index}</b> {type_label}\n"
        f"┣ 🧾 <b>Тип:</b> {currency_icon}\n"
        f"┣ 👤 <b>User ID:</b> <code>{tx.user_id}</code>\n"
        f"┣ 💸 <b>Сумма:</b> {amount_str}\n"
        f"┗ 🕒 <i>{formatted_time}</i>\n"
        f"┄┄┄┄┄┄┄┄┄┄┄┄┄┄┄┄"
    )


# --- Формирование общего сообщения ---
def format_transactions_message(transactions: list[UserTransaction], page: int, total_pages: int, total_count: int) -> str:
    header = (
        f"💼 <b>ИСТОРИЯ ТРАНЗАКЦИЙ</b>\n\n"
        f"📄 Страница: <b>{page}/{total_pages}</b>\n"
        f"🧾 Всего записей: <b>{total_count}</b>\n\n"
    )

    if not transactions:
        return header + "📭 <i>На этой странице нет транзакций</i>"

    tx_lines = [
        format_transaction_line(i + 1 + (page - 1) * PAGE_SIZE, tx)
        for i, tx in enumerate(transactions)
    ]

    return header + "\n".join(tx_lines)


# --- Команда /transactions ---
@router.message(F.text.startswith("/transactions"))
async def list_transactions(message: Message):
    if message.from_user.id not in settings.admins:
        return

    page = 1
    async with SessionLocal() as session:
        transactions, total_count = await get_transactions_page(session, page)

    total_pages = max((total_count + PAGE_SIZE - 1) // PAGE_SIZE, 1)
    text = format_transactions_message(transactions, page, total_pages, total_count)
    kb = build_transactions_keyboard(page, total_pages)

    await message.answer(text, parse_mode="HTML", reply_markup=kb)


# --- Пагинация ---
@router.callback_query(F.data.startswith("tx_page:"))
async def paginate_transactions(cb: CallbackQuery):
    try:
        page = int(cb.data.split(":")[1])
        async with SessionLocal() as session:
            transactions, total_count = await get_transactions_page(session, page)

        total_pages = max((total_count + PAGE_SIZE - 1) // PAGE_SIZE, 1)

        if page < 1 or page > total_pages:
            await cb.answer("❌ Такой страницы не существует!")
            return

        text = format_transactions_message(transactions, page, total_pages, total_count)
        kb = build_transactions_keyboard(page, total_pages)

        await cb.message.edit_text(text, reply_markup=kb, parse_mode="HTML")
        await cb.answer()
    except Exception as e:
        await cb.answer("⚠️ Ошибка при загрузке страницы!")


# --- Обработка нажатия на текущую страницу ---
@router.callback_query(F.data == "current_page_tx")
async def handle_current_page(cb: CallbackQuery):
    await cb.answer("📄 Вы уже на этой странице.")
