# logic/feedback_free.py
from aiogram import Router, F, Bot
from aiogram.types import Message
from db_manager.db import Database
from config import config
import asyncio

feedback_free_router = Router()
db = Database()


@feedback_free_router.message(F.text & ~F.text.startswith('/'))
async def collect_free_feedback(message: Message, bot: Bot):
    """
    Автоматический сбор обратной связи без FSM и кнопок.
    Любое сообщение, не начинающееся с '/', считается отзывом.
    """

    feedback_text = message.text.strip()

    # Игнорируем пустые сообщения
    if not feedback_text:
        return

    # Сохраняем отзыв в базу
    db.add_feedback(user_id=message.from_user.id, description=feedback_text, status=0)

    # Уведомляем администраторов
    for admin_id, _ in db.get_all_admins():
        try:
            await bot.send_message(
                admin_id,
               f"🆕 Получен новый отзыв:\n\n{feedback_text}"
                #f"🆕 Получен новый отзыв от @{message.from_user.username or message.from_user.full_name}:\n\n{feedback_text}"
            )
        except Exception:
            pass

    # Благодарим пользователя
    ans_1 = await message.answer(
        "Спасибо за ваше сообщение! 💬 Мы обязательно его рассмотрим и примем во внимание."
    )
    ans_2 = await message.answer(
        "Если хотите добавить что-то еще — просто напишите сюда!📨"
    )

    # Через 30 секунд очищаем чат
    await asyncio.sleep(30)
    for msg in (ans_1, ans_2, message):
        try:
            await msg.delete()
        except Exception:
            pass