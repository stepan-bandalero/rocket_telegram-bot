from aiogram import F, Router
from aiogram.types import Message, InlineKeyboardMarkup, InlineKeyboardButton, CallbackQuery
from aiogram.filters import Command
from sqlalchemy import func, select, desc, and_
from sqlalchemy.ext.asyncio import AsyncSession
from datetime import datetime, timezone, timedelta
from typing import Tuple, List, Dict, Optional
from decimal import Decimal

from bot.config import settings
from bot.db import SessionLocal
from bot.models.users import User
from bot.models.user_transaction import UserTransaction
from bot.models.user_spins import UserSpin
from bot.models.user_gift_upgrades import UserGiftUpgrade
from bot.models.user_gift import UserGift
from bot.models.plinko_games import PlinkoGame
from bot.models.star_invoice import StarsInvoice
import html

router = Router()

PAGE_SIZE = 8  # элементов на странице
MSK = timezone(timedelta(hours=3))




# Создадим словарь для кейсов из предоставленных данных
CASES_DATA = {
    # TON кейсы
    "case-1": {"name": "Free 24h", "cost_type": "free", "cost_value": 0},
    "case-32": {"name": "Free", "cost_type": "free", "cost_value": 0},
    "case-3": {"name": "Farm", "cost_type": "ton", "cost_value": 0.1},
    "case-13": {"name": "Farm", "cost_type": "stars", "cost_value": 10},
    "case-33": {"name": "Farm Cap", "cost_type": "stars", "cost_value": 15},
    "case-22": {"name": "Heart", "cost_type": "ton", "cost_value": 1.2},
    "case-26": {"name": "Heart", "cost_type": "stars", "cost_value": 120},
    "case-23": {"name": "Arm", "cost_type": "ton", "cost_value": 1.8},
    "case-27": {"name": "Arm", "cost_type": "stars", "cost_value": 180},
    "case-5": {"name": "Oscar", "cost_type": "ton", "cost_value": 2.5},
    "case-15": {"name": "Oscar", "cost_type": "stars", "cost_value": 250},
    "case-6": {"name": "Perfume", "cost_type": "ton", "cost_value": 2.5},
    "case-16": {"name": "Perfume", "cost_type": "stars", "cost_value": 250},
    "case-30": {"name": "Winter", "cost_type": "ton", "cost_value": 4},
    "case-31": {"name": "Winter", "cost_type": "stars", "cost_value": 400},
    "case-7": {"name": "Magic", "cost_type": "ton", "cost_value": 5},
    "case-18": {"name": "Magic", "cost_type": "stars", "cost_value": 500},
    "case-24": {"name": "Snoop", "cost_type": "ton", "cost_value": 8},
    "case-28": {"name": "Snoop", "cost_type": "stars", "cost_value": 800},
    "case-9": {"name": "Ring", "cost_type": "ton", "cost_value": 10},
    "case-19": {"name": "Ring", "cost_type": "stars", "cost_value": 1000},
    "case-25": {"name": "Gem", "cost_type": "ton", "cost_value": 10},
    "case-29": {"name": "Gem", "cost_type": "stars", "cost_value": 1000},
    "case-8": {"name": "Cap", "cost_type": "ton", "cost_value": 25},
    "case-20": {"name": "Cap", "cost_type": "stars", "cost_value": 2500},
    "case-10": {"name": "VIP", "cost_type": "ton", "cost_value": 90},
    "case-21": {"name": "VIP", "cost_type": "stars", "cost_value": 9000},
    "case-35": {"name": "Peach", "cost_type": "ton", "cost_value": 1},
    "case-36": {"name": "Peach", "cost_type": "stars", "cost_value": 100},
}

# Словарь для преобразования режимов плинко
PLINKO_MODE_NAMES = {
    "stars": "⭐ Звезды",
    "ton": "💰 TON",
    "gift": "🎁 Подарок"
}

