# Railway Volumes Setup для ChromaDB та History

## Проблема
- ChromaDB векторна база зберігається в `/app/vector_db_storage` 
- Файлова історія чатів зберігається в `/app/history`
- При кожному новому деплої контейнер пересоздаётся і **ВСІ ФАЙЛИ ВТРАЧАЮТЬСЯ**

## Рішення
Railway Volumes - постійне сховище, яке монтується в контейнер і **ЗБЕРІГАЄТЬСЯ МІЖ ДЕПЛОЯМИ**.

## Налаштування (вже зроблено в коді)

### 1. `railway.toml`
```toml
# Persistent storage for vector database and chat history
[[deploy.volumes]]
mountPath = "/app/vector_db_storage"
name = "chromadb_storage"

[[deploy.volumes]]
mountPath = "/app/history"
name = "chat_history"
```

### 2. `Dockerfile`
```dockerfile
RUN mkdir -p history logs uploads vector_db_storage
RUN chmod 777 vector_db_storage history
```

## ⚠️ ОБОВ'ЯЗКОВО: Активація через Railway Dashboard

**ВАЖЛИВО:** Railway Volumes потрібно створити вручну через веб-інтерфейс!

### Крок 1: Відкрити проект
https://railway.app → BrainAi Online → Settings

### Крок 2: Створити Volume для ChromaDB
1. Прокрутити до секції "Volumes"
2. Натиснути "New Volume"
3. **Mount Path**: `/app/vector_db_storage`
4. **Name**: `chromadb_storage` (має співпадати з railway.toml!)
5. Натиснути "Add"

### Крок 3: Створити Volume для History
1. Натиснути "New Volume" ще раз
2. **Mount Path**: `/app/history`
3. **Name**: `chat_history` (має співпадати з railway.toml!)
4. Натиснути "Add"

### Крок 4: Redeploy
Railway автоматично перезапустить деплоймент з новими volumes.

## Що зберігається

### ChromaDB Volume (`/app/vector_db_storage`)
- ✅ `chroma.sqlite3` - база даних ChromaDB
- ✅ `uuid/` - директорії з векторними ембеддінгами
- ✅ Колекції: `user_{user_id}_chats`

### History Volume (`/app/history`)
- ✅ `{chat_id}.json` - файли з історією чатів
- ✅ Формат: `[{user_input, archetype, model_response}, ...]`

### Ефемерне (НЕ зберігається)
- ❌ `/app/logs` - логи очищаються при деплої
- ❌ `/app/uploads` - тимчасові файли видаляються

## Перевірка після деплою

### 1. Перевірити логи Railway
Має бути:
```
Mounting volume chromadb_storage to /app/vector_db_storage
Mounting volume chat_history to /app/history
```

### 2. Перевірити Vector DB
```bash
curl https://brainaionline-production.up.railway.app/api/debug/vector-db
```
Після надсилання повідомлень повинно бути `admin_collection_count` > 0

### 3. Перевірити History
```bash
curl https://brainaionline-production.up.railway.app/api/history
```
Повинен повернути список файлів історії

## Тестування персистентності

1. **Надішліть повідомлення** в чат
2. **Перевірте дані**:
   - Vector DB: `/api/vector-db` (має показати чати)
   - History: `/api/history` (має показати файли)
3. **Зробіть деплой** (будь-який `git push`)
4. **Перевірте знову** - дані **МАЮТЬ ЗБЕРЕГТИСЯ!**

## ❌ Якщо дані все одно втрачаються

1. **Перевірте чи створені volumes** в Railway Dashboard → Settings → Volumes
2. **Перевірте mount paths**: Мають бути точно `/app/vector_db_storage` та `/app/history`
3. **Перевірте назви**: Мають співпадати з `railway.toml` (`chromadb_storage` та `chat_history`)
4. **Подивіться логи деплою**: Шукайте рядки "Mounting volume..."
