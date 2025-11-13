# 🚀 BrainAi Production Deployment Guide

## 📋 Зміст

1. [Підготовка проекту](#підготовка-проекту)
2. [Налаштування GitHub](#налаштування-github)
3. [Розгортання на Render](#розгортання-на-render)
4. [Налаштування безпеки](#налаштування-безпеки)
5. [Моніторинг та обслуговування](#моніторинг-та-обслуговування)

---

## ⚠️ КРИТИЧНО: Безпека перед деплоєм

### 1. Видаліть .env з Git історії (ОБОВ'ЯЗКОВО!)

```powershell
# ⚠️ ВАЖЛИВО: Ваш .env містить реальні API ключі!
# Виконайте ці команди ПЕРЕД першим commit:

# Видалити .env з індексу Git (але залишити локально)
git rm --cached .env

# Перевірити, що .env в .gitignore
cat .gitignore | Select-String ".env"

# Якщо .env вже був закомічений раніше, очистіть історію:
git filter-branch --force --index-filter "git rm --cached --ignore-unmatch .env" --prune-empty --tag-name-filter cat -- --all

# Форсований push (УВАГА: це перезапише історію)
git push origin --force --all
```

### 2. Створіть .env з шаблону

```powershell
# Скопіюйте шаблон
Copy-Item .env.example .env

# Відредагуйте .env і додайте РЕАЛЬНІ ключі
notepad .env
```

---

## 1️⃣ Підготовка проекту

### Крок 1: Перевірте файли

Переконайтеся, що у вас є:

```
✅ render.yaml
✅ .env.example (БЕЗ реальних ключів!)
✅ .gitignore (з .env в списку)
✅ requirements.txt (оновлений)
✅ gunicorn_config.py
✅ core/settings.py
✅ core/auth.py
✅ core/rate_limit.py
✅ core/database.py
```

### Крок 2: Тестування локально

```powershell
# Створіть віртуальне середовище
python -m venv venv
.\venv\Scripts\Activate.ps1

# Встановіть залежності
pip install -r requirements.txt

# Запустіть локально
$env:DATABASE_URL="sqlite:///./test.db"
$env:SECRET_KEY="test-secret-key"
$env:ADMIN_PASSWORD="admin123"
uvicorn main:app --reload

# Перевірте в браузері: http://localhost:8000
# Swagger docs: http://localhost:8000/docs
```

---

## 2️⃣ Налаштування GitHub

### Крок 1: Створіть репозиторій

```powershell
# Ініціалізуйте Git
git init
git add .
git commit -m "Initial commit: Production-ready BrainAi"

# Створіть репозиторій на GitHub (через веб-інтерфейс)
# Потім:
git remote add origin https://github.com/YOUR_USERNAME/brainai-production.git
git branch -M main
git push -u origin main
```

### Крок 2: Перевірте, що .env НЕ в репозиторії

```powershell
# Перевірте файли в Git
git ls-files | Select-String ".env"

# Якщо .env з'явився - НЕГАЙНО видаліть:
git rm --cached .env
git commit -m "Remove .env from tracking"
git push
```

---

## 3️⃣ Розгортання на Render

### Крок 1: Реєстрація на Render

1. Перейдіть на https://render.com
2. Зареєструйтеся (можна через GitHub)
3. Підтвердіть email

### Крок 2: Підключіть GitHub репозиторій

1. В Render Dashboard натисніть **"New +"**
2. Виберіть **"Blueprint"**
3. Підключіть GitHub акаунт (дозвольте доступ)
4. Виберіть репозиторій `brainai-production`
5. Натисніть **"Apply"**

Render автоматично:
- Створить Web Service
- Створить PostgreSQL Database
- Підключить DATABASE_URL

### Крок 3: Додайте Environment Variables

**ВАЖЛИВО**: Додайте ці змінні ВРУЧНУ в Render Dashboard:

1. Перейдіть в **Dashboard → brainai-production → Environment**
2. Додайте змінні:

```bash
# === ОБОВ'ЯЗКОВІ ===
SECRET_KEY=<згенеруйте випадковий ключ>
SESSION_SECRET=<згенеруйте випадковий ключ>
ADMIN_PASSWORD=<створіть надійний пароль>

# === AI API КЛЮЧІ ===
GOOGLE_API_KEY=<ваш Google AI ключ>
# АБО
OPENAI_API_KEY=<ваш OpenAI ключ>

# === НАЛАШТУВАННЯ ===
AI_PROVIDER=google_ai
ENVIRONMENT=production
DEBUG=false
```

**Як згенерувати SECRET_KEY**:

```powershell
# В PowerShell:
-join ((65..90) + (97..122) + (48..57) | Get-Random -Count 32 | % {[char]$_})
```

### Крок 4: Налаштуйте Custom Domain (опціонально)

1. В Dashboard → Settings → Custom Domain
2. Додайте ваш домен
3. Налаштуйте DNS записи (Render покаже інструкції)

---

## 4️⃣ Налаштування безпеки

### 1. CORS (Cross-Origin Resource Sharing)

```powershell
# В Render Environment Variables додайте:
CORS_ORIGINS=["https://yourdomain.com","https://brainai-production.onrender.com"]
```

### 2. Rate Limiting

Вже налаштовано в коді:
- 60 запитів на хвилину
- 1000 запитів на годину

Змініть в Environment Variables:
```
RATE_LIMIT_PER_MINUTE=60
RATE_LIMIT_PER_HOUR=1000
```

### 3. Автентифікація

**Перший вхід**:

```bash
# POST /api/auth/login
{
  "username": "admin",
  "password": "<ваш ADMIN_PASSWORD>"
}

# Отримаєте токен:
{
  "access_token": "eyJ...",
  "token_type": "bearer"
}
```

**Використання токена**:

```bash
# Додайте в headers:
Authorization: Bearer eyJ...
```

### 4. Змініть пароль адміна

```bash
# В Render Dashboard → Environment
ADMIN_PASSWORD=<новий_надійний_пароль>

# Restart service
```

---

## 5️⃣ Моніторинг та обслуговування

### Health Check

```bash
# GET /health
{
  "status": "healthy",
  "version": "1.0.0",
  "environment": "production",
  "timestamp": "2025-11-13T10:30:00Z",
  "checks": {
    "database": true,
    "vector_db": true
  }
}
```

### Логи

```powershell
# В Render Dashboard → Logs
# Показує всі логи в реальному часі
```

### Metrics

```bash
# GET /api/metrics (потрібна автентифікація)
{
  "requests_total": 12345,
  "errors_total": 12,
  "cache_hits": 800,
  "cache_misses": 200
}
```

### Backup Database

```powershell
# В Render Dashboard → brainai-db
# Manual Backup → Create Backup
# Download backup
```

---

## 🔧 Troubleshooting

### Проблема: "Database connection failed"

**Рішення**:
1. Перевірте, що DATABASE_URL встановлено
2. В Render Dashboard → brainai-db → перевірте статус
3. Restart service

### Проблема: "AI API key not found"

**Рішення**:
```powershell
# Перевірте Environment Variables:
# 1. GOOGLE_API_KEY або OPENAI_API_KEY встановлено
# 2. AI_PROVIDER = google_ai або openai
# 3. Restart service
```

### Проблема: "Rate limit exceeded"

**Рішення**:
```powershell
# Збільште ліміти в Environment Variables:
RATE_LIMIT_PER_MINUTE=120
RATE_LIMIT_PER_HOUR=2000
```

---

## 📊 Вартість

### Free Tier (90 днів):
- Web Service: Free
- PostgreSQL: Free (обмеження: 1GB storage)

### Paid Plans:
- Web Service (Starter): **$7/міс**
- PostgreSQL (Starter): **$7/міс**
- **Загалом: $14/міс**

---

## 🚀 Наступні кроки

### 1. Налаштуйте CI/CD

Додамо автоматичний деплой при push в GitHub (файл створимо окремо).

### 2. Додайте моніторинг

Інтеграція з Sentry для відстеження помилок.

### 3. Оптимізація

- Додайте Redis для кешування
- Налаштуйте CDN для статичних файлів

---

## 📞 Підтримка

Якщо виникли питання:
1. Перевірте логи в Render Dashboard
2. Перегляньте документацію: https://render.com/docs
3. GitHub Issues: створіть issue в репозиторії

---

## ✅ Чеклист готовності до продакшн

- [ ] .env видалено з Git
- [ ] API ключі в Environment Variables
- [ ] SECRET_KEY згенеровано
- [ ] ADMIN_PASSWORD змінено
- [ ] CORS налаштовано
- [ ] Database backup налаштовано
- [ ] Health check працює
- [ ] Логування працює
- [ ] Автентифікація працює
- [ ] Rate limiting активний

**Готово до запуску! 🎉**
