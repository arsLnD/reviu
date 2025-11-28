import os
import sqlite3
from typing import Any, Dict, List, Optional, Tuple

DEFAULT_WELCOME_TEXT = (
    "Привет! 👋\n\n"
    "Добро пожаловать в нашего Telegram-бота отзывов. "
    "Нажмите на кнопку ниже, чтобы оставить отзыв или посмотреть мнения других пользователей."
)


class Database:
    def __init__(self, path_to_database: str = "database/database.db") -> None:
        os.makedirs(os.path.dirname(path_to_database), exist_ok=True)
        self.connection = sqlite3.connect(path_to_database, check_same_thread=False)
        self.connection.row_factory = sqlite3.Row
        self._create_tables()

    def _create_tables(self) -> None:
        with self.connection:
            self.connection.execute(
                """
                CREATE TABLE IF NOT EXISTS users (
                    user_id INTEGER PRIMARY KEY,
                    username TEXT,
                    full_name TEXT,
                    first_seen TEXT DEFAULT CURRENT_TIMESTAMP,
                    last_seen TEXT DEFAULT CURRENT_TIMESTAMP
                )
                """
            )

            self.connection.execute(
                """
                CREATE TABLE IF NOT EXISTS reviews (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    user_id INTEGER NOT NULL,
                    username TEXT,
                    full_name TEXT,
                    rating INTEGER NOT NULL CHECK(rating BETWEEN 1 AND 5),
                    text TEXT NOT NULL,
                    photo_file_id TEXT,
                    created_at TEXT DEFAULT CURRENT_TIMESTAMP,
                    is_approved INTEGER DEFAULT 0,
                    admin_reply TEXT,
                    admin_id INTEGER,
                    admin_username TEXT,
                    admin_reply_at TEXT
                )
                """
            )
            
            # Добавляем колонку is_approved если таблица уже существует
            try:
                self.connection.execute("ALTER TABLE reviews ADD COLUMN is_approved INTEGER DEFAULT 0")
            except sqlite3.OperationalError:
                pass  # Колонка уже существует

            self.connection.execute(
                """
                CREATE TABLE IF NOT EXISTS welcome_post (
                    id INTEGER PRIMARY KEY CHECK(id = 1),
                    text TEXT NOT NULL,
                    media_type TEXT,
                    media_file_id TEXT,
                    updated_at TEXT DEFAULT CURRENT_TIMESTAMP,
                    updated_by INTEGER
                )
                """
            )

            self.connection.execute(
                """
                INSERT OR IGNORE INTO welcome_post (id, text)
                VALUES (1, ?)
                """,
                (DEFAULT_WELCOME_TEXT,),
            )

    # --- USERS ---
    def upsert_user(self, user_id: int, username: Optional[str], full_name: Optional[str]) -> None:
        with self.connection:
            self.connection.execute(
                """
                INSERT INTO users (user_id, username, full_name)
                VALUES (?, ?, ?)
                ON CONFLICT(user_id) DO UPDATE SET
                    username = excluded.username,
                    full_name = excluded.full_name,
                    last_seen = CURRENT_TIMESTAMP
                """,
                (user_id, username, full_name),
            )

    # --- WELCOME POST ---
    def get_welcome_post(self) -> Dict[str, Any]:
        cursor = self.connection.execute("SELECT * FROM welcome_post WHERE id = 1")
        row = cursor.fetchone()
        if not row:
            return {"text": DEFAULT_WELCOME_TEXT, "media_type": None, "media_file_id": None}
        return dict(row)

    def update_welcome_post(
        self,
        text: str,
        media_type: Optional[str],
        media_file_id: Optional[str],
        updated_by: int,
    ) -> None:
        with self.connection:
            self.connection.execute(
                """
                UPDATE welcome_post
                SET text = ?, media_type = ?, media_file_id = ?, updated_at = CURRENT_TIMESTAMP, updated_by = ?
                WHERE id = 1
                """,
                (text, media_type, media_file_id, updated_by),
            )

    # --- REVIEWS ---
    def create_review(
        self,
        user_id: int,
        username: Optional[str],
        full_name: Optional[str],
        rating: int,
        text: str,
        photo_file_id: Optional[str] = None,
    ) -> int:

        with self.connection:
            cursor = self.connection.execute(
                """
                INSERT INTO reviews (user_id, username, full_name, rating, text, photo_file_id)
                VALUES (?, ?, ?, ?, ?, ?)
                """,
                (user_id, username, full_name, rating, text, photo_file_id),
            )
        return cursor.lastrowid

    def count_reviews(self, approved_only: bool = True) -> int:
        if approved_only:
            cursor = self.connection.execute("SELECT COUNT(*) FROM reviews WHERE is_approved = 1")
        else:
            cursor = self.connection.execute("SELECT COUNT(*) FROM reviews")
        result = cursor.fetchone()
        return result[0] if result else 0

    def get_reviews_page(self, page: int, per_page: int, approved_only: bool = True) -> List[Dict[str, Any]]:
        offset = (page - 1) * per_page
        if approved_only:
            cursor = self.connection.execute(
                """
                SELECT *
                FROM reviews
                WHERE is_approved = 1
                ORDER BY created_at DESC, id DESC
                LIMIT ? OFFSET ?
                """,
                (per_page, offset),
            )
        else:
            cursor = self.connection.execute(
                """
                SELECT *
                FROM reviews
                ORDER BY created_at DESC, id DESC
                LIMIT ? OFFSET ?
                """,
                (per_page, offset),
            )
        return [dict(row) for row in cursor.fetchall()]
    
    def get_pending_reviews(self) -> List[Dict[str, Any]]:
        """Получить все неодобренные отзывы"""
        cursor = self.connection.execute(
            """
            SELECT *
            FROM reviews
            WHERE is_approved = 0
            ORDER BY created_at DESC, id DESC
            """
        )
        return [dict(row) for row in cursor.fetchall()]
    
    def approve_review(self, review_id: int) -> bool:
        """Одобрить отзыв"""
        with self.connection:
            cursor = self.connection.execute(
                "UPDATE reviews SET is_approved = 1 WHERE id = ?",
                (review_id,)
            )
            return cursor.rowcount > 0
    
    def delete_review(self, review_id: int) -> bool:
        """Удалить отзыв"""
        with self.connection:
            cursor = self.connection.execute("DELETE FROM reviews WHERE id = ?", (review_id,))
            return cursor.rowcount > 0

    def get_review(self, review_id: int) -> Optional[Dict[str, Any]]:
        cursor = self.connection.execute("SELECT * FROM reviews WHERE id = ?", (review_id,))
        row = cursor.fetchone()
        return dict(row) if row else None

    def save_admin_reply(
        self, review_id: int, admin_id: int, admin_username: Optional[str], reply_text: str
    ) -> None:
        with self.connection:
            self.connection.execute(
                """
                UPDATE reviews
                SET admin_reply = ?,
                    admin_id = ?,
                    admin_username = ?,
                    admin_reply_at = CURRENT_TIMESTAMP
                WHERE id = ?
                """,
                (reply_text, admin_id, admin_username, review_id),
            )

    def get_review_author(self, review_id: int) -> Optional[Tuple[int, str]]:
        cursor = self.connection.execute(
            "SELECT user_id, full_name FROM reviews WHERE id = ?", (review_id,)
        )
        row = cursor.fetchone()
        if not row:
            return None
        return row[0], row[1] or ""