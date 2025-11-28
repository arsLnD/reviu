"""
Система автоматических бэкапов SQLite базы данных.
Для PostgreSQL бэкапы не требуются, так как Railway автоматически делает их.
"""
import os
import shutil
import asyncio
from datetime import datetime
from pathlib import Path
from loguru import logger


async def backup_sqlite_database(db_path: str, backup_dir: str = "backups") -> str | None:
    """
    Создает бэкап SQLite базы данных.
    
    Args:
        db_path: Путь к файлу базы данных
        backup_dir: Директория для хранения бэкапов
        
    Returns:
        Путь к созданному бэкапу или None в случае ошибки
    """
    if not os.path.exists(db_path):
        logger.warning(f"База данных не найдена: {db_path}")
        return None
    
    # Создаем директорию для бэкапов
    os.makedirs(backup_dir, exist_ok=True)
    
    # Формируем имя файла бэкапа с датой и временем
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    backup_filename = f"database_backup_{timestamp}.db"
    backup_path = os.path.join(backup_dir, backup_filename)
    
    try:
        # Копируем файл базы данных
        shutil.copy2(db_path, backup_path)
        logger.info(f"Бэкап создан: {backup_path}")
        
        # Удаляем старые бэкапы (оставляем только последние 10)
        cleanup_old_backups(backup_dir, keep_count=10)
        
        return backup_path
    except Exception as e:
        logger.error(f"Ошибка при создании бэкапа: {e}")
        return None


def cleanup_old_backups(backup_dir: str, keep_count: int = 10) -> None:
    """
    Удаляет старые бэкапы, оставляя только последние N файлов.
    
    Args:
        backup_dir: Директория с бэкапами
        keep_count: Количество бэкапов для сохранения
    """
    try:
        backup_files = []
        for filename in os.listdir(backup_dir):
            if filename.startswith("database_backup_") and filename.endswith(".db"):
                filepath = os.path.join(backup_dir, filename)
                backup_files.append((os.path.getmtime(filepath), filepath))
        
        # Сортируем по времени модификации (новые первыми)
        backup_files.sort(reverse=True)
        
        # Удаляем старые бэкапы
        if len(backup_files) > keep_count:
            for _, filepath in backup_files[keep_count:]:
                try:
                    os.remove(filepath)
                    logger.info(f"Удален старый бэкап: {filepath}")
                except Exception as e:
                    logger.error(f"Ошибка при удалении бэкапа {filepath}: {e}")
    except Exception as e:
        logger.error(f"Ошибка при очистке старых бэкапов: {e}")


async def periodic_backup(db_path: str, interval_hours: int = 24) -> None:
    """
    Периодическое создание бэкапов.
    
    Args:
        db_path: Путь к файлу базы данных
        interval_hours: Интервал между бэкапами в часах
    """
    while True:
        try:
            await asyncio.sleep(interval_hours * 3600)  # Конвертируем часы в секунды
            await backup_sqlite_database(db_path)
        except Exception as e:
            logger.error(f"Ошибка в периодическом бэкапе: {e}")
            await asyncio.sleep(3600)  # Ждем час перед повтором при ошибке