# Словарь для преобразования типов наград
REWARD_TYPE_NAMES = {
    "stars": "⭐ Звезды",
    "ton": "💰 TON",
    "gift": "🎁 Подарок",
    "none": "❌ Нет"
}


async def get_user_activity_data(
        session: AsyncSession,
        user_id: int,
        activity_type: str,
        page: int
) -> Tuple[List, int, str, Dict]:
    """Получить данные активности пользователя по типу"""
    offset = (page - 1) * PAGE_SIZE

    if activity_type == "spins":
        # Кейсы
        stmt = (
            select(UserSpin)
            .where(UserSpin.user_id == user_id)
            .order_by(desc(UserSpin.created_at))
            .offset(offset)
            .limit(PAGE_SIZE)
        )
        total_stmt = select(func.count(UserSpin.id)).where(UserSpin.user_id == user_id)

    elif activity_type == "upgrades":
        # Апгрейды подарков с джойном для получения информации о подарке
        stmt = (
            select(UserGiftUpgrade, UserGift)
            .join(UserGift, UserGiftUpgrade.from_gift_id == UserGift.id)
            .where(UserGiftUpgrade.user_id == user_id)
            .order_by(desc(UserGiftUpgrade.created_at))
            .offset(offset)
            .limit(PAGE_SIZE)
        )
        total_stmt = select(func.count(UserGiftUpgrade.id)).where(UserGiftUpgrade.user_id == user_id)

    elif activity_type == "plinko":
        # Plinko игры с LEFT JOIN для получения информации о выигранном подарке
        stmt = (
            select(PlinkoGame, UserGift)
            .outerjoin(UserGift, PlinkoGame.won_gift_id == UserGift.id)
            .where(PlinkoGame.user_id == user_id)
            .order_by(desc(PlinkoGame.created_at))
            .offset(offset)
            .limit(PAGE_SIZE)
        )
        total_stmt = select(func.count(PlinkoGame.id)).where(PlinkoGame.user_id == user_id)

    elif activity_type == "stars":
        # Пополнения звездами
        stmt = (
            select(StarsInvoice)
            .where(and_(
                StarsInvoice.telegram_id == user_id,
                StarsInvoice.status == 'paid'
            ))
            .order_by(desc(StarsInvoice.created_at))
            .offset(offset)
            .limit(PAGE_SIZE)
        )
        total_stmt = select(func.count(StarsInvoice.id)).where(
            and_(
                StarsInvoice.telegram_id == user_id,
                StarsInvoice.status == 'paid'
            )
        )

    result = await session.execute(stmt)

    if activity_type in ["upgrades", "plinko"]:
        # Для апгрейдов и плинко возвращаем tuple
        items = result.all()
    else:
        items = result.scalars().all()

    total_result = await session.execute(total_stmt)
    total_count = total_result.scalar_one() or 0

    # Для кейсов получаем дополнительную информацию
    extra_info = {}
    if activity_type == "spins":
        # Получаем общую сумму выигрыша для отображения
        total_prize_stmt = select(func.sum(UserSpin.prize_amount)).where(UserSpin.user_id == user_id)
        total_prize_result = await session.execute(total_prize_stmt)
        total_prize = total_prize_result.scalar_one() or 0

        # Определяем тип валюты (по последнему кейсу)
        if items:
            last_case_id = items[0].case_id
            case_info = CASES_DATA.get(last_case_id, {})
            if case_info.get("cost_type") == "ton":
                total_prize = total_prize / 100  # Конвертируем из центов

        extra_info = {"total_prize": total_prize}

    return items, total_count, activity_type, extra_info




# --- Обновленная функция для форматирования сообщения активности ---


