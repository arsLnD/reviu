# Инструкция по деплою на GitHub и Railway

## 🔴 Проблема: Ошибка 403 при push

Если вы видите ошибку:
```
remote: Permission to luhverchikv/MIPBot.git denied to arsLnD.
fatal: unable to access 'https://github.com/...': The requested URL returned error: 403
```

Это означает, что у вас нет прав на репозиторий `luhverchikv/MIPBot`.

## ✅ Решение 1: Создать свой репозиторий (рекомендуется)

### Шаг 1: Создайте новый репозиторий на GitHub

1. Зайдите на [github.com](https://github.com)
2. Нажмите **"+"** → **"New repository"**
3. Заполните:
   - **Repository name**: `telegram-review-bot` (или любое другое имя)
   - **Description**: "Telegram bot for collecting reviews"
   - **Visibility**: Public или Private (на ваше усмотрение)
   - **НЕ** ставьте галочки на "Add README", "Add .gitignore", "Choose a license"
4. Нажмите **"Create repository"**

### Шаг 2: Измените remote URL

В PowerShell выполните:

```powershell
# Удалите старый remote
git remote remove origin

# Добавьте новый remote (замените YOUR_USERNAME на ваш GitHub username)
git remote add origin https://github.com/YOUR_USERNAME/telegram-review-bot.git

# Проверьте
git remote -v
```

### Шаг 3: Настройте аутентификацию

#### Вариант A: Personal Access Token (проще)

1. Зайдите на GitHub → **Settings** → **Developer settings** → **Personal access tokens** → **Tokens (classic)**
2. Нажмите **"Generate new token (classic)"**
3. Заполните:
   - **Note**: "Telegram Bot Project"
   - **Expiration**: 90 days (или No expiration)
   - **Scopes**: отметьте `repo` (полный доступ к репозиториям)
4. Нажмите **"Generate token"**
5. **Скопируйте токен** (он показывается только один раз!)

6. При следующем `git push` используйте токен вместо пароля:
   ```
   Username: ваш_github_username
   Password: ваш_personal_access_token
   ```

#### Вариант B: SSH (безопаснее, но сложнее)

1. Создайте SSH ключ (если его нет):
   ```powershell
   ssh-keygen -t ed25519 -C "your_email@example.com"
   # Нажмите Enter для всех вопросов
   ```

2. Скопируйте публичный ключ:
   ```powershell
   cat ~/.ssh/id_ed25519.pub
   ```

3. Добавьте ключ на GitHub:
   - GitHub → **Settings** → **SSH and GPG keys** → **New SSH key**
   - Вставьте содержимое `id_ed25519.pub`
   - Нажмите **"Add SSH key"**

4. Измените remote на SSH:
   ```powershell
   git remote set-url origin git@github.com:YOUR_USERNAME/telegram-review-bot.git
   ```

### Шаг 4: Запушьте код

```powershell
# Добавьте все файлы
git add .

# Сделайте коммит
git commit -m "Initial commit: Telegram review bot with PostgreSQL support"

# Запушьте в GitHub
git push -u origin main
```

Если попросит пароль/токен - используйте Personal Access Token из шага 3.

## ✅ Решение 2: Получить права на существующий репозиторий

Если репозиторий `luhverchikv/MIPBot` принадлежит вам или вы хотите работать с ним:

1. Попросите владельца (`luhverchikv`) добавить вас как collaborator:
   - Репозиторий → **Settings** → **Collaborators** → **Add people**
   - Введите ваш GitHub username

2. Или сделайте Fork репозитория:
   - На странице репозитория нажмите **"Fork"**
   - Это создаст копию репозитория в вашем аккаунте

## 🔧 Настройка Git для Windows (исправление LF/CRLF)

Чтобы убрать предупреждение о LF/CRLF:

```powershell
# Автоматическая конвертация окончаний строк
git config --global core.autocrlf true

# Или для этого проекта только
git config core.autocrlf true
```

## 📦 Деплой на Railway

После успешного push в GitHub:

1. Зайдите на [railway.app](https://railway.app/)
2. **New Project** → **Deploy from GitHub repo**
3. Выберите ваш репозиторий
4. Добавьте PostgreSQL: **"+ New"** → **"Database"** → **"Add PostgreSQL"**
5. Добавьте переменные окружения:
   - `BOT_TOKEN`
   - `OWNER_ID`
   - `ADMIN_IDS`
   - `DATABASE_URL` (создается автоматически)
6. Нажмите **Deploy**

Готово! 🎉


