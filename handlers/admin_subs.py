import re
from aiogram import F, Router
from aiogram.types import Message, CallbackQuery, InlineKeyboardMarkup, InlineKeyboardButton
from aiogram.fsm.context import FSMContext
from aiogram.fsm.state import State, StatesGroup
from sqlalchemy import select, func, update, delete
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from config import settings
from db import SessionLocal
from models.partner import PartnerRedirect, PartnerRequirement

router = Router()

PAGE_SIZE = 5  # партнёров на странице

# -------------------- FSM для добавления / редактирования --------------------
class PartnerForm(StatesGroup):
    waiting_for_id = State()
    waiting_for_name = State()
    waiting_for_link = State()
    waiting_for_analytics_event = State()
    waiting_for_avatar_url = State()

class EditFieldForm(StatesGroup):
    waiting_for_value = State()

class RequirementForm(StatesGroup):
    waiting_for_sort_order = State()

# -------------------- Вспомогательные функции --------------------
async def get_partners_page(session: AsyncSession, page: int):
    offset = (page - 1) * PAGE_SIZE
    stmt = (
        select(PartnerRedirect)
        .options(selectinload(PartnerRedirect.requirements))
        .order_by(PartnerRedirect.name)
        .offset(offset)
        .limit(PAGE_SIZE)
    )
    result = await session.execute(stmt)
    partners = result.scalars().all()

    total = await session.scalar(select(func.count(PartnerRedirect.id)))
    return partners, total

def build_partners_keyboard(partners, page: int, total_pages: int) -> InlineKeyboardMarkup:
    buttons = []
    for p in partners:
        status_icon = "🟢" if p.is_active else "🔴"
        btn_text = f"{status_icon} {p.name} ({p.id})"
        buttons.append([InlineKeyboardButton(text=btn_text, callback_data=f"partner_detail:{p.id}")])

    nav_buttons = []
    if page > 1:
        nav_buttons.append(InlineKeyboardButton(text="◀️ Назад", callback_data=f"partners_page:{page-1}"))
    if page < total_pages:
        nav_buttons.append(InlineKeyboardButton(text="Вперёд ▶️", callback_data=f"partners_page:{page+1}"))
    if nav_buttons:
        buttons.append(nav_buttons)

    buttons.append([InlineKeyboardButton(text="➕ Добавить партнёра", callback_data="partner_add")])
    return InlineKeyboardMarkup(inline_keyboard=buttons)

def build_detail_keyboard(partner_id: str, is_active: bool) -> InlineKeyboardMarkup:
    toggle_text = "🔴 Деактивировать" if is_active else "🟢 Активировать"
    return InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text="✏️ ID", callback_data=f"partner_edit_field:{partner_id}:id")],
        [InlineKeyboardButton(text="✏️ Название", callback_data=f"partner_edit_field:{partner_id}:name")],
        [InlineKeyboardButton(text="✏️ Ссылка", callback_data=f"partner_edit_field:{partner_id}:link")],
        [InlineKeyboardButton(text="✏️ Аналитика", callback_data=f"partner_edit_field:{partner_id}:analytics_event")],
        [InlineKeyboardButton(text="✏️ Аватар", callback_data=f"partner_edit_field:{partner_id}:avatar_url")],
        [InlineKeyboardButton(text=toggle_text, callback_data=f"partner_toggle:{partner_id}")],
        [InlineKeyboardButton(text="🔗 Привязки к фичам", callback_data=f"partner_requirements:{partner_id}")],
        [InlineKeyboardButton(text="❌ Удалить партнёра", callback_data=f"partner_delete:{partner_id}")],
        [InlineKeyboardButton(text="🔙 Назад к списку", callback_data="partners_page:1")],
    ])

def build_requirements_keyboard(partner_id: str) -> InlineKeyboardMarkup:
    return InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text="➕ Привязать к free_lottery", callback_data=f"req_add:{partner_id}:free_lottery")],
        [InlineKeyboardButton(text="➕ Привязать к free_case", callback_data=f"req_add:{partner_id}:free_case")],
        [InlineKeyboardButton(text="🔙 Назад к партнёру", callback_data=f"partner_detail:{partner_id}")],
    ])

