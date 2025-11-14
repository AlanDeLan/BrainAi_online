# 🔄 Міграція на PostgreSQL (БЕЗ Railway Volumes)

## 🚨 Проблема
Railway безкоштовний план **НЕ ПІДТРИМУЄ** volumes, тому:
- ❌ ChromaDB не може зберігати дані між deploys
- ❌ Файлова історія втрачається при кожному deploy
- ❌ Vector DB завжди порожня

## ✅ Рішення: PostgreSQL для ВСЬОГО

У тебе вже є PostgreSQL база даних! Використаємо її для:
1. **Історія чатів** → таблиця `chat_messages` (вже є!)
2. **Семантичний пошук** → PostgreSQL full-text search
3. **Файли** → Тимчасові (обробляємо та видаляємо)

## 📊 Що вже працює

### ✅ PostgreSQL таблиці (існують)
```sql
users - Користувачі (id, email, password_hash)
archetypes - Архетипи користувачів  
chat_messages - Повідомлення чатів (chat_id, user_id, role, content)
user_sessions - Сесії користувачів
```

### ✅ Endpoints що працюють
- `/api/history/db` - Отримати історію з бази
- `/api/history/db/{chat_id}` - Отримати конкретний чат
- `/api/auth/*` - Авторизація працює

## 🔧 Що треба змінити

### 1. Вимкнути ChromaDB (не працює без volumes)

**Файл:** `main.py`

Замінити всі виклики ChromaDB на PostgreSQL:

```python
# СТАРИЙ КОД (з ChromaDB):
from vector_db.client import save_message
save_message(chat_id, message_id, text, role="user", ...)

# НОВИЙ КОД (PostgreSQL):
from core.db_models import ChatMessage
db_message = ChatMessage(
    chat_id=chat_id,
    user_id=user_id,
    role="user",
    content=text,
    message_index=msg_index
)
db.add(db_message)
db.commit()
```

### 2. Замінити файлову історію на PostgreSQL

**БУЛО:**
```python
# Зберігати в файл history/{chat_id}.json
async with aiofiles.open(filepath, "w") as f:
    await f.write(json.dumps(chat_history))
```

**СТАЛО:**
```python
# Зберігати в PostgreSQL
from core.db_models import ChatMessage
# Зберігається автоматично через ChatMessage
```

### 3. Семантичний пошук через PostgreSQL

**Замість ChromaDB векторів:**
```python
# PostgreSQL full-text search
SELECT * FROM chat_messages 
WHERE to_tsvector('english', content) @@ plainto_tsquery('english', 'query')
ORDER BY ts_rank(to_tsvector(content), plainto_tsquery('query')) DESC
LIMIT 5;
```

## 🚀 Швидке впровадження

### Крок 1: Оновити railway.toml (видалити volumes)

```toml
[build]
builder = "DOCKERFILE"
dockerfilePath = "Dockerfile"

[deploy]
startCommand = "python railway_start.py"
healthcheckPath = "/health"
healthcheckTimeout = 100
restartPolicyType = "ON_FAILURE"
restartPolicyMaxRetries = 10

# ВИДАЛИТИ volumes (не працюють на безкоштовному плані)
# [[deploy.volumes]]
# mountPath = "/app/vector_db_storage"
# name = "chromadb_storage"
```

### Крок 2: Оновити код збереження

Замінити в `main.py` функцію `/process`:

```python
@app.post("/process")
async def process_text(
    request: Request,
    db: Session = Depends(get_db),
    user_id: Optional[int] = Depends(get_current_user_id_optional)
):
    # ... існуючий код ...
    
    # ЗАМІСТЬ збереження у файл та ChromaDB:
    if remember and chat_id:
        from core.db_models import ChatMessage
        
        # Отримати існуючі повідомлення для індексу
        existing = db.query(ChatMessage).filter(
            ChatMessage.chat_id == chat_id
        ).count()
        
        # Зберегти повідомлення користувача
        user_msg = ChatMessage(
            chat_id=chat_id,
            user_id=user_id or 1,  # Default to admin if no auth
            role="user",
            content=text,
            message_index=existing,
            msg_metadata={"archetype": archetype}
        )
        db.add(user_msg)
        
        # Зберегти відповідь асистента
        assistant_msg = ChatMessage(
            chat_id=chat_id,
            user_id=user_id or 1,
            role="assistant",
            content=result.get("response", ""),
            message_index=existing + 1,
            msg_metadata={"archetype": archetype}
        )
        db.add(assistant_msg)
        
        db.commit()
        logger.info(f"💾 Saved to PostgreSQL: {chat_id}")
    
    return JSONResponse(content=result)
```

### Крок 3: Оновити завантаження історії

```python
# ЗАМІСТЬ читання з файлу:
if remember and chat_id:
    from core.db_models import ChatMessage
    
    # Завантажити з PostgreSQL
    messages = db.query(ChatMessage).filter(
        ChatMessage.chat_id == chat_id
    ).order_by(ChatMessage.message_index).all()
    
    # Конвертувати у формат chat_history
    chat_history = []
    for i in range(0, len(messages), 2):
        if i + 1 < len(messages):
            chat_history.append({
                "user_input": messages[i].content,
                "archetype": messages[i].msg_metadata.get("archetype", archetype),
                "model_response": messages[i + 1].content
            })
```

### Крок 4: Видалити ChromaDB залежності

**Dockerfile:**
```dockerfile
# ВИДАЛИТИ ChromaDB залежності
# RUN apt-get install -y build-essential

# ВИДАЛИТИ директорії
RUN mkdir -p logs uploads
# БЕЗ: vector_db_storage history
```

**requirements.txt:**
```
# ВИДАЛИТИ або закоментувати:
# chromadb
# sentence-transformers
```

## 📝 Переваги PostgreSQL підходу

### ✅ Що працюватиме:
- ✅ Історія зберігається між deploys
- ✅ Швидкі запити (індекси PostgreSQL)
- ✅ Повнотекстовий пошук
- ✅ Резервні копії (Railway автоматично)
- ✅ Безкоштовно на Railway

### ⚠️ Що втратимо:
- ❌ Векторні ембеддінги (семантична схожість)
- ❌ ChromaDB автоматичний поділ на чанки
- ⚠️ Пошук буде простіший (ключові слова, не семантика)

### 💡 Компроміс:
PostgreSQL full-text search **достатньо потужний** для більшості задач!

## 🎯 Наступні кроки

Хочеш щоб я:
1. ✅ **Зараз змінив код** (видалю ChromaDB, переключу на PostgreSQL)
2. ✅ **Оновив railway.toml** (видалю volumes)
3. ✅ **Задеплоїв зміни** (git commit + push)

Після цього:
- Історія зберігатиметься в PostgreSQL
- Дані НЕ ВТРАЧАТИМУТЬСЯ при deploy
- Vector DB UI показуватиме дані з PostgreSQL

**Продовжуємо?** 🚀
