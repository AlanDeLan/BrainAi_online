# Local Gemini Brain - Инструкция для Windows 11

## Быстрый запуск

### Автоматический запуск (рекомендуется)

Просто выполните:
```powershell
.\start_server.ps1
```

Скрипт автоматически:
- ✅ Проверит наличие Python
- ✅ Создаст виртуальное окружение `.venv` (если его нет)
- ✅ Активирует виртуальное окружение
- ✅ Установит все зависимости из `requirements.txt`
- ✅ Проверит наличие файла `.env` и переменной `GOOGLE_API_KEY`
- ✅ Проверит занятость порта 8000
- ✅ Запустит сервер

### Ручной запуск

1. **Создание виртуального окружения:**
   ```powershell
   python -m venv .venv
   ```

2. **Активация виртуального окружения:**
   ```powershell
   .\.venv\Scripts\Activate.ps1
   ```

3. **Установка зависимостей:**
   ```powershell
   pip install -r requirements.txt
   ```

4. **Создание файла `.env`:**
   Создайте файл `.env` в корне проекта со следующим содержимым:
   ```
   GOOGLE_API_KEY=your_api_key_here
   ```

5. **Запуск сервера:**
   ```powershell
   uvicorn main:app --host 127.0.0.1 --port 8000 --reload
   ```

## Параметры скрипта запуска

```powershell
# Пропустить проверку .env файла
.\start_server.ps1 -SkipEnvCheck

# Пропустить установку зависимостей
.\start_server.ps1 -SkipDeps

# Комбинация параметров
.\start_server.ps1 -SkipEnvCheck -SkipDeps
```

## Доступ к серверу

После запуска сервер будет доступен по адресу:
- **Главная страница:** http://127.0.0.1:8000
- **Документация API:** http://127.0.0.1:8000/docs
- **Альтернативная документация:** http://127.0.0.1:8000/redoc

## Остановка сервера

Нажмите `Ctrl+C` в терминале, где запущен сервер.

## Удаление виртуального окружения

Если нужно удалить существующее виртуальное окружение:

```powershell
# Сначала деактивируйте (если активно)
deactivate

# Затем удалите папку
Remove-Item -Recurse -Force .venv
```

Или одной командой (без деактивации):
```powershell
Remove-Item -Recurse -Force .venv
```

**Примечание:** Если окружение называется иначе (например, `venv`):
```powershell
Remove-Item -Recurse -Force venv
```

## Отображение кирилицы в консоли

Если кирилица отображается как кракозябры в PowerShell:

**Временное решение (для текущей сессии):**
```powershell
[Console]::OutputEncoding = [System.Text.Encoding]::UTF8
[Console]::InputEncoding = [System.Text.Encoding]::UTF8
chcp 65001
```

Или запустите скрипт:
```powershell
.\setup_encoding.ps1
```

**Постоянное решение:**
Добавьте настройки в PowerShell профиль:
```powershell
# Відкрийте профіль
notepad $PROFILE

# Додайте ці рядки:
[Console]::OutputEncoding = [System.Text.Encoding]::UTF8
[Console]::InputEncoding = [System.Text.Encoding]::UTF8
chcp 65001 | Out-Null
```

**Автоматическое настройка:**
Скрипт `start_server.ps1` автоматически устанавливает UTF-8 при запуске.

## Решение проблем

### Ошибка выполнения скриптов PowerShell

Если появляется ошибка о политике выполнения:
```powershell
Set-ExecutionPolicy -ExecutionPolicy RemoteSigned -Scope CurrentUser
```

### Порт 8000 занят

Если порт 8000 уже занят другим процессом:
1. Найдите процесс: `Get-NetTCPConnection -LocalPort 8000`
2. Остановите процесс или используйте другой порт: `uvicorn main:app --port 8080`

### Проблемы с активацией виртуального окружения

Если активация не работает:
```powershell
# Проверьте наличие файла
Test-Path .\.venv\Scripts\Activate.ps1

# Альтернативный способ активации
& .\.venv\Scripts\python.exe
```

## Структура проекта

```
local_gemini/
├── .venv/              # Виртуальное окружение (создается автоматически)
├── .env                # Файл с переменными окружения (создайте вручную)
├── history/            # История чатов (создается автоматически)
├── prompts/            # Файлы с промптами архетипов (новое!)
│   ├── sofiya_base.txt
│   ├── sofiya_context_instructions.txt
│   └── ...
├── main.py             # Главный файл FastAPI приложения
├── run_app.py          # Альтернативный скрипт запуска (кроссплатформенный)
├── start_server.ps1    # PowerShell скрипт для Windows
├── requirements.txt    # Зависимости Python
├── archetypes.yaml     # Конфигурация архетипов
├── core/               # Основная логика
├── conferences/        # Роуты для конференций
├── static/             # Статические файлы (CSS, JS)
└── templates/          # HTML шаблоны
```

## Настройка промптов архетипов

Промпти архетипів можна:
- ✅ Виносити в окремі файли для зручного редагування
- ✅ Створювати багатоступінчасті промпти (основний + додаткові)
- ✅ Комбінувати файли та текст

**Детальна інструкція:** `prompts/PROMPTS_GUIDE.md`

## Системные требования

- **Windows 11** (или Windows 10)
- **Python 3.8+** (рекомендуется 3.11+)
- **PowerShell 5.1+** (встроен в Windows)
- **Интернет-соединение** (для работы с Gemini API)

## Зависимости

Все зависимости автоматически устанавливаются из `requirements.txt`:
- FastAPI - веб-фреймворк
- Uvicorn - ASGI сервер
- Pydantic - валидация данных
- Google Generative AI - API для Gemini
- ChromaDB - векторная база данных
- И другие...

## Поддержка

При возникновении проблем проверьте:
1. Правильность установки Python
2. Наличие файла `.env` с корректным `GOOGLE_API_KEY`
3. Логи в консоли при запуске сервера
4. Занятость порта 8000


