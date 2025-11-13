# 📋 Швидкий старт для розгортання на Render

## ⚠️ КРИТИЧНО: Перед початком

### 1. Видаліть .env з Git (якщо він там є)

```powershell
# Перевірте, чи .env в Git
git ls-files | Select-String ".env"

# Якщо знайдено - НЕГАЙНО видаліть:
git rm --cached .env
git commit -m "Remove .env from Git tracking"

# Якщо .env був у попередніх комітах:
git filter-branch --force --index-filter "git rm --cached --ignore-unmatch .env" --prune-empty --tag-name-filter cat -- --all
git push origin --force --all
```

---

## 🚀 Крок 1: Локальне тестування

```powershell
# Створіть віртуальне середовище
python -m venv venv
.\venv\Scripts\Activate.ps1

# Встановіть залежності
pip install -r requirements.txt

# Створіть .env з .env.example
Copy-Item .env.example .env

# Відредагуйте .env і додайте РЕАЛЬНІ ключі
notepad .env

# Запустіть локально
python main_production.py

# Відкрийте: http://localhost:8000
# API Docs: http://localhost:8000/docs
```

---

## 📦 Крок 2: Створіть GitHub репозиторій

```powershell
# Ініціалізуйте Git
git init
git add .
git commit -m "feat: Production-ready BrainAi with security"

# Створіть репозиторій на GitHub (через браузер)
# Потім:
git remote add origin https://github.com/YOUR_USERNAME/brainai-production.git
git branch -M main
git push -u origin main
```

---

## ☁️ Крок 3: Розгортання на Render

### A. Через Blueprint (Автоматично)

1. **Перейдіть на** https://render.com
2. **Натисніть** "New +" → "Blueprint"
3. **Підключіть** GitHub репозиторій
4. **Виберіть** `brainai-production`
5. **Натисніть** "Apply"

Render автоматично створить:
- ✅ Web Service (Python)
- ✅ PostgreSQL Database
- ✅ З'єднання між ними

### B. Вручну (якщо Blueprint не спрацював)

#### Створіть PostgreSQL:
1. "New +" → "PostgreSQL"
2. Name: `brainai-db`
3. Database: `brainai`
4. Region: Frankfurt
5. Plan: Free або Starter ($7/міс)
6. Create Database

#### Створіть Web Service:
1. "New +" → "Web Service"
2. Connect GitHub → `brainai-production`
3. Settings:
   - **Name**: `brainai-production`
   - **Region**: Frankfurt
   - **Branch**: main
   - **Runtime**: Python 3
   - **Build Command**: `pip install -r requirements.txt`
   - **Start Command**: `uvicorn main_production:app --host 0.0.0.0 --port $PORT --workers 2`
4. Create Web Service

---

## 🔑 Крок 4: Налаштуйте Environment Variables

В Render Dashboard → **brainai-production** → **Environment**:

### Згенеруйте секретні ключі:

```powershell
# SECRET_KEY (32 символи)
-join ((65..90) + (97..122) + (48..57) | Get-Random -Count 32 | % {[char]$_})

# SESSION_SECRET (32 символи)
-join ((65..90) + (97..122) + (48..57) | Get-Random -Count 32 | % {[char]$_})
```

### Додайте змінні:

| Key | Value | Примітка |
|-----|-------|----------|
| `DATABASE_URL` | (автоматично з БД) | Не змінюйте |
| `SECRET_KEY` | `<згенерований ключ>` | Для JWT |
| `SESSION_SECRET` | `<згенерований ключ>` | Для сесій |
| `ADMIN_PASSWORD` | `<ваш пароль>` | Мінімум 8 символів |
| `GOOGLE_API_KEY` | `AIza...` | З Google AI Studio |
| `OPENAI_API_KEY` | `sk-proj-...` | Опціонально |
| `AI_PROVIDER` | `google_ai` | Або `openai` |
| `ENVIRONMENT` | `production` | Обов'язково |
| `DEBUG` | `false` | Обов'язково |
| `CORS_ORIGINS` | `["https://your-app.onrender.com"]` | Ваш домен |