# --- Вспомогательные функции для форматирования ---
def format_prize_amount(prize_amount, case_id: str) -> str:
    """Форматировать сумму приза в зависимости от типа кейса"""
    if not prize_amount:
        return "0"

    try:
        # Проверяем, является ли prize_amount Decimal
        if isinstance(prize_amount, Decimal):
            amount_float = float(prize_amount)
        else:
            amount_float = float(prize_amount)

        # Получаем информацию о кейсе
        case_info = CASES_DATA.get(case_id, {})
        cost_type = case_info.get("cost_type", "")

        if cost_type == "ton":
            # Для TON кейсов делим на 100 (центы)
            formatted_amount = amount_float / 100
            return f"{formatted_amount:.2f} TON"
        else:
            # Для star и free кейсов отображаем как есть
            return f"{amount_float:.8f}".rstrip('0').rstrip('.')

    except (ValueError, TypeError):
        return str(prize_amount)


def get_case_info(case_id: str) -> Dict:
    """Получить информацию о кейсе"""
    return CASES_DATA.get(case_id, {
        "name": f"Unknown ({case_id})",
        "cost_type": "unknown",
        "cost_value": 0
    })


def format_cost_value(case_id: str) -> str:
    """Форматировать стоимость кейса"""
    case_info = get_case_info(case_id)
    cost_type = case_info.get("cost_type", "")
    cost_value = case_info.get("cost_value", 0)

    if cost_type == "ton":
        return f"{cost_value:.1f} TON"
    elif cost_type == "stars":
        return f"{int(cost_value)} ⭐"
    elif cost_type == "free":
        return "Бесплатно"
    else:
        return "Неизвестно"


# --- Форматирование элементов активности (обновленная версия) ---

