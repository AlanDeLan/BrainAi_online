# Production Dockerfile для BrainAi Online
# Оптимізовано для DigitalOcean App Platform

FROM python:3.11-slim

# Встановлюємо робочу директорію
WORKDIR /app

# Встановлюємо системні залежності для ChromaDB
RUN apt-get update && apt-get install -y \
    build-essential \
    && rm -rf /var/lib/apt/lists/*

# Копіюємо файл залежностей
COPY requirements.txt .

# Встановлюємо Python залежності
RUN pip install --no-cache-dir -r requirements.txt

# Копіюємо весь проект
COPY . .

# Створюємо необхідні директорії
RUN mkdir -p history logs uploads

# Volume для vector_db_storage буде змонтовано через App Platform

# Відкриваємо порт
EXPOSE 8000

# Змінні середовища
ENV PYTHONUNBUFFERED=1
ENV GOOGLE_API_KEY=""

# Команда запуску (production)
CMD ["uvicorn", "main_production:app", "--host", "0.0.0.0", "--port", "8000", "--workers", "1"]








