from aiogram import F, Router
from aiogram.types import Message, InlineKeyboardButton, InlineKeyboardMarkup, CallbackQuery
from sqlalchemy import func
from sqlalchemy.future import select
from sqlalchemy.ext.asyncio import AsyncSession
from bot.db import SessionLocal
from bot.models.users import User

router = Router()

PAGE_SIZE = 10  # пользователей на странице


async def get_users_page(session: AsyncSession, page: int):
    offset = (page - 1) * PAGE_SIZE
    stmt = select(User).order_by(User.telegram_id).offset(offset).limit(PAGE_SIZE)
    result = await session.execute(stmt)
    users = result.scalars().all()

    total_stmt = select(func.count(User.telegram_id))
    total_result = await session.execute(total_stmt)
    total_count = total_result.scalar_one()

    return users, total_count


def build_users_keyboard(current_page: int, total_pages: int) -> InlineKeyboardMarkup:
    buttons = []

    if current_page > 1:
        buttons.append(InlineKeyboardButton("⬅️ Назад", callback_data=f"user_page:{current_page - 1}"))
    if current_page < total_pages:
        buttons.append(InlineKeyboardButton("Вперед ➡️", callback_data=f"user_page:{current_page + 1}"))

    if buttons:
        kb = InlineKeyboardMarkup()
        kb.row(*buttons)
        return kb
    else:
        # если кнопок нет, возвращаем пустую клавиатуру
        return InlineKeyboardMarkup(inline_keyboard=[])


def format_user_line(index: int, user: User) -> str:
    username = f"@{user.username}" if user.username else "—"
    ref = f"🟢 Реферал: {user.referred_by}" if user.referred_by else ""
    balance_val = user.ton_balance if user.ton_balance is not None else 0
    balance = f"💰 {balance_val / 100:.2f} TON"
    return f"{index:02d}. <b>{user.first_name}</b> {username} | {balance} {ref}"


@router.message(F.text.startswith("/users"))
async def list_users(message: Message):
    page = 1
    async with SessionLocal() as session:
        users, total_count = await get_users_page(session, page)

    total_pages = max((total_count + PAGE_SIZE - 1) // PAGE_SIZE, 1)

    header = f"📋 <b>Пользователи</b> (страница {page}/{total_pages})\n"
    separator = "―" * 40 + "\n"
    user_lines = [format_user_line(i + 1 + (page - 1) * PAGE_SIZE, u) for i, u in enumerate(users)]
    text = header + separator + "\n".join(user_lines) + "\n" + separator

    kb = build_users_keyboard(page, total_pages)
    await message.answer(text, reply_markup=kb, parse_mode="HTML")


@router.callback_query(F.data.startswith("user_page:"))
async def paginate_users(cb: CallbackQuery):
    page = int(cb.data.split(":")[1])
    async with SessionLocal() as session:
        users, total_count = await get_users_page(session, page)

    total_pages = max((total_count + PAGE_SIZE - 1) // PAGE_SIZE, 1)

    header = f"📋 <b>Пользователи</b> (страница {page}/{total_pages})\n"
    separator = "―" * 40 + "\n"
    user_lines = [format_user_line(i + 1 + (page - 1) * PAGE_SIZE, u) for i, u in enumerate(users)]
    text = header + separator + "\n".join(user_lines) + "\n" + separator

    kb = build_users_keyboard(page, total_pages)
    await cb.message.edit_text(text, reply_markup=kb, parse_mode="HTML")
    await cb.answer()
