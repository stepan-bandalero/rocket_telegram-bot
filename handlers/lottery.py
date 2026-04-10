from __future__ import annotations

import re
from datetime import datetime
from zoneinfo import ZoneInfo

from aiogram import Router, F
from aiogram.types import Message, CallbackQuery, BufferedInputFile, InlineKeyboardMarkup
from aiogram.filters import Command, StateFilter
from aiogram.fsm.context import FSMContext
from aiogram.utils.keyboard import InlineKeyboardBuilder

from db import SessionLocal
from models.Lottery import Lottery
from models.LotteryTicket import LotteryTicket
from models.LotteryWinner import LotteryWinner
from models.gift_catalog import GiftCatalog
from states.create_lottery import CreateLottery
from utils.lottery import generate_lottery_preview
from config import settings


router = Router()


# -------------------------------------------------------------------
# Вспомогательные функции
# -------------------------------------------------------------------


def parse_datetime(date_str: str) -> datetime | None:
    pattern = r'^(\d{2})\.(\d{2})\.(\d{4})\s+(\d{2}):(\d{2})$'
    match = re.match(pattern, date_str.strip())
    if not match:
        return None
    day, month, year, hour, minute = map(int, match.groups())
    tz = ZoneInfo("Europe/Moscow")
    try:
        return datetime(year, month, day, hour, minute, tzinfo=tz)
    except ValueError:
        return None


def get_cancel_button() -> InlineKeyboardMarkup:
    """Кнопка отмены для любого шага."""
    kb = InlineKeyboardBuilder()
    kb.button(text="❌ Отмена", callback_data="cancel_creation", style="danger")
    return kb.as_markup()


# -------------------------------------------------------------------
# Команды
# -------------------------------------------------------------------


@router.message(Command("create"))
async def cmd_create(message: Message, state: FSMContext):
    if message.from_user.id not in settings.admins:
        return
    await state.set_state(CreateLottery.title)
    await message.answer(
        "Введите название лотереи:",
        reply_markup=get_cancel_button()
    )


@router.message(Command("cancel"))
async def cmd_cancel(message: Message, state: FSMContext):
    if message.from_user.id not in settings.admins:
        return
    await state.clear()
    await message.answer("Действие отменено.")


@router.callback_query(F.data == "cancel_creation")
async def cancel_callback(callback: CallbackQuery, state: FSMContext):
    await callback.answer()
    await state.clear()
    await callback.message.edit_text("❌ Создание лотереи отменено.")


# -------------------------------------------------------------------
# Ввод названия
# -------------------------------------------------------------------


@router.message(CreateLottery.title)
async def process_title(message: Message, state: FSMContext):
    if message.from_user.id not in settings.admins:
        return
    await state.update_data(title=message.text)
    description = "🎉 Участвуй и выигрывай!"
    await state.update_data(description=description)

    kb = InlineKeyboardBuilder()
    kb.button(text="💰 Платная", callback_data="type_paid")
    kb.button(text="🎁 Бесплатная", callback_data="type_free")
    await state.set_state(CreateLottery.type)
    await message.answer(
        "Выберите тип лотереи:",
        reply_markup=kb.as_markup()
    )


# -------------------------------------------------------------------
# Выбор типа
# -------------------------------------------------------------------


@router.callback_query(StateFilter(CreateLottery.type), F.data.startswith("type_"))
async def process_type(callback: CallbackQuery, state: FSMContext):
    await callback.answer()
    t = callback.data.split("_")[1]  # paid / free
    await state.update_data(type=t)

    if t == "paid":
        await state.set_state(CreateLottery.ticket_price_stars)
        await callback.message.edit_text(
            "Введите стоимость билета в звёздах (целое число):",
            reply_markup=get_cancel_button()
        )
    else:
        # Бесплатная лотерея: автоматом ставим max_tickets_per_user = 1, остальное None
        await state.update_data(
            ticket_price_stars=None,
            max_tickets_per_user=1,
            max_total_tickets=None
        )
        await state.set_state(CreateLottery.prize_gift_id)
        await callback.message.edit_text(
            "Введите ID приза (текст):",
            reply_markup=get_cancel_button()
        )


# -------------------------------------------------------------------
# Ввод цены билета (для платной)
# -------------------------------------------------------------------


@router.message(CreateLottery.ticket_price_stars)
async def process_ticket_price(message: Message, state: FSMContext):
    if message.from_user.id not in settings.admins:
        return
    if not message.text.isdigit():
        await message.answer(
            "❌ Пожалуйста, введите целое число.",
            reply_markup=get_cancel_button()
        )
        return
    await state.update_data(ticket_price_stars=int(message.text))
    await state.set_state(CreateLottery.prize_gift_id)
    await message.answer(
        "Введите ID приза (текст):",
        reply_markup=get_cancel_button()
    )


# -------------------------------------------------------------------
# Ввод ID приза
# -------------------------------------------------------------------


@router.message(CreateLottery.prize_gift_id)
async def process_prize_gift_id(message: Message, state: FSMContext):
    if message.from_user.id not in settings.admins:
        return
    prize_id = message.text.strip()
    # Проверяем существование приза в базе
    async with SessionLocal() as session:
        gift = await session.get(GiftCatalog, prize_id)
        if not gift:
            await message.answer(
                f"❌ Приз с ID '{prize_id}' не найден. Проверьте ID и попробуйте снова:",
                reply_markup=get_cancel_button()
            )
            return
    await state.update_data(prize_gift_id=prize_id)
    await state.set_state(CreateLottery.winners_count)
    await message.answer(
        "Введите количество победителей (целое число > 0):",
        reply_markup=get_cancel_button()
    )


