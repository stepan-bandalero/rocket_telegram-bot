import re

from aiogram import Router, F
from aiogram.types import Message
from datetime import datetime, timezone
from sqlalchemy import select

from config import settings
from db import SessionLocal
from models.gift_catalog import GiftCatalog
from models.users import User
from models.user_gift import UserGift, GiftStatus
from models.user_transaction import UserTransaction  # модель для транзакций

router = Router()


def slugify(slug_part: str) -> str:
    """
    Превращает DurovsCap из ссылки → durovsсap для поиска по tg_gift_slug.
    Убирает все заглавные буквы, любые разделители.
    """
    # Убираем любые не буквенно-цифровые символы
    cleaned = re.sub(r"[^a-zA-Z0-9]", "", slug_part)
    # Переводим в нижний регистр
    return cleaned.lower()


@router.message(F.text.startswith("/add_gift"))
async def add_gift_to_user(message: Message):
    # проверка на админа
    if message.from_user.id not in settings.admins:
        return

    parts = message.text.split(maxsplit=2)
    if len(parts) < 3:
        await message.answer("❌ Использование: /add_gift &lt;ID_пользователя&qt; &lt;Ссылка на подарок&qt;")
        return

    try:
        telegram_id = int(parts[1])
        gift_link = parts[2]
    except ValueError:
        await message.answer("❌ ID пользователя должен быть числом")
        return

    if not gift_link.startswith(("http://t.me/nft/", "https://t.me/nft/", "t.me/nft/")):
        await message.answer("❌ Неверная ссылка на подарок")
        return

    # извлекаем slug подарка
    slug_part = gift_link.split("/")[-1].split("-")[0]
    tg_gift_slug = slugify(slug_part)

    async with SessionLocal() as session:
        # проверяем пользователя
        user = await session.get(User, telegram_id)
        if not user:
            # создаем пользователя если не найден
            user = User(telegram_id=telegram_id, created_at=datetime.now(timezone.utc))
            session.add(user)
            await session.commit()

        # ищем подарок в каталоге
        stmt = select(GiftCatalog).where(GiftCatalog.tg_gift_slug == tg_gift_slug, GiftCatalog.is_active == True)
        result = await session.execute(stmt)
        gift = result.scalars().first()
        if not gift:
            await message.answer(f"❌ Подарок с tg_gift_slug '{tg_gift_slug}' не найден")
            return

        # добавляем подарок пользователю
        user_gift = UserGift(
            user_id=telegram_id,
            gift_catalog_id=gift.id,
            price_cents=gift.price_cents,
            status=GiftStatus.AVAILABLE,
            gift_image_url=f"/gifts/{tg_gift_slug}.png",
            received_at=datetime.now(timezone.utc)
        )
        session.add(user_gift)
        await session.commit()  # 🔹 важно, чтобы получить ID подарка

        # создаём транзакцию в user_transactions
        transaction = UserTransaction(
            user_id=telegram_id,
            type="deposit",
            currency="gift",
            amount=gift.price_cents,
            created_at=datetime.now(timezone.utc)
        )
        session.add(transaction)
        await session.commit()

    await message.answer(
        f"✅ Подарок <b>{gift.title}</b> добавлен пользователю <code>{telegram_id}</code>",
        parse_mode="HTML"
    )
