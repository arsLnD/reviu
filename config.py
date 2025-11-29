from dataclasses import dataclass
from environs import Env


@dataclass
class TgBot:
    token: str
    owner_id: int
    admin_ids: list[int]


@dataclass
class DatabaseConfig:
    url: str | None = None  # PostgreSQL connection string (DATABASE_URL)
    path: str = "database/database.db"  # SQLite path (если DATABASE_URL не указан)
    backup_dir: str = "backups"  # Директория для бэкапов SQLite
    backup_interval_hours: int = 24  # Интервал между бэкапами в часах
    backup_keep_count: int = 10  # Количество бэкапов для хранения


@dataclass
class Config:
    bot: TgBot
    database: DatabaseConfig


# Инициализация Env
env = Env()
env.read_env()  # Читаем из .env файла в корне проекта


# Создаем конфиг
config = Config(
    bot=TgBot(
        token=env('BOT_TOKEN'),
        owner_id=env.int('OWNER_ID'),
        admin_ids=env.list('ADMIN_IDS', subcast=int, default=[])
    ),
    database=DatabaseConfig(
        url=env('DATABASE_URL', default=None),
        path=env('DATABASE_PATH', default="database/database.db"),
        backup_dir=env('BACKUP_DIR', default="backups"),
        backup_interval_hours=env.int('BACKUP_INTERVAL_HOURS', default=24),
        backup_keep_count=env.int('BACKUP_KEEP_COUNT', default=10)
    ),
)