def format_partner_detail(p: PartnerRedirect) -> str:
    req_lines = []
    for r in p.requirements:
        req_lines.append(f"  • {r.feature_key} (порядок: {r.sort_order})")
    req_text = "\n".join(req_lines) if req_lines else "  — нет привязок"
    status = "🟢 Активен" if p.is_active else "🔴 Неактивен"
    avatar = p.avatar_url or "—"
    return (
        f"📋 <b>{p.name}</b>\n"
        f"┣ 🆔 <code>{p.id}</code>\n"
        f"┣ 🔗 {p.link}\n"
        f"┣ 📊 Аналитика: <code>{p.analytics_event}</code>\n"
        f"┣ 🖼 Аватар: {avatar}\n"
        f"┣ 📌 Статус: {status}\n"
        f"┣ 📅 Создан: {p.created_at.strftime('%d.%m.%Y %H:%M')}\n"
        f"┣ 🔄 Обновлён: {p.updated_at.strftime('%d.%m.%Y %H:%M')}\n"
        f"┗ 🔗 Привязки:\n{req_text}"
    )

# -------------------- Команда /partners (или /subs) --------------------
@router.message(F.text.startswith("/partners"))
@router.message(F.text.startswith("/subs"))
async def cmd_partners(message: Message):
    if message.from_user.id not in settings.admins:
        return
    await show_partners_page(message, page=1)

