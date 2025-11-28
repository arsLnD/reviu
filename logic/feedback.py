from aiogram import F, Router
from aiogram.exceptions import TelegramBadRequest
from aiogram.fsm.context import FSMContext
from aiogram.fsm.state import State, StatesGroup
from aiogram.types import CallbackQuery, Message

from db_manager.db import Database
from menu.keyboard import rating_keyboard, reviews_keyboard, skip_media_keyboard
from utils.permissions import is_admin
from config import config

REVIEWS_PER_PAGE = 5


class ReviewState(StatesGroup):
    waiting_for_rating = State()
    waiting_for_text = State()
    waiting_for_media = State()


db = Database()
feedback_router = Router()


def _format_rating(rating: int) -> str:
    return "⭐" * rating + "☆" * (5 - rating)


def _format_review_block(review: dict, role: str, is_last: bool = False) -> str:
    """Форматирует один отзыв с красивым оформлением"""
    separator = "─" * 35
    
    # Заголовок отзыва
    header = f"📝 Отзыв №{review['id']}"
    rating_display = _format_rating(review['rating'])
    
    lines = [
        separator,
        f"{header}",
        f"⭐ Оценка: {rating_display}",
        "",
        f"{review['text']}",
    ]
    
    # Информация о фото
    if review.get("photo_file_id"):
        lines.append("")
        lines.append("📷 Фото прикреплено")
    
    # Информация об авторе (только для админов)
    if role == "admin":
        lines.append("")
        user_info = f"👤 Автор: {review.get('full_name') or 'Без имени'}"
        if review.get("username"):
            user_info += f" (@{review['username']})"
        user_info += f" | ID: {review['user_id']}"
        lines.append(user_info)
    
    # Ответ администрации
    if review.get("admin_reply"):
        lines.append("")
        lines.append("💬 Ответ администрации:")
        if role == "admin" and review.get("admin_username"):
            lines.append(f"   от @{review['admin_username']}")
        # Форматируем ответ с отступом для читаемости
        reply_lines = review['admin_reply'].split('\n')
        for reply_line in reply_lines:
            lines.append(f"   {reply_line}")
    
    # Добавляем разделитель в конце, если это не последний отзыв
    if not is_last:
        lines.append("")
        lines.append(separator)
        lines.append("")
    
    return "\n".join(lines)