# --- Обновленная функция форматирования элементов активности ---
def format_activity_item(index: int, item, activity_type: str) -> str:
    """Форматировать элемент активности в строку"""
    # Форматируем дату
    if activity_type in ["upgrades", "plinko"]:
        dt = item[0].created_at
    else:
        dt = item.created_at

    if dt.tzinfo is None:
        dt = dt.replace(tzinfo=timezone.utc)
    formatted_time = dt.astimezone(MSK).strftime("%d.%m.%Y %H:%M MSK")

    if activity_type == "spins":
        # Кейсы
        spin = item
        demo_mark = " 🆓" if getattr(spin, 'is_demo', False) else ""

        # Получаем информацию о кейсе
        case_info = get_case_info(spin.case_id)
        case_name = case_info.get("name", spin.case_id)
        cost_type = case_info.get("cost_type", "")

        # Форматируем приз
        if cost_type == "ton":
            # Для TON кейсов конвертируем
            prize_value = float(spin.prize_amount) / 100 if spin.prize_amount else 0
            prize_str = f"{prize_value:.8f}".rstrip('0').rstrip('.') + " TON"
        else:
            # Для других типов как есть
            prize_str = f"{spin.prize_amount:.8f}".rstrip('0').rstrip('.') if spin.prize_amount else "0"

        # Форматируем стоимость
        cost_str = format_cost_value(spin.case_id)

        return (
            f"<b>#{index}</b> 🎡 <b>{case_name}</b>{demo_mark}\n"
            f"┣ 💰 <b>Стоимость:</b> {cost_str}\n"
            f"┣ 🏆 <b>Приз:</b> {spin.prize_title}\n"
            f"┣ 🎁 <b>Сумма:</b> {prize_str}\n"
            f"┗ 🕒 <i>{formatted_time}</i>\n"
            f"┄┄┄┄┄┄┄┄┄┄┄┄┄┄┄┄"
        )

    elif activity_type == "upgrades":
        # Апгрейды
        upgrade = item[0]
        user_gift = item[1] if len(item) > 1 else None

        success_icon = "✅" if upgrade.success else "❌"
        chance_pct = round(upgrade.chance * 100, 1)

        # Получаем информацию о подарке
        gift_info = ""
        if user_gift:
            # Получаем стоимость подарка (делим на 100 если в центах)
            price = user_gift.price_cents / 100 if user_gift.price_cents else 0
            gift_catalog_id = getattr(user_gift, 'gift_catalog_id', 'Unknown')
            gift_info = f"\n┣ 🎁 <b>Подарок:</b> {gift_catalog_id}\n┣ 💰 <b>Стоимость:</b> {price:.2f} TON"

        return (
            f"<b>#{index}</b> ⚡ <b>Апгрейд</b> {success_icon}\n"
            f"┣ 🎯 <b>Цель:</b> <code>{upgrade.target_gift_id}</code>"
            f"{gift_info}"
            f"\n┣ 🎲 <b>Шанс:</b> {chance_pct}%\n"
            f"┗ 🕒 <i>{formatted_time}</i>\n"
            f"┄┄┄┄┄┄┄┄┄┄┄┄┄┄┄┄"
        )

    elif activity_type == "plinko":
        # Plinko
        game = item[0]
        won_gift = item[1] if len(item) > 1 else None

        # Преобразуем режим
        mode_name = PLINKO_MODE_NAMES.get(game.mode, game.mode)

        # Форматируем ставку
        bet_amount = 0
        if game.bet_amount:
            if game.mode == "ton":
                bet_amount = game.bet_amount / 100
            elif game.mode == "stars":
                bet_amount = game.bet_amount
            else:
                bet_amount = game.bet_amount

        # Получаем название типа награды
        reward_type_name = REWARD_TYPE_NAMES.get(game.reward_type, game.reward_type)
        reward_icon = "💰" if game.reward_type == "ton" else "⭐" if game.reward_type == "stars" else "🎁"

        multiplier = f"{game.multiplier:.2f}x"

        # Определяем, выиграл ли пользователь
        result_lines = []

        if game.reward_type == "none" or game.reward_amount == 0:
            result_lines.append("❌ <b>Результат:</b> Проигрыш")
        else:
            # Форматируем выигрыш
            reward_amount = 0
            if game.reward_amount:
                if game.reward_type == "ton":
                    reward_amount = game.reward_amount / 100
                else:
                    reward_amount = game.reward_amount

            result_lines.append(f"✅ <b>Выигрыш:</b> {reward_amount:.2f} {reward_type_name.split()[-1]}")

            # Добавляем информацию о выигранном подарке, если есть
            if won_gift:
                gift_catalog_id = getattr(won_gift, 'gift_catalog_id', 'Unknown')
                gift_price = won_gift.price_cents / 100 if won_gift.price_cents else 0
                result_lines.append(f"🎁 <b>Подарок:</b> {gift_catalog_id}")
                if gift_price > 0:
                    result_lines.append(f"💰 <b>Стоимость подарка:</b> {gift_price:.2f} TON")

        # Объединяем строки результата
        result_text = "\n┣ ".join(result_lines)

        return (
            f"<b>#{index}</b> 🎯 <b>Плинко</b>\n"
            f"┣ 🎮 <b>Режим:</b> {mode_name}\n"
            f"┣ 🎲 <b>Ставка:</b> {bet_amount:.2f}\n"
            f"┣ ⚡ <b>Множитель:</b> {multiplier}\n"
            f"┣ {result_text}\n"
            f"┗ 🕒 <i>{formatted_time}</i>\n"
            f"┄┄┄┄┄┄┄┄┄┄┄┄┄┄┄┄"
        )

    elif activity_type == "stars":
        # Звезды
        invoice = item
        status_icon = "✅" if invoice.status == 'paid' else "⏳"

        # Получаем время обработки, если есть
        processed_time = ""
        if invoice.processed_at:
            pt = invoice.processed_at
            if pt.tzinfo is None:
                pt = pt.replace(tzinfo=timezone.utc)
            processed_time = f"\n┣ ⏰ <b>Обработано:</b> {pt.astimezone(MSK).strftime('%d.%m.%Y %H:%M MSK')}"

        return (
            f"<b>#{index}</b> ⭐ <b>Пополнение</b> {status_icon}\n"
            f"┣ 💫 <b>Звезд:</b> {invoice.amount}\n"
            f"┣ 📋 <b>ID:</b> <code>{invoice.id}</code>\n"
            f"┗ 🕒 <i>{formatted_time}</i>\n"
            f"┄┄┄┄┄┄┄┄┄┄┄┄┄┄┄┄"
        )


