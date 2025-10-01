from aiogram import Router, F, Bot
from aiogram.filters import CommandStart
from aiogram.types import Message, CallbackQuery
from sqlalchemy.ext.asyncio import AsyncSession
from bot.models.users import User
from bot.services.referral import process_referral
from bot.services.subscriptions import check_subscriptions
from bot.utils.keyboards import get_subscription_keyboard

from aiogram.types import InlineKeyboardMarkup, InlineKeyboardButton, WebAppInfo

keyboard = InlineKeyboardMarkup(
    inline_keyboard=[
        # Первая строка - одна кнопка "Запустить"
        [InlineKeyboardButton(
            text="▶️ Запустить",
            web_app=WebAppInfo(url="https://rocket-app.top")
        )],        # Вторая строка - две кнопки
        [
            InlineKeyboardButton(text="📗 Отзывы", url="https://t.me/rocket_gift"),
            InlineKeyboardButton(text="👩🏼‍💻 Менеджер", url="https://t.me/GiftsToRocket")
        ]
    ]
)

router = Router()


@router.message(CommandStart())
async def cmd_start(message: Message, bot: Bot, session: AsyncSession):
    args = message.text.split(maxsplit=1)
    payload = args[1] if len(args) > 1 else None

    user = await session.get(User, message.from_user.id)

    if not user:
        # новый пользователь
        user = User(
            telegram_id=message.from_user.id,
            username=message.from_user.username,
            first_name=message.from_user.first_name,
        )
        session.add(user)
        await session.flush()
        await session.commit()


    # проверка подписки
    not_subscribed = await check_subscriptions(session, bot, message.from_user.id)
    if not_subscribed:
        kb = get_subscription_keyboard(not_subscribed)
        await message.answer_photo(
            photo="https://i.ibb.co/YFFsrwW3/5678867.jpg",
            caption="🚀 <b>Добро пожаловать в ROCKET!\n\n Для авторизации</b> подпишитесь на канал и нажмите <b>«Продолжить».</b>",
            reply_markup=kb
        )
        return

    await message.answer_photo(
        photo="https://i.ibb.co/M59wqfSj/IMG-4720.jpg",
        caption="<b>ROCKET</b> — Первая <b>NFT краш игра</b> с тысячами <b>подарков</b> в <b>Telegram!</b> \n\n"
                "🪙 <b>Стейкинг, турниры, дропы</b> с бонусами и эксклюзивными <b>NFT</b> каждый день\n"
                "🎁 Более <b>5000 NFT подарков</b> уже отправлены победителям <b>ROCKET</b>\n\n"
                "Скорее жми кнопку <b>«Запустить»</b>",
        reply_markup=keyboard
    )


@router.callback_query(F.data == "check_subs")
async def cb_check_subs(callback: CallbackQuery, bot: Bot, session: AsyncSession):
    user_id = callback.from_user.id
    not_subscribed = await check_subscriptions(session, bot, user_id)

    if not_subscribed:
        # Показываем плашку вверху чата на несколько секунд
        await callback.answer("❌ Вы ещё не подписаны на все каналы!", show_alert=False)
    else:
        user = await session.get(User, user_id)

        # Меняем на второе сообщение
        await callback.message.edit_media(
            media=InputMediaPhoto(
                media="https://i.ibb.co/M59wqfSj/IMG-4720.jpg",
                caption="<b>ROCKET</b> — Первая <b>NFT краш игра</b> с тысячами <b>подарков</b> в <b>Telegram!</b> \n\n"
                        "🪙 <b>Стейкинг, турниры, дропы</b> с бонусами и эксклюзивными <b>NFT</b> каждый день\n"
                        "🎁 Более <b>5000 NFT подарков</b> уже отправлены победителям <b>ROCKET</b>\n\n"
                        "Скорее жми кнопку <b>«Запустить»</b>"
            ),
            reply_markup=keyboard
        )
        # Можно также показать плашку об успехе
        await callback.answer("✅ Отлично! Доступ открыт!", show_alert=False)
        