async def show_partners_page(target: Message | CallbackQuery, page: int):
    async with SessionLocal() as session:
        partners, total = await get_partners_page(session, page)
    total_pages = max((total + PAGE_SIZE - 1) // PAGE_SIZE, 1)
    text = f"📋 <b>Партнёрские ссылки</b>\nСтраница {page}/{total_pages}\nВсего: {total}\n\nВыберите партнёра:"
    kb = build_partners_keyboard(partners, page, total_pages)

    if isinstance(target, Message):
        await target.answer(text, parse_mode="HTML", reply_markup=kb)
    else:
        await target.message.edit_text(text, parse_mode="HTML", reply_markup=kb)
        await target.answer()

@router.callback_query(F.data.startswith("partners_page:"))
async def paginate_partners(cb: CallbackQuery):
    page = int(cb.data.split(":")[1])
    await show_partners_page(cb, page)

# -------------------- Детальный просмотр партнёра --------------------
@router.callback_query(F.data.startswith("partner_detail:"))
async def partner_detail(cb: CallbackQuery):
    partner_id = cb.data.split(":")[1]
    async with SessionLocal() as session:
        stmt = select(PartnerRedirect).options(selectinload(PartnerRedirect.requirements)).where(PartnerRedirect.id == partner_id)
        result = await session.execute(stmt)
        partner = result.scalar_one_or_none()
        if not partner:
            await cb.answer("Партнёр не найден", show_alert=True)
            return

    text = format_partner_detail(partner)
    kb = build_detail_keyboard(partner.id, partner.is_active)
    await cb.message.edit_text(text, parse_mode="HTML", reply_markup=kb)
    await cb.answer()

# -------------------- Переключение активности --------------------
@router.callback_query(F.data.startswith("partner_toggle:"))
async def toggle_partner_active(cb: CallbackQuery):
    partner_id = cb.data.split(":")[1]
    async with SessionLocal() as session:
        stmt = select(PartnerRedirect).where(PartnerRedirect.id == partner_id)
        result = await session.execute(stmt)
        partner = result.scalar_one_or_none()
        if not partner:
            await cb.answer("Партнёр не найден", show_alert=True)
            return
        partner.is_active = not partner.is_active
        await session.commit()
        await session.refresh(partner)

    await cb.answer(f"Статус изменён на {'активен' if partner.is_active else 'неактивен'}")
    await partner_detail(cb)

# -------------------- Удаление партнёра --------------------
@router.callback_query(F.data.startswith("partner_delete:"))
async def delete_partner(cb: CallbackQuery):
    partner_id = cb.data.split(":")[1]
    async with SessionLocal() as session:
        stmt = delete(PartnerRedirect).where(PartnerRedirect.id == partner_id)
        await session.execute(stmt)
        await session.commit()
    await cb.answer("Партнёр удалён")
    await show_partners_page(cb, page=1)

# -------------------- Добавление нового партнёра (через FSM) --------------------
@router.callback_query(F.data == "partner_add")
async def start_add_partner(cb: CallbackQuery, state: FSMContext):
    await cb.message.edit_text("Введите уникальный ID партнёра (например, <code>stage</code>):", parse_mode="HTML")
    await state.set_state(PartnerForm.waiting_for_id)
    await cb.answer()

@router.message(PartnerForm.waiting_for_id)
async def process_id(message: Message, state: FSMContext):
    partner_id = message.text.strip()
    if not re.match(r'^[a-zA-Z0-9_]+$', partner_id):
        await message.answer("❌ ID должен содержать только латинские буквы, цифры и подчёркивания. Попробуйте снова:")
        return
    async with SessionLocal() as session:
        exists = await session.get(PartnerRedirect, partner_id)
        if exists:
            await message.answer("❌ Партнёр с таким ID уже существует. Введите другой ID:")
            return
    await state.update_data(id=partner_id)
    await message.answer("Введите название партнёра (например, <b>Stage</b>):", parse_mode="HTML")
    await state.set_state(PartnerForm.waiting_for_name)

@router.message(PartnerForm.waiting_for_name)
async def process_name(message: Message, state: FSMContext):
    name = message.text.strip()
    if not name:
        await message.answer("Название не может быть пустым. Введите название:")
        return
    await state.update_data(name=name)
    await message.answer("Введите ссылку для перехода (полный URL):")
    await state.set_state(PartnerForm.waiting_for_link)

@router.message(PartnerForm.waiting_for_link)
async def process_link(message: Message, state: FSMContext):
    link = message.text.strip()
    if not link.startswith(('http://', 'https://')):
        await message.answer("❌ Ссылка должна начинаться с http:// или https://")
        return
    await state.update_data(link=link)
    await message.answer("Введите название события для аналитики (например, <code>stage</code>):", parse_mode="HTML")
    await state.set_state(PartnerForm.waiting_for_analytics_event)

@router.message(PartnerForm.waiting_for_analytics_event)
async def process_analytics(message: Message, state: FSMContext):
    event = message.text.strip()
    if not event:
        await message.answer("Событие не может быть пустым.")
        return
    await state.update_data(analytics_event=event)
    await message.answer("Введите URL аватарки (или отправьте <code>-</code> чтобы пропустить):", parse_mode="HTML")
    await state.set_state(PartnerForm.waiting_for_avatar_url)

@router.message(PartnerForm.waiting_for_avatar_url)
async def process_avatar(message: Message, state: FSMContext):
    avatar = message.text.strip()
    if avatar == "-":
        avatar = None
    data = await state.get_data()
    async with SessionLocal() as session:
        new_partner = PartnerRedirect(
            id=data['id'],
            name=data['name'],
            link=data['link'],
            analytics_event=data['analytics_event'],
            avatar_url=avatar
        )
        session.add(new_partner)
        await session.commit()
    await state.clear()
    await message.answer(f"✅ Партнёр <b>{data['name']}</b> успешно добавлен!", parse_mode="HTML")
    await show_partners_page(message, page=1)

# -------------------- Редактирование полей --------------------
@router.callback_query(F.data.startswith("partner_edit_field:"))
async def edit_field_start(cb: CallbackQuery, state: FSMContext):
    _, partner_id, field = cb.data.split(":")
    await state.update_data(edit_partner_id=partner_id, edit_field=field)
    field_names = {
        "id": "ID",
        "name": "название",
        "link": "ссылку",
        "analytics_event": "событие аналитики",
        "avatar_url": "URL аватарки"
    }
    await cb.message.edit_text(f"Введите новое значение для поля <b>{field_names[field]}</b>:", parse_mode="HTML")
    await state.set_state(EditFieldForm.waiting_for_value)
    await cb.answer()

@router.message(EditFieldForm.waiting_for_value)
async def edit_field_value(message: Message, state: FSMContext):
    data = await state.get_data()
    partner_id = data['edit_partner_id']
    field = data['edit_field']
    new_value = message.text.strip()

    if field == "id" and not re.match(r'^[a-zA-Z0-9_]+$', new_value):
        await message.answer("❌ ID должен содержать только латинские буквы, цифры и подчёркивания.")
        return
    if field == "link" and not new_value.startswith(('http://', 'https://')):
        await message.answer("❌ Ссылка должна начинаться с http:// или https://")
        return
    if field == "avatar_url" and new_value == "-":
        new_value = None

    async with SessionLocal() as session:
        if field == "id":
            # Проверка уникальности нового ID
            exists = await session.get(PartnerRedirect, new_value)
            if exists:
                await message.answer("❌ Партнёр с таким ID уже существует.")
                return
            # Меняем ID, каскад обновит FK в requirements
            stmt = update(PartnerRedirect).where(PartnerRedirect.id == partner_id).values(id=new_value)
        else:
            stmt = update(PartnerRedirect).where(PartnerRedirect.id == partner_id).values(**{field: new_value})
        await session.execute(stmt)
        await session.commit()

    await state.clear()
    await message.answer("✅ Поле обновлено!")
    # Возвращаемся к деталям партнёра
    await show_partner_detail_by_id(message, new_value if field == "id" else partner_id)

async def show_partner_detail_by_id(target: Message, partner_id: str):
    async with SessionLocal() as session:
        stmt = select(PartnerRedirect).options(selectinload(PartnerRedirect.requirements)).where(PartnerRedirect.id == partner_id)
        result = await session.execute(stmt)
        partner = result.scalar_one()
    text = format_partner_detail(partner)
    kb = build_detail_keyboard(partner.id, partner.is_active)
    await target.answer(text, parse_mode="HTML", reply_markup=kb)

# -------------------- Управление привязками --------------------
@router.callback_query(F.data.startswith("partner_requirements:"))
async def manage_requirements(cb: CallbackQuery):
    partner_id = cb.data.split(":")[1]
    async with SessionLocal() as session:
        partner = await session.get(PartnerRedirect, partner_id, options=[selectinload(PartnerRedirect.requirements)])
        if not partner:
            await cb.answer("Партнёр не найден", show_alert=True)
            return

    text = f"🔗 <b>Управление привязками для {partner.name}</b>\n\n"
    if partner.requirements:
        for req in partner.requirements:
            text += f"• {req.feature_key} (порядок {req.sort_order}) - "
            text += f"/delreq_{req.id}\n"
    else:
        text += "Нет привязок\n"

    kb = InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text="➕ Привязать к free_lottery", callback_data=f"req_add:{partner_id}:free_lottery")],
        [InlineKeyboardButton(text="➕ Привязать к free_case", callback_data=f"req_add:{partner_id}:free_case")],
        [InlineKeyboardButton(text="🔙 Назад к партнёру", callback_data=f"partner_detail:{partner_id}")],
    ])
    await cb.message.edit_text(text, parse_mode="HTML", reply_markup=kb)
    await cb.answer()

