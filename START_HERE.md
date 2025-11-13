# 🎯 ЩО ВАМ ПОТРІБНО ЗРОБИТИ ЗАРАЗ

## ⚠️ ТЕРМІНОВО! Крок 0: Безпека API ключів

### 🔴 КРИТИЧНО: Ваш .env містить РЕАЛЬНІ API ключі!

Виконайте ЦІ КОМАНДИ ЗАРАЗ:

```powershell
# 1. Перевірте, чи .env вже в Git
cd "c:\Users\alan\OneDrive\IT_project\GitHub\BrainAi_local"
git ls-files | Select-String ".env"

# 2. Якщо .env знайдено - ВИДАЛІТЬ з індексу:
git rm --cached .env

# 3. Закомітьте видалення:
git add .gitignore
git commit -m "security: Remove .env from Git tracking"

# 4. Якщо .env був у попередніх комітах - очистіть історію:
# ⚠️ УВАГА: Це перезапише Git історію!
git filter-branch --force --index-filter "git rm --cached --ignore-unmatch .env" --prune-empty --tag-name-filter cat -- --all

# 5. Після очищення історії:
git push origin --force --all
```

**ВАЖЛИВО**: Після цього вам потрібно:
1. Видалити старі API ключі на Google AI Studio / OpenAI
2. Створити НОВІ ключі
3. Додати їх в Render Environment Variables (НЕ в .env!)

---

## 📋 Крок 1: Підготовка локально

### A. Створіть новий .env з шаблону

```powershell
# У PowerShell:
cd "c:\Users\alan\OneDrive\IT_project\GitHub\BrainAi_local"

# Видаліть старий .env (НЕБЕЗПЕЧНИЙ!)
Remove-Item .env -Force

# Створіть новий з шаблону
Copy-Item .env.example .env

# Відкрийте для редагування
notepad .env
```

### B. Згенеруйте нові секретні ключі

```powershell
# SECRET_KEY (скопіюйте результат):
Write-Host "SECRET_KEY=" -NoNewline
-join ((65..90) + (97..122) + (48..57) | Get-Random -Count 32 | % {[char]$_})

# SESSION_SECRET (скопіюйте результат):
Write-Host "SESSION_SECRET=" -NoNewline
-join ((65..90) + (97..122) + (48..57) | Get-Random -Count 32 | % {[char]$_})
```

**Додайте ці ключі в .env файл**

### C. Отримайте НОВІ AI API ключі

#### Google AI Studio (рекомендовано):
1. Перейдіть: https://makersuite.google.com/app/apikey
2. **ВИДАЛІТЬ старий ключ** (який був в Git)
3. Натисніть "Create API Key"
4. Скопіюйте ключ
5. Додайте в .env: `GOOGLE_API_KEY=AIza...`

#### OpenAI (опціонально):
1. Перейдіть: https://platform.openai.com/api-keys
2. **Revoke** старий ключ (який був в Git)
3. "Create new secret key"
4. Скопіюйте ключ
5. Додайте в .env: `OPENAI_API_KEY=sk-proj-...`

### D. Встановіть залежності

```powershell
# Створіть віртуальне середовище
python -m venv venv

# Активуйте
.\venv\Scripts\Activate.ps1

# Встановіть залежності
pip install -r requirements.txt
```

### E. Локальне тестування

```powershell
# Запустіть сервер
python main_production.py

# Має з'явитися:
# ====================================
# 🚀 Starting BrainAi in PRODUCTION mode
# ====================================
# ✅ Database initialized
# ✅ Admin user initialized
# ✅ Application started successfully!

# Відкрийте в браузері: http://localhost:8000
```

### F. Перевірте endpoints

```powershell
# Health check
curl http://localhost:8000/health

# Логін (отримайте токен)
curl -X POST http://localhost:8000/api/auth/login `
  -H "Content-Type: application/json" `
  -d '{\"username\": \"admin\", \"password\": \"your-password\"}'

# Скопіюйте access_token з відповіді
```

Якщо все працює - переходьте до Кроку 2!

---

## 📦 Крок 2: Git та GitHub

### A. Перевірте .gitignore

```powershell
# Переконайтеся, що .env в .gitignore:
Get-Content .gitignore | Select-String "^.env$"

# Має бути: .env
```

### B. Закомітьте зміни