# --- Обновленная функция для форматирования сообщения активности ---
def format_activity_message(
        user_id: int,
        activity_type: str,
        page: int,
        total_pages: int,
        total_count: int,
        items: List,
        extra_info: Dict = None
) -> str:
    """Создать сообщение с активностью"""
    type_names = {
        "spins": "🎡 Кейсы",
        "upgrades": "⚡ Апгрейды подарков",
        "plinko": "🎯 Игры в плинко",
        "stars": "⭐ Пополнения звездами"
    }

    type_name = type_names.get(activity_type, "Активность")

    # Базовый заголовок
    header = (
        f"👤 <b>Активность пользователя</b>\n"
        f"🆔 <code>{user_id}</code>\n\n"
        f"📂 <b>{type_name}</b>\n"
        f"📄 Страница: <b>{page}/{total_pages}</b>\n"
        f"📊 Всего записей: <b>{total_count}</b>\n"
    )

    # Добавляем дополнительную информацию для кейсов
    if activity_type == "spins" and extra_info and "total_prize" in extra_info:
        total_prize = extra_info["total_prize"]
        if isinstance(total_prize, (int, float)):
            header += f"💰 <b>Общий выигрыш:</b> {total_prize:.8f}".rstrip('0').rstrip('.') + "\n"

    header += "\n"

    if not items:
        return header + "📭 <i>На этой странице нет записей</i>"

    # Форматируем элементы
    items_text = "\n".join([
        format_activity_item(i + 1 + (page - 1) * PAGE_SIZE, item, activity_type)
        for i, item in enumerate(items)
    ])

    return header + items_text


# --- Формирование клавиатуры активности ---
def build_activity_keyboard(
        user_id: int,
        activity_type: str,
        current_page: int,
        total_pages: int
) -> InlineKeyboardMarkup:
    """Создать клавиатуру для навигации по активности"""
    buttons = []

    # Кнопки пагинации
    if current_page > 2:
        buttons.append(InlineKeyboardButton(
            text="⏪ 1",
            callback_data=f"act_page:{user_id}:{activity_type}:1"
        ))
    if current_page > 1:
        buttons.append(InlineKeyboardButton(
            text="◀️ Назад",
            callback_data=f"act_page:{user_id}:{activity_type}:{current_page - 1}"
        ))

    buttons.append(InlineKeyboardButton(
        text=f"{current_page}/{total_pages}",
        callback_data="current_page_act"
    ))

    if current_page < total_pages:
        buttons.append(InlineKeyboardButton(
            text="Вперёд ▶️",
            callback_data=f"act_page:{user_id}:{activity_type}:{current_page + 1}"
        ))
    if current_page < total_pages - 1:
        buttons.append(InlineKeyboardButton(
            text=f"{total_pages} ⏩",
            callback_data=f"act_page:{user_id}:{activity_type}:{total_pages}"
        ))

    # Кнопки переключения типа активности
    type_buttons = []
    types_data = [
        ("🎡 Кейсы", "spins"),
        ("⚡ Апгрейды", "upgrades"),
        ("🎯 Плинко", "plinko"),
        ("⭐ Звезды", "stars")
    ]

    for label, act_type in types_data:
        if act_type != activity_type:  # Текущий тип не показываем
            type_buttons.append(InlineKeyboardButton(
                text=label,
                callback_data=f"act_type:{user_id}:{act_type}:1"
            ))

    keyboard = []

    # Добавляем кнопки пагинации
    if len(buttons) <= 3:
        keyboard.append(buttons)
    elif len(buttons) == 4:
        keyboard.append(buttons[:2])
        keyboard.append(buttons[2:])
    else:
        keyboard.append(buttons[:2])
        keyboard.append([buttons[2]])
        keyboard.append(buttons[3:])

    # Добавляем кнопки переключения типа
    if type_buttons:
        keyboard.append(type_buttons[:2])
        if len(type_buttons) > 2:
            keyboard.append(type_buttons[2:])

    # Кнопка возврата в меню
    keyboard.append([
        InlineKeyboardButton(
            text="🔙 Выбрать тип",
            callback_data=f"act_menu:{user_id}"
        )
    ])

    return InlineKeyboardMarkup(inline_keyboard=keyboard)