async def _send_reviews_page(call: CallbackQuery, role: str, page: int):
    # Для пользователей показываем только одобренные, для админов - все
    approved_only = role == "user"
    total_reviews = db.count_reviews(approved_only=approved_only)
    if total_reviews == 0:
        if role == "user":
            empty_text = (
                "📚 Отзывы пользователей\n\n"
                "─" * 30 + "\n"
                "😔 Пока нет отзывов.\n"
                "Будьте первым, кто оставит отзыв!\n"
                "─" * 30
            )
        else:
            empty_text = (
                "📚 Отзывы пользователей (админ-панель)\n\n"
                "─" * 30 + "\n"
                "📭 Отзывов пока нет.\n"
                "─" * 30
            )
        await call.message.edit_text(empty_text)
        await call.answer()
        return

    total_pages = max((total_reviews - 1) // REVIEWS_PER_PAGE + 1, 1)
    page = max(1, min(page, total_pages))

    rows = db.get_reviews_page(page, REVIEWS_PER_PAGE, approved_only=approved_only)
    
    if not rows:
        body = "На этой странице нет отзывов."
    else:
        # Форматируем каждый отзыв с учетом, является ли он последним
        formatted_reviews = []
        for idx, review in enumerate(rows):
            is_last = idx == len(rows) - 1
            formatted_reviews.append(_format_review_block(review, role, is_last=is_last))
        body = "\n".join(formatted_reviews)

    review_ids = [review["id"] for review in rows]
    has_photos = {review["id"]: bool(review.get("photo_file_id")) for review in rows}
    keyboard = reviews_keyboard(role, page, total_pages, review_ids, has_photos)

    # Красивый заголовок с информацией о странице
    if role == "user":
        header = f"📚 Отзывы пользователей"
    else:
        header = f"📚 Отзывы пользователей (админ-панель)"
    
    page_info = f"\n📄 Страница {page} из {total_pages} | Всего отзывов: {total_reviews}"
    text = f"{header}{page_info}\n\n{body}"

    try:
        await call.message.edit_text(text, reply_markup=keyboard)
    except TelegramBadRequest:
        await call.message.answer(text, reply_markup=keyboard)
    await call.answer()


@feedback_router.callback_query(F.data == "review:new")
async def start_review(call: CallbackQuery, state: FSMContext):
    await state.clear()
    await state.set_state(ReviewState.waiting_for_rating)
    user = call.from_user
    await state.update_data(
        author_id=user.id,
        username=user.username,
        full_name=user.full_name,
    )
    await call.message.answer(
        "Оцените ваш опыт от 1 до 5 (где 5 — отлично):",
        reply_markup=rating_keyboard(),
    )
    await call.answer()


@feedback_router.callback_query(ReviewState.waiting_for_rating, F.data.startswith("review:rating:"))
async def set_rating(call: CallbackQuery, state: FSMContext):
    data = await state.get_data()
    if data.get("author_id") != call.from_user.id:
        await call.answer("Эта оценка не для вас.", show_alert=True)
        return

    try:
        rating = int(call.data.split(":")[-1])
    except (ValueError, IndexError):
        await call.answer("Неверное значение.", show_alert=True)
        return

    await state.update_data(rating=rating)
    await state.set_state(ReviewState.waiting_for_text)
    await call.message.answer("Напишите текст отзыва. Постарайтесь быть максимально конкретным.")
    await call.answer()


@feedback_router.message(ReviewState.waiting_for_text)
async def collect_text(message: Message, state: FSMContext):
    data = await state.get_data()
    if data.get("author_id") != message.from_user.id:
        return

    text = (message.text or "").strip()
    if not text:
        await message.answer("Пожалуйста, отправьте текстовое сообщение с отзывом.")
        return

    await state.update_data(text=text)
    await state.set_state(ReviewState.waiting_for_media)
    await message.answer(
        "Хотите прикрепить фото? Отправьте его одним сообщением или нажмите «Пропустить».",
        reply_markup=skip_media_keyboard(),
    )


@feedback_router.message(ReviewState.waiting_for_media, F.photo)
async def collect_photo(message: Message, state: FSMContext):
    data = await state.get_data()
    if data.get("author_id") != message.from_user.id:
        return

    file_id = message.photo[-1].file_id
    await state.update_data(photo=file_id)
    await finalize_review(message, state)


@feedback_router.message(ReviewState.waiting_for_media)
async def handle_skip_text(message: Message, state: FSMContext):
    data = await state.get_data()
    if data.get("author_id") != message.from_user.id:
        return

    if message.text and message.text.lower().strip() in {"пропустить", "/skip", "skip"}:
        await finalize_review(message, state)
        return

    await message.answer("Если хотите прикрепить фото — отправьте его. Либо напишите «Пропустить».")


@feedback_router.callback_query(ReviewState.waiting_for_media, F.data == "review:skip_media")
async def skip_media(call: CallbackQuery, state: FSMContext):
    data = await state.get_data()
    if data.get("author_id") != call.from_user.id:
        await call.answer("Эта кнопка не для вас.", show_alert=True)
        return
    await finalize_review(call.message, state)
    await call.answer()


async def finalize_review(message: Message, state: FSMContext):
    data = await state.get_data()
    rating = data.get("rating")
    text = data.get("text")
    user_id = data.get("author_id")
    username = data.get("username")
    full_name = data.get("full_name")

    if not all([rating, text, user_id]):
        await message.answer("Не удалось сохранить отзыв. Попробуйте еще раз.")
        await state.clear()
        return

    photo_id = data.get("photo")
    db.create_review(
        user_id=user_id,
        username=username,
        full_name=full_name,
        rating=rating,
        text=text,
        photo_file_id=photo_id,
    )

    await state.clear()
    await message.answer("Спасибо! Ваш отзыв отправлен модераторам и появится в списке после проверки.")

    recipients = set(config.bot.admin_ids + [config.bot.owner_id])
    recipients.discard(user_id)

    for admin_id in recipients:
        try:
            await message.bot.send_message(
                admin_id,
                (
                    "🆕 Новый отзыв\n"
                    f"Оценка: {rating}\n"
                    f"Текст: {text}\n"
                    f"Фото: {'есть' if photo_id else 'нет'}"
                ),
            )
        except Exception:
            continue


@feedback_router.callback_query(F.data.startswith("reviews:user:"))
async def reviews_user_pagination(call: CallbackQuery):
    try:
        page_number = int(call.data.split(":")[2])
    except (ValueError, IndexError):
        await call.answer("Неверная страница.", show_alert=True)
        return

    await _send_reviews_page(call, "user", page_number)


@feedback_router.callback_query(F.data.startswith("reviews:admin:"))
async def reviews_admin_pagination(call: CallbackQuery):
    if not is_admin(call.from_user.id):
        await call.answer("Недостаточно прав.", show_alert=True)
        return
    try:
        page_number = int(call.data.split(":")[2])
    except (ValueError, IndexError):
        await call.answer("Неверная страница.", show_alert=True)
        return

    await _send_reviews_page(call, "admin", page_number)


@feedback_router.callback_query(F.data.startswith("reviews:photo:"))
async def show_review_photo(call: CallbackQuery):
    _, _, review_id, role, page = call.data.split(":")
    review = db.get_review(int(review_id))
    if not review or not review.get("photo_file_id"):
        await call.answer("Фото не найдено", show_alert=True)
        return

    if role == "admin" and not is_admin(call.from_user.id):
        await call.answer("Недостаточно прав.", show_alert=True)
        return

    try:
        await call.message.answer_photo(
            review["photo_file_id"],
            caption=f"Фото отзыва №{review['id']}",
        )
    except TelegramBadRequest:
        await call.message.answer("Не удалось отправить фото.")

    await call.answer()