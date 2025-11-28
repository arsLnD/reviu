# admin/broadcast_poll.py

from aiogram import Router, F, Bot
from aiogram.types import Message
from aiogram.filters import Command
from aiogram.exceptions import TelegramAPIError

from db_manager.db import Database

db = Database()
broadcast_poll_router = Router()


@broadcast_poll_router.message(Command("broadcast_poll"))
async def start_broadcast_poll(message: Message):
    """Запуск рассылки опроса"""
    if not db.is_admin(message.from_user.id):
        await message.answer("🚫 У вас нет прав для запуска рассылки.")
        return

    await message.answer(
        "🗳 Отправьте сюда опрос, который нужно разослать всем пользователям.\n\n"
        "Создайте его прямо в Telegram → выберите «Опрос» → введите вопрос, ответы и отправьте сюда."
    )


@broadcast_poll_router.message(F.poll)
async def receive_poll(message: Message, bot: Bot):
    """Получение опроса и рассылка"""
    if not db.is_admin(message.from_user.id):
        await message.answer("🚫 Только администраторы могут рассылать опросы.")
        return

    poll = message.poll
    question = poll.question
    options = [opt.text for opt in poll.options]
    is_anonymous = poll.is_anonymous
    allows_multiple_answers = poll.allows_multiple_answers

    users = db.get_all_users()  # должен вернуть список user_id
    sent = 0

    await message.answer("📤 Начинаю рассылку опроса...")

    for user_id in users:
        try:
            await bot.send_poll(
                chat_id=user_id,
                question=question,
                options=options,
                is_anonymous=is_anonymous,
                allows_multiple_answers=allows_multiple_answers
            )
            sent += 1
        except TelegramAPIError:
            continue
        except Exception as e:
            print(f"Ошибка при отправке пользователю {user_id}: {e}")

    await message.answer(f"✅ Рассылка завершена.\nОпрос отправлен {sent} пользователям.")