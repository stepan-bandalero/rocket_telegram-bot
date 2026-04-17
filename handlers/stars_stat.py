import io
from datetime import datetime

import matplotlib.pyplot as plt
import matplotlib.dates as mdates
from aiogram import F, Router
from aiogram.types import Message, BufferedInputFile
from sqlalchemy import select, func, and_, desc
from sqlalchemy.ext.asyncio import AsyncSession

from config import settings
from db import SessionLocal
from models.star_invoice import StarsInvoice
from models.users import User

router = Router()



async def get_stars_statistics(session: AsyncSession):
    """Собирает базовую статистику + топы по разовым пополнениям."""
    paid_filter = StarsInvoice.status == "paid"

    # Общие суммы
    total_res = await session.execute(
        select(
            func.sum(StarsInvoice.amount).label("total_sum"),
            func.count(StarsInvoice.id).label("total_count")
        ).where(paid_filter)
    )
    total_sum, total_count = total_res.one()
    total_sum = total_sum or 0
    total_count = total_count or 0

    # Помесячная группировка
    monthly_query = (
        select(
            func.date_trunc('month', StarsInvoice.created_at).label("month"),
            func.sum(StarsInvoice.amount).label("month_sum"),
            func.count(StarsInvoice.id).label("month_count")
        )
        .where(paid_filter)
        .group_by("month")
        .order_by("month")
    )
    monthly_res = await session.execute(monthly_query)
    monthly_data = {}
    for row in monthly_res:
        month_start = row.month
        key = month_start.strftime("%Y-%m")
        monthly_data[key] = {
            "sum": int(row.month_sum),
            "count": row.month_count,
            "month_start": month_start
        }

    # Топ разовых пополнений за всё время (максимальный amount)
    all_time_top_query = (
        select(
            StarsInvoice.telegram_id,
            User.username,
            User.first_name,
            StarsInvoice.amount,
            StarsInvoice.created_at
        )
        .join(User, StarsInvoice.telegram_id == User.telegram_id)
        .where(paid_filter)
        .order_by(desc(StarsInvoice.amount))
        .limit(5)
    )
    all_time_top_res = await session.execute(all_time_top_query)
    all_time_top = [dict(row) for row in all_time_top_res.mappings().all()]

    # Топ разовых пополнений за текущий месяц
    now = datetime.now()
    month_start = datetime(now.year, now.month, 1)
    month_top_query = (
        select(
            StarsInvoice.telegram_id,
            User.username,
            User.first_name,
            StarsInvoice.amount,
            StarsInvoice.created_at
        )
        .join(User, StarsInvoice.telegram_id == User.telegram_id)
        .where(and_(paid_filter, StarsInvoice.created_at >= month_start))
        .order_by(desc(StarsInvoice.amount))
        .limit(5)
    )
    month_top_res = await session.execute(month_top_query)
    month_top = [dict(row) for row in month_top_res.mappings().all()]

    return {
        "total_sum": total_sum,
        "total_count": total_count,
        "monthly_data": monthly_data,
        "all_time_top": all_time_top,
        "month_top": month_top,
    }




def generate_monthly_chart(monthly_data: dict) -> io.BytesIO:
    """
    Строит столбчатую диаграмму по месяцам: сумма звёзд.
    Возвращает BytesIO с PNG-изображением.
    """
    if not monthly_data:
        return None

    # Сортируем месяцы хронологически
    sorted_months = sorted(monthly_data.items(), key=lambda x: x[0])

    # Преобразуем строки 'YYYY-MM' в объекты datetime для корректной оси X
    dates = [datetime.strptime(month_str, "%Y-%m") for month_str, _ in sorted_months]
    sums = [data["sum"] for _, data in sorted_months]

    plt.figure(figsize=(10, 5))
    # width=20 задаёт ширину столбцов в днях (примерно 2/3 месяца)
    bars = plt.bar(dates, sums, color='#F4B41A', edgecolor='#D4941A', linewidth=1.2, width=20)

    # Подписи значений над столбцами
    for bar, val in zip(bars, sums):
        plt.text(
            bar.get_x() + bar.get_width() / 2,
            bar.get_height() + (max(sums) * 0.02),
            f"{val:,}".replace(",", " "),
            ha='center',
            va='bottom',
            fontsize=10,
            weight='bold'
        )

    # Убираем эмодзи из заголовка, чтобы избежать предупреждений о шрифтах
    plt.title("Пополнения звёзд по месяцам", fontsize=16, pad=15)
    plt.xlabel("Месяц", fontsize=12, labelpad=10)
    plt.ylabel("Сумма звёзд", fontsize=12, labelpad=10)

    # Настройка формата дат на оси X: "Янв 2026"
    ax = plt.gca()
    ax.xaxis.set_major_formatter(mdates.DateFormatter('%b %Y'))
    ax.xaxis.set_major_locator(mdates.MonthLocator())
    plt.xticks(rotation=45, ha='right')

    plt.grid(axis='y', linestyle='--', alpha=0.4)
    plt.tight_layout()

    buf = io.BytesIO()
    plt.savefig(buf, format='png', dpi=120, facecolor='white')
    plt.close()
    buf.seek(0)
    return buf