# --- Клавиатура выбора типа активности ---
def build_activity_type_keyboard(user_id: int) -> InlineKeyboardMarkup:
    """Клавиатура для выбора типа активности"""
    keyboard = InlineKeyboardMarkup(inline_keyboard=[
        [
            InlineKeyboardButton(
                text="🎡 Кейсы",
                callback_data=f"act_type:{user_id}:spins:1"
            ),
            InlineKeyboardButton(
                text="⚡ Апгрейды",
                callback_data=f"act_type:{user_id}:upgrades:1"
            )
        ],
        [
            InlineKeyboardButton(
                text="🎯 Плинко",
                callback_data=f"act_type:{user_id}:plinko:1"
            ),
            InlineKeyboardButton(
                text="⭐ Звезды",
                callback_data=f"act_type:{user_id}:stars:1"
            )
        ],
        [
            InlineKeyboardButton(
                text="📊 Общая статистика",
                callback_data=f"act_stats:{user_id}"
            )
        ],
        # [
        #     InlineKeyboardButton(
        #         text="🔙 Назад",
        #         callback_data="act_back"
        #     )
        # ]
    ])
    return keyboard


# --- Форматирование заголовка активности ---
def format_activity_header(user_id: int, activity_type: str, page: int, total_pages: int, total_count: int) -> str:
    """Создать заголовок для активности"""
    type_names = {
        "spins": "🎡 Кейсы",
        "upgrades": "⚡ Апгрейды подарков",
        "plinko": "🎯 Игры в плинко",
        "stars": "⭐ Пополнения звездами"
    }

    type_name = type_names.get(activity_type, "Активность")

    return (
        f"👤 <b>Активность пользователя</b>\n"
        f"🆔 <code>{user_id}</code>\n\n"
        f"📂 <b>{type_name}</b>\n"
        f"📄 Страница: <b>{page}/{total_pages}</b>\n"
        f"📊 Всего записей: <b>{total_count}</b>\n\n"
    )


# --- Команда /activity ---
@router.message(Command("activity"))
async def activity_command(message: Message):
    """Обработчик команды /activity"""
    if message.from_user.id not in settings.admins:
        await message.answer("⛔ У вас нет доступа к этой команде.")
        return

    # Проверяем аргументы
    args = message.text.split()
    if len(args) < 2:
        await message.answer(
            "📝 <b>Использование команды:</b>\n"
            "<code>/activity user_id</code>\n\n"
            "Пример:\n"
            "<code>/activity 123456789</code>"
        )
        return

    try:
        user_id = int(args[1])
    except ValueError:
        await message.answer("❌ Неверный формат ID пользователя.")
        return

    # Проверяем существование пользователя
    async with SessionLocal() as session:
        user_stmt = select(User).where(User.telegram_id == user_id)
        user_result = await session.execute(user_stmt)
        user = user_result.scalar_one_or_none()

        if not user:
            await message.answer(f"❌ Пользователь с ID <code>{user_id}</code> не найден.")
            return

        # Получаем общую статистику
        stats_text = await get_user_statistics(session, user_id, user)

        # Показываем меню выбора типа активности
        text = (
            f"👤 <b>Пользователь:</b> <code>{user_id}</code>\n"
            f"📛 Имя:{html.escape(user.first_name) if user.first_name else '—'}\n"
            f"🔗 Юзернейм: @{user.username or 'Не указан'}\n"
            f"💰 Баланс TON: {user.ton_balance / 100 if user.ton_balance else 0:.2f}\n"
            f"⭐ Баланс звезд: {user.stars_balance or 0}\n\n"
            f"{stats_text}\n\n"
            f"👇 <b>Выберите тип активности для просмотра:</b>"
        )

        kb = build_activity_type_keyboard(user_id)
        await message.answer(text, parse_mode="HTML", reply_markup=kb)


