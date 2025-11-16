# Production Dockerfile для BrainAi Online
# Оптимізовано для Railway.app

FROM python:3.11-slim

# Build ID для примусового оновлення (Railway cache buster)
ARG RAILWAY_GIT_COMMIT_SHA=unknown
ENV BUILD_VERSION=${RAILWAY_GIT_COMMIT_SHA}
# Cache buster - змінюйте це значення для примусового rebuild
ENV CACHE_BUST=2025-11-16-10-00

# Встановлюємо робочу директорію
WORKDIR /app

# Встановлюємо системні залежності для ChromaDB
RUN apt-get update && apt-get install -y \
    build-essential \
    && rm -rf /var/lib/apt/lists/*

# Копіюємо файл залежностей (production)
COPY requirements.production.txt requirements.txt

# Встановлюємо Python залежності
RUN pip install --no-cache-dir -r requirements.txt

# Копіюємо весь проект (з примусовою інвалідацією кешу)
# Railway bug workaround: додаємо timestamp для гарантованого оновлення
RUN echo "Build timestamp: $(date)" > /tmp/build_timestamp
COPY . .

# КРИТИЧНО: Видаляємо весь Python cache щоб уникнути використання старого коду
RUN find . -type d -name __pycache__ -exec rm -rf {} + 2>/dev/null || true
RUN find . -type f -name "*.pyc" -delete 2>/dev/null || true

# Створюємо необхідні директорії
RUN mkdir -p logs uploads

# Note: history and vector_db_storage removed - using PostgreSQL instead
# Free Railway plan does not support persistent volumes

# Volume для vector_db_storage буде змонтовано через Railway

# Відкриваємо порт (Railway використовує змінну $PORT)
EXPOSE 8000

# Змінні середовища
ENV PYTHONUNBUFFERED=1
ENV PYTHONDONTWRITEBYTECODE=1

# Команда запуску через Python скрипт
CMD ["python", "railway_start.py"]








