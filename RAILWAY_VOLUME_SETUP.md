# Railway Volume Setup для ChromaDB

## Проблема
ChromaDB векторна база зберігається в `/app/vector_db_storage` всередині Docker контейнера. При кожному новому деплої контейнер пересоздаётся і всі файли втрачаються.

## Рішення
Railway Volumes - постійне сховище, яке монтується в контейнер і зберігається між деплоями.

## Налаштування (вже зроблено в коді)

### 1. `railway.toml`
```toml
[[deploy.volumes]]
mountPath = "/app/vector_db_storage"
name = "chromadb_storage"
```

### 2. `Dockerfile`
```dockerfile
RUN mkdir -p vector_db_storage
RUN chmod 777 vector_db_storage
```

## Активація через Railway Dashboard

**ВАЖЛИВО:** Railway Volumes потрібно активувати через веб-інтерфейс!

### Крок 1: Відкрити проект
https://railway.app/project/YOUR_PROJECT_ID

### Крок 2: Settings → Volumes
1. Натисніть "New Volume"
2. Mount Path: `/app/vector_db_storage`
3. Name: `chromadb_storage`
4. Натисніть "Add"

### Крок 3: Redeploy
Після додавання volume Railway автоматично перезапустить деплоймент.

## Перевірка

Після деплою виконайте:
```bash
curl https://brainaionline-production.up.railway.app/api/debug/vector-db
```

Повинно показати `admin_collection_count` > 0 після надсилання повідомлень.

## Тестування збереження

1. Надішліть кілька повідомлень в чат
2. Перевірте векторну БД - має бути непорожньою
3. Зробіть новий деплоймент (будь-який git push)
4. Перевірте векторну БД знову - **дані мають зберегтися!**

## Альтернатива (якщо Railway Volumes платні)

Використовувати PostgreSQL для ChromaDB metadata + S3 для vectors (складніше).
