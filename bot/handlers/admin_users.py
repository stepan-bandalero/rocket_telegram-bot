from aiogram import F, Router
from aiogram.types import Message, InlineKeyboardButton, InlineKeyboardMarkup, CallbackQuery
from sqlalchemy import func
from sqlalchemy.future import select
from sqlalchemy.ext.asyncio import AsyncSession

from bot.config import settings
from bot.db import SessionLocal
from bot.models.users import User

router = Router()

PAGE_SIZE = 8  # пользователей на странице (меньше для лучшего вида)


async def get_users_page(session: AsyncSession, page: int):
    offset = (page - 1) * PAGE_SIZE
    # Сортировка сначала по балансу (убывание), потом по telegram_id
    stmt = select(User).order_by(User.ton_balance.desc(), User.telegram_id).offset(offset).limit(PAGE_SIZE)
    result = await session.execute(stmt)
    users = result.scalars().all()

    total_stmt = select(func.count(User.telegram_id))
    total_result = await session.execute(total_stmt)
    total_count = total_result.scalar_one()

    return users, total_count


def build_users_keyboard(current_page: int, total_pages: int) -> InlineKeyboardMarkup:
    buttons = []

    # Добавляем кнопку первой страницы если мы не на ней
    if current_page > 2:
        buttons.append(InlineKeyboardButton("⏪ 1", callback_data=f"user_page:1"))

    if current_page > 1:
        buttons.append(InlineKeyboardButton("◀️ Назад", callback_data=f"user_page:{current_page - 1}"))

    # Кнопка текущей страницы
    buttons.append(InlineKeyboardButton(f"{current_page}/{total_pages}", callback_data="current_page"))

    if current_page < total_pages:
        buttons.append(InlineKeyboardButton("Вперед ▶️", callback_data=f"user_page:{current_page + 1}"))

    # Добавляем кнопку последней страницы если мы не на ней
    if current_page < total_pages - 1:
        buttons.append(InlineKeyboardButton(f"{total_pages} ⏩", callback_data=f"user_page:{total_pages}"))

    kb = InlineKeyboardMarkup(inline_keyboard=[])
    if buttons:
        # Разбиваем кнопки на строки для лучшего отображения
        if len(buttons) > 3:
            kb.row(buttons[0], buttons[1])  # ⏪ и ◀️
            kb.row(buttons[2])  # текущая страница
            kb.row(buttons[3], buttons[4])  # ▶️ и ⏩
        else:
            kb.row(*buttons)

    return kb


def format_user_line(index: int, user: User) -> str:
    # Эмодзи для топ-3 позиций
    rank_emoji = {1: "🥇", 2: "🥈", 3: "🥉"}
    rank_icon = rank_emoji.get(index, f"#{index:02d}")

    username = f"@{user.username}" if user.username else "—"
    first_name = user.first_name or "Не указано"

    # Форматирование баланса
    balance_val = user.ton_balance if user.ton_balance is not None else 0
    balance = f"{balance_val / 100:.2f} TON"

    # Красивое оформление в зависимости от позиции
    if index <= 3:
        user_header = f"{rank_icon} <b>🏆 ТОП-{index}</b>"
    else:
        user_header = f"{rank_icon} <b>{first_name}</b>"

    return (
        f"{user_header}\n"
        f"┣ 👤 {username}\n"
        f"┣ 🆔 {user.telegram_id}\n"
        f"┣ 💰 {balance}\n"
        f"┗ 📊 Реф: {user.referred_by or '—'}\n"
        f"┄┄┄┄┄┄┄┄┄┄┄┄┄┄┄┄"
    )


def format_users_message(users: list, page: int, total_pages: int, total_count: int) -> str:
    # Заголовок с красивым оформлением
    header = (
        f"📊 <b>СПИСОК ПОЛЬЗОВАТЕЛЕЙ</b>\n"
        f"┏━━━━━━━━━━━━━━━━━━━━━━━┓\n"
        f"┃ 📄 Страница: <b>{page}/{total_pages}</b>     ┃\n"
        f"┃ 👥 Всего: <b>{total_count}</b> пользователей ┃\n"
        f"┗━━━━━━━━━━━━━━━━━━━━━━━┛\n\n"
    )

    # Формируем список пользователей
    user_lines = [
        format_user_line(i + 1 + (page - 1) * PAGE_SIZE, user)
        for i, user in enumerate(users)
    ]

    # Если пользователей нет
    if not user_lines:
        return header + "📭 <i>На этой странице пока нет пользователей</i>"

    return header + "\n".join(user_lines)


@router.message(F.text.startswith("/users"))
async def list_users(message: Message):
    if message.from_user.id not in settings.admins:
        return
    page = 1
    async with SessionLocal() as session:
        users, total_count = await get_users_page(session, page)

    total_pages = max((total_count + PAGE_SIZE - 1) // PAGE_SIZE, 1)

    text = format_users_message(users, page, total_pages, total_count)
    kb = build_users_keyboard(page, total_pages)

    await message.answer(text, parse_mode="HTML", reply_markup=kb)


@router.callback_query(F.data.startswith("user_page:"))
async def paginate_users(cb: CallbackQuery):
    try:
        page = int(cb.data.split(":")[1])
        async with SessionLocal() as session:
            users, total_count = await get_users_page(session, page)

        total_pages = max((total_count + PAGE_SIZE - 1) // PAGE_SIZE, 1)

        # Проверяем, что запрашиваемая страница существует
        if page < 1 or page > total_pages:
            await cb.answer("❌ Эта страница не существует!")
            return

        text = format_users_message(users, page, total_pages, total_count)
        kb = build_users_keyboard(page, total_pages)

        await cb.message.edit_text(text, reply_markup=kb, parse_mode="HTML")
        await cb.answer()

    except ValueError:
        await cb.answer("❌ Ошибка пагинации!")
    except Exception as e:
        await cb.answer("❌ Произошла ошибка!")


@router.callback_query(F.data == "current_page")
async def handle_current_page(cb: CallbackQuery):
    """Обработчик нажатия на кнопку текущей страницы"""
    await cb.answer(f"📄 Вы на этой странице!")