def format_number(num: int) -> str:
    """Форматирует число с разделителями тысяч."""
    return f"{num:,}".replace(",", " ")


def month_name_with_year(date_str: str) -> str:
    """Преобразует 'YYYY-MM' в 'Месяц ГГГГ'."""
    months = [
        "Январь", "Февраль", "Март", "Апрель", "Май", "Июнь",
        "Июль", "Август", "Сентябрь", "Октябрь", "Ноябрь", "Декабрь"
    ]
    y, m = map(int, date_str.split('-'))
    return f"{months[m-1]} {y}"


def format_top_users(top_list: list, title: str) -> list:
    """Форматирует список топ-пополнений."""
    lines = [f"<b>{title}</b>"]
    if not top_list:
        lines.append("   └— (нет данных)")
        return lines

    medals = ["🥇", "🥈", "🥉", "4️⃣", "5️⃣"]
    for i, tx in enumerate(top_list[:5]):
        name = tx.get("first_name") or tx.get("username") or f"ID:{tx['telegram_id']}"
        amount = format_number(tx['amount'])
        date_str = tx['created_at'].strftime("%d.%m.%Y") if tx.get('created_at') else ""
        lines.append(f"   {medals[i]} {name} — {amount} ⭐  <i>{date_str}</i>")
    return lines


@router.message(F.text == "/stars")
async def stars_statistics(message: Message):
    if message.from_user.id not in settings.admins:
        return

    async with SessionLocal() as session:
        stats = await get_stars_statistics(session)

    total_sum = stats["total_sum"]
    total_count = stats["total_count"]
    monthly_data = stats["monthly_data"]

    if total_count == 0:
        await message.answer("📊 Пока нет ни одного оплаченного пополнения звёзд.")
        return

    # Формируем текстовый отчёт
    lines = [
        "⭐️ <b>СТАТИСТИКА ПОПОЛНЕНИЙ ЗВЁЗД</b> ⭐️",
        "",
        f"💰 <b>Всего получено звёзд:</b> {format_number(total_sum)}",
        f"📦 <b>Всего транзакций:</b> {total_count}",
        "",
        "📅 <b>По месяцам:</b>"
    ]

    # Сортируем месяцы от новых к старым
    sorted_months = sorted(monthly_data.items(), key=lambda x: x[0], reverse=True)

    # Последний месяц и изменение
    if sorted_months:
        last_key, last_data = sorted_months[0]
        last_month_name = month_name_with_year(last_key)
        change_str = ""
        if len(sorted_months) > 1:
            prev_sum = sorted_months[1][1]["sum"]
            if prev_sum > 0:
                change = ((last_data["sum"] - prev_sum) / prev_sum) * 100
                arrow = "📈" if change > 0 else "📉" if change < 0 else "➖"
                change_str = f"  {arrow} {change:+.1f}%"
        lines.append(
            f"• <b>{last_month_name}</b>: {format_number(last_data['sum'])} ⭐ "
            f"({last_data['count']} пополн.){change_str}"
        )

        # Остальные месяцы (без процентов)
        for month_str, data in sorted_months[1:]:
            month_name = month_name_with_year(month_str)
            lines.append(
                f"• {month_name}: {format_number(data['sum'])} ⭐ ({data['count']} пополн.)"
            )

    # Среднемесячное
    if len(monthly_data) > 0:
        avg_monthly = total_sum / len(monthly_data)
        lines.append("")
        lines.append(f"📊 <b>Среднемесячное пополнение:</b> {format_number(int(avg_monthly))} ⭐")

    # Топ разовых пополнений
    lines.append("")
    lines.extend(format_top_users(stats["all_time_top"], "🏆 Крупнейшие разовые пополнения (всё время):"))

    lines.append("")
    current_month_name = datetime.now().strftime("%B %Y")
    lines.extend(format_top_users(stats["month_top"], f"📆 Крупнейшие пополнения за {current_month_name}:"))

    text_report = "\n".join(lines)

    # График
    chart_buf = generate_monthly_chart(monthly_data)

    if chart_buf:
        photo = BufferedInputFile(chart_buf.read(), filename="stars_chart.png")
        await message.answer_photo(photo, caption=text_report, parse_mode="HTML")
    else:
        await message.answer(text_report, parse_mode="HTML")