# 📦 Руководство по бэкапам базы данных

## ⚠️ Важно: Бэкапы работают ТОЛЬКО для SQLite!

**PostgreSQL на Railway автоматически делает бэкапы**, поэтому для PostgreSQL дополнительная система бэкапов не нужна.

Бэкапы создаются **только для SQLite** (локальная разработка).

---

## 📍 Где находятся бэкапы?

По умолчанию бэкапы сохраняются в папку **`backups/`** в корне проекта.

### Просмотр бэкапов в PowerShell:

```powershell
# Показать все бэкапы с датой и размером
Get-ChildItem backups -Filter "*.db" | Sort-Object LastWriteTime -Descending | Format-Table Name, @{Label="Size (KB)"; Expression={[math]::Round($_.Length/1KB, 2)}}, LastWriteTime -AutoSize

# Показать только имена файлов
Get-ChildItem backups -Filter "*.db" | Select-Object Name

# Показать последний бэкап
Get-ChildItem backups -Filter "*.db" | Sort-Object LastWriteTime -Descending | Select-Object -First 1
```

### Просмотр бэкапов в командной строке (CMD):

```cmd
dir backups\*.db /O-D
```

---

## ⚙️ Настройка пути для бэкапов

### Способ 1: Через переменные окружения (.env)

Добавьте в файл `.env`:

```env
# Путь к директории для бэкапов (по умолчанию: backups)
BACKUP_DIR=my_backups

# Интервал между бэкапами в часах (по умолчанию: 24)
BACKUP_INTERVAL_HOURS=12

# Количество бэкапов для хранения (по умолчанию: 10)
BACKUP_KEEP_COUNT=20
```

### Способ 2: Через код (config.py)

Измените значения по умолчанию в `config.py`:

```python
@dataclass
class DatabaseConfig:
    backup_dir: str = "my_custom_backups"  # Ваша папка
    backup_interval_hours: int = 12  # Каждые 12 часов
    backup_keep_count: int = 20  # Хранить 20 бэкапов
```

---

## 🔄 Как работают бэкапы?

1. **Автоматическое создание**: Бэкапы создаются автоматически каждые 24 часа (или по настройке)
2. **Именование**: `database_backup_YYYYMMDD_HHMMSS.db`
   - Пример: `database_backup_20250115_143022.db`
3. **Очистка старых**: Автоматически удаляются старые бэкапы, оставляются только последние 10 (или по настройке)
4. **Только для SQLite**: Бэкапы создаются только если используется SQLite, не для PostgreSQL

---

## 🛠️ Ручное создание бэкапа

Если нужно создать бэкап вручную (например, перед важным изменением):

### Через Python:

```python
from utils.backup import backup_sqlite_database
import asyncio

# Создать бэкап
backup_path = asyncio.run(backup_sqlite_database("database/database.db"))
print(f"Бэкап создан: {backup_path}")
```

### Через PowerShell (простое копирование):

```powershell
# Создать папку для бэкапа
New-Item -ItemType Directory -Force -Path backups

# Скопировать базу данных
$timestamp = Get-Date -Format "yyyyMMdd_HHmmss"
Copy-Item "database\database.db" "backups\database_backup_$timestamp.db"
```

---

## 📥 Восстановление из бэкапа

### Способ 1: Простое копирование

```powershell
# Остановите бота
# Скопируйте бэкап обратно
Copy-Item "backups\database_backup_20250115_143022.db" "database\database.db" -Force

# Запустите бота снова
```

### Способ 2: Через Python скрипт

Создайте файл `restore_backup.py`:

```python
import shutil
import sys

backup_file = sys.argv[1] if len(sys.argv) > 1 else None
if not backup_file:
    print("Использование: python restore_backup.py backups/database_backup_YYYYMMDD_HHMMSS.db")
    sys.exit(1)

target = "database/database.db"
shutil.copy2(backup_file, target)
print(f"База данных восстановлена из {backup_file}")
```

Использование:
```powershell
python restore_backup.py backups\database_backup_20250115_143022.db
```

---

## 📊 Проверка размера бэкапов

```powershell
# Размер всех бэкапов
$totalSize = (Get-ChildItem backups -Filter "*.db" | Measure-Object -Property Length -Sum).Sum
Write-Host "Общий размер бэкапов: $([math]::Round($totalSize/1MB, 2)) MB"

# Размер каждого бэкапа
Get-ChildItem backups -Filter "*.db" | ForEach-Object {
    Write-Host "$($_.Name): $([math]::Round($_.Length/1KB, 2)) KB"
}
```

---

## 🗑️ Удаление старых бэкапов вручную

```powershell
# Удалить все бэкапы старше 30 дней
Get-ChildItem backups -Filter "*.db" | Where-Object {
    $_.LastWriteTime -lt (Get-Date).AddDays(-30)
} | Remove-Item

# Удалить все бэкапы кроме последних 5
Get-ChildItem backups -Filter "*.db" | Sort-Object LastWriteTime -Descending | Select-Object -Skip 5 | Remove-Item
```

---

## ❓ Частые вопросы

### Q: Почему бэкапы не создаются?

**A:** Проверьте:
1. Используется ли SQLite (не PostgreSQL)?
2. Существует ли файл `database/database.db`?
3. Есть ли права на запись в папку `backups/`?
4. Проверьте логи бота на ошибки

### Q: Можно ли изменить формат имени файла?

**A:** Да, измените функцию `backup_sqlite_database` в `utils/backup.py`:

```python
timestamp = datetime.now().strftime("ваш_формат")
```

### Q: Бэкапы создаются на Railway?

**A:** Нет! На Railway используйте PostgreSQL — Railway автоматически делает бэкапы для PostgreSQL. SQLite на Railway теряется при перезапуске.

### Q: Как часто создаются бэкапы?

**A:** По умолчанию каждые 24 часа. Измените через `BACKUP_INTERVAL_HOURS` в `.env`.

---

## 📝 Примеры конфигурации

### Для разработки (частые бэкапы):

```env
BACKUP_DIR=dev_backups
BACKUP_INTERVAL_HOURS=1
BACKUP_KEEP_COUNT=50
```

### Для продакшена (редкие бэкапы):

```env
BACKUP_DIR=prod_backups
BACKUP_INTERVAL_HOURS=168  # Раз в неделю
BACKUP_KEEP_COUNT=4  # Хранить 4 недели
```

### Для тестирования (очень частые):

```env
BACKUP_DIR=test_backups
BACKUP_INTERVAL_HOURS=0.5  # Каждые 30 минут
BACKUP_KEEP_COUNT=100
```


