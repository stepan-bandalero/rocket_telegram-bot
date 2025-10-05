from aiogram import Router, F
from aiogram.types import Message
from sqlalchemy.ext.asyncio import AsyncSession

from bot.config import settings
from bot.services.promo import PromoService
from bot.middlewares.db import DataBaseSessionMiddleware

router = Router()
router.message.middleware(DataBaseSessionMiddleware())

#
# @router.message(F.text.startswith("/add_promo"))
# async def add_promo(message: Message, session: AsyncSession):
#     if message.from_user.id not in settings.admins:
#         return
#
#     try:
#         _, tg_id_str = message.text.split(maxsplit=1)
#         tg_id = int(tg_id_str.strip())
#     except (ValueError, IndexError):
#         await message.answer("❌ Используй: <code>/add_promo &lt;telegram_id&gt;</code>")
#         return
#
#     promo = await PromoService.create_promo(session, tg_id)
#
#     promo_url = f"{settings.bot_href}?start={promo.code}"
#
#     text = (
#         "🎉 <b>Реферальная ссылка создана!</b>\n\n"
#         f"🔗 <b>Ссылка:</b> <code>{promo_url}</code>\n"
#         f"👤 <b>Админ:</b> <code>{promo.created_by}</code>"
#     )
#
#     await message.answer(text, disable_web_page_preview=True)


@router.message(F.text.startswith("/add_promo"))
async def add_promo(message: Message, session: AsyncSession):
    if message.from_user.id not in settings.admins:
        return

    try:
        _, tg_id_str, percent_str = message.text.split(maxsplit=2)
        tg_id = int(tg_id_str.strip())
        percent = int(percent_str.strip())

        if not (0 < percent <= 100):
            raise ValueError("invalid percent")

    except (ValueError, IndexError):
        await message.answer("❌ Используй: <code>/add_promo &lt;telegram_id&gt; &lt;процент&gt;</code>")
        return

    promo = await PromoService.create_promo(session, tg_id, percent)

    promo_url = f"{settings.bot_href}?start={promo.code}"

    text = (
        "🎉 <b>Реферальная ссылка создана!</b>\n\n"
        f"🔗 <b>Ссылка:</b> <code>{promo_url}</code>\n"
        f"👤 <b>Админ:</b> <code>{promo.created_by}</code>\n"
        f"📈 <b>Процент:</b> <code>{promo.referral_percentage}%</code>"
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

    parts: list[str] = []
    header = "📊 <b>Статистика по промо-ссылкам</b>\n\n"
    current = header

    for promo in promos:
        # форматируем числа с разделителями тысяч
        referrals = f"{promo['referrals_count']:,}".replace(",", " ")
        active = f"{promo['active_users']:,}".replace(",", " ")
        deposits = f"{promo['total_deposits_cents'] / 100:,.2f}".replace(",", " ")
        withdrawals = f"{promo['total_withdrawals_cents'] / 100:,.2f}".replace(",", " ")

        block = (
            f"▫️ <b>Админ:</b> <code>{promo['created_by']}</code>\n"
            f"🔗 <b>Ссылка:</b> <code>{settings.bot_href}?start={promo['code']}</code>\n"
            f"   🔑 Код: <code>{promo['code']}</code>\n"
            f"   📈 Процент: <b>{promo['referral_percentage']}%</b>\n"
            f"   👥 Переходов: {referrals}\n"
            f"   🟢 Активных: {active}\n"
            f"   💰 Пополнений: <b>{deposits} TON</b>\n"
            f"   💸 Выводов: <b>{withdrawals} TON</b>\n\n"
        )

        # проверяем лимит телеграма (4096 символов)
        if len(current) + len(block) > 4000:
            parts.append(current)
            current = block
        else:
            current += block

    if current:
        parts.append(current)

    # отправляем по частям
    for part in parts:
        await message.answer(part, disable_web_page_preview=True)



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