# --- Получение общей статистики пользователя ---
async def get_user_statistics(session: AsyncSession, user_id: int, user: User) -> str:
    """Получить общую статистику пользователя"""
    # Количество кейсов
    spins_count = await session.execute(
        select(func.count(UserSpin.id)).where(UserSpin.user_id == user_id)
    )
    spins = spins_count.scalar_one() or 0

    # Количество апгрейдов
    upgrades_count = await session.execute(
        select(func.count(UserGiftUpgrade.id)).where(UserGiftUpgrade.user_id == user_id)
    )
    upgrades = upgrades_count.scalar_one() or 0

    # Количество игр в плинко
    plinko_count = await session.execute(
        select(func.count(PlinkoGame.id)).where(PlinkoGame.user_id == user_id)
    )
    plinko = plinko_count.scalar_one() or 0

    # Сумма пополненных звезд
    stars_sum = await session.execute(
        select(func.sum(StarsInvoice.amount)).where(
            and_(
                StarsInvoice.telegram_id == user_id,
                StarsInvoice.status == 'paid'
            )
        )
    )
    stars = stars_sum.scalar_one() or 0

    # Общее количество транзакций
    transactions_count = await session.execute(
        select(func.count(UserTransaction.id)).where(UserTransaction.user_id == user_id)
    )
    transactions = transactions_count.scalar_one() or 0

    return (
        f"📊 <b>Статистика активности:</b>\n"
        f"├─ 🎡 Кейсов: <b>{spins}</b>\n"
        f"├─ ⚡ Апгрейдов: <b>{upgrades}</b>\n"
        f"├─ 🎯 Игр в плинко: <b>{plinko}</b>\n"
        f"├─ ⭐ Звезд пополнено: <b>{stars}</b>\n"
        f"└─ 💰 Транзакций: <b>{transactions}</b>"
    )


