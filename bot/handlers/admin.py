from aiogram import Router, Bot
from aiogram.filters import Command
from aiogram.types import Message

from bot.config import settings
from bot.services.stats import send_admin_stats
from bot.utils.keyboards import broadcast_main_kb

router = Router()




@router.message(Command("stats"))
async def cmd_stats(message: Message, bot: Bot, session):
    """Панель с общей информацией о системе"""
    if message.from_user.id not in settings.admins:
        return
    await send_admin_stats(message, bot, session)


@router.message(Command("broadcast"))
async def broadcast_command(message: Message):
    """Быстрый доступ к рассылкам"""
    if message.from_user.id not in settings.admins:
        return

    await message.answer(
        "📊 <b>Управление рассылками</b>\n\n"
        "Выберите действие:",
        reply_markup=broadcast_main_kb()
    )



@router.message(Command("admin"))
async def admin_panel(message: Message):
    """Главная панель администратора"""
    if message.from_user.id not in settings.admins:
        return

    admin_commands = [
        {
            "command": "/stats",
            "description": "📊 Панель с общей информацией о системе",
            "usage": "Просто введите команду",
            "status": "✅ Активна"
        },
        {
            "command": "/broadcast",
            "description": "📢 Управление рассылками сообщений",
            "usage": "Открывает меню рассылок",
            "status": "✅ Активна"
        },
        {
            "command": "/users",
            "description": "👥 Просмотр списка пользователей с пагинацией",
            "usage": "Просто введите команду",
            "status": "✅ Активна"
        },
        {
            "command": "/add_channel",
            "description": "➕ Добавление нового канала",
            "usage": "/add_channel &lt;ID&gt; &lt;Название&gt; &lt;URL&gt;",
            "status": "✅ Активна"
        },
        {
            "command": "/delete_channel",
            "description": "🗑️ Удаление канала",
            "usage": "/delete_channel &lt;ID_канала&gt;",
            "status": "✅ Активна"
        },
        {
            "command": "/channels",
            "description": "📋 Просмотр списка всех каналов",
            "usage": "Просто введите команду",
            "status": "✅ Активна"
        },
        {
            "command": "/add_promo",
            "description": "🎁 Создание промо-ссылки",
            "usage": "/add_promo &lt;Название_промо&gt;",
            "status": "✅ Активна"
        },
        {
            "command": "/promos",
            "description": "📊 Статистика по промо-ссылкам",
            "usage": "Просто введите команду",
            "status": "✅ Активна"
        },
        {
            "command": "/delete_promo",
            "description": "❌ Удаление промо-ссылки",
            "usage": "/delete_promo &lt;Код_промо&gt;",
            "status": "✅ Активна"
        },
        {
            "command": "/user_info",
            "description": "👤 Подробная информация о пользователе",
            "usage": "/user_info &lt;ID_пользователя&gt;",
            "status": "🔄 В разработке"
        },
        {
            "command": "/referral_stats",
            "description": "📈 Реферальная статистика пользователя",
            "usage": "/referral_stats &lt;ID_пользователя&gt;",
            "status": "🔄 В разработке"
        },
        {
            "command": "/add_gift",
            "description": "🎁 Добавление подарка в инвентарь",
            "usage": "/add_gift &lt;ID_пользователя&gt; &lt;Ссылка_на_подарок&gt;",
            "status": "✅ Активна"
        },
        {
            "command": "/manage_balance",
            "description": "💰 Управление балансом TON",
            "usage": "/manage_balance &lt;ID&gt; &lt; +/-/= &gt; &lt;Сумма&gt;",
            "status": "✅ Активна"
        },
        {
            "command": "/transactions",
            "description": "💳 Просмотр списка транзакций",
            "usage": "Просто введите команду",
            "status": "🔄 В разработке"
        }
    ]

    # Разделяем команды на активные и в разработке
    active_commands = [cmd for cmd in admin_commands if cmd["status"] == "✅ Активна"]
    developing_commands = [cmd for cmd in admin_commands if cmd["status"] == "🔄 В разработке"]

    text = format_admin_panel(active_commands, developing_commands)
    await message.answer(text, parse_mode="HTML", disable_web_page_preview=True)

def format_admin_panel(active_commands, developing_commands):
    """Форматирование панели администратора"""



    # Активные команды
    active_section = "✅ <b>АКТИВНЫЕ КОМАНДЫ</b>\n"
    for cmd in active_commands:
        active_section += (
            f"\n🔹 <b>{cmd['command']}</b>\n"
            f"{cmd['description']}\n"
            f"<blockquote>{cmd['usage']}</blockquote>\n"
        )

    # Команды в разработке
    developing_section = "\n🛠️ <b>В РАЗРАБОТКЕ</b>\n"
    for cmd in developing_commands:
        developing_section += (
            f"\n⚙️ <b>{cmd['command']}</b>\n"
            f"{cmd['description']}\n"
            f"<blockquote>{cmd['usage']}</blockquote>\n"
        )



    return active_section + developing_section



