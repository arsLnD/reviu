# admin/broadcast.py

from aiogram import Bot
from aiogram.types import InlineKeyboardMarkup, InlineKeyboardButton, Message
from aiogram.exceptions import TelegramAPIError

async def send_broadcast_message(bot: Bot, user_id: int, text: str, photo_id: str = None, video_id: str = None, document_id: str = None, url: str = None, url_text: str = "Перейти"):
    """
    Универсальная функция для отправки рассылочного сообщения.
    Поддерживает текст, фото/видео/документ, и URL-кнопку.
    """
    keyboard = None
    if url:
        keyboard = InlineKeyboardMarkup(inline_keyboard=[
            [InlineKeyboardButton(text=url_text, url=url)]
        ])

    try:
        if document_id:
            await bot.send_document(
                chat_id=user_id,
                document=document_id,
                caption=text,
                reply_markup=keyboard,
                parse_mode="HTML"
            )
        elif video_id:
            await bot.send_video(
                chat_id=user_id,
                video=video_id,
                caption=text,
                reply_markup=keyboard,
                parse_mode="HTML"
            )
        elif photo_id:
            await bot.send_photo(
                chat_id=user_id,
                photo=photo_id,
                caption=text,
                reply_markup=keyboard,
                parse_mode="HTML"
            )
        else:
            await bot.send_message(
                chat_id=user_id,
                text=text,
                reply_markup=keyboard,
                parse_mode="HTML"
            )
        return True
    except TelegramAPIError:
        return False
    except Exception as e:
        print(f"Ошибка при отправке сообщения пользователю {user_id}: {e}")
        return False