from aiogram import Router
from aiogram.filters import CommandStart
from aiogram.types import Message

from db_manager.db import Database
from menu.keyboard import admin_start_keyboard, user_start_keyboard
from utils.permissions import is_admin

menu_router = Router()
db = Database()


async def _send_welcome_post(message: Message, keyboard):
    welcome = db.get_welcome_post()
    text = welcome.get("text") or ""
    media_type = welcome.get("media_type")
    media_file_id = welcome.get("media_file_id")

    if media_type == "photo" and media_file_id:
        await message.answer_photo(photo=media_file_id, caption=text, reply_markup=keyboard)
    elif media_type == "video" and media_file_id:
        await message.answer_video(video=media_file_id, caption=text, reply_markup=keyboard)
    else:
        await message.answer(text, reply_markup=keyboard)


@menu_router.message(CommandStart())
async def command_start(message: Message) -> None:
    user = message.from_user
    db.upsert_user(user.id, user.username, user.full_name)

    keyboard = admin_start_keyboard() if is_admin(user.id) else user_start_keyboard()
    await _send_welcome_post(message, keyboard)