@router.callback_query(F.data.startswith("req_add:"))
async def add_requirement_start(cb: CallbackQuery, state: FSMContext):
    _, partner_id, feature = cb.data.split(":")
    await state.update_data(req_partner_id=partner_id, req_feature=feature)
    await cb.message.edit_text(
        f"Введите порядковый номер (sort_order) для привязки к <b>{feature}</b> (целое число):",
        parse_mode="HTML"
    )
    await state.set_state(RequirementForm.waiting_for_sort_order)
    await cb.answer()

@router.message(RequirementForm.waiting_for_sort_order)
async def add_requirement_finish(message: Message, state: FSMContext):
    try:
        sort_order = int(message.text.strip())
    except ValueError:
        await message.answer("❌ Введите целое число.")
        return
    data = await state.get_data()
    partner_id = data['req_partner_id']
    feature = data['req_feature']
    async with SessionLocal() as session:
        new_req = PartnerRequirement(
            partner_id=partner_id,
            feature_key=feature,
            sort_order=sort_order
        )
        session.add(new_req)
        await session.commit()
    await state.clear()
    await message.answer("✅ Привязка добавлена!")
    await show_partner_detail_by_id(message, partner_id)

# Удаление привязки (по ID) через команду в тексте или кнопку
@router.message(F.text.startswith("/delreq_"))
async def delete_requirement_by_command(message: Message):
    if message.from_user.id not in settings.admins:
        return
    try:
        req_id = int(message.text.split("_")[1])
    except:
        return
    async with SessionLocal() as session:
        req = await session.get(PartnerRequirement, req_id)
        if not req:
            await message.answer("Привязка не найдена")
            return
        partner_id = req.partner_id
        await session.delete(req)
        await session.commit()
    await message.answer("✅ Привязка удалена")
    await show_partner_detail_by_id(message, partner_id)