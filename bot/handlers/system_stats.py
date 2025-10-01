from aiogram import Bot, Router
from aiogram.types import Message
from aiogram.filters import Command
import aiohttp
import json

from bot.config import settings

router = Router()


@router.message(Command("system_stats"))
async def cmd_system_stats(message: Message, bot: Bot):
    """Статистика системы и ресурсов сервера"""
    if message.from_user.id not in settings.admins:
        return

    await send_system_stats(message, bot)


async def get_system_stats():
    """Получение статистики системы с game сервера"""
    try:
        async with aiohttp.ClientSession() as session:
            async with session.get("https://rocket-app.top/api/system-stats", timeout=10) as response:
                if response.status == 200:
                    return await response.json()
                else:
                    return None
    except Exception as e:
        print(f"Error getting system stats: {e}")
        return None


async def get_online_users():
    """Получение количества онлайн пользователей"""
    try:
        async with aiohttp.ClientSession() as session:
            async with session.get("https://rocket-app.top/api/online-users-count", timeout=5) as response:
                if response.status == 200:
                    data = await response.json()
                    return data.get("online_users", "N/A")
    except Exception as e:
        print(f"Error getting online users: {e}")
    return "N/A"


async def get_detailed_online_users():
    """Получение детальной информации об онлайн пользователях"""
    try:
        async with aiohttp.ClientSession() as session:
            async with session.get("https://rocket-app.top/api/online-users", timeout=5) as response:
                if response.status == 200:
                    return await response.json()
    except Exception as e:
        print(f"Error getting detailed online users: {e}")
    return None


def format_bytes(bytes_size):
    """Форматирование байтов в читаемый вид"""
    for unit in ['B', 'KB', 'MB', 'GB', 'TB']:
        if bytes_size < 1024.0:
            return f"{bytes_size:.1f} {unit}"
        bytes_size /= 1024.0
    return f"{bytes_size:.1f} PB"


def get_health_status(cpu_usage, memory_usage):
    """Определение статуса здоровья системы"""
    if cpu_usage < 70 and memory_usage < 80:
        return "🟢 НОРМА"
    elif cpu_usage < 90 and memory_usage < 90:
        return "🟡 ВНИМАНИЕ"
    else:
        return "🔴 КРИТИЧЕСКИ"


async def send_system_stats(message: Message, bot: Bot):
    """Отправка статистики системы админу"""


    # Получаем все данные параллельно
    system_stats = await get_system_stats()
    online_users_count = await get_online_users()
    detailed_online = await get_detailed_online_users()

    if not system_stats:
        await message.answer("❌ <b>ОШИБКА</b>\nНе удалось получить данные с game сервера",
                             parse_mode="HTML")
        return

    # Основные метрики
    cpu_usage = float(system_stats['cpu']['usage'])
    memory_usage = system_stats['memory']['usage']
    health_status = get_health_status(cpu_usage, memory_usage)

    # Детали по памяти
    memory_total = system_stats['memory']['total']
    memory_used = system_stats['memory']['used']

    # Сетевая активность
    network_rx = system_stats['network']['rx_sec']
    network_tx = system_stats['network']['tx_sec']

    # Load average
    load_avg = system_stats.get('load', {})


    # Процессы
    processes = system_stats['processes']

    # Детальная информация об онлайн пользователях
    online_details = ""
    if detailed_online:
        active_users = detailed_online.get('active', 0)
        total_connections = detailed_online.get('total_connections', 0)
        online_details = f"├─ 🔥 Активные: <b>{active_users}</b>\n└─ 🔗 Коннекты: <b>{total_connections}</b>\n"

    # Форматируем текст сообщения
    text = f"""
🖥️ <b>СИСТЕМНАЯ СТАТИСТИКА</b>
⏰ {system_stats.get('timestamp', 'N/A')}
{'=' * 40}

📊 <b>СОСТОЯНИЕ СИСТЕМЫ</b>
├─ 🩺 Статус: <b>{health_status}</b>
├─ ⏱️ Время ответа: <b>{(await get_response_time()):.2f}мс</b>
└─ 🕐 Таймстамп: <b>{system_stats.get('timestamp', 'N/A')}</b>

🔧 <b>ПРОЦЕССОР (CPU)</b>
├─ 📊 Загрузка: <b>{cpu_usage}%</b>
├─ 👤 Пользователь: <b>{system_stats['cpu']['user']}%</b>
├─ ⚙️ Система: <b>{system_stats['cpu']['system']}%</b>
└─ 🎯 Ядра: <b>{system_stats['cpu']['cores']}</b>

💾 <b>ПАМЯТЬ (RAM)</b>
├─ 📊 Использование: <b>{memory_usage}%</b>
├─ 💿 Всего: <b>{memory_total} MB</b>
├─ 🚀 Использовано: <b>{memory_used} MB</b>
└─ 📉 Свободно: <b>{system_stats['memory']['free']} MB</b>

🌐 <b>СЕТЬ</b>
├─ 📥 Прием: <b>{format_bytes(network_rx)}/сек</b>
└─ 📤 Передача: <b>{format_bytes(network_tx)}/сек</b>

📈 <b>НАГРУЗКА (LOAD AVERAGE)</b>
├─ 1 мин: <b>{load_avg.get('avg1', 0):.2f}</b>
├─ 5 мин: <b>{load_avg.get('avg5', 0):.2f}</b>
└─ 15 мин: <b>{load_avg.get('avg15', 0):.2f}</b>

⚙️ <b>ПРОЦЕССЫ</b>
├─ 📊 Всего: <b>{processes['total']}</b>
├─ 🏃‍♂️ Выполняются: <b>{processes['running']}</b>
└─ ⏸️ Заблокированы: <b>{processes['blocked']}</b>

👥 <b>ОНЛАЙН ПОЛЬЗОВАТЕЛИ</b>
├─ 🌐 Всего онлайн: <b>{online_users_count}</b>
{online_details if online_details else "└─ ⚠️ Детали недоступны"}
"""

    await message.answer(text, parse_mode="HTML")


async def get_response_time():
    """Измерение времени ответа сервера"""
    import time
    try:
        start_time = time.time()
        async with aiohttp.ClientSession() as session:
            async with session.get("https://rocket-app.top/api/health", timeout=5) as response:
                if response.status == 200:
                    return (time.time() - start_time) * 1000  # в миллисекундах
    except:
        pass
    return 0.0


# Дополнительная команда для быстрого просмотра
@router.message(Command("health"))
async def cmd_health(message: Message, bot: Bot):
    """Быстрая проверка здоровья системы"""
    if message.from_user.id not in settings.admins:
        return

    system_stats = await get_system_stats()
    online_users = await get_online_users()

    if not system_stats:
        await message.answer("🔴 <b>СЕРВЕР НЕДОСТУПЕН</b>", parse_mode="HTML")
        return

    cpu_usage = float(system_stats['cpu']['usage'])
    memory_usage = system_stats['memory']['usage']
    health_status = get_health_status(cpu_usage, memory_usage)

    text = f"""
🩺 <b>БЫСТРАЯ ПРОВЕРКА ЗДОРОВЬЯ</b>
{'=' * 25}

📊 Статус: <b>{health_status}</b>
🔢 CPU: <b>{cpu_usage}%</b>
💾 RAM: <b>{memory_usage}%</b>
👥 Онлайн: <b>{online_users}</b>
⏱️ Ответ: <b>{(await get_response_time()):.2f}мс</b>
"""

    await message.answer(text, parse_mode="HTML")