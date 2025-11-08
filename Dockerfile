# Dockerfile для Local Gemini Brain
# Опціональний спосіб упаковки для кроссплатформенного розповсюдження

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
RUN mkdir -p history vector_db_storage

# Відкриваємо порт
EXPOSE 8000

# Змінні середовища
ENV PYTHONUNBUFFERED=1
ENV GOOGLE_API_KEY=""

# Команда запуску
CMD ["python", "-m", "uvicorn", "main:app", "--host", "0.0.0.0", "--port", "8000"]





