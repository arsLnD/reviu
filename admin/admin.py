from aiogram import F, Router, Bot
from aiogram.exceptions import TelegramBadRequest
from aiogram.fsm.context import FSMContext
from aiogram.fsm.state import State, StatesGroup
from aiogram.types import CallbackQuery, Message

from db_manager.db import Database
from menu.keyboard import moderation_keyboard
from utils.permissions import is_admin
from logic.feedback import _format_rating

admin_router = Router()
db = Database()


class WelcomeState(StatesGroup):
    waiting_for_content = State()


class AdminReplyState(StatesGroup):
    waiting_for_reply = State()


@admin_router.callback_query(F.data == "welcome:edit")
async def start_welcome_edit(call: CallbackQuery, state: FSMContext):
    if not is_admin(call.from_user.id):
        await call.answer("Недостаточно прав.", show_alert=True)
        return

    await state.set_state(WelcomeState.waiting_for_content)
    await call.message.answer(
        "Отправьте новый приветственный пост.\n"
        "Можно приложить фото или видео, текст укажите в подписи.\n"
        "Чтобы оставить только текст — пришлите обычное сообщение."
    )
    await call.answer()


@admin_router.message(WelcomeState.waiting_for_content)
async def process_welcome_content(message: Message, state: FSMContext):
    if not is_admin(message.from_user.id):
        return

    text = (message.caption or message.text or "").strip()
    if not text:
        await message.answer("Текст приветствия обязателен. Попробуйте снова.")
        return

    media_type = None
    media_file_id = None

    if message.photo:
        media_type = "photo"
        media_file_id = message.photo[-1].file_id
    elif message.video:
        media_type = "video"
        media_file_id = message.video.file_id

    db.update_welcome_post(
        text=text,
        media_type=media_type,
        media_file_id=media_file_id,
        updated_by=message.from_user.id,
    )

    await message.answer("Приветственный пост обновлён ✅")
    await state.clear()


@admin_router.callback_query(F.data.startswith("reviews:reply:"))
async def start_review_reply(call: CallbackQuery, state: FSMContext):
    if not is_admin(call.from_user.id):
        await call.answer("Недостаточно прав.", show_alert=True)
        return

    _, _, review_id, page = call.data.split(":")
    review = db.get_review(int(review_id))
    if not review:
        await call.answer("Отзыв не найден.", show_alert=True)
        return

    await state.set_state(AdminReplyState.waiting_for_reply)
    await state.update_data(review_id=review["id"], return_page=int(page))
    await call.message.answer(
        f"Напишите ответ для пользователя {review.get('full_name') or review['user_id']} по отзыву №{review['id']}."
    )
    await call.answer()


@admin_router.message(AdminReplyState.waiting_for_reply)
async def send_admin_reply(message: Message, state: FSMContext):
    if not is_admin(message.from_user.id):
        return

    data = await state.get_data()
    review_id = data.get("review_id")
    review = db.get_review(review_id) if review_id else None
    if not review:
        await message.answer("Не удалось найти отзыв. Попробуйте заново открыть список отзывов.")
        await state.clear()
        return

    reply_text = (message.text or message.caption or "").strip()
    if not reply_text:
        await message.answer("Ответ не может быть пустым.")
        return

    db.save_admin_reply(
        review_id=review_id,
        admin_id=message.from_user.id,
        admin_username=message.from_user.username,
        reply_text=reply_text,
    )

    try:
        await message.bot.send_message(
            chat_id=review["user_id"],
            text=(
                f"Администрация ответила на ваш отзыв №{review_id}:\n\n"
                f"{reply_text}"
            ),
        )
        delivered = True
    except TelegramBadRequest:
        delivered = False

    await message.answer(
        "Ответ отправлен пользователю." if delivered else "Ответ сохранён, но отправить сообщение пользователю не удалось."
    )

    await state.clear()


@admin_router.callback_query(F.data == "admin:moderation")
async def show_moderation_queue(call: CallbackQuery):
    """Показать очередь модерации"""
    if not is_admin(call.from_user.id):
        await call.answer("Недостаточно прав.", show_alert=True)
        return
    
    pending = db.get_pending_reviews()
    
    if not pending:
        await call.message.edit_text("Нет отзывов на модерации. Все отзывы проверены! ✅")
        await call.answer()
        return
    
    # Показываем первый отзыв из очереди
    review = pending[0]
    text_lines = [
        f"⏳ Отзыв на модерации (всего: {len(pending)})",
        "",
        f"№{review['id']} · {_format_rating(review['rating'])}",
        f"👤 {review.get('full_name') or 'Без имени'}",
        f"ID: {review['user_id']}",
        "",
        review['text'],
    ]
    
    if review.get("photo_file_id"):
        text_lines.append("\n📎 Фото прикреплено")
    
    text = "\n".join(text_lines)
    keyboard = moderation_keyboard(review['id'])
    
    try:
        if review.get("photo_file_id"):
            # Для фото всегда отправляем новое сообщение, так как edit_text не работает с медиа
            await call.message.answer_photo(
                review["photo_file_id"],
                caption=text,
                reply_markup=keyboard
            )
        else:
            await call.message.edit_text(text, reply_markup=keyboard)
    except TelegramBadRequest:
        # Если не удалось отредактировать, отправляем новое сообщение
        if review.get("photo_file_id"):
            await call.message.answer_photo(
                review["photo_file_id"],
                caption=text,
                reply_markup=keyboard
            )
        else:
            await call.message.answer(text, reply_markup=keyboard)
    
    await call.answer()


