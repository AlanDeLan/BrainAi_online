# 🚨 Виправлення помилки GOOGLE_API_KEY на Railway

**Дата:** 16 листопада 2025  
**Проблема:** `ValueError: GOOGLE_API_KEY not found in configuration`

---

## 📋 Опис проблеми

Railway логи показують:
```
2025-11-16 07:19:21 - ERROR - Configuration error: GOOGLE_API_KEY not found in configuration
ValueError: GOOGLE_API_KEY not found in configuration
```

**Причина:** Сервер налаштований на `AI_PROVIDER=google_ai`, але змінна `GOOGLE_API_KEY` відсутня в Railway Environment Variables.

---

## ✅ Виправлення (2 варіанти)

### Варіант 1: Додати Google AI ключ (Рекомендовано)

1. **Отримати ключ:**
   - Перейти на https://makersuite.google.com/app/apikey
   - Створити новий API ключ
   - Скопіювати ключ

2. **Додати в Railway:**
   ```bash
   # Railway Dashboard → Variables → Add Variable
   GOOGLE_API_KEY=your-google-api-key-here
   ```

3. **Перезапустити:**
   - Railway автоматично перезапустить після додавання змінної
   - Або вручну: Deploy → Redeploy

### Варіант 2: Перемкнутися на OpenAI

1. **Перевірити чи є OpenAI ключ:**
   ```bash
   # Railway Dashboard → Variables
   # Переконайтеся що є:
   OPENAI_API_KEY=sk-...
   ```

2. **Змінити AI провайдер:**
   ```bash
   # Railway Dashboard → Variables → Edit
   AI_PROVIDER=openai
   ```

3. **Перезапустити:**
   - Railway автоматично перезапустить

---

## 🔧 Автоматичний Fallback

**Виправлення вже додано в код:**

```python
# core/ai_providers.py
def generate_response(...):
    provider = get_current_provider()
    config = get_provider_config()
    
    # Auto-fallback: if Google AI is configured but key is missing, use OpenAI
    if provider == AIProvider.GOOGLE_AI and not config.get('google_api_key'):
        logger.warning("GOOGLE_API_KEY not found, falling back to OpenAI")
        provider = AIProvider.OPENAI
    
    if provider == AIProvider.GOOGLE_AI:
        return _generate_google_ai(...)
    elif provider == AIProvider.OPENAI:
        return _generate_openai(...)
```

**Результат:**
- ✅ Якщо `GOOGLE_API_KEY` відсутній → автоматично використає OpenAI
- ✅ Немає помилки 500
- ✅ Працює з будь-яким доступним провайдером

---

## 🚀 Швидке виправлення (Railway)

### Крок 1: Перевірити змінні
```bash
# Railway Dashboard → Your Project → Variables
```

Переконайтеся що є **принаймні один** ключ:
- `GOOGLE_API_KEY=AIza...` (для Google AI)
- **АБО**
- `OPENAI_API_KEY=sk-...` (для OpenAI)

### Крок 2: Встановити провайдер
```bash
# Якщо є GOOGLE_API_KEY:
AI_PROVIDER=google_ai

# Якщо є OPENAI_API_KEY:
AI_PROVIDER=openai
```

### Крок 3: Перезапустити
```bash
# Railway автоматично перезапустить при зміні змінних
# Або вручну:
railway up --detach
```

---

## 📊 Перевірка після виправлення

### 1. Перевірити логи:
```bash
# Railway Dashboard → Deployments → Latest → Logs
```

Має бути:
```
[OK] Database initialized
[OK] Admin user initialized
[OK] Application started successfully!
Uvicorn running on http://0.0.0.0:8080
```

**Не має бути:**
```
ValueError: GOOGLE_API_KEY not found in configuration
```

### 2. Тестовий запит:
```bash
curl -X POST https://your-railway-app.up.railway.app/process \
  -H "Content-Type: application/json" \
  -d '{
    "text": "Привіт",
    "archetype": "afina"
  }'
```

**Очікуваний результат:**
```json
{
  "response": "Привіт! Я Афіна...",
  "chat_id": "..."
}
```

---

## 🔍 Діагностика

### Якщо помилка залишається:

1. **Перевірити чи змінна встановлена:**
   ```bash
   # Railway → Variables
   # Переконатись що немає пробілів:
   GOOGLE_API_KEY=AIza...  ✅ Правильно
   GOOGLE_API_KEY = AIza...  ❌ Неправильно (пробіли)
   ```

2. **Перевірити чи ключ валідний:**
   ```bash
   # Google AI:
   curl "https://generativelanguage.googleapis.com/v1/models?key=YOUR_KEY"
   
   # OpenAI:
   curl https://api.openai.com/v1/models \
     -H "Authorization: Bearer YOUR_KEY"
   ```

3. **Перевірити логи Railway:**
   ```bash
   # Має показувати який провайдер використовується:
   INFO - AI Provider: google_ai
   # або
   INFO - AI Provider: openai
   ```

---

## 📝 Рекомендації

### Для Production:

1. ✅ **Використовуйте Google AI** (дешевше, якісніше для української мови)
   ```bash
   AI_PROVIDER=google_ai
   GOOGLE_API_KEY=AIza...
   ```

2. ✅ **Додайте backup OpenAI** (на випадок проблем з Google)
   ```bash
   OPENAI_API_KEY=sk-...
   ```

3. ✅ **Встановіть лімити** (захист від перевитрати)
   ```bash
   RATE_LIMIT_PER_MINUTE=60
   RATE_LIMIT_PER_HOUR=1000
   ```

### Для Development:

```bash
# .env файл (локально)
AI_PROVIDER=openai  # Простіше налаштувати
OPENAI_API_KEY=sk-...
```

---

## 🎯 Результат після виправлення

### До:
```
❌ ValueError: GOOGLE_API_KEY not found in configuration
❌ HTTP 500 Internal Server Error
❌ Користувач бачить помилку
```

### Після:
```
✅ Auto-fallback на OpenAI якщо Google ключ відсутній
✅ HTTP 200 OK
✅ Користувач отримує відповідь AI
```

---

## 🔗 Корисні посилання

- **Google AI API Keys:** https://makersuite.google.com/app/apikey
- **OpenAI API Keys:** https://platform.openai.com/api-keys
- **Railway Dashboard:** https://railway.app/dashboard
- **Railway Environment Variables:** https://docs.railway.app/guides/variables

---

**Останнє оновлення:** 16 листопада 2025  
**Статус:** ✅ Виправлено в коді (auto-fallback додано)  
**Потребує:** Налаштування Railway Environment Variables