# --- Обновленный обработчик выбора типа активности ---
@router.callback_query(F.data.startswith("act_type:"))
async def handle_activity_type(cb: CallbackQuery):
    """Обработчик выбора типа активности"""
    try:
        _, user_id_str, activity_type, page_str = cb.data.split(":")
        user_id = int(user_id_str)
        page = int(page_str)

        async with SessionLocal() as session:
            items, total_count, activity_type, extra_info = await get_user_activity_data(
                session, user_id, activity_type, page
            )

            total_pages = max((total_count + PAGE_SIZE - 1) // PAGE_SIZE, 1)

            if page < 1 or page > total_pages:
                await cb.answer("❌ Такой страницы не существует!")
                return

            # Формируем сообщение с использованием новой функции
            text = format_activity_message(
                user_id, activity_type, page, total_pages, total_count, items, extra_info
            )

            kb = build_activity_keyboard(user_id, activity_type, page, total_pages)

            await cb.message.edit_text(text, reply_markup=kb, parse_mode="HTML")
            await cb.answer()

    except Exception as e:
        print(f"Error in handle_activity_type: {e}")
        await cb.answer("⚠️ Ошибка при загрузке активности!")


# --- Обновленный обработчик пагинации активности ---
@router.callback_query(F.data.startswith("act_page:"))
async def handle_activity_page(cb: CallbackQuery):
    """Обработчик пагинации активности"""
    try:
        _, user_id_str, activity_type, page_str = cb.data.split(":")
        user_id = int(user_id_str)
        page = int(page_str)

        async with SessionLocal() as session:
            items, total_count, activity_type, extra_info = await get_user_activity_data(
                session, user_id, activity_type, page
            )

            total_pages = max((total_count + PAGE_SIZE - 1) // PAGE_SIZE, 1)

            if page < 1 or page > total_pages:
                await cb.answer("❌ Такой страницы не существует!")
                return

            text = format_activity_message(
                user_id, activity_type, page, total_pages, total_count, items, extra_info
            )

            kb = build_activity_keyboard(user_id, activity_type, page, total_pages)

            await cb.message.edit_text(text, reply_markup=kb, parse_mode="HTML")
            await cb.answer()

    except Exception as e:
        print(f"Error in handle_activity_page: {e}")
        await cb.answer("⚠️ Ошибка при загрузке страницы!")


# --- Обработка кнопки "Общая статистика" ---
@router.callback_query(F.data.startswith("act_stats:"))
async def handle_activity_stats(cb: CallbackQuery):
    """Показать общую статистику пользователя"""
    try:
        _, user_id_str = cb.data.split(":")
        user_id = int(user_id_str)

        async with SessionLocal() as session:
            user_stmt = select(User).where(User.telegram_id == user_id)
            user_result = await session.execute(user_stmt)
            user = user_result.scalar_one_or_none()

            if not user:
                await cb.answer("❌ Пользователь не найден!")
                return

            stats_text = await get_user_statistics(session, user_id, user)

            text = (
                f"👤 <b>Пользователь:</b> <code>{user_id}</code>\n"
                f"📛 Имя: {user.first_name or 'Не указано'}\n"
                f"🔗 Юзернейм: @{user.username or 'Не указан'}\n"
                f"💰 Баланс TON: {user.ton_balance / 100 if user.ton_balance else 0:.2f}\n"
                f"⭐ Баланс звезд: {user.stars_balance or 0}\n\n"
                f"{stats_text}\n\n"
                f"👇 <b>Выберите тип активности для просмотра:</b>"
            )

            kb = build_activity_type_keyboard(user_id)
            await cb.message.edit_text(text, reply_markup=kb, parse_mode="HTML")
            await cb.answer("📊 Статистика обновлена")

    except Exception as e:
        print(f"Error in handle_activity_stats: {e}")
        await cb.answer("⚠️ Ошибка при загрузке статистики!")


# --- Обработка возврата к меню ---
@router.callback_query(F.data.startswith("act_menu:"))
async def handle_activity_menu(cb: CallbackQuery):
    """Вернуться к выбору типа активности"""
    try:
        _, user_id_str = cb.data.split(":")
        user_id = int(user_id_str)

        async with SessionLocal() as session:
            user_stmt = select(User).where(User.telegram_id == user_id)
            user_result = await session.execute(user_stmt)
            user = user_result.scalar_one_or_none()

            if not user:
                await cb.answer("❌ Пользователь не найден!")
                return

            stats_text = await get_user_statistics(session, user_id, user)

            text = (
                f"👤 <b>Пользователь:</b> <code>{user_id}</code>\n"
                f"📛 Имя: {user.first_name or 'Не указано'}\n"
                f"🔗 Юзернейм: @{user.username or 'Не указан'}\n"
                f"💰 Баланс TON: {user.ton_balance / 100 if user.ton_balance else 0:.2f}\n"
                f"⭐ Баланс звезд: {user.stars_balance or 0}\n\n"
                f"{stats_text}\n\n"
                f"👇 <b>Выберите тип активности для просмотра:</b>"
            )

            kb = build_activity_type_keyboard(user_id)
            await cb.message.edit_text(text, reply_markup=kb, parse_mode="HTML")
            await cb.answer("↩️ Возврат в меню")

    except Exception as e:
        print(f"Error in handle_activity_menu: {e}")
        await cb.answer("⚠️ Ошибка при возврате в меню!")


# --- Обработка кнопки "Назад" ---
@router.callback_query(F.data == "act_back")
async def handle_activity_back(cb: CallbackQuery):
    """Обработчик кнопки "Назад" в меню выбора типа"""
    await cb.message.delete()
    await cb.answer("🗑️ Меню закрыто")


# --- Обработка текущей страницы ---
@router.callback_query(F.data == "current_page_act")
async def handle_current_page_act(cb: CallbackQuery):
    """Обработчик нажатия на текущую страницу"""
    await cb.answer("📄 Вы уже на этой странице.")