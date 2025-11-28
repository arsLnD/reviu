# handlers/owner.py
from aiogram import Router, F
from aiogram.utils.keyboard import InlineKeyboardBuilder
from aiogram.types import Message, CallbackQuery, InlineKeyboardMarkup, InlineKeyboardButton
from aiogram.fsm.context import FSMContext
from aiogram.fsm.state import State, StatesGroup
from aiogram.filters import Command
from db_manager.db import Database
from config import config


db = Database()
owner_router = Router()
OWNER_ID = config.bot.owner_id


class OwnerStates(StatesGroup):
    waiting_for_admin_id = State()
    waiting_for_alias = State()

# --- Команда /owner ---
@owner_router.message(Command("owner"))
async def owner_panel(message: Message):
    if message.from_user.id != OWNER_ID:
        await message.answer("🚫 У вас нет прав для этой команды.")
        return

    count = db.count_admins()

    keyboard = InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text="➕ Добавить", callback_data="owner_add_admin"),
         InlineKeyboardButton(text="➖ Удалить", callback_data="owner_delete_admin")]
    ])

    await message.answer(f"👥 Администраторов: {count}", reply_markup=keyboard)

# --- Добавление администратора ---
@owner_router.callback_query(F.data == "owner_add_admin")
async def owner_add_admin(call: CallbackQuery, state: FSMContext):
    if call.from_user.id != OWNER_ID:
        await call.answer("🚫 Нет доступа", show_alert=True)
        return

    await call.message.edit_text("Пожалуйста, отправьте контакт пользователя, которого вы хотите сделать администратором.")
    await state.set_state(OwnerStates.waiting_for_admin_id)

@owner_router.message(F.contact, OwnerStates.waiting_for_admin_id)
async def process_admin_id(message: Message, state: FSMContext):
    admin_contact: Contact = message.contact
    admin_id = admin_contact.user_id
    owner_id = message.from_user.id
    
    user_exists = db.user_exists(admin_id)
    if not user_exists:
        await message.answer("Этот пользователь не зарегистрирован в боте.")
        await state.clear()
        return

    builder = InlineKeyboardBuilder()
    builder.button(text="✅ Подтвердить", callback_data=f"confirm_admin:{admin_id}:{owner_id}")
    
    try:
        await message.bot.send_message(
            chat_id=admin_id,
            text="Здравствуйте! Вам предложили роль администратора. Вы согласны?",
            reply_markup=builder.as_markup()
        )
        await message.answer("Запрос на назначение администратором отправлен. Дождитесь подтверждения.")
    except Exception as e:
        await message.answer(f"Не удалось отправить сообщение пользователю. Ошибка: {e}")
    
    # Сбрасываем состояние после отправки запроса
    await state.clear()
    
    

@owner_router.callback_query(F.data.startswith("confirm_admin:"))
async def confirm_admin(call: CallbackQuery, state: FSMContext):
    parts = call.data.split(":")
    admin_id = int(parts[1])
    owner_id = int(parts[2])
    
    await call.message.edit_text("Вы подтвердили роль администратора. Поздравляю! 🎉")
    
    # Отправляем сообщение владельцу с кнопкой "Продолжить"
    builder = InlineKeyboardBuilder()
    builder.button(text="Продолжить", callback_data=f"set_alias:{admin_id}")
    
    await call.message.bot.send_message(
        chat_id=owner_id,
        text="Пользователь согласился стать администратором.",
        reply_markup=builder.as_markup()
    )
    
    
@owner_router.callback_query(F.data.startswith("set_alias:"))
async def start_alias_input(call: CallbackQuery, state: FSMContext):
    admin_id = int(call.data.split(":")[1])
    owner_id = call.from_user.id # This is safe because the owner is clicking the button
    
    await call.message.edit_text("Теперь введите псевдоним для нового администратора.")
    
    # Переводим владельца в состояние ожидания псевдонима и сохраняем ID администратора
    await state.set_state(OwnerStates.waiting_for_alias)
    await state.update_data(admin_id=admin_id)


    
    
    
    
    
    
    
    
    
    #await state.update_data(admin_id=admin_id)
    #await message.answer("Введите псевдоним для администратора:")
    #await state.set_state(OwnerStates.waiting_for_alias)

@owner_router.message(OwnerStates.waiting_for_alias)
async def process_admin_alias(message: Message, state: FSMContext):
    alias = message.text.strip()
    data = await state.get_data()
    admin_id = data.get("admin_id")

    db.add_admin(admin_id, alias)
    await message.answer(f"✅ Администратор добавлен!\n🆔 ID: {admin_id}\n👤 Псевдоним: {alias}")
    await state.clear()

# --- Удаление администратора ---
@owner_router.callback_query(F.data == "owner_delete_admin")
async def owner_delete_admin(call: CallbackQuery):
    if call.from_user.id != OWNER_ID:
        await call.answer("🚫 Нет доступа", show_alert=True)
        return

    admins = db.get_all_admins()
    if not admins:
        await call.message.edit_text("⚠️ Нет администраторов для удаления.")
        return

    keyboard = InlineKeyboardMarkup(
        inline_keyboard=[
            [InlineKeyboardButton(text=f"{alias or user_id}", callback_data=f"delete_admin:{user_id}")]
            for user_id, alias in admins
        ]
    )

    await call.message.edit_text("Выберите администратора для удаления:", reply_markup=keyboard)

@owner_router.callback_query(F.data.startswith("delete_admin:"))
async def delete_admin_confirm(call: CallbackQuery):
    if call.from_user.id != OWNER_ID:
        await call.answer("🚫 Нет доступа", show_alert=True)
        return

    admin_id = int(call.data.split(":")[1])
    db.delete_admin(admin_id)
    await call.message.edit_text(f"✅ Администратор {admin_id} удалён.")