```powershell
# Ініціалізуйте Git (якщо ще не зробили)
git init

# Додайте файли
git add .

# Перевірте, що .env НЕ додано:
git status | Select-String ".env"
# Не повинно бути .env у списку!

# Створіть commit
git commit -m "feat: Production-ready deployment with security"
```

### C. Створіть GitHub репозиторій

1. **Перейдіть на GitHub**: https://github.com/new
2. **Repository name**: `brainai-production` (або ваша назва)
3. **Visibility**: Private (рекомендовано для продакшн)
4. **НЕ** ставте галочку "Add README" (у вас вже є файли)
5. Натисніть **"Create repository"**

### D. Підключіть локальний репозиторій

```powershell
# Додайте remote (замініть YOUR_USERNAME):
git remote add origin https://github.com/YOUR_USERNAME/brainai-production.git

# Перейменуйте гілку на main
git branch -M main

# Запуште код
git push -u origin main
```

**ВАЖЛИВО**: GitHub попросить авторизацію:
- Використайте Personal Access Token (не пароль!)
- Створіть token: GitHub → Settings → Developer settings → Personal access tokens

---

## ☁️ Крок 3: Render Deployment

### A. Реєстрація на Render

1. Перейдіть: https://render.com
2. Натисніть **"Get Started for Free"**
3. Зареєструйтеся через GitHub (рекомендовано)
4. Підтвердіть email

### B. Підключіть GitHub

1. В Render Dashboard натисніть **"New +"**
2. Виберіть **"Blueprint"**
3. Натисніть **"Connect GitHub"**
4. Дозвольте доступ до репозиторіїв
5. Виберіть репозиторій `brainai-production`
6. Натисніть **"Apply"**

Render почне створення:
- ✅ Web Service (brainai-production)
- ✅ PostgreSQL Database (brainai-db)

**Зачекайте 2-3 хвилини**

### C. Налаштуйте Environment Variables

**КРИТИЧНО**: Додайте ці змінні ВРУЧНУ в Render!

1. Перейдіть: **Dashboard → brainai-production → Environment**
2. Натисніть **"Add Environment Variable"**
3. Додайте ПО ОДНІЙ змінній:

```bash
# 1. Секретні ключі (з кроку 1B)
SECRET_KEY=<ваш згенерований ключ>
SESSION_SECRET=<ваш згенерований ключ>

# 2. Admin credentials
ADMIN_USERNAME=admin
ADMIN_PASSWORD=<створіть надійний пароль>

# 3. AI API ключі (НОВІ з кроку 1C!)
GOOGLE_API_KEY=<ваш НОВИЙ Google AI ключ>
# АБО
OPENAI_API_KEY=<ваш НОВИЙ OpenAI ключ>

# 4. AI Provider
AI_PROVIDER=google_ai
# АБО
AI_PROVIDER=openai

# 5. Environment
ENVIRONMENT=production
DEBUG=false

# 6. CORS (додайте ваш домен після деплою)
CORS_ORIGINS=["https://brainai-production.onrender.com"]

# 7. Rate Limiting (опціонально)
RATE_LIMIT_PER_MINUTE=60
RATE_LIMIT_PER_HOUR=1000

# 8. JWT (опціонально)
JWT_ALGORITHM=HS256
JWT_EXPIRATION_HOURS=24

# 9. Logging
LOG_LEVEL=INFO
```

4. Натисніть **"Save Changes"**
5. Render автоматично перезапустить сервіс

### D. Дочекайтеся деплою

Перейдіть в **Logs** та слідкуйте за процесом:

```
[build] Installing dependencies...
[build] ✅ Build successful
[deploy] Starting server...
[deploy] ✅ Application started successfully!
```

**Це займе 5-10 хвилин при першому деплої**

---

## ✅ Крок 4: Перевірка

### A. Отримайте URL вашого сервісу

В Render Dashboard знайдіть URL:
```
https://brainai-production.onrender.com
```

### B. Перевірте Health Check

```powershell
# У PowerShell:
curl https://brainai-production.onrender.com/health

# Очікується:
# {
#   "status": "healthy",
#   "version": "1.0.0",
#   "environment": "production",
#   "checks": {
#     "database": true,
#     "ai_provider": true
#   }
# }
```

Якщо `"status": "healthy"` - **ВСЕ ПРАЦЮЄ!** 🎉

### C. Перевірте автентифікацію

