from aiogram import Router, F, Bot
from aiogram.filters import CommandStart
from aiogram.types import Message, CallbackQuery
from sqlalchemy.ext.asyncio import AsyncSession
from bot.models.users import User
from bot.services.referral import process_referral
from bot.services.subscriptions import check_subscriptions
from bot.utils.keyboards import get_subscription_keyboard

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

        ref_type, ref_value = await process_referral(session, user, payload)

        await session.commit()

        text = "Добро пожаловать! 🎉\nВы зарегистрированы в системе."
    else:
        text = "С возвращением 👋"

    # проверка подписки
    not_subscribed = await check_subscriptions(session, bot, message.from_user.id)
    if not_subscribed:
        kb = get_subscription_keyboard(not_subscribed)
        await message.answer(
            "Для работы с ботом необходимо подписаться на каналы:",
            reply_markup=kb,
        )
        return

    await message.answer(text)







@router.callback_query(F.data == "check_subs")
async def cb_check_subs(callback: CallbackQuery, bot: Bot, session: AsyncSession):
    user_id = callback.from_user.id
    not_subscribed = await check_subscriptions(session, bot, user_id)

    if not_subscribed:
        kb = get_subscription_keyboard(not_subscribed)
        await callback.message.edit_text(
            "❌ Вы ещё не подписаны на все каналы. Подпишитесь и нажмите кнопку снова:",
            reply_markup=kb,
        )
    else:
        user = await session.get(User, user_id)
        text = f"✅ Отлично, {user.first_name or 'друг'}!\nТеперь вам доступно меню."
        await callback.message.edit_text(text)
        # тут можно показать основное меню бота