# -------------------------------------------------------------------
# Ввод количества победителей
# -------------------------------------------------------------------


@router.message(CreateLottery.winners_count)
async def process_winners_count(message: Message, state: FSMContext):
    if message.from_user.id not in settings.admins:
        return
    if not message.text.isdigit() or int(message.text) <= 0:
        await message.answer(
            "❌ Пожалуйста, введите положительное целое число.",
            reply_markup=get_cancel_button()
        )
        return
    await state.update_data(winners_count=int(message.text))
    await state.set_state(CreateLottery.results_date)
    await message.answer(
        "Введите дату и время розыгрыша в формате ДД.ММ.ГГГГ ЧЧ:ММ\n"
        "Например: 01.03.2026 15:00",
        reply_markup=get_cancel_button()
    )


# -------------------------------------------------------------------
# Ввод даты розыгрыша
# -------------------------------------------------------------------


@router.message(CreateLottery.results_date)
async def process_results_date(message: Message, state: FSMContext):
    if message.from_user.id not in settings.admins:
        return
    dt = parse_datetime(message.text)
    if dt is None:
        await message.answer(
            "❌ Неверный формат. Используйте ДД.ММ.ГГГГ ЧЧ:ММ",
            reply_markup=get_cancel_button()
        )
        return
    if dt < datetime.now(ZoneInfo("Europe/Moscow")):
        await message.answer(
            "❌ Дата не может быть в прошлом. Введите будущую дату.",
            reply_markup=get_cancel_button()
        )
        return
    await state.update_data(results_date=dt.isoformat())

    await show_preview(message, state)


# -------------------------------------------------------------------
# Ввод максимума билетов на пользователя (только для paid)
# -------------------------------------------------------------------


@router.message(CreateLottery.max_tickets_per_user)
async def process_max_per_user(message: Message, state: FSMContext):
    if message.from_user.id not in settings.admins:
        return
    if not message.text.isdigit():
        await message.answer(
            "❌ Введите число.",
            reply_markup=get_cancel_button()
        )
        return
    val = int(message.text)
    await state.update_data(max_tickets_per_user=val if val > 0 else None)
    await state.set_state(CreateLottery.max_total_tickets)
    await message.answer(
        "Введите максимальное общее количество билетов (0 — без ограничений):",
        reply_markup=get_cancel_button()
    )


# -------------------------------------------------------------------
# Ввод общего максимума билетов
# -------------------------------------------------------------------


@router.message(CreateLottery.max_total_tickets)
async def process_max_total(message: Message, state: FSMContext):
    if message.from_user.id not in settings.admins:
        return
    if not message.text.isdigit():
        await message.answer(
            "❌ Введите число.",
            reply_markup=get_cancel_button()
        )
        return
    val = int(message.text)
    await state.update_data(max_total_tickets=val if val > 0 else None)
    await show_preview(message, state)


# -------------------------------------------------------------------
# Функция показа предпросмотра
# -------------------------------------------------------------------


async def show_preview(message: Message, state: FSMContext):
    data = await state.get_data()
    await message.answer("⏳ Генерирую предпросмотр...")

    try:
        image_bytes = await generate_lottery_preview(data)
        # Отправляем фото
        await message.answer_photo(
            BufferedInputFile(image_bytes, filename="preview.png"),
            caption="📸 Вот как будет выглядеть карточка лотереи. Всё верно?"
        )
        # Кнопки подтверждения
        kb = InlineKeyboardBuilder()
        kb.button(text="✅ Да, сохранить", callback_data="confirm_yes", style="success")
        kb.button(text="🔄 Нет, изменить", callback_data="confirm_no", style="danger")
        kb.button(text="❌ Отмена", callback_data="cancel_creation")
        kb.adjust(2)
        await state.set_state(CreateLottery.confirm)
        await message.answer(
            "Подтверждаете создание?",
            reply_markup=kb.as_markup()
        )
    except Exception as e:
        await message.answer(f"❌ Ошибка при генерации: {e}")
        await state.clear()


# -------------------------------------------------------------------
# Подтверждение создания (сохранение в БД)
# -------------------------------------------------------------------


@router.callback_query(StateFilter(CreateLottery.confirm), F.data == "confirm_yes")
async def confirm_yes(callback: CallbackQuery, state: FSMContext):
    await callback.answer()
    data = await state.get_data()

    # Преобразуем дату
    results_date = datetime.fromisoformat(data["results_date"])

    # Создаём запись лотереи
    new_lottery = Lottery(
        title=data["title"],
        description=data.get("description", "🎉 Участвуй и выигрывай!"),
        type=data["type"],
        ticket_price_stars=data.get("ticket_price_stars"),
        prize_gift_id=data["prize_gift_id"],
        winners_count=data["winners_count"],
        results_date=results_date,
        status="active",
        max_tickets_per_user=data.get("max_tickets_per_user"),
        max_total_tickets=data.get("max_total_tickets"),
        tickets_sold_count=0
    )

    async with SessionLocal() as session:
        session.add(new_lottery)
        await session.commit()
        await session.refresh(new_lottery)

    await callback.message.edit_text(
        f"✅ Лотерея успешно создана!\n"
        f"ID: `{new_lottery.id}`\n"
        f"Название: {new_lottery.title}",
        parse_mode="Markdown"
    )
    await state.clear()


@router.callback_query(StateFilter(CreateLottery.confirm), F.data == "confirm_no")
async def confirm_no(callback: CallbackQuery, state: FSMContext):
    await callback.answer()
    await callback.message.edit_text(
        "🔄 Хорошо, давайте начнём заново. Введите название лотереи:"
    )
    await state.set_state(CreateLottery.title)
