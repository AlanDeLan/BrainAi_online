# 📚 Детальний мануал: Логіка роботи BrainAi

**Версія:** 2.0 Production  
**Дата:** 16 листопада 2025  
**Автор:** Документація розробника

---

## 📋 Зміст

1. [Загальна архітектура](#загальна-архітектура)
2. [Контекст та пам'ять](#контекст-та-память)
3. [Історія чатів](#історія-чатів)
4. [База даних](#база-даних)
5. [Векторний пошук](#векторний-пошук)
6. [Процес обробки запиту](#процес-обробки-запиту)
7. [Автентифікація](#автентифікація)
8. [Архетипи AI](#архетипи-ai)
9. [Оптимізація токенів](#оптимізація-токенів)
10. [Приклади коду](#приклади-коду)

---

## 🏗️ Загальна архітектура

### Компоненти системи

```
┌─────────────────────────────────────────────────────────────┐
│                        КОРИСТУВАЧ                           │
└───────────────────────┬─────────────────────────────────────┘
                        │
                        │ HTTP/HTTPS
                        ▼
┌─────────────────────────────────────────────────────────────┐
│                     FastAPI Backend                         │
│  ┌──────────┐  ┌──────────┐  ┌──────────┐  ┌────────────┐  │
│  │  Auth    │  │  Logic   │  │  Cache   │  │ Rate Limit │  │
│  │ (JWT)    │  │ (AI)     │  │ (Memory) │  │ (60/min)   │  │
│  └──────────┘  └──────────┘  └──────────┘  └────────────┘  │
└───────────────┬─────────────────────────────────┬───────────┘
                │                                 │
        ┌───────┴──────┐                   ┌──────┴──────┐
        │              │                   │             │
        ▼              ▼                   ▼             ▼
┌──────────────┐ ┌──────────────┐  ┌──────────┐  ┌──────────┐
│  PostgreSQL  │ │   pgvector   │  │ Google   │  │  OpenAI  │
│  (Messages)  │ │ (Embeddings) │  │   AI     │  │   API    │
└──────────────┘ └──────────────┘  └──────────┘  └──────────┘
```

### Потік даних

```
Користувач вводить текст
    ↓
JWT перевірка
    ↓
Rate limiting перевірка
    ↓
Завантаження контексту (Sliding Window + Semantic Search)
    ↓
AI обробка (Google AI / OpenAI)
    ↓
Збереження в PostgreSQL + pgvector
    ↓
Відповідь користувачу
```

---

## 🧠 Контекст та пам'ять

### 1. Система пам'яті

BrainAi використовує **гібридну систему пам'яті** з трьома рівнями:

```python
┌────────────────────────────────────────────────────────┐
│              СТРУКТУРА ПАМ'ЯТІ                         │
├────────────────────────────────────────────────────────┤
│                                                        │
│  1️⃣ SLIDING WINDOW (Короткострокова пам'ять)          │
│     └─ Останні 3 обміни (MAX_RECENT_MESSAGES = 3)     │
│     └─ Зберігає безпосередній контекст розмови        │
│     └─ Завжди присутній у промпті                     │
│                                                        │
│  2️⃣ SEMANTIC SEARCH - Current Chat (Середньострокова) │
│     └─ Top 3 найрелевантніших повідомлення з          │
│        ПОТОЧНОГО чату (n_results=3)                    │
│     └─ Використовує pgvector для пошуку подібності   │
│     └─ Додається якщо релевантність > threshold       │
│                                                        │
│  3️⃣ SEMANTIC SEARCH - Global (Довгострокова)          │
│     └─ Top 2 найрелевантніших повідомлення з          │
│        УСІХ чатів користувача (n_results=2)           │
│     └─ Використовує pgvector для глобального пошуку  │
│     └─ Додається якщо релевантність > threshold       │
│                                                        │
└────────────────────────────────────────────────────────┘
```

### 2. Алгоритм формування контексту

**Файл:** `core/logic.py`, функція `process_with_archetype()`

```python
async def process_with_archetype(
    text: str,
    chat_id: str,
    user_id: int,
    archetype_data: dict
):
    """
    КРОК 1: Завантаження Sliding Window
    ------------------------------------
    Останні 3 обміни = останні 6 повідомлень (user + assistant)
    """
    recent_messages = db.query(ChatMessage)\
        .filter(
            ChatMessage.user_id == user_id,
            ChatMessage.chat_id == chat_id
        )\
        .order_by(ChatMessage.message_index.desc())\
        .limit(MAX_RECENT_MESSAGES * 2)\
        .all()
    
    recent_messages.reverse()  # Хронологічний порядок
    
    """
    КРОК 2: Семантичний пошук по поточному чату
    --------------------------------------------
    Знаходимо схожі повідомлення з ПОТОЧНОЇ розмови
    """
    relevant_messages = search_chat_messages(
        chat_id=chat_id,
        query_text=text,
        n_results=3,
        user_id=user_id
    )
    
    """
    КРОК 3: Глобальний семантичний пошук
    -------------------------------------
    Знаходимо схожі повідомлення з ІНШИХ розмов
    """
    relevant_chats = search_chats(
        query_text=text,
        n_results=2,
        user_id=user_id,
        exclude_chat_id=chat_id  # Виключаємо поточний чат
    )
    
    """
    КРОК 4: Об'єднання контексту
    -----------------------------
    Формуємо фінальний промпт
    """
    context = {
        "recent": recent_messages,        # 6 повідомлень
        "current_chat": relevant_messages, # до 3 повідомлень
        "other_chats": relevant_chats      # до 2 повідомлень
    }
    
    # Максимум: 6 + 3 + 2 = 11 повідомлень у контексті
```

### 3. Чому саме така структура?

#### ✅ Переваги Sliding Window:

```python
MAX_RECENT_MESSAGES = 3  # Останні 3 обміни

# Приклад розмови:
# User: "Як справи?"
# AI: "Добре, дякую!"
# User: "Розкажи про проект"
# AI: "Проект має архітектуру..."
# User: "А база даних?"
# AI: "База даних PostgreSQL..."
# User: "Яка версія?" <-- НОВИЙ ЗАПИТ
```

**Sliding Window завантажить:**
- 👤 User: "Розкажи про проект"
- 🤖 AI: "Проект має архітектуру..."
- 👤 User: "А база даних?"
- 🤖 AI: "База даних PostgreSQL..."
- 👤 User: "Яка версія?"
- 🤖 AI: ??? (обробляється)

**Чому 3, а не 5 або 10?**
- ✅ **Економія токенів**: 3 обміни ≈ 500-1000 токенів
- ✅ **Актуальність**: Зберігає лише свіжий контекст
- ✅ **Швидкість**: Менше даних для обробки
- ❌ Якщо 10: занадто багато токенів, втрата фокусу

#### ✅ Переваги Semantic Search:

```python
# Приклад: Користувач 2 тижні тому обговорював PostgreSQL
# Тепер питає: "Як налаштувати БД?"

# Semantic Search знайде:
relevant_messages = [
    "PostgreSQL потребує DATABASE_URL",
    "Індекси покращують продуктивність",
    "pgvector для векторного пошуку"
]

# Навіть якщо це було в іншому чаті!
```

**Чому 3 + 2, а не 10 + 10?**
- ✅ **Точність**: Топ-3 = найрелевантніші
- ✅ **Баланс**: Поточний чат важливіший (3) ніж інші (2)
- ✅ **Токени**: 5 додаткових повідомлень ≈ 1000 токенів
- ❌ Якщо 10+10: втрата релевантності, шум у контексті

---

## 📜 Історія чатів

### 1. Модель даних

**Файл:** `core/db_models.py`

```python
class ChatMessage(Base):
    """
    Кожне повідомлення у системі
    """
    __tablename__ = "chat_messages"
    
    id = Column(Integer, primary_key=True)
    user_id = Column(Integer, ForeignKey("users.id"), nullable=False)
    chat_id = Column(String, nullable=False, index=True)
    
    role = Column(String, nullable=False)  # "user" або "assistant"
    content = Column(Text, nullable=False)
    
    message_index = Column(Integer, nullable=False)  # Порядок у чаті
    created_at = Column(DateTime, default=datetime.utcnow)
    
    # ВАЖЛИВО: Індекси для швидкого пошуку
    __table_args__ = (
        Index('idx_chat_user_chat', 'user_id', 'chat_id'),
        Index('idx_chat_user_created', 'user_id', 'created_at'),
    )
```

### 2. Збереження історії

**Файл:** `main_production.py`, endpoint `/api/process`

```python
@app.post("/api/process")
async def process_message(
    request: ProcessRequest,
    current_user_id: int = Depends(get_current_user_id),
    db: Session = Depends(get_db)
):
    """
    КРОК 1: Користувач відправляє повідомлення
    """
    user_message = request.text
    chat_id = request.chat_id or str(uuid.uuid4())
    
    """
    КРОК 2: Знаходимо наступний message_index
    """
    last_message = db.query(ChatMessage)\
        .filter(
            ChatMessage.user_id == current_user_id,
            ChatMessage.chat_id == chat_id
        )\
        .order_by(ChatMessage.message_index.desc())\
        .first()
    
    next_index = (last_message.message_index + 1) if last_message else 0
    
    """
    КРОК 3: Зберігаємо повідомлення користувача
    """
    user_msg_db = ChatMessage(
        user_id=current_user_id,
        chat_id=chat_id,
        role="user",
        content=user_message,
        message_index=next_index
    )
    db.add(user_msg_db)
    db.commit()
    
    """
    КРОК 4: AI обробляє та генерує відповідь
    """
    ai_response = await process_with_archetype(
        text=user_message,
        chat_id=chat_id,
        user_id=current_user_id,
        archetype_data=archetype
    )
    
    """
    КРОК 5: Зберігаємо відповідь AI
    """
    assistant_msg_db = ChatMessage(
        user_id=current_user_id,
        chat_id=chat_id,
        role="assistant",
        content=ai_response,
        message_index=next_index + 1
    )
    db.add(assistant_msg_db)
    db.commit()
    
    """
    КРОК 6: Зберігаємо embeddings для semantic search
    """
    await save_chat_embedding(
        chat_id=chat_id,
        user_id=current_user_id,
        text=user_message,
        role="user"
    )
    await save_chat_embedding(
        chat_id=chat_id,
        user_id=current_user_id,
        text=ai_response,
        role="assistant"
    )
    
    return {"response": ai_response, "chat_id": chat_id}
```

### 3. Завантаження історії

**Endpoint:** `/api/history/db`

```python
@app.get("/api/history/db")
async def get_db_history(
    chat_id: Optional[str] = None,
    limit: int = 100,
    current_user_id: int = Depends(get_current_user_id),
    db: Session = Depends(get_db)
):
    """
    Повертає історію повідомлень
    """
    query = db.query(ChatMessage).filter(
        ChatMessage.user_id == current_user_id
    )
    
    # Фільтр по конкретному чату (опціонально)
    if chat_id:
        query = query.filter(ChatMessage.chat_id == chat_id)
    
    # Сортування по часу створення
    messages = query.order_by(ChatMessage.created_at.asc())\
                    .limit(limit)\
                    .all()
    
    # Групування по chat_id
    chats = {}
    for msg in messages:
        if msg.chat_id not in chats:
            chats[msg.chat_id] = []
        chats[msg.chat_id].append({
            "role": msg.role,
            "content": msg.content,
            "created_at": msg.created_at.isoformat()
        })
    
    return {"chats": chats}
```

### 4. Ізоляція користувачів

**КРИТИЧНО ВАЖЛИВО:** Кожен запит фільтрується по `user_id`

```python
# ❌ ПОГАНО: Користувач А може бачити дані користувача Б
messages = db.query(ChatMessage).all()

# ✅ ДОБРЕ: Користувач бачить лише свої дані
messages = db.query(ChatMessage)\
    .filter(ChatMessage.user_id == current_user_id)\
    .all()

# ✅ ДОБРЕ: З додатковим фільтром по chat_id
messages = db.query(ChatMessage)\
    .filter(
        ChatMessage.user_id == current_user_id,
        ChatMessage.chat_id == chat_id
    )\
    .all()
```

**Гарантія безпеки:**
1. JWT токен → current_user_id (Depends(get_current_user_id))
2. Кожен DB запит має `filter(user_id == current_user_id)`
3. PostgreSQL Foreign Key constraints

---

## 🗄️ База даних

### 1. Схема PostgreSQL

```sql
-- Таблиця користувачів
CREATE TABLE users (
    id SERIAL PRIMARY KEY,
    email VARCHAR(255) UNIQUE NOT NULL,
    password_hash TEXT NOT NULL,
    created_at TIMESTAMP DEFAULT NOW(),
    updated_at TIMESTAMP DEFAULT NOW()
);

-- Таблиця повідомлень
CREATE TABLE chat_messages (
    id SERIAL PRIMARY KEY,
    user_id INTEGER REFERENCES users(id) ON DELETE CASCADE,
    chat_id VARCHAR(255) NOT NULL,
    role VARCHAR(50) NOT NULL,  -- 'user' або 'assistant'
    content TEXT NOT NULL,
    message_index INTEGER NOT NULL,
    created_at TIMESTAMP DEFAULT NOW(),
    
    -- Індекси для швидкого пошуку
    INDEX idx_chat_user_chat (user_id, chat_id),
    INDEX idx_chat_user_created (user_id, created_at)
);

-- Таблиця векторних embeddings (pgvector)
CREATE TABLE chat_embeddings (
    id SERIAL PRIMARY KEY,
    user_id INTEGER REFERENCES users(id) ON DELETE CASCADE,
    chat_id VARCHAR(255) NOT NULL,
    message_id INTEGER REFERENCES chat_messages(id) ON DELETE CASCADE,
    embedding vector(768),  -- pgvector тип даних
    text_content TEXT NOT NULL,
    created_at TIMESTAMP DEFAULT NOW(),
    
    -- Індекс для векторного пошуку
    INDEX idx_embeddings_user_chat (user_id, chat_id)
);

-- Індекс для векторного пошуку (HNSW - Hierarchical Navigable Small World)
CREATE INDEX idx_embeddings_vector ON chat_embeddings
USING hnsw (embedding vector_cosine_ops);

-- Таблиця сесій
CREATE TABLE user_sessions (
    id SERIAL PRIMARY KEY,
    user_id INTEGER REFERENCES users(id) ON DELETE CASCADE,
    token_hash VARCHAR(255) UNIQUE NOT NULL,
    created_at TIMESTAMP DEFAULT NOW(),
    expires_at TIMESTAMP NOT NULL
);

-- Таблиця архетипів
CREATE TABLE archetypes (
    id SERIAL PRIMARY KEY,
    user_id INTEGER REFERENCES users(id) ON DELETE CASCADE,
    name VARCHAR(255) NOT NULL,
    config JSONB NOT NULL,
    created_at TIMESTAMP DEFAULT NOW(),
    
    UNIQUE(user_id, name)
);
```

### 2. Ініціалізація БД

**Файл:** `core/database.py`

```python
class DatabaseManager:
    def __init__(self):
        self.engine = None
        self.SessionLocal = None
        self.Base = Base  # SQLAlchemy declarative_base
    
    def init_db(self, database_url: str):
        """
        КРОК 1: Створення engine
        """
        self.engine = create_engine(
            database_url,
            pool_size=5,          # 5 постійних з'єднань
            max_overflow=10,      # +10 тимчасових
            pool_pre_ping=True    # Перевірка з'єднання
        )
        
        """
        КРОК 2: Створення session factory
        """
        self.SessionLocal = sessionmaker(
            autocommit=False,
            autoflush=False,
            bind=self.engine
        )
        
        """
        КРОК 3: Включення pgvector (PostgreSQL)
        """
        if "postgresql" in database_url:
            with self.engine.connect() as conn:
                conn.execute(text("CREATE EXTENSION IF NOT EXISTS vector"))
                conn.commit()
        
        """
        КРОК 4: Створення всіх таблиць
        """
        Base.metadata.create_all(bind=self.engine)
        
        """
        КРОК 5: Створення індексів
        """
        self._create_indexes()
    
    def _create_indexes(self):
        """
        Створення індексів для оптимізації
        """
        with self.engine.connect() as conn:
            # Індекс для chat_messages
            conn.execute(text("""
                CREATE INDEX IF NOT EXISTS idx_chat_user_chat
                ON chat_messages(user_id, chat_id)
            """))
            
            # Індекс для векторного пошуку
            conn.execute(text("""
                CREATE INDEX IF NOT EXISTS idx_embeddings_vector
                ON chat_embeddings
                USING hnsw (embedding vector_cosine_ops)
            """))
            
            conn.commit()
```

### 3. Dependency Injection

**Файл:** `main_production.py`

```python
def get_db():
    """
    FastAPI Dependency для отримання DB session
    """
    if db_manager.SessionLocal is None:
        raise RuntimeError("Database not initialized. Call init_database() first")
    
    db = db_manager.SessionLocal()
    try:
        yield db  # Передаємо session в endpoint
    finally:
        db.close()  # Завжди закриваємо з'єднання

# Використання в endpoint:
@app.get("/api/history")
async def get_history(
    db: Session = Depends(get_db),  # <-- Автоматична ін'єкція
    current_user_id: int = Depends(get_current_user_id)
):
    messages = db.query(ChatMessage)\
        .filter(ChatMessage.user_id == current_user_id)\
        .all()
    
    return {"messages": messages}
```

### 4. Транзакції та error handling

```python
@app.post("/api/process")
async def process_message(db: Session = Depends(get_db)):
    try:
        # Крок 1: Створюємо повідомлення
        msg = ChatMessage(content="...")
        db.add(msg)
        
        # Крок 2: Обробляємо AI
        response = await ai_process(msg.content)
        
        # Крок 3: Зберігаємо відповідь
        reply = ChatMessage(content=response)
        db.add(reply)
        
        # Крок 4: Commit транзакції
        db.commit()
        
        return {"response": response}
    
    except Exception as e:
        # Rollback при помилці
        db.rollback()
        logger.error(f"Error processing: {e}")
        
        # Не фейлимо запит, якщо тільки save не вдався
        return {"response": response, "error": "Failed to save"}
```

---

## 🔍 Векторний пошук (pgvector)

### 1. Що таке pgvector?

**pgvector** - це розширення PostgreSQL для зберігання та пошуку векторів (embeddings).

```python
# Текст → Вектор (embedding)
text = "Як налаштувати PostgreSQL?"
embedding = [0.123, -0.456, 0.789, ...]  # 768 чисел

# Пошук схожих текстів
similar_texts = search_similar(embedding)
```

### 2. Створення embeddings

**Файл:** `vector_db/client.py`

```python
from sentence_transformers import SentenceTransformer

# Модель для створення embeddings
model = SentenceTransformer('paraphrase-multilingual-mpnet-base-v2')

def create_embedding(text: str) -> List[float]:
    """
    Перетворює текст у вектор (768 чисел)
    """
    embedding = model.encode(text, convert_to_numpy=True)
    return embedding.tolist()  # [0.123, -0.456, ..., 0.789]

# Приклад:
text = "Як працює база даних?"
vector = create_embedding(text)
# [0.0234, -0.1234, 0.5678, ..., -0.9012]  (768 чисел)
```

### 3. Збереження в pgvector

```python
async def save_chat_embedding(
    chat_id: str,
    user_id: int,
    text: str,
    role: str,
    message_id: int
):
    """
    Зберігає embedding у PostgreSQL
    """
    # Крок 1: Створюємо embedding
    embedding_vector = create_embedding(text)
    
    # Крок 2: Зберігаємо в БД
    embedding_record = ChatEmbedding(
        user_id=user_id,
        chat_id=chat_id,
        message_id=message_id,
        embedding=embedding_vector,  # pgvector vector(768)
        text_content=text
    )
    
    db.add(embedding_record)
    db.commit()
```

### 4. Семантичний пошук

**Файл:** `core/semantic_search.py`

```python
def search_chat_messages(
    chat_id: str,
    query_text: str,
    n_results: int = 3,
    user_id: int = None
) -> List[Dict]:
    """
    Знаходить найсхожіші повідомлення у ПОТОЧНОМУ чаті
    """
    # Крок 1: Створюємо embedding запиту
    query_embedding = create_embedding(query_text)
    
    # Крок 2: Векторний пошук (cosine similarity)
    results = db.query(ChatEmbedding)\
        .filter(
            ChatEmbedding.user_id == user_id,
            ChatEmbedding.chat_id == chat_id
        )\
        .order_by(
            ChatEmbedding.embedding.cosine_distance(query_embedding)
        )\
        .limit(n_results)\
        .all()
    
    return [
        {
            "text": r.text_content,
            "message_id": r.message_id,
            "similarity": 1 - cosine_distance(query_embedding, r.embedding)
        }
        for r in results
    ]

def search_chats(
    query_text: str,
    n_results: int = 2,
    user_id: int = None,
    exclude_chat_id: str = None
) -> List[Dict]:
    """
    Знаходить найсхожіші повідомлення у ВСІХ чатах користувача
    """
    query_embedding = create_embedding(query_text)
    
    query = db.query(ChatEmbedding)\
        .filter(ChatEmbedding.user_id == user_id)
    
    # Виключаємо поточний чат
    if exclude_chat_id:
        query = query.filter(ChatEmbedding.chat_id != exclude_chat_id)
    
    results = query\
        .order_by(
            ChatEmbedding.embedding.cosine_distance(query_embedding)
        )\
        .limit(n_results)\
        .all()
    
    return [
        {
            "text": r.text_content,
            "chat_id": r.chat_id,
            "message_id": r.message_id,
            "similarity": 1 - cosine_distance(query_embedding, r.embedding)
        }
        for r in results
    ]
```

### 5. Як працює cosine similarity?

```python
# Два вектори (embeddings)
vec1 = [0.5, 0.3, 0.2]  # "Як налаштувати базу даних?"
vec2 = [0.4, 0.35, 0.25]  # "База даних PostgreSQL"
vec3 = [0.1, 0.9, 0.0]  # "Погода сьогодні"

# Cosine similarity (від 0 до 1, де 1 = ідентичні)
similarity(vec1, vec2) = 0.95  # Дуже схожі
similarity(vec1, vec3) = 0.15  # Несхожі

# pgvector використовує cosine distance (від 0 до 2, де 0 = ідентичні)
cosine_distance = 1 - cosine_similarity

# У SQL:
SELECT * FROM chat_embeddings
ORDER BY embedding <=> '[0.5, 0.3, 0.2]'  -- <=> = cosine distance
LIMIT 3;
```

---

## ⚙️ Процес обробки запиту

### Повний lifecycle запиту

```python
┌─────────────────────────────────────────────────────────────┐
│                  LIFECYCLE ЗАПИТУ                           │
└─────────────────────────────────────────────────────────────┘

1️⃣ ОТРИМАННЯ ЗАПИТУ
   ↓
   POST /api/process
   {
       "text": "Як працює база даних?",
       "chat_id": "abc123",
       "archetype_id": "afina"
   }

2️⃣ АВТЕНТИФІКАЦІЯ
   ↓
   JWT токен → current_user_id = 5
   Rate limiting: 60 запитів/хв ✅

3️⃣ ЗАВАНТАЖЕННЯ КОНТЕКСТУ
   ↓
   ┌────────────────────────────────────┐
   │ A. Sliding Window                  │
   │    └─ Останні 3 обміни (6 повідомлень) │
   │                                    │
   │ B. Semantic Search - Current Chat  │
   │    └─ Top 3 схожі з поточного чату│
   │                                    │
   │ C. Semantic Search - Global        │
   │    └─ Top 2 схожі з інших чатів   │
   └────────────────────────────────────┘

4️⃣ ФОРМУВАННЯ ПРОМПТУ
   ↓
   System Prompt (архетип Афіна):
   "Ти - інтелектуальний асистент..."
   
   Context:
   [Sliding Window + Semantic Search]
   
   User Message:
   "Як працює база даних?"

5️⃣ AI ОБРОБКА
   ↓
   Google AI API (primary) або OpenAI (fallback)
   ↓
   Response: "База даних PostgreSQL використовує..."

6️⃣ ЗБЕРЕЖЕННЯ В БД
   ↓
   PostgreSQL:
   ├─ chat_messages: user message
   ├─ chat_messages: assistant response
   └─ chat_embeddings: vectors для обох

7️⃣ ВІДПОВІДЬ КОРИСТУВАЧУ
   ↓
   {
       "response": "База даних PostgreSQL...",
       "chat_id": "abc123",
       "stats": {
           "tokens_used": 1234,
           "cache_hit": false
       }
   }
```

### Код повного циклу

**Файл:** `main_production.py`

```python
@app.post("/api/process")
async def process_message(
    request: ProcessRequest,
    current_user_id: int = Depends(get_current_user_id),
    db: Session = Depends(get_db)
):
    """
    ═══════════════════════════════════════════════════
    КРОК 1: Валідація вхідних даних
    ═══════════════════════════════════════════════════
    """
    if not request.text or not request.text.strip():
        raise HTTPException(400, "Text cannot be empty")
    
    user_message = request.text.strip()
    chat_id = request.chat_id or str(uuid.uuid4())
    archetype_id = request.archetype_id or "afina"
    
    """
    ═══════════════════════════════════════════════════
    КРОК 2: Завантаження архетипу
    ═══════════════════════════════════════════════════
    """
    archetype = load_archetype_config(archetype_id, current_user_id)
    if not archetype:
        raise HTTPException(404, "Archetype not found")
    
    """
    ═══════════════════════════════════════════════════
    КРОК 3: Знаходимо наступний message_index
    ═══════════════════════════════════════════════════
    """
    last_message = db.query(ChatMessage)\
        .filter(
            ChatMessage.user_id == current_user_id,
            ChatMessage.chat_id == chat_id
        )\
        .order_by(ChatMessage.message_index.desc())\
        .first()
    
    next_index = (last_message.message_index + 1) if last_message else 0
    
    """
    ═══════════════════════════════════════════════════
    КРОК 4: Зберігаємо повідомлення користувача
    ═══════════════════════════════════════════════════
    """
    user_msg_db = ChatMessage(
        user_id=current_user_id,
        chat_id=chat_id,
        role="user",
        content=user_message,
        message_index=next_index
    )
    db.add(user_msg_db)
    db.commit()
    db.refresh(user_msg_db)  # Отримуємо ID
    
    """
    ═══════════════════════════════════════════════════
    КРОК 5: AI обробка (з контекстом)
    ═══════════════════════════════════════════════════
    """
    try:
        ai_response = await process_with_archetype(
            text=user_message,
            chat_id=chat_id,
            user_id=current_user_id,
            archetype_data=archetype
        )
    except Exception as e:
        logger.error(f"AI processing error: {e}")
        raise HTTPException(500, "AI processing failed")
    
    """
    ═══════════════════════════════════════════════════
    КРОК 6: Зберігаємо відповідь AI
    ═══════════════════════════════════════════════════
    """
    assistant_msg_db = ChatMessage(
        user_id=current_user_id,
        chat_id=chat_id,
        role="assistant",
        content=ai_response,
        message_index=next_index + 1
    )
    db.add(assistant_msg_db)
    db.commit()
    db.refresh(assistant_msg_db)
    
    """
    ═══════════════════════════════════════════════════
    КРОК 7: Зберігаємо embeddings для semantic search
    ═══════════════════════════════════════════════════
    """
    try:
        # User message embedding
        await save_chat_embedding(
            chat_id=chat_id,
            user_id=current_user_id,
            text=user_message,
            role="user",
            message_id=user_msg_db.id
        )
        
        # Assistant response embedding
        await save_chat_embedding(
            chat_id=chat_id,
            user_id=current_user_id,
            text=ai_response,
            role="assistant",
            message_id=assistant_msg_db.id
        )
    except Exception as e:
        logger.warning(f"Failed to save embeddings: {e}")
        # Не фейлимо запит, якщо embeddings не збереглися
    
    """
    ═══════════════════════════════════════════════════
    КРОК 8: Повертаємо відповідь
    ═══════════════════════════════════════════════════
    """
    return {
        "response": ai_response,
        "chat_id": chat_id,
        "message_index": next_index + 1,
        "archetype": archetype_id
    }
```

---

## 🔐 Автентифікація

### 1. JWT токени

**Файл:** `core/auth.py`

```python
from jose import jwt, JWTError
from datetime import datetime, timedelta

SECRET_KEY = os.getenv("SECRET_KEY", "your-secret-key-here")
ALGORITHM = "HS256"
ACCESS_TOKEN_EXPIRE_DAYS = 7

def create_access_token(data: dict) -> str:
    """
    Створює JWT токен
    """
    to_encode = data.copy()
    expire = datetime.utcnow() + timedelta(days=ACCESS_TOKEN_EXPIRE_DAYS)
    to_encode.update({"exp": expire})
    
    encoded_jwt = jwt.encode(to_encode, SECRET_KEY, algorithm=ALGORITHM)
    return encoded_jwt

# Приклад:
token = create_access_token({"sub": "admin@brainai.local", "user_id": 1})
# eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9...
```

### 2. Перевірка токена

```python
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials

security = HTTPBearer()

async def get_current_user_id(
    credentials: HTTPAuthorizationCredentials = Depends(security),
    db: Session = Depends(get_db)
) -> int:
    """
    Dependency для отримання user_id з JWT
    """
    token = credentials.credentials
    
    try:
        # Декодуємо JWT
        payload = jwt.decode(token, SECRET_KEY, algorithms=[ALGORITHM])
        email: str = payload.get("sub")
        user_id: int = payload.get("user_id")
        
        if email is None or user_id is None:
            raise HTTPException(401, "Invalid token")
        
        # Перевіряємо чи сесія ще активна
        session = db.query(UserSession)\
            .filter(UserSession.token_hash == hash_token(token))\
            .first()
        
        if not session:
            raise HTTPException(401, "Session expired")
        
        if session.expires_at < datetime.utcnow():
            raise HTTPException(401, "Token expired")
        
        return user_id
    
    except JWTError:
        raise HTTPException(401, "Invalid token")

# Використання:
@app.get("/api/profile")
async def get_profile(current_user_id: int = Depends(get_current_user_id)):
    # current_user_id автоматично витягується з JWT
    return {"user_id": current_user_id}
```

### 3. Хешування паролів

**Bcrypt з SHA256 pre-hash** (обхід 72-byte ліміту bcrypt)

```python
import bcrypt
import hashlib

class User(Base):
    @staticmethod
    def hash_password(password: str) -> str:
        """
        SHA256 → bcrypt (обхід 72-byte ліміту)
        """
        # Крок 1: SHA256 pre-hash
        sha_hash = hashlib.sha256(password.encode()).hexdigest()
        
        # Крок 2: bcrypt hash
        bcrypt_hash = bcrypt.hashpw(
            sha_hash.encode(),
            bcrypt.gensalt()
        )
        
        return bcrypt_hash.decode()
    
    def verify_password(self, password: str) -> bool:
        """
        Перевірка пароля
        """
        # Крок 1: SHA256 pre-hash
        sha_hash = hashlib.sha256(password.encode()).hexdigest()
        
        # Крок 2: Порівняння з bcrypt hash
        return bcrypt.checkpw(
            sha_hash.encode(),
            self.password_hash.encode()
        )

# Приклад:
user = User(email="admin@brainai.local")
user.password_hash = User.hash_password("SecureAdmin2024!")

# Перевірка:
user.verify_password("SecureAdmin2024!")  # True
user.verify_password("wrong")  # False
```

### 4. Login/Register flow

```python
@app.post("/api/auth/login")
async def login(
    request: LoginRequest,
    db: Session = Depends(get_db)
):
    """
    КРОК 1: Знайти користувача
    """
    user = db.query(User)\
        .filter(User.email == request.email)\
        .first()
    
    if not user:
        raise HTTPException(401, "Invalid credentials")
    
    """
    КРОК 2: Перевірити пароль
    """
    if not user.verify_password(request.password):
        raise HTTPException(401, "Invalid credentials")
    
    """
    КРОК 3: Створити JWT токен
    """
    access_token = create_access_token({
        "sub": user.email,
        "user_id": user.id
    })
    
    """
    КРОК 4: Зберегти сесію
    """
    session = UserSession(
        user_id=user.id,
        token_hash=hash_token(access_token),
        expires_at=datetime.utcnow() + timedelta(days=7)
    )
    db.add(session)
    db.commit()
    
    """
    КРОК 5: Повернути токен
    """
    return {
        "access_token": access_token,
        "token_type": "bearer",
        "expires_in": 7 * 24 * 60 * 60  # 7 днів у секундах
    }
```

---

## 🎭 Архетипи AI

### 1. Конфігурація архетипу

**Файл:** `archetypes.yaml`

```yaml
afina:
  name: "Афіна"
  description: "Інтелектуальний асистент для навчання та наукової роботи"
  
  prompts:
    base: "prompts/afina_base.txt"
    context_instructions: "prompts/afina_context_instructions.txt"
    response_style: "prompts/afina_response_style.txt"
  
  settings:
    temperature: 0.7        # Креативність (0-1)
    max_tokens: 2000        # Максимум токенів у відповіді
    top_p: 0.9              # Nucleus sampling
    frequency_penalty: 0.5  # Уникати повторень
    presence_penalty: 0.3   # Заохочувати нові теми

sofiya:
  name: "Софія"
  description: "Креативний асистент для написання текстів"
  
  prompts:
    base: "prompts/sofiya_base.txt"
    context_instructions: "prompts/sofiya_context_instructions.txt"
    response_style: "prompts/sofiya_response_style.txt"
  
  settings:
    temperature: 0.9        # Більше креативності
    max_tokens: 3000
    top_p: 0.95
    frequency_penalty: 0.7
    presence_penalty: 0.5
```

### 2. Структура промптів

**Файл:** `prompts/afina_base.txt`

```
Ти - Афіна, інтелектуальний асистент створений для допомоги у навчанні та науковій роботі.

ТВОЇ ПРИНЦИПИ:
1. Точність та фактична коректність
2. Структурованість та логічність викладу
3. Посилання на джерела та перевірені дані
4. Спрощення складних концепцій без втрати змісту

ТВОЇ ВМІННЯ:
- Аналіз та синтез інформації
- Пояснення складних концепцій простою мовою
- Допомога у дослідженнях та написанні наукових робіт
- Критичне мислення та логічна аргументація

СТИЛЬ КОМУНІКАЦІЇ:
- Професійний, але дружній
- Структуровані відповіді з використанням списків та підзаголовків
- Приклади для ілюстрації складних тем
- Запитання для уточнення, якщо потрібно
```

### 3. Завантаження архетипу

**Файл:** `core/logic.py`

```python
def load_archetype_config(archetype_id: str, user_id: int) -> dict:
    """
    Завантаження конфігурації архетипу
    """
    # Спочатку шукаємо кастомний архетип користувача
    custom = db.query(Archetype)\
        .filter(
            Archetype.user_id == user_id,
            Archetype.name == archetype_id
        )\
        .first()
    
    if custom:
        return custom.config
    
    # Якщо немає кастомного, завантажуємо з archetypes.yaml
    with open("archetypes.yaml", "r", encoding="utf-8") as f:
        archetypes = yaml.safe_load(f)
    
    if archetype_id not in archetypes:
        return None
    
    config = archetypes[archetype_id]
    
    # Завантажуємо промпти з файлів
    config["system_prompt"] = load_prompt_file(
        config["prompts"]["base"]
    )
    config["context_instructions"] = load_prompt_file(
        config["prompts"]["context_instructions"]
    )
    config["response_style"] = load_prompt_file(
        config["prompts"]["response_style"]
    )
    
    return config

def load_prompt_file(filepath: str) -> str:
    """
    Завантаження тексту промпту з файлу
    """
    with open(filepath, "r", encoding="utf-8") as f:
        return f.read()
```

### 4. Використання в AI запиті

```python
async def process_with_archetype(
    text: str,
    chat_id: str,
    user_id: int,
    archetype_data: dict
):
    """
    КРОК 1: Формуємо system prompt
    """
    system_prompt = archetype_data["system_prompt"]
    
    """
    КРОК 2: Додаємо інструкції щодо контексту
    """
    context_instructions = archetype_data["context_instructions"]
    
    """
    КРОК 3: Завантажуємо контекст
    """
    recent_messages = load_recent_messages(chat_id, user_id, limit=3)
    relevant_context = search_relevant_context(text, chat_id, user_id)
    
    """
    КРОК 4: Формуємо фінальний промпт
    """
    messages = [
        {
            "role": "system",
            "content": f"{system_prompt}\n\n{context_instructions}"
        },
        # Контекст з історії
        *[
            {"role": msg.role, "content": msg.content}
            for msg in recent_messages
        ],
        # Релевантний контекст
        {
            "role": "system",
            "content": f"Релевантна інформація:\n{relevant_context}"
        },
        # Поточний запит
        {
            "role": "user",
            "content": text
        }
    ]
    
    """
    КРОК 5: AI запит з налаштуваннями архетипу
    """
    response = await genai_client.generate_content(
        messages=messages,
        temperature=archetype_data["settings"]["temperature"],
        max_tokens=archetype_data["settings"]["max_tokens"],
        top_p=archetype_data["settings"]["top_p"]
    )
    
    return response.text
```

---

## ⚡ Оптимізація токенів

### 1. Проблема експлоненційного зростання

```python
# ❌ ПОГАНО: Завантажувати всю історію
all_messages = db.query(ChatMessage)\
    .filter(ChatMessage.chat_id == chat_id)\
    .all()

# Якщо у чаті 1000 повідомлень:
# 1000 * 200 токенів = 200,000 токенів
# Ліміт моделі: 32,000 токенів ❌
```

### 2. Sliding Window Strategy

```python
# ✅ ДОБРЕ: Тільки останні 3 обміни
MAX_RECENT_MESSAGES = 3  # 3 обміни = 6 повідомлень

recent_messages = db.query(ChatMessage)\
    .filter(ChatMessage.chat_id == chat_id)\
    .order_by(ChatMessage.message_index.desc())\
    .limit(MAX_RECENT_MESSAGES * 2)\  # * 2 бо user + assistant
    .all()

# 6 повідомлень * 200 токенів = 1,200 токенів ✅
```

### 3. Semantic Search Optimization

```python
# ✅ ДОБРЕ: Тільки найрелевантніші
relevant_current = search_chat_messages(
    chat_id=chat_id,
    query_text=text,
    n_results=3  # Топ-3 з поточного чату
)

relevant_global = search_chats(
    query_text=text,
    n_results=2,  # Топ-2 з інших чатів
    exclude_chat_id=chat_id
)

# 5 повідомлень * 200 токенів = 1,000 токенів ✅
```

### 4. Загальний бюджет токенів

```python
"""
РОЗПОДІЛ ТОКЕНІВ (на прикладі GPT-4):

Загальний ліміт: 8,192 токена

1. System Prompt (архетип):       500 токенів
2. Sliding Window (6 повідомлень): 1,200 токенів
3. Semantic Search (5 повідомлень): 1,000 токенів
4. User Message:                    300 токенів
5. Response Budget:                 2,000 токенів
6. Резерв:                          3,192 токена

TOTAL: 5,000 / 8,192 ≈ 61% використання
"""

def estimate_tokens(text: str) -> int:
    """
    Приблизна оцінка кількості токенів
    """
    # Англійська: ~4 символи = 1 токен
    # Українська: ~3 символи = 1 токен (більше UTF-8)
    return len(text) // 3

def trim_context_if_needed(messages: List[Dict], max_tokens: int = 5000):
    """
    Обрізання контексту якщо перевищено ліміт
    """
    total_tokens = sum(estimate_tokens(m["content"]) for m in messages)
    
    if total_tokens <= max_tokens:
        return messages
    
    # Видаляємо найстаріші повідомлення
    while total_tokens > max_tokens and len(messages) > 2:
        removed = messages.pop(0)  # Видаляємо найстаріше
        total_tokens -= estimate_tokens(removed["content"])
    
    return messages
```

### 5. Кешування для економії токенів

**Файл:** `core/cache.py`

```python
from functools import lru_cache
from datetime import datetime, timedelta

class ContextCache:
    def __init__(self, ttl_seconds: int = 300):
        self.cache = {}
        self.ttl = ttl_seconds
    
    def get(self, key: str):
        """
        Отримати з кешу
        """
        if key not in self.cache:
            return None
        
        entry = self.cache[key]
        if datetime.now() > entry["expires_at"]:
            del self.cache[key]
            return None
        
        return entry["value"]
    
    def set(self, key: str, value: any):
        """
        Зберегти в кеш
        """
        self.cache[key] = {
            "value": value,
            "expires_at": datetime.now() + timedelta(seconds=self.ttl)
        }

# Використання:
cache = ContextCache(ttl_seconds=300)  # 5 хвилин

def load_recent_messages(chat_id, user_id):
    # Перевіряємо кеш
    cache_key = f"recent:{chat_id}:{user_id}"
    cached = cache.get(cache_key)
    if cached:
        return cached
    
    # Завантажуємо з БД
    messages = db.query(ChatMessage)\
        .filter(...)\
        .all()
    
    # Зберігаємо в кеш
    cache.set(cache_key, messages)
    return messages
```

---

## 💡 Приклади коду

### Приклад 1: Повний цикл чату

```python
"""
Сценарій: Користувач починає новий чат про програмування
"""

# 1. Login
response = requests.post("http://localhost:8000/api/auth/login", json={
    "email": "admin@brainai.local",
    "password": "SecureAdmin2024!"
})
token = response.json()["access_token"]
headers = {"Authorization": f"Bearer {token}"}

# 2. Перше повідомлення (створює новий чат)
response = requests.post("http://localhost:8000/api/process", 
    headers=headers,
    json={
        "text": "Поясни що таке REST API",
        "archetype_id": "afina"
    }
)
chat_id = response.json()["chat_id"]
print(response.json()["response"])

# 3. Друге повідомлення (продовження чату)
response = requests.post("http://localhost:8000/api/process",
    headers=headers,
    json={
        "text": "А як зробити автентифікацію?",
        "chat_id": chat_id,  # Продовжуємо той самий чат
        "archetype_id": "afina"
    }
)
print(response.json()["response"])

# 4. Завантаження історії
response = requests.get(f"http://localhost:8000/api/history/db?chat_id={chat_id}",
    headers=headers
)
history = response.json()["chats"][chat_id]
for msg in history:
    print(f"{msg['role']}: {msg['content'][:50]}...")
```

### Приклад 2: Створення кастомного архетипу

```python
"""
Сценарій: Користувач створює власного AI асистента для кодування
"""

custom_archetype = {
    "name": "CodeMentor",
    "description": "Експерт з Python та веб-розробки",
    "system_prompt": """
        Ти - CodeMentor, експерт з програмування на Python.
        
        Твої завдання:
        1. Писати чистий, ідіоматичний Python код
        2. Пояснювати складні концепції простими словами
        3. Давати приклади коду з коментарями
        4. Вказувати на best practices
        
        Формат відповідей:
        - Короткий опис
        - Приклад коду
        - Пояснення
        - Підказки щодо покращення
    """,
    "settings": {
        "temperature": 0.5,  # Менше креативності для коду
        "max_tokens": 2500,
        "top_p": 0.8
    }
}

# Створюємо архетип
response = requests.post("http://localhost:8000/api/archetypes",
    headers=headers,
    json=custom_archetype
)

# Використовуємо новий архетип
response = requests.post("http://localhost:8000/api/process",
    headers=headers,
    json={
        "text": "Як реалізувати JWT автентифікацію?",
        "archetype_id": "CodeMentor"
    }
)
```

### Приклад 3: Семантичний пошук

```python
"""
Сценарій: Користувач шукає інформацію про базу даних,
яку обговорював 2 тижні тому
"""

# Поточний запит
user_query = "Як налаштувати індекси PostgreSQL?"

# Система автоматично:
# 1. Створює embedding запиту
query_embedding = create_embedding(user_query)

# 2. Шукає схожі повідомлення
similar_messages = db.query(ChatEmbedding)\
    .filter(ChatEmbedding.user_id == current_user_id)\
    .order_by(
        ChatEmbedding.embedding.cosine_distance(query_embedding)
    )\
    .limit(5)\
    .all()

# 3. Знаходить релевантний контекст:
# "PostgreSQL індекси потрібні для швидкості"
# "CREATE INDEX idx_name ON table(column)"
# "EXPLAIN ANALYZE покаже чи використовується індекс"

# 4. Додає до промпту
# AI відповідає з урахуванням попередньої розмови!
```

---

## 🎯 Висновок

### Ключові принципи BrainAi:

1. **Гібридна пам'ять**: Sliding Window + Semantic Search
2. **Ізоляція користувачів**: user_id у кожному запиті
3. **Оптимізація токенів**: Обмежений контекст (3+3+2)
4. **Векторний пошук**: pgvector для семантичного пошуку
5. **Транзакційність**: PostgreSQL + commit/rollback
6. **Безпека**: JWT + bcrypt + rate limiting
7. **Гнучкість**: Архетипи для різних сценаріїв

### Архітектурні рішення:

- ✅ PostgreSQL > SQLite (production)
- ✅ pgvector > FAISS/ChromaDB (інтеграція з PostgreSQL)
- ✅ JWT > Session cookies (stateless)
- ✅ FastAPI > Flask (async, швидкість)
- ✅ Sliding Window > Full history (токени)

### Наступні кроки:

1. Додати тести (критично!)
2. Додати WebSocket для streaming
3. Додати Redis для кешування
4. Розширити метрики та моніторинг
5. Додати support для файлів (PDF, DOCX)

---

**Останнє оновлення:** 16 листопада 2025  
**Версія:** 2.0 Production  
**Автор:** BrainAi Development Team