```powershell
# Логін:
curl -X POST https://brainai-production.onrender.com/api/auth/login `
  -H "Content-Type: application/json" `
  -d '{\"username\": \"admin\", \"password\": \"your-admin-password\"}'

# Очікується токен:
# {
#   "access_token": "eyJ...",
#   "token_type": "bearer"
# }
```

### D. Перевірте AI (з токеном)

```powershell
# Замініть YOUR_TOKEN на отриманий токен:
curl -X POST https://brainai-production.onrender.com/process `
  -H "Authorization: Bearer YOUR_TOKEN" `
  -H "Content-Type: application/json" `
  -d '{
    \"text\": \"Привіт! Як справи?\",
    \"archetype\": \"sofiya\",
    \"remember\": true
  }'
```

---

## 🔧 Крок 5: Налаштування CI/CD (опціонально)

### A. Отримайте Render API ключ

1. **Render Dashboard** → Settings → API Keys
2. Натисніть **"Create API Key"**
3. Скопіюйте ключ (він показується тільки раз!)

### B. Знайдіть Service ID

1. Відкрийте ваш сервіс в Render
2. URL буде: `https://dashboard.render.com/web/srv-XXXXXXXXXX`
3. Скопіюйте `srv-XXXXXXXXXX` - це ваш Service ID

### C. Додайте GitHub Secrets

1. **GitHub** → Ваш репозиторій → Settings
2. **Secrets and variables** → Actions
3. **New repository secret**
4. Додайте:

```
Name: RENDER_API_KEY
Value: <ваш Render API ключ>

Name: RENDER_SERVICE_ID
Value: srv-XXXXXXXXXX

Name: RENDER_URL
Value: https://brainai-production.onrender.com

Name: GOOGLE_API_KEY
Value: <ваш Google API ключ> (для тестів)
```

### D. Тестування CI/CD

```powershell
# Зробіть невелику зміну:
echo "# Test deploy" >> README.md

# Закомітьте:
git add README.md
git commit -m "test: CI/CD pipeline"
git push

# Перейдіть на GitHub → Actions
# Подивіться на процес деплою
```

---

## 📊 Крок 6: Моніторинг

### Де дивитися логи:

1. **Render Logs** (реал-тайм):
   - Dashboard → brainai-production → Logs

2. **Metrics** (через API):
   ```powershell
   curl -H "Authorization: Bearer YOUR_TOKEN" \
     https://brainai-production.onrender.com/api/metrics
   ```

3. **Database** (backups):
   - Dashboard → brainai-db → Manual Backup

---

## 🆘 Troubleshooting

### Проблема: "Build failed"

**Рішення**:
```powershell
# Перевірте requirements.txt локально:
pip install -r requirements.txt

# Якщо помилки - виправте і запуште:
git add requirements.txt
git commit -m "fix: Update dependencies"
git push
```

### Проблема: "Environment variable not set"

**Рішення**:
1. Dashboard → Environment
2. Перевірте, що ВСІ змінні додано
3. Save Changes
4. Manual Deploy

### Проблема: "Database connection failed"

**Рішення**:
1. Dashboard → brainai-db → перевірте статус
2. Якщо "Suspended" - Restart
3. Перевірте DATABASE_URL в Environment Variables

---

## ✅ Чеклист готовності

- [ ] .env видалено з Git
- [ ] Нові API ключі створено
- [ ] Старі ключі видалено
- [ ] Environment Variables в Render додано
- [ ] Health check повертає "healthy"
- [ ] Автентифікація працює
- [ ] AI відповідає на запити
- [ ] Логи без помилок
- [ ] Backup database налаштовано

---

## 🎉 Готово!

Ваш AI-асистент розгорнуто на Render!

**URL**: https://brainai-production.onrender.com

### Наступні кроки:

1. **Додайте custom domain** (опціонально):
   - Dashboard → Settings → Custom Domain

2. **Налаштуйте monitoring** (рекомендовано):
   - Інтеграція з Sentry для помилок
   - Uptime monitoring

3. **Оптимізація** (пізніше):
   - Redis для кешування
   - CDN для статики

---

## 📞 Підтримка

Якщо щось не працює:

1. **Перевірте Logs** в Render Dashboard
2. **Прочитайте** RENDER_DEPLOYMENT.md
3. **Перевірте** SECURITY.md для безпеки

**Успіхів! 🚀**
