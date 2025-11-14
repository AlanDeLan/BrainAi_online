# 🔍 Перевірка Railway Volumes

## Проблема: Секції "Volumes" не існує в Railway Dashboard

Railway змінив UI в 2024-2025. Ось де насправді знаходяться volumes:

## 📍 Де знайти Volumes

### Метод 1: Через вкладку сервісу
1. Відкрити https://railway.app
2. Обрати проект **BrainAi Online**
3. Клікнути на **ім'я сервісу** (не Settings!)
4. Зверху з'являться вкладки: **Variables | Deployments | Metrics | Volumes**
5. Клікнути **Volumes**

### Метод 2: Через бічну панель
1. Клікнути на сервіс
2. У правій панелі знайти розділ **"Storage"** або **"Volumes"**

### Метод 3: Через Deploy Logs
1. Відкрити останній Deploy
2. Подивитись логи, шукати рядки:
   ```
   ✅ Mounting volume chromadb_storage to /app/vector_db_storage
   ✅ Mounting volume chat_history to /app/history
   ```
3. Якщо таких рядків НЕМАЄ - volumes НЕ СТВОРЕНІ

## 🛠️ Як створити Volumes (якщо їх немає)

### Варіант 1: Railway CLI (найпростіше)

```bash
# Встановити CLI
npm i -g @railway/cli

# Або через PowerShell:
# winget install Railway.CLI

# Логін
railway login

# Підключитись до проекту
cd c:\Users\alan\OneDrive\IT_project\GitHub\BrainAi_online
railway link

# Створити volumes
railway volume create chromadb_storage --mount-path /app/vector_db_storage
railway volume create chat_history --mount-path /app/history

# Перевірити
railway volume list
```

### Варіант 2: Через Railway Dashboard (новий UI)

1. **Service** → натиснути на назву сервісу
2. Шукати **"Add Volume"** або **"+ New Volume"**
3. Якщо кнопки немає - Railway автоматично створює volumes з `railway.toml`

### Варіант 3: Автоматично через railway.toml (вже налаштовано!)

Railway **ПОВИНЕН** автоматично створювати volumes описані в `railway.toml` при deploy.

**Наш railway.toml:**
```toml
[[deploy.volumes]]
mountPath = "/app/vector_db_storage"
name = "chromadb_storage"

[[deploy.volumes]]
mountPath = "/app/history"
name = "chat_history"
```

## 🔍 Діагностика

### Крок 1: Перевірити Deploy Logs

1. Railway Dashboard → Project → Service
2. Відкрити **Deployments**
3. Клікнути на останній deploy
4. Шукати в логах:

**✅ Якщо volumes працюють:**
```
Mounting volume chromadb_storage to /app/vector_db_storage
Mounting volume chat_history to /app/history
Starting container...
```

**❌ Якщо volumes НЕ працюють:**
```
Starting container...
# Без рядків про mounting
```

### Крок 2: Перевірити API

```bash
# Перевірити Vector DB
curl https://brainaionline-production.up.railway.app/api/debug/vector-db

# Перевірити History
curl https://brainaionline-production.up.railway.app/api/history
```

**Якщо після deploy дані зникають** - volumes НЕ ПРАЦЮЮТЬ.

### Крок 3: Перевірити розмір volumes (якщо створені)

В Railway Dashboard повинен показуватись розмір:
- `chromadb_storage`: XXX MB
- `chat_history`: XXX MB

## 🚨 Чому volumes можуть не працювати

### Причина 1: Railway не підтримує volumes на безкоштовному плані
- ⚠️ З 2024 року Railway може вимагати платний план для volumes
- Перевір: Settings → Billing

### Причина 2: railway.toml не застосувався
- Переконайся що файл є в **корені репозиторію**
- Переконайся що він **закомічений** в git
- Зроби **новий deploy** після додавання railway.toml

### Причина 3: Volumes треба створити вручну
- Якщо автоматичне створення не працює
- Використай Railway CLI (варіант 1)

## ✅ Рішення

### Якщо volumes не створюються автоматично:

**Використай Railway CLI:**

```powershell
# Встановити Railway CLI
winget install Railway.CLI

# АБО через npm
npm install -g @railway/cli

# Логін
railway login

# Підключитись до проекту
cd c:\Users\alan\OneDrive\IT_project\GitHub\BrainAi_online
railway link

# Вибрати правильний service якщо їх декілька
railway service

# Створити volumes
railway volumes create

# АБО конкретно:
railway run bash -c "mkdir -p /app/vector_db_storage /app/history"
```

### Після створення volumes:

1. **Redeploy** проект
2. **Перевірити логи** - мають бути рядки про mounting
3. **Надіслати повідомлення** в чат
4. **Зробити deploy** ще раз
5. **Перевірити дані** - мають зберегтись!

## 📊 Альтернатива: PostgreSQL для всього

Якщо Railway volumes не працюють або платні:

### Зберігати історію в PostgreSQL (вже є код!)
- ✅ Endpoint `/api/history/db` працює
- ✅ Дані в PostgreSQL зберігаються між deploys
- ✅ Безкоштовно на Railway

### Зберігати Vector DB в PostgreSQL
- ❓ ChromaDB може використовувати PostgreSQL як backend
- ❓ Але потрібна допрацювання коду

## 🎯 Що робити ЗАРАЗ

1. **Подивись Deploy Logs** - шукай "Mounting volume"
2. **Якщо немає** - volumes не створені
3. **Встанови Railway CLI** та створи volumes вручну
4. **Або скажи** якщо хочеш зберігати все в PostgreSQL

Яка ситуація у тебе? Є рядки про mounting в логах deploy?
