# main.py

import asyncio
from aiogram import Bot, Dispatcher
from config import config
from utils.logger import setup_logging, logger
from db_manager.db import Database

from menu.start_menu import menu_router
from logic.feedback import feedback_router
from admin.admin import admin_router


async def main():
    setup_logging()
    logger.info("Starting bot application")

    # Инициализируем базу данных (автоматически выберет PostgreSQL или SQLite)
    db = Database()
    if db.use_postgres:
        logger.info("Using PostgreSQL database")
    else:
        logger.info(f"Using SQLite database: {db.db_path}")
        # Запускаем периодические бэкапы для SQLite (только если не PostgreSQL)
        from utils.backup import periodic_backup
        backup_task = asyncio.create_task(periodic_backup(db.db_path))
        logger.info(f"SQLite backup system started (every {config.database.backup_interval_hours} hours)")
        logger.info(f"Backups will be saved to: {config.database.backup_dir}")

    bot = Bot(config.bot.token)
    dp = Dispatcher()

    logger.bind(bot_id=bot.id).info("Bot instance created")

    dp.include_router(menu_router)
    dp.include_router(feedback_router)
    dp.include_router(admin_router)
    
    try:
        logger.info("Starting bot polling")
        await dp.start_polling(bot)
    except Exception as e:
        logger.error("Bot polling failed: {}", str(e))
        raise
    finally:
        logger.info("Bot shutting down")


if __name__ == "__main__":
    asyncio.run(main())