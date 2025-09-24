from aiogram import Router, F
from aiogram.types import Message
from sqlalchemy.ext.asyncio import AsyncSession

from bot.config import settings
from bot.services.promo import PromoService
from bot.middlewares.db import DataBaseSessionMiddleware

router = Router()
router.message.middleware(DataBaseSessionMiddleware())


@router.message(F.text.startswith("/add_promo"))
async def add_promo(message: Message, session: AsyncSession):
    if message.from_user.id not in settings.admins:
        return

    try:
        # всё после команды — это название (с пробелами)
        title = message.text.split(maxsplit=1)[1].strip()
    except IndexError:
        await message.answer("❌ Используй: <code>/add_promo &lt;название&gt;</code>")
        return

    promo = await PromoService.create_promo(session, title, message.from_user.id)

    promo_url = f"{settings.bot_href}?start={promo.code}"

    text = (
        "🎉 <b>Промо-ссылка создана!</b>\n\n"
        f"🔗 <b>Ссылка:</b> <code>{promo_url}</code>\n"
        f"🏷 <b>Название:</b> {promo.title}\n"
        f"🔑 <b>Код:</b> <code>{promo.code}</code>\n"
        f"👤 <b>Создатель:</b> <code>{promo.created_by}</code>"
    )

    await message.answer(text, disable_web_page_preview=True)


@router.message(F.text == "/promos")
async def list_promos(message: Message, session: AsyncSession):
    if message.from_user.id not in settings.admins:
        return
    promos = await PromoService.get_promos(session)
    if not promos:
        await message.answer("📭 Промо-ссылок пока нет.")
        return

    text = "📊 <b>Статистика по промо-ссылкам</b>\n\n"
    for promo in promos:
        text += (
            f"▫️ <b>{promo['title']}</b>\n"
            f"🔗 <b>Ссылка:</b> <code>{settings.bot_href}?start={promo['code']}</code>\n"
            f"   🔑 Код: <code>{promo['code']}</code>\n"
            f"   👥 Переходов: {promo['referrals_count']}\n"
            f"   🟢 Активных: {promo['active_users']}\n\n"
        )
    await message.answer(text)


@router.message(F.text.startswith("/delete_promo"))
async def delete_promo(message: Message, session: AsyncSession):
    if message.from_user.id not in settings.admins:
        return
    try:
        _, promo_code = message.text.split(maxsplit=1)
        promo_code = promo_code.strip()
    except ValueError:
        # Экранируем спецсимволы HTML или используем Markdown
        await message.answer("❌ Используй: <code>/delete_promo &lt;код&gt;</code>", parse_mode="HTML")
        return

    deleted = await PromoService.delete_promo(session, promo_code)
    if deleted:
        await message.answer(
            f"🗑 Промо с кодом <code>{promo_code}</code> удален.", parse_mode="HTML"
        )
    else:
        await message.answer("⚠ Промо не найден.", parse_mode="HTML")