@admin_router.callback_query(F.data.startswith("moderation:approve:"))
async def approve_review(call: CallbackQuery, bot: Bot):
    """Одобрить отзыв"""
    if not is_admin(call.from_user.id):
        await call.answer("Недостаточно прав.", show_alert=True)
        return
    
    try:
        review_id = int(call.data.split(":")[2])
    except (ValueError, IndexError):
        await call.answer("Неверный ID отзыва.", show_alert=True)
        return
    
    review = db.get_review(review_id)
    if not review:
        await call.answer("Отзыв не найден.", show_alert=True)
        return
    
    if db.approve_review(review_id):
        await call.message.edit_text(f"✅ Отзыв №{review_id} одобрен и теперь виден пользователям.")
        
        # Уведомляем автора отзыва
        try:
            await bot.send_message(
                review["user_id"],
                f"Ваш отзыв №{review_id} был одобрен модератором и теперь виден другим пользователям! 🎉"
            )
        except Exception:
            pass  # Пользователь мог заблокировать бота
        
        # Показываем следующий отзыв на модерации, если есть
        pending = db.get_pending_reviews()
        if pending:
            await show_moderation_queue(call)
        else:
            await call.message.answer("Все отзывы проверены! ✅")
    else:
        await call.answer("Не удалось одобрить отзыв.", show_alert=True)
    
    await call.answer()


@admin_router.callback_query(F.data.startswith("moderation:reject:"))
async def reject_review(call: CallbackQuery, bot: Bot):
    """Отклонить отзыв (удалить без уведомления)"""
    if not is_admin(call.from_user.id):
        await call.answer("Недостаточно прав.", show_alert=True)
        return
    
    try:
        review_id = int(call.data.split(":")[2])
    except (ValueError, IndexError):
        await call.answer("Неверный ID отзыва.", show_alert=True)
        return
    
    review = db.get_review(review_id)
    if not review:
        await call.answer("Отзыв не найден.", show_alert=True)
        return
    
    if db.delete_review(review_id):
        await call.message.edit_text(f"❌ Отзыв №{review_id} отклонён и удалён.")
        
        # Показываем следующий отзыв на модерации, если есть
        pending = db.get_pending_reviews()
        if pending:
            await show_moderation_queue(call)
        else:
            await call.message.answer("Все отзывы проверены! ✅")
    else:
        await call.answer("Не удалось отклонить отзыв.", show_alert=True)
    
    await call.answer()


@admin_router.callback_query(F.data.startswith("moderation:delete:"))
async def delete_review_from_moderation(call: CallbackQuery):
    """Удалить отзыв из модерации"""
    if not is_admin(call.from_user.id):
        await call.answer("Недостаточно прав.", show_alert=True)
        return
    
    try:
        review_id = int(call.data.split(":")[2])
    except (ValueError, IndexError):
        await call.answer("Неверный ID отзыва.", show_alert=True)
        return
    
    if db.delete_review(review_id):
        await call.message.edit_text(f"🗑️ Отзыв №{review_id} удалён.")
        
        # Показываем следующий отзыв на модерации, если есть
        pending = db.get_pending_reviews()
        if pending:
            await show_moderation_queue(call)
        else:
            await call.message.answer("Все отзывы проверены! ✅")
    else:
        await call.answer("Не удалось удалить отзыв.", show_alert=True)
    
    await call.answer()


@admin_router.callback_query(F.data.startswith("reviews:delete:"))
async def delete_review_from_list(call: CallbackQuery):
    """Удалить отзыв из списка просмотра"""
    if not is_admin(call.from_user.id):
        await call.answer("Недостаточно прав.", show_alert=True)
        return
    
    try:
        parts = call.data.split(":")
        review_id = int(parts[2])
        page = int(parts[3])
    except (ValueError, IndexError):
        await call.answer("Неверные параметры.", show_alert=True)
        return
    
    if db.delete_review(review_id):
        await call.answer(f"Отзыв №{review_id} удалён.", show_alert=True)
        # Обновляем страницу отзывов
        from logic.feedback import _send_reviews_page
        await _send_reviews_page(call, "admin", page)
    else:
        await call.answer("Не удалось удалить отзыв.", show_alert=True)
