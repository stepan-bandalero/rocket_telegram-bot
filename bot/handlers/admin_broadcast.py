from aiogram import Router, F
from aiogram.types import Message, CallbackQuery
from aiogram.fsm.context import FSMContext

from bot.db import SessionLocal
from bot.services.broadcast import BroadcastService
from bot.models.broadcast_task import BroadcastTask
from bot.config import settings
from bot.states.broadcast_states import BroadcastStates


router = Router()


@router.message(F.text == "/broadcast")
async def start_broadcast(message: Message, state: FSMContext):
    if message.from_user.id not in settings.admins:
        return
    await message.answer("Выберите тип рассылки: text, photo, video, video_note")
    await state.set_state(BroadcastStates.waiting_type)


@router.message(BroadcastStates.waiting_type)
async def set_type(message: Message, state: FSMContext):
    if message.text not in ["text", "photo", "video", "video_note"]:
        await message.answer("Неверный тип, выберите: text, photo, video, video_note")
        return
    await state.update_data(content_type=message.text)
    await message.answer("Введите текст рассылки (можно оставить пустым)")
    await state.set_state(BroadcastStates.waiting_text)


@router.message(BroadcastStates.waiting_text)
async def set_text(message: Message, state: FSMContext):
    await state.update_data(text=message.text)
    data = await state.get_data()
    if data["content_type"] == "text":
        await message.answer("Подтвердите рассылку или добавьте кнопки")
        await state.set_state(BroadcastStates.confirm)
    else:
        await message.answer("Отправьте media (URL или file_id)")
        await state.set_state(BroadcastStates.waiting_media)





@router.message(BroadcastStates.waiting_media)
async def set_media(message: Message, state: FSMContext):
    await state.update_data(media=message.text)
    await message.answer("Добавить кнопки? (y/n)")
    await state.set_state(BroadcastStates.waiting_buttons)


@router.message(BroadcastStates.waiting_buttons)
async def set_buttons(message: Message, state: FSMContext):
    buttons = []
    if message.text.lower() == "y":
        await message.answer("Введите кнопки в формате: text|url или text|web_app_url (по одной в строке)")
        # Здесь можно добавить отдельный FSM для добавления нескольких кнопок
    await state.update_data(buttons=buttons)
    await message.answer("Подтвердите рассылку")
    await state.set_state(BroadcastStates.confirm)


@router.message(BroadcastStates.confirm)
async def confirm_broadcast(message: Message, state: FSMContext):
    data = await state.get_data()
    task = BroadcastTask(
        content_type=data["content_type"],
        text=data.get("text"),
        media=data.get("media"),
        buttons=data.get("buttons", [])
    )
    async with SessionLocal() as session:
        session.add(task)
        await session.commit()
        await message.answer(f"✅ Рассылка #{task.id} создана и добавлена в очередь")
    await state.clear()


@router.message(F.text.startswith("/stop_broadcast"))
async def stop_broadcast(message: Message):
    task_id = int(message.text.split()[-1])
    if task_id in BroadcastService.stop_flags:
        BroadcastService.stop_flags[task_id].set()
        await message.answer(f"⏹ Рассылка #{task_id} остановлена")
    else:
        await message.answer("❌ Нет такой активной рассылки")
