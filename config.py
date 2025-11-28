from dataclasses import dataclass
from environs import Env


@dataclass
class TgBot:
    token: str
    owner_id: int
    admin_ids: list[int]


@dataclass
class Config:
    bot: TgBot


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
)