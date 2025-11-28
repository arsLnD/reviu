import os
import sqlite3
from typing import Any, Dict, List, Optional, Tuple

# Попытка импортировать PostgreSQL драйвер
try:
    import psycopg2
    from psycopg2.extras import RealDictCursor
    POSTGRES_AVAILABLE = True
except ImportError:
    POSTGRES_AVAILABLE = False
    psycopg2 = None

from config import config

DEFAULT_WELCOME_TEXT = (
    "Привет! 👋\n\n"
    "Добро пожаловать в нашего Telegram-бота отзывов. "
    "Нажмите на кнопку ниже, чтобы оставить отзыв или посмотреть мнения других пользователей."
)


class Database:
    def __init__(self, database_url: Optional[str] = None, path_to_database: Optional[str] = None) -> None:
        """
        Инициализация базы данных.
        Если указан database_url (PostgreSQL) - используем его, иначе SQLite.
        """
        self.use_postgres = False
        self.connection = None
        self.db_path = None
        
        # Приоритет: database_url из параметра > config > SQLite
        db_url = database_url or config.database.url
        
        if db_url and POSTGRES_AVAILABLE and psycopg2:
            # Используем PostgreSQL
            self.use_postgres = True
            self.connection = psycopg2.connect(db_url)
            self.connection.autocommit = False
        else:
            # Используем SQLite
            if not path_to_database:
                path_to_database = config.database.path
            self.db_path = path_to_database
            os.makedirs(os.path.dirname(path_to_database), exist_ok=True)
            self.connection = sqlite3.connect(path_to_database, check_same_thread=False)
            self.connection.row_factory = sqlite3.Row
        
        self._create_tables()

    def _execute(self, query: str, params: tuple = ()) -> Any:
        """Универсальный метод выполнения запросов для SQLite и PostgreSQL"""
        # Адаптируем запрос для PostgreSQL (заменяем ? на %s)
        if self.use_postgres:
            query = query.replace('?', '%s')
            cursor = self.connection.cursor(cursor_factory=RealDictCursor)
        else:
            cursor = self.connection.cursor()
        
        try:
            cursor.execute(query, params)
            return cursor
        except Exception as e:
            if self.use_postgres:
                self.connection.rollback()
            raise

    def _execute_many(self, query: str, params_list: list) -> None:
        """Универсальный метод для массовых операций"""
        cursor = self.connection.cursor()
        try:
            if self.use_postgres:
                query = query.replace('?', '%s')
            cursor.executemany(query, params_list)
        except Exception as e:
            self.connection.rollback()
            raise

    def _fetchone(self, cursor: Any) -> Optional[Dict[str, Any]]:
        """Получить одну строку результата"""
        row = cursor.fetchone()
        if not row:
            return None
        # Для PostgreSQL RealDictCursor уже возвращает dict
        if self.use_postgres:
            return dict(row)
        # Для SQLite Row тоже можно конвертировать в dict
        return dict(row)

    def _fetchall(self, cursor: Any) -> List[Dict[str, Any]]:
        """Получить все строки результата"""
        rows = cursor.fetchall()
        if self.use_postgres:
            return [dict(row) for row in rows]
        return [dict(row) for row in rows]

    def _create_tables(self) -> None:
        """Создание таблиц с поддержкой SQLite и PostgreSQL"""
        
        # Адаптация SQL для PostgreSQL
        auto_increment = "SERIAL" if self.use_postgres else "INTEGER PRIMARY KEY AUTOINCREMENT"
        integer_primary = "INTEGER PRIMARY KEY" if not self.use_postgres else "SERIAL PRIMARY KEY"
        timestamp_default = "DEFAULT CURRENT_TIMESTAMP" if not self.use_postgres else "DEFAULT NOW()"
        
        with self.connection:
            # Таблица users
            if self.use_postgres:
                self._execute("""
                    CREATE TABLE IF NOT EXISTS users (
                        user_id BIGINT PRIMARY KEY,
                        username TEXT,
                        full_name TEXT,
                        first_seen TIMESTAMP DEFAULT NOW(),
                        last_seen TIMESTAMP DEFAULT NOW()
                    )
                """)
            else:
                self._execute("""
                    CREATE TABLE IF NOT EXISTS users (
                        user_id INTEGER PRIMARY KEY,
                        username TEXT,
                        full_name TEXT,
                        first_seen TEXT DEFAULT CURRENT_TIMESTAMP,
                        last_seen TEXT DEFAULT CURRENT_TIMESTAMP
                    )
                """)

            # Таблица reviews
            if self.use_postgres:
                self._execute("""
                    CREATE TABLE IF NOT EXISTS reviews (
                        id SERIAL PRIMARY KEY,
                        user_id BIGINT NOT NULL,
                        username TEXT,
                        full_name TEXT,
                        rating INTEGER NOT NULL CHECK(rating BETWEEN 1 AND 5),
                        text TEXT NOT NULL,
                        photo_file_id TEXT,
                        created_at TIMESTAMP DEFAULT NOW(),
                        is_approved INTEGER DEFAULT 0,
                        admin_reply TEXT,
                        admin_id BIGINT,
                        admin_username TEXT,
                        admin_reply_at TIMESTAMP
                    )
                """)
            else:
                self._execute("""
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
                """)
            
            # Добавляем колонку is_approved если таблица уже существует (только для SQLite)
            if not self.use_postgres:
                try:
                    self._execute("ALTER TABLE reviews ADD COLUMN is_approved INTEGER DEFAULT 0")
                except sqlite3.OperationalError:
                    pass  # Колонка уже существует

            # Таблица welcome_post
            if self.use_postgres:
                self._execute("""
                    CREATE TABLE IF NOT EXISTS welcome_post (
                        id INTEGER PRIMARY KEY CHECK(id = 1),
                        text TEXT NOT NULL,
                        media_type TEXT,
                        media_file_id TEXT,
                        updated_at TIMESTAMP DEFAULT NOW(),
                        updated_by BIGINT
                    )
                """)
            else:
                self._execute("""
                    CREATE TABLE IF NOT EXISTS welcome_post (
                        id INTEGER PRIMARY KEY CHECK(id = 1),
                        text TEXT NOT NULL,
                        media_type TEXT,
                        media_file_id TEXT,
                        updated_at TEXT DEFAULT CURRENT_TIMESTAMP,
                        updated_by INTEGER
                    )
                """)

            # Вставка дефолтного приветствия
            if self.use_postgres:
                self._execute("""
                    INSERT INTO welcome_post (id, text)
                    VALUES (1, %s)
                    ON CONFLICT (id) DO NOTHING
                """, (DEFAULT_WELCOME_TEXT,))
            else:
                self._execute("""
                    INSERT OR IGNORE INTO welcome_post (id, text)
                    VALUES (1, ?)
                """, (DEFAULT_WELCOME_TEXT,))

    # --- USERS ---
    def upsert_user(self, user_id: int, username: Optional[str], full_name: Optional[str]) -> None:
        if self.use_postgres:
            with self.connection:
                self._execute("""
                    INSERT INTO users (user_id, username, full_name)
                    VALUES (%s, %s, %s)
                    ON CONFLICT(user_id) DO UPDATE SET
                        username = EXCLUDED.username,
                        full_name = EXCLUDED.full_name,
                        last_seen = NOW()
                """, (user_id, username, full_name))
        else:
            with self.connection:
                self._execute("""
                    INSERT INTO users (user_id, username, full_name)
                    VALUES (?, ?, ?)
                    ON CONFLICT(user_id) DO UPDATE SET
                        username = excluded.username,
                        full_name = excluded.full_name,
                        last_seen = CURRENT_TIMESTAMP
                """, (user_id, username, full_name))

    # --- WELCOME POST ---
    def get_welcome_post(self) -> Dict[str, Any]:
        cursor = self._execute("SELECT * FROM welcome_post WHERE id = 1")
        row = self._fetchone(cursor)
        if not row:
            return {"text": DEFAULT_WELCOME_TEXT, "media_type": None, "media_file_id": None}
        return row

    def update_welcome_post(
        self,
        text: str,
        media_type: Optional[str],
        media_file_id: Optional[str],
        updated_by: int,
    ) -> None:
        if self.use_postgres:
            with self.connection:
                self._execute("""
                    UPDATE welcome_post
                    SET text = %s, media_type = %s, media_file_id = %s, updated_at = NOW(), updated_by = %s
                    WHERE id = 1
                """, (text, media_type, media_file_id, updated_by))
        else:
            with self.connection:
                self._execute("""
                    UPDATE welcome_post
                    SET text = ?, media_type = ?, media_file_id = ?, updated_at = CURRENT_TIMESTAMP, updated_by = ?
                    WHERE id = 1
                """, (text, media_type, media_file_id, updated_by))

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
        if self.use_postgres:
            with self.connection:
                cursor = self._execute("""
                    INSERT INTO reviews (user_id, username, full_name, rating, text, photo_file_id)
                    VALUES (%s, %s, %s, %s, %s, %s)
                    RETURNING id
                """, (user_id, username, full_name, rating, text, photo_file_id))
                result = cursor.fetchone()
                return result[0] if result else 0
        else:
            with self.connection:
                cursor = self._execute("""
                    INSERT INTO reviews (user_id, username, full_name, rating, text, photo_file_id)
                    VALUES (?, ?, ?, ?, ?, ?)
                """, (user_id, username, full_name, rating, text, photo_file_id))
            return cursor.lastrowid

    def count_reviews(self, approved_only: bool = True) -> int:
        if approved_only:
            cursor = self._execute("SELECT COUNT(*) FROM reviews WHERE is_approved = 1")
        else:
            cursor = self._execute("SELECT COUNT(*) FROM reviews")
        result = cursor.fetchone()
        return result[0] if result else 0

    def get_reviews_page(self, page: int, per_page: int, approved_only: bool = True) -> List[Dict[str, Any]]:
        offset = (page - 1) * per_page
        if approved_only:
            cursor = self._execute("""
                SELECT *
                FROM reviews
                WHERE is_approved = 1
                ORDER BY created_at DESC, id DESC
                LIMIT ? OFFSET ?
            """, (per_page, offset))
        else:
            cursor = self._execute("""
                SELECT *
                FROM reviews
                ORDER BY created_at DESC, id DESC
                LIMIT ? OFFSET ?
            """, (per_page, offset))
        return self._fetchall(cursor)
    
    def get_pending_reviews(self) -> List[Dict[str, Any]]:
        """Получить все неодобренные отзывы"""
        cursor = self._execute("""
            SELECT *
            FROM reviews
            WHERE is_approved = 0
            ORDER BY created_at DESC, id DESC
        """)
        return self._fetchall(cursor)
    
    def approve_review(self, review_id: int) -> bool:
        """Одобрить отзыв"""
        with self.connection:
            cursor = self._execute("UPDATE reviews SET is_approved = 1 WHERE id = ?", (review_id,))
            return cursor.rowcount > 0
    
    def delete_review(self, review_id: int) -> bool:
        """Удалить отзыв"""
        with self.connection:
            cursor = self._execute("DELETE FROM reviews WHERE id = ?", (review_id,))
            return cursor.rowcount > 0

    def get_review(self, review_id: int) -> Optional[Dict[str, Any]]:
        cursor = self._execute("SELECT * FROM reviews WHERE id = ?", (review_id,))
        return self._fetchone(cursor)

    def save_admin_reply(
        self, review_id: int, admin_id: int, admin_username: Optional[str], reply_text: str
    ) -> None:
        if self.use_postgres:
            with self.connection:
                self._execute("""
                    UPDATE reviews
                    SET admin_reply = %s,
                        admin_id = %s,
                        admin_username = %s,
                        admin_reply_at = NOW()
                    WHERE id = %s
                """, (reply_text, admin_id, admin_username, review_id))
        else:
            with self.connection:
                self._execute("""
                    UPDATE reviews
                    SET admin_reply = ?,
                        admin_id = ?,
                        admin_username = ?,
                        admin_reply_at = CURRENT_TIMESTAMP
                    WHERE id = ?
                """, (reply_text, admin_id, admin_username, review_id))

    def get_review_author(self, review_id: int) -> Optional[Tuple[int, str]]:
        cursor = self._execute("SELECT user_id, full_name FROM reviews WHERE id = ?", (review_id,))
        row = self._fetchone(cursor)
        if not row:
            return None
        return row['user_id'], row.get('full_name') or ""