---

## ✅ Крок 5: Перевірка

### A. Перевірте деплой

```powershell
# Дочекайтеся завершення деплою (3-5 хвилин)
# В Logs побачите:
# ✅ Application started successfully!
```

### B. Тестування endpoints

```powershell
# Health Check
curl https://brainai-production.onrender.com/health

# Очікується:
# {
#   "status": "healthy",
#   "version": "1.0.0",
#   "environment": "production",
#   "checks": {
#     "database": true,
#     "ai_provider": true,
#     "vector_db": true
#   }
# }
```

### C. Логін та отримання токена

```powershell
# POST /api/auth/login
curl -X POST https://brainai-production.onrender.com/api/auth/login `
  -H "Content-Type: application/json" `
  -d '{
    "username": "admin",
    "password": "your-admin-password"
  }'

# Очікується:
# {
#   "access_token": "eyJhbGciOiJIUzI1NiIs...",
#   "token_type": "bearer",
#   "expires_in": 86400
# }
```

### D. Використання API

```powershell
# Додайте токен в headers
curl https://brainai-production.onrender.com/api/metrics `
  -H "Authorization: Bearer YOUR_TOKEN_HERE"
```

---

## 🔧 Крок 6: Налаштуйте CI/CD (опціонально)

### Додайте GitHub Secrets:

1. **GitHub** → Ваш репозиторій → Settings → Secrets and variables → Actions
2. **Додайте секрети**:

| Name | Value | Де взяти |
|------|-------|----------|
| `RENDER_API_KEY` | `rnd_...` | Render → Account Settings → API Keys |
| `RENDER_SERVICE_ID` | `srv-...` | Render → brainai-production → Settings (в URL) |
| `RENDER_URL` | `https://brainai-production.onrender.com` | URL вашого сервісу |
| `GOOGLE_API_KEY` | `AIza...` | Для тестів |

Тепер при кожному push в `main`:
- ✅ Запустяться тести
- ✅ Перевірка безпеки
- ✅ Автоматичний деплой
- ✅ Health check

---

## 📊 Моніторинг

### Логи в реальному часі:
```
Render Dashboard → brainai-production → Logs
```

### Metrics:
```
GET /api/metrics
Authorization: Bearer YOUR_TOKEN
```

### Database Backup:
```
Render Dashboard → brainai-db → Manual Backup
```

---

## 💰 Вартість

### Free Tier (90 днів):
- Web Service: **Free**
- PostgreSQL: **Free** (1GB)

### Після 90 днів:
- Web Service (Starter): **$7/міс**
- PostgreSQL (Starter): **$7/міс**
- **Загалом: $14/міс**

---

## 🆘 Troubleshooting

### "Database connection failed"
```powershell
# Перевірте:
1. DATABASE_URL встановлено
2. БД створено і активна
3. Restart service
```

### "AI API key not found"
```powershell
# Перевірте Environment Variables:
GOOGLE_API_KEY або OPENAI_API_KEY
AI_PROVIDER = google_ai або openai
```

### "Unauthorized" при запитах
```powershell
# Отримайте новий токен:
POST /api/auth/login

# Додайте в headers:
Authorization: Bearer <токен>
```

---

## ✅ Готово!

Ваш AI-асистент розгорнуто на Render з:

✅ JWT автентифікацією
✅ Rate limiting (захист від DDoS)
✅ PostgreSQL базою даних
✅ CORS налаштуванням
✅ Автоматичними деплоями
✅ Моніторингом та логами

🎉 **Вітаємо з успішним розгортанням!**

---

## 📖 Детальна документація

Повна інструкція: [RENDER_DEPLOYMENT.md](./RENDER_DEPLOYMENT.md)
