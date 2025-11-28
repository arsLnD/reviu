from aiogram.utils.keyboard import InlineKeyboardBuilder
from aiogram.types import InlineKeyboardMarkup, InlineKeyboardButton


def user_start_keyboard() -> InlineKeyboardMarkup:
    builder = InlineKeyboardBuilder()
    builder.button(text="📝 Оставить отзыв", callback_data="review:new")
    builder.button(text="📖 Посмотреть отзывы", callback_data="reviews:user:1")
    builder.adjust(1)
    return builder.as_markup()


def admin_start_keyboard() -> InlineKeyboardMarkup:
    builder = InlineKeyboardBuilder()
    builder.button(text="✏️ Изменить привет", callback_data="welcome:edit")
    builder.button(text="📚 Посмотреть отзывы", callback_data="reviews:admin:1")
    builder.button(text="✅ Модерация отзывов", callback_data="admin:moderation")
    builder.adjust(1)
    return builder.as_markup()


def rating_keyboard() -> InlineKeyboardMarkup:
    builder = InlineKeyboardBuilder()
    for rate in range(1, 6):
        builder.button(text=f"{rate}⭐", callback_data=f"review:rating:{rate}")
    builder.adjust(5)
    return builder.as_markup()


def skip_media_keyboard() -> InlineKeyboardMarkup:
    builder = InlineKeyboardBuilder()
    builder.button(text="Пропустить", callback_data="review:skip_media")
    return builder.as_markup()


def reviews_keyboard(
    role: str,
    page: int,
    total_pages: int,
    review_ids: list[int],
    has_photos: dict[int, bool],
) -> InlineKeyboardMarkup:
    rows: list[list[InlineKeyboardButton]] = []

    if role == "admin":
        for review_id in review_ids:
            row = [
                InlineKeyboardButton(
                    text=f"Ответить №{review_id}",
                    callback_data=f"reviews:reply:{review_id}:{page}",
                ),
                InlineKeyboardButton(
                    text=f"🗑️ Удалить №{review_id}",
                    callback_data=f"reviews:delete:{review_id}:{page}",
                )
            ]
            if has_photos.get(review_id):
                row.append(
                    InlineKeyboardButton(
                        text=f"Фото №{review_id}",
                        callback_data=f"reviews:photo:{review_id}:{role}:{page}",
                    )
                )
            rows.append(row)
    else:
        for review_id in review_ids:
            if has_photos.get(review_id):
                rows.append(
                    [
                        InlineKeyboardButton(
                            text=f"Фото №{review_id}",
                            callback_data=f"reviews:photo:{review_id}:{role}:{page}",
                        )
                    ]
                )

    nav_row: list[InlineKeyboardButton] = []
    if page > 1:
        nav_row.append(
            InlineKeyboardButton(text="⬅️ Назад", callback_data=f"reviews:{role}:{page-1}")
        )
    if page < total_pages:
        nav_row.append(
            InlineKeyboardButton(text="Вперед ➡️", callback_data=f"reviews:{role}:{page+1}")
        )
    if nav_row:
        rows.append(nav_row)

    return InlineKeyboardMarkup(inline_keyboard=rows) if rows else InlineKeyboardMarkup(inline_keyboard=[])


def moderation_keyboard(review_id: int) -> InlineKeyboardMarkup:
    """Клавиатура для модерации отзыва"""
    builder = InlineKeyboardBuilder()
    builder.button(text="✅ Одобрить", callback_data=f"moderation:approve:{review_id}")
    builder.button(text="❌ Отклонить", callback_data=f"moderation:reject:{review_id}")
    builder.button(text="🗑️ Удалить", callback_data=f"moderation:delete:{review_id}")
    builder.adjust(1)
    return builder.as_markup()