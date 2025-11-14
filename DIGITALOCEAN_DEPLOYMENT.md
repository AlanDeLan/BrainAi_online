# 🌊 Розгортання BrainAi Online на DigitalOcean App Platform

Повний гайд з розгортання застосунку на DigitalOcean App Platform з підтримкою PostgreSQL та persistent storage.

---

## 📋 Зміст

1. [Підготовка](#підготовка)
2. [Створення застосунку](#створення-застосунку)
3. [Налаштування змінних середовища](#налаштування-змінних-середовища)
4. [База даних PostgreSQL](#база-даних-postgresql)
5. [Persistent Storage](#persistent-storage)
6. [Деплой та моніторинг](#деплой-та-моніторинг)
7. [Налаштування домену](#налаштування-домену)
8. [CI/CD](#cicd)
9. [Troubleshooting](#troubleshooting)

---

## 🚀 Підготовка

### Передумови

- Акаунт на [DigitalOcean](https://cloud.digitalocean.com/)
- GitHub репозиторій з кодом застосунку
- API ключі (Google AI / OpenAI)

### Вартість

**Базова конфігурація (мінімум ~$12/міс):**
- App Platform Basic XXS: **$5/міс** (512MB RAM, 1 vCPU)
- PostgreSQL Dev Database: **$7/міс** (1GB RAM, 10GB storage, 25 connections)
- Persistent Volume (1GB): **$0.10/міс**

**Рекомендована конфігурація (~$20/міс):**
- App Platform Basic XS: **$12/міс** (1GB RAM, 1 vCPU)
- PostgreSQL Production: **$15/міс** (1GB RAM, 10GB storage)
- Persistent Volume (5GB): **$0.50/міс**

---

## 📦 Створення застосунку

### Метод 1: Через веб-інтерфейс

1. Відкрийте [DigitalOcean Dashboard](https://cloud.digitalocean.com/apps)
2. Натисніть **Create App**
3. Виберіть **GitHub** як джерело
4. Авторизуйте DigitalOcean у GitHub
5. Виберіть репозиторій **AlanDeLan/BrainAi_online**
6. Виберіть гілку **main**
7. Активуйте **Autodeploy** (автоматичний деплой при push)

### Метод 2: Через doctl CLI

```powershell
# Встановіть doctl (якщо ще не встановлено)
choco install doctl

# Авторизуйтесь
doctl auth init

# Створіть застосунок з конфігурації
doctl apps create --spec .do/app.yaml

# Отримайте ID застосунку
doctl apps list
```

### Метод 3: Імпорт з app.yaml

1. У Dashboard натисніть **Create App**
2. Виберіть **Edit Your App Spec**
3. Вставте вміст файлу `.do/app.yaml`
4. Натисніть **Save**

---

## 🔐 Налаштування змінних середовища

### Обов'язкові змінні

Перейдіть у **Settings → App-Level Environment Variables** та додайте:

| Ключ | Значення | Тип |
|------|----------|-----|
| `GOOGLE_API_KEY` | Ваш ключ Google AI Studio | Secret |
| `OPENAI_API_KEY` | Ваш ключ OpenAI (опціонально) | Secret |
| `SECRET_KEY` | Згенеруйте 64 символи | Secret |
| `SESSION_SECRET` | Згенеруйте 64 символи | Secret |
| `DATABASE_URL` | Автоматично з бази даних | Secret |

### Генерація секретних ключів

```powershell
# PowerShell
-join ((48..57) + (65..90) + (97..122) | Get-Random -Count 64 | ForEach-Object {[char]$_})

# Python
python -c "import secrets; print(secrets.token_urlsafe(48))"
```

### Опціональні змінні

| Ключ | Значення за замовчуванням | Опис |
|------|---------------------------|------|
| `AI_PROVIDER` | `google_ai` | `google_ai` або `openai` |
| `CORS_ORIGINS` | `["https://brainai-online-xxxxx.ondigitalocean.app"]` | Оновіть після деплою |
| `RATE_LIMIT_PER_MINUTE` | `60` | Запитів на хвилину |
| `RATE_LIMIT_PER_HOUR` | `1000` | Запитів на годину |
| `LOG_LEVEL` | `INFO` | `DEBUG`, `INFO`, `WARNING`, `ERROR` |
| `DEBUG` | `false` | Не вмикайте у продакшені! |

### Налаштування через CLI

```powershell
# Отримайте ID застосунку
$APP_ID = (doctl apps list --format ID --no-header)

# Додайте змінні
doctl apps update $APP_ID --spec .do/app.yaml
```

---

## 🗄️ База даних PostgreSQL

### Створення бази даних

1. У App Dashboard перейдіть **Database**
2. Натисніть **Add Database**
3. Виберіть **PostgreSQL 15**
4. Виберіть план:
   - **Dev Database** ($7/міс) - для тестування
   - **Production** ($15/міс) - для продакшену
5. Регіон: **Frankfurt** (FRA1)
6. Назва кластера: `brainai-cluster`

### Автоматичне підключення

DigitalOcean автоматично створить змінну `DATABASE_URL` у форматі:
```
postgresql://username:password@host:port/database?sslmode=require
```

### Перевірка підключення

```powershell
# Через CLI
doctl databases list
doctl databases connection $DB_ID
```

### Міграції (якщо використовуєте Alembic)

```powershell
# Локально запустіть міграції
alembic upgrade head

# Або додайте команду в app.yaml → jobs
```

---

## 💾 Persistent Storage

### Налаштування Volume

1. У App Dashboard → **Settings → Storage**
2. Натисніть **Add Storage**
3. Заповніть:
   - **Name**: `vector-db-storage`
   - **Mount Path**: `/app/vector_db_storage`
   - **Size**: `1 GB` (можна збільшити до 250 GB)
4. Натисніть **Create**

### Використання у коді

```python
# core/settings.py
VECTOR_DB_PATH = os.getenv("VECTOR_DB_PATH", "/app/vector_db_storage")
```

Volume автоматично зберігається між деплоями та перезапусками.

### Бекап Volume (опціонально)

```powershell
# Створіть снапшот через CLI
doctl apps tier volumes snapshot create $VOLUME_ID --snapshot-name backup-$(Get-Date -Format "yyyyMMdd")
```

---

## 🚀 Деплой та моніторинг

### Деплой застосунку

```powershell
# Автоматичний деплой при git push
git add .
git commit -m "feat: deploy to DigitalOcean"
git push origin main

# Або вручну через CLI
doctl apps create-deployment $APP_ID
```

### Моніторинг логів

**Через веб-інтерфейс:**
1. App Dashboard → **Runtime Logs**
2. Виберіть **web** service
3. Оберіть період часу

**Через CLI:**
```powershell
# Realtime logs
doctl apps logs $APP_ID --type run --follow

# Build logs
doctl apps logs $APP_ID --type build
```

### Health Check

```powershell
# Перевірка здоров'я застосунку
curl https://brainai-online-xxxxx.ondigitalocean.app/health

# Очікувана відповідь:
# {
#   "status": "healthy",
#   "timestamp": "2025-11-14T12:00:00Z",
#   "version": "1.0.0"
# }
```

### Метрики

Dashboard → **Insights**:
- CPU Usage
- Memory Usage
- HTTP Requests (Rate, Status Codes)
- Response Time
- Crash Rate

---

## 🌐 Налаштування домену

### Додавання власного домену

1. App Dashboard → **Settings → Domains**
2. Натисніть **Add Domain**
3. Введіть ваш домен: `brainai.yourdomain.com`
4. DigitalOcean надасть DNS записи:
   ```
   CNAME brainai → brainai-online-xxxxx.ondigitalocean.app
   ```
5. Додайте цей CNAME у вашому DNS провайдері
6. Дочекайтесь поширення (до 48 годин)
7. SSL сертифікат буде видано автоматично (Let's Encrypt)

### Оновлення CORS_ORIGINS

Після додавання домену оновіть змінну:
```yaml
CORS_ORIGINS: '["https://brainai.yourdomain.com"]'
```

---

## 🔄 CI/CD

### Автоматичний деплой

Вже налаштовано у `.do/app.yaml`:
```yaml
github:
  deploy_on_push: true
  branch: main
```

Кожен `git push` на `main` автоматично запускає:
1. Build Docker image
2. Run tests (якщо є)
3. Deploy нової версії
4. Health check
5. Rollback у разі помилки

### GitHub Actions (додатково)

Створіть `.github/workflows/digitalocean.yml`:

```yaml
name: Deploy to DigitalOcean

on:
  push:
    branches: [main]

jobs:
  deploy:
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v3
      
      - name: Install doctl
        uses: digitalocean/action-doctl@v2
        with:
          token: ${{ secrets.DIGITALOCEAN_TOKEN }}
      
      - name: Deploy to App Platform
        run: |
          doctl apps create-deployment ${{ secrets.APP_ID }} --wait
```

### Rollback

```powershell
# Список деплоїв
doctl apps list-deployments $APP_ID

# Rollback до попередньої версії
doctl apps rollback $APP_ID $DEPLOYMENT_ID
```

---

## 🔧 Troubleshooting

### Застосунок не запускається

**Перевірте логи:**
```powershell
doctl apps logs $APP_ID --type run --follow
```

**Типові проблеми:**
- ❌ **Port mismatch**: Переконайтесь, що app слухає на `$PORT` (8000)
- ❌ **Missing env vars**: Перевірте всі обов'язкові змінні
- ❌ **Database connection**: Перевірте `DATABASE_URL`

### Health check fails

```python
# main_production.py
@app.get("/health")
async def health_check():
    return {
        "status": "healthy",
        "timestamp": datetime.utcnow().isoformat(),
        "database": await check_db_connection()
    }
```

### High memory usage

**Оптимізація:**
1. Зменшіть кількість workers у `gunicorn_config.py`
2. Увімкніть swap (автоматично у DigitalOcean)
3. Upgrade до більшого плану (Basic XS - 1GB RAM)

### Повільна відповідь

**Рішення:**
- Використовуйте Redis для кешування (додайте як managed database)
- Оптимізуйте SQL запити
- Додайте CDN для статичних файлів

### Volume не монтується

```powershell
# Перевірте статус volume
doctl apps tier volumes list

# Перевірте mount path у app.yaml
volumes:
  - name: vector-db-storage
    mount_path: /app/vector_db_storage
```

---

## 📊 Вартість оптимізації

### Скорочення витрат

1. **Використовуйте Dev Database** ($7) замість Production ($15)
2. **Basic XXS plan** ($5) для малого трафіку
3. **Автоскейлінг**: платите тільки за використані ресурси
4. **Scheduled scaling**: вимикайте у неробочий час

```yaml
autoscaling:
  min_instance_count: 0  # Вимикається при 0 запитах
  max_instance_count: 3
```

### Моніторинг витрат

Dashboard → **Billing**:
- Поточні витрати
- Прогноз на місяць
- Розбивка по ресурсам

---

## 🎯 Чеклист деплою

- [ ] Створено застосунок на DigitalOcean
- [ ] Додано PostgreSQL базу даних
- [ ] Налаштовано всі змінні середовища
- [ ] Створено persistent volume для векторної БД
- [ ] Перевірено health endpoint
- [ ] Оновлено CORS_ORIGINS з реальним URL
- [ ] Налаштовано власний домен (опціонально)
- [ ] Увімкнено автоматичний деплой
- [ ] Протестовано основний функціонал
- [ ] Налаштовано моніторинг та алерти

---

## 🔗 Корисні посилання

- [DigitalOcean App Platform Docs](https://docs.digitalocean.com/products/app-platform/)
- [App Spec Reference](https://docs.digitalocean.com/products/app-platform/reference/app-spec/)
- [doctl CLI](https://docs.digitalocean.com/reference/doctl/)
- [PostgreSQL Managed Database](https://docs.digitalocean.com/products/databases/postgresql/)
- [Pricing Calculator](https://www.digitalocean.com/pricing/app-platform)

---

## ⚡ Швидкий старт

```powershell
# 1. Клонуйте репозиторій
git clone https://github.com/AlanDeLan/BrainAi_online.git
cd BrainAi_online

# 2. Створіть застосунок
doctl apps create --spec .do/app.yaml

# 3. Отримайте URL
doctl apps list

# 4. Відкрийте у браузері
start https://brainai-online-xxxxx.ondigitalocean.app
```

---

**Успішного деплою! 